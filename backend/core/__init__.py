# Trigger redeploy - 2026-03-01 SECURITY PATCH
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Request, Body, Query, UploadFile, File as FastAPIFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
import secrets
import string
import json
import hashlib
import re
import io
import random
import httpx
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import List, Optional, Dict, Any, Tuple
import uuid
from datetime import datetime, timezone, timedelta
from time import time as get_time
from zoneinfo import ZoneInfo
import bcrypt
import jwt
from enum import Enum
from bson import ObjectId

# ==================== SECURITY IMPORTS (2026-03-01) ====================
import bleach  # XSS protection via input sanitization
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest
import stripe  # For webhook signature verification
import resend
from pywebpush import webpush, WebPushException
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# ==================== BILLING MODULE IMPORTS (PHASE 3 - FULLY MODULARIZED) ====================
# All billing models, service functions, and scheduler are now imported from the module
from modules.billing.models import (
    BillingStatus,
    BillingCycle,
    BillingProvider,
    BillingEventType,
    SeatUpgradeRequestStatus,
    ConfirmPaymentRequest,
    ConfirmPaymentResponse,
    PaymentHistoryResponse,
    SeatUpgradeRequestModel,
    SeatUpgradeRequestResponse,
    SeatUpgradeRequest as BillingSeatUpgradeRequest,
    SeatUpdateRequest,
    BillingPreviewRequest,
    BillingPreviewResponse,
    BillingInfoResponse,
    SeatUsageResponse,
    SeatReductionValidation,
)

# Import service functions from billing module
from modules.billing.service import (
    DEFAULT_GRACE_PERIOD_DAYS,
    BILLING_EMAIL_TEMPLATES,
    init_service as init_billing_service,
    log_billing_engine_event,
    send_billing_notification_email,
    update_condominium_billing_status,
)

# Import scheduler functions from billing module
from modules.billing.scheduler import (
    init_scheduler as init_billing_scheduler,
    process_billing_for_condominium,
    run_daily_billing_check,
    start_billing_scheduler,
    stop_billing_scheduler,
    get_scheduler_instance,
)

# Import core seat engine functions from users module
from modules.users.service import (
    set_db as set_users_db,
    set_logger as set_users_logger,
    count_active_users,
    count_active_residents,
    update_active_user_count,
    can_create_user,
)

# Import user models from users module
from modules.users.models import (
    CreateUserByAdmin,
    CreateEmployeeByHR,
    UserStatusUpdateV2,
)

# Import centralized email service
from services.email_service import (
    send_email,
    send_email_sync,
    is_email_configured,
    get_email_status,
    get_sender,
    get_welcome_email_html,
    get_password_reset_email_html,
    get_emergency_alert_email_html,
    get_notification_email_html,
    get_condominium_welcome_email_html,
    get_visitor_preregistration_email_html,
    get_user_credentials_email_html,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# ==================== MONGODB CONNECTION ====================
# MONGO_URL must be set - supports both local (mongodb://) and Atlas (mongodb+srv://)
# Examples:
#   Local:  mongodb://localhost:27017
#   Atlas:  mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
mongo_url = os.environ.get('MONGO_URL')
if not mongo_url:
    raise RuntimeError("MONGO_URL environment variable is required")

db_name = os.environ.get('DB_NAME')
if not db_name:
    raise RuntimeError("DB_NAME environment variable is required")

# Configure client with production-ready settings for Atlas
# NOTE: Connection is lazy - actual connection happens on first operation
try:
    client = AsyncIOMotorClient(
        mongo_url,
        serverSelectionTimeoutMS=10000,  # 10s timeout for server selection
        connectTimeoutMS=20000,          # 20s timeout for initial connection
        socketTimeoutMS=30000,           # 30s timeout for socket operations
        maxPoolSize=50,                  # Connection pool for Railway
        retryWrites=True,
        retryReads=True,
        w='majority',                    # Write concern for Atlas
        appname='genturix-backend'       # Identify app in Atlas logs
    )
    db = client[db_name]
except Exception as e:
    # Log error but don't crash - let health/readiness endpoints report the issue
    import logging
    logging.error(f"[MONGO] Failed to initialize client: {e}")
    client = None
    db = None

# ==================== PHASE 1: ENVIRONMENT VALIDATION ====================
# Environment Configuration - MUST be validated first
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development').lower()

if ENVIRONMENT not in ["development", "production"]:
    raise RuntimeError("ENVIRONMENT must be 'development' or 'production'")

FRONTEND_URL = os.environ.get('FRONTEND_URL', '')

# Development Mode Configuration
# When DEV_MODE=true:
# - Disable mandatory password reset on first login
# - Don't block if email not configured
# - Return generated password in API response for testing
DEV_MODE = os.environ.get('DEV_MODE', 'false').lower() == 'true'

# SECURITY: DEV_MODE cannot be enabled in production
if ENVIRONMENT == "production" and DEV_MODE:
    raise RuntimeError("DEV_MODE cannot be enabled in production")

# ==================== PHASE 2: JWT SECRETS HARDENING ====================
# JWT Configuration - NO FALLBACK DEFAULTS (security requirement)
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
JWT_REFRESH_SECRET_KEY = os.environ.get('JWT_REFRESH_SECRET_KEY')

if not JWT_SECRET_KEY or not JWT_REFRESH_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY and JWT_REFRESH_SECRET_KEY must be defined in environment variables")

JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
# Phase 1: Reduced TTL from 30 to 15 minutes for better security
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', 15))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.environ.get('REFRESH_TOKEN_EXPIRE_MINUTES', 10080))

# Guard role extended session - 12 hours (720 minutes) for security personnel on shift
GUARD_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('GUARD_ACCESS_TOKEN_EXPIRE_MINUTES', 720))

# ==================== SECURE COOKIE CONFIGURATION ====================
# Cookie name for refresh token
REFRESH_TOKEN_COOKIE_NAME = "genturix_refresh_token"
# Cookie settings - SECURITY: httpOnly prevents XSS, Secure requires HTTPS
COOKIE_SECURE = ENVIRONMENT == "production"  # True in production (HTTPS required)
COOKIE_SAMESITE = "lax"  # Prevents CSRF while allowing same-site navigation
COOKIE_MAX_AGE = REFRESH_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds

# Email Configuration (Resend)
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
# Production sender - centralized in services/email_service.py
SENDER_EMAIL = "Genturix Security <no-reply@genturix.com>"
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Stripe Webhook Secret for signature verification (SECURITY CRITICAL)
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
# Warning logged after logger is initialized (see startup section)

# VAPID Configuration for Push Notifications
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
VAPID_CLAIMS_EMAIL = os.environ.get('VAPID_CLAIMS_EMAIL', 'admin@genturix.com')

# Password hashing using bcrypt directly (avoids passlib compatibility issues)
# No pwd_context needed - using bcrypt module directly

# Security
security = HTTPBearer()

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

# ==================== ENUMS ====================
class RoleEnum(str, Enum):
    SUPER_ADMIN = "SuperAdmin"
    ADMINISTRADOR = "Administrador"
    SUPERVISOR = "Supervisor"
    HR = "HR"  # Human Resources - manages employees, recruitment, absences
    GUARDA = "Guarda"
    RESIDENTE = "Residente"
    ESTUDIANTE = "Estudiante"

