"""GENTURIX - Visitors + Authorizations + Notifications Router (Auto-extracted from server.py)"""
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

# ==================== VISITOR PRE-REGISTRATION MODULE ====================
# Flow: Resident creates → Guard executes → Admin audits

@router.post("/visitors/pre-register")
async def create_visitor_preregistration(
    visitor: VisitorPreRegistration,
    request: Request,
    current_user = Depends(get_current_user)
):
    """Resident pre-registers a visitor - creates PENDING record"""
    visitor_id = str(uuid.uuid4())
    
    # Sanitize user inputs
    sanitized_name = sanitize_text(visitor.full_name)
    sanitized_notes = sanitize_text(visitor.notes) if visitor.notes else None
    sanitized_plate = sanitize_text(visitor.vehicle_plate) if visitor.vehicle_plate else None
    
    visitor_doc = {
        "id": visitor_id,
        "full_name": sanitized_name,
        "national_id": visitor.national_id,
        "vehicle_plate": sanitized_plate,
        "visit_type": visitor.visit_type.value,
        "expected_date": visitor.expected_date,
        "expected_time": visitor.expected_time,
        "notes": sanitized_notes,
        "status": VisitorStatusEnum.PENDING.value,
        "created_by": current_user["id"],
        "created_by_name": current_user.get("full_name", "Resident"),
        "condominium_id": current_user.get("condominium_id"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "entry_at": None,
        "entry_by": None,
        "entry_by_name": None,
        "exit_at": None,
        "exit_by": None,
        "exit_by_name": None
    }
    
    await db.visitors.insert_one(visitor_doc)
    
    # Notify guards about the new pre-registration using dynamic targeting
    condo_id = current_user.get("condominium_id")
    if condo_id:
        resident_name = current_user.get("full_name", "Un residente")
        resident_apt = current_user.get("apartment", "")
        apt_text = f" ({resident_apt})" if resident_apt else ""
        
        await send_targeted_push_notification(
            condominium_id=condo_id,
            title="📋 Nuevo visitante preregistrado",
            body=f"{visitor.full_name} para {resident_name}{apt_text}",
            target_roles=["Guarda"],
            data={
                "type": "visitor_preregistration",
                "visitor_id": visitor_id,
                "visitor_name": visitor.full_name,
                "resident_name": resident_name,
                "expected_date": visitor.expected_date,
                "expected_time": visitor.expected_time,
                "url": "/guard?tab=visits"
            },
            tag=f"preregister-{visitor_id[:8]}"
        )
    
    await log_audit_event(
        AuditEventType.ACCESS_GRANTED,
        current_user["id"],
        "visitors",
        {"action": "pre_registration", "visitor": visitor.full_name, "expected_date": visitor.expected_date, "resident": current_user.get("full_name")},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"id": visitor_id, "message": "Visitor pre-registered successfully", "status": "pending"}

@router.get("/visitors/my-visitors")
async def get_my_visitors(current_user = Depends(get_current_user)):
    """Get visitors pre-registered by the current resident"""
    visitors = await db.visitors.find(
        {"created_by": current_user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return visitors

@router.delete("/visitors/{visitor_id}")
async def cancel_visitor_preregistration(
    visitor_id: str,
    current_user = Depends(get_current_user)
):
    """Resident cancels their own visitor pre-registration"""
    result = await db.visitors.update_one(
        {"id": visitor_id, "created_by": current_user["id"], "status": "pending"},
        {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Visitor not found or cannot be cancelled")
    
    await log_audit_event(
        AuditEventType.USER_UPDATED, current_user["id"], "visitors",
        {"action": "visitor_cancelled", "visitor_id": visitor_id},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=current_user.get("condominium_id"),
        user_email=current_user.get("email"),
    )
    return {"message": "Visitor pre-registration cancelled"}

@router.get("/visitors/pending")
async def get_pending_visitors(
    search: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """Guard gets list of pending visitors expected today - SCOPED BY CONDOMINIUM"""
    # Use tenant_filter for automatic multi-tenant filtering
    query = tenant_filter(current_user, {"status": {"$in": ["pending", "entry_registered"]}})
    
    visitors = await db.visitors.find(query, {"_id": 0}).sort("expected_date", -1).to_list(100)
    
    # Filter by search term if provided
    if search:
        search_lower = search.lower()
        visitors = [
            v for v in visitors 
            if search_lower in v.get("full_name", "").lower() or
               search_lower in (v.get("vehicle_plate") or "").lower() or
               search_lower in (v.get("created_by_name") or "").lower() or
               search_lower in (v.get("national_id") or "").lower()
        ]
    
    return visitors

@router.post("/visitors/{visitor_id}/entry")
async def register_visitor_entry(
    visitor_id: str,
    entry_data: VisitorEntry,
    request: Request,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """Guard registers visitor ENTRY"""
    visitor = await db.visitors.find_one({"id": visitor_id})
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    
    if visitor.get("status") not in ["pending", "approved"]:
        raise HTTPException(status_code=400, detail=f"Cannot register entry. Current status: {visitor.get('status')}")
    
    entry_time = datetime.now(timezone.utc).isoformat()
    
    # Sanitize user input
    sanitized_notes = sanitize_text(entry_data.notes) if entry_data.notes else None
    
    await db.visitors.update_one(
        {"id": visitor_id},
        {"$set": {
            "status": "entry_registered",
            "entry_at": entry_time,
            "entry_by": current_user["id"],
            "entry_by_name": current_user.get("full_name", "Guard"),
            "entry_notes": sanitized_notes,
            "updated_at": entry_time
        }}
    )
    
    await log_audit_event(
        AuditEventType.ACCESS_GRANTED,
        current_user["id"],
        "visitors",
        {
            "action": "entry_registered",
            "visitor": visitor.get("full_name"),
            "visitor_id": visitor_id,
            "resident": visitor.get("created_by_name"),
            "guard": current_user.get("full_name")
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "Visitor entry registered", "entry_at": entry_time}

@router.post("/visitors/{visitor_id}/exit")
async def register_visitor_exit(
    visitor_id: str,
    exit_data: VisitorExit,
    request: Request,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """Guard registers visitor EXIT and saves to guard_history"""
    visitor = await db.visitors.find_one({"id": visitor_id})
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    
    if visitor.get("status") != "entry_registered":
        raise HTTPException(status_code=400, detail=f"Cannot register exit. Current status: {visitor.get('status')}")
    
    exit_time = datetime.now(timezone.utc).isoformat()
    
    await db.visitors.update_one(
        {"id": visitor_id},
        {"$set": {
            "status": "exit_registered",
            "exit_at": exit_time,
            "exit_by": current_user["id"],
            "exit_by_name": current_user.get("full_name", "Guard"),
            "exit_notes": exit_data.notes,
            "updated_at": exit_time
        }}
    )
    
    # Get guard info if resolver is a guard
    guard = await db.guards.find_one({"user_id": current_user["id"]})
    guard_id = guard["id"] if guard else None
    condo_id = visitor.get("condominium_id") or current_user.get("condominium_id")
    
    # Save to guard_history
    history_entry = {
        "id": str(uuid.uuid4()),
        "type": "visit_completed",
        "guard_id": guard_id,
        "guard_user_id": current_user["id"],
        "guard_name": current_user.get("full_name"),
        "condominium_id": condo_id,
        "visitor_id": visitor_id,
        "visitor_name": visitor.get("full_name"),
        "resident_name": visitor.get("created_by_name"),
        "entry_at": visitor.get("entry_at"),
        "exit_at": exit_time,
        "notes": exit_data.notes,
        "timestamp": exit_time
    }
    await db.guard_history.insert_one(history_entry)
    
    await log_audit_event(
        AuditEventType.ACCESS_DENIED,
        current_user["id"],
        "visitors",
        {
            "action": "exit_registered",
            "visitor": visitor.get("full_name"),
            "visitor_id": visitor_id,
            "resident": visitor.get("created_by_name"),
            "guard": current_user.get("full_name"),
            "duration_minutes": None  # Could calculate from entry_at
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "Visitor exit registered", "exit_at": exit_time}

@router.get("/visitors/all")
async def get_all_visitors(
    status: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """Admin/Guard gets visitor records for audit - SCOPED BY CONDOMINIUM"""
    # Use tenant_filter for automatic multi-tenant filtering
    extra = {"status": status} if status else None
    query = tenant_filter(current_user, extra)
    
    visitors = await db.visitors.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return visitors

# ==================== ADVANCED VISITOR AUTHORIZATION SYSTEM ====================
# Phase 3: Competitor-Level Feature
# Flow: Resident creates authorization → Guard validates & checks in → System notifies

def get_color_code_for_type(auth_type: str) -> str:
    """Get color code based on authorization type"""
    color_map = {
        "permanent": "green",
        "recurring": "blue",
        "temporary": "yellow",
        "extended": "purple"
    }
    return color_map.get(auth_type, "yellow")

def check_authorization_validity(authorization: dict, condominium_timezone: str = None) -> dict:
    """
    Check if an authorization is currently valid.
    Returns: {is_valid: bool, status: str, message: str}
    
    TIMEZONE FIX: Uses condominium timezone for day/time calculations.
    Falls back to UTC if no timezone provided.
    """
    # Get current time in condominium timezone (or UTC as fallback)
    if condominium_timezone:
        try:
            tz = ZoneInfo(condominium_timezone)
            now = datetime.now(tz)
        except Exception as e:
            logger.warning(f"[AUTH-VALIDITY] Invalid timezone '{condominium_timezone}', falling back to UTC: {e}")
            now = datetime.now(timezone.utc)
    else:
        now = datetime.now(timezone.utc)
    
    today_str = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    current_day_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][now.weekday()]
    
    auth_type = authorization.get("authorization_type", "temporary")
    
    # Check if authorization is active
    if not authorization.get("is_active", True):
        return {"is_valid": False, "status": "revoked", "message": "Autorización revocada"}
    
    # Permanent: Always valid
    if auth_type == "permanent":
        return {"is_valid": True, "status": "authorized", "message": "Autorización permanente"}
    
    # Check date range for temporary, extended
    valid_from = authorization.get("valid_from")
    valid_to = authorization.get("valid_to")
    
    if valid_from and today_str < valid_from:
        return {"is_valid": False, "status": "not_yet_valid", "message": f"Válido desde {valid_from}"}
    
    if valid_to and today_str > valid_to:
        return {"is_valid": False, "status": "expired", "message": f"Expiró el {valid_to}"}
    
    # Check allowed days for recurring
    if auth_type == "recurring":
        allowed_days = authorization.get("allowed_days", [])
        if allowed_days and current_day_es not in allowed_days:
            return {"is_valid": False, "status": "not_today", "message": f"No autorizado hoy ({current_day_es})"}
    
    # Check time windows for extended
    if auth_type == "extended":
        hours_from = authorization.get("allowed_hours_from")
        hours_to = authorization.get("allowed_hours_to")
        
        if hours_from and current_time < hours_from:
            return {"is_valid": False, "status": "too_early", "message": f"Válido desde las {hours_from}"}
        
        if hours_to and current_time > hours_to:
            return {"is_valid": False, "status": "too_late", "message": f"Válido hasta las {hours_to}"}
    
    return {"is_valid": True, "status": "authorized", "message": "Autorización válida"}

# ===================== RESIDENT AUTHORIZATION ENDPOINTS =====================

@router.post("/authorizations")
async def create_visitor_authorization(
    auth_data: VisitorAuthorizationCreate,
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    Resident creates a visitor authorization.
    Types: temporary (single/range), permanent (always), recurring (days), extended (range+hours)
    """
    auth_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Auto-assign color based on type
    color_code = get_color_code_for_type(auth_data.authorization_type.value)
    
    # Set defaults based on type
    valid_from = auth_data.valid_from
    valid_to = auth_data.valid_to
    
    if auth_data.authorization_type == AuthorizationTypeEnum.TEMPORARY and not valid_from:
        # Default to today if temporary and no date set
        valid_from = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        valid_to = valid_to or valid_from
    
    auth_doc = {
        "id": auth_id,
        "visitor_name": auth_data.visitor_name,
        "identification_number": auth_data.identification_number,
        "vehicle_plate": auth_data.vehicle_plate.upper() if auth_data.vehicle_plate else None,
        "authorization_type": auth_data.authorization_type.value,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "allowed_days": auth_data.allowed_days or [],
        "allowed_hours_from": auth_data.allowed_hours_from,
        "allowed_hours_to": auth_data.allowed_hours_to,
        "notes": auth_data.notes,
        "color_code": color_code,
        "is_active": True,
        "status": "pending",  # Status for tracking: pending -> used
        "created_by": current_user["id"],
        "created_by_name": current_user.get("full_name", "Residente"),
        "resident_apartment": current_user.get("role_data", {}).get("apartment_number", "N/A"),
        "condominium_id": current_user.get("condominium_id"),
        "created_at": now,
        "updated_at": now,
        "total_visits": 0,
        "last_visit": None,
        "checked_in_at": None,
        "checked_in_by": None,
        "checked_in_by_name": None,
        # Visitor type fields
        "visitor_type": auth_data.visitor_type or "visitor",
        "company": auth_data.company,
        "service_type": auth_data.service_type
    }
    
    await db.visitor_authorizations.insert_one(auth_doc)
    
    await log_audit_event(
        AuditEventType.AUTHORIZATION_CREATED,
        current_user["id"],
        "visitor_authorizations",
        {
            "authorization_id": auth_id,
            "visitor_name": auth_data.visitor_name,
            "type": auth_data.authorization_type.value,
            "resident": current_user.get("full_name")
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    # ========== NOTIFY GUARDS AND ADMINS ==========
    condo_id = current_user.get("condominium_id")
    if condo_id:
        resident_name = current_user.get("full_name", "Un residente")
        visitor_name = auth_data.visitor_name
        apartment = current_user.get("role_data", {}).get("apartment_number", "")
        
        # Create notification payload
        notification_payload = {
            "title": "📋 Nuevo visitante preregistrado",
            "body": f"{visitor_name} - autorizado por {resident_name}" + (f" ({apartment})" if apartment else ""),
            "icon": "/logo192.png",
            "badge": "/logo192.png",
            "tag": f"preregistration-{auth_id[:8]}",
            "data": {
                "type": "visitor_preregistration",
                "authorization_id": auth_id,
                "visitor_name": visitor_name,
                "resident_name": resident_name,
                "url": "/guard?tab=pending"
            }
        }
        
        # Create notification in DB for guards
        guard_users = await db.users.find(
            {"condominium_id": condo_id, "roles": {"$in": ["Guarda"]}, "is_active": True},
            {"_id": 0, "id": 1}
        ).to_list(None)
        
        for guard in guard_users:
            await db.guard_notifications.insert_one({
                "id": str(uuid.uuid4()),
                "type": "visitor_preregistration",
                "guard_user_id": guard["id"],
                "condominium_id": condo_id,
                "title": "Nuevo visitante preregistrado",
                "message": f"{visitor_name} ha sido autorizado por {resident_name}" + (f" - Apto {apartment}" if apartment else ""),
                "data": {
                    "authorization_id": auth_id,
                    "visitor_name": visitor_name,
                    "resident_name": resident_name
                },
                "read": False,
                "created_at": now
            })
        
        # Send push notifications to guards and admins
        try:
            await send_push_to_guards(condo_id, notification_payload)
            await send_push_to_admins(condo_id, notification_payload)
            logger.info(f"[PREREGISTRATION] Notifications sent for visitor {visitor_name}")
        except Exception as e:
            logger.warning(f"[PREREGISTRATION] Failed to send push notifications: {e}")
        
        # === SEND EMAIL TO GUARDS (fail-safe) ===
        try:
            print(f"[EMAIL TRIGGER] visitor_preregistration → notifying guards for visitor {visitor_name}")
            # Get condominium info
            condo_info = await db.condominiums.find_one(
                {"id": condo_id},
                {"_id": 0, "name": 1}
            )
            condo_name = condo_info.get("name", "Condominio") if condo_info else "Condominio"
            
            # Get guard users with email
            guard_users_with_email = await db.users.find(
                {"condominium_id": condo_id, "roles": {"$in": ["Guarda"]}, "is_active": True},
                {"_id": 0, "email": 1, "full_name": 1}
            ).to_list(20)
            
            print(f"[EMAIL DEBUG] Found {len(guard_users_with_email)} guards with email")
            
            for guard in guard_users_with_email:
                guard_email = guard.get("email")
                guard_name = guard.get("full_name", "Guardia")
                if guard_email:
                    try:
                        preregistration_html = get_visitor_preregistration_email_html(
                            guard_name=guard_name,
                            visitor_name=visitor_name,
                            resident_name=resident_name,
                            apartment=apartment or "N/A",
                            valid_from=auth_data.valid_from or "Hoy",
                            valid_to=auth_data.valid_to or "Sin límite",
                            condominium_name=condo_name
                        )
                        await send_email(
                            to=guard_email,
                            subject=f"📋 Visitante Preregistrado - {visitor_name}",
                            html=preregistration_html
                        )
                    except Exception as guard_email_error:
                        logger.warning(f"[EMAIL] Failed to send preregistration email to guard {guard_email}: {guard_email_error}")
        except Exception as email_error:
            logger.warning(f"[EMAIL] Failed to send preregistration emails: {email_error}")
            # Continue - don't break API flow
    
    # Return without _id
    auth_doc.pop("_id", None)
    return auth_doc

@router.get("/authorizations/my")
async def get_my_authorizations(
    status: Optional[str] = None,  # active, expired, all, used
    request: Request = None,
    current_user = Depends(get_current_user)
):
    """Resident gets their own visitor authorizations with usage status"""
    # CRITICAL: Enforce tenant isolation
    user_id = current_user["id"]
    condo_id = current_user.get("condominium_id")
    
    # P0 SECURITY: Require valid condominium_id
    if not condo_id:
        logger.warning(f"[SECURITY] authorizations/my blocked: user {user_id} has no condominium_id")
        raise HTTPException(status_code=403, detail="Usuario no asignado a un condominio")
    
    query = {
        "created_by": user_id,
        "condominium_id": condo_id  # Multi-tenant filter - REQUIRED
    }
    
    if status == "active":
        query["is_active"] = True
        query["status"] = {"$ne": "used"}  # Exclude used authorizations from active
    elif status == "expired":
        query["is_active"] = False
    elif status == "used":
        query["status"] = "used"
    elif status == "all":
        pass  # Return all including inactive
    else:
        # DEFAULT: Only return active (not deleted) authorizations
        query["is_active"] = True
    
    authorizations = await db.visitor_authorizations.find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # SECURITY LOG
    logger.info(f"[SECURITY] visit_query_scoped | endpoint=authorizations/my | user_id={user_id[:12]}... | condo_id={condo_id[:12]}... | status={status} | records_returned={len(authorizations)}")
    
    # Get condominium timezone for validity checks
    condo_timezone = None
    condo_id = current_user.get("condominium_id")
    if condo_id:
        condo = await db.condominiums.find_one({"id": condo_id}, {"timezone": 1})
        condo_timezone = condo.get("timezone") if condo else None
    
    # Enrich with validity status and usage info
    for auth in authorizations:
        validity = check_authorization_validity(auth, condo_timezone)
        auth["validity_status"] = validity["status"]
        auth["validity_message"] = validity["message"]
        auth["is_currently_valid"] = validity["is_valid"]
        
        # P0 FIX: Check if there's a visitor currently INSIDE using this authorization
        # This prevents residents from deleting authorizations while visitor is inside
        active_inside = await db.visitor_entries.find_one({
            "authorization_id": auth.get("id"),
            "status": "inside"
        }, {"_id": 0, "id": 1})
        auth["has_visitor_inside"] = active_inside is not None
        
        # Check if authorization has been used (has entry record)
        auth_type = auth.get("authorization_type")
        if auth_type in ["temporary", "extended"]:
            # For one-time use authorizations, check if already used
            entry_exists = await db.visitor_entries.find_one({"authorization_id": auth.get("id")})
            if entry_exists:
                auth["status"] = "used"
                auth["was_used"] = True
                auth["used_at"] = entry_exists.get("entry_at")
                auth["used_by_guard"] = entry_exists.get("entry_by_name") or entry_exists.get("guard_name")
            else:
                auth["was_used"] = False
        else:
            # For permanent/recurring, check last usage
            last_entry = await db.visitor_entries.find_one(
                {"authorization_id": auth.get("id")},
                sort=[("entry_at", -1)]
            )
            if last_entry:
                auth["last_used_at"] = last_entry.get("entry_at")
                auth["total_uses"] = await db.visitor_entries.count_documents({"authorization_id": auth.get("id")})
            else:
                auth["total_uses"] = 0
    
    return authorizations


# ===================== AUDIT & HISTORY (must be before {auth_id} routes) =====================

@router.get("/authorizations/history")
async def get_authorization_history(
    auth_id: Optional[str] = None,
    resident_id: Optional[str] = None,
    visitor_name: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """
    Get visitor entry/exit history for audit.
    Filterable by authorization, resident, visitor name, date range.
    """
    # Build extra filters
    extra = {}
    if auth_id:
        extra["authorization_id"] = auth_id
    if resident_id:
        extra["resident_id"] = resident_id
    if visitor_name:
        extra["visitor_name"] = {"$regex": visitor_name, "$options": "i"}
    
    # Date filtering
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = f"{date_from}T00:00:00"
        if date_to:
            date_query["$lte"] = f"{date_to}T23:59:59"
        if date_query:
            extra["entry_at"] = date_query
    
    # Use tenant_filter for multi-tenant scoping
    query = tenant_filter(current_user, extra if extra else None)
    
    entries = await db.visitor_entries.find(query, {"_id": 0}).sort("entry_at", -1).to_list(500)
    return entries

@router.get("/authorizations/stats")
async def get_authorization_stats(
    current_user = Depends(require_role("Administrador", "Supervisor"))
):
    """Get statistics about visitor authorizations and entries"""
    # Use tenant_filter for multi-tenant scoping
    query = tenant_filter(current_user)
    
    if not query and "SuperAdmin" not in current_user.get("roles", []):
        # No condominium assigned
        return {}
    
    # Count active authorizations by type
    auth_pipeline = [
        {"$match": {**query, "is_active": True}},
        {"$group": {"_id": "$authorization_type", "count": {"$sum": 1}}}
    ]
    auth_counts = await db.visitor_authorizations.aggregate(auth_pipeline).to_list(10)
    
    # Count entries today
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_entries = await db.visitor_entries.count_documents({
        **query,
        "entry_at": {"$gte": f"{today}T00:00:00"}
    })
    
    # Count visitors currently inside
    inside_count = await db.visitor_entries.count_documents({
        **query,
        "status": "inside"
    })
    
    # Total authorizations
    total_auths = await db.visitor_authorizations.count_documents({**query, "is_active": True})
    
    return {
        "total_active_authorizations": total_auths,
        "authorizations_by_type": {item["_id"]: item["count"] for item in auth_counts},
        "entries_today": today_entries,
        "visitors_inside": inside_count
    }

@router.get("/authorizations/{auth_id}")
async def get_authorization(
    auth_id: str,
    current_user = Depends(get_current_user)
):
    """Get a specific authorization by ID"""
    # Use get_tenant_resource for automatic 404/403 handling
    auth = await get_tenant_resource(db.visitor_authorizations, auth_id, current_user)
    
    # Get condominium timezone for validity check
    condo_timezone = None
    condo_id = current_user.get("condominium_id")
    if condo_id:
        condo = await db.condominiums.find_one({"id": condo_id}, {"timezone": 1})
        condo_timezone = condo.get("timezone") if condo else None
    
    validity = check_authorization_validity(auth, condo_timezone)
    auth["validity_status"] = validity["status"]
    auth["validity_message"] = validity["message"]
    auth["is_currently_valid"] = validity["is_valid"]
    
    return auth

@router.patch("/authorizations/{auth_id}")
async def update_authorization(
    auth_id: str,
    auth_data: VisitorAuthorizationUpdate,
    request: Request,
    current_user = Depends(get_current_user)
):
    """Resident updates their own authorization"""
    auth = await db.visitor_authorizations.find_one({"id": auth_id})
    if not auth:
        raise HTTPException(status_code=404, detail="Autorización no encontrada")
    
    # Only owner can update
    if auth.get("created_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Solo puedes modificar tus propias autorizaciones")
    
    update_fields = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if auth_data.visitor_name is not None:
        update_fields["visitor_name"] = auth_data.visitor_name
    if auth_data.identification_number is not None:
        update_fields["identification_number"] = auth_data.identification_number
    if auth_data.vehicle_plate is not None:
        update_fields["vehicle_plate"] = auth_data.vehicle_plate.upper() if auth_data.vehicle_plate else None
    if auth_data.authorization_type is not None:
        update_fields["authorization_type"] = auth_data.authorization_type.value
        update_fields["color_code"] = get_color_code_for_type(auth_data.authorization_type.value)
    if auth_data.valid_from is not None:
        update_fields["valid_from"] = auth_data.valid_from
    if auth_data.valid_to is not None:
        update_fields["valid_to"] = auth_data.valid_to
    if auth_data.allowed_days is not None:
        update_fields["allowed_days"] = auth_data.allowed_days
    if auth_data.allowed_hours_from is not None:
        update_fields["allowed_hours_from"] = auth_data.allowed_hours_from
    if auth_data.allowed_hours_to is not None:
        update_fields["allowed_hours_to"] = auth_data.allowed_hours_to
    if auth_data.notes is not None:
        update_fields["notes"] = auth_data.notes
    if auth_data.is_active is not None:
        update_fields["is_active"] = auth_data.is_active
    # Visitor type fields
    if auth_data.visitor_type is not None:
        update_fields["visitor_type"] = auth_data.visitor_type
    if auth_data.company is not None:
        update_fields["company"] = auth_data.company
    if auth_data.service_type is not None:
        update_fields["service_type"] = auth_data.service_type
    
    await db.visitor_authorizations.update_one(
        {"id": auth_id},
        {"$set": update_fields}
    )
    
    await log_audit_event(
        AuditEventType.AUTHORIZATION_UPDATED,
        current_user["id"],
        "visitor_authorizations",
        {"authorization_id": auth_id, "changes": list(update_fields.keys())},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    # Fetch and return updated
    updated = await db.visitor_authorizations.find_one({"id": auth_id}, {"_id": 0})
    return updated

@router.delete("/authorizations/{auth_id}")
async def deactivate_authorization(
    auth_id: str,
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    Resident deactivates (soft delete) their authorization.
    
    BUSINESS RULES:
    - Resident CAN delete when: status is PENDING or visitor has EXITED
    - Resident CANNOT delete when: visitor is currently INSIDE the condominium
    - This prevents losing track of who's inside
    """
    auth = await db.visitor_authorizations.find_one({"id": auth_id})
    if not auth:
        raise HTTPException(status_code=404, detail="Autorización no encontrada")
    
    # Only owner can deactivate
    if auth.get("created_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Solo puedes eliminar tus propias autorizaciones")
    
    # ==================== P0 FIX: PREVENT DELETION WHEN VISITOR IS INSIDE ====================
    # Check if this authorization has an active visitor entry (status = "inside")
    user_roles = current_user.get("roles", [])
    is_resident = "Residente" in user_roles and not any(r in user_roles for r in ["Administrador", "SuperAdmin", "Guarda", "Supervisor", "RRHH"])
    
    if is_resident:
        # Check for active visitor entries using this authorization
        active_entry = await db.visitor_entries.find_one({
            "authorization_id": auth_id,
            "status": "inside"
        }, {"_id": 0, "id": 1, "visitor_name": 1})
        
        if active_entry:
            raise HTTPException(
                status_code=403, 
                detail="No puedes eliminar esta autorización mientras la persona esté dentro del condominio. Contacta al guarda para registrar su salida primero."
            )
    # ==================== END P0 FIX ====================
    
    await db.visitor_authorizations.update_one(
        {"id": auth_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    await log_audit_event(
        AuditEventType.AUTHORIZATION_DEACTIVATED,
        current_user["id"],
        "visitor_authorizations",
        {"authorization_id": auth_id, "visitor_name": auth.get("visitor_name")},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "Autorización desactivada"}

# ===================== GUARD AUTHORIZATION ENDPOINTS =====================

@router.get("/guard/authorizations")
async def get_authorizations_for_guard(
    search: Optional[str] = None,
    include_used: bool = False,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """
    Guard gets list of active authorizations for validation.
    Supports search by visitor name, ID, or vehicle plate.
    By default, only returns PENDING authorizations (not yet used).
    """
    condo_id = current_user.get("condominium_id")
    
    query = {"is_active": True}
    
    # By default, only show pending authorizations (not used yet)
    if not include_used:
        query["status"] = {"$in": ["pending", None]}  # Include None for backwards compatibility
    
    if "SuperAdmin" not in current_user.get("roles", []):
        if condo_id:
            query["condominium_id"] = condo_id
        else:
            return []
    
    authorizations = await db.visitor_authorizations.find(query, {"_id": 0}).to_list(500)
    
    # ==================== FILTER OUT ALREADY CHECKED-IN (for temporary/extended) ====================
    # This handles legacy data where status wasn't set to 'used'
    # Check multiple indicators: checked_in_at, total_visits, or actual entry in visitor_entries
    filtered_authorizations = []
    
    for auth in authorizations:
        auth_type = auth.get("authorization_type", "temporary")
        auth_id = auth.get("id")
        
        # Only filter temporary and extended (permanent/recurring can be reused)
        if auth_type not in ["temporary", "extended"]:
            filtered_authorizations.append(auth)
            continue
        
        # For temporary/extended, ALWAYS check if there's an entry in visitor_entries
        # This is the most reliable indicator that the authorization was used
        entry_exists = await db.visitor_entries.find_one({"authorization_id": auth_id})
        
        # Also check other indicators
        checked_in_at = auth.get("checked_in_at")
        total_visits = auth.get("total_visits", 0)
        
        already_used = entry_exists or checked_in_at or total_visits > 0
        
        if already_used:
            # Fix legacy data: update status to 'used'
            result = await db.visitor_authorizations.update_one(
                {"id": auth_id, "status": {"$in": ["pending", None]}},
                {"$set": {"status": "used"}}
            )
            if result.modified_count > 0:
                logger.info(f"[guard/authorizations] Auto-fixed auth {auth_id[:8]} to status=used (entry_exists={bool(entry_exists)}, checked_in_at={bool(checked_in_at)}, visits={total_visits})")
            
            if not include_used:
                continue  # Skip from results
        
        filtered_authorizations.append(auth)
    
    authorizations = filtered_authorizations
    # ================================================================================================
    
    # Get condominium timezone for validity checks
    condo_timezone = None
    if condo_id:
        condo = await db.condominiums.find_one({"id": condo_id}, {"timezone": 1})
        condo_timezone = condo.get("timezone") if condo else None
    
    # Enrich with validity status
    for auth in authorizations:
        validity = check_authorization_validity(auth, condo_timezone)
        auth["validity_status"] = validity["status"]
        auth["validity_message"] = validity["message"]
        auth["is_currently_valid"] = validity["is_valid"]
        
        # PHASE 3: Add is_visitor_inside flag for frontend
        active_entry = await db.visitor_entries.find_one({
            "authorization_id": auth.get("id"),
            "status": "inside",
            "exit_at": None
        }, {"_id": 0, "id": 1, "entry_at": 1})
        auth["is_visitor_inside"] = active_entry is not None
        if active_entry:
            auth["active_entry_id"] = active_entry.get("id")
            auth["entry_at"] = active_entry.get("entry_at")
    
    # Filter by search if provided
    if search:
        search_lower = search.lower().strip()
        authorizations = [
            a for a in authorizations
            if search_lower in a.get("visitor_name", "").lower() or
               search_lower in (a.get("identification_number") or "").lower() or
               search_lower in (a.get("vehicle_plate") or "").lower() or
               search_lower in (a.get("created_by_name") or "").lower()
        ]
    
    # Sort: valid first, then by name
    authorizations.sort(key=lambda x: (not x.get("is_currently_valid", False), x.get("visitor_name", "").lower()))
    
    return authorizations

@router.post("/guard/checkin")
async def fast_checkin(
    checkin_data: FastCheckInRequest,
    request: Request,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """
    Guard registers a visitor check-in (entry).
    - If authorization_id provided: validates authorization and logs entry
    - If no authorization: creates manual entry record
    - For TEMPORARY authorizations: marks as "used" after check-in
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    entry_id = str(uuid.uuid4())
    condo_id = current_user.get("condominium_id")
    
    authorization = None
    resident_id = None
    resident_name = None
    resident_apartment = None
    visitor_name = checkin_data.visitor_name
    is_authorized = False
    auth_type = "manual"
    color_code = "gray"
    
    # ==================== PHASE 1: PREVENT DUPLICATE ENTRIES (AUTHORIZATION) ====================
    # Check if visitor with this authorization is already inside
    if checkin_data.authorization_id:
        existing_inside = await db.visitor_entries.find_one({
            "authorization_id": checkin_data.authorization_id,
            "status": "inside",
            "exit_at": None
        })
        if existing_inside:
            logger.warning(
                f"[check-in] BLOCKED - Visitor already inside with auth {checkin_data.authorization_id[:8]}"
            )
            raise HTTPException(
                status_code=400,
                detail="El visitante ya se encuentra dentro del condominio. Debe registrar su salida antes de un nuevo ingreso."
            )
    
    # ==================== PHASE 2: PREVENT DUPLICATE ENTRIES (MANUAL) ====================
    # For manual entries, check by visitor_name + condominium to prevent duplicates
    if checkin_data.visitor_name and not checkin_data.authorization_id:
        # Normalize visitor name for comparison
        normalized_name = checkin_data.visitor_name.strip().lower()
        
        # Check if same visitor name is already inside this condo (case-insensitive)
        # Use regex for case-insensitive match on visitor_name
        existing_manual = await db.visitor_entries.find_one({
            "condominium_id": condo_id,
            "status": "inside",
            "exit_at": None,
            "authorization_id": None,  # Only manual entries
            "visitor_name": {"$regex": f"^{re.escape(normalized_name)}$", "$options": "i"}
        })
        
        if existing_manual:
            logger.warning(
                f"[check-in] BLOCKED - Manual visitor '{checkin_data.visitor_name}' already inside condo {condo_id[:8]}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe un visitante con el nombre '{checkin_data.visitor_name}' dentro del condominio. Verifique si es la misma persona."
            )
    # ==========================================================================================
    
    # If authorization provided, validate it
    if checkin_data.authorization_id:
        authorization = await db.visitor_authorizations.find_one({
            "id": checkin_data.authorization_id,
            "condominium_id": condo_id
        })
        
        if not authorization:
            raise HTTPException(status_code=404, detail="Autorización no encontrada")
        
        # ==================== BLOCK REUSE OF TEMPORARY/EXTENDED AUTHORIZATIONS ====================
        auth_status = authorization.get("status", "pending")
        auth_type_value = authorization.get("authorization_type", "temporary")
        
        # For TEMPORARY and EXTENDED authorizations, check multiple indicators of usage
        if auth_type_value in ["temporary", "extended"]:
            # Check 1: Status is "used"
            if auth_status == "used":
                raise HTTPException(
                    status_code=409, 
                    detail="Esta autorización ya fue utilizada. No se puede usar nuevamente."
                )
            
            # Check 2: checked_in_at is set
            if authorization.get("checked_in_at"):
                # Fix the status and reject
                await db.visitor_authorizations.update_one(
                    {"id": checkin_data.authorization_id},
                    {"$set": {"status": "used"}}
                )
                raise HTTPException(
                    status_code=409, 
                    detail="Esta autorización ya tiene un registro de entrada. No se puede usar nuevamente."
                )
            
            # Check 3: There's already an entry in visitor_entries with this authorization_id
            existing_entry = await db.visitor_entries.find_one({"authorization_id": checkin_data.authorization_id})
            if existing_entry:
                # Fix the status and reject
                await db.visitor_authorizations.update_one(
                    {"id": checkin_data.authorization_id},
                    {"$set": {"status": "used"}}
                )
                logger.warning(f"[check-in] BLOCKED duplicate check-in for auth {checkin_data.authorization_id[:8]} - entry already exists")
                raise HTTPException(
                    status_code=409, 
                    detail="Ya existe un registro de entrada para esta autorización. No se permite duplicar."
                )
        # ==========================================================================================
        
        # Get condominium timezone for validity check
        condo_timezone = None
        condo = await db.condominiums.find_one({"id": condo_id}, {"timezone": 1})
        condo_timezone = condo.get("timezone") if condo else None
        
        validity = check_authorization_validity(authorization, condo_timezone)
        
        if not validity["is_valid"]:
            # Still allow entry but mark as unauthorized
            is_authorized = False
        else:
            is_authorized = True
        
        visitor_name = authorization.get("visitor_name")
        resident_id = authorization.get("created_by")
        resident_name = authorization.get("created_by_name")
        resident_apartment = authorization.get("resident_apartment")
        auth_type = auth_type_value
        color_code = authorization.get("color_code", "yellow")
    
    # Create entry record
    entry_doc = {
        "id": entry_id,
        "authorization_id": checkin_data.authorization_id,
        "visitor_name": visitor_name or "Visitante Manual",
        "identification_number": checkin_data.identification_number or (authorization.get("identification_number") if authorization else None),
        "vehicle_plate": (checkin_data.vehicle_plate or (authorization.get("vehicle_plate") if authorization else None) or "").upper() or None,
        "destination": checkin_data.destination or resident_apartment,
        "authorization_type": auth_type,
        "color_code": color_code,
        "is_authorized": is_authorized,
        "resident_id": resident_id,
        "resident_name": resident_name,
        "resident_apartment": resident_apartment,
        # New visitor type fields
        "visitor_type": checkin_data.visitor_type or "visitor",
        "company": checkin_data.company,
        "service_type": checkin_data.service_type,
        "authorized_by": checkin_data.authorized_by,
        "estimated_time": checkin_data.estimated_time,
        "entry_at": now_iso,
        "resident_name": resident_name,
        "resident_apartment": resident_apartment,
        "entry_at": now_iso,
        "entry_by": current_user["id"],
        "entry_by_name": current_user.get("full_name", "Guardia"),
        "entry_notes": checkin_data.notes,
        "exit_at": None,
        "exit_by": None,
        "exit_by_name": None,
        "exit_notes": None,
        "status": "inside",
        "condominium_id": condo_id,
        "created_at": now_iso
    }
    
    await db.visitor_entries.insert_one(entry_doc)
    
    # Update authorization stats and status
    if authorization:
        auth_type_value = authorization.get("authorization_type", "temporary")
        
        # DEBUG LOG
        logger.info(f"[check-in] Auth ID: {checkin_data.authorization_id[:8]}, Type: {auth_type_value}, Will mark as used: {auth_type_value in ['temporary', 'extended']}")
        
        update_data = {
            "$inc": {"total_visits": 1},
            "$set": {
                "last_visit": now_iso,
                "checked_in_at": now_iso,
                "checked_in_by": current_user["id"],
                "checked_in_by_name": current_user.get("full_name", "Guardia"),
                "last_entry_date": now.strftime("%Y-%m-%d")  # Track last entry date
            }
        }
        
        # For TEMPORARY and EXTENDED authorizations, mark as "used" after check-in
        # PERMANENT and RECURRING authorizations stay active (can be used multiple times)
        if auth_type_value in ["temporary", "extended"]:
            update_data["$set"]["status"] = "used"
            logger.info(f"[check-in] Setting status=used for auth {checkin_data.authorization_id[:8]}")
        
        result = await db.visitor_authorizations.update_one(
            {"id": checkin_data.authorization_id},
            update_data
        )
        logger.info(f"[check-in] Update result: matched={result.matched_count}, modified={result.modified_count}")
        
        # VERIFICATION: Check if update actually worked
        if auth_type_value in ["temporary", "extended"]:
            verification = await db.visitor_authorizations.find_one(
                {"id": checkin_data.authorization_id},
                {"_id": 0, "status": 1, "authorization_type": 1, "visitor_name": 1}
            )
            logger.info(f"[check-in] VERIFICATION after update: {verification}")
    
    # Create notification AND send push to resident
    if resident_id:
        await create_and_send_notification(
            user_id=resident_id,
            condominium_id=condo_id,
            notification_type="visitor_arrival",
            title="🚪 Tu visitante ha llegado",
            message=f"{visitor_name} ha ingresado al condominio",
            data={
                "entry_id": entry_id,
                "visitor_name": visitor_name,
                "entry_at": now_iso,
                "guard_name": current_user.get("full_name")
            },
            send_push=False,  # Disable old push, use targeted instead
            url="/resident?tab=history"
        )
        
        # PHASE 1: Send targeted push notification to resident owner
        await send_targeted_push_notification(
            condominium_id=condo_id,
            title="🚪 Tu visitante ha llegado",
            body=f"{visitor_name} ha ingresado al condominio",
            target_user_ids=[resident_id],
            exclude_user_ids=[current_user["id"]],
            data={
                "type": "visitor_arrival",
                "entry_id": entry_id,
                "visitor_name": visitor_name,
                "entry_at": now_iso,
                "guard_name": current_user.get("full_name"),
                "url": "/resident?tab=history"
            },
            tag=f"checkin-{entry_id[:8]}"
        )
        
        await log_audit_event(
            AuditEventType.VISITOR_ARRIVAL_NOTIFIED,
            current_user["id"],
            "visitor_notifications",
            {"resident_id": resident_id, "visitor_name": visitor_name},
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "unknown")
        )
    
    await log_audit_event(
        AuditEventType.VISITOR_CHECKIN,
        current_user["id"],
        "visitor_entries",
        {
            "entry_id": entry_id,
            "visitor_name": visitor_name,
            "is_authorized": is_authorized,
            "authorization_id": checkin_data.authorization_id
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id,
        user_email=current_user.get("email")
    )
    print(f"[FLOW] visitor_entry_registered | entry_id={entry_id} visitor={visitor_name} authorized={is_authorized} condo={condo_id[:8]}")
    
    entry_doc.pop("_id", None)
    return {
        "success": True,
        "entry": entry_doc,
        "is_authorized": is_authorized,
        "message": "Entrada registrada" if is_authorized else "Entrada registrada (sin autorización válida)",
        "authorization_marked_used": authorization is not None and authorization.get("authorization_type") in ["temporary", "extended"]
    }

@router.get("/guard/entries-today")
async def get_entries_today(
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """
    Get all visitor entries for today.
    Returns list of visitors who have checked in today, for guard reference.
    """
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        return []
    
    # Get start of today in UTC
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    
    entries = await db.visitor_entries.find(
        {
            "condominium_id": condo_id,
            "entry_at": {"$gte": today_start}
        },
        {"_id": 0}
    ).sort("entry_at", -1).to_list(100)
    
    return entries

@router.post("/guard/checkout/{entry_id}")
async def fast_checkout(
    entry_id: str,
    checkout_data: FastCheckOutRequest,
    request: Request,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """
    Guard registers a visitor check-out (exit).
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    condo_id = current_user.get("condominium_id")
    
    # Find entry
    entry = await db.visitor_entries.find_one({
        "id": entry_id,
        "status": "inside"
    })
    
    if not entry:
        raise HTTPException(status_code=404, detail="Registro de entrada no encontrado o ya salió")
    
    # Multi-tenant check
    if entry.get("condominium_id") != condo_id and "SuperAdmin" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="No tienes acceso a este registro")
    
    # Calculate duration
    entry_at = entry.get("entry_at")
    duration_minutes = None
    if entry_at:
        try:
            entry_time = datetime.fromisoformat(entry_at.replace('Z', '+00:00'))
            duration_minutes = int((now - entry_time).total_seconds() / 60)
        except ValueError:
            pass
    
    # Update entry
    await db.visitor_entries.update_one(
        {"id": entry_id},
        {"$set": {
            "exit_at": now_iso,
            "exit_by": current_user["id"],
            "exit_by_name": current_user.get("full_name", "Guardia"),
            "exit_notes": checkout_data.notes,
            "status": "completed",
            "duration_minutes": duration_minutes
        }}
    )
    
    # Create notification AND send push to resident (optional for exit)
    resident_id = entry.get("resident_id")
    if resident_id:
        # Format duration for display
        duration_text = ""
        if duration_minutes:
            hours = duration_minutes // 60
            mins = duration_minutes % 60
            if hours > 0:
                duration_text = f" (duración: {hours}h {mins}m)"
            else:
                duration_text = f" (duración: {mins} min)"
        
        await create_and_send_notification(
            user_id=resident_id,
            condominium_id=condo_id,
            notification_type="visitor_exit",
            title="👋 Tu visitante ha salido",
            message=f"{entry.get('visitor_name')} ha salido del condominio{duration_text}",
            data={
                "entry_id": entry_id,
                "visitor_name": entry.get("visitor_name"),
                "exit_at": now_iso,
                "duration_minutes": duration_minutes,
                "guard_name": current_user.get("full_name")
            },
            send_push=False,  # Disable old push, use targeted instead
            url="/resident?tab=history"
        )
        
        # PHASE 2: Send targeted push notification to resident owner
        await send_targeted_push_notification(
            condominium_id=condo_id,
            title="👋 Tu visitante ha salido",
            body=f"{entry.get('visitor_name')} ha salido del condominio{duration_text}",
            target_user_ids=[resident_id],
            exclude_user_ids=[current_user["id"]],
            data={
                "type": "visitor_exit",
                "entry_id": entry_id,
                "visitor_name": entry.get("visitor_name"),
                "exit_at": now_iso,
                "duration_minutes": duration_minutes,
                "guard_name": current_user.get("full_name"),
                "url": "/resident?tab=history"
            },
            tag=f"checkout-{entry_id[:8]}"
        )
        
        await log_audit_event(
            AuditEventType.VISITOR_EXIT_NOTIFIED,
            current_user["id"],
            "visitor_notifications",
            {"resident_id": resident_id, "visitor_name": entry.get("visitor_name")},
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "unknown")
        )
    
    # Save to guard_history for audit
    guard = await db.guards.find_one({"user_id": current_user["id"]})
    history_entry = {
        "id": str(uuid.uuid4()),
        "type": "visitor_checkout",
        "guard_id": guard["id"] if guard else None,
        "guard_user_id": current_user["id"],
        "guard_name": current_user.get("full_name"),
        "condominium_id": condo_id,
        "entry_id": entry_id,
        "visitor_name": entry.get("visitor_name"),
        "resident_name": entry.get("resident_name"),
        "entry_at": entry_at,
        "exit_at": now_iso,
        "duration_minutes": duration_minutes,
        "timestamp": now_iso
    }
    await db.guard_history.insert_one(history_entry)
    
    await log_audit_event(
        AuditEventType.VISITOR_CHECKOUT,
        current_user["id"],
        "visitor_entries",
        {
            "entry_id": entry_id,
            "visitor_name": entry.get("visitor_name"),
            "duration_minutes": duration_minutes
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "success": True,
        "message": "Salida registrada",
        "exit_at": now_iso,
        "duration_minutes": duration_minutes
    }

@router.get("/guard/visitors-inside")
async def get_visitors_inside(
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """Get all visitors currently inside the condominium"""
    condo_id = current_user.get("condominium_id")
    
    query = {"status": "inside"}
    if "SuperAdmin" not in current_user.get("roles", []):
        if condo_id:
            query["condominium_id"] = condo_id
        else:
            return []
    
    entries = await db.visitor_entries.find(query, {"_id": 0}).sort("entry_at", -1).to_list(200)
    return entries

@router.get("/guard/visits-summary")
async def get_visits_summary(
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """
    Get complete visits summary for Guard 'Visitas' tab (READ-ONLY view)
    Returns: pending authorizations, visitors inside, today's exits
    """
    condo_id = current_user.get("condominium_id")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    base_query = {}
    if "SuperAdmin" not in current_user.get("roles", []):
        if condo_id:
            base_query["condominium_id"] = condo_id
        else:
            return {"pending": [], "inside": [], "exits": []}
    
    # 1. Get pending authorizations for today (not yet used)
    pending_query = {
        **base_query,
        "is_active": True,
        "status": "pending"
    }
    pending_auths = await db.visitor_authorizations.find(pending_query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    # Get condominium timezone for validity checks
    condo_timezone = None
    if condo_id:
        condo = await db.condominiums.find_one({"id": condo_id}, {"timezone": 1})
        condo_timezone = condo.get("timezone") if condo else None
    
    # Filter and enrich pending authorizations with validity
    enriched_pending = []
    for auth in pending_auths:
        validity = check_authorization_validity(auth, condo_timezone)
        if validity.get("is_valid"):
            auth["validity_status"] = validity["status"]
            auth["validity_message"] = validity["message"]
            auth["is_currently_valid"] = True
            enriched_pending.append(auth)
    
    # 2. Get visitors currently inside
    inside_query = {
        **base_query,
        "status": "inside"
    }
    inside_entries = await db.visitor_entries.find(inside_query, {"_id": 0}).sort("entry_at", -1).to_list(200)
    
    # 3. Get today's exits (completed visits)
    exits_query = {
        **base_query,
        "status": {"$in": ["exited", "completed"]},  # Support both status values
        "exit_at": {"$gte": f"{today}T00:00:00"}
    }
    today_exits = await db.visitor_entries.find(exits_query, {"_id": 0}).sort("exit_at", -1).to_list(100)
    
    return {
        "pending": enriched_pending,
        "inside": inside_entries,
        "exits": today_exits
    }

# ===================== RESIDENT NOTIFICATIONS =====================

@router.get("/resident/visitor-notifications")
async def get_visitor_notifications(
    unread_only: bool = False,
    current_user = Depends(get_current_user)
):
    """Resident gets their visitor arrival/exit notifications"""
    query = {
        "user_id": current_user["id"],
        "type": {"$in": ["visitor_arrival", "visitor_exit"]}
    }
    
    if unread_only:
        query["read"] = False
    
    notifications = await db.resident_notifications.find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    return notifications

@router.put("/resident/visitor-notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user = Depends(get_current_user)
):
    """Mark a notification as read"""
    result = await db.resident_notifications.update_one(
        {"id": notification_id, "user_id": current_user["id"]},
        {"$set": {"read": True}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    
    return {"message": "Notificación marcada como leída"}

@router.put("/resident/visitor-notifications/read-all")
async def mark_all_notifications_read(
    current_user = Depends(get_current_user)
):
    """Mark all visitor notifications as read"""
    result = await db.resident_notifications.update_many(
        {
            "user_id": current_user["id"],
            "type": {"$in": ["visitor_arrival", "visitor_exit"]},
            "read": False
        },
        {"$set": {"read": True}}
    )
    
    return {"message": f"{result.modified_count} notificaciones marcadas como leídas", "count": result.modified_count}


@router.get("/resident/visitor-notifications/unread-count")
async def get_resident_unread_notification_count(
    current_user = Depends(get_current_user)
):
    """Get count of unread visitor notifications for resident"""
    count = await db.resident_notifications.count_documents({
        "user_id": current_user["id"],
        "type": {"$in": ["visitor_arrival", "visitor_exit"]},
        "read": False
    })
    
    return {"count": count}


# ============================================
# RESIDENT VISIT HISTORY (Advanced Module)
# ============================================

@router.get("/resident/visit-history")
async def get_resident_visit_history(
    filter_period: Optional[str] = None,  # today, 7days, 30days, custom
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    visitor_type: Optional[str] = None,  # visitor, delivery, maintenance, etc.
    status: Optional[str] = None,  # inside, completed
    search: Optional[str] = None,  # Search by name, document, plate
    page: int = 1,
    page_size: int = 20,
    request: Request = None,
    current_user = Depends(get_current_user)
):
    """
    Advanced visit history for residents.
    Returns paginated list of visitor entries related to the resident's house.
    Enforces tenant isolation (validates condominium_id + resident_id).
    """
    user_id = current_user["id"]
    condo_id = current_user.get("condominium_id")
    
    # P0 SECURITY: Require valid condominium_id
    if not condo_id:
        logger.warning(f"[SECURITY] resident/visit-history blocked: user {user_id} has no condominium_id")
        raise HTTPException(status_code=403, detail="Usuario no asignado a un condominio")
    
    # Base query: Only visits related to this resident's authorizations
    # Find all authorization IDs created by this resident
    resident_auth_ids = await db.visitor_authorizations.distinct(
        "id",
        {"created_by": user_id, "condominium_id": condo_id}
    )
    
    # Also include legacy visitors registered by this resident
    legacy_visitor_ids = await db.visitors.distinct(
        "id",
        {"created_by": user_id, "condominium_id": condo_id}
    )
    
    # P0 FIX: Build query with proper handling of empty arrays
    # If no authorizations exist, we should ONLY match by resident_id, not return all records
    or_conditions = []
    
    if resident_auth_ids:
        or_conditions.append({"authorization_id": {"$in": resident_auth_ids}})
    
    if legacy_visitor_ids:
        or_conditions.append({"visitor_id": {"$in": legacy_visitor_ids}})
    
    # Always include direct resident_id match
    or_conditions.append({"resident_id": user_id})
    
    # Build query with MANDATORY condominium_id filter
    query = {
        "condominium_id": condo_id,  # REQUIRED - never query without this
        "$or": or_conditions
    }
    
    # Date filtering
    now = datetime.now(timezone.utc)
    if filter_period == "today":
        today_str = now.strftime("%Y-%m-%d")
        query["entry_at"] = {"$gte": f"{today_str}T00:00:00"}
    elif filter_period == "7days":
        seven_days_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        query["entry_at"] = {"$gte": f"{seven_days_ago}T00:00:00"}
    elif filter_period == "30days":
        thirty_days_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        query["entry_at"] = {"$gte": f"{thirty_days_ago}T00:00:00"}
    elif filter_period == "custom" and (date_from or date_to):
        date_query = {}
        if date_from:
            date_query["$gte"] = f"{date_from}T00:00:00"
        if date_to:
            date_query["$lte"] = f"{date_to}T23:59:59"
        if date_query:
            query["entry_at"] = date_query
    
    # Visitor type filter
    if visitor_type:
        query["visitor_type"] = visitor_type
    
    # Status filter
    if status:
        query["status"] = status
    
    # Search filter (name, document, plate)
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        query["$and"] = query.get("$and", []) + [{
            "$or": [
                {"visitor_name": search_regex},
                {"document_number": search_regex},
                {"vehicle_plate": search_regex}
            ]
        }]
    
    # Get total count for pagination
    total_count = await db.visitor_entries.count_documents(query)
    
    # Calculate pagination
    skip = (page - 1) * page_size
    total_pages = (total_count + page_size - 1) // page_size
    
    # Fetch entries with pagination
    entries = await db.visitor_entries.find(
        query, 
        {"_id": 0}
    ).sort("entry_at", -1).skip(skip).limit(page_size).to_list(page_size)
    
    # Enrich entries with additional data
    enriched_entries = []
    for entry in entries:
        # Calculate duration if both entry and exit exist
        duration_minutes = None
        if entry.get("entry_at") and entry.get("exit_at"):
            try:
                entry_time = datetime.fromisoformat(entry["entry_at"].replace("Z", "+00:00"))
                exit_time = datetime.fromisoformat(entry["exit_at"].replace("Z", "+00:00"))
                duration_minutes = int((exit_time - entry_time).total_seconds() / 60)
            except Exception as time_err:
                logger.debug(f"[VISITS] Could not calculate duration: {time_err}")
        
        # Get authorization details if available
        auth_details = None
        if entry.get("authorization_id"):
            auth = await db.visitor_authorizations.find_one(
                {"id": entry["authorization_id"]},
                {"_id": 0, "authorization_type": 1, "visitor_type": 1}
            )
            if auth:
                auth_details = auth
        
        enriched_entry = {
            **entry,
            "duration_minutes": duration_minutes,
            "authorization_details": auth_details,
            # Determine display type
            "display_type": entry.get("visitor_type") or (auth_details.get("visitor_type") if auth_details else "visitor")
        }
        enriched_entries.append(enriched_entry)
    
    # Get count of visitors currently inside (for badge)
    inside_count = await db.visitor_entries.count_documents({
        **{k: v for k, v in query.items() if k not in ["entry_at", "status"]},
        "status": "inside"
    })
    
    result = {
        "entries": enriched_entries,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        },
        "summary": {
            "total_visits": total_count,
            "visitors_inside": inside_count
        }
    }
    
    # P0 SECURITY LOG
    logger.info(f"[SECURITY] visit_query_scoped | endpoint=resident/visit-history | user_id={user_id[:12]}... | condo_id={condo_id[:12]}... | records_returned={len(enriched_entries)}")
    
    return result


@router.get("/resident/visit-history/export")
async def export_resident_visit_history(
    filter_period: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    visitor_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Export visit history data for PDF generation.
    Returns all matching entries (up to 500) with resident/condo info.
    """
    user_id = current_user["id"]
    condo_id = current_user.get("condominium_id")
    
    if not condo_id:
        raise HTTPException(status_code=403, detail="Usuario no asignado a un condominio")
    
    # Get resident and condo info
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "full_name": 1, "role_data": 1})
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "name": 1})
    
    # Get apartment info from role_data
    apartment = user.get("role_data", {}).get("apartment_number", "N/A") if user else "N/A"
    
    # Build query (same as main endpoint but without pagination)
    resident_auth_ids = await db.visitor_authorizations.distinct(
        "id",
        {"created_by": user_id, "condominium_id": condo_id}
    )
    
    legacy_visitor_ids = await db.visitors.distinct(
        "id",
        {"created_by": user_id, "condominium_id": condo_id}
    )
    
    # P0 FIX: Build query with proper handling of empty arrays
    or_conditions = []
    
    if resident_auth_ids:
        or_conditions.append({"authorization_id": {"$in": resident_auth_ids}})
    
    if legacy_visitor_ids:
        or_conditions.append({"visitor_id": {"$in": legacy_visitor_ids}})
    
    # Always include direct resident_id match
    or_conditions.append({"resident_id": user_id})
    
    query = {
        "condominium_id": condo_id,  # REQUIRED
        "$or": or_conditions
    }
    
    # Apply filters
    now = datetime.now(timezone.utc)
    if filter_period == "today":
        query["entry_at"] = {"$gte": now.strftime("%Y-%m-%d") + "T00:00:00"}
    elif filter_period == "7days":
        query["entry_at"] = {"$gte": (now - timedelta(days=7)).strftime("%Y-%m-%d") + "T00:00:00"}
    elif filter_period == "30days":
        query["entry_at"] = {"$gte": (now - timedelta(days=30)).strftime("%Y-%m-%d") + "T00:00:00"}
    elif filter_period == "custom" and (date_from or date_to):
        date_query = {}
        if date_from:
            date_query["$gte"] = f"{date_from}T00:00:00"
        if date_to:
            date_query["$lte"] = f"{date_to}T23:59:59"
        if date_query:
            query["entry_at"] = date_query
    
    if visitor_type:
        query["visitor_type"] = visitor_type
    if status:
        query["status"] = status
    
    # Fetch entries (limit 500 for export)
    entries = await db.visitor_entries.find(query, {"_id": 0}).sort("entry_at", -1).to_list(500)
    
    # Enrich with duration
    for entry in entries:
        if entry.get("entry_at") and entry.get("exit_at"):
            try:
                entry_time = datetime.fromisoformat(entry["entry_at"].replace("Z", "+00:00"))
                exit_time = datetime.fromisoformat(entry["exit_at"].replace("Z", "+00:00"))
                entry["duration_minutes"] = int((exit_time - entry_time).total_seconds() / 60)
            except Exception as calc_err:
                logger.debug(f"[VISITS] Duration calc error: {calc_err}")
                entry["duration_minutes"] = None
        else:
            entry["duration_minutes"] = None
    
    return {
        "resident_name": user.get("full_name", "N/A") if user else "N/A",
        "apartment": apartment,
        "condominium_name": condo.get("name", "N/A") if condo else "N/A",
        "export_date": now.isoformat(),
        "filter_applied": {
            "period": filter_period,
            "date_from": date_from,
            "date_to": date_to,
            "visitor_type": visitor_type,
            "status": status
        },
        "total_entries": len(entries),
        "entries": entries
    }


@router.get("/resident/visit-history/export/pdf")
async def export_resident_visit_history_pdf(
    filter_period: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    visitor_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Export visit history as PDF file (like audit export).
    Uses reportlab for reliable PDF generation.
    """
    user_id = current_user["id"]
    condo_id = current_user.get("condominium_id")
    
    if not condo_id:
        raise HTTPException(status_code=403, detail="Usuario no asignado a un condominio")
    
    # Get resident and condo info
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "full_name": 1, "role_data": 1})
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "name": 1})
    
    resident_name = user.get("full_name", "N/A") if user else "N/A"
    apartment = user.get("role_data", {}).get("apartment_number", "N/A") if user else "N/A"
    condo_name = condo.get("name", "N/A") if condo else "N/A"
    
    # Build query (same as JSON export)
    resident_auth_ids = await db.visitor_authorizations.distinct(
        "id",
        {"created_by": user_id, "condominium_id": condo_id}
    )
    
    legacy_visitor_ids = await db.visitors.distinct(
        "id",
        {"created_by": user_id, "condominium_id": condo_id}
    )
    
    or_conditions = []
    if resident_auth_ids:
        or_conditions.append({"authorization_id": {"$in": resident_auth_ids}})
    if legacy_visitor_ids:
        or_conditions.append({"visitor_id": {"$in": legacy_visitor_ids}})
    or_conditions.append({"resident_id": user_id})
    
    query = {
        "condominium_id": condo_id,
        "$or": or_conditions
    }
    
    # Apply filters
    now = datetime.now(timezone.utc)
    if filter_period == "today":
        query["entry_at"] = {"$gte": now.strftime("%Y-%m-%d") + "T00:00:00"}
    elif filter_period == "7days":
        query["entry_at"] = {"$gte": (now - timedelta(days=7)).strftime("%Y-%m-%d") + "T00:00:00"}
    elif filter_period == "30days":
        query["entry_at"] = {"$gte": (now - timedelta(days=30)).strftime("%Y-%m-%d") + "T00:00:00"}
    elif filter_period == "custom" and (date_from or date_to):
        date_query = {}
        if date_from:
            date_query["$gte"] = f"{date_from}T00:00:00"
        if date_to:
            date_query["$lte"] = f"{date_to}T23:59:59"
        if date_query:
            query["entry_at"] = date_query
    
    if visitor_type:
        query["visitor_type"] = visitor_type
    if status:
        query["status"] = status
    
    # Fetch entries
    entries = await db.visitor_entries.find(query, {"_id": 0}).sort("entry_at", -1).to_list(500)
    
    logger.info(f"[VISIT-PDF-EXPORT] Generating PDF for {resident_name}, entries: {len(entries)}")
    
    # Create PDF using reportlab (same pattern as audit export)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=30, bottomMargin=30, leftMargin=40, rightMargin=40)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    # Subtitle style
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#64748B'),
        spaceBefore=5,
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    # Header
    elements.append(Paragraph("HISTORIAL DE VISITAS", title_style))
    elements.append(Paragraph(f"Residente: {resident_name} | Apartamento: {apartment}", subtitle_style))
    elements.append(Paragraph(f"Condominio: {condo_name}", subtitle_style))
    elements.append(Paragraph(f"Generado: {now.strftime('%d/%m/%Y %H:%M')}", subtitle_style))
    elements.append(Spacer(1, 20))
    
    if entries:
        # Table header
        table_data = [['Visitante', 'Tipo', 'Fecha', 'Entrada', 'Salida', 'Estado']]
        
        # Status translations
        status_map = {
            'completed': 'Completada',
            'active': 'En curso',
            'cancelled': 'Cancelada',
            'pending': 'Pendiente'
        }
        
        # Type translations
        type_map = {
            'guest': 'Invitado',
            'delivery': 'Delivery',
            'service': 'Servicio',
            'contractor': 'Contratista',
            'other': 'Otro'
        }
        
        for entry in entries:
            visitor_name = entry.get('visitor_name', 'N/A')
            v_type = type_map.get(entry.get('visitor_type', ''), entry.get('visitor_type', 'N/A'))
            
            # Parse dates
            entry_at = entry.get('entry_at', '')
            exit_at = entry.get('exit_at', '')
            
            try:
                entry_dt = datetime.fromisoformat(entry_at.replace('Z', '+00:00'))
                date_str = entry_dt.strftime('%d/%m/%Y')
                entry_time = entry_dt.strftime('%H:%M')
            except:
                date_str = 'N/A'
                entry_time = 'N/A'
            
            try:
                if exit_at:
                    exit_dt = datetime.fromisoformat(exit_at.replace('Z', '+00:00'))
                    exit_time = exit_dt.strftime('%H:%M')
                else:
                    exit_time = '-'
            except:
                exit_time = '-'
            
            v_status = status_map.get(entry.get('status', ''), entry.get('status', 'N/A'))
            
            table_data.append([visitor_name, v_type, date_str, entry_time, exit_time, v_status])
        
        # Create table
        table = Table(table_data, colWidths=[120, 70, 70, 55, 55, 70])
        table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            
            # Data rows style
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#1E293B')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            
            # Alternating row colors
            *[('BACKGROUND', (0, i), (-1, i), colors.HexColor('#EFF6FF')) for i in range(2, len(table_data), 2)],
        ]))
        
        elements.append(table)
        
        # Footer with count
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#64748B'),
            spaceBefore=20,
            alignment=TA_CENTER
        )
        elements.append(Spacer(1, 15))
        elements.append(Paragraph(f"Total de visitas: {len(entries)}", footer_style))
    else:
        # No records message
        no_data_style = ParagraphStyle(
            'NoData',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#94A3B8'),
            alignment=TA_CENTER,
            spaceBefore=50
        )
        elements.append(Paragraph("No hay visitas registradas para el período seleccionado.", no_data_style))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    logger.info(f"[VISIT-PDF-EXPORT] PDF generated, size: {len(pdf_bytes)} bytes")
    
    # Return PDF file
    filename = f"historial-visitas-{now.strftime('%Y%m%d-%H%M%S')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


# ============================================
# GUARD/ADMIN NOTIFICATIONS ENDPOINTS
# ============================================

@router.get("/notifications")
async def get_user_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user = Depends(get_current_user)
):
    """
    Get notifications for current user (Admin, Guard, or Supervisor).
    Returns notifications from guard_notifications collection.
    """
    user_id = current_user["id"]
    roles = current_user.get("roles", [])
    condo_id = current_user.get("condominium_id")
    
    # Build query based on user role
    query = {}
    
    if "Guarda" in roles:
        # Guards see notifications addressed to them specifically
        query["$or"] = [
            {"guard_user_id": user_id},
            {"guard_id": user_id}
        ]
    elif "Administrador" in roles or "Supervisor" in roles:
        # Admins/Supervisors see all notifications for their condo
        if condo_id:
            query["condominium_id"] = condo_id
    elif "SuperAdmin" in roles:
        # SuperAdmin sees all
        pass
    else:
        # Other roles - return empty
        return []
    
    if unread_only:
        query["read"] = False
    
    notifications = await db.guard_notifications.find(
        query, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return notifications

@router.get("/notifications/unread-count")
async def get_unread_notification_count(
    current_user = Depends(get_current_user)
):
    """Get count of unread notifications for the current user"""
    user_id = current_user["id"]
    roles = current_user.get("roles", [])
    condo_id = current_user.get("condominium_id")
    
    # Build query based on user role
    query = {"read": False}
    
    if "Guarda" in roles:
        query["$or"] = [
            {"guard_user_id": user_id},
            {"guard_id": user_id}
        ]
    elif "Administrador" in roles or "Supervisor" in roles:
        if condo_id:
            query["condominium_id"] = condo_id
    elif "SuperAdmin" in roles:
        pass
    else:
        return {"count": 0}
    
    count = await db.guard_notifications.count_documents(query)
    return {"count": count}

@router.put("/notifications/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    current_user = Depends(get_current_user)
):
    """Mark a specific notification as read"""
    user_id = current_user["id"]
    roles = current_user.get("roles", [])
    condo_id = current_user.get("condominium_id")
    
    # Build query to ensure user can only mark their own notifications
    query = {"id": notification_id}
    
    if "Guarda" in roles:
        query["$or"] = [
            {"guard_user_id": user_id},
            {"guard_id": user_id}
        ]
    elif "Administrador" in roles or "Supervisor" in roles:
        if condo_id:
            query["condominium_id"] = condo_id
    elif "SuperAdmin" not in roles:
        raise HTTPException(status_code=403, detail="No tienes permiso")
    
    result = await db.guard_notifications.update_one(
        query,
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    
    return {"message": "Notificación marcada como leída"}

@router.put("/notifications/mark-all-read")
async def mark_all_guard_notifications_read(
    current_user = Depends(get_current_user)
):
    """Mark all notifications as read for the current user"""
    user_id = current_user["id"]
    roles = current_user.get("roles", [])
    condo_id = current_user.get("condominium_id")
    
    # Build query based on user role
    query = {"read": False}
    
    if "Guarda" in roles:
        query["$or"] = [
            {"guard_user_id": user_id},
            {"guard_id": user_id}
        ]
    elif "Administrador" in roles or "Supervisor" in roles:
        if condo_id:
            query["condominium_id"] = condo_id
    elif "SuperAdmin" not in roles:
        raise HTTPException(status_code=403, detail="No tienes permiso")
    
    result = await db.guard_notifications.update_many(
        query,
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {
        "message": f"{result.modified_count} notificaciones marcadas como leídas",
        "count": result.modified_count
    }



# Endpoint for Guards to write to their logbook
@router.get("/security/logbook")
async def get_guard_logbook(current_user = Depends(require_role_and_module("Administrador", "Supervisor", "Guarda", module="security"))):
    """Get logbook entries for guards - scoped by condominium"""
    # Use tenant_filter for multi-tenant scoping
    query = tenant_filter(current_user)
    
    logs = await db.access_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(50)
    
    # Format as logbook entries
    logbook_entries = []
    for log in logs:
        logbook_entries.append({
            "id": log.get("id"),
            "event_type": log.get("access_type", "entry"),
            "timestamp": log.get("timestamp"),
            "details": {
                "person": log.get("person_name"),
                "notes": log.get("notes"),
                "location": log.get("location")
            }
        })
    
    return logbook_entries


