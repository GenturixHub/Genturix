"""GENTURIX - Super Admin + Config + Onboarding Router (Auto-extracted from server.py)"""
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

# ==================== SUPER ADMIN ENDPOINTS ====================

@router.get("/super-admin/stats")
async def get_platform_stats(
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Get global platform statistics"""
    total_condos = await db.condominiums.count_documents({})
    active_condos = await db.condominiums.count_documents({"is_active": True})
    demo_condos = await db.condominiums.count_documents({"is_demo": True})
    total_users = await db.users.count_documents({})
    active_users = await db.users.count_documents({"is_active": True})
    total_alerts = await db.panic_events.count_documents({})
    active_alerts = await db.panic_events.count_documents({"status": "active"})
    
    # Calculate MRR (Monthly Recurring Revenue)
    condos = await db.condominiums.find({"is_active": True}, {"_id": 0}).to_list(1000)
    mrr = 0.0
    for condo in condos:
        user_count = await db.users.count_documents({"condominium_id": condo.get("id"), "is_active": True})
        price = condo.get("price_per_user", 1.0)
        discount = condo.get("discount_percent", 0)
        mrr += user_count * price * (1 - discount / 100)
    
    return {
        "condominiums": {
            "total": total_condos,
            "active": active_condos,
            "demo": demo_condos,
            "suspended": total_condos - active_condos
        },
        "users": {
            "total": total_users,
            "active": active_users
        },
        "alerts": {
            "total": total_alerts,
            "active": active_alerts
        },
        "revenue": {
            "mrr_usd": round(mrr, 2),
            "price_per_user": 1.0
        }
    }

@router.get("/super-admin/users")
async def get_all_users_global(
    condo_id: Optional[str] = None,
    role: Optional[str] = None,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Get all users across all condominiums with filters"""
    query = {}
    if condo_id:
        query["condominium_id"] = condo_id
    if role:
        query["roles"] = role
    
    users = await db.users.find(query, {"_id": 0, "hashed_password": 0}).to_list(1000)
    
    # Enrich with condominium name
    for user in users:
        if user.get("condominium_id"):
            condo = await db.condominiums.find_one({"id": user["condominium_id"]}, {"name": 1})
            user["condominium_name"] = condo.get("name") if condo else "Unknown"
    
    return users

@router.put("/super-admin/users/{user_id}/lock")
async def lock_user(
    user_id: str,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Lock a user account (security)"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_active": False, "locked_by": current_user["id"], "locked_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    await log_audit_event(
        AuditEventType.USER_LOCKED,
        current_user["id"],
        "super_admin",
        {"user_id": user_id, "email": user.get("email"), "action": "locked"},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "User locked successfully"}

@router.put("/super-admin/users/{user_id}/unlock")
async def unlock_user(
    user_id: str,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Unlock a user account"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_active": True, "locked_by": None, "locked_at": None}}
    )
    
    await log_audit_event(
        AuditEventType.USER_UNLOCKED,
        current_user["id"],
        "super_admin",
        {"user_id": user_id, "email": user.get("email"), "action": "unlocked"},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "User unlocked successfully"}