class AuditEventType(str, Enum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    PANIC_BUTTON = "panic_button"
    PANIC_RESOLVED = "panic_resolved"
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    PAYMENT_INITIATED = "payment_initiated"
    PAYMENT_COMPLETED = "payment_completed"
    COURSE_ENROLLED = "course_enrolled"
    CERTIFICATE_ISSUED = "certificate_issued"
    SHIFT_CREATED = "shift_created"
    # Super Admin events
    CONDO_CREATED = "condo_created"
    CONDO_UPDATED = "condo_updated"
    CONDO_DEACTIVATED = "condo_deactivated"
    MODULE_TOGGLED = "module_toggled"
    USER_LOCKED = "user_locked"
    USER_UNLOCKED = "user_unlocked"
    DEMO_RESET = "demo_reset"
    PLAN_UPDATED = "plan_updated"
    SHIFT_UPDATED = "shift_updated"
    SHIFT_DELETED = "shift_deleted"
    CLOCK_IN = "clock_in"
    CLOCK_OUT = "clock_out"
    ABSENCE_REQUESTED = "absence_requested"
    ABSENCE_APPROVED = "absence_approved"
    ABSENCE_REJECTED = "absence_rejected"
    # Recruitment events
    CANDIDATE_CREATED = "candidate_created"
    CANDIDATE_UPDATED = "candidate_updated"
    CANDIDATE_HIRED = "candidate_hired"
    CANDIDATE_REJECTED = "candidate_rejected"
    # User management events
    EMPLOYEE_CREATED = "employee_created"
    EMPLOYEE_DEACTIVATED = "employee_deactivated"
    EMPLOYEE_ACTIVATED = "employee_activated"
    # Performance evaluation events
    EVALUATION_CREATED = "evaluation_created"
    EVALUATION_UPDATED = "evaluation_updated"
    # Credential email events
    CREDENTIALS_EMAIL_SENT = "credentials_email_sent"
    CREDENTIALS_EMAIL_FAILED = "credentials_email_failed"
    PASSWORD_CHANGED = "password_changed"
    # Condominium management events
    CONDOMINIUM_DELETED = "condominium_deleted"
    # Visitor Authorization events
    AUTHORIZATION_CREATED = "authorization_created"
    AUTHORIZATION_UPDATED = "authorization_updated"
    AUTHORIZATION_DEACTIVATED = "authorization_deactivated"
    VISITOR_CHECKIN = "visitor_checkin"
    VISITOR_CHECKOUT = "visitor_checkout"
    VISITOR_ARRIVAL_NOTIFIED = "visitor_arrival_notified"
    VISITOR_EXIT_NOTIFIED = "visitor_exit_notified"
    # User status events
    USER_BLOCKED = "user_blocked"
    USER_UNBLOCKED = "user_unblocked"
    USER_SUSPENDED = "user_suspended"
    USER_DELETED = "user_deleted"
    # Seat management events
    SEAT_LIMIT_UPDATED = "seat_limit_updated"
    SEAT_REDUCTION_BLOCKED = "seat_reduction_blocked"
    # Password reset events
    PASSWORD_RESET_BY_ADMIN = "password_reset_by_admin"
    PASSWORD_RESET_TOKEN_USED = "password_reset_token_used"
    # Security events
    SECURITY_ALERT = "security_alert"
    # Pricing events
    PRICING_GLOBAL_UPDATED = "pricing_global_updated"
    PRICING_OVERRIDE_UPDATED = "pricing_override_updated"

# ==================== USER STATUS ENUM ====================
class UserStatus(str, Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    SUSPENDED = "suspended"

# ==================== MODELS ====================
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    roles: List[RoleEnum] = [RoleEnum.RESIDENTE]
    condominium_id: Optional[str] = None  # Multi-tenant support

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    roles: List[str]
    is_active: bool
    status: str = "active"  # active, blocked, suspended
    created_at: str
    condominium_id: Optional[str] = None  # Multi-tenant support
    password_reset_required: bool = False  # True if user needs to change password

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None  # DEPRECATED: Now sent as httpOnly cookie
    token_type: str = "bearer"
    user: UserResponse
    password_reset_required: bool = False  # Flag for frontend to show password change dialog

class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None  # Optional - can come from httpOnly cookie instead

# Password Change Model
class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password meets security requirements"""
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v

# Profile Models
class ProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    roles: List[str]
    is_active: bool
    created_at: str
    condominium_id: Optional[str] = None
    condominium_name: Optional[str] = None
    phone: Optional[str] = None
    profile_photo: Optional[str] = None
    public_description: Optional[str] = None
    role_data: Optional[Dict[str, Any]] = None
    language: str = "es"  # User's preferred language

class PublicProfileResponse(BaseModel):
    """Public profile visible to other users in same condominium"""
    id: str
    full_name: str
    roles: List[str]
    profile_photo: Optional[str] = None
    public_description: Optional[str] = None
    condominium_name: Optional[str] = None
    # Only show phone if user opted in
    phone: Optional[str] = None

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    profile_photo: Optional[str] = None
    public_description: Optional[str] = None

# Language Model
class LanguageUpdate(BaseModel):
    language: str = Field(..., pattern="^(es|en)$", description="Language code: 'es' or 'en'")

# Security Module Models
class PanicType(str, Enum):
    MEDICAL_EMERGENCY = "emergencia_medica"
    SUSPICIOUS_ACTIVITY = "actividad_sospechosa"
    GENERAL_EMERGENCY = "emergencia_general"

class PanicEventCreate(BaseModel):
    panic_type: PanicType
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None

class AccessLogCreate(BaseModel):
    person_name: str
    access_type: str  # entry, exit
    location: str
    notes: Optional[str] = None

class PanicResolveRequest(BaseModel):
    notes: Optional[str] = None

# HR Module Models
class GuardCreate(BaseModel):
    user_id: str
    badge_number: str
    phone: str
    emergency_contact: str
    hire_date: str
    hourly_rate: float

class GuardUpdate(BaseModel):
    badge_number: Optional[str] = None
    phone: Optional[str] = None
    emergency_contact: Optional[str] = None
    hourly_rate: Optional[float] = None
    is_active: Optional[bool] = None

class ShiftCreate(BaseModel):
    guard_id: str
    start_time: str
    end_time: str
    location: str
    notes: Optional[str] = None

class ShiftUpdate(BaseModel):
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None  # scheduled, in_progress, completed, cancelled

class ClockRequest(BaseModel):
    type: str  # "IN" or "OUT"

class AbsenceCreate(BaseModel):
    reason: str
    type: str  # vacaciones, permiso_medico, personal, otro
    start_date: str
    end_date: str
    notes: Optional[str] = None

class AbsenceAction(BaseModel):
    action: str  # approve, reject
    admin_notes: Optional[str] = None

# Performance Evaluation Models
class EvaluationCategory(BaseModel):
    discipline: int = Field(..., ge=1, le=5)
    punctuality: int = Field(..., ge=1, le=5)
    performance: int = Field(..., ge=1, le=5)
    communication: int = Field(..., ge=1, le=5)

class EvaluationCreate(BaseModel):
    employee_id: str
    categories: EvaluationCategory
    comments: Optional[str] = None

class EvaluationUpdate(BaseModel):
    categories: Optional[EvaluationCategory] = None
    comments: Optional[str] = None

# Recruitment Models
class CandidateCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    position: str  # Guarda, Supervisor
    experience_years: int = 0
    notes: Optional[str] = None
    documents: Optional[List[str]] = None  # URLs to documents

class CandidateUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    position: Optional[str] = None
    experience_years: Optional[int] = None
    notes: Optional[str] = None
    status: Optional[str] = None  # applied, interview, hired, rejected

class HireCandidate(BaseModel):
    badge_number: str
    hourly_rate: float
    password: str = Field(..., min_length=8)

# Condominium Deletion Model (Super Admin only)
class CondominiumDeleteRequest(BaseModel):
    password: str = Field(..., min_length=1, description="Super Admin password for verification")

# NOTE: CreateUserByAdmin and CreateEmployeeByHR models moved to modules/users/models.py
# Imported at top of file from modules.users.models

# School Module Models
class CourseCreate(BaseModel):
    title: str
    description: str
    duration_hours: int
    instructor: str
    category: str

class EnrollmentCreate(BaseModel):
    course_id: str
    student_id: str

class LessonProgressUpdate(BaseModel):
    course_id: str
    lesson_id: str
    completed: bool

# Payments Module Models
class PaymentPackage(BaseModel):
    package_id: str
    origin_url: str

class CheckoutStatusRequest(BaseModel):
    session_id: str

# ==================== VISITOR PRE-REGISTRATION MODELS ====================
class VisitTypeEnum(str, Enum):
    FAMILIAR = "familiar"
    DELIVERY = "delivery"
    SERVICE = "service"
    FRIEND = "friend"
    OTHER = "other"

class VisitorStatusEnum(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    ENTRY_REGISTERED = "entry_registered"
    EXIT_REGISTERED = "exit_registered"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class AuthorizationTypeEnum(str, Enum):
    TEMPORARY = "temporary"      # Single date or date range
    PERMANENT = "permanent"      # Always allowed
    RECURRING = "recurring"      # Specific days of week
    EXTENDED = "extended"        # Date range + time windows

class AuthorizationColorEnum(str, Enum):
    GREEN = "green"       # Permanent visitors
    BLUE = "blue"         # Recurring visitors
    YELLOW = "yellow"     # Temporary visitors
    PURPLE = "purple"     # Extended visitors
    GRAY = "gray"         # Expired/Inactive

class AuthorizationStatusEnum(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"

# New model for advanced visitor authorizations
class VisitorAuthorizationCreate(BaseModel):
    visitor_name: str = Field(..., min_length=2, max_length=100)
    identification_number: Optional[str] = None
    vehicle_plate: Optional[str] = None
    authorization_type: AuthorizationTypeEnum = AuthorizationTypeEnum.TEMPORARY
    valid_from: Optional[str] = None  # YYYY-MM-DD
    valid_to: Optional[str] = None    # YYYY-MM-DD
    allowed_days: Optional[List[str]] = None  # ["Lunes", "Martes", etc.]
    allowed_hours_from: Optional[str] = None  # HH:MM
    allowed_hours_to: Optional[str] = None    # HH:MM
    notes: Optional[str] = None
    # Visitor type fields (Delivery, Maintenance, Technical, Cleaning, Other)
    visitor_type: Optional[str] = "visitor"
    company: Optional[str] = None
    service_type: Optional[str] = None

class VisitorAuthorizationUpdate(BaseModel):
    visitor_name: Optional[str] = None
    identification_number: Optional[str] = None
    vehicle_plate: Optional[str] = None
    authorization_type: Optional[AuthorizationTypeEnum] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    allowed_days: Optional[List[str]] = None
    allowed_hours_from: Optional[str] = None
    allowed_hours_to: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    # Visitor type fields
    visitor_type: Optional[str] = None
    company: Optional[str] = None
    service_type: Optional[str] = None

# Fast Check-in by Guard
class FastCheckInRequest(BaseModel):
    authorization_id: Optional[str] = None  # If pre-authorized
    visitor_name: Optional[str] = None      # Manual entry if not authorized
    identification_number: Optional[str] = None
    vehicle_plate: Optional[str] = None
    destination: Optional[str] = None       # Apartment/House visiting
    notes: Optional[str] = None
    # New fields for visitor types (Delivery, Maintenance, etc.)
    visitor_type: Optional[str] = "visitor"  # visitor, delivery, maintenance, technical, cleaning, other
    company: Optional[str] = None            # Company name for delivery/maintenance/technical/cleaning
    service_type: Optional[str] = None       # Type of service (package, food, repair, etc.)
    authorized_by: Optional[str] = None      # Who authorized: resident, admin, guard
    estimated_time: Optional[str] = None     # Estimated time for cleaning

# Check-out by Guard  
class FastCheckOutRequest(BaseModel):
    notes: Optional[str] = None

class VisitorPreRegistration(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    national_id: Optional[str] = None  # Cedula
    vehicle_plate: Optional[str] = None
    visit_type: VisitTypeEnum = VisitTypeEnum.FRIEND
    expected_date: str  # ISO format date
    expected_time: Optional[str] = None
    notes: Optional[str] = None

class VisitorEntry(BaseModel):
    visitor_id: str
    notes: Optional[str] = None

class VisitorExit(BaseModel):
    visitor_id: str
    notes: Optional[str] = None

# ==================== DEVELOPER PROFILE MODEL ====================
class DeveloperProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=150)
    bio: Optional[str] = Field(None, max_length=2000)
    photo_url: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = Field(None, max_length=500)
    linkedin: Optional[str] = Field(None, max_length=500)
    github: Optional[str] = Field(None, max_length=500)

# ==================== RESERVATIONS MODELS ====================
class AreaTypeEnum(str, Enum):
    POOL = "pool"
    GYM = "gym"
    TENNIS = "tennis"
    BBQ = "bbq"
    SALON = "salon"
    CINEMA = "cinema"
    PLAYGROUND = "playground"
    OTHER = "other"

# NEW: Reservation behavior types (Phase 1)
class ReservationBehaviorEnum(str, Enum):
    EXCLUSIVE = "exclusive"      # 1 reserva bloquea el área (Rancho, Salón) - DEFAULT/LEGACY
    CAPACITY = "capacity"        # Múltiples reservas hasta max_capacity (Gimnasio, Piscina)
    SLOT_BASED = "slot_based"    # Slots fijos, 1 reserva = 1 slot (Canchas)
    FREE_ACCESS = "free_access"  # No se permiten reservas (áreas abiertas)

class ReservationModeEnum(str, Enum):
    BY_HOUR = "por_hora"      # Gym: 1 hour slots
    BLOCK = "bloque"          # Ranch: Full block reservation
    FLEXIBLE = "flexible"     # Pool: Configurable duration

class ReservationStatusEnum(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class AreaCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    area_type: AreaTypeEnum = AreaTypeEnum.OTHER
    capacity: int = Field(..., gt=0)
    description: Optional[str] = None
    rules: Optional[str] = None
    available_from: str = "06:00"  # Opening time HH:MM
    available_until: str = "22:00"  # Closing time HH:MM
    requires_approval: bool = False
    reservation_mode: str = "flexible"  # por_hora | bloque | flexible
    min_duration_hours: int = 1  # Minimum reservation duration
    max_duration_hours: int = 4  # Maximum reservation duration (renamed from max_hours_per_reservation)
    max_reservations_per_day: int = 10
    slot_duration_minutes: int = 60  # Duration of each slot (for visual display)
    allowed_days: List[str] = Field(default=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
    is_active: bool = True
    condominium_id: Optional[str] = None  # For SuperAdmin to specify condo
    # NEW: Phase 1 fields with backward-compatible defaults
    reservation_behavior: Optional[str] = "exclusive"  # exclusive | capacity | slot_based | free_access
    max_capacity_per_slot: Optional[int] = None  # For CAPACITY type: max people per time slot
    max_reservations_per_user_per_day: Optional[int] = None  # Limit per user per day

class AreaUpdate(BaseModel):
    name: Optional[str] = None
    area_type: Optional[AreaTypeEnum] = None
    capacity: Optional[int] = None
    description: Optional[str] = None
    rules: Optional[str] = None
    available_from: Optional[str] = None
    available_until: Optional[str] = None
    requires_approval: Optional[bool] = None
    reservation_mode: Optional[str] = None
    min_duration_hours: Optional[int] = None
    max_duration_hours: Optional[int] = None
    max_reservations_per_day: Optional[int] = None
    slot_duration_minutes: Optional[int] = None
    allowed_days: Optional[List[str]] = None
    is_active: Optional[bool] = None
    # NEW: Phase 1 fields
    reservation_behavior: Optional[str] = None
    max_capacity_per_slot: Optional[int] = None
    max_reservations_per_user_per_day: Optional[int] = None

class ReservationCreate(BaseModel):
    area_id: str
    date: str  # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    purpose: Optional[str] = None
    guests_count: int = 1

class ReservationUpdate(BaseModel):
    status: ReservationStatusEnum
    admin_notes: Optional[str] = None

# ==================== MULTI-TENANT MODELS ====================
# Configuración de módulos habilitados por condominio
class ModuleConfig(BaseModel):
    enabled: bool = False
    settings: Dict[str, Any] = {}

class CondominiumModules(BaseModel):
    security: ModuleConfig = ModuleConfig(enabled=True)
    hr: ModuleConfig = ModuleConfig(enabled=True)
    school: ModuleConfig = ModuleConfig(enabled=False)
    payments: ModuleConfig = ModuleConfig(enabled=True)
    audit: ModuleConfig = ModuleConfig(enabled=True)
    reservations: ModuleConfig = ModuleConfig(enabled=False)
    access_control: ModuleConfig = ModuleConfig(enabled=True)
    messaging: ModuleConfig = ModuleConfig(enabled=False)

class CondominiumCreate(BaseModel):
    """Model for creating PRODUCTION condominiums only"""
    name: str = Field(..., min_length=2, max_length=100)
    address: str = Field(..., min_length=5)
    contact_email: EmailStr
    contact_phone: str
    max_users: int = Field(default=100, ge=1)
    modules: Optional[CondominiumModules] = None
    # Billing fields for production - ENHANCED
    initial_units: int = Field(default=10, ge=1, le=10000, description="Number of billable seats")
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|yearly)$")
    billing_provider: str = Field(default="stripe", pattern="^(stripe|sinpe|ticopay|manual)$")
    billing_email: Optional[EmailStr] = None  # Separate email for invoices
    # Legacy field - kept for backward compatibility
    paid_seats: Optional[int] = None  # Will default to initial_units if not provided

class DemoCondominiumCreate(BaseModel):
    """Model for creating DEMO condominiums - simplified, no billing"""
    name: str = Field(..., min_length=2, max_length=100)
    address: str = Field(default="Demo Address")
    contact_email: EmailStr
    contact_phone: str = Field(default="")
    # Demo always has fixed 10 seats, no billing

class CondominiumUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    max_users: Optional[int] = None
    modules: Optional[CondominiumModules] = None
    is_active: Optional[bool] = None
    paid_seats: Optional[int] = None
    environment: Optional[str] = Field(default=None, pattern="^(demo|production)$")

class CondominiumResponse(BaseModel):
    id: str
    name: str
    address: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    max_users: int = 100
    current_users: int = 0
    modules: Dict[str, Any] = {}
    is_active: bool = True
    created_at: str
    price_per_user: float = 1.0  # $1 USD per user per month (legacy)
    status: str = "active"  # active, demo, suspended
    is_demo: bool = False
    discount_percent: float = 0.0
    plan: str = "basic"
    # Environment: "demo" or "production"
    environment: str = "production"
    # SaaS Billing Fields - ENHANCED
    billing_model: str = "per_seat"
    paid_seats: int = 10  # How many users are paid for
    price_per_seat: float = 1.50  # Dynamic price per seat
    billing_cycle: str = "monthly"  # monthly or yearly
    billing_provider: str = "stripe"  # stripe, sinpe, ticopay, manual
    billing_email: Optional[str] = None  # Email for invoices
    billing_status: str = "pending_payment"  # pending_payment, active, past_due, cancelled, trialing
    next_invoice_amount: float = 0.0  # Calculated monthly/yearly total
    next_billing_date: Optional[str] = None
    billing_started_at: Optional[str] = None
    yearly_discount_percent: float = 10.0  # Default 10% discount for yearly
    grace_period_days: int = 5  # Days after due date before suspension
    # Computed fields
    active_users: int = 0  # Real count of active users (excluding SuperAdmin)
    remaining_seats: int = 10  # paid_seats - active_users
    # Legacy Stripe fields (for future integration)
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    billing_period_end: Optional[str] = None

# SaaS Billing Models - Now imported from modules.billing.models
# (BillingStatus, BillingCycle, BillingProvider, BillingEventType, 
#  SeatUpgradeRequestStatus, ConfirmPaymentRequest, ConfirmPaymentResponse,
#  PaymentHistoryResponse, SeatUpgradeRequestModel, SeatUpgradeRequestResponse,
#  SeatUpgradeRequest, SeatUpdateRequest, BillingPreviewRequest, 
#  BillingPreviewResponse, BillingInfoResponse)

# Local alias for backward compatibility
SeatUpgradeRequest = BillingSeatUpgradeRequest

# Push Notification Models
class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str

class PushSubscriptionData(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys
    expirationTime: Optional[str] = None

class PushSubscriptionRequest(BaseModel):
    subscription: PushSubscriptionData

class PushNotificationPayload(BaseModel):
    title: str
    body: str
    icon: Optional[str] = "/logo192.png"
    badge: Optional[str] = "/logo192.png"
    tag: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    requireInteraction: bool = True
    urgency: str = "high"

# ==================== PUSH SUBSCRIPTION DOCUMENT SCHEMA ====================
# Each push_subscription document MUST have:
# - id: str (UUID)
# - user_id: str (REQUIRED - owner of subscription)
# - role: str (REQUIRED - user's primary role at subscription time)
# - condominium_id: str (REQUIRED - tenant scope)
# - endpoint: str (push service URL)
# - keys: { p256dh: str, auth: str }
# - is_active: bool
# - created_at: str (ISO datetime)
# - updated_at: str (ISO datetime)
# ===========================================================================

# ==================== INVITATION & ACCESS REQUEST MODELS ====================
class InvitationUsageLimitEnum(str, Enum):
    SINGLE = "single"           # 1 uso (default)
    UNLIMITED = "unlimited"     # Ilimitado hasta expirar
    FIXED = "fixed"             # Número fijo de usos

class InvitationCreate(BaseModel):
    expiration_days: int = Field(default=7, ge=1, le=365)  # 7, 30, o custom
    expiration_date: Optional[str] = None  # Custom date override (ISO format)
    usage_limit_type: InvitationUsageLimitEnum = InvitationUsageLimitEnum.SINGLE
    max_uses: int = Field(default=1, ge=1, le=1000)  # Only used if usage_limit_type is FIXED
    notes: Optional[str] = None  # Admin notes for this invitation

class InvitationResponse(BaseModel):
    id: str
    token: str
    condominium_id: str
    condominium_name: str
    created_by_id: str
    created_by_name: str
    expires_at: str
    usage_limit_type: str
    max_uses: int
    current_uses: int
    is_active: bool
    is_expired: bool
    notes: Optional[str] = None
    created_at: str
    invite_url: str

class AccessRequestCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    apartment_number: str = Field(..., min_length=1, max_length=50)
    tower_block: Optional[str] = None
    resident_type: str = Field(default="owner")  # owner, tenant
    notes: Optional[str] = None  # Message from requestor

class AccessRequestResponse(BaseModel):
    id: str
    invitation_id: str
    condominium_id: str
    condominium_name: str
    full_name: str
    email: str
    phone: Optional[str] = None
    apartment_number: str
    tower_block: Optional[str] = None
    resident_type: str
    notes: Optional[str] = None
    status: str  # pending_approval, approved, rejected
    status_message: Optional[str] = None  # Rejection reason or welcome message
    created_at: str
    processed_at: Optional[str] = None
    processed_by_id: Optional[str] = None
    processed_by_name: Optional[str] = None

class AccessRequestAction(BaseModel):
    action: str  # approve, reject
    message: Optional[str] = None  # Rejection reason or welcome message
    send_email: bool = True  # Send notification email to requestor

# ==================== CONDOMINIUM SETTINGS MODELS ====================
class WorkingHours(BaseModel):
    start: str = "06:00"
    end: str = "22:00"

class GeneralSettings(BaseModel):
    timezone: str = "America/Mexico_City"
    working_hours: WorkingHours = WorkingHours()
    condominium_name_display: Optional[str] = None  # Override display name

class ReservationSettings(BaseModel):
    enabled: bool = True
    max_active_per_user: int = Field(default=3, ge=1, le=20)
    allow_same_day: bool = True
    approval_required_by_default: bool = False
    min_hours_advance: int = Field(default=1, ge=0, le=72)  # Minimum hours in advance to reserve
    max_days_advance: int = Field(default=30, ge=1, le=365)  # Maximum days in advance to reserve

class VisitSettings(BaseModel):
    allow_resident_preregistration: bool = True
    allow_recurrent_visits: bool = True
    allow_permanent_visits: bool = False
    require_id_photo: bool = False
    max_preregistrations_per_day: int = Field(default=10, ge=1, le=50)

class NotificationSettings(BaseModel):
    panic_sound_enabled: bool = True
    push_enabled: bool = True
    email_notifications_enabled: bool = True

class CondominiumSettingsModel(BaseModel):
    general: GeneralSettings = GeneralSettings()
    reservations: ReservationSettings = ReservationSettings()
    visits: VisitSettings = VisitSettings()
    notifications: NotificationSettings = NotificationSettings()

class CondominiumSettingsUpdate(BaseModel):
    general: Optional[GeneralSettings] = None
    reservations: Optional[ReservationSettings] = None
    visits: Optional[VisitSettings] = None
    notifications: Optional[NotificationSettings] = None

class CondominiumSettingsResponse(BaseModel):
    condominium_id: str
    condominium_name: str
    general: GeneralSettings
    reservations: ReservationSettings
    visits: VisitSettings
    notifications: NotificationSettings
    updated_at: str
    created_at: str

# Helper function to get default settings
def get_default_condominium_settings() -> dict:
    """Get default condominium settings as dict"""
    return {
        "general": GeneralSettings().model_dump(),
        "reservations": ReservationSettings().model_dump(),
        "visits": VisitSettings().model_dump(),
        "notifications": NotificationSettings().model_dump()
    }

# ==================== HELPER FUNCTIONS ====================
def hash_password(password: str) -> str:
    """Hash password using bcrypt directly"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash using bcrypt directly"""
    if not hashed_password:
        return False
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False

def generate_temporary_password(length: int = 12) -> str:
    """Generate a secure temporary password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    # Ensure at least one of each: uppercase, lowercase, digit, special
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%")
    ]
    # Fill the rest with random characters
    password.extend(secrets.choice(alphabet) for _ in range(length - 4))
    # Shuffle to avoid predictable pattern
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)

async def send_credentials_email(
    recipient_email: str,
    user_name: str,
    role: str,
    condominium_name: str,
    temporary_password: str,
    login_url: str
) -> dict:
    """Send credentials email to new user using Resend"""
    
    print(f"[EMAIL TRIGGER] create_user → sending credentials to {recipient_email}")
    
    # FIRST: Check if email sending is enabled via toggle
    email_enabled = await is_email_enabled()
    if not email_enabled:
        print(f"[EMAIL BLOCKED] Email toggle is OFF (recipient: {recipient_email})")
        logger.info(f"Email not sent - Email sending is DISABLED via toggle (recipient: {recipient_email})")
        return {"status": "skipped", "reason": "Email sending disabled (testing mode)", "toggle_disabled": True}
    
    # SECOND: Check if API key is configured
    if not RESEND_API_KEY:
        print(f"[EMAIL BLOCKED] RESEND_API_KEY not configured")
        logger.warning("Email not sent - RESEND_API_KEY not configured")
        return {"status": "skipped", "reason": "Email service not configured"}
    
    # Role name in Spanish
    role_names = {
        "Residente": "Residente",
        "Guarda": "Guardia de Seguridad",
        "HR": "Recursos Humanos",
        "Supervisor": "Supervisor",
        "Estudiante": "Estudiante",
        "Administrador": "Administrador"
    }
    role_display = role_names.get(role, role)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0A0A0F; color: #ffffff; margin: 0; padding: 0;">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background-color: #0F111A; border-radius: 12px; overflow: hidden;">
            <tr>
                <td style="padding: 40px 30px; background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%);">
                    <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #ffffff;">GENTURIX</h1>
                    <p style="margin: 8px 0 0 0; font-size: 14px; color: rgba(255,255,255,0.8);">Plataforma de Seguridad Empresarial</p>
                </td>
            </tr>
            <tr>
                <td style="padding: 40px 30px;">
                    <h2 style="margin: 0 0 20px 0; font-size: 22px; color: #ffffff;">¡Bienvenido/a, {user_name}!</h2>
                    <p style="margin: 0 0 20px 0; font-size: 16px; color: #9CA3AF; line-height: 1.6;">
                        Se ha creado tu cuenta en la plataforma GENTURIX. A continuación encontrarás tus credenciales de acceso:
                    </p>
                    
                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #1E293B; border-radius: 8px; margin: 20px 0;">
                        <tr>
                            <td style="padding: 20px;">
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td style="padding: 8px 0; border-bottom: 1px solid #374151;">
                                            <span style="color: #9CA3AF; font-size: 13px;">Rol</span><br>
                                            <span style="color: #ffffff; font-size: 16px; font-weight: 600;">{role_display}</span>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; border-bottom: 1px solid #374151;">
                                            <span style="color: #9CA3AF; font-size: 13px;">Condominio</span><br>
                                            <span style="color: #ffffff; font-size: 16px; font-weight: 600;">{condominium_name}</span>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; border-bottom: 1px solid #374151;">
                                            <span style="color: #9CA3AF; font-size: 13px;">Email / Usuario</span><br>
                                            <span style="color: #6366F1; font-size: 16px; font-weight: 600;">{recipient_email}</span>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0;">
                                            <span style="color: #9CA3AF; font-size: 13px;">Contraseña Temporal</span><br>
                                            <span style="color: #10B981; font-size: 18px; font-weight: 700; font-family: monospace; letter-spacing: 1px;">{temporary_password}</span>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                    
                    <div style="background-color: #FEF3C7; border-radius: 8px; padding: 16px; margin: 20px 0;">
                        <p style="margin: 0; color: #92400E; font-size: 14px;">
                            ⚠️ <strong>Importante:</strong> Por seguridad, deberás cambiar tu contraseña en el primer inicio de sesión.
                        </p>
                    </div>
                    
                    <a href="{login_url}" style="display: inline-block; padding: 14px 28px; background-color: #6366F1; color: #ffffff; text-decoration: none; font-weight: 600; font-size: 16px; border-radius: 8px; margin: 20px 0;">
                        Iniciar Sesión
                    </a>
                    
                    <p style="margin: 20px 0 0 0; font-size: 14px; color: #6B7280;">
                        Si el botón no funciona, copia y pega esta URL en tu navegador:<br>
                        <a href="{login_url}" style="color: #6366F1;">{login_url}</a>
                    </p>
                </td>
            </tr>
            <tr>
                <td style="padding: 20px 30px; background-color: #0A0A0F; border-top: 1px solid #1E293B;">
                    <p style="margin: 0; font-size: 12px; color: #6B7280; text-align: center;">
                        Este es un correo automático de GENTURIX. Por favor no responder.<br>
                        © 2026 GENTURIX - Todos los derechos reservados.
                    </p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    params = {
        "from": SENDER_EMAIL,
        "to": [recipient_email],
        "subject": f"Tus Credenciales de Acceso a GENTURIX - {condominium_name}",
        "html": html_content
    }
    
    try:
        # Run sync SDK in thread to keep FastAPI non-blocking
        logger.info(f"[RESEND-AUDIT] Attempting to send credentials email | recipient={recipient_email} | from={SENDER_EMAIL}")
        email_response = await asyncio.to_thread(resend.Emails.send, params)
        
        # Detailed response logging for audit
        if isinstance(email_response, dict):
            email_id = email_response.get("id", "N/A")
            print(f"[EMAIL SENT] {recipient_email}")
            logger.info(f"[RESEND-AUDIT] SUCCESS | email_id={email_id} | recipient={recipient_email} | response={email_response}")
        else:
            print(f"[EMAIL SENT] {recipient_email}")
            logger.info(f"[RESEND-AUDIT] SUCCESS | response_type={type(email_response).__name__} | recipient={recipient_email} | response={email_response}")
        
        return {
            "status": "success",
            "email_id": email_response.get("id") if isinstance(email_response, dict) else str(email_response),
            "recipient": recipient_email,
            "from": SENDER_EMAIL
        }
    except Exception as e:
        error_str = str(e)
        error_type = type(e).__name__
        logger.error(f"[RESEND-AUDIT] FAILED | recipient={recipient_email} | error_type={error_type} | error={error_str}")
        return {
            "status": "failed",
            "error": error_str,
            "error_type": error_type,
            "recipient": recipient_email,
            "from": SENDER_EMAIL
        }

async def send_password_reset_email(
    recipient_email: str,
    user_name: str,
    new_password: str,
    login_url: str
) -> dict:
    """Send password reset email with new temporary password using Resend"""
    
    print(f"[EMAIL TRIGGER] password_reset → sending new password to {recipient_email}")
    
    # Check if email sending is enabled
    email_enabled = await is_email_enabled()
    if not email_enabled:
        print(f"[EMAIL BLOCKED] Email toggle is OFF (recipient: {recipient_email})")
        logger.info(f"Password reset email not sent - Email sending is DISABLED (recipient: {recipient_email})")
        return {"status": "skipped", "reason": "Email sending disabled", "toggle_disabled": True}
    
    if not RESEND_API_KEY:
        print(f"[EMAIL BLOCKED] RESEND_API_KEY not configured")
        logger.warning("Password reset email not sent - RESEND_API_KEY not configured")
        return {"status": "skipped", "reason": "Email service not configured"}
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0A0A0F; color: #ffffff; margin: 0; padding: 0;">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background-color: #0F111A; border-radius: 12px; overflow: hidden;">
            <tr>
                <td style="padding: 40px 30px; background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%);">
                    <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #ffffff;">GENTURIX</h1>
                    <p style="margin: 8px 0 0 0; font-size: 14px; color: rgba(255,255,255,0.8);">Restablecimiento de Contraseña</p>
                </td>
            </tr>
            <tr>
                <td style="padding: 40px 30px;">
                    <h2 style="margin: 0 0 20px 0; font-size: 22px; color: #ffffff;">Hola, {user_name}</h2>
                    <p style="margin: 0 0 20px 0; font-size: 16px; color: #9CA3AF; line-height: 1.6;">
                        Se ha restablecido tu contraseña. A continuación encontrarás tu nueva contraseña temporal:
                    </p>
                    
                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #1E293B; border-radius: 8px; margin: 20px 0;">
                        <tr>
                            <td style="padding: 20px; text-align: center;">
                                <span style="color: #9CA3AF; font-size: 13px;">Nueva Contraseña Temporal</span><br>
                                <span style="color: #10B981; font-size: 24px; font-weight: 700; font-family: monospace; letter-spacing: 2px;">{new_password}</span>
                            </td>
                        </tr>
                    </table>
                    
                    <div style="background-color: #FEF3C7; border-radius: 8px; padding: 16px; margin: 20px 0;">
                        <p style="margin: 0; color: #92400E; font-size: 14px;">
                            ⚠️ <strong>Importante:</strong> Por seguridad, deberás cambiar esta contraseña en tu próximo inicio de sesión.
                        </p>
                    </div>
                    
                    <a href="{login_url}" style="display: inline-block; padding: 14px 28px; background-color: #6366F1; color: #ffffff; text-decoration: none; font-weight: 600; font-size: 16px; border-radius: 8px; margin: 20px 0;">
                        Iniciar Sesión
                    </a>
                    
                    <p style="margin: 20px 0 0 0; font-size: 14px; color: #6B7280;">
                        Si no solicitaste este cambio, contacta inmediatamente al administrador.
                    </p>
                </td>
            </tr>
            <tr>
                <td style="padding: 20px 30px; background-color: #0A0A0F; border-top: 1px solid #1E293B;">
                    <p style="margin: 0; font-size: 12px; color: #6B7280; text-align: center;">
                        Este es un correo automático de GENTURIX. Por favor no responder.<br>
                        © 2026 GENTURIX - Todos los derechos reservados.
                    </p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    params = {
        "from": SENDER_EMAIL,
        "to": [recipient_email],
        "subject": "🔐 Restablecimiento de Contraseña - GENTURIX",
        "html": html_content
    }
    
    try:
        logger.info(f"[RESEND-AUDIT] Attempting to send password reset email | recipient={recipient_email} | from={SENDER_EMAIL}")
        email_response = await asyncio.to_thread(resend.Emails.send, params)
        
        if isinstance(email_response, dict):
            email_id = email_response.get("id", "N/A")
            print(f"[EMAIL SENT] {recipient_email}")
            logger.info(f"[RESEND-AUDIT] SUCCESS | email_id={email_id} | recipient={recipient_email} | type=password_reset")
        else:
            print(f"[EMAIL SENT] {recipient_email}")
            logger.info(f"[RESEND-AUDIT] SUCCESS | response_type={type(email_response).__name__} | recipient={recipient_email}")
        
        return {
            "status": "success",
            "email_id": email_response.get("id") if isinstance(email_response, dict) else str(email_response),
            "recipient": recipient_email,
            "from": SENDER_EMAIL
        }
    except Exception as e:
        error_str = str(e)
        error_type = type(e).__name__
        logger.error(f"[RESEND-AUDIT] FAILED | recipient={recipient_email} | error_type={error_type} | error={error_str} | type=password_reset")
        return {
            "status": "failed",
            "error": error_str,
            "error_type": error_type,
            "recipient": recipient_email,
            "from": SENDER_EMAIL
        }

# ==================== PASSWORD RESET TOKEN FUNCTIONS ====================
def create_password_reset_token(user_id: str, email: str) -> str:
    """Create a secure password reset token that expires in 1 hour"""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=1)
    to_encode = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": int(now.timestamp()),
        "type": "password_reset"
    }
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_password_reset_token(token: str) -> Optional[dict]:
    """Verify a password reset token and return payload if valid"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "password_reset":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("[RESET-TOKEN] Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"[RESET-TOKEN] Invalid token: {e}")
        return None

async def send_password_reset_link_email(
    recipient_email: str,
    user_name: str,
    reset_link: str,
    admin_name: str = "Administrador"
) -> dict:
    """Send password reset email with secure link (not temporary password)"""
    
    print(f"[EMAIL TRIGGER] password_reset_link → sending reset link to {recipient_email}")
    
    email_enabled = await is_email_enabled()
    if not email_enabled:
        print(f"[EMAIL BLOCKED] Email toggle is OFF (recipient: {recipient_email})")
        logger.info(f"Password reset link email not sent - Email sending is DISABLED (recipient: {recipient_email})")
        return {"status": "skipped", "reason": "Email sending disabled", "toggle_disabled": True}
    
    if not RESEND_API_KEY:
        print(f"[EMAIL BLOCKED] RESEND_API_KEY not configured")
        logger.warning("Password reset link email not sent - RESEND_API_KEY not configured")
        return {"status": "skipped", "reason": "Email service not configured"}
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0A0A0F; color: #ffffff; margin: 0; padding: 0;">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background-color: #0F111A; border-radius: 12px; overflow: hidden;">
            <tr>
                <td style="padding: 40px 30px; background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%);">
                    <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #ffffff;">GENTURIX</h1>
                    <p style="margin: 8px 0 0 0; font-size: 14px; color: rgba(255,255,255,0.8);">Solicitud de Restablecimiento de Contraseña</p>
                </td>
            </tr>
            <tr>
                <td style="padding: 40px 30px;">
                    <h2 style="margin: 0 0 20px 0; font-size: 22px; color: #ffffff;">Hola, {user_name}</h2>
                    <p style="margin: 0 0 20px 0; font-size: 16px; color: #9CA3AF; line-height: 1.6;">
                        El administrador <strong style="color: #ffffff;">{admin_name}</strong> ha solicitado restablecer tu contraseña.
                    </p>
                    <p style="margin: 0 0 20px 0; font-size: 16px; color: #9CA3AF; line-height: 1.6;">
                        Haz clic en el siguiente botón para crear tu nueva contraseña:
                    </p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_link}" style="display: inline-block; padding: 16px 32px; background: linear-gradient(135deg, #10B981 0%, #059669 100%); color: #ffffff; text-decoration: none; font-weight: 600; font-size: 16px; border-radius: 8px;">
                            🔐 Restablecer Contraseña
                        </a>
                    </div>
                    
                    <div style="background-color: #1E293B; border-radius: 8px; padding: 16px; margin: 20px 0;">
                        <p style="margin: 0; color: #9CA3AF; font-size: 14px;">
                            ⏰ Este enlace expirará en <strong style="color: #F59E0B;">1 hora</strong>.
                        </p>
                    </div>
                    
                    <div style="background-color: #FEF3C7; border-radius: 8px; padding: 16px; margin: 20px 0;">
                        <p style="margin: 0; color: #92400E; font-size: 14px;">
                            ⚠️ <strong>Importante:</strong> Si no reconoces esta solicitud, ignora este correo y contacta inmediatamente a tu administrador.
                        </p>
                    </div>
                    
                    <p style="margin: 20px 0 0 0; font-size: 13px; color: #6B7280;">
                        Si el botón no funciona, copia y pega este enlace en tu navegador:<br>
                        <span style="color: #60A5FA; word-break: break-all;">{reset_link}</span>
                    </p>
                </td>
            </tr>
            <tr>
                <td style="padding: 20px 30px; background-color: #0A0A0F; border-top: 1px solid #1E293B;">
                    <p style="margin: 0; font-size: 12px; color: #6B7280; text-align: center;">
                        Este es un correo automático de GENTURIX. Por favor no responder.<br>
                        © 2026 GENTURIX - Todos los derechos reservados.
                    </p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    params = {
        "from": SENDER_EMAIL,
        "to": [recipient_email],
        "subject": "🔐 Restablece tu Contraseña - GENTURIX",
        "html": html_content
    }
    
    try:
        email_response = await asyncio.to_thread(resend.Emails.send, params)
        print(f"[EMAIL SENT] {recipient_email}")
        logger.info(f"Password reset link email sent to {recipient_email}")
        return {
            "status": "success",
            "email_id": email_response.get("id") if isinstance(email_response, dict) else str(email_response),
            "recipient": recipient_email
        }
    except Exception as e:
        logger.error(f"Failed to send password reset link email to {recipient_email}: {str(e)}")
        return {
            "status": "failed",
            "error": str(e),
            "recipient": recipient_email
        }

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire, 
        "iat": int(now.timestamp()),  # Issued at timestamp
        "type": "access"
    })
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def create_refresh_token(data: dict, refresh_token_id: str) -> str:
    """
    Create a refresh token with rotation support.
    
    Phase 2 & 3: Refresh Token Rotation
    - Includes refresh_token_id in payload
    - This ID is stored in DB and validated on refresh
    - Prevents reuse of stolen refresh tokens
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire, 
        "iat": int(now.timestamp()),
        "type": "refresh",
        "jti": refresh_token_id  # JWT ID for rotation tracking
    })
    return jwt.encode(to_encode, JWT_REFRESH_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def verify_refresh_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_REFRESH_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    user = await db.users.find_one({"id": user_id})
    
    if not user or not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Security: Check user status (blocked/suspended users cannot access)
    user_status = user.get("status", "active")
    if user_status in ["blocked", "suspended"]:
        status_messages = {
            "blocked": "Tu cuenta ha sido bloqueada. Contacta al administrador.",
            "suspended": "Tu cuenta ha sido suspendida temporalmente. Contacta al administrador."
        }
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=status_messages.get(user_status, "Cuenta no disponible"),
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Security: Check if token was issued before status was changed (session invalidation)
    status_changed_at = user.get("status_changed_at")
    token_iat = payload.get("iat")
    
    if status_changed_at and token_iat:
        try:
            status_time = datetime.fromisoformat(status_changed_at.replace("Z", "+00:00"))
            status_timestamp = status_time.timestamp()
            
            if token_iat < status_timestamp:
                logger.info(f"[JWT-CHECK] Rejecting token - issued before status change. User: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session expired due to account status change. Please login again.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"[JWT-CHECK] Error parsing status_changed_at: {e}")
            pass
    
    # Security: Check if token was issued before password was changed
    # This invalidates all sessions after a password change
    password_changed_at = user.get("password_changed_at")
    
    if password_changed_at and token_iat:
        try:
            # Parse password_changed_at (ISO format) to timestamp
            pwd_changed_time = datetime.fromisoformat(password_changed_at.replace("Z", "+00:00"))
            pwd_changed_timestamp = pwd_changed_time.timestamp()
            
            logger.debug(f"[JWT-CHECK] Token iat: {token_iat}, Password changed at: {pwd_changed_timestamp}")
            
            # If token was issued BEFORE password was changed, reject it
            if token_iat < pwd_changed_timestamp:
                logger.info(f"[JWT-CHECK] Rejecting token - issued before password change. User: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session expired due to password change. Please login again.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Log any parsing errors but don't block the user
            logger.warning(f"[JWT-CHECK] Error parsing password_changed_at: {e}")
            pass
    
    return user

def require_role(*allowed_roles):
    async def check_role(current_user = Depends(get_current_user)):
        user_roles = current_user.get("roles", [])
        if not any(role in user_roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return check_role

def require_role_and_module(*allowed_roles, module: str):
    """Combined dependency that checks both role AND module status"""
    async def check_role_and_module(current_user = Depends(get_current_user)):
        user_roles = current_user.get("roles", [])
        
        # Check role first
        if not any(role in user_roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(allowed_roles)}"
            )
        
        # SuperAdmin bypasses module checks
        if "SuperAdmin" in user_roles:
            return current_user
        
        # Check module status
        condo_id = current_user.get("condominium_id")
        if not condo_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario no asignado a un condominio"
            )
        
        condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "modules": 1})
        if not condo:
            raise HTTPException(status_code=404, detail="Condominio no encontrado")
        
        modules = condo.get("modules", {})
        module_config = modules.get(module)
        
        # Handle both boolean and dict formats
        is_enabled = False
        if isinstance(module_config, bool):
            is_enabled = module_config
        elif isinstance(module_config, dict):
            is_enabled = module_config.get("enabled", False)
        elif module_config is None:
            # Module not configured - default to enabled for backwards compatibility
            is_enabled = True
        
        if not is_enabled:
            logger.warning(f"[module-check] Access DENIED to module '{module}' for user {current_user.get('email')}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Módulo '{module}' no está habilitado para este condominio"
            )
        
        return current_user
    return check_role_and_module

def require_module(module_name: str):
    """Dependency that checks if a module is enabled for the user's condominium"""
    async def check_module(current_user = Depends(get_current_user)):
        # SuperAdmin bypasses module checks
        if "SuperAdmin" in current_user.get("roles", []):
            logger.info(f"[module-check] SuperAdmin bypasses {module_name} check")
            return current_user
        
        condo_id = current_user.get("condominium_id")
        if not condo_id:
            # Users without condominium can't access module-protected endpoints
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario no asignado a un condominio"
            )
        
        condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "modules": 1})
        if not condo:
            raise HTTPException(status_code=404, detail="Condominio no encontrado")
        
        modules = condo.get("modules", {})
        module_config = modules.get(module_name)
        
        logger.info(f"[module-check] Module '{module_name}' config: {module_config}")
        
        # Handle both boolean and dict formats
        is_enabled = False
        if isinstance(module_config, bool):
            is_enabled = module_config
        elif isinstance(module_config, dict):
            is_enabled = module_config.get("enabled", False)
        elif module_config is None:
            # Module not configured - default to enabled for backwards compatibility
            is_enabled = True
        
        logger.info(f"[module-check] Module '{module_name}' is_enabled: {is_enabled}")
        
        if not is_enabled:
            logger.warning(f"[module-check] Access DENIED to module '{module_name}' for user {current_user.get('email')}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Módulo '{module_name}' no está habilitado para este condominio"
            )
        
        return current_user
    return check_module

