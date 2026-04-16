"""GENTURIX - Guard Module Router (Auto-extracted from server.py)"""
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

# ==================== GUARD MY SHIFT ====================
@router.get("/guard/my-shift")
async def get_guard_my_shift(current_user = Depends(require_role("Guarda", "Administrador", "Supervisor"))):
    """
    Get guard's current and upcoming shift information.
    Used for the "Mi Turno" tab in Guard UI.
    Includes can_clock_in flag and message for UI validation.
    
    A shift is CURRENT if: start_time <= now <= end_time AND status in [scheduled, in_progress]
    A shift is UPCOMING if: start_time > now AND status = scheduled
    Early clock-in allowed: 15 minutes before shift start
    """
    guard = await db.guards.find_one({"user_id": current_user["id"]})
    if not guard:
        logger.warning(f"[my-shift] No guard record found for user_id={current_user['id']}")
        return {
            "has_guard_record": False,
            "current_shift": None,
            "next_shift": None,
            "can_clock_in": False,
            "clock_in_message": "No tienes registro como empleado"
        }
    
    condo_id = current_user.get("condominium_id")
    guard_condo_id = guard.get("condominium_id")
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    today = now.date().isoformat()
    
    logger.info(f"[my-shift] Checking shifts for guard_id={guard['id']}, user_condo={condo_id}, guard_condo={guard_condo_id}, now={now_iso}")
    
    # Check current clock status
    today_logs = await db.hr_clock_logs.find({
        "employee_id": guard["id"],
        "date": today
    }).sort("timestamp", -1).to_list(10)
    
    is_clocked_in = False
    if today_logs:
        is_clocked_in = today_logs[0]["type"] == "IN"
    
    # Use guard's condominium_id if user's is not set (for consistency)
    effective_condo_id = condo_id or guard_condo_id
    
    # Find current active shift (now is between start and end time)
    # Status must be scheduled (not started) or in_progress (started but not ended)
    current_shift_query = {
        "guard_id": guard["id"],
        "status": {"$in": ["scheduled", "in_progress"]},
        "start_time": {"$lte": now_iso},
        "end_time": {"$gte": now_iso}
    }
    # Only filter by condo if we have one
    if effective_condo_id:
        current_shift_query["condominium_id"] = effective_condo_id
    
    current_shift = await db.shifts.find_one(current_shift_query, {"_id": 0})
    
    if not current_shift:
        # Log why no shift was found - check all shifts for this guard
        all_guard_shifts = await db.shifts.find({
            "guard_id": guard["id"]
        }, {"_id": 0}).to_list(20)
        
        if all_guard_shifts:
            logger.info(f"[my-shift] Guard has {len(all_guard_shifts)} total shifts. Checking why none match...")
            for s in all_guard_shifts[:5]:  # Log first 5
                match_reasons = []
                if s.get("status") not in ["scheduled", "in_progress"]:
                    match_reasons.append(f"status={s.get('status')} (need scheduled/in_progress)")
                if s.get("start_time", "") > now_iso:
                    match_reasons.append(f"start_time={s.get('start_time')} > now")
                if s.get("end_time", "") < now_iso:
                    match_reasons.append(f"end_time={s.get('end_time')} < now")
                if effective_condo_id and s.get("condominium_id") != effective_condo_id:
                    match_reasons.append(f"condo mismatch: shift={s.get('condominium_id')} != user={effective_condo_id}")
                logger.info(f"[my-shift] Shift {s.get('id')[:8]}... rejected: {', '.join(match_reasons) or 'unknown'}")
        else:
            logger.info("[my-shift] Guard has NO shifts assigned at all")
    
    # Find next upcoming shift (start_time > now)
    next_shift_query = {
        "guard_id": guard["id"],
        "status": "scheduled",
        "start_time": {"$gt": now_iso}
    }
    if effective_condo_id:
        next_shift_query["condominium_id"] = effective_condo_id
    
    next_shift = await db.shifts.find_one(
        next_shift_query, 
        {"_id": 0},
        sort=[("start_time", 1)]
    )
    
    # Determine if guard can clock in
    can_clock_in = False
    clock_in_message = None
    
    if is_clocked_in:
        can_clock_in = False  # Already clocked in
        clock_in_message = "Ya tienes entrada registrada"
    elif current_shift:
        can_clock_in = True
        clock_in_message = None
        logger.info(f"[my-shift] Guard CAN clock in - current shift found: {current_shift.get('id')}")
    elif next_shift:
        # Check if within 15 minute early window
        shift_start_str = next_shift["start_time"]
        # Ensure timezone-aware datetime
        if 'Z' in shift_start_str:
            shift_start = datetime.fromisoformat(shift_start_str.replace('Z', '+00:00'))
        elif '+' in shift_start_str or shift_start_str.endswith('-00:00'):
            shift_start = datetime.fromisoformat(shift_start_str)
        else:
            # Assume UTC if no timezone info
            shift_start = datetime.fromisoformat(shift_start_str).replace(tzinfo=timezone.utc)
        
        minutes_until = int((shift_start - now).total_seconds() / 60)
        if minutes_until <= 15:
            can_clock_in = True
            clock_in_message = f"Tu turno comienza en {minutes_until} minutos"
            logger.info("[my-shift] Guard CAN clock in - within 15 min early window")
        else:
            can_clock_in = False
            if minutes_until > 60:
                clock_in_message = f"Tu turno comienza en {minutes_until // 60}h {minutes_until % 60}min. Puedes fichar 15 min antes."
            else:
                clock_in_message = f"Tu turno comienza en {minutes_until} minutos. Puedes fichar 15 min antes."
            logger.info(f"[my-shift] Guard CANNOT clock in - next shift in {minutes_until} min")
    else:
        can_clock_in = False
        clock_in_message = "No tienes un turno asignado para hoy"
        logger.info("[my-shift] Guard CANNOT clock in - no shifts found")
    
    return {
        "has_guard_record": True,
        "guard_id": guard["id"],
        "guard_name": guard.get("user_name") or guard.get("name") or "Sin nombre",
        "current_shift": current_shift,
        "next_shift": next_shift,
        "is_clocked_in": is_clocked_in,
        "can_clock_in": can_clock_in,
        "clock_in_message": clock_in_message
    }

