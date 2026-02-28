# Trigger redeploy - 2026-02-26 MODULAR
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Request, Body, Query
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
    except:
        pass
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
    user_agent: str = "unknown"
):
    audit_log = {
        "id": str(uuid.uuid4()),
        "event_type": event_type.value,
        "user_id": user_id,
        "module": module,
        "details": details,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.audit_logs.insert_one(audit_log)

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
        except:
            pass
        
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
    """Log billing-related events for audit"""
    event = {
        "id": str(uuid.uuid4()),
        "event_type": f"billing_{event_type}",
        "condominium_id": condominium_id,
        "user_id": user_id,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.billing_logs.insert_one(event)
    logger.info(f"Billing event logged: {event_type} for condo {condominium_id}")

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate, request: Request):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    
    # Validate condominium if provided
    if user_data.condominium_id:
        condo = await db.condominiums.find_one({"id": user_data.condominium_id, "is_active": True})
        if not condo:
            raise HTTPException(status_code=400, detail="Invalid or inactive condominium")
        
        # Check user limit
        current_users = await db.users.count_documents({"condominium_id": user_data.condominium_id, "is_active": True})
        if current_users >= condo.get("max_users", 100):
            raise HTTPException(status_code=400, detail="Condominium user limit reached")
    
    user_id = str(uuid.uuid4())
    # SECURITY FIX: Force "Residente" role for all public registrations
    # Prevents privilege escalation via self-assigned roles
    forced_role = ["Residente"]
    
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "hashed_password": hash_password(user_data.password),
        "roles": forced_role,
        "condominium_id": user_data.condominium_id,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    # Update condominium user count
    if user_data.condominium_id:
        await db.condominiums.update_one(
            {"id": user_data.condominium_id},
            {"$inc": {"current_users": 1}}
        )
    
    await log_audit_event(
        AuditEventType.USER_CREATED,
        user_id,
        "auth",
        {"email": user_data.email, "roles": forced_role, "condominium_id": user_data.condominium_id},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return UserResponse(
        id=user_id,
        email=user_data.email,
        full_name=user_data.full_name,
        roles=forced_role,
        is_active=True,
        created_at=user_doc["created_at"],
        condominium_id=user_data.condominium_id
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin, request: Request):
    # ==================== RATE LIMITING CHECK ====================
    client_ip = request.client.host if request.client else "unknown"
    normalized_email = credentials.email.lower().strip()
    rate_limit_identifier = f"{normalized_email}:{client_ip}"
    request_id = getattr(request.state, 'request_id', 'N/A')
    
    print(f"[AUTH EVENT] Login attempt | email={normalized_email} | ip={client_ip} | request_id={request_id}")
    
    check_rate_limit(rate_limit_identifier)
    
    # ==================== AUTHENTICATION ====================
    user = await db.users.find_one({"email": normalized_email})
    
    if not user or not verify_password(credentials.password, user.get("hashed_password", "")):
        print(f"[AUTH EVENT] Login FAILED | email={normalized_email} | ip={client_ip} | reason=invalid_credentials")
        await log_audit_event(
            AuditEventType.LOGIN_FAILURE,
            None,
            "auth",
            {"email": normalized_email, "reason": "invalid_credentials"},
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "unknown")
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.get("is_active"):
        print(f"[AUTH EVENT] Login BLOCKED | email={normalized_email} | reason=account_inactive")
        raise HTTPException(status_code=403, detail="User account is inactive")
    
    # Check if password reset is required
    password_reset_required = user.get("password_reset_required", False)
    
    # Phase 3: Generate refresh_token_id for rotation tracking
    refresh_token_id = str(uuid.uuid4())
    
    # Store refresh_token_id in user document
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"refresh_token_id": refresh_token_id}}
    )
    
    # Include condominium_id in token for tenant-aware requests
    token_data = {
        "sub": user["id"], 
        "email": user["email"], 
        "roles": user["roles"],
        "condominium_id": user.get("condominium_id")
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data, refresh_token_id)
    
    await log_audit_event(
        AuditEventType.LOGIN_SUCCESS,
        user["id"],
        "auth",
        {"email": user["email"], "password_reset_required": password_reset_required},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    # Build response body (without refresh_token in body for security)
    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "roles": user["roles"],
            "is_active": user["is_active"],
            "created_at": user["created_at"],
            "condominium_id": user.get("condominium_id"),
            "password_reset_required": password_reset_required
        },
        "password_reset_required": password_reset_required
    }
    
    # Create response with httpOnly cookie for refresh token
    response = JSONResponse(content=response_data)
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,  # SECURITY: Prevents JavaScript access (XSS protection)
        secure=COOKIE_SECURE,  # SECURITY: Only send over HTTPS in production
        samesite=COOKIE_SAMESITE,  # SECURITY: CSRF protection
        path="/api/auth"  # Restrict cookie to auth endpoints only
    )
    
    print(f"[AUTH EVENT] Login SUCCESS | user_id={user['id']} | email={user['email']} | roles={user['roles']}")
    
    return response

@api_router.post("/auth/refresh")
async def refresh_token_endpoint(request: Request, token_request: RefreshTokenRequest = None):
    """
    Refresh access token with rotation security.
    
    Phase 2: Refresh Token Rotation
    - Validates refresh_token_id (jti) against DB
    - Generates new tokens on each refresh
    - Invalidates previous refresh token automatically
    - Prevents reuse of stolen refresh tokens
    
    SECURITY: Now accepts refresh token from:
    1. httpOnly cookie (preferred, more secure)
    2. Request body (deprecated, for backward compatibility)
    """
    # Try to get refresh token from cookie first (more secure)
    refresh_token_value = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    
    # Fall back to body if no cookie (backward compatibility)
    if not refresh_token_value and token_request and token_request.refresh_token:
        refresh_token_value = token_request.refresh_token
        logger.warning("[SECURITY] Refresh token received in body instead of cookie - consider updating client")
    
    if not refresh_token_value:
        raise HTTPException(status_code=401, detail="No refresh token provided")
    
    payload = verify_refresh_token(refresh_token_value)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    user = await db.users.find_one({"id": payload["sub"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Phase 4: Validate user status - reject blocked/suspended/inactive users
    user_status = user.get("status", "active")
    is_active = user.get("is_active", True)
    
    if not is_active or user_status in ["blocked", "suspended", "inactive"]:
        logger.warning(
            f"[SECURITY] Refresh attempt by inactive/blocked user {user['id']}. "
            f"Status: {user_status}, is_active: {is_active}"
        )
        # Clear refresh token to prevent further attempts
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {"refresh_token_id": None}}
        )
        raise HTTPException(
            status_code=401, 
            detail="Account is not active. Please contact support."
        )
    
    # Phase 2 & 3: Validate refresh_token_id matches what's stored in DB
    token_jti = payload.get("jti")
    stored_jti = user.get("refresh_token_id")
    
    # Phase 4: If stored_jti is None, user has logged out - reject refresh
    if stored_jti is None:
        logger.warning(
            f"[SECURITY] Refresh attempt after logout for user {user['id']}. "
            f"Token JTI: {token_jti}"
        )
        raise HTTPException(
            status_code=401, 
            detail="Session expired. Please login again."
        )
    
    # If token has jti, it must match stored jti
    if token_jti and token_jti != stored_jti:
        # Possible token reuse attack - log and reject
        logger.warning(
            f"[SECURITY] Refresh token reuse detected for user {user['id']}. "
            f"Token JTI: {token_jti}, Stored JTI: {stored_jti}"
        )
        # Invalidate all sessions for this user (security measure)
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {"refresh_token_id": None}}
        )
        await log_audit_event(
            AuditEventType.SECURITY_ALERT,
            user["id"],
            "auth",
            {"reason": "refresh_token_reuse_detected", "token_jti": token_jti},
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "unknown")
        )
        raise HTTPException(
            status_code=401, 
            detail="Session invalidated. Please login again."
        )
    
    # Generate new refresh_token_id for rotation
    new_refresh_token_id = str(uuid.uuid4())
    
    # Update stored refresh_token_id (invalidates previous token)
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"refresh_token_id": new_refresh_token_id}}
    )
    
    token_data = {
        "sub": user["id"], 
        "email": user["email"], 
        "roles": user["roles"],
        "condominium_id": user.get("condominium_id")
    }
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data, new_refresh_token_id)
    
    await log_audit_event(
        AuditEventType.TOKEN_REFRESH,
        user["id"],
        "auth",
        {"rotated": True},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    # Return new access token and set new refresh token in cookie
    response = JSONResponse(content={
        "access_token": new_access_token, 
        "token_type": "bearer"
    })
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=new_refresh_token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/api/auth"
    )
    
    return response

@api_router.post("/auth/logout")
async def logout(request: Request, current_user = Depends(get_current_user)):
    """
    Logout and invalidate refresh tokens.
    
    Phase 4: Logout Hardening
    - Sets refresh_token_id to None
    - Invalidates any future refresh attempts with old tokens
    """
    # Invalidate refresh token by clearing refresh_token_id
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {"refresh_token_id": None}}
    )
    
    await log_audit_event(
        AuditEventType.LOGOUT,
        current_user["id"],
        "auth",
        {"refresh_token_invalidated": True},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    # Create response and clear the refresh token cookie
    response = JSONResponse(content={"message": "Successfully logged out"})
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        path="/api/auth",
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE
    )
    
    return response

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        roles=current_user["roles"],
        is_active=current_user["is_active"],
        created_at=current_user["created_at"],
        condominium_id=current_user.get("condominium_id")
    )

@api_router.post("/auth/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    Change user password - Secure password change for all authenticated users.
    
    Security features:
    - Rate limited (5 attempts per minute)
    - Validates current password
    - Enforces password policy (8+ chars, 1 uppercase, 1 number)
    - Confirms new password matches
    - Updates passwordChangedAt to invalidate old tokens
    - Logs audit event
    """
    # SECURITY: Rate limiting for password change attempts
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_identifier = f"change_pwd:{current_user['id']}:{client_ip}"
    check_rate_limit(rate_limit_identifier)
    
    # Verify current password
    user = await db.users.find_one({"id": current_user["id"]})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if not verify_password(password_data.current_password, user.get("hashed_password", "")):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
    
    # Check new password is different from current
    if password_data.current_password == password_data.new_password:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe ser diferente a la actual")
    
    # Verify confirm_password matches new_password
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(status_code=400, detail="Las contraseñas no coinciden")
    
    # Get current timestamp for password change
    password_changed_at = datetime.now(timezone.utc).isoformat()
    
    # Update password, clear reset flag, and set password_changed_at
    await db.users.update_one(
        {"id": current_user["id"]},
        {
            "$set": {
                "hashed_password": hash_password(password_data.new_password),
                "password_reset_required": False,
                "password_changed_at": password_changed_at
            }
        }
    )
    
    # Log audit event with full context
    await log_audit_event(
        AuditEventType.PASSWORD_CHANGED,
        current_user["id"],
        "auth",
        {
            "forced_reset": user.get("password_reset_required", False),
            "tenant_id": current_user.get("condominium_id"),
            "user_agent": request.headers.get("user-agent", "unknown")[:200],
            "ip_address": request.client.host if request.client else "unknown"
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "message": "Contraseña actualizada exitosamente",
        "password_changed_at": password_changed_at,
        "sessions_invalidated": True
    }

# ==================== PUSH NOTIFICATION ROUTES ====================
@api_router.get("/push/vapid-public-key")
async def get_vapid_public_key():
    """Get the VAPID public key for push subscription"""
    if not VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=503, detail="Push notifications not configured")
    return {"publicKey": VAPID_PUBLIC_KEY}


# ==================== FORGOT PASSWORD ENDPOINTS (CODE BASED) ====================

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordWithCodeRequest(BaseModel):
    email: str
    code: str
    new_password: str


@api_router.post("/auth/request-password-reset")
async def request_password_reset_code(
    request_data: ForgotPasswordRequest,
    request: Request
):
    """
    Request a password reset code via email.
    
    - Generates a 6-digit verification code
    - Code expires in 10 minutes
    - Sends code via email using Resend
    """
    email = request_data.email.lower().strip()
    
    # Validate email format
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not re.match(email_regex, email):
        raise HTTPException(status_code=400, detail="Formato de email inválido")
    
    # Find user
    user = await db.users.find_one({"email": email}, {"_id": 0, "id": 1, "full_name": 1, "is_active": 1})
    
    # Security: Always return success even if user doesn't exist (prevents email enumeration)
    if not user:
        logger.info(f"[PASSWORD-RESET] Code requested for non-existent email: {email}")
        return {"message": "Si el correo existe, recibirás un código de verificación"}
    
    if not user.get("is_active"):
        logger.info(f"[PASSWORD-RESET] Code requested for inactive user: {email}")
        return {"message": "Si el correo existe, recibirás un código de verificación"}
    
    # Generate 6-digit code
    code = str(random.randint(100000, 999999))
    
    # Store code with expiration (10 minutes)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    # Hash the code for storage (security)
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    
    # Upsert the reset code (one per email)
    await db.password_reset_codes.update_one(
        {"email": email},
        {
            "$set": {
                "email": email,
                "code_hash": code_hash,
                "expires_at": expires_at.isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "attempts": 0
            }
        },
        upsert=True
    )
    
    # Send email with code
    print(f"[EMAIL TRIGGER] password_reset_code → sending code to {email}")
    
    try:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
                <h1 style="color: #00d4ff; margin: 0;">GENTURIX</h1>
                <p style="color: #888; margin-top: 5px;">Recuperación de Contraseña</p>
            </div>
            
            <div style="background: #ffffff; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #eee;">
                <p>Hola,</p>
                <p>Recibimos una solicitud para restablecer tu contraseña.</p>
                
                <div style="background: #f8f9fa; padding: 25px; border-radius: 8px; margin: 25px 0; text-align: center;">
                    <p style="margin: 0 0 10px 0; font-size: 14px; color: #666;">Tu código de verificación es:</p>
                    <p style="margin: 0; font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #1a1a2e;">{code}</p>
                </div>
                
                <p style="color: #e74c3c; font-size: 14px;">
                    <strong>Este código expira en 10 minutos.</strong>
                </p>
                
                <p style="color: #666; font-size: 14px;">
                    Si no solicitaste este código, puedes ignorar este mensaje.
                </p>
            </div>
            
            <div style="text-align: center; padding: 20px; color: #888; font-size: 12px;">
                <p>Este es un correo automático de Genturix Security.</p>
            </div>
        </body>
        </html>
        """
        
        await send_email(
            to=email,
            subject="Código de Recuperación - Genturix",
            html=html_content
        )
    except Exception as e:
        logger.error(f"[PASSWORD-RESET] Failed to send code email to {email}: {e}")
        # Still return success to prevent email enumeration
    
    logger.info(f"[PASSWORD-RESET] Code sent to {email}")
    
    return {"message": "Si el correo existe, recibirás un código de verificación"}


@api_router.post("/auth/reset-password")
async def reset_password_with_code(
    request_data: ResetPasswordWithCodeRequest,
    request: Request
):
    """
    Reset password using the verification code.
    
    - Validates the 6-digit code
    - Checks expiration (10 minutes)
    - Updates password
    - Deletes used code
    """
    email = request_data.email.lower().strip()
    code = request_data.code.strip()
    new_password = request_data.new_password
    
    # Validate code format
    if not code or len(code) != 6 or not code.isdigit():
        raise HTTPException(status_code=400, detail="Código de verificación inválido")
    
    # Validate password
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres")
    if not any(c.isupper() for c in new_password):
        raise HTTPException(status_code=400, detail="La contraseña debe contener al menos una mayúscula")
    if not any(c.isdigit() for c in new_password):
        raise HTTPException(status_code=400, detail="La contraseña debe contener al menos un número")
    
    # Find reset code - query by normalized email
    print(f"[RESET PASSWORD VERIFY] Looking up code for email={email}")
    reset_record = await db.password_reset_codes.find_one({"email": email})
    
    if not reset_record:
        print(f"[RESET PASSWORD VERIFY] NO RECORD FOUND for email={email}")
        logger.warning(f"[RESET PASSWORD VERIFY] No reset record found for email={email}")
        raise HTTPException(status_code=400, detail="No hay código de verificación para este correo")
    
    # Check expiration
    expires_at = datetime.fromisoformat(reset_record["expires_at"].replace("Z", "+00:00"))
    now_utc = datetime.now(timezone.utc)
    is_expired = now_utc > expires_at
    
    print(f"[RESET PASSWORD VERIFY] email={email} expires_at={expires_at.isoformat()} now={now_utc.isoformat()} expired={is_expired}")
    
    if is_expired:
        await db.password_reset_codes.delete_one({"email": email})
        logger.info(f"[RESET PASSWORD VERIFY] Code expired for email={email}")
        raise HTTPException(status_code=400, detail="El código ha expirado. Solicita uno nuevo.")
    
    # Verify code (compare hashes)
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    stored_hash = reset_record.get("code_hash")
    code_hash_match = code_hash == stored_hash
    attempt_count = reset_record.get("attempts", 0)
    
    print(f"[RESET PASSWORD VERIFY] email={email} code_hash_match={code_hash_match} attempt_count={attempt_count}")
    logger.info(f"[RESET PASSWORD VERIFY] email={email} code_hash_match={code_hash_match} attempts={attempt_count}")
    
    if not code_hash_match:
        # Increment attempts
        attempts = reset_record.get("attempts", 0) + 1
        if attempts >= 5:
            await db.password_reset_codes.delete_one({"email": email})
            raise HTTPException(status_code=400, detail="Demasiados intentos fallidos. Solicita un nuevo código.")
        
        await db.password_reset_codes.update_one(
            {"email": email},
            {"$set": {"attempts": attempts}}
        )
        raise HTTPException(status_code=400, detail="Código de verificación incorrecto")
    
    # Find user and update password
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Update password
    password_changed_at = datetime.now(timezone.utc).isoformat()
    
    await db.users.update_one(
        {"email": email},
        {
            "$set": {
                "hashed_password": hash_password(new_password),
                "password_changed_at": password_changed_at,
                "password_reset_required": False,
                "updated_at": password_changed_at
            }
        }
    )
    
    # Delete used code (single use)
    await db.password_reset_codes.delete_one({"email": email})
    
    # Log audit event
    await log_audit_event(
        AuditEventType.PASSWORD_RESET_COMPLETED,
        user.get("id"),
        "auth",
        {"method": "verification_code", "email": email},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    print(f"[AUTH EVENT] Password reset SUCCESS | email={email}")
    logger.info(f"[PASSWORD-RESET] Password reset completed for {email}")
    print(f"[FLOW] password_reset_success | email={email}")
    
    return {"message": "Contraseña actualizada exitosamente"}


# ==================== PUSH NOTIFICATION ENDPOINTS (REFACTORED) ====================
# Backend is the ONLY authority for push notification routing.
# All subscriptions MUST have: user_id, role, condominium_id

def get_primary_role(roles: list) -> str:
    """Get the primary role for a user (for push targeting)"""
    role_priority = ["SuperAdmin", "Administrador", "Supervisor", "Guarda", "Guardia", "HR", "Residente"]
    for role in role_priority:
        if role in roles:
            return role
    return roles[0] if roles else "unknown"


@api_router.post("/push/subscribe")
async def subscribe_to_push(
    request: PushSubscriptionRequest,
    current_user = Depends(get_current_user)
):
    """
    Register a push notification subscription for the authenticated user.
    
    REQUIREMENTS:
    - User MUST be authenticated
    - User MUST have a valid condominium_id (except SuperAdmin)
    - Saves: user_id, role, condominium_id, endpoint, keys
    
    If subscription already exists for user_id + endpoint → UPDATE it.
    """
    # ==================== AUDIT LOGGING ====================
    user_id = current_user.get("id")
    user_email = current_user.get("email", "unknown")
    logger.info(f"[PUSH-SUBSCRIBE-DEBUG] ======= REQUEST START =======")
    logger.info(f"[PUSH-SUBSCRIBE-DEBUG] User: {user_email} | ID: {user_id[:12]}...")
    logger.info(f"[PUSH-SUBSCRIBE-DEBUG] Subscription endpoint: {request.subscription.endpoint[:50]}...")
    logger.info(f"[PUSH-SUBSCRIBE-DEBUG] Has p256dh: {bool(request.subscription.keys.p256dh)}")
    logger.info(f"[PUSH-SUBSCRIBE-DEBUG] Has auth: {bool(request.subscription.keys.auth)}")
    # =======================================================
    
    user_roles = current_user.get("roles", [])
    condo_id = current_user.get("condominium_id")
    
    # VALIDATION 1: User must have roles
    if not user_roles:
        raise HTTPException(
            status_code=403, 
            detail="Usuario sin roles asignados. Contacta al administrador."
        )
    
    # VALIDATION 2: Non-SuperAdmin users MUST have condominium_id
    is_super_admin = "SuperAdmin" in user_roles
    if not is_super_admin and not condo_id:
        raise HTTPException(
            status_code=403,
            detail="Usuario no asignado a un condominio. Contacta al administrador."
        )
    
    # VALIDATION 3: Verify user is active
    db_user = await db.users.find_one(
        {"id": user_id}, 
        {"_id": 0, "is_active": 1, "status": 1}
    )
    if not db_user or not db_user.get("is_active", True):
        raise HTTPException(
            status_code=403,
            detail="Cuenta de usuario inactiva."
        )
    
    if db_user.get("status") in ["blocked", "suspended"]:
        raise HTTPException(
            status_code=403,
            detail="Cuenta bloqueada o suspendida."
        )
    
    subscription = request.subscription
    primary_role = get_primary_role(user_roles)
    
    # ==================== PHASE 2: CLEANUP SAFETY ====================
    # Before insert/update, clean up invalid subscriptions for this user:
    # 1. Remove inactive subscriptions
    # 2. Remove entries with missing/empty endpoint
    cleanup_result = await db.push_subscriptions.delete_many({
        "user_id": user_id,
        "$or": [
            {"is_active": False},
            {"endpoint": None},
            {"endpoint": ""},
            {"endpoint": {"$exists": False}}
        ]
    })
    if cleanup_result.deleted_count > 0:
        logger.info(f"[PUSH-CLEANUP] Removed {cleanup_result.deleted_count} invalid subscriptions for user {user_id}")
    # ==================================================================
    
    # Check if subscription already exists for this user + endpoint
    existing = await db.push_subscriptions.find_one({
        "user_id": user_id,
        "endpoint": subscription.endpoint
    })
    
    now = datetime.now(timezone.utc).isoformat()
    
    if existing:
        # UPDATE existing subscription
        await db.push_subscriptions.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "role": primary_role,  # Update role in case it changed
                "condominium_id": condo_id,  # Update condo in case transferred
                "p256dh": subscription.keys.p256dh,
                "auth": subscription.keys.auth,
                "expiration_time": subscription.expirationTime,
                "is_active": True,
                "updated_at": now
            }}
        )
        logger.info(f"[PUSH-SUBSCRIBE-DEBUG] Subscription UPDATED for user {user_id[:12]}... (role={primary_role})")
        logger.info(f"[PUSH-SUBSCRIBE-DEBUG] ======= REQUEST SUCCESS =======")
        return {
            "message": "Suscripción actualizada",
            "status": "updated",
            "role": primary_role
        }
    
    # CREATE new subscription with all required fields
    sub_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "role": primary_role,
        "condominium_id": condo_id,
        "endpoint": subscription.endpoint,
        "p256dh": subscription.keys.p256dh,
        "auth": subscription.keys.auth,
        "expiration_time": subscription.expirationTime,
        "is_active": True,
        "created_at": now,
        "updated_at": now
    }
    
    await db.push_subscriptions.insert_one(sub_doc)
    
    logger.info(f"[PUSH-SUBSCRIBE-DEBUG] Subscription CREATED for user {user_id[:12]}... (role={primary_role}, condo={condo_id[:8] if condo_id else 'N/A'}...)")
    logger.info(f"[PUSH-SUBSCRIBE-DEBUG] ======= REQUEST SUCCESS =======")
    return {
        "message": "Suscripción exitosa",
        "status": "created",
        "role": primary_role
    }


@api_router.delete("/push/unsubscribe")
async def unsubscribe_from_push(
    request: PushSubscriptionRequest,
    current_user = Depends(get_current_user)
):
    """
    Remove a specific push subscription for the authenticated user.
    Used when user manually disables notifications.
    """
    user_id = current_user.get("id")
    subscription = request.subscription
    
    result = await db.push_subscriptions.delete_one({
        "user_id": user_id,
        "endpoint": subscription.endpoint
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada")
    
    logger.info(f"[PUSH] Subscription REMOVED for user {user_id}")
    return {"message": "Suscripción eliminada", "deleted_count": 1}


@api_router.delete("/push/unsubscribe-all")
async def unsubscribe_all_push(current_user = Depends(get_current_user)):
    """
    Remove ALL push subscriptions for the current user.
    MUST be called on logout to clean up stale subscriptions.
    """
    user_id = current_user.get("id")
    
    result = await db.push_subscriptions.delete_many({
        "user_id": user_id
    })
    
    logger.info(f"[PUSH] ALL subscriptions REMOVED for user {user_id}: {result.deleted_count} deleted")
    return {
        "message": f"{result.deleted_count} suscripciones eliminadas",
        "deleted_count": result.deleted_count
    }


@api_router.get("/push/status")
async def get_push_status(current_user = Depends(get_current_user)):
    """Get current user's push notification subscription status"""
    user_id = current_user.get("id")
    
    subscriptions = await db.push_subscriptions.find({
        "user_id": user_id,
        "is_active": True
    }, {"_id": 0, "id": 1, "endpoint": 1, "role": 1, "created_at": 1}).to_list(None)
    
    return {
        "is_subscribed": len(subscriptions) > 0,
        "subscription_count": len(subscriptions),
        "subscriptions": subscriptions
    }


@api_router.post("/push/cleanup")
async def cleanup_invalid_subscriptions(current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))):
    """
    [SUPERADMIN ONLY] Clean up invalid push subscriptions.
    
    Removes subscriptions that:
    - Have no user_id
    - Have no condominium_id (except SuperAdmin subscriptions)
    - Belong to deleted/inactive users
    
    This is a maintenance endpoint for data hygiene.
    """
    deleted_counts = {
        "no_user_id": 0,
        "no_condo_id": 0,
        "user_deleted": 0,
        "user_inactive": 0
    }
    
    # 1. Remove subscriptions without user_id
    result = await db.push_subscriptions.delete_many({
        "$or": [
            {"user_id": None},
            {"user_id": {"$exists": False}},
            {"user_id": ""}
        ]
    })
    deleted_counts["no_user_id"] = result.deleted_count
    
    # 2. Get all subscriptions with user_id but check user validity
    subscriptions = await db.push_subscriptions.find({}, {"_id": 1, "user_id": 1}).to_list(None)
    
    user_ids = list(set([s.get("user_id") for s in subscriptions if s.get("user_id")]))
    
    # Get valid users
    valid_users = await db.users.find(
        {"id": {"$in": user_ids}},
        {"_id": 0, "id": 1, "is_active": 1, "status": 1}
    ).to_list(None)
    
    valid_user_ids = set([u["id"] for u in valid_users if u.get("is_active", True) and u.get("status", "active") in ["active", None]])
    deleted_user_ids = set(user_ids) - set([u["id"] for u in valid_users])
    inactive_user_ids = set([u["id"] for u in valid_users if not u.get("is_active", True) or u.get("status") in ["blocked", "suspended"]])
    
    # Delete subscriptions for deleted users
    if deleted_user_ids:
        result = await db.push_subscriptions.delete_many({"user_id": {"$in": list(deleted_user_ids)}})
        deleted_counts["user_deleted"] = result.deleted_count
    
    # Delete subscriptions for inactive users
    if inactive_user_ids:
        result = await db.push_subscriptions.delete_many({"user_id": {"$in": list(inactive_user_ids)}})
        deleted_counts["user_inactive"] = result.deleted_count
    
    total_deleted = sum(deleted_counts.values())
    
    logger.info(f"[PUSH-CLEANUP] Cleanup completed: {total_deleted} subscriptions removed - {deleted_counts}")
    
    return {
        "message": f"Limpieza completada: {total_deleted} suscripciones eliminadas",
        "details": deleted_counts,
        "total_deleted": total_deleted
    }


# ============================================================
# TEMPORARY CLEANUP ENDPOINT - REMOVE AFTER PRODUCTION CLEAN
# ============================================================

@api_router.get("/push/cleanup-legacy")
async def cleanup_legacy_push_subscriptions(
    dry_run: bool = True,
    current_user = Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN))
):
    """
    [ADMIN/SUPERADMIN ONLY] Clean up legacy push subscriptions.
    
    TEMPORARY CLEANUP ENDPOINT - REMOVE AFTER PRODUCTION CLEAN
    
    Removes subscriptions that:
    - role is null
    - OR endpoint does not exist
    - OR endpoint is empty string
    - OR is_active is false
    
    Parameters:
    - dry_run: If True (default), only counts without deleting. Set to False to actually delete.
    
    This endpoint:
    - ONLY affects push_subscriptions collection
    - Does NOT touch users or other collections
    - Does NOT modify VAPID or send_push logic
    """
    
    # Build query for invalid/legacy subscriptions
    cleanup_query = {
        "$or": [
            {"role": None},
            {"role": {"$exists": False}},
            {"endpoint": {"$exists": False}},
            {"endpoint": None},
            {"endpoint": ""},
            {"is_active": False}
        ]
    }
    
    # Count documents to be deleted
    count_to_delete = await db.push_subscriptions.count_documents(cleanup_query)
    total_before = await db.push_subscriptions.count_documents({})
    
    logger.info(f"[PUSH-CLEANUP-LEGACY] Found {count_to_delete} legacy subscriptions to clean (dry_run={dry_run})")
    
    deleted_count = 0
    
    if not dry_run and count_to_delete > 0:
        # Actually delete the documents
        result = await db.push_subscriptions.delete_many(cleanup_query)
        deleted_count = result.deleted_count
        logger.info(f"[PUSH-CLEANUP-LEGACY] Deleted {deleted_count} legacy subscriptions")
    
    # Count remaining subscriptions
    remaining = await db.push_subscriptions.count_documents({})
    
    return {
        "dry_run": dry_run,
        "total_before": total_before,
        "matched_for_deletion": count_to_delete,
        "deleted_count": deleted_count,
        "remaining_subscriptions": remaining,
        "message": f"{'DRY RUN: Would delete' if dry_run else 'Deleted'} {count_to_delete if dry_run else deleted_count} legacy subscriptions"
    }


# ============================================================
# TEMPORARY DEBUG ENDPOINTS - REMOVE AFTER PRODUCTION DEBUG
# ============================================================

@api_router.get("/push/debug")
async def debug_push_subscriptions(current_user = Depends(get_current_user)):
    """
    [TEMPORARY DEBUG] Get current user's push subscription status.
    
    Returns subscription metadata WITHOUT sensitive keys (p256dh, auth).
    Use this to verify subscriptions are being stored correctly.
    
    REMOVE THIS ENDPOINT AFTER DEBUGGING.
    """
    user_id = current_user.get("id")
    
    try:
        subscriptions = await db.push_subscriptions.find(
            {"user_id": user_id, "is_active": True},
            {"_id": 0, "endpoint": 1, "is_active": 1, "created_at": 1, "updated_at": 1, "role": 1, "condominium_id": 1}
        ).to_list(None)
        
        # Truncate endpoints for readability (they're very long)
        safe_subs = []
        for sub in subscriptions:
            safe_subs.append({
                "endpoint": sub.get("endpoint", "")[:80] + "..." if len(sub.get("endpoint", "")) > 80 else sub.get("endpoint", ""),
                "endpoint_full_length": len(sub.get("endpoint", "")),
                "is_active": sub.get("is_active", False),
                "role": sub.get("role"),
                "condominium_id": sub.get("condominium_id"),
                "created_at": sub.get("created_at"),
                "updated_at": sub.get("updated_at")
            })
        
        logger.info(f"[PUSH-DEBUG] User {user_id} has {len(subscriptions)} active subscriptions")
        
        return {
            "user_id": user_id,
            "subscriptions_count": len(subscriptions),
            "subscriptions": safe_subs,
            "vapid_configured": bool(VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY)
        }
        
    except Exception as e:
        logger.error(f"[PUSH-DEBUG] Error fetching subscriptions for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching subscriptions: {str(e)}")


@api_router.post("/push/test")
async def test_push_notification(current_user = Depends(get_current_user)):
    """
    [TEMPORARY DEBUG] Send a test push notification to current user.
    
    Uses existing send_push_to_user() function.
    Helps verify the entire push pipeline works end-to-end.
    
    REMOVE THIS ENDPOINT AFTER DEBUGGING.
    """
    user_id = current_user.get("id")
    
    # Check VAPID configuration
    if not VAPID_PUBLIC_KEY or not VAPID_PRIVATE_KEY:
        raise HTTPException(
            status_code=503, 
            detail="VAPID keys not configured on server"
        )
    
    # Check if user has active subscriptions
    sub_count = await db.push_subscriptions.count_documents({
        "user_id": user_id,
        "is_active": True
    })
    
    if sub_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No hay suscripciones push activas. Activa las notificaciones primero en tu perfil."
        )
    
    logger.info(f"[PUSH-TEST] Sending test push to {sub_count} subscriptions for user {user_id}")
    
    # Send test notification using existing function
    payload = {
        "title": "Test Push Production",
        "body": "Si recibes esto, Web Push funciona correctamente.",
        "icon": "/logo192.png",
        "badge": "/logo192.png",
        "tag": "test-push",
        "data": {
            "type": "test",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }
    
    try:
        result = await send_push_to_user(user_id, payload)
        
        logger.info(f"[PUSH-TEST] Test push result for user {user_id}: {result}")
        
        return {
            "status": "sent",
            "user_id": user_id,
            "subscriptions_attempted": result.get("total", sub_count),
            "successful": result.get("success", 0),
            "failed": result.get("failed", 0),
            "message": "Notificación de prueba enviada. Debería aparecer en unos segundos."
        }
        
    except Exception as e:
        logger.error(f"[PUSH-TEST] Error sending test push to user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error sending push: {str(e)}")

# ============================================================
# END TEMPORARY DEBUG ENDPOINTS
# ============================================================


# ==================== PROFILE MODULE ====================
@api_router.get("/profile", response_model=ProfileResponse)
async def get_profile(current_user = Depends(get_current_user)):
    """Get current user's full profile with role-specific data"""
    condo_name = None
    if current_user.get("condominium_id"):
        condo = await db.condominiums.find_one({"id": current_user["condominium_id"]}, {"_id": 0, "name": 1})
        if condo:
            condo_name = condo.get("name")
    
    return ProfileResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        roles=current_user["roles"],
        is_active=current_user["is_active"],
        created_at=current_user["created_at"],
        condominium_id=current_user.get("condominium_id"),
        condominium_name=condo_name,
        phone=current_user.get("phone"),
        profile_photo=current_user.get("profile_photo"),
        public_description=current_user.get("public_description"),
        role_data=current_user.get("role_data"),
        language=current_user.get("language", "es")
    )

@api_router.get("/profile/{user_id}", response_model=PublicProfileResponse)
async def get_public_profile(user_id: str, current_user = Depends(get_current_user)):
    """Get public profile of another user - MUST be in same condominium (multi-tenant enforced)"""
    # Fetch the target user - exclude sensitive fields
    target_user = await db.users.find_one({"id": user_id}, {"_id": 0, "hashed_password": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Multi-tenant validation: Super Admin can view any profile, others only within their condo
    is_super_admin = "SuperAdmin" in current_user.get("roles", [])
    current_condo = current_user.get("condominium_id")
    target_condo = target_user.get("condominium_id")
    
    if not is_super_admin:
        # Users can only view profiles within their own condominium
        if current_condo != target_condo:
            raise HTTPException(status_code=403, detail="No tienes permiso para ver este perfil")
    
    # Get condominium name
    condo_name = None
    if target_condo:
        condo = await db.condominiums.find_one({"id": target_condo}, {"_id": 0, "name": 1})
        if condo:
            condo_name = condo.get("name")
    
    # Return public profile (limited info)
    return PublicProfileResponse(
        id=target_user["id"],
        full_name=target_user["full_name"],
        roles=target_user["roles"],
        profile_photo=target_user.get("profile_photo"),
        public_description=target_user.get("public_description"),
        condominium_name=condo_name,
        phone=target_user.get("phone")  # Include phone for internal contacts
    )

@api_router.patch("/profile", response_model=ProfileResponse)
async def update_profile(profile_data: ProfileUpdate, current_user = Depends(get_current_user)):
    """Update current user's profile (name, phone, photo, description)"""
    update_fields = {}
    
    if profile_data.full_name is not None:
        update_fields["full_name"] = profile_data.full_name
    if profile_data.phone is not None:
        update_fields["phone"] = profile_data.phone
    if profile_data.profile_photo is not None:
        update_fields["profile_photo"] = profile_data.profile_photo
    if profile_data.public_description is not None:
        update_fields["public_description"] = profile_data.public_description
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": update_fields}
    )
    
    # Fetch updated user - exclude sensitive fields
    updated_user = await db.users.find_one({"id": current_user["id"]}, {"_id": 0, "hashed_password": 0})
    
    condo_name = None
    if updated_user.get("condominium_id"):
        condo = await db.condominiums.find_one({"id": updated_user["condominium_id"]}, {"_id": 0, "name": 1})
        if condo:
            condo_name = condo.get("name")
    
    return ProfileResponse(
        id=updated_user["id"],
        email=updated_user["email"],
        full_name=updated_user["full_name"],
        roles=updated_user["roles"],
        is_active=updated_user["is_active"],
        created_at=updated_user["created_at"],
        condominium_id=updated_user.get("condominium_id"),
        condominium_name=condo_name,
        phone=updated_user.get("phone"),
        profile_photo=updated_user.get("profile_photo"),
        public_description=updated_user.get("public_description"),
        role_data=updated_user.get("role_data"),
        language=updated_user.get("language", "es")
    )

@api_router.patch("/profile/language")
async def update_language(language_data: LanguageUpdate, current_user = Depends(get_current_user)):
    """Update current user's language preference"""
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {
            "language": language_data.language,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Language updated successfully", "language": language_data.language}

@api_router.get("/profile/directory/condominium")
async def get_condominium_directory(current_user = Depends(get_current_user)):
    """
    Get directory of condominium users.
    
    SECURITY: Residents can ONLY see admins and guards (emergency contacts).
    Admins, Guards, and SuperAdmins can see all users.
    """
    user_roles = current_user.get("roles", [])
    is_resident = "Residente" in user_roles and not any(r in user_roles for r in ["Administrador", "SuperAdmin", "Guarda", "Supervisor", "HR"])
    is_super_admin = "SuperAdmin" in user_roles
    condo_id = current_user.get("condominium_id")
    
    # SuperAdmin can see all users if no specific condo
    if is_super_admin and not condo_id:
        return {"users": [], "grouped_by_role": {}, "condominium_name": None}
    
    if not condo_id and not is_super_admin:
        raise HTTPException(status_code=400, detail="Usuario no asignado a ningún condominio")
    
    # Get condominium name
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "name": 1})
    condo_name = condo.get("name") if condo else "Desconocido"
    
    # SECURITY FIX: Residents can only see admins and guards
    base_query = {"condominium_id": condo_id, "is_active": True}
    if is_resident:
        base_query["roles"] = {"$in": ["Administrador", "Guarda", "Supervisor"]}
    
    users_cursor = db.users.find(
        base_query,
        {"_id": 0, "id": 1, "full_name": 1, "email": 1, "roles": 1, "profile_photo": 1, "phone": 1, "public_description": 1, "role_data": 1}
    )
    users = await users_cursor.to_list(length=500)
    
    # Group users by primary role
    grouped = {}
    role_order = ["Administrador", "Supervisor", "HR", "Guarda", "Residente", "Estudiante"]
    
    for role in role_order:
        grouped[role] = []
    
    for user in users:
        primary_role = user.get("roles", ["Otro"])[0]
        if primary_role not in grouped:
            grouped[primary_role] = []
        grouped[primary_role].append({
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user.get("email"),
            "roles": user.get("roles", []),
            "profile_photo": user.get("profile_photo"),
            "phone": user.get("phone"),
            "public_description": user.get("public_description"),
            "role_data": user.get("role_data")
        })
    
    # Remove empty role groups
    grouped = {k: v for k, v in grouped.items() if v}
    
    return {
        "users": users,
        "grouped_by_role": grouped,
        "condominium_name": condo_name,
        "total_count": len(users)
    }

# ==================== SECURITY MODULE ====================
@api_router.post("/security/panic")
async def trigger_panic(event: PanicEventCreate, request: Request, current_user = Depends(get_current_user)):
    """Trigger panic alert - scoped to user's condominium, only notifies guards in same condo"""
    
    # ========== DIAGNÓSTICO P0 ==========
    user_id = current_user.get("id", "UNKNOWN")
    user_email = current_user.get("email", "UNKNOWN")
    user_roles = current_user.get("roles", [])
    condo_id = current_user.get("condominium_id")
    
    logger.info(f"[PANIC-DIAG] ========== PANIC REQUEST RECEIVED ==========")
    logger.info(f"[PANIC-DIAG] User ID: {user_id}")
    logger.info(f"[PANIC-DIAG] User Email: {user_email}")
    logger.info(f"[PANIC-DIAG] User Roles: {user_roles}")
    logger.info(f"[PANIC-DIAG] Condominium ID: {condo_id}")
    logger.info(f"[PANIC-DIAG] Panic Type: {event.panic_type.value}")
    logger.info(f"[PANIC-DIAG] Location: {event.location}")
    logger.info(f"[PANIC-DIAG] GPS: lat={event.latitude}, lng={event.longitude}")
    logger.info(f"[PANIC-DIAG] Description: {event.description}")
    
    # Validar condominium_id
    if not condo_id:
        logger.error(f"[PANIC-DIAG] ERROR: User {user_email} has NO condominium_id")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no asignado a un condominio. Contacta al administrador."
        )
    
    # Validar que el usuario existe y está activo
    db_user = await db.users.find_one({"id": user_id}, {"_id": 0, "is_active": 1})
    if not db_user:
        logger.error(f"[PANIC-DIAG] ERROR: User {user_id} not found in database")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado. Sesión inválida."
        )
    
    if not db_user.get("is_active", True):
        logger.error(f"[PANIC-DIAG] ERROR: User {user_id} is inactive")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada. Contacta al administrador."
        )
    
    # Log GPS status
    has_gps = event.latitude is not None and event.longitude is not None
    logger.info(f"[PANIC-DIAG] GPS Available: {has_gps}")
    
    # ========== FIN DIAGNÓSTICO ==========
    
    panic_type_labels = {
        "emergencia_medica": "🚑 Emergencia Médica",
        "actividad_sospechosa": "👁️ Actividad Sospechosa",
        "emergencia_general": "🚨 Emergencia General"
    }
    
    # Map internal panic type to display type for notifications
    panic_type_display_map = {
        "emergencia_medica": "medical",
        "actividad_sospechosa": "suspicious",
        "emergencia_general": "general"
    }
    
    condo_id = current_user.get("condominium_id")
    
    # Get apartment number from role_data if available
    role_data = current_user.get("role_data", {})
    apartment = role_data.get("apartment_number", "N/A")
    
    panic_event = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "user_name": current_user["full_name"],
        "user_email": current_user["email"],
        "condominium_id": condo_id,  # CRITICAL: Multi-tenant filter
        "panic_type": event.panic_type.value,
        "panic_type_label": panic_type_labels.get(event.panic_type.value, "Emergencia"),
        "location": event.location,
        "latitude": event.latitude,
        "longitude": event.longitude,
        "description": event.description,
        "apartment": apartment,
        "status": "active",
        "is_test": False,  # Mark as real data
        "notified_guards": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "resolved_at": None,
        "resolved_by": None
    }
    
    await db.panic_events.insert_one(panic_event)
    
    # Notify ONLY guards in the same condominium
    guard_query = {"status": "active"}
    if condo_id:
        guard_query["condominium_id"] = condo_id
    
    active_guards = await db.guards.find(guard_query, {"_id": 0}).to_list(100)
    for guard in active_guards:
        notification = {
            "id": str(uuid.uuid4()),
            "guard_id": guard["id"],
            "guard_user_id": guard.get("user_id"),
            "panic_event_id": panic_event["id"],
            "condominium_id": condo_id,
            "panic_type": event.panic_type.value,
            "panic_type_label": panic_type_labels.get(event.panic_type.value, "Emergencia"),
            "resident_name": current_user["full_name"],
            "location": event.location,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.guard_notifications.insert_one(notification)
        panic_event["notified_guards"].append(guard["id"])
    
    # Update panic event with notified guards
    await db.panic_events.update_one(
        {"id": panic_event["id"]},
        {"$set": {"notified_guards": panic_event["notified_guards"]}}
    )
    
    # Send PUSH NOTIFICATIONS to all subscribed guards in this condominium
    # SECURITY: Backend decides who receives - ONLY guards in same condo, excluding sender
    push_result = await notify_guards_of_panic(
        condominium_id=condo_id,
        panic_data={
            "event_id": panic_event["id"],
            "panic_type": panic_type_display_map.get(event.panic_type.value, "general"),
            "resident_name": current_user["full_name"],
            "apartment": apartment,
            "timestamp": panic_event["created_at"]
        },
        sender_id=current_user["id"]  # Exclude sender from notifications
    )
    
    # === SEND EMAIL ALERT TO ADMINISTRATORS (fail-safe) ===
    try:
        # Get condominium info for email
        condo_info = await db.condominiums.find_one(
            {"id": condo_id}, 
            {"_id": 0, "name": 1, "contact_email": 1}
        )
        condo_name = condo_info.get("name", "Condominio") if condo_info else "Condominio"
        
        # Get admin users for this condominium
        admin_users = await db.users.find(
            {"condominium_id": condo_id, "roles": {"$in": ["Administrador"]}, "is_active": True},
            {"_id": 0, "email": 1, "full_name": 1}
        ).to_list(10)
        
        # Send email to each admin
        for admin in admin_users:
            admin_email = admin.get("email")
            if admin_email:
                try:
                    alert_html = get_emergency_alert_email_html(
                        resident_name=current_user["full_name"],
                        alert_type=panic_type_labels.get(event.panic_type.value, "Emergencia"),
                        location=event.location or apartment,
                        timestamp=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC"),
                        condominium_name=condo_name
                    )
                    await send_email(
                        to=admin_email,
                        subject=f"🚨 ALERTA DE EMERGENCIA - {condo_name}",
                        html=alert_html
                    )
                except Exception as admin_email_error:
                    logger.warning(f"[EMAIL] Failed to send emergency alert to admin {admin_email}: {admin_email_error}")
    except Exception as email_error:
        logger.warning(f"[EMAIL] Failed to send emergency alert emails: {email_error}")
        # Continue - don't break API flow
    
    # Log to audit
    await log_audit_event(
        AuditEventType.PANIC_BUTTON,
        current_user["id"],
        "security",
        {
            "panic_type": event.panic_type.value,
            "location": event.location,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "description": event.description,
            "notified_guards_count": len(active_guards),
            "push_notifications": push_result
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    logger.info(f"[PANIC-DIAG] SUCCESS: Alert {panic_event['id']} created, {len(active_guards)} guards notified")
    
    return {
        "message": "Alerta enviada exitosamente",
        "event_id": panic_event["id"],
        "panic_type": event.panic_type.value,
        "notified_guards": len(active_guards),
        "push_notifications": push_result
    }

@api_router.get("/resident/my-alerts")
async def get_resident_alerts(current_user = Depends(get_current_user)):
    """
    Resident gets their own alert history - STRICTLY filtered by user_id AND condominium_id.
    Shows: alert type, timestamp, status (active/resolved), resolved_by
    """
    condo_id = current_user.get("condominium_id")
    user_id = current_user["id"]
    
    if not condo_id:
        return []
    
    query = {
        "user_id": user_id,
        "condominium_id": condo_id,
        "is_test": {"$ne": True}
    }
    
    events = await db.panic_events.find(query, {"_id": 0}).sort("created_at", -1).to_list(50)
    
    # Format response for resident view
    formatted_events = []
    for e in events:
        formatted_events.append({
            "id": e.get("id"),
            "panic_type": e.get("panic_type"),
            "panic_type_label": e.get("panic_type_label"),
            "location": e.get("location"),
            "status": e.get("status"),
            "created_at": e.get("created_at"),
            "resolved_at": e.get("resolved_at"),
            "resolved_by_name": e.get("resolved_by_name"),
            "notified_guards": len(e.get("notified_guards", []))
        })
    
    return formatted_events

@api_router.get("/security/panic-events")
async def get_panic_events(current_user = Depends(require_module("security"))):
    """Get panic events - scoped by condominium, excludes test/demo data"""
    # Verify role
    allowed_roles = ["Administrador", "Supervisor", "Guarda", "SuperAdmin"]
    if not any(role in current_user.get("roles", []) for role in allowed_roles):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    # Use tenant_filter for automatic condominium scoping
    query = tenant_filter(current_user, {"is_test": {"$ne": True}})
    
    events = await db.panic_events.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return events

@api_router.put("/security/panic/{event_id}/resolve")
async def resolve_panic(event_id: str, resolve_data: PanicResolveRequest, request: Request, current_user = Depends(require_role_and_module("Administrador", "Supervisor", "Guarda", module="security"))):
    """Resolve a panic event and save to guard_history"""
    # Use get_tenant_resource for automatic 404/403 handling
    event = await get_tenant_resource(db.panic_events, event_id, current_user)
    
    resolved_at = datetime.now(timezone.utc).isoformat()
    resolution_notes = resolve_data.notes if resolve_data.notes else None
    
    await db.panic_events.update_one(
        {"id": event_id},
        {"$set": {
            "status": "resolved", 
            "resolved_at": resolved_at, 
            "resolved_by": current_user["id"],
            "resolved_by_name": current_user.get("full_name", "Unknown"),
            "resolution_notes": resolution_notes
        }}
    )
    
    # Get guard info if resolver is a guard
    guard = await db.guards.find_one({"user_id": current_user["id"]})
    guard_id = guard["id"] if guard else None
    
    # Save to guard_history for audit trail
    history_entry = {
        "id": str(uuid.uuid4()),
        "type": "alert_resolved",
        "guard_id": guard_id,
        "guard_user_id": current_user["id"],
        "guard_name": current_user.get("full_name"),
        "condominium_id": event.get("condominium_id") or current_user.get("condominium_id"),
        "event_id": event_id,
        "event_type": event.get("panic_type"),
        "event_type_label": event.get("panic_type_label"),
        "resident_name": event.get("user_name"),
        "location": event.get("location"),
        "original_created_at": event.get("created_at"),
        "resolved_at": resolved_at,
        "resolution_notes": resolution_notes,
        "timestamp": resolved_at
    }
    await db.guard_history.insert_one(history_entry)
    
    # Log audit event
    await log_audit_event(
        AuditEventType.PANIC_RESOLVED,
        current_user["id"],
        "security",
        {
            "event_id": event_id,
            "panic_type": event.get("panic_type"),
            "resident_name": event.get("user_name"),
            "location": event.get("location"),
            "resolution_notes": resolution_notes
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "Panic event resolved"}

@api_router.post("/security/access-log")
async def create_access_log(log: AccessLogCreate, request: Request, current_user = Depends(require_role_and_module("Administrador", "Supervisor", "Guarda", module="security"))):
    # Determine role for source field
    user_roles = current_user.get("roles", [])
    if "Administrador" in user_roles:
        source = "manual_admin"
    elif "Supervisor" in user_roles:
        source = "manual_supervisor"
    else:
        source = "manual_guard"
    
    access_log = {
        "id": str(uuid.uuid4()),
        "person_name": log.person_name,
        "access_type": log.access_type,
        "location": log.location,
        "notes": log.notes,
        "recorded_by": current_user["id"],
        "recorded_by_name": current_user.get("full_name", "Usuario"),
        "condominium_id": current_user.get("condominium_id"),
        "source": source,
        "status": "inside" if log.access_type == "entry" else "outside",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await db.access_logs.insert_one(access_log)
    
    # Remove MongoDB _id before returning
    access_log.pop("_id", None)
    
    # Use appropriate audit event type based on access type
    audit_event = AuditEventType.ACCESS_GRANTED if log.access_type == "entry" else AuditEventType.ACCESS_DENIED
    
    # Log audit event with manual access action
    await log_audit_event(
        audit_event,
        current_user["id"],
        "access",
        {
            "action": "manual_access_created",
            "person": log.person_name, 
            "type": log.access_type, 
            "location": log.location, 
            "performed_by_role": source.replace("manual_", "").upper(),
            "performed_by_name": current_user.get("full_name"),
            "condominium_id": current_user.get("condominium_id")
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return access_log

@api_router.get("/security/access-logs")
async def get_access_logs(
    include_visitor_entries: bool = True,
    limit: int = 100,
    current_user = Depends(require_role_and_module("Administrador", "Supervisor", "Guarda", "SuperAdmin", module="security"))
):
    """
    Get unified access logs combining:
    - Manual access_logs entries
    - visitor_entries (check-ins from guards)
    Scoped by condominium for non-SuperAdmin users
    """
    # Use tenant_filter for automatic condominium scoping
    query = tenant_filter(current_user)
    
    # Get manual access logs
    manual_logs = await db.access_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit // 2)
    
    # Convert to unified format
    unified_logs = []
    for log in manual_logs:
        unified_logs.append({
            "id": log.get("id"),
            "person_name": log.get("person_name"),
            "access_type": log.get("access_type", "entry"),
            "entry_type": "manual",
            "location": log.get("location", "Sin ubicación"),
            "timestamp": log.get("timestamp"),
            "guard_name": log.get("recorded_by_name"),
            "notes": log.get("notes"),
            "source": log.get("source", "manual")
        })
    
    # Include visitor entries (actual check-ins)
    if include_visitor_entries:
        entries = await db.visitor_entries.find(query, {"_id": 0}).sort("entry_at", -1).to_list(limit)
        
        for entry in entries:
            unified_logs.append({
                "id": entry.get("id"),
                "person_name": entry.get("visitor_name", "Visitante"),
                "access_type": "entry" if entry.get("entry_at") else "exit",
                "entry_type": entry.get("authorization_type", "visitor"),
                "location": entry.get("destination", "Sin destino"),
                "timestamp": entry.get("entry_at") or entry.get("exit_at"),
                "exit_timestamp": entry.get("exit_at"),
                "guard_name": entry.get("guard_name"),
                "vehicle_plate": entry.get("vehicle_plate"),
                "is_authorized": entry.get("is_authorized", True),
                "resident_name": entry.get("authorized_by_name"),
                "source": "check_in"
            })
    
    # Sort all by timestamp (most recent first)
    unified_logs.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    
    return unified_logs[:limit]

# Endpoint for Residents to see their visitor notifications
@api_router.get("/resident/notifications")
async def get_resident_notifications(current_user = Depends(get_current_user)):
    """Get visitor entry/exit notifications for a resident"""
    # Get visitor records created by this resident that have been executed
    visitors = await db.visitors.find(
        {"created_by": current_user["id"], "status": {"$in": ["entry_registered", "exit_registered"]}},
        {"_id": 0}
    ).sort("updated_at", -1).to_list(20)
    
    return visitors

# ==================== VISITOR PRE-REGISTRATION MODULE ====================
# Flow: Resident creates → Guard executes → Admin audits

@api_router.post("/visitors/pre-register")
async def create_visitor_preregistration(
    visitor: VisitorPreRegistration,
    request: Request,
    current_user = Depends(get_current_user)
):
    """Resident pre-registers a visitor - creates PENDING record"""
    visitor_id = str(uuid.uuid4())
    
    visitor_doc = {
        "id": visitor_id,
        "full_name": visitor.full_name,
        "national_id": visitor.national_id,
        "vehicle_plate": visitor.vehicle_plate,
        "visit_type": visitor.visit_type.value,
        "expected_date": visitor.expected_date,
        "expected_time": visitor.expected_time,
        "notes": visitor.notes,
        "status": VisitorStatusEnum.PENDING.value,
        "created_by": current_user["id"],
        "created_by_name": current_user.get("full_name", "Resident"),
        "condominium_id": current_user.get("condominium_id"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "entry_at": None,
        "entry_by": None,
        "entry_by_name": None,
        "exit_at": None,
        "exit_by": None,
        "exit_by_name": None
    }
    
    await db.visitors.insert_one(visitor_doc)
    
    # Notify guards about the new pre-registration using dynamic targeting
    condo_id = current_user.get("condominium_id")
    if condo_id:
        resident_name = current_user.get("full_name", "Un residente")
        resident_apt = current_user.get("apartment", "")
        apt_text = f" ({resident_apt})" if resident_apt else ""
        
        await send_targeted_push_notification(
            condominium_id=condo_id,
            title="📋 Nuevo visitante preregistrado",
            body=f"{visitor.full_name} para {resident_name}{apt_text}",
            target_roles=["Guarda"],
            data={
                "type": "visitor_preregistration",
                "visitor_id": visitor_id,
                "visitor_name": visitor.full_name,
                "resident_name": resident_name,
                "expected_date": visitor.expected_date,
                "expected_time": visitor.expected_time,
                "url": "/guard?tab=visits"
            },
            tag=f"preregister-{visitor_id[:8]}"
        )
    
    await log_audit_event(
        AuditEventType.ACCESS_GRANTED,
        current_user["id"],
        "visitors",
        {"action": "pre_registration", "visitor": visitor.full_name, "expected_date": visitor.expected_date, "resident": current_user.get("full_name")},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"id": visitor_id, "message": "Visitor pre-registered successfully", "status": "pending"}

@api_router.get("/visitors/my-visitors")
async def get_my_visitors(current_user = Depends(get_current_user)):
    """Get visitors pre-registered by the current resident"""
    visitors = await db.visitors.find(
        {"created_by": current_user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return visitors

@api_router.delete("/visitors/{visitor_id}")
async def cancel_visitor_preregistration(
    visitor_id: str,
    current_user = Depends(get_current_user)
):
    """Resident cancels their own visitor pre-registration"""
    result = await db.visitors.update_one(
        {"id": visitor_id, "created_by": current_user["id"], "status": "pending"},
        {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Visitor not found or cannot be cancelled")
    
    return {"message": "Visitor pre-registration cancelled"}

@api_router.get("/visitors/pending")
async def get_pending_visitors(
    search: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """Guard gets list of pending visitors expected today - SCOPED BY CONDOMINIUM"""
    # Use tenant_filter for automatic multi-tenant filtering
    query = tenant_filter(current_user, {"status": {"$in": ["pending", "entry_registered"]}})
    
    visitors = await db.visitors.find(query, {"_id": 0}).sort("expected_date", -1).to_list(100)
    
    # Filter by search term if provided
    if search:
        search_lower = search.lower()
        visitors = [
            v for v in visitors 
            if search_lower in v.get("full_name", "").lower() or
               search_lower in (v.get("vehicle_plate") or "").lower() or
               search_lower in (v.get("created_by_name") or "").lower() or
               search_lower in (v.get("national_id") or "").lower()
        ]
    
    return visitors

@api_router.post("/visitors/{visitor_id}/entry")
async def register_visitor_entry(
    visitor_id: str,
    entry_data: VisitorEntry,
    request: Request,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """Guard registers visitor ENTRY"""
    visitor = await db.visitors.find_one({"id": visitor_id})
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    
    if visitor.get("status") not in ["pending", "approved"]:
        raise HTTPException(status_code=400, detail=f"Cannot register entry. Current status: {visitor.get('status')}")
    
    entry_time = datetime.now(timezone.utc).isoformat()
    
    await db.visitors.update_one(
        {"id": visitor_id},
        {"$set": {
            "status": "entry_registered",
            "entry_at": entry_time,
            "entry_by": current_user["id"],
            "entry_by_name": current_user.get("full_name", "Guard"),
            "entry_notes": entry_data.notes,
            "updated_at": entry_time
        }}
    )
    
    await log_audit_event(
        AuditEventType.ACCESS_GRANTED,
        current_user["id"],
        "visitors",
        {
            "action": "entry_registered",
            "visitor": visitor.get("full_name"),
            "visitor_id": visitor_id,
            "resident": visitor.get("created_by_name"),
            "guard": current_user.get("full_name")
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "Visitor entry registered", "entry_at": entry_time}

@api_router.post("/visitors/{visitor_id}/exit")
async def register_visitor_exit(
    visitor_id: str,
    exit_data: VisitorExit,
    request: Request,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """Guard registers visitor EXIT and saves to guard_history"""
    visitor = await db.visitors.find_one({"id": visitor_id})
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    
    if visitor.get("status") != "entry_registered":
        raise HTTPException(status_code=400, detail=f"Cannot register exit. Current status: {visitor.get('status')}")
    
    exit_time = datetime.now(timezone.utc).isoformat()
    
    await db.visitors.update_one(
        {"id": visitor_id},
        {"$set": {
            "status": "exit_registered",
            "exit_at": exit_time,
            "exit_by": current_user["id"],
            "exit_by_name": current_user.get("full_name", "Guard"),
            "exit_notes": exit_data.notes,
            "updated_at": exit_time
        }}
    )
    
    # Get guard info if resolver is a guard
    guard = await db.guards.find_one({"user_id": current_user["id"]})
    guard_id = guard["id"] if guard else None
    condo_id = visitor.get("condominium_id") or current_user.get("condominium_id")
    
    # Save to guard_history
    history_entry = {
        "id": str(uuid.uuid4()),
        "type": "visit_completed",
        "guard_id": guard_id,
        "guard_user_id": current_user["id"],
        "guard_name": current_user.get("full_name"),
        "condominium_id": condo_id,
        "visitor_id": visitor_id,
        "visitor_name": visitor.get("full_name"),
        "resident_name": visitor.get("created_by_name"),
        "entry_at": visitor.get("entry_at"),
        "exit_at": exit_time,
        "notes": exit_data.notes,
        "timestamp": exit_time
    }
    await db.guard_history.insert_one(history_entry)
    
    await log_audit_event(
        AuditEventType.ACCESS_DENIED,
        current_user["id"],
        "visitors",
        {
            "action": "exit_registered",
            "visitor": visitor.get("full_name"),
            "visitor_id": visitor_id,
            "resident": visitor.get("created_by_name"),
            "guard": current_user.get("full_name"),
            "duration_minutes": None  # Could calculate from entry_at
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "Visitor exit registered", "exit_at": exit_time}

@api_router.get("/visitors/all")
async def get_all_visitors(
    status: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """Admin/Guard gets visitor records for audit - SCOPED BY CONDOMINIUM"""
    # Use tenant_filter for automatic multi-tenant filtering
    extra = {"status": status} if status else None
    query = tenant_filter(current_user, extra)
    
    visitors = await db.visitors.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return visitors

# ==================== ADVANCED VISITOR AUTHORIZATION SYSTEM ====================
# Phase 3: Competitor-Level Feature
# Flow: Resident creates authorization → Guard validates & checks in → System notifies

def get_color_code_for_type(auth_type: str) -> str:
    """Get color code based on authorization type"""
    color_map = {
        "permanent": "green",
        "recurring": "blue",
        "temporary": "yellow",
        "extended": "purple"
    }
    return color_map.get(auth_type, "yellow")

def check_authorization_validity(authorization: dict, condominium_timezone: str = None) -> dict:
    """
    Check if an authorization is currently valid.
    Returns: {is_valid: bool, status: str, message: str}
    
    TIMEZONE FIX: Uses condominium timezone for day/time calculations.
    Falls back to UTC if no timezone provided.
    """
    # Get current time in condominium timezone (or UTC as fallback)
    if condominium_timezone:
        try:
            tz = ZoneInfo(condominium_timezone)
            now = datetime.now(tz)
        except Exception as e:
            logger.warning(f"[AUTH-VALIDITY] Invalid timezone '{condominium_timezone}', falling back to UTC: {e}")
            now = datetime.now(timezone.utc)
    else:
        now = datetime.now(timezone.utc)
    
    today_str = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    current_day_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][now.weekday()]
    
    auth_type = authorization.get("authorization_type", "temporary")
    
    # Check if authorization is active
    if not authorization.get("is_active", True):
        return {"is_valid": False, "status": "revoked", "message": "Autorización revocada"}
    
    # Permanent: Always valid
    if auth_type == "permanent":
        return {"is_valid": True, "status": "authorized", "message": "Autorización permanente"}
    
    # Check date range for temporary, extended
    valid_from = authorization.get("valid_from")
    valid_to = authorization.get("valid_to")
    
    if valid_from and today_str < valid_from:
        return {"is_valid": False, "status": "not_yet_valid", "message": f"Válido desde {valid_from}"}
    
    if valid_to and today_str > valid_to:
        return {"is_valid": False, "status": "expired", "message": f"Expiró el {valid_to}"}
    
    # Check allowed days for recurring
    if auth_type == "recurring":
        allowed_days = authorization.get("allowed_days", [])
        if allowed_days and current_day_es not in allowed_days:
            return {"is_valid": False, "status": "not_today", "message": f"No autorizado hoy ({current_day_es})"}
    
    # Check time windows for extended
    if auth_type == "extended":
        hours_from = authorization.get("allowed_hours_from")
        hours_to = authorization.get("allowed_hours_to")
        
        if hours_from and current_time < hours_from:
            return {"is_valid": False, "status": "too_early", "message": f"Válido desde las {hours_from}"}
        
        if hours_to and current_time > hours_to:
            return {"is_valid": False, "status": "too_late", "message": f"Válido hasta las {hours_to}"}
    
    return {"is_valid": True, "status": "authorized", "message": "Autorización válida"}

# ===================== RESIDENT AUTHORIZATION ENDPOINTS =====================

@api_router.post("/authorizations")
async def create_visitor_authorization(
    auth_data: VisitorAuthorizationCreate,
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    Resident creates a visitor authorization.
    Types: temporary (single/range), permanent (always), recurring (days), extended (range+hours)
    """
    auth_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Auto-assign color based on type
    color_code = get_color_code_for_type(auth_data.authorization_type.value)
    
    # Set defaults based on type
    valid_from = auth_data.valid_from
    valid_to = auth_data.valid_to
    
    if auth_data.authorization_type == AuthorizationTypeEnum.TEMPORARY and not valid_from:
        # Default to today if temporary and no date set
        valid_from = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        valid_to = valid_to or valid_from
    
    auth_doc = {
        "id": auth_id,
        "visitor_name": auth_data.visitor_name,
        "identification_number": auth_data.identification_number,
        "vehicle_plate": auth_data.vehicle_plate.upper() if auth_data.vehicle_plate else None,
        "authorization_type": auth_data.authorization_type.value,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "allowed_days": auth_data.allowed_days or [],
        "allowed_hours_from": auth_data.allowed_hours_from,
        "allowed_hours_to": auth_data.allowed_hours_to,
        "notes": auth_data.notes,
        "color_code": color_code,
        "is_active": True,
        "status": "pending",  # Status for tracking: pending -> used
        "created_by": current_user["id"],
        "created_by_name": current_user.get("full_name", "Residente"),
        "resident_apartment": current_user.get("role_data", {}).get("apartment_number", "N/A"),
        "condominium_id": current_user.get("condominium_id"),
        "created_at": now,
        "updated_at": now,
        "total_visits": 0,
        "last_visit": None,
        "checked_in_at": None,
        "checked_in_by": None,
        "checked_in_by_name": None,
        # Visitor type fields
        "visitor_type": auth_data.visitor_type or "visitor",
        "company": auth_data.company,
        "service_type": auth_data.service_type
    }
    
    await db.visitor_authorizations.insert_one(auth_doc)
    
    await log_audit_event(
        AuditEventType.AUTHORIZATION_CREATED,
        current_user["id"],
        "visitor_authorizations",
        {
            "authorization_id": auth_id,
            "visitor_name": auth_data.visitor_name,
            "type": auth_data.authorization_type.value,
            "resident": current_user.get("full_name")
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    # ========== NOTIFY GUARDS AND ADMINS ==========
    condo_id = current_user.get("condominium_id")
    if condo_id:
        resident_name = current_user.get("full_name", "Un residente")
        visitor_name = auth_data.visitor_name
        apartment = current_user.get("role_data", {}).get("apartment_number", "")
        
        # Create notification payload
        notification_payload = {
            "title": "📋 Nuevo visitante preregistrado",
            "body": f"{visitor_name} - autorizado por {resident_name}" + (f" ({apartment})" if apartment else ""),
            "icon": "/logo192.png",
            "badge": "/logo192.png",
            "tag": f"preregistration-{auth_id[:8]}",
            "data": {
                "type": "visitor_preregistration",
                "authorization_id": auth_id,
                "visitor_name": visitor_name,
                "resident_name": resident_name,
                "url": "/guard?tab=pending"
            }
        }
        
        # Create notification in DB for guards
        guard_users = await db.users.find(
            {"condominium_id": condo_id, "roles": {"$in": ["Guarda"]}, "is_active": True},
            {"_id": 0, "id": 1}
        ).to_list(None)
        
        for guard in guard_users:
            await db.guard_notifications.insert_one({
                "id": str(uuid.uuid4()),
                "type": "visitor_preregistration",
                "guard_user_id": guard["id"],
                "condominium_id": condo_id,
                "title": "Nuevo visitante preregistrado",
                "message": f"{visitor_name} ha sido autorizado por {resident_name}" + (f" - Apto {apartment}" if apartment else ""),
                "data": {
                    "authorization_id": auth_id,
                    "visitor_name": visitor_name,
                    "resident_name": resident_name
                },
                "read": False,
                "created_at": now
            })
        
        # Send push notifications to guards and admins
        try:
            await send_push_to_guards(condo_id, notification_payload)
            await send_push_to_admins(condo_id, notification_payload)
            logger.info(f"[PREREGISTRATION] Notifications sent for visitor {visitor_name}")
        except Exception as e:
            logger.warning(f"[PREREGISTRATION] Failed to send push notifications: {e}")
        
        # === SEND EMAIL TO GUARDS (fail-safe) ===
        try:
            print(f"[EMAIL TRIGGER] visitor_preregistration → notifying guards for visitor {visitor_name}")
            # Get condominium info
            condo_info = await db.condominiums.find_one(
                {"id": condo_id},
                {"_id": 0, "name": 1}
            )
            condo_name = condo_info.get("name", "Condominio") if condo_info else "Condominio"
            
            # Get guard users with email
            guard_users_with_email = await db.users.find(
                {"condominium_id": condo_id, "roles": {"$in": ["Guarda"]}, "is_active": True},
                {"_id": 0, "email": 1, "full_name": 1}
            ).to_list(20)
            
            print(f"[EMAIL DEBUG] Found {len(guard_users_with_email)} guards with email")
            
            for guard in guard_users_with_email:
                guard_email = guard.get("email")
                guard_name = guard.get("full_name", "Guardia")
                if guard_email:
                    try:
                        preregistration_html = get_visitor_preregistration_email_html(
                            guard_name=guard_name,
                            visitor_name=visitor_name,
                            resident_name=resident_name,
                            apartment=apartment or "N/A",
                            valid_from=auth_data.valid_from or "Hoy",
                            valid_to=auth_data.valid_to or "Sin límite",
                            condominium_name=condo_name
                        )
                        await send_email(
                            to=guard_email,
                            subject=f"📋 Visitante Preregistrado - {visitor_name}",
                            html=preregistration_html
                        )
                    except Exception as guard_email_error:
                        logger.warning(f"[EMAIL] Failed to send preregistration email to guard {guard_email}: {guard_email_error}")
        except Exception as email_error:
            logger.warning(f"[EMAIL] Failed to send preregistration emails: {email_error}")
            # Continue - don't break API flow
    
    # Return without _id
    auth_doc.pop("_id", None)
    return auth_doc

@api_router.get("/authorizations/my")
async def get_my_authorizations(
    status: Optional[str] = None,  # active, expired, all, used
    current_user = Depends(get_current_user)
):
    """Resident gets their own visitor authorizations with usage status"""
    query = {"created_by": current_user["id"]}
    
    if status == "active":
        query["is_active"] = True
        query["status"] = {"$ne": "used"}  # Exclude used authorizations from active
    elif status == "expired":
        query["is_active"] = False
    elif status == "used":
        query["status"] = "used"
    elif status == "all":
        pass  # Return all including inactive
    else:
        # DEFAULT: Only return active (not deleted) authorizations
        query["is_active"] = True
    
    authorizations = await db.visitor_authorizations.find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # Get condominium timezone for validity checks
    condo_timezone = None
    condo_id = current_user.get("condominium_id")
    if condo_id:
        condo = await db.condominiums.find_one({"id": condo_id}, {"timezone": 1})
        condo_timezone = condo.get("timezone") if condo else None
    
    # Enrich with validity status and usage info
    for auth in authorizations:
        validity = check_authorization_validity(auth, condo_timezone)
        auth["validity_status"] = validity["status"]
        auth["validity_message"] = validity["message"]
        auth["is_currently_valid"] = validity["is_valid"]
        
        # P0 FIX: Check if there's a visitor currently INSIDE using this authorization
        # This prevents residents from deleting authorizations while visitor is inside
        active_inside = await db.visitor_entries.find_one({
            "authorization_id": auth.get("id"),
            "status": "inside"
        }, {"_id": 0, "id": 1})
        auth["has_visitor_inside"] = active_inside is not None
        
        # Check if authorization has been used (has entry record)
        auth_type = auth.get("authorization_type")
        if auth_type in ["temporary", "extended"]:
            # For one-time use authorizations, check if already used
            entry_exists = await db.visitor_entries.find_one({"authorization_id": auth.get("id")})
            if entry_exists:
                auth["status"] = "used"
                auth["was_used"] = True
                auth["used_at"] = entry_exists.get("entry_at")
                auth["used_by_guard"] = entry_exists.get("entry_by_name") or entry_exists.get("guard_name")
            else:
                auth["was_used"] = False
        else:
            # For permanent/recurring, check last usage
            last_entry = await db.visitor_entries.find_one(
                {"authorization_id": auth.get("id")},
                sort=[("entry_at", -1)]
            )
            if last_entry:
                auth["last_used_at"] = last_entry.get("entry_at")
                auth["total_uses"] = await db.visitor_entries.count_documents({"authorization_id": auth.get("id")})
            else:
                auth["total_uses"] = 0
    
    return authorizations


# ===================== AUDIT & HISTORY (must be before {auth_id} routes) =====================

@api_router.get("/authorizations/history")
async def get_authorization_history(
    auth_id: Optional[str] = None,
    resident_id: Optional[str] = None,
    visitor_name: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """
    Get visitor entry/exit history for audit.
    Filterable by authorization, resident, visitor name, date range.
    """
    # Build extra filters
    extra = {}
    if auth_id:
        extra["authorization_id"] = auth_id
    if resident_id:
        extra["resident_id"] = resident_id
    if visitor_name:
        extra["visitor_name"] = {"$regex": visitor_name, "$options": "i"}
    
    # Date filtering
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = f"{date_from}T00:00:00"
        if date_to:
            date_query["$lte"] = f"{date_to}T23:59:59"
        if date_query:
            extra["entry_at"] = date_query
    
    # Use tenant_filter for multi-tenant scoping
    query = tenant_filter(current_user, extra if extra else None)
    
    entries = await db.visitor_entries.find(query, {"_id": 0}).sort("entry_at", -1).to_list(500)
    return entries

@api_router.get("/authorizations/stats")
async def get_authorization_stats(
    current_user = Depends(require_role("Administrador", "Supervisor"))
):
    """Get statistics about visitor authorizations and entries"""
    # Use tenant_filter for multi-tenant scoping
    query = tenant_filter(current_user)
    
    if not query and "SuperAdmin" not in current_user.get("roles", []):
        # No condominium assigned
        return {}
    
    # Count active authorizations by type
    auth_pipeline = [
        {"$match": {**query, "is_active": True}},
        {"$group": {"_id": "$authorization_type", "count": {"$sum": 1}}}
    ]
    auth_counts = await db.visitor_authorizations.aggregate(auth_pipeline).to_list(10)
    
    # Count entries today
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_entries = await db.visitor_entries.count_documents({
        **query,
        "entry_at": {"$gte": f"{today}T00:00:00"}
    })
    
    # Count visitors currently inside
    inside_count = await db.visitor_entries.count_documents({
        **query,
        "status": "inside"
    })
    
    # Total authorizations
    total_auths = await db.visitor_authorizations.count_documents({**query, "is_active": True})
    
    return {
        "total_active_authorizations": total_auths,
        "authorizations_by_type": {item["_id"]: item["count"] for item in auth_counts},
        "entries_today": today_entries,
        "visitors_inside": inside_count
    }

@api_router.get("/authorizations/{auth_id}")
async def get_authorization(
    auth_id: str,
    current_user = Depends(get_current_user)
):
    """Get a specific authorization by ID"""
    # Use get_tenant_resource for automatic 404/403 handling
    auth = await get_tenant_resource(db.visitor_authorizations, auth_id, current_user)
    
    # Get condominium timezone for validity check
    condo_timezone = None
    condo_id = current_user.get("condominium_id")
    if condo_id:
        condo = await db.condominiums.find_one({"id": condo_id}, {"timezone": 1})
        condo_timezone = condo.get("timezone") if condo else None
    
    validity = check_authorization_validity(auth, condo_timezone)
    auth["validity_status"] = validity["status"]
    auth["validity_message"] = validity["message"]
    auth["is_currently_valid"] = validity["is_valid"]
    
    return auth

@api_router.patch("/authorizations/{auth_id}")
async def update_authorization(
    auth_id: str,
    auth_data: VisitorAuthorizationUpdate,
    request: Request,
    current_user = Depends(get_current_user)
):
    """Resident updates their own authorization"""
    auth = await db.visitor_authorizations.find_one({"id": auth_id})
    if not auth:
        raise HTTPException(status_code=404, detail="Autorización no encontrada")
    
    # Only owner can update
    if auth.get("created_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Solo puedes modificar tus propias autorizaciones")
    
    update_fields = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if auth_data.visitor_name is not None:
        update_fields["visitor_name"] = auth_data.visitor_name
    if auth_data.identification_number is not None:
        update_fields["identification_number"] = auth_data.identification_number
    if auth_data.vehicle_plate is not None:
        update_fields["vehicle_plate"] = auth_data.vehicle_plate.upper() if auth_data.vehicle_plate else None
    if auth_data.authorization_type is not None:
        update_fields["authorization_type"] = auth_data.authorization_type.value
        update_fields["color_code"] = get_color_code_for_type(auth_data.authorization_type.value)
    if auth_data.valid_from is not None:
        update_fields["valid_from"] = auth_data.valid_from
    if auth_data.valid_to is not None:
        update_fields["valid_to"] = auth_data.valid_to
    if auth_data.allowed_days is not None:
        update_fields["allowed_days"] = auth_data.allowed_days
    if auth_data.allowed_hours_from is not None:
        update_fields["allowed_hours_from"] = auth_data.allowed_hours_from
    if auth_data.allowed_hours_to is not None:
        update_fields["allowed_hours_to"] = auth_data.allowed_hours_to
    if auth_data.notes is not None:
        update_fields["notes"] = auth_data.notes
    if auth_data.is_active is not None:
        update_fields["is_active"] = auth_data.is_active
    # Visitor type fields
    if auth_data.visitor_type is not None:
        update_fields["visitor_type"] = auth_data.visitor_type
    if auth_data.company is not None:
        update_fields["company"] = auth_data.company
    if auth_data.service_type is not None:
        update_fields["service_type"] = auth_data.service_type
    
    await db.visitor_authorizations.update_one(
        {"id": auth_id},
        {"$set": update_fields}
    )
    
    await log_audit_event(
        AuditEventType.AUTHORIZATION_UPDATED,
        current_user["id"],
        "visitor_authorizations",
        {"authorization_id": auth_id, "changes": list(update_fields.keys())},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    # Fetch and return updated
    updated = await db.visitor_authorizations.find_one({"id": auth_id}, {"_id": 0})
    return updated

@api_router.delete("/authorizations/{auth_id}")
async def deactivate_authorization(
    auth_id: str,
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    Resident deactivates (soft delete) their authorization.
    
    BUSINESS RULES:
    - Resident CAN delete when: status is PENDING or visitor has EXITED
    - Resident CANNOT delete when: visitor is currently INSIDE the condominium
    - This prevents losing track of who's inside
    """
    auth = await db.visitor_authorizations.find_one({"id": auth_id})
    if not auth:
        raise HTTPException(status_code=404, detail="Autorización no encontrada")
    
    # Only owner can deactivate
    if auth.get("created_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Solo puedes eliminar tus propias autorizaciones")
    
    # ==================== P0 FIX: PREVENT DELETION WHEN VISITOR IS INSIDE ====================
    # Check if this authorization has an active visitor entry (status = "inside")
    user_roles = current_user.get("roles", [])
    is_resident = "Residente" in user_roles and not any(r in user_roles for r in ["Administrador", "SuperAdmin", "Guarda", "Supervisor", "RRHH"])
    
    if is_resident:
        # Check for active visitor entries using this authorization
        active_entry = await db.visitor_entries.find_one({
            "authorization_id": auth_id,
            "status": "inside"
        }, {"_id": 0, "id": 1, "visitor_name": 1})
        
        if active_entry:
            raise HTTPException(
                status_code=403, 
                detail="No puedes eliminar esta autorización mientras la persona esté dentro del condominio. Contacta al guarda para registrar su salida primero."
            )
    # ==================== END P0 FIX ====================
    
    await db.visitor_authorizations.update_one(
        {"id": auth_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    await log_audit_event(
        AuditEventType.AUTHORIZATION_DEACTIVATED,
        current_user["id"],
        "visitor_authorizations",
        {"authorization_id": auth_id, "visitor_name": auth.get("visitor_name")},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "Autorización desactivada"}

# ===================== GUARD AUTHORIZATION ENDPOINTS =====================

@api_router.get("/guard/authorizations")
async def get_authorizations_for_guard(
    search: Optional[str] = None,
    include_used: bool = False,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """
    Guard gets list of active authorizations for validation.
    Supports search by visitor name, ID, or vehicle plate.
    By default, only returns PENDING authorizations (not yet used).
    """
    condo_id = current_user.get("condominium_id")
    
    query = {"is_active": True}
    
    # By default, only show pending authorizations (not used yet)
    if not include_used:
        query["status"] = {"$in": ["pending", None]}  # Include None for backwards compatibility
    
    if "SuperAdmin" not in current_user.get("roles", []):
        if condo_id:
            query["condominium_id"] = condo_id
        else:
            return []
    
    authorizations = await db.visitor_authorizations.find(query, {"_id": 0}).to_list(500)
    
    # ==================== FILTER OUT ALREADY CHECKED-IN (for temporary/extended) ====================
    # This handles legacy data where status wasn't set to 'used'
    # Check multiple indicators: checked_in_at, total_visits, or actual entry in visitor_entries
    filtered_authorizations = []
    
    for auth in authorizations:
        auth_type = auth.get("authorization_type", "temporary")
        auth_id = auth.get("id")
        
        # Only filter temporary and extended (permanent/recurring can be reused)
        if auth_type not in ["temporary", "extended"]:
            filtered_authorizations.append(auth)
            continue
        
        # For temporary/extended, ALWAYS check if there's an entry in visitor_entries
        # This is the most reliable indicator that the authorization was used
        entry_exists = await db.visitor_entries.find_one({"authorization_id": auth_id})
        
        # Also check other indicators
        checked_in_at = auth.get("checked_in_at")
        total_visits = auth.get("total_visits", 0)
        
        already_used = entry_exists or checked_in_at or total_visits > 0
        
        if already_used:
            # Fix legacy data: update status to 'used'
            result = await db.visitor_authorizations.update_one(
                {"id": auth_id, "status": {"$in": ["pending", None]}},
                {"$set": {"status": "used"}}
            )
            if result.modified_count > 0:
                logger.info(f"[guard/authorizations] Auto-fixed auth {auth_id[:8]} to status=used (entry_exists={bool(entry_exists)}, checked_in_at={bool(checked_in_at)}, visits={total_visits})")
            
            if not include_used:
                continue  # Skip from results
        
        filtered_authorizations.append(auth)
    
    authorizations = filtered_authorizations
    # ================================================================================================
    
    # Get condominium timezone for validity checks
    condo_timezone = None
    if condo_id:
        condo = await db.condominiums.find_one({"id": condo_id}, {"timezone": 1})
        condo_timezone = condo.get("timezone") if condo else None
    
    # Enrich with validity status
    for auth in authorizations:
        validity = check_authorization_validity(auth, condo_timezone)
        auth["validity_status"] = validity["status"]
        auth["validity_message"] = validity["message"]
        auth["is_currently_valid"] = validity["is_valid"]
        
        # PHASE 3: Add is_visitor_inside flag for frontend
        active_entry = await db.visitor_entries.find_one({
            "authorization_id": auth.get("id"),
            "status": "inside",
            "exit_at": None
        }, {"_id": 0, "id": 1, "entry_at": 1})
        auth["is_visitor_inside"] = active_entry is not None
        if active_entry:
            auth["active_entry_id"] = active_entry.get("id")
            auth["entry_at"] = active_entry.get("entry_at")
    
    # Filter by search if provided
    if search:
        search_lower = search.lower().strip()
        authorizations = [
            a for a in authorizations
            if search_lower in a.get("visitor_name", "").lower() or
               search_lower in (a.get("identification_number") or "").lower() or
               search_lower in (a.get("vehicle_plate") or "").lower() or
               search_lower in (a.get("created_by_name") or "").lower()
        ]
    
    # Sort: valid first, then by name
    authorizations.sort(key=lambda x: (not x.get("is_currently_valid", False), x.get("visitor_name", "").lower()))
    
    return authorizations

@api_router.post("/guard/checkin")
async def fast_checkin(
    checkin_data: FastCheckInRequest,
    request: Request,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """
    Guard registers a visitor check-in (entry).
    - If authorization_id provided: validates authorization and logs entry
    - If no authorization: creates manual entry record
    - For TEMPORARY authorizations: marks as "used" after check-in
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    entry_id = str(uuid.uuid4())
    condo_id = current_user.get("condominium_id")
    
    authorization = None
    resident_id = None
    resident_name = None
    resident_apartment = None
    visitor_name = checkin_data.visitor_name
    is_authorized = False
    auth_type = "manual"
    color_code = "gray"
    
    # ==================== PHASE 1: PREVENT DUPLICATE ENTRIES (AUTHORIZATION) ====================
    # Check if visitor with this authorization is already inside
    if checkin_data.authorization_id:
        existing_inside = await db.visitor_entries.find_one({
            "authorization_id": checkin_data.authorization_id,
            "status": "inside",
            "exit_at": None
        })
        if existing_inside:
            logger.warning(
                f"[check-in] BLOCKED - Visitor already inside with auth {checkin_data.authorization_id[:8]}"
            )
            raise HTTPException(
                status_code=400,
                detail="El visitante ya se encuentra dentro del condominio. Debe registrar su salida antes de un nuevo ingreso."
            )
    
    # ==================== PHASE 2: PREVENT DUPLICATE ENTRIES (MANUAL) ====================
    # For manual entries, check by visitor_name + condominium to prevent duplicates
    if checkin_data.visitor_name and not checkin_data.authorization_id:
        # Normalize visitor name for comparison
        normalized_name = checkin_data.visitor_name.strip().lower()
        
        # Check if same visitor name is already inside this condo (case-insensitive)
        # Use regex for case-insensitive match on visitor_name
        existing_manual = await db.visitor_entries.find_one({
            "condominium_id": condo_id,
            "status": "inside",
            "exit_at": None,
            "authorization_id": None,  # Only manual entries
            "visitor_name": {"$regex": f"^{re.escape(normalized_name)}$", "$options": "i"}
        })
        
        if existing_manual:
            logger.warning(
                f"[check-in] BLOCKED - Manual visitor '{checkin_data.visitor_name}' already inside condo {condo_id[:8]}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe un visitante con el nombre '{checkin_data.visitor_name}' dentro del condominio. Verifique si es la misma persona."
            )
    # ==========================================================================================
    
    # If authorization provided, validate it
    if checkin_data.authorization_id:
        authorization = await db.visitor_authorizations.find_one({
            "id": checkin_data.authorization_id,
            "condominium_id": condo_id
        })
        
        if not authorization:
            raise HTTPException(status_code=404, detail="Autorización no encontrada")
        
        # ==================== BLOCK REUSE OF TEMPORARY/EXTENDED AUTHORIZATIONS ====================
        auth_status = authorization.get("status", "pending")
        auth_type_value = authorization.get("authorization_type", "temporary")
        
        # For TEMPORARY and EXTENDED authorizations, check multiple indicators of usage
        if auth_type_value in ["temporary", "extended"]:
            # Check 1: Status is "used"
            if auth_status == "used":
                raise HTTPException(
                    status_code=409, 
                    detail="Esta autorización ya fue utilizada. No se puede usar nuevamente."
                )
            
            # Check 2: checked_in_at is set
            if authorization.get("checked_in_at"):
                # Fix the status and reject
                await db.visitor_authorizations.update_one(
                    {"id": checkin_data.authorization_id},
                    {"$set": {"status": "used"}}
                )
                raise HTTPException(
                    status_code=409, 
                    detail="Esta autorización ya tiene un registro de entrada. No se puede usar nuevamente."
                )
            
            # Check 3: There's already an entry in visitor_entries with this authorization_id
            existing_entry = await db.visitor_entries.find_one({"authorization_id": checkin_data.authorization_id})
            if existing_entry:
                # Fix the status and reject
                await db.visitor_authorizations.update_one(
                    {"id": checkin_data.authorization_id},
                    {"$set": {"status": "used"}}
                )
                logger.warning(f"[check-in] BLOCKED duplicate check-in for auth {checkin_data.authorization_id[:8]} - entry already exists")
                raise HTTPException(
                    status_code=409, 
                    detail="Ya existe un registro de entrada para esta autorización. No se permite duplicar."
                )
        # ==========================================================================================
        
        # Get condominium timezone for validity check
        condo_timezone = None
        condo = await db.condominiums.find_one({"id": condo_id}, {"timezone": 1})
        condo_timezone = condo.get("timezone") if condo else None
        
        validity = check_authorization_validity(authorization, condo_timezone)
        
        if not validity["is_valid"]:
            # Still allow entry but mark as unauthorized
            is_authorized = False
        else:
            is_authorized = True
        
        visitor_name = authorization.get("visitor_name")
        resident_id = authorization.get("created_by")
        resident_name = authorization.get("created_by_name")
        resident_apartment = authorization.get("resident_apartment")
        auth_type = auth_type_value
        color_code = authorization.get("color_code", "yellow")
    
    # Create entry record
    entry_doc = {
        "id": entry_id,
        "authorization_id": checkin_data.authorization_id,
        "visitor_name": visitor_name or "Visitante Manual",
        "identification_number": checkin_data.identification_number or (authorization.get("identification_number") if authorization else None),
        "vehicle_plate": (checkin_data.vehicle_plate or (authorization.get("vehicle_plate") if authorization else None) or "").upper() or None,
        "destination": checkin_data.destination or resident_apartment,
        "authorization_type": auth_type,
        "color_code": color_code,
        "is_authorized": is_authorized,
        "resident_id": resident_id,
        "resident_name": resident_name,
        "resident_apartment": resident_apartment,
        # New visitor type fields
        "visitor_type": checkin_data.visitor_type or "visitor",
        "company": checkin_data.company,
        "service_type": checkin_data.service_type,
        "authorized_by": checkin_data.authorized_by,
        "estimated_time": checkin_data.estimated_time,
        "entry_at": now_iso,
        "resident_name": resident_name,
        "resident_apartment": resident_apartment,
        "entry_at": now_iso,
        "entry_by": current_user["id"],
        "entry_by_name": current_user.get("full_name", "Guardia"),
        "entry_notes": checkin_data.notes,
        "exit_at": None,
        "exit_by": None,
        "exit_by_name": None,
        "exit_notes": None,
        "status": "inside",
        "condominium_id": condo_id,
        "created_at": now_iso
    }
    
    await db.visitor_entries.insert_one(entry_doc)
    
    # Update authorization stats and status
    if authorization:
        auth_type_value = authorization.get("authorization_type", "temporary")
        
        # DEBUG LOG
        logger.info(f"[check-in] Auth ID: {checkin_data.authorization_id[:8]}, Type: {auth_type_value}, Will mark as used: {auth_type_value in ['temporary', 'extended']}")
        
        update_data = {
            "$inc": {"total_visits": 1},
            "$set": {
                "last_visit": now_iso,
                "checked_in_at": now_iso,
                "checked_in_by": current_user["id"],
                "checked_in_by_name": current_user.get("full_name", "Guardia"),
                "last_entry_date": now.strftime("%Y-%m-%d")  # Track last entry date
            }
        }
        
        # For TEMPORARY and EXTENDED authorizations, mark as "used" after check-in
        # PERMANENT and RECURRING authorizations stay active (can be used multiple times)
        if auth_type_value in ["temporary", "extended"]:
            update_data["$set"]["status"] = "used"
            logger.info(f"[check-in] Setting status=used for auth {checkin_data.authorization_id[:8]}")
        
        result = await db.visitor_authorizations.update_one(
            {"id": checkin_data.authorization_id},
            update_data
        )
        logger.info(f"[check-in] Update result: matched={result.matched_count}, modified={result.modified_count}")
        
        # VERIFICATION: Check if update actually worked
        if auth_type_value in ["temporary", "extended"]:
            verification = await db.visitor_authorizations.find_one(
                {"id": checkin_data.authorization_id},
                {"_id": 0, "status": 1, "authorization_type": 1, "visitor_name": 1}
            )
            logger.info(f"[check-in] VERIFICATION after update: {verification}")
    
    # Create notification AND send push to resident
    if resident_id:
        await create_and_send_notification(
            user_id=resident_id,
            condominium_id=condo_id,
            notification_type="visitor_arrival",
            title="🚪 Tu visitante ha llegado",
            message=f"{visitor_name} ha ingresado al condominio",
            data={
                "entry_id": entry_id,
                "visitor_name": visitor_name,
                "entry_at": now_iso,
                "guard_name": current_user.get("full_name")
            },
            send_push=False,  # Disable old push, use targeted instead
            url="/resident?tab=history"
        )
        
        # PHASE 1: Send targeted push notification to resident owner
        await send_targeted_push_notification(
            condominium_id=condo_id,
            title="🚪 Tu visitante ha llegado",
            body=f"{visitor_name} ha ingresado al condominio",
            target_user_ids=[resident_id],
            exclude_user_ids=[current_user["id"]],
            data={
                "type": "visitor_arrival",
                "entry_id": entry_id,
                "visitor_name": visitor_name,
                "entry_at": now_iso,
                "guard_name": current_user.get("full_name"),
                "url": "/resident?tab=history"
            },
            tag=f"checkin-{entry_id[:8]}"
        )
        
        await log_audit_event(
            AuditEventType.VISITOR_ARRIVAL_NOTIFIED,
            current_user["id"],
            "visitor_notifications",
            {"resident_id": resident_id, "visitor_name": visitor_name},
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "unknown")
        )
    
    await log_audit_event(
        AuditEventType.VISITOR_CHECKIN,
        current_user["id"],
        "visitor_entries",
        {
            "entry_id": entry_id,
            "visitor_name": visitor_name,
            "is_authorized": is_authorized,
            "authorization_id": checkin_data.authorization_id
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    entry_doc.pop("_id", None)
    return {
        "success": True,
        "entry": entry_doc,
        "is_authorized": is_authorized,
        "message": "Entrada registrada" if is_authorized else "Entrada registrada (sin autorización válida)",
        "authorization_marked_used": authorization is not None and authorization.get("authorization_type") in ["temporary", "extended"]
    }

@api_router.get("/guard/entries-today")
async def get_entries_today(
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """
    Get all visitor entries for today.
    Returns list of visitors who have checked in today, for guard reference.
    """
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        return []
    
    # Get start of today in UTC
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    
    entries = await db.visitor_entries.find(
        {
            "condominium_id": condo_id,
            "entry_at": {"$gte": today_start}
        },
        {"_id": 0}
    ).sort("entry_at", -1).to_list(100)
    
    return entries

@api_router.post("/guard/checkout/{entry_id}")
async def fast_checkout(
    entry_id: str,
    checkout_data: FastCheckOutRequest,
    request: Request,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """
    Guard registers a visitor check-out (exit).
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    condo_id = current_user.get("condominium_id")
    
    # Find entry
    entry = await db.visitor_entries.find_one({
        "id": entry_id,
        "status": "inside"
    })
    
    if not entry:
        raise HTTPException(status_code=404, detail="Registro de entrada no encontrado o ya salió")
    
    # Multi-tenant check
    if entry.get("condominium_id") != condo_id and "SuperAdmin" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="No tienes acceso a este registro")
    
    # Calculate duration
    entry_at = entry.get("entry_at")
    duration_minutes = None
    if entry_at:
        try:
            entry_time = datetime.fromisoformat(entry_at.replace('Z', '+00:00'))
            duration_minutes = int((now - entry_time).total_seconds() / 60)
        except ValueError:
            pass
    
    # Update entry
    await db.visitor_entries.update_one(
        {"id": entry_id},
        {"$set": {
            "exit_at": now_iso,
            "exit_by": current_user["id"],
            "exit_by_name": current_user.get("full_name", "Guardia"),
            "exit_notes": checkout_data.notes,
            "status": "completed",
            "duration_minutes": duration_minutes
        }}
    )
    
    # Create notification AND send push to resident (optional for exit)
    resident_id = entry.get("resident_id")
    if resident_id:
        # Format duration for display
        duration_text = ""
        if duration_minutes:
            hours = duration_minutes // 60
            mins = duration_minutes % 60
            if hours > 0:
                duration_text = f" (duración: {hours}h {mins}m)"
            else:
                duration_text = f" (duración: {mins} min)"
        
        await create_and_send_notification(
            user_id=resident_id,
            condominium_id=condo_id,
            notification_type="visitor_exit",
            title="👋 Tu visitante ha salido",
            message=f"{entry.get('visitor_name')} ha salido del condominio{duration_text}",
            data={
                "entry_id": entry_id,
                "visitor_name": entry.get("visitor_name"),
                "exit_at": now_iso,
                "duration_minutes": duration_minutes,
                "guard_name": current_user.get("full_name")
            },
            send_push=False,  # Disable old push, use targeted instead
            url="/resident?tab=history"
        )
        
        # PHASE 2: Send targeted push notification to resident owner
        await send_targeted_push_notification(
            condominium_id=condo_id,
            title="👋 Tu visitante ha salido",
            body=f"{entry.get('visitor_name')} ha salido del condominio{duration_text}",
            target_user_ids=[resident_id],
            exclude_user_ids=[current_user["id"]],
            data={
                "type": "visitor_exit",
                "entry_id": entry_id,
                "visitor_name": entry.get("visitor_name"),
                "exit_at": now_iso,
                "duration_minutes": duration_minutes,
                "guard_name": current_user.get("full_name"),
                "url": "/resident?tab=history"
            },
            tag=f"checkout-{entry_id[:8]}"
        )
        
        await log_audit_event(
            AuditEventType.VISITOR_EXIT_NOTIFIED,
            current_user["id"],
            "visitor_notifications",
            {"resident_id": resident_id, "visitor_name": entry.get("visitor_name")},
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "unknown")
        )
    
    # Save to guard_history for audit
    guard = await db.guards.find_one({"user_id": current_user["id"]})
    history_entry = {
        "id": str(uuid.uuid4()),
        "type": "visitor_checkout",
        "guard_id": guard["id"] if guard else None,
        "guard_user_id": current_user["id"],
        "guard_name": current_user.get("full_name"),
        "condominium_id": condo_id,
        "entry_id": entry_id,
        "visitor_name": entry.get("visitor_name"),
        "resident_name": entry.get("resident_name"),
        "entry_at": entry_at,
        "exit_at": now_iso,
        "duration_minutes": duration_minutes,
        "timestamp": now_iso
    }
    await db.guard_history.insert_one(history_entry)
    
    await log_audit_event(
        AuditEventType.VISITOR_CHECKOUT,
        current_user["id"],
        "visitor_entries",
        {
            "entry_id": entry_id,
            "visitor_name": entry.get("visitor_name"),
            "duration_minutes": duration_minutes
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "success": True,
        "message": "Salida registrada",
        "exit_at": now_iso,
        "duration_minutes": duration_minutes
    }

@api_router.get("/guard/visitors-inside")
async def get_visitors_inside(
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """Get all visitors currently inside the condominium"""
    condo_id = current_user.get("condominium_id")
    
    query = {"status": "inside"}
    if "SuperAdmin" not in current_user.get("roles", []):
        if condo_id:
            query["condominium_id"] = condo_id
        else:
            return []
    
    entries = await db.visitor_entries.find(query, {"_id": 0}).sort("entry_at", -1).to_list(200)
    return entries

@api_router.get("/guard/visits-summary")
async def get_visits_summary(
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """
    Get complete visits summary for Guard 'Visitas' tab (READ-ONLY view)
    Returns: pending authorizations, visitors inside, today's exits
    """
    condo_id = current_user.get("condominium_id")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    base_query = {}
    if "SuperAdmin" not in current_user.get("roles", []):
        if condo_id:
            base_query["condominium_id"] = condo_id
        else:
            return {"pending": [], "inside": [], "exits": []}
    
    # 1. Get pending authorizations for today (not yet used)
    pending_query = {
        **base_query,
        "is_active": True,
        "status": "pending"
    }
    pending_auths = await db.visitor_authorizations.find(pending_query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    # Get condominium timezone for validity checks
    condo_timezone = None
    if condo_id:
        condo = await db.condominiums.find_one({"id": condo_id}, {"timezone": 1})
        condo_timezone = condo.get("timezone") if condo else None
    
    # Filter and enrich pending authorizations with validity
    enriched_pending = []
    for auth in pending_auths:
        validity = check_authorization_validity(auth, condo_timezone)
        if validity.get("is_valid"):
            auth["validity_status"] = validity["status"]
            auth["validity_message"] = validity["message"]
            auth["is_currently_valid"] = True
            enriched_pending.append(auth)
    
    # 2. Get visitors currently inside
    inside_query = {
        **base_query,
        "status": "inside"
    }
    inside_entries = await db.visitor_entries.find(inside_query, {"_id": 0}).sort("entry_at", -1).to_list(200)
    
    # 3. Get today's exits (completed visits)
    exits_query = {
        **base_query,
        "status": {"$in": ["exited", "completed"]},  # Support both status values
        "exit_at": {"$gte": f"{today}T00:00:00"}
    }
    today_exits = await db.visitor_entries.find(exits_query, {"_id": 0}).sort("exit_at", -1).to_list(100)
    
    return {
        "pending": enriched_pending,
        "inside": inside_entries,
        "exits": today_exits
    }

# ===================== RESIDENT NOTIFICATIONS =====================

@api_router.get("/resident/visitor-notifications")
async def get_visitor_notifications(
    unread_only: bool = False,
    current_user = Depends(get_current_user)
):
    """Resident gets their visitor arrival/exit notifications"""
    query = {
        "user_id": current_user["id"],
        "type": {"$in": ["visitor_arrival", "visitor_exit"]}
    }
    
    if unread_only:
        query["read"] = False
    
    notifications = await db.resident_notifications.find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    return notifications

@api_router.put("/resident/visitor-notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user = Depends(get_current_user)
):
    """Mark a notification as read"""
    result = await db.resident_notifications.update_one(
        {"id": notification_id, "user_id": current_user["id"]},
        {"$set": {"read": True}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    
    return {"message": "Notificación marcada como leída"}

@api_router.put("/resident/visitor-notifications/read-all")
async def mark_all_notifications_read(
    current_user = Depends(get_current_user)
):
    """Mark all visitor notifications as read"""
    result = await db.resident_notifications.update_many(
        {
            "user_id": current_user["id"],
            "type": {"$in": ["visitor_arrival", "visitor_exit"]},
            "read": False
        },
        {"$set": {"read": True}}
    )
    
    return {"message": f"{result.modified_count} notificaciones marcadas como leídas", "count": result.modified_count}


@api_router.get("/resident/visitor-notifications/unread-count")
async def get_resident_unread_notification_count(
    current_user = Depends(get_current_user)
):
    """Get count of unread visitor notifications for resident"""
    count = await db.resident_notifications.count_documents({
        "user_id": current_user["id"],
        "type": {"$in": ["visitor_arrival", "visitor_exit"]},
        "read": False
    })
    
    return {"count": count}


# ============================================
# RESIDENT VISIT HISTORY (Advanced Module)
# ============================================

@api_router.get("/resident/visit-history")
async def get_resident_visit_history(
    filter_period: Optional[str] = None,  # today, 7days, 30days, custom
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    visitor_type: Optional[str] = None,  # visitor, delivery, maintenance, etc.
    status: Optional[str] = None,  # inside, completed
    search: Optional[str] = None,  # Search by name, document, plate
    page: int = 1,
    page_size: int = 20,
    current_user = Depends(get_current_user)
):
    """
    Advanced visit history for residents.
    Returns paginated list of visitor entries related to the resident's house.
    Enforces tenant isolation (validates condominium_id + resident_id).
    """
    user_id = current_user["id"]
    condo_id = current_user.get("condominium_id")
    
    if not condo_id:
        raise HTTPException(status_code=403, detail="Usuario no asignado a un condominio")
    
    # Base query: Only visits related to this resident's authorizations
    # Find all authorization IDs created by this resident
    resident_auth_ids = await db.visitor_authorizations.distinct(
        "id",
        {"created_by": user_id, "condominium_id": condo_id}
    )
    
    # Also include legacy visitors registered by this resident
    legacy_visitor_ids = await db.visitors.distinct(
        "id",
        {"created_by": user_id, "condominium_id": condo_id}
    )
    
    # Build query for visitor_entries
    query = {
        "condominium_id": condo_id,
        "$or": [
            {"authorization_id": {"$in": resident_auth_ids}},
            {"visitor_id": {"$in": legacy_visitor_ids}},
            {"resident_id": user_id}
        ]
    }
    
    # Date filtering
    now = datetime.now(timezone.utc)
    if filter_period == "today":
        today_str = now.strftime("%Y-%m-%d")
        query["entry_at"] = {"$gte": f"{today_str}T00:00:00"}
    elif filter_period == "7days":
        seven_days_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        query["entry_at"] = {"$gte": f"{seven_days_ago}T00:00:00"}
    elif filter_period == "30days":
        thirty_days_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        query["entry_at"] = {"$gte": f"{thirty_days_ago}T00:00:00"}
    elif filter_period == "custom" and (date_from or date_to):
        date_query = {}
        if date_from:
            date_query["$gte"] = f"{date_from}T00:00:00"
        if date_to:
            date_query["$lte"] = f"{date_to}T23:59:59"
        if date_query:
            query["entry_at"] = date_query
    
    # Visitor type filter
    if visitor_type:
        query["visitor_type"] = visitor_type
    
    # Status filter
    if status:
        query["status"] = status
    
    # Search filter (name, document, plate)
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        query["$and"] = query.get("$and", []) + [{
            "$or": [
                {"visitor_name": search_regex},
                {"document_number": search_regex},
                {"vehicle_plate": search_regex}
            ]
        }]
    
    # Get total count for pagination
    total_count = await db.visitor_entries.count_documents(query)
    
    # Calculate pagination
    skip = (page - 1) * page_size
    total_pages = (total_count + page_size - 1) // page_size
    
    # Fetch entries with pagination
    entries = await db.visitor_entries.find(
        query, 
        {"_id": 0}
    ).sort("entry_at", -1).skip(skip).limit(page_size).to_list(page_size)
    
    # Enrich entries with additional data
    enriched_entries = []
    for entry in entries:
        # Calculate duration if both entry and exit exist
        duration_minutes = None
        if entry.get("entry_at") and entry.get("exit_at"):
            try:
                entry_time = datetime.fromisoformat(entry["entry_at"].replace("Z", "+00:00"))
                exit_time = datetime.fromisoformat(entry["exit_at"].replace("Z", "+00:00"))
                duration_minutes = int((exit_time - entry_time).total_seconds() / 60)
            except:
                pass
        
        # Get authorization details if available
        auth_details = None
        if entry.get("authorization_id"):
            auth = await db.visitor_authorizations.find_one(
                {"id": entry["authorization_id"]},
                {"_id": 0, "authorization_type": 1, "visitor_type": 1}
            )
            if auth:
                auth_details = auth
        
        enriched_entry = {
            **entry,
            "duration_minutes": duration_minutes,
            "authorization_details": auth_details,
            # Determine display type
            "display_type": entry.get("visitor_type") or (auth_details.get("visitor_type") if auth_details else "visitor")
        }
        enriched_entries.append(enriched_entry)
    
    # Get count of visitors currently inside (for badge)
    inside_count = await db.visitor_entries.count_documents({
        **{k: v for k, v in query.items() if k not in ["entry_at", "status"]},
        "status": "inside"
    })
    
    return {
        "entries": enriched_entries,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        },
        "summary": {
            "total_visits": total_count,
            "visitors_inside": inside_count
        }
    }


@api_router.get("/resident/visit-history/export")
async def export_resident_visit_history(
    filter_period: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    visitor_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Export visit history data for PDF generation.
    Returns all matching entries (up to 500) with resident/condo info.
    """
    user_id = current_user["id"]
    condo_id = current_user.get("condominium_id")
    
    if not condo_id:
        raise HTTPException(status_code=403, detail="Usuario no asignado a un condominio")
    
    # Get resident and condo info
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "full_name": 1, "role_data": 1})
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "name": 1})
    
    # Get apartment info from role_data
    apartment = user.get("role_data", {}).get("apartment_number", "N/A") if user else "N/A"
    
    # Build query (same as main endpoint but without pagination)
    resident_auth_ids = await db.visitor_authorizations.distinct(
        "id",
        {"created_by": user_id, "condominium_id": condo_id}
    )
    
    legacy_visitor_ids = await db.visitors.distinct(
        "id",
        {"created_by": user_id, "condominium_id": condo_id}
    )
    
    query = {
        "condominium_id": condo_id,
        "$or": [
            {"authorization_id": {"$in": resident_auth_ids}},
            {"visitor_id": {"$in": legacy_visitor_ids}},
            {"resident_id": user_id}
        ]
    }
    
    # Apply filters
    now = datetime.now(timezone.utc)
    if filter_period == "today":
        query["entry_at"] = {"$gte": now.strftime("%Y-%m-%d") + "T00:00:00"}
    elif filter_period == "7days":
        query["entry_at"] = {"$gte": (now - timedelta(days=7)).strftime("%Y-%m-%d") + "T00:00:00"}
    elif filter_period == "30days":
        query["entry_at"] = {"$gte": (now - timedelta(days=30)).strftime("%Y-%m-%d") + "T00:00:00"}
    elif filter_period == "custom" and (date_from or date_to):
        date_query = {}
        if date_from:
            date_query["$gte"] = f"{date_from}T00:00:00"
        if date_to:
            date_query["$lte"] = f"{date_to}T23:59:59"
        if date_query:
            query["entry_at"] = date_query
    
    if visitor_type:
        query["visitor_type"] = visitor_type
    if status:
        query["status"] = status
    
    # Fetch entries (limit 500 for export)
    entries = await db.visitor_entries.find(query, {"_id": 0}).sort("entry_at", -1).to_list(500)
    
    # Enrich with duration
    for entry in entries:
        if entry.get("entry_at") and entry.get("exit_at"):
            try:
                entry_time = datetime.fromisoformat(entry["entry_at"].replace("Z", "+00:00"))
                exit_time = datetime.fromisoformat(entry["exit_at"].replace("Z", "+00:00"))
                entry["duration_minutes"] = int((exit_time - entry_time).total_seconds() / 60)
            except:
                entry["duration_minutes"] = None
        else:
            entry["duration_minutes"] = None
    
    return {
        "resident_name": user.get("full_name", "N/A") if user else "N/A",
        "apartment": apartment,
        "condominium_name": condo.get("name", "N/A") if condo else "N/A",
        "export_date": now.isoformat(),
        "filter_applied": {
            "period": filter_period,
            "date_from": date_from,
            "date_to": date_to,
            "visitor_type": visitor_type,
            "status": status
        },
        "total_entries": len(entries),
        "entries": entries
    }


# ============================================
# GUARD/ADMIN NOTIFICATIONS ENDPOINTS
# ============================================

@api_router.get("/notifications")
async def get_user_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user = Depends(get_current_user)
):
    """
    Get notifications for current user (Admin, Guard, or Supervisor).
    Returns notifications from guard_notifications collection.
    """
    user_id = current_user["id"]
    roles = current_user.get("roles", [])
    condo_id = current_user.get("condominium_id")
    
    # Build query based on user role
    query = {}
    
    if "Guarda" in roles:
        # Guards see notifications addressed to them specifically
        query["$or"] = [
            {"guard_user_id": user_id},
            {"guard_id": user_id}
        ]
    elif "Administrador" in roles or "Supervisor" in roles:
        # Admins/Supervisors see all notifications for their condo
        if condo_id:
            query["condominium_id"] = condo_id
    elif "SuperAdmin" in roles:
        # SuperAdmin sees all
        pass
    else:
        # Other roles - return empty
        return []
    
    if unread_only:
        query["read"] = False
    
    notifications = await db.guard_notifications.find(
        query, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return notifications

@api_router.get("/notifications/unread-count")
async def get_unread_notification_count(
    current_user = Depends(get_current_user)
):
    """Get count of unread notifications for the current user"""
    user_id = current_user["id"]
    roles = current_user.get("roles", [])
    condo_id = current_user.get("condominium_id")
    
    # Build query based on user role
    query = {"read": False}
    
    if "Guarda" in roles:
        query["$or"] = [
            {"guard_user_id": user_id},
            {"guard_id": user_id}
        ]
    elif "Administrador" in roles or "Supervisor" in roles:
        if condo_id:
            query["condominium_id"] = condo_id
    elif "SuperAdmin" in roles:
        pass
    else:
        return {"count": 0}
    
    count = await db.guard_notifications.count_documents(query)
    return {"count": count}

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    current_user = Depends(get_current_user)
):
    """Mark a specific notification as read"""
    user_id = current_user["id"]
    roles = current_user.get("roles", [])
    condo_id = current_user.get("condominium_id")
    
    # Build query to ensure user can only mark their own notifications
    query = {"id": notification_id}
    
    if "Guarda" in roles:
        query["$or"] = [
            {"guard_user_id": user_id},
            {"guard_id": user_id}
        ]
    elif "Administrador" in roles or "Supervisor" in roles:
        if condo_id:
            query["condominium_id"] = condo_id
    elif "SuperAdmin" not in roles:
        raise HTTPException(status_code=403, detail="No tienes permiso")
    
    result = await db.guard_notifications.update_one(
        query,
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    
    return {"message": "Notificación marcada como leída"}

@api_router.put("/notifications/mark-all-read")
async def mark_all_guard_notifications_read(
    current_user = Depends(get_current_user)
):
    """Mark all notifications as read for the current user"""
    user_id = current_user["id"]
    roles = current_user.get("roles", [])
    condo_id = current_user.get("condominium_id")
    
    # Build query based on user role
    query = {"read": False}
    
    if "Guarda" in roles:
        query["$or"] = [
            {"guard_user_id": user_id},
            {"guard_id": user_id}
        ]
    elif "Administrador" in roles or "Supervisor" in roles:
        if condo_id:
            query["condominium_id"] = condo_id
    elif "SuperAdmin" not in roles:
        raise HTTPException(status_code=403, detail="No tienes permiso")
    
    result = await db.guard_notifications.update_many(
        query,
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {
        "message": f"{result.modified_count} notificaciones marcadas como leídas",
        "count": result.modified_count
    }



# Endpoint for Guards to write to their logbook
@api_router.get("/security/logbook")
async def get_guard_logbook(current_user = Depends(require_role_and_module("Administrador", "Supervisor", "Guarda", module="security"))):
    """Get logbook entries for guards - scoped by condominium"""
    # Use tenant_filter for multi-tenant scoping
    query = tenant_filter(current_user)
    
    logs = await db.access_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(50)
    
    # Format as logbook entries
    logbook_entries = []
    for log in logs:
        logbook_entries.append({
            "id": log.get("id"),
            "event_type": log.get("access_type", "entry"),
            "timestamp": log.get("timestamp"),
            "details": {
                "person": log.get("person_name"),
                "notes": log.get("notes"),
                "location": log.get("location")
            }
        })
    
    return logbook_entries


# ==================== GUARD MY SHIFT ====================
@api_router.get("/guard/my-shift")
async def get_guard_my_shift(current_user = Depends(require_role("Guarda", "Administrador", "Supervisor"))):
    """
    Get guard's current and upcoming shift information.
    Used for the "Mi Turno" tab in Guard UI.
    Includes can_clock_in flag and message for UI validation.
    
    A shift is CURRENT if: start_time <= now <= end_time AND status in [scheduled, in_progress]
    A shift is UPCOMING if: start_time > now AND status = scheduled
    Early clock-in allowed: 15 minutes before shift start
    """
    guard = await db.guards.find_one({"user_id": current_user["id"]})
    if not guard:
        logger.warning(f"[my-shift] No guard record found for user_id={current_user['id']}")
        return {
            "has_guard_record": False,
            "current_shift": None,
            "next_shift": None,
            "can_clock_in": False,
            "clock_in_message": "No tienes registro como empleado"
        }
    
    condo_id = current_user.get("condominium_id")
    guard_condo_id = guard.get("condominium_id")
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    today = now.date().isoformat()
    
    logger.info(f"[my-shift] Checking shifts for guard_id={guard['id']}, user_condo={condo_id}, guard_condo={guard_condo_id}, now={now_iso}")
    
    # Check current clock status
    today_logs = await db.hr_clock_logs.find({
        "employee_id": guard["id"],
        "date": today
    }).sort("timestamp", -1).to_list(10)
    
    is_clocked_in = False
    if today_logs:
        is_clocked_in = today_logs[0]["type"] == "IN"
    
    # Use guard's condominium_id if user's is not set (for consistency)
    effective_condo_id = condo_id or guard_condo_id
    
    # Find current active shift (now is between start and end time)
    # Status must be scheduled (not started) or in_progress (started but not ended)
    current_shift_query = {
        "guard_id": guard["id"],
        "status": {"$in": ["scheduled", "in_progress"]},
        "start_time": {"$lte": now_iso},
        "end_time": {"$gte": now_iso}
    }
    # Only filter by condo if we have one
    if effective_condo_id:
        current_shift_query["condominium_id"] = effective_condo_id
    
    current_shift = await db.shifts.find_one(current_shift_query, {"_id": 0})
    
    if not current_shift:
        # Log why no shift was found - check all shifts for this guard
        all_guard_shifts = await db.shifts.find({
            "guard_id": guard["id"]
        }, {"_id": 0}).to_list(20)
        
        if all_guard_shifts:
            logger.info(f"[my-shift] Guard has {len(all_guard_shifts)} total shifts. Checking why none match...")
            for s in all_guard_shifts[:5]:  # Log first 5
                match_reasons = []
                if s.get("status") not in ["scheduled", "in_progress"]:
                    match_reasons.append(f"status={s.get('status')} (need scheduled/in_progress)")
                if s.get("start_time", "") > now_iso:
                    match_reasons.append(f"start_time={s.get('start_time')} > now")
                if s.get("end_time", "") < now_iso:
                    match_reasons.append(f"end_time={s.get('end_time')} < now")
                if effective_condo_id and s.get("condominium_id") != effective_condo_id:
                    match_reasons.append(f"condo mismatch: shift={s.get('condominium_id')} != user={effective_condo_id}")
                logger.info(f"[my-shift] Shift {s.get('id')[:8]}... rejected: {', '.join(match_reasons) or 'unknown'}")
        else:
            logger.info("[my-shift] Guard has NO shifts assigned at all")
    
    # Find next upcoming shift (start_time > now)
    next_shift_query = {
        "guard_id": guard["id"],
        "status": "scheduled",
        "start_time": {"$gt": now_iso}
    }
    if effective_condo_id:
        next_shift_query["condominium_id"] = effective_condo_id
    
    next_shift = await db.shifts.find_one(
        next_shift_query, 
        {"_id": 0},
        sort=[("start_time", 1)]
    )
    
    # Determine if guard can clock in
    can_clock_in = False
    clock_in_message = None
    
    if is_clocked_in:
        can_clock_in = False  # Already clocked in
        clock_in_message = "Ya tienes entrada registrada"
    elif current_shift:
        can_clock_in = True
        clock_in_message = None
        logger.info(f"[my-shift] Guard CAN clock in - current shift found: {current_shift.get('id')}")
    elif next_shift:
        # Check if within 15 minute early window
        shift_start_str = next_shift["start_time"]
        # Ensure timezone-aware datetime
        if 'Z' in shift_start_str:
            shift_start = datetime.fromisoformat(shift_start_str.replace('Z', '+00:00'))
        elif '+' in shift_start_str or shift_start_str.endswith('-00:00'):
            shift_start = datetime.fromisoformat(shift_start_str)
        else:
            # Assume UTC if no timezone info
            shift_start = datetime.fromisoformat(shift_start_str).replace(tzinfo=timezone.utc)
        
        minutes_until = int((shift_start - now).total_seconds() / 60)
        if minutes_until <= 15:
            can_clock_in = True
            clock_in_message = f"Tu turno comienza en {minutes_until} minutos"
            logger.info("[my-shift] Guard CAN clock in - within 15 min early window")
        else:
            can_clock_in = False
            if minutes_until > 60:
                clock_in_message = f"Tu turno comienza en {minutes_until // 60}h {minutes_until % 60}min. Puedes fichar 15 min antes."
            else:
                clock_in_message = f"Tu turno comienza en {minutes_until} minutos. Puedes fichar 15 min antes."
            logger.info(f"[my-shift] Guard CANNOT clock in - next shift in {minutes_until} min")
    else:
        can_clock_in = False
        clock_in_message = "No tienes un turno asignado para hoy"
        logger.info("[my-shift] Guard CANNOT clock in - no shifts found")
    
    return {
        "has_guard_record": True,
        "guard_id": guard["id"],
        "guard_name": guard.get("user_name") or guard.get("name") or "Sin nombre",
        "current_shift": current_shift,
        "next_shift": next_shift,
        "is_clocked_in": is_clocked_in,
        "can_clock_in": can_clock_in,
        "clock_in_message": clock_in_message
    }

@api_router.get("/guard/my-absences")
async def get_guard_my_absences(current_user = Depends(require_role("Guarda"))):
    """
    Get guard's own absence requests (read-only).
    Guards can only see their own absences.
    """
    guard = await db.guards.find_one({"user_id": current_user["id"]})
    if not guard:
        return []
    
    condo_id = current_user.get("condominium_id")
    
    absences = await db.hr_absences.find({
        "employee_id": guard["id"],
        "condominium_id": condo_id
    }, {"_id": 0}).sort("created_at", -1).to_list(50)
    
    return absences


# ==================== GUARD HISTORY ====================
@api_router.get("/guard/history")
async def get_guard_history(
    history_type: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """
    Get comprehensive guard action history.
    Includes: alerts resolved, visits completed, clock events, completed shifts.
    Single source of truth for Guard UI History tab.
    """
    condo_id = current_user.get("condominium_id")
    guard = None
    guard_id = None
    
    # Get guard record if user is a guard
    if "Guarda" in current_user.get("roles", []):
        guard = await db.guards.find_one({"user_id": current_user["id"]})
        if guard:
            guard_id = guard["id"]
    
    # Build base query with multi-tenant filtering
    base_query = {}
    if "SuperAdmin" not in current_user.get("roles", []) and condo_id:
        base_query["condominium_id"] = condo_id
    
    # Guards see only their own history
    if guard_id and "Administrador" not in current_user.get("roles", []):
        base_query["guard_id"] = guard_id
    
    # Filter by type if specified
    valid_types = ["alert_resolved", "visit_completed", "clock_in", "clock_out", "shift_completed"]
    if history_type and history_type in valid_types:
        base_query["type"] = history_type
    
    # Get guard_history entries (legacy)
    history_entries = await db.guard_history.find(base_query, {"_id": 0}).sort("timestamp", -1).to_list(100)
    
    # ==================== VISITOR ENTRIES (Check-ins/Check-outs) ====================
    # Guards see ALL entries in their condominium (useful for shift handoff)
    visitor_query = {}
    if condo_id:
        visitor_query["condominium_id"] = condo_id
    
    visitor_entries = await db.visitor_entries.find(visitor_query, {"_id": 0}).sort("entry_at", -1).to_list(50)
    
    for entry in visitor_entries:
        # Add check-in event
        history_entries.append({
            "id": f"{entry.get('id')}_in",
            "type": "visit_entry",
            "guard_id": guard_id,
            "guard_name": entry.get("entry_by_name"),
            "condominium_id": entry.get("condominium_id"),
            "timestamp": entry.get("entry_at"),
            "visitor_name": entry.get("visitor_name"),
            "destination": entry.get("destination") or entry.get("resident_apartment"),
            "vehicle_plate": entry.get("vehicle_plate"),
            "is_authorized": entry.get("is_authorized", False)
        })
        
        # Add check-out event if exists
        if entry.get("exit_at"):
            history_entries.append({
                "id": f"{entry.get('id')}_out",
                "type": "visit_exit",
                "guard_id": guard_id,
                "guard_name": entry.get("exit_by_name"),
                "condominium_id": entry.get("condominium_id"),
                "timestamp": entry.get("exit_at"),
                "visitor_name": entry.get("visitor_name"),
                "destination": entry.get("destination") or entry.get("resident_apartment")
            })
    
    # ==================== RESOLVED PANIC ALERTS ====================
    # Guards see ALL resolved alerts in their condominium
    alert_query = {"status": "resolved"}
    if condo_id:
        alert_query["condominium_id"] = condo_id
    
    resolved_alerts = await db.panic_events.find(alert_query, {"_id": 0}).sort("resolved_at", -1).to_list(30)
    
    for alert in resolved_alerts:
        history_entries.append({
            "id": alert.get("id"),
            "type": "alert_resolved",
            "guard_id": guard_id,
            "guard_name": alert.get("resolved_by_name"),
            "condominium_id": alert.get("condominium_id"),
            "timestamp": alert.get("resolved_at") or alert.get("created_at"),
            "alert_type": alert.get("panic_type"),
            "user_name": alert.get("user_name"),
            "location": alert.get("location"),
            "resolution_notes": alert.get("resolution_notes")
        })
    
    # ==================== CLOCK LOGS ====================
    clock_query = {}
    if condo_id:
        clock_query["condominium_id"] = condo_id
    if guard_id and "Administrador" not in current_user.get("roles", []):
        clock_query["employee_id"] = guard_id
    
    clock_logs = await db.hr_clock_logs.find(clock_query, {"_id": 0}).sort("timestamp", -1).to_list(50)
    
    for log in clock_logs:
        history_entries.append({
            "id": log.get("id"),
            "type": f"clock_{log['type'].lower()}",
            "guard_id": log.get("employee_id"),
            "guard_name": log.get("employee_name"),
            "condominium_id": log.get("condominium_id"),
            "timestamp": log.get("timestamp"),
            "date": log.get("date")
        })
    
    # ==================== COMPLETED SHIFTS ====================
    shift_query = {"status": "completed"}
    if condo_id:
        shift_query["condominium_id"] = condo_id
    if guard_id and "Administrador" not in current_user.get("roles", []):
        shift_query["guard_id"] = guard_id
    
    completed_shifts = await db.shifts.find(shift_query, {"_id": 0}).sort("end_time", -1).to_list(20)
    
    for shift in completed_shifts:
        history_entries.append({
            "id": shift.get("id"),
            "type": "shift_completed",
            "guard_id": shift.get("guard_id"),
            "guard_name": shift.get("guard_name"),
            "condominium_id": shift.get("condominium_id"),
            "timestamp": shift.get("end_time"),
            "shift_start": shift.get("start_time"),
            "shift_end": shift.get("end_time"),
            "location": shift.get("location")
        })
    
    # Sort all entries by timestamp (newest first)
    history_entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return history_entries[:100]



@api_router.get("/security/active-guards")
async def get_active_guards(current_user = Depends(require_role("Administrador", "Supervisor"))):
    """Get active guards - scoped by condominium"""
    query = {"status": "active"}
    if "SuperAdmin" not in current_user.get("roles", []):
        condo_id = current_user.get("condominium_id")
        if condo_id:
            query["condominium_id"] = condo_id
    guards = await db.guards.find(query, {"_id": 0}).to_list(100)
    return guards

@api_router.get("/security/dashboard-stats")
async def get_security_stats(current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))):
    """Security stats - scoped by condominium"""
    condo_filter = {}
    if "SuperAdmin" not in current_user.get("roles", []):
        condo_id = current_user.get("condominium_id")
        if condo_id:
            condo_filter["condominium_id"] = condo_id
    
    active_panic = await db.panic_events.count_documents({**condo_filter, "status": "active"})
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    today_access = await db.access_logs.count_documents({**condo_filter, "timestamp": {"$gte": today_start}})
    active_guards = await db.guards.count_documents({**condo_filter, "status": "active"})
    total_events = await db.panic_events.count_documents(condo_filter)
    
    return {
        "active_alerts": active_panic,
        "today_accesses": today_access,
        "active_guards": active_guards,
        "total_events": total_events
    }

# ==================== HR MODULE ====================
@api_router.post("/hr/guards")
async def create_guard(guard: GuardCreate, request: Request, current_user = Depends(require_module("hr"))):
    # Verify admin/HR role
    if not any(role in current_user.get("roles", []) for role in ["Administrador", "HR", "SuperAdmin"]):
        raise HTTPException(status_code=403, detail="Se requiere rol de Administrador o HR")
    
    user = await db.users.find_one({"id": guard.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    guard_doc = {
        "id": str(uuid.uuid4()),
        "user_id": guard.user_id,
        "user_name": user["full_name"],
        "email": user["email"],
        "badge_number": guard.badge_number,
        "phone": guard.phone,
        "emergency_contact": guard.emergency_contact,
        "hire_date": guard.hire_date,
        "hourly_rate": guard.hourly_rate,
        "is_active": True,
        "total_hours": 0,
        "condominium_id": current_user.get("condominium_id"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.guards.insert_one(guard_doc)
    
    # Add Guarda role to user
    await db.users.update_one(
        {"id": guard.user_id},
        {"$addToSet": {"roles": "Guarda"}}
    )
    
    return guard_doc

@api_router.get("/hr/guards")
async def get_guards(
    include_invalid: bool = False,
    current_user = Depends(require_module("hr"))
):
    """Get guards/employees - filtered by condominium, optionally including invalid records"""
    # Verify role
    if not any(role in current_user.get("roles", []) for role in ["Administrador", "Supervisor", "HR", "SuperAdmin"]):
        raise HTTPException(status_code=403, detail="Se requiere rol de Administrador, Supervisor o HR")
    
    # Use tenant_filter with extra conditions
    extra = {}
    if not include_invalid:
        extra["user_id"] = {"$ne": None, "$exists": True}
        extra["is_active"] = True
    
    query = tenant_filter(current_user, extra if extra else None)
    
    guards = await db.guards.find(query, {"_id": 0}).to_list(100)
    
    # Enrich with user data and validation status
    enriched_guards = []
    for guard in guards:
        # Check if user exists
        user_id = guard.get("user_id")
        user_valid = False
        user_data = None
        
        if user_id:
            user = await db.users.find_one({"id": user_id}, {"_id": 0, "full_name": 1, "email": 1, "is_active": 1})
            if user:
                user_valid = True
                user_data = user
                # Update guard name from user if missing
                if not guard.get("user_name") or not guard.get("full_name"):
                    guard["user_name"] = user.get("full_name")
                    guard["full_name"] = user.get("full_name")
                    guard["email"] = user.get("email")
        
        guard["_is_evaluable"] = user_valid and guard.get("is_active", False)
        guard["_validation_status"] = "valid" if user_valid else "invalid_user"
        
        enriched_guards.append(guard)
    
    return enriched_guards

# ==================== HR DATA INTEGRITY VALIDATION ====================

@api_router.get("/hr/validate-integrity")
async def validate_hr_integrity(
    current_user = Depends(require_role_and_module("Administrador", "SuperAdmin", module="hr"))
):
    """
    Validate HR data integrity - detect and report issues:
    - Duplicate guards by user_id
    - Guards without user_id
    - Guards with non-existent users
    - Orphan evaluations
    """
    issues = {
        "duplicates": [],
        "missing_user_id": [],
        "invalid_user": [],
        "orphan_evaluations": [],
        "summary": {
            "total_guards": 0,
            "valid_guards": 0,
            "invalid_guards": 0,
            "total_evaluations": 0,
            "orphan_evaluations": 0
        }
    }
    
    # Get all guards
    guards = await db.guards.find({}, {"_id": 0}).to_list(500)
    issues["summary"]["total_guards"] = len(guards)
    
    # 1. Check for duplicates by user_id
    user_ids = [g.get("user_id") for g in guards if g.get("user_id")]
    duplicate_uids = [uid for uid in set(user_ids) if user_ids.count(uid) > 1]
    
    for dup_uid in duplicate_uids:
        dup_guards = [g for g in guards if g.get("user_id") == dup_uid]
        issues["duplicates"].append({
            "user_id": dup_uid,
            "count": len(dup_guards),
            "guard_ids": [g.get("id") for g in dup_guards],
            "names": [g.get("user_name") or g.get("full_name") for g in dup_guards]
        })
    
    # 2. Check for guards without user_id
    for guard in guards:
        if not guard.get("user_id"):
            issues["missing_user_id"].append({
                "guard_id": guard.get("id"),
                "name": guard.get("user_name") or guard.get("full_name") or "Unknown",
                "is_active": guard.get("is_active")
            })
    
    # 3. Check for guards with non-existent users
    valid_count = 0
    for guard in guards:
        user_id = guard.get("user_id")
        if user_id:
            user = await db.users.find_one({"id": user_id})
            if user:
                valid_count += 1
            else:
                issues["invalid_user"].append({
                    "guard_id": guard.get("id"),
                    "user_id": user_id,
                    "name": guard.get("user_name") or guard.get("full_name") or "Unknown"
                })
    
    issues["summary"]["valid_guards"] = valid_count
    issues["summary"]["invalid_guards"] = len(guards) - valid_count
    
    # 4. Check for orphan evaluations
    evaluations = await db.hr_evaluations.find({}, {"_id": 0}).to_list(500)
    issues["summary"]["total_evaluations"] = len(evaluations)
    
    for eval in evaluations:
        emp_id = eval.get("employee_id")
        if emp_id:
            # Check in guards first, then users
            guard = await db.guards.find_one({"id": emp_id})
            if not guard:
                user = await db.users.find_one({"id": emp_id})
                if not user:
                    issues["orphan_evaluations"].append({
                        "evaluation_id": eval.get("id"),
                        "employee_id": emp_id,
                        "employee_name": eval.get("employee_name"),
                        "created_at": eval.get("created_at")
                    })
    
    issues["summary"]["orphan_evaluations"] = len(issues["orphan_evaluations"])
    
    return issues

@api_router.post("/hr/cleanup-invalid-guards")
async def cleanup_invalid_guards(
    dry_run: bool = True,
    current_user = Depends(require_role("SuperAdmin"))
):
    """
    Clean up invalid guard records:
    - Deactivate guards without user_id
    - Deactivate guards with non-existent users
    - Remove duplicate guard records (keep the one with most evaluations)
    
    Set dry_run=false to actually perform cleanup
    """
    results = {
        "dry_run": dry_run,
        "deactivated": [],
        "removed_duplicates": [],
        "errors": []
    }
    
    guards = await db.guards.find({}, {"_id": 0}).to_list(500)
    
    # 1. Handle guards without user_id
    for guard in guards:
        if not guard.get("user_id"):
            if not dry_run:
                await db.guards.update_one(
                    {"id": guard.get("id")},
                    {"$set": {"is_active": False, "deactivation_reason": "no_user_id"}}
                )
            results["deactivated"].append({
                "guard_id": guard.get("id"),
                "reason": "no_user_id",
                "name": guard.get("user_name") or "Unknown"
            })
    
    # 2. Handle guards with non-existent users
    for guard in guards:
        user_id = guard.get("user_id")
        if user_id:
            user = await db.users.find_one({"id": user_id})
            if not user:
                if not dry_run:
                    await db.guards.update_one(
                        {"id": guard.get("id")},
                        {"$set": {"is_active": False, "deactivation_reason": "user_not_found"}}
                    )
                results["deactivated"].append({
                    "guard_id": guard.get("id"),
                    "reason": "user_not_found",
                    "user_id": user_id
                })
    
    # 3. Handle duplicates
    user_ids = [g.get("user_id") for g in guards if g.get("user_id")]
    duplicate_uids = [uid for uid in set(user_ids) if user_ids.count(uid) > 1]
    
    for dup_uid in duplicate_uids:
        dup_guards = [g for g in guards if g.get("user_id") == dup_uid]
        
        # Get evaluation count for each duplicate
        for dg in dup_guards:
            eval_count = await db.hr_evaluations.count_documents({"employee_id": dg.get("id")})
            dg["_eval_count"] = eval_count
        
        # Sort by evaluation count (keep the one with most evaluations)
        dup_guards.sort(key=lambda x: x.get("_eval_count", 0), reverse=True)
        
        # Keep first (most evaluations), deactivate others
        keep_guard = dup_guards[0]
        for to_remove in dup_guards[1:]:
            if not dry_run:
                await db.guards.update_one(
                    {"id": to_remove.get("id")},
                    {"$set": {"is_active": False, "deactivation_reason": "duplicate"}}
                )
            results["removed_duplicates"].append({
                "kept_guard_id": keep_guard.get("id"),
                "deactivated_guard_id": to_remove.get("id"),
                "user_id": dup_uid
            })
    
    return results

@api_router.get("/hr/evaluable-employees")
async def get_evaluable_employees(
    current_user = Depends(require_role("Administrador", "Supervisor", "HR"))
):
    """
    Get employees that are eligible for evaluation:
    - Have valid user_id
    - User exists in users collection
    - Is active
    - Not the current user (can't evaluate yourself)
    """
    condo_id = current_user.get("condominium_id")
    current_user_id = current_user.get("id")
    
    # Build query
    query = {
        "user_id": {"$ne": None, "$exists": True},
        "is_active": True
    }
    
    if "SuperAdmin" not in current_user.get("roles", []) and condo_id:
        query["condominium_id"] = condo_id
    
    guards = await db.guards.find(query, {"_id": 0}).to_list(100)
    
    evaluable_employees = []
    for guard in guards:
        user_id = guard.get("user_id")
        
        # Skip self
        if user_id == current_user_id:
            continue
        
        # Verify user exists
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "full_name": 1, "email": 1, "is_active": 1})
        if user and user.get("is_active", True):
            # Enrich guard data with user info
            guard["user_name"] = user.get("full_name") or guard.get("user_name")
            guard["full_name"] = user.get("full_name") or guard.get("full_name")
            guard["email"] = user.get("email") or guard.get("email")
            guard["_is_evaluable"] = True
            
            # Get evaluation count
            eval_count = await db.hr_evaluations.count_documents({"employee_id": guard.get("id")})
            guard["evaluation_count"] = eval_count
            
            evaluable_employees.append(guard)
    
    return evaluable_employees

@api_router.get("/hr/guards/{guard_id}")
async def get_guard(guard_id: str, current_user = Depends(require_role_and_module("Administrador", "Supervisor", "HR", module="hr"))):
    """Get a single guard by ID - must belong to user's condominium"""
    # Use get_tenant_resource for automatic 404/403 handling
    guard = await get_tenant_resource(db.guards, guard_id, current_user)
    return guard

@api_router.put("/hr/guards/{guard_id}")
async def update_guard(
    guard_id: str,
    guard_update: GuardUpdate,
    request: Request,
    current_user = Depends(require_role_and_module("Administrador", module="hr"))
):
    """Update guard/employee details - must belong to user's condominium"""
    # Use get_tenant_resource for tenant validation
    guard = await get_tenant_resource(db.guards, guard_id, current_user)
    
    # Build update dict with only provided fields
    update_data = {}
    if guard_update.badge_number is not None:
        update_data["badge_number"] = guard_update.badge_number
    if guard_update.phone is not None:
        update_data["phone"] = guard_update.phone
    if guard_update.emergency_contact is not None:
        update_data["emergency_contact"] = guard_update.emergency_contact
    if guard_update.hourly_rate is not None:
        update_data["hourly_rate"] = guard_update.hourly_rate
    if guard_update.is_active is not None:
        update_data["is_active"] = guard_update.is_active
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.guards.update_one(
        {"id": guard_id},
        {"$set": update_data}
    )
    
    await log_audit_event(
        AuditEventType.USER_UPDATED,
        current_user["id"],
        "hr",
        {"guard_id": guard_id, "updated_fields": list(update_data.keys())},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    updated_guard = await db.guards.find_one({"id": guard_id}, {"_id": 0})
    return updated_guard

# ==================== HR SHIFTS (FULL CRUD) ====================

@api_router.post("/hr/shifts")
async def create_shift(shift: ShiftCreate, request: Request, current_user = Depends(require_role_and_module("Administrador", "Supervisor", "HR", "SuperAdmin", module="hr"))):
    """Create a new shift with validations"""
    # Validate guard exists and is active
    guard = await db.guards.find_one({"id": shift.guard_id})
    if not guard:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    if not guard.get("is_active", True):
        raise HTTPException(status_code=400, detail="El empleado no está activo")
    
    # Parse and validate times
    try:
        start_dt = datetime.fromisoformat(shift.start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(shift.end_time.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use ISO 8601")
    
    if start_dt >= end_dt:
        raise HTTPException(status_code=400, detail="La hora de inicio debe ser anterior a la hora de fin")
    
    # Check for overlapping shifts (only scheduled or in_progress - allow creating new shifts over completed ones)
    existing_shifts = await db.shifts.find({
        "guard_id": shift.guard_id,
        "status": {"$in": ["scheduled", "in_progress"]},  # Only active shifts can cause overlap
        "$or": [
            {"start_time": {"$lt": shift.end_time}, "end_time": {"$gt": shift.start_time}}
        ]
    }).to_list(100)
    
    if existing_shifts:
        raise HTTPException(status_code=400, detail="El empleado ya tiene un turno programado en ese horario")
    
    # Get condominium_id - prefer user's condo, fallback to guard's condo (important for SuperAdmin)
    condominium_id = current_user.get("condominium_id") or guard.get("condominium_id")
    
    if not condominium_id:
        raise HTTPException(status_code=400, detail="No se puede determinar el condominio. El empleado debe estar asignado a un condominio.")
    
    shift_doc = {
        "id": str(uuid.uuid4()),
        "guard_id": shift.guard_id,
        "guard_name": guard.get("user_name") or guard.get("name") or "Sin nombre",
        "start_time": shift.start_time,
        "end_time": shift.end_time,
        "location": shift.location,
        "notes": shift.notes,
        "status": "scheduled",
        "condominium_id": condominium_id,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.shifts.insert_one(shift_doc)
    
    # Remove MongoDB _id before returning
    shift_doc.pop("_id", None)
    
    await log_audit_event(
        AuditEventType.SHIFT_CREATED,
        current_user["id"],
        "hr",
        {"shift_id": shift_doc["id"], "guard_id": shift.guard_id, "location": shift.location},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return shift_doc

@api_router.get("/hr/shifts")
async def get_shifts(
    status: Optional[str] = None,
    guard_id: Optional[str] = None,
    current_user = Depends(require_module("hr"))
):
    """Get shifts with optional filters - scoped by condominium"""
    # Verify role
    allowed_roles = ["Administrador", "Supervisor", "Guarda", "HR", "SuperAdmin"]
    if not any(role in current_user.get("roles", []) for role in allowed_roles):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    # Build extra filters
    extra = {}
    if status:
        extra["status"] = status
    if guard_id:
        extra["guard_id"] = guard_id
    
    # Use tenant_filter for multi-tenant scoping
    query = tenant_filter(current_user, extra if extra else None)
    
    # Guards can only see their own shifts
    if "Guarda" in current_user.get("roles", []) and "Administrador" not in current_user.get("roles", []):
        guard = await db.guards.find_one({"user_id": current_user["id"]})
        if guard:
            query["guard_id"] = guard["id"]
    
    shifts = await db.shifts.find(query, {"_id": 0}).sort("start_time", -1).to_list(100)
    return shifts

@api_router.get("/hr/shifts/{shift_id}")
async def get_shift(shift_id: str, current_user = Depends(require_role("Administrador", "Supervisor", "Guarda", "HR"))):
    """Get a single shift by ID - must belong to user's condominium"""
    # Use get_tenant_resource for automatic 404/403 handling
    shift = await get_tenant_resource(db.shifts, shift_id, current_user)
    return shift

@api_router.put("/hr/shifts/{shift_id}")
async def update_shift(
    shift_id: str,
    shift_update: ShiftUpdate,
    request: Request,
    current_user = Depends(require_role("Administrador", "Supervisor", "HR"))
):
    """Update an existing shift - must belong to user's condominium"""
    # Use get_tenant_resource for tenant validation
    shift = await get_tenant_resource(db.shifts, shift_id, current_user)
    
    update_data = {}
    
    if shift_update.start_time is not None:
        update_data["start_time"] = shift_update.start_time
    if shift_update.end_time is not None:
        update_data["end_time"] = shift_update.end_time
    if shift_update.location is not None:
        update_data["location"] = shift_update.location
    if shift_update.notes is not None:
        update_data["notes"] = shift_update.notes
    if shift_update.status is not None:
        if shift_update.status not in ["scheduled", "in_progress", "completed", "cancelled"]:
            raise HTTPException(status_code=400, detail="Estado inválido")
        update_data["status"] = shift_update.status
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    
    # Validate times if both are being updated
    new_start = update_data.get("start_time", shift["start_time"])
    new_end = update_data.get("end_time", shift["end_time"])
    
    try:
        start_dt = datetime.fromisoformat(new_start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(new_end.replace('Z', '+00:00'))
        if start_dt >= end_dt:
            raise HTTPException(status_code=400, detail="La hora de inicio debe ser anterior a la hora de fin")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido")
    
    # Check for overlaps (excluding current shift)
    if "start_time" in update_data or "end_time" in update_data:
        existing = await db.shifts.find({
            "id": {"$ne": shift_id},
            "guard_id": shift["guard_id"],
            "status": {"$ne": "cancelled"},
            "$or": [
                {"start_time": {"$lt": new_end}, "end_time": {"$gt": new_start}}
            ]
        }).to_list(100)
        
        if existing:
            raise HTTPException(status_code=400, detail="El cambio genera conflicto con otro turno")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["updated_by"] = current_user["id"]
    
    await db.shifts.update_one({"id": shift_id}, {"$set": update_data})
    
    await log_audit_event(
        AuditEventType.SHIFT_UPDATED,
        current_user["id"],
        "hr",
        {"shift_id": shift_id, "updated_fields": list(update_data.keys())},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    updated_shift = await db.shifts.find_one({"id": shift_id}, {"_id": 0})
    return updated_shift

@api_router.delete("/hr/shifts/{shift_id}")
async def delete_shift(
    shift_id: str,
    request: Request,
    current_user = Depends(require_role("Administrador", "HR", "Supervisor", "SuperAdmin"))
):
    """Delete (cancel) a shift - must belong to user's condominium"""
    # Use get_tenant_resource for tenant validation
    shift = await get_tenant_resource(db.shifts, shift_id, current_user)
    
    # Soft delete - mark as cancelled
    await db.shifts.update_one(
        {"id": shift_id},
        {"$set": {
            "status": "cancelled",
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
            "cancelled_by": current_user["id"]
        }}
    )
    
    await log_audit_event(
        AuditEventType.SHIFT_DELETED,
        current_user["id"],
        "hr",
        {"shift_id": shift_id, "guard_id": shift["guard_id"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "Turno cancelado exitosamente"}

# ==================== HR CLOCK IN/OUT ====================

@api_router.post("/hr/clock")
async def clock_in_out(
    clock_req: ClockRequest,
    request: Request,
    current_user = Depends(require_role("Guarda", "Administrador", "Supervisor"))
):
    """
    Register clock in or clock out.
    
    Clock IN rules:
    - Guard must have an active shift (current time within shift window)
    - OR be within 15 minutes before shift start (early clock in allowed)
    - Cannot clock in if already clocked in
    
    Clock OUT rules:
    - Must have clocked in first
    - Will auto-complete shift if clocking out after shift end time
    """
    if clock_req.type not in ["IN", "OUT"]:
        raise HTTPException(status_code=400, detail="Tipo debe ser 'IN' o 'OUT'")
    
    # Get guard record for current user
    guard = await db.guards.find_one({"user_id": current_user["id"]})
    if not guard:
        raise HTTPException(status_code=404, detail="No tienes registro como empleado")
    
    if not guard.get("is_active", True):
        raise HTTPException(status_code=400, detail="Tu cuenta de empleado no está activa")
    
    condo_id = current_user.get("condominium_id")
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    today = now.date().isoformat()
    
    # Get today's clock logs for this employee
    today_logs = await db.hr_clock_logs.find({
        "employee_id": guard["id"],
        "date": today
    }).sort("timestamp", -1).to_list(100)
    
    # Variables for shift linking
    linked_shift_id = None
    shift_info = None
    
    if clock_req.type == "IN":
        # Check if already clocked in without clocking out
        if today_logs:
            last_log = today_logs[0]
            if last_log["type"] == "IN":
                raise HTTPException(status_code=400, detail="Ya tienes una entrada registrada. Debes registrar salida primero.")
        
        # Find active or upcoming shift for validation
        # Allow clock in if: within shift time OR up to 15 minutes before shift start
        early_window_future = (now + timedelta(minutes=15)).isoformat()
        
        active_shift = await db.shifts.find_one({
            "guard_id": guard["id"],
            "condominium_id": condo_id,
            "status": {"$in": ["scheduled", "in_progress"]},
            "$or": [
                # Currently within shift window
                {"start_time": {"$lte": now_iso}, "end_time": {"$gte": now_iso}},
                # OR shift starts within next 15 minutes (early clock-in allowed)
                {"start_time": {"$gt": now_iso, "$lte": early_window_future}}
            ]
        }, {"_id": 0})
        
        if not active_shift:
            # Check if there's any upcoming shift today
            today_end = f"{today}T23:59:59+00:00"
            upcoming_shift = await db.shifts.find_one({
                "guard_id": guard["id"],
                "condominium_id": condo_id,
                "status": "scheduled",
                "start_time": {"$gte": now_iso, "$lte": today_end}
            }, {"_id": 0})
            
            if upcoming_shift:
                shift_start_str = upcoming_shift["start_time"]
                # Ensure timezone-aware datetime
                if 'Z' in shift_start_str:
                    shift_start = datetime.fromisoformat(shift_start_str.replace('Z', '+00:00'))
                elif '+' in shift_start_str or shift_start_str.endswith('-00:00'):
                    shift_start = datetime.fromisoformat(shift_start_str)
                else:
                    shift_start = datetime.fromisoformat(shift_start_str).replace(tzinfo=timezone.utc)
                
                minutes_until = int((shift_start - now).total_seconds() / 60)
                raise HTTPException(
                    status_code=400, 
                    detail=f"Tu turno comienza en {minutes_until} minutos. Puedes fichar entrada 15 minutos antes."
                )
            else:
                raise HTTPException(
                    status_code=400, 
                    detail="No tienes un turno asignado para hoy. Contacta a tu supervisor."
                )
        
        linked_shift_id = active_shift["id"]
        shift_info = active_shift
        
        # Update shift status to in_progress
        await db.shifts.update_one(
            {"id": linked_shift_id},
            {"$set": {"status": "in_progress", "clock_in_time": now_iso}}
        )
    
    elif clock_req.type == "OUT":
        # Check if there's a clock in first
        if not today_logs:
            raise HTTPException(status_code=400, detail="No tienes entrada registrada hoy. Debes registrar entrada primero.")
        
        last_log = today_logs[0]
        if last_log["type"] == "OUT":
            raise HTTPException(status_code=400, detail="Ya registraste salida. Debes registrar entrada primero.")
        
        # Get linked shift from clock in
        linked_shift_id = last_log.get("shift_id")
        
        if linked_shift_id:
            shift_info = await db.shifts.find_one({"id": linked_shift_id}, {"_id": 0})
    
    clock_doc = {
        "id": str(uuid.uuid4()),
        "employee_id": guard["id"],
        "employee_name": guard.get("user_name") or guard.get("name") or "Sin nombre",
        "type": clock_req.type,
        "timestamp": now_iso,
        "date": today,
        "shift_id": linked_shift_id,
        "condominium_id": condo_id,
        "created_at": now_iso
    }
    
    await db.hr_clock_logs.insert_one(clock_doc)
    
    # Remove MongoDB _id
    clock_doc.pop("_id", None)
    
    # Calculate hours if clocking out
    hours_worked = None
    if clock_req.type == "OUT" and today_logs:
        last_in = next((log for log in today_logs if log["type"] == "IN"), None)
        if last_in:
            in_time = datetime.fromisoformat(last_in["timestamp"].replace('Z', '+00:00'))
            out_time = now
            hours_worked = round((out_time - in_time).total_seconds() / 3600, 2)
            
            # Update guard's total hours
            await db.guards.update_one(
                {"id": guard["id"]},
                {"$inc": {"total_hours": hours_worked}}
            )
            
            # Complete the shift if clocking out
            if linked_shift_id:
                await db.shifts.update_one(
                    {"id": linked_shift_id},
                    {"$set": {
                        "status": "completed",
                        "clock_out_time": now_iso,
                        "hours_worked": hours_worked,
                        "completed_at": now_iso
                    }}
                )
    
    await log_audit_event(
        AuditEventType.CLOCK_IN if clock_req.type == "IN" else AuditEventType.CLOCK_OUT,
        current_user["id"],
        "hr",
        {
            "employee_id": guard["id"], 
            "type": clock_req.type, 
            "hours_worked": hours_worked,
            "shift_id": linked_shift_id
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        **clock_doc,
        "hours_worked": hours_worked,
        "shift_info": shift_info,
        "message": f"{'Entrada' if clock_req.type == 'IN' else 'Salida'} registrada exitosamente"
    }

@api_router.get("/hr/clock/status")
async def get_clock_status(current_user = Depends(require_role("Guarda", "Administrador", "Supervisor", "HR"))):
    """Get current clock status for logged-in employee"""
    guard = await db.guards.find_one({"user_id": current_user["id"]})
    if not guard:
        return {"is_clocked_in": False, "message": "No tienes registro como empleado", "today_logs": []}
    
    today = datetime.now(timezone.utc).date().isoformat()
    
    today_logs = await db.hr_clock_logs.find({
        "employee_id": guard["id"],
        "date": today
    }).sort("timestamp", -1).to_list(100)
    
    if not today_logs:
        return {
            "is_clocked_in": False,
            "last_action": None,
            "last_time": None,
            "employee_id": guard["id"],
            "employee_name": guard.get("user_name") or guard.get("name") or "Sin nombre",
            "today_logs": []
        }
    
    last_log = today_logs[0]
    return {
        "is_clocked_in": last_log["type"] == "IN",
        "last_action": last_log["type"],
        "last_time": last_log["timestamp"],
        "employee_id": guard["id"],
        "employee_name": guard.get("user_name") or guard.get("name") or "Sin nombre",
        "today_logs": [{"type": log["type"], "timestamp": log["timestamp"]} for log in today_logs]
    }

@api_router.get("/hr/clock/history")
async def get_clock_history(
    employee_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda", "HR"))
):
    """Get clock history with filters - scoped by condominium"""
    # Build extra filters
    extra = {}
    
    # Guards can only see their own history
    if "Guarda" in current_user.get("roles", []) and "Administrador" not in current_user.get("roles", []):
        guard = await db.guards.find_one({"user_id": current_user["id"]})
        if guard:
            extra["employee_id"] = guard["id"]
    elif employee_id:
        extra["employee_id"] = employee_id
    
    if start_date:
        extra["date"] = {"$gte": start_date}
    if end_date:
        if "date" in extra:
            extra["date"]["$lte"] = end_date
        else:
            extra["date"] = {"$lte": end_date}
    
    # Use tenant_filter for multi-tenant scoping
    query = tenant_filter(current_user, extra if extra else None)
    
    logs = await db.hr_clock_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(500)
    return logs

# ==================== HR ABSENCES ====================

@api_router.post("/hr/absences")
async def create_absence_request(
    absence: AbsenceCreate,
    request: Request,
    current_user = Depends(require_role("Guarda", "Administrador", "Supervisor"))
):
    """Create a new absence request"""
    # Get guard record
    guard = await db.guards.find_one({"user_id": current_user["id"]})
    if not guard:
        raise HTTPException(status_code=404, detail="No tienes registro como empleado")
    
    # Validate dates
    try:
        start_dt = datetime.fromisoformat(absence.start_date)
        end_dt = datetime.fromisoformat(absence.end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")
    
    if start_dt > end_dt:
        raise HTTPException(status_code=400, detail="La fecha de inicio debe ser anterior o igual a la fecha de fin")
    
    # Validate type
    valid_types = ["vacaciones", "permiso_medico", "personal", "otro"]
    if absence.type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Use: {', '.join(valid_types)}")
    
    # Check for overlapping requests
    existing = await db.hr_absences.find({
        "employee_id": guard["id"],
        "status": {"$in": ["pending", "approved"]},
        "$or": [
            {"start_date": {"$lte": absence.end_date}, "end_date": {"$gte": absence.start_date}}
        ]
    }).to_list(100)
    
    if existing:
        raise HTTPException(status_code=400, detail="Ya tienes una solicitud para esas fechas")
    
    # Determine source based on role
    is_guard_request = "Guarda" in current_user.get("roles", []) and "Administrador" not in current_user.get("roles", [])
    
    absence_doc = {
        "id": str(uuid.uuid4()),
        "employee_id": guard["id"],
        "employee_name": guard.get("user_name") or guard.get("name") or "Sin nombre",
        "reason": absence.reason,
        "type": absence.type,
        "start_date": absence.start_date,
        "end_date": absence.end_date,
        "notes": absence.notes,
        "status": "pending",
        "source": "guard" if is_guard_request else "admin",
        "condominium_id": current_user.get("condominium_id"),
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.hr_absences.insert_one(absence_doc)
    
    # Remove MongoDB _id
    absence_doc.pop("_id", None)
    
    await log_audit_event(
        AuditEventType.ABSENCE_REQUESTED,
        current_user["id"],
        "hr",
        {
            "absence_id": absence_doc["id"], 
            "type": absence.type, 
            "dates": f"{absence.start_date} - {absence.end_date}",
            "source": absence_doc["source"],
            "guard_id": guard["id"],
            "condominium_id": absence_doc["condominium_id"]
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return absence_doc

@api_router.get("/hr/absences")
async def get_absences(
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda", "HR"))
):
    """Get absence requests with filters - scoped by condominium"""
    # Build extra filters
    extra = {}
    if status:
        if status not in ["pending", "approved", "rejected"]:
            raise HTTPException(status_code=400, detail="Estado inválido")
        extra["status"] = status
    
    # Use tenant_filter for multi-tenant scoping
    query = tenant_filter(current_user, extra if extra else None)
    
    # Guards can only see their own absences
    if "Guarda" in current_user.get("roles", []) and "Administrador" not in current_user.get("roles", []):
        guard = await db.guards.find_one({"user_id": current_user["id"]})
        if guard:
            query["employee_id"] = guard["id"]
    elif employee_id:
        query["employee_id"] = employee_id
    
    absences = await db.hr_absences.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return absences

@api_router.get("/hr/absences/{absence_id}")
async def get_absence(absence_id: str, current_user = Depends(require_role("Administrador", "Supervisor", "Guarda", "HR"))):
    """Get a single absence request - must belong to user's condominium"""
    # Use get_tenant_resource for automatic 404/403 handling
    absence = await get_tenant_resource(db.hr_absences, absence_id, current_user)
    return absence

@api_router.put("/hr/absences/{absence_id}/approve")
async def approve_absence(
    absence_id: str,
    request: Request,
    admin_notes: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor", "HR"))
):
    """Approve an absence request"""
    # Use get_tenant_resource for tenant validation
    absence = await get_tenant_resource(db.hr_absences, absence_id, current_user)
    
    if absence["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"La solicitud ya fue {absence['status']}")
    
    await db.hr_absences.update_one(
        {"id": absence_id},
        {"$set": {
            "status": "approved",
            "approved_by": current_user["id"],
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "admin_notes": admin_notes
        }}
    )
    
    await log_audit_event(
        AuditEventType.ABSENCE_APPROVED,
        current_user["id"],
        "hr",
        {"absence_id": absence_id, "employee_id": absence["employee_id"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    updated = await db.hr_absences.find_one({"id": absence_id}, {"_id": 0})
    return updated

@api_router.put("/hr/absences/{absence_id}/reject")
async def reject_absence(
    absence_id: str,
    request: Request,
    admin_notes: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor", "HR"))
):
    """Reject an absence request - must belong to user's condominium"""
    # Use get_tenant_resource for tenant validation
    absence = await get_tenant_resource(db.hr_absences, absence_id, current_user)
    
    if absence["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"La solicitud ya fue {absence['status']}")
    
    await db.hr_absences.update_one(
        {"id": absence_id},
        {"$set": {
            "status": "rejected",
            "rejected_by": current_user["id"],
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "admin_notes": admin_notes
        }}
    )
    
    await log_audit_event(
        AuditEventType.ABSENCE_REJECTED,
        current_user["id"],
        "hr",
        {"absence_id": absence_id, "employee_id": absence["employee_id"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    updated = await db.hr_absences.find_one({"id": absence_id}, {"_id": 0})
    return updated

@api_router.get("/hr/payroll")
async def get_payroll(current_user = Depends(require_role("Administrador", "HR"))):
    """Get payroll data - scoped by condominium"""
    # Use tenant_filter for multi-tenant scoping
    query = tenant_filter(current_user)
    guards = await db.guards.find(query, {"_id": 0}).to_list(100)
    payroll = []
    for guard in guards:
        payroll.append({
            "guard_id": guard["id"],
            "guard_name": guard.get("user_name") or guard.get("name") or "Sin nombre",
            "badge_number": guard.get("badge_number", "N/A"),
            "hourly_rate": guard.get("hourly_rate", 0),
            "total_hours": guard.get("total_hours", 0),
            "total_pay": guard.get("total_hours", 0) * guard.get("hourly_rate", 0)
        })
    return payroll

# ==================== HR RECRUITMENT ====================

@api_router.post("/hr/candidates")
async def create_candidate(
    candidate: CandidateCreate,
    request: Request,
    current_user = Depends(require_role_and_module("Administrador", "HR", module="hr"))
):
    """Create a new recruitment candidate"""
    # Check if email already exists
    existing = await db.hr_candidates.find_one({"email": candidate.email})
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un candidato con ese email")
    
    existing_user = await db.users.find_one({"email": candidate.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Este email ya está registrado como usuario")
    
    candidate_doc = {
        "id": str(uuid.uuid4()),
        "full_name": candidate.full_name,
        "email": candidate.email,
        "phone": candidate.phone,
        "position": candidate.position,
        "experience_years": candidate.experience_years,
        "notes": candidate.notes,
        "documents": candidate.documents or [],
        "status": "applied",  # applied, interview, hired, rejected
        "condominium_id": current_user.get("condominium_id"),
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.hr_candidates.insert_one(candidate_doc)
    candidate_doc.pop("_id", None)
    
    await log_audit_event(
        AuditEventType.CANDIDATE_CREATED,
        current_user["id"],
        "hr",
        {"candidate_id": candidate_doc["id"], "name": candidate.full_name, "position": candidate.position},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return candidate_doc

@api_router.get("/hr/candidates")
async def get_candidates(
    status: Optional[str] = None,
    position: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "HR"))
):
    """List recruitment candidates - scoped by condominium"""
    # Build extra filters
    extra = {}
    if status:
        extra["status"] = status
    if position:
        extra["position"] = position
    
    # Use tenant_filter for multi-tenant scoping
    query = tenant_filter(current_user, extra if extra else None)
    
    candidates = await db.hr_candidates.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return candidates

@api_router.get("/hr/candidates/{candidate_id}")
async def get_candidate(
    candidate_id: str,
    current_user = Depends(require_role("Administrador", "HR"))
):
    """Get a single candidate - must belong to user's condominium"""
    # Use get_tenant_resource for tenant validation
    candidate = await get_tenant_resource(db.hr_candidates, candidate_id, current_user)
    return candidate

@api_router.put("/hr/candidates/{candidate_id}")
async def update_candidate(
    candidate_id: str,
    update: CandidateUpdate,
    request: Request,
    current_user = Depends(require_role("Administrador", "HR"))
):
    """Update candidate information - must belong to user's condominium"""
    # Use get_tenant_resource for tenant validation
    candidate = await get_tenant_resource(db.hr_candidates, candidate_id, current_user)
    
    update_data = {}
    if update.full_name is not None:
        update_data["full_name"] = update.full_name
    if update.phone is not None:
        update_data["phone"] = update.phone
    if update.position is not None:
        update_data["position"] = update.position
    if update.experience_years is not None:
        update_data["experience_years"] = update.experience_years
    if update.notes is not None:
        update_data["notes"] = update.notes
    if update.status is not None:
        if update.status not in ["applied", "interview", "hired", "rejected"]:
            raise HTTPException(status_code=400, detail="Estado inválido")
        update_data["status"] = update.status
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["updated_by"] = current_user["id"]
    
    await db.hr_candidates.update_one({"id": candidate_id}, {"$set": update_data})
    
    await log_audit_event(
        AuditEventType.CANDIDATE_UPDATED,
        current_user["id"],
        "hr",
        {"candidate_id": candidate_id, "updated_fields": list(update_data.keys())},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    updated = await db.hr_candidates.find_one({"id": candidate_id}, {"_id": 0})
    return updated

@api_router.post("/hr/candidates/{candidate_id}/hire")
async def hire_candidate(
    candidate_id: str,
    hire_data: HireCandidate,
    request: Request,
    current_user = Depends(require_role("Administrador", "HR"))
):
    """Hire a candidate - must belong to user's condominium"""
    # Use get_tenant_resource for tenant validation
    candidate = await get_tenant_resource(db.hr_candidates, candidate_id, current_user)
    
    if candidate["status"] == "hired":
        raise HTTPException(status_code=400, detail="Este candidato ya fue contratado")
    
    if candidate["status"] == "rejected":
        raise HTTPException(status_code=400, detail="Este candidato fue rechazado")
    
    # Check email not already in use
    existing_user = await db.users.find_one({"email": candidate["email"]})
    if existing_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado como usuario")
    
    # Check badge number not in use
    existing_badge = await db.guards.find_one({"badge_number": hire_data.badge_number})
    if existing_badge:
        raise HTTPException(status_code=400, detail="El número de identificación ya está en uso")
    
    condominium_id = current_user.get("condominium_id") or candidate.get("condominium_id")
    
    # 1. Create user account
    user_id = str(uuid.uuid4())
    role = RoleEnum.GUARDA if candidate["position"] in ["Guarda", "Guard"] else RoleEnum.SUPERVISOR
    
    user_doc = {
        "id": user_id,
        "email": candidate["email"],
        "hashed_password": hash_password(hire_data.password),
        "full_name": candidate["full_name"],
        "roles": [role.value],
        "condominium_id": condominium_id,
        "is_active": True,
        "is_locked": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    # 2. Create guard/employee record
    guard_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_name": candidate["full_name"],
        "email": candidate["email"],
        "badge_number": hire_data.badge_number,
        "phone": candidate["phone"],
        "emergency_contact": "",
        "hire_date": datetime.now(timezone.utc).date().isoformat(),
        "hourly_rate": hire_data.hourly_rate,
        "is_active": True,
        "total_hours": 0,
        "condominium_id": condominium_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.guards.insert_one(guard_doc)
    
    # 3. Update candidate status
    await db.hr_candidates.update_one(
        {"id": candidate_id},
        {"$set": {
            "status": "hired",
            "hired_at": datetime.now(timezone.utc).isoformat(),
            "hired_by": current_user["id"],
            "user_id": user_id,
            "guard_id": guard_doc["id"]
        }}
    )
    
    await log_audit_event(
        AuditEventType.CANDIDATE_HIRED,
        current_user["id"],
        "hr",
        {
            "candidate_id": candidate_id,
            "user_id": user_id,
            "guard_id": guard_doc["id"],
            "name": candidate["full_name"],
            "position": candidate["position"]
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "message": f"Candidato {candidate['full_name']} contratado exitosamente",
        "user_id": user_id,
        "guard_id": guard_doc["id"],
        "email": candidate["email"],
        "credentials": {
            "email": candidate["email"],
            "password": "********"  # Don't return actual password
        }
    }

@api_router.put("/hr/candidates/{candidate_id}/reject")
async def reject_candidate(
    candidate_id: str,
    request: Request,
    reason: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "HR"))
):
    """Reject a candidate"""
    candidate = await db.hr_candidates.find_one({"id": candidate_id})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
    if candidate["status"] == "hired":
        raise HTTPException(status_code=400, detail="No se puede rechazar un candidato ya contratado")
    
    await db.hr_candidates.update_one(
        {"id": candidate_id},
        {"$set": {
            "status": "rejected",
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "rejected_by": current_user["id"],
            "rejection_reason": reason
        }}
    )
    
    await log_audit_event(
        AuditEventType.CANDIDATE_REJECTED,
        current_user["id"],
        "hr",
        {"candidate_id": candidate_id, "name": candidate["full_name"], "reason": reason},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": f"Candidato {candidate['full_name']} rechazado"}

# ==================== HR EMPLOYEE MANAGEMENT ====================

@api_router.post("/hr/employees")
async def create_employee_directly(
    employee: CreateEmployeeByHR,
    request: Request,
    current_user = Depends(require_role_and_module("Administrador", "HR", module="hr"))
):
    """Create a new employee (guard) directly without recruitment"""
    # Check email not in use
    existing_user = await db.users.find_one({"email": employee.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # Check badge number
    existing_badge = await db.guards.find_one({"badge_number": employee.badge_number})
    if existing_badge:
        raise HTTPException(status_code=400, detail="El número de identificación ya está en uso")
    
    condominium_id = current_user.get("condominium_id")
    
    # 1. Create user account
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": employee.email,
        "hashed_password": hash_password(employee.password),
        "full_name": employee.full_name,
        "roles": [RoleEnum.GUARDA.value],
        "condominium_id": condominium_id,
        "is_active": True,
        "is_locked": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    # 2. Create guard record
    guard_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_name": employee.full_name,
        "email": employee.email,
        "badge_number": employee.badge_number,
        "phone": employee.phone,
        "emergency_contact": employee.emergency_contact,
        "hire_date": datetime.now(timezone.utc).date().isoformat(),
        "hourly_rate": employee.hourly_rate,
        "is_active": True,
        "total_hours": 0,
        "condominium_id": condominium_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.guards.insert_one(guard_doc)
    
    await log_audit_event(
        AuditEventType.EMPLOYEE_CREATED,
        current_user["id"],
        "hr",
        {"user_id": user_id, "guard_id": guard_doc["id"], "name": employee.full_name},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "message": f"Empleado {employee.full_name} creado exitosamente",
        "user_id": user_id,
        "guard_id": guard_doc["id"],
        "credentials": {
            "email": employee.email,
            "password": "********"
        }
    }

@api_router.put("/hr/employees/{guard_id}/deactivate")
async def deactivate_employee(
    guard_id: str,
    request: Request,
    current_user = Depends(require_role("Administrador", "HR"))
):
    """Deactivate an employee"""
    guard = await db.guards.find_one({"id": guard_id})
    if not guard:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    # Deactivate guard record
    await db.guards.update_one(
        {"id": guard_id},
        {"$set": {"is_active": False, "deactivated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Deactivate user account if user_id exists
    user_id = guard.get("user_id")
    if user_id:
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"is_active": False}}
        )
    
    # Get employee name safely
    employee_name = guard.get("user_name") or guard.get("name") or guard.get("full_name") or "desconocido"
    
    await log_audit_event(
        AuditEventType.EMPLOYEE_DEACTIVATED,
        current_user["id"],
        "hr",
        {"guard_id": guard_id, "user_id": user_id, "name": employee_name},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": f"Empleado {employee_name} desactivado"}

@api_router.put("/hr/employees/{guard_id}/activate")
async def activate_employee(
    guard_id: str,
    request: Request,
    current_user = Depends(require_role("Administrador", "HR"))
):
    """Reactivate an employee"""
    guard = await db.guards.find_one({"id": guard_id})
    if not guard:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    # Activate guard record
    await db.guards.update_one(
        {"id": guard_id},
        {"$set": {"is_active": True, "reactivated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Activate user account if user_id exists
    user_id = guard.get("user_id")
    if user_id:
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"is_active": True}}
        )
    
    # Get employee name safely
    employee_name = guard.get("user_name") or guard.get("name") or guard.get("full_name") or "desconocido"
    
    await log_audit_event(
        AuditEventType.EMPLOYEE_ACTIVATED,
        current_user["id"],
        "hr",
        {"guard_id": guard_id, "user_id": user_id, "name": employee_name},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": f"Empleado {employee_name} reactivado"}

# ==================== HR PERFORMANCE EVALUATIONS ====================

@api_router.post("/hr/evaluations")
async def create_evaluation(
    evaluation: EvaluationCreate,
    request: Request,
    current_user = Depends(require_role_and_module("Administrador", "HR", "Supervisor", module="hr"))
):
    """Create a new performance evaluation for an employee"""
    condominium_id = current_user.get("condominium_id")
    
    # First try to find in guards collection
    employee = await db.guards.find_one({"id": evaluation.employee_id})
    employee_name = None
    
    if employee:
        # Verify same condominium (multi-tenant isolation)
        if employee.get("condominium_id") != condominium_id:
            raise HTTPException(status_code=403, detail="No puedes evaluar empleados de otro condominio")
        employee_name = employee["user_name"]
        
        # Cannot evaluate yourself
        evaluator_guard = await db.guards.find_one({"user_id": current_user["id"]})
        if evaluator_guard and evaluator_guard["id"] == evaluation.employee_id:
            raise HTTPException(status_code=400, detail="No puedes evaluarte a ti mismo")
    else:
        # Try to find in users collection (for users with employee roles but no guard record)
        employee = await db.users.find_one({
            "id": evaluation.employee_id,
            "condominium_id": condominium_id,
            "roles": {"$in": ["Guarda", "Supervisor", "HR"]}
        })
        
        if not employee:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        
        employee_name = employee.get("full_name", "Unknown")
        
        # Cannot evaluate yourself
        if employee["id"] == current_user["id"]:
            raise HTTPException(status_code=400, detail="No puedes evaluarte a ti mismo")
    
    # Calculate average score
    categories = evaluation.categories
    avg_score = round((categories.discipline + categories.punctuality + 
                       categories.performance + categories.communication) / 4, 2)
    
    evaluation_doc = {
        "id": str(uuid.uuid4()),
        "employee_id": evaluation.employee_id,
        "employee_name": employee_name,
        "evaluator_id": current_user["id"],
        "evaluator_name": current_user.get("full_name", "Unknown"),
        "categories": {
            "discipline": categories.discipline,
            "punctuality": categories.punctuality,
            "performance": categories.performance,
            "communication": categories.communication
        },
        "score": avg_score,
        "comments": evaluation.comments,
        "condominium_id": condominium_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.hr_evaluations.insert_one(evaluation_doc)
    evaluation_doc.pop("_id", None)
    
    await log_audit_event(
        AuditEventType.EVALUATION_CREATED,
        current_user["id"],
        "hr",
        {
            "evaluation_id": evaluation_doc["id"],
            "employee_id": evaluation.employee_id,
            "employee_name": employee_name,
            "score": avg_score,
            "condominium_id": condominium_id
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return evaluation_doc

@api_router.get("/hr/evaluations")
async def get_evaluations(
    employee_id: Optional[str] = None,
    request: Request = None,
    current_user = Depends(require_module("hr"))
):
    """Get evaluations - HR/Admin sees all in condominium, employees see only their own"""
    user_roles = current_user.get("roles", [])
    condominium_id = current_user.get("condominium_id")
    
    # Build query based on role
    query = {"condominium_id": condominium_id}
    
    # Check if user is HR, Admin, Supervisor or SuperAdmin
    is_hr_or_admin = any(role in user_roles for role in ["Administrador", "HR", "Supervisor", "SuperAdmin"])
    
    if is_hr_or_admin:
        # HR/Admin can filter by employee or see all
        if employee_id:
            query["employee_id"] = employee_id
    else:
        # Regular employees (Guard) can only see their own evaluations
        guard = await db.guards.find_one({"user_id": current_user["id"]})
        if guard:
            query["employee_id"] = guard["id"]
        else:
            # No guard record = no evaluations
            return []
    
    evaluations = await db.hr_evaluations.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return evaluations

@api_router.get("/hr/evaluations/{evaluation_id}")
async def get_evaluation(
    evaluation_id: str,
    current_user = Depends(get_current_user)
):
    """Get a specific evaluation by ID"""
    evaluation = await db.hr_evaluations.find_one({"id": evaluation_id}, {"_id": 0})
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    
    # Check condominium access
    if evaluation.get("condominium_id") != current_user.get("condominium_id"):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta evaluación")
    
    user_roles = current_user.get("roles", [])
    is_hr_or_admin = any(role in user_roles for role in ["Administrador", "HR", "Supervisor", "SuperAdmin"])
    
    # If not HR/Admin, check if it's their own evaluation
    if not is_hr_or_admin:
        guard = await db.guards.find_one({"user_id": current_user["id"]})
        if not guard or evaluation["employee_id"] != guard["id"]:
            raise HTTPException(status_code=403, detail="Solo puedes ver tus propias evaluaciones")
    
    return evaluation

@api_router.get("/hr/evaluations/employee/{employee_id}/summary")
async def get_employee_evaluation_summary(
    employee_id: str,
    current_user = Depends(get_current_user)
):
    """Get evaluation summary for an employee (average scores, count, etc.)"""
    user_roles = current_user.get("roles", [])
    condominium_id = current_user.get("condominium_id")
    
    # Verify employee exists - check guards first, then users
    employee = await db.guards.find_one({"id": employee_id})
    employee_name = None
    
    if employee:
        if employee.get("condominium_id") != condominium_id:
            raise HTTPException(status_code=403, detail="No tienes acceso a este empleado")
        employee_name = employee["user_name"]
    else:
        # Try users collection
        employee = await db.users.find_one({
            "id": employee_id,
            "condominium_id": condominium_id,
            "roles": {"$in": ["Guarda", "Supervisor", "HR"]}
        })
        if not employee:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        employee_name = employee.get("full_name", "Unknown")
    
    # Check permissions - HR/Admin can see all, employees only their own
    is_hr_or_admin = any(role in user_roles for role in ["Administrador", "HR", "Supervisor", "SuperAdmin"])
    if not is_hr_or_admin:
        # Check if this is the current user's evaluation
        if employee_id != current_user["id"]:
            guard = await db.guards.find_one({"user_id": current_user["id"]})
            if not guard or guard["id"] != employee_id:
                raise HTTPException(status_code=403, detail="Solo puedes ver tus propias evaluaciones")
    
    # Get all evaluations for this employee
    evaluations = await db.hr_evaluations.find(
        {"employee_id": employee_id, "condominium_id": condominium_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    if not evaluations:
        return {
            "employee_id": employee_id,
            "employee_name": employee_name,
            "total_evaluations": 0,
            "average_score": 0,
            "category_averages": {
                "discipline": 0,
                "punctuality": 0,
                "performance": 0,
                "communication": 0
            },
            "last_evaluation": None,
            "evaluations": []
        }
    
    # Calculate averages
    total = len(evaluations)
    avg_score = round(sum(e["score"] for e in evaluations) / total, 2)
    
    category_averages = {
        "discipline": round(sum(e["categories"]["discipline"] for e in evaluations) / total, 2),
        "punctuality": round(sum(e["categories"]["punctuality"] for e in evaluations) / total, 2),
        "performance": round(sum(e["categories"]["performance"] for e in evaluations) / total, 2),
        "communication": round(sum(e["categories"]["communication"] for e in evaluations) / total, 2)
    }
    
    return {
        "employee_id": employee_id,
        "employee_name": employee_name,
        "total_evaluations": total,
        "average_score": avg_score,
        "category_averages": category_averages,
        "last_evaluation": evaluations[0]["created_at"] if evaluations else None,
        "evaluations": evaluations[:10]  # Last 10 evaluations
    }

@api_router.get("/hr/evaluable-employees")
async def get_evaluable_employees(
    current_user = Depends(require_role("Administrador", "HR", "Supervisor"))
):
    """Get all employees that can be evaluated (guards + users with employee roles)"""
    condominium_id = current_user.get("condominium_id")
    
    # Get guards from guards collection
    guards = await db.guards.find(
        {"condominium_id": condominium_id, "is_active": {"$ne": False}},
        {"_id": 0}
    ).to_list(100)
    
    # Get existing guard user IDs to avoid duplicates
    guard_user_ids = {g.get("user_id") for g in guards if g.get("user_id")}
    
    # Get users with employee roles that don't have guard records
    users = await db.users.find(
        {
            "condominium_id": condominium_id,
            "roles": {"$in": ["Guarda", "Supervisor", "HR"]},
            "is_active": {"$ne": False},
            "id": {"$nin": list(guard_user_ids)}
        },
        {"_id": 0, "id": 1, "full_name": 1, "email": 1, "roles": 1}
    ).to_list(100)
    
    # Convert users to employee format
    user_employees = [
        {
            "id": u["id"],
            "user_id": u["id"],
            "user_name": u.get("full_name", u.get("email", "Unknown")),
            "position": u.get("roles", ["Empleado"])[0] if u.get("roles") else "Empleado",
            "condominium_id": condominium_id,
            "is_active": True
        }
        for u in users
    ]
    
    # Combine and return
    all_employees = guards + user_employees
    return all_employees

# ==================== ADMIN USER MANAGEMENT ====================

@api_router.post("/admin/users")
async def create_user_by_admin(
    user_data: CreateUserByAdmin,
    request: Request,
    current_user = Depends(require_role("Administrador", "SuperAdmin"))
):
    """Admin creates a user (Resident, HR, Guard, etc.) with role-specific validation"""
    # CRITICAL: Normalize email to lowercase
    normalized_email = user_data.email.lower().strip()
    
    # Check email not in use
    existing = await db.users.find_one({"email": normalized_email})
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # Validate role
    valid_roles = ["Residente", "HR", "Guarda", "Supervisor", "Estudiante"]
    if user_data.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Rol inválido. Use: {', '.join(valid_roles)}")
    
    # Determine condominium_id early for billing check
    is_super_admin = "SuperAdmin" in current_user.get("roles", [])
    condominium_id = current_user.get("condominium_id")
    
    # If SuperAdmin without condo, use the one from the request
    if is_super_admin and not condominium_id:
        condominium_id = user_data.condominium_id
    
    if not condominium_id:
        raise HTTPException(status_code=400, detail="Se requiere condominium_id para crear usuarios")
    
    # ==================== SAAS BILLING ENFORCEMENT ====================
    # Check if we can create a new user based on paid seats (only for residents)
    can_create, error_msg = await can_create_user(condominium_id, user_data.role)
    if not can_create:
        # Log the blocked attempt
        await log_billing_event(
            "user_creation_blocked",
            condominium_id,
            {"reason": error_msg, "attempted_role": user_data.role, "attempted_email": normalized_email},
            current_user["id"]
        )
        raise HTTPException(status_code=403, detail=error_msg)
    # ==================================================================
    
    # Role-specific validation
    role_data = {}
    
    if user_data.role == "Residente":
        if not user_data.apartment_number:
            raise HTTPException(status_code=400, detail="Número de apartamento/casa es requerido para Residente")
        role_data = {
            "apartment_number": user_data.apartment_number,
            "tower_block": user_data.tower_block,
            "resident_type": user_data.resident_type or "owner"
        }
    
    elif user_data.role == "Guarda":
        if not user_data.badge_number:
            raise HTTPException(status_code=400, detail="Número de placa es requerido para Guarda")
        role_data = {
            "badge_number": user_data.badge_number,
            "main_location": user_data.main_location or "Entrada Principal",
            "initial_shift": user_data.initial_shift,
            "total_hours": 0
        }
        # Also create guard record
        guard_id = str(uuid.uuid4())
        guard_doc = {
            "id": guard_id,
            "email": normalized_email,
            "name": user_data.full_name,
            "badge": user_data.badge_number,
            "phone": user_data.phone,
            "condominium_id": condominium_id,  # Use the already-determined condominium_id
            "status": "active",
            "is_active": True,
            "location": user_data.main_location or "Entrada Principal",
            "rate": 15.0,
            "total_hours": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.guards.insert_one(guard_doc)
        role_data["guard_id"] = guard_id
    
    elif user_data.role == "HR":
        role_data = {
            "department": user_data.department or "Recursos Humanos",
            "permission_level": user_data.permission_level or "HR"
        }
    
    elif user_data.role == "Estudiante":
        role_data = {
            "subscription_plan": user_data.subscription_plan or "basic",
            "subscription_status": user_data.subscription_status or "trial",
            "enrolled_courses": []
        }
    
    elif user_data.role == "Supervisor":
        role_data = {
            "supervised_area": user_data.supervised_area or "General",
            "guard_assignments": user_data.guard_assignments or []
        }
    
    # Get condominium name and environment for email logic
    condo = await db.condominiums.find_one({"id": condominium_id}, {"_id": 0, "name": 1, "environment": 1, "is_demo": 1})
    condo_name = condo.get("name", "GENTURIX") if condo else "GENTURIX"
    
    # IMPORTANT: Use tenant environment instead of global DEV_MODE
    # Demo tenants: Don't send emails, show credentials in UI
    # Production tenants: Send emails via Resend
    tenant_is_demo = condo.get("environment", "production") == "demo" if condo else False
    # Fallback: if environment not set but is_demo is true, treat as demo
    if condo and condo.get("is_demo") and not tenant_is_demo:
        tenant_is_demo = True
    
    # Determine if we should send credentials email and generate temp password
    send_email = user_data.send_credentials_email
    password_to_use = user_data.password
    password_reset_required = False
    
    # Check if email sending is enabled (toggle)
    email_toggle_enabled = await is_email_enabled()
    
    # For DEMO tenants: Never send emails, always show credentials
    # For PRODUCTION tenants: Send emails if requested
    if tenant_is_demo:
        # Demo tenant: Don't send email, show credentials
        send_email = False
        password_reset_required = False
        show_password_in_response = True
    elif send_email:
        # Production tenant with email requested
        # Generate a temporary password if sending email
        password_to_use = generate_temporary_password()
        # Require password reset if email toggle is enabled (so user will receive the email)
        password_reset_required = email_toggle_enabled
        # Show password only if email toggle is disabled (email won't be sent)
        show_password_in_response = not email_toggle_enabled
    else:
        # Production tenant, no email requested
        password_reset_required = False
        show_password_in_response = True  # Show since no email will be sent
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": normalized_email,  # Use normalized email
        "hashed_password": hash_password(password_to_use),
        "full_name": user_data.full_name,
        "roles": [user_data.role],
        "condominium_id": condominium_id,
        "phone": user_data.phone,
        "is_active": True,
        "is_locked": False,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "role_data": role_data,  # Store role-specific data
        "password_reset_required": password_reset_required,
        "credentials_email_sent": False
    }
    
    await db.users.insert_one(user_doc)
    
    # ==================== UPDATE ACTIVE USER COUNT ====================
    await update_active_user_count(condominium_id)
    await log_billing_event(
        "user_created",
        condominium_id,
        {"user_id": user_id, "role": user_data.role, "email": normalized_email},
        current_user["id"]
    )
    # ==================================================================
    
    await log_audit_event(
        AuditEventType.USER_CREATED,
        current_user["id"],
        "admin",
        {
            "user_id": user_id, 
            "email": user_data.email, 
            "role": user_data.role,
            "role_data": role_data,
            "send_credentials_email": send_email
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    # Send credentials email if requested
    email_result = None
    if send_email:
        # Get the login URL from the request origin or use app subdomain
        origin = request.headers.get("origin", "https://app.genturix.com")
        login_url = f"{origin}/login"
        
        email_result = await send_credentials_email(
            recipient_email=user_data.email,
            user_name=user_data.full_name,
            role=user_data.role,
            condominium_name=condo_name,
            temporary_password=password_to_use,
            login_url=login_url
        )
        
        # Update user document with email status
        email_sent = email_result.get("status") == "success"
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"credentials_email_sent": email_sent}}
        )
        
        # Log email dispatch
        if email_sent:
            await log_audit_event(
                AuditEventType.CREDENTIALS_EMAIL_SENT,
                current_user["id"],
                "admin",
                {
                    "user_id": user_id,
                    "recipient_email": user_data.email,
                    "role": user_data.role,
                    "condominium_id": condominium_id
                },
                request.client.host if request.client else "unknown",
                request.headers.get("user-agent", "unknown")
            )
        else:
            await log_audit_event(
                AuditEventType.CREDENTIALS_EMAIL_FAILED,
                current_user["id"],
                "admin",
                {
                    "user_id": user_id,
                    "recipient_email": user_data.email,
                    "error": email_result.get("error", "Unknown error")
                },
                request.client.host if request.client else "unknown",
                request.headers.get("user-agent", "unknown")
            )
    
    response = {
        "message": f"Usuario {user_data.full_name} creado exitosamente",
        "user_id": user_id,
        "role": user_data.role,
        "role_data": role_data,
        "credentials": {
            "email": user_data.email,
            "password": password_to_use if show_password_in_response else "********",
            "show_password": show_password_in_response
        },
        "tenant_environment": "demo" if tenant_is_demo else "production",
        "email_toggle_enabled": email_toggle_enabled
    }
    
    # Add appropriate message based on tenant type
    if tenant_is_demo:
        response["demo_mode_notice"] = "Modo DEMO: Las credenciales se muestran en pantalla. Los emails no se envían."
    
    if send_email:
        response["email_status"] = email_result.get("status", "unknown")
        if email_result.get("status") == "success":
            response["email_message"] = f"Credenciales enviadas a {user_data.email}"
        elif email_result.get("status") == "skipped":
            if email_result.get("toggle_disabled"):
                response["email_message"] = "Envío de emails deshabilitado (modo pruebas) - credenciales mostradas en pantalla"
            else:
                response["email_message"] = "Servicio de email no configurado - credenciales no enviadas"
        else:
            response["email_message"] = f"Error al enviar email: {email_result.get('error', 'Unknown')}"
    
    return response

@api_router.get("/admin/users")
async def get_users_by_admin(
    role: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "SuperAdmin"))
):
    """Get users in admin's condominium"""
    query = {}
    
    # Filter by condominium for non-super-admins
    if "SuperAdmin" not in current_user.get("roles", []):
        query["condominium_id"] = current_user.get("condominium_id")
    
    if role:
        query["roles"] = role
    
    users = await db.users.find(query, {"_id": 0, "hashed_password": 0}).to_list(500)
    return users

# ==================== RESERVATIONS MODULE ====================

async def check_module_enabled(condo_id: str, module_name: str):
    """Helper to check if a module is enabled for a condominium"""
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "modules": 1})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    modules = condo.get("modules", {})
    module_config = modules.get(module_name, False)
    
    # Handle both boolean and dict formats
    is_enabled = False
    if isinstance(module_config, bool):
        is_enabled = module_config
    elif isinstance(module_config, dict):
        is_enabled = module_config.get("enabled", False)
    
    if not is_enabled:
        raise HTTPException(status_code=403, detail=f"Módulo '{module_name}' no está habilitado para este condominio")
    return True

@api_router.get("/reservations/areas")
async def get_areas(current_user = Depends(get_current_user)):
    """Get all areas for reservations in the user's condominium"""
    condo_id = current_user.get("condominium_id")
    if not condo_id and "SuperAdmin" not in current_user.get("roles", []):
        raise HTTPException(status_code=400, detail="Usuario no asignado a condominio")
    
    if condo_id:
        await check_module_enabled(condo_id, "reservations")
    
    # Use tenant_filter for automatic scoping
    query = tenant_filter(current_user, {"is_active": True})
    
    areas = await db.reservation_areas.find(query, {"_id": 0}).to_list(100)
    
    return areas

@api_router.post("/reservations/areas")
async def create_area(
    area_data: AreaCreate,
    request: Request,
    current_user = Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN))
):
    """Create a new area for reservations (Admin or SuperAdmin)"""
    # SuperAdmin can pass condominium_id, Admin uses their own
    condo_id = area_data.condominium_id if hasattr(area_data, 'condominium_id') and area_data.condominium_id else current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asignado a condominio")
    
    await check_module_enabled(condo_id, "reservations")
    
    area_id = str(uuid.uuid4())
    area_doc = {
        "id": area_id,
        "condominium_id": condo_id,
        "name": area_data.name,
        "area_type": area_data.area_type.value,
        "capacity": area_data.capacity,
        "description": area_data.description,
        "rules": area_data.rules,
        "available_from": area_data.available_from,
        "available_until": area_data.available_until,
        "requires_approval": area_data.requires_approval,
        "reservation_mode": area_data.reservation_mode,
        "min_duration_hours": area_data.min_duration_hours,
        "max_duration_hours": area_data.max_duration_hours,
        "max_reservations_per_day": area_data.max_reservations_per_day,
        "slot_duration_minutes": area_data.slot_duration_minutes,
        "allowed_days": area_data.allowed_days,
        "is_active": area_data.is_active,
        # NEW: Phase 1 fields (backward compatible defaults)
        "reservation_behavior": area_data.reservation_behavior or "exclusive",
        "max_capacity_per_slot": area_data.max_capacity_per_slot,
        "max_reservations_per_user_per_day": area_data.max_reservations_per_user_per_day,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.reservation_areas.insert_one(area_doc)
    
    await log_audit_event(
        AuditEventType.ACCESS_GRANTED,
        current_user["id"],
        "reservations",
        {"action": "area_created", "area_id": area_id, "name": area_data.name},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": f"Área '{area_data.name}' creada exitosamente", "area_id": area_id}

@api_router.patch("/reservations/areas/{area_id}")
async def update_area(
    area_id: str,
    area_data: AreaUpdate,
    request: Request,
    current_user = Depends(require_role("Administrador"))
):
    """Update an area (Admin only)"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asignado a condominio")
    
    # Check area exists and belongs to this condo
    area = await db.reservation_areas.find_one({"id": area_id, "condominium_id": condo_id})
    if not area:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    
    update_fields = {k: v for k, v in area_data.model_dump().items() if v is not None}
    if "area_type" in update_fields:
        update_fields["area_type"] = update_fields["area_type"].value
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.reservation_areas.update_one({"id": area_id}, {"$set": update_fields})
    
    await log_audit_event(
        AuditEventType.ACCESS_GRANTED,
        current_user["id"],
        "reservations",
        {"action": "area_updated", "area_id": area_id},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "Área actualizada exitosamente"}

@api_router.delete("/reservations/areas/{area_id}")
async def delete_area(
    area_id: str,
    request: Request,
    current_user = Depends(require_role("Administrador"))
):
    """Soft delete an area (Admin only)"""
    condo_id = current_user.get("condominium_id")
    
    result = await db.reservation_areas.update_one(
        {"id": area_id, "condominium_id": condo_id},
        {"$set": {"is_active": False, "deleted_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    
    await log_audit_event(
        AuditEventType.ACCESS_GRANTED,
        current_user["id"],
        "reservations",
        {"action": "area_deleted", "area_id": area_id},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "Área eliminada exitosamente"}

@api_router.get("/reservations")
async def get_reservations(
    date: Optional[str] = None,
    area_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Get reservations for the condominium"""
    condo_id = current_user.get("condominium_id")
    if not condo_id and "SuperAdmin" not in current_user.get("roles", []):
        raise HTTPException(status_code=400, detail="Usuario no asignado a condominio")
    
    if condo_id:
        await check_module_enabled(condo_id, "reservations")
    
    # Build extra filters
    extra = {}
    if date:
        extra["date"] = date
    if area_id:
        extra["area_id"] = area_id
    if status:
        extra["status"] = status
    
    # Use tenant_filter for automatic scoping
    query = tenant_filter(current_user, extra if extra else None)
    
    # Non-admins only see their own reservations
    if "Administrador" not in current_user.get("roles", []) and "Guarda" not in current_user.get("roles", []) and "SuperAdmin" not in current_user.get("roles", []):
        query["resident_id"] = current_user["id"]
    
    reservations = await db.reservations.find(query, {"_id": 0}).sort("date", 1).to_list(200)
    
    # Enrich with area and user info
    for res in reservations:
        area = await db.reservation_areas.find_one({"id": res.get("area_id")}, {"_id": 0, "name": 1, "area_type": 1})
        if area:
            res["area_name"] = area.get("name")
            res["area_type"] = area.get("area_type")
        user = await db.users.find_one({"id": res.get("resident_id")}, {"_id": 0, "full_name": 1, "profile_photo": 1})
        if user:
            res["resident_name"] = user.get("full_name")
            res["resident_photo"] = user.get("profile_photo")
    
    return reservations

# Day name mapping for validation
DAY_NAMES = {
    0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 
    4: "Viernes", 5: "Sábado", 6: "Domingo"
}

@api_router.post("/reservations")
async def create_reservation(
    reservation: ReservationCreate,
    request: Request,
    current_user = Depends(get_current_user)
):
    """Create a new reservation (Resident)"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asignado a condominio")
    
    await check_module_enabled(condo_id, "reservations")
    
    # Check area exists and is active
    area = await db.reservation_areas.find_one({"id": reservation.area_id, "condominium_id": condo_id, "is_active": True})
    if not area:
        raise HTTPException(status_code=404, detail="Área no encontrada o no disponible")
    
    # Check capacity
    if reservation.guests_count > area.get("capacity", 10):
        raise HTTPException(status_code=400, detail=f"El área solo permite {area['capacity']} personas")
    
    # Validate time is within area's available hours (closing time)
    area_from = area.get("available_from", "06:00")
    area_until = area.get("available_until", "22:00")
    if reservation.start_time < area_from or reservation.end_time > area_until:
        raise HTTPException(status_code=400, detail=f"El horario debe estar entre {area_from} y {area_until}. Cierra a las {area_until}.")
    
    # ==================== VALIDATE DURATION BASED ON AREA MODE ====================
    reservation_mode = area.get("reservation_mode", "flexible")
    min_duration = area.get("min_duration_hours", 1)
    max_duration = area.get("max_duration_hours", area.get("max_hours_per_reservation", 4))
    
    # Calculate reservation duration in hours
    try:
        start_parts = reservation.start_time.split(":")
        end_parts = reservation.end_time.split(":")
        start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
        end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
        duration_hours = (end_minutes - start_minutes) / 60
        
        if duration_hours < min_duration:
            raise HTTPException(status_code=400, detail=f"La reservación debe ser de al menos {min_duration} hora(s)")
        
        if duration_hours > max_duration:
            raise HTTPException(status_code=400, detail=f"La reservación no puede exceder {max_duration} hora(s)")
        
        # For "por_hora" mode (gym), enforce exactly 1 hour
        if reservation_mode == "por_hora" and duration_hours != 1:
            raise HTTPException(status_code=400, detail="Este tipo de área solo permite reservaciones de 1 hora")
        
        # For "bloque" mode (ranch), allow only full block
        if reservation_mode == "bloque":
            # Must be the full block from opening to closing
            expected_duration = (int(area_until.split(":")[0]) - int(area_from.split(":")[0]))
            if duration_hours != expected_duration:
                raise HTTPException(status_code=400, detail=f"Este tipo de área requiere reservar el bloque completo ({area_from} - {area_until})")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de hora inválido. Use HH:MM")
    # ==============================================================================
    
    # Validate day is allowed
    try:
        res_date = datetime.strptime(reservation.date, "%Y-%m-%d")
        day_name = DAY_NAMES.get(res_date.weekday())
        allowed_days = area.get("allowed_days", list(DAY_NAMES.values()))
        if allowed_days and len(allowed_days) > 0 and day_name not in allowed_days:
            raise HTTPException(status_code=400, detail=f"Esta área no está disponible los días {day_name}")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")
    
    # Check max reservations per day for this area
    max_per_day = area.get("max_reservations_per_day", 10)
    daily_count = await db.reservations.count_documents({
        "area_id": reservation.area_id,
        "date": reservation.date,
        "status": {"$in": ["pending", "approved"]}
    })
    if daily_count >= max_per_day:
        raise HTTPException(status_code=400, detail=f"Se alcanzó el límite de {max_per_day} reservaciones para esta área en esta fecha")
    
    # NEW: Check max reservations per user per day (Phase 1)
    max_user_per_day = area.get("max_reservations_per_user_per_day")
    if max_user_per_day:
        user_daily_count = await db.reservations.count_documents({
            "area_id": reservation.area_id,
            "date": reservation.date,
            "resident_id": current_user["id"],
            "status": {"$in": ["pending", "approved"]}
        })
        if user_daily_count >= max_user_per_day:
            raise HTTPException(status_code=400, detail=f"Has alcanzado el límite de {max_user_per_day} reservación(es) por día para esta área")
    
    # Get reservation behavior (backward compatible)
    behavior = area.get("reservation_behavior", "exclusive")
    
    # FREE_ACCESS areas cannot be reserved
    if behavior == "free_access":
        raise HTTPException(status_code=400, detail="Esta área es de acceso libre y no requiere reservación")
    
    # Check for overlapping reservations based on behavior type
    if behavior == "capacity":
        # CAPACITY: Check if there's room in the slot
        max_capacity = area.get("max_capacity_per_slot") or area.get("capacity", 10)
        
        # Get all reservations that overlap with requested time
        overlapping = await db.reservations.find({
            "area_id": reservation.area_id,
            "date": reservation.date,
            "status": {"$in": ["pending", "approved"]},
            "start_time": {"$lt": reservation.end_time},
            "end_time": {"$gt": reservation.start_time}
        }, {"_id": 0, "guests_count": 1}).to_list(100)
        
        current_count = sum(r.get("guests_count", 1) for r in overlapping)
        if current_count + reservation.guests_count > max_capacity:
            raise HTTPException(
                status_code=409, 
                detail=f"No hay suficiente capacidad. Disponible: {max(0, max_capacity - current_count)}, Solicitado: {reservation.guests_count}"
            )
    else:
        # EXCLUSIVE or SLOT_BASED: Check for any overlap
        existing = await db.reservations.find_one({
            "area_id": reservation.area_id,
            "date": reservation.date,
            "status": {"$in": ["pending", "approved"]},
            "$or": [
                {"start_time": {"$lt": reservation.end_time}, "end_time": {"$gt": reservation.start_time}}
            ]
        })
        
        if existing:
            raise HTTPException(status_code=409, detail="Ya existe una reservación en ese horario")
    
    reservation_id = str(uuid.uuid4())
    status = "pending" if area.get("requires_approval", False) else "approved"
    
    reservation_doc = {
        "id": reservation_id,
        "condominium_id": condo_id,
        "area_id": reservation.area_id,
        "resident_id": current_user["id"],
        "date": reservation.date,
        "start_time": reservation.start_time,
        "end_time": reservation.end_time,
        "purpose": reservation.purpose,
        "guests_count": reservation.guests_count,
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.reservations.insert_one(reservation_doc)
    
    # If auto-approved, send notification to resident
    if status == "approved":
        await create_and_send_notification(
            user_id=current_user["id"],
            condominium_id=condo_id,
            notification_type="reservation_approved",
            title="✅ Reservación confirmada",
            message=f"{area['name']} el {reservation.date} de {reservation.start_time} a {reservation.end_time}",
            data={
                "reservation_id": reservation_id,
                "area_name": area["name"],
                "date": reservation.date,
                "start_time": reservation.start_time,
                "end_time": reservation.end_time
            },
            send_push=True,
            url="/resident?tab=reservations"
        )
    else:
        # Notify admins about pending reservation using dynamic targeting
        await send_targeted_push_notification(
            condominium_id=condo_id,
            title="📅 Nueva reservación pendiente",
            body=f"{current_user.get('full_name', 'Residente')} solicitó {area['name']} para {reservation.date}",
            target_roles=["Administrador", "Supervisor"],
            data={
                "type": "reservation_pending",
                "reservation_id": reservation_id,
                "url": "/admin/reservations"
            },
            tag=f"reservation-pending-{reservation_id[:8]}"
        )
    
    await log_audit_event(
        AuditEventType.ACCESS_GRANTED,
        current_user["id"],
        "reservations",
        {"action": "reservation_created", "reservation_id": reservation_id, "area": area["name"], "date": reservation.date},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "message": "Reservación creada exitosamente",
        "reservation_id": reservation_id,
        "status": status,
        "requires_approval": area.get("requires_approval", False)
    }

@api_router.get("/reservations/availability/{area_id}")
async def get_area_availability(
    area_id: str,
    date: str,
    current_user = Depends(get_current_user)
):
    """Get availability for an area on a specific date"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asignado a condominio")
    
    # Get the area
    area = await db.reservation_areas.find_one({"id": area_id, "condominium_id": condo_id, "is_active": True})
    if not area:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    
    # Get existing reservations for this date
    existing = await db.reservations.find({
        "area_id": area_id,
        "date": date,
        "status": {"$in": ["pending", "approved"]}
    }, {"_id": 0, "start_time": 1, "end_time": 1, "status": 1}).to_list(50)
    
    # Check if day is allowed
    is_day_allowed = True
    day_name = None
    try:
        res_date = datetime.strptime(date, "%Y-%m-%d")
        day_name = DAY_NAMES.get(res_date.weekday())
        allowed_days = area.get("allowed_days", [])
        
        # If no allowed_days configured, all days are allowed
        if allowed_days and len(allowed_days) > 0:
            is_day_allowed = day_name in allowed_days
        else:
            is_day_allowed = True  # No restrictions = all days allowed
            
        # Also check if date is not in the past
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if res_date < today:
            is_day_allowed = False
    except ValueError:
        is_day_allowed = False
    
    # Check max reservations per day
    max_per_day = area.get("max_reservations_per_day", 10)
    reservations_count = len([r for r in existing if r.get("status") == "approved"])
    slots_remaining = max(0, max_per_day - reservations_count)
    
    # Calculate if area is available for reservation
    # Available if: day is allowed AND there are slots remaining
    is_available = is_day_allowed and slots_remaining > 0
    
    # Get operating hours
    available_from = area.get("available_from", "06:00")
    available_until = area.get("available_until", "22:00")
    
    # Generate time slots for the day
    time_slots = []
    try:
        start_hour = int(available_from.split(":")[0])
        end_hour = int(available_until.split(":")[0])
        
        for hour in range(start_hour, end_hour):
            slot_start = f"{str(hour).zfill(2)}:00"
            slot_end = f"{str(hour + 1).zfill(2)}:00"
            
            # Check if this slot is occupied
            slot_occupied = False
            for res in existing:
                res_start = res.get("start_time", "")
                res_end = res.get("end_time", "")
                # Check overlap
                if res_start <= slot_start < res_end or res_start < slot_end <= res_end:
                    slot_occupied = True
                    break
                if slot_start <= res_start < slot_end:
                    slot_occupied = True
                    break
            
            time_slots.append({
                "start_time": slot_start,
                "end_time": slot_end,
                "status": "occupied" if slot_occupied else "available"
            })
    except:
        pass  # If time parsing fails, return empty slots
    
    # Get area configuration for frontend
    reservation_mode = area.get("reservation_mode", "flexible")
    min_duration = area.get("min_duration_hours", 1)
    max_duration = area.get("max_duration_hours", area.get("max_hours_per_reservation", 4))
    slot_duration = area.get("slot_duration_minutes", 60)
    
    return {
        "area_id": area_id,
        "area_name": area.get("name"),
        "area_type": area.get("area_type"),
        "date": date,
        "day_name": day_name,
        "is_day_allowed": is_day_allowed,
        "is_available": is_available,
        "available_from": available_from,
        "available_until": available_until,
        "capacity": area.get("capacity", 10),
        "max_reservations_per_day": max_per_day,
        "current_reservations": reservations_count,
        "slots_remaining": slots_remaining,
        "reserved_slots": existing,
        "time_slots": time_slots,
        # New: Area configuration for UI
        "reservation_mode": reservation_mode,
        "min_duration_hours": min_duration,
        "max_duration_hours": max_duration,
        "slot_duration_minutes": slot_duration,
        "message": None if is_available else (
            "Fecha no disponible (día no permitido)" if not is_day_allowed else
            "No hay espacios disponibles para esta fecha"
        )
    }


# ============================================
# NEW: SMART AVAILABILITY ENDPOINT (Phase 2-3)
# Returns detailed slot availability based on area behavior type
# ============================================
@api_router.get("/reservations/smart-availability/{area_id}")
async def get_smart_availability(
    area_id: str,
    date: str,
    current_user = Depends(get_current_user)
):
    """
    Get smart availability for an area based on its reservation_behavior type.
    Returns detailed slots with remaining capacity for CAPACITY type areas.
    Backward compatible: areas without reservation_behavior use EXCLUSIVE logic.
    """
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asignado a condominio")
    
    # Get the area
    area = await db.reservation_areas.find_one({"id": area_id, "condominium_id": condo_id, "is_active": True})
    if not area:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    
    # Get reservation behavior (default to EXCLUSIVE for backward compatibility)
    behavior = area.get("reservation_behavior", "exclusive")
    
    # FREE_ACCESS areas cannot be reserved
    if behavior == "free_access":
        return {
            "area_id": area_id,
            "area_name": area.get("name"),
            "reservation_behavior": behavior,
            "date": date,
            "is_available": False,
            "message": "Esta área es de acceso libre y no requiere reservación",
            "time_slots": []
        }
    
    # Parse and validate date
    try:
        res_date = datetime.strptime(date, "%Y-%m-%d")
        day_name = DAY_NAMES.get(res_date.weekday())
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Check if date is in the past
        if res_date < today:
            return {
                "area_id": area_id,
                "area_name": area.get("name"),
                "reservation_behavior": behavior,
                "date": date,
                "is_available": False,
                "message": "No se pueden hacer reservaciones en fechas pasadas",
                "time_slots": []
            }
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")
    
    # Check if day is allowed
    allowed_days = area.get("allowed_days", [])
    if allowed_days and len(allowed_days) > 0 and day_name not in allowed_days:
        return {
            "area_id": area_id,
            "area_name": area.get("name"),
            "reservation_behavior": behavior,
            "date": date,
            "day_name": day_name,
            "is_available": False,
            "message": f"El área no está disponible los {day_name}",
            "time_slots": []
        }
    
    # Get existing reservations for this date
    existing_reservations = await db.reservations.find({
        "area_id": area_id,
        "date": date,
        "status": {"$in": ["pending", "approved"]}
    }, {"_id": 0}).to_list(100)
    
    # Check user's reservations for this day (for max_reservations_per_user_per_day)
    max_user_per_day = area.get("max_reservations_per_user_per_day")
    user_reservations_today = 0
    if max_user_per_day:
        user_reservations_today = await db.reservations.count_documents({
            "area_id": area_id,
            "date": date,
            "resident_id": current_user["id"],
            "status": {"$in": ["pending", "approved"]}
        })
    
    user_can_reserve = max_user_per_day is None or user_reservations_today < max_user_per_day
    
    # Get operating hours
    available_from = area.get("available_from", "06:00")
    available_until = area.get("available_until", "22:00")
    slot_duration = area.get("slot_duration_minutes", 60)
    
    # Parse hours
    try:
        start_hour = int(available_from.split(":")[0])
        start_min = int(available_from.split(":")[1]) if ":" in available_from else 0
        end_hour = int(available_until.split(":")[0])
        end_min = int(available_until.split(":")[1]) if ":" in available_until else 0
    except:
        start_hour, start_min = 6, 0
        end_hour, end_min = 22, 0
    
    # Generate time slots based on behavior type
    time_slots = []
    
    if behavior == "exclusive":
        # EXCLUSIVE: 1 reservation blocks the entire area for that time
        current_time = start_hour * 60 + start_min
        end_time = end_hour * 60 + end_min
        
        while current_time < end_time:
            slot_start = f"{current_time // 60:02d}:{current_time % 60:02d}"
            slot_end_mins = min(current_time + slot_duration, end_time)
            slot_end = f"{slot_end_mins // 60:02d}:{slot_end_mins % 60:02d}"
            
            # Check if this slot overlaps with any existing reservation
            slot_occupied = False
            occupied_by = None
            for res in existing_reservations:
                res_start = res.get("start_time", "")
                res_end = res.get("end_time", "")
                # Check overlap
                if res_start < slot_end and res_end > slot_start:
                    slot_occupied = True
                    occupied_by = res.get("status")
                    break
            
            time_slots.append({
                "start": slot_start,
                "end": slot_end,
                "available": not slot_occupied and user_can_reserve,
                "status": "occupied" if slot_occupied else ("available" if user_can_reserve else "user_limit"),
                "remaining_slots": 0 if slot_occupied else 1,
                "total_capacity": 1
            })
            
            current_time += slot_duration
    
    elif behavior == "capacity":
        # CAPACITY: Multiple reservations allowed up to max_capacity_per_slot
        max_capacity = area.get("max_capacity_per_slot") or area.get("capacity", 10)
        current_time = start_hour * 60 + start_min
        end_time = end_hour * 60 + end_min
        
        while current_time < end_time:
            slot_start = f"{current_time // 60:02d}:{current_time % 60:02d}"
            slot_end_mins = min(current_time + slot_duration, end_time)
            slot_end = f"{slot_end_mins // 60:02d}:{slot_end_mins % 60:02d}"
            
            # Count reservations in this slot
            slot_reservations = 0
            for res in existing_reservations:
                res_start = res.get("start_time", "")
                res_end = res.get("end_time", "")
                # Check overlap
                if res_start < slot_end and res_end > slot_start:
                    slot_reservations += res.get("guests_count", 1)
            
            remaining = max(0, max_capacity - slot_reservations)
            slot_available = remaining > 0 and user_can_reserve
            
            # Determine status
            if remaining == 0:
                status = "full"
            elif remaining <= max_capacity * 0.3:
                status = "limited"  # Yellow - few spots left
            else:
                status = "available"
            
            if not user_can_reserve:
                status = "user_limit"
            
            time_slots.append({
                "start": slot_start,
                "end": slot_end,
                "available": slot_available,
                "status": status,
                "remaining_slots": remaining,
                "total_capacity": max_capacity,
                "current_count": slot_reservations
            })
            
            current_time += slot_duration
    
    elif behavior == "slot_based":
        # SLOT_BASED: Fixed slots, 1 reservation = 1 slot, no overlap allowed
        current_time = start_hour * 60 + start_min
        end_time = end_hour * 60 + end_min
        
        while current_time < end_time:
            slot_start = f"{current_time // 60:02d}:{current_time % 60:02d}"
            slot_end_mins = min(current_time + slot_duration, end_time)
            slot_end = f"{slot_end_mins // 60:02d}:{slot_end_mins % 60:02d}"
            
            # Check if exact slot is taken
            slot_taken = False
            for res in existing_reservations:
                if res.get("start_time") == slot_start and res.get("end_time") == slot_end:
                    slot_taken = True
                    break
            
            time_slots.append({
                "start": slot_start,
                "end": slot_end,
                "available": not slot_taken and user_can_reserve,
                "status": "occupied" if slot_taken else ("available" if user_can_reserve else "user_limit"),
                "remaining_slots": 0 if slot_taken else 1,
                "total_capacity": 1
            })
            
            current_time += slot_duration
    
    # Calculate overall availability
    available_slots = sum(1 for s in time_slots if s["available"])
    is_available = available_slots > 0
    
    # Build response
    return {
        "area_id": area_id,
        "area_name": area.get("name"),
        "area_type": area.get("area_type"),
        "reservation_behavior": behavior,
        "date": date,
        "day_name": day_name,
        "is_day_allowed": True,  # If we got here, day is allowed
        "is_available": is_available,
        "available_from": available_from,
        "available_until": available_until,
        "capacity": area.get("capacity", 10),
        "max_capacity_per_slot": area.get("max_capacity_per_slot"),
        "slot_duration_minutes": slot_duration,
        "time_slots": time_slots,
        "available_slots_count": available_slots,
        "total_slots_count": len(time_slots),
        # User limits info
        "user_reservations_today": user_reservations_today,
        "max_reservations_per_user_per_day": max_user_per_day,
        "user_can_reserve": user_can_reserve,
        # Area config for UI
        "min_duration_hours": area.get("min_duration_hours", 1),
        "max_duration_hours": area.get("max_duration_hours", 4),
        "requires_approval": area.get("requires_approval", False),
        "message": None if is_available else (
            "Has alcanzado el límite de reservaciones por día" if not user_can_reserve else
            "No hay espacios disponibles para esta fecha"
        )
    }


@api_router.patch("/reservations/{reservation_id}")
async def update_reservation_status(
    reservation_id: str,
    update: ReservationUpdate,
    request: Request,
    current_user = Depends(get_current_user)
):
    """Update reservation status (Admin approves/rejects, Resident cancels own)"""
    is_admin = "Administrador" in current_user.get("roles", []) or "SuperAdmin" in current_user.get("roles", [])
    
    # Use get_tenant_resource for tenant validation
    reservation = await get_tenant_resource(db.reservations, reservation_id, current_user)
    
    # Non-admin can only cancel their own reservations
    if not is_admin:
        if update.status != ReservationStatusEnum.CANCELLED:
            raise HTTPException(status_code=403, detail="Solo puedes cancelar tus propias reservaciones")
        if reservation.get("resident_id") != current_user["id"]:
            raise HTTPException(status_code=403, detail="No puedes modificar reservaciones de otros usuarios")
    
    update_fields = {
        "status": update.status.value,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["id"]
    }
    
    if update.admin_notes:
        update_fields["admin_notes"] = update.admin_notes
    
    await db.reservations.update_one({"id": reservation_id}, {"$set": update_fields})
    
    # Send push notification to resident based on new status
    resident_id = reservation.get("resident_id")
    condominium_id = reservation.get("condominium_id")  # Get condo_id from reservation
    area_id = reservation.get("area_id")
    area = await db.reservation_areas.find_one({"id": area_id}, {"_id": 0, "name": 1})
    area_name = area.get("name", "Área común") if area else "Área común"
    
    if resident_id and is_admin:
        if update.status == ReservationStatusEnum.APPROVED:
            await create_and_send_notification(
                user_id=resident_id,
                condominium_id=condominium_id,
                notification_type="reservation_approved",
                title="✅ Reservación aprobada",
                message=f"Tu reservación de {area_name} para el {reservation.get('date')} de {reservation.get('start_time')} a {reservation.get('end_time')} fue aprobada",
                data={
                    "reservation_id": reservation_id,
                    "area_name": area_name,
                    "date": reservation.get("date"),
                    "start_time": reservation.get("start_time"),
                    "end_time": reservation.get("end_time")
                },
                send_push=False,  # Disable old push, use targeted instead
                url="/resident?tab=reservations"
            )
            
            # PHASE 3: Send targeted push notification to resident owner
            await send_targeted_push_notification(
                condominium_id=condominium_id,
                title="✅ Reservación aprobada",
                body=f"Tu reservación de {area_name} para el {reservation.get('date')} fue aprobada",
                target_user_ids=[resident_id],
                exclude_user_ids=[current_user["id"]],
                data={
                    "type": "reservation_approved",
                    "reservation_id": reservation_id,
                    "area_name": area_name,
                    "date": reservation.get("date"),
                    "start_time": reservation.get("start_time"),
                    "end_time": reservation.get("end_time"),
                    "url": "/resident?tab=reservations"
                },
                tag=f"reservation-approved-{reservation_id[:8]}"
            )
        elif update.status == ReservationStatusEnum.REJECTED:
            reason = update.admin_notes or "Sin motivo especificado"
            await create_and_send_notification(
                user_id=resident_id,
                condominium_id=condominium_id,
                notification_type="reservation_rejected",
                title="❌ Reservación rechazada",
                message=f"Tu reservación de {area_name} fue rechazada. Motivo: {reason}",
                data={
                    "reservation_id": reservation_id,
                    "area_name": area_name,
                    "date": reservation.get("date"),
                    "reason": reason
                },
                send_push=False,  # Disable old push, use targeted instead
                url="/resident?tab=reservations"
            )
            
            # Send targeted push notification to resident owner for rejection too
            await send_targeted_push_notification(
                condominium_id=condominium_id,
                title="❌ Reservación rechazada",
                body=f"Tu reservación de {area_name} fue rechazada. Motivo: {reason}",
                target_user_ids=[resident_id],
                exclude_user_ids=[current_user["id"]],
                data={
                    "type": "reservation_rejected",
                    "reservation_id": reservation_id,
                    "area_name": area_name,
                    "date": reservation.get("date"),
                    "reason": reason,
                    "url": "/resident?tab=reservations"
                },
                tag=f"reservation-rejected-{reservation_id[:8]}"
            )
    
    await log_audit_event(
        AuditEventType.ACCESS_GRANTED,
        current_user["id"],
        "reservations",
        {"action": "reservation_updated", "reservation_id": reservation_id, "new_status": update.status.value},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": f"Reservación {update.status.value} exitosamente"}


# ==================== DELETE RESERVATION (CANCEL) ====================
class CancelReservationRequest(BaseModel):
    """Request body for cancellation with optional reason"""
    reason: Optional[str] = None

@api_router.delete("/reservations/{reservation_id}")
async def cancel_reservation(
    reservation_id: str,
    request: Request,
    body: Optional[CancelReservationRequest] = None,
    current_user = Depends(get_current_user)
):
    """
    Cancel a reservation (soft delete - changes status to 'cancelled')
    
    RULES:
    - Resident: Can only cancel their OWN reservations that are pending/approved and NOT yet started
    - Admin: Can cancel ANY reservation except 'completed' ones
    
    This endpoint liberates the slot so others can book it.
    """
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asignado a condominio")
    
    await check_module_enabled(condo_id, "reservations")
    
    user_roles = current_user.get("roles", [])
    is_admin = "Administrador" in user_roles or "SuperAdmin" in user_roles
    
    # Find the reservation
    reservation = await db.reservations.find_one({"id": reservation_id, "condominium_id": condo_id}, {"_id": 0})
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservación no encontrada")
    
    current_status = reservation.get("status", "")
    reservation_date = reservation.get("date", "")
    reservation_start = reservation.get("start_time", "00:00")
    resident_id = reservation.get("resident_id")
    
    # Get area info for notification
    area = await db.reservation_areas.find_one({"id": reservation.get("area_id")}, {"_id": 0, "name": 1})
    area_name = area.get("name", "Área común") if area else "Área común"
    
    # ==================== VALIDATION RULES ====================
    
    # Rule: Cannot cancel completed reservations (for anyone)
    if current_status == "completed":
        raise HTTPException(status_code=400, detail="No se puede cancelar una reservación ya completada")
    
    # Rule: Cannot cancel already cancelled reservations
    if current_status == "cancelled":
        raise HTTPException(status_code=400, detail="Esta reservación ya fue cancelada")
    
    # ==================== RESIDENT-SPECIFIC RULES ====================
    if not is_admin:
        # Resident can only cancel their own reservations
        if reservation.get("resident_id") != current_user["id"]:
            raise HTTPException(status_code=403, detail="Solo puedes cancelar tus propias reservaciones")
        
        # Resident can only cancel pending or approved reservations
        if current_status not in ["pending", "approved"]:
            raise HTTPException(status_code=400, detail="Solo puedes cancelar reservaciones pendientes o aprobadas")
        
        # Resident cannot cancel if reservation has already started
        try:
            now = datetime.now(timezone.utc)
            res_datetime_str = f"{reservation_date}T{reservation_start}"
            res_start_dt = datetime.fromisoformat(res_datetime_str).replace(tzinfo=timezone.utc)
            
            if now >= res_start_dt:
                raise HTTPException(
                    status_code=400, 
                    detail="No puedes cancelar una reservación que ya inició o está en progreso"
                )
        except ValueError:
            # If date parsing fails, allow cancellation (fail-safe)
            pass
    
    # ==================== ADMIN-SPECIFIC RULES ====================
    # Admins can cancel any reservation except completed ones (already checked above)
    
    # ==================== PERFORM CANCELLATION ====================
    cancellation_reason = body.reason if body else None
    
    update_fields = {
        "status": "cancelled",
        "cancelled_at": datetime.now(timezone.utc).isoformat(),
        "cancelled_by": current_user["id"],
        "cancelled_by_role": "Administrador" if is_admin else "Residente",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["id"]
    }
    
    if cancellation_reason:
        update_fields["cancellation_reason"] = cancellation_reason
    
    await db.reservations.update_one({"id": reservation_id}, {"$set": update_fields})
    
    # ==================== NOTIFICATIONS ====================
    # If admin cancels resident's reservation, notify the resident
    if is_admin and resident_id and resident_id != current_user["id"]:
        reason_text = cancellation_reason or "Sin motivo especificado"
        await create_and_send_notification(
            user_id=resident_id,
            condominium_id=condo_id,
            notification_type="reservation_cancelled",
            title="❌ Reservación cancelada",
            message=f"Tu reservación de {area_name} para el {reservation_date} fue cancelada por el administrador. Motivo: {reason_text}",
            data={
                "reservation_id": reservation_id,
                "area_name": area_name,
                "date": reservation_date,
                "cancelled_by": "admin",
                "reason": reason_text
            },
            send_push=True,
            url="/resident?tab=reservations"
        )
    
    # ==================== AUDIT LOG ====================
    await log_audit_event(
        AuditEventType.ACCESS_GRANTED,
        current_user["id"],
        "reservations",
        {
            "action": "reservation_cancelled",
            "reservation_id": reservation_id,
            "area": area_name,
            "date": reservation_date,
            "cancelled_by_role": "admin" if is_admin else "resident",
            "reason": cancellation_reason
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "message": "Reservación cancelada exitosamente. El espacio ha sido liberado.",
        "reservation_id": reservation_id,
        "cancelled_by": "admin" if is_admin else "resident"
    }


@api_router.get("/reservations/today")
async def get_today_reservations(current_user = Depends(get_current_user)):
    """Get today's reservations for guard view"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asignado a condominio")
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    reservations = await db.reservations.find(
        {"condominium_id": condo_id, "date": today, "status": "approved"},
        {"_id": 0}
    ).sort("start_time", 1).to_list(50)
    
    # Enrich with area and user info
    for res in reservations:
        area = await db.reservation_areas.find_one({"id": res.get("area_id")}, {"_id": 0, "name": 1, "area_type": 1})
        if area:
            res["area_name"] = area.get("name")
            res["area_type"] = area.get("area_type")
        user = await db.users.find_one({"id": res.get("resident_id")}, {"_id": 0, "full_name": 1, "profile_photo": 1})
        if user:
            res["resident_name"] = user.get("full_name")
            res["resident_photo"] = user.get("profile_photo")
    
    return reservations

# ==================== SCHOOL MODULE ====================
@api_router.post("/school/courses")
async def create_course(course: CourseCreate, request: Request, current_user = Depends(require_role("Administrador"))):
    course_doc = {
        "id": str(uuid.uuid4()),
        "title": course.title,
        "description": course.description,
        "duration_hours": course.duration_hours,
        "instructor": course.instructor,
        "category": course.category,
        "lessons": [],
        "enrolled_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.courses.insert_one(course_doc)
    return course_doc

@api_router.get("/school/courses")
async def get_courses(current_user = Depends(get_current_user)):
    courses = await db.courses.find({}, {"_id": 0}).to_list(100)
    return courses

@api_router.get("/school/courses/{course_id}")
async def get_course(course_id: str, current_user = Depends(get_current_user)):
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@api_router.post("/school/enroll")
async def enroll_course(enrollment: EnrollmentCreate, request: Request, current_user = Depends(get_current_user)):
    course = await db.courses.find_one({"id": enrollment.course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    existing = await db.enrollments.find_one({
        "course_id": enrollment.course_id,
        "student_id": enrollment.student_id
    })
    if existing:
        raise HTTPException(status_code=409, detail="Already enrolled")
    
    enrollment_doc = {
        "id": str(uuid.uuid4()),
        "course_id": enrollment.course_id,
        "course_title": course["title"],
        "student_id": enrollment.student_id,
        "student_name": current_user["full_name"],
        "progress": 0,
        "completed_lessons": [],
        "enrolled_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "certificate_id": None
    }
    
    await db.enrollments.insert_one(enrollment_doc)
    await db.courses.update_one({"id": enrollment.course_id}, {"$inc": {"enrolled_count": 1}})
    
    await log_audit_event(
        AuditEventType.COURSE_ENROLLED,
        current_user["id"],
        "school",
        {"course_id": enrollment.course_id, "course_title": course["title"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return enrollment_doc

@api_router.get("/school/enrollments")
async def get_my_enrollments(current_user = Depends(get_current_user)):
    enrollments = await db.enrollments.find({"student_id": current_user["id"]}, {"_id": 0}).to_list(100)
    return enrollments

@api_router.get("/school/certificates")
async def get_certificates(current_user = Depends(get_current_user)):
    certificates = await db.certificates.find({"student_id": current_user["id"]}, {"_id": 0}).to_list(100)
    return certificates

@api_router.get("/school/student-progress/{student_id}")
async def get_student_progress(student_id: str, current_user = Depends(get_current_user)):
    if current_user["id"] != student_id and "Administrador" not in current_user["roles"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    enrollments = await db.enrollments.find({"student_id": student_id}, {"_id": 0}).to_list(100)
    certificates = await db.certificates.find({"student_id": student_id}, {"_id": 0}).to_list(100)
    
    return {
        "enrollments": enrollments,
        "certificates": certificates,
        "total_courses": len(enrollments),
        "completed_courses": len([e for e in enrollments if e.get("completed_at")]),
        "total_certificates": len(certificates)
    }

# ==================== PAYMENTS MODULE ====================
# GENTURIX PRICING MODEL: $1 per user per month
# Simple, accessible, massive adoption model

class UserSubscriptionCreate(BaseModel):
    user_count: int = 1

# ==================== PRICING SYSTEM (SaaS) ====================
# Default fallback price - used ONLY if database config is missing
FALLBACK_PRICE_PER_SEAT = 1.50
DEFAULT_CURRENCY = "USD"

async def ensure_global_pricing_config():
    """
    Ensure global pricing configuration exists in database.
    Called on startup to initialize default config if missing.
    """
    existing = await db.system_config.find_one({"id": "global_pricing"})
    if not existing:
        default_config = {
            "id": "global_pricing",
            "default_seat_price": FALLBACK_PRICE_PER_SEAT,
            "currency": DEFAULT_CURRENCY,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.system_config.insert_one(default_config)
        logger.info(f"[PRICING] Global pricing config initialized: ${FALLBACK_PRICE_PER_SEAT}/seat")

async def get_global_pricing() -> dict:
    """
    Get global pricing configuration from database.
    Returns: {"default_seat_price": float, "currency": str}
    """
    config = await db.system_config.find_one({"id": "global_pricing"}, {"_id": 0})
    if config:
        return {
            "default_seat_price": config.get("default_seat_price", FALLBACK_PRICE_PER_SEAT),
            "currency": config.get("currency", DEFAULT_CURRENCY)
        }
    # Fallback if config missing (should not happen after startup)
    return {
        "default_seat_price": FALLBACK_PRICE_PER_SEAT,
        "currency": DEFAULT_CURRENCY
    }

async def get_effective_seat_price(condominium_id: str) -> float:
    """
    PHASE 2: Get effective seat price for a condominium.
    
    Logic:
    1. Look up condominium's seat_price_override
    2. If override exists and > 0 → return override
    3. If not → return global default_seat_price
    4. If nothing found → safe fallback = 1.50
    
    NEVER hardcode price in endpoints. Always use this function.
    """
    # Step 1: Check condominium for override
    if condominium_id:
        condo = await db.condominiums.find_one(
            {"id": condominium_id},
            {"_id": 0, "seat_price_override": 1}
        )
        if condo:
            override = condo.get("seat_price_override")
            if override is not None and override > 0:
                logger.debug(f"[PRICING] Using override ${override}/seat for condo {condominium_id[:8]}...")
                return float(override)
    
    # Step 2: Get global default
    global_config = await get_global_pricing()
    return global_config["default_seat_price"]

async def get_condominium_pricing_info(condominium_id: str) -> dict:
    """
    Get complete pricing info for a condominium.
    Returns: {"effective_price": float, "uses_override": bool, "override_price": float|None, "global_price": float, "currency": str}
    """
    global_config = await get_global_pricing()
    
    override_price = None
    uses_override = False
    
    if condominium_id:
        condo = await db.condominiums.find_one(
            {"id": condominium_id},
            {"_id": 0, "seat_price_override": 1}
        )
        if condo and condo.get("seat_price_override") is not None and condo.get("seat_price_override") > 0:
            override_price = condo.get("seat_price_override")
            uses_override = True
    
    effective_price = override_price if uses_override else global_config["default_seat_price"]
    
    return {
        "effective_price": effective_price,
        "uses_override": uses_override,
        "override_price": override_price,
        "global_price": global_config["default_seat_price"],
        "currency": global_config["currency"]
    }

# Legacy constant for backward compatibility (will be replaced with dynamic pricing)
GENTURIX_PRICE_PER_USER = 1.00  # DEPRECATED: Use get_effective_seat_price() instead

async def calculate_subscription_price_dynamic(user_count: int, condominium_id: str) -> dict:
    """
    PHASE 4: Calculate price using dynamic pricing system.
    Returns: {"total": float, "price_per_seat": float, "currency": str}
    """
    price_per_seat = await get_effective_seat_price(condominium_id)
    total = round(user_count * price_per_seat, 2)
    global_config = await get_global_pricing()
    
    return {
        "total": total,
        "price_per_seat": price_per_seat,
        "currency": global_config["currency"]
    }

def calculate_subscription_price(user_count: int) -> float:
    """DEPRECATED: Use calculate_subscription_price_dynamic() instead"""
    return round(user_count * GENTURIX_PRICE_PER_USER, 2)

# ==================== BILLING ENGINE ====================
# Central billing calculation and event logging system
# Independent of payment providers (Stripe, Sinpe, TicoPay, Manual)

YEARLY_DISCOUNT_PERCENT = 10.0  # 10% discount for yearly billing (default)

async def calculate_invoice(
    condominium: dict, 
    billing_cycle: str = None,
    seat_price_override: float = None,
    yearly_discount_override: float = None
) -> dict:
    """
    BILLING ENGINE: Central invoice calculation function.
    
    This is the single source of truth for all billing calculations.
    Used by: Stripe integration, manual billing, reports, upgrade/downgrade
    
    Args:
        condominium: Dict with condominium data (must have 'id', 'paid_seats')
        billing_cycle: Override billing cycle (defaults to condominium's cycle)
        seat_price_override: Custom price per seat (for preview/onboarding)
        yearly_discount_override: Custom yearly discount 0-50% (for preview/onboarding)
    
    Returns:
        {
            "seats": int,
            "price_per_seat": float,
            "billing_cycle": str,
            "monthly_amount": float,
            "yearly_amount": float,
            "yearly_discount_percent": float,
            "effective_amount": float,
            "next_billing_date": str,
            "currency": str
        }
    """
    condo_id = condominium.get("id")
    seats = condominium.get("paid_seats", 10)
    cycle = billing_cycle or condominium.get("billing_cycle", "monthly")
    
    # Get effective price (override > condo override > global > fallback)
    if seat_price_override is not None and seat_price_override > 0:
        price_per_seat = seat_price_override
    else:
        price_per_seat = await get_effective_seat_price(condo_id)
    
    global_config = await get_global_pricing()
    
    # Get effective discount (override > condo override > global)
    if yearly_discount_override is not None and 0 <= yearly_discount_override <= 50:
        discount_percent = yearly_discount_override
    else:
        # Check if condo has custom discount
        if condo_id:
            condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "yearly_discount_percent": 1})
            if condo and condo.get("yearly_discount_percent") is not None:
                discount_percent = condo.get("yearly_discount_percent")
            else:
                discount_percent = YEARLY_DISCOUNT_PERCENT
        else:
            discount_percent = YEARLY_DISCOUNT_PERCENT
    
    # Calculate amounts
    monthly_amount = round(seats * price_per_seat, 2)
    yearly_amount_before_discount = monthly_amount * 12
    yearly_discount = round(yearly_amount_before_discount * (discount_percent / 100), 2)
    yearly_amount = round(yearly_amount_before_discount - yearly_discount, 2)
    
    # Effective amount based on cycle
    effective_amount = yearly_amount if cycle == "yearly" else monthly_amount
    
    # Calculate next billing date
    now = datetime.now(timezone.utc)
    if cycle == "yearly":
        next_billing = now + timedelta(days=365)
    else:
        # Next month, same day
        if now.month == 12:
            next_billing = now.replace(year=now.year + 1, month=1)
        else:
            next_billing = now.replace(month=now.month + 1)
    
    return {
        "seats": seats,
        "price_per_seat": price_per_seat,
        "billing_cycle": cycle,
        "monthly_amount": monthly_amount,
        "yearly_amount": yearly_amount,
        "yearly_amount_before_discount": yearly_amount_before_discount,
        "yearly_discount_percent": discount_percent,
        "yearly_discount_amount": yearly_discount,
        "effective_amount": effective_amount,
        "next_billing_date": next_billing.isoformat(),
        "currency": global_config.get("currency", "USD")
    }

async def calculate_billing_preview(
    initial_units: int, 
    billing_cycle: str = "monthly", 
    condominium_id: str = None,
    seat_price_override: float = None,
    yearly_discount_override: float = None
) -> dict:
    """
    Calculate billing preview for new condominium or seat change.
    Does NOT create any records - purely informational.
    
    Args:
        seat_price_override: Custom price per seat (overrides global/condo price)
        yearly_discount_override: Custom yearly discount 0-50% (overrides global)
    """
    # Create temporary condo dict for calculation
    temp_condo = {
        "id": condominium_id,
        "paid_seats": initial_units,
        "billing_cycle": billing_cycle
    }
    
    return await calculate_invoice(
        temp_condo, 
        billing_cycle, 
        seat_price_override=seat_price_override,
        yearly_discount_override=yearly_discount_override
    )

# ==================== END BILLING ENGINE ====================
# NOTE: The following functions are now imported from modules.billing (PHASE 3):
# - log_billing_engine_event (from modules.billing.service)
# - update_condominium_billing_status (from modules.billing.service)
# - send_billing_notification_email (from modules.billing.service)
# - process_billing_for_condominium (from modules.billing.scheduler)
# - run_daily_billing_check (from modules.billing.scheduler)
# - start_billing_scheduler (from modules.billing.scheduler)
# - stop_billing_scheduler (from modules.billing.scheduler)
# - DEFAULT_GRACE_PERIOD_DAYS (from modules.billing.service)
# - BILLING_EMAIL_TEMPLATES (from modules.billing.service)

# ==================== PARTIAL BLOCKING MIDDLEWARE ====================
"""
BLOQUEO PARCIAL INTELIGENTE

- Condominios suspendidos solo pueden hacer GET requests
- POST, PUT, DELETE están bloqueados
- Dashboard y consultas siguen funcionando
"""

# Routes that are ALWAYS allowed (even when suspended)
ALWAYS_ALLOWED_ROUTES = [
    "/api/auth/",           # Authentication
    "/api/health",          # Health checks
    "/api/billing/",        # Billing endpoints (need to pay!)
    "/api/super-admin/",    # SuperAdmin routes
]

# Routes that are blocked when suspended (checked by method)
BLOCKED_WHEN_SUSPENDED_METHODS = ["POST", "PUT", "DELETE", "PATCH"]


async def check_billing_access(
    condominium_id: str,
    method: str,
    path: str
) -> Tuple[bool, Optional[str]]:
    """
    Central function to check if a request should be allowed based on billing status.
    
    Returns:
        Tuple[bool, Optional[str]]: (is_allowed, error_message)
    
    Logic:
    - Suspended condos: Block POST/PUT/DELETE/PATCH, allow GET
    - Past due condos: Allow all (warning only)
    - Active condos: Allow all
    """
    # Check if route is always allowed
    for allowed_route in ALWAYS_ALLOWED_ROUTES:
        if path.startswith(allowed_route):
            return True, None
    
    # Get condominium
    condo = await db.condominiums.find_one(
        {"id": condominium_id},
        {"_id": 0, "billing_status": 1, "environment": 1, "is_demo": 1, "name": 1}
    )
    
    if not condo:
        return True, None  # Unknown condo - let other middleware handle
    
    # Demo condos are never blocked
    if condo.get("is_demo") or condo.get("environment") == "demo":
        return True, None
    
    billing_status = condo.get("billing_status", "active")
    
    # Suspended: Block modifications
    if billing_status == "suspended":
        if method.upper() in BLOCKED_WHEN_SUSPENDED_METHODS:
            return False, f"Cuenta suspendida por falta de pago. Solo consultas permitidas. Contacte soporte para regularizar."
    
    return True, None


async def check_billing_access_dependency(
    request: Request,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    FastAPI dependency for partial blocking.
    Raises HTTPException if access is denied.
    """
    condominium_id = current_user.get("condominium_id")
    
    # SuperAdmins are never blocked
    user_roles = current_user.get("roles", [])
    if "SuperAdmin" in user_roles:
        return current_user
    
    if not condominium_id:
        return current_user
    
    is_allowed, error_message = await check_billing_access(
        condominium_id,
        request.method,
        request.url.path
    )
    
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=error_message
        )
    
    return current_user


# ==================== BILLING SCHEDULER ADMIN ENDPOINTS ====================

@billing_router.post("/scheduler/run-now")
async def run_billing_scheduler_now(
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    SuperAdmin: Manually trigger the daily billing check.
    Useful for testing or immediate processing.
    """
    results = await run_daily_billing_check()
    
    return {
        "success": True,
        "message": "Billing check completed",
        "results": {
            "total_evaluated": results["total_evaluated"],
            "transitioned_to_past_due": results["transitioned_to_past_due"],
            "transitioned_to_suspended": results["transitioned_to_suspended"],
            "emails_sent": results["emails_sent"],
            "errors": results["errors"]
        }
    }


@billing_router.get("/scheduler/history")
async def get_scheduler_run_history(
    limit: int = Query(30, ge=1, le=100),
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    SuperAdmin: Get history of billing scheduler runs.
    """
    runs = await db.billing_scheduler_runs.find(
        {},
        {"_id": 0}
    ).sort("run_time", -1).limit(limit).to_list(limit)
    
    return {
        "runs": runs,
        "count": len(runs)
    }


@billing_router.get("/scheduler/status")
async def get_scheduler_status(
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    SuperAdmin: Check billing scheduler status.
    """
    # Get scheduler instance from billing module
    billing_scheduler = get_scheduler_instance()
    
    is_running = billing_scheduler is not None and billing_scheduler.running
    
    next_run = None
    if is_running:
        job = billing_scheduler.get_job("daily_billing_check")
        if job and job.next_run_time:
            next_run = job.next_run_time.isoformat()
    
    # Get last run
    last_run = await db.billing_scheduler_runs.find_one(
        {},
        {"_id": 0},
        sort=[("run_time", -1)]
    )
    
    return {
        "is_running": is_running,
        "next_run_scheduled": next_run,
        "last_run": last_run
    }


@api_router.put("/condominiums/{condominium_id}/grace-period")
async def update_grace_period(
    condominium_id: str,
    grace_days: int = Query(..., ge=0, le=30, description="Grace period in days (0-30)"),
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    SuperAdmin: Update grace period for a specific condominium.
    """
    result = await db.condominiums.update_one(
        {"id": condominium_id},
        {"$set": {
            "grace_period_days": grace_days,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    return {
        "success": True,
        "condominium_id": condominium_id,
        "grace_period_days": grace_days
    }

# ==================== END AUTOMATIC BILLING SCHEDULER ====================

@billing_router.post("/preview", response_model=BillingPreviewResponse)
async def get_billing_preview(
    preview_request: BillingPreviewRequest,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """
    BILLING ENGINE: Calculate billing preview before creating/modifying condominium.
    
    Use this endpoint to show users the cost breakdown before they commit.
    Does NOT create any records - purely informational.
    
    Supports custom seat_price_override and yearly_discount_percent for flexible pricing.
    """
    preview = await calculate_billing_preview(
        initial_units=preview_request.initial_units,
        billing_cycle=preview_request.billing_cycle,
        condominium_id=preview_request.condominium_id,
        seat_price_override=preview_request.seat_price_override,
        yearly_discount_override=preview_request.yearly_discount_percent
    )
    
    return BillingPreviewResponse(
        seats=preview["seats"],
        price_per_seat=preview["price_per_seat"],
        billing_cycle=preview["billing_cycle"],
        monthly_amount=preview["monthly_amount"],
        yearly_amount=preview["yearly_amount"],
        yearly_discount_percent=preview["yearly_discount_percent"],
        effective_amount=preview["effective_amount"],
        next_billing_date=preview["next_billing_date"],
        currency=preview["currency"]
    )

@billing_router.get("/events/{condominium_id}")
async def get_billing_events(
    condominium_id: str,
    limit: int = 50,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    BILLING ENGINE: Get billing event history for a condominium.
    SuperAdmin only - audit trail for billing changes.
    """
    events = await db.billing_events.find(
        {"condominium_id": condominium_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "condominium_id": condominium_id,
        "events": events,
        "total": len(events)
    }

@billing_router.patch("/seats/{condominium_id}")
async def update_condominium_seats(
    condominium_id: str,
    request: Request,
    seat_update: SeatUpdateRequest,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    BILLING ENGINE: Update seat count for a condominium.
    Recalculates billing and logs the change.
    Does NOT integrate with payment providers yet.
    """
    # Get current condominium
    condo = await db.condominiums.find_one({"id": condominium_id}, {"_id": 0})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    if condo.get("environment") == "demo" or condo.get("is_demo"):
        raise HTTPException(status_code=403, detail="No se pueden modificar asientos en condominios DEMO")
    
    previous_seats = condo.get("paid_seats", 10)
    new_seats = seat_update.new_seat_count
    
    if new_seats == previous_seats:
        raise HTTPException(status_code=400, detail="La cantidad de asientos es la misma")
    
    # Calculate new billing
    new_preview = await calculate_billing_preview(
        initial_units=new_seats,
        billing_cycle=condo.get("billing_cycle", "monthly"),
        condominium_id=condominium_id
    )
    
    # Determine event type
    event_type = "seats_upgraded" if new_seats > previous_seats else "seats_downgraded"
    
    # Update condominium
    update_data = {
        "paid_seats": new_seats,
        "max_users": new_seats,
        "next_invoice_amount": new_preview["effective_amount"],
        "price_per_seat": new_preview["price_per_seat"],
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.condominiums.update_one(
        {"id": condominium_id},
        {"$set": update_data}
    )
    
    # Log billing event
    await log_billing_engine_event(
        event_type=event_type,
        condominium_id=condominium_id,
        data={
            "previous_seats": previous_seats,
            "new_seats": new_seats,
            "change": new_seats - previous_seats,
            "previous_amount": condo.get("next_invoice_amount", 0),
            "new_amount": new_preview["effective_amount"],
            "reason": seat_update.reason
        },
        triggered_by=current_user["id"],
        previous_state={"paid_seats": previous_seats},
        new_state={"paid_seats": new_seats}
    )
    
    return {
        "condominium_id": condominium_id,
        "previous_seats": previous_seats,
        "new_seats": new_seats,
        "change": new_seats - previous_seats,
        "new_monthly_amount": new_preview["monthly_amount"],
        "new_effective_amount": new_preview["effective_amount"],
        "billing_cycle": condo.get("billing_cycle", "monthly"),
        "message": f"Asientos actualizados de {previous_seats} a {new_seats}"
    }

# ==================== SINPE BILLING CONTROL ====================
# Complete financial control for SINPE/manual payments
# Includes: Payment confirmation, history, upgrade requests, seat protection

@billing_router.post("/confirm-payment/{condominium_id}", response_model=ConfirmPaymentResponse)
async def confirm_sinpe_payment(
    condominium_id: str,
    request: Request,
    payment_data: ConfirmPaymentRequest,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    SINPE BILLING: Confirm a manual/SINPE payment for a condominium.
    
    SUPPORTS PARTIAL PAYMENTS:
    - Calculates total_paid for current billing cycle
    - Only activates condominium when balance_due <= 0
    - Keeps past_due status if partial payment leaves balance
    - Recalculates next_billing_date ONLY when fully paid
    
    Only SuperAdmin can confirm payments.
    """
    # Get condominium
    condo = await db.condominiums.find_one({"id": condominium_id}, {"_id": 0})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    if condo.get("environment") == "demo" or condo.get("is_demo"):
        raise HTTPException(status_code=403, detail="Los condominios DEMO no tienen facturación")
    
    now = datetime.now(timezone.utc)
    billing_cycle = condo.get("billing_cycle", "monthly")
    paid_seats = condo.get("paid_seats", 10)
    previous_status = condo.get("billing_status", "pending_payment")
    invoice_amount = condo.get("next_invoice_amount", 0)
    current_billing_date = condo.get("next_billing_date")
    
    # Parse current billing date to identify the billing cycle
    billing_cycle_start = None
    if current_billing_date:
        try:
            billing_cycle_start = datetime.fromisoformat(current_billing_date.replace("Z", "+00:00"))
            if billing_cycle_start.tzinfo is None:
                billing_cycle_start = billing_cycle_start.replace(tzinfo=timezone.utc)
            # Go back one cycle to get the start of current billing period
            if billing_cycle == "yearly":
                billing_cycle_start = billing_cycle_start - timedelta(days=365)
            else:
                billing_cycle_start = billing_cycle_start - timedelta(days=30)
        except:
            billing_cycle_start = now - timedelta(days=30)
    else:
        billing_cycle_start = now - timedelta(days=30)
    
    # Calculate total paid in current billing cycle
    # Get all payments made since the start of current billing cycle
    payments_in_cycle = await db.billing_payments.find({
        "condominium_id": condominium_id,
        "payment_date": {"$gte": billing_cycle_start.isoformat()}
    }, {"_id": 0, "amount_paid": 1}).to_list(1000)
    
    total_paid_before = sum(p.get("amount_paid", 0) for p in payments_in_cycle)
    total_paid_after = total_paid_before + payment_data.amount_paid
    
    # Calculate balance due
    balance_due = max(0, round(invoice_amount - total_paid_after, 2))
    is_fully_paid = balance_due <= 0
    
    # Create payment record
    payment_id = str(uuid.uuid4())
    payment_record = {
        "id": payment_id,
        "condominium_id": condominium_id,
        "condominium_name": condo.get("name", "Unknown"),
        "seats_at_payment": paid_seats,
        "amount_paid": payment_data.amount_paid,
        "invoice_amount": invoice_amount,
        "total_paid_cycle": total_paid_after,
        "balance_due": balance_due,
        "is_partial_payment": not is_fully_paid,
        "billing_cycle": billing_cycle,
        "billing_cycle_start": billing_cycle_start.isoformat(),
        "payment_method": condo.get("billing_provider", "sinpe"),
        "payment_reference": payment_data.payment_reference,
        "notes": payment_data.notes,
        "payment_date": now.isoformat(),
        "confirmed_by": current_user["id"],
        "confirmed_by_name": current_user.get("full_name", current_user.get("email")),
        "created_at": now.isoformat()
    }
    
    await db.billing_payments.insert_one(payment_record)
    
    # Determine new status and whether to update next_billing_date
    next_billing = None
    new_status = previous_status
    
    if is_fully_paid:
        # FULLY PAID: Activate and calculate next billing date
        new_status = "active"
        
        if billing_cycle == "yearly":
            next_billing = now + timedelta(days=365)
        else:
            if now.month == 12:
                next_billing = now.replace(year=now.year + 1, month=1, day=now.day)
            else:
                try:
                    next_billing = now.replace(month=now.month + 1)
                except ValueError:
                    next_billing = (now.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        payment_record["next_billing_date"] = next_billing.isoformat()
        
        # Update condominium with active status and new billing date
        update_data = {
            "billing_status": new_status,
            "next_billing_date": next_billing.isoformat(),
            "last_payment_date": now.isoformat(),
            "last_payment_amount": payment_data.amount_paid,
            "total_paid_current_cycle": total_paid_after,
            "balance_due": 0,
            "updated_at": now.isoformat()
        }
    else:
        # PARTIAL PAYMENT: Keep past_due or pending_payment, don't change next_billing_date
        if previous_status in ["suspended", "cancelled"]:
            new_status = "past_due"  # Reactivate to past_due with partial payment
        elif previous_status == "active":
            new_status = "past_due"  # Shouldn't happen but handle it
        else:
            new_status = previous_status  # Keep as past_due or pending_payment
        
        update_data = {
            "billing_status": new_status,
            "last_payment_date": now.isoformat(),
            "last_payment_amount": payment_data.amount_paid,
            "total_paid_current_cycle": total_paid_after,
            "balance_due": balance_due,
            "updated_at": now.isoformat()
        }
    
    await db.condominiums.update_one(
        {"id": condominium_id},
        {"$set": update_data}
    )
    
    # Log billing event with partial payment details
    event_data = {
        "payment_id": payment_id,
        "amount_paid": payment_data.amount_paid,
        "invoice_amount": invoice_amount,
        "total_paid_cycle": total_paid_after,
        "balance_due": balance_due,
        "is_partial_payment": not is_fully_paid,
        "payment_method": condo.get("billing_provider", "sinpe"),
        "payment_reference": payment_data.payment_reference,
        "seats": paid_seats,
        "billing_cycle": billing_cycle
    }
    
    await log_billing_engine_event(
        event_type="payment_received" if is_fully_paid else "partial_payment_received",
        condominium_id=condominium_id,
        data=event_data,
        triggered_by=current_user["id"],
        previous_state={"billing_status": previous_status, "balance_due": invoice_amount - total_paid_before},
        new_state={"billing_status": new_status, "balance_due": balance_due}
    )
    
    logger.info(
        f"[SINPE-PAYMENT] {'FULL' if is_fully_paid else 'PARTIAL'} payment ${payment_data.amount_paid} "
        f"for condo={condominium_id[:8]}... (total: ${total_paid_after}/{invoice_amount}, "
        f"balance: ${balance_due}) by {current_user['email']}"
    )
    
    # Send appropriate email
    billing_email = condo.get("billing_email") or condo.get("admin_email") or condo.get("contact_email")
    if billing_email:
        if is_fully_paid:
            await send_billing_notification_email(
                "payment_confirmed",
                billing_email,
                condo.get("name", "Unknown"),
                payment_data.amount_paid,
                now.strftime("%d/%m/%Y"),
                paid_seats,
                next_due_date=next_billing.strftime("%d/%m/%Y") if next_billing else ""
            )
        # For partial payments, we could add a specific email template later
    
    # Build response message
    if is_fully_paid:
        message = f"Pago completo de ${payment_data.amount_paid} confirmado. Próximo cobro: {next_billing.strftime('%d/%m/%Y') if next_billing else 'N/A'}"
    else:
        message = f"Pago parcial de ${payment_data.amount_paid} registrado. Saldo pendiente: ${balance_due:.2f}. Total pagado este ciclo: ${total_paid_after:.2f}"
    
    return ConfirmPaymentResponse(
        payment_id=payment_id,
        condominium_id=condominium_id,
        amount_paid=payment_data.amount_paid,
        invoice_amount=invoice_amount,
        total_paid_cycle=total_paid_after,
        balance_due=balance_due,
        previous_status=previous_status,
        new_status=new_status,
        next_billing_date=next_billing.isoformat() if next_billing else None,
        is_fully_paid=is_fully_paid,
        message=message
    )

@billing_router.get("/payments/{condominium_id}")
async def get_payment_history(
    condominium_id: str,
    limit: int = 50,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """
    SINPE BILLING: Get payment history for a condominium.
    """
    # Verify access - SuperAdmin can view any, Admin only their own
    user_roles = current_user.get("roles", [])
    is_super = "SuperAdmin" in user_roles or "super_admin" in user_roles
    if not is_super and current_user.get("condominium_id") != condominium_id:
        raise HTTPException(status_code=403, detail="No autorizado para ver este historial")
    
    payments = await db.billing_payments.find(
        {"condominium_id": condominium_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Get condominium info
    condo = await db.condominiums.find_one({"id": condominium_id}, {"_id": 0, "name": 1, "paid_seats": 1, "billing_status": 1})
    
    return {
        "condominium_id": condominium_id,
        "condominium_name": condo.get("name") if condo else "Unknown",
        "current_status": condo.get("billing_status") if condo else "unknown",
        "payments": payments,
        "total": len(payments)
    }

@billing_router.get("/payments")
async def get_all_pending_payments(
    status: Optional[str] = None,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    SINPE BILLING: Get all condominiums with pending payments (SuperAdmin only).
    """
    query = {"environment": {"$ne": "demo"}, "is_demo": {"$ne": True}}
    if status:
        query["billing_status"] = status
    else:
        query["billing_status"] = {"$in": ["pending_payment", "past_due", "upgrade_pending"]}
    
    condos = await db.condominiums.find(
        query,
        {"_id": 0, "id": 1, "name": 1, "contact_email": 1, "paid_seats": 1, 
         "billing_status": 1, "next_invoice_amount": 1, "next_billing_date": 1,
         "billing_cycle": 1, "billing_provider": 1, "created_at": 1,
         "balance_due": 1, "total_paid_current_cycle": 1}
    ).sort("created_at", -1).to_list(100)
    
    return {
        "pending_count": len(condos),
        "condominiums": condos
    }


@billing_router.get("/balance/{condominium_id}")
async def get_billing_balance(
    condominium_id: str,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """
    Get detailed billing balance for a condominium.
    Shows invoice amount, total paid in current cycle, and balance due.
    
    Returns:
    - invoice_amount: Total due for current billing cycle
    - total_paid_cycle: Total paid in current billing cycle
    - balance_due: Remaining amount to pay
    - billing_status: Current status
    - is_fully_paid: True if balance_due <= 0
    - payments_this_cycle: List of payments in current cycle
    """
    # Verify access
    user_roles = current_user.get("roles", [])
    is_super = "SuperAdmin" in user_roles or "super_admin" in user_roles
    if not is_super and current_user.get("condominium_id") != condominium_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    condo = await db.condominiums.find_one({"id": condominium_id}, {"_id": 0})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    invoice_amount = condo.get("next_invoice_amount", 0)
    total_paid_cycle = condo.get("total_paid_current_cycle", 0)
    balance_due = condo.get("balance_due", invoice_amount)
    billing_status = condo.get("billing_status", "pending_payment")
    next_billing_date = condo.get("next_billing_date")
    
    # Get payments for current billing cycle
    billing_cycle_start = None
    if next_billing_date:
        try:
            billing_date = datetime.fromisoformat(next_billing_date.replace("Z", "+00:00"))
            billing_cycle = condo.get("billing_cycle", "monthly")
            if billing_cycle == "yearly":
                billing_cycle_start = billing_date - timedelta(days=365)
            else:
                billing_cycle_start = billing_date - timedelta(days=30)
        except:
            billing_cycle_start = datetime.now(timezone.utc) - timedelta(days=30)
    else:
        billing_cycle_start = datetime.now(timezone.utc) - timedelta(days=30)
    
    payments_this_cycle = await db.billing_payments.find({
        "condominium_id": condominium_id,
        "payment_date": {"$gte": billing_cycle_start.isoformat()}
    }, {"_id": 0, "id": 1, "amount_paid": 1, "payment_date": 1, "payment_reference": 1, "is_partial_payment": 1}).sort("payment_date", -1).to_list(100)
    
    return {
        "condominium_id": condominium_id,
        "condominium_name": condo.get("name", "Unknown"),
        "invoice_amount": invoice_amount,
        "total_paid_cycle": total_paid_cycle,
        "balance_due": balance_due,
        "billing_status": billing_status,
        "is_fully_paid": balance_due <= 0,
        "next_billing_date": next_billing_date,
        "billing_cycle": condo.get("billing_cycle", "monthly"),
        "paid_seats": condo.get("paid_seats", 10),
        "price_per_seat": condo.get("price_per_seat", 2.99),
        "payments_this_cycle": payments_this_cycle,
        "payments_count": len(payments_this_cycle)
    }

# ==================== SEAT UPGRADE REQUESTS ====================

@billing_router.post("/request-seat-upgrade")
async def request_seat_upgrade(
    request_data: SeatUpgradeRequestModel,
    current_user = Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN))
):
    """
    SINPE BILLING: Request additional seats for a condominium.
    
    Admin can request, but SuperAdmin must approve.
    After approval, payment must be confirmed to activate new seats.
    """
    condo_id = current_user.get("condominium_id")
    
    # SuperAdmin can specify condominium_id in request - they should use direct methods instead
    user_roles = current_user.get("roles", [])
    if "SuperAdmin" in user_roles:
        raise HTTPException(status_code=400, detail="SuperAdmin debe usar /billing/seats/{condo_id} para cambios directos")
    
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario sin condominio asignado")
    
    # Get condominium
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    if condo.get("environment") == "demo" or condo.get("is_demo"):
        raise HTTPException(status_code=403, detail="Los condominios DEMO no pueden solicitar más asientos")
    
    current_seats = condo.get("paid_seats", 10)
    requested_seats = request_data.requested_seats
    
    if requested_seats <= current_seats:
        raise HTTPException(status_code=400, detail=f"Debe solicitar más de {current_seats} asientos actuales")
    
    # Check for pending requests
    existing = await db.seat_upgrade_requests.find_one({
        "condominium_id": condo_id,
        "status": "pending"
    })
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe una solicitud pendiente de aprobación")
    
    # Calculate pricing
    current_preview = await calculate_billing_preview(current_seats, condo.get("billing_cycle", "monthly"), condo_id)
    new_preview = await calculate_billing_preview(requested_seats, condo.get("billing_cycle", "monthly"), condo_id)
    
    now = datetime.now(timezone.utc)
    request_id = str(uuid.uuid4())
    
    upgrade_request = {
        "id": request_id,
        "condominium_id": condo_id,
        "condominium_name": condo.get("name", "Unknown"),
        "current_seats": current_seats,
        "requested_seats": requested_seats,
        "additional_seats": requested_seats - current_seats,
        "current_amount": current_preview["effective_amount"],
        "new_amount": new_preview["effective_amount"],
        "difference_amount": round(new_preview["effective_amount"] - current_preview["effective_amount"], 2),
        "billing_cycle": condo.get("billing_cycle", "monthly"),
        "status": "pending",
        "reason": request_data.reason,
        "requested_by": current_user["id"],
        "requested_by_name": current_user.get("full_name", current_user.get("email")),
        "approved_by": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.seat_upgrade_requests.insert_one(upgrade_request)
    
    # Log event
    await log_billing_engine_event(
        event_type="upgrade_requested",
        condominium_id=condo_id,
        data={
            "request_id": request_id,
            "current_seats": current_seats,
            "requested_seats": requested_seats,
            "difference_amount": upgrade_request["difference_amount"]
        },
        triggered_by=current_user["id"],
        previous_state={"paid_seats": current_seats},
        new_state={"requested_seats": requested_seats, "status": "pending"}
    )
    
    logger.info(f"[SEAT-UPGRADE] Request created: {current_seats}→{requested_seats} for condo={condo_id[:8]}...")
    
    return {
        "request_id": request_id,
        "condominium_id": condo_id,
        "current_seats": current_seats,
        "requested_seats": requested_seats,
        "additional_seats": requested_seats - current_seats,
        "current_amount": current_preview["effective_amount"],
        "new_amount": new_preview["effective_amount"],
        "difference_amount": upgrade_request["difference_amount"],
        "status": "pending",
        "message": f"Solicitud creada. Esperando aprobación de SuperAdmin para {requested_seats - current_seats} asientos adicionales (${upgrade_request['difference_amount']}/{'año' if condo.get('billing_cycle') == 'yearly' else 'mes'})"
    }

@billing_router.get("/my-pending-request")
async def get_my_pending_request(
    current_user = Depends(require_role(RoleEnum.ADMINISTRADOR))
):
    """
    Get the current admin's pending seat upgrade request, if any.
    Returns null/404 if no pending request exists.
    """
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario sin condominio asignado")
    
    pending_request = await db.seat_upgrade_requests.find_one(
        {"condominium_id": condo_id, "status": "pending"},
        {"_id": 0}
    )
    
    if not pending_request:
        raise HTTPException(status_code=404, detail="No hay solicitud pendiente")
    
    return pending_request

@billing_router.get("/upgrade-requests")
async def get_upgrade_requests(
    status: Optional[str] = "pending",
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    SINPE BILLING: Get all seat upgrade requests (SuperAdmin only).
    """
    query = {}
    if status:
        query["status"] = status
    
    requests = await db.seat_upgrade_requests.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {
        "total": len(requests),
        "requests": requests
    }

@billing_router.patch("/approve-seat-upgrade/{request_id}")
async def approve_seat_upgrade(
    request_id: str,
    approve: bool = True,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    SINPE BILLING: Approve or reject a seat upgrade request.
    
    If approved:
    - Updates paid_seats
    - Recalculates next_invoice_amount
    - Sets billing_status to "upgrade_pending" (awaiting payment)
    
    Payment must be confirmed separately to activate.
    """
    # Get request
    upgrade_req = await db.seat_upgrade_requests.find_one({"id": request_id}, {"_id": 0})
    if not upgrade_req:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    if upgrade_req["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Solicitud ya fue {upgrade_req['status']}")
    
    condo_id = upgrade_req["condominium_id"]
    now = datetime.now(timezone.utc)
    
    if approve:
        # Get condominium
        condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0})
        if not condo:
            raise HTTPException(status_code=404, detail="Condominio no encontrado")
        
        new_seats = upgrade_req["requested_seats"]
        new_preview = await calculate_billing_preview(new_seats, condo.get("billing_cycle", "monthly"), condo_id)
        
        # Update condominium
        await db.condominiums.update_one(
            {"id": condo_id},
            {"$set": {
                "paid_seats": new_seats,
                "max_users": new_seats,
                "next_invoice_amount": new_preview["effective_amount"],
                "billing_status": "upgrade_pending",  # Awaiting payment for upgrade
                "updated_at": now.isoformat()
            }}
        )
        
        # Update request
        await db.seat_upgrade_requests.update_one(
            {"id": request_id},
            {"$set": {
                "status": "approved",
                "approved_by": current_user["id"],
                "approved_by_name": current_user.get("full_name", current_user.get("email")),
                "updated_at": now.isoformat()
            }}
        )
        
        # Log event
        await log_billing_engine_event(
            event_type="upgrade_approved",
            condominium_id=condo_id,
            data={
                "request_id": request_id,
                "previous_seats": upgrade_req["current_seats"],
                "new_seats": new_seats,
                "new_amount": new_preview["effective_amount"]
            },
            triggered_by=current_user["id"],
            previous_state={"paid_seats": upgrade_req["current_seats"]},
            new_state={"paid_seats": new_seats, "billing_status": "upgrade_pending"}
        )
        
        logger.info(f"[SEAT-UPGRADE] Approved: {upgrade_req['current_seats']}→{new_seats} for condo={condo_id[:8]}...")
        print(f"[FLOW] seat_upgrade_processed | request_id={request_id} status=approved condo_id={condo_id[:8]}")
        
        # === SEND EMAIL NOTIFICATION TO ADMIN ===
        try:
            # Get admin who requested the upgrade
            requester_id = upgrade_req.get("requested_by")
            requester = await db.users.find_one({"id": requester_id}, {"_id": 0, "email": 1, "full_name": 1})
            
            if requester and requester.get("email"):
                admin_email = requester["email"]
                admin_name = requester.get("full_name", "Administrador")
                
                print(f"[EMAIL TRIGGER] seat_upgrade_approved | email={admin_email} condo={condo.get('name')}")
                logger.info(f"[EMAIL TRIGGER] seat_upgrade_approved | admin={admin_email}")
                
                upgrade_email_html = f"""
                <!DOCTYPE html>
                <html>
                <head><meta charset="UTF-8"></head>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(135deg, #10B981 0%, #059669 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
                        <h1 style="color: #ffffff; margin: 0;">Solicitud Aprobada</h1>
                        <p style="color: rgba(255,255,255,0.9); margin-top: 5px;">Upgrade de Asientos - GENTURIX</p>
                    </div>
                    
                    <div style="background: #ffffff; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #eee;">
                        <p>Hola {admin_name},</p>
                        <p>Tu solicitud de upgrade de asientos ha sido <strong style="color: #10B981;">aprobada</strong>.</p>
                        
                        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 8px 0; color: #666;">Condominio:</td>
                                    <td style="padding: 8px 0; font-weight: bold; text-align: right;">{condo.get('name', 'N/A')}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #666;">Asientos anteriores:</td>
                                    <td style="padding: 8px 0; text-align: right;">{upgrade_req['current_seats']}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #666;">Nuevos asientos:</td>
                                    <td style="padding: 8px 0; font-weight: bold; color: #10B981; text-align: right;">{new_seats}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #666;">Fecha efectiva:</td>
                                    <td style="padding: 8px 0; text-align: right;">{now.strftime('%d/%m/%Y')}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #666;">Nuevo monto:</td>
                                    <td style="padding: 8px 0; font-weight: bold; text-align: right;">${new_preview['effective_amount']:.2f}/{condo.get('billing_cycle', 'mes')}</td>
                                </tr>
                            </table>
                        </div>
                        
                        <p style="color: #666; font-size: 14px;">
                            Los nuevos asientos ya están disponibles. Ahora puedes crear hasta {new_seats} usuarios en tu condominio.
                        </p>
                    </div>
                    
                    <div style="text-align: center; padding: 20px; color: #888; font-size: 12px;">
                        <p>Este es un correo automático de Genturix Security.</p>
                    </div>
                </body>
                </html>
                """
                
                email_result = await send_email(
                    to=admin_email,
                    subject=f"✅ Solicitud de Asientos Aprobada - {condo.get('name', 'Genturix')}",
                    html=upgrade_email_html
                )
                
                if email_result.get("success"):
                    print(f"[EMAIL SENT] seat_upgrade_approved | email={admin_email}")
                    logger.info(f"[EMAIL SENT] seat_upgrade_approved to {admin_email}")
                else:
                    print(f"[EMAIL ERROR] seat_upgrade_approved failed | email={admin_email}")
                    logger.warning(f"[EMAIL ERROR] seat_upgrade_approved failed for {admin_email}: {email_result.get('error')}")
        except Exception as email_error:
            print(f"[EMAIL ERROR] seat_upgrade_approved exception | error={str(email_error)}")
            logger.error(f"[EMAIL ERROR] seat_upgrade_approved exception: {email_error}", exc_info=True)
            # Don't fail the request if email fails
        
        return {
            "request_id": request_id,
            "status": "approved",
            "condominium_id": condo_id,
            "new_seats": new_seats,
            "new_amount": new_preview["effective_amount"],
            "billing_status": "upgrade_pending",
            "message": f"Solicitud aprobada. Asientos actualizados a {new_seats}. Esperando confirmación de pago."
        }
    else:
        # Reject
        await db.seat_upgrade_requests.update_one(
            {"id": request_id},
            {"$set": {
                "status": "rejected",
                "approved_by": current_user["id"],
                "approved_by_name": current_user.get("full_name", current_user.get("email")),
                "updated_at": now.isoformat()
            }}
        )
        
        await log_billing_engine_event(
            event_type="upgrade_rejected",
            condominium_id=condo_id,
            data={"request_id": request_id, "requested_seats": upgrade_req["requested_seats"]},
            triggered_by=current_user["id"]
        )
        
        return {
            "request_id": request_id,
            "status": "rejected",
            "message": "Solicitud rechazada"
        }

# ==================== SEAT PROTECTION MIDDLEWARE ====================

async def check_seat_limit(condominium_id: str) -> dict:
    """
    SEAT PROTECTION: Check if condominium can create more users.
    
    Returns:
        {
            "can_create": bool,
            "current_users": int,
            "paid_seats": int,
            "remaining": int,
            "reason": str or None
        }
    """
    condo = await db.condominiums.find_one(
        {"id": condominium_id},
        {"_id": 0, "paid_seats": 1, "billing_status": 1, "environment": 1, "is_demo": 1, "name": 1}
    )
    
    if not condo:
        return {"can_create": False, "reason": "Condominio no encontrado"}
    
    # Demo condos have fixed limit of 10
    is_demo = condo.get("environment") == "demo" or condo.get("is_demo")
    paid_seats = 10 if is_demo else condo.get("paid_seats", 10)
    
    # Count active users (excluding super_admin)
    current_users = await db.users.count_documents({
        "condominium_id": condominium_id,
        "role": {"$ne": "super_admin"},
        "is_active": {"$ne": False}
    })
    
    remaining = paid_seats - current_users
    
    # Check billing status for production condos
    billing_status = condo.get("billing_status", "active")
    blocked_statuses = ["suspended", "cancelled"]
    
    if not is_demo and billing_status in blocked_statuses:
        return {
            "can_create": False,
            "current_users": current_users,
            "paid_seats": paid_seats,
            "remaining": remaining,
            "billing_status": billing_status,
            "reason": f"Condominio suspendido por falta de pago. Contacte soporte."
        }
    
    if current_users >= paid_seats:
        return {
            "can_create": False,
            "current_users": current_users,
            "paid_seats": paid_seats,
            "remaining": 0,
            "billing_status": billing_status,
            "reason": f"Límite de {paid_seats} asientos alcanzado. Solicite más asientos para continuar."
        }
    
    return {
        "can_create": True,
        "current_users": current_users,
        "paid_seats": paid_seats,
        "remaining": remaining,
        "billing_status": billing_status,
        "reason": None
    }

async def check_module_access(condominium_id: str, module_id: str = None) -> dict:
    """
    MODULE PROTECTION: Check if condominium can access modules.
    
    Blocks access if billing_status is past_due or suspended.
    """
    condo = await db.condominiums.find_one(
        {"id": condominium_id},
        {"_id": 0, "billing_status": 1, "environment": 1, "is_demo": 1, "modules": 1}
    )
    
    if not condo:
        return {"can_access": False, "reason": "Condominio no encontrado"}
    
    is_demo = condo.get("environment") == "demo" or condo.get("is_demo")
    
    # Demo condos always have access
    if is_demo:
        return {"can_access": True, "reason": None}
    
    billing_status = condo.get("billing_status", "active")
    blocked_statuses = ["past_due", "suspended", "cancelled"]
    
    if billing_status in blocked_statuses:
        return {
            "can_access": False,
            "billing_status": billing_status,
            "reason": f"Acceso bloqueado: {billing_status}. Por favor regularice su pago."
        }
    
    return {
        "can_access": True,
        "billing_status": billing_status,
        "reason": None
    }

@billing_router.get("/seat-status/{condominium_id}")
async def get_seat_status(
    condominium_id: str,
    current_user = Depends(get_current_user)
):
    """
    SEAT PROTECTION: Get current seat usage status for a condominium.
    """
    # Verify access - SuperAdmin can view any, others only their own
    user_roles = current_user.get("roles", [])
    is_super = "SuperAdmin" in user_roles or "super_admin" in user_roles
    if not is_super and current_user.get("condominium_id") != condominium_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    status = await check_seat_limit(condominium_id)
    
    # Add percentage
    if status.get("paid_seats", 0) > 0:
        status["usage_percent"] = round((status.get("current_users", 0) / status["paid_seats"]) * 100, 1)
    else:
        status["usage_percent"] = 0
    
    return status

# ==================== END SINPE BILLING CONTROL ====================

@api_router.get("/payments/pricing")
async def get_pricing_info(current_user = Depends(get_current_user)):
    """
    Get GENTURIX pricing model for current user's condominium.
    PHASE 4: Uses dynamic pricing system.
    """
    condo_id = current_user.get("condominium_id")
    pricing_info = await get_condominium_pricing_info(condo_id)
    
    return {
        "model": "per_user",
        "price_per_user": pricing_info["effective_price"],
        "currency": pricing_info["currency"].lower(),
        "billing_period": "monthly",
        "uses_override": pricing_info["uses_override"],
        "description": f"${pricing_info['effective_price']} por usuario al mes",
        "features": [
            "Acceso completo a GENTURIX",
            "Botón de pánico (3 tipos de emergencia)",
            "Registro de accesos",
            "Genturix School básico",
            "Auditoría completa",
            "Soporte por email"
        ],
        "premium_modules": [
            {"name": "Genturix School Pro", "price": 2.00, "description": "Cursos ilimitados y certificaciones"},
            {"name": "Monitoreo CCTV", "price": 3.00, "description": "Integración con cámaras IP"},
            {"name": "API Access", "price": 5.00, "description": "Acceso a API para integraciones"}
        ]
    }

@api_router.post("/payments/calculate")
async def calculate_price(subscription: UserSubscriptionCreate, current_user = Depends(get_current_user)):
    """
    Calculate subscription price based on user count.
    PHASE 4: Uses dynamic pricing system.
    """
    if subscription.user_count < 1:
        raise HTTPException(status_code=400, detail="Minimum 1 user required")
    
    condo_id = current_user.get("condominium_id")
    pricing = await calculate_subscription_price_dynamic(subscription.user_count, condo_id)
    
    return {
        "user_count": subscription.user_count,
        "price_per_user": pricing["price_per_seat"],
        "total": pricing["total"],
        "currency": pricing["currency"].lower(),
        "billing_period": "monthly"
    }

@api_router.post("/payments/checkout")
async def create_checkout(request: Request, current_user = Depends(get_current_user), user_count: int = 1, origin_url: str = ""):
    """
    Create checkout session for subscription.
    PHASE 4: Uses dynamic pricing system.
    """
    if user_count < 1:
        raise HTTPException(status_code=400, detail="Minimum 1 user required")
    
    condo_id = current_user.get("condominium_id")
    pricing = await calculate_subscription_price_dynamic(user_count, condo_id)
    total_amount = pricing["total"]
    
    stripe_api_key = os.environ.get('STRIPE_API_KEY')
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    host_url = origin_url.rstrip('/') if origin_url else str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe"
    success_url = f"{host_url}/payments?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{host_url}/payments"
    
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    checkout_request = CheckoutSessionRequest(
        amount=total_amount,
        currency=pricing["currency"].lower(),
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": current_user["id"],
            "user_email": current_user["email"],
            "user_count": str(user_count),
            "price_per_user": str(pricing["price_per_seat"])  # Use dynamic price from calculation
        }
    )
    
    session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Create payment transaction record
    transaction = {
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": current_user["id"],
        "user_email": current_user["email"],
        "user_count": user_count,
        "price_per_user": pricing["price_per_seat"],  # Use dynamic price
        "amount": total_amount,
        "currency": "usd",
        "payment_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.payment_transactions.insert_one(transaction)
    
    await log_audit_event(
        AuditEventType.PAYMENT_INITIATED,
        current_user["id"],
        "payments",
        {"user_count": user_count, "amount": total_amount, "session_id": session.session_id},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"url": session.url, "session_id": session.session_id, "amount": total_amount, "user_count": user_count}

@api_router.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str, request: Request, current_user = Depends(get_current_user)):
    stripe_api_key = os.environ.get('STRIPE_API_KEY')
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe"
    
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    status_response: CheckoutStatusResponse = await stripe_checkout.get_checkout_status(session_id)
    
    # Update transaction in database
    if status_response.payment_status == "paid":
        transaction = await db.payment_transactions.find_one({"session_id": session_id})
        if transaction and transaction.get("payment_status") != "completed":
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"payment_status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}}
            )
            
            await log_audit_event(
                AuditEventType.PAYMENT_COMPLETED,
                current_user["id"],
                "payments",
                {"session_id": session_id, "amount": transaction.get("amount")},
                request.client.host if request.client else "unknown",
                request.headers.get("user-agent", "unknown")
            )
    
    return {
        "status": status_response.status,
        "payment_status": status_response.payment_status,
        "amount_total": status_response.amount_total,
        "currency": status_response.currency
    }

@api_router.get("/payments/history")
async def get_payment_history(current_user = Depends(get_current_user)):
    transactions = await db.payment_transactions.find(
        {"user_id": current_user["id"]}, 
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return transactions

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events with signature verification"""
    stripe_api_key = os.environ.get('STRIPE_API_KEY')
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    # ==================== SECURITY: FAIL-CLOSED MODE ====================
    # In production: ALWAYS require STRIPE_WEBHOOK_SECRET
    # In development: Allow without secret (with warning)
    
    if ENVIRONMENT == "production":
        if not STRIPE_WEBHOOK_SECRET:
            logger.error("[SECURITY] Stripe webhook secret missing in PRODUCTION - rejecting request")
            raise HTTPException(
                status_code=500, 
                detail="Webhook security not configured. Contact administrator."
            )
        # Production with secret: verify signature
        try:
            stripe.Webhook.construct_event(
                payload=body,
                sig_header=signature,
                secret=STRIPE_WEBHOOK_SECRET
            )
            logger.info("[SECURITY] Stripe webhook verified successfully")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"[SECURITY] Stripe signature invalid: {e}")
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
        except Exception as e:
            logger.error(f"[SECURITY] Stripe signature verification error: {e}")
            raise HTTPException(status_code=400, detail="Webhook signature verification failed")
    else:
        # Development/staging: verify if secret exists, warn if not
        if STRIPE_WEBHOOK_SECRET:
            try:
                stripe.Webhook.construct_event(
                    payload=body,
                    sig_header=signature,
                    secret=STRIPE_WEBHOOK_SECRET
                )
                logger.debug("[STRIPE-WEBHOOK] Signature verified successfully (dev mode)")
            except stripe.error.SignatureVerificationError as e:
                logger.error(f"[STRIPE-WEBHOOK] Invalid signature: {e}")
                raise HTTPException(status_code=400, detail="Invalid webhook signature")
            except Exception as e:
                logger.error(f"[STRIPE-WEBHOOK] Signature verification error: {e}")
                raise HTTPException(status_code=400, detail="Webhook signature verification failed")
        else:
            logger.warning("[STRIPE-WEBHOOK] Processing without signature verification (dev mode) - STRIPE_WEBHOOK_SECRET not set")
    # ==========================================================================
    
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe"
    
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        if webhook_response.payment_status == "paid":
            await db.payment_transactions.update_one(
                {"session_id": webhook_response.session_id},
                {"$set": {"payment_status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}}
            )
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

# ==================== SAAS BILLING ENDPOINTS ====================

@billing_router.get("/info")
async def get_condominium_billing_info(current_user = Depends(get_current_user)):
    """Get billing information for the current user's condominium"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asociado a un condominio")
    
    billing_info = await get_billing_info(condo_id)
    if not billing_info:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    return billing_info

@billing_router.get("/can-create-user")
async def check_can_create_user(
    role: str = "Residente",
    current_user = Depends(require_role("Administrador", "SuperAdmin"))
):
    """Check if the condominium can create a new user of the specified role"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asociado a un condominio")
    
    can_create, error_msg = await can_create_user(condo_id, role)
    billing_info = await get_billing_info(condo_id)
    active_residents = await count_active_residents(condo_id)
    
    return {
        "can_create": can_create,
        "error_message": error_msg if not can_create else None,
        "paid_seats": billing_info.get("paid_seats", 0),
        "active_users": billing_info.get("active_users", 0),
        "active_residents": active_residents,
        "remaining_seats": max(0, billing_info.get("paid_seats", 0) - active_residents),
        "billing_status": billing_info.get("billing_status", "unknown"),
        "role_checked": role
    }

@billing_router.post("/upgrade-seats")
async def upgrade_seats(
    request: Request,
    upgrade: SeatUpgradeRequest,
    origin_url: str = "",
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))  # CHANGED: Only SuperAdmin can directly upgrade
):
    """
    BILLING ENGINE: Create a Stripe checkout session to upgrade seats.
    
    SECURITY: Only SuperAdmin can directly upgrade seats.
    Regular Admins must use POST /billing/request-seat-upgrade to create a request.
    """
    # For SuperAdmin, they need to specify condominium_id in the request
    condo_id = upgrade.condominium_id if hasattr(upgrade, 'condominium_id') and upgrade.condominium_id else current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="condominium_id requerido para SuperAdmin")
    
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    # ==================== DEMO ENVIRONMENT CHECK ====================
    # Demo condominiums cannot purchase additional seats
    condo_environment = condo.get("environment", "production")
    if condo_environment == "demo" or condo.get("is_demo"):
        raise HTTPException(
            status_code=403, 
            detail="Los condominios en modo Demo no pueden comprar asientos adicionales. Contacte al administrador para cambiar a modo Producción."
        )
    # ================================================================
    
    stripe_api_key = os.environ.get('STRIPE_API_KEY')
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe no configurado")
    
    # Calculate new total and amount to charge using dynamic pricing
    current_seats = condo.get("paid_seats", 10)
    new_total_seats = current_seats + upgrade.additional_seats
    
    # PHASE 4: Use dynamic pricing
    pricing = await calculate_subscription_price_dynamic(upgrade.additional_seats, condo_id)
    upgrade_cost = pricing["total"]
    currency = pricing["currency"].lower()
    
    host_url = origin_url.rstrip('/') if origin_url else str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe-subscription"
    success_url = f"{host_url}/admin/dashboard?upgrade=success&seats={new_total_seats}"
    cancel_url = f"{host_url}/admin/dashboard?upgrade=cancelled"
    
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    checkout_request = CheckoutSessionRequest(
        amount=upgrade_cost,
        currency=currency,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "type": "seat_upgrade",
            "condominium_id": condo_id,
            "condominium_name": condo.get("name", ""),
            "user_id": current_user["id"],
            "user_email": current_user["email"],
            "current_seats": str(current_seats),
            "additional_seats": str(upgrade.additional_seats),
            "new_total_seats": str(new_total_seats),
            "price_per_seat": str(pricing["price_per_seat"])
        }
    )
    
    session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Create upgrade transaction record
    transaction = {
        "id": str(uuid.uuid4()),
        "type": "seat_upgrade",
        "session_id": session.session_id,
        "condominium_id": condo_id,
        "user_id": current_user["id"],
        "user_email": current_user["email"],
        "current_seats": current_seats,
        "additional_seats": upgrade.additional_seats,
        "new_total_seats": new_total_seats,
        "amount": upgrade_cost,
        "currency": currency,
        "payment_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.billing_transactions.insert_one(transaction)
    
    await log_billing_event(
        "upgrade_initiated",
        condo_id,
        {
            "current_seats": current_seats,
            "additional_seats": upgrade.additional_seats,
            "new_total_seats": new_total_seats,
            "amount": upgrade_cost,
            "session_id": session.session_id
        },
        current_user["id"]
    )
    
    return {
        "url": session.url,
        "session_id": session.session_id,
        "current_seats": current_seats,
        "additional_seats": upgrade.additional_seats,
        "new_total_seats": new_total_seats,
        "amount": upgrade_cost
    }

@api_router.post("/webhook/stripe-subscription")
async def stripe_subscription_webhook(request: Request):
    """Handle Stripe webhook events for subscription updates with signature verification"""
    stripe_api_key = os.environ.get('STRIPE_API_KEY')
    if not stripe_api_key:
        return {"status": "error", "message": "Stripe not configured"}
    
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    # ==================== SECURITY: FAIL-CLOSED MODE ====================
    # In production: ALWAYS require STRIPE_WEBHOOK_SECRET
    # In development: Allow without secret (with warning)
    
    if ENVIRONMENT == "production":
        if not STRIPE_WEBHOOK_SECRET:
            logger.error("[SECURITY] Stripe subscription webhook secret missing in PRODUCTION - rejecting request")
            raise HTTPException(
                status_code=500, 
                detail="Webhook security not configured. Contact administrator."
            )
        # Production with secret: verify signature
        try:
            stripe.Webhook.construct_event(
                payload=body,
                sig_header=signature,
                secret=STRIPE_WEBHOOK_SECRET
            )
            logger.info("[SECURITY] Stripe subscription webhook verified successfully")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"[SECURITY] Stripe subscription signature invalid: {e}")
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
        except Exception as e:
            logger.error(f"[SECURITY] Stripe subscription signature verification error: {e}")
            raise HTTPException(status_code=400, detail="Webhook signature verification failed")
    else:
        # Development/staging: verify if secret exists, warn if not
        if STRIPE_WEBHOOK_SECRET:
            try:
                stripe.Webhook.construct_event(
                    payload=body,
                    sig_header=signature,
                    secret=STRIPE_WEBHOOK_SECRET
                )
                logger.debug("[STRIPE-SUBSCRIPTION-WEBHOOK] Signature verified successfully (dev mode)")
            except stripe.error.SignatureVerificationError as e:
                logger.error(f"[STRIPE-SUBSCRIPTION-WEBHOOK] Invalid signature: {e}")
                raise HTTPException(status_code=400, detail="Invalid webhook signature")
            except Exception as e:
                logger.error(f"[STRIPE-SUBSCRIPTION-WEBHOOK] Signature verification error: {e}")
                raise HTTPException(status_code=400, detail="Webhook signature verification failed")
        else:
            logger.warning("[STRIPE-SUBSCRIPTION-WEBHOOK] Processing without signature verification (dev mode) - STRIPE_WEBHOOK_SECRET not set")
    # ==========================================================================
    
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe-subscription"
    
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        if webhook_response.payment_status == "paid":
            # Find the billing transaction
            transaction = await db.billing_transactions.find_one({"session_id": webhook_response.session_id})
            
            if transaction and transaction.get("payment_status") != "completed":
                condo_id = transaction.get("condominium_id")
                new_total_seats = transaction.get("new_total_seats")
                
                # ==================== DEMO ENVIRONMENT CHECK ====================
                # Verify the condominium is not in demo mode before processing payment
                condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "environment": 1, "is_demo": 1})
                if condo:
                    condo_environment = condo.get("environment", "production")
                    if condo_environment == "demo" or condo.get("is_demo"):
                        logger.warning(f"[STRIPE-WEBHOOK] Ignoring payment for demo condominium: {condo_id}")
                        # Mark transaction as ignored (demo)
                        await db.billing_transactions.update_one(
                            {"session_id": webhook_response.session_id},
                            {"$set": {"payment_status": "ignored_demo", "note": "Demo condominium - payment ignored"}}
                        )
                        return {"status": "success", "note": "Demo condominium - no changes applied"}
                # ================================================================
                
                # Update condominium paid_seats
                await db.condominiums.update_one(
                    {"id": condo_id},
                    {
                        "$set": {
                            "paid_seats": new_total_seats,
                            "billing_status": "active",
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
                
                # Update transaction status
                await db.billing_transactions.update_one(
                    {"session_id": webhook_response.session_id},
                    {"$set": {"payment_status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}}
                )
                
                # Log the upgrade completion
                await log_billing_event(
                    "upgrade_completed",
                    condo_id,
                    {
                        "new_total_seats": new_total_seats,
                        "session_id": webhook_response.session_id
                    }
                )
                
                logger.info(f"Seat upgrade completed for condo {condo_id}: {new_total_seats} seats")
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Subscription webhook error: {e}")
        return {"status": "error", "message": str(e)}

@billing_router.get("/history")
async def get_billing_history(current_user = Depends(require_role("Administrador"))):
    """Get billing transaction history for the condominium"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asociado a un condominio")
    
    transactions = await db.billing_transactions.find(
        {"condominium_id": condo_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return transactions

@billing_super_admin_router.get("/overview")
async def get_all_condominiums_billing(
    current_user = Depends(require_role("SuperAdmin")),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    billing_status: Optional[str] = Query(None, description="Filter by billing_status (comma-separated for multiple)"),
    billing_provider: Optional[str] = Query(None, description="Filter by billing_provider (sinpe, stripe, manual)"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    sort_by: str = Query("next_invoice_amount", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order")
):
    """
    SuperAdmin: Get billing overview for all condominiums.
    
    OPTIMIZED v2.0:
    - Real backend pagination with skip/limit
    - Direct MongoDB filtering by billing_status and billing_provider
    - Eliminates N+1 by using aggregation pipeline
    - Uses persisted current_users field (falls back to count if not set)
    
    Query params:
    - page: Page number (1-indexed)
    - page_size: Items per page (max 100)
    - billing_status: Filter by status (comma-separated, e.g., "pending_payment,past_due")
    - billing_provider: Filter by provider (sinpe, stripe, manual)
    - search: Search by condominium name or admin email
    - sort_by: Sort field (next_invoice_amount, paid_seats, condominium_name, etc.)
    - sort_order: asc or desc
    """
    
    # Build MongoDB filter
    mongo_filter = {
        "is_demo": {"$ne": True},
        "environment": {"$ne": "demo"}
    }
    
    # Filter by billing_status if provided
    if billing_status:
        status_list = [s.strip() for s in billing_status.split(",") if s.strip()]
        if status_list:
            mongo_filter["billing_status"] = {"$in": status_list}
    
    # Filter by billing_provider if provided
    if billing_provider:
        mongo_filter["billing_provider"] = billing_provider
    
    # Search filter
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        mongo_filter["$or"] = [
            {"name": search_regex},
            {"admin_email": search_regex},
            {"contact_email": search_regex}
        ]
    
    # Get global pricing config
    global_config = await get_global_pricing()
    default_price = global_config.get("price_per_seat", 2.99)
    
    # Build aggregation pipeline (ELIMINATES N+1)
    pipeline = [
        # Stage 1: Match filter
        {"$match": mongo_filter},
        
        # Stage 2: Lookup users count per condominium (single query, not N+1)
        {"$lookup": {
            "from": "users",
            "let": {"condo_id": "$id"},
            "pipeline": [
                {"$match": {
                    "$expr": {
                        "$and": [
                            {"$eq": ["$condominium_id", "$$condo_id"]},
                            {"$eq": ["$is_active", True]}
                        ]
                    }
                }},
                {"$count": "count"}
            ],
            "as": "user_count_result"
        }},
        
        # Stage 3: Add computed fields
        {"$addFields": {
            "active_users_computed": {
                "$ifNull": [
                    {"$arrayElemAt": ["$user_count_result.count", 0]},
                    {"$ifNull": ["$current_users", 0]}
                ]
            },
            "effective_price": {
                "$ifNull": [
                    "$seat_price_override",
                    {"$ifNull": ["$price_per_seat", default_price]}
                ]
            }
        }},
        
        # Stage 4: Project final fields
        {"$project": {
            "_id": 0,
            "condominium_id": "$id",
            "condominium_name": "$name",
            "admin_email": {"$ifNull": ["$admin_email", "$contact_email"]},
            "paid_seats": {"$ifNull": ["$paid_seats", 10]},
            "current_users": "$active_users_computed",
            "remaining_seats": {
                "$max": [0, {"$subtract": [{"$ifNull": ["$paid_seats", 10]}, "$active_users_computed"]}]
            },
            "billing_status": {"$ifNull": ["$billing_status", "active"]},
            "billing_cycle": {"$ifNull": ["$billing_cycle", "monthly"]},
            "billing_provider": {"$ifNull": ["$billing_provider", "manual"]},
            "next_invoice_amount": {"$ifNull": ["$next_invoice_amount", 0]},
            "next_billing_date": "$next_billing_date",
            "price_per_seat": "$effective_price",
            "seat_price_override": "$seat_price_override",
            "yearly_discount_percent": {"$ifNull": ["$yearly_discount_percent", 10]},
            "uses_override": {
                "$and": [
                    {"$ne": ["$seat_price_override", None]},
                    {"$gt": ["$seat_price_override", 0]}
                ]
            },
            "stripe_customer_id": "$stripe_customer_id",
            "stripe_subscription_id": "$stripe_subscription_id",
            "environment": "$environment",
            "is_demo": "$is_demo",
            "created_at": "$created_at"
        }}
    ]
    
    # Build sort stage
    sort_field_map = {
        "next_invoice_amount": "next_invoice_amount",
        "paid_seats": "paid_seats",
        "condominium_name": "condominium_name",
        "billing_status": "billing_status",
        "next_billing_date": "next_billing_date",
        "current_users": "current_users"
    }
    sort_field = sort_field_map.get(sort_by, "next_invoice_amount")
    sort_direction = 1 if sort_order == "asc" else -1
    pipeline.append({"$sort": {sort_field: sort_direction}})
    
    # Get total count before pagination (using same filter)
    total_count = await db.condominiums.count_documents(mongo_filter)
    
    # Add pagination
    skip = (page - 1) * page_size
    pipeline.append({"$skip": skip})
    pipeline.append({"$limit": page_size})
    
    # Execute aggregation
    condos = await db.condominiums.aggregate(pipeline).to_list(page_size)
    
    # Calculate totals for filtered results (separate aggregation for accuracy)
    totals_pipeline = [
        {"$match": mongo_filter},
        {"$lookup": {
            "from": "users",
            "let": {"condo_id": "$id"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$condominium_id", "$$condo_id"]},
                    {"$eq": ["$is_active", True]}
                ]}}},
                {"$count": "count"}
            ],
            "as": "user_count_result"
        }},
        {"$group": {
            "_id": None,
            "total_paid_seats": {"$sum": {"$ifNull": ["$paid_seats", 10]}},
            "total_active_users": {
                "$sum": {"$ifNull": [{"$arrayElemAt": ["$user_count_result.count", 0]}, {"$ifNull": ["$current_users", 0]}]}
            },
            "total_monthly_revenue": {"$sum": {"$ifNull": ["$next_invoice_amount", 0]}}
        }}
    ]
    
    totals_result = await db.condominiums.aggregate(totals_pipeline).to_list(1)
    totals = totals_result[0] if totals_result else {
        "total_paid_seats": 0,
        "total_active_users": 0,
        "total_monthly_revenue": 0
    }
    
    return {
        "condominiums": condos,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size if total_count > 0 else 0,
            "has_next": skip + page_size < total_count,
            "has_prev": page > 1
        },
        "totals": {
            "total_condominiums": total_count,
            "total_paid_seats": totals.get("total_paid_seats", 0),
            "total_active_users": totals.get("total_active_users", 0),
            "total_monthly_revenue": round(totals.get("total_monthly_revenue", 0), 2)
        }
    }


# Legacy endpoint for backwards compatibility (deprecated)
@billing_super_admin_router.get("/overview-legacy")
async def get_all_condominiums_billing_legacy(current_user = Depends(require_role("SuperAdmin"))):
    """
    DEPRECATED: Use /super-admin/billing/overview with pagination params instead.
    This endpoint is kept for backwards compatibility but will be removed.
    """
    condos = await db.condominiums.find({"is_active": True}, {"_id": 0}).to_list(1000)
    
    # Get global pricing for comparison
    global_config = await get_global_pricing()
    
    overview = []
    total_revenue = 0
    total_users = 0
    total_seats = 0
    
    for condo in condos:
        condo_id = condo.get("id")
        active_users = await count_active_users(condo_id)
        paid_seats = condo.get("paid_seats", 10)
        
        # PHASE 4: Use dynamic pricing per condo
        price_per_seat = await get_effective_seat_price(condo_id)
        monthly_revenue = round(paid_seats * price_per_seat, 2)
        
        overview.append({
            "condominium_id": condo_id,
            "condominium_name": condo.get("name", ""),
            "paid_seats": paid_seats,
            "active_users": active_users,
            "remaining_seats": max(0, paid_seats - active_users),
            "billing_status": condo.get("billing_status", "active"),
            "monthly_revenue": monthly_revenue,
            "price_per_seat": price_per_seat,
            "uses_override": condo.get("seat_price_override") is not None and condo.get("seat_price_override") > 0,
            "stripe_customer_id": condo.get("stripe_customer_id"),
            "stripe_subscription_id": condo.get("stripe_subscription_id")
        })
        
        total_revenue += monthly_revenue
        total_users += active_users
        total_seats += paid_seats
    
    return {
        "condominiums": overview,
        "totals": {
            "total_condominiums": len(condos),
            "total_paid_seats": total_seats,
            "total_active_users": total_users,
            "total_monthly_revenue": total_revenue
        }
    }


@api_router.patch("/super-admin/condominiums/{condo_id}/billing")
async def update_condominium_billing(
    condo_id: str,
    paid_seats: Optional[int] = None,
    billing_status: Optional[str] = None,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    current_user = Depends(require_role("SuperAdmin"))
):
    """SuperAdmin: Update condominium billing settings"""
    condo = await db.condominiums.find_one({"id": condo_id})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if paid_seats is not None:
        # Prevent downgrading below active users
        active_users = await count_active_users(condo_id)
        if paid_seats < active_users:
            raise HTTPException(
                status_code=400, 
                detail=f"No se puede reducir a {paid_seats} asientos. Hay {active_users} usuarios activos."
            )
        update_data["paid_seats"] = paid_seats
    
    if billing_status is not None:
        if billing_status not in ["active", "past_due", "cancelled", "trialing"]:
            raise HTTPException(status_code=400, detail="Estado de facturación inválido")
        update_data["billing_status"] = billing_status
    
    if stripe_customer_id is not None:
        update_data["stripe_customer_id"] = stripe_customer_id
    
    if stripe_subscription_id is not None:
        update_data["stripe_subscription_id"] = stripe_subscription_id
    
    await db.condominiums.update_one({"id": condo_id}, {"$set": update_data})
    
    await log_billing_event(
        "billing_updated_by_superadmin",
        condo_id,
        {"updates": update_data},
        current_user["id"]
    )
    
    return {"message": "Configuración de facturación actualizada", "updates": update_data}

# ==================== AUDIT MODULE ====================
@api_router.get("/audit/logs")
async def get_audit_logs(
    module: Optional[str] = None,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user = Depends(require_module("audit"))
):
    """
    Get audit logs - TENANT ISOLATED.
    
    - SuperAdmin: sees ALL logs from all condominiums
    - Administrador: sees ONLY logs from their condominium
    - Other roles: access denied
    """
    roles = current_user.get("roles", [])
    
    # Verify role
    if not any(role in roles for role in ["Administrador", "SuperAdmin"]):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    query = {}
    
    # CRITICAL: Multi-tenant isolation
    # SuperAdmin sees all, others see ONLY their condominium
    if "SuperAdmin" not in roles:
        condo_id = current_user.get("condominium_id")
        if condo_id:
            query["condominium_id"] = condo_id
        else:
            # No condominium assigned - return empty
            return []
    
    if module:
        query["module"] = module
    if event_type:
        query["event_type"] = event_type
    if user_id:
        query["user_id"] = user_id
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(500)
    return logs

@api_router.get("/audit/stats")
async def get_audit_stats(current_user = Depends(require_module("audit"))):
    """
    Get audit statistics - TENANT ISOLATED.
    
    - SuperAdmin: sees global stats
    - Administrador: sees ONLY stats from their condominium
    """
    roles = current_user.get("roles", [])
    
    # Verify role
    if not any(role in roles for role in ["Administrador", "SuperAdmin"]):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    # Build tenant filter
    base_query = {}
    if "SuperAdmin" not in roles:
        condo_id = current_user.get("condominium_id")
        if condo_id:
            base_query["condominium_id"] = condo_id
        else:
            return {
                "total_events": 0,
                "today_events": 0,
                "login_failures": 0,
                "panic_events": 0
            }
    
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    
    total_events = await db.audit_logs.count_documents(base_query)
    today_events = await db.audit_logs.count_documents({**base_query, "timestamp": {"$gte": today_start}})
    login_failures = await db.audit_logs.count_documents({**base_query, "event_type": "login_failure"})
    panic_events = await db.audit_logs.count_documents({**base_query, "event_type": "panic_button"})
    
    return {
        "total_events": total_events,
        "today_events": today_events,
        "login_failures": login_failures,
        "panic_events": panic_events
    }

@api_router.get("/audit/export")
async def export_audit_logs_pdf(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    event_type: Optional[str] = None,
    current_user = Depends(require_module("audit"))
):
    """
    Export audit logs as PDF file.
    - Requires Administrador or SuperAdmin role
    - Applies tenant filtering (multi-tenant safe)
    - Returns direct PDF download
    """
    # Verify role
    roles = current_user.get("roles", [])
    if not any(role in roles for role in ["Administrador", "SuperAdmin"]):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    # Build query - SuperAdmin sees all, others see their condo
    condo_id = current_user.get("condominium_id")
    query = {}
    
    # CRITICAL: Apply strict tenant filter
    # SuperAdmin sees all, others see ONLY their condo (no system logs)
    if "SuperAdmin" not in roles:
        if condo_id:
            query["condominium_id"] = condo_id
        else:
            # No condominium assigned - return empty PDF
            raise HTTPException(status_code=403, detail="No tiene condominio asignado")
    
    # Apply date filters (timestamp field is ISO string)
    if from_date:
        try:
            # Validate date format
            datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            query["timestamp"] = query.get("timestamp", {})
            query["timestamp"]["$gte"] = from_date
        except ValueError:
            pass
    
    if to_date:
        try:
            # Validate date format
            datetime.fromisoformat(to_date.replace('Z', '+00:00'))
            query["timestamp"] = query.get("timestamp", {})
            query["timestamp"]["$lte"] = to_date
        except ValueError:
            pass
    
    # Apply event type filter
    if event_type:
        query["event_type"] = event_type
    
    # DIAGNOSTIC LOG
    logger.info(f"[AUDIT-EXPORT] Query filter: {query}")
    
    # Fetch logs (max 1000 to avoid huge PDFs)
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(1000)
    
    # DIAGNOSTIC LOG
    logger.info(f"[AUDIT-EXPORT] Total logs encontrados: {len(logs)}")
    
    # Get condominium name for the header
    condo_name = "Todos los Condominios"
    if condo_id:
        condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "name": 1})
        if condo:
            condo_name = condo.get("name", "Condominio")
    elif "SuperAdmin" in roles:
        condo_name = "Todos los Condominios (SuperAdmin)"
    
    # Generate PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=6,
        alignment=TA_CENTER
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    # Build content
    elements = []
    
    # Title
    elements.append(Paragraph("GENTURIX - Reporte de Auditoría", title_style))
    
    # Subtitle with date and condo
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    subtitle_text = f"Condominio: {condo_name}<br/>Fecha de generación: {now_str}"
    if from_date or to_date:
        date_range = f"Período: {from_date or 'Inicio'} a {to_date or 'Ahora'}"
        subtitle_text += f"<br/>{date_range}"
    elements.append(Paragraph(subtitle_text, subtitle_style))
    
    elements.append(Spacer(1, 12))
    
    if logs:
        # Pre-fetch user names for all user_ids in logs
        user_ids = list(set(log.get("user_id") for log in logs if log.get("user_id")))
        users_map = {}
        if user_ids:
            users = await db.users.find(
                {"id": {"$in": user_ids}}, 
                {"_id": 0, "id": 1, "full_name": 1, "email": 1}
            ).to_list(None)
            users_map = {u["id"]: u.get("full_name") or u.get("email", "Usuario") for u in users}
        
        # Table header
        table_data = [["Fecha", "Usuario", "Evento", "Módulo", "IP"]]
        
        # Table rows
        for log in logs:
            # Format timestamp
            timestamp = log.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    timestamp = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    timestamp = str(timestamp)[:16]
            
            # Get user name from pre-fetched map or fallback
            user_id = log.get("user_id", "")
            user_name = users_map.get(user_id, log.get("user_name", "Sistema"))
            if len(str(user_name)) > 25:
                user_name = str(user_name)[:22] + "..."
            
            # Event type
            event_type_val = log.get("event_type", "N/A")
            if len(str(event_type_val)) > 25:
                event_type_val = str(event_type_val)[:22] + "..."
            
            # Module/Resource
            module = log.get("module", log.get("resource_type", "N/A"))
            if len(str(module)) > 15:
                module = str(module)[:12] + "..."
            
            # IP Address
            ip_address = log.get("ip_address", "N/A")
            if len(str(ip_address)) > 15:
                ip_address = str(ip_address)[:12] + "..."
            
            table_data.append([
                timestamp,
                user_name,
                event_type_val,
                module,
                ip_address
            ])
        
        # Create table with adjusted column widths
        col_widths = [85, 110, 130, 70, 80]
        table = Table(table_data, colWidths=col_widths)
        
        # Table style
        table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Body style
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#334155')),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F8FAFC'), colors.white]),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ]))
        
        elements.append(table)
        
        # Footer with count
        elements.append(Spacer(1, 20))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#64748B'),
            alignment=TA_LEFT
        )
        elements.append(Paragraph(f"Total de registros: {len(logs)}", footer_style))
        if len(logs) == 1000:
            elements.append(Paragraph("(Limitado a 1000 registros)", footer_style))
    else:
        # No records message
        no_data_style = ParagraphStyle(
            'NoData',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#94A3B8'),
            alignment=TA_CENTER,
            spaceBefore=50
        )
        elements.append(Paragraph("Sin registros de auditoría para los filtros seleccionados.", no_data_style))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    # FINAL LOG
    logger.info(f"[AUDIT-EXPORT] PDF generado con {len(logs)} registros, tamaño: {len(pdf_bytes)} bytes")
    
    # Log the export action
    await log_audit_event(
        AuditEventType.SECURITY_ALERT,
        current_user["id"],
        "audit_logs",
        {"action": "export_pdf", "records_count": len(logs)},
        "system",
        "pdf_export"
    )
    
    # Return PDF file
    filename = f"audit-report-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

# ==================== DASHBOARD ====================
@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user = Depends(get_current_user)):
    """Dashboard stats - scoped by condominium for Admin, global for SuperAdmin"""
    roles = current_user.get("roles", [])
    
    # Use tenant_filter for consistent scoping
    condo_filter = tenant_filter(current_user)
    
    # SuperAdmin sees global data (empty filter)
    if "SuperAdmin" in roles:
        stats = {
            "total_users": await db.users.count_documents({}),
            "active_guards": await db.guards.count_documents({"status": "active"}),
            "active_alerts": await db.panic_events.count_documents({"status": "active"}),
            "total_courses": await db.courses.count_documents({}),
            "pending_payments": await db.payment_transactions.count_documents({"payment_status": "pending"})
        }
    else:
        # Admin/others see only their condominium data
        stats = {
            "total_users": await db.users.count_documents(condo_filter),
            "active_guards": await db.guards.count_documents(tenant_filter(current_user, {"status": "active"})),
            "active_alerts": await db.panic_events.count_documents(tenant_filter(current_user, {"status": "active"})),
            "total_courses": await db.courses.count_documents(condo_filter),
            "pending_payments": await db.payment_transactions.count_documents(tenant_filter(current_user, {"payment_status": "pending"}))
        }
    return stats

@api_router.get("/dashboard/recent-activity")
async def get_recent_activity(current_user = Depends(get_current_user)):
    """
    Recent activity combining multiple sources:
    - Audit logs (logins, user changes)
    - Visitor entries (check-ins)
    - Panic events
    - Reservations
    Scoped by condominium for Admin, global for SuperAdmin
    """
    roles = current_user.get("roles", [])
    
    activities = []
    
    # Use tenant_filter for consistent scoping
    condo_query = tenant_filter(current_user)
    
    # 1. Audit logs (logins, user actions)
    audit_logs = await db.audit_logs.find(condo_query, {"_id": 0}).sort("timestamp", -1).to_list(10)
    for log in audit_logs:
        activities.append({
            "id": log.get("id"),
            "event_type": log.get("event_type"),
            "module": log.get("module"),
            "description": log.get("description") or log.get("event_type", "").replace("_", " ").title(),
            "user_name": log.get("user_name") or log.get("email"),
            "timestamp": log.get("timestamp"),
            "source": "audit"
        })
    
    # 2. Visitor entries (check-ins)
    entries = await db.visitor_entries.find(condo_query, {"_id": 0}).sort("entry_at", -1).to_list(10)
    for entry in entries:
        activities.append({
            "id": entry.get("id"),
            "event_type": "visitor_checkin",
            "module": "security",
            "description": f"{entry.get('visitor_name')} - Entrada de visitante",
            "user_name": entry.get("guard_name"),
            "timestamp": entry.get("entry_at"),
            "details": {
                "visitor_name": entry.get("visitor_name"),
                "authorization_type": entry.get("authorization_type"),
                "destination": entry.get("destination")
            },
            "source": "visitor"
        })
    
    # 3. Panic events (alerts)
    panic_events = await db.panic_events.find(condo_query, {"_id": 0}).sort("created_at", -1).to_list(5)
    for event in panic_events:
        activities.append({
            "id": event.get("id"),
            "event_type": "panic_alert",
            "module": "security",
            "description": f"Alerta: {event.get('panic_type_label', event.get('panic_type', 'Emergencia'))}",
            "user_name": event.get("user_name"),
            "timestamp": event.get("created_at"),
            "details": {
                "location": event.get("location"),
                "status": event.get("status")
            },
            "source": "panic"
        })
    
    # 4. Reservations
    reservations = await db.reservations.find(condo_query, {"_id": 0}).sort("created_at", -1).to_list(5)
    for res in reservations:
        activities.append({
            "id": res.get("id"),
            "event_type": "reservation_created",
            "module": "reservations",
            "description": f"Reservación: {res.get('area_name', 'Área común')}",
            "user_name": res.get("resident_name"),
            "timestamp": res.get("created_at"),
            "details": {
                "area_name": res.get("area_name"),
                "date": res.get("date"),
                "status": res.get("status")
            },
            "source": "reservation"
        })
    
    # Sort all by timestamp (most recent first)
    activities.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    
    return activities[:20]

# ==================== USERS MANAGEMENT ====================
@api_router.get("/users")
async def get_users(current_user = Depends(require_role("Administrador"))):
    """Get users - scoped by condominium"""
    query = {}
    if "SuperAdmin" not in current_user.get("roles", []):
        condo_id = current_user.get("condominium_id")
        if condo_id:
            query["condominium_id"] = condo_id
    users = await db.users.find(query, {"_id": 0, "hashed_password": 0}).to_list(100)
    return users

@api_router.put("/users/{user_id}/roles")
async def update_user_roles(user_id: str, roles: List[str], current_user = Depends(require_role("Administrador"))):
    """Update user roles - only for users in same condominium"""
    # Verify user belongs to same condominium
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if "SuperAdmin" not in current_user.get("roles", []):
        if target_user.get("condominium_id") != current_user.get("condominium_id"):
            raise HTTPException(status_code=403, detail="No tienes permiso para modificar este usuario")
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"roles": roles, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Roles updated"}

# ==================== SEAT MANAGEMENT MODELS ====================
# NOTE: UserStatusUpdateV2 model moved to modules/users/models.py
# NOTE: SeatUsageResponse and SeatReductionValidation are imported from modules.billing.models

# ==================== SEAT MANAGEMENT ENDPOINTS ====================

@api_router.get("/admin/seat-usage")
async def get_seat_usage(current_user = Depends(require_role("Administrador", "SuperAdmin"))):
    """
    Get detailed seat usage for the condominium.
    Returns seat_limit, active_residents (calculated dynamically), and availability.
    """
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asociado a un condominio")
    
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    seat_limit = condo.get("paid_seats", 10)
    
    # Count active residents dynamically (status='active' AND role='Residente')
    active_residents = await db.users.count_documents({
        "condominium_id": condo_id,
        "roles": {"$in": ["Residente"]},
        "$or": [
            {"status": "active"},
            {"status": {"$exists": False}, "is_active": True}  # Backward compatibility
        ]
    })
    
    # Count total users by role
    pipeline = [
        {"$match": {"condominium_id": condo_id, "roles": {"$not": {"$in": ["SuperAdmin"]}}}},
        {"$unwind": "$roles"},
        {"$group": {"_id": "$roles", "count": {"$sum": 1}}}
    ]
    role_counts = await db.users.aggregate(pipeline).to_list(100)
    users_by_role = {item["_id"]: item["count"] for item in role_counts}
    
    # Count users by status
    status_pipeline = [
        {"$match": {"condominium_id": condo_id, "roles": {"$not": {"$in": ["SuperAdmin"]}}}},
        {"$group": {
            "_id": {"$ifNull": ["$status", {"$cond": [{"$eq": ["$is_active", False]}, "blocked", "active"]}]},
            "count": {"$sum": 1}
        }}
    ]
    status_counts = await db.users.aggregate(status_pipeline).to_list(100)
    users_by_status = {item["_id"]: item["count"] for item in status_counts}
    
    total_users = await db.users.count_documents({
        "condominium_id": condo_id,
        "roles": {"$not": {"$in": ["SuperAdmin"]}}
    })
    
    return {
        "seat_limit": seat_limit,
        "active_residents": active_residents,
        "available_seats": max(0, seat_limit - active_residents),
        "total_users": total_users,
        "users_by_role": users_by_role,
        "users_by_status": users_by_status,
        "can_add_resident": active_residents < seat_limit,
        "billing_status": condo.get("billing_status", "active")
    }

@api_router.post("/admin/validate-seat-reduction")
async def validate_seat_reduction(
    validation: SeatReductionValidation,
    current_user = Depends(require_role("Administrador", "SuperAdmin"))
):
    """
    Validate if seat reduction is allowed.
    Returns error if activeResidents > newSeatLimit.
    """
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asociado a un condominio")
    
    # Count active residents
    active_residents = await db.users.count_documents({
        "condominium_id": condo_id,
        "roles": {"$in": ["Residente"]},
        "$or": [
            {"status": "active"},
            {"status": {"$exists": False}, "is_active": True}
        ]
    })
    
    if active_residents > validation.new_seat_limit:
        residents_to_remove = active_residents - validation.new_seat_limit
        return {
            "can_reduce": False,
            "current_active_residents": active_residents,
            "new_seat_limit": validation.new_seat_limit,
            "residents_to_remove": residents_to_remove,
            "message": f"Debes eliminar o bloquear {residents_to_remove} residente(s) antes de reducir el plan a {validation.new_seat_limit} asientos."
        }
    
    return {
        "can_reduce": True,
        "current_active_residents": active_residents,
        "new_seat_limit": validation.new_seat_limit,
        "residents_to_remove": 0,
        "message": "Puedes reducir el plan de forma segura."
    }

@api_router.patch("/admin/users/{user_id}/status-v2")
async def update_user_status_v2(
    user_id: str, 
    status_data: UserStatusUpdateV2,
    request: Request,
    current_user = Depends(require_role("Administrador", "SuperAdmin"))
):
    """
    Update user status with enhanced seat management.
    - Validates seat limits when activating residents
    - Invalidates user sessions when blocking/suspending
    - Updates active user counts
    """
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Admin can only update users from their condominium
    if "SuperAdmin" not in current_user.get("roles", []):
        if target_user.get("condominium_id") != current_user.get("condominium_id"):
            raise HTTPException(status_code=403, detail="No tienes permiso para modificar este usuario")
    
    # Cannot modify yourself
    if target_user["id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="No puedes modificar tu propio estado")
    
    condo_id = target_user.get("condominium_id")
    is_resident = "Residente" in target_user.get("roles", [])
    old_status = target_user.get("status", "active" if target_user.get("is_active", True) else "blocked")
    new_status = status_data.status
    
    # If activating a resident, check seat limit
    if new_status == "active" and is_resident and old_status != "active":
        condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "paid_seats": 1})
        seat_limit = condo.get("paid_seats", 10) if condo else 10
        
        active_residents = await db.users.count_documents({
            "condominium_id": condo_id,
            "roles": {"$in": ["Residente"]},
            "$or": [
                {"status": "active"},
                {"status": {"$exists": False}, "is_active": True}
            ]
        })
        
        if active_residents >= seat_limit:
            raise HTTPException(
                status_code=400, 
                detail=f"No hay asientos disponibles ({active_residents}/{seat_limit}). Aumenta tu plan o bloquea otros residentes primero."
            )
    
    # Prepare update
    update_data = {
        "status": new_status,
        "is_active": new_status == "active",
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # If blocking/suspending, invalidate sessions by setting status_changed_at
    if new_status in ["blocked", "suspended"]:
        update_data["status_changed_at"] = datetime.now(timezone.utc).isoformat()
        if status_data.reason:
            update_data["status_reason"] = status_data.reason
    
    result = await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="No se pudo actualizar el usuario")
    
    # Update active user count
    if condo_id:
        await update_active_user_count(condo_id)
    
    # Determine audit event type
    if new_status == "blocked":
        event_type = AuditEventType.USER_BLOCKED
    elif new_status == "suspended":
        event_type = AuditEventType.USER_SUSPENDED
    elif new_status == "active" and old_status in ["blocked", "suspended"]:
        event_type = AuditEventType.USER_UNBLOCKED
    else:
        event_type = AuditEventType.USER_UPDATED
    
    await log_audit_event(
        event_type,
        current_user["id"],
        "users",
        {
            "target_user_id": user_id,
            "target_user_email": target_user.get("email"),
            "target_role": target_user.get("roles", []),
            "old_status": old_status,
            "new_status": new_status,
            "reason": status_data.reason,
            "is_resident": is_resident
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    status_messages = {
        "active": "activado",
        "blocked": "bloqueado",
        "suspended": "suspendido"
    }
    
    return {
        "message": f"Usuario {status_messages.get(new_status, new_status)} exitosamente",
        "user_id": user_id,
        "new_status": new_status,
        "session_invalidated": new_status in ["blocked", "suspended"]
    }

@api_router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    request: Request,
    current_user = Depends(require_role("Administrador", "SuperAdmin"))
):
    """
    Delete a user permanently.
    - Releases the seat if the user is a resident
    - Cannot delete yourself
    - Cannot delete SuperAdmins
    """
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Admin can only delete users from their condominium
    if "SuperAdmin" not in current_user.get("roles", []):
        if target_user.get("condominium_id") != current_user.get("condominium_id"):
            raise HTTPException(status_code=403, detail="No tienes permiso para eliminar este usuario")
    
    # Cannot delete yourself
    if target_user["id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")
    
    # Cannot delete SuperAdmins
    if "SuperAdmin" in target_user.get("roles", []):
        raise HTTPException(status_code=403, detail="No puedes eliminar un SuperAdmin")
    
    condo_id = target_user.get("condominium_id")
    is_resident = "Residente" in target_user.get("roles", [])
    
    # Delete the user
    result = await db.users.delete_one({"id": user_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No se pudo eliminar el usuario")
    
    # Update active user count (releases the seat)
    if condo_id:
        await update_active_user_count(condo_id)
    
    # Log audit event
    await log_audit_event(
        AuditEventType.USER_DELETED,
        current_user["id"],
        "users",
        {
            "deleted_user_id": user_id,
            "deleted_user_email": target_user.get("email"),
            "deleted_user_roles": target_user.get("roles", []),
            "was_resident": is_resident,
            "seat_released": is_resident
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "message": "Usuario eliminado exitosamente",
        "user_id": user_id,
        "seat_released": is_resident
    }

# ==================== LEGACY STATUS ENDPOINT (kept for backward compatibility) ====================
class UserStatusUpdate(BaseModel):
    is_active: bool

@api_router.patch("/admin/users/{user_id}/status")
async def update_user_status(
    user_id: str, 
    status_data: UserStatusUpdate,
    request: Request,
    current_user = Depends(require_role("Administrador", "SuperAdmin"))
):
    """Update user active status (Admin only)"""
    # Get the user to update
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Admin can only update users from their condominium
    if "SuperAdmin" not in current_user.get("roles", []):
        if target_user.get("condominium_id") != current_user.get("condominium_id"):
            raise HTTPException(status_code=403, detail="No tienes permiso para modificar este usuario")
    
    # Cannot deactivate yourself
    if target_user["id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="No puedes desactivarte a ti mismo")
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_active": status_data.is_active, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="No se pudo actualizar el usuario")
    
    # ==================== UPDATE ACTIVE USER COUNT ====================
    condo_id = target_user.get("condominium_id")
    if condo_id:
        await update_active_user_count(condo_id)
        await log_billing_event(
            "user_status_changed",
            condo_id,
            {"user_id": user_id, "new_status": "active" if status_data.is_active else "inactive"},
            current_user["id"]
        )
    # ==================================================================
    
    # Log audit event
    await log_audit_event(
        AuditEventType.USER_UPDATED,
        current_user["id"],
        "users",
        {
            "action": "status_change",
            "target_user_id": user_id,
            "target_user_email": target_user.get("email"),
            "new_status": "active" if status_data.is_active else "inactive"
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": f"Usuario {'activado' if status_data.is_active else 'desactivado'} exitosamente"}

# ==================== ENTERPRISE PASSWORD RESET SYSTEM ====================
@api_router.post("/admin/users/{user_id}/reset-password")
async def admin_reset_user_password(
    user_id: str,
    request: Request,
    current_user = Depends(require_role("Administrador", "SuperAdmin"))
):
    """
    Enterprise-grade password reset by Admin.
    - Generates secure reset token (expires in 1 hour)
    - Sends email with reset link (NOT temporary password)
    - Invalidates all existing sessions
    - Logs audit event with full context
    - Does NOT expose password to admin
    """
    # Find user
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    user_roles = user.get("roles", [])
    condo_id = user.get("condominium_id")
    admin_roles = current_user.get("roles", [])
    admin_condo_id = current_user.get("condominium_id")
    
    # ==================== SECURITY VALIDATIONS ====================
    # 1. Cannot reset your own password via this endpoint
    if user["id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="No puedes restablecer tu propia contraseña con este método. Usa 'Cambiar Contraseña'.")
    
    # 2. Cannot reset SuperAdmin passwords (only SuperAdmin can do it for themselves)
    if "SuperAdmin" in user_roles:
        raise HTTPException(status_code=403, detail="No se puede restablecer la contraseña de un SuperAdmin")
    
    # 3. Admins cannot reset other Admin passwords (prevents privilege escalation)
    if "Administrador" in user_roles and "SuperAdmin" not in admin_roles:
        raise HTTPException(status_code=403, detail="No tienes permiso para restablecer la contraseña de otro Administrador")
    
    # 4. Admins can only reset users from their own condominium
    if "SuperAdmin" not in admin_roles:
        if condo_id != admin_condo_id:
            raise HTTPException(status_code=403, detail="No tienes permiso para modificar usuarios de otro condominio")
    
    # ==================== GENERATE RESET TOKEN ====================
    reset_token = create_password_reset_token(user["id"], user["email"])
    
    # Store token hash and metadata in user record for validation
    token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
    reset_timestamp = datetime.now(timezone.utc)
    
    await db.users.update_one(
        {"id": user_id},
        {
            "$set": {
                "password_reset_token_hash": token_hash,
                "password_reset_requested_at": reset_timestamp.isoformat(),
                "password_reset_requested_by": current_user["id"],
                "password_reset_required": True,
                # Invalidate all existing sessions
                "password_changed_at": reset_timestamp.isoformat()
            }
        }
    )
    
    # ==================== SEND RESET EMAIL ====================
    # Build reset link
    frontend_url = os.environ.get('REACT_APP_BACKEND_URL', 'https://localhost:3000').replace('/api', '')
    # If it doesn't have protocol, add it
    if not frontend_url.startswith('http'):
        frontend_url = f"https://{frontend_url}"
    reset_link = f"{frontend_url}/reset-password?token={reset_token}"
    
    email_result = await send_password_reset_link_email(
        recipient_email=user["email"],
        user_name=user.get("full_name", "Usuario"),
        reset_link=reset_link,
        admin_name=current_user.get("full_name", "Administrador")
    )
    
    # ==================== AUDIT LOGGING ====================
    await log_audit_event(
        AuditEventType.PASSWORD_RESET_BY_ADMIN,
        current_user["id"],
        "users",
        {
            "action": "password_reset_initiated",
            "target_user_id": user_id,
            "target_email": user["email"],
            "target_roles": user_roles,
            "condominium_id": condo_id,
            "email_sent": email_result.get("status") == "success",
            "email_status": email_result.get("status"),
            "sessions_invalidated": True
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    logger.info(f"[PASSWORD-RESET] Admin {current_user['email']} initiated reset for {user['email']}")
    
    return {
        "message": "Se ha enviado un enlace de restablecimiento al correo del usuario",
        "email_status": email_result.get("status"),
        "email_sent_to": user["email"] if email_result.get("status") == "success" else None,
        "token_expires_in": "1 hour",
        "sessions_invalidated": True
    }

@api_router.post("/auth/reset-password-complete")
async def complete_password_reset(
    request: Request,
    token: str = Body(...),
    new_password: str = Body(..., min_length=8)
):
    """
    Complete password reset using the token from email link.
    Validates token, updates password, clears reset flags.
    """
    # Validate token
    payload = verify_password_reset_token(token)
    if not payload:
        raise HTTPException(status_code=400, detail="El enlace de restablecimiento es inválido o ha expirado")
    
    user_id = payload.get("sub")
    email = payload.get("email")
    
    # Find user and verify token matches
    user = await db.users.find_one({"id": user_id, "email": email})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Verify token hash matches stored hash
    stored_hash = user.get("password_reset_token_hash")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    if not stored_hash or stored_hash != token_hash:
        raise HTTPException(status_code=400, detail="Este enlace de restablecimiento ya fue utilizado o es inválido")
    
    # Validate password requirements
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres")
    if not any(c.isupper() for c in new_password):
        raise HTTPException(status_code=400, detail="La contraseña debe contener al menos una mayúscula")
    if not any(c.isdigit() for c in new_password):
        raise HTTPException(status_code=400, detail="La contraseña debe contener al menos un número")
    
    # Update password and clear reset flags
    password_changed_at = datetime.now(timezone.utc).isoformat()
    
    await db.users.update_one(
        {"id": user_id},
        {
            "$set": {
                "hashed_password": hash_password(new_password),
                "password_changed_at": password_changed_at,
                "password_reset_required": False,
                "updated_at": password_changed_at
            },
            "$unset": {
                "password_reset_token_hash": "",
                "password_reset_requested_at": "",
                "password_reset_requested_by": ""
            }
        }
    )
    
    # Log audit event
    await log_audit_event(
        AuditEventType.PASSWORD_RESET_TOKEN_USED,
        user_id,
        "users",
        {
            "action": "password_reset_completed",
            "email": email,
            "requested_by": user.get("password_reset_requested_by")
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    logger.info(f"[PASSWORD-RESET] User {email} completed password reset")
    
    return {
        "message": "Contraseña actualizada exitosamente",
        "can_login": True
    }

@api_router.get("/auth/verify-reset-token")
async def verify_reset_token_endpoint(token: str):
    """Verify if a reset token is valid (for frontend to show form)"""
    payload = verify_password_reset_token(token)
    if not payload:
        return {"valid": False, "reason": "Token inválido o expirado"}
    
    user_id = payload.get("sub")
    email = payload.get("email")
    
    # Verify user exists and token matches
    user = await db.users.find_one({"id": user_id, "email": email}, {"_id": 0, "password_reset_token_hash": 1, "full_name": 1})
    if not user:
        return {"valid": False, "reason": "Usuario no encontrado"}
    
    stored_hash = user.get("password_reset_token_hash")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    if not stored_hash or stored_hash != token_hash:
        return {"valid": False, "reason": "Este enlace ya fue utilizado"}
    
    return {
        "valid": True,
        "email": email,
        "user_name": user.get("full_name", "Usuario")
    }
# ==================== END PASSWORD RESET SYSTEM ====================

@api_router.put("/users/{user_id}/status")
async def update_user_status_legacy(user_id: str, is_active: bool, current_user = Depends(require_role("Administrador"))):
    """Legacy endpoint - use PATCH /admin/users/{user_id}/status instead"""
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_active": is_active, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Status updated"}

# ==================== INVITATION & ACCESS REQUEST MODULE ====================
# Admin can create invite links/QR codes for residents to request access

def generate_invite_token(length: int = 32) -> str:
    """Generate a secure random token for invitation links"""
    return secrets.token_urlsafe(length)

async def send_access_approved_email(
    recipient_email: str,
    user_name: str,
    condominium_name: str,
    temporary_password: str,
    login_url: str
) -> dict:
    """
    Send email when access request is approved.
    Uses centralized email service for consistent sending.
    """
    print(f"[EMAIL TRIGGER] access_approved → preparing credentials email for {recipient_email}")
    logger.info(f"[EMAIL TRIGGER] Access approved - recipient: {recipient_email}, condo: {condominium_name}")
    
    # Check if email is enabled globally
    email_enabled = await is_email_enabled()
    if not email_enabled:
        print(f"[EMAIL BLOCKED] Email toggle is OFF (recipient: {recipient_email})")
        logger.warning(f"[EMAIL BLOCKED] Global email toggle disabled for {recipient_email}")
        return {"status": "skipped", "reason": "Email sending disabled"}
    
    # Check if email service is configured
    if not is_email_configured():
        print(f"[EMAIL BLOCKED] RESEND_API_KEY not configured")
        logger.warning(f"[EMAIL BLOCKED] Email service not configured for {recipient_email}")
        return {"status": "skipped", "reason": "Email service not configured"}
    
    # Get centralized sender
    sender = get_sender()
    print(f"[EMAIL SERVICE] Using sender: {sender}")
    logger.info(f"[EMAIL SERVICE] Sender configured: {sender}")
    
    # Build HTML content using the template from email_service
    html_content = get_user_credentials_email_html(
        user_name=user_name,
        email=recipient_email,
        password=temporary_password,
        role="Residente",
        condominium_name=condominium_name,
        login_url=login_url
    )
    
    subject = f"¡Solicitud Aprobada! - {condominium_name}"
    
    try:
        print(f"[EMAIL SERVICE] Attempting to send email to {recipient_email}")
        logger.info(f"[EMAIL SERVICE] Sending approval email to {recipient_email}")
        
        # Use centralized async email sender
        result = await send_email(
            to=recipient_email,
            subject=subject,
            html=html_content,
            sender=sender
        )
        
        if result.get("success"):
            print(f"[EMAIL SENT] Successfully sent to {recipient_email} - ID: {result.get('email_id')}")
            logger.info(f"[EMAIL SENT] Access approval email sent to {recipient_email} - ID: {result.get('email_id')}")
            return {"status": "success", "email_id": result.get("email_id")}
        else:
            error_msg = result.get("error", "Unknown error")
            print(f"[EMAIL ERROR] Failed to send to {recipient_email}: {error_msg}")
            logger.error(f"[EMAIL ERROR] Failed to send approval email to {recipient_email}: {error_msg}")
            return {"status": "error", "reason": error_msg}
            
    except Exception as e:
        print(f"[EMAIL ERROR] Exception while sending to {recipient_email}: {str(e)}")
        logger.error(f"[EMAIL ERROR] Exception sending approval email to {recipient_email}: {str(e)}", exc_info=True)
        return {"status": "error", "reason": str(e)}

async def send_access_rejected_email(
    recipient_email: str,
    user_name: str,
    condominium_name: str,
    rejection_reason: Optional[str] = None
) -> dict:
    """Send email when access request is rejected"""
    email_enabled = await is_email_enabled()
    if not email_enabled:
        return {"status": "skipped", "reason": "Email sending disabled"}
    
    if not RESEND_API_KEY:
        return {"status": "skipped", "reason": "Email service not configured"}
    
    reason_text = rejection_reason or "Tu solicitud no cumple con los requisitos de verificación."
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0A0A0F; color: #ffffff; margin: 0; padding: 0;">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background-color: #0F111A; border-radius: 12px; overflow: hidden;">
            <tr>
                <td style="padding: 40px 30px; background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%);">
                    <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #ffffff;">Solicitud No Aprobada</h1>
                    <p style="margin: 8px 0 0 0; font-size: 14px; color: rgba(255,255,255,0.8);">GENTURIX - {condominium_name}</p>
                </td>
            </tr>
            <tr>
                <td style="padding: 40px 30px;">
                    <h2 style="margin: 0 0 20px 0; font-size: 22px; color: #ffffff;">Hola, {user_name}</h2>
                    <p style="margin: 0 0 20px 0; font-size: 16px; color: #9CA3AF; line-height: 1.6;">
                        Lamentamos informarte que tu solicitud de acceso a <strong>{condominium_name}</strong> no ha sido aprobada.
                    </p>
                    
                    <div style="background-color: #1E293B; border-radius: 8px; padding: 20px; margin: 20px 0;">
                        <p style="margin: 0; color: #9CA3AF; font-size: 14px;">
                            <strong>Motivo:</strong><br>
                            <span style="color: #ffffff;">{reason_text}</span>
                        </p>
                    </div>
                    
                    <p style="margin: 20px 0 0 0; font-size: 14px; color: #6B7280;">
                        Si crees que esto es un error, contacta a la administración del condominio.
                    </p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    try:
        params = {
            "from": f"GENTURIX <{SENDER_EMAIL}>",
            "to": [recipient_email],
            "subject": f"Solicitud de Acceso - {condominium_name}",
            "html": html_content
        }
        email_response = await asyncio.to_thread(resend.Emails.send, params)
        return {"status": "success", "email_id": str(email_response)}
    except Exception as e:
        logger.error(f"Failed to send rejection email: {e}")
        return {"status": "error", "reason": str(e)}

# --- Invitation Endpoints (Admin) ---

@api_router.post("/invitations")
async def create_invitation(
    invite_data: InvitationCreate,
    request: Request,
    current_user = Depends(require_role("Administrador"))
):
    """Create a new invitation link for residents to request access"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asignado a ningún condominio")
    
    # Get condominium name
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "name": 1})
    condo_name = condo.get("name", "Condominio") if condo else "Condominio"
    
    # Calculate expiration
    if invite_data.expiration_date:
        expires_at = invite_data.expiration_date
    else:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=invite_data.expiration_days)).isoformat()
    
    # Determine max uses based on limit type
    if invite_data.usage_limit_type == InvitationUsageLimitEnum.SINGLE:
        max_uses = 1
    elif invite_data.usage_limit_type == InvitationUsageLimitEnum.UNLIMITED:
        max_uses = 999999  # Effectively unlimited
    else:
        max_uses = invite_data.max_uses
    
    invitation = {
        "id": str(uuid.uuid4()),
        "token": generate_invite_token(),
        "condominium_id": condo_id,
        "condominium_name": condo_name,
        "created_by_id": current_user["id"],
        "created_by_name": current_user.get("full_name", "Admin"),
        "expires_at": expires_at,
        "usage_limit_type": invite_data.usage_limit_type.value,
        "max_uses": max_uses,
        "current_uses": 0,
        "is_active": True,
        "notes": invite_data.notes,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.invitations.insert_one(invitation)
    
    # Log audit event
    await log_audit_event(
        AuditEventType.USER_CREATED,
        current_user["id"],
        "invitations",
        {"action": "invitation_created", "invitation_id": invitation["id"], "expires_at": expires_at},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    # Build invite URL (frontend will handle this)
    base_url = request.headers.get("origin", "")
    invite_url = f"{base_url}/join/{invitation['token']}"
    
    return {
        **{k: v for k, v in invitation.items() if k != "_id"},
        "invite_url": invite_url,
        "is_expired": datetime.fromisoformat(expires_at.replace('Z', '+00:00')) < datetime.now(timezone.utc)
    }

@api_router.get("/invitations")
async def get_invitations(
    current_user = Depends(require_role("Administrador"))
):
    """Get all invitations for the admin's condominium"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asignado a ningún condominio")
    
    invitations = await db.invitations.find(
        {"condominium_id": condo_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    now = datetime.now(timezone.utc)
    base_url = ""  # Will be filled by frontend
    
    for inv in invitations:
        expires_at = datetime.fromisoformat(inv["expires_at"].replace('Z', '+00:00'))
        inv["is_expired"] = expires_at < now
        inv["invite_url"] = f"/join/{inv['token']}"
    
    return invitations

@api_router.delete("/invitations/{invitation_id}")
async def revoke_invitation(
    invitation_id: str,
    request: Request,
    current_user = Depends(require_role("Administrador"))
):
    """Revoke/deactivate an invitation"""
    condo_id = current_user.get("condominium_id")
    
    invitation = await db.invitations.find_one({
        "id": invitation_id,
        "condominium_id": condo_id
    })
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    
    await db.invitations.update_one(
        {"id": invitation_id},
        {"$set": {"is_active": False, "revoked_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Log audit event
    await log_audit_event(
        AuditEventType.USER_UPDATED,
        current_user["id"],
        "invitations",
        {"action": "invitation_revoked", "invitation_id": invitation_id},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "Invitación revocada exitosamente"}

# --- Public Invitation Endpoints (No Auth Required) ---

@api_router.get("/invitations/{token}/info")
async def get_invitation_info(token: str):
    """Get public info about an invitation (no auth required)"""
    invitation = await db.invitations.find_one({"token": token}, {"_id": 0})
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitación no válida o expirada")
    
    # Check if expired
    expires_at = datetime.fromisoformat(invitation["expires_at"].replace('Z', '+00:00'))
    is_expired = expires_at < datetime.now(timezone.utc)
    
    # Check if active
    if not invitation.get("is_active", True):
        raise HTTPException(status_code=400, detail="Esta invitación ha sido revocada")
    
    if is_expired:
        raise HTTPException(status_code=400, detail="Esta invitación ha expirado")
    
    # Check usage limit
    if invitation.get("current_uses", 0) >= invitation.get("max_uses", 1):
        if invitation.get("usage_limit_type") != "unlimited":
            raise HTTPException(status_code=400, detail="Esta invitación ha alcanzado su límite de uso")
    
    return {
        "condominium_name": invitation["condominium_name"],
        "is_valid": True
    }

@api_router.post("/invitations/{token}/request")
async def submit_access_request(
    token: str,
    request_data: AccessRequestCreate,
    request: Request
):
    """Submit an access request using an invitation link (no auth required)"""
    invitation = await db.invitations.find_one({"token": token}, {"_id": 0})
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitación no válida")
    
    # Validate invitation
    expires_at = datetime.fromisoformat(invitation["expires_at"].replace('Z', '+00:00'))
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Esta invitación ha expirado")
    
    if not invitation.get("is_active", True):
        raise HTTPException(status_code=400, detail="Esta invitación ha sido revocada")
    
    if invitation.get("usage_limit_type") != "unlimited":
        if invitation.get("current_uses", 0) >= invitation.get("max_uses", 1):
            raise HTTPException(status_code=400, detail="Esta invitación ha alcanzado su límite de uso")
    
    # Check if email already has a pending request or existing user
    existing_user = await db.users.find_one({"email": request_data.email.lower()})
    if existing_user:
        raise HTTPException(status_code=400, detail="Ya existe una cuenta con este email")
    
    existing_request = await db.access_requests.find_one({
        "email": request_data.email.lower(),
        "status": "pending_approval"
    })
    if existing_request:
        raise HTTPException(status_code=400, detail="Ya existe una solicitud pendiente con este email")
    
    # Create access request
    access_request = {
        "id": str(uuid.uuid4()),
        "invitation_id": invitation["id"],
        "condominium_id": invitation["condominium_id"],
        "condominium_name": invitation["condominium_name"],
        "full_name": request_data.full_name.strip(),
        "email": request_data.email.lower().strip(),
        "phone": request_data.phone,
        "apartment_number": request_data.apartment_number.strip(),
        "tower_block": request_data.tower_block,
        "resident_type": request_data.resident_type,
        "notes": request_data.notes,
        "status": "pending_approval",
        "status_message": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "processed_at": None,
        "processed_by_id": None,
        "processed_by_name": None
    }
    
    await db.access_requests.insert_one(access_request)
    
    # Increment invitation usage counter
    await db.invitations.update_one(
        {"id": invitation["id"]},
        {"$inc": {"current_uses": 1}}
    )
    
    # Log audit event
    await log_audit_event(
        AuditEventType.USER_CREATED,
        "public",
        "access_requests",
        {
            "action": "access_request_created",
            "request_id": access_request["id"],
            "email": access_request["email"],
            "condominium_id": access_request["condominium_id"]
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "id": access_request["id"],
        "status": "pending_approval",
        "message": "Tu solicitud ha sido enviada. Recibirás un email cuando sea procesada."
    }

@api_router.get("/invitations/{token}/request-status")
async def get_request_status(token: str, email: str):
    """Check the status of an access request (no auth required)"""
    invitation = await db.invitations.find_one({"token": token}, {"_id": 0})
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitación no válida")
    
    access_request = await db.access_requests.find_one({
        "invitation_id": invitation["id"],
        "email": email.lower()
    }, {"_id": 0})
    
    if not access_request:
        raise HTTPException(status_code=404, detail="No se encontró ninguna solicitud con este email")
    
    return {
        "status": access_request["status"],
        "status_message": access_request.get("status_message"),
        "created_at": access_request["created_at"],
        "processed_at": access_request.get("processed_at")
    }

# --- Access Request Management (Admin) ---

@api_router.get("/access-requests")
async def get_access_requests(
    status: str = "all",
    current_user = Depends(require_role("Administrador"))
):
    """Get all access requests for the admin's condominium"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asignado a ningún condominio")
    
    query = {"condominium_id": condo_id}
    if status != "all":
        query["status"] = status
    
    requests = await db.access_requests.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    
    return requests

@api_router.get("/access-requests/count")
async def get_access_requests_count(
    current_user = Depends(require_role("Administrador"))
):
    """Get count of pending access requests"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        return {"pending": 0}
    
    count = await db.access_requests.count_documents({
        "condominium_id": condo_id,
        "status": "pending_approval"
    })
    
    return {"pending": count}

@api_router.post("/access-requests/{request_id}/action")
async def process_access_request(
    request_id: str,
    action_data: AccessRequestAction,
    request: Request,
    current_user = Depends(require_role("Administrador"))
):
    """Approve or reject an access request"""
    condo_id = current_user.get("condominium_id")
    
    access_request = await db.access_requests.find_one({
        "id": request_id,
        "condominium_id": condo_id
    })
    
    if not access_request:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    if access_request["status"] != "pending_approval":
        raise HTTPException(status_code=400, detail="Esta solicitud ya ha sido procesada")
    
    now = datetime.now(timezone.utc).isoformat()
    
    if action_data.action == "approve":
        # Create user account
        temp_password = generate_temporary_password()
        
        # Get condominium name for email
        condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "name": 1})
        condo_name = condo.get("name", "Condominio") if condo else "Condominio"
        
        new_user = {
            "id": str(uuid.uuid4()),
            "email": access_request["email"],
            "full_name": access_request["full_name"],
            "hashed_password": hash_password(temp_password),
            "roles": ["Residente"],
            "condominium_id": condo_id,
            "is_active": True,
            "password_reset_required": True,
            "role_data": {
                "apartment_number": access_request["apartment_number"],
                "tower_block": access_request.get("tower_block"),
                "resident_type": access_request.get("resident_type", "owner")
            },
            "phone": access_request.get("phone"),
            "created_at": now,
            "created_via": "access_request",
            "access_request_id": request_id
        }
        
        await db.users.insert_one(new_user)
        
        print(f"[FLOW] access_request_approved | request_id={request_id} user_id={new_user['id']} email={access_request['email']}")
        logger.info(f"[FLOW] access_request_approved | request_id={request_id} user_id={new_user['id']}")
        
        # Update request status
        await db.access_requests.update_one(
            {"id": request_id},
            {"$set": {
                "status": "approved",
                "status_message": action_data.message or "Bienvenido al condominio",
                "processed_at": now,
                "processed_by_id": current_user["id"],
                "processed_by_name": current_user.get("full_name", "Admin"),
                "user_id": new_user["id"]
            }}
        )
        
        # Send email if requested
        email_result = {"status": "skipped"}
        if action_data.send_email:
            print(f"[EMAIL TRIGGER] resident_credentials | email={access_request['email']} condominium_id={condo_id} user_id={new_user['id']}")
            logger.info(f"[EMAIL TRIGGER] resident_credentials | email={access_request['email']} condo={condo_id}")
            login_url = request.headers.get("origin", "") + "/login"
            email_result = await send_access_approved_email(
                access_request["email"],
                access_request["full_name"],
                condo_name,
                temp_password,
                login_url
            )
            
            # Log email result explicitly
            if email_result.get("status") == "success":
                print(f"[EMAIL SENT] resident_credentials | email={access_request['email']} email_id={email_result.get('email_id')}")
            else:
                print(f"[EMAIL ERROR] resident_credentials_failed | email={access_request['email']} reason={email_result.get('reason', 'unknown')}")
                logger.error(f"[EMAIL ERROR] resident_credentials_failed | email={access_request['email']} reason={email_result.get('reason')}")
        
        # Log audit event
        await log_audit_event(
            AuditEventType.ACCESS_GRANTED,
            current_user["id"],
            "access_requests",
            {
                "action": "access_request_approved",
                "request_id": request_id,
                "user_id": new_user["id"],
                "email": access_request["email"]
            },
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "unknown")
        )
        
        return {
            "message": "Solicitud aprobada. Se ha creado la cuenta del usuario.",
            "user_id": new_user["id"],
            "email_sent": email_result.get("status") == "success",
            "credentials": {
                "email": access_request["email"],
                "password": temp_password if not action_data.send_email else None
            }
        }
    
    elif action_data.action == "reject":
        # Update request status
        await db.access_requests.update_one(
            {"id": request_id},
            {"$set": {
                "status": "rejected",
                "status_message": action_data.message or "Solicitud rechazada",
                "processed_at": now,
                "processed_by_id": current_user["id"],
                "processed_by_name": current_user.get("full_name", "Admin")
            }}
        )
        
        # Send rejection email if requested
        email_result = {"status": "skipped"}
        if action_data.send_email:
            condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "name": 1})
            condo_name = condo.get("name", "Condominio") if condo else "Condominio"
            email_result = await send_access_rejected_email(
                access_request["email"],
                access_request["full_name"],
                condo_name,
                action_data.message
            )
        
        # Log audit event
        await log_audit_event(
            AuditEventType.ACCESS_DENIED,
            current_user["id"],
            "access_requests",
            {
                "action": "access_request_rejected",
                "request_id": request_id,
                "email": access_request["email"],
                "reason": action_data.message
            },
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "unknown")
        )
        
        return {
            "message": "Solicitud rechazada.",
            "email_sent": email_result.get("status") == "success"
        }
    
    else:
        raise HTTPException(status_code=400, detail="Acción no válida. Use 'approve' o 'reject'")

# ==================== CONDOMINIUM SETTINGS MODULE ====================
# Admin settings for their condominium - rules for reservations, visits, notifications

@api_router.get("/admin/condominium-settings")
async def get_condominium_settings(
    current_user = Depends(require_role("Administrador"))
):
    """Get current condominium settings"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asignado a ningún condominio")
    
    # Try to find existing settings
    settings = await db.condominium_settings.find_one(
        {"condominium_id": condo_id},
        {"_id": 0}
    )
    
    # If no settings exist, create default ones
    if not settings:
        condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "name": 1})
        condo_name = condo.get("name", "Condominio") if condo else "Condominio"
        
        settings = {
            "condominium_id": condo_id,
            "condominium_name": condo_name,
            **get_default_condominium_settings(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.condominium_settings.insert_one(settings)
        # Remove _id from response
        settings.pop("_id", None)
    
    return settings

@api_router.put("/admin/condominium-settings")
async def update_condominium_settings(
    settings_update: CondominiumSettingsUpdate,
    request: Request,
    current_user = Depends(require_role("Administrador"))
):
    """Update condominium settings"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asignado a ningún condominio")
    
    # Get current settings
    current_settings = await db.condominium_settings.find_one({"condominium_id": condo_id})
    
    if not current_settings:
        # Create default settings first
        condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "name": 1})
        condo_name = condo.get("name", "Condominio") if condo else "Condominio"
        
        current_settings = {
            "condominium_id": condo_id,
            "condominium_name": condo_name,
            **get_default_condominium_settings(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.condominium_settings.insert_one(current_settings)
    
    # Build update dict with only provided fields
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if settings_update.general is not None:
        update_data["general"] = settings_update.general.model_dump()
    
    if settings_update.reservations is not None:
        update_data["reservations"] = settings_update.reservations.model_dump()
    
    if settings_update.visits is not None:
        update_data["visits"] = settings_update.visits.model_dump()
    
    if settings_update.notifications is not None:
        update_data["notifications"] = settings_update.notifications.model_dump()
    
    # Apply update
    await db.condominium_settings.update_one(
        {"condominium_id": condo_id},
        {"$set": update_data}
    )
    
    # Log audit event
    await log_audit_event(
        AuditEventType.USER_UPDATED,
        current_user["id"],
        "condominium_settings",
        {
            "action": "settings_updated",
            "condominium_id": condo_id,
            "updated_sections": [k for k in update_data.keys() if k != "updated_at"]
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    # Return updated settings
    updated_settings = await db.condominium_settings.find_one(
        {"condominium_id": condo_id},
        {"_id": 0}
    )
    
    return updated_settings

@api_router.get("/condominium-settings/public")
async def get_public_condominium_settings(
    current_user = Depends(get_current_user)
):
    """Get condominium settings (read-only for all authenticated users)"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        # SuperAdmin doesn't have a condominium
        return {"error": "No condominium assigned"}
    
    settings = await db.condominium_settings.find_one(
        {"condominium_id": condo_id},
        {"_id": 0}
    )
    
    if not settings:
        # Return defaults
        condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "name": 1})
        condo_name = condo.get("name", "Condominio") if condo else "Condominio"
        return {
            "condominium_id": condo_id,
            "condominium_name": condo_name,
            **get_default_condominium_settings(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    
    return settings

# ==================== MULTI-TENANT MODULE ====================
# Condominium/Tenant Management Endpoints (Super Admin)

@api_router.post("/condominiums", response_model=CondominiumResponse)
async def create_production_condominium(
    condo_data: CondominiumCreate,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """
    Create a new PRODUCTION condominium/tenant (Super Admin only).
    
    BILLING ENGINE INTEGRATION:
    - Calculates initial invoice based on seats and billing cycle
    - Creates billing event audit trail
    - Sets billing_status to "pending_payment" (awaiting first payment)
    - Does NOT integrate with payment providers yet (Stripe, Sinpe, etc.)
    
    For DEMO tenants, use POST /api/superadmin/condominiums/demo instead.
    """
    condo_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Initialize module config with defaults
    modules = condo_data.modules if condo_data.modules else CondominiumModules()
    
    # BILLING ENGINE: Determine seat count (prefer initial_units over legacy paid_seats)
    paid_seats = condo_data.initial_units if condo_data.initial_units else (
        condo_data.paid_seats if condo_data.paid_seats else 10
    )
    
    # BILLING ENGINE: Get effective price for this condominium
    # (Uses global pricing since condo doesn't exist yet)
    price_per_seat = await get_effective_seat_price(None)
    
    # BILLING ENGINE: Calculate invoice preview
    billing_preview = await calculate_billing_preview(
        initial_units=paid_seats,
        billing_cycle=condo_data.billing_cycle,
        condominium_id=None  # New condo, no override yet
    )
    
    # Build condominium document with enhanced billing fields
    condo_doc = {
        "id": condo_id,
        "name": condo_data.name,
        "address": condo_data.address,
        "contact_email": condo_data.contact_email,
        "contact_phone": condo_data.contact_phone,
        "billing_email": condo_data.billing_email or condo_data.contact_email,
        "max_users": paid_seats,  # Sync with paid_seats
        "current_users": 0,
        "modules": modules.model_dump(),
        "status": "active",
        "is_demo": False,
        "environment": "production",
        "is_active": True,
        # BILLING ENGINE: Enhanced billing configuration
        "billing_model": "per_seat",
        "paid_seats": paid_seats,
        "price_per_seat": price_per_seat,
        "billing_cycle": condo_data.billing_cycle,
        "billing_provider": condo_data.billing_provider,
        "billing_enabled": True,
        "billing_status": "pending_payment",  # Awaiting first payment
        "next_invoice_amount": billing_preview["effective_amount"],
        "next_billing_date": billing_preview["next_billing_date"],
        "billing_started_at": now.isoformat(),
        "yearly_discount_percent": billing_preview["yearly_discount_percent"],
        # Legacy fields (kept for backward compatibility)
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
        "price_per_user": price_per_seat,  # Legacy field
        "discount_percent": 0,
        "free_modules": [],
        "plan": "basic",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.condominiums.insert_one(condo_doc)
    
    # Create default condominium settings
    settings_doc = {
        "condominium_id": condo_id,
        "condominium_name": condo_data.name,
        **get_default_condominium_settings(),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    await db.condominium_settings.insert_one(settings_doc)
    
    # BILLING ENGINE: Log creation event
    await log_billing_engine_event(
        event_type="condominium_created",
        condominium_id=condo_id,
        data={
            "name": condo_data.name,
            "paid_seats": paid_seats,
            "price_per_seat": price_per_seat,
            "billing_cycle": condo_data.billing_cycle,
            "billing_provider": condo_data.billing_provider,
            "monthly_amount": billing_preview["monthly_amount"],
            "effective_amount": billing_preview["effective_amount"],
            "next_billing_date": billing_preview["next_billing_date"]
        },
        triggered_by=current_user["id"],
        previous_state=None,
        new_state={
            "paid_seats": paid_seats,
            "billing_status": "pending_payment",
            "billing_cycle": condo_data.billing_cycle
        }
    )
    
    # Log audit event
    await log_audit_event(
        AuditEventType.CONDO_CREATED,
        current_user["id"],
        "super_admin",
        {
            "condo_id": condo_id, 
            "name": condo_data.name, 
            "action": "created", 
            "environment": "production",
            "billing_provider": condo_data.billing_provider,
            "initial_seats": paid_seats
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return CondominiumResponse(
        id=condo_id,
        name=condo_data.name,
        address=condo_data.address,
        contact_email=condo_data.contact_email,
        contact_phone=condo_data.contact_phone,
        billing_email=condo_data.billing_email or condo_data.contact_email,
        max_users=paid_seats,
        current_users=0,
        modules=modules.model_dump(),
        is_active=True,
        created_at=condo_doc["created_at"],
        environment="production",
        is_demo=False,
        # BILLING ENGINE: Enhanced response
        billing_model="per_seat",
        paid_seats=paid_seats,
        price_per_seat=price_per_seat,
        billing_cycle=condo_data.billing_cycle,
        billing_provider=condo_data.billing_provider,
        billing_status="pending_payment",
        next_invoice_amount=billing_preview["effective_amount"],
        next_billing_date=billing_preview["next_billing_date"],
        billing_started_at=condo_doc["billing_started_at"],
        yearly_discount_percent=billing_preview["yearly_discount_percent"],
        status="active",
        plan="basic"
    )


@api_router.post("/superadmin/condominiums/demo", response_model=CondominiumResponse)
async def create_demo_condominium(
    condo_data: DemoCondominiumCreate,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    Create a new DEMO condominium (Super Admin only).
    
    DEMO tenants have:
    - Fixed seat limit of 10 users
    - NO billing (billing_enabled = false)
    - NO Stripe integration
    - Default modules enabled
    - Simplified creation process
    
    For PRODUCTION tenants with billing, use POST /api/condominiums instead.
    """
    condo_id = str(uuid.uuid4())
    
    # Initialize all modules enabled by default for demo
    modules = CondominiumModules()
    
    # DEMO configuration - fixed values
    DEMO_SEAT_LIMIT = 10
    
    condo_doc = {
        "id": condo_id,
        "name": condo_data.name,
        "address": condo_data.address,
        "contact_email": condo_data.contact_email,
        "contact_phone": condo_data.contact_phone or "",
        "max_users": DEMO_SEAT_LIMIT,
        "current_users": 0,
        "modules": modules.model_dump(),
        "status": "demo",
        "is_demo": True,
        "environment": "demo",
        "is_active": True,
        # Billing configuration (DEMO - disabled)
        "paid_seats": DEMO_SEAT_LIMIT,
        "billing_enabled": False,
        "billing_status": "demo",
        "stripe_customer_id": None,
        "price_per_user": 0,  # Free for demo
        "discount_percent": 100,  # 100% discount = free
        "free_modules": ["security", "visitors", "hr", "reservations", "school", "payments"],
        "plan": "demo",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.condominiums.insert_one(condo_doc)
    
    # Create default condominium settings
    settings_doc = {
        "condominium_id": condo_id,
        "condominium_name": condo_data.name,
        **get_default_condominium_settings(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.condominium_settings.insert_one(settings_doc)
    
    await log_audit_event(
        AuditEventType.CONDO_CREATED,
        current_user["id"],
        "super_admin",
        {"condo_id": condo_id, "name": condo_data.name, "action": "created", "environment": "demo"},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    logger.info(f"Demo condominium created: {condo_data.name} by {current_user['email']}")
    
    return CondominiumResponse(
        id=condo_id,
        name=condo_data.name,
        address=condo_data.address,
        contact_email=condo_data.contact_email,
        contact_phone=condo_data.contact_phone or "",
        max_users=DEMO_SEAT_LIMIT,
        current_users=0,
        modules=modules.model_dump(),
        is_active=True,
        created_at=condo_doc["created_at"],
        environment="demo",
        is_demo=True,
        paid_seats=DEMO_SEAT_LIMIT,
        billing_status="demo",
        status="demo",
        plan="demo"
    )


class DemoWithDataRequest(BaseModel):
    """Request model for creating a demo condominium with pre-loaded test data"""
    name: str = Field(..., min_length=2, max_length=100)
    admin_email: EmailStr
    admin_name: str = Field(default="Admin Demo")
    include_guards: bool = Field(default=True)
    include_residents: bool = Field(default=True)
    include_areas: bool = Field(default=True)


@api_router.post("/superadmin/condominiums/demo-with-data")
async def create_demo_with_test_data(
    request_data: DemoWithDataRequest,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    Create a DEMO condominium with pre-loaded test data for quick demonstrations.
    
    This endpoint creates:
    - Demo condominium (10 seats, no billing)
    - Admin user with credentials
    - Optional: 2 sample guards
    - Optional: 3 sample residents  
    - Optional: 2 reservation areas (Gym, Pool)
    
    Returns all created credentials for immediate use.
    """
    # Validate admin email not in use
    existing_user = await db.users.find_one({"email": request_data.admin_email.lower()})
    if existing_user:
        raise HTTPException(status_code=400, detail=f"El email {request_data.admin_email} ya está registrado")
    
    # Generate IDs
    condo_id = str(uuid.uuid4())
    admin_id = str(uuid.uuid4())
    
    # Generate passwords
    admin_password = generate_temporary_password(12)
    guard1_password = generate_temporary_password(10)
    guard2_password = generate_temporary_password(10)
    
    created_users = []
    created_areas = []
    
    try:
        # === STEP 1: Create Demo Condominium ===
        modules = CondominiumModules()
        condo_doc = {
            "id": condo_id,
            "name": request_data.name,
            "address": "Dirección Demo - Para pruebas",
            "contact_email": request_data.admin_email.lower(),
            "contact_phone": "",
            "max_users": 10,
            "current_users": 0,
            "modules": modules.model_dump(),
            "status": "demo",
            "is_demo": True,
            "environment": "demo",
            "is_active": True,
            "paid_seats": 10,
            "billing_enabled": False,
            "billing_status": "demo",
            "stripe_customer_id": None,
            "price_per_user": 0,
            "discount_percent": 100,
            "free_modules": ["security", "visitors", "hr", "reservations", "school", "payments"],
            "plan": "demo",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.condominiums.insert_one(condo_doc)
        
        # Create settings
        settings_doc = {
            "condominium_id": condo_id,
            "condominium_name": request_data.name,
            **get_default_condominium_settings(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.condominium_settings.insert_one(settings_doc)
        
        # === STEP 2: Create Admin User ===
        admin_doc = {
            "id": admin_id,
            "email": request_data.admin_email.lower(),
            "hashed_password": hash_password(admin_password),
            "full_name": request_data.admin_name,
            "roles": [RoleEnum.ADMINISTRADOR.value],
            "condominium_id": condo_id,
            "is_active": True,
            "status": "active",
            "is_locked": False,
            "password_reset_required": False,  # Demo doesn't require reset
            "created_by": current_user["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(admin_doc)
        created_users.append({
            "role": "Administrador",
            "email": request_data.admin_email.lower(),
            "password": admin_password,
            "name": request_data.admin_name
        })
        
        user_count = 1  # Admin
        
        # === STEP 3: Create Guards (optional) ===
        if request_data.include_guards:
            guard1_id = str(uuid.uuid4())
            guard1_email = f"guardia1.{condo_id[:8]}@demo.genturix.com"
            guard1_doc = {
                "id": guard1_id,
                "email": guard1_email,
                "hashed_password": hash_password(guard1_password),
                "full_name": "Carlos Seguridad",
                "roles": [RoleEnum.GUARDA.value],
                "condominium_id": condo_id,
                "is_active": True,
                "status": "active",
                "is_locked": False,
                "password_reset_required": False,
                "created_by": admin_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(guard1_doc)
            created_users.append({
                "role": "Guardia",
                "email": guard1_email,
                "password": guard1_password,
                "name": "Carlos Seguridad"
            })
            
            guard2_id = str(uuid.uuid4())
            guard2_email = f"guardia2.{condo_id[:8]}@demo.genturix.com"
            guard2_doc = {
                "id": guard2_id,
                "email": guard2_email,
                "hashed_password": hash_password(guard2_password),
                "full_name": "María Vigilancia",
                "roles": [RoleEnum.GUARDA.value],
                "condominium_id": condo_id,
                "is_active": True,
                "status": "active",
                "is_locked": False,
                "password_reset_required": False,
                "created_by": admin_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(guard2_doc)
            created_users.append({
                "role": "Guardia",
                "email": guard2_email,
                "password": guard2_password,
                "name": "María Vigilancia"
            })
            user_count += 2
        
        # === STEP 4: Create Residents (optional) ===
        if request_data.include_residents:
            residents_data = [
                {"name": "Roberto Pérez", "apartment": "A-101"},
                {"name": "Ana García", "apartment": "B-202"},
                {"name": "Luis Martínez", "apartment": "C-303"}
            ]
            for resident in residents_data:
                res_id = str(uuid.uuid4())
                res_password = generate_temporary_password(10)
                res_email = f"residente.{res_id[:8]}@demo.genturix.com"
                res_doc = {
                    "id": res_id,
                    "email": res_email,
                    "hashed_password": hash_password(res_password),
                    "full_name": resident["name"],
                    "roles": [RoleEnum.RESIDENTE.value],
                    "condominium_id": condo_id,
                    "apartment": resident["apartment"],
                    "is_active": True,
                    "status": "active",
                    "is_locked": False,
                    "password_reset_required": False,
                    "created_by": admin_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                await db.users.insert_one(res_doc)
                created_users.append({
                    "role": "Residente",
                    "email": res_email,
                    "password": res_password,
                    "name": resident["name"],
                    "apartment": resident["apartment"]
                })
            user_count += 3
        
        # === STEP 5: Create Reservation Areas (optional) ===
        if request_data.include_areas:
            areas_data = [
                {"name": "Gimnasio", "capacity": 15, "open_time": "06:00", "close_time": "22:00"},
                {"name": "Piscina", "capacity": 25, "open_time": "08:00", "close_time": "20:00"}
            ]
            for area in areas_data:
                area_id = str(uuid.uuid4())
                area_doc = {
                    "id": area_id,
                    "condominium_id": condo_id,
                    "name": area["name"],
                    "capacity": area["capacity"],
                    "requires_approval": False,
                    "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
                    "open_time": area["open_time"],
                    "close_time": area["close_time"],
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await db.reservation_areas.insert_one(area_doc)
                created_areas.append({
                    "id": area_id,
                    "name": area["name"],
                    "capacity": area["capacity"],
                    "schedule": f"{area['open_time']} - {area['close_time']}"
                })
        
        # Update user count
        await db.condominiums.update_one(
            {"id": condo_id},
            {"$set": {"current_users": user_count}}
        )
        
        # Audit log
        await log_audit_event(
            AuditEventType.CONDO_CREATED,
            current_user["id"],
            "super_admin",
            {
                "action": "demo_with_data_created",
                "condo_id": condo_id,
                "name": request_data.name,
                "users_created": len(created_users),
                "areas_created": len(created_areas)
            },
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "unknown")
        )
        
        logger.info(f"Demo condominium with data created: {request_data.name} by {current_user['email']} ({len(created_users)} users, {len(created_areas)} areas)")
        
        return {
            "success": True,
            "message": f"Demo '{request_data.name}' creado con datos de prueba",
            "condominium": {
                "id": condo_id,
                "name": request_data.name,
                "environment": "demo",
                "seat_limit": 10,
                "users_created": user_count
            },
            "credentials": created_users,
            "areas_created": created_areas,
            "warning": "⚠️ Guarda estas credenciales. Este es un ambiente DEMO sin emails."
        }
        
    except Exception as e:
        # Rollback on error
        logger.error(f"Demo with data creation failed, rolling back: {str(e)}")
        await db.condominiums.delete_one({"id": condo_id})
        await db.users.delete_many({"condominium_id": condo_id})
        await db.reservation_areas.delete_many({"condominium_id": condo_id})
        await db.condominium_settings.delete_one({"condominium_id": condo_id})
        raise HTTPException(status_code=500, detail=f"Error al crear demo: {str(e)}")


@api_router.get("/condominiums")
async def list_condominiums(
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """List all condominiums (Super Admin only)"""
    condos = await db.condominiums.find({}, {"_id": 0}).to_list(100)
    # Enrich with default values for fields that may not exist
    for condo in condos:
        condo.setdefault("status", "active")
        condo.setdefault("is_demo", False)
        condo.setdefault("environment", "production")  # Default to production for existing condos
        condo.setdefault("discount_percent", 0.0)
        condo.setdefault("plan", "basic")
        condo.setdefault("price_per_user", 1.0)
        # Sync environment with is_demo for backwards compatibility
        if condo.get("is_demo") and condo.get("environment") == "production":
            condo["environment"] = "demo"
        # Calculate current_users from database if not set
        if condo.get("current_users", 0) == 0:
            user_count = await db.users.count_documents({"condominium_id": condo["id"], "is_active": True})
            condo["current_users"] = user_count
    return condos

@api_router.get("/condominiums/{condo_id}", response_model=CondominiumResponse)
async def get_condominium(
    condo_id: str,
    current_user = Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPERVISOR))
):
    """Get condominium details"""
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominium not found")
    return condo

@api_router.patch("/condominiums/{condo_id}")
async def update_condominium(
    condo_id: str,
    update_data: CondominiumUpdate,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Update condominium details (Super Admin only)"""
    update_fields = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # Convert modules Pydantic model to dict if present
    if "modules" in update_fields and update_fields["modules"]:
        update_fields["modules"] = update_fields["modules"].model_dump() if hasattr(update_fields["modules"], "model_dump") else update_fields["modules"]
    
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.condominiums.update_one(
        {"id": condo_id},
        {"$set": update_fields}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Condominium not found")
    
    return {"message": "Condominium updated successfully"}

@api_router.delete("/condominiums/{condo_id}")
async def deactivate_condominium(
    condo_id: str,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Deactivate a condominium (soft delete)"""
    result = await db.condominiums.update_one(
        {"id": condo_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Condominium not found")
    
    return {"message": "Condominium deactivated"}

@api_router.get("/condominiums/{condo_id}/users")
async def get_condominium_users(
    condo_id: str,
    current_user = Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPERVISOR))
):
    """Get all users belonging to a condominium"""
    users = await db.users.find(
        {"condominium_id": condo_id},
        {"_id": 0, "hashed_password": 0}
    ).to_list(500)
    return users

@api_router.get("/condominiums/{condo_id}/billing")
async def get_condominium_billing(
    condo_id: str,
    current_user = Depends(require_role(RoleEnum.ADMINISTRADOR))
):
    """Get billing information for a condominium"""
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominium not found")
    
    # Calculate monthly cost
    user_count = await db.users.count_documents({"condominium_id": condo_id, "is_active": True})
    price_per_user = condo.get("price_per_user", 1.0)
    monthly_cost = user_count * price_per_user
    
    return {
        "condominium_id": condo_id,
        "condominium_name": condo.get("name"),
        "active_users": user_count,
        "price_per_user": price_per_user,
        "monthly_cost_usd": monthly_cost,
        "billing_cycle": "monthly",
        "currency": "USD"
    }

@api_router.patch("/condominiums/{condo_id}/modules/{module_name}")
async def update_module_config(
    condo_id: str,
    module_name: str,
    enabled: bool,
    settings: Optional[Dict[str, Any]] = None,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Enable/disable a module for a condominium"""
    valid_modules = ["security", "hr", "school", "payments", "audit", "reservations", "access_control", "messaging", "visits", "cctv"]
    
    if module_name not in valid_modules:
        logger.error(f"[module-toggle] Invalid module '{module_name}' requested. Valid: {valid_modules}")
        raise HTTPException(status_code=400, detail=f"Invalid module. Valid modules: {', '.join(valid_modules)}")
    
    # Verify condominium exists first
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "id": 1, "name": 1, "modules": 1})
    if not condo:
        logger.error(f"[module-toggle] Condominium {condo_id} not found")
        raise HTTPException(status_code=404, detail="Condominium not found")
    
    # Check current module structure - it might be a boolean or an object
    current_modules = condo.get("modules", {})
    current_value = current_modules.get(module_name)
    
    # If module is stored as a boolean (legacy format), convert to object format
    if isinstance(current_value, bool) or current_value is None:
        # Use $set with the full module object structure
        update_data = {
            f"modules.{module_name}": {"enabled": enabled},
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    else:
        # Module is already an object, just update the enabled field
        update_data = {
            f"modules.{module_name}.enabled": enabled,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    
    if settings:
        update_data[f"modules.{module_name}.settings"] = settings
    
    logger.info(f"[module-toggle] Updating module '{module_name}' to enabled={enabled} for condo '{condo.get('name')}' ({condo_id})")
    logger.info(f"[module-toggle] Current module value: {current_value} (type: {type(current_value).__name__})")
    logger.info(f"[module-toggle] Update data: {update_data}")
    
    result = await db.condominiums.update_one(
        {"id": condo_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0 and result.matched_count == 0:
        logger.error(f"[module-toggle] No document matched for condo_id={condo_id}")
        raise HTTPException(status_code=404, detail="Condominium not found")
    
    logger.info(f"[module-toggle] SUCCESS: Module '{module_name}' {'enabled' if enabled else 'disabled'} for condo {condo_id}. Modified: {result.modified_count}")
    return {"message": f"Module '{module_name}' {'enabled' if enabled else 'disabled'} successfully", "module": module_name, "enabled": enabled}

# ==================== SUPER ADMIN ENDPOINTS ====================

@api_router.get("/super-admin/stats")
async def get_platform_stats(
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Get global platform statistics"""
    total_condos = await db.condominiums.count_documents({})
    active_condos = await db.condominiums.count_documents({"is_active": True})
    demo_condos = await db.condominiums.count_documents({"is_demo": True})
    total_users = await db.users.count_documents({})
    active_users = await db.users.count_documents({"is_active": True})
    total_alerts = await db.panic_events.count_documents({})
    active_alerts = await db.panic_events.count_documents({"status": "active"})
    
    # Calculate MRR (Monthly Recurring Revenue)
    condos = await db.condominiums.find({"is_active": True}, {"_id": 0}).to_list(1000)
    mrr = 0.0
    for condo in condos:
        user_count = await db.users.count_documents({"condominium_id": condo.get("id"), "is_active": True})
        price = condo.get("price_per_user", 1.0)
        discount = condo.get("discount_percent", 0)
        mrr += user_count * price * (1 - discount / 100)
    
    return {
        "condominiums": {
            "total": total_condos,
            "active": active_condos,
            "demo": demo_condos,
            "suspended": total_condos - active_condos
        },
        "users": {
            "total": total_users,
            "active": active_users
        },
        "alerts": {
            "total": total_alerts,
            "active": active_alerts
        },
        "revenue": {
            "mrr_usd": round(mrr, 2),
            "price_per_user": 1.0
        }
    }

@api_router.get("/super-admin/users")
async def get_all_users_global(
    condo_id: Optional[str] = None,
    role: Optional[str] = None,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Get all users across all condominiums with filters"""
    query = {}
    if condo_id:
        query["condominium_id"] = condo_id
    if role:
        query["roles"] = role
    
    users = await db.users.find(query, {"_id": 0, "hashed_password": 0}).to_list(1000)
    
    # Enrich with condominium name
    for user in users:
        if user.get("condominium_id"):
            condo = await db.condominiums.find_one({"id": user["condominium_id"]}, {"name": 1})
            user["condominium_name"] = condo.get("name") if condo else "Unknown"
    
    return users

@api_router.put("/super-admin/users/{user_id}/lock")
async def lock_user(
    user_id: str,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Lock a user account (security)"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_active": False, "locked_by": current_user["id"], "locked_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    await log_audit_event(
        AuditEventType.USER_LOCKED,
        current_user["id"],
        "super_admin",
        {"user_id": user_id, "email": user.get("email"), "action": "locked"},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "User locked successfully"}

@api_router.put("/super-admin/users/{user_id}/unlock")
async def unlock_user(
    user_id: str,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Unlock a user account"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_active": True, "locked_by": None, "locked_at": None}}
    )
    
    await log_audit_event(
        AuditEventType.USER_UNLOCKED,
        current_user["id"],
        "super_admin",
        {"user_id": user_id, "email": user.get("email"), "action": "unlocked"},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "User unlocked successfully"}

@api_router.post("/super-admin/condominiums/{condo_id}/make-demo")
async def make_demo_condominium(
    condo_id: str,
    max_users: int = 10,
    request: Request = None,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Convert a condominium to demo/sandbox mode"""
    result = await db.condominiums.update_one(
        {"id": condo_id},
        {"$set": {
            "is_demo": True,
            "status": "demo",
            "max_users": max_users,
            "price_per_user": 0,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Condominium not found")
    
    return {"message": "Condominium converted to demo mode"}

@api_router.post("/super-admin/condominiums/{condo_id}/reset-demo")
async def reset_demo_data(
    condo_id: str,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Reset demo data for a sandbox condominium"""
    condo = await db.condominiums.find_one({"id": condo_id})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominium not found")
    
    if not condo.get("is_demo"):
        raise HTTPException(status_code=400, detail="Only demo condominiums can be reset")
    
    # Delete associated data
    await db.panic_events.delete_many({"condominium_id": condo_id})
    await db.visitors.delete_many({"condominium_id": condo_id})
    await db.access_logs.delete_many({"condominium_id": condo_id})
    
    await log_audit_event(
        AuditEventType.DEMO_RESET,
        current_user["id"],
        "super_admin",
        {"condo_id": condo_id, "name": condo.get("name"), "action": "demo_reset"},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "Demo data reset successfully"}

@api_router.patch("/super-admin/condominiums/{condo_id}/pricing")
async def update_condo_pricing(
    condo_id: str,
    discount_percent: Optional[int] = None,
    free_modules: Optional[List[str]] = None,
    plan: Optional[str] = None,
    seat_price_override: Optional[float] = None,
    request: Request = None,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """
    Update pricing/plan for a condominium.
    
    PHASE 3: seat_price_override
    - Set to a value > 0 to override global price for this condo
    - Set to 0 or omit to use global default price
    """
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if discount_percent is not None:
        update_data["discount_percent"] = max(0, min(100, discount_percent))
    if free_modules is not None:
        update_data["free_modules"] = free_modules
    if plan is not None:
        update_data["plan"] = plan
    
    # PHASE 3: Handle seat price override
    if seat_price_override is not None:
        if seat_price_override <= 0:
            # Remove override (use global default)
            update_data["seat_price_override"] = None
        else:
            update_data["seat_price_override"] = round(seat_price_override, 2)
    
    result = await db.condominiums.update_one({"id": condo_id}, {"$set": update_data})
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Condominium not found")
    
    if request:
        await log_audit_event(
            AuditEventType.PRICING_OVERRIDE_UPDATED if seat_price_override is not None else AuditEventType.PLAN_UPDATED,
            current_user["id"],
            "super_admin",
            {"condo_id": condo_id, "changes": update_data},
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "unknown")
        )
    
    return {"message": "Pricing updated successfully"}

# ==================== GLOBAL PRICING ENDPOINTS ====================

class GlobalPricingUpdate(BaseModel):
    default_seat_price: float = Field(..., gt=0, description="Default price per seat (must be > 0)")
    currency: str = Field(default="USD", description="Currency code")

@api_router.get("/super-admin/pricing/global")
async def get_global_pricing_config(
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    Get global pricing configuration.
    Only SuperAdmin can view global pricing.
    """
    config = await db.system_config.find_one({"id": "global_pricing"}, {"_id": 0})
    
    if not config:
        # Initialize if missing
        await ensure_global_pricing_config()
        config = await db.system_config.find_one({"id": "global_pricing"}, {"_id": 0})
    
    return {
        "default_seat_price": config.get("default_seat_price", FALLBACK_PRICE_PER_SEAT),
        "currency": config.get("currency", DEFAULT_CURRENCY),
        "updated_at": config.get("updated_at")
    }

@api_router.put("/super-admin/pricing/global")
async def update_global_pricing(
    pricing: GlobalPricingUpdate,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    PHASE 3: Update global pricing configuration.
    Only SuperAdmin can update global pricing.
    
    This affects ALL condominiums that don't have a seat_price_override.
    """
    # Validate price
    if pricing.default_seat_price <= 0:
        raise HTTPException(status_code=400, detail="Price must be greater than 0")
    
    # Validate currency
    if pricing.currency.upper() not in ["USD", "EUR", "MXN"]:
        raise HTTPException(status_code=400, detail="Currency must be USD, EUR, or MXN")
    
    update_data = {
        "default_seat_price": round(pricing.default_seat_price, 2),
        "currency": pricing.currency.upper(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Upsert global pricing config
    await db.system_config.update_one(
        {"id": "global_pricing"},
        {"$set": update_data, "$setOnInsert": {"id": "global_pricing", "created_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    
    # Log audit event
    await log_audit_event(
        AuditEventType.PRICING_GLOBAL_UPDATED,
        current_user["id"],
        "system_config",
        {"old_price": "see_previous_logs", "new_price": update_data["default_seat_price"], "currency": update_data["currency"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    logger.info(f"[PRICING] Global pricing updated: ${update_data['default_seat_price']} {update_data['currency']} by {current_user['email']}")
    
    return {
        "message": "Global pricing updated successfully",
        "default_seat_price": update_data["default_seat_price"],
        "currency": update_data["currency"]
    }

@api_router.get("/super-admin/pricing/condominiums")
async def get_all_condominiums_pricing(
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    PHASE 5: Get pricing info for all condominiums.
    Shows effective price and whether each condo uses override or global.
    """
    global_config = await get_global_pricing()
    
    condos = await db.condominiums.find(
        {},
        {"_id": 0, "id": 1, "name": 1, "seat_price_override": 1, "seat_limit": 1}
    ).to_list(None)
    
    result = []
    for condo in condos:
        override = condo.get("seat_price_override")
        uses_override = override is not None and override > 0
        effective_price = override if uses_override else global_config["default_seat_price"]
        
        result.append({
            "id": condo["id"],
            "name": condo.get("name", "Unknown"),
            "effective_price": effective_price,
            "uses_override": uses_override,
            "override_price": override if uses_override else None,
            "global_price": global_config["default_seat_price"],
            "seat_limit": condo.get("seat_limit", 0),
            "currency": global_config["currency"]
        })
    
    return {
        "global_pricing": global_config,
        "condominiums": result,
        "total": len(result)
    }

@api_router.patch("/super-admin/condominiums/{condo_id}/status")
async def update_condo_status(
    condo_id: str,
    status: str,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Update condominium status (active/demo/suspended)"""
    valid_statuses = ["active", "demo", "suspended"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {', '.join(valid_statuses)}")
    
    result = await db.condominiums.update_one(
        {"id": condo_id},
        {"$set": {
            "status": status,
            "is_active": status != "suspended",
            "is_demo": status == "demo",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Condominium not found")
    
    await log_audit_event(
        AuditEventType.CONDO_UPDATED,
        current_user["id"],
        "super_admin",
        {"condo_id": condo_id, "new_status": status},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": f"Status updated to {status}"}

@api_router.get("/super-admin/audit")
async def get_super_admin_audit(
    module: Optional[str] = "super_admin",
    limit: int = 100,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Get audit logs for super admin actions"""
    query = {}
    if module:
        query["module"] = module
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return logs


@api_router.get("/super-admin/audit/global")
async def get_global_audit_logs(
    limit: int = 500,
    module: Optional[str] = None,
    event_type: Optional[str] = None,
    condominium_id: Optional[str] = None,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    Global System Audit - SuperAdmin Only.
    
    Returns logs from ALL condominiums with full details.
    
    Fields returned:
    - timestamp
    - user_id
    - user_email (fetched from users collection)
    - condominium_id
    - condominium_name (fetched from condominiums collection)
    - action (event_type)
    - module
    - details
    
    Sorted by newest first.
    """
    query = {}
    
    if module:
        query["module"] = module
    if event_type:
        query["event_type"] = event_type
    if condominium_id:
        query["condominium_id"] = condominium_id
    
    # Fetch logs
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    
    # Enrich with user emails and condominium names
    user_ids = list(set([log.get("user_id") for log in logs if log.get("user_id")]))
    condo_ids = list(set([log.get("condominium_id") for log in logs if log.get("condominium_id")]))
    
    # Fetch users and condominiums for enrichment
    users = {}
    if user_ids:
        user_docs = await db.users.find(
            {"id": {"$in": user_ids}}, 
            {"_id": 0, "id": 1, "email": 1}
        ).to_list(len(user_ids))
        users = {u["id"]: u.get("email", "N/A") for u in user_docs}
    
    condos = {}
    if condo_ids:
        condo_docs = await db.condominiums.find(
            {"id": {"$in": condo_ids}}, 
            {"_id": 0, "id": 1, "name": 1}
        ).to_list(len(condo_ids))
        condos = {c["id"]: c.get("name", "N/A") for c in condo_docs}
    
    # Enrich logs
    enriched_logs = []
    for log in logs:
        enriched_log = {
            "timestamp": log.get("timestamp"),
            "user_id": log.get("user_id"),
            "user_email": users.get(log.get("user_id"), "N/A"),
            "condominium_id": log.get("condominium_id"),
            "condominium_name": condos.get(log.get("condominium_id"), "Sistema"),
            "action": log.get("event_type"),
            "module": log.get("module"),
            "endpoint": log.get("endpoint"),
            "status": log.get("status", "success"),
            "details": log.get("details", {})
        }
        enriched_logs.append(enriched_log)
    
    return {
        "logs": enriched_logs,
        "total": len(enriched_logs),
        "scope": "global"
    }


@api_router.delete("/super-admin/condominiums/{condo_id}")
async def permanently_delete_condominium(
    condo_id: str,
    delete_request: CondominiumDeleteRequest,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    PERMANENTLY DELETE a condominium and ALL related data.
    
    This is an IRREVERSIBLE action. Requires Super Admin role and password verification.
    
    Deletes:
    - Condominium record
    - All users belonging to the condominium
    - All panic events
    - All guard history
    - All HR data (guards, employees, shifts, absences)
    - All visitors
    - All audit logs linked to the condominium
    """
    # Step 1: Verify Super Admin password
    user = await db.users.find_one({"id": current_user["id"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(delete_request.password, user["hashed_password"]):
        raise HTTPException(status_code=403, detail="Contraseña incorrecta")
    
    # Step 2: Verify condominium exists
    condo = await db.condominiums.find_one({"id": condo_id})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    condo_name = condo.get("name", "Unknown")
    
    # Step 3: Cascade delete all related data
    deletion_stats = {
        "condominium": condo_name,
        "users_deleted": 0,
        "panic_events_deleted": 0,
        "guard_history_deleted": 0,
        "guards_deleted": 0,
        "employees_deleted": 0,
        "shifts_deleted": 0,
        "absences_deleted": 0,
        "visitors_deleted": 0,
        "audit_logs_deleted": 0,
        "candidates_deleted": 0
    }
    
    # Delete users
    users_result = await db.users.delete_many({"condominium_id": condo_id})
    deletion_stats["users_deleted"] = users_result.deleted_count
    
    # Delete panic events
    panic_result = await db.panic_events.delete_many({"condominium_id": condo_id})
    deletion_stats["panic_events_deleted"] = panic_result.deleted_count
    
    # Delete guard history
    history_result = await db.guard_history.delete_many({"condominium_id": condo_id})
    deletion_stats["guard_history_deleted"] = history_result.deleted_count
    
    # Delete guards
    guards_result = await db.guards.delete_many({"condominium_id": condo_id})
    deletion_stats["guards_deleted"] = guards_result.deleted_count
    
    # Delete employees
    employees_result = await db.employees.delete_many({"condominium_id": condo_id})
    deletion_stats["employees_deleted"] = employees_result.deleted_count
    
    # Delete shifts
    shifts_result = await db.shifts.delete_many({"condominium_id": condo_id})
    deletion_stats["shifts_deleted"] = shifts_result.deleted_count
    
    # Delete absences
    absences_result = await db.absences.delete_many({"condominium_id": condo_id})
    deletion_stats["absences_deleted"] = absences_result.deleted_count
    
    # Delete visitors
    visitors_result = await db.visitors.delete_many({"condominium_id": condo_id})
    deletion_stats["visitors_deleted"] = visitors_result.deleted_count
    
    # Delete candidates (HR recruitment)
    candidates_result = await db.candidates.delete_many({"condominium_id": condo_id})
    deletion_stats["candidates_deleted"] = candidates_result.deleted_count
    
    # Delete audit logs linked to condo users (we keep the final deletion log)
    audit_result = await db.audit_logs.delete_many({
        "$or": [
            {"details.condominium_id": condo_id},
            {"details.condo_id": condo_id}
        ]
    })
    deletion_stats["audit_logs_deleted"] = audit_result.deleted_count
    
    # Step 4: Delete the condominium itself
    await db.condominiums.delete_one({"id": condo_id})
    
    # Step 5: Log the deletion (this log persists for Super Admin audit trail)
    await log_audit_event(
        AuditEventType.CONDOMINIUM_DELETED,
        current_user["id"],
        "super_admin",
        {
            "action": "CONDOMINIUM_DELETED",
            "condo_id": condo_id,
            "condo_name": condo_name,
            "deletion_stats": deletion_stats,
            "performed_by_email": current_user.get("email"),
            "irreversible": True
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "message": f"Condominio '{condo_name}' eliminado permanentemente",
        "deletion_stats": deletion_stats
    }


# ==================== FIX EXISTING USERS WITHOUT CONDOMINIUM ====================

@api_router.post("/admin/fix-orphan-users")
async def fix_orphan_users(
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Fix users without condominium_id by assigning them to a demo condominium"""
    # Find or create demo condominium
    demo_condo = await db.condominiums.find_one({"name": "Residencial Las Palmas"})
    if not demo_condo:
        demo_condo_id = str(uuid.uuid4())
        demo_condo = {
            "id": demo_condo_id,
            "name": "Residencial Las Palmas",
            "address": "Av. Principal #123",
            "status": "demo",
            "is_active": True,
            "max_users": 50,
            "modules": {"security": True, "visitors": True, "school": True},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.condominiums.insert_one(demo_condo)
        
        # Create default settings for demo condo
        existing_settings = await db.condominium_settings.find_one({"condominium_id": demo_condo["id"]})
        if not existing_settings:
            settings_doc = {
                "condominium_id": demo_condo["id"],
                "condominium_name": demo_condo["name"],
                **get_default_condominium_settings(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            await db.condominium_settings.insert_one(settings_doc)
    
    demo_condo_id = demo_condo["id"]
    
    # Find all users without condominium_id (except SuperAdmin)
    orphan_query = {
        "$and": [
            {"$or": [{"condominium_id": None}, {"condominium_id": {"$exists": False}}]},
            {"roles": {"$nin": ["SuperAdmin"]}}
        ]
    }
    
    result = await db.users.update_many(
        orphan_query,
        {"$set": {"condominium_id": demo_condo_id}}
    )
    
    # Also fix guards without condominium_id
    guard_result = await db.guards.update_many(
        {"$or": [{"condominium_id": None}, {"condominium_id": {"$exists": False}}]},
        {"$set": {"condominium_id": demo_condo_id}}
    )
    
    await log_audit_event(
        AuditEventType.USER_UPDATED,
        current_user["id"],
        "admin",
        {
            "action": "fix_orphan_users",
            "users_fixed": result.modified_count,
            "guards_fixed": guard_result.modified_count,
            "assigned_condo": demo_condo_id
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "message": f"Fixed {result.modified_count} users and {guard_result.modified_count} guards",
        "users_fixed": result.modified_count,
        "guards_fixed": guard_result.modified_count,
        "assigned_condominium_id": demo_condo_id
    }

# ==================== SUPER ADMIN: CONDOMINIUM ADMIN CREATION ====================

class CreateCondoAdminRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    phone: Optional[str] = None

@api_router.post("/super-admin/condominiums/{condo_id}/admin")
async def create_condominium_admin(
    condo_id: str,
    admin_data: CreateCondoAdminRequest,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """Super Admin creates a Condominium Administrator for a specific condominium"""
    # Verify condominium exists
    condo = await db.condominiums.find_one({"id": condo_id})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    # Check email not in use
    existing = await db.users.find_one({"email": admin_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # Force role to Administrador
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": admin_data.email,
        "hashed_password": hash_password(admin_data.password),
        "full_name": admin_data.full_name,
        "roles": [RoleEnum.ADMINISTRADOR.value],
        "condominium_id": condo_id,  # Associate with the condominium
        "phone": admin_data.phone,
        "is_active": True,
        "is_locked": False,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    # Update condominium to reference this admin
    await db.condominiums.update_one(
        {"id": condo_id},
        {"$set": {"admin_id": user_id, "admin_email": admin_data.email}}
    )
    
    await log_audit_event(
        AuditEventType.USER_CREATED,
        current_user["id"],
        "super_admin",
        {
            "action": "create_condo_admin",
            "user_id": user_id,
            "email": admin_data.email,
            "condominium_id": condo_id,
            "condominium_name": condo["name"]
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "message": f"Administrador {admin_data.full_name} creado para {condo['name']}",
        "user_id": user_id,
        "condominium_id": condo_id,
        "credentials": {
            "email": admin_data.email,
            "password": "********"
        }
    }

# ==================== ONBOARDING WIZARD ====================
class OnboardingCondominiumInfo(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    address: str = Field(..., min_length=5, max_length=200)
    country: str = Field(default="Mexico")
    timezone: str = Field(default="America/Mexico_City")

# BILLING ENGINE: Billing configuration for onboarding
class OnboardingBillingInfo(BaseModel):
    initial_units: int = Field(..., ge=1, le=10000, description="Number of billable seats")
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|yearly)$")
    billing_provider: str = Field(default="sinpe", pattern="^(stripe|sinpe|ticopay|manual)$")
    billing_email: Optional[EmailStr] = None  # If different from admin email
    seat_price_override: Optional[float] = Field(default=None, gt=0, le=1000, description="Custom price per seat")
    yearly_discount_percent: Optional[float] = Field(default=None, ge=0, le=50, description="Custom yearly discount 0-50%")

class OnboardingAdminInfo(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr

class OnboardingModules(BaseModel):
    security: bool = True  # Always true, cannot be disabled
    hr: bool = False
    reservations: bool = False
    school: bool = False
    payments: bool = False
    cctv: bool = False  # Coming soon

class OnboardingArea(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    capacity: int = Field(..., ge=1, le=1000)
    requires_approval: bool = False
    available_days: List[str] = Field(default=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
    open_time: str = Field(default="08:00")
    close_time: str = Field(default="22:00")

class OnboardingWizardRequest(BaseModel):
    condominium: OnboardingCondominiumInfo
    admin: OnboardingAdminInfo
    modules: OnboardingModules
    areas: List[OnboardingArea] = []
    # BILLING ENGINE: Required billing configuration
    billing: OnboardingBillingInfo

@api_router.post("/super-admin/onboarding/create-condominium")
async def onboarding_create_condominium(
    wizard_data: OnboardingWizardRequest,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    Atomically create a new condominium with admin, modules, and areas.
    This is the main endpoint for the onboarding wizard.
    Returns admin credentials ONCE - they are not stored or retrievable later.
    """
    logger.info(f"Onboarding started by {current_user['email']} for: {wizard_data.condominium.name}")
    
    # CRITICAL: Normalize admin email to lowercase
    normalized_admin_email = wizard_data.admin.email.lower().strip()
    
    # Validate email is not in use
    existing_user = await db.users.find_one({"email": normalized_admin_email})
    if existing_user:
        logger.warning(f"Onboarding failed: email {normalized_admin_email} already registered")
        raise HTTPException(
            status_code=400, 
            detail=f"El email del administrador '{normalized_admin_email}' ya está registrado en el sistema"
        )
    
    # Validate condominium name is not in use
    existing_condo = await db.condominiums.find_one({"name": wizard_data.condominium.name})
    if existing_condo:
        logger.warning(f"Onboarding failed: condominium name '{wizard_data.condominium.name}' already exists")
        raise HTTPException(
            status_code=400, 
            detail=f"Ya existe un condominio con el nombre '{wizard_data.condominium.name}'"
        )
    
    # Validate timezone (basic check - must start with valid region)
    valid_tz_prefixes = ['America/', 'Europe/', 'Asia/', 'Africa/', 'Pacific/', 'UTC']
    if not any(wizard_data.condominium.timezone.startswith(prefix) for prefix in valid_tz_prefixes):
        logger.warning(f"Onboarding failed: invalid timezone '{wizard_data.condominium.timezone}'")
        raise HTTPException(
            status_code=400,
            detail=f"Zona horaria inválida: '{wizard_data.condominium.timezone}'. Use un formato válido como 'America/Costa_Rica'"
        )
    
    # Generate IDs
    condo_id = str(uuid.uuid4())
    admin_user_id = str(uuid.uuid4())
    
    # Generate secure temporary password for admin
    admin_password = generate_temporary_password(12)
    
    # Prepare module config - ensure security is always enabled
    modules_config = {
        "security": True,  # Always true
        "visitors": True,  # Always included with security
        "hr": wizard_data.modules.hr,
        "reservations": wizard_data.modules.reservations,
        "school": wizard_data.modules.school,
        "payments": wizard_data.modules.payments,
        "cctv": False  # Coming soon - always false for now
    }
    
    try:
        # === STEP 1: Create Condominium ===
        condo_doc = {
            "id": condo_id,
            "name": wizard_data.condominium.name,
            "address": wizard_data.condominium.address,
            "country": wizard_data.condominium.country,
            "timezone": wizard_data.condominium.timezone,
            "contact_email": normalized_admin_email,
            "billing_email": wizard_data.billing.billing_email or normalized_admin_email,
            "modules": modules_config,
            "status": "active",
            "is_demo": False,
            "environment": "production",
            "is_active": True,
            # BILLING ENGINE: Core billing fields
            "billing_model": "per_seat",
            "paid_seats": wizard_data.billing.initial_units,
            "max_users": wizard_data.billing.initial_units,  # Sync with paid_seats
            "current_users": 1,  # Admin user
            "price_per_seat": await get_effective_seat_price(None),
            "seat_price_override": wizard_data.billing.seat_price_override,  # Custom price (optional)
            "billing_cycle": wizard_data.billing.billing_cycle,
            "billing_provider": wizard_data.billing.billing_provider,
            "billing_enabled": True,
            "billing_status": "pending_payment",
            "next_invoice_amount": 0,  # Will be calculated below
            "next_billing_date": None,  # Will be set after first payment
            "billing_started_at": datetime.now(timezone.utc).isoformat(),
            "yearly_discount_percent": wizard_data.billing.yearly_discount_percent if wizard_data.billing.yearly_discount_percent is not None else YEARLY_DISCOUNT_PERCENT,
            # Legacy fields for backward compatibility
            "price_per_user": 1.0,
            "discount_percent": 0,
            "free_modules": [],
            "plan": "basic",
            "admin_id": admin_user_id,
            "admin_email": normalized_admin_email,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "onboarding_completed": True,
            "onboarding_completed_by": current_user["id"],
            "onboarding_completed_at": datetime.now(timezone.utc).isoformat()
        }
        
        # BILLING ENGINE: Calculate invoice amount (using overrides if provided)
        billing_preview = await calculate_billing_preview(
            initial_units=wizard_data.billing.initial_units,
            billing_cycle=wizard_data.billing.billing_cycle,
            condominium_id=None,
            seat_price_override=wizard_data.billing.seat_price_override,
            yearly_discount_override=wizard_data.billing.yearly_discount_percent
        )
        condo_doc["next_invoice_amount"] = billing_preview["effective_amount"]
        condo_doc["price_per_seat"] = billing_preview["price_per_seat"]
        
        await db.condominiums.insert_one(condo_doc)
        
        # BILLING ENGINE: Log creation event
        await log_billing_engine_event(
            event_type="condominium_created",
            condominium_id=condo_id,
            data={
                "name": wizard_data.condominium.name,
                "paid_seats": wizard_data.billing.initial_units,
                "price_per_seat": billing_preview["price_per_seat"],
                "seat_price_override": wizard_data.billing.seat_price_override,
                "yearly_discount_percent": billing_preview["yearly_discount_percent"],
                "billing_cycle": wizard_data.billing.billing_cycle,
                "billing_provider": wizard_data.billing.billing_provider,
                "monthly_amount": billing_preview["monthly_amount"],
                "effective_amount": billing_preview["effective_amount"],
                "source": "onboarding_wizard"
            },
            triggered_by=current_user["id"],
            previous_state=None,
            new_state={
                "paid_seats": wizard_data.billing.initial_units,
                "billing_status": "pending_payment",
                "billing_cycle": wizard_data.billing.billing_cycle,
                "seat_price_override": wizard_data.billing.seat_price_override,
                "yearly_discount_percent": billing_preview["yearly_discount_percent"]
            }
        )
        
        # Create default condominium settings
        settings_doc = {
            "condominium_id": condo_id,
            "condominium_name": wizard_data.condominium.name,
            **get_default_condominium_settings(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.condominium_settings.insert_one(settings_doc)
        
        # === STEP 2: Create Admin User ===
        admin_doc = {
            "id": admin_user_id,
            "email": normalized_admin_email,  # Use normalized email
            "hashed_password": hash_password(admin_password),
            "full_name": wizard_data.admin.full_name,
            "roles": [RoleEnum.ADMINISTRADOR.value],
            "condominium_id": condo_id,
            "is_active": True,
            "is_locked": False,
            "password_reset_required": not DEV_MODE,  # Skip password reset in DEV_MODE
            "created_by": current_user["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.users.insert_one(admin_doc)
        
        # === STEP 3: Create Areas (if reservations enabled and areas provided) ===
        created_areas = []
        if wizard_data.modules.reservations and wizard_data.areas:
            for area in wizard_data.areas:
                area_id = str(uuid.uuid4())
                area_doc = {
                    "id": area_id,
                    "condominium_id": condo_id,
                    "name": area.name,
                    "capacity": area.capacity,
                    "requires_approval": area.requires_approval,
                    "available_days": area.available_days,
                    "open_time": area.open_time,
                    "close_time": area.close_time,
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await db.reservation_areas.insert_one(area_doc)
                created_areas.append({"id": area_id, "name": area.name})
        
        # === STEP 4: Log Audit Event ===
        await log_audit_event(
            AuditEventType.CONDO_CREATED,
            current_user["id"],
            "super_admin",
            {
                "action": "onboarding_completed",
                "condominium_id": condo_id,
                "condominium_name": wizard_data.condominium.name,
                "admin_user_id": admin_user_id,
                "admin_email": wizard_data.admin.email,
                "modules_enabled": [k for k, v in modules_config.items() if v],
                "areas_created": len(created_areas)
            },
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "unknown")
        )
        
        # === STEP 5: Send Welcome Email to Admin (fail-safe) ===
        try:
            print(f"[EMAIL TRIGGER] create_condominium → sending welcome email to {normalized_admin_email}")
            login_url = f"{FRONTEND_URL}/login" if FRONTEND_URL else "https://genturix.com/login"
            welcome_html = get_condominium_welcome_email_html(
                admin_name=wizard_data.admin.full_name,
                condominium_name=wizard_data.condominium.name,
                email=normalized_admin_email,
                password=admin_password,
                login_url=login_url
            )
            email_result = await send_email(
                to=normalized_admin_email,
                subject=f"¡Bienvenido a GENTURIX! - {wizard_data.condominium.name}",
                html=welcome_html
            )
            print(f"[EMAIL RESULT] create_condominium → {email_result}")
        except Exception as email_error:
            print(f"[EMAIL ERROR] create_condominium → {email_error}")
            logger.warning(f"[EMAIL] Failed to send welcome email to {normalized_admin_email}: {email_error}")
            # Continue - don't break API flow
        
        logger.info(f"Onboarding completed: {wizard_data.condominium.name} by {current_user['email']}")
        
        return {
            "success": True,
            "message": f"Condominio '{wizard_data.condominium.name}' creado exitosamente",
            "condominium": {
                "id": condo_id,
                "name": wizard_data.condominium.name,
                "address": wizard_data.condominium.address,
                "timezone": wizard_data.condominium.timezone
            },
            "admin_credentials": {
                "email": wizard_data.admin.email,
                "password": admin_password,  # SHOWN ONCE - NOT STORED
                "show_password": True,  # Always show for wizard (one-time display)
                "warning": "Guarda estas credenciales ahora. No se mostrarán de nuevo." if not DEV_MODE else "Modo desarrollo: La contraseña no requiere cambio obligatorio."
            },
            "modules_enabled": [k for k, v in modules_config.items() if v],
            "areas_created": created_areas,
            "dev_mode": DEV_MODE
        }
        
    except Exception as e:
        # === ROLLBACK on any error ===
        logger.error(f"Onboarding failed, rolling back: {str(e)}")
        
        # Delete any created documents
        await db.condominiums.delete_one({"id": condo_id})
        await db.users.delete_one({"id": admin_user_id})
        await db.reservation_areas.delete_many({"condominium_id": condo_id})
        
        raise HTTPException(
            status_code=500,
            detail=f"Error durante el onboarding. Todos los cambios han sido revertidos. Error: {str(e)}"
        )


# Validation endpoints for onboarding
class OnboardingValidation(BaseModel):
    field: str  # "email" or "name"
    value: str

@api_router.post("/super-admin/onboarding/validate")
async def validate_onboarding_field(
    data: OnboardingValidation,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """Validate a single field before submitting the entire wizard"""
    if data.field == "email":
        # CRITICAL: Normalize email for validation
        normalized_email = data.value.lower().strip()
        existing = await db.users.find_one({"email": normalized_email})
        if existing:
            return {
                "valid": False,
                "field": "email",
                "message": f"El email '{normalized_email}' ya está registrado en el sistema"
            }
        return {"valid": True, "field": "email", "message": "Email disponible"}
    
    elif data.field == "name":
        existing = await db.condominiums.find_one({"name": data.value})
        if existing:
            return {
                "valid": False,
                "field": "name",
                "message": f"Ya existe un condominio con el nombre '{data.value}'"
            }
        return {"valid": True, "field": "name", "message": "Nombre disponible"}
    
    return {"valid": True, "message": "Campo válido"}


@api_router.get("/super-admin/onboarding/timezones")
async def get_available_timezones(current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))):
    """Get list of available timezones for onboarding"""
    return {
        "timezones": [
            # Centroamérica
            {"value": "America/Costa_Rica", "label": "Costa Rica (San José)", "offset": "UTC-6"},
            {"value": "America/Guatemala", "label": "Guatemala", "offset": "UTC-6"},
            {"value": "America/Tegucigalpa", "label": "Honduras (Tegucigalpa)", "offset": "UTC-6"},
            {"value": "America/El_Salvador", "label": "El Salvador", "offset": "UTC-6"},
            {"value": "America/Managua", "label": "Nicaragua (Managua)", "offset": "UTC-6"},
            {"value": "America/Panama", "label": "Panamá", "offset": "UTC-5"},
            # Norteamérica
            {"value": "America/Mexico_City", "label": "México (Ciudad de México)", "offset": "UTC-6"},
            {"value": "America/Tijuana", "label": "México (Tijuana)", "offset": "UTC-8"},
            {"value": "America/Cancun", "label": "México (Cancún)", "offset": "UTC-5"},
            {"value": "America/New_York", "label": "Estados Unidos (Este)", "offset": "UTC-5"},
            {"value": "America/Los_Angeles", "label": "Estados Unidos (Pacífico)", "offset": "UTC-8"},
            # Sudamérica
            {"value": "America/Argentina/Buenos_Aires", "label": "Argentina (Buenos Aires)", "offset": "UTC-3"},
            {"value": "America/La_Paz", "label": "Bolivia (La Paz)", "offset": "UTC-4"},
            {"value": "America/Sao_Paulo", "label": "Brasil (São Paulo)", "offset": "UTC-3"},
            {"value": "America/Santiago", "label": "Chile (Santiago)", "offset": "UTC-3"},
            {"value": "America/Bogota", "label": "Colombia (Bogotá)", "offset": "UTC-5"},
            {"value": "America/Guayaquil", "label": "Ecuador (Guayaquil)", "offset": "UTC-5"},
            {"value": "America/Asuncion", "label": "Paraguay (Asunción)", "offset": "UTC-4"},
            {"value": "America/Lima", "label": "Perú (Lima)", "offset": "UTC-5"},
            {"value": "America/Montevideo", "label": "Uruguay (Montevideo)", "offset": "UTC-3"},
            {"value": "America/Caracas", "label": "Venezuela (Caracas)", "offset": "UTC-4"},
            # Caribe
            {"value": "America/Puerto_Rico", "label": "Puerto Rico", "offset": "UTC-4"},
            {"value": "America/Santo_Domingo", "label": "República Dominicana", "offset": "UTC-4"},
            {"value": "America/Havana", "label": "Cuba (La Habana)", "offset": "UTC-5"},
            # Europa
            {"value": "Europe/Madrid", "label": "España (Madrid)", "offset": "UTC+1"},
            {"value": "Europe/Lisbon", "label": "Portugal (Lisboa)", "offset": "UTC+0"},
            # Otros
            {"value": "UTC", "label": "UTC", "offset": "UTC+0"}
        ]
    }

# ==================== DEMO DATA SEEDING ====================
@api_router.post("/seed-demo-data")
async def seed_demo_data():
    """Seed demo data for testing and demonstration"""
    
    # Check if demo data already exists
    existing_demo = await db.users.find_one({"email": "admin@genturix.com"})
    if existing_demo:
        return {"message": "Demo data already exists"}
    
    # Find or create demo condominium
    demo_condo = await db.condominiums.find_one({"name": "Residencial Las Palmas"})
    if not demo_condo:
        demo_condo_id = str(uuid.uuid4())
        demo_condo = {
            "id": demo_condo_id,
            "name": "Residencial Las Palmas",
            "address": "Av. Principal #123",
            "status": "demo",
            "is_active": True,
            "max_users": 50,
            "modules": {"security": True, "visitors": True, "school": True},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.condominiums.insert_one(demo_condo)
        
        # Create default settings for demo condo
        settings_doc = {
            "condominium_id": demo_condo["id"],
            "condominium_name": demo_condo["name"],
            **get_default_condominium_settings(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.condominium_settings.insert_one(settings_doc)
    
    demo_condo_id = demo_condo["id"]
    
    # Demo Users - SuperAdmin doesn't get condominium_id (platform-wide), others do
    demo_users = [
        {"email": "superadmin@genturix.com", "full_name": "Super Administrador", "password": "SuperAdmin123!", "roles": ["SuperAdmin"], "condo": None},
        {"email": "admin@genturix.com", "full_name": "Carlos Admin", "password": "Admin123!", "roles": ["Administrador"], "condo": demo_condo_id},
        {"email": "supervisor@genturix.com", "full_name": "María Supervisor", "password": "Super123!", "roles": ["Supervisor"], "condo": demo_condo_id},
        {"email": "guarda1@genturix.com", "full_name": "Juan Pérez", "password": "Guard123!", "roles": ["Guarda"], "condo": demo_condo_id},
        {"email": "guarda2@genturix.com", "full_name": "Pedro García", "password": "Guard123!", "roles": ["Guarda"], "condo": demo_condo_id},
        {"email": "residente@genturix.com", "full_name": "Ana Martínez", "password": "Resi123!", "roles": ["Residente"], "condo": demo_condo_id},
        {"email": "estudiante@genturix.com", "full_name": "Luis Estudiante", "password": "Stud123!", "roles": ["Estudiante"], "condo": demo_condo_id},
    ]
    
    user_ids = {}
    for user_data in demo_users:
        user_id = str(uuid.uuid4())
        user_ids[user_data["email"]] = user_id
        user_doc = {
            "id": user_id,
            "email": user_data["email"],
            "full_name": user_data["full_name"],
            "hashed_password": hash_password(user_data["password"]),
            "roles": user_data["roles"],
            "condominium_id": user_data["condo"],
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(user_doc)
    
    # Demo Guards
    demo_guards = [
        {"user_id": user_ids["guarda1@genturix.com"], "badge": "G-001", "phone": "+1234567890", "rate": 15.0},
        {"user_id": user_ids["guarda2@genturix.com"], "badge": "G-002", "phone": "+1234567891", "rate": 15.0},
    ]
    
    guard_ids = []
    for guard_data in demo_guards:
        user = await db.users.find_one({"id": guard_data["user_id"]})
        guard_id = str(uuid.uuid4())
        guard_ids.append(guard_id)
        guard_doc = {
            "id": guard_id,
            "user_id": guard_data["user_id"],
            "user_name": user["full_name"],
            "email": user["email"],
            "badge_number": guard_data["badge"],
            "phone": guard_data["phone"],
            "emergency_contact": "+0987654321",
            "hire_date": "2024-01-15",
            "hourly_rate": guard_data["rate"],
            "is_active": True,
            "total_hours": 160,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.guards.insert_one(guard_doc)
    
    # Demo Shifts
    today = datetime.now(timezone.utc).date()
    for i, guard_id in enumerate(guard_ids):
        shift_doc = {
            "id": str(uuid.uuid4()),
            "guard_id": guard_id,
            "guard_name": demo_guards[i]["badge"],
            "start_time": f"{today}T08:00:00Z",
            "end_time": f"{today}T16:00:00Z",
            "location": "Entrada Principal" if i == 0 else "Perímetro Norte",
            "notes": "Turno regular",
            "status": "active",
            "created_by": user_ids["admin@genturix.com"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.shifts.insert_one(shift_doc)
    
    # Demo Courses
    demo_courses = [
        {"title": "Seguridad Básica", "desc": "Fundamentos de seguridad física y vigilancia", "hours": 40, "instructor": "Instructor López", "category": "Seguridad"},
        {"title": "Primeros Auxilios", "desc": "Técnicas básicas de primeros auxilios y emergencias", "hours": 20, "instructor": "Dr. Ramírez", "category": "Salud"},
        {"title": "Protocolos de Emergencia", "desc": "Manejo de situaciones de emergencia y evacuación", "hours": 30, "instructor": "Cap. Moreno", "category": "Seguridad"},
    ]
    
    course_ids = []
    for course_data in demo_courses:
        course_id = str(uuid.uuid4())
        course_ids.append(course_id)
        course_doc = {
            "id": course_id,
            "title": course_data["title"],
            "description": course_data["desc"],
            "duration_hours": course_data["hours"],
            "instructor": course_data["instructor"],
            "category": course_data["category"],
            "lessons": [
                {"id": str(uuid.uuid4()), "title": "Introducción", "order": 1},
                {"id": str(uuid.uuid4()), "title": "Conceptos Básicos", "order": 2},
                {"id": str(uuid.uuid4()), "title": "Práctica", "order": 3},
                {"id": str(uuid.uuid4()), "title": "Evaluación Final", "order": 4},
            ],
            "enrolled_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.courses.insert_one(course_doc)
    
    # Demo Panic Events
    panic_event = {
        "id": str(uuid.uuid4()),
        "user_id": user_ids["residente@genturix.com"],
        "user_name": "Ana Martínez",
        "location": "Edificio A - Piso 3",
        "description": "Ruido sospechoso en pasillo",
        "status": "resolved",
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        "resolved_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    }
    await db.panic_events.insert_one(panic_event)
    
    # Demo Access Logs
    demo_accesses = [
        {"person": "Visitante 1", "type": "entry", "location": "Entrada Principal"},
        {"person": "Proveedor ABC", "type": "entry", "location": "Entrada Servicio"},
        {"person": "Visitante 1", "type": "exit", "location": "Entrada Principal"},
    ]
    
    for access_data in demo_accesses:
        access_log = {
            "id": str(uuid.uuid4()),
            "person_name": access_data["person"],
            "access_type": access_data["type"],
            "location": access_data["location"],
            "notes": None,
            "recorded_by": user_ids["guarda1@genturix.com"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.access_logs.insert_one(access_log)
    
    # Demo Audit Logs
    demo_audit = [
        {"type": AuditEventType.LOGIN_SUCCESS, "user": user_ids["admin@genturix.com"], "module": "auth", "details": {"email": "admin@genturix.com"}},
        {"type": AuditEventType.USER_CREATED, "user": user_ids["admin@genturix.com"], "module": "auth", "details": {"created_user": "guarda1@genturix.com"}},
        {"type": AuditEventType.PANIC_BUTTON, "user": user_ids["residente@genturix.com"], "module": "security", "details": {"location": "Edificio A"}},
    ]
    
    for audit_data in demo_audit:
        await log_audit_event(
            audit_data["type"],
            audit_data["user"],
            audit_data["module"],
            audit_data["details"]
        )
    
    return {"message": "Demo data seeded successfully", "credentials": {
        "admin": {"email": "admin@genturix.com", "password": "Admin123!"},
        "supervisor": {"email": "supervisor@genturix.com", "password": "Super123!"},
        "guarda": {"email": "guarda1@genturix.com", "password": "Guard123!"},
        "residente": {"email": "residente@genturix.com", "password": "Resi123!"},
        "estudiante": {"email": "estudiante@genturix.com", "password": "Stud123!"}
    }}

# ==================== DIAGNOSTIC ENDPOINT ====================
@api_router.get("/guard/diagnose-authorizations")
async def diagnose_authorizations(
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """
    Diagnostic endpoint to check authorization state.
    Returns detailed info about pending authorizations and their usage.
    """
    condo_id = current_user.get("condominium_id")
    
    # Get all pending temporary/extended authorizations
    pending = await db.visitor_authorizations.find({
        "condominium_id": condo_id,
        "authorization_type": {"$in": ["temporary", "extended"]},
        "status": {"$in": ["pending", None]},
        "is_active": True
    }, {"_id": 0}).to_list(100)
    
    results = []
    for auth in pending:
        auth_id = auth.get("id")
        
        # Check for entries with this auth_id
        entries = await db.visitor_entries.find({"authorization_id": auth_id}, {"_id": 0}).to_list(10)
        
        results.append({
            "id": auth_id[:12] + "...",
            "visitor_name": auth.get("visitor_name"),
            "authorization_type": auth.get("authorization_type"),
            "status": auth.get("status"),
            "checked_in_at": auth.get("checked_in_at"),
            "total_visits": auth.get("total_visits", 0),
            "entries_count": len(entries),
            "entries": [{"entry_at": e.get("entry_at"), "visitor_name": e.get("visitor_name")} for e in entries[:3]],
            "SHOULD_BE_USED": len(entries) > 0 or auth.get("checked_in_at") or (auth.get("total_visits", 0) > 0)
        })
    
    return {
        "condo_id": condo_id[:12] + "..." if condo_id else None,
        "total_pending": len(pending),
        "authorizations": results
    }

# ==================== CLEANUP USED AUTHORIZATIONS ====================
@api_router.post("/guard/cleanup-authorizations")
async def cleanup_used_authorizations(
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """
    Manually clean up authorizations that have been used but weren't marked as 'used'.
    This fixes legacy data issues where temporary/extended authorizations weren't properly
    marked after check-in.
    """
    condo_id = current_user.get("condominium_id")
    
    # Find all temporary/extended authorizations in this condominium
    query = {
        "condominium_id": condo_id,
        "authorization_type": {"$in": ["temporary", "extended"]},
        "status": {"$in": ["pending", None]},
        "is_active": True
    }
    
    authorizations = await db.visitor_authorizations.find(query, {"_id": 0}).to_list(500)
    logger.info(f"[cleanup] Found {len(authorizations)} temporary/extended pending authorizations in condo {condo_id[:8] if condo_id else 'N/A'}")
    
    fixed_count = 0
    fixed_auths = []
    
    for auth in authorizations:
        auth_id = auth.get("id")
        visitor_name = auth.get("visitor_name")
        auth_type = auth.get("authorization_type")
        
        # Check if there's an entry in visitor_entries with this authorization_id
        entry_exists = await db.visitor_entries.find_one({"authorization_id": auth_id})
        
        # Or check if checked_in_at is set or total_visits > 0
        already_used = (
            entry_exists or 
            auth.get("checked_in_at") or 
            (auth.get("total_visits", 0) > 0)
        )
        
        logger.info(f"[cleanup] Checking auth {auth_id[:8]} - {visitor_name} (type={auth_type}): entry_exists={bool(entry_exists)}, checked_in_at={bool(auth.get('checked_in_at'))}, total_visits={auth.get('total_visits', 0)}, already_used={already_used}")
        
        if already_used:
            # Mark as used
            result = await db.visitor_authorizations.update_one(
                {"id": auth_id},
                {"$set": {"status": "used"}}
            )
            if result.modified_count > 0:
                fixed_count += 1
                fixed_auths.append({
                    "visitor_name": visitor_name,
                    "authorization_type": auth_type
                })
                logger.info(f"[cleanup] Fixed auth {auth_id[:8]} - {visitor_name}")
    
    # Also check ALL authorizations regardless of type to see what's happening
    all_pending = await db.visitor_authorizations.find({
        "condominium_id": condo_id,
        "status": {"$in": ["pending", None]},
        "is_active": True
    }, {"_id": 0}).to_list(100)
    
    logger.info(f"[cleanup] Total pending auths in condo: {len(all_pending)}")
    for a in all_pending[:5]:  # Log first 5
        logger.info(f"[cleanup] Pending: {a.get('visitor_name')} - type={a.get('authorization_type')}, status={a.get('status')}")
    
    return {
        "success": True,
        "message": f"Se corrigieron {fixed_count} autorizaciones",
        "fixed_count": fixed_count,
        "fixed_authorizations": fixed_auths,
        "total_pending_checked": len(authorizations),
        "total_all_pending": len(all_pending)
    }

# ==================== HEALTH CHECK ====================
@api_router.get("/")
async def root():
    return {"message": "GENTURIX Enterprise Platform API", "version": "1.0.0"}

@api_router.get("/config/dev-mode")
async def get_dev_mode_status():
    """
    Returns whether the server is in development mode.
    DEPRECATED: Use /config/tenant-environment instead for tenant-specific logic.
    """
    return {
        "dev_mode": DEV_MODE,
        "features": {
            "skip_password_reset": DEV_MODE,
            "show_generated_passwords": DEV_MODE,
            "skip_email_validation": DEV_MODE
        },
        "notice": "DEPRECATED: Use tenant environment field instead"
    }

@api_router.get("/config/tenant-environment")
async def get_tenant_environment(current_user = Depends(get_current_user)):
    """
    Get the environment type for the current user's tenant.
    Returns "demo" or "production" based on tenant configuration.
    """
    condo_id = current_user.get("condominium_id")
    
    # SuperAdmin without condo defaults to production
    if not condo_id:
        if "SuperAdmin" in current_user.get("roles", []):
            return {
                "environment": "production",
                "is_demo": False,
                "features": {
                    "skip_password_reset": False,
                    "show_generated_passwords": False,
                    "send_emails": True
                }
            }
        return {"environment": "production", "is_demo": False}
    
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "environment": 1, "is_demo": 1, "name": 1})
    
    if not condo:
        return {"environment": "production", "is_demo": False}
    
    # Determine environment
    environment = condo.get("environment", "production")
    # Fallback: if environment not set but is_demo is true
    if condo.get("is_demo") and environment == "production":
        environment = "demo"
    
    is_demo = environment == "demo"
    
    return {
        "environment": environment,
        "is_demo": is_demo,
        "condominium_name": condo.get("name", "N/A"),
        "features": {
            "skip_password_reset": is_demo,
            "show_generated_passwords": is_demo,
            "send_emails": not is_demo  # Demo tenants don't send emails
        }
    }

# ==================== EMAIL TOGGLE CONFIG ====================
# This allows SuperAdmin to enable/disable email sending without touching .env

async def get_email_config():
    """Get email configuration from database or create default"""
    config = await db.system_config.find_one({"key": "email_settings"})
    if not config:
        # Default: emails ENABLED for production
        # Change to False only for testing environments
        default_config = {
            "key": "email_settings",
            "email_enabled": True,  # PRODUCTION MODE: Emails enabled by default
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": "system"
        }
        await db.system_config.insert_one(default_config)
        return default_config
    return config

async def is_email_enabled():
    """Quick check if email sending is enabled"""
    config = await get_email_config()
    return config.get("email_enabled", False)

@api_router.get("/config/email-status")
async def get_config_email_status(current_user = Depends(get_current_user)):
    """
    Get current email sending status.
    Any authenticated user can check this.
    """
    config = await get_email_config()
    return {
        "email_enabled": config.get("email_enabled", False),
        "updated_at": config.get("updated_at"),
        "updated_by": config.get("updated_by"),
        "status_text": "Emails HABILITADOS (modo producción)" if config.get("email_enabled") else "Emails DESHABILITADOS (modo pruebas)"
    }

class EmailToggleRequest(BaseModel):
    email_enabled: bool

@api_router.post("/config/email-status")
async def set_email_status(
    data: EmailToggleRequest,
    request: Request,
    current_user = Depends(require_role("SuperAdmin"))
):
    """
    Toggle email sending on/off.
    ONLY SuperAdmin can change this setting.
    """
    now = datetime.now(timezone.utc).isoformat()
    
    # Get current status for audit
    old_config = await get_email_config()
    old_status = old_config.get("email_enabled", False)
    
    # Update config
    await db.system_config.update_one(
        {"key": "email_settings"},
        {
            "$set": {
                "email_enabled": data.email_enabled,
                "updated_at": now,
                "updated_by": current_user.get("email", current_user.get("id"))
            }
        },
        upsert=True
    )
    
    # Log to audit
    await log_audit_event(
        AuditEventType.CONFIG_CHANGED if hasattr(AuditEventType, 'CONFIG_CHANGED') else AuditEventType.USER_UPDATED,
        current_user["id"],
        "system_config",
        {
            "setting": "email_enabled",
            "old_value": old_status,
            "new_value": data.email_enabled,
            "changed_by": current_user.get("email")
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    action = "habilitado" if data.email_enabled else "deshabilitado"
    
    return {
        "success": True,
        "email_enabled": data.email_enabled,
        "message": f"Envío de emails {action} exitosamente",
        "status_text": "Emails HABILITADOS (modo producción)" if data.email_enabled else "Emails DESHABILITADOS (modo pruebas)",
        "updated_at": now,
        "updated_by": current_user.get("email")
    }

# ==================== EMAIL SERVICE ENDPOINTS ====================
# Aliases for backward compatibility (imports at top of file)
email_service_send = send_email
get_email_service_status = get_email_status

@api_router.get("/test-email")
async def test_email_simple(
    email: str = Query(..., description="Email address to send test email to")
):
    """
    Simple GET endpoint for quick email testing.
    
    Usage: GET /api/test-email?email=test@example.com
    
    Returns: { "status": "sent" } on success
    """
    if not is_email_configured():
        return {
            "status": "error",
            "error": "Email service not configured (RESEND_API_KEY missing)"
        }
    
    html = get_notification_email_html(
        title="Test Email - Genturix",
        message=f"This is a test email sent at {datetime.now(timezone.utc).isoformat()}. If you received this, the email service is working correctly.",
        action_url=None
    )
    
    try:
        result = await send_email(
            to=email,
            subject="[TEST] Genturix Email Service",
            html=html
        )
        
        if result.get("success"):
            return {"status": "sent", "email_id": result.get("email_id")}
        else:
            return {"status": "error", "error": result.get("error")}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@api_router.get("/email/service-status")
async def check_email_service_status(
    current_user = Depends(require_role("SuperAdmin"))
):
    """Get current email service configuration status."""
    return get_email_service_status()


# ==================== EMAIL DEBUG ENDPOINT ====================
@api_router.get("/email/debug")
async def email_debug_endpoint(
    test_email: Optional[str] = Query(None, description="Optional: Email to send test to"),
    current_user = Depends(require_role("SuperAdmin"))
):
    """
    Comprehensive email system diagnostic endpoint.
    
    Tests:
    1. Resend API connection
    2. Sender configuration
    3. Email toggle status
    4. Optional test email send
    
    Usage: GET /api/email/debug?test_email=your@email.com
    """
    diagnostics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {}
    }
    
    # Check 1: RESEND_API_KEY configured
    api_key_ok = bool(RESEND_API_KEY)
    diagnostics["checks"]["resend_api_key"] = {
        "status": "OK" if api_key_ok else "FAIL",
        "configured": api_key_ok,
        "preview": f"{RESEND_API_KEY[:8]}..." if api_key_ok else None
    }
    
    # Check 2: Sender configuration (from email_service)
    sender = get_sender()
    diagnostics["checks"]["sender_config"] = {
        "status": "OK",
        "sender": sender,
        "service_configured": is_email_configured()
    }
    
    # Check 3: Email toggle status (database)
    email_toggle = await is_email_enabled()
    diagnostics["checks"]["email_toggle"] = {
        "status": "OK" if email_toggle else "WARN",
        "enabled": email_toggle,
        "note": "Emails are ENABLED" if email_toggle else "Emails are DISABLED - enable via POST /api/config/email-status"
    }
    
    # Check 4: Database connectivity for email config
    try:
        config = await get_email_config()
        diagnostics["checks"]["database_config"] = {
            "status": "OK",
            "email_enabled": config.get("email_enabled"),
            "updated_at": config.get("updated_at"),
            "updated_by": config.get("updated_by")
        }
    except Exception as e:
        diagnostics["checks"]["database_config"] = {
            "status": "FAIL",
            "error": str(e)
        }
    
    # Check 5: Optional test email
    if test_email:
        print(f"[EMAIL DEBUG] Sending test email to {test_email}")
        try:
            html = get_notification_email_html(
                title="Email Debug Test - Genturix",
                message=f"This is a diagnostic test email sent at {datetime.now(timezone.utc).isoformat()}. All systems are operational.",
                action_url=None
            )
            result = await send_email(
                to=test_email,
                subject="[DEBUG] Genturix Email System Test",
                html=html
            )
            diagnostics["checks"]["test_email_send"] = {
                "status": "OK" if result.get("success") else "FAIL",
                "recipient": test_email,
                "result": result
            }
        except Exception as e:
            diagnostics["checks"]["test_email_send"] = {
                "status": "FAIL",
                "recipient": test_email,
                "error": str(e)
            }
    
    # Overall status
    all_ok = all(
        check.get("status") in ["OK", "WARN"] 
        for check in diagnostics["checks"].values()
    )
    diagnostics["overall_status"] = "HEALTHY" if all_ok else "ISSUES_DETECTED"
    
    return diagnostics


# ==================== RESEND DIAGNOSTIC ENDPOINT (TEMPORARY) ====================
class TestEmailRequest(BaseModel):
    recipient_email: str
    test_type: str = "simple"  # "simple" or "credentials"

@api_router.post("/email/test-resend")
async def test_resend_email(
    data: TestEmailRequest,
    request: Request,
    current_user = Depends(require_role("SuperAdmin"))
):
    """
    🔧 DIAGNOSTIC ENDPOINT - TEMPORARY
    
    Tests the Resend email pipeline and returns detailed diagnostics.
    Only SuperAdmin can use this endpoint.
    
    This endpoint will be removed after audit is complete.
    """
    import time
    start_time = time.time()
    
    diagnostics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": str(uuid.uuid4()),
        "requested_by": current_user.get("email"),
        "recipient": data.recipient_email,
        "test_type": data.test_type
    }
    
    # 1. Check environment configuration
    diagnostics["config"] = {
        "RESEND_API_KEY_present": bool(RESEND_API_KEY),
        "RESEND_API_KEY_prefix": RESEND_API_KEY[:10] + "..." if RESEND_API_KEY else None,
        "SENDER_EMAIL": SENDER_EMAIL,
        "ENVIRONMENT": os.environ.get("ENVIRONMENT", "not_set")
    }
    
    # 2. Check email toggle status
    email_config = await get_email_config()
    diagnostics["toggle_status"] = {
        "email_enabled": email_config.get("email_enabled", False),
        "updated_at": email_config.get("updated_at"),
        "config_exists": bool(email_config.get("key"))
    }
    
    # 3. Validate API key format
    if RESEND_API_KEY:
        diagnostics["api_key_validation"] = {
            "starts_with_re_": RESEND_API_KEY.startswith("re_"),
            "length": len(RESEND_API_KEY),
            "valid_format": RESEND_API_KEY.startswith("re_") and len(RESEND_API_KEY) > 20
        }
    else:
        diagnostics["api_key_validation"] = {"error": "API key not configured"}
    
    # 4. Check domain (from SENDER_EMAIL)
    sender_domain = SENDER_EMAIL.split("@")[-1] if "@" in SENDER_EMAIL else "invalid"
    diagnostics["domain_info"] = {
        "sender_email": SENDER_EMAIL,
        "domain": sender_domain,
        "is_resend_test_domain": sender_domain == "resend.dev",
        "warning": "Using resend.dev test domain - emails only work to verified addresses" if sender_domain == "resend.dev" else None
    }
    
    # 5. Attempt to send test email
    if not RESEND_API_KEY:
        diagnostics["send_result"] = {
            "status": "skipped",
            "reason": "RESEND_API_KEY not configured"
        }
    else:
        test_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>🔧 GENTURIX - Test de Diagnóstico Resend</h2>
            <p>Este es un correo de prueba para validar la configuración de Resend.</p>
            <hr>
            <p><strong>Timestamp:</strong> {diagnostics["timestamp"]}</p>
            <p><strong>Request ID:</strong> {diagnostics["request_id"]}</p>
            <p><strong>Enviado por:</strong> {current_user.get("email")}</p>
            <p><strong>Ambiente:</strong> {os.environ.get("ENVIRONMENT", "not_set")}</p>
            <hr>
            <p style="color: #666; font-size: 12px;">
                Este correo fue enviado como parte de una auditoría del sistema de emails.
            </p>
        </body>
        </html>
        """
        
        params = {
            "from": SENDER_EMAIL,
            "to": [data.recipient_email],
            "subject": f"[GENTURIX-DIAG] Test Resend - {diagnostics['request_id'][:8]}",
            "html": test_html
        }
        
        try:
            logger.info(f"[RESEND-DIAG] Attempting test email | request_id={diagnostics['request_id']} | to={data.recipient_email}")
            
            email_response = await asyncio.to_thread(resend.Emails.send, params)
            
            elapsed_time = time.time() - start_time
            
            # Parse response
            if isinstance(email_response, dict):
                diagnostics["send_result"] = {
                    "status": "success",
                    "email_id": email_response.get("id"),
                    "response": email_response,
                    "elapsed_ms": round(elapsed_time * 1000, 2)
                }
                logger.info(f"[RESEND-DIAG] SUCCESS | request_id={diagnostics['request_id']} | email_id={email_response.get('id')}")
            else:
                # Handle Resend SDK response object
                diagnostics["send_result"] = {
                    "status": "success",
                    "email_id": getattr(email_response, 'id', str(email_response)),
                    "response_type": type(email_response).__name__,
                    "elapsed_ms": round(elapsed_time * 1000, 2)
                }
                logger.info(f"[RESEND-DIAG] SUCCESS | request_id={diagnostics['request_id']} | response_type={type(email_response).__name__}")
                
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_str = str(e)
            error_type = type(e).__name__
            
            # Try to extract HTTP status from error
            http_status = None
            if "401" in error_str:
                http_status = 401
            elif "403" in error_str:
                http_status = 403
            elif "422" in error_str:
                http_status = 422
            elif "429" in error_str:
                http_status = 429
            
            diagnostics["send_result"] = {
                "status": "failed",
                "error": error_str,
                "error_type": error_type,
                "http_status": http_status,
                "elapsed_ms": round(elapsed_time * 1000, 2),
                "possible_causes": []
            }
            
            # Add possible causes based on error
            if http_status == 401:
                diagnostics["send_result"]["possible_causes"].append("Invalid API key")
            elif http_status == 403:
                diagnostics["send_result"]["possible_causes"].append("Domain not verified or sender email not authorized")
            elif http_status == 422:
                diagnostics["send_result"]["possible_causes"].append("Invalid email format or missing required fields")
            elif http_status == 429:
                diagnostics["send_result"]["possible_causes"].append("Rate limit exceeded")
            elif "domain" in error_str.lower():
                diagnostics["send_result"]["possible_causes"].append("Sender domain not verified in Resend")
            
            logger.error(f"[RESEND-DIAG] FAILED | request_id={diagnostics['request_id']} | error_type={error_type} | error={error_str}")
    
    # 6. Summary
    diagnostics["summary"] = {
        "api_key_configured": bool(RESEND_API_KEY),
        "sender_email_valid": "@" in SENDER_EMAIL,
        "using_test_domain": sender_domain == "resend.dev",
        "email_toggle_enabled": email_config.get("email_enabled", False),
        "send_attempted": diagnostics.get("send_result", {}).get("status") != "skipped",
        "send_successful": diagnostics.get("send_result", {}).get("status") == "success"
    }
    
    # Log full diagnostics
    logger.info(f"[RESEND-DIAG] Full diagnostics | request_id={diagnostics['request_id']} | summary={diagnostics['summary']}")
    
    return diagnostics

# ==================== SYSTEM RESET (FULL WIPE) ====================
@api_router.post("/super-admin/reset-all-data")
async def reset_all_data(
    request: Request,
    current_user = Depends(require_role("SuperAdmin"))
):
    """
    ⚠️ DANGER: Complete system wipe.
    Deletes ALL data from ALL collections EXCEPT the SuperAdmin account.
    
    This endpoint:
    - Deletes all condominiums
    - Deletes all users (except SuperAdmin)
    - Deletes all guards, shifts, reservations, authorizations, etc.
    - Leaves the system in a clean state
    """
    superadmin_email = current_user.get("email", "").lower().strip()
    
    # Keep track of what was deleted for the response
    deleted_counts = {}
    
    # Collections to clear completely
    collections_to_clear = [
        "condominiums",
        "guards", 
        "guard_shifts",
        "visitors",
        "visitor_authorizations",
        "access_logs",
        "panic_alerts",
        "reservations",
        "reservation_areas",
        "employees",
        "announcements",
        "audit_logs",
        "push_subscriptions",
        "courses",
        "modules",
        "student_progress"
    ]
    
    for collection_name in collections_to_clear:
        collection = db[collection_name]
        count = await collection.count_documents({})
        await collection.delete_many({})
        deleted_counts[collection_name] = count
    
    # Delete all users EXCEPT the SuperAdmin who is making the request
    users_deleted = await db.users.delete_many({
        "email": {"$ne": superadmin_email}
    })
    deleted_counts["users"] = users_deleted.deleted_count
    
    # Clear system config except email_settings
    await db.system_config.delete_many({"key": {"$ne": "email_settings"}})
    
    # Log this critical action
    await log_audit_event(
        AuditEventType.USER_DELETED if hasattr(AuditEventType, 'USER_DELETED') else AuditEventType.USER_UPDATED,
        current_user["id"],
        "system",
        {
            "action": "FULL_SYSTEM_RESET",
            "deleted_counts": deleted_counts,
            "initiated_by": superadmin_email,
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "success": True,
        "message": "Sistema limpiado completamente. Solo permanece la cuenta SuperAdmin.",
        "deleted_counts": deleted_counts,
        "preserved": {
            "superadmin_account": superadmin_email,
            "email_settings": True
        },
        "next_steps": [
            "Crear un nuevo condominio desde el Onboarding Wizard",
            "Configurar módulos y usuarios",
            "Comenzar pruebas desde cero"
        ]
    }

# Include the billing router in api_router
# This maintains the /api/billing/* path structure
api_router.include_router(billing_router)

# Include the super-admin billing router
# This maintains the /api/super-admin/billing/* path structure
api_router.include_router(billing_super_admin_router)

# Include the router in the main app
app.include_router(api_router)

# ==================== CORS CONFIGURATION ====================
def get_cors_origins() -> list:
    """
    Get allowed origins based on environment.
    
    PRODUCTION: Explicit list of allowed production domains
    DEVELOPMENT: Production domains + localhost fallbacks
    
    IMPORTANT: All production domains must be explicitly listed for security
    
    Domain architecture:
    - https://genturix.com - Landing page
    - https://app.genturix.com - Application frontend (PWA)
    - https://www.genturix.com - WWW redirect
    - https://genturix.vercel.app - Vercel deployment
    """
    # Production domains - explicitly listed for security
    production_origins = [
        "https://genturix.com",
        "https://www.genturix.com",
        "https://app.genturix.com",  # Main application subdomain
        "https://genturix.vercel.app",
    ]
    
    # Add FRONTEND_URL if set and not already in list
    if FRONTEND_URL:
        frontend = FRONTEND_URL.rstrip('/')
        if frontend not in production_origins:
            production_origins.append(frontend)
    
    if ENVIRONMENT == "production":
        if not production_origins:
            logger.error("[CORS] CRITICAL: No production origins configured!")
        logger.info(f"[CORS] Production mode - allowing origins: {production_origins}")
        return production_origins
    else:
        # Development mode - add localhost fallbacks
        dev_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
        all_origins = list(set(production_origins + dev_origins))
        logger.info(f"[CORS] Development mode - allowing origins: {all_origins}")
        return all_origins
        return all_origins

cors_origins = get_cors_origins()
logger.info(f"[CORS] Environment: {ENVIRONMENT}, Allowed origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== MONGODB INDEX INITIALIZATION ====================
async def initialize_indexes():
    """Initialize MongoDB indexes for performance and data integrity.
    Safe to call multiple times - indexes are created only if they don't exist.
    Each index is created independently to avoid partial failures."""
    
    async def safe_create_index(collection, keys, **kwargs):
        """Create index safely, handling existing indexes and duplicates"""
        try:
            index_name = await collection.create_index(keys, **kwargs)
            return True, index_name
        except Exception as e:
            error_code = getattr(e, 'code', None)
            # 85 = IndexOptionsConflict (index already exists with different options)
            # 11000 = DuplicateKey (can't create unique index due to duplicates)
            if error_code == 85:
                return True, f"already exists"
            elif error_code == 11000:
                return False, f"duplicate key error - clean data first"
            return False, str(e)
    
    indexes_to_create = [
        # ==================== USERS ====================
        (db.users, "email", {"unique": True, "background": True}),
        (db.users, "condominium_id", {"background": True}),
        
        # ==================== BILLING (HIGH IMPACT) ====================
        # Optimizes payment history queries by condominium
        (db.billing_payments, [("condominium_id", 1), ("created_at", -1)], {"background": True}),
        # Optimizes billing events audit trail
        (db.billing_events, [("condominium_id", 1), ("created_at", -1)], {"background": True}),
        # Optimizes financial dashboard and portfolio queries
        (db.condominiums, "billing_status", {"background": True}),
        # Optimizes lookups by id (if not already unique)
        (db.condominiums, "id", {"unique": True, "background": True}),
        # Optimizes seat upgrade request lookups
        (db.seat_upgrade_requests, [("condominium_id", 1), ("status", 1)], {"background": True}),
        # Optimizes billing scheduler runs queries
        (db.billing_scheduler_runs, "run_date", {"background": True}),
        # Optimizes email deduplication checks
        (db.billing_email_log, [("condominium_id", 1), ("email_type", 1), ("sent_date", 1)], {"background": True}),
        
        # ==================== GUARDS & SHIFTS ====================
        # Optimizes guard queries by condominium
        (db.guards, "condominium_id", {"background": True}),
        # Optimizes shift reports and lookups
        (db.shifts, [("condominium_id", 1), ("guard_id", 1)], {"background": True}),
        (db.shifts, [("condominium_id", 1), ("start_time", -1)], {"background": True}),
        
        # ==================== PUSH NOTIFICATIONS ====================
        # Compound unique index for deduplication
        (db.push_subscriptions, [("user_id", 1), ("endpoint", 1)], {"unique": True, "background": True}),
        (db.push_subscriptions, "condominium_id", {"background": True}),
        
        # ==================== AUDIT LOGS ====================
        (db.audit_logs, "user_id", {"background": True}),
        (db.audit_logs, "created_at", {"background": True, "expireAfterSeconds": 60*60*24*90}),  # 90-day TTL
        
        # ==================== RESERVATIONS ====================
        (db.reservations, "condominium_id", {"background": True}),
        (db.reservations, "start_time", {"background": True}),
        
        # ==================== VISITORS ====================
        (db.visitor_authorizations, "condominium_id", {"background": True}),
        (db.visitor_authorizations, "created_by", {"background": True}),
        (db.visitor_entries, "condominium_id", {"background": True}),
    ]
    
    success_count = 0
    for collection, keys, options in indexes_to_create:
        collection_name = collection.name
        success, result = await safe_create_index(collection, keys, **options)
        if success:
            logger.info(f"[DB-INDEX] {collection_name}.{keys}: {result}")
            success_count += 1
        else:
            logger.warning(f"[DB-INDEX] {collection_name}.{keys}: FAILED - {result}")
    
    logger.info(f"[DB-INDEX] Initialization complete: {success_count}/{len(indexes_to_create)} indexes ready")

@app.on_event("startup")
async def startup_event():
    """
    Application startup tasks.
    
    IMPORTANT: These tasks are non-blocking. If MongoDB fails, the app
    will still start but features requiring DB will fail gracefully.
    This allows Railway health checks to pass and the app to receive
    traffic while DB issues are resolved.
    """
    # Test MongoDB connection first
    try:
        await db.command("ping")
        logger.info("[STARTUP] MongoDB connection successful")
    except Exception as e:
        logger.error(f"[STARTUP] MongoDB connection FAILED: {e}")
        logger.warning("[STARTUP] App will start but DB features will be unavailable")
        return  # Skip DB-dependent initialization
    
    # Initialize indexes (non-fatal if fails)
    try:
        await initialize_indexes()
    except Exception as e:
        logger.error(f"[STARTUP] Index initialization failed: {e}")
        logger.warning("[STARTUP] Indexes may not be optimized, but app will continue")
    
    # Initialize global pricing config (non-fatal if fails)
    try:
        await ensure_global_pricing_config()
    except Exception as e:
        logger.error(f"[STARTUP] Global pricing config failed: {e}")
        logger.warning("[STARTUP] Pricing will use fallback defaults")
    
    # Initialize billing module dependencies (PHASE 3)
    try:
        init_billing_service(
            database=db,
            resend_key=RESEND_API_KEY,
            sender_email=SENDER_EMAIL,
            yearly_discount=YEARLY_DISCOUNT_PERCENT,
            log=logger
        )
        init_billing_scheduler(database=db, log=logger)
        logger.info("[STARTUP] Billing module initialized successfully")
    except Exception as e:
        logger.error(f"[STARTUP] Billing module initialization failed: {e}")
        logger.warning("[STARTUP] Billing features may not work correctly")
    
    # Initialize users module (PHASE 2A - Core Seat Engine)
    try:
        set_users_db(db)
        set_users_logger(logger)
        logger.info("[STARTUP] Users module initialized successfully")
    except Exception as e:
        logger.error(f"[STARTUP] Users module initialization failed: {e}")
        logger.warning("[STARTUP] User seat management may not work correctly")
    
    # Start billing scheduler (non-fatal if fails)
    try:
        start_billing_scheduler()
        logger.info("[STARTUP] Billing scheduler started successfully")
    except Exception as e:
        logger.error(f"[STARTUP] Billing scheduler failed to start: {e}")
        logger.warning("[STARTUP] Automatic billing checks will not run")

@app.on_event("shutdown")
async def shutdown_db_client():
    stop_billing_scheduler()
    client.close()



# ============================================
# RAILWAY DYNAMIC PORT ENTRY POINT
# ============================================
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