# ==================== MULTI-TENANT ENFORCEMENT SYSTEM ====================

# -------------------- PHASE 1: Centralized Validation --------------------
async def validate_tenant_resource(resource: dict, current_user: dict) -> None:
    """
    Validate that the current user has access to the resource's tenant.
    
    Rules:
    - SuperAdmin → always allowed
    - resource.condominium_id must match current_user.condominium_id
    - Missing condominium_id on either side → 403
    
    Args:
        resource: The resource document from database
        current_user: The authenticated user from get_current_user()
    
    Raises:
        HTTPException 403: If tenant validation fails
    """
    # SuperAdmin bypasses all tenant checks
    user_roles = current_user.get("roles", [])
    if "SuperAdmin" in user_roles:
        return
    
    user_condo_id = current_user.get("condominium_id")
    resource_condo_id = resource.get("condominium_id") if resource else None
    
    # Validate both have condominium_id
    if not user_condo_id:
        logger.warning(
            f"[TENANT-BLOCK] User {current_user.get('id')} has no condominium_id"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: user not assigned to a condominium"
        )
    
    if not resource_condo_id:
        logger.warning(
            f"[TENANT-BLOCK] Resource has no condominium_id. "
            f"User: {current_user.get('id')}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: resource has no tenant association"
        )
    
    # Validate match
    if user_condo_id != resource_condo_id:
        logger.warning(
            f"[TENANT-BLOCK] Cross-tenant access attempt: "
            f"user={current_user.get('id')} (condo={user_condo_id}) "
            f"tried to access resource in condo={resource_condo_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: cross-tenant access blocked"
        )

