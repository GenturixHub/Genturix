"""GENTURIX - Casos / Incidencias Router (Auto-extracted from server.py)"""
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

# ==================== CASOS / INCIDENCIAS ====================
# Case/incident management module for residents and admins
# Collections: casos, caso_comments

class CasoCategory(str, Enum):
    MANTENIMIENTO = "mantenimiento"
    SEGURIDAD = "seguridad"
    RUIDO = "ruido"
    LIMPIEZA = "limpieza"
    INFRAESTRUCTURA = "infraestructura"
    CONVIVENCIA = "convivencia"
    OTRO = "otro"

class CasoPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class CasoStatus(str, Enum):
    OPEN = "open"
    REVIEW = "review"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
    REJECTED = "rejected"

class CasoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)
    category: CasoCategory
    priority: CasoPriority = CasoPriority.MEDIUM
    visibility: Optional[str] = Field("private", pattern=r"^(private|community)$")

class CasoUpdate(BaseModel):
    status: Optional[CasoStatus] = None
    priority: Optional[CasoPriority] = None
    assigned_to: Optional[str] = None

class CasoCommentCreate(BaseModel):
    comment: str = Field(..., min_length=1, max_length=2000)
    is_internal: bool = False


@router.post("/casos")
@limiter.limit(RATE_LIMIT_PUSH)
async def create_caso(
    payload: CasoCreate,
    request: Request,
    current_user=Depends(get_current_user),
):
    """Resident or admin creates a new case/incident."""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="No condominium associated")

    caso_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    doc = {
        "id": caso_id,
        "condominium_id": condo_id,
        "created_by": current_user["id"],
        "created_by_name": current_user.get("full_name", "Usuario"),
        "title": sanitize_text(payload.title),
        "description": sanitize_text(payload.description),
        "category": payload.category.value,
        "priority": payload.priority.value,
        "visibility": payload.visibility or "private",
        "status": CasoStatus.OPEN.value,
        "attachments": [],
        "assigned_to": None,
        "created_at": now,
        "updated_at": now,
        "closed_at": None,
    }

    await db.casos.insert_one(doc)

    await log_audit_event(
        AuditEventType.SECURITY_ALERT,
        current_user["id"],
        "casos",
        {"action": "caso_created", "caso_id": caso_id, "title": doc["title"], "category": doc["category"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id,
        user_email=current_user.get("email"),
    )

    # Notify admins via notifications_v2
    try:
        notif_doc = {
            "id": str(uuid.uuid4()),
            "title": f"Nuevo caso: {doc['title']}",
            "message": f"{doc['created_by_name']} reportó: {doc['description'][:100]}",
            "notification_type": "alert",
            "priority": doc["priority"],
            "is_broadcast": True,
            "condominium_id": condo_id,
            "target_roles": ["Administrador", "Supervisor"],
            "target_user_id": None,
            "created_by": current_user["id"],
            "created_by_name": doc["created_by_name"],
            "read_by": [],
            "created_at": now,
        }
        await db.notifications_v2.insert_one(notif_doc)
    except Exception as e:
        logger.warning(f"[CASOS] Notification creation failed: {e}")

    # Push notification to admins
    try:
        await send_targeted_push_notification(
            condominium_id=condo_id,
            title=f"Nuevo caso: {doc['title']}",
            body=f"{doc['created_by_name']} - {doc['category']}",
            target_roles=["Administrador", "Supervisor"],
            data={"type": "caso_created", "caso_id": caso_id, "url": "/admin/casos"},
            tag=f"caso-{caso_id[:8]}",
        )
    except Exception as e:
        logger.warning(f"[CASOS] Push notification failed: {e}")

    safe_doc = {k: v for k, v in doc.items() if k != "_id"}
    return safe_doc


@router.get("/casos")
async def get_casos(
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user=Depends(get_current_user),
):
    """Get cases. Admin sees all in condo, resident sees own only."""
    condo_id = current_user.get("condominium_id")
    roles = current_user.get("roles", [])
    is_admin = any(r in roles for r in ["Administrador", "Supervisor", "SuperAdmin"])

    query = {"condominium_id": condo_id}

    if not is_admin:
        # Residents and Guards see their own cases + all community cases
        query["$or"] = [
            {"created_by": current_user["id"]},
            {"visibility": "community"},
        ]

    if status:
        query["status"] = status
    if category:
        query["category"] = category
    if priority:
        query["priority"] = priority

    skip = (max(1, page) - 1) * page_size
    total = await db.casos.count_documents(query)
    items = (
        await db.casos.find(query, {"_id": 0})
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


@router.get("/casos/stats")
async def get_casos_stats(
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPERVISOR, RoleEnum.SUPER_ADMIN)),
):
    """Get case statistics for admin dashboard."""
    condo_id = current_user.get("condominium_id")
    base = {"condominium_id": condo_id}

    total = await db.casos.count_documents(base)
    open_count = await db.casos.count_documents({**base, "status": "open"})
    in_progress = await db.casos.count_documents({**base, "status": {"$in": ["review", "in_progress"]}})
    closed = await db.casos.count_documents({**base, "status": "closed"})
    urgent = await db.casos.count_documents({**base, "priority": "urgent", "status": {"$ne": "closed"}})

    return {
        "total": total,
        "open": open_count,
        "in_progress": in_progress,
        "closed": closed,
        "urgent": urgent,
    }



@router.get("/casos/{caso_id}")
async def get_caso_detail(
    caso_id: str,
    current_user=Depends(get_current_user),
):
    """Get case detail with comments."""
    condo_id = current_user.get("condominium_id")
    roles = current_user.get("roles", [])
    is_admin = any(r in roles for r in ["Administrador", "Supervisor", "SuperAdmin"])

    caso = await db.casos.find_one(
        {"id": caso_id, "condominium_id": condo_id}, {"_id": 0}
    )
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    if not is_admin and caso["created_by"] != current_user["id"]:
        # Allow access to community cases for all residents in same condo
        if caso.get("visibility") != "community":
            raise HTTPException(status_code=403, detail="No tienes permiso para ver este caso")

    # Fetch comments
    comment_query = {"caso_id": caso_id}
    if not is_admin:
        comment_query["is_internal"] = False

    comments = (
        await db.caso_comments.find(comment_query, {"_id": 0})
        .sort("created_at", 1)
        .to_list(200)
    )

    caso["comments"] = comments
    return caso


@router.patch("/casos/{caso_id}")
async def update_caso(
    caso_id: str,
    payload: CasoUpdate,
    request: Request,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPERVISOR, RoleEnum.SUPER_ADMIN)),
):
    """Admin updates case status, priority, or assignment."""
    condo_id = current_user.get("condominium_id")

    caso = await db.casos.find_one(
        {"id": caso_id, "condominium_id": condo_id}, {"_id": 0}
    )
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    update_fields = {}
    if payload.status is not None:
        update_fields["status"] = payload.status.value
        if payload.status == CasoStatus.CLOSED:
            update_fields["closed_at"] = datetime.now(timezone.utc).isoformat()
    if payload.priority is not None:
        update_fields["priority"] = payload.priority.value
    if payload.assigned_to is not None:
        update_fields["assigned_to"] = payload.assigned_to

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db.casos.update_one({"id": caso_id}, {"$set": update_fields})

    await log_audit_event(
        AuditEventType.SECURITY_ALERT,
        current_user["id"],
        "casos",
        {"action": "caso_updated", "caso_id": caso_id, "fields": list(update_fields.keys())},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id,
        user_email=current_user.get("email"),
    )

    # Notify the case creator about status change
    if payload.status is not None and caso["created_by"] != current_user["id"]:
        try:
            status_labels = {
                "open": "Abierto", "review": "En revisión",
                "in_progress": "En progreso", "closed": "Cerrado", "rejected": "Rechazado",
            }
            notif_doc = {
                "id": str(uuid.uuid4()),
                "title": f"Caso actualizado: {caso['title']}",
                "message": f"Estado cambiado a: {status_labels.get(payload.status.value, payload.status.value)}",
                "notification_type": "info",
                "priority": "normal",
                "is_broadcast": False,
                "condominium_id": condo_id,
                "target_roles": None,
                "target_user_id": caso["created_by"],
                "created_by": current_user["id"],
                "created_by_name": current_user.get("full_name", "Admin"),
                "read_by": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.notifications_v2.insert_one(notif_doc)
        except Exception as e:
            logger.warning(f"[CASOS] Status notification failed: {e}")

    updated = await db.casos.find_one({"id": caso_id}, {"_id": 0})
    return updated


@router.post("/casos/{caso_id}/comments")
async def add_caso_comment(
    caso_id: str,
    payload: CasoCommentCreate,
    request: Request,
    current_user=Depends(get_current_user),
):
    """Add a comment to a case."""
    condo_id = current_user.get("condominium_id")
    roles = current_user.get("roles", [])
    is_admin = any(r in roles for r in ["Administrador", "Supervisor", "SuperAdmin"])

    caso = await db.casos.find_one(
        {"id": caso_id, "condominium_id": condo_id}, {"_id": 0}
    )
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    if not is_admin and caso["created_by"] != current_user["id"]:
        # Allow comments on community cases for any resident/guard in same condo
        if caso.get("visibility") != "community":
            raise HTTPException(status_code=403, detail="No tienes permiso")

    # Only admins can make internal comments
    is_internal = payload.is_internal and is_admin

    comment_doc = {
        "id": str(uuid.uuid4()),
        "caso_id": caso_id,
        "author_id": current_user["id"],
        "author_name": current_user.get("full_name", "Usuario"),
        "author_role": roles[0] if roles else "Unknown",
        "comment": sanitize_text(payload.comment),
        "is_internal": is_internal,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.caso_comments.insert_one(comment_doc)

    # Update caso updated_at
    await db.casos.update_one(
        {"id": caso_id},
        {"$set": {"updated_at": comment_doc["created_at"]}},
    )

    await log_audit_event(
        AuditEventType.SECURITY_ALERT,
        current_user["id"],
        "casos",
        {"action": "comment_added", "caso_id": caso_id, "is_internal": is_internal},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id,
        user_email=current_user.get("email"),
    )

    # Notify the other party about the new comment
    notify_user_id = None
    if is_admin and caso["created_by"] != current_user["id"] and not is_internal:
        notify_user_id = caso["created_by"]
    elif not is_admin and caso.get("assigned_to"):
        notify_user_id = caso["assigned_to"]

    if notify_user_id:
        try:
            notif_doc = {
                "id": str(uuid.uuid4()),
                "title": f"Nuevo comentario en: {caso['title']}",
                "message": f"{comment_doc['author_name']}: {comment_doc['comment'][:100]}",
                "notification_type": "info",
                "priority": "normal",
                "is_broadcast": False,
                "condominium_id": condo_id,
                "target_roles": None,
                "target_user_id": notify_user_id,
                "created_by": current_user["id"],
                "created_by_name": comment_doc["author_name"],
                "read_by": [],
                "created_at": comment_doc["created_at"],
            }
            await db.notifications_v2.insert_one(notif_doc)
        except Exception as e:
            logger.warning(f"[CASOS] Comment notification failed: {e}")

    safe_doc = {k: v for k, v in comment_doc.items() if k != "_id"}
    return safe_doc


# ── Case Deletion (owner only) ──

@router.delete("/casos/{caso_id}")
async def delete_caso(
    caso_id: str,
    request: Request,
    current_user=Depends(get_current_user),
):
    """Delete a case. Only the creator can delete, and only if not closed."""
    condo_id = current_user.get("condominium_id")
    roles = current_user.get("roles", [])
    is_admin = any(r in roles for r in ["Administrador", "Supervisor", "SuperAdmin"])

    caso = await db.casos.find_one({"id": caso_id, "condominium_id": condo_id}, {"_id": 0})
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    # Only creator or admin can delete
    if not is_admin and caso["created_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Solo puedes eliminar tus propios casos")

    # Cannot delete closed cases (unless admin)
    if not is_admin and caso.get("status") == "closed":
        raise HTTPException(status_code=400, detail="No se puede eliminar un caso cerrado")

    await db.casos.delete_one({"id": caso_id})
    await db.caso_comments.delete_many({"caso_id": caso_id})

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "casos",
        {"action": "caso_deleted", "caso_id": caso_id, "title": caso.get("title", "")},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=current_user.get("email"),
    )

    return {"status": "ok", "deleted": caso_id}


# ── Case Attachments (photo upload) ──

CASO_MAX_ATTACHMENT = 5 * 1024 * 1024  # 5MB
CASO_ALLOWED_IMAGE = {"jpg", "jpeg", "png", "webp"}


@router.post("/casos/{caso_id}/attachments")
@limiter.limit(RATE_LIMIT_PUSH)
async def upload_caso_attachment(
    caso_id: str,
    file: UploadFile = FastAPIFile(...),
    request: Request = None,
    current_user=Depends(get_current_user),
):
    """Upload an image attachment to a case."""
    condo_id = current_user.get("condominium_id")
    roles = current_user.get("roles", [])
    is_admin = any(r in roles for r in ["Administrador", "Supervisor", "SuperAdmin"])

    caso = await db.casos.find_one({"id": caso_id, "condominium_id": condo_id}, {"_id": 0})
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    # Permission: creator, admin, or community case participant
    if not is_admin and caso["created_by"] != current_user["id"]:
        if caso.get("visibility") != "community":
            raise HTTPException(status_code=403, detail="No tienes permiso")

    # Validate file
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in CASO_ALLOWED_IMAGE:
        raise HTTPException(status_code=400, detail=f"Formato no permitido. Usa: {', '.join(CASO_ALLOWED_IMAGE)}")

    data = await file.read()
    if len(data) > CASO_MAX_ATTACHMENT:
        raise HTTPException(status_code=400, detail="Imagen excede 5 MB")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Archivo vacio")

    content_type = file.content_type or f"image/{ext}"
    storage_path = f"{DOC_APP_NAME}/casos/{condo_id}/{caso_id}/{uuid.uuid4()}.{ext}"

    try:
        result = await _put_object(storage_path, data, content_type)
        file_url = result.get("path") or result.get("url") or storage_path
        logger.info(f"[CASOS] Attachment uploaded: {storage_path}")
    except Exception as e:
        logger.error(f"[CASOS] Attachment upload failed: {e}")
        raise HTTPException(status_code=500, detail="Error al subir imagen")

    # Add to case attachments array
    await db.casos.update_one(
        {"id": caso_id},
        {
            "$push": {"attachments": file_url},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
        },
    )

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "casos",
        {"action": "attachment_uploaded", "caso_id": caso_id, "file": file_url},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=current_user.get("email"),
    )

    return {"status": "ok", "url": file_url}


# ── Guard status update on cases ──

class GuardCasoStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(in_progress|closed)$")


@router.patch("/casos/{caso_id}/guard-update")
async def guard_update_caso(
    caso_id: str,
    payload: GuardCasoStatusUpdate,
    request: Request,
    current_user=Depends(require_role(RoleEnum.GUARDA)),
):
    """Guard updates case status (limited to in_progress or closed)."""
    condo_id = current_user.get("condominium_id")

    caso = await db.casos.find_one({"id": caso_id, "condominium_id": condo_id}, {"_id": 0})
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    # Guards can only update community cases
    if caso.get("visibility") != "community":
        raise HTTPException(status_code=403, detail="Solo puedes actualizar casos comunitarios")

    now = datetime.now(timezone.utc).isoformat()
    update = {"status": payload.status, "updated_at": now}
    if payload.status == "closed":
        update["closed_at"] = now

    await db.casos.update_one({"id": caso_id}, {"$set": update})

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "casos",
        {"action": "guard_status_update", "caso_id": caso_id, "new_status": payload.status},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=current_user.get("email"),
    )

    return {"status": "ok", "new_status": payload.status}


