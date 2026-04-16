"""GENTURIX - Documentos Module Router (Auto-extracted from server.py)"""
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

# ==================== DOCUMENTOS ====================
# Document management module with Emergent Object Storage
# Collection: documents

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
DOC_APP_NAME = "genturix"
_doc_storage_key = None
LOCAL_UPLOAD_DIR = Path("/app/backend/uploads")
_use_local_storage = not EMERGENT_LLM_KEY

if _use_local_storage:
    LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    logger.warning("[DOCUMENTOS] EMERGENT_LLM_KEY not configured — using fallback local storage at /app/backend/uploads")
else:
    logger.info("[DOCUMENTOS] Emergent Object Storage configured")

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "txt", "csv", "jpg", "jpeg", "png", "gif", "webp",
}
BLOCKED_EXTENSIONS = {
    "exe", "bat", "cmd", "sh", "ps1", "msi", "dll", "com", "scr",
    "vbs", "js", "jar", "py", "php", "asp", "aspx", "jsp", "cgi",
}
ALLOWED_MIME_PREFIXES = {
    "application/pdf", "application/msword", "application/vnd.", "text/",
    "image/jpeg", "image/png", "image/gif", "image/webp",
}
MIME_MAP = {
    "pdf": "application/pdf", "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "txt": "text/plain", "csv": "text/csv",
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp",
}


