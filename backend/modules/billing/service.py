"""
BILLING SERVICE MODULE
======================
Core billing logic and utility functions.
Extracted from server.py without logic changes.
"""

import uuid
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import resend

# These will be set by the main app on initialization
db = None
logger = logging.getLogger(__name__)

# Config values - will be imported from main
RESEND_API_KEY = None
SENDER_EMAIL = None
YEARLY_DISCOUNT_PERCENT = 10

# Default grace period in days
DEFAULT_GRACE_PERIOD_DAYS = 5


def init_service(database, resend_key, sender_email, yearly_discount, log):
    """Initialize service with dependencies from main app."""
    global db, RESEND_API_KEY, SENDER_EMAIL, YEARLY_DISCOUNT_PERCENT, logger
    db = database
    RESEND_API_KEY = resend_key
    SENDER_EMAIL = sender_email
    YEARLY_DISCOUNT_PERCENT = yearly_discount
    logger = log


# Import helper functions that will be needed
# These need to be available in server.py scope
async def get_effective_seat_price(condominium_id: str) -> float:
    """Get effective seat price for a condominium."""
    # This function is defined in server.py, we'll reference it there
    raise NotImplementedError("Must be called from server.py context")


async def get_global_pricing() -> dict:
    """Get global pricing configuration."""
    raise NotImplementedError("Must be called from server.py context")


# Email templates for billing notifications
BILLING_EMAIL_TEMPLATES = {
    "reminder_3_days": {
        "subject": "Recordatorio: Tu suscripción vence en 3 días - {condo_name}",
        "template": """
        <h2>Recordatorio de Pago - {condo_name}</h2>
        <p>Hola,</p>
        <p>Este es un recordatorio de que tu suscripción de Genturix vence en <strong>3 días</strong>.</p>
        <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p><strong>Detalles de facturación:</strong></p>
            <ul>
                <li>Condominio: {condo_name}</li>
                <li>Monto: ${amount}</li>
                <li>Fecha de vencimiento: {due_date}</li>
                <li>Asientos contratados: {seats}</li>
            </ul>
        </div>
        <p>Por favor realiza el pago antes de la fecha de vencimiento para evitar interrupciones en el servicio.</p>
        <p>Saludos,<br>Equipo Genturix</p>
        """
    },
    "reminder_due_today": {
        "subject": "URGENTE: Tu suscripción vence HOY - {condo_name}",
        "template": """
        <h2>Tu Pago Vence Hoy - {condo_name}</h2>
        <p>Hola,</p>
        <p><strong>Tu suscripción de Genturix vence HOY.</strong></p>
        <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107;">
            <p><strong>Acción requerida:</strong></p>
            <ul>
                <li>Condominio: {condo_name}</li>
                <li>Monto pendiente: ${amount}</li>
                <li>Fecha de vencimiento: {due_date}</li>
            </ul>
        </div>
        <p>Si ya realizaste el pago, puedes ignorar este mensaje. De lo contrario, por favor realiza el pago hoy para evitar restricciones.</p>
        <p>Saludos,<br>Equipo Genturix</p>
        """
    },
    "status_past_due": {
        "subject": "AVISO: Tu cuenta está en mora - {condo_name}",
        "template": """
        <h2>Cuenta en Mora - {condo_name}</h2>
        <p>Hola,</p>
        <p>Tu suscripción de Genturix ha vencido y tu cuenta está ahora <strong>en estado de mora</strong>.</p>
        <div style="background: #f8d7da; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #dc3545;">
            <p><strong>Estado de la cuenta:</strong></p>
            <ul>
                <li>Condominio: {condo_name}</li>
                <li>Monto pendiente: ${amount}</li>
                <li>Días vencido: {days_overdue}</li>
                <li>Período de gracia: {grace_days} días</li>
            </ul>
        </div>
        <p><strong>Importante:</strong> Si el pago no se realiza dentro del período de gracia, tu cuenta será suspendida y se restringirá el acceso a ciertas funciones.</p>
        <p>Por favor contacta a soporte si necesitas ayuda.</p>
        <p>Saludos,<br>Equipo Genturix</p>
        """
    },
    "status_suspended": {
        "subject": "ALERTA: Tu cuenta ha sido suspendida - {condo_name}",
        "template": """
        <h2>Cuenta Suspendida - {condo_name}</h2>
        <p>Hola,</p>
        <p>Lamentamos informarte que tu cuenta de Genturix ha sido <strong>suspendida</strong> por falta de pago.</p>
        <div style="background: #f5c6cb; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #721c24;">
            <p><strong>Restricciones activas:</strong></p>
            <ul>
                <li>No se pueden crear nuevos registros</li>
                <li>No se pueden editar datos existentes</li>
                <li>Acceso limitado a consultas y dashboard</li>
            </ul>
            <p><strong>Deuda pendiente:</strong> ${amount}</p>
        </div>
        <p>Para reactivar tu cuenta, por favor realiza el pago pendiente lo antes posible.</p>
        <p>Contacta a soporte: soporte@genturix.com</p>
        <p>Saludos,<br>Equipo Genturix</p>
        """
    },
    "payment_confirmed": {
        "subject": "Pago Confirmado - Tu cuenta está activa - {condo_name}",
        "template": """
        <h2>Pago Confirmado - {condo_name}</h2>
        <p>Hola,</p>
        <p>Hemos recibido tu pago exitosamente. Tu cuenta de Genturix está ahora <strong>activa</strong>.</p>
        <div style="background: #d4edda; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745;">
            <p><strong>Detalles del pago:</strong></p>
            <ul>
                <li>Condominio: {condo_name}</li>
                <li>Monto pagado: ${amount}</li>
                <li>Próxima fecha de cobro: {next_due_date}</li>
            </ul>
        </div>
        <p>Gracias por confiar en Genturix.</p>
        <p>Saludos,<br>Equipo Genturix</p>
        """
    }
}


