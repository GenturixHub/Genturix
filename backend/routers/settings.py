"""GENTURIX - Condominium Settings Router (Auto-extracted from server.py)"""
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

# ==================== CONDOMINIUM SETTINGS MODULE ====================
# Admin settings for their condominium - rules for reservations, visits, notifications

@router.get("/admin/condominium-settings")
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

@router.put("/admin/condominium-settings")
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

@router.get("/condominium-settings/public")
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



# ==================== SYSTEM STATUS (Maintenance Mode) ====================

@router.get("/system/status")
async def get_system_status():
    """Public endpoint — returns maintenance flag. No auth required."""
    doc = await db.system_config.find_one({"key": "maintenance"}, {"_id": 0})
    return {"maintenance": doc.get("enabled", False) if doc else False}


@router.put("/system/maintenance")
async def toggle_maintenance(
    request: Request,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Admin toggles maintenance mode on/off."""
    body = await request.json()
    enabled = bool(body.get("enabled", False))

    await db.system_config.update_one(
        {"key": "maintenance"},
        {"$set": {"enabled": enabled, "updated_by": current_user["id"], "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "system",
        {"action": "maintenance_toggled", "enabled": enabled},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=current_user.get("condominium_id"),
        user_email=current_user.get("email"),
    )

    return {"maintenance": enabled}
