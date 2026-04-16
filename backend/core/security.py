"""GENTURIX Core — Rate Limiting, Middleware, Security"""
from .imports import *
from .imports import _rate_limit_exceeded_handler
from .database import *

# ==================== RATE LIMITING CONFIGURATION ====================
# In-memory rate limiting for login brute-force protection
LOGIN_ATTEMPTS: Dict[str, list] = {}
MAX_ATTEMPTS_PER_MINUTE = 5
BLOCK_WINDOW_SECONDS = 60

def check_rate_limit(identifier: str) -> None:
    """
    Check if the identifier (email:ip) has exceeded rate limits.
    Raises HTTPException 429 if too many attempts.
    """
    now = get_time()
    attempts = LOGIN_ATTEMPTS.get(identifier, [])
    
    # Filter out old attempts outside the window
    attempts = [ts for ts in attempts if now - ts < BLOCK_WINDOW_SECONDS]
    
    if len(attempts) >= MAX_ATTEMPTS_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Please try again later."
        )
    
    # Record this attempt
    attempts.append(now)
    LOGIN_ATTEMPTS[identifier] = attempts

# ==================== PHASE 3: LOGGING CONFIGURATION ====================
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG' if ENVIRONMENT == 'development' else 'INFO').upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
logger.info(f"[STARTUP] Logging configured: level={LOG_LEVEL}, environment={ENVIRONMENT}")

# Log security warnings for missing configurations
if not STRIPE_WEBHOOK_SECRET:
    logger.warning("[SECURITY] STRIPE_WEBHOOK_SECRET not configured - webhook signature verification DISABLED")

# Create the main app
app = FastAPI(
    title="GENTURIX Enterprise Platform", 
    version="1.0.0",
    # Phase 4: Disable docs in production
    docs_url="/docs" if ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if ENVIRONMENT != "production" else None
)

# ==================== RATE LIMITING CONFIGURATION (2026-03-01) ====================
# Global rate limiter using slowapi
# Limits per IP address to prevent abuse
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Rate limit constants
RATE_LIMIT_GLOBAL = "60/minute"      # Default for most endpoints
RATE_LIMIT_AUTH = "5/minute"          # Login, register
RATE_LIMIT_SENSITIVE = "3/minute"     # Password reset, access requests
RATE_LIMIT_PUSH = "10/minute"         # Push notification endpoints

logger.info(f"[SECURITY] Rate limiting enabled: global={RATE_LIMIT_GLOBAL}, auth={RATE_LIMIT_AUTH}, sensitive={RATE_LIMIT_SENSITIVE}")

# ==================== INPUT SANITIZATION (2026-03-01) ====================
def sanitize_text(text: str, max_length: int = 10000) -> str:
    """
    Sanitize user input to prevent XSS attacks.
    
    - Strips all HTML tags
    - Removes potentially dangerous characters
    - Truncates to max_length
    
    Use for: names, descriptions, messages, notes, etc.
    Do NOT use for: IDs, emails, passwords, numeric fields
    """
    if not text:
        return text
    if not isinstance(text, str):
        return str(text)
    
    # Remove HTML tags completely
    cleaned = bleach.clean(text, tags=[], strip=True)
    # Truncate to max length
    return cleaned[:max_length] if len(cleaned) > max_length else cleaned


def sanitize_dict_fields(data: dict, fields: List[str]) -> dict:
    """
    Sanitize specific fields in a dictionary.
    Returns a new dict with sanitized values.
    """
    result = data.copy()
    for field in fields:
        if field in result and isinstance(result[field], str):
            result[field] = sanitize_text(result[field])
    return result


# Fields that should be sanitized (user-provided text)
SANITIZE_FIELDS = [
    "full_name", "name", "description", "message", "notes",
    "visitor_name", "public_description", "reason", "comments",
    "address", "contact_phone", "apartment", "apartment_number",
    "title", "comment", "subject", "body",
]

logger.info(f"[SECURITY] Input sanitization enabled for fields: {SANITIZE_FIELDS}")

# ==================== PHASE 2: REQUEST ID MIDDLEWARE ====================
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """
    Middleware that generates a unique request_id for each request.
    - Stores in request.state.request_id for access in handlers
    - Adds X-Request-ID header to response for client tracking
    """
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Optional: Log request start (debug level)
    if LOG_LEVEL == 'DEBUG':
        logger.debug(f"[REQUEST-START] {request_id} | {request.method} {request.url.path}")
    
    # Process request
    response = await call_next(request)
    
    # Add request_id header to response
    response.headers["X-Request-ID"] = request_id
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; img-src 'self' data: blob: https:; connect-src 'self' https://*.emergentagent.com https://*.stripe.com https://*.genturix.com; frame-src https://*.stripe.com"
    
    # Optional: Log request completion (debug level)
    if LOG_LEVEL == 'DEBUG':
        logger.debug(f"[REQUEST-END] {request_id} | Status: {response.status_code}")
    
    return response

