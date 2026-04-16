"""GENTURIX - HR Module Router (Auto-extracted from server.py)"""
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

# ==================== HR MODULE ====================
@router.post("/hr/guards")
async def create_guard(guard: GuardCreate, request: Request, current_user = Depends(require_module("hr"))):
    # Verify admin/HR role
    if not any(role in current_user.get("roles", []) for role in ["Administrador", "HR", "SuperAdmin"]):
        raise HTTPException(status_code=403, detail="Se requiere rol de Administrador o HR")
    
    user = await db.users.find_one({"id": guard.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    guard_doc = {
        "id": str(uuid.uuid4()),
        "user_id": guard.user_id,
        "user_name": user["full_name"],
        "email": user["email"],
        "badge_number": guard.badge_number,
        "phone": guard.phone,
        "emergency_contact": guard.emergency_contact,
        "hire_date": guard.hire_date,
        "hourly_rate": guard.hourly_rate,
        "is_active": True,
        "total_hours": 0,
        "condominium_id": current_user.get("condominium_id"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.guards.insert_one(guard_doc)
    
    # Add Guarda role to user
    await db.users.update_one(
        {"id": guard.user_id},
        {"$addToSet": {"roles": "Guarda"}}
    )
    
    await log_audit_event(
        AuditEventType.USER_UPDATED, current_user["id"], "hr",
        {"action": "guard_created", "guard_id": guard_doc.get("id", "")},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=current_user.get("condominium_id"),
        user_email=current_user.get("email"),
    )
    return guard_doc

@router.get("/hr/guards")
async def get_guards(
    include_invalid: bool = False,
    current_user = Depends(require_module("hr"))
):
    """Get guards/employees - filtered by condominium, optionally including invalid records"""
    # Verify role
    if not any(role in current_user.get("roles", []) for role in ["Administrador", "Supervisor", "HR", "SuperAdmin"]):
        raise HTTPException(status_code=403, detail="Se requiere rol de Administrador, Supervisor o HR")
    
    # Use tenant_filter with extra conditions
    extra = {}
    if not include_invalid:
        extra["user_id"] = {"$ne": None, "$exists": True}
        extra["is_active"] = True
    
    query = tenant_filter(current_user, extra if extra else None)
    
    guards = await db.guards.find(query, {"_id": 0}).to_list(100)
    
    # Enrich with user data and validation status
    enriched_guards = []
    for guard in guards:
        # Check if user exists
        user_id = guard.get("user_id")
        user_valid = False
        user_data = None
        
        if user_id:
            user = await db.users.find_one({"id": user_id}, {"_id": 0, "full_name": 1, "email": 1, "is_active": 1})
            if user:
                user_valid = True
                user_data = user
                # Update guard name from user if missing
                if not guard.get("user_name") or not guard.get("full_name"):
                    guard["user_name"] = user.get("full_name")
                    guard["full_name"] = user.get("full_name")
                    guard["email"] = user.get("email")
        
        guard["_is_evaluable"] = user_valid and guard.get("is_active", False)
        guard["_validation_status"] = "valid" if user_valid else "invalid_user"
        
        enriched_guards.append(guard)
    
    return enriched_guards

# ==================== HR DATA INTEGRITY VALIDATION ====================

@router.get("/hr/validate-integrity")
async def validate_hr_integrity(
    current_user = Depends(require_role_and_module("Administrador", "SuperAdmin", module="hr"))
):
    """
    Validate HR data integrity - detect and report issues:
    - Duplicate guards by user_id
    - Guards without user_id
    - Guards with non-existent users
    - Orphan evaluations
    """
    issues = {
        "duplicates": [],
        "missing_user_id": [],
        "invalid_user": [],
        "orphan_evaluations": [],
        "summary": {
            "total_guards": 0,
            "valid_guards": 0,
            "invalid_guards": 0,
            "total_evaluations": 0,
            "orphan_evaluations": 0
        }
    }
    
    # Get all guards
    guards = await db.guards.find({}, {"_id": 0}).to_list(500)
    issues["summary"]["total_guards"] = len(guards)
    
    # 1. Check for duplicates by user_id
    user_ids = [g.get("user_id") for g in guards if g.get("user_id")]
    duplicate_uids = [uid for uid in set(user_ids) if user_ids.count(uid) > 1]
    
    for dup_uid in duplicate_uids:
        dup_guards = [g for g in guards if g.get("user_id") == dup_uid]
        issues["duplicates"].append({
            "user_id": dup_uid,
            "count": len(dup_guards),
            "guard_ids": [g.get("id") for g in dup_guards],
            "names": [g.get("user_name") or g.get("full_name") for g in dup_guards]
        })
    
    # 2. Check for guards without user_id
    for guard in guards:
        if not guard.get("user_id"):
            issues["missing_user_id"].append({
                "guard_id": guard.get("id"),
                "name": guard.get("user_name") or guard.get("full_name") or "Unknown",
                "is_active": guard.get("is_active")
            })
    
    # 3. Check for guards with non-existent users
    valid_count = 0
    for guard in guards:
        user_id = guard.get("user_id")
        if user_id:
            user = await db.users.find_one({"id": user_id})
            if user:
                valid_count += 1
            else:
                issues["invalid_user"].append({
                    "guard_id": guard.get("id"),
                    "user_id": user_id,
                    "name": guard.get("user_name") or guard.get("full_name") or "Unknown"
                })
    
    issues["summary"]["valid_guards"] = valid_count
    issues["summary"]["invalid_guards"] = len(guards) - valid_count
    
    # 4. Check for orphan evaluations
    evaluations = await db.hr_evaluations.find({}, {"_id": 0}).to_list(500)
    issues["summary"]["total_evaluations"] = len(evaluations)
    
    for eval in evaluations:
        emp_id = eval.get("employee_id")
        if emp_id:
            # Check in guards first, then users
            guard = await db.guards.find_one({"id": emp_id})
            if not guard:
                user = await db.users.find_one({"id": emp_id})
                if not user:
                    issues["orphan_evaluations"].append({
                        "evaluation_id": eval.get("id"),
                        "employee_id": emp_id,
                        "employee_name": eval.get("employee_name"),
                        "created_at": eval.get("created_at")
                    })
    
    issues["summary"]["orphan_evaluations"] = len(issues["orphan_evaluations"])
    
    return issues

@router.post("/hr/cleanup-invalid-guards")
async def cleanup_invalid_guards(
    dry_run: bool = True,
    current_user = Depends(require_role("SuperAdmin"))
):
    """
    Clean up invalid guard records:
    - Deactivate guards without user_id
    - Deactivate guards with non-existent users
    - Remove duplicate guard records (keep the one with most evaluations)
    
    Set dry_run=false to actually perform cleanup
    """
    results = {
        "dry_run": dry_run,
        "deactivated": [],
        "removed_duplicates": [],
        "errors": []
    }
    
    guards = await db.guards.find({}, {"_id": 0}).to_list(500)
    
    # 1. Handle guards without user_id
    for guard in guards:
        if not guard.get("user_id"):
            if not dry_run:
                await db.guards.update_one(
                    {"id": guard.get("id")},
                    {"$set": {"is_active": False, "deactivation_reason": "no_user_id"}}
                )
            results["deactivated"].append({
                "guard_id": guard.get("id"),
                "reason": "no_user_id",
                "name": guard.get("user_name") or "Unknown"
            })
    
    # 2. Handle guards with non-existent users
    for guard in guards:
        user_id = guard.get("user_id")
        if user_id:
            user = await db.users.find_one({"id": user_id})
            if not user:
                if not dry_run:
                    await db.guards.update_one(
                        {"id": guard.get("id")},
                        {"$set": {"is_active": False, "deactivation_reason": "user_not_found"}}
                    )
                results["deactivated"].append({
                    "guard_id": guard.get("id"),
                    "reason": "user_not_found",
                    "user_id": user_id
                })
    
    # 3. Handle duplicates
    user_ids = [g.get("user_id") for g in guards if g.get("user_id")]
    duplicate_uids = [uid for uid in set(user_ids) if user_ids.count(uid) > 1]
    
    for dup_uid in duplicate_uids:
        dup_guards = [g for g in guards if g.get("user_id") == dup_uid]
        
        # Get evaluation count for each duplicate
        for dg in dup_guards:
            eval_count = await db.hr_evaluations.count_documents({"employee_id": dg.get("id")})
            dg["_eval_count"] = eval_count
        
        # Sort by evaluation count (keep the one with most evaluations)
        dup_guards.sort(key=lambda x: x.get("_eval_count", 0), reverse=True)
        
        # Keep first (most evaluations), deactivate others
        keep_guard = dup_guards[0]
        for to_remove in dup_guards[1:]:
            if not dry_run:
                await db.guards.update_one(
                    {"id": to_remove.get("id")},
                    {"$set": {"is_active": False, "deactivation_reason": "duplicate"}}
                )
            results["removed_duplicates"].append({
                "kept_guard_id": keep_guard.get("id"),
                "deactivated_guard_id": to_remove.get("id"),
                "user_id": dup_uid
            })
    
    await log_audit_event(
        AuditEventType.USER_UPDATED, current_user["id"], "hr",
        {"action": "guards_cleanup", "removed": len(invalid_guards)},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=current_user.get("condominium_id"),
        user_email=current_user.get("email"),
    )
    return results

@router.get("/hr/evaluable-employees")
async def get_evaluable_employees(
    current_user = Depends(require_role("Administrador", "Supervisor", "HR"))
):
    """
    Get employees that are eligible for evaluation:
    - Have valid user_id
    - User exists in users collection
    - Is active
    - Not the current user (can't evaluate yourself)
    """
    condo_id = current_user.get("condominium_id")
    current_user_id = current_user.get("id")
    
    # Build query
    query = {
        "user_id": {"$ne": None, "$exists": True},
        "is_active": True
    }
    
    if "SuperAdmin" not in current_user.get("roles", []) and condo_id:
        query["condominium_id"] = condo_id
    
    guards = await db.guards.find(query, {"_id": 0}).to_list(100)
    
    evaluable_employees = []
    for guard in guards:
        user_id = guard.get("user_id")
        
        # Skip self
        if user_id == current_user_id:
            continue
        
        # Verify user exists
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "full_name": 1, "email": 1, "is_active": 1})
        if user and user.get("is_active", True):
            # Enrich guard data with user info
            guard["user_name"] = user.get("full_name") or guard.get("user_name")
            guard["full_name"] = user.get("full_name") or guard.get("full_name")
            guard["email"] = user.get("email") or guard.get("email")
            guard["_is_evaluable"] = True
            
            # Get evaluation count
            eval_count = await db.hr_evaluations.count_documents({"employee_id": guard.get("id")})
            guard["evaluation_count"] = eval_count
            
            evaluable_employees.append(guard)
    
    return evaluable_employees

@router.get("/hr/guards/{guard_id}")
async def get_guard(guard_id: str, current_user = Depends(require_role_and_module("Administrador", "Supervisor", "HR", module="hr"))):
    """Get a single guard by ID - must belong to user's condominium"""
    # Use get_tenant_resource for automatic 404/403 handling
    guard = await get_tenant_resource(db.guards, guard_id, current_user)
    return guard

@router.put("/hr/guards/{guard_id}")
async def update_guard(
    guard_id: str,
    guard_update: GuardUpdate,
    request: Request,
    current_user = Depends(require_role_and_module("Administrador", module="hr"))
):
    """Update guard/employee details - must belong to user's condominium"""
    # Use get_tenant_resource for tenant validation
    guard = await get_tenant_resource(db.guards, guard_id, current_user)
    
    # Build update dict with only provided fields
    update_data = {}
    if guard_update.badge_number is not None:
        update_data["badge_number"] = guard_update.badge_number
    if guard_update.phone is not None:
        update_data["phone"] = guard_update.phone
    if guard_update.emergency_contact is not None:
        update_data["emergency_contact"] = guard_update.emergency_contact
    if guard_update.hourly_rate is not None:
        update_data["hourly_rate"] = guard_update.hourly_rate
    if guard_update.is_active is not None:
        update_data["is_active"] = guard_update.is_active
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.guards.update_one(
        {"id": guard_id},
        {"$set": update_data}
    )
    
    await log_audit_event(
        AuditEventType.USER_UPDATED,
        current_user["id"],
        "hr",
        {"guard_id": guard_id, "updated_fields": list(update_data.keys())},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    updated_guard = await db.guards.find_one({"id": guard_id}, {"_id": 0})
    return updated_guard

# ==================== HR SHIFTS (FULL CRUD) ====================

@router.post("/hr/shifts")
async def create_shift(shift: ShiftCreate, request: Request, current_user = Depends(require_role_and_module("Administrador", "Supervisor", "HR", "SuperAdmin", module="hr"))):
    """Create a new shift with validations"""
    # Validate guard exists and is active
    guard = await db.guards.find_one({"id": shift.guard_id})
    if not guard:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    if not guard.get("is_active", True):
        raise HTTPException(status_code=400, detail="El empleado no está activo")
    
    # Parse and validate times
    try:
        start_dt = datetime.fromisoformat(shift.start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(shift.end_time.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use ISO 8601")
    
    if start_dt >= end_dt:
        raise HTTPException(status_code=400, detail="La hora de inicio debe ser anterior a la hora de fin")
    
    # Check for overlapping shifts (only scheduled or in_progress - allow creating new shifts over completed ones)
    existing_shifts = await db.shifts.find({
        "guard_id": shift.guard_id,
        "status": {"$in": ["scheduled", "in_progress"]},  # Only active shifts can cause overlap
        "$or": [
            {"start_time": {"$lt": shift.end_time}, "end_time": {"$gt": shift.start_time}}
        ]
    }).to_list(100)
    
    if existing_shifts:
        raise HTTPException(status_code=400, detail="El empleado ya tiene un turno programado en ese horario")
    
    # Get condominium_id - prefer user's condo, fallback to guard's condo (important for SuperAdmin)
    condominium_id = current_user.get("condominium_id") or guard.get("condominium_id")
    
    if not condominium_id:
        raise HTTPException(status_code=400, detail="No se puede determinar el condominio. El empleado debe estar asignado a un condominio.")
    
    shift_doc = {
        "id": str(uuid.uuid4()),
        "guard_id": shift.guard_id,
        "guard_name": guard.get("user_name") or guard.get("name") or "Sin nombre",
        "start_time": shift.start_time,
        "end_time": shift.end_time,
        "location": shift.location,
        "notes": shift.notes,
        "status": "scheduled",
        "condominium_id": condominium_id,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.shifts.insert_one(shift_doc)
    
    # Remove MongoDB _id before returning
    shift_doc.pop("_id", None)
    
    await log_audit_event(
        AuditEventType.SHIFT_CREATED,
        current_user["id"],
        "hr",
        {"shift_id": shift_doc["id"], "guard_id": shift.guard_id, "location": shift.location},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return shift_doc

@router.get("/hr/shifts")
async def get_shifts(
    status: Optional[str] = None,
    guard_id: Optional[str] = None,
    current_user = Depends(require_module("hr"))
):
    """Get shifts with optional filters - scoped by condominium"""
    # Verify role
    allowed_roles = ["Administrador", "Supervisor", "Guarda", "HR", "SuperAdmin"]
    if not any(role in current_user.get("roles", []) for role in allowed_roles):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    # Build extra filters
    extra = {}
    if status:
        extra["status"] = status
    if guard_id:
        extra["guard_id"] = guard_id
    
    # Use tenant_filter for multi-tenant scoping
    query = tenant_filter(current_user, extra if extra else None)
    
    # Guards can only see their own shifts
    if "Guarda" in current_user.get("roles", []) and "Administrador" not in current_user.get("roles", []):
        guard = await db.guards.find_one({"user_id": current_user["id"]})
        if guard:
            query["guard_id"] = guard["id"]
    
    shifts = await db.shifts.find(query, {"_id": 0}).sort("start_time", -1).to_list(100)
    return shifts

@router.get("/hr/shifts/{shift_id}")
async def get_shift(shift_id: str, current_user = Depends(require_role("Administrador", "Supervisor", "Guarda", "HR"))):
    """Get a single shift by ID - must belong to user's condominium"""
    # Use get_tenant_resource for automatic 404/403 handling
    shift = await get_tenant_resource(db.shifts, shift_id, current_user)
    return shift

@router.put("/hr/shifts/{shift_id}")
async def update_shift(
    shift_id: str,
    shift_update: ShiftUpdate,
    request: Request,
    current_user = Depends(require_role("Administrador", "Supervisor", "HR"))
):
    """Update an existing shift - must belong to user's condominium"""
    # Use get_tenant_resource for tenant validation
    shift = await get_tenant_resource(db.shifts, shift_id, current_user)
    
    update_data = {}
    
    if shift_update.start_time is not None:
        update_data["start_time"] = shift_update.start_time
    if shift_update.end_time is not None:
        update_data["end_time"] = shift_update.end_time
    if shift_update.location is not None:
        update_data["location"] = shift_update.location
    if shift_update.notes is not None:
        update_data["notes"] = shift_update.notes
    if shift_update.status is not None:
        if shift_update.status not in ["scheduled", "in_progress", "completed", "cancelled"]:
            raise HTTPException(status_code=400, detail="Estado inválido")
        update_data["status"] = shift_update.status
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    
    # Validate times if both are being updated
    new_start = update_data.get("start_time", shift["start_time"])
    new_end = update_data.get("end_time", shift["end_time"])
    
    try:
        start_dt = datetime.fromisoformat(new_start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(new_end.replace('Z', '+00:00'))
        if start_dt >= end_dt:
            raise HTTPException(status_code=400, detail="La hora de inicio debe ser anterior a la hora de fin")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido")
    
    # Check for overlaps (excluding current shift)
    if "start_time" in update_data or "end_time" in update_data:
        existing = await db.shifts.find({
            "id": {"$ne": shift_id},
            "guard_id": shift["guard_id"],
            "status": {"$ne": "cancelled"},
            "$or": [
                {"start_time": {"$lt": new_end}, "end_time": {"$gt": new_start}}
            ]
        }).to_list(100)
        
        if existing:
            raise HTTPException(status_code=400, detail="El cambio genera conflicto con otro turno")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["updated_by"] = current_user["id"]
    
    await db.shifts.update_one({"id": shift_id}, {"$set": update_data})
    
    await log_audit_event(
        AuditEventType.SHIFT_UPDATED,
        current_user["id"],
        "hr",
        {"shift_id": shift_id, "updated_fields": list(update_data.keys())},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    updated_shift = await db.shifts.find_one({"id": shift_id}, {"_id": 0})
    return updated_shift

@router.delete("/hr/shifts/{shift_id}")
async def delete_shift(
    shift_id: str,
    request: Request,
    current_user = Depends(require_role("Administrador", "HR", "Supervisor", "SuperAdmin"))
):
    """Delete (cancel) a shift - must belong to user's condominium"""
    # Use get_tenant_resource for tenant validation
    shift = await get_tenant_resource(db.shifts, shift_id, current_user)
    
    # Soft delete - mark as cancelled
    await db.shifts.update_one(
        {"id": shift_id},
        {"$set": {
            "status": "cancelled",
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
            "cancelled_by": current_user["id"]
        }}
    )
    
    await log_audit_event(
        AuditEventType.SHIFT_DELETED,
        current_user["id"],
        "hr",
        {"shift_id": shift_id, "guard_id": shift["guard_id"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "Turno cancelado exitosamente"}

# ==================== HR CLOCK IN/OUT ====================

@router.post("/hr/clock")
async def clock_in_out(
    clock_req: ClockRequest,
    request: Request,
    current_user = Depends(require_role("Guarda", "Administrador", "Supervisor"))
):
    """
    Register clock in or clock out.
    
    Clock IN rules:
    - Guard must have an active shift (current time within shift window)
    - OR be within 15 minutes before shift start (early clock in allowed)
    - Cannot clock in if already clocked in
    
    Clock OUT rules:
    - Must have clocked in first
    - Will auto-complete shift if clocking out after shift end time
    """
    if clock_req.type not in ["IN", "OUT"]:
        raise HTTPException(status_code=400, detail="Tipo debe ser 'IN' o 'OUT'")
    
    # Get guard record for current user
    guard = await db.guards.find_one({"user_id": current_user["id"]})
    if not guard:
        raise HTTPException(status_code=404, detail="No tienes registro como empleado")
    
    if not guard.get("is_active", True):
        raise HTTPException(status_code=400, detail="Tu cuenta de empleado no está activa")
    
    condo_id = current_user.get("condominium_id")
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    today = now.date().isoformat()
    
    # Get today's clock logs for this employee
    today_logs = await db.hr_clock_logs.find({
        "employee_id": guard["id"],
        "date": today
    }).sort("timestamp", -1).to_list(100)
    
    # Variables for shift linking
    linked_shift_id = None
    shift_info = None
    
    if clock_req.type == "IN":
        # Check if already clocked in without clocking out
        if today_logs:
            last_log = today_logs[0]
            if last_log["type"] == "IN":
                raise HTTPException(status_code=400, detail="Ya tienes una entrada registrada. Debes registrar salida primero.")
        
        # Find active or upcoming shift for validation
        # Allow clock in if: within shift time OR up to 15 minutes before shift start
        early_window_future = (now + timedelta(minutes=15)).isoformat()
        
        active_shift = await db.shifts.find_one({
            "guard_id": guard["id"],
            "condominium_id": condo_id,
            "status": {"$in": ["scheduled", "in_progress"]},
            "$or": [
                # Currently within shift window
                {"start_time": {"$lte": now_iso}, "end_time": {"$gte": now_iso}},
                # OR shift starts within next 15 minutes (early clock-in allowed)
                {"start_time": {"$gt": now_iso, "$lte": early_window_future}}
            ]
        }, {"_id": 0})
        
        if not active_shift:
            # Check if there's any upcoming shift today
            today_end = f"{today}T23:59:59+00:00"
            upcoming_shift = await db.shifts.find_one({
                "guard_id": guard["id"],
                "condominium_id": condo_id,
                "status": "scheduled",
                "start_time": {"$gte": now_iso, "$lte": today_end}
            }, {"_id": 0})
            
            if upcoming_shift:
                shift_start_str = upcoming_shift["start_time"]
                # Ensure timezone-aware datetime
                if 'Z' in shift_start_str:
                    shift_start = datetime.fromisoformat(shift_start_str.replace('Z', '+00:00'))
                elif '+' in shift_start_str or shift_start_str.endswith('-00:00'):
                    shift_start = datetime.fromisoformat(shift_start_str)
                else:
                    shift_start = datetime.fromisoformat(shift_start_str).replace(tzinfo=timezone.utc)
                
                minutes_until = int((shift_start - now).total_seconds() / 60)
                raise HTTPException(
                    status_code=400, 
                    detail=f"Tu turno comienza en {minutes_until} minutos. Puedes fichar entrada 15 minutos antes."
                )
            else:
                raise HTTPException(
                    status_code=400, 
                    detail="No tienes un turno asignado para hoy. Contacta a tu supervisor."
                )
        
        linked_shift_id = active_shift["id"]
        shift_info = active_shift
        
        # Update shift status to in_progress
        await db.shifts.update_one(
            {"id": linked_shift_id},
            {"$set": {"status": "in_progress", "clock_in_time": now_iso}}
        )
    
    elif clock_req.type == "OUT":
        # Check if there's a clock in first
        if not today_logs:
            raise HTTPException(status_code=400, detail="No tienes entrada registrada hoy. Debes registrar entrada primero.")
        
        last_log = today_logs[0]
        if last_log["type"] == "OUT":
            raise HTTPException(status_code=400, detail="Ya registraste salida. Debes registrar entrada primero.")
        
        # Get linked shift from clock in
        linked_shift_id = last_log.get("shift_id")
        
        if linked_shift_id:
            shift_info = await db.shifts.find_one({"id": linked_shift_id}, {"_id": 0})
    
    clock_doc = {
        "id": str(uuid.uuid4()),
        "employee_id": guard["id"],
        "employee_name": guard.get("user_name") or guard.get("name") or "Sin nombre",
        "type": clock_req.type,
        "timestamp": now_iso,
        "date": today,
        "shift_id": linked_shift_id,
        "condominium_id": condo_id,
        "created_at": now_iso
    }
    
    await db.hr_clock_logs.insert_one(clock_doc)
    
    # Remove MongoDB _id
    clock_doc.pop("_id", None)
    
    # Calculate hours if clocking out
    hours_worked = None
    if clock_req.type == "OUT" and today_logs:
        last_in = next((log for log in today_logs if log["type"] == "IN"), None)
        if last_in:
            in_time = datetime.fromisoformat(last_in["timestamp"].replace('Z', '+00:00'))
            out_time = now
            hours_worked = round((out_time - in_time).total_seconds() / 3600, 2)
            
            # Update guard's total hours
            await db.guards.update_one(
                {"id": guard["id"]},
                {"$inc": {"total_hours": hours_worked}}
            )
            
            # Complete the shift if clocking out
            if linked_shift_id:
                await db.shifts.update_one(
                    {"id": linked_shift_id},
                    {"$set": {
                        "status": "completed",
                        "clock_out_time": now_iso,
                        "hours_worked": hours_worked,
                        "completed_at": now_iso
                    }}
                )
    
    await log_audit_event(
        AuditEventType.CLOCK_IN if clock_req.type == "IN" else AuditEventType.CLOCK_OUT,
        current_user["id"],
        "hr",
        {
            "employee_id": guard["id"], 
            "type": clock_req.type, 
            "hours_worked": hours_worked,
            "shift_id": linked_shift_id
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        **clock_doc,
        "hours_worked": hours_worked,
        "shift_info": shift_info,
        "message": f"{'Entrada' if clock_req.type == 'IN' else 'Salida'} registrada exitosamente"
    }

@router.get("/hr/clock/status")
async def get_clock_status(current_user = Depends(require_role("Guarda", "Administrador", "Supervisor", "HR"))):
    """Get current clock status for logged-in employee"""
    guard = await db.guards.find_one({"user_id": current_user["id"]})
    if not guard:
        return {"is_clocked_in": False, "message": "No tienes registro como empleado", "today_logs": []}
    
    today = datetime.now(timezone.utc).date().isoformat()
    
    today_logs = await db.hr_clock_logs.find({
        "employee_id": guard["id"],
        "date": today
    }).sort("timestamp", -1).to_list(100)
    
    if not today_logs:
        return {
            "is_clocked_in": False,
            "last_action": None,
            "last_time": None,
            "employee_id": guard["id"],
            "employee_name": guard.get("user_name") or guard.get("name") or "Sin nombre",
            "today_logs": []
        }
    
    last_log = today_logs[0]
    return {
        "is_clocked_in": last_log["type"] == "IN",
        "last_action": last_log["type"],
        "last_time": last_log["timestamp"],
        "employee_id": guard["id"],
        "employee_name": guard.get("user_name") or guard.get("name") or "Sin nombre",
        "today_logs": [{"type": log["type"], "timestamp": log["timestamp"]} for log in today_logs]
    }

@router.get("/hr/clock/history")
async def get_clock_history(
    employee_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda", "HR"))
):
    """Get clock history with filters - scoped by condominium"""
    # Build extra filters
    extra = {}
    
    # Guards can only see their own history
    if "Guarda" in current_user.get("roles", []) and "Administrador" not in current_user.get("roles", []):
        guard = await db.guards.find_one({"user_id": current_user["id"]})
        if guard:
            extra["employee_id"] = guard["id"]
    elif employee_id:
        extra["employee_id"] = employee_id
    
    if start_date:
        extra["date"] = {"$gte": start_date}
    if end_date:
        if "date" in extra:
            extra["date"]["$lte"] = end_date
        else:
            extra["date"] = {"$lte": end_date}
    
    # Use tenant_filter for multi-tenant scoping
    query = tenant_filter(current_user, extra if extra else None)
    
    logs = await db.hr_clock_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(500)
    return logs

# ==================== HR ABSENCES ====================

@router.post("/hr/absences")
async def create_absence_request(
    absence: AbsenceCreate,
    request: Request,
    current_user = Depends(require_role("Guarda", "Administrador", "Supervisor"))
):
    """Create a new absence request"""
    # Get guard record
    guard = await db.guards.find_one({"user_id": current_user["id"]})
    if not guard:
        raise HTTPException(status_code=404, detail="No tienes registro como empleado")
    
    # Validate dates
    try:
        start_dt = datetime.fromisoformat(absence.start_date)
        end_dt = datetime.fromisoformat(absence.end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")
    
    if start_dt > end_dt:
        raise HTTPException(status_code=400, detail="La fecha de inicio debe ser anterior o igual a la fecha de fin")
    
    # Validate type
    valid_types = ["vacaciones", "permiso_medico", "personal", "otro"]
    if absence.type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Use: {', '.join(valid_types)}")
    
    # Check for overlapping requests
    existing = await db.hr_absences.find({
        "employee_id": guard["id"],
        "status": {"$in": ["pending", "approved"]},
        "$or": [
            {"start_date": {"$lte": absence.end_date}, "end_date": {"$gte": absence.start_date}}
        ]
    }).to_list(100)
    
    if existing:
        raise HTTPException(status_code=400, detail="Ya tienes una solicitud para esas fechas")
    
    # Determine source based on role
    is_guard_request = "Guarda" in current_user.get("roles", []) and "Administrador" not in current_user.get("roles", [])
    
    absence_doc = {
        "id": str(uuid.uuid4()),
        "employee_id": guard["id"],
        "employee_name": guard.get("user_name") or guard.get("name") or "Sin nombre",
        "reason": absence.reason,
        "type": absence.type,
        "start_date": absence.start_date,
        "end_date": absence.end_date,
        "notes": absence.notes,
        "status": "pending",
        "source": "guard" if is_guard_request else "admin",
        "condominium_id": current_user.get("condominium_id"),
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.hr_absences.insert_one(absence_doc)
    
    # Remove MongoDB _id
    absence_doc.pop("_id", None)
    
    await log_audit_event(
        AuditEventType.ABSENCE_REQUESTED,
        current_user["id"],
        "hr",
        {
            "absence_id": absence_doc["id"], 
            "type": absence.type, 
            "dates": f"{absence.start_date} - {absence.end_date}",
            "source": absence_doc["source"],
            "guard_id": guard["id"],
            "condominium_id": absence_doc["condominium_id"]
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return absence_doc

@router.get("/hr/absences")
async def get_absences(
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda", "HR"))
):
    """Get absence requests with filters - scoped by condominium"""
    # Build extra filters
    extra = {}
    if status:
        if status not in ["pending", "approved", "rejected"]:
            raise HTTPException(status_code=400, detail="Estado inválido")
        extra["status"] = status
    
    # Use tenant_filter for multi-tenant scoping
    query = tenant_filter(current_user, extra if extra else None)
    
    # Guards can only see their own absences
    if "Guarda" in current_user.get("roles", []) and "Administrador" not in current_user.get("roles", []):
        guard = await db.guards.find_one({"user_id": current_user["id"]})
        if guard:
            query["employee_id"] = guard["id"]
    elif employee_id:
        query["employee_id"] = employee_id
    
    absences = await db.hr_absences.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return absences

@router.get("/hr/absences/{absence_id}")
async def get_absence(absence_id: str, current_user = Depends(require_role("Administrador", "Supervisor", "Guarda", "HR"))):
    """Get a single absence request - must belong to user's condominium"""
    # Use get_tenant_resource for automatic 404/403 handling
    absence = await get_tenant_resource(db.hr_absences, absence_id, current_user)
    return absence

@router.put("/hr/absences/{absence_id}/approve")
async def approve_absence(
    absence_id: str,
    request: Request,
    admin_notes: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor", "HR"))
):
    """Approve an absence request"""
    # Use get_tenant_resource for tenant validation
    absence = await get_tenant_resource(db.hr_absences, absence_id, current_user)
    
    if absence["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"La solicitud ya fue {absence['status']}")
    
    await db.hr_absences.update_one(
        {"id": absence_id},
        {"$set": {
            "status": "approved",
            "approved_by": current_user["id"],
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "admin_notes": admin_notes
        }}
    )
    
    await log_audit_event(
        AuditEventType.ABSENCE_APPROVED,
        current_user["id"],
        "hr",
        {"absence_id": absence_id, "employee_id": absence["employee_id"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    updated = await db.hr_absences.find_one({"id": absence_id}, {"_id": 0})
    return updated

@router.put("/hr/absences/{absence_id}/reject")
async def reject_absence(
    absence_id: str,
    request: Request,
    admin_notes: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor", "HR"))
):
    """Reject an absence request - must belong to user's condominium"""
    # Use get_tenant_resource for tenant validation
    absence = await get_tenant_resource(db.hr_absences, absence_id, current_user)
    
    if absence["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"La solicitud ya fue {absence['status']}")
    
    await db.hr_absences.update_one(
        {"id": absence_id},
        {"$set": {
            "status": "rejected",
            "rejected_by": current_user["id"],
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "admin_notes": admin_notes
        }}
    )
    
    await log_audit_event(
        AuditEventType.ABSENCE_REJECTED,
        current_user["id"],
        "hr",
        {"absence_id": absence_id, "employee_id": absence["employee_id"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    updated = await db.hr_absences.find_one({"id": absence_id}, {"_id": 0})
    return updated

@router.get("/hr/payroll")
async def get_payroll(current_user = Depends(require_role("Administrador", "HR"))):
    """Get payroll data - scoped by condominium"""
    # Use tenant_filter for multi-tenant scoping
    query = tenant_filter(current_user)
    guards = await db.guards.find(query, {"_id": 0}).to_list(100)
    payroll = []
    for guard in guards:
        payroll.append({
            "guard_id": guard["id"],
            "guard_name": guard.get("user_name") or guard.get("name") or "Sin nombre",
            "badge_number": guard.get("badge_number", "N/A"),
            "hourly_rate": guard.get("hourly_rate", 0),
            "total_hours": guard.get("total_hours", 0),
            "total_pay": guard.get("total_hours", 0) * guard.get("hourly_rate", 0)
        })
    return payroll

# ==================== HR RECRUITMENT ====================

@router.post("/hr/candidates")
async def create_candidate(
    candidate: CandidateCreate,
    request: Request,
    current_user = Depends(require_role_and_module("Administrador", "HR", module="hr"))
):
    """Create a new recruitment candidate"""
    # Check if email already exists
    existing = await db.hr_candidates.find_one({"email": candidate.email})
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un candidato con ese email")
    
    existing_user = await db.users.find_one({"email": candidate.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Este email ya está registrado como usuario")
    
    candidate_doc = {
        "id": str(uuid.uuid4()),
        "full_name": candidate.full_name,
        "email": candidate.email,
        "phone": candidate.phone,
        "position": candidate.position,
        "experience_years": candidate.experience_years,
        "notes": candidate.notes,
        "documents": candidate.documents or [],
        "status": "applied",  # applied, interview, hired, rejected
        "condominium_id": current_user.get("condominium_id"),
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.hr_candidates.insert_one(candidate_doc)
    candidate_doc.pop("_id", None)
    
    await log_audit_event(
        AuditEventType.CANDIDATE_CREATED,
        current_user["id"],
        "hr",
        {"candidate_id": candidate_doc["id"], "name": candidate.full_name, "position": candidate.position},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return candidate_doc

@router.get("/hr/candidates")
async def get_candidates(
    status: Optional[str] = None,
    position: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "HR"))
):
    """List recruitment candidates - scoped by condominium"""
    # Build extra filters
    extra = {}
    if status:
        extra["status"] = status
    if position:
        extra["position"] = position
    
    # Use tenant_filter for multi-tenant scoping
    query = tenant_filter(current_user, extra if extra else None)
    
    candidates = await db.hr_candidates.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return candidates

@router.get("/hr/candidates/{candidate_id}")
async def get_candidate(
    candidate_id: str,
    current_user = Depends(require_role("Administrador", "HR"))
):
    """Get a single candidate - must belong to user's condominium"""
    # Use get_tenant_resource for tenant validation
    candidate = await get_tenant_resource(db.hr_candidates, candidate_id, current_user)
    return candidate

@router.put("/hr/candidates/{candidate_id}")
async def update_candidate(
    candidate_id: str,
    update: CandidateUpdate,
    request: Request,
    current_user = Depends(require_role("Administrador", "HR"))
):
    """Update candidate information - must belong to user's condominium"""
    # Use get_tenant_resource for tenant validation
    candidate = await get_tenant_resource(db.hr_candidates, candidate_id, current_user)
    
    update_data = {}
    if update.full_name is not None:
        update_data["full_name"] = update.full_name
    if update.phone is not None:
        update_data["phone"] = update.phone
    if update.position is not None:
        update_data["position"] = update.position
    if update.experience_years is not None:
        update_data["experience_years"] = update.experience_years
    if update.notes is not None:
        update_data["notes"] = update.notes
    if update.status is not None:
        if update.status not in ["applied", "interview", "hired", "rejected"]:
            raise HTTPException(status_code=400, detail="Estado inválido")
        update_data["status"] = update.status
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["updated_by"] = current_user["id"]
    
    await db.hr_candidates.update_one({"id": candidate_id}, {"$set": update_data})
    
    await log_audit_event(
        AuditEventType.CANDIDATE_UPDATED,
        current_user["id"],
        "hr",
        {"candidate_id": candidate_id, "updated_fields": list(update_data.keys())},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    updated = await db.hr_candidates.find_one({"id": candidate_id}, {"_id": 0})
    return updated

@router.post("/hr/candidates/{candidate_id}/hire")
async def hire_candidate(
    candidate_id: str,
    hire_data: HireCandidate,
    request: Request,
    current_user = Depends(require_role("Administrador", "HR"))
):
    """Hire a candidate - must belong to user's condominium"""
    # Use get_tenant_resource for tenant validation
    candidate = await get_tenant_resource(db.hr_candidates, candidate_id, current_user)
    
    if candidate["status"] == "hired":
        raise HTTPException(status_code=400, detail="Este candidato ya fue contratado")
    
    if candidate["status"] == "rejected":
        raise HTTPException(status_code=400, detail="Este candidato fue rechazado")
    
    # Check email not already in use
    existing_user = await db.users.find_one({"email": candidate["email"]})
    if existing_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado como usuario")
    
    # Check badge number not in use
    existing_badge = await db.guards.find_one({"badge_number": hire_data.badge_number})
    if existing_badge:
        raise HTTPException(status_code=400, detail="El número de identificación ya está en uso")
    
    condominium_id = current_user.get("condominium_id") or candidate.get("condominium_id")
    
    # 1. Create user account
    user_id = str(uuid.uuid4())
    role = RoleEnum.GUARDA if candidate["position"] in ["Guarda", "Guard"] else RoleEnum.SUPERVISOR
    
    user_doc = {
        "id": user_id,
        "email": candidate["email"],
        "hashed_password": hash_password(hire_data.password),
        "full_name": candidate["full_name"],
        "roles": [role.value],
        "condominium_id": condominium_id,
        "is_active": True,
        "is_locked": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    # 2. Create guard/employee record
    guard_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_name": candidate["full_name"],
        "email": candidate["email"],
        "badge_number": hire_data.badge_number,
        "phone": candidate["phone"],
        "emergency_contact": "",
        "hire_date": datetime.now(timezone.utc).date().isoformat(),
        "hourly_rate": hire_data.hourly_rate,
        "is_active": True,
        "total_hours": 0,
        "condominium_id": condominium_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.guards.insert_one(guard_doc)
    
    # 3. Update candidate status
    await db.hr_candidates.update_one(
        {"id": candidate_id},
        {"$set": {
            "status": "hired",
            "hired_at": datetime.now(timezone.utc).isoformat(),
            "hired_by": current_user["id"],
            "user_id": user_id,
            "guard_id": guard_doc["id"]
        }}
    )
    
    await log_audit_event(
        AuditEventType.CANDIDATE_HIRED,
        current_user["id"],
        "hr",
        {
            "candidate_id": candidate_id,
            "user_id": user_id,
            "guard_id": guard_doc["id"],
            "name": candidate["full_name"],
            "position": candidate["position"]
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "message": f"Candidato {candidate['full_name']} contratado exitosamente",
        "user_id": user_id,
        "guard_id": guard_doc["id"],
        "email": candidate["email"],
        "credentials": {
            "email": candidate["email"],
            "password": "********"  # Don't return actual password
        }
    }

@router.put("/hr/candidates/{candidate_id}/reject")
async def reject_candidate(
    candidate_id: str,
    request: Request,
    reason: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "HR"))
):
    """Reject a candidate"""
    candidate = await db.hr_candidates.find_one({"id": candidate_id})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
    if candidate["status"] == "hired":
        raise HTTPException(status_code=400, detail="No se puede rechazar un candidato ya contratado")
    
    await db.hr_candidates.update_one(
        {"id": candidate_id},
        {"$set": {
            "status": "rejected",
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "rejected_by": current_user["id"],
            "rejection_reason": reason
        }}
    )
    
    await log_audit_event(
        AuditEventType.CANDIDATE_REJECTED,
        current_user["id"],
        "hr",
        {"candidate_id": candidate_id, "name": candidate["full_name"], "reason": reason},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": f"Candidato {candidate['full_name']} rechazado"}

# ==================== HR EMPLOYEE MANAGEMENT ====================

@router.post("/hr/employees")
async def create_employee_directly(
    employee: CreateEmployeeByHR,
    request: Request,
    current_user = Depends(require_role_and_module("Administrador", "HR", module="hr"))
):
    """Create a new employee (guard) directly without recruitment"""
    # Check email not in use
    existing_user = await db.users.find_one({"email": employee.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # Check badge number
    existing_badge = await db.guards.find_one({"badge_number": employee.badge_number})
    if existing_badge:
        raise HTTPException(status_code=400, detail="El número de identificación ya está en uso")
    
    condominium_id = current_user.get("condominium_id")
    
    # 1. Create user account
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": employee.email,
        "hashed_password": hash_password(employee.password),
        "full_name": employee.full_name,
        "roles": [RoleEnum.GUARDA.value],
        "condominium_id": condominium_id,
        "is_active": True,
        "is_locked": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    # 2. Create guard record
    guard_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_name": employee.full_name,
        "email": employee.email,
        "badge_number": employee.badge_number,
        "phone": employee.phone,
        "emergency_contact": employee.emergency_contact,
        "hire_date": datetime.now(timezone.utc).date().isoformat(),
        "hourly_rate": employee.hourly_rate,
        "is_active": True,
        "total_hours": 0,
        "condominium_id": condominium_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.guards.insert_one(guard_doc)
    
    await log_audit_event(
        AuditEventType.EMPLOYEE_CREATED,
        current_user["id"],
        "hr",
        {"user_id": user_id, "guard_id": guard_doc["id"], "name": employee.full_name},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "message": f"Empleado {employee.full_name} creado exitosamente",
        "user_id": user_id,
        "guard_id": guard_doc["id"],
        "credentials": {
            "email": employee.email,
            "password": "********"
        }
    }

@router.put("/hr/employees/{guard_id}/deactivate")
async def deactivate_employee(
    guard_id: str,
    request: Request,
    current_user = Depends(require_role("Administrador", "HR"))
):
    """Deactivate an employee"""
    guard = await db.guards.find_one({"id": guard_id})
    if not guard:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    # Deactivate guard record
    await db.guards.update_one(
        {"id": guard_id},
        {"$set": {"is_active": False, "deactivated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Deactivate user account if user_id exists
    user_id = guard.get("user_id")
    if user_id:
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"is_active": False}}
        )
    
    # Get employee name safely
    employee_name = guard.get("user_name") or guard.get("name") or guard.get("full_name") or "desconocido"
    
    await log_audit_event(
        AuditEventType.EMPLOYEE_DEACTIVATED,
        current_user["id"],
        "hr",
        {"guard_id": guard_id, "user_id": user_id, "name": employee_name},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": f"Empleado {employee_name} desactivado"}

@router.put("/hr/employees/{guard_id}/activate")
async def activate_employee(
    guard_id: str,
    request: Request,
    current_user = Depends(require_role("Administrador", "HR"))
):
    """Reactivate an employee"""
    guard = await db.guards.find_one({"id": guard_id})
    if not guard:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    # Activate guard record
    await db.guards.update_one(
        {"id": guard_id},
        {"$set": {"is_active": True, "reactivated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Activate user account if user_id exists
    user_id = guard.get("user_id")
    if user_id:
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"is_active": True}}
        )
    
    # Get employee name safely
    employee_name = guard.get("user_name") or guard.get("name") or guard.get("full_name") or "desconocido"
    
    await log_audit_event(
        AuditEventType.EMPLOYEE_ACTIVATED,
        current_user["id"],
        "hr",
        {"guard_id": guard_id, "user_id": user_id, "name": employee_name},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": f"Empleado {employee_name} reactivado"}

# ==================== HR PERFORMANCE EVALUATIONS ====================

@router.post("/hr/evaluations")
async def create_evaluation(
    evaluation: EvaluationCreate,
    request: Request,
    current_user = Depends(require_role_and_module("Administrador", "HR", "Supervisor", module="hr"))
):
    """Create a new performance evaluation for an employee"""
    condominium_id = current_user.get("condominium_id")
    
    # First try to find in guards collection
    employee = await db.guards.find_one({"id": evaluation.employee_id})
    employee_name = None
    
    if employee:
        # Verify same condominium (multi-tenant isolation)
        if employee.get("condominium_id") != condominium_id:
            raise HTTPException(status_code=403, detail="No puedes evaluar empleados de otro condominio")
        employee_name = employee["user_name"]
        
        # Cannot evaluate yourself
        evaluator_guard = await db.guards.find_one({"user_id": current_user["id"]})
        if evaluator_guard and evaluator_guard["id"] == evaluation.employee_id:
            raise HTTPException(status_code=400, detail="No puedes evaluarte a ti mismo")
    else:
        # Try to find in users collection (for users with employee roles but no guard record)
        employee = await db.users.find_one({
            "id": evaluation.employee_id,
            "condominium_id": condominium_id,
            "roles": {"$in": ["Guarda", "Supervisor", "HR"]}
        })
        
        if not employee:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        
        employee_name = employee.get("full_name", "Unknown")
        
        # Cannot evaluate yourself
        if employee["id"] == current_user["id"]:
            raise HTTPException(status_code=400, detail="No puedes evaluarte a ti mismo")
    
    # Calculate average score
    categories = evaluation.categories
    avg_score = round((categories.discipline + categories.punctuality + 
                       categories.performance + categories.communication) / 4, 2)
    
    evaluation_doc = {
        "id": str(uuid.uuid4()),
        "employee_id": evaluation.employee_id,
        "employee_name": employee_name,
        "evaluator_id": current_user["id"],
        "evaluator_name": current_user.get("full_name", "Unknown"),
        "categories": {
            "discipline": categories.discipline,
            "punctuality": categories.punctuality,
            "performance": categories.performance,
            "communication": categories.communication
        },
        "score": avg_score,
        "comments": evaluation.comments,
        "condominium_id": condominium_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.hr_evaluations.insert_one(evaluation_doc)
    evaluation_doc.pop("_id", None)
    
    await log_audit_event(
        AuditEventType.EVALUATION_CREATED,
        current_user["id"],
        "hr",
        {
            "evaluation_id": evaluation_doc["id"],
            "employee_id": evaluation.employee_id,
            "employee_name": employee_name,
            "score": avg_score,
            "condominium_id": condominium_id
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return evaluation_doc

@router.get("/hr/evaluations")
async def get_evaluations(
    employee_id: Optional[str] = None,
    request: Request = None,
    current_user = Depends(require_module("hr"))
):
    """Get evaluations - HR/Admin sees all in condominium, employees see only their own"""
    user_roles = current_user.get("roles", [])
    condominium_id = current_user.get("condominium_id")
    
    # Build query based on role
    query = {"condominium_id": condominium_id}
    
    # Check if user is HR, Admin, Supervisor or SuperAdmin
    is_hr_or_admin = any(role in user_roles for role in ["Administrador", "HR", "Supervisor", "SuperAdmin"])
    
    if is_hr_or_admin:
        # HR/Admin can filter by employee or see all
        if employee_id:
            query["employee_id"] = employee_id
    else:
        # Regular employees (Guard) can only see their own evaluations
        guard = await db.guards.find_one({"user_id": current_user["id"]})
        if guard:
            query["employee_id"] = guard["id"]
        else:
            # No guard record = no evaluations
            return []
    
    evaluations = await db.hr_evaluations.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return evaluations

@router.get("/hr/evaluations/{evaluation_id}")
async def get_evaluation(
    evaluation_id: str,
    current_user = Depends(get_current_user)
):
    """Get a specific evaluation by ID"""
    evaluation = await db.hr_evaluations.find_one({"id": evaluation_id}, {"_id": 0})
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    
    # Check condominium access
    if evaluation.get("condominium_id") != current_user.get("condominium_id"):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta evaluación")
    
    user_roles = current_user.get("roles", [])
    is_hr_or_admin = any(role in user_roles for role in ["Administrador", "HR", "Supervisor", "SuperAdmin"])
    
    # If not HR/Admin, check if it's their own evaluation
    if not is_hr_or_admin:
        guard = await db.guards.find_one({"user_id": current_user["id"]})
        if not guard or evaluation["employee_id"] != guard["id"]:
            raise HTTPException(status_code=403, detail="Solo puedes ver tus propias evaluaciones")
    
    return evaluation

@router.get("/hr/evaluations/employee/{employee_id}/summary")
async def get_employee_evaluation_summary(
    employee_id: str,
    current_user = Depends(get_current_user)
):
    """Get evaluation summary for an employee (average scores, count, etc.)"""
    user_roles = current_user.get("roles", [])
    condominium_id = current_user.get("condominium_id")
    
    # Verify employee exists - check guards first, then users
    employee = await db.guards.find_one({"id": employee_id})
    employee_name = None
    
    if employee:
        if employee.get("condominium_id") != condominium_id:
            raise HTTPException(status_code=403, detail="No tienes acceso a este empleado")
        employee_name = employee["user_name"]
    else:
        # Try users collection
        employee = await db.users.find_one({
            "id": employee_id,
            "condominium_id": condominium_id,
            "roles": {"$in": ["Guarda", "Supervisor", "HR"]}
        })
        if not employee:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        employee_name = employee.get("full_name", "Unknown")
    
    # Check permissions - HR/Admin can see all, employees only their own
    is_hr_or_admin = any(role in user_roles for role in ["Administrador", "HR", "Supervisor", "SuperAdmin"])
    if not is_hr_or_admin:
        # Check if this is the current user's evaluation
        if employee_id != current_user["id"]:
            guard = await db.guards.find_one({"user_id": current_user["id"]})
            if not guard or guard["id"] != employee_id:
                raise HTTPException(status_code=403, detail="Solo puedes ver tus propias evaluaciones")
    
    # Get all evaluations for this employee
    evaluations = await db.hr_evaluations.find(
        {"employee_id": employee_id, "condominium_id": condominium_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    if not evaluations:
        return {
            "employee_id": employee_id,
            "employee_name": employee_name,
            "total_evaluations": 0,
            "average_score": 0,
            "category_averages": {
                "discipline": 0,
                "punctuality": 0,
                "performance": 0,
                "communication": 0
            },
            "last_evaluation": None,
            "evaluations": []
        }
    
    # Calculate averages
    total = len(evaluations)
    avg_score = round(sum(e["score"] for e in evaluations) / total, 2)
    
    category_averages = {
        "discipline": round(sum(e["categories"]["discipline"] for e in evaluations) / total, 2),
        "punctuality": round(sum(e["categories"]["punctuality"] for e in evaluations) / total, 2),
        "performance": round(sum(e["categories"]["performance"] for e in evaluations) / total, 2),
        "communication": round(sum(e["categories"]["communication"] for e in evaluations) / total, 2)
    }
    
    return {
        "employee_id": employee_id,
        "employee_name": employee_name,
        "total_evaluations": total,
        "average_score": avg_score,
        "category_averages": category_averages,
        "last_evaluation": evaluations[0]["created_at"] if evaluations else None,
        "evaluations": evaluations[:10]  # Last 10 evaluations
    }

@router.get("/hr/evaluable-employees")
async def get_evaluable_employees(
    current_user = Depends(require_role("Administrador", "HR", "Supervisor"))
):
    """Get all employees that can be evaluated (guards + users with employee roles)"""
    condominium_id = current_user.get("condominium_id")
    
    # Get guards from guards collection
    guards = await db.guards.find(
        {"condominium_id": condominium_id, "is_active": {"$ne": False}},
        {"_id": 0}
    ).to_list(100)
    
    # Get existing guard user IDs to avoid duplicates
    guard_user_ids = {g.get("user_id") for g in guards if g.get("user_id")}
    
    # Get users with employee roles that don't have guard records
    users = await db.users.find(
        {
            "condominium_id": condominium_id,
            "roles": {"$in": ["Guarda", "Supervisor", "HR"]},
            "is_active": {"$ne": False},
            "id": {"$nin": list(guard_user_ids)}
        },
        {"_id": 0, "id": 1, "full_name": 1, "email": 1, "roles": 1}
    ).to_list(100)
    
    # Convert users to employee format
    user_employees = [
        {
            "id": u["id"],
            "user_id": u["id"],
            "user_name": u.get("full_name", u.get("email", "Unknown")),
            "position": u.get("roles", ["Empleado"])[0] if u.get("roles") else "Empleado",
            "condominium_id": condominium_id,
            "is_active": True
        }
        for u in users
    ]
    
    # Combine and return
    all_employees = guards + user_employees
    return all_employees

