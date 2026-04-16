"""GENTURIX - Admin User Management Router (Auto-extracted from server.py)"""
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

# ==================== ADMIN USER MANAGEMENT ====================

@router.post("/admin/users")
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

@router.get("/admin/users")
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