# ==================== PARTIAL BILLING BLOCK MIDDLEWARE ====================
@app.middleware("http")
async def billing_block_middleware(request: Request, call_next):
    """
    Middleware for partial blocking of suspended condominiums.
    
    - Blocks POST/PUT/DELETE/PATCH for suspended condos
    - Allows GET requests (dashboard, queries)
    - Always allows: auth, health, billing, super-admin routes
    """
    # Always allow certain routes
    always_allowed = ["/api/auth/", "/api/health", "/api/billing/", "/api/super-admin/", "/api/push/"]
    path = request.url.path
    
    for allowed in always_allowed:
        if path.startswith(allowed):
            return await call_next(request)
    
    # Only block POST/PUT/DELETE/PATCH
    if request.method.upper() not in ["POST", "PUT", "DELETE", "PATCH"]:
        return await call_next(request)
    
    # Try to get user from token
    try:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            
            # SuperAdmins are never blocked
            roles = payload.get("roles", [])
            if "SuperAdmin" in roles:
                return await call_next(request)
            
            condominium_id = payload.get("condominium_id")
            if condominium_id:
                # Check billing status
                condo = await db.condominiums.find_one(
                    {"id": condominium_id},
                    {"_id": 0, "billing_status": 1, "is_demo": 1, "environment": 1}
                )
                
                if condo:
                    # Demo condos are never blocked
                    if condo.get("is_demo") or condo.get("environment") == "demo":
                        return await call_next(request)
                    
                    billing_status = condo.get("billing_status", "active")
                    if billing_status == "suspended":
                        return JSONResponse(
                            status_code=402,
                            content={
                                "detail": "Cuenta suspendida por falta de pago. Solo consultas permitidas.",
                                "billing_status": "suspended",
                                "action_required": "payment"
                            }
                        )
    except jwt.PyJWTError:
        pass  # Let the request continue, auth middleware will handle invalid tokens
    except Exception as e:
        logger.debug(f"[BILLING-BLOCK] Non-blocking error: {e}")
    
    return await call_next(request)

# ==================== PHASE 1: GLOBAL EXCEPTION HANDLERS ====================
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback

def get_user_id_from_request(request: Request) -> str:
    """Extract user_id from request state if available"""
    try:
        if hasattr(request.state, 'user'):
            return request.state.user.get('id', 'anonymous')
    except Exception as e:
        logger.debug(f"[AUTH] Could not extract user_id from request: {e}")
    return 'anonymous'

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handler for HTTP exceptions (4xx, 5xx).
    - Logs warning for client errors (4xx)
    - Logs error for server errors (5xx)
    - Includes request_id for traceability
    """
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    user_id = get_user_id_from_request(request)
    
    # Log based on status code severity
    log_data = {
        "request_id": request_id,
        "path": request.url.path,
        "method": request.method,
        "status_code": exc.status_code,
        "detail": exc.detail,
        "user_id": user_id
    }
    
    if exc.status_code >= 500:
        logger.error(f"[HTTP-ERROR] {log_data}")
    elif exc.status_code >= 400:
        logger.warning(f"[HTTP-WARN] {log_data}")
    
    # Return clean response with request_id
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail if isinstance(exc.detail, str) else "Request failed",
            "detail": exc.detail,
            "request_id": request_id
        },
        headers={"X-Request-ID": request_id}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Production-grade global exception handler.
    - Generates unique request_id for tracking
    - Logs full error details including traceback (internal only)
    - Returns safe JSON response without exposing internals
    - Adjusts detail level based on environment
    """
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    user_id = get_user_id_from_request(request)
    
    # Get full traceback for logging
    tb_str = traceback.format_exc()
    
    # Log complete error information (internal only)
    logger.error(
        f"[UNHANDLED-EXCEPTION]\n"
        f"  request_id: {request_id}\n"
        f"  path: {request.url.path}\n"
        f"  method: {request.method}\n"
        f"  user_id: {user_id}\n"
        f"  exception_type: {type(exc).__name__}\n"
        f"  exception_msg: {str(exc)}\n"
        f"  traceback:\n{tb_str}"
    )
    
    # Phase 4: Production protection - minimal details in response
    if ENVIRONMENT == "production":
        response_content = {
            "error": "Internal Server Error",
            "request_id": request_id
        }
    else:
        # Development: include more context (but never stacktrace)
        response_content = {
            "error": "Internal Server Error",
            "request_id": request_id,
            "detail": "An unexpected error occurred",
            "exception_type": type(exc).__name__
        }
    
    return JSONResponse(
        status_code=500,
        content=response_content,
        headers={"X-Request-ID": request_id}
    )

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ==================== BILLING ROUTER (PHASE 2 MODULARIZATION) ====================
# This router groups all billing-related endpoints for future extraction
# It uses /api/billing prefix via api_router include
billing_router = APIRouter(prefix="/billing", tags=["billing"])