def _sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and injection."""
    import unicodedata
    name = unicodedata.normalize("NFKD", filename)
    name = re.sub(r'[^\w\s\-.]', '', name)
    name = re.sub(r'\.{2,}', '.', name)
    name = name.strip('. ')
    return name[:200] if name else "unnamed"


def _validate_upload_mime(content_type: str, ext: str) -> bool:
    """Validate that the MIME type is allowed and consistent with extension."""
    if not content_type:
        return False
    # Block dangerous MIME types
    dangerous = ["application/x-executable", "application/x-msdos-program", "application/x-sh"]
    if content_type in dangerous:
        return False
    # Check against allowed prefixes
    return any(content_type.startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES)


async def _init_doc_storage(force_refresh: bool = False):
    global _doc_storage_key
    if _use_local_storage:
        return "__local__"
    if _doc_storage_key and not force_refresh:
        return _doc_storage_key
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=503, detail="Storage no configurado: falta EMERGENT_LLM_KEY")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{STORAGE_URL}/init",
                json={"emergent_key": EMERGENT_LLM_KEY},
            )
            resp.raise_for_status()
            _doc_storage_key = resp.json()["storage_key"]
            logger.info("[DOCUMENTOS] Storage initialized successfully")
            return _doc_storage_key
    except httpx.HTTPStatusError as e:
        logger.error(f"[DOCUMENTOS] Storage init failed: HTTP {e.response.status_code} - {e.response.text[:200]}")
        _doc_storage_key = None
        raise HTTPException(status_code=503, detail=f"Error inicializando storage: HTTP {e.response.status_code}")
    except Exception as e:
        logger.error(f"[DOCUMENTOS] Storage init error: {type(e).__name__}: {e}")
        _doc_storage_key = None
        raise HTTPException(status_code=503, detail=f"Error de conexion con storage: {type(e).__name__}")


async def _put_object(path: str, data: bytes, content_type: str) -> dict:
    if _use_local_storage:
        local_path = LOCAL_UPLOAD_DIR / path.replace("/", "_")
        local_path.write_bytes(data)
        logger.info(f"[DOCUMENTOS] Local storage: saved {len(data)} bytes to {local_path.name}")
        return {"path": f"local://{local_path.name}"}
    key = await _init_doc_storage()
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.put(
                f"{STORAGE_URL}/objects/{path}",
                headers={"X-Storage-Key": key, "Content-Type": content_type},
                content=data,
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"[DOCUMENTOS] Upload to storage failed: HTTP {e.response.status_code} - {e.response.text[:200]}")
        if e.response.status_code in (401, 403):
            logger.warning("[DOCUMENTOS] Storage key possibly expired, retrying with fresh key...")
            key = await _init_doc_storage(force_refresh=True)
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.put(
                    f"{STORAGE_URL}/objects/{path}",
                    headers={"X-Storage-Key": key, "Content-Type": content_type},
                    content=data,
                )
                resp.raise_for_status()
                return resp.json()
        raise
    except Exception as e:
        logger.error(f"[DOCUMENTOS] Upload error: {type(e).__name__}: {e}")
        raise


async def _get_object(path: str):
    if path.startswith("local://"):
        local_name = path[len("local://"):]
        local_path = LOCAL_UPLOAD_DIR / local_name
        if not local_path.exists():
            raise HTTPException(status_code=404, detail="Archivo no encontrado en storage local")
        data = local_path.read_bytes()
        ext = local_name.rsplit(".", 1)[-1].lower() if "." in local_name else ""
        ct = MIME_MAP.get(ext, "application/octet-stream")
        return data, ct
    key = await _init_doc_storage()
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(
                f"{STORAGE_URL}/objects/{path}",
                headers={"X-Storage-Key": key},
            )
            resp.raise_for_status()
            return resp.content, resp.headers.get("Content-Type", "application/octet-stream")
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (401, 403):
            key = await _init_doc_storage(force_refresh=True)
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.get(
                    f"{STORAGE_URL}/objects/{path}",
                    headers={"X-Storage-Key": key},
                )
                resp.raise_for_status()
                return resp.content, resp.headers.get("Content-Type", "application/octet-stream")
        raise


class DocCategory(str, Enum):
    REGLAMENTO = "reglamento"
    ACTA = "acta"
    COMUNICADO = "comunicado"
    CONTRATO = "contrato"
    MANUAL = "manual"
    FINANCIERO = "financiero"
    OTRO = "otro"

class DocVisibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    ROLES = "roles"

class DocUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[DocCategory] = None
    visibility: Optional[DocVisibility] = None
    allowed_roles: Optional[List[str]] = None


@router.post("/documentos")
@limiter.limit(RATE_LIMIT_PUSH)
async def upload_document(
    request: Request,
    file: UploadFile = FastAPIFile(...),
    name: str = Query(..., min_length=1, max_length=200),
    description: str = Query("", max_length=2000),
    category: str = Query("otro"),
    visibility: str = Query("public"),
    allowed_roles: str = Query(""),
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Admin uploads a document to object storage."""
    condo_id = current_user.get("condominium_id")
    if not condo_id and "SuperAdmin" not in current_user.get("roles", []):
        raise HTTPException(status_code=400, detail="No condominium associated")

    logger.info(f"[DOCUMENTOS] UPLOAD START | file={file.filename} | content_type={file.content_type} | user={current_user.get('email')} | condo={condo_id}")

    # Validate extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Tipo de archivo no permitido: .{ext}")
    if ext in BLOCKED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Tipo de archivo bloqueado por seguridad")

    # Read and validate size
    data = await file.read()
    logger.info(f"[DOCUMENTOS] File read | size={len(data)} bytes | ext={ext}")
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Archivo excede 20 MB")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    content_type = file.content_type or MIME_MAP.get(ext, "application/octet-stream")
    logger.info(f"[DOCUMENTOS] MIME validation | content_type={content_type}")

    # MIME type validation
    if not _validate_upload_mime(content_type, ext):
        raise HTTPException(status_code=400, detail=f"Tipo MIME no permitido: {content_type}")

    # Sanitize filename
    safe_filename = _sanitize_filename(file.filename)
    storage_path = f"{DOC_APP_NAME}/docs/{condo_id}/{uuid.uuid4()}.{ext}"

    try:
        result = await _put_object(storage_path, data, content_type)
        logger.info(f"[DOCUMENTOS] UPLOAD SUCCESS | path={storage_path}")
    except HTTPException:
        raise  # Re-raise HTTP exceptions from storage init
    except httpx.HTTPStatusError as e:
        logger.error(f"[DOCUMENTOS] Storage HTTP error: {e.response.status_code} - {e.response.text[:200]}")
        raise HTTPException(status_code=502, detail=f"Error al subir al storage: HTTP {e.response.status_code}")
    except httpx.TimeoutException:
        logger.error(f"[DOCUMENTOS] Storage timeout uploading {len(data)} bytes")
        raise HTTPException(status_code=504, detail="Timeout al subir archivo. Intenta con un archivo más pequeño.")
    except Exception as e:
        logger.error(f"[DOCUMENTOS] Upload failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al subir archivo: {type(e).__name__}")

    roles_list = [r.strip() for r in allowed_roles.split(",") if r.strip()] if allowed_roles else []
    now = datetime.now(timezone.utc).isoformat()

    doc = {
        "id": str(uuid.uuid4()),
        "condominium_id": condo_id,
        "name": sanitize_text(name),
        "description": sanitize_text(description) if description else "",
        "category": category,
        "file_url": result.get("path", storage_path),
        "file_name": safe_filename,
        "file_size": len(data),
        "file_type": content_type,
        "visibility": visibility,
        "allowed_roles": roles_list,
        "uploaded_by": current_user["id"],
        "uploaded_by_name": current_user.get("full_name", "Admin"),
        "version": 1,
        "parent_doc_id": None,
        "is_deleted": False,
        "created_at": now,
        "updated_at": now,
    }

    await db.documents.insert_one(doc)

    await log_audit_event(
        AuditEventType.SECURITY_ALERT,
        current_user["id"],
        "documentos",
        {"action": "document_uploaded", "doc_id": doc["id"], "name": doc["name"], "category": category},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id,
        user_email=current_user.get("email"),
    )

    safe = {k: v for k, v in doc.items() if k not in ("_id", "file_url")}
    return safe


