"""GENTURIX - Condominiums Multi-tenant Router (Auto-extracted from server.py)"""
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

@router.post("/condominiums", response_model=CondominiumResponse)
async def create_production_condominium(
    condo_data: CondominiumCreate,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """
    Create a new PRODUCTION condominium/tenant (Super Admin only).
    
    BILLING ENGINE INTEGRATION:
    - Calculates initial invoice based on seats and billing cycle
    - Creates billing event audit trail
    - Sets billing_status to "pending_payment" (awaiting first payment)
    - Does NOT integrate with payment providers yet (Stripe, Sinpe, etc.)
    
    For DEMO tenants, use POST /api/superadmin/condominiums/demo instead.
    """
    condo_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Initialize module config with defaults
    modules = condo_data.modules if condo_data.modules else CondominiumModules()
    
    # BILLING ENGINE: Determine seat count (prefer initial_units over legacy paid_seats)
    paid_seats = condo_data.initial_units if condo_data.initial_units else (
        condo_data.paid_seats if condo_data.paid_seats else 10
    )
    
    # BILLING ENGINE: Get effective price for this condominium
    # (Uses global pricing since condo doesn't exist yet)
    price_per_seat = await get_effective_seat_price(None)
    
    # BILLING ENGINE: Calculate invoice preview
    billing_preview = await calculate_billing_preview(
        initial_units=paid_seats,
        billing_cycle=condo_data.billing_cycle,
        condominium_id=None  # New condo, no override yet
    )
    
    # Build condominium document with enhanced billing fields
    condo_doc = {
        "id": condo_id,
        "name": condo_data.name,
        "address": condo_data.address,
        "contact_email": condo_data.contact_email,
        "contact_phone": condo_data.contact_phone,
        "billing_email": condo_data.billing_email or condo_data.contact_email,
        "max_users": paid_seats,  # Sync with paid_seats
        "current_users": 0,
        "modules": modules.model_dump(),
        "status": "active",
        "is_demo": False,
        "environment": "production",
        "is_active": True,
        # BILLING ENGINE: Enhanced billing configuration
        "billing_model": "per_seat",
        "paid_seats": paid_seats,
        "price_per_seat": price_per_seat,
        "billing_cycle": condo_data.billing_cycle,
        "billing_provider": condo_data.billing_provider,
        "billing_enabled": True,
        "billing_status": "pending_payment",  # Awaiting first payment
        "next_invoice_amount": billing_preview["effective_amount"],
        "next_billing_date": billing_preview["next_billing_date"],
        "billing_started_at": now.isoformat(),
        "yearly_discount_percent": billing_preview["yearly_discount_percent"],
        # Legacy fields (kept for backward compatibility)
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
        "price_per_user": price_per_seat,  # Legacy field
        "discount_percent": 0,
        "free_modules": [],
        "plan": "basic",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.condominiums.insert_one(condo_doc)
    
    # Create default condominium settings
    settings_doc = {
        "condominium_id": condo_id,
        "condominium_name": condo_data.name,
        **get_default_condominium_settings(),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    await db.condominium_settings.insert_one(settings_doc)
    
    # BILLING ENGINE: Log creation event
    await log_billing_engine_event(
        event_type="condominium_created",
        condominium_id=condo_id,
        data={
            "name": condo_data.name,
            "paid_seats": paid_seats,
            "price_per_seat": price_per_seat,
            "billing_cycle": condo_data.billing_cycle,
            "billing_provider": condo_data.billing_provider,
            "monthly_amount": billing_preview["monthly_amount"],
            "effective_amount": billing_preview["effective_amount"],
            "next_billing_date": billing_preview["next_billing_date"]
        },
        triggered_by=current_user["id"],
        previous_state=None,
        new_state={
            "paid_seats": paid_seats,
            "billing_status": "pending_payment",
            "billing_cycle": condo_data.billing_cycle
        }
    )
    
    # Log audit event
    await log_audit_event(
        AuditEventType.CONDO_CREATED,
        current_user["id"],
        "super_admin",
        {
            "condo_id": condo_id, 
            "name": condo_data.name, 
            "action": "created", 
            "environment": "production",
            "billing_provider": condo_data.billing_provider,
            "initial_seats": paid_seats
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return CondominiumResponse(
        id=condo_id,
        name=condo_data.name,
        address=condo_data.address,
        contact_email=condo_data.contact_email,
        contact_phone=condo_data.contact_phone,
        billing_email=condo_data.billing_email or condo_data.contact_email,
        max_users=paid_seats,
        current_users=0,
        modules=modules.model_dump(),
        is_active=True,
        created_at=condo_doc["created_at"],
        environment="production",
        is_demo=False,
        # BILLING ENGINE: Enhanced response
        billing_model="per_seat",
        paid_seats=paid_seats,
        price_per_seat=price_per_seat,
        billing_cycle=condo_data.billing_cycle,
        billing_provider=condo_data.billing_provider,
        billing_status="pending_payment",
        next_invoice_amount=billing_preview["effective_amount"],
        next_billing_date=billing_preview["next_billing_date"],
        billing_started_at=condo_doc["billing_started_at"],
        yearly_discount_percent=billing_preview["yearly_discount_percent"],
        status="active",
        plan="basic"
    )


@router.post("/superadmin/condominiums/demo", response_model=CondominiumResponse)
async def create_demo_condominium(
    condo_data: DemoCondominiumCreate,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    Create a new DEMO condominium (Super Admin only).
    
    DEMO tenants have:
    - Fixed seat limit of 10 users
    - NO billing (billing_enabled = false)
    - NO Stripe integration
    - Default modules enabled
    - Simplified creation process
    
    For PRODUCTION tenants with billing, use POST /api/condominiums instead.
    """
    condo_id = str(uuid.uuid4())
    
    # Initialize all modules enabled by default for demo
    modules = CondominiumModules()
    
    # DEMO configuration - fixed values
    DEMO_SEAT_LIMIT = 10
    
    condo_doc = {
        "id": condo_id,
        "name": condo_data.name,
        "address": condo_data.address,
        "contact_email": condo_data.contact_email,
        "contact_phone": condo_data.contact_phone or "",
        "max_users": DEMO_SEAT_LIMIT,
        "current_users": 0,
        "modules": modules.model_dump(),
        "status": "demo",
        "is_demo": True,
        "environment": "demo",
        "is_active": True,
        # Billing configuration (DEMO - disabled)
        "paid_seats": DEMO_SEAT_LIMIT,
        "billing_enabled": False,
        "billing_status": "demo",
        "stripe_customer_id": None,
        "price_per_user": 0,  # Free for demo
        "discount_percent": 100,  # 100% discount = free
        "free_modules": ["security", "visitors", "hr", "reservations", "school", "payments"],
        "plan": "demo",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.condominiums.insert_one(condo_doc)
    
    # Create default condominium settings
    settings_doc = {
        "condominium_id": condo_id,
        "condominium_name": condo_data.name,
        **get_default_condominium_settings(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.condominium_settings.insert_one(settings_doc)
    
    await log_audit_event(
        AuditEventType.CONDO_CREATED,
        current_user["id"],
        "super_admin",
        {"condo_id": condo_id, "name": condo_data.name, "action": "created", "environment": "demo"},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    logger.info(f"Demo condominium created: {condo_data.name} by {current_user['email']}")
    
    return CondominiumResponse(
        id=condo_id,
        name=condo_data.name,
        address=condo_data.address,
        contact_email=condo_data.contact_email,
        contact_phone=condo_data.contact_phone or "",
        max_users=DEMO_SEAT_LIMIT,
        current_users=0,
        modules=modules.model_dump(),
        is_active=True,
        created_at=condo_doc["created_at"],
        environment="demo",
        is_demo=True,
        paid_seats=DEMO_SEAT_LIMIT,
        billing_status="demo",
        status="demo",
        plan="demo"
    )


class DemoWithDataRequest(BaseModel):
    """Request model for creating a demo condominium with pre-loaded test data"""
    name: str = Field(..., min_length=2, max_length=100)
    admin_email: EmailStr
    admin_name: str = Field(default="Admin Demo")
    include_guards: bool = Field(default=True)
    include_residents: bool = Field(default=True)
    include_areas: bool = Field(default=True)


@router.post("/superadmin/condominiums/demo-with-data")
async def create_demo_with_test_data(
    request_data: DemoWithDataRequest,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    Create a DEMO condominium with pre-loaded test data for quick demonstrations.
    
    This endpoint creates:
    - Demo condominium (10 seats, no billing)
    - Admin user with credentials
    - Optional: 2 sample guards
    - Optional: 3 sample residents  
    - Optional: 2 reservation areas (Gym, Pool)
    
    Returns all created credentials for immediate use.
    """
    # Validate admin email not in use
    existing_user = await db.users.find_one({"email": request_data.admin_email.lower()})
    if existing_user:
        raise HTTPException(status_code=400, detail=f"El email {request_data.admin_email} ya está registrado")
    
    # Generate IDs
    condo_id = str(uuid.uuid4())
    admin_id = str(uuid.uuid4())
    
    # Generate passwords
    admin_password = generate_temporary_password(12)
    guard1_password = generate_temporary_password(10)
    guard2_password = generate_temporary_password(10)
    
    created_users = []
    created_areas = []
    
    try:
        # === STEP 1: Create Demo Condominium ===
        modules = CondominiumModules()
        condo_doc = {
            "id": condo_id,
            "name": request_data.name,
            "address": "Dirección Demo - Para pruebas",
            "contact_email": request_data.admin_email.lower(),
            "contact_phone": "",
            "max_users": 10,
            "current_users": 0,
            "modules": modules.model_dump(),
            "status": "demo",
            "is_demo": True,
            "environment": "demo",
            "is_active": True,
            "paid_seats": 10,
            "billing_enabled": False,
            "billing_status": "demo",
            "stripe_customer_id": None,
            "price_per_user": 0,
            "discount_percent": 100,
            "free_modules": ["security", "visitors", "hr", "reservations", "school", "payments"],
            "plan": "demo",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.condominiums.insert_one(condo_doc)
        
        # Create settings
        settings_doc = {
            "condominium_id": condo_id,
            "condominium_name": request_data.name,
            **get_default_condominium_settings(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.condominium_settings.insert_one(settings_doc)
        
        # === STEP 2: Create Admin User ===
        admin_doc = {
            "id": admin_id,
            "email": request_data.admin_email.lower(),
            "hashed_password": hash_password(admin_password),
            "full_name": request_data.admin_name,
            "roles": [RoleEnum.ADMINISTRADOR.value],
            "condominium_id": condo_id,
            "is_active": True,
            "status": "active",
            "is_locked": False,
            "password_reset_required": False,  # Demo doesn't require reset
            "created_by": current_user["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(admin_doc)
        created_users.append({
            "role": "Administrador",
            "email": request_data.admin_email.lower(),
            "password": admin_password,
            "name": request_data.admin_name
        })
        
        user_count = 1  # Admin
        
        # === STEP 3: Create Guards (optional) ===
        if request_data.include_guards:
            guard1_id = str(uuid.uuid4())
            guard1_email = f"guardia1.{condo_id[:8]}@demo.genturix.com"
            guard1_doc = {
                "id": guard1_id,
                "email": guard1_email,
                "hashed_password": hash_password(guard1_password),
                "full_name": "Carlos Seguridad",
                "roles": [RoleEnum.GUARDA.value],
                "condominium_id": condo_id,
                "is_active": True,
                "status": "active",
                "is_locked": False,
                "password_reset_required": False,
                "created_by": admin_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(guard1_doc)
            created_users.append({
                "role": "Guardia",
                "email": guard1_email,
                "password": guard1_password,
                "name": "Carlos Seguridad"
            })
            
            guard2_id = str(uuid.uuid4())
            guard2_email = f"guardia2.{condo_id[:8]}@demo.genturix.com"
            guard2_doc = {
                "id": guard2_id,
                "email": guard2_email,
                "hashed_password": hash_password(guard2_password),
                "full_name": "María Vigilancia",
                "roles": [RoleEnum.GUARDA.value],
                "condominium_id": condo_id,
                "is_active": True,
                "status": "active",
                "is_locked": False,
                "password_reset_required": False,
                "created_by": admin_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(guard2_doc)
            created_users.append({
                "role": "Guardia",
                "email": guard2_email,
                "password": guard2_password,
                "name": "María Vigilancia"
            })
            user_count += 2
        
        # === STEP 4: Create Residents (optional) ===
        if request_data.include_residents:
            residents_data = [
                {"name": "Roberto Pérez", "apartment": "A-101"},
                {"name": "Ana García", "apartment": "B-202"},
                {"name": "Luis Martínez", "apartment": "C-303"}
            ]
            for resident in residents_data:
                res_id = str(uuid.uuid4())
                res_password = generate_temporary_password(10)
                res_email = f"residente.{res_id[:8]}@demo.genturix.com"
                res_doc = {
                    "id": res_id,
                    "email": res_email,
                    "hashed_password": hash_password(res_password),
                    "full_name": resident["name"],
                    "roles": [RoleEnum.RESIDENTE.value],
                    "condominium_id": condo_id,
                    "apartment": resident["apartment"],
                    "is_active": True,
                    "status": "active",
                    "is_locked": False,
                    "password_reset_required": False,
                    "created_by": admin_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                await db.users.insert_one(res_doc)
                created_users.append({
                    "role": "Residente",
                    "email": res_email,
                    "password": res_password,
                    "name": resident["name"],
                    "apartment": resident["apartment"]
                })
            user_count += 3
        
        # === STEP 5: Create Reservation Areas (optional) ===
        if request_data.include_areas:
            areas_data = [
                {"name": "Gimnasio", "capacity": 15, "open_time": "06:00", "close_time": "22:00"},
                {"name": "Piscina", "capacity": 25, "open_time": "08:00", "close_time": "20:00"}
            ]
            for area in areas_data:
                area_id = str(uuid.uuid4())
                area_doc = {
                    "id": area_id,
                    "condominium_id": condo_id,
                    "name": area["name"],
                    "capacity": area["capacity"],
                    "requires_approval": False,
                    "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
                    "open_time": area["open_time"],
                    "close_time": area["close_time"],
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await db.reservation_areas.insert_one(area_doc)
                created_areas.append({
                    "id": area_id,
                    "name": area["name"],
                    "capacity": area["capacity"],
                    "schedule": f"{area['open_time']} - {area['close_time']}"
                })
        
        # Update user count
        await db.condominiums.update_one(
            {"id": condo_id},
            {"$set": {"current_users": user_count}}
        )
        
        # Audit log
        await log_audit_event(
            AuditEventType.CONDO_CREATED,
            current_user["id"],
            "super_admin",
            {
                "action": "demo_with_data_created",
                "condo_id": condo_id,
                "name": request_data.name,
                "users_created": len(created_users),
                "areas_created": len(created_areas)
            },
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "unknown")
        )
        
        logger.info(f"Demo condominium with data created: {request_data.name} by {current_user['email']} ({len(created_users)} users, {len(created_areas)} areas)")
        
        return {
            "success": True,
            "message": f"Demo '{request_data.name}' creado con datos de prueba",
            "condominium": {
                "id": condo_id,
                "name": request_data.name,
                "environment": "demo",
                "seat_limit": 10,
                "users_created": user_count
            },
            "credentials": created_users,
            "areas_created": created_areas,
            "warning": "⚠️ Guarda estas credenciales. Este es un ambiente DEMO sin emails."
        }
        
    except Exception as e:
        # Rollback on error
        logger.error(f"Demo with data creation failed, rolling back: {str(e)}")
        await db.condominiums.delete_one({"id": condo_id})
        await db.users.delete_many({"condominium_id": condo_id})
        await db.reservation_areas.delete_many({"condominium_id": condo_id})
        await db.condominium_settings.delete_one({"condominium_id": condo_id})
        raise HTTPException(status_code=500, detail=f"Error al crear demo: {str(e)}")


@router.get("/condominiums")
async def list_condominiums(
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """List all condominiums (Super Admin only)"""
    condos = await db.condominiums.find({}, {"_id": 0}).to_list(100)
    # Enrich with default values for fields that may not exist
    for condo in condos:
        condo.setdefault("status", "active")
        condo.setdefault("is_demo", False)
        condo.setdefault("environment", "production")  # Default to production for existing condos
        condo.setdefault("discount_percent", 0.0)
        condo.setdefault("plan", "basic")
        condo.setdefault("price_per_user", 1.0)
        # Sync environment with is_demo for backwards compatibility
        if condo.get("is_demo") and condo.get("environment") == "production":
            condo["environment"] = "demo"
        # Calculate current_users from database if not set
        if condo.get("current_users", 0) == 0:
            user_count = await db.users.count_documents({"condominium_id": condo["id"], "is_active": True})
            condo["current_users"] = user_count
    return condos

@router.get("/condominiums/{condo_id}", response_model=CondominiumResponse)
async def get_condominium(
    condo_id: str,
    current_user = Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPERVISOR))
):
    """Get condominium details"""
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominium not found")
    return condo

@router.patch("/condominiums/{condo_id}")
async def update_condominium(
    condo_id: str,
    update_data: CondominiumUpdate,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Update condominium details (Super Admin only)"""
    update_fields = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # Convert modules Pydantic model to dict if present
    if "modules" in update_fields and update_fields["modules"]:
        update_fields["modules"] = update_fields["modules"].model_dump() if hasattr(update_fields["modules"], "model_dump") else update_fields["modules"]
    
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.condominiums.update_one(
        {"id": condo_id},
        {"$set": update_fields}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Condominium not found")
    
    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "condominiums",
        {"action": "condominium_updated", "condo_id": condo_id},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id,
        user_email=current_user.get("email"),
    )
    return {"message": "Condominium updated successfully"}

@router.delete("/condominiums/{condo_id}")
async def deactivate_condominium(
    condo_id: str,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Deactivate a condominium (soft delete)"""
    result = await db.condominiums.update_one(
        {"id": condo_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Condominium not found")
    
    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "condominiums",
        {"action": "condominium_deactivated", "condo_id": condo_id},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id,
        user_email=current_user.get("email"),
    )
    return {"message": "Condominium deactivated"}

@router.get("/condominiums/{condo_id}/users")
async def get_condominium_users(
    condo_id: str,
    current_user = Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPERVISOR))
):
    """Get all users belonging to a condominium"""
    users = await db.users.find(
        {"condominium_id": condo_id},
        {"_id": 0, "hashed_password": 0}
    ).to_list(500)
    return users

@router.get("/condominiums/{condo_id}/billing")
async def get_condominium_billing(
    condo_id: str,
    current_user = Depends(require_role(RoleEnum.ADMINISTRADOR))
):
    """Get billing information for a condominium"""
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominium not found")
    
    # Calculate monthly cost
    user_count = await db.users.count_documents({"condominium_id": condo_id, "is_active": True})
    price_per_user = condo.get("price_per_user", 1.0)
    monthly_cost = user_count * price_per_user
    
    return {
        "condominium_id": condo_id,
        "condominium_name": condo.get("name"),
        "active_users": user_count,
        "price_per_user": price_per_user,
        "monthly_cost_usd": monthly_cost,
        "billing_cycle": "monthly",
        "currency": "USD"
    }

@router.patch("/condominiums/{condo_id}/modules/{module_name}")
async def update_module_config(
    condo_id: str,
    module_name: str,
    enabled: bool,
    settings: Optional[Dict[str, Any]] = None,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Enable/disable a module for a condominium"""
    valid_modules = ["security", "hr", "school", "payments", "audit", "reservations", "access_control", "messaging", "visits", "cctv"]
    
    if module_name not in valid_modules:
        logger.error(f"[module-toggle] Invalid module '{module_name}' requested. Valid: {valid_modules}")
        raise HTTPException(status_code=400, detail=f"Invalid module. Valid modules: {', '.join(valid_modules)}")
    
    # Verify condominium exists first
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "id": 1, "name": 1, "modules": 1})
    if not condo:
        logger.error(f"[module-toggle] Condominium {condo_id} not found")
        raise HTTPException(status_code=404, detail="Condominium not found")
    
    # Check current module structure - it might be a boolean or an object
    current_modules = condo.get("modules", {})
    current_value = current_modules.get(module_name)
    
    # If module is stored as a boolean (legacy format), convert to object format
    if isinstance(current_value, bool) or current_value is None:
        # Use $set with the full module object structure
        update_data = {
            f"modules.{module_name}": {"enabled": enabled},
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    else:
        # Module is already an object, just update the enabled field
        update_data = {
            f"modules.{module_name}.enabled": enabled,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    
    if settings:
        update_data[f"modules.{module_name}.settings"] = settings
    
    logger.info(f"[module-toggle] Updating module '{module_name}' to enabled={enabled} for condo '{condo.get('name')}' ({condo_id})")
    logger.info(f"[module-toggle] Current module value: {current_value} (type: {type(current_value).__name__})")
    logger.info(f"[module-toggle] Update data: {update_data}")
    
    result = await db.condominiums.update_one(
        {"id": condo_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0 and result.matched_count == 0:
        logger.error(f"[module-toggle] No document matched for condo_id={condo_id}")
        raise HTTPException(status_code=404, detail="Condominium not found")
    
    logger.info(f"[module-toggle] SUCCESS: Module '{module_name}' {'enabled' if enabled else 'disabled'} for condo {condo_id}. Modified: {result.modified_count}")
    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "condominiums",
        {"action": "module_config_updated", "condo_id": condo_id, "module": module_name},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id,
        user_email=current_user.get("email"),
    )
    return {"message": f"Module '{module_name}' {'enabled' if enabled else 'disabled'} successfully", "module": module_name, "enabled": enabled}