# SuperAdmin billing router - uses /api/super-admin/billing/* path
billing_super_admin_router = APIRouter(prefix="/super-admin/billing", tags=["super-admin-billing"])

# ==================== HEALTH & READINESS ENDPOINTS ====================

# Application version
APP_VERSION = "1.0.0"
APP_SERVICE_NAME = "genturix-api"

@api_router.get("/health")
async def health_check():
    """
    Basic health check endpoint - ALWAYS returns 200 if server is alive.
    
    PHASE 1: Health Endpoint
    - NO database checks
    - NO external service validation
    - Used by load balancers for basic liveness probe
    
    Returns:
        200: {"status": "ok", "service": "genturix-api", "version": "1.0.0"}
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "service": APP_SERVICE_NAME,
            "version": APP_VERSION
        }
    )

@api_router.get("/readiness")
async def readiness_check(request: Request):
    """
    Readiness check endpoint - validates all critical dependencies.
    
    PHASE 2: Readiness Endpoint
    Validates:
    1. MongoDB connectivity (ping)
    2. JWT secrets configured
    3. Stripe API key present
    4. Resend API key present
    5. Valid ENVIRONMENT setting
    
    Returns:
        200: {"status": "ready"} - all dependencies OK
        503: {"status": "not_ready", "reason": "..."} - something failed
    
    SECURITY: Does NOT expose actual secret values, only presence check.
    """
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    checks_failed = []
    
    # CHECK 1: MongoDB connectivity
    try:
        await db.command("ping")
    except Exception as e:
        checks_failed.append("MongoDB connection failed")
        logger.error(
            f"[READINESS] MongoDB ping failed | request_id={request_id} | error={str(e)}"
        )
    
    # CHECK 2: JWT secrets present
    if not JWT_SECRET_KEY:
        checks_failed.append("JWT_SECRET_KEY not configured")
        logger.error(f"[READINESS] JWT_SECRET_KEY missing | request_id={request_id}")
    
    if not JWT_REFRESH_SECRET_KEY:
        checks_failed.append("JWT_REFRESH_SECRET_KEY not configured")
        logger.error(f"[READINESS] JWT_REFRESH_SECRET_KEY missing | request_id={request_id}")
    
    # CHECK 3: Stripe API key present
    stripe_key = os.environ.get("STRIPE_API_KEY", "")
    if not stripe_key:
        checks_failed.append("STRIPE_API_KEY not configured")
        logger.error(f"[READINESS] STRIPE_API_KEY missing | request_id={request_id}")
    
    # CHECK 4: Resend API key present
    resend_key = os.environ.get("RESEND_API_KEY", "")
    if not resend_key:
        checks_failed.append("RESEND_API_KEY not configured")
        logger.error(f"[READINESS] RESEND_API_KEY missing | request_id={request_id}")
    
    # CHECK 5: Valid ENVIRONMENT setting
    if ENVIRONMENT not in ["development", "production"]:
        checks_failed.append(f"Invalid ENVIRONMENT: {ENVIRONMENT}")
        logger.error(f"[READINESS] Invalid ENVIRONMENT | request_id={request_id} | value={ENVIRONMENT}")
    
    # Return result
    if checks_failed:
        # PHASE 3: Structured error logging
        logger.error(
            f"[READINESS] NOT READY | request_id={request_id} | "
            f"failed_checks={len(checks_failed)} | reasons={checks_failed}"
        )
        
        # PHASE 4: Security - generic message, no secrets exposed
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "reason": "One or more critical dependencies unavailable",
                "failed_checks": len(checks_failed),
                "request_id": request_id
            }
        )
    
    logger.debug(f"[READINESS] READY | request_id={request_id}")
    return JSONResponse(
        status_code=200,
        content={
            "status": "ready"
        }
    )