# -------------------- PHASE 2: Resource Getter with Validation --------------------
async def get_tenant_resource(
    collection, 
    resource_id: str, 
    current_user: dict,
    id_field: str = "id"
) -> dict:
    """
    Fetch a resource by ID and validate tenant access.
    
    Args:
        collection: MongoDB collection to query
        resource_id: The ID of the resource to fetch
        current_user: The authenticated user from get_current_user()
        id_field: The field name for ID (default: "id")
    
    Returns:
        The resource document if found and authorized
    
    Raises:
        HTTPException 404: If resource not found
        HTTPException 403: If tenant validation fails
    """
    resource = await collection.find_one({id_field: resource_id}, {"_id": 0})
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )
    
    await validate_tenant_resource(resource, current_user)
    
    return resource

# -------------------- PHASE 3: Automatic Tenant Filter --------------------
def tenant_filter(current_user: dict, extra_filter: dict = None) -> dict:
    """
    Generate a MongoDB filter that enforces tenant isolation.
    
    Args:
        current_user: The authenticated user from get_current_user()
        extra_filter: Additional filter conditions to merge
    
    Returns:
        MongoDB filter dict with condominium_id constraint (unless SuperAdmin)
    
    Usage:
        # In list endpoints:
        results = await db.reservations.find(
            tenant_filter(current_user, {"status": "active"})
        ).to_list(100)
    """
    user_roles = current_user.get("roles", [])
    
    # SuperAdmin sees all data
    if "SuperAdmin" in user_roles:
        return extra_filter or {}
    
    # Regular users see only their condominium's data
    user_condo_id = current_user.get("condominium_id")
    
    if not user_condo_id:
        logger.warning(
            f"[TENANT-FILTER] User {current_user.get('id')} has no condominium_id, "
            f"returning empty filter (will match nothing)"
        )
        # Return impossible filter to prevent data leakage
        return {"condominium_id": "__INVALID_NO_CONDO__"}
    
    base_filter = {"condominium_id": user_condo_id}
    
    if extra_filter:
        return {**base_filter, **extra_filter}
    
    return base_filter

