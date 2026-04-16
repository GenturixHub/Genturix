"""GENTURIX - Profile Module Router (Auto-extracted from server.py)"""
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


# ==================== PROFILE MODULE ====================
@router.get("/profile", response_model=ProfileResponse)
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

@router.get("/profile/{user_id}", response_model=PublicProfileResponse)
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

@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(profile_data: ProfileUpdate, current_user = Depends(get_current_user)):
    """Update current user's profile (name, phone, photo, description)"""
    update_fields = {}
    
    if profile_data.full_name is not None:
        update_fields["full_name"] = profile_data.full_name
    if profile_data.phone is not None:
        update_fields["phone"] = profile_data.phone
    if profile_data.profile_photo is not None:
        update_fields["profile_photo"] = profile_data.profile_photo
        print(f"[FLOW] profile_image_updated | user_id={current_user['id']} photo_url={profile_data.profile_photo[:50]}...")
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

@router.patch("/profile/language")
async def update_language(language_data: LanguageUpdate, current_user = Depends(get_current_user)):
    """Update current user's language preference"""
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {
            "language": language_data.language,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    await log_audit_event(
        AuditEventType.USER_UPDATED, current_user["id"], "profile",
        {"action": "language_changed", "language": language_data.language},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=current_user.get("condominium_id"),
        user_email=current_user.get("email"),
    )
    return {"message": "Language updated successfully", "language": language_data.language}


class DeleteAccountRequest(BaseModel):
    """Request model for account deletion"""
    password: str
    reason: Optional[str] = None


@router.delete("/users/delete-account")
async def delete_own_account(
    delete_request: DeleteAccountRequest,
    current_user = Depends(get_current_user)
):
    """
    Delete the current user's own account.
    
    Flow:
    1. Validate password
    2. Check user can be deleted (not SuperAdmin, not sole Admin)
    3. Delete user
    4. Seat is automatically released (counted dynamically)
    5. Clean up related data
    
    Returns:
        Success message on deletion
    """
    user_id = current_user["id"]
    user_email = current_user["email"]
    user_roles = current_user.get("roles", [])
    condominium_id = current_user.get("condominium_id")
    
    # SuperAdmin cannot delete their own account through this endpoint
    if "SuperAdmin" in user_roles:
        raise HTTPException(
            status_code=403, 
            detail="SuperAdmin no puede eliminar su cuenta por este medio"
        )
    
    # Verify password
    user_with_password = await db.users.find_one(
        {"id": user_id}, 
        {"_id": 0, "hashed_password": 1}
    )
    
    if not user_with_password or not verify_password(delete_request.password, user_with_password["hashed_password"]):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    
    # If user is an Admin, check they're not the last admin
    if "Administrador" in user_roles and condominium_id:
        admin_count = await db.users.count_documents({
            "condominium_id": condominium_id,
            "roles": "Administrador",
            "is_active": True,
            "id": {"$ne": user_id}  # Exclude current user
        })
        
        if admin_count == 0:
            raise HTTPException(
                status_code=400, 
                detail="No puedes eliminar tu cuenta porque eres el único administrador del condominio"
            )
    
    # Log the deletion attempt
    logger.info(f"[ACCOUNT-DELETE] User {user_email} (roles: {user_roles}) requesting account deletion")
    
    try:
        # Clean up related data first
        
        # 1. Remove push subscriptions
        await db.push_subscriptions.delete_many({"user_id": user_id})
        
        # 2. Remove password reset tokens
        await db.password_reset_tokens.delete_many({"user_id": user_id})
        
        # 3. Cancel active visitor authorizations
        await db.visitor_authorizations.update_many(
            {"created_by": user_id, "status": "active"},
            {"$set": {"status": "cancelled", "cancelled_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        # 4. Cancel future reservations (not past ones for audit trail)
        now = datetime.now(timezone.utc).isoformat()
        await db.reservations.update_many(
            {"user_id": user_id, "start_time": {"$gt": now}, "status": {"$in": ["confirmed", "pending"]}},
            {"$set": {"status": "cancelled", "cancelled_at": now, "cancelled_reason": "account_deleted"}}
        )
        
        # 5. Delete the user
        result = await db.users.delete_one({"id": user_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=500, detail="Error al eliminar la cuenta")
        
        # Log successful deletion
        logger.info(f"[ACCOUNT-DELETE] Successfully deleted user {user_email}")
        
        # Create audit log
        if condominium_id:
            await db.audit_logs.insert_one({
                "id": str(uuid.uuid4()),
                "condominium_id": condominium_id,
                "action": "user_self_deleted",
                "actor_id": user_id,
                "actor_email": user_email,
                "actor_roles": user_roles,
                "details": {
                    "reason": delete_request.reason or "No reason provided",
                    "deleted_at": datetime.now(timezone.utc).isoformat()
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ip_address": None
            })
        
        # Note: Seat count is calculated dynamically by count_active_users()
        # No need to manually decrement - the deleted user simply won't be counted
        
        return {
            "success": True,
            "message": "Tu cuenta ha sido eliminada exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ACCOUNT-DELETE] Error deleting user {user_email}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al eliminar la cuenta")


@router.get("/profile/directory/condominium")
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

