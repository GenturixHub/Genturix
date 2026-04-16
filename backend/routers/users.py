"""GENTURIX - Users Management + Password Reset Router (Auto-extracted from server.py)"""
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

@router.get("/users")
async def get_users(current_user = Depends(require_role("Administrador"))):
    """Get users - scoped by condominium"""
    query = {}
    if "SuperAdmin" not in current_user.get("roles", []):
        condo_id = current_user.get("condominium_id")
        if condo_id:
            query["condominium_id"] = condo_id
    users = await db.users.find(query, {"_id": 0, "hashed_password": 0}).to_list(100)
    return users

@router.put("/users/{user_id}/roles")
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
    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "users",
        {"action": "roles_updated", "target_user_id": user_id, "new_roles": role_data.roles},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=current_user.get("condominium_id"),
        user_email=current_user.get("email"),
    )
    return {"message": "Roles updated"}

# ==================== SEAT MANAGEMENT MODELS ====================
# NOTE: UserStatusUpdateV2 model moved to modules/users/models.py
# NOTE: SeatUsageResponse and SeatReductionValidation are imported from modules.billing.models

# ==================== SEAT MANAGEMENT ENDPOINTS ====================

@router.get("/admin/seat-usage")
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

@router.post("/admin/validate-seat-reduction")
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

@router.patch("/admin/users/{user_id}/status-v2")
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

@router.delete("/admin/users/{user_id}")
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

@router.patch("/admin/users/{user_id}/status")
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
@router.post("/admin/users/{user_id}/reset-password")
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

@router.post("/auth/reset-password-complete")
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

@router.get("/auth/verify-reset-token")
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

@router.put("/users/{user_id}/status")
async def update_user_status_legacy(user_id: str, is_active: bool, current_user = Depends(require_role("Administrador"))):
    """Legacy endpoint - use PATCH /admin/users/{user_id}/status instead"""
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_active": is_active, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "users",
        {"action": "status_updated_legacy", "target_user_id": user_id, "is_active": is_active},
        "unknown", "unknown",
        condominium_id=current_user.get("condominium_id"),
        user_email=current_user.get("email"),
    )
    return {"message": "Status updated"}