@router.get("/documentos")
async def get_documents(
    category: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user=Depends(get_current_user),
):
    """List documents visible to the current user."""
    condo_id = current_user.get("condominium_id")
    roles = current_user.get("roles", [])
    is_admin = any(r in roles for r in ["Administrador", "Supervisor", "SuperAdmin"])

    query = {"condominium_id": condo_id, "is_deleted": False}

    if not is_admin:
        query["$or"] = [
            {"visibility": "public"},
            {"visibility": "roles", "allowed_roles": {"$in": roles}},
        ]

    if category:
        query["category"] = category

    skip = (max(1, page) - 1) * page_size
    total = await db.documents.count_documents(query)
    items = (
        await db.documents.find(query, {"_id": 0, "file_url": 0})
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


@router.get("/documentos/{doc_id}")
async def get_document_detail(
    doc_id: str,
    current_user=Depends(get_current_user),
):
    """Get document metadata (no file_url exposed)."""
    condo_id = current_user.get("condominium_id")
    doc = await db.documents.find_one(
        {"id": doc_id, "condominium_id": condo_id, "is_deleted": False},
        {"_id": 0, "file_url": 0},
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    roles = current_user.get("roles", [])
    is_admin = any(r in roles for r in ["Administrador", "Supervisor", "SuperAdmin"])

    if not is_admin:
        if doc["visibility"] == "private":
            raise HTTPException(status_code=403, detail="No tienes acceso")
        if doc["visibility"] == "roles" and not any(r in doc.get("allowed_roles", []) for r in roles):
            raise HTTPException(status_code=403, detail="No tienes acceso")

    return doc


@router.get("/documentos/{doc_id}/download")
async def download_document(
    doc_id: str,
    current_user=Depends(get_current_user),
):
    """Download a document. Streams from object storage."""
    condo_id = current_user.get("condominium_id")
    doc = await db.documents.find_one(
        {"id": doc_id, "condominium_id": condo_id, "is_deleted": False},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    roles = current_user.get("roles", [])
    is_admin = any(r in roles for r in ["Administrador", "Supervisor", "SuperAdmin"])

    if not is_admin:
        if doc["visibility"] == "private":
            raise HTTPException(status_code=403, detail="No tienes acceso")
        if doc["visibility"] == "roles" and not any(r in doc.get("allowed_roles", []) for r in roles):
            raise HTTPException(status_code=403, detail="No tienes acceso")

    try:
        data, ct = await _get_object(doc["file_url"])
    except Exception as e:
        logger.error(f"[DOCUMENTOS] Download failed: {e}")
        raise HTTPException(status_code=500, detail="Error al descargar archivo")

    return Response(
        content=data,
        media_type=doc.get("file_type", ct),
        headers={
            "Content-Disposition": f'attachment; filename="{doc["file_name"]}"',
        },
    )


@router.patch("/documentos/{doc_id}")
async def update_document(
    doc_id: str,
    payload: DocUpdate,
    request: Request,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Admin updates document metadata."""
    condo_id = current_user.get("condominium_id")
    doc = await db.documents.find_one(
        {"id": doc_id, "condominium_id": condo_id, "is_deleted": False},
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    update_fields = {}
    if payload.name is not None:
        update_fields["name"] = sanitize_text(payload.name)
    if payload.description is not None:
        update_fields["description"] = sanitize_text(payload.description)
    if payload.category is not None:
        update_fields["category"] = payload.category.value
    if payload.visibility is not None:
        update_fields["visibility"] = payload.visibility.value
    if payload.allowed_roles is not None:
        update_fields["allowed_roles"] = payload.allowed_roles

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.documents.update_one({"id": doc_id}, {"$set": update_fields})

    await log_audit_event(
        AuditEventType.SECURITY_ALERT,
        current_user["id"],
        "documentos",
        {"action": "document_updated", "doc_id": doc_id, "fields": list(update_fields.keys())},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id,
        user_email=current_user.get("email"),
    )

    updated = await db.documents.find_one({"id": doc_id}, {"_id": 0, "file_url": 0})
    return updated


@router.delete("/documentos/{doc_id}")
async def delete_document(
    doc_id: str,
    request: Request,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Soft-delete a document."""
    condo_id = current_user.get("condominium_id")
    result = await db.documents.update_one(
        {"id": doc_id, "condominium_id": condo_id, "is_deleted": False},
        {"$set": {"is_deleted": True, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    await log_audit_event(
        AuditEventType.SECURITY_ALERT,
        current_user["id"],
        "documentos",
        {"action": "document_deleted", "doc_id": doc_id},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id,
        user_email=current_user.get("email"),
    )

    return {"message": "Documento eliminado"}



