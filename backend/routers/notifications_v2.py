"""GENTURIX - Notifications V2 Router (Auto-extracted from server.py)"""
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

# ==================== NOTIFICATIONS V2 ====================
# New notification system with broadcasts, preferences, and pagination
# Coexists with existing /api/notifications endpoints
# All endpoints under /api/notifications/v2/*

class NotificationV2Type(str, Enum):
    BROADCAST = "broadcast"
    SYSTEM = "system"
    ALERT = "alert"
    INFO = "info"

class NotificationV2Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class NotificationV2Create(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=2000)
    notification_type: NotificationV2Type = NotificationV2Type.BROADCAST
    priority: NotificationV2Priority = NotificationV2Priority.NORMAL
    target_roles: Optional[List[str]] = None  # None = all roles

class PreferencesUpdate(BaseModel):
    broadcasts_enabled: Optional[bool] = None
    alerts_enabled: Optional[bool] = None
    system_enabled: Optional[bool] = None
    email_notifications: Optional[bool] = None

DEFAULT_PREFERENCES = {
    "broadcasts_enabled": True,
    "alerts_enabled": True,
    "system_enabled": True,
    "email_notifications": False,
}

@router.get("/notifications/v2")
async def get_notifications_v2(
    page: int = 1,
    page_size: int = 20,
    unread_only: bool = False,
    notification_type: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    """List notifications for current user with pagination and filters."""
    user_id = current_user["id"]
    condo_id = current_user.get("condominium_id")
    roles = current_user.get("roles", [])

    query = {
        "$or": [
            {"target_user_id": user_id},
            {
                "is_broadcast": True,
                "condominium_id": condo_id,
                "$or": [
                    {"target_roles": None},
                    {"target_roles": []},
                    {"target_roles": {"$in": roles}},
                ],
            },
        ]
    }

    if unread_only:
        query["read_by"] = {"$nin": [user_id]}

    if notification_type:
        query["notification_type"] = notification_type

    skip = (max(1, page) - 1) * page_size
    total = await db.notifications_v2.count_documents(query)
    items = (
        await db.notifications_v2.find(query, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(min(page_size, 50))
        .to_list(min(page_size, 50))
    )

    # Enrich with read status per user
    for item in items:
        item["read"] = user_id in item.get("read_by", [])
        item.pop("read_by", None)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, -(-total // page_size)),
    }


@router.get("/notifications/v2/unread-count")
async def get_notifications_v2_unread_count(
    current_user=Depends(get_current_user),
):
    """Get unread count for the v2 notification system."""
    user_id = current_user["id"]
    condo_id = current_user.get("condominium_id")
    roles = current_user.get("roles", [])

    query = {
        "read_by": {"$nin": [user_id]},
        "$or": [
            {"target_user_id": user_id},
            {
                "is_broadcast": True,
                "condominium_id": condo_id,
                "$or": [
                    {"target_roles": None},
                    {"target_roles": []},
                    {"target_roles": {"$in": roles}},
                ],
            },
        ],
    }
    count = await db.notifications_v2.count_documents(query)
    return {"count": count}


@router.post("/notifications/v2/broadcast")
async def create_broadcast_notification(
    payload: NotificationV2Create,
    request: Request,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Admin creates a broadcast notification for their condominium."""
    condo_id = current_user.get("condominium_id")
    if not condo_id and "SuperAdmin" not in current_user.get("roles", []):
        raise HTTPException(status_code=400, detail="No condominium associated")

    sanitized_title = sanitize_text(payload.title)
    sanitized_message = sanitize_text(payload.message)

    doc = {
        "id": str(uuid.uuid4()),
        "title": sanitized_title,
        "message": sanitized_message,
        "notification_type": payload.notification_type.value,
        "priority": payload.priority.value,
        "is_broadcast": True,
        "condominium_id": condo_id,
        "target_roles": payload.target_roles,
        "target_user_id": None,
        "created_by": current_user["id"],
        "created_by_name": current_user.get("full_name", "Admin"),
        "read_by": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.notifications_v2.insert_one(doc)

    # Store broadcast record
    broadcast_doc = {
        "id": doc["id"],
        "notification_id": doc["id"],
        "condominium_id": condo_id,
        "title": sanitized_title,
        "message": sanitized_message,
        "target_roles": payload.target_roles,
        "created_by": current_user["id"],
        "created_by_name": current_user.get("full_name", "Admin"),
        "created_at": doc["created_at"],
    }
    await db.notification_broadcasts.insert_one(broadcast_doc)

    # Audit log
    await log_audit_event(
        AuditEventType.SECURITY_ALERT,
        current_user["id"],
        "notifications_v2",
        {
            "action": "broadcast_created",
            "title": sanitized_title,
            "target_roles": payload.target_roles,
            "priority": payload.priority.value,
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id,
        user_email=current_user.get("email"),
    )

    # Send push notification to targeted users
    if condo_id:
        try:
            await send_targeted_push_notification(
                condominium_id=condo_id,
                title=sanitized_title,
                body=sanitized_message[:100],
                target_roles=payload.target_roles if payload.target_roles else None,
                data={
                    "type": "broadcast_v2",
                    "notification_id": doc["id"],
                    "url": "/admin/notifications",
                },
                tag=f"broadcast-{doc['id'][:8]}",
            )
        except Exception as e:
            logger.warning(f"[NOTIF-V2] Push broadcast failed: {e}")

    safe_doc = {k: v for k, v in doc.items() if k != "_id"}
    safe_doc.pop("read_by", None)
    safe_doc["read"] = False
    return safe_doc


@router.patch("/notifications/v2/read/{notification_id}")
async def mark_notification_v2_read(
    notification_id: str,
    current_user=Depends(get_current_user),
):
    """Mark a v2 notification as read for the current user."""
    user_id = current_user["id"]

    result = await db.notifications_v2.update_one(
        {"id": notification_id},
        {"$addToSet": {"read_by": user_id}},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")

    return {"message": "Notificación marcada como leída"}


@router.patch("/notifications/v2/read-all")
async def mark_all_notifications_v2_read(
    current_user=Depends(get_current_user),
):
    """Mark all v2 notifications as read for the current user."""
    user_id = current_user["id"]
    condo_id = current_user.get("condominium_id")
    roles = current_user.get("roles", [])

    query = {
        "read_by": {"$nin": [user_id]},
        "$or": [
            {"target_user_id": user_id},
            {
                "is_broadcast": True,
                "condominium_id": condo_id,
                "$or": [
                    {"target_roles": None},
                    {"target_roles": []},
                    {"target_roles": {"$in": roles}},
                ],
            },
        ],
    }

    result = await db.notifications_v2.update_many(
        query,
        {"$addToSet": {"read_by": user_id}},
    )

    return {
        "message": f"{result.modified_count} notificaciones marcadas como leídas",
        "count": result.modified_count,
    }


@router.get("/notifications/v2/broadcasts")
async def get_broadcast_history(
    page: int = 1,
    page_size: int = 20,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Admin gets broadcast history for their condominium."""
    condo_id = current_user.get("condominium_id")
    query = {}
    if condo_id:
        query["condominium_id"] = condo_id

    skip = (max(1, page) - 1) * page_size
    total = await db.notification_broadcasts.count_documents(query)
    items = (
        await db.notification_broadcasts.find(query, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(min(page_size, 50))
        .to_list(min(page_size, 50))
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, -(-total // page_size)),
    }


@router.get("/notifications/v2/preferences")
async def get_notification_preferences(
    current_user=Depends(get_current_user),
):
    """Get notification preferences for the current user."""
    user_id = current_user["id"]

    prefs = await db.notification_preferences.find_one(
        {"user_id": user_id}, {"_id": 0}
    )

    if not prefs:
        return {
            "user_id": user_id,
            **DEFAULT_PREFERENCES,
        }

    return prefs


@router.patch("/notifications/v2/preferences")
async def update_notification_preferences(
    payload: PreferencesUpdate,
    request: Request,
    current_user=Depends(get_current_user),
):
    """Update notification preferences for the current user."""
    user_id = current_user["id"]

    update_fields = {
        k: v for k, v in payload.model_dump().items() if v is not None
    }

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db.notification_preferences.update_one(
        {"user_id": user_id},
        {
            "$set": update_fields,
            "$setOnInsert": {
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **{k: v for k, v in DEFAULT_PREFERENCES.items() if k not in update_fields},
            },
        },
        upsert=True,
    )

    await log_audit_event(
        AuditEventType.USER_UPDATED,
        user_id,
        "notifications_v2",
        {"action": "preferences_updated", "fields": list(update_fields.keys())},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=current_user.get("condominium_id"),
        user_email=current_user.get("email"),
    )

    prefs = await db.notification_preferences.find_one(
        {"user_id": user_id}, {"_id": 0}
    )
    return prefs