# -------------------- LEGACY HELPER (kept for compatibility) --------------------
def enforce_same_condominium(resource_condo_id: str, current_user: dict) -> None:
    """
    LEGACY: Use validate_tenant_resource() or get_tenant_resource() instead.
    
    Validate that the current user belongs to the same condominium as the resource.
    Prevents cross-tenant data access.
    """
    # SuperAdmin bypasses tenant check
    user_roles = current_user.get("roles", [])
    if "SuperAdmin" in user_roles:
        return
    
    user_condo_id = current_user.get("condominium_id")
    
    # Block access if condominiums don't match
    if user_condo_id != resource_condo_id:
        logger.warning(
            f"[TENANT-BLOCK] Cross-tenant access attempt: "
            f"user={current_user.get('id')} (condo={user_condo_id}) "
            f"tried to access resource in condo={resource_condo_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: cross-tenant access blocked"
        )

async def log_audit_event(
    event_type: AuditEventType,
    user_id: Optional[str],
    module: str,
    details: dict,
    ip_address: str = "unknown",
    user_agent: str = "unknown",
    condominium_id: Optional[str] = None,
    user_email: Optional[str] = None
):
    """
    Log an audit event with multi-tenant support.
    CRITICAL: Always pass condominium_id for tenant isolation.
    """
    audit_log = {
        "id": str(uuid.uuid4()),
        "event_type": event_type.value,
        "user_id": user_id,
        "user_email": user_email,
        "condominium_id": condominium_id,
        "module": module,
        "details": details,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.audit_logs.insert_one(audit_log)
    print(f"[FLOW] audit_event_logged | event={event_type.value} module={module} condo={condominium_id[:8] if condominium_id else 'N/A'}")

# ==================== PUSH NOTIFICATION HELPERS ====================
async def send_push_notification(subscription_info: dict, payload: dict) -> bool:
    """
    Send a push notification to a single subscriber.
    
    SECURITY: This is a low-level function. Caller MUST validate:
    - User is authenticated
    - Condominium exists
    - Role is valid
    
    ERROR HANDLING (CONSERVATIVE - only delete on definitive errors):
    - 404/410 Gone: Auto-delete stale subscription from DB
    - 401/403/429/500/502/503: Log but keep subscription (temporary errors)
    - Timeout/Network: Log but keep subscription (temporary errors)
    - Other errors: Log and keep subscription
    
    IMPORTANT: Only delete subscriptions when we are CERTAIN they are permanently invalid.
    """
    endpoint = subscription_info.get("endpoint", "")
    endpoint_short = endpoint[:50] if endpoint else "NO_ENDPOINT"
    
    if not VAPID_PUBLIC_KEY or not VAPID_PRIVATE_KEY:
        logger.warning("[PUSH-SEND-FAILED] VAPID keys not configured")
        return False
    
    if not endpoint:
        logger.warning("[PUSH-SEND-FAILED] Subscription missing endpoint")
        return False
    
    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{VAPID_CLAIMS_EMAIL}"}
        )
        logger.info(f"[PUSH-SEND-SUCCESS] Notification sent to: {endpoint_short}...")
        return True
        
    except WebPushException as e:
        status_code = e.response.status_code if e.response else None
        error_body = ""
        try:
            if e.response:
                error_body = e.response.text[:100] if e.response.text else ""
        except Exception as parse_err:
            logger.debug(f"[PUSH] Could not parse error response: {parse_err}")
        
        # ONLY delete on 404 (Not Found) or 410 (Gone) - subscription is permanently invalid
        if status_code in [404, 410]:
            delete_result = await db.push_subscriptions.delete_one({"endpoint": endpoint})
            if delete_result.deleted_count > 0:
                logger.warning(f"[PUSH-SUB-DELETED] Removed invalid subscription (HTTP {status_code}): {endpoint_short}...")
            else:
                logger.warning(f"[PUSH-SEND-FAILED] HTTP {status_code} but subscription not found in DB: {endpoint_short}...")
            return False
        
        # 401/403 - Auth errors, likely temporary (VAPID token refresh, etc.)
        if status_code in [401, 403]:
            logger.warning(f"[PUSH-SEND-FAILED] Auth error HTTP {status_code} (keeping subscription): {endpoint_short}... | {error_body}")
            return False
        
        # 429 - Rate limited, definitely keep subscription
        if status_code == 429:
            logger.warning(f"[PUSH-SEND-FAILED] Rate limited HTTP 429 (keeping subscription): {endpoint_short}...")
            return False
        
        # 500/502/503/504 - Server errors, temporary
        if status_code in [500, 502, 503, 504]:
            logger.warning(f"[PUSH-SEND-FAILED] Server error HTTP {status_code} (keeping subscription): {endpoint_short}...")
            return False
        
        # Any other WebPush error - log but keep subscription (be conservative)
        logger.error(f"[PUSH-SEND-FAILED] WebPush error HTTP {status_code} (keeping subscription): {endpoint_short}... | {error_body}")
        return False
        
    except TimeoutError:
        logger.warning(f"[PUSH-SEND-FAILED] Timeout (keeping subscription): {endpoint_short}...")
        return False
        
    except ConnectionError as e:
        logger.warning(f"[PUSH-SEND-FAILED] Connection error (keeping subscription): {endpoint_short}... | {str(e)[:50]}")
        return False
        
    except Exception as e:
        # Unknown error - be conservative, keep subscription
        logger.error(f"[PUSH-SEND-FAILED] Unexpected error (keeping subscription): {endpoint_short}... | {type(e).__name__}: {str(e)[:100]}")
        return False

