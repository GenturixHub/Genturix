"""GENTURIX - Reservations Module Router (Auto-extracted from server.py)"""
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

# ==================== RESERVATIONS MODULE ====================

async def check_module_enabled(condo_id: str, module_name: str):
    """Helper to check if a module is enabled for a condominium"""
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "modules": 1})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    modules = condo.get("modules", {})
    module_config = modules.get(module_name, False)
    
    # Handle both boolean and dict formats
    is_enabled = False
    if isinstance(module_config, bool):
        is_enabled = module_config
    elif isinstance(module_config, dict):
        is_enabled = module_config.get("enabled", False)
    
    if not is_enabled:
        raise HTTPException(status_code=403, detail=f"Módulo '{module_name}' no está habilitado para este condominio")
    return True

@router.get("/reservations/areas")
async def get_areas(current_user = Depends(get_current_user)):
    """Get all areas for reservations in the user's condominium"""
    condo_id = current_user.get("condominium_id")
    if not condo_id and "SuperAdmin" not in current_user.get("roles", []):
        raise HTTPException(status_code=400, detail="Usuario no asignado a condominio")
    
    if condo_id:
        await check_module_enabled(condo_id, "reservations")
    
    # Use tenant_filter for automatic scoping
    query = tenant_filter(current_user, {"is_active": True})
    
    areas = await db.reservation_areas.find(query, {"_id": 0}).to_list(100)
    
    return areas

