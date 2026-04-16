"""GENTURIX - Invitations + Access Requests Router (Auto-extracted from server.py)"""
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

@router.post("/invitations")
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

@router.get("/invitations")
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

@router.delete("/invitations/{invitation_id}")
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

@router.get("/invitations/{token}/info")
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

@router.post("/invitations/{token}/request")
@limiter.limit(RATE_LIMIT_SENSITIVE)
async def submit_access_request(
    request: Request,
    token: str,
    request_data: AccessRequestCreate
):
    """Submit an access request using an invitation link - rate limited (no auth required)"""
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
    
    # Sanitize user inputs
    sanitized_name = sanitize_text(request_data.full_name.strip())
    sanitized_apt = sanitize_text(request_data.apartment_number.strip())
    sanitized_tower = sanitize_text(request_data.tower_block) if request_data.tower_block else None
    sanitized_notes = sanitize_text(request_data.notes) if request_data.notes else None
    
    # Create access request
    access_request = {
        "id": str(uuid.uuid4()),
        "invitation_id": invitation["id"],
        "condominium_id": invitation["condominium_id"],
        "condominium_name": invitation["condominium_name"],
        "full_name": sanitized_name,
        "email": request_data.email.lower().strip(),
        "phone": request_data.phone,
        "apartment_number": sanitized_apt,
        "tower_block": sanitized_tower,
        "resident_type": request_data.resident_type,
        "notes": sanitized_notes,
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

@router.get("/invitations/{token}/request-status")
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

@router.get("/access-requests")
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

@router.get("/access-requests/count")
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

@router.post("/access-requests/{request_id}/action")
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
            request.headers.get("user-agent", "unknown"),
            condominium_id=condo_id,
            user_email=current_user.get("email")
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
            request.headers.get("user-agent", "unknown"),
            condominium_id=condo_id,
            user_email=current_user.get("email")
        )
        
        return {
            "message": "Solicitud rechazada.",
            "email_sent": email_result.get("status") == "success"
        }
    
    else:
        raise HTTPException(status_code=400, detail="Acción no válida. Use 'approve' o 'reject'")