async def send_push_notification_with_cleanup(subscription_info: dict, payload: dict, user_id: str = None) -> dict:
    """
    Send a push notification and return detailed result for parallel processing.
    Returns: {"success": bool, "deleted": bool, "endpoint": str, "error": str|None}
    
    ERROR HANDLING (CONSERVATIVE):
    - Only delete subscription on HTTP 404 or 410 (subscription permanently invalid)
    - Keep subscription for all other errors (401, 403, 429, 500, timeout, network, etc.)
    
    v2.0: Added user_id parameter for better logging
    """
    endpoint = subscription_info.get("endpoint", "")
    endpoint_short = endpoint[:50] if endpoint else "NO_ENDPOINT"
    result = {"success": False, "deleted": False, "endpoint": endpoint, "error": None, "user_id": user_id}
    
    if not VAPID_PUBLIC_KEY or not VAPID_PRIVATE_KEY:
        result["error"] = "VAPID not configured"
        return result
    
    if not endpoint:
        result["error"] = "Missing endpoint"
        return result
    
    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{VAPID_CLAIMS_EMAIL}"}
        )
        result["success"] = True
        logger.info(f"[PUSH-SEND-SUCCESS] Notification sent to user={user_id}: {endpoint_short}...")
        return result
        
    except WebPushException as e:
        status_code = e.response.status_code if e.response else None
        result["error"] = f"HTTP {status_code}"
        
        # ONLY delete on 404 (Not Found) or 410 (Gone) - subscription is permanently invalid
        if status_code in [404, 410]:
            delete_result = await db.push_subscriptions.delete_one({"endpoint": endpoint})
            if delete_result.deleted_count > 0:
                result["deleted"] = True
                # STRUCTURED LOG for cleanup tracking
                logger.warning(f"[PUSH-CLEANUP] Invalid subscription removed: user_id={user_id}, endpoint={endpoint_short}..., reason=HTTP_{status_code}")
            else:
                logger.warning(f"[PUSH-SEND-FAILED] HTTP {status_code} but subscription not in DB: user={user_id}, {endpoint_short}...")
        else:
            # All other errors: keep the subscription
            logger.warning(f"[PUSH-SEND-FAILED] HTTP {status_code} (keeping subscription): user={user_id}, {endpoint_short}...")
        
        return result
        
    except TimeoutError:
        result["error"] = "Timeout"
        logger.warning(f"[PUSH-SEND-FAILED] Timeout (keeping subscription): user={user_id}, {endpoint_short}...")
        return result
        
    except ConnectionError as e:
        result["error"] = f"Connection: {str(e)[:30]}"
        logger.warning(f"[PUSH-SEND-FAILED] Connection error (keeping subscription): user={user_id}, {endpoint_short}...")
        return result
        
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)[:50]}"
        logger.error(f"[PUSH-SEND-FAILED] Unexpected error (keeping subscription): user={user_id}, {endpoint_short}... | {result['error']}")
        return result
        return result