async def send_billing_notification_email(
    email_type: str,
    recipient_email: str,
    condo_name: str,
    amount: float,
    due_date: str,
    seats: int = 0,
    days_overdue: int = 0,
    grace_days: int = DEFAULT_GRACE_PERIOD_DAYS,
    next_due_date: str = ""
) -> bool:
    """
    Send billing notification email using Resend.
    Returns True if successful, False otherwise.
    """
    if not RESEND_API_KEY or RESEND_API_KEY == "your_resend_api_key_here":
        logger.warning(f"[BILLING-EMAIL] Skipping email - Resend not configured")
        return False
    
    template_config = BILLING_EMAIL_TEMPLATES.get(email_type)
    if not template_config:
        logger.error(f"[BILLING-EMAIL] Unknown email type: {email_type}")
        return False
    
    try:
        subject = template_config["subject"].format(condo_name=condo_name)
        html_content = template_config["template"].format(
            condo_name=condo_name,
            amount=f"{amount:,.2f}",
            due_date=due_date,
            seats=seats,
            days_overdue=days_overdue,
            grace_days=grace_days,
            next_due_date=next_due_date
        )
        
        params = {
            "from": SENDER_EMAIL,
            "to": [recipient_email],
            "subject": subject,
            "html": html_content
        }
        
        await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[BILLING-EMAIL] Sent {email_type} to {recipient_email} for {condo_name}")
        return True
        
    except Exception as e:
        logger.error(f"[BILLING-EMAIL] Failed to send {email_type}: {e}")
        return False


async def check_and_log_email_sent(
    condominium_id: str,
    email_type: str,
    today_str: str
) -> bool:
    """
    Check if an email of this type was already sent today.
    Returns True if already sent, False if not.
    """
    existing = await db.billing_email_log.find_one({
        "condominium_id": condominium_id,
        "email_type": email_type,
        "sent_date": today_str
    })
    return existing is not None


async def log_email_sent(
    condominium_id: str,
    email_type: str,
    recipient_email: str,
    today_str: str
):
    """Log that an email was sent to prevent duplicates."""
    await db.billing_email_log.insert_one({
        "condominium_id": condominium_id,
        "email_type": email_type,
        "recipient_email": recipient_email,
        "sent_date": today_str,
        "created_at": datetime.now(timezone.utc).isoformat()
    })


async def log_billing_engine_event(
    event_type: str,
    condominium_id: str,
    data: dict,
    triggered_by: str = None,
    previous_state: dict = None,
    new_state: dict = None
):
    """
    BILLING ENGINE: Log billing event to billing_events collection.
    Creates audit trail for all billing-related changes.
    """
    event = {
        "id": str(uuid.uuid4()),
        "condominium_id": condominium_id,
        "event_type": event_type,
        "data": data,
        "previous_state": previous_state,
        "new_state": new_state,
        "triggered_by": triggered_by,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.billing_events.insert_one(event)
    logger.info(f"[BILLING-EVENT] {event_type} | condo={condominium_id[:8]}... | data={data}")
    
    return event


async def update_condominium_billing_status(
    condominium_id: str,
    new_status: str,
    triggered_by: str = None,
    additional_data: dict = None
):
    """
    Update condominium billing status with audit logging.
    """
    # Get current state
    condo = await db.condominiums.find_one({"id": condominium_id}, {"_id": 0})
    if not condo:
        return None
    
    previous_status = condo.get("billing_status", "unknown")
    
    # Update condominium
    update_data = {
        "billing_status": new_status,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    if additional_data:
        update_data.update(additional_data)
    
    await db.condominiums.update_one(
        {"id": condominium_id},
        {"$set": update_data}
    )
    
    # Log event
    await log_billing_engine_event(
        event_type="status_changed",
        condominium_id=condominium_id,
        data={"from": previous_status, "to": new_status, **(additional_data or {})},
        triggered_by=triggered_by,
        previous_state={"billing_status": previous_status},
        new_state={"billing_status": new_status}
    )
    
    return {"previous_status": previous_status, "new_status": new_status}
