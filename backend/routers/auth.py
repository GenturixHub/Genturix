"""GENTURIX - Auth + Password Reset Router (Auto-extracted from server.py)"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Response, UploadFile, File as FastAPIFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum
import uuid, io, json, os, re

# Import ALL shared dependencies from core
from core import *

router = APIRouter()

# ==================== AUTH ROUTES ====================

@router.post("/auth/register", response_model=UserResponse)
@limiter.limit(RATE_LIMIT_AUTH)
async def register(request: Request, user_data: UserCreate):
    """Register new user - rate limited to prevent abuse"""
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
        {"email": user_data.email, "roles": forced_role},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=user_data.condominium_id,
        user_email=user_data.email
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

@router.post("/auth/login", response_model=TokenResponse)
@limiter.limit(RATE_LIMIT_AUTH)
async def login(request: Request, credentials: UserLogin):
    """Login endpoint - rate limited to prevent brute force"""
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
            request.headers.get("user-agent", "unknown"),
            user_email=normalized_email
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
    
    # Determine token expiration based on role
    # Guards get extended sessions (12 hours) for shift work
    user_roles = user.get("roles", [])
    is_guard = "Guarda" in user_roles or "Guard" in user_roles
    
    if is_guard:
        # Extended session for guards - 12 hours
        access_token_expires = timedelta(minutes=GUARD_ACCESS_TOKEN_EXPIRE_MINUTES)
        print(f"[AUTH] Guard role detected - using extended session ({GUARD_ACCESS_TOKEN_EXPIRE_MINUTES} minutes)")
    else:
        # Standard session for other roles
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    access_token = create_access_token(token_data, access_token_expires)
    refresh_token = create_refresh_token(token_data, refresh_token_id)
    
    await log_audit_event(
        AuditEventType.LOGIN_SUCCESS,
        user["id"],
        "auth",
        {"email": user["email"], "password_reset_required": password_reset_required},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=user.get("condominium_id"),
        user_email=user.get("email")
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
            "apartment": user.get("apartment") or user.get("role_data", {}).get("apartment_number"),
            "profile_photo": user.get("profile_photo"),
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

@router.post("/auth/refresh")
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
        logger.warning("[SECURITY] Refresh token received in body instead of cookie")
    
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
    
    # Determine token expiration based on role (same logic as login)
    user_roles = user.get("roles", [])
    is_guard = "Guarda" in user_roles or "Guard" in user_roles
    
    if is_guard:
        access_token_expires = timedelta(minutes=GUARD_ACCESS_TOKEN_EXPIRE_MINUTES)
    else:
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    new_access_token = create_access_token(token_data, access_token_expires)
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

@router.post("/auth/logout")
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

@router.get("/auth/me", response_model=UserResponse)
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

@router.post("/auth/change-password")
@limiter.limit(RATE_LIMIT_SENSITIVE)
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
        request.headers.get("user-agent", "unknown"),
        condominium_id=current_user.get("condominium_id"),
        user_email=current_user.get("email")
    )
    
    return {
        "message": "Contraseña actualizada exitosamente",
        "password_changed_at": password_changed_at,
        "sessions_invalidated": True
    }

# ==================== PUSH NOTIFICATION ROUTES ====================
@router.get("/push/vapid-public-key")
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


@router.post("/auth/request-password-reset")
@limiter.limit(RATE_LIMIT_SENSITIVE)
async def request_password_reset_code(
    request: Request,
    request_data: ForgotPasswordRequest
):
    """
    Request a password reset code via email - rate limited to prevent abuse.
    
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
    
    await log_audit_event(
        AuditEventType.USER_UPDATED, user.get("id", "unknown"), "auth",
        {"action": "password_reset_requested"},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=user.get("condominium_id"),
        user_email=email,
    )
    
    return {"message": "Si el correo existe, recibirás un código de verificación"}


@router.post("/auth/reset-password")
@limiter.limit(RATE_LIMIT_SENSITIVE)
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
    
    logger.debug(f"[PASSWORD-RESET] Verifying code for {email}, match={code_hash_match}, attempts={attempt_count}")
    
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
    
    # Log audit event (non-blocking - don't fail if audit logging fails)
    try:
        await log_audit_event(
            AuditEventType.PASSWORD_RESET_COMPLETED,
            user.get("id"),
            "auth",
            {"method": "verification_code", "email": email},
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "unknown")
        )
    except Exception as audit_error:
        # Audit logging should not block password reset success
        logger.warning(f"[PASSWORD-RESET] Audit log failed (non-critical): {str(audit_error)}")
    
    print(f"[AUTH EVENT] Password reset SUCCESS | email={email}")
    logger.info(f"[PASSWORD-RESET] Password reset completed for {email}")
    print(f"[FLOW] password_reset_success | email={email}")
    
    return {"message": "Contraseña actualizada exitosamente"}


# ==================== PUSH NOTIFICATION ENDPOINTS (REFACTORED) ====================