async def notify_guards_of_panic(condominium_id: str, panic_data: dict, sender_id: str = None):
    """
    Send push notifications to guards about a panic alert.
    
    SECURITY RULES (Backend is the ONLY authority):
    ✅ SEND TO:
       - Guards (role='Guarda') in the SAME condominium
       - Only ACTIVE guards (status='active')
       - Only users with valid push subscriptions
    
    ❌ DO NOT SEND TO:
       - The sender (user who triggered the alert)
       - Residents
       - Administrators
       - SuperAdmins
       - Supervisors
       - HR
       - Guards from OTHER condominiums
       - Inactive/blocked users
    
    Args:
        condominium_id: Target condominium (REQUIRED)
        panic_data: Alert information
        sender_id: User ID of panic trigger (to exclude from notifications)
    
    Returns:
        dict with sent, failed, total, excluded counts
    """
    result = {"sent": 0, "failed": 0, "total": 0, "excluded": 0, "reason": None}
    
    # ==================== AUDIT LOG START ====================
    logger.info(f"[PANIC-PUSH-AUDIT] ======= NOTIFY GUARDS START =======")
    logger.info(f"[PANIC-PUSH-AUDIT] Input | condo_id={condominium_id} | sender_id={sender_id}")
    logger.info(f"[PANIC-PUSH-AUDIT] Panic data | type={panic_data.get('panic_type')} | resident={panic_data.get('resident_name')} | apt={panic_data.get('apartment')}")
    # ==========================================================
    
    # VALIDATION 1: Condominium is required
    if not condominium_id:
        result["reason"] = "No condominium_id provided"
        logger.warning("[PANIC-PUSH-AUDIT] FAILED: missing condominium_id")
        return result
    
    # VALIDATION 2: Verify condominium exists
    condo = await db.condominiums.find_one({"id": condominium_id}, {"_id": 0, "id": 1, "is_active": 1, "name": 1})
    if not condo:
        result["reason"] = "Condominium not found"
        logger.warning(f"[PANIC-PUSH-AUDIT] FAILED: Condominium {condominium_id} not found in database")
        return result
    
    logger.info(f"[PANIC-PUSH-AUDIT] Condominium found | name={condo.get('name')} | is_active={condo.get('is_active', True)}")
    
    if not condo.get("is_active", True):
        result["reason"] = "Condominium is inactive"
        logger.warning(f"[PANIC-PUSH-AUDIT] FAILED: Condominium {condo.get('name')} is inactive")
        return result
    
    # STEP 1: Get ACTIVE guard user IDs for this condominium ONLY
    guard_query = {
        "condominium_id": condominium_id,
        "roles": {"$in": ["Guarda"]},  # ONLY Guarda role
        "is_active": True,
        "status": {"$in": ["active", None]}  # Active or no status field (legacy)
    }
    
    # Exclude sender if provided
    if sender_id:
        guard_query["id"] = {"$ne": sender_id}
    
    guards = await db.users.find(guard_query, {"_id": 0, "id": 1, "full_name": 1, "email": 1}).to_list(None)
    guard_ids = [g["id"] for g in guards]
    
    # ==================== AUDIT LOG: GUARDS FOUND ====================
    logger.info(f"[PANIC-PUSH-AUDIT] Guards query | condominium_id={condominium_id} | roles='Guarda' | is_active=True")
    logger.info(f"[PANIC-PUSH-AUDIT] Guards found | count={len(guard_ids)}")
    for g in guards[:5]:  # Log first 5 guards
        logger.info(f"[PANIC-PUSH-AUDIT]   - Guard: {g.get('email')} | id={g.get('id')[:12]}...")
    if len(guards) > 5:
        logger.info(f"[PANIC-PUSH-AUDIT]   ... and {len(guards) - 5} more guards")
    # =================================================================
    
    if not guard_ids:
        result["reason"] = "No active guards found in this condominium"
        logger.warning(f"[PANIC-PUSH-AUDIT] FAILED: No active guards in condo {condo.get('name')}")
        return result
    
    # STEP 2: Get push subscriptions for these guards ONLY
    # Filter by user_id AND condominium_id for extra security
    subscriptions = await db.push_subscriptions.find({
        "user_id": {"$in": guard_ids},
        "condominium_id": condominium_id,
        "is_active": True
    }).to_list(None)
    
    # ==================== AUDIT LOG: SUBSCRIPTIONS ====================
    logger.info(f"[PANIC-PUSH-AUDIT] Subscriptions query | user_ids={len(guard_ids)} guards | condo={condominium_id[:12]}... | is_active=True")
    logger.info(f"[PANIC-PUSH-AUDIT] Subscriptions found | count={len(subscriptions)}")
    
    # Log subscription details per guard
    subs_by_guard = {}
    for sub in subscriptions:
        uid = sub.get("user_id")
        if uid not in subs_by_guard:
            subs_by_guard[uid] = 0
        subs_by_guard[uid] += 1
    
    for gid, count in subs_by_guard.items():
        guard = next((g for g in guards if g["id"] == gid), None)
        guard_email = guard.get("email", "unknown") if guard else "unknown"
        logger.info(f"[PANIC-PUSH-AUDIT]   - Guard {guard_email}: {count} active subscription(s)")
    
    # Log guards WITHOUT subscriptions
    guards_without_subs = [g for g in guards if g["id"] not in subs_by_guard]
    if guards_without_subs:
        logger.warning(f"[PANIC-PUSH-AUDIT] Guards WITHOUT subscriptions: {len(guards_without_subs)}")
        for g in guards_without_subs[:3]:
            logger.warning(f"[PANIC-PUSH-AUDIT]   - {g.get('email')} has NO push subscription!")
    # =================================================================
    
    result["total"] = len(subscriptions)
    
    if not subscriptions:
        result["reason"] = "No push subscriptions for guards"
        logger.warning(f"[PANIC-PUSH-AUDIT] FAILED: No push subscriptions found for {len(guard_ids)} guards")
        return result
    
    # STEP 3: Build notification payload
    panic_type_display = {
        "medical": "🚑 Emergencia Médica",
        "suspicious": "👁️ Actividad Sospechosa", 
        "general": "🚨 Alerta General"
    }.get(panic_data.get("panic_type", "general"), "🚨 Alerta")
    
    payload = {
        "title": f"¡ALERTA DE PÁNICO! - {panic_type_display}",
        "body": f"{panic_data.get('resident_name', 'Residente')} - {panic_data.get('apartment', 'N/A')}",
        "icon": "/logo192.png",
        "badge": "/logo192.png",
        "tag": f"panic-{panic_data.get('event_id', 'unknown')}",
        "requireInteraction": True,
        "urgency": "high",
        "data": {
            "type": "panic_alert",
            "event_id": panic_data.get("event_id"),
            "panic_type": panic_data.get("panic_type"),
            "resident_name": panic_data.get("resident_name"),
            "apartment": panic_data.get("apartment"),
            "timestamp": panic_data.get("timestamp"),
            "url": f"/guard?alert={panic_data.get('event_id')}"
        }
    }
    
    # ==================== PHASE 3: PARALLEL PUSH DELIVERY ====================
    # Build push tasks, filtering invalid entries
    push_tasks = []
    for sub in subscriptions:
        # Extra validation: ensure subscription belongs to a guard in this condo
        sub_user_id = sub.get("user_id")
        if sub_user_id not in guard_ids:
            result["excluded"] += 1
            continue
        
        endpoint = sub.get("endpoint")
        if not endpoint:
            result["excluded"] += 1
            continue
        
        subscription_info = {
            "endpoint": endpoint,
            "keys": {
                "p256dh": sub.get("p256dh"),
                "auth": sub.get("auth")
            }
        }
        # Pass user_id for better logging
        push_tasks.append(send_push_notification_with_cleanup(subscription_info, payload, user_id=sub_user_id))
    
    # Execute all push notifications in parallel
    deleted_count = 0
    if push_tasks:
        push_results = await asyncio.gather(*push_tasks, return_exceptions=True)
        
        # Process results
        for res in push_results:
            if isinstance(res, Exception):
                result["failed"] += 1
            elif isinstance(res, dict):
                if res.get("success"):
                    result["sent"] += 1
                else:
                    result["failed"] += 1
                if res.get("deleted"):
                    deleted_count += 1
    # ======================================================================
    
    # ==================== PHASE 4: STRUCTURED LOGGING ====================
    logger.info(f"[PANIC-PUSH-AUDIT] ======= DELIVERY COMPLETE =======")
    logger.info(
        f"[PANIC-PUSH-AUDIT] Result | "
        f"condo={condo.get('name', condominium_id[:8])} | "
        f"guards_found={len(guard_ids)} | "
        f"total_subs={result['total']} | "
        f"sent={result['sent']} | "
        f"failed={result['failed']} | "
        f"excluded={result['excluded']} | "
        f"deleted_invalid={deleted_count}"
    )
    logger.info(f"[PANIC-PUSH-AUDIT] ======= NOTIFY GUARDS END =======")
    # ===================================================================
    
    return result

# ==================== CONTEXTUAL PUSH NOTIFICATION HELPERS ====================

async def send_push_to_user(user_id: str, payload: dict) -> dict:
    """
    Send push notification to a specific user (all their active subscriptions).
    
    Returns detailed result including success/failure counts.
    Does NOT delete subscriptions on temporary errors - only on 404/410.
    """
    result = {"sent": 0, "failed": 0, "total": 0, "deleted": 0}
    
    if not VAPID_PUBLIC_KEY or not VAPID_PRIVATE_KEY:
        logger.warning("[PUSH-SEND-FAILED] VAPID keys not configured")
        return result
    
    subscriptions = await db.push_subscriptions.find({
        "user_id": user_id,
        "is_active": True
    }).to_list(None)
    
    result["total"] = len(subscriptions)
    
    if not subscriptions:
        logger.debug(f"[PUSH-SEND-FAILED] No active subscriptions for user {user_id[:8]}...")
        return result
    
    logger.info(f"[PUSH-SEND-START] Sending to user {user_id[:8]}... ({len(subscriptions)} subscriptions)")
    
    for sub in subscriptions:
        sub_user_id = sub.get("user_id")
        subscription_info = {
            "endpoint": sub.get("endpoint"),
            "keys": {
                "p256dh": sub.get("p256dh"),
                "auth": sub.get("auth")
            }
        }
        # Use the function that returns detailed results (with user_id for logging)
        send_result = await send_push_notification_with_cleanup(subscription_info, payload, user_id=sub_user_id)
        
        if send_result["success"]:
            result["sent"] += 1
        else:
            result["failed"] += 1
            if send_result.get("deleted"):
                result["deleted"] += 1
    
    logger.info(f"[PUSH-SEND-COMPLETE] User {user_id[:8]}...: sent={result['sent']}, failed={result['failed']}, deleted={result['deleted']}")
    
    return result

async def send_push_to_guards(condominium_id: str, payload: dict, exclude_user_id: str = None) -> dict:
    """
    Send push notification to all guards in a condominium.
    
    SECURITY: Only sends to users with role 'Guarda' in the specified condominium.
    Uses push_subscriptions filtered by user_id AND condominium_id.
    
    Args:
        condominium_id: Target condominium (REQUIRED)
        payload: Notification payload
        exclude_user_id: Optional user ID to exclude from notifications
    """
    result = {"sent": 0, "failed": 0, "total": 0}
    
    if not condominium_id:
        return result
    
    # Get ACTIVE guard user IDs for this condominium
    guard_query = {
        "condominium_id": condominium_id,
        "roles": {"$in": ["Guarda"]},
        "is_active": True
    }
    
    if exclude_user_id:
        guard_query["id"] = {"$ne": exclude_user_id}
    
    guards = await db.users.find(guard_query, {"_id": 0, "id": 1}).to_list(None)
    guard_ids = [g["id"] for g in guards]
    
    if not guard_ids:
        return result
    
    # Get subscriptions for these guards only, filtered by condo
    subscriptions = await db.push_subscriptions.find({
        "user_id": {"$in": guard_ids},
        "condominium_id": condominium_id,
        "is_active": True
    }).to_list(None)
    
    result["total"] = len(subscriptions)
    
    if not subscriptions:
        return result
    
    for sub in subscriptions:
        subscription_info = {
            "endpoint": sub.get("endpoint"),
            "keys": {
                "p256dh": sub.get("p256dh"),
                "auth": sub.get("auth")
            }
        }
        success = await send_push_notification(subscription_info, payload)
        if success:
            result["sent"] += 1
        else:
            result["failed"] += 1
    
    logger.info(f"[PUSH-GUARDS] Sent: {result['sent']}, Failed: {result['failed']}")
    return result

async def send_push_to_admins(condominium_id: str, payload: dict) -> dict:
    """
    Send push notification to admins in a condominium.
    
    SECURITY: Only sends to users with role 'Administrador' or 'Supervisor'
    in the specified condominium.
    """
    result = {"sent": 0, "failed": 0, "total": 0}
    
    if not condominium_id:
        return result
    
    # Get admin user IDs for this condominium
    admins = await db.users.find({
        "condominium_id": condominium_id,
        "roles": {"$in": ["Administrador", "Supervisor"]},
        "is_active": True,
        "status": {"$in": ["active", None]}
    }, {"_id": 0, "id": 1}).to_list(None)
    
    admin_ids = [a["id"] for a in admins]
    
    if not admin_ids:
        return result
    
    # Get subscriptions filtered by user_id AND condominium_id
    subscriptions = await db.push_subscriptions.find({
        "user_id": {"$in": admin_ids},
        "condominium_id": condominium_id,
        "is_active": True
    }).to_list(None)
    
    result["total"] = len(subscriptions)
    
    if not subscriptions:
        return result
    
    for sub in subscriptions:
        subscription_info = {
            "endpoint": sub.get("endpoint"),
            "keys": {
                "p256dh": sub.get("p256dh"),
                "auth": sub.get("auth")
            }
        }
        success = await send_push_notification(subscription_info, payload)
        if success:
            result["sent"] += 1
        else:
            result["failed"] += 1
    
    logger.info(f"[PUSH-ADMINS] Sent: {result['sent']}, Failed: {result['failed']}")
    return result

# ==================== DYNAMIC PUSH TARGETING SYSTEM ====================

