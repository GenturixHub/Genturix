"""
GENTURIX - Centralized Email Service
=====================================
Production email sending using Resend.
All outgoing emails should go through this service.

Sender: Genturix Security <no-reply@gentrix.com>
"""

import os
import asyncio
import logging
from typing import Optional, List, Dict, Any

import resend

logger = logging.getLogger(__name__)

# Initialize Resend API key
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Standard sender address for all emails (Production)
DEFAULT_SENDER = "Genturix Security <no-reply@gentrix.com>"

# Fallback sender for testing (Resend sandbox)
FALLBACK_SENDER = "Genturix <onboarding@resend.dev>"


def get_sender() -> str:
    """Get the appropriate sender based on configuration."""
    if not RESEND_API_KEY:
        return FALLBACK_SENDER
    
    # Check if using production domain
    # If key is configured, use production sender
    return DEFAULT_SENDER


def send_email_sync(
    to: str,
    subject: str,
    html: str,
    sender: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send email synchronously.
    
    Args:
        to: Recipient email address
        subject: Email subject
        html: HTML content of the email
        sender: Optional custom sender (defaults to DEFAULT_SENDER)
    
    Returns:
        Dict with success status and email_id or error
    """
    if not RESEND_API_KEY:
        logger.warning("[EMAIL] RESEND_API_KEY not configured - email not sent")
        return {"success": False, "error": "Email service not configured"}
    
    try:
        params = {
            "from": sender or get_sender(),
            "to": [to] if isinstance(to, str) else to,
            "subject": subject,
            "html": html
        }
        
        response = resend.Emails.send(params)
        email_id = response.get("id", "unknown")
        
        # Production logging
        print(f"[EMAIL SENT] {to}")
        logger.info(f"[EMAIL] Sent to: {to} | Subject: {subject[:50]}... | ID: {email_id}")
        
        return {
            "success": True,
            "email_id": email_id,
            "recipient": to
        }
        
    except Exception as e:
        logger.error(f"[EMAIL] Failed to send to {to}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "recipient": to
        }


async def send_email(
    to: str,
    subject: str,
    html: str,
    sender: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send email asynchronously (non-blocking).
    
    Args:
        to: Recipient email address
        subject: Email subject
        html: HTML content of the email
        sender: Optional custom sender (defaults to DEFAULT_SENDER)
    
    Returns:
        Dict with success status and email_id or error
    """
    if not RESEND_API_KEY:
        logger.warning("[EMAIL] RESEND_API_KEY not configured - email not sent")
        return {"success": False, "error": "Email service not configured"}
    
    try:
        params = {
            "from": sender or get_sender(),
            "to": [to] if isinstance(to, str) else to,
            "subject": subject,
            "html": html
        }
        
        # Run in thread to avoid blocking
        response = await asyncio.to_thread(resend.Emails.send, params)
        email_id = response.get("id", "unknown")
        
        logger.info(f"[EMAIL] Sent to: {to} | Subject: {subject[:50]}... | ID: {email_id}")
        
        return {
            "success": True,
            "email_id": email_id,
            "recipient": to
        }
        
    except Exception as e:
        logger.error(f"[EMAIL] Failed to send to {to}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "recipient": to
        }


async def send_bulk_emails(
    recipients: List[Dict[str, str]],
    subject: str,
    html_template: str,
    personalize: bool = False
) -> Dict[str, Any]:
    """
    Send emails to multiple recipients.
    
    Args:
        recipients: List of dicts with 'email' and optionally 'name'
        subject: Email subject
        html_template: HTML template (can contain {name} placeholder)
        personalize: Whether to personalize with recipient name
    
    Returns:
        Dict with summary of sent/failed emails
    """
    results = {
        "total": len(recipients),
        "sent": 0,
        "failed": 0,
        "details": []
    }
    
    for recipient in recipients:
        email = recipient.get("email")
        name = recipient.get("name", "Usuario")
        
        if not email:
            continue
        
        html = html_template
        if personalize and "{name}" in html:
            html = html.replace("{name}", name)
        
        result = await send_email(to=email, subject=subject, html=html)
        
        if result.get("success"):
            results["sent"] += 1
        else:
            results["failed"] += 1
        
        results["details"].append(result)
    
    return results


# =============================================================================
# Email Templates
# =============================================================================

def get_welcome_email_html(user_name: str, email: str, password: str, login_url: str) -> str:
    """Generate welcome email with credentials."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 30px; border-radius: 10px; text-align: center;">
            <h1 style="color: #00d4ff; margin: 0;">GENTURIX</h1>
            <p style="color: #888; margin-top: 5px;">Sistema de Seguridad Residencial</p>
        </div>
        
        <div style="padding: 30px 20px;">
            <h2 style="color: #1a1a2e;">¡Bienvenido, {user_name}!</h2>
            <p>Tu cuenta ha sido creada exitosamente. Aquí están tus credenciales de acceso:</p>
            
            <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>Email:</strong> {email}</p>
                <p style="margin: 5px 0;"><strong>Contraseña temporal:</strong> <code style="background: #e0e0e0; padding: 2px 8px; border-radius: 4px;">{password}</code></p>
            </div>
            
            <p style="color: #e74c3c;"><strong>Importante:</strong> Por seguridad, te recomendamos cambiar tu contraseña después del primer inicio de sesión.</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{login_url}" style="background: #00d4ff; color: #1a1a2e; padding: 12px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; display: inline-block;">
                    Iniciar Sesión
                </a>
            </div>
        </div>
        
        <div style="text-align: center; padding: 20px; color: #888; font-size: 12px; border-top: 1px solid #eee;">
            <p>Este es un correo automático de Genturix Security.</p>
            <p>Si no solicitaste esta cuenta, por favor ignora este mensaje.</p>
        </div>
    </body>
    </html>
    """


def get_password_reset_email_html(user_name: str, reset_url: str) -> str:
    """Generate password reset email."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 30px; border-radius: 10px; text-align: center;">
            <h1 style="color: #00d4ff; margin: 0;">GENTURIX</h1>
            <p style="color: #888; margin-top: 5px;">Recuperación de Contraseña</p>
        </div>
        
        <div style="padding: 30px 20px;">
            <h2 style="color: #1a1a2e;">Hola, {user_name}</h2>
            <p>Recibimos una solicitud para restablecer tu contraseña.</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" style="background: #00d4ff; color: #1a1a2e; padding: 12px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; display: inline-block;">
                    Restablecer Contraseña
                </a>
            </div>
            
            <p style="color: #888; font-size: 14px;">Este enlace expira en 1 hora.</p>
            <p style="color: #888; font-size: 14px;">Si no solicitaste este cambio, puedes ignorar este correo de forma segura.</p>
        </div>
        
        <div style="text-align: center; padding: 20px; color: #888; font-size: 12px; border-top: 1px solid #eee;">
            <p>Este es un correo automático de Genturix Security.</p>
        </div>
    </body>
    </html>
    """


def get_notification_email_html(title: str, message: str, action_url: Optional[str] = None, action_text: str = "Ver Detalles") -> str:
    """Generate generic notification email."""
    action_button = ""
    if action_url:
        action_button = f"""
        <div style="text-align: center; margin: 30px 0;">
            <a href="{action_url}" style="background: #00d4ff; color: #1a1a2e; padding: 12px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; display: inline-block;">
                {action_text}
            </a>
        </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 30px; border-radius: 10px; text-align: center;">
            <h1 style="color: #00d4ff; margin: 0;">GENTURIX</h1>
            <p style="color: #888; margin-top: 5px;">Notificación del Sistema</p>
        </div>
        
        <div style="padding: 30px 20px;">
            <h2 style="color: #1a1a2e;">{title}</h2>
            <p>{message}</p>
            {action_button}
        </div>
        
        <div style="text-align: center; padding: 20px; color: #888; font-size: 12px; border-top: 1px solid #eee;">
            <p>Este es un correo automático de Genturix Security.</p>
        </div>
    </body>
    </html>
    """


def get_emergency_alert_email_html(
    resident_name: str,
    alert_type: str,
    location: str,
    timestamp: str,
    condominium_name: str
) -> str:
    """Generate emergency alert email."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #c0392b 0%, #e74c3c 100%); padding: 30px; border-radius: 10px; text-align: center;">
            <h1 style="color: white; margin: 0;">⚠️ ALERTA DE EMERGENCIA</h1>
            <p style="color: rgba(255,255,255,0.9); margin-top: 5px;">GENTURIX Security</p>
        </div>
        
        <div style="padding: 30px 20px;">
            <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p style="margin: 0; color: #856404;"><strong>Tipo de alerta:</strong> {alert_type}</p>
            </div>
            
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;"><strong>Residente:</strong></td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;">{resident_name}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;"><strong>Ubicación:</strong></td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;">{location}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;"><strong>Hora:</strong></td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;">{timestamp}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 0;"><strong>Condominio:</strong></td>
                    <td style="padding: 10px 0;">{condominium_name}</td>
                </tr>
            </table>
            
            <p style="color: #e74c3c; margin-top: 20px;"><strong>Por favor, responda a esta emergencia inmediatamente.</strong></p>
        </div>
        
        <div style="text-align: center; padding: 20px; color: #888; font-size: 12px; border-top: 1px solid #eee;">
            <p>Este es un correo automático de emergencia de Genturix Security.</p>
        </div>
    </body>
    </html>
    """


# =============================================================================
# Utility Functions
# =============================================================================

def is_email_configured() -> bool:
    """Check if email service is properly configured."""
    return bool(RESEND_API_KEY)


def get_email_status() -> Dict[str, Any]:
    """Get current email service status."""
    return {
        "configured": is_email_configured(),
        "sender": get_sender(),
        "api_key_set": bool(RESEND_API_KEY),
        "api_key_preview": f"{RESEND_API_KEY[:8]}..." if RESEND_API_KEY else None
    }
