"""GENTURIX - Security + Panic Module Router (Auto-extracted from server.py)"""
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

# ==================== SECURITY MODULE ====================
@router.post("/security/panic")
async def trigger_panic(event: PanicEventCreate, request: Request, current_user = Depends(get_current_user)):
    """Trigger panic alert - scoped to user's condominium, only notifies guards in same condo"""
    
    # ========== DIAGNÓSTICO P0 ==========
    user_id = current_user.get("id", "UNKNOWN")
    user_email = current_user.get("email", "UNKNOWN")
    user_roles = current_user.get("roles", [])
    condo_id = current_user.get("condominium_id")
    
    logger.info(f"[PANIC-DIAG] ========== PANIC REQUEST RECEIVED ==========")
    logger.info(f"[PANIC-DIAG] User ID: {user_id}")
    logger.info(f"[PANIC-DIAG] User Email: {user_email}")
    logger.info(f"[PANIC-DIAG] User Roles: {user_roles}")
    logger.info(f"[PANIC-DIAG] Condominium ID: {condo_id}")
    logger.info(f"[PANIC-DIAG] Panic Type: {event.panic_type.value}")
    logger.info(f"[PANIC-DIAG] Location: {event.location}")
    logger.info(f"[PANIC-DIAG] GPS: lat={event.latitude}, lng={event.longitude}")
    logger.info(f"[PANIC-DIAG] Description: {event.description}")
    
    # Validar condominium_id
    if not condo_id:
        logger.error(f"[PANIC-DIAG] ERROR: User {user_email} has NO condominium_id")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no asignado a un condominio. Contacta al administrador."
        )
    
    # Validar que el usuario existe y está activo
    db_user = await db.users.find_one({"id": user_id}, {"_id": 0, "is_active": 1})
    if not db_user:
        logger.error(f"[PANIC-DIAG] ERROR: User {user_id} not found in database")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado. Sesión inválida."
        )
    
    if not db_user.get("is_active", True):
        logger.error(f"[PANIC-DIAG] ERROR: User {user_id} is inactive")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada. Contacta al administrador."
        )
    
    # Log GPS status
    has_gps = event.latitude is not None and event.longitude is not None
    logger.info(f"[PANIC-DIAG] GPS Available: {has_gps}")
    
    # ========== FIN DIAGNÓSTICO ==========
    
    panic_type_labels = {
        "emergencia_medica": "🚑 Emergencia Médica",
        "actividad_sospechosa": "👁️ Actividad Sospechosa",
        "emergencia_general": "🚨 Emergencia General"
    }
    
    # Map internal panic type to display type for notifications
    panic_type_display_map = {
        "emergencia_medica": "medical",
        "actividad_sospechosa": "suspicious",
        "emergencia_general": "general"
    }
    
    condo_id = current_user.get("condominium_id")
    
    # Get apartment number from role_data if available
    role_data = current_user.get("role_data", {})
    apartment = role_data.get("apartment_number", "N/A")
    
    panic_event = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "user_name": current_user["full_name"],
        "user_email": current_user["email"],
        "condominium_id": condo_id,  # CRITICAL: Multi-tenant filter
        "panic_type": event.panic_type.value,
        "panic_type_label": panic_type_labels.get(event.panic_type.value, "Emergencia"),
        "location": event.location,
        "latitude": event.latitude,
        "longitude": event.longitude,
        "description": event.description,
        "apartment": apartment,
        "status": "active",
        "is_test": False,  # Mark as real data
        "notified_guards": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "resolved_at": None,
        "resolved_by": None
    }
    
    await db.panic_events.insert_one(panic_event)
    
    # Notify ONLY guards in the same condominium
    guard_query = {"status": "active"}
    if condo_id:
        guard_query["condominium_id"] = condo_id
    
    active_guards = await db.guards.find(guard_query, {"_id": 0}).to_list(100)
    for guard in active_guards:
        notification = {
            "id": str(uuid.uuid4()),
            "guard_id": guard["id"],
            "guard_user_id": guard.get("user_id"),
            "panic_event_id": panic_event["id"],
            "condominium_id": condo_id,
            "panic_type": event.panic_type.value,
            "panic_type_label": panic_type_labels.get(event.panic_type.value, "Emergencia"),
            "resident_name": current_user["full_name"],
            "location": event.location,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.guard_notifications.insert_one(notification)
        panic_event["notified_guards"].append(guard["id"])
    
    # Update panic event with notified guards
    await db.panic_events.update_one(
        {"id": panic_event["id"]},
        {"$set": {"notified_guards": panic_event["notified_guards"]}}
    )
    
    # Send PUSH NOTIFICATIONS to all subscribed guards in this condominium
    # SECURITY: Backend decides who receives - ONLY guards in same condo, excluding sender
    push_result = await notify_guards_of_panic(
        condominium_id=condo_id,
        panic_data={
            "event_id": panic_event["id"],
            "panic_type": panic_type_display_map.get(event.panic_type.value, "general"),
            "resident_name": current_user["full_name"],
            "apartment": apartment,
            "timestamp": panic_event["created_at"]
        },
        sender_id=current_user["id"]  # Exclude sender from notifications
    )
    
    # === SEND EMAIL ALERT TO ADMINISTRATORS (fail-safe) ===
    try:
        # Get condominium info for email
        condo_info = await db.condominiums.find_one(
            {"id": condo_id}, 
            {"_id": 0, "name": 1, "contact_email": 1}
        )
        condo_name = condo_info.get("name", "Condominio") if condo_info else "Condominio"
        
        # Get admin users for this condominium
        admin_users = await db.users.find(
            {"condominium_id": condo_id, "roles": {"$in": ["Administrador"]}, "is_active": True},
            {"_id": 0, "email": 1, "full_name": 1}
        ).to_list(10)
        
        # Send email to each admin
        for admin in admin_users:
            admin_email = admin.get("email")
            if admin_email:
                try:
                    alert_html = get_emergency_alert_email_html(
                        resident_name=current_user["full_name"],
                        alert_type=panic_type_labels.get(event.panic_type.value, "Emergencia"),
                        location=event.location or apartment,
                        timestamp=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC"),
                        condominium_name=condo_name
                    )
                    await send_email(
                        to=admin_email,
                        subject=f"🚨 ALERTA DE EMERGENCIA - {condo_name}",
                        html=alert_html
                    )
                except Exception as admin_email_error:
                    logger.warning(f"[EMAIL] Failed to send emergency alert to admin {admin_email}: {admin_email_error}")
    except Exception as email_error:
        logger.warning(f"[EMAIL] Failed to send emergency alert emails: {email_error}")
        # Continue - don't break API flow
    
    # Log to audit
    await log_audit_event(
        AuditEventType.PANIC_BUTTON,
        current_user["id"],
        "security",
        {
            "panic_type": event.panic_type.value,
            "location": event.location,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "description": event.description,
            "notified_guards_count": len(active_guards),
            "push_notifications": push_result
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id,
        user_email=user_email
    )
    
    # Log flow event
    print(f"[FLOW] panic_alert_triggered | event_id={panic_event['id']} type={event.panic_type.value} condo={condo_id[:8]} guards_notified={len(active_guards)}")
    logger.info(f"[PANIC-DIAG] SUCCESS: Alert {panic_event['id']} created, {len(active_guards)} guards notified")
    
    return {
        "message": "Alerta enviada exitosamente",
        "event_id": panic_event["id"],
        "panic_type": event.panic_type.value,
        "notified_guards": len(active_guards),
        "push_notifications": push_result
    }

@router.get("/resident/my-alerts")
async def get_resident_alerts(current_user = Depends(get_current_user)):
    """
    Resident gets their own alert history - STRICTLY filtered by user_id AND condominium_id.
    Shows: alert type, timestamp, status (active/resolved), resolved_by
    """
    condo_id = current_user.get("condominium_id")
    user_id = current_user["id"]
    
    if not condo_id:
        return []
    
    query = {
        "user_id": user_id,
        "condominium_id": condo_id,
        "is_test": {"$ne": True}
    }
    
    events = await db.panic_events.find(query, {"_id": 0}).sort("created_at", -1).to_list(50)
    
    # Format response for resident view
    formatted_events = []
    for e in events:
        formatted_events.append({
            "id": e.get("id"),
            "panic_type": e.get("panic_type"),
            "panic_type_label": e.get("panic_type_label"),
            "location": e.get("location"),
            "status": e.get("status"),
            "created_at": e.get("created_at"),
            "resolved_at": e.get("resolved_at"),
            "resolved_by_name": e.get("resolved_by_name"),
            "notified_guards": len(e.get("notified_guards", []))
        })
    
    return formatted_events

@router.get("/security/panic-events")
async def get_panic_events(current_user = Depends(require_module("security"))):
    """Get panic events - scoped by condominium, excludes test/demo data"""
    # Verify role
    allowed_roles = ["Administrador", "Supervisor", "Guarda", "SuperAdmin"]
    if not any(role in current_user.get("roles", []) for role in allowed_roles):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    # Use tenant_filter for automatic condominium scoping
    query = tenant_filter(current_user, {"is_test": {"$ne": True}})
    
    events = await db.panic_events.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return events

@router.put("/security/panic/{event_id}/resolve")
async def resolve_panic(event_id: str, resolve_data: PanicResolveRequest, request: Request, current_user = Depends(require_role_and_module("Administrador", "Supervisor", "Guarda", module="security"))):
    """Resolve a panic event and save to guard_history"""
    # Use get_tenant_resource for automatic 404/403 handling
    event = await get_tenant_resource(db.panic_events, event_id, current_user)
    
    resolved_at = datetime.now(timezone.utc).isoformat()
    resolution_notes = resolve_data.notes if resolve_data.notes else None
    
    await db.panic_events.update_one(
        {"id": event_id},
        {"$set": {
            "status": "resolved", 
            "resolved_at": resolved_at, 
            "resolved_by": current_user["id"],
            "resolved_by_name": current_user.get("full_name", "Unknown"),
            "resolution_notes": resolution_notes
        }}
    )
    
    # Get guard info if resolver is a guard
    guard = await db.guards.find_one({"user_id": current_user["id"]})
    guard_id = guard["id"] if guard else None
    
    # Save to guard_history for audit trail
    history_entry = {
        "id": str(uuid.uuid4()),
        "type": "alert_resolved",
        "guard_id": guard_id,
        "guard_user_id": current_user["id"],
        "guard_name": current_user.get("full_name"),
        "condominium_id": event.get("condominium_id") or current_user.get("condominium_id"),
        "event_id": event_id,
        "event_type": event.get("panic_type"),
        "event_type_label": event.get("panic_type_label"),
        "resident_name": event.get("user_name"),
        "location": event.get("location"),
        "original_created_at": event.get("created_at"),
        "resolved_at": resolved_at,
        "resolution_notes": resolution_notes,
        "timestamp": resolved_at
    }
    await db.guard_history.insert_one(history_entry)
    
    # Log audit event
    await log_audit_event(
        AuditEventType.PANIC_RESOLVED,
        current_user["id"],
        "security",
        {
            "event_id": event_id,
            "panic_type": event.get("panic_type"),
            "resident_name": event.get("user_name"),
            "location": event.get("location"),
            "resolution_notes": resolution_notes
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "Panic event resolved"}

@router.post("/security/access-log")
async def create_access_log(log: AccessLogCreate, request: Request, current_user = Depends(require_role_and_module("Administrador", "Supervisor", "Guarda", module="security"))):
    # Determine role for source field
    user_roles = current_user.get("roles", [])
    if "Administrador" in user_roles:
        source = "manual_admin"
    elif "Supervisor" in user_roles:
        source = "manual_supervisor"
    else:
        source = "manual_guard"
    
    access_log = {
        "id": str(uuid.uuid4()),
        "person_name": log.person_name,
        "access_type": log.access_type,
        "location": log.location,
        "notes": log.notes,
        "recorded_by": current_user["id"],
        "recorded_by_name": current_user.get("full_name", "Usuario"),
        "condominium_id": current_user.get("condominium_id"),
        "source": source,
        "status": "inside" if log.access_type == "entry" else "outside",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await db.access_logs.insert_one(access_log)
    
    # Remove MongoDB _id before returning
    access_log.pop("_id", None)
    
    # Use appropriate audit event type based on access type
    audit_event = AuditEventType.ACCESS_GRANTED if log.access_type == "entry" else AuditEventType.ACCESS_DENIED
    
    # Log audit event with manual access action
    await log_audit_event(
        audit_event,
        current_user["id"],
        "access",
        {
            "action": "manual_access_created",
            "person": log.person_name, 
            "type": log.access_type, 
            "location": log.location, 
            "performed_by_role": source.replace("manual_", "").upper(),
            "performed_by_name": current_user.get("full_name"),
            "condominium_id": current_user.get("condominium_id")
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return access_log

@router.get("/security/access-logs")
async def get_access_logs(
    include_visitor_entries: bool = True,
    limit: int = 100,
    current_user = Depends(require_role_and_module("Administrador", "Supervisor", "Guarda", "SuperAdmin", module="security"))
):
    """
    Get unified access logs combining:
    - Manual access_logs entries
    - visitor_entries (check-ins from guards)
    Scoped by condominium for non-SuperAdmin users
    """
    # Use tenant_filter for automatic condominium scoping
    query = tenant_filter(current_user)
    
    # Get manual access logs
    manual_logs = await db.access_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit // 2)
    
    # Convert to unified format
    unified_logs = []
    for log in manual_logs:
        unified_logs.append({
            "id": log.get("id"),
            "person_name": log.get("person_name"),
            "access_type": log.get("access_type", "entry"),
            "entry_type": "manual",
            "location": log.get("location", "Sin ubicación"),
            "timestamp": log.get("timestamp"),
            "guard_name": log.get("recorded_by_name"),
            "notes": log.get("notes"),
            "source": log.get("source", "manual")
        })
    
    # Include visitor entries (actual check-ins)
    if include_visitor_entries:
        entries = await db.visitor_entries.find(query, {"_id": 0}).sort("entry_at", -1).to_list(limit)
        
        for entry in entries:
            unified_logs.append({
                "id": entry.get("id"),
                "person_name": entry.get("visitor_name", "Visitante"),
                "access_type": "entry" if entry.get("entry_at") else "exit",
                "entry_type": entry.get("authorization_type", "visitor"),
                "location": entry.get("destination", "Sin destino"),
                "timestamp": entry.get("entry_at") or entry.get("exit_at"),
                "exit_timestamp": entry.get("exit_at"),
                "guard_name": entry.get("guard_name"),
                "vehicle_plate": entry.get("vehicle_plate"),
                "is_authorized": entry.get("is_authorized", True),
                "resident_name": entry.get("authorized_by_name"),
                "source": "check_in"
            })
    
    # Sort all by timestamp (most recent first)
    unified_logs.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    
    return unified_logs[:limit]

# Endpoint for Residents to see their visitor notifications
@router.get("/resident/notifications")
async def get_resident_notifications(current_user = Depends(get_current_user)):
    """Get visitor entry/exit notifications for a resident"""
    # Get visitor records created by this resident that have been executed
    visitors = await db.visitors.find(
        {"created_by": current_user["id"], "status": {"$in": ["entry_registered", "exit_registered"]}},
        {"_id": 0}
    ).sort("updated_at", -1).to_list(20)
    
    return visitors