async def send_targeted_push_notification(
    condominium_id: str,
    title: str,
    body: str,
    target_roles: List[str] = None,
    target_user_ids: List[str] = None,
    exclude_user_ids: List[str] = None,
    data: dict = None,
    tag: str = None,
    require_interaction: bool = False
) -> dict:
    """
    Send push notifications with dynamic targeting.
    
    This is a unified function that supports multiple targeting strategies:
    - By specific user IDs (e.g., notify reservation owner)
    - By roles (e.g., notify all guards, all admins)
    - Combined exclusions (e.g., all guards except sender)
    
    TARGETING RULES:
    - If target_user_ids is provided: Send to those specific users only
    - If target_roles is provided: Send to users with those roles in the condo
    - If NEITHER is provided: Return without sending (fail-safe)
    
    SECURITY:
    - All queries are scoped to condominium_id
    - Only sends to is_active=True subscriptions
    - Validates condominium exists before sending
    
    Args:
        condominium_id: Target condominium (REQUIRED)
        title: Notification title
        body: Notification body text
        target_roles: List of roles to target (e.g., ["Guarda", "Administrador"])
        target_user_ids: List of specific user IDs to target
        exclude_user_ids: List of user IDs to exclude from notifications
        data: Additional data payload for the notification
        tag: Notification tag for grouping/deduplication
        require_interaction: Whether notification requires user action
    
    Returns:
        dict with sent, failed, total, skipped counts and targeting info
    """
    result = {
        "sent": 0,
        "failed": 0,
        "total": 0,
        "skipped": 0,
        "target_type": None,
        "reason": None
    }
    
    # VALIDATION 1: VAPID keys required
    if not VAPID_PUBLIC_KEY or not VAPID_PRIVATE_KEY:
        result["reason"] = "VAPID keys not configured"
        logger.warning("[PUSH-TARGETED] VAPID keys not configured, skipping")
        return result
    
    # VALIDATION 2: Condominium is required
    if not condominium_id:
        result["reason"] = "No condominium_id provided"
        logger.warning("[PUSH-TARGETED] Missing condominium_id")
        return result
    
    # VALIDATION 3: At least one targeting method must be provided
    if not target_user_ids and not target_roles:
        result["reason"] = "No targeting specified (target_roles or target_user_ids required)"
        logger.warning("[PUSH-TARGETED] No targeting specified, aborting")
        return result
    
    # VALIDATION 4: Verify condominium exists and is active
    condo = await db.condominiums.find_one(
        {"id": condominium_id}, 
        {"_id": 0, "id": 1, "is_active": 1, "name": 1}
    )
    if not condo:
        result["reason"] = "Condominium not found"
        logger.warning(f"[PUSH-TARGETED] Condominium {condominium_id} not found")
        return result
    
    if not condo.get("is_active", True):
        result["reason"] = "Condominium is inactive"
        logger.warning(f"[PUSH-TARGETED] Condominium {condominium_id} is inactive")
        return result
    
    # BUILD SUBSCRIPTION QUERY
    subscription_query = {
        "condominium_id": condominium_id,
        "is_active": True
    }
    
    # TARGETING STRATEGY 1: Specific user IDs
    if target_user_ids:
        result["target_type"] = "user_ids"
        
        # Filter out excluded users if any
        effective_user_ids = [uid for uid in target_user_ids if uid not in (exclude_user_ids or [])]
        
        if not effective_user_ids:
            result["reason"] = "All target users were excluded"
            return result
        
        subscription_query["user_id"] = {"$in": effective_user_ids}
        
        logger.info(
            f"[PUSH-TARGETED] Targeting {len(effective_user_ids)} specific users "
            f"in condo {condominium_id[:8]}..."
        )
    
    # TARGETING STRATEGY 2: By roles
    elif target_roles:
        result["target_type"] = "roles"
        
        # First, get user IDs that match the role criteria
        user_query = {
            "condominium_id": condominium_id,
            "roles": {"$in": target_roles},
            "is_active": True,
            "status": {"$in": ["active", None]}
        }
        
        # Apply exclusions at user level
        if exclude_user_ids:
            user_query["id"] = {"$nin": exclude_user_ids}
        
        matching_users = await db.users.find(user_query, {"_id": 0, "id": 1}).to_list(None)
        matching_user_ids = [u["id"] for u in matching_users]
        
        if not matching_user_ids:
            result["reason"] = f"No active users with roles {target_roles} in this condominium"
            logger.info(
                f"[PUSH-TARGETED] No users found with roles {target_roles} "
                f"in condo {condominium_id[:8]}..."
            )
            return result
        
        subscription_query["user_id"] = {"$in": matching_user_ids}
        
        logger.info(
            f"[PUSH-TARGETED] Targeting roles {target_roles}: "
            f"found {len(matching_user_ids)} users in condo {condominium_id[:8]}..."
        )
    
    # FETCH SUBSCRIPTIONS
    subscriptions = await db.push_subscriptions.find(subscription_query).to_list(None)
    result["total"] = len(subscriptions)
    
    if not subscriptions:
        result["reason"] = "No push subscriptions found for target"
        logger.info(f"[PUSH-TARGETED] No subscriptions found for query")
        return result
    
    # BUILD NOTIFICATION PAYLOAD
    payload = {
        "title": title,
        "body": body,
        "icon": "/logo192.png",
        "badge": "/logo192.png",
        "requireInteraction": require_interaction,
        "data": data or {}
    }
    
    if tag:
        payload["tag"] = tag
    
    # ==================== PHASE 3: PARALLEL PUSH DELIVERY ====================
    # Build subscription info list, filtering invalid entries
    push_tasks = []
    for sub in subscriptions:
        sub_user_id = sub.get("user_id")
        endpoint = sub.get("endpoint")
        if not endpoint:
            result["skipped"] += 1
            continue
        
        subscription_info = {
            "endpoint": endpoint,
            "keys": {
                "p256dh": sub.get("p256dh"),
                "auth": sub.get("auth")
            }
        }
        # Pass user_id for better logging
        push_tasks.append(send_push_notification_with_cleanup(subscription_info, payload, user_id=sub_user_id))
    
    # Execute all push notifications in parallel
    if push_tasks:
        push_results = await asyncio.gather(*push_tasks, return_exceptions=True)
        
        # Process results
        deleted_count = 0
        for res in push_results:
            if isinstance(res, Exception):
                result["failed"] += 1
            elif isinstance(res, dict):
                if res.get("success"):
                    result["sent"] += 1
                else:
                    result["failed"] += 1
                if res.get("deleted"):
                    deleted_count += 1
        
        result["deleted_invalid"] = deleted_count
    # ======================================================================
    
    # PHASE 4: STRUCTURED LOGGING
    logger.info(
        f"[PUSH-TARGETED] Complete | "
        f"condo={condominium_id[:8]}... | "
        f"target_type={result['target_type']} | "
        f"target_roles={target_roles} | "
        f"target_users={len(target_user_ids) if target_user_ids else 0} | "
        f"total_found={result['total']} | "
        f"sent={result['sent']} | "
        f"failed={result['failed']} | "
        f"deleted_invalid={result.get('deleted_invalid', 0)}"
    )
    
    return result

# ==================== END DYNAMIC PUSH TARGETING ====================

async def create_and_send_notification(
    user_id: str,
    condominium_id: str,
    notification_type: str,
    title: str,
    message: str,
    data: dict = None,
    send_push: bool = True,
    url: str = None
) -> dict:
    """
    Creates a notification in DB and optionally sends push.
    Prevents duplicates by checking existing notifications.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # Check for duplicate (same type, user, and key data within last minute)
    duplicate_check = {
        "type": notification_type,
        "user_id": user_id,
        "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()}
    }
    
    # Add specific data fields to duplicate check based on type
    if data:
        if notification_type == "visitor_arrival" and data.get("entry_id"):
            duplicate_check["data.entry_id"] = data["entry_id"]
        elif notification_type == "visitor_exit" and data.get("entry_id"):
            duplicate_check["data.entry_id"] = data["entry_id"]
        elif notification_type in ["reservation_approved", "reservation_rejected"] and data.get("reservation_id"):
            duplicate_check["data.reservation_id"] = data["reservation_id"]
    
    existing = await db.resident_notifications.find_one(duplicate_check)
    if existing:
        logger.debug(f"Skipping duplicate notification: {notification_type} for user {user_id}")
        return {"created": False, "push_sent": False, "reason": "duplicate"}
    
    # Create notification document
    notification_doc = {
        "id": str(uuid.uuid4()),
        "type": notification_type,
        "user_id": user_id,
        "condominium_id": condominium_id,
        "title": title,
        "message": message,
        "data": data or {},
        "url": url,
        "read": False,
        "created_at": now_iso
    }
    
    await db.resident_notifications.insert_one(notification_doc)
    
    # Send push if enabled
    push_result = {"sent": 0}
    if send_push:
        payload = {
            "title": title,
            "body": message,
            "icon": "/logo192.png",
            "badge": "/logo192.png",
            "tag": f"{notification_type}-{notification_doc['id'][:8]}",
            "data": {
                "type": notification_type,
                "notification_id": notification_doc["id"],
                "url": url or "/resident?tab=history",
                **(data or {})
            }
        }
        push_result = await send_push_to_user(user_id, payload)
    
    return {
        "created": True,
        "notification_id": notification_doc["id"],
        "push_sent": push_result.get("sent", 0) > 0
    }

# ==================== SAAS BILLING HELPERS ====================
# NOTE: Core seat engine functions moved to modules/users/service.py:
# - count_active_users()
# - count_active_residents()
# - update_active_user_count()
# - can_create_user()
# These are now imported at the top of this file.

async def get_billing_info(condominium_id: str) -> dict:
    """Get billing information for a condominium"""
    condo = await db.condominiums.find_one({"id": condominium_id}, {"_id": 0})
    if not condo:
        return None
    
    active_users = await count_active_users(condominium_id)
    paid_seats = condo.get("paid_seats", 10)
    billing_status = condo.get("billing_status", "active")
    
    # Determine environment and billing enabled status
    environment = condo.get("environment", "production")
    is_demo = condo.get("is_demo", False)
    # Demo condos have billing disabled regardless of other settings
    billing_enabled = not (environment == "demo" or is_demo)
    
    # PHASE 4: Use dynamic pricing
    price_per_seat = await get_effective_seat_price(condominium_id)
    
    return {
        "condominium_id": condominium_id,
        "condominium_name": condo.get("name", ""),
        "paid_seats": paid_seats,
        "active_users": active_users,
        "remaining_seats": max(0, paid_seats - active_users),
        "billing_status": billing_status,
        "stripe_customer_id": condo.get("stripe_customer_id"),
        "stripe_subscription_id": condo.get("stripe_subscription_id"),
        "billing_period_end": condo.get("billing_period_end"),
        "price_per_seat": price_per_seat,
        "monthly_cost": round(paid_seats * price_per_seat, 2),
        "can_create_users": active_users < paid_seats and billing_status in ["active", "trialing"],
        # Environment info
        "environment": environment,
        "is_demo": is_demo or environment == "demo",
        "billing_enabled": billing_enabled
    }

async def log_billing_event(
    event_type: str,
    condominium_id: str,
    details: dict,
    user_id: str = None
):
    """
    DEPRECATED: This function writes to billing_logs (legacy).
    Use log_billing_engine_event() instead which writes to billing_events.
    Kept for backward compatibility but marked for removal.
    """
    # Log deprecation warning (once per event type)
    logger.warning(f"[DEPRECATED] log_billing_event called for {event_type} - use log_billing_engine_event instead")
    
    # Still write for backward compatibility, but will be removed in future
    event = {
        "id": str(uuid.uuid4()),
        "event_type": f"billing_{event_type}",
        "condominium_id": condominium_id,
        "user_id": user_id,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "_deprecated": True  # Mark as deprecated data
    }
    await db.billing_logs.insert_one(event)
    logger.info(f"[DEPRECATED] Billing event logged: {event_type} for condo {condominium_id}")