@router.post("/super-admin/condominiums/{condo_id}/make-demo")
async def make_demo_condominium(
    condo_id: str,
    max_users: int = 10,
    request: Request = None,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Convert a condominium to demo/sandbox mode"""
    result = await db.condominiums.update_one(
        {"id": condo_id},
        {"$set": {
            "is_demo": True,
            "status": "demo",
            "max_users": max_users,
            "price_per_user": 0,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Condominium not found")
    
    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "condominiums",
        {"action": "make_demo", "condo_id": condo_id},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id,
        user_email=current_user.get("email"),
    )
    return {"message": "Condominium converted to demo mode"}

@router.post("/super-admin/condominiums/{condo_id}/reset-demo")
async def reset_demo_data(
    condo_id: str,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Reset demo data for a sandbox condominium"""
    condo = await db.condominiums.find_one({"id": condo_id})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominium not found")
    
    if not condo.get("is_demo"):
        raise HTTPException(status_code=400, detail="Only demo condominiums can be reset")
    
    # Delete associated data
    await db.panic_events.delete_many({"condominium_id": condo_id})
    await db.visitors.delete_many({"condominium_id": condo_id})
    await db.access_logs.delete_many({"condominium_id": condo_id})
    
    await log_audit_event(
        AuditEventType.DEMO_RESET,
        current_user["id"],
        "super_admin",
        {"condo_id": condo_id, "name": condo.get("name"), "action": "demo_reset"},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "Demo data reset successfully"}

@router.patch("/super-admin/condominiums/{condo_id}/pricing")
async def update_condo_pricing(
    condo_id: str,
    discount_percent: Optional[int] = None,
    free_modules: Optional[List[str]] = None,
    plan: Optional[str] = None,
    seat_price_override: Optional[float] = None,
    request: Request = None,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """
    Update pricing/plan for a condominium.
    
    PHASE 3: seat_price_override
    - Set to a value > 0 to override global price for this condo
    - Set to 0 or omit to use global default price
    """
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if discount_percent is not None:
        update_data["discount_percent"] = max(0, min(100, discount_percent))
    if free_modules is not None:
        update_data["free_modules"] = free_modules
    if plan is not None:
        update_data["plan"] = plan
    
    # PHASE 3: Handle seat price override
    if seat_price_override is not None:
        if seat_price_override <= 0:
            # Remove override (use global default)
            update_data["seat_price_override"] = None
        else:
            update_data["seat_price_override"] = round(seat_price_override, 2)
    
    result = await db.condominiums.update_one({"id": condo_id}, {"$set": update_data})
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Condominium not found")
    
    if request:
        await log_audit_event(
            AuditEventType.PRICING_OVERRIDE_UPDATED if seat_price_override is not None else AuditEventType.PLAN_UPDATED,
            current_user["id"],
            "super_admin",
            {"condo_id": condo_id, "changes": update_data},
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "unknown")
        )
    
    return {"message": "Pricing updated successfully"}

# ==================== GLOBAL PRICING ENDPOINTS ====================

class GlobalPricingUpdate(BaseModel):
    default_seat_price: float = Field(..., gt=0, description="Default price per seat (must be > 0)")
    currency: str = Field(default="USD", description="Currency code")

@router.get("/super-admin/pricing/global")
async def get_global_pricing_config(
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    Get global pricing configuration.
    Only SuperAdmin can view global pricing.
    """
    config = await db.system_config.find_one({"id": "global_pricing"}, {"_id": 0})
    
    if not config:
        # Initialize if missing
        await ensure_global_pricing_config()
        config = await db.system_config.find_one({"id": "global_pricing"}, {"_id": 0})
    
    return {
        "default_seat_price": config.get("default_seat_price", FALLBACK_PRICE_PER_SEAT),
        "currency": config.get("currency", DEFAULT_CURRENCY),
        "updated_at": config.get("updated_at")
    }

@router.put("/super-admin/pricing/global")
async def update_global_pricing(
    pricing: GlobalPricingUpdate,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    PHASE 3: Update global pricing configuration.
    Only SuperAdmin can update global pricing.
    
    This affects ALL condominiums that don't have a seat_price_override.
    """
    # Validate price
    if pricing.default_seat_price <= 0:
        raise HTTPException(status_code=400, detail="Price must be greater than 0")
    
    # Validate currency
    if pricing.currency.upper() not in ["USD", "EUR", "MXN"]:
        raise HTTPException(status_code=400, detail="Currency must be USD, EUR, or MXN")
    
    update_data = {
        "default_seat_price": round(pricing.default_seat_price, 2),
        "currency": pricing.currency.upper(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Upsert global pricing config
    await db.system_config.update_one(
        {"id": "global_pricing"},
        {"$set": update_data, "$setOnInsert": {"id": "global_pricing", "created_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    
    # Log audit event
    await log_audit_event(
        AuditEventType.PRICING_GLOBAL_UPDATED,
        current_user["id"],
        "system_config",
        {"old_price": "see_previous_logs", "new_price": update_data["default_seat_price"], "currency": update_data["currency"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    logger.info(f"[PRICING] Global pricing updated: ${update_data['default_seat_price']} {update_data['currency']} by {current_user['email']}")
    
    return {
        "message": "Global pricing updated successfully",
        "default_seat_price": update_data["default_seat_price"],
        "currency": update_data["currency"]
    }

@router.get("/super-admin/pricing/condominiums")
async def get_all_condominiums_pricing(
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    PHASE 5: Get pricing info for all condominiums.
    Shows effective price and whether each condo uses override or global.
    """
    global_config = await get_global_pricing()
    
    condos = await db.condominiums.find(
        {},
        {"_id": 0, "id": 1, "name": 1, "seat_price_override": 1, "seat_limit": 1}
    ).to_list(None)
    
    result = []
    for condo in condos:
        override = condo.get("seat_price_override")
        uses_override = override is not None and override > 0
        effective_price = override if uses_override else global_config["default_seat_price"]
        
        result.append({
            "id": condo["id"],
            "name": condo.get("name", "Unknown"),
            "effective_price": effective_price,
            "uses_override": uses_override,
            "override_price": override if uses_override else None,
            "global_price": global_config["default_seat_price"],
            "seat_limit": condo.get("seat_limit", 0),
            "currency": global_config["currency"]
        })
    
    return {
        "global_pricing": global_config,
        "condominiums": result,
        "total": len(result)
    }

@router.patch("/super-admin/condominiums/{condo_id}/status")
async def update_condo_status(
    condo_id: str,
    status: str,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Update condominium status (active/demo/suspended)"""
    valid_statuses = ["active", "demo", "suspended"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {', '.join(valid_statuses)}")
    
    result = await db.condominiums.update_one(
        {"id": condo_id},
        {"$set": {
            "status": status,
            "is_active": status != "suspended",
            "is_demo": status == "demo",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Condominium not found")
    
    await log_audit_event(
        AuditEventType.CONDO_UPDATED,
        current_user["id"],
        "super_admin",
        {"condo_id": condo_id, "new_status": status},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": f"Status updated to {status}"}

@router.get("/super-admin/audit")
async def get_super_admin_audit(
    module: Optional[str] = "super_admin",
    limit: int = 100,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Get audit logs for super admin actions"""
    query = {}
    if module:
        query["module"] = module
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return logs


@router.get("/super-admin/audit/global")
async def get_global_audit_logs(
    limit: int = 500,
    module: Optional[str] = None,
    event_type: Optional[str] = None,
    condominium_id: Optional[str] = None,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    Global System Audit - SuperAdmin Only.
    
    Returns logs from ALL condominiums with full details.
    
    Fields returned:
    - timestamp
    - user_id
    - user_email (fetched from users collection)
    - condominium_id
    - condominium_name (fetched from condominiums collection)
    - action (event_type)
    - module
    - details
    
    Sorted by newest first.
    """
    query = {}
    
    if module:
        query["module"] = module
    if event_type:
        query["event_type"] = event_type
    if condominium_id:
        query["condominium_id"] = condominium_id
    
    # Fetch logs
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    
    # Enrich with user emails and condominium names
    user_ids = list(set([log.get("user_id") for log in logs if log.get("user_id")]))
    condo_ids = list(set([log.get("condominium_id") for log in logs if log.get("condominium_id")]))
    
    # Fetch users and condominiums for enrichment
    users = {}
    if user_ids:
        user_docs = await db.users.find(
            {"id": {"$in": user_ids}}, 
            {"_id": 0, "id": 1, "email": 1}
        ).to_list(len(user_ids))
        users = {u["id"]: u.get("email", "N/A") for u in user_docs}
    
    condos = {}
    if condo_ids:
        condo_docs = await db.condominiums.find(
            {"id": {"$in": condo_ids}}, 
            {"_id": 0, "id": 1, "name": 1}
        ).to_list(len(condo_ids))
        condos = {c["id"]: c.get("name", "N/A") for c in condo_docs}
    
    # Enrich logs
    enriched_logs = []
    for log in logs:
        enriched_log = {
            "timestamp": log.get("timestamp"),
            "user_id": log.get("user_id"),
            "user_email": users.get(log.get("user_id"), "N/A"),
            "condominium_id": log.get("condominium_id"),
            "condominium_name": condos.get(log.get("condominium_id"), "Sistema"),
            "action": log.get("event_type"),
            "module": log.get("module"),
            "endpoint": log.get("endpoint"),
            "status": log.get("status", "success"),
            "details": log.get("details", {})
        }
        enriched_logs.append(enriched_log)
    
    return {
        "logs": enriched_logs,
        "total": len(enriched_logs),
        "scope": "global"
    }


@router.delete("/super-admin/condominiums/{condo_id}")
async def permanently_delete_condominium(
    condo_id: str,
    delete_request: CondominiumDeleteRequest,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    PERMANENTLY DELETE a condominium and ALL related data.
    
    This is an IRREVERSIBLE action. Requires Super Admin role and password verification.
    
    Deletes:
    - Condominium record
    - All users belonging to the condominium
    - All panic events
    - All guard history
    - All HR data (guards, employees, shifts, absences)
    - All visitors
    - All audit logs linked to the condominium
    """
    # Step 1: Verify Super Admin password
    user = await db.users.find_one({"id": current_user["id"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(delete_request.password, user["hashed_password"]):
        raise HTTPException(status_code=403, detail="Contraseña incorrecta")
    
    # Step 2: Verify condominium exists
    condo = await db.condominiums.find_one({"id": condo_id})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    condo_name = condo.get("name", "Unknown")
    
    # Step 3: Cascade delete all related data
    deletion_stats = {
        "condominium": condo_name,
        "users_deleted": 0,
        "panic_events_deleted": 0,
        "guard_history_deleted": 0,
        "guards_deleted": 0,
        "employees_deleted": 0,
        "shifts_deleted": 0,
        "absences_deleted": 0,
        "visitors_deleted": 0,
        "audit_logs_deleted": 0,
        "candidates_deleted": 0
    }
    
    # Delete users
    users_result = await db.users.delete_many({"condominium_id": condo_id})
    deletion_stats["users_deleted"] = users_result.deleted_count
    
    # Delete panic events
    panic_result = await db.panic_events.delete_many({"condominium_id": condo_id})
    deletion_stats["panic_events_deleted"] = panic_result.deleted_count
    
    # Delete guard history
    history_result = await db.guard_history.delete_many({"condominium_id": condo_id})
    deletion_stats["guard_history_deleted"] = history_result.deleted_count
    
    # Delete guards
    guards_result = await db.guards.delete_many({"condominium_id": condo_id})
    deletion_stats["guards_deleted"] = guards_result.deleted_count
    
    # Delete employees
    employees_result = await db.employees.delete_many({"condominium_id": condo_id})
    deletion_stats["employees_deleted"] = employees_result.deleted_count
    
    # Delete shifts
    shifts_result = await db.shifts.delete_many({"condominium_id": condo_id})
    deletion_stats["shifts_deleted"] = shifts_result.deleted_count
    
    # Delete absences
    absences_result = await db.absences.delete_many({"condominium_id": condo_id})
    deletion_stats["absences_deleted"] = absences_result.deleted_count
    
    # Delete visitors
    visitors_result = await db.visitors.delete_many({"condominium_id": condo_id})
    deletion_stats["visitors_deleted"] = visitors_result.deleted_count
    
    # Delete candidates (HR recruitment)
    candidates_result = await db.candidates.delete_many({"condominium_id": condo_id})
    deletion_stats["candidates_deleted"] = candidates_result.deleted_count
    
    # Delete audit logs linked to condo users (we keep the final deletion log)
    audit_result = await db.audit_logs.delete_many({
        "$or": [
            {"details.condominium_id": condo_id},
            {"details.condo_id": condo_id}
        ]
    })
    deletion_stats["audit_logs_deleted"] = audit_result.deleted_count
    
    # Step 4: Delete the condominium itself
    await db.condominiums.delete_one({"id": condo_id})
    
    # Step 5: Log the deletion (this log persists for Super Admin audit trail)
    await log_audit_event(
        AuditEventType.CONDOMINIUM_DELETED,
        current_user["id"],
        "super_admin",
        {
            "action": "CONDOMINIUM_DELETED",
            "condo_id": condo_id,
            "condo_name": condo_name,
            "deletion_stats": deletion_stats,
            "performed_by_email": current_user.get("email"),
            "irreversible": True
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "message": f"Condominio '{condo_name}' eliminado permanentemente",
        "deletion_stats": deletion_stats
    }


# ==================== FIX EXISTING USERS WITHOUT CONDOMINIUM ====================

@router.post("/admin/fix-orphan-users")
async def fix_orphan_users(
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Fix users without condominium_id by assigning them to a demo condominium"""
    # Find or create demo condominium
    demo_condo = await db.condominiums.find_one({"name": "Residencial Las Palmas"})
    if not demo_condo:
        demo_condo_id = str(uuid.uuid4())
        demo_condo = {
            "id": demo_condo_id,
            "name": "Residencial Las Palmas",
            "address": "Av. Principal #123",
            "status": "demo",
            "is_active": True,
            "max_users": 50,
            "modules": {"security": True, "visitors": True, "school": True},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.condominiums.insert_one(demo_condo)
        
        # Create default settings for demo condo
        existing_settings = await db.condominium_settings.find_one({"condominium_id": demo_condo["id"]})
        if not existing_settings:
            settings_doc = {
                "condominium_id": demo_condo["id"],
                "condominium_name": demo_condo["name"],
                **get_default_condominium_settings(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            await db.condominium_settings.insert_one(settings_doc)
    
    demo_condo_id = demo_condo["id"]
    
    # Find all users without condominium_id (except SuperAdmin)
    orphan_query = {
        "$and": [
            {"$or": [{"condominium_id": None}, {"condominium_id": {"$exists": False}}]},
            {"roles": {"$nin": ["SuperAdmin"]}}
        ]
    }
    
    result = await db.users.update_many(
        orphan_query,
        {"$set": {"condominium_id": demo_condo_id}}
    )
    
    # Also fix guards without condominium_id
    guard_result = await db.guards.update_many(
        {"$or": [{"condominium_id": None}, {"condominium_id": {"$exists": False}}]},
        {"$set": {"condominium_id": demo_condo_id}}
    )
    
    await log_audit_event(
        AuditEventType.USER_UPDATED,
        current_user["id"],
        "admin",
        {
            "action": "fix_orphan_users",
            "users_fixed": result.modified_count,
            "guards_fixed": guard_result.modified_count,
            "assigned_condo": demo_condo_id
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "message": f"Fixed {result.modified_count} users and {guard_result.modified_count} guards",
        "users_fixed": result.modified_count,
        "guards_fixed": guard_result.modified_count,
        "assigned_condominium_id": demo_condo_id
    }

# ==================== SUPER ADMIN: CONDOMINIUM ADMIN CREATION ====================

class CreateCondoAdminRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    phone: Optional[str] = None

@router.post("/super-admin/condominiums/{condo_id}/admin")
async def create_condominium_admin(
    condo_id: str,
    admin_data: CreateCondoAdminRequest,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """Super Admin creates a Condominium Administrator for a specific condominium"""
    # Verify condominium exists
    condo = await db.condominiums.find_one({"id": condo_id})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    # Check email not in use
    existing = await db.users.find_one({"email": admin_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # Force role to Administrador
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": admin_data.email,
        "hashed_password": hash_password(admin_data.password),
        "full_name": admin_data.full_name,
        "roles": [RoleEnum.ADMINISTRADOR.value],
        "condominium_id": condo_id,  # Associate with the condominium
        "phone": admin_data.phone,
        "is_active": True,
        "is_locked": False,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    # Update condominium to reference this admin
    await db.condominiums.update_one(
        {"id": condo_id},
        {"$set": {"admin_id": user_id, "admin_email": admin_data.email}}
    )
    
    await log_audit_event(
        AuditEventType.USER_CREATED,
        current_user["id"],
        "super_admin",
        {
            "action": "create_condo_admin",
            "user_id": user_id,
            "email": admin_data.email,
            "condominium_id": condo_id,
            "condominium_name": condo["name"]
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "message": f"Administrador {admin_data.full_name} creado para {condo['name']}",
        "user_id": user_id,
        "condominium_id": condo_id,
        "credentials": {
            "email": admin_data.email,
            "password": "********"
        }
    }

# ==================== ONBOARDING WIZARD ====================
class OnboardingCondominiumInfo(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    address: str = Field(..., min_length=5, max_length=200)
    country: str = Field(default="Mexico")
    timezone: str = Field(default="America/Mexico_City")

# BILLING ENGINE: Billing configuration for onboarding
class OnboardingBillingInfo(BaseModel):
    initial_units: int = Field(..., ge=1, le=10000, description="Number of billable seats")
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|yearly)$")
    billing_provider: str = Field(default="sinpe", pattern="^(stripe|sinpe|ticopay|manual)$")
    billing_email: Optional[EmailStr] = None  # If different from admin email
    seat_price_override: Optional[float] = Field(default=None, gt=0, le=1000, description="Custom price per seat")
    yearly_discount_percent: Optional[float] = Field(default=None, ge=0, le=50, description="Custom yearly discount 0-50%")

class OnboardingAdminInfo(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr

class OnboardingModules(BaseModel):
    security: bool = True  # Always true, cannot be disabled
    hr: bool = False
    reservations: bool = False
    school: bool = False
    payments: bool = False
    cctv: bool = False  # Coming soon

class OnboardingArea(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    capacity: int = Field(..., ge=1, le=1000)
    requires_approval: bool = False
    available_days: List[str] = Field(default=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
    open_time: str = Field(default="08:00")
    close_time: str = Field(default="22:00")

class OnboardingWizardRequest(BaseModel):
    condominium: OnboardingCondominiumInfo
    admin: OnboardingAdminInfo
    modules: OnboardingModules
    areas: List[OnboardingArea] = []
    # BILLING ENGINE: Required billing configuration
    billing: OnboardingBillingInfo

@router.post("/super-admin/onboarding/create-condominium")
async def onboarding_create_condominium(
    wizard_data: OnboardingWizardRequest,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    Atomically create a new condominium with admin, modules, and areas.
    This is the main endpoint for the onboarding wizard.
    Returns admin credentials ONCE - they are not stored or retrievable later.
    """
    logger.info(f"Onboarding started by {current_user['email']} for: {wizard_data.condominium.name}")
    
    # CRITICAL: Normalize admin email to lowercase
    normalized_admin_email = wizard_data.admin.email.lower().strip()
    
    # Validate email is not in use
    existing_user = await db.users.find_one({"email": normalized_admin_email})
    if existing_user:
        logger.warning(f"Onboarding failed: email {normalized_admin_email} already registered")
        raise HTTPException(
            status_code=400, 
            detail=f"El email del administrador '{normalized_admin_email}' ya está registrado en el sistema"
        )
    
    # Validate condominium name is not in use
    existing_condo = await db.condominiums.find_one({"name": wizard_data.condominium.name})
    if existing_condo:
        logger.warning(f"Onboarding failed: condominium name '{wizard_data.condominium.name}' already exists")
        raise HTTPException(
            status_code=400, 
            detail=f"Ya existe un condominio con el nombre '{wizard_data.condominium.name}'"
        )
    
    # Validate timezone (basic check - must start with valid region)
    valid_tz_prefixes = ['America/', 'Europe/', 'Asia/', 'Africa/', 'Pacific/', 'UTC']
    if not any(wizard_data.condominium.timezone.startswith(prefix) for prefix in valid_tz_prefixes):
        logger.warning(f"Onboarding failed: invalid timezone '{wizard_data.condominium.timezone}'")
        raise HTTPException(
            status_code=400,
            detail=f"Zona horaria inválida: '{wizard_data.condominium.timezone}'. Use un formato válido como 'America/Costa_Rica'"
        )
    
    # Generate IDs
    condo_id = str(uuid.uuid4())
    admin_user_id = str(uuid.uuid4())
    
    # Generate secure temporary password for admin
    admin_password = generate_temporary_password(12)
    
    # Prepare module config - ensure security is always enabled
    modules_config = {
        "security": True,  # Always true
        "visitors": True,  # Always included with security
        "hr": wizard_data.modules.hr,
        "reservations": wizard_data.modules.reservations,
        "school": wizard_data.modules.school,
        "payments": wizard_data.modules.payments,
        "cctv": False  # Coming soon - always false for now
    }
    
    try:
        # === STEP 1: Create Condominium ===
        condo_doc = {
            "id": condo_id,
            "name": wizard_data.condominium.name,
            "address": wizard_data.condominium.address,
            "country": wizard_data.condominium.country,
            "timezone": wizard_data.condominium.timezone,
            "contact_email": normalized_admin_email,
            "billing_email": wizard_data.billing.billing_email or normalized_admin_email,
            "modules": modules_config,
            "status": "active",
            "is_demo": False,
            "environment": "production",
            "is_active": True,
            # BILLING ENGINE: Core billing fields
            "billing_model": "per_seat",
            "paid_seats": wizard_data.billing.initial_units,
            "max_users": wizard_data.billing.initial_units,  # Sync with paid_seats
            "current_users": 1,  # Admin user
            "price_per_seat": await get_effective_seat_price(None),
            "seat_price_override": wizard_data.billing.seat_price_override,  # Custom price (optional)
            "billing_cycle": wizard_data.billing.billing_cycle,
            "billing_provider": wizard_data.billing.billing_provider,
            "billing_enabled": True,
            "billing_status": "pending_payment",
            "next_invoice_amount": 0,  # Will be calculated below
            "next_billing_date": None,  # Will be set after first payment
            "billing_started_at": datetime.now(timezone.utc).isoformat(),
            "yearly_discount_percent": wizard_data.billing.yearly_discount_percent if wizard_data.billing.yearly_discount_percent is not None else YEARLY_DISCOUNT_PERCENT,
            # Legacy fields for backward compatibility
            "price_per_user": 1.0,
            "discount_percent": 0,
            "free_modules": [],
            "plan": "basic",
            "admin_id": admin_user_id,
            "admin_email": normalized_admin_email,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "onboarding_completed": True,
            "onboarding_completed_by": current_user["id"],
            "onboarding_completed_at": datetime.now(timezone.utc).isoformat()
        }
        
        # BILLING ENGINE: Calculate invoice amount (using overrides if provided)
        billing_preview = await calculate_billing_preview(
            initial_units=wizard_data.billing.initial_units,
            billing_cycle=wizard_data.billing.billing_cycle,
            condominium_id=None,
            seat_price_override=wizard_data.billing.seat_price_override,
            yearly_discount_override=wizard_data.billing.yearly_discount_percent
        )
        condo_doc["next_invoice_amount"] = billing_preview["effective_amount"]
        condo_doc["price_per_seat"] = billing_preview["price_per_seat"]
        
        await db.condominiums.insert_one(condo_doc)
        
        # BILLING ENGINE: Log creation event
        await log_billing_engine_event(
            event_type="condominium_created",
            condominium_id=condo_id,
            data={
                "name": wizard_data.condominium.name,
                "paid_seats": wizard_data.billing.initial_units,
                "price_per_seat": billing_preview["price_per_seat"],
                "seat_price_override": wizard_data.billing.seat_price_override,
                "yearly_discount_percent": billing_preview["yearly_discount_percent"],
                "billing_cycle": wizard_data.billing.billing_cycle,
                "billing_provider": wizard_data.billing.billing_provider,
                "monthly_amount": billing_preview["monthly_amount"],
                "effective_amount": billing_preview["effective_amount"],
                "source": "onboarding_wizard"
            },
            triggered_by=current_user["id"],
            previous_state=None,
            new_state={
                "paid_seats": wizard_data.billing.initial_units,
                "billing_status": "pending_payment",
                "billing_cycle": wizard_data.billing.billing_cycle,
                "seat_price_override": wizard_data.billing.seat_price_override,
                "yearly_discount_percent": billing_preview["yearly_discount_percent"]
            }
        )
        
        # Create default condominium settings
        settings_doc = {
            "condominium_id": condo_id,
            "condominium_name": wizard_data.condominium.name,
            **get_default_condominium_settings(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.condominium_settings.insert_one(settings_doc)
        
        # === STEP 2: Create Admin User ===
        admin_doc = {
            "id": admin_user_id,
            "email": normalized_admin_email,  # Use normalized email
            "hashed_password": hash_password(admin_password),
            "full_name": wizard_data.admin.full_name,
            "roles": [RoleEnum.ADMINISTRADOR.value],
            "condominium_id": condo_id,
            "is_active": True,
            "is_locked": False,
            "password_reset_required": not DEV_MODE,  # Skip password reset in DEV_MODE
            "created_by": current_user["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.users.insert_one(admin_doc)
        
        # === STEP 3: Create Areas (if reservations enabled and areas provided) ===
        created_areas = []
        if wizard_data.modules.reservations and wizard_data.areas:
            for area in wizard_data.areas:
                area_id = str(uuid.uuid4())
                area_doc = {
                    "id": area_id,
                    "condominium_id": condo_id,
                    "name": area.name,
                    "capacity": area.capacity,
                    "requires_approval": area.requires_approval,
                    "available_days": area.available_days,
                    "open_time": area.open_time,
                    "close_time": area.close_time,
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await db.reservation_areas.insert_one(area_doc)
                created_areas.append({"id": area_id, "name": area.name})
        
        # === STEP 4: Log Audit Event ===
        await log_audit_event(
            AuditEventType.CONDO_CREATED,
            current_user["id"],
            "super_admin",
            {
                "action": "onboarding_completed",
                "condominium_id": condo_id,
                "condominium_name": wizard_data.condominium.name,
                "admin_user_id": admin_user_id,
                "admin_email": wizard_data.admin.email,
                "modules_enabled": [k for k, v in modules_config.items() if v],
                "areas_created": len(created_areas)
            },
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "unknown")
        )
        
        # === STEP 5: Send Welcome Email to Admin (fail-safe) ===
        try:
            print(f"[EMAIL TRIGGER] create_condominium → sending welcome email to {normalized_admin_email}")
            login_url = f"{FRONTEND_URL}/login" if FRONTEND_URL else "https://genturix.com/login"
            welcome_html = get_condominium_welcome_email_html(
                admin_name=wizard_data.admin.full_name,
                condominium_name=wizard_data.condominium.name,
                email=normalized_admin_email,
                password=admin_password,
                login_url=login_url
            )
            email_result = await send_email(
                to=normalized_admin_email,
                subject=f"¡Bienvenido a GENTURIX! - {wizard_data.condominium.name}",
                html=welcome_html
            )
            print(f"[EMAIL RESULT] create_condominium → {email_result}")
        except Exception as email_error:
            print(f"[EMAIL ERROR] create_condominium → {email_error}")
            logger.warning(f"[EMAIL] Failed to send welcome email to {normalized_admin_email}: {email_error}")
            # Continue - don't break API flow
        
        logger.info(f"Onboarding completed: {wizard_data.condominium.name} by {current_user['email']}")
        
        return {
            "success": True,
            "message": f"Condominio '{wizard_data.condominium.name}' creado exitosamente",
            "condominium": {
                "id": condo_id,
                "name": wizard_data.condominium.name,
                "address": wizard_data.condominium.address,
                "timezone": wizard_data.condominium.timezone
            },
            "admin_credentials": {
                "email": wizard_data.admin.email,
                "password": admin_password,  # SHOWN ONCE - NOT STORED
                "show_password": True,  # Always show for wizard (one-time display)
                "warning": "Guarda estas credenciales ahora. No se mostrarán de nuevo." if not DEV_MODE else "Modo desarrollo: La contraseña no requiere cambio obligatorio."
            },
            "modules_enabled": [k for k, v in modules_config.items() if v],
            "areas_created": created_areas,
            "dev_mode": DEV_MODE
        }
        
    except Exception as e:
        # === ROLLBACK on any error ===
        logger.error(f"Onboarding failed, rolling back: {str(e)}")
        
        # Delete any created documents
        await db.condominiums.delete_one({"id": condo_id})
        await db.users.delete_one({"id": admin_user_id})
        await db.reservation_areas.delete_many({"condominium_id": condo_id})
        
        raise HTTPException(
            status_code=500,
            detail=f"Error durante el onboarding. Todos los cambios han sido revertidos. Error: {str(e)}"
        )


# Validation endpoints for onboarding
class OnboardingValidation(BaseModel):
    field: str  # "email" or "name"
    value: str

@router.post("/super-admin/onboarding/validate")
async def validate_onboarding_field(
    data: OnboardingValidation,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """Validate a single field before submitting the entire wizard"""
    if data.field == "email":
        # CRITICAL: Normalize email for validation
        normalized_email = data.value.lower().strip()
        existing = await db.users.find_one({"email": normalized_email})
        if existing:
            return {
                "valid": False,
                "field": "email",
                "message": f"El email '{normalized_email}' ya está registrado en el sistema"
            }
        return {"valid": True, "field": "email", "message": "Email disponible"}
    
    elif data.field == "name":
        existing = await db.condominiums.find_one({"name": data.value})
        if existing:
            return {
                "valid": False,
                "field": "name",
                "message": f"Ya existe un condominio con el nombre '{data.value}'"
            }
        return {"valid": True, "field": "name", "message": "Nombre disponible"}
    
    return {"valid": True, "message": "Campo válido"}


@router.get("/super-admin/onboarding/timezones")
async def get_available_timezones(current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))):
    """Get list of available timezones for onboarding"""
    return {
        "timezones": [
            # Centroamérica
            {"value": "America/Costa_Rica", "label": "Costa Rica (San José)", "offset": "UTC-6"},
            {"value": "America/Guatemala", "label": "Guatemala", "offset": "UTC-6"},
            {"value": "America/Tegucigalpa", "label": "Honduras (Tegucigalpa)", "offset": "UTC-6"},
            {"value": "America/El_Salvador", "label": "El Salvador", "offset": "UTC-6"},
            {"value": "America/Managua", "label": "Nicaragua (Managua)", "offset": "UTC-6"},
            {"value": "America/Panama", "label": "Panamá", "offset": "UTC-5"},
            # Norteamérica
            {"value": "America/Mexico_City", "label": "México (Ciudad de México)", "offset": "UTC-6"},
            {"value": "America/Tijuana", "label": "México (Tijuana)", "offset": "UTC-8"},
            {"value": "America/Cancun", "label": "México (Cancún)", "offset": "UTC-5"},
            {"value": "America/New_York", "label": "Estados Unidos (Este)", "offset": "UTC-5"},
            {"value": "America/Los_Angeles", "label": "Estados Unidos (Pacífico)", "offset": "UTC-8"},
            # Sudamérica
            {"value": "America/Argentina/Buenos_Aires", "label": "Argentina (Buenos Aires)", "offset": "UTC-3"},
            {"value": "America/La_Paz", "label": "Bolivia (La Paz)", "offset": "UTC-4"},
            {"value": "America/Sao_Paulo", "label": "Brasil (São Paulo)", "offset": "UTC-3"},
            {"value": "America/Santiago", "label": "Chile (Santiago)", "offset": "UTC-3"},
            {"value": "America/Bogota", "label": "Colombia (Bogotá)", "offset": "UTC-5"},
            {"value": "America/Guayaquil", "label": "Ecuador (Guayaquil)", "offset": "UTC-5"},
            {"value": "America/Asuncion", "label": "Paraguay (Asunción)", "offset": "UTC-4"},
            {"value": "America/Lima", "label": "Perú (Lima)", "offset": "UTC-5"},
            {"value": "America/Montevideo", "label": "Uruguay (Montevideo)", "offset": "UTC-3"},
            {"value": "America/Caracas", "label": "Venezuela (Caracas)", "offset": "UTC-4"},
            # Caribe
            {"value": "America/Puerto_Rico", "label": "Puerto Rico", "offset": "UTC-4"},
            {"value": "America/Santo_Domingo", "label": "República Dominicana", "offset": "UTC-4"},
            {"value": "America/Havana", "label": "Cuba (La Habana)", "offset": "UTC-5"},
            # Europa
            {"value": "Europe/Madrid", "label": "España (Madrid)", "offset": "UTC+1"},
            {"value": "Europe/Lisbon", "label": "Portugal (Lisboa)", "offset": "UTC+0"},
            # Otros
            {"value": "UTC", "label": "UTC", "offset": "UTC+0"}
        ]
    }

# ==================== DEMO DATA SEEDING ====================
@router.post("/seed-demo-data")
async def seed_demo_data():
    """Seed demo data for testing and demonstration"""
    
    # Check if demo data already exists
    existing_demo = await db.users.find_one({"email": "admin@genturix.com"})
    if existing_demo:
        return {"message": "Demo data already exists"}
    
    # Find or create demo condominium
    demo_condo = await db.condominiums.find_one({"name": "Residencial Las Palmas"})
    if not demo_condo:
        demo_condo_id = str(uuid.uuid4())
        demo_condo = {
            "id": demo_condo_id,
            "name": "Residencial Las Palmas",
            "address": "Av. Principal #123",
            "status": "demo",
            "is_active": True,
            "max_users": 50,
            "modules": {"security": True, "visitors": True, "school": True},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.condominiums.insert_one(demo_condo)
        
        # Create default settings for demo condo
        settings_doc = {
            "condominium_id": demo_condo["id"],
            "condominium_name": demo_condo["name"],
            **get_default_condominium_settings(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.condominium_settings.insert_one(settings_doc)
    
    demo_condo_id = demo_condo["id"]
    
    # Demo Users - SuperAdmin doesn't get condominium_id (platform-wide), others do
    demo_users = [
        {"email": "superadmin@genturix.com", "full_name": "Super Administrador", "password": "SuperAdmin123!", "roles": ["SuperAdmin"], "condo": None},
        {"email": "admin@genturix.com", "full_name": "Carlos Admin", "password": "Admin123!", "roles": ["Administrador"], "condo": demo_condo_id},
        {"email": "supervisor@genturix.com", "full_name": "María Supervisor", "password": "Super123!", "roles": ["Supervisor"], "condo": demo_condo_id},
        {"email": "guarda1@genturix.com", "full_name": "Juan Pérez", "password": "Guard123!", "roles": ["Guarda"], "condo": demo_condo_id},
        {"email": "guarda2@genturix.com", "full_name": "Pedro García", "password": "Guard123!", "roles": ["Guarda"], "condo": demo_condo_id},
        {"email": "residente@genturix.com", "full_name": "Ana Martínez", "password": "Resi123!", "roles": ["Residente"], "condo": demo_condo_id},
        {"email": "estudiante@genturix.com", "full_name": "Luis Estudiante", "password": "Stud123!", "roles": ["Estudiante"], "condo": demo_condo_id},
    ]
    
    user_ids = {}
    for user_data in demo_users:
        user_id = str(uuid.uuid4())
        user_ids[user_data["email"]] = user_id
        user_doc = {
            "id": user_id,
            "email": user_data["email"],
            "full_name": user_data["full_name"],
            "hashed_password": hash_password(user_data["password"]),
            "roles": user_data["roles"],
            "condominium_id": user_data["condo"],
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(user_doc)
    
    # Demo Guards
    demo_guards = [
        {"user_id": user_ids["guarda1@genturix.com"], "badge": "G-001", "phone": "+1234567890", "rate": 15.0},
        {"user_id": user_ids["guarda2@genturix.com"], "badge": "G-002", "phone": "+1234567891", "rate": 15.0},
    ]
    
    guard_ids = []
    for guard_data in demo_guards:
        user = await db.users.find_one({"id": guard_data["user_id"]})
        guard_id = str(uuid.uuid4())
        guard_ids.append(guard_id)
        guard_doc = {
            "id": guard_id,
            "user_id": guard_data["user_id"],
            "user_name": user["full_name"],
            "email": user["email"],
            "badge_number": guard_data["badge"],
            "phone": guard_data["phone"],
            "emergency_contact": "+0987654321",
            "hire_date": "2024-01-15",
            "hourly_rate": guard_data["rate"],
            "is_active": True,
            "total_hours": 160,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.guards.insert_one(guard_doc)
    
    # Demo Shifts
    today = datetime.now(timezone.utc).date()
    for i, guard_id in enumerate(guard_ids):
        shift_doc = {
            "id": str(uuid.uuid4()),
            "guard_id": guard_id,
            "guard_name": demo_guards[i]["badge"],
            "start_time": f"{today}T08:00:00Z",
            "end_time": f"{today}T16:00:00Z",
            "location": "Entrada Principal" if i == 0 else "Perímetro Norte",
            "notes": "Turno regular",
            "status": "active",
            "created_by": user_ids["admin@genturix.com"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.shifts.insert_one(shift_doc)
    
    # Demo Courses
    demo_courses = [
        {"title": "Seguridad Básica", "desc": "Fundamentos de seguridad física y vigilancia", "hours": 40, "instructor": "Instructor López", "category": "Seguridad"},
        {"title": "Primeros Auxilios", "desc": "Técnicas básicas de primeros auxilios y emergencias", "hours": 20, "instructor": "Dr. Ramírez", "category": "Salud"},
        {"title": "Protocolos de Emergencia", "desc": "Manejo de situaciones de emergencia y evacuación", "hours": 30, "instructor": "Cap. Moreno", "category": "Seguridad"},
    ]
    
    course_ids = []
    for course_data in demo_courses:
        course_id = str(uuid.uuid4())
        course_ids.append(course_id)
        course_doc = {
            "id": course_id,
            "title": course_data["title"],
            "description": course_data["desc"],
            "duration_hours": course_data["hours"],
            "instructor": course_data["instructor"],
            "category": course_data["category"],
            "lessons": [
                {"id": str(uuid.uuid4()), "title": "Introducción", "order": 1},
                {"id": str(uuid.uuid4()), "title": "Conceptos Básicos", "order": 2},
                {"id": str(uuid.uuid4()), "title": "Práctica", "order": 3},
                {"id": str(uuid.uuid4()), "title": "Evaluación Final", "order": 4},
            ],
            "enrolled_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.courses.insert_one(course_doc)
    
    # Demo Panic Events
    panic_event = {
        "id": str(uuid.uuid4()),
        "user_id": user_ids["residente@genturix.com"],
        "user_name": "Ana Martínez",
        "location": "Edificio A - Piso 3",
        "description": "Ruido sospechoso en pasillo",
        "status": "resolved",
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        "resolved_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    }
    await db.panic_events.insert_one(panic_event)
    
    # Demo Access Logs
    demo_accesses = [
        {"person": "Visitante 1", "type": "entry", "location": "Entrada Principal"},
        {"person": "Proveedor ABC", "type": "entry", "location": "Entrada Servicio"},
        {"person": "Visitante 1", "type": "exit", "location": "Entrada Principal"},
    ]
    
    for access_data in demo_accesses:
        access_log = {
            "id": str(uuid.uuid4()),
            "person_name": access_data["person"],
            "access_type": access_data["type"],
            "location": access_data["location"],
            "notes": None,
            "recorded_by": user_ids["guarda1@genturix.com"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.access_logs.insert_one(access_log)
    
    # Demo Audit Logs
    demo_audit = [
        {"type": AuditEventType.LOGIN_SUCCESS, "user": user_ids["admin@genturix.com"], "module": "auth", "details": {"email": "admin@genturix.com"}},
        {"type": AuditEventType.USER_CREATED, "user": user_ids["admin@genturix.com"], "module": "auth", "details": {"created_user": "guarda1@genturix.com"}},
        {"type": AuditEventType.PANIC_BUTTON, "user": user_ids["residente@genturix.com"], "module": "security", "details": {"location": "Edificio A"}},
    ]
    
    for audit_data in demo_audit:
        await log_audit_event(
            audit_data["type"],
            audit_data["user"],
            audit_data["module"],
            audit_data["details"]
        )
    
    return {"message": "Demo data seeded successfully", "credentials": {
        "admin": {"email": "admin@genturix.com", "password": "Admin123!"},
        "supervisor": {"email": "supervisor@genturix.com", "password": "Super123!"},
        "guarda": {"email": "guarda1@genturix.com", "password": "Guard123!"},
        "residente": {"email": "residente@genturix.com", "password": "Resi123!"},
        "estudiante": {"email": "estudiante@genturix.com", "password": "Stud123!"}
    }}

# ==================== DIAGNOSTIC ENDPOINT ====================
@router.get("/guard/diagnose-authorizations")
async def diagnose_authorizations(
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """
    Diagnostic endpoint to check authorization state.
    Returns detailed info about pending authorizations and their usage.
    """
    condo_id = current_user.get("condominium_id")
    
    # Get all pending temporary/extended authorizations
    pending = await db.visitor_authorizations.find({
        "condominium_id": condo_id,
        "authorization_type": {"$in": ["temporary", "extended"]},
        "status": {"$in": ["pending", None]},
        "is_active": True
    }, {"_id": 0}).to_list(100)
    
    results = []
    for auth in pending:
        auth_id = auth.get("id")
        
        # Check for entries with this auth_id
        entries = await db.visitor_entries.find({"authorization_id": auth_id}, {"_id": 0}).to_list(10)
        
        results.append({
            "id": auth_id[:12] + "...",
            "visitor_name": auth.get("visitor_name"),
            "authorization_type": auth.get("authorization_type"),
            "status": auth.get("status"),
            "checked_in_at": auth.get("checked_in_at"),
            "total_visits": auth.get("total_visits", 0),
            "entries_count": len(entries),
            "entries": [{"entry_at": e.get("entry_at"), "visitor_name": e.get("visitor_name")} for e in entries[:3]],
            "SHOULD_BE_USED": len(entries) > 0 or auth.get("checked_in_at") or (auth.get("total_visits", 0) > 0)
        })
    
    return {
        "condo_id": condo_id[:12] + "..." if condo_id else None,
        "total_pending": len(pending),
        "authorizations": results
    }

# ==================== CLEANUP USED AUTHORIZATIONS ====================
@router.post("/guard/cleanup-authorizations")
async def cleanup_used_authorizations(
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """
    Manually clean up authorizations that have been used but weren't marked as 'used'.
    This fixes legacy data issues where temporary/extended authorizations weren't properly
    marked after check-in.
    """
    condo_id = current_user.get("condominium_id")
    
    # Find all temporary/extended authorizations in this condominium
    query = {
        "condominium_id": condo_id,
        "authorization_type": {"$in": ["temporary", "extended"]},
        "status": {"$in": ["pending", None]},
        "is_active": True
    }
    
    authorizations = await db.visitor_authorizations.find(query, {"_id": 0}).to_list(500)
    logger.info(f"[cleanup] Found {len(authorizations)} temporary/extended pending authorizations in condo {condo_id[:8] if condo_id else 'N/A'}")
    
    fixed_count = 0
    fixed_auths = []
    
    for auth in authorizations:
        auth_id = auth.get("id")
        visitor_name = auth.get("visitor_name")
        auth_type = auth.get("authorization_type")
        
        # Check if there's an entry in visitor_entries with this authorization_id
        entry_exists = await db.visitor_entries.find_one({"authorization_id": auth_id})
        
        # Or check if checked_in_at is set or total_visits > 0
        already_used = (
            entry_exists or 
            auth.get("checked_in_at") or 
            (auth.get("total_visits", 0) > 0)
        )
        
        logger.info(f"[cleanup] Checking auth {auth_id[:8]} - {visitor_name} (type={auth_type}): entry_exists={bool(entry_exists)}, checked_in_at={bool(auth.get('checked_in_at'))}, total_visits={auth.get('total_visits', 0)}, already_used={already_used}")
        
        if already_used:
            # Mark as used
            result = await db.visitor_authorizations.update_one(
                {"id": auth_id},
                {"$set": {"status": "used"}}
            )
            if result.modified_count > 0:
                fixed_count += 1
                fixed_auths.append({
                    "visitor_name": visitor_name,
                    "authorization_type": auth_type
                })
                logger.info(f"[cleanup] Fixed auth {auth_id[:8]} - {visitor_name}")
    
    # Also check ALL authorizations regardless of type to see what's happening
    all_pending = await db.visitor_authorizations.find({
        "condominium_id": condo_id,
        "status": {"$in": ["pending", None]},
        "is_active": True
    }, {"_id": 0}).to_list(100)
    
    logger.info(f"[cleanup] Total pending auths in condo: {len(all_pending)}")
    for a in all_pending[:5]:  # Log first 5
        logger.info(f"[cleanup] Pending: {a.get('visitor_name')} - type={a.get('authorization_type')}, status={a.get('status')}")
    
    await log_audit_event(
        AuditEventType.USER_UPDATED, current_user["id"], "guard",
        {"action": "cleanup_authorizations"},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=current_user.get("condominium_id"),
        user_email=current_user.get("email"),
    )
    return {
        "success": True,
        "message": f"Se corrigieron {fixed_count} autorizaciones",
        "fixed_count": fixed_count,
        "fixed_authorizations": fixed_auths,
        "total_pending_checked": len(authorizations),
        "total_all_pending": len(all_pending)
    }

# ==================== HEALTH CHECK ====================
@router.get("/")
async def root():
    return {"message": "GENTURIX Enterprise Platform API", "version": "1.0.0"}

@router.get("/config/dev-mode")
async def get_dev_mode_status():
    """
    Returns whether the server is in development mode.
    DEPRECATED: Use /config/tenant-environment instead for tenant-specific logic.
    """
    return {
        "dev_mode": DEV_MODE,
        "features": {
            "skip_password_reset": DEV_MODE,
            "show_generated_passwords": DEV_MODE,
            "skip_email_validation": DEV_MODE
        },
        "notice": "DEPRECATED: Use tenant environment field instead"
    }

@router.get("/config/tenant-environment")
async def get_tenant_environment(current_user = Depends(get_current_user)):
    """
    Get the environment type for the current user's tenant.
    Returns "demo" or "production" based on tenant configuration.
    """
    condo_id = current_user.get("condominium_id")
    
    # SuperAdmin without condo defaults to production
    if not condo_id:
        if "SuperAdmin" in current_user.get("roles", []):
            return {
                "environment": "production",
                "is_demo": False,
                "features": {
                    "skip_password_reset": False,
                    "show_generated_passwords": False,
                    "send_emails": True
                }
            }
        return {"environment": "production", "is_demo": False}
    
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "environment": 1, "is_demo": 1, "name": 1})
    
    if not condo:
        return {"environment": "production", "is_demo": False}
    
    # Determine environment
    environment = condo.get("environment", "production")
    # Fallback: if environment not set but is_demo is true
    if condo.get("is_demo") and environment == "production":
        environment = "demo"
    
    is_demo = environment == "demo"
    
    return {
        "environment": environment,
        "is_demo": is_demo,
        "condominium_name": condo.get("name", "N/A"),
        "features": {
            "skip_password_reset": is_demo,
            "show_generated_passwords": is_demo,
            "send_emails": not is_demo  # Demo tenants don't send emails
        }
    }

# ==================== EMAIL TOGGLE CONFIG ====================
# This allows SuperAdmin to enable/disable email sending without touching .env

async def get_email_config():
    """Get email configuration from database or create default"""
    config = await db.system_config.find_one({"key": "email_settings"})
    if not config:
        # Default: emails ENABLED for production
        # Change to False only for testing environments
        default_config = {
            "key": "email_settings",
            "email_enabled": True,  # PRODUCTION MODE: Emails enabled by default
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": "system"
        }
        await db.system_config.insert_one(default_config)
        return default_config
    return config

async def is_email_enabled():
    """Quick check if email sending is enabled"""
    config = await get_email_config()
    return config.get("email_enabled", False)

@router.get("/config/email-status")
async def get_config_email_status(current_user = Depends(get_current_user)):
    """
    Get current email sending status.
    Any authenticated user can check this.
    """
    config = await get_email_config()
    return {
        "email_enabled": config.get("email_enabled", False),
        "updated_at": config.get("updated_at"),
        "updated_by": config.get("updated_by"),
        "status_text": "Emails HABILITADOS (modo producción)" if config.get("email_enabled") else "Emails DESHABILITADOS (modo pruebas)"
    }

class EmailToggleRequest(BaseModel):
    email_enabled: bool

@router.post("/config/email-status")
async def set_email_status(
    data: EmailToggleRequest,
    request: Request,
    current_user = Depends(require_role("SuperAdmin"))
):
    """
    Toggle email sending on/off.
    ONLY SuperAdmin can change this setting.
    """
    now = datetime.now(timezone.utc).isoformat()
    
    # Get current status for audit
    old_config = await get_email_config()
    old_status = old_config.get("email_enabled", False)
    
    # Update config
    await db.system_config.update_one(
        {"key": "email_settings"},
        {
            "$set": {
                "email_enabled": data.email_enabled,
                "updated_at": now,
                "updated_by": current_user.get("email", current_user.get("id"))
            }
        },
        upsert=True
    )
    
    # Log to audit
    await log_audit_event(
        AuditEventType.CONFIG_CHANGED if hasattr(AuditEventType, 'CONFIG_CHANGED') else AuditEventType.USER_UPDATED,
        current_user["id"],
        "system_config",
        {
            "setting": "email_enabled",
            "old_value": old_status,
            "new_value": data.email_enabled,
            "changed_by": current_user.get("email")
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    action = "habilitado" if data.email_enabled else "deshabilitado"
    
    return {
        "success": True,
        "email_enabled": data.email_enabled,
        "message": f"Envío de emails {action} exitosamente",
        "status_text": "Emails HABILITADOS (modo producción)" if data.email_enabled else "Emails DESHABILITADOS (modo pruebas)",
        "updated_at": now,
        "updated_by": current_user.get("email")
    }

# ==================== EMAIL SERVICE ENDPOINTS ====================
# Aliases for backward compatibility (imports at top of file)
email_service_send = send_email
get_email_service_status = get_email_status

@router.get("/test-email")
async def test_email_simple(
    email: str = Query(..., description="Email address to send test email to")
):
    """
    Simple GET endpoint for quick email testing.
    
    Usage: GET /api/test-email?email=test@example.com
    
    Returns: { "status": "sent" } on success
    """
    if not is_email_configured():
        return {
            "status": "error",
            "error": "Email service not configured (RESEND_API_KEY missing)"
        }
    
    html = get_notification_email_html(
        title="Test Email - Genturix",
        message=f"This is a test email sent at {datetime.now(timezone.utc).isoformat()}. If you received this, the email service is working correctly.",
        action_url=None
    )
    
    try:
        result = await send_email(
            to=email,
            subject="[TEST] Genturix Email Service",
            html=html
        )
        
        if result.get("success"):
            return {"status": "sent", "email_id": result.get("email_id")}
        else:
            return {"status": "error", "error": result.get("error")}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@router.get("/email/service-status")
async def check_email_service_status(
    current_user = Depends(require_role("SuperAdmin"))
):
    """Get current email service configuration status."""
    return get_email_service_status()


# ==================== EMAIL DEBUG ENDPOINT ====================
@router.get("/email/debug")
async def email_debug_endpoint(
    test_email: Optional[str] = Query(None, description="Optional: Email to send test to"),
    current_user = Depends(require_role("SuperAdmin"))
):
    """
    Comprehensive email system diagnostic endpoint.
    
    Tests:
    1. Resend API connection
    2. Sender configuration
    3. Email toggle status
    4. Optional test email send
    
    Usage: GET /api/email/debug?test_email=your@email.com
    """
    diagnostics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {}
    }
    
    # Check 1: RESEND_API_KEY configured
    api_key_ok = bool(RESEND_API_KEY)
    diagnostics["checks"]["resend_api_key"] = {
        "status": "OK" if api_key_ok else "FAIL",
        "configured": api_key_ok,
        "preview": f"{RESEND_API_KEY[:8]}..." if api_key_ok else None
    }
    
    # Check 2: Sender configuration (from email_service)
    sender = get_sender()
    diagnostics["checks"]["sender_config"] = {
        "status": "OK",
        "sender": sender,
        "service_configured": is_email_configured()
    }
    
    # Check 3: Email toggle status (database)
    email_toggle = await is_email_enabled()
    diagnostics["checks"]["email_toggle"] = {
        "status": "OK" if email_toggle else "WARN",
        "enabled": email_toggle,
        "note": "Emails are ENABLED" if email_toggle else "Emails are DISABLED - enable via POST /api/config/email-status"
    }
    
    # Check 4: Database connectivity for email config
    try:
        config = await get_email_config()
        diagnostics["checks"]["database_config"] = {
            "status": "OK",
            "email_enabled": config.get("email_enabled"),
            "updated_at": config.get("updated_at"),
            "updated_by": config.get("updated_by")
        }
    except Exception as e:
        diagnostics["checks"]["database_config"] = {
            "status": "FAIL",
            "error": str(e)
        }
    
    # Check 5: Optional test email
    if test_email:
        print(f"[EMAIL DEBUG] Sending test email to {test_email}")
        try:
            html = get_notification_email_html(
                title="Email Debug Test - Genturix",
                message=f"This is a diagnostic test email sent at {datetime.now(timezone.utc).isoformat()}. All systems are operational.",
                action_url=None
            )
            result = await send_email(
                to=test_email,
                subject="[DEBUG] Genturix Email System Test",
                html=html
            )
            diagnostics["checks"]["test_email_send"] = {
                "status": "OK" if result.get("success") else "FAIL",
                "recipient": test_email,
                "result": result
            }
        except Exception as e:
            diagnostics["checks"]["test_email_send"] = {
                "status": "FAIL",
                "recipient": test_email,
                "error": str(e)
            }
    
    # Overall status
    all_ok = all(
        check.get("status") in ["OK", "WARN"] 
        for check in diagnostics["checks"].values()
    )
    diagnostics["overall_status"] = "HEALTHY" if all_ok else "ISSUES_DETECTED"
    
    return diagnostics


# ==================== RESEND DIAGNOSTIC ENDPOINT (TEMPORARY) ====================
class TestEmailRequest(BaseModel):
    recipient_email: str
    test_type: str = "simple"  # "simple" or "credentials"

@router.post("/email/test-resend")
async def test_resend_email(
    data: TestEmailRequest,
    request: Request,
    current_user = Depends(require_role("SuperAdmin"))
):
    """
    🔧 DIAGNOSTIC ENDPOINT - TEMPORARY
    
    Tests the Resend email pipeline and returns detailed diagnostics.
    Only SuperAdmin can use this endpoint.
    
    This endpoint will be removed after audit is complete.
    """
    import time
    start_time = time.time()
    
    diagnostics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": str(uuid.uuid4()),
        "requested_by": current_user.get("email"),
        "recipient": data.recipient_email,
        "test_type": data.test_type
    }
    
    # 1. Check environment configuration
    diagnostics["config"] = {
        "RESEND_API_KEY_present": bool(RESEND_API_KEY),
        "RESEND_API_KEY_prefix": RESEND_API_KEY[:10] + "..." if RESEND_API_KEY else None,
        "SENDER_EMAIL": SENDER_EMAIL,
        "ENVIRONMENT": os.environ.get("ENVIRONMENT", "not_set")
    }
    
    # 2. Check email toggle status
    email_config = await get_email_config()
    diagnostics["toggle_status"] = {
        "email_enabled": email_config.get("email_enabled", False),
        "updated_at": email_config.get("updated_at"),
        "config_exists": bool(email_config.get("key"))
    }
    
    # 3. Validate API key format
    if RESEND_API_KEY:
        diagnostics["api_key_validation"] = {
            "starts_with_re_": RESEND_API_KEY.startswith("re_"),
            "length": len(RESEND_API_KEY),
            "valid_format": RESEND_API_KEY.startswith("re_") and len(RESEND_API_KEY) > 20
        }
    else:
        diagnostics["api_key_validation"] = {"error": "API key not configured"}
    
    # 4. Check domain (from SENDER_EMAIL)
    sender_domain = SENDER_EMAIL.split("@")[-1] if "@" in SENDER_EMAIL else "invalid"
    diagnostics["domain_info"] = {
        "sender_email": SENDER_EMAIL,
        "domain": sender_domain,
        "is_resend_test_domain": sender_domain == "resend.dev",
        "warning": "Using resend.dev test domain - emails only work to verified addresses" if sender_domain == "resend.dev" else None
    }
    
    # 5. Attempt to send test email
    if not RESEND_API_KEY:
        diagnostics["send_result"] = {
            "status": "skipped",
            "reason": "RESEND_API_KEY not configured"
        }
    else:
        test_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>🔧 GENTURIX - Test de Diagnóstico Resend</h2>
            <p>Este es un correo de prueba para validar la configuración de Resend.</p>
            <hr>
            <p><strong>Timestamp:</strong> {diagnostics["timestamp"]}</p>
            <p><strong>Request ID:</strong> {diagnostics["request_id"]}</p>
            <p><strong>Enviado por:</strong> {current_user.get("email")}</p>
            <p><strong>Ambiente:</strong> {os.environ.get("ENVIRONMENT", "not_set")}</p>
            <hr>
            <p style="color: #666; font-size: 12px;">
                Este correo fue enviado como parte de una auditoría del sistema de emails.
            </p>
        </body>
        </html>
        """
        
        params = {
            "from": SENDER_EMAIL,
            "to": [data.recipient_email],
            "subject": f"[GENTURIX-DIAG] Test Resend - {diagnostics['request_id'][:8]}",
            "html": test_html
        }
        
        try:
            logger.info(f"[RESEND-DIAG] Attempting test email | request_id={diagnostics['request_id']} | to={data.recipient_email}")
            
            email_response = await asyncio.to_thread(resend.Emails.send, params)
            
            elapsed_time = time.time() - start_time
            
            # Parse response
            if isinstance(email_response, dict):
                diagnostics["send_result"] = {
                    "status": "success",
                    "email_id": email_response.get("id"),
                    "response": email_response,
                    "elapsed_ms": round(elapsed_time * 1000, 2)
                }
                logger.info(f"[RESEND-DIAG] SUCCESS | request_id={diagnostics['request_id']} | email_id={email_response.get('id')}")
            else:
                # Handle Resend SDK response object
                diagnostics["send_result"] = {
                    "status": "success",
                    "email_id": getattr(email_response, 'id', str(email_response)),
                    "response_type": type(email_response).__name__,
                    "elapsed_ms": round(elapsed_time * 1000, 2)
                }
                logger.info(f"[RESEND-DIAG] SUCCESS | request_id={diagnostics['request_id']} | response_type={type(email_response).__name__}")
                
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_str = str(e)
            error_type = type(e).__name__
            
            # Try to extract HTTP status from error
            http_status = None
            if "401" in error_str:
                http_status = 401
            elif "403" in error_str:
                http_status = 403
            elif "422" in error_str:
                http_status = 422
            elif "429" in error_str:
                http_status = 429
            
            diagnostics["send_result"] = {
                "status": "failed",
                "error": error_str,
                "error_type": error_type,
                "http_status": http_status,
                "elapsed_ms": round(elapsed_time * 1000, 2),
                "possible_causes": []
            }
            
            # Add possible causes based on error
            if http_status == 401:
                diagnostics["send_result"]["possible_causes"].append("Invalid API key")
            elif http_status == 403:
                diagnostics["send_result"]["possible_causes"].append("Domain not verified or sender email not authorized")
            elif http_status == 422:
                diagnostics["send_result"]["possible_causes"].append("Invalid email format or missing required fields")
            elif http_status == 429:
                diagnostics["send_result"]["possible_causes"].append("Rate limit exceeded")
            elif "domain" in error_str.lower():
                diagnostics["send_result"]["possible_causes"].append("Sender domain not verified in Resend")
            
            logger.error(f"[RESEND-DIAG] FAILED | request_id={diagnostics['request_id']} | error_type={error_type} | error={error_str}")
    
    # 6. Summary
    diagnostics["summary"] = {
        "api_key_configured": bool(RESEND_API_KEY),
        "sender_email_valid": "@" in SENDER_EMAIL,
        "using_test_domain": sender_domain == "resend.dev",
        "email_toggle_enabled": email_config.get("email_enabled", False),
        "send_attempted": diagnostics.get("send_result", {}).get("status") != "skipped",
        "send_successful": diagnostics.get("send_result", {}).get("status") == "success"
    }
    
    # Log full diagnostics
    logger.info(f"[RESEND-DIAG] Full diagnostics | request_id={diagnostics['request_id']} | summary={diagnostics['summary']}")
    
    return diagnostics

# ==================== SYSTEM RESET (FULL WIPE) ====================
@router.post("/super-admin/reset-all-data")
async def reset_all_data(
    request: Request,
    current_user = Depends(require_role("SuperAdmin"))
):
    """
    ⚠️ DANGER: Complete system wipe.
    Deletes ALL data from ALL collections EXCEPT the SuperAdmin account.
    
    This endpoint:
    - Deletes all condominiums
    - Deletes all users (except SuperAdmin)
    - Deletes all guards, shifts, reservations, authorizations, etc.
    - Leaves the system in a clean state
    """
    superadmin_email = current_user.get("email", "").lower().strip()
    
    # Keep track of what was deleted for the response
    deleted_counts = {}
    
    # Collections to clear completely
    collections_to_clear = [
        "condominiums",
        "guards", 
        "guard_shifts",
        "visitors",
        "visitor_authorizations",
        "access_logs",
        "panic_alerts",
        "reservations",
        "reservation_areas",
        "employees",
        "announcements",
        "audit_logs",
        "push_subscriptions",
        "courses",
        "modules",
        "student_progress"
    ]
    
    for collection_name in collections_to_clear:
        collection = db[collection_name]
        count = await collection.count_documents({})
        await collection.delete_many({})
        deleted_counts[collection_name] = count
    
    # Delete all users EXCEPT the SuperAdmin who is making the request
    users_deleted = await db.users.delete_many({
        "email": {"$ne": superadmin_email}
    })
    deleted_counts["users"] = users_deleted.deleted_count
    
    # Clear system config except email_settings
    await db.system_config.delete_many({"key": {"$ne": "email_settings"}})
    
    # Log this critical action
    await log_audit_event(
        AuditEventType.USER_DELETED if hasattr(AuditEventType, 'USER_DELETED') else AuditEventType.USER_UPDATED,
        current_user["id"],
        "system",
        {
            "action": "FULL_SYSTEM_RESET",
            "deleted_counts": deleted_counts,
            "initiated_by": superadmin_email,
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "success": True,
        "message": "Sistema limpiado completamente. Solo permanece la cuenta SuperAdmin.",
        "deleted_counts": deleted_counts,
        "preserved": {
            "superadmin_account": superadmin_email,
            "email_settings": True
        },
        "next_steps": [
            "Crear un nuevo condominio desde el Onboarding Wizard",
            "Configurar módulos y usuarios",
            "Comenzar pruebas desde cero"
        ]
    }

# Include the billing router in api_router
# This maintains the /api/billing/* path structure
api_router.include_router(billing_router)

# Include the super-admin billing router
# This maintains the /api/super-admin/billing/* path structure
api_router.include_router(billing_super_admin_router)

# ==================== DEVELOPER PROFILE ENDPOINTS ====================
@router.get("/developer-profile")
async def get_developer_profile():
    """
    Public endpoint - Get the platform developer profile.
    No authentication required.
    """
    profile = await db.platform_developer_profile.find_one({}, {"_id": 0})
    
    if not profile:
        # Return default empty profile
        return {
            "id": None,
            "name": "",
            "title": "",
            "bio": "",
            "photo_url": None,
            "email": "",
            "website": "",
            "linkedin": "",
            "github": "",
            "created_at": None,
            "updated_at": None
        }
    
    return profile

@router.put("/super-admin/developer-profile")
async def update_developer_profile(
    profile_data: DeveloperProfileUpdate,
    request: Request,
    current_user = Depends(require_role("SuperAdmin"))
):
    """
    SuperAdmin only - Update the platform developer profile.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # Get existing profile or create new
    existing = await db.platform_developer_profile.find_one({})
    
    if existing:
        # Update existing profile
        update_data = {k: v for k, v in profile_data.model_dump().items() if v is not None}
        update_data["updated_at"] = now_iso
        
        await db.platform_developer_profile.update_one(
            {"id": existing.get("id")},
            {"$set": update_data}
        )
        
        # Log audit
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "action": "developer_profile_updated",
            "user_id": current_user.get("id"),
            "resource_type": "platform",
            "resource_id": "developer_profile",
            "details": {"updated_fields": list(update_data.keys())},
            "created_at": now_iso
        })
        
        # Return updated profile
        updated = await db.platform_developer_profile.find_one({}, {"_id": 0})
        return updated
    else:
        # Create new profile
        new_profile = {
            "id": str(uuid.uuid4()),
            "name": profile_data.name or "",
            "title": profile_data.title or "",
            "bio": profile_data.bio or "",
            "photo_url": profile_data.photo_url,
            "email": profile_data.email or "",
            "website": profile_data.website or "",
            "linkedin": profile_data.linkedin or "",
            "github": profile_data.github or "",
            "created_at": now_iso,
            "updated_at": now_iso
        }
        
        await db.platform_developer_profile.insert_one(new_profile)
        
        # Log audit
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "action": "developer_profile_created",
            "user_id": current_user.get("id"),
            "resource_type": "platform",
            "resource_id": "developer_profile",
            "details": {"profile_id": new_profile["id"]},
            "created_at": now_iso
        })
        
        # Remove _id before returning
        if "_id" in new_profile:
            del new_profile["_id"]
        return new_profile

@router.post("/super-admin/developer-profile/photo")
async def upload_developer_photo(
    request: Request,
    current_user = Depends(require_role("SuperAdmin"))
):
    """
    SuperAdmin only - Upload developer profile photo.
    Accepts base64 encoded image data.
    """
    try:
        body = await request.json()
        photo_data = body.get("photo_data")  # Base64 encoded image
        
        if not photo_data:
            raise HTTPException(status_code=400, detail="No photo data provided")
        
        # For now, store the base64 data directly
        # In production, you'd upload to S3/Cloudinary and store the URL
        now_iso = datetime.now(timezone.utc).isoformat()
        
        # Ensure profile exists
        existing = await db.platform_developer_profile.find_one({})
        
        if existing:
            await db.platform_developer_profile.update_one(
                {"id": existing.get("id")},
                {"$set": {"photo_url": photo_data, "updated_at": now_iso}}
            )
        else:
            new_profile = {
                "id": str(uuid.uuid4()),
                "name": "",
                "title": "",
                "bio": "",
                "photo_url": photo_data,
                "email": "",
                "website": "",
                "linkedin": "",
                "github": "",
                "created_at": now_iso,
                "updated_at": now_iso
            }
            await db.platform_developer_profile.insert_one(new_profile)
        
        await log_audit_event(
            AuditEventType.USER_UPDATED, current_user["id"], "developer",
            {"action": "photo_uploaded"},
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "unknown"),
            condominium_id=current_user.get("condominium_id"),
            user_email=current_user.get("email"),
        )
        return {"success": True, "message": "Photo uploaded successfully"}
        
    except Exception as e:
        logger.error(f"[DEVELOPER-PHOTO] Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Include the router in the main app