@router.get("/guard/my-absences")
async def get_guard_my_absences(current_user = Depends(require_role("Guarda"))):
    """
    Get guard's own absence requests (read-only).
    Guards can only see their own absences.
    """
    guard = await db.guards.find_one({"user_id": current_user["id"]})
    if not guard:
        return []
    
    condo_id = current_user.get("condominium_id")
    
    absences = await db.hr_absences.find({
        "employee_id": guard["id"],
        "condominium_id": condo_id
    }, {"_id": 0}).sort("created_at", -1).to_list(50)
    
    return absences


# ==================== GUARD HISTORY ====================
@router.get("/guard/history")
async def get_guard_history(
    history_type: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """
    Get comprehensive guard action history.
    Includes: alerts resolved, visits completed, clock events, completed shifts.
    Single source of truth for Guard UI History tab.
    """
    condo_id = current_user.get("condominium_id")
    guard = None
    guard_id = None
    
    # Get guard record if user is a guard
    if "Guarda" in current_user.get("roles", []):
        guard = await db.guards.find_one({"user_id": current_user["id"]})
        if guard:
            guard_id = guard["id"]
    
    # Build base query with multi-tenant filtering
    base_query = {}
    if "SuperAdmin" not in current_user.get("roles", []) and condo_id:
        base_query["condominium_id"] = condo_id
    
    # Guards see only their own history
    if guard_id and "Administrador" not in current_user.get("roles", []):
        base_query["guard_id"] = guard_id
    
    # Filter by type if specified
    valid_types = ["alert_resolved", "visit_completed", "clock_in", "clock_out", "shift_completed"]
    if history_type and history_type in valid_types:
        base_query["type"] = history_type
    
    # Get guard_history entries (legacy)
    history_entries = await db.guard_history.find(base_query, {"_id": 0}).sort("timestamp", -1).to_list(100)
    
    # ==================== VISITOR ENTRIES (Check-ins/Check-outs) ====================
    # Guards see ALL entries in their condominium (useful for shift handoff)
    visitor_query = {}
    if condo_id:
        visitor_query["condominium_id"] = condo_id
    
    visitor_entries = await db.visitor_entries.find(visitor_query, {"_id": 0}).sort("entry_at", -1).to_list(50)
    
    for entry in visitor_entries:
        # Add check-in event
        history_entries.append({
            "id": f"{entry.get('id')}_in",
            "type": "visit_entry",
            "guard_id": guard_id,
            "guard_name": entry.get("entry_by_name"),
            "condominium_id": entry.get("condominium_id"),
            "timestamp": entry.get("entry_at"),
            "visitor_name": entry.get("visitor_name"),
            "destination": entry.get("destination") or entry.get("resident_apartment"),
            "vehicle_plate": entry.get("vehicle_plate"),
            "is_authorized": entry.get("is_authorized", False)
        })
        
        # Add check-out event if exists
        if entry.get("exit_at"):
            history_entries.append({
                "id": f"{entry.get('id')}_out",
                "type": "visit_exit",
                "guard_id": guard_id,
                "guard_name": entry.get("exit_by_name"),
                "condominium_id": entry.get("condominium_id"),
                "timestamp": entry.get("exit_at"),
                "visitor_name": entry.get("visitor_name"),
                "destination": entry.get("destination") or entry.get("resident_apartment")
            })
    
    # ==================== RESOLVED PANIC ALERTS ====================
    # Guards see ALL resolved alerts in their condominium
    alert_query = {"status": "resolved"}
    if condo_id:
        alert_query["condominium_id"] = condo_id
    
    resolved_alerts = await db.panic_events.find(alert_query, {"_id": 0}).sort("resolved_at", -1).to_list(30)
    
    for alert in resolved_alerts:
        history_entries.append({
            "id": alert.get("id"),
            "type": "alert_resolved",
            "guard_id": guard_id,
            "guard_name": alert.get("resolved_by_name"),
            "condominium_id": alert.get("condominium_id"),
            "timestamp": alert.get("resolved_at") or alert.get("created_at"),
            "alert_type": alert.get("panic_type"),
            "user_name": alert.get("user_name"),
            "location": alert.get("location"),
            "resolution_notes": alert.get("resolution_notes")
        })
    
    # ==================== CLOCK LOGS ====================
    clock_query = {}
    if condo_id:
        clock_query["condominium_id"] = condo_id
    if guard_id and "Administrador" not in current_user.get("roles", []):
        clock_query["employee_id"] = guard_id
    
    clock_logs = await db.hr_clock_logs.find(clock_query, {"_id": 0}).sort("timestamp", -1).to_list(50)
    
    for log in clock_logs:
        history_entries.append({
            "id": log.get("id"),
            "type": f"clock_{log['type'].lower()}",
            "guard_id": log.get("employee_id"),
            "guard_name": log.get("employee_name"),
            "condominium_id": log.get("condominium_id"),
            "timestamp": log.get("timestamp"),
            "date": log.get("date")
        })
    
    # ==================== COMPLETED SHIFTS ====================
    shift_query = {"status": "completed"}
    if condo_id:
        shift_query["condominium_id"] = condo_id
    if guard_id and "Administrador" not in current_user.get("roles", []):
        shift_query["guard_id"] = guard_id
    
    completed_shifts = await db.shifts.find(shift_query, {"_id": 0}).sort("end_time", -1).to_list(20)
    
    for shift in completed_shifts:
        history_entries.append({
            "id": shift.get("id"),
            "type": "shift_completed",
            "guard_id": shift.get("guard_id"),
            "guard_name": shift.get("guard_name"),
            "condominium_id": shift.get("condominium_id"),
            "timestamp": shift.get("end_time"),
            "shift_start": shift.get("start_time"),
            "shift_end": shift.get("end_time"),
            "location": shift.get("location")
        })
    
    # Sort all entries by timestamp (newest first)
    history_entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return history_entries[:100]



@router.get("/security/active-guards")
async def get_active_guards(current_user = Depends(require_role("Administrador", "Supervisor"))):
    """Get active guards - scoped by condominium"""
    query = {"status": "active"}
    if "SuperAdmin" not in current_user.get("roles", []):
        condo_id = current_user.get("condominium_id")
        if condo_id:
            query["condominium_id"] = condo_id
    guards = await db.guards.find(query, {"_id": 0}).to_list(100)
    return guards

@router.get("/security/dashboard-stats")
async def get_security_stats(current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))):
    """Security stats - scoped by condominium"""
    condo_filter = {}
    if "SuperAdmin" not in current_user.get("roles", []):
        condo_id = current_user.get("condominium_id")
        if condo_id:
            condo_filter["condominium_id"] = condo_id
    
    active_panic = await db.panic_events.count_documents({**condo_filter, "status": "active"})
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    today_access = await db.access_logs.count_documents({**condo_filter, "timestamp": {"$gte": today_start}})
    active_guards = await db.guards.count_documents({**condo_filter, "status": "active"})
    total_events = await db.panic_events.count_documents(condo_filter)
    
    return {
        "active_alerts": active_panic,
        "today_accesses": today_access,
        "active_guards": active_guards,
        "total_events": total_events
    }

