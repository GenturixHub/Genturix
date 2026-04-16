"""GENTURIX Core — Database, JWT, Cookie Configuration"""
from .imports import *

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