@router.post("/reservations/areas")
async def create_area(
    area_data: AreaCreate,
    request: Request,
    current_user = Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN))
):
    """Create a new area for reservations (Admin or SuperAdmin)"""
    # SuperAdmin can pass condominium_id, Admin uses their own
    condo_id = area_data.condominium_id if hasattr(area_data, 'condominium_id') and area_data.condominium_id else current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asignado a condominio")
    
    await check_module_enabled(condo_id, "reservations")
    
    area_id = str(uuid.uuid4())
    area_doc = {
        "id": area_id,
        "condominium_id": condo_id,
        "name": area_data.name,
        "area_type": area_data.area_type.value,
        "capacity": area_data.capacity,
        "description": area_data.description,
        "rules": area_data.rules,
        "available_from": area_data.available_from,
        "available_until": area_data.available_until,
        "requires_approval": area_data.requires_approval,
        "reservation_mode": area_data.reservation_mode,
        "min_duration_hours": area_data.min_duration_hours,
        "max_duration_hours": area_data.max_duration_hours,
        "max_reservations_per_day": area_data.max_reservations_per_day,
        "slot_duration_minutes": area_data.slot_duration_minutes,
        "allowed_days": area_data.allowed_days,
        "is_active": area_data.is_active,
        # NEW: Phase 1 fields (backward compatible defaults)
        "reservation_behavior": area_data.reservation_behavior or "exclusive",
        "max_capacity_per_slot": area_data.max_capacity_per_slot,
        "max_reservations_per_user_per_day": area_data.max_reservations_per_user_per_day,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.reservation_areas.insert_one(area_doc)
    
    await log_audit_event(
        AuditEventType.ACCESS_GRANTED,
        current_user["id"],
        "reservations",
        {"action": "area_created", "area_id": area_id, "name": area_data.name},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": f"Área '{area_data.name}' creada exitosamente", "area_id": area_id}

@router.patch("/reservations/areas/{area_id}")
async def update_area(
    area_id: str,
    area_data: AreaUpdate,
    request: Request,
    current_user = Depends(require_role("Administrador"))
):
    """Update an area (Admin only)"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asignado a condominio")
    
    # Check area exists and belongs to this condo
    area = await db.reservation_areas.find_one({"id": area_id, "condominium_id": condo_id})
    if not area:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    
    update_fields = {k: v for k, v in area_data.model_dump().items() if v is not None}
    if "area_type" in update_fields:
        update_fields["area_type"] = update_fields["area_type"].value
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.reservation_areas.update_one({"id": area_id}, {"$set": update_fields})
    
    await log_audit_event(
        AuditEventType.ACCESS_GRANTED,
        current_user["id"],
        "reservations",
        {"action": "area_updated", "area_id": area_id},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "Área actualizada exitosamente"}

@router.delete("/reservations/areas/{area_id}")
async def delete_area(
    area_id: str,
    request: Request,
    current_user = Depends(require_role("Administrador"))
):
    """Soft delete an area (Admin only)"""
    condo_id = current_user.get("condominium_id")
    
    result = await db.reservation_areas.update_one(
        {"id": area_id, "condominium_id": condo_id},
        {"$set": {"is_active": False, "deleted_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    
    await log_audit_event(
        AuditEventType.ACCESS_GRANTED,
        current_user["id"],
        "reservations",
        {"action": "area_deleted", "area_id": area_id},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "Área eliminada exitosamente"}

@router.get("/reservations")
async def get_reservations(
    date: Optional[str] = None,
    area_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Get reservations for the condominium"""
    condo_id = current_user.get("condominium_id")
    if not condo_id and "SuperAdmin" not in current_user.get("roles", []):
        raise HTTPException(status_code=400, detail="Usuario no asignado a condominio")
    
    if condo_id:
        await check_module_enabled(condo_id, "reservations")
    
    # Build extra filters
    extra = {}
    if date:
        extra["date"] = date
    if area_id:
        extra["area_id"] = area_id
    if status:
        extra["status"] = status
    
    # Use tenant_filter for automatic scoping
    query = tenant_filter(current_user, extra if extra else None)
    
    # Non-admins only see their own reservations
    if "Administrador" not in current_user.get("roles", []) and "Guarda" not in current_user.get("roles", []) and "SuperAdmin" not in current_user.get("roles", []):
        query["resident_id"] = current_user["id"]
    
    reservations = await db.reservations.find(query, {"_id": 0}).sort("date", 1).to_list(200)
    
    # Enrich with area and user info
    for res in reservations:
        area = await db.reservation_areas.find_one({"id": res.get("area_id")}, {"_id": 0, "name": 1, "area_type": 1})
        if area:
            res["area_name"] = area.get("name")
            res["area_type"] = area.get("area_type")
        user = await db.users.find_one({"id": res.get("resident_id")}, {"_id": 0, "full_name": 1, "profile_photo": 1})
        if user:
            res["resident_name"] = user.get("full_name")
            res["resident_photo"] = user.get("profile_photo")
    
    return reservations

# Day name mapping for validation
DAY_NAMES = {
    0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 
    4: "Viernes", 5: "Sábado", 6: "Domingo"
}

@router.post("/reservations")
async def create_reservation(
    reservation: ReservationCreate,
    request: Request,
    current_user = Depends(get_current_user)
):
    """Create a new reservation (Resident)"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asignado a condominio")
    
    await check_module_enabled(condo_id, "reservations")
    
    # Check area exists and is active
    area = await db.reservation_areas.find_one({"id": reservation.area_id, "condominium_id": condo_id, "is_active": True})
    if not area:
        raise HTTPException(status_code=404, detail="Área no encontrada o no disponible")
    
    # Check capacity
    if reservation.guests_count > area.get("capacity", 10):
        raise HTTPException(status_code=400, detail=f"El área solo permite {area['capacity']} personas")
    
    # Validate time is within area's available hours (closing time)
    area_from = area.get("available_from", "06:00")
    area_until = area.get("available_until", "22:00")
    if reservation.start_time < area_from or reservation.end_time > area_until:
        raise HTTPException(status_code=400, detail=f"El horario debe estar entre {area_from} y {area_until}. Cierra a las {area_until}.")
    
    # ==================== VALIDATE DURATION BASED ON AREA MODE ====================
    reservation_mode = area.get("reservation_mode", "flexible")
    min_duration = area.get("min_duration_hours", 1)
    max_duration = area.get("max_duration_hours", area.get("max_hours_per_reservation", 4))
    
    # Calculate reservation duration in hours
    try:
        start_parts = reservation.start_time.split(":")
        end_parts = reservation.end_time.split(":")
        start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
        end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
        duration_hours = (end_minutes - start_minutes) / 60
        
        if duration_hours < min_duration:
            raise HTTPException(status_code=400, detail=f"La reservación debe ser de al menos {min_duration} hora(s)")
        
        if duration_hours > max_duration:
            raise HTTPException(status_code=400, detail=f"La reservación no puede exceder {max_duration} hora(s)")
        
        # For "por_hora" mode (gym), enforce exactly 1 hour
        if reservation_mode == "por_hora" and duration_hours != 1:
            raise HTTPException(status_code=400, detail="Este tipo de área solo permite reservaciones de 1 hora")
        
        # For "bloque" mode (ranch), allow only full block
        if reservation_mode == "bloque":
            # Must be the full block from opening to closing
            expected_duration = (int(area_until.split(":")[0]) - int(area_from.split(":")[0]))
            if duration_hours != expected_duration:
                raise HTTPException(status_code=400, detail=f"Este tipo de área requiere reservar el bloque completo ({area_from} - {area_until})")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de hora inválido. Use HH:MM")
    # ==============================================================================
    
    # Validate day is allowed
    try:
        res_date = datetime.strptime(reservation.date, "%Y-%m-%d")
        day_name = DAY_NAMES.get(res_date.weekday())
        allowed_days = area.get("allowed_days", list(DAY_NAMES.values()))
        if allowed_days and len(allowed_days) > 0 and day_name not in allowed_days:
            raise HTTPException(status_code=400, detail=f"Esta área no está disponible los días {day_name}")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")
    
    # Check max reservations per day for this area
    max_per_day = area.get("max_reservations_per_day", 10)
    daily_count = await db.reservations.count_documents({
        "area_id": reservation.area_id,
        "date": reservation.date,
        "status": {"$in": ["pending", "approved"]}
    })
    if daily_count >= max_per_day:
        raise HTTPException(status_code=400, detail=f"Se alcanzó el límite de {max_per_day} reservaciones para esta área en esta fecha")
    
    # NEW: Check max reservations per user per day (Phase 1)
    max_user_per_day = area.get("max_reservations_per_user_per_day")
    if max_user_per_day:
        user_daily_count = await db.reservations.count_documents({
            "area_id": reservation.area_id,
            "date": reservation.date,
            "resident_id": current_user["id"],
            "status": {"$in": ["pending", "approved"]}
        })
        if user_daily_count >= max_user_per_day:
            raise HTTPException(status_code=400, detail=f"Has alcanzado el límite de {max_user_per_day} reservación(es) por día para esta área")
    
    # Get reservation behavior (backward compatible)
    behavior = area.get("reservation_behavior", "exclusive")
    
    # FREE_ACCESS areas cannot be reserved
    if behavior == "free_access":
        raise HTTPException(status_code=400, detail="Esta área es de acceso libre y no requiere reservación")
    
    # Check for overlapping reservations based on behavior type
    if behavior == "capacity":
        # CAPACITY: Check if there's room in the slot
        max_capacity = area.get("max_capacity_per_slot") or area.get("capacity", 10)
        
        # Get all reservations that overlap with requested time
        overlapping = await db.reservations.find({
            "area_id": reservation.area_id,
            "date": reservation.date,
            "status": {"$in": ["pending", "approved"]},
            "start_time": {"$lt": reservation.end_time},
            "end_time": {"$gt": reservation.start_time}
        }, {"_id": 0, "guests_count": 1}).to_list(100)
        
        current_count = sum(r.get("guests_count", 1) for r in overlapping)
        if current_count + reservation.guests_count > max_capacity:
            raise HTTPException(
                status_code=409, 
                detail=f"No hay suficiente capacidad. Disponible: {max(0, max_capacity - current_count)}, Solicitado: {reservation.guests_count}"
            )
    else:
        # EXCLUSIVE or SLOT_BASED: Check for any overlap
        existing = await db.reservations.find_one({
            "area_id": reservation.area_id,
            "date": reservation.date,
            "status": {"$in": ["pending", "approved"]},
            "$or": [
                {"start_time": {"$lt": reservation.end_time}, "end_time": {"$gt": reservation.start_time}}
            ]
        })
        
        if existing:
            raise HTTPException(status_code=409, detail="Ya existe una reservación en ese horario")
    
    reservation_id = str(uuid.uuid4())
    status = "pending" if area.get("requires_approval", False) else "approved"
    
    # Sanitize user input
    sanitized_purpose = sanitize_text(reservation.purpose) if reservation.purpose else ""
    
    reservation_doc = {
        "id": reservation_id,
        "condominium_id": condo_id,
        "area_id": reservation.area_id,
        "resident_id": current_user["id"],
        "date": reservation.date,
        "start_time": reservation.start_time,
        "end_time": reservation.end_time,
        "purpose": sanitized_purpose,
        "guests_count": reservation.guests_count,
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.reservations.insert_one(reservation_doc)
    
    # If auto-approved, send notification to resident
    if status == "approved":
        await create_and_send_notification(
            user_id=current_user["id"],
            condominium_id=condo_id,
            notification_type="reservation_approved",
            title="✅ Reservación confirmada",
            message=f"{area['name']} el {reservation.date} de {reservation.start_time} a {reservation.end_time}",
            data={
                "reservation_id": reservation_id,
                "area_name": area["name"],
                "date": reservation.date,
                "start_time": reservation.start_time,
                "end_time": reservation.end_time
            },
            send_push=True,
            url="/resident?tab=reservations"
        )
    else:
        # Notify admins about pending reservation using dynamic targeting
        await send_targeted_push_notification(
            condominium_id=condo_id,
            title="📅 Nueva reservación pendiente",
            body=f"{current_user.get('full_name', 'Residente')} solicitó {area['name']} para {reservation.date}",
            target_roles=["Administrador", "Supervisor"],
            data={
                "type": "reservation_pending",
                "reservation_id": reservation_id,
                "url": "/admin/reservations"
            },
            tag=f"reservation-pending-{reservation_id[:8]}"
        )
    
    await log_audit_event(
        AuditEventType.ACCESS_GRANTED,
        current_user["id"],
        "reservations",
        {"action": "reservation_created", "reservation_id": reservation_id, "area": area["name"], "date": reservation.date},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id,
        user_email=current_user.get("email")
    )
    print(f"[FLOW] reservation_created | id={reservation_id} area={area['name']} date={reservation.date} condo={condo_id[:8]}")
    
    return {
        "message": "Reservación creada exitosamente",
        "reservation_id": reservation_id,
        "status": status,
        "requires_approval": area.get("requires_approval", False)
    }

@router.get("/reservations/availability/{area_id}")
async def get_area_availability(
    area_id: str,
    date: str,
    current_user = Depends(get_current_user)
):
    """Get availability for an area on a specific date"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asignado a condominio")
    
    # Get the area
    area = await db.reservation_areas.find_one({"id": area_id, "condominium_id": condo_id, "is_active": True})
    if not area:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    
    # Get existing reservations for this date
    existing = await db.reservations.find({
        "area_id": area_id,
        "date": date,
        "status": {"$in": ["pending", "approved"]}
    }, {"_id": 0, "start_time": 1, "end_time": 1, "status": 1}).to_list(50)
    
    # Check if day is allowed
    is_day_allowed = True
    day_name = None
    try:
        res_date = datetime.strptime(date, "%Y-%m-%d")
        day_name = DAY_NAMES.get(res_date.weekday())
        allowed_days = area.get("allowed_days", [])
        
        # If no allowed_days configured, all days are allowed
        if allowed_days and len(allowed_days) > 0:
            is_day_allowed = day_name in allowed_days
        else:
            is_day_allowed = True  # No restrictions = all days allowed
            
        # Also check if date is not in the past
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if res_date < today:
            is_day_allowed = False
    except ValueError:
        is_day_allowed = False
    
    # Check max reservations per day
    max_per_day = area.get("max_reservations_per_day", 10)
    reservations_count = len([r for r in existing if r.get("status") == "approved"])
    slots_remaining = max(0, max_per_day - reservations_count)
    
    # Calculate if area is available for reservation
    # Available if: day is allowed AND there are slots remaining
    is_available = is_day_allowed and slots_remaining > 0
    
    # Get operating hours
    available_from = area.get("available_from", "06:00")
    available_until = area.get("available_until", "22:00")
    
    # Generate time slots for the day
    time_slots = []
    try:
        start_hour = int(available_from.split(":")[0])
        end_hour = int(available_until.split(":")[0])
        
        for hour in range(start_hour, end_hour):
            slot_start = f"{str(hour).zfill(2)}:00"
            slot_end = f"{str(hour + 1).zfill(2)}:00"
            
            # Check if this slot is occupied
            slot_occupied = False
            for res in existing:
                res_start = res.get("start_time", "")
                res_end = res.get("end_time", "")
                # Check overlap
                if res_start <= slot_start < res_end or res_start < slot_end <= res_end:
                    slot_occupied = True
                    break
                if slot_start <= res_start < slot_end:
                    slot_occupied = True
                    break
            
            time_slots.append({
                "start_time": slot_start,
                "end_time": slot_end,
                "status": "occupied" if slot_occupied else "available"
            })
    except Exception as slot_err:
        logger.warning(f"[RESERVATIONS] Time slot parsing error: {slot_err}")
    
    # Get area configuration for frontend
    reservation_mode = area.get("reservation_mode", "flexible")
    min_duration = area.get("min_duration_hours", 1)
    max_duration = area.get("max_duration_hours", area.get("max_hours_per_reservation", 4))
    slot_duration = area.get("slot_duration_minutes", 60)
    
    return {
        "area_id": area_id,
        "area_name": area.get("name"),
        "area_type": area.get("area_type"),
        "date": date,
        "day_name": day_name,
        "is_day_allowed": is_day_allowed,
        "is_available": is_available,
        "available_from": available_from,
        "available_until": available_until,
        "capacity": area.get("capacity", 10),
        "max_reservations_per_day": max_per_day,
        "current_reservations": reservations_count,
        "slots_remaining": slots_remaining,
        "reserved_slots": existing,
        "time_slots": time_slots,
        # New: Area configuration for UI
        "reservation_mode": reservation_mode,
        "min_duration_hours": min_duration,
        "max_duration_hours": max_duration,
        "slot_duration_minutes": slot_duration,
        "message": None if is_available else (
            "Fecha no disponible (día no permitido)" if not is_day_allowed else
            "No hay espacios disponibles para esta fecha"
        )
    }


# ============================================
# NEW: SMART AVAILABILITY ENDPOINT (Phase 2-3)
# Returns detailed slot availability based on area behavior type
# ============================================
@router.get("/reservations/smart-availability/{area_id}")
async def get_smart_availability(
    area_id: str,
    date: str,
    current_user = Depends(get_current_user)
):
    """
    Get smart availability for an area based on its reservation_behavior type.
    Returns detailed slots with remaining capacity for CAPACITY type areas.
    Backward compatible: areas without reservation_behavior use EXCLUSIVE logic.
    """
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asignado a condominio")
    
    # Get the area
    area = await db.reservation_areas.find_one({"id": area_id, "condominium_id": condo_id, "is_active": True})
    if not area:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    
    # Get reservation behavior (default to EXCLUSIVE for backward compatibility)
    behavior = area.get("reservation_behavior", "exclusive")
    
    # FREE_ACCESS areas cannot be reserved
    if behavior == "free_access":
        return {
            "area_id": area_id,
            "area_name": area.get("name"),
            "reservation_behavior": behavior,
            "date": date,
            "is_available": False,
            "message": "Esta área es de acceso libre y no requiere reservación",
            "time_slots": []
        }
    
    # Parse and validate date
    try:
        res_date = datetime.strptime(date, "%Y-%m-%d")
        day_name = DAY_NAMES.get(res_date.weekday())
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Check if date is in the past
        if res_date < today:
            return {
                "area_id": area_id,
                "area_name": area.get("name"),
                "reservation_behavior": behavior,
                "date": date,
                "is_available": False,
                "message": "No se pueden hacer reservaciones en fechas pasadas",
                "time_slots": []
            }
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")
    
    # Check if day is allowed
    allowed_days = area.get("allowed_days", [])
    if allowed_days and len(allowed_days) > 0 and day_name not in allowed_days:
        return {
            "area_id": area_id,
            "area_name": area.get("name"),
            "reservation_behavior": behavior,
            "date": date,
            "day_name": day_name,
            "is_available": False,
            "message": f"El área no está disponible los {day_name}",
            "time_slots": []
        }
    
    # Get existing reservations for this date
    existing_reservations = await db.reservations.find({
        "area_id": area_id,
        "date": date,
        "status": {"$in": ["pending", "approved"]}
    }, {"_id": 0}).to_list(100)
    
    # Check user's reservations for this day (for max_reservations_per_user_per_day)
    max_user_per_day = area.get("max_reservations_per_user_per_day")
    user_reservations_today = 0
    if max_user_per_day:
        user_reservations_today = await db.reservations.count_documents({
            "area_id": area_id,
            "date": date,
            "resident_id": current_user["id"],
            "status": {"$in": ["pending", "approved"]}
        })
    
    user_can_reserve = max_user_per_day is None or user_reservations_today < max_user_per_day
    
    # Get operating hours
    available_from = area.get("available_from", "06:00")
    available_until = area.get("available_until", "22:00")
    slot_duration = area.get("slot_duration_minutes", 60)
    
    # Parse hours
    try:
        start_hour = int(available_from.split(":")[0])
        start_min = int(available_from.split(":")[1]) if ":" in available_from else 0
        end_hour = int(available_until.split(":")[0])
        end_min = int(available_until.split(":")[1]) if ":" in available_until else 0
    except Exception as parse_err:
        logger.debug(f"[RESERVATIONS] Time parse error, using defaults: {parse_err}")
        start_hour, start_min = 6, 0
        end_hour, end_min = 22, 0
    
    # Generate time slots based on behavior type
    time_slots = []
    
    if behavior == "exclusive":
        # EXCLUSIVE: 1 reservation blocks the entire area for that time
        current_time = start_hour * 60 + start_min
        end_time = end_hour * 60 + end_min
        
        while current_time < end_time:
            slot_start = f"{current_time // 60:02d}:{current_time % 60:02d}"
            slot_end_mins = min(current_time + slot_duration, end_time)
            slot_end = f"{slot_end_mins // 60:02d}:{slot_end_mins % 60:02d}"
            
            # Check if this slot overlaps with any existing reservation
            slot_occupied = False
            occupied_by = None
            for res in existing_reservations:
                res_start = res.get("start_time", "")
                res_end = res.get("end_time", "")
                # Check overlap
                if res_start < slot_end and res_end > slot_start:
                    slot_occupied = True
                    occupied_by = res.get("status")
                    break
            
            time_slots.append({
                "start": slot_start,
                "end": slot_end,
                "available": not slot_occupied and user_can_reserve,
                "status": "occupied" if slot_occupied else ("available" if user_can_reserve else "user_limit"),
                "remaining_slots": 0 if slot_occupied else 1,
                "total_capacity": 1
            })
            
            current_time += slot_duration
    
    elif behavior == "capacity":
        # CAPACITY: Multiple reservations allowed up to max_capacity_per_slot
        max_capacity = area.get("max_capacity_per_slot") or area.get("capacity", 10)
        current_time = start_hour * 60 + start_min
        end_time = end_hour * 60 + end_min
        
        while current_time < end_time:
            slot_start = f"{current_time // 60:02d}:{current_time % 60:02d}"
            slot_end_mins = min(current_time + slot_duration, end_time)
            slot_end = f"{slot_end_mins // 60:02d}:{slot_end_mins % 60:02d}"
            
            # Count reservations in this slot
            slot_reservations = 0
            for res in existing_reservations:
                res_start = res.get("start_time", "")
                res_end = res.get("end_time", "")
                # Check overlap
                if res_start < slot_end and res_end > slot_start:
                    slot_reservations += res.get("guests_count", 1)
            
            remaining = max(0, max_capacity - slot_reservations)
            slot_available = remaining > 0 and user_can_reserve
            
            # Determine status
            if remaining == 0:
                status = "full"
            elif remaining <= max_capacity * 0.3:
                status = "limited"  # Yellow - few spots left
            else:
                status = "available"
            
            if not user_can_reserve:
                status = "user_limit"
            
            time_slots.append({
                "start": slot_start,
                "end": slot_end,
                "available": slot_available,
                "status": status,
                "remaining_slots": remaining,
                "total_capacity": max_capacity,
                "current_count": slot_reservations
            })
            
            current_time += slot_duration
    
    elif behavior == "slot_based":
        # SLOT_BASED: Fixed slots, 1 reservation = 1 slot, no overlap allowed
        current_time = start_hour * 60 + start_min
        end_time = end_hour * 60 + end_min
        
        while current_time < end_time:
            slot_start = f"{current_time // 60:02d}:{current_time % 60:02d}"
            slot_end_mins = min(current_time + slot_duration, end_time)
            slot_end = f"{slot_end_mins // 60:02d}:{slot_end_mins % 60:02d}"
            
            # Check if exact slot is taken
            slot_taken = False
            for res in existing_reservations:
                if res.get("start_time") == slot_start and res.get("end_time") == slot_end:
                    slot_taken = True
                    break
            
            time_slots.append({
                "start": slot_start,
                "end": slot_end,
                "available": not slot_taken and user_can_reserve,
                "status": "occupied" if slot_taken else ("available" if user_can_reserve else "user_limit"),
                "remaining_slots": 0 if slot_taken else 1,
                "total_capacity": 1
            })
            
            current_time += slot_duration
    
    # Calculate overall availability
    available_slots = sum(1 for s in time_slots if s["available"])
    is_available = available_slots > 0
    
    # Build response
    return {
        "area_id": area_id,
        "area_name": area.get("name"),
        "area_type": area.get("area_type"),
        "reservation_behavior": behavior,
        "date": date,
        "day_name": day_name,
        "is_day_allowed": True,  # If we got here, day is allowed
        "is_available": is_available,
        "available_from": available_from,
        "available_until": available_until,
        "capacity": area.get("capacity", 10),
        "max_capacity_per_slot": area.get("max_capacity_per_slot"),
        "slot_duration_minutes": slot_duration,
        "time_slots": time_slots,
        "available_slots_count": available_slots,
        "total_slots_count": len(time_slots),
        # User limits info
        "user_reservations_today": user_reservations_today,
        "max_reservations_per_user_per_day": max_user_per_day,
        "user_can_reserve": user_can_reserve,
        # Area config for UI
        "min_duration_hours": area.get("min_duration_hours", 1),
        "max_duration_hours": area.get("max_duration_hours", 4),
        "requires_approval": area.get("requires_approval", False),
        "message": None if is_available else (
            "Has alcanzado el límite de reservaciones por día" if not user_can_reserve else
            "No hay espacios disponibles para esta fecha"
        )
    }


@router.patch("/reservations/{reservation_id}")
async def update_reservation_status(
    reservation_id: str,
    update: ReservationUpdate,
    request: Request,
    current_user = Depends(get_current_user)
):
    """Update reservation status (Admin approves/rejects, Resident cancels own)"""
    is_admin = "Administrador" in current_user.get("roles", []) or "SuperAdmin" in current_user.get("roles", [])
    
    # Use get_tenant_resource for tenant validation
    reservation = await get_tenant_resource(db.reservations, reservation_id, current_user)
    
    # Non-admin can only cancel their own reservations
    if not is_admin:
        if update.status != ReservationStatusEnum.CANCELLED:
            raise HTTPException(status_code=403, detail="Solo puedes cancelar tus propias reservaciones")
        if reservation.get("resident_id") != current_user["id"]:
            raise HTTPException(status_code=403, detail="No puedes modificar reservaciones de otros usuarios")
    
    update_fields = {
        "status": update.status.value,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["id"]
    }
    
    if update.admin_notes:
        update_fields["admin_notes"] = update.admin_notes
    
    await db.reservations.update_one({"id": reservation_id}, {"$set": update_fields})
    
    # Send push notification to resident based on new status
    resident_id = reservation.get("resident_id")
    condominium_id = reservation.get("condominium_id")  # Get condo_id from reservation
    area_id = reservation.get("area_id")
    area = await db.reservation_areas.find_one({"id": area_id}, {"_id": 0, "name": 1})
    area_name = area.get("name", "Área común") if area else "Área común"
    
    if resident_id and is_admin:
        if update.status == ReservationStatusEnum.APPROVED:
            await create_and_send_notification(
                user_id=resident_id,
                condominium_id=condominium_id,
                notification_type="reservation_approved",
                title="✅ Reservación aprobada",
                message=f"Tu reservación de {area_name} para el {reservation.get('date')} de {reservation.get('start_time')} a {reservation.get('end_time')} fue aprobada",
                data={
                    "reservation_id": reservation_id,
                    "area_name": area_name,
                    "date": reservation.get("date"),
                    "start_time": reservation.get("start_time"),
                    "end_time": reservation.get("end_time")
                },
                send_push=False,  # Disable old push, use targeted instead
                url="/resident?tab=reservations"
            )
            
            # PHASE 3: Send targeted push notification to resident owner
            await send_targeted_push_notification(
                condominium_id=condominium_id,
                title="✅ Reservación aprobada",
                body=f"Tu reservación de {area_name} para el {reservation.get('date')} fue aprobada",
                target_user_ids=[resident_id],
                exclude_user_ids=[current_user["id"]],
                data={
                    "type": "reservation_approved",
                    "reservation_id": reservation_id,
                    "area_name": area_name,
                    "date": reservation.get("date"),
                    "start_time": reservation.get("start_time"),
                    "end_time": reservation.get("end_time"),
                    "url": "/resident?tab=reservations"
                },
                tag=f"reservation-approved-{reservation_id[:8]}"
            )
        elif update.status == ReservationStatusEnum.REJECTED:
            reason = update.admin_notes or "Sin motivo especificado"
            await create_and_send_notification(
                user_id=resident_id,
                condominium_id=condominium_id,
                notification_type="reservation_rejected",
                title="❌ Reservación rechazada",
                message=f"Tu reservación de {area_name} fue rechazada. Motivo: {reason}",
                data={
                    "reservation_id": reservation_id,
                    "area_name": area_name,
                    "date": reservation.get("date"),
                    "reason": reason
                },
                send_push=False,  # Disable old push, use targeted instead
                url="/resident?tab=reservations"
            )
            
            # Send targeted push notification to resident owner for rejection too
            await send_targeted_push_notification(
                condominium_id=condominium_id,
                title="❌ Reservación rechazada",
                body=f"Tu reservación de {area_name} fue rechazada. Motivo: {reason}",
                target_user_ids=[resident_id],
                exclude_user_ids=[current_user["id"]],
                data={
                    "type": "reservation_rejected",
                    "reservation_id": reservation_id,
                    "area_name": area_name,
                    "date": reservation.get("date"),
                    "reason": reason,
                    "url": "/resident?tab=reservations"
                },
                tag=f"reservation-rejected-{reservation_id[:8]}"
            )
    
    await log_audit_event(
        AuditEventType.ACCESS_GRANTED,
        current_user["id"],
        "reservations",
        {"action": "reservation_updated", "reservation_id": reservation_id, "new_status": update.status.value},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": f"Reservación {update.status.value} exitosamente"}


# ==================== DELETE RESERVATION (CANCEL) ====================
class CancelReservationRequest(BaseModel):
    """Request body for cancellation with optional reason"""
    reason: Optional[str] = None

@router.delete("/reservations/{reservation_id}")
async def cancel_reservation(
    reservation_id: str,
    request: Request,
    body: Optional[CancelReservationRequest] = None,
    current_user = Depends(get_current_user)
):
    """
    Cancel a reservation (soft delete - changes status to 'cancelled')
    
    RULES:
    - Resident: Can only cancel their OWN reservations that are pending/approved and NOT yet started
    - Admin: Can cancel ANY reservation except 'completed' ones
    
    This endpoint liberates the slot so others can book it.
    """
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asignado a condominio")
    
    await check_module_enabled(condo_id, "reservations")
    
    user_roles = current_user.get("roles", [])
    is_admin = "Administrador" in user_roles or "SuperAdmin" in user_roles
    
    # Find the reservation
    reservation = await db.reservations.find_one({"id": reservation_id, "condominium_id": condo_id}, {"_id": 0})
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservación no encontrada")
    
    current_status = reservation.get("status", "")
    reservation_date = reservation.get("date", "")
    reservation_start = reservation.get("start_time", "00:00")
    resident_id = reservation.get("resident_id")
    
    # Get area info for notification
    area = await db.reservation_areas.find_one({"id": reservation.get("area_id")}, {"_id": 0, "name": 1})
    area_name = area.get("name", "Área común") if area else "Área común"
    
    # ==================== VALIDATION RULES ====================
    
    # Rule: Cannot cancel completed reservations (for anyone)
    if current_status == "completed":
        raise HTTPException(status_code=400, detail="No se puede cancelar una reservación ya completada")
    
    # Rule: Cannot cancel already cancelled reservations
    if current_status == "cancelled":
        raise HTTPException(status_code=400, detail="Esta reservación ya fue cancelada")
    
    # ==================== RESIDENT-SPECIFIC RULES ====================
    if not is_admin:
        # Resident can only cancel their own reservations
        if reservation.get("resident_id") != current_user["id"]:
            raise HTTPException(status_code=403, detail="Solo puedes cancelar tus propias reservaciones")
        
        # Resident can only cancel pending or approved reservations
        if current_status not in ["pending", "approved"]:
            raise HTTPException(status_code=400, detail="Solo puedes cancelar reservaciones pendientes o aprobadas")
        
        # Resident cannot cancel if reservation has already started
        try:
            now = datetime.now(timezone.utc)
            res_datetime_str = f"{reservation_date}T{reservation_start}"
            res_start_dt = datetime.fromisoformat(res_datetime_str).replace(tzinfo=timezone.utc)
            
            if now >= res_start_dt:
                raise HTTPException(
                    status_code=400, 
                    detail="No puedes cancelar una reservación que ya inició o está en progreso"
                )
        except ValueError:
            # If date parsing fails, allow cancellation (fail-safe)
            pass
    
    # ==================== ADMIN-SPECIFIC RULES ====================
    # Admins can cancel any reservation except completed ones (already checked above)
    
    # ==================== PERFORM CANCELLATION ====================
    cancellation_reason = body.reason if body else None
    
    update_fields = {
        "status": "cancelled",
        "cancelled_at": datetime.now(timezone.utc).isoformat(),
        "cancelled_by": current_user["id"],
        "cancelled_by_role": "Administrador" if is_admin else "Residente",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["id"]
    }
    
    if cancellation_reason:
        update_fields["cancellation_reason"] = cancellation_reason
    
    await db.reservations.update_one({"id": reservation_id}, {"$set": update_fields})
    
    # ==================== NOTIFICATIONS ====================
    # If admin cancels resident's reservation, notify the resident
    if is_admin and resident_id and resident_id != current_user["id"]:
        reason_text = cancellation_reason or "Sin motivo especificado"
        await create_and_send_notification(
            user_id=resident_id,
            condominium_id=condo_id,
            notification_type="reservation_cancelled",
            title="❌ Reservación cancelada",
            message=f"Tu reservación de {area_name} para el {reservation_date} fue cancelada por el administrador. Motivo: {reason_text}",
            data={
                "reservation_id": reservation_id,
                "area_name": area_name,
                "date": reservation_date,
                "cancelled_by": "admin",
                "reason": reason_text
            },
            send_push=True,
            url="/resident?tab=reservations"
        )
    
    # ==================== AUDIT LOG ====================
    await log_audit_event(
        AuditEventType.ACCESS_GRANTED,
        current_user["id"],
        "reservations",
        {
            "action": "reservation_cancelled",
            "reservation_id": reservation_id,
            "area": area_name,
            "date": reservation_date,
            "cancelled_by_role": "admin" if is_admin else "resident",
            "reason": cancellation_reason
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "message": "Reservación cancelada exitosamente. El espacio ha sido liberado.",
        "reservation_id": reservation_id,
        "cancelled_by": "admin" if is_admin else "resident"
    }


@router.get("/reservations/today")
async def get_today_reservations(current_user = Depends(get_current_user)):
    """Get today's reservations for guard view"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asignado a condominio")
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    reservations = await db.reservations.find(
        {"condominium_id": condo_id, "date": today, "status": "approved"},
        {"_id": 0}
    ).sort("start_time", 1).to_list(50)
    
    # Enrich with area and user info
    for res in reservations:
        area = await db.reservation_areas.find_one({"id": res.get("area_id")}, {"_id": 0, "name": 1, "area_type": 1})
        if area:
            res["area_name"] = area.get("name")
            res["area_type"] = area.get("area_type")
        user = await db.users.find_one({"id": res.get("resident_id")}, {"_id": 0, "full_name": 1, "profile_photo": 1})
        if user:
            res["resident_name"] = user.get("full_name")
            res["resident_photo"] = user.get("profile_photo")
    
    return reservations

