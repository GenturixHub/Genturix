"""GENTURIX Core — Helper Functions (Auth, Push, Billing, Audit)"""
from .imports import *
from .database import *
from .security import *
from .enums import *
from .models import *

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

async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    """Like get_current_user but returns None instead of raising on missing/invalid auth."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

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

