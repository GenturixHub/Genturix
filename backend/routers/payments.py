"""GENTURIX - Payments + SaaS Billing Router (Auto-extracted from server.py)"""
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

# ==================== PAYMENTS MODULE ====================
# GENTURIX PRICING MODEL: $1 per user per month
# Simple, accessible, massive adoption model

class UserSubscriptionCreate(BaseModel):
    user_count: int = 1


# ==================== PRICING SYSTEM (SaaS) ====================
# Default fallback price - used ONLY if database config is missing
FALLBACK_PRICE_PER_SEAT = 1.50
DEFAULT_CURRENCY = "USD"

async def ensure_global_pricing_config():
    """
    Ensure global pricing configuration exists in database.
    Called on startup to initialize default config if missing.
    """
    existing = await db.system_config.find_one({"id": "global_pricing"})
    if not existing:
        default_config = {
            "id": "global_pricing",
            "default_seat_price": FALLBACK_PRICE_PER_SEAT,
            "currency": DEFAULT_CURRENCY,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.system_config.insert_one(default_config)
        logger.info(f"[PRICING] Global pricing config initialized: ${FALLBACK_PRICE_PER_SEAT}/seat")

async def get_global_pricing() -> dict:
    """
    Get global pricing configuration from database.
    Returns: {"default_seat_price": float, "currency": str}
    """
    config = await db.system_config.find_one({"id": "global_pricing"}, {"_id": 0})
    if config:
        return {
            "default_seat_price": config.get("default_seat_price", FALLBACK_PRICE_PER_SEAT),
            "currency": config.get("currency", DEFAULT_CURRENCY)
        }
    # Fallback if config missing (should not happen after startup)
    return {
        "default_seat_price": FALLBACK_PRICE_PER_SEAT,
        "currency": DEFAULT_CURRENCY
    }

async def get_effective_seat_price(condominium_id: str) -> float:
    """
    PHASE 2: Get effective seat price for a condominium.
    
    Logic:
    1. Look up condominium's seat_price_override
    2. If override exists and > 0 → return override
    3. If not → return global default_seat_price
    4. If nothing found → safe fallback = 1.50
    
    NEVER hardcode price in endpoints. Always use this function.
    """
    # Step 1: Check condominium for override
    if condominium_id:
        condo = await db.condominiums.find_one(
            {"id": condominium_id},
            {"_id": 0, "seat_price_override": 1}
        )
        if condo:
            override = condo.get("seat_price_override")
            if override is not None and override > 0:
                logger.debug(f"[PRICING] Using override ${override}/seat for condo {condominium_id[:8]}...")
                return float(override)
    
    # Step 2: Get global default
    global_config = await get_global_pricing()
    return global_config["default_seat_price"]

async def get_condominium_pricing_info(condominium_id: str) -> dict:
    """
    Get complete pricing info for a condominium.
    Returns: {"effective_price": float, "uses_override": bool, "override_price": float|None, "global_price": float, "currency": str}
    """
    global_config = await get_global_pricing()
    
    override_price = None
    uses_override = False
    
    if condominium_id:
        condo = await db.condominiums.find_one(
            {"id": condominium_id},
            {"_id": 0, "seat_price_override": 1}
        )
        if condo and condo.get("seat_price_override") is not None and condo.get("seat_price_override") > 0:
            override_price = condo.get("seat_price_override")
            uses_override = True
    
    effective_price = override_price if uses_override else global_config["default_seat_price"]
    
    return {
        "effective_price": effective_price,
        "uses_override": uses_override,
        "override_price": override_price,
        "global_price": global_config["default_seat_price"],
        "currency": global_config["currency"]
    }

# Legacy constant for backward compatibility (will be replaced with dynamic pricing)
GENTURIX_PRICE_PER_USER = 1.00  # DEPRECATED: Use get_effective_seat_price() instead

async def calculate_subscription_price_dynamic(user_count: int, condominium_id: str) -> dict:
    """
    PHASE 4: Calculate price using dynamic pricing system.
    Returns: {"total": float, "price_per_seat": float, "currency": str}
    """
    price_per_seat = await get_effective_seat_price(condominium_id)
    total = round(user_count * price_per_seat, 2)
    global_config = await get_global_pricing()
    
    return {
        "total": total,
        "price_per_seat": price_per_seat,
        "currency": global_config["currency"]
    }

def calculate_subscription_price(user_count: int) -> float:
    """DEPRECATED: Use calculate_subscription_price_dynamic() instead"""
    return round(user_count * GENTURIX_PRICE_PER_USER, 2)

# ==================== BILLING ENGINE ====================
# Central billing calculation and event logging system
# Independent of payment providers (Stripe, Sinpe, TicoPay, Manual)

YEARLY_DISCOUNT_PERCENT = 10.0  # 10% discount for yearly billing (default)

async def calculate_invoice(
    condominium: dict, 
    billing_cycle: str = None,
    seat_price_override: float = None,
    yearly_discount_override: float = None
) -> dict:
    """
    BILLING ENGINE: Central invoice calculation function.
    
    This is the single source of truth for all billing calculations.
    Used by: Stripe integration, manual billing, reports, upgrade/downgrade
    
    Args:
        condominium: Dict with condominium data (must have 'id', 'paid_seats')
        billing_cycle: Override billing cycle (defaults to condominium's cycle)
        seat_price_override: Custom price per seat (for preview/onboarding)
        yearly_discount_override: Custom yearly discount 0-50% (for preview/onboarding)
    
    Returns:
        {
            "seats": int,
            "price_per_seat": float,
            "billing_cycle": str,
            "monthly_amount": float,
            "yearly_amount": float,
            "yearly_discount_percent": float,
            "effective_amount": float,
            "next_billing_date": str,
            "currency": str
        }
    """
    condo_id = condominium.get("id")
    seats = condominium.get("paid_seats", 10)
    cycle = billing_cycle or condominium.get("billing_cycle", "monthly")
    
    # Get effective price (override > condo override > global > fallback)
    if seat_price_override is not None and seat_price_override > 0:
        price_per_seat = seat_price_override
    else:
        price_per_seat = await get_effective_seat_price(condo_id)
    
    global_config = await get_global_pricing()
    
    # Get effective discount (override > condo override > global)
    if yearly_discount_override is not None and 0 <= yearly_discount_override <= 50:
        discount_percent = yearly_discount_override
    else:
        # Check if condo has custom discount
        if condo_id:
            condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "yearly_discount_percent": 1})
            if condo and condo.get("yearly_discount_percent") is not None:
                discount_percent = condo.get("yearly_discount_percent")
            else:
                discount_percent = YEARLY_DISCOUNT_PERCENT
        else:
            discount_percent = YEARLY_DISCOUNT_PERCENT
    
    # Calculate amounts
    monthly_amount = round(seats * price_per_seat, 2)
    yearly_amount_before_discount = monthly_amount * 12
    yearly_discount = round(yearly_amount_before_discount * (discount_percent / 100), 2)
    yearly_amount = round(yearly_amount_before_discount - yearly_discount, 2)
    
    # Effective amount based on cycle
    effective_amount = yearly_amount if cycle == "yearly" else monthly_amount
    
    # Calculate next billing date
    now = datetime.now(timezone.utc)
    if cycle == "yearly":
        next_billing = now + timedelta(days=365)
    else:
        # Next month, same day
        if now.month == 12:
            next_billing = now.replace(year=now.year + 1, month=1)
        else:
            next_billing = now.replace(month=now.month + 1)
    
    return {
        "seats": seats,
        "price_per_seat": price_per_seat,
        "billing_cycle": cycle,
        "monthly_amount": monthly_amount,
        "yearly_amount": yearly_amount,
        "yearly_amount_before_discount": yearly_amount_before_discount,
        "yearly_discount_percent": discount_percent,
        "yearly_discount_amount": yearly_discount,
        "effective_amount": effective_amount,
        "next_billing_date": next_billing.isoformat(),
        "currency": global_config.get("currency", "USD")
    }

async def calculate_billing_preview(
    initial_units: int, 
    billing_cycle: str = "monthly", 
    condominium_id: str = None,
    seat_price_override: float = None,
    yearly_discount_override: float = None
) -> dict:
    """
    Calculate billing preview for new condominium or seat change.
    Does NOT create any records - purely informational.
    
    Args:
        seat_price_override: Custom price per seat (overrides global/condo price)
        yearly_discount_override: Custom yearly discount 0-50% (overrides global)
    """
    # Create temporary condo dict for calculation
    temp_condo = {
        "id": condominium_id,
        "paid_seats": initial_units,
        "billing_cycle": billing_cycle
    }
    
    return await calculate_invoice(
        temp_condo, 
        billing_cycle, 
        seat_price_override=seat_price_override,
        yearly_discount_override=yearly_discount_override
    )

# ==================== END BILLING ENGINE ====================
# NOTE: The following functions are now imported from modules.billing (PHASE 3):
# - log_billing_engine_event (from modules.billing.service)
# - update_condominium_billing_status (from modules.billing.service)
# - send_billing_notification_email (from modules.billing.service)
# - process_billing_for_condominium (from modules.billing.scheduler)
# - run_daily_billing_check (from modules.billing.scheduler)
# - start_billing_scheduler (from modules.billing.scheduler)
# - stop_billing_scheduler (from modules.billing.scheduler)
# - DEFAULT_GRACE_PERIOD_DAYS (from modules.billing.service)
# - BILLING_EMAIL_TEMPLATES (from modules.billing.service)

# ==================== PARTIAL BLOCKING MIDDLEWARE ====================
"""
BLOQUEO PARCIAL INTELIGENTE

- Condominios suspendidos solo pueden hacer GET requests
- POST, PUT, DELETE están bloqueados
- Dashboard y consultas siguen funcionando
"""

# Routes that are ALWAYS allowed (even when suspended)
ALWAYS_ALLOWED_ROUTES = [
    "/api/auth/",           # Authentication
    "/api/health",          # Health checks
    "/api/billing/",        # Billing endpoints (need to pay!)
    "/api/super-admin/",    # SuperAdmin routes
]

# Routes that are blocked when suspended (checked by method)
BLOCKED_WHEN_SUSPENDED_METHODS = ["POST", "PUT", "DELETE", "PATCH"]


async def check_billing_access(
    condominium_id: str,
    method: str,
    path: str
) -> Tuple[bool, Optional[str]]:
    """
    Central function to check if a request should be allowed based on billing status.
    
    Returns:
        Tuple[bool, Optional[str]]: (is_allowed, error_message)
    
    Logic:
    - Suspended condos: Block POST/PUT/DELETE/PATCH, allow GET
    - Past due condos: Allow all (warning only)
    - Active condos: Allow all
    """
    # Check if route is always allowed
    for allowed_route in ALWAYS_ALLOWED_ROUTES:
        if path.startswith(allowed_route):
            return True, None
    
    # Get condominium
    condo = await db.condominiums.find_one(
        {"id": condominium_id},
        {"_id": 0, "billing_status": 1, "environment": 1, "is_demo": 1, "name": 1}
    )
    
    if not condo:
        return True, None  # Unknown condo - let other middleware handle
    
    # Demo condos are never blocked
    if condo.get("is_demo") or condo.get("environment") == "demo":
        return True, None
    
    billing_status = condo.get("billing_status", "active")
    
    # Suspended: Block modifications
    if billing_status == "suspended":
        if method.upper() in BLOCKED_WHEN_SUSPENDED_METHODS:
            return False, f"Cuenta suspendida por falta de pago. Solo consultas permitidas. Contacte soporte para regularizar."
    
    return True, None


async def check_billing_access_dependency(
    request: Request,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    FastAPI dependency for partial blocking.
    Raises HTTPException if access is denied.
    """
    condominium_id = current_user.get("condominium_id")
    
    # SuperAdmins are never blocked
    user_roles = current_user.get("roles", [])
    if "SuperAdmin" in user_roles:
        return current_user
    
    if not condominium_id:
        return current_user
    
    is_allowed, error_message = await check_billing_access(
        condominium_id,
        request.method,
        request.url.path
    )
    
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=error_message
        )
    
    return current_user


# ==================== BILLING SCHEDULER ADMIN ENDPOINTS ====================

@billing_router.post("/scheduler/run-now")
async def run_billing_scheduler_now(
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    SuperAdmin: Manually trigger the daily billing check.
    Useful for testing or immediate processing.
    """
    results = await run_daily_billing_check()
    
    return {
        "success": True,
        "message": "Billing check completed",
        "results": {
            "total_evaluated": results["total_evaluated"],
            "transitioned_to_past_due": results["transitioned_to_past_due"],
            "transitioned_to_suspended": results["transitioned_to_suspended"],
            "emails_sent": results["emails_sent"],
            "errors": results["errors"]
        }
    }


@billing_router.get("/scheduler/history")
async def get_scheduler_run_history(
    limit: int = Query(30, ge=1, le=100),
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    SuperAdmin: Get history of billing scheduler runs.
    """
    runs = await db.billing_scheduler_runs.find(
        {},
        {"_id": 0}
    ).sort("run_time", -1).limit(limit).to_list(limit)
    
    return {
        "runs": runs,
        "count": len(runs)
    }


@billing_router.get("/scheduler/status")
async def get_scheduler_status(
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    SuperAdmin: Check billing scheduler status.
    """
    # Get scheduler instance from billing module
    billing_scheduler = get_scheduler_instance()
    
    is_running = billing_scheduler is not None and billing_scheduler.running
    
    next_run = None
    if is_running:
        job = billing_scheduler.get_job("daily_billing_check")
        if job and job.next_run_time:
            next_run = job.next_run_time.isoformat()
    
    # Get last run
    last_run = await db.billing_scheduler_runs.find_one(
        {},
        {"_id": 0},
        sort=[("run_time", -1)]
    )
    
    return {
        "is_running": is_running,
        "next_run_scheduled": next_run,
        "last_run": last_run
    }


@router.put("/condominiums/{condominium_id}/grace-period")
async def update_grace_period(
    condominium_id: str,
    grace_days: int = Query(..., ge=0, le=30, description="Grace period in days (0-30)"),
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    SuperAdmin: Update grace period for a specific condominium.
    """
    result = await db.condominiums.update_one(
        {"id": condominium_id},
        {"$set": {
            "grace_period_days": grace_days,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "billing",
        {"action": "grace_period_updated", "condo_id": condominium_id},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condominium_id,
        user_email=current_user.get("email"),
    )
    return {
        "success": True,
        "condominium_id": condominium_id,
        "grace_period_days": grace_days
    }

# ==================== END AUTOMATIC BILLING SCHEDULER ====================

@billing_router.post("/preview", response_model=BillingPreviewResponse)
async def get_billing_preview(
    preview_request: BillingPreviewRequest,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """
    BILLING ENGINE: Calculate billing preview before creating/modifying condominium.
    
    Use this endpoint to show users the cost breakdown before they commit.
    Does NOT create any records - purely informational.
    
    Supports custom seat_price_override and yearly_discount_percent for flexible pricing.
    """
    preview = await calculate_billing_preview(
        initial_units=preview_request.initial_units,
        billing_cycle=preview_request.billing_cycle,
        condominium_id=preview_request.condominium_id,
        seat_price_override=preview_request.seat_price_override,
        yearly_discount_override=preview_request.yearly_discount_percent
    )
    
    return BillingPreviewResponse(
        seats=preview["seats"],
        price_per_seat=preview["price_per_seat"],
        billing_cycle=preview["billing_cycle"],
        monthly_amount=preview["monthly_amount"],
        yearly_amount=preview["yearly_amount"],
        yearly_discount_percent=preview["yearly_discount_percent"],
        effective_amount=preview["effective_amount"],
        next_billing_date=preview["next_billing_date"],
        currency=preview["currency"]
    )

@billing_router.get("/events/{condominium_id}")
async def get_billing_events(
    condominium_id: str,
    limit: int = 50,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    BILLING ENGINE: Get billing event history for a condominium.
    SuperAdmin only - audit trail for billing changes.
    """
    events = await db.billing_events.find(
        {"condominium_id": condominium_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "condominium_id": condominium_id,
        "events": events,
        "total": len(events)
    }

@billing_router.patch("/seats/{condominium_id}")
async def update_condominium_seats(
    condominium_id: str,
    request: Request,
    seat_update: SeatUpdateRequest,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    BILLING ENGINE: Update seat count for a condominium.
    Recalculates billing and logs the change.
    Does NOT integrate with payment providers yet.
    """
    # Get current condominium
    condo = await db.condominiums.find_one({"id": condominium_id}, {"_id": 0})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    if condo.get("environment") == "demo" or condo.get("is_demo"):
        raise HTTPException(status_code=403, detail="No se pueden modificar asientos en condominios DEMO")
    
    previous_seats = condo.get("paid_seats", 10)
    new_seats = seat_update.new_seat_count
    
    if new_seats == previous_seats:
        raise HTTPException(status_code=400, detail="La cantidad de asientos es la misma")
    
    # Calculate new billing
    new_preview = await calculate_billing_preview(
        initial_units=new_seats,
        billing_cycle=condo.get("billing_cycle", "monthly"),
        condominium_id=condominium_id
    )
    
    # Determine event type
    event_type = "seats_upgraded" if new_seats > previous_seats else "seats_downgraded"
    
    # Update condominium
    update_data = {
        "paid_seats": new_seats,
        "max_users": new_seats,
        "next_invoice_amount": new_preview["effective_amount"],
        "price_per_seat": new_preview["price_per_seat"],
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.condominiums.update_one(
        {"id": condominium_id},
        {"$set": update_data}
    )
    
    # Log billing event
    await log_billing_engine_event(
        event_type=event_type,
        condominium_id=condominium_id,
        data={
            "previous_seats": previous_seats,
            "new_seats": new_seats,
            "change": new_seats - previous_seats,
            "previous_amount": condo.get("next_invoice_amount", 0),
            "new_amount": new_preview["effective_amount"],
            "reason": seat_update.reason
        },
        triggered_by=current_user["id"],
        previous_state={"paid_seats": previous_seats},
        new_state={"paid_seats": new_seats}
    )
    
    return {
        "condominium_id": condominium_id,
        "previous_seats": previous_seats,
        "new_seats": new_seats,
        "change": new_seats - previous_seats,
        "new_monthly_amount": new_preview["monthly_amount"],
        "new_effective_amount": new_preview["effective_amount"],
        "billing_cycle": condo.get("billing_cycle", "monthly"),
        "message": f"Asientos actualizados de {previous_seats} a {new_seats}"
    }

# ==================== SINPE BILLING CONTROL ====================
# Complete financial control for SINPE/manual payments
# Includes: Payment confirmation, history, upgrade requests, seat protection

@billing_router.post("/confirm-payment/{condominium_id}", response_model=ConfirmPaymentResponse)
async def confirm_sinpe_payment(
    condominium_id: str,
    request: Request,
    payment_data: ConfirmPaymentRequest,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    SINPE BILLING: Confirm a manual/SINPE payment for a condominium.
    
    SUPPORTS PARTIAL PAYMENTS:
    - Calculates total_paid for current billing cycle
    - Only activates condominium when balance_due <= 0
    - Keeps past_due status if partial payment leaves balance
    - Recalculates next_billing_date ONLY when fully paid
    
    Only SuperAdmin can confirm payments.
    """
    # Get condominium
    condo = await db.condominiums.find_one({"id": condominium_id}, {"_id": 0})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    if condo.get("environment") == "demo" or condo.get("is_demo"):
        raise HTTPException(status_code=403, detail="Los condominios DEMO no tienen facturación")
    
    now = datetime.now(timezone.utc)
    billing_cycle = condo.get("billing_cycle", "monthly")
    paid_seats = condo.get("paid_seats", 10)
    previous_status = condo.get("billing_status", "pending_payment")
    invoice_amount = condo.get("next_invoice_amount", 0)
    current_billing_date = condo.get("next_billing_date")
    
    # Parse current billing date to identify the billing cycle
    billing_cycle_start = None
    if current_billing_date:
        try:
            billing_cycle_start = datetime.fromisoformat(current_billing_date.replace("Z", "+00:00"))
            if billing_cycle_start.tzinfo is None:
                billing_cycle_start = billing_cycle_start.replace(tzinfo=timezone.utc)
            # Go back one cycle to get the start of current billing period
            if billing_cycle == "yearly":
                billing_cycle_start = billing_cycle_start - timedelta(days=365)
            else:
                billing_cycle_start = billing_cycle_start - timedelta(days=30)
        except Exception as date_err:
            logger.debug(f"[BILLING] Date parse error, using default: {date_err}")
            billing_cycle_start = now - timedelta(days=30)
    else:
        billing_cycle_start = now - timedelta(days=30)
    
    # Calculate total paid in current billing cycle
    # Get all payments made since the start of current billing cycle
    payments_in_cycle = await db.billing_payments.find({
        "condominium_id": condominium_id,
        "payment_date": {"$gte": billing_cycle_start.isoformat()}
    }, {"_id": 0, "amount_paid": 1}).to_list(1000)
    
    total_paid_before = sum(p.get("amount_paid", 0) for p in payments_in_cycle)
    total_paid_after = total_paid_before + payment_data.amount_paid
    
    # Calculate balance due
    balance_due = max(0, round(invoice_amount - total_paid_after, 2))
    is_fully_paid = balance_due <= 0
    
    # Create payment record
    payment_id = str(uuid.uuid4())
    payment_record = {
        "id": payment_id,
        "condominium_id": condominium_id,
        "condominium_name": condo.get("name", "Unknown"),
        "seats_at_payment": paid_seats,
        "amount_paid": payment_data.amount_paid,
        "invoice_amount": invoice_amount,
        "total_paid_cycle": total_paid_after,
        "balance_due": balance_due,
        "is_partial_payment": not is_fully_paid,
        "billing_cycle": billing_cycle,
        "billing_cycle_start": billing_cycle_start.isoformat(),
        "payment_method": condo.get("billing_provider", "sinpe"),
        "payment_reference": payment_data.payment_reference,
        "notes": payment_data.notes,
        "payment_date": now.isoformat(),
        "confirmed_by": current_user["id"],
        "confirmed_by_name": current_user.get("full_name", current_user.get("email")),
        "created_at": now.isoformat()
    }
    
    await db.billing_payments.insert_one(payment_record)
    
    # Determine new status and whether to update next_billing_date
    next_billing = None
    new_status = previous_status
    
    if is_fully_paid:
        # FULLY PAID: Activate and calculate next billing date
        new_status = "active"
        
        if billing_cycle == "yearly":
            next_billing = now + timedelta(days=365)
        else:
            if now.month == 12:
                next_billing = now.replace(year=now.year + 1, month=1, day=now.day)
            else:
                try:
                    next_billing = now.replace(month=now.month + 1)
                except ValueError:
                    next_billing = (now.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        payment_record["next_billing_date"] = next_billing.isoformat()
        
        # Update condominium with active status and new billing date
        update_data = {
            "billing_status": new_status,
            "next_billing_date": next_billing.isoformat(),
            "last_payment_date": now.isoformat(),
            "last_payment_amount": payment_data.amount_paid,
            "total_paid_current_cycle": total_paid_after,
            "balance_due": 0,
            "updated_at": now.isoformat()
        }
    else:
        # PARTIAL PAYMENT: Keep past_due or pending_payment, don't change next_billing_date
        if previous_status in ["suspended", "cancelled"]:
            new_status = "past_due"  # Reactivate to past_due with partial payment
        elif previous_status == "active":
            new_status = "past_due"  # Shouldn't happen but handle it
        else:
            new_status = previous_status  # Keep as past_due or pending_payment
        
        update_data = {
            "billing_status": new_status,
            "last_payment_date": now.isoformat(),
            "last_payment_amount": payment_data.amount_paid,
            "total_paid_current_cycle": total_paid_after,
            "balance_due": balance_due,
            "updated_at": now.isoformat()
        }
    
    await db.condominiums.update_one(
        {"id": condominium_id},
        {"$set": update_data}
    )
    
    # Log billing event with partial payment details
    event_data = {
        "payment_id": payment_id,
        "amount_paid": payment_data.amount_paid,
        "invoice_amount": invoice_amount,
        "total_paid_cycle": total_paid_after,
        "balance_due": balance_due,
        "is_partial_payment": not is_fully_paid,
        "payment_method": condo.get("billing_provider", "sinpe"),
        "payment_reference": payment_data.payment_reference,
        "seats": paid_seats,
        "billing_cycle": billing_cycle
    }
    
    await log_billing_engine_event(
        event_type="payment_received" if is_fully_paid else "partial_payment_received",
        condominium_id=condominium_id,
        data=event_data,
        triggered_by=current_user["id"],
        previous_state={"billing_status": previous_status, "balance_due": invoice_amount - total_paid_before},
        new_state={"billing_status": new_status, "balance_due": balance_due}
    )
    
    logger.info(
        f"[SINPE-PAYMENT] {'FULL' if is_fully_paid else 'PARTIAL'} payment ${payment_data.amount_paid} "
        f"for condo={condominium_id[:8]}... (total: ${total_paid_after}/{invoice_amount}, "
        f"balance: ${balance_due}) by {current_user['email']}"
    )
    
    # Send appropriate email
    billing_email = condo.get("billing_email") or condo.get("admin_email") or condo.get("contact_email")
    if billing_email:
        if is_fully_paid:
            await send_billing_notification_email(
                "payment_confirmed",
                billing_email,
                condo.get("name", "Unknown"),
                payment_data.amount_paid,
                now.strftime("%d/%m/%Y"),
                paid_seats,
                next_due_date=next_billing.strftime("%d/%m/%Y") if next_billing else ""
            )
        # For partial payments, we could add a specific email template later
    
    # Build response message
    if is_fully_paid:
        message = f"Pago completo de ${payment_data.amount_paid} confirmado. Próximo cobro: {next_billing.strftime('%d/%m/%Y') if next_billing else 'N/A'}"
    else:
        message = f"Pago parcial de ${payment_data.amount_paid} registrado. Saldo pendiente: ${balance_due:.2f}. Total pagado este ciclo: ${total_paid_after:.2f}"
    
    return ConfirmPaymentResponse(
        payment_id=payment_id,
        condominium_id=condominium_id,
        amount_paid=payment_data.amount_paid,
        invoice_amount=invoice_amount,
        total_paid_cycle=total_paid_after,
        balance_due=balance_due,
        previous_status=previous_status,
        new_status=new_status,
        next_billing_date=next_billing.isoformat() if next_billing else None,
        is_fully_paid=is_fully_paid,
        message=message
    )

@billing_router.get("/payments/{condominium_id}")
async def get_payment_history(
    condominium_id: str,
    limit: int = 50,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """
    SINPE BILLING: Get payment history for a condominium.
    """
    # Verify access - SuperAdmin can view any, Admin only their own
    user_roles = current_user.get("roles", [])
    is_super = "SuperAdmin" in user_roles or "super_admin" in user_roles
    if not is_super and current_user.get("condominium_id") != condominium_id:
        raise HTTPException(status_code=403, detail="No autorizado para ver este historial")
    
    payments = await db.billing_payments.find(
        {"condominium_id": condominium_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Get condominium info
    condo = await db.condominiums.find_one({"id": condominium_id}, {"_id": 0, "name": 1, "paid_seats": 1, "billing_status": 1})
    
    return {
        "condominium_id": condominium_id,
        "condominium_name": condo.get("name") if condo else "Unknown",
        "current_status": condo.get("billing_status") if condo else "unknown",
        "payments": payments,
        "total": len(payments)
    }

@billing_router.get("/payments")
async def get_all_pending_payments(
    status: Optional[str] = None,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    SINPE BILLING: Get all condominiums with pending payments (SuperAdmin only).
    """
    query = {"environment": {"$ne": "demo"}, "is_demo": {"$ne": True}}
    if status:
        query["billing_status"] = status
    else:
        query["billing_status"] = {"$in": ["pending_payment", "past_due", "upgrade_pending"]}
    
    condos = await db.condominiums.find(
        query,
        {"_id": 0, "id": 1, "name": 1, "contact_email": 1, "paid_seats": 1, 
         "billing_status": 1, "next_invoice_amount": 1, "next_billing_date": 1,
         "billing_cycle": 1, "billing_provider": 1, "created_at": 1,
         "balance_due": 1, "total_paid_current_cycle": 1}
    ).sort("created_at", -1).to_list(100)
    
    return {
        "pending_count": len(condos),
        "condominiums": condos
    }


@billing_router.get("/balance/{condominium_id}")
async def get_billing_balance(
    condominium_id: str,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """
    Get detailed billing balance for a condominium.
    Shows invoice amount, total paid in current cycle, and balance due.
    
    Returns:
    - invoice_amount: Total due for current billing cycle
    - total_paid_cycle: Total paid in current billing cycle
    - balance_due: Remaining amount to pay
    - billing_status: Current status
    - is_fully_paid: True if balance_due <= 0
    - payments_this_cycle: List of payments in current cycle
    """
    # Verify access
    user_roles = current_user.get("roles", [])
    is_super = "SuperAdmin" in user_roles or "super_admin" in user_roles
    if not is_super and current_user.get("condominium_id") != condominium_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    condo = await db.condominiums.find_one({"id": condominium_id}, {"_id": 0})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    invoice_amount = condo.get("next_invoice_amount", 0)
    total_paid_cycle = condo.get("total_paid_current_cycle", 0)
    balance_due = condo.get("balance_due", invoice_amount)
    billing_status = condo.get("billing_status", "pending_payment")
    next_billing_date = condo.get("next_billing_date")
    
    # Get payments for current billing cycle
    billing_cycle_start = None
    if next_billing_date:
        try:
            billing_date = datetime.fromisoformat(next_billing_date.replace("Z", "+00:00"))
            billing_cycle = condo.get("billing_cycle", "monthly")
            if billing_cycle == "yearly":
                billing_cycle_start = billing_date - timedelta(days=365)
            else:
                billing_cycle_start = billing_date - timedelta(days=30)
        except Exception as date_err:
            logger.debug(f"[BILLING] Billing date parse error: {date_err}")
            billing_cycle_start = datetime.now(timezone.utc) - timedelta(days=30)
    else:
        billing_cycle_start = datetime.now(timezone.utc) - timedelta(days=30)
    
    payments_this_cycle = await db.billing_payments.find({
        "condominium_id": condominium_id,
        "payment_date": {"$gte": billing_cycle_start.isoformat()}
    }, {"_id": 0, "id": 1, "amount_paid": 1, "payment_date": 1, "payment_reference": 1, "is_partial_payment": 1}).sort("payment_date", -1).to_list(100)
    
    return {
        "condominium_id": condominium_id,
        "condominium_name": condo.get("name", "Unknown"),
        "invoice_amount": invoice_amount,
        "total_paid_cycle": total_paid_cycle,
        "balance_due": balance_due,
        "billing_status": billing_status,
        "is_fully_paid": balance_due <= 0,
        "next_billing_date": next_billing_date,
        "billing_cycle": condo.get("billing_cycle", "monthly"),
        "paid_seats": condo.get("paid_seats", 10),
        "price_per_seat": condo.get("price_per_seat", 2.99),
        "payments_this_cycle": payments_this_cycle,
        "payments_count": len(payments_this_cycle)
    }

# ==================== SEAT UPGRADE REQUESTS ====================

@billing_router.post("/request-seat-upgrade")
async def request_seat_upgrade(
    request_data: SeatUpgradeRequestModel,
    current_user = Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN))
):
    """
    SINPE BILLING: Request additional seats for a condominium.
    
    Admin can request, but SuperAdmin must approve.
    After approval, payment must be confirmed to activate new seats.
    """
    condo_id = current_user.get("condominium_id")
    
    # SuperAdmin can specify condominium_id in request - they should use direct methods instead
    user_roles = current_user.get("roles", [])
    if "SuperAdmin" in user_roles:
        raise HTTPException(status_code=400, detail="SuperAdmin debe usar /billing/seats/{condo_id} para cambios directos")
    
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario sin condominio asignado")
    
    # Get condominium
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    if condo.get("environment") == "demo" or condo.get("is_demo"):
        raise HTTPException(status_code=403, detail="Los condominios DEMO no pueden solicitar más asientos")
    
    current_seats = condo.get("paid_seats", 10)
    requested_seats = request_data.requested_seats
    
    if requested_seats <= current_seats:
        raise HTTPException(status_code=400, detail=f"Debe solicitar más de {current_seats} asientos actuales")
    
    # Check for pending requests
    existing = await db.seat_upgrade_requests.find_one({
        "condominium_id": condo_id,
        "status": "pending"
    })
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe una solicitud pendiente de aprobación")
    
    # Calculate pricing
    current_preview = await calculate_billing_preview(current_seats, condo.get("billing_cycle", "monthly"), condo_id)
    new_preview = await calculate_billing_preview(requested_seats, condo.get("billing_cycle", "monthly"), condo_id)
    
    now = datetime.now(timezone.utc)
    request_id = str(uuid.uuid4())
    
    upgrade_request = {
        "id": request_id,
        "condominium_id": condo_id,
        "condominium_name": condo.get("name", "Unknown"),
        "current_seats": current_seats,
        "requested_seats": requested_seats,
        "additional_seats": requested_seats - current_seats,
        "current_amount": current_preview["effective_amount"],
        "new_amount": new_preview["effective_amount"],
        "difference_amount": round(new_preview["effective_amount"] - current_preview["effective_amount"], 2),
        "billing_cycle": condo.get("billing_cycle", "monthly"),
        "status": "pending",
        "reason": request_data.reason,
        "requested_by": current_user["id"],
        "requested_by_name": current_user.get("full_name", current_user.get("email")),
        "approved_by": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.seat_upgrade_requests.insert_one(upgrade_request)
    
    # Log event
    await log_billing_engine_event(
        event_type="upgrade_requested",
        condominium_id=condo_id,
        data={
            "request_id": request_id,
            "current_seats": current_seats,
            "requested_seats": requested_seats,
            "difference_amount": upgrade_request["difference_amount"]
        },
        triggered_by=current_user["id"],
        previous_state={"paid_seats": current_seats},
        new_state={"requested_seats": requested_seats, "status": "pending"}
    )
    
    logger.info(f"[SEAT-UPGRADE] Request created: {current_seats}→{requested_seats} for condo={condo_id[:8]}...")
    
    return {
        "request_id": request_id,
        "condominium_id": condo_id,
        "current_seats": current_seats,
        "requested_seats": requested_seats,
        "additional_seats": requested_seats - current_seats,
        "current_amount": current_preview["effective_amount"],
        "new_amount": new_preview["effective_amount"],
        "difference_amount": upgrade_request["difference_amount"],
        "status": "pending",
        "message": f"Solicitud creada. Esperando aprobación de SuperAdmin para {requested_seats - current_seats} asientos adicionales (${upgrade_request['difference_amount']}/{'año' if condo.get('billing_cycle') == 'yearly' else 'mes'})"
    }

@billing_router.get("/my-pending-request")
async def get_my_pending_request(
    current_user = Depends(require_role(RoleEnum.ADMINISTRADOR))
):
    """
    Get the current admin's pending seat upgrade request, if any.
    Returns null/404 if no pending request exists.
    """
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario sin condominio asignado")
    
    pending_request = await db.seat_upgrade_requests.find_one(
        {"condominium_id": condo_id, "status": "pending"},
        {"_id": 0}
    )
    
    if not pending_request:
        raise HTTPException(status_code=404, detail="No hay solicitud pendiente")
    
    return pending_request

@billing_router.get("/upgrade-requests")
async def get_upgrade_requests(
    status: Optional[str] = "pending",
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    SINPE BILLING: Get all seat upgrade requests (SuperAdmin only).
    """
    query = {}
    if status:
        query["status"] = status
    
    requests = await db.seat_upgrade_requests.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {
        "total": len(requests),
        "requests": requests
    }

@billing_router.patch("/approve-seat-upgrade/{request_id}")
async def approve_seat_upgrade(
    request_id: str,
    approve: bool = True,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    SINPE BILLING: Approve or reject a seat upgrade request.
    
    If approved:
    - Updates paid_seats
    - Recalculates next_invoice_amount
    - Sets billing_status to "upgrade_pending" (awaiting payment)
    
    Payment must be confirmed separately to activate.
    """
    # Get request
    upgrade_req = await db.seat_upgrade_requests.find_one({"id": request_id}, {"_id": 0})
    if not upgrade_req:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    if upgrade_req["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Solicitud ya fue {upgrade_req['status']}")
    
    condo_id = upgrade_req["condominium_id"]
    now = datetime.now(timezone.utc)
    
    if approve:
        # Get condominium
        condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0})
        if not condo:
            raise HTTPException(status_code=404, detail="Condominio no encontrado")
        
        new_seats = upgrade_req["requested_seats"]
        new_preview = await calculate_billing_preview(new_seats, condo.get("billing_cycle", "monthly"), condo_id)
        
        # Update condominium
        await db.condominiums.update_one(
            {"id": condo_id},
            {"$set": {
                "paid_seats": new_seats,
                "max_users": new_seats,
                "next_invoice_amount": new_preview["effective_amount"],
                "billing_status": "upgrade_pending",  # Awaiting payment for upgrade
                "updated_at": now.isoformat()
            }}
        )
        
        # Update request
        await db.seat_upgrade_requests.update_one(
            {"id": request_id},
            {"$set": {
                "status": "approved",
                "approved_by": current_user["id"],
                "approved_by_name": current_user.get("full_name", current_user.get("email")),
                "updated_at": now.isoformat()
            }}
        )
        
        # Log event
        await log_billing_engine_event(
            event_type="upgrade_approved",
            condominium_id=condo_id,
            data={
                "request_id": request_id,
                "previous_seats": upgrade_req["current_seats"],
                "new_seats": new_seats,
                "new_amount": new_preview["effective_amount"]
            },
            triggered_by=current_user["id"],
            previous_state={"paid_seats": upgrade_req["current_seats"]},
            new_state={"paid_seats": new_seats, "billing_status": "upgrade_pending"}
        )
        
        logger.info(f"[SEAT-UPGRADE] Approved: {upgrade_req['current_seats']}→{new_seats} for condo={condo_id[:8]}...")
        print(f"[FLOW] seat_upgrade_processed | request_id={request_id} status=approved condo_id={condo_id[:8]}")
        
        # === SEND EMAIL NOTIFICATION TO ADMIN ===
        try:
            # Get admin who requested the upgrade
            requester_id = upgrade_req.get("requested_by")
            requester = await db.users.find_one({"id": requester_id}, {"_id": 0, "email": 1, "full_name": 1})
            
            if requester and requester.get("email"):
                admin_email = requester["email"]
                admin_name = requester.get("full_name", "Administrador")
                
                print(f"[EMAIL TRIGGER] seat_upgrade_approved | email={admin_email} condo={condo.get('name')}")
                logger.info(f"[EMAIL TRIGGER] seat_upgrade_approved | admin={admin_email}")
                
                upgrade_email_html = f"""
                <!DOCTYPE html>
                <html>
                <head><meta charset="UTF-8"></head>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(135deg, #10B981 0%, #059669 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
                        <h1 style="color: #ffffff; margin: 0;">Solicitud Aprobada</h1>
                        <p style="color: rgba(255,255,255,0.9); margin-top: 5px;">Upgrade de Asientos - GENTURIX</p>
                    </div>
                    
                    <div style="background: #ffffff; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #eee;">
                        <p>Hola {admin_name},</p>
                        <p>Tu solicitud de upgrade de asientos ha sido <strong style="color: #10B981;">aprobada</strong>.</p>
                        
                        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 8px 0; color: #666;">Condominio:</td>
                                    <td style="padding: 8px 0; font-weight: bold; text-align: right;">{condo.get('name', 'N/A')}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #666;">Asientos anteriores:</td>
                                    <td style="padding: 8px 0; text-align: right;">{upgrade_req['current_seats']}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #666;">Nuevos asientos:</td>
                                    <td style="padding: 8px 0; font-weight: bold; color: #10B981; text-align: right;">{new_seats}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #666;">Fecha efectiva:</td>
                                    <td style="padding: 8px 0; text-align: right;">{now.strftime('%d/%m/%Y')}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #666;">Nuevo monto:</td>
                                    <td style="padding: 8px 0; font-weight: bold; text-align: right;">${new_preview['effective_amount']:.2f}/{condo.get('billing_cycle', 'mes')}</td>
                                </tr>
                            </table>
                        </div>
                        
                        <p style="color: #666; font-size: 14px;">
                            Los nuevos asientos ya están disponibles. Ahora puedes crear hasta {new_seats} usuarios en tu condominio.
                        </p>
                    </div>
                    
                    <div style="text-align: center; padding: 20px; color: #888; font-size: 12px;">
                        <p>Este es un correo automático de Genturix Security.</p>
                    </div>
                </body>
                </html>
                """
                
                email_result = await send_email(
                    to=admin_email,
                    subject=f"✅ Solicitud de Asientos Aprobada - {condo.get('name', 'Genturix')}",
                    html=upgrade_email_html
                )
                
                if email_result.get("success"):
                    print(f"[EMAIL SENT] seat_upgrade_approved | email={admin_email}")
                    logger.info(f"[EMAIL SENT] seat_upgrade_approved to {admin_email}")
                else:
                    print(f"[EMAIL ERROR] seat_upgrade_approved failed | email={admin_email}")
                    logger.warning(f"[EMAIL ERROR] seat_upgrade_approved failed for {admin_email}: {email_result.get('error')}")
        except Exception as email_error:
            print(f"[EMAIL ERROR] seat_upgrade_approved exception | error={str(email_error)}")
            logger.error(f"[EMAIL ERROR] seat_upgrade_approved exception: {email_error}", exc_info=True)
            # Don't fail the request if email fails
        
        return {
            "request_id": request_id,
            "status": "approved",
            "condominium_id": condo_id,
            "new_seats": new_seats,
            "new_amount": new_preview["effective_amount"],
            "billing_status": "upgrade_pending",
            "message": f"Solicitud aprobada. Asientos actualizados a {new_seats}. Esperando confirmación de pago."
        }
    else:
        # Reject
        await db.seat_upgrade_requests.update_one(
            {"id": request_id},
            {"$set": {
                "status": "rejected",
                "approved_by": current_user["id"],
                "approved_by_name": current_user.get("full_name", current_user.get("email")),
                "updated_at": now.isoformat()
            }}
        )
        
        print(f"[FLOW] seat_upgrade_processed | request_id={request_id} status=rejected condo_id={condo_id[:8]}")
        
        await log_billing_engine_event(
            event_type="upgrade_rejected",
            condominium_id=condo_id,
            data={"request_id": request_id, "requested_seats": upgrade_req["requested_seats"]},
            triggered_by=current_user["id"]
        )
        
        return {
            "request_id": request_id,
            "status": "rejected",
            "message": "Solicitud rechazada"
        }

# ==================== SEAT PROTECTION MIDDLEWARE ====================

async def check_seat_limit(condominium_id: str) -> dict:
    """
    SEAT PROTECTION: Check if condominium can create more users.
    
    Returns:
        {
            "can_create": bool,
            "current_users": int,
            "paid_seats": int,
            "remaining": int,
            "reason": str or None
        }
    """
    condo = await db.condominiums.find_one(
        {"id": condominium_id},
        {"_id": 0, "paid_seats": 1, "billing_status": 1, "environment": 1, "is_demo": 1, "name": 1}
    )
    
    if not condo:
        return {"can_create": False, "reason": "Condominio no encontrado"}
    
    # Demo condos have fixed limit of 10
    is_demo = condo.get("environment") == "demo" or condo.get("is_demo")
    paid_seats = 10 if is_demo else condo.get("paid_seats", 10)
    
    # Count active users (excluding super_admin)
    current_users = await db.users.count_documents({
        "condominium_id": condominium_id,
        "role": {"$ne": "super_admin"},
        "is_active": {"$ne": False}
    })
    
    remaining = paid_seats - current_users
    
    # Check billing status for production condos
    billing_status = condo.get("billing_status", "active")
    blocked_statuses = ["suspended", "cancelled"]
    
    if not is_demo and billing_status in blocked_statuses:
        return {
            "can_create": False,
            "current_users": current_users,
            "paid_seats": paid_seats,
            "remaining": remaining,
            "billing_status": billing_status,
            "reason": f"Condominio suspendido por falta de pago. Contacte soporte."
        }
    
    if current_users >= paid_seats:
        return {
            "can_create": False,
            "current_users": current_users,
            "paid_seats": paid_seats,
            "remaining": 0,
            "billing_status": billing_status,
            "reason": f"Límite de {paid_seats} asientos alcanzado. Solicite más asientos para continuar."
        }
    
    return {
        "can_create": True,
        "current_users": current_users,
        "paid_seats": paid_seats,
        "remaining": remaining,
        "billing_status": billing_status,
        "reason": None
    }

async def check_module_access(condominium_id: str, module_id: str = None) -> dict:
    """
    MODULE PROTECTION: Check if condominium can access modules.
    
    Blocks access if billing_status is past_due or suspended.
    """
    condo = await db.condominiums.find_one(
        {"id": condominium_id},
        {"_id": 0, "billing_status": 1, "environment": 1, "is_demo": 1, "modules": 1}
    )
    
    if not condo:
        return {"can_access": False, "reason": "Condominio no encontrado"}
    
    is_demo = condo.get("environment") == "demo" or condo.get("is_demo")
    
    # Demo condos always have access
    if is_demo:
        return {"can_access": True, "reason": None}
    
    billing_status = condo.get("billing_status", "active")
    blocked_statuses = ["past_due", "suspended", "cancelled"]
    
    if billing_status in blocked_statuses:
        return {
            "can_access": False,
            "billing_status": billing_status,
            "reason": f"Acceso bloqueado: {billing_status}. Por favor regularice su pago."
        }
    
    return {
        "can_access": True,
        "billing_status": billing_status,
        "reason": None
    }

@billing_router.get("/seat-status/{condominium_id}")
async def get_seat_status(
    condominium_id: str,
    current_user = Depends(get_current_user)
):
    """
    SEAT PROTECTION: Get current seat usage status for a condominium.
    """
    # Verify access - SuperAdmin can view any, others only their own
    user_roles = current_user.get("roles", [])
    is_super = "SuperAdmin" in user_roles or "super_admin" in user_roles
    if not is_super and current_user.get("condominium_id") != condominium_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    status = await check_seat_limit(condominium_id)
    
    # Add percentage
    if status.get("paid_seats", 0) > 0:
        status["usage_percent"] = round((status.get("current_users", 0) / status["paid_seats"]) * 100, 1)
    else:
        status["usage_percent"] = 0
    
    return status

# ==================== END SINPE BILLING CONTROL ====================

@router.get("/payments/pricing")
async def get_pricing_info(current_user = Depends(get_current_user)):
    """
    Get GENTURIX pricing model for current user's condominium.
    PHASE 4: Uses dynamic pricing system.
    """
    condo_id = current_user.get("condominium_id")
    pricing_info = await get_condominium_pricing_info(condo_id)
    
    return {
        "model": "per_user",
        "price_per_user": pricing_info["effective_price"],
        "currency": pricing_info["currency"].lower(),
        "billing_period": "monthly",
        "uses_override": pricing_info["uses_override"],
        "description": f"${pricing_info['effective_price']} por usuario al mes",
        "features": [
            "Acceso completo a GENTURIX",
            "Botón de pánico (3 tipos de emergencia)",
            "Registro de accesos",
            "Genturix School básico",
            "Auditoría completa",
            "Soporte por email"
        ],
        "premium_modules": [
            {"name": "Genturix School Pro", "price": 2.00, "description": "Cursos ilimitados y certificaciones"},
            {"name": "Monitoreo CCTV", "price": 3.00, "description": "Integración con cámaras IP"},
            {"name": "API Access", "price": 5.00, "description": "Acceso a API para integraciones"}
        ]
    }

@router.post("/payments/calculate")
async def calculate_price(subscription: UserSubscriptionCreate, current_user = Depends(get_current_user)):
    """
    Calculate subscription price based on user count.
    PHASE 4: Uses dynamic pricing system.
    """
    if subscription.user_count < 1:
        raise HTTPException(status_code=400, detail="Minimum 1 user required")
    
    condo_id = current_user.get("condominium_id")
    pricing = await calculate_subscription_price_dynamic(subscription.user_count, condo_id)
    
    return {
        "user_count": subscription.user_count,
        "price_per_user": pricing["price_per_seat"],
        "total": pricing["total"],
        "currency": pricing["currency"].lower(),
        "billing_period": "monthly"
    }

@router.post("/payments/checkout")
async def create_checkout(request: Request, current_user = Depends(get_current_user), user_count: int = 1, origin_url: str = ""):
    """
    Create checkout session for subscription.
    PHASE 4: Uses dynamic pricing system.
    """
    if user_count < 1:
        raise HTTPException(status_code=400, detail="Minimum 1 user required")
    
    condo_id = current_user.get("condominium_id")
    pricing = await calculate_subscription_price_dynamic(user_count, condo_id)
    total_amount = pricing["total"]
    
    stripe_api_key = os.environ.get('STRIPE_API_KEY')
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    host_url = origin_url.rstrip('/') if origin_url else str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe"
    success_url = f"{host_url}/payments?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{host_url}/payments"
    
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    checkout_request = CheckoutSessionRequest(
        amount=total_amount,
        currency=pricing["currency"].lower(),
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": current_user["id"],
            "user_email": current_user["email"],
            "user_count": str(user_count),
            "price_per_user": str(pricing["price_per_seat"])  # Use dynamic price from calculation
        }
    )
    
    session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Create payment transaction record
    transaction = {
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": current_user["id"],
        "user_email": current_user["email"],
        "user_count": user_count,
        "price_per_user": pricing["price_per_seat"],  # Use dynamic price
        "amount": total_amount,
        "currency": "usd",
        "payment_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.payment_transactions.insert_one(transaction)
    
    await log_audit_event(
        AuditEventType.PAYMENT_INITIATED,
        current_user["id"],
        "payments",
        {"user_count": user_count, "amount": total_amount, "session_id": session.session_id},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"url": session.url, "session_id": session.session_id, "amount": total_amount, "user_count": user_count}

@router.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str, request: Request, current_user = Depends(get_current_user)):
    stripe_api_key = os.environ.get('STRIPE_API_KEY')
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe"
    
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    status_response: CheckoutStatusResponse = await stripe_checkout.get_checkout_status(session_id)
    
    # Update transaction in database
    if status_response.payment_status == "paid":
        transaction = await db.payment_transactions.find_one({"session_id": session_id})
        if transaction and transaction.get("payment_status") != "completed":
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"payment_status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}}
            )
            
            await log_audit_event(
                AuditEventType.PAYMENT_COMPLETED,
                current_user["id"],
                "payments",
                {"session_id": session_id, "amount": transaction.get("amount")},
                request.client.host if request.client else "unknown",
                request.headers.get("user-agent", "unknown")
            )
    
    return {
        "status": status_response.status,
        "payment_status": status_response.payment_status,
        "amount_total": status_response.amount_total,
        "currency": status_response.currency
    }

@router.get("/payments/history")
async def get_payment_history(current_user = Depends(get_current_user)):
    transactions = await db.payment_transactions.find(
        {"user_id": current_user["id"]}, 
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return transactions

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events with signature verification"""
    stripe_api_key = os.environ.get('STRIPE_API_KEY')
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    # ==================== SECURITY: FAIL-CLOSED MODE ====================
    # In production: ALWAYS require STRIPE_WEBHOOK_SECRET
    # In development: Allow without secret (with warning)
    
    if ENVIRONMENT == "production":
        if not STRIPE_WEBHOOK_SECRET:
            logger.error("[SECURITY] Stripe webhook secret missing in PRODUCTION - rejecting request")
            raise HTTPException(
                status_code=500, 
                detail="Webhook security not configured. Contact administrator."
            )
        # Production with secret: verify signature
        try:
            stripe.Webhook.construct_event(
                payload=body,
                sig_header=signature,
                secret=STRIPE_WEBHOOK_SECRET
            )
            logger.info("[SECURITY] Stripe webhook verified successfully")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"[SECURITY] Stripe signature invalid: {e}")
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
        except Exception as e:
            logger.error(f"[SECURITY] Stripe signature verification error: {e}")
            raise HTTPException(status_code=400, detail="Webhook signature verification failed")
    else:
        # Development/staging: verify if secret exists, warn if not
        if STRIPE_WEBHOOK_SECRET:
            try:
                stripe.Webhook.construct_event(
                    payload=body,
                    sig_header=signature,
                    secret=STRIPE_WEBHOOK_SECRET
                )
                logger.debug("[STRIPE-WEBHOOK] Signature verified successfully (dev mode)")
            except stripe.error.SignatureVerificationError as e:
                logger.error(f"[STRIPE-WEBHOOK] Invalid signature: {e}")
                raise HTTPException(status_code=400, detail="Invalid webhook signature")
            except Exception as e:
                logger.error(f"[STRIPE-WEBHOOK] Signature verification error: {e}")
                raise HTTPException(status_code=400, detail="Webhook signature verification failed")
        else:
            logger.warning("[STRIPE-WEBHOOK] Processing without signature verification (dev mode) - STRIPE_WEBHOOK_SECRET not set")
    # ==========================================================================
    
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe"
    
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        if webhook_response.payment_status == "paid":
            await db.payment_transactions.update_one(
                {"session_id": webhook_response.session_id},
                {"$set": {"payment_status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}}
            )
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

# ==================== SAAS BILLING ENDPOINTS ====================

@billing_router.get("/info")
async def get_condominium_billing_info(current_user = Depends(get_current_user)):
    """Get billing information for the current user's condominium"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asociado a un condominio")
    
    billing_info = await get_billing_info(condo_id)
    if not billing_info:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    return billing_info

@billing_router.get("/can-create-user")
async def check_can_create_user(
    role: str = "Residente",
    current_user = Depends(require_role("Administrador", "SuperAdmin"))
):
    """Check if the condominium can create a new user of the specified role"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asociado a un condominio")
    
    can_create, error_msg = await can_create_user(condo_id, role)
    billing_info = await get_billing_info(condo_id)
    active_residents = await count_active_residents(condo_id)
    
    return {
        "can_create": can_create,
        "error_message": error_msg if not can_create else None,
        "paid_seats": billing_info.get("paid_seats", 0),
        "active_users": billing_info.get("active_users", 0),
        "active_residents": active_residents,
        "remaining_seats": max(0, billing_info.get("paid_seats", 0) - active_residents),
        "billing_status": billing_info.get("billing_status", "unknown"),
        "role_checked": role
    }

@billing_router.post("/upgrade-seats")
async def upgrade_seats(
    request: Request,
    upgrade: SeatUpgradeRequest,
    origin_url: str = "",
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))  # CHANGED: Only SuperAdmin can directly upgrade
):
    """
    BILLING ENGINE: Create a Stripe checkout session to upgrade seats.
    
    SECURITY: Only SuperAdmin can directly upgrade seats.
    Regular Admins must use POST /billing/request-seat-upgrade to create a request.
    """
    # For SuperAdmin, they need to specify condominium_id in the request
    condo_id = upgrade.condominium_id if hasattr(upgrade, 'condominium_id') and upgrade.condominium_id else current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="condominium_id requerido para SuperAdmin")
    
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    # ==================== DEMO ENVIRONMENT CHECK ====================
    # Demo condominiums cannot purchase additional seats
    condo_environment = condo.get("environment", "production")
    if condo_environment == "demo" or condo.get("is_demo"):
        raise HTTPException(
            status_code=403, 
            detail="Los condominios en modo Demo no pueden comprar asientos adicionales. Contacte al administrador para cambiar a modo Producción."
        )
    # ================================================================
    
    stripe_api_key = os.environ.get('STRIPE_API_KEY')
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe no configurado")
    
    # Calculate new total and amount to charge using dynamic pricing
    current_seats = condo.get("paid_seats", 10)
    new_total_seats = current_seats + upgrade.additional_seats
    
    # PHASE 4: Use dynamic pricing
    pricing = await calculate_subscription_price_dynamic(upgrade.additional_seats, condo_id)
    upgrade_cost = pricing["total"]
    currency = pricing["currency"].lower()
    
    host_url = origin_url.rstrip('/') if origin_url else str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe-subscription"
    success_url = f"{host_url}/admin/dashboard?upgrade=success&seats={new_total_seats}"
    cancel_url = f"{host_url}/admin/dashboard?upgrade=cancelled"
    
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    checkout_request = CheckoutSessionRequest(
        amount=upgrade_cost,
        currency=currency,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "type": "seat_upgrade",
            "condominium_id": condo_id,
            "condominium_name": condo.get("name", ""),
            "user_id": current_user["id"],
            "user_email": current_user["email"],
            "current_seats": str(current_seats),
            "additional_seats": str(upgrade.additional_seats),
            "new_total_seats": str(new_total_seats),
            "price_per_seat": str(pricing["price_per_seat"])
        }
    )
    
    session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Create upgrade transaction record
    transaction = {
        "id": str(uuid.uuid4()),
        "type": "seat_upgrade",
        "session_id": session.session_id,
        "condominium_id": condo_id,
        "user_id": current_user["id"],
        "user_email": current_user["email"],
        "current_seats": current_seats,
        "additional_seats": upgrade.additional_seats,
        "new_total_seats": new_total_seats,
        "amount": upgrade_cost,
        "currency": currency,
        "payment_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.billing_transactions.insert_one(transaction)
    
    await log_billing_event(
        "upgrade_initiated",
        condo_id,
        {
            "current_seats": current_seats,
            "additional_seats": upgrade.additional_seats,
            "new_total_seats": new_total_seats,
            "amount": upgrade_cost,
            "session_id": session.session_id
        },
        current_user["id"]
    )
    
    return {
        "url": session.url,
        "session_id": session.session_id,
        "current_seats": current_seats,
        "additional_seats": upgrade.additional_seats,
        "new_total_seats": new_total_seats,
        "amount": upgrade_cost
    }

@router.post("/webhook/stripe-subscription")
async def stripe_subscription_webhook(request: Request):
    """Handle Stripe webhook events for subscription updates with signature verification"""
    stripe_api_key = os.environ.get('STRIPE_API_KEY')
    if not stripe_api_key:
        return {"status": "error", "message": "Stripe not configured"}
    
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    # ==================== SECURITY: FAIL-CLOSED MODE ====================
    # In production: ALWAYS require STRIPE_WEBHOOK_SECRET
    # In development: Allow without secret (with warning)
    
    if ENVIRONMENT == "production":
        if not STRIPE_WEBHOOK_SECRET:
            logger.error("[SECURITY] Stripe subscription webhook secret missing in PRODUCTION - rejecting request")
            raise HTTPException(
                status_code=500, 
                detail="Webhook security not configured. Contact administrator."
            )
        # Production with secret: verify signature
        try:
            stripe.Webhook.construct_event(
                payload=body,
                sig_header=signature,
                secret=STRIPE_WEBHOOK_SECRET
            )
            logger.info("[SECURITY] Stripe subscription webhook verified successfully")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"[SECURITY] Stripe subscription signature invalid: {e}")
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
        except Exception as e:
            logger.error(f"[SECURITY] Stripe subscription signature verification error: {e}")
            raise HTTPException(status_code=400, detail="Webhook signature verification failed")
    else:
        # Development/staging: verify if secret exists, warn if not
        if STRIPE_WEBHOOK_SECRET:
            try:
                stripe.Webhook.construct_event(
                    payload=body,
                    sig_header=signature,
                    secret=STRIPE_WEBHOOK_SECRET
                )
                logger.debug("[STRIPE-SUBSCRIPTION-WEBHOOK] Signature verified successfully (dev mode)")
            except stripe.error.SignatureVerificationError as e:
                logger.error(f"[STRIPE-SUBSCRIPTION-WEBHOOK] Invalid signature: {e}")
                raise HTTPException(status_code=400, detail="Invalid webhook signature")
            except Exception as e:
                logger.error(f"[STRIPE-SUBSCRIPTION-WEBHOOK] Signature verification error: {e}")
                raise HTTPException(status_code=400, detail="Webhook signature verification failed")
        else:
            logger.warning("[STRIPE-SUBSCRIPTION-WEBHOOK] Processing without signature verification (dev mode) - STRIPE_WEBHOOK_SECRET not set")
    # ==========================================================================
    
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe-subscription"
    
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        if webhook_response.payment_status == "paid":
            # Find the billing transaction
            transaction = await db.billing_transactions.find_one({"session_id": webhook_response.session_id})
            
            if transaction and transaction.get("payment_status") != "completed":
                condo_id = transaction.get("condominium_id")
                new_total_seats = transaction.get("new_total_seats")
                
                # ==================== DEMO ENVIRONMENT CHECK ====================
                # Verify the condominium is not in demo mode before processing payment
                condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "environment": 1, "is_demo": 1})
                if condo:
                    condo_environment = condo.get("environment", "production")
                    if condo_environment == "demo" or condo.get("is_demo"):
                        logger.warning(f"[STRIPE-WEBHOOK] Ignoring payment for demo condominium: {condo_id}")
                        # Mark transaction as ignored (demo)
                        await db.billing_transactions.update_one(
                            {"session_id": webhook_response.session_id},
                            {"$set": {"payment_status": "ignored_demo", "note": "Demo condominium - payment ignored"}}
                        )
                        return {"status": "success", "note": "Demo condominium - no changes applied"}
                # ================================================================
                
                # Update condominium paid_seats
                await db.condominiums.update_one(
                    {"id": condo_id},
                    {
                        "$set": {
                            "paid_seats": new_total_seats,
                            "billing_status": "active",
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
                
                # Update transaction status
                await db.billing_transactions.update_one(
                    {"session_id": webhook_response.session_id},
                    {"$set": {"payment_status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}}
                )
                
                # Log the upgrade completion
                await log_billing_event(
                    "upgrade_completed",
                    condo_id,
                    {
                        "new_total_seats": new_total_seats,
                        "session_id": webhook_response.session_id
                    }
                )
                
                logger.info(f"Seat upgrade completed for condo {condo_id}: {new_total_seats} seats")
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Subscription webhook error: {e}")
        return {"status": "error", "message": str(e)}

@billing_router.get("/history")
async def get_billing_history(current_user = Depends(require_role("Administrador"))):
    """Get billing transaction history for the condominium"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asociado a un condominio")
    
    transactions = await db.billing_transactions.find(
        {"condominium_id": condo_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return transactions

@billing_super_admin_router.get("/overview")
async def get_all_condominiums_billing(
    current_user = Depends(require_role("SuperAdmin")),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    billing_status: Optional[str] = Query(None, description="Filter by billing_status (comma-separated for multiple)"),
    billing_provider: Optional[str] = Query(None, description="Filter by billing_provider (sinpe, stripe, manual)"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    sort_by: str = Query("next_invoice_amount", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order")
):
    """
    SuperAdmin: Get billing overview for all condominiums.
    
    OPTIMIZED v2.0:
    - Real backend pagination with skip/limit
    - Direct MongoDB filtering by billing_status and billing_provider
    - Eliminates N+1 by using aggregation pipeline
    - Uses persisted current_users field (falls back to count if not set)
    
    Query params:
    - page: Page number (1-indexed)
    - page_size: Items per page (max 100)
    - billing_status: Filter by status (comma-separated, e.g., "pending_payment,past_due")
    - billing_provider: Filter by provider (sinpe, stripe, manual)
    - search: Search by condominium name or admin email
    - sort_by: Sort field (next_invoice_amount, paid_seats, condominium_name, etc.)
    - sort_order: asc or desc
    """
    
    # Build MongoDB filter
    mongo_filter = {
        "is_demo": {"$ne": True},
        "environment": {"$ne": "demo"}
    }
    
    # Filter by billing_status if provided
    if billing_status:
        status_list = [s.strip() for s in billing_status.split(",") if s.strip()]
        if status_list:
            mongo_filter["billing_status"] = {"$in": status_list}
    
    # Filter by billing_provider if provided
    if billing_provider:
        mongo_filter["billing_provider"] = billing_provider
    
    # Search filter
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        mongo_filter["$or"] = [
            {"name": search_regex},
            {"admin_email": search_regex},
            {"contact_email": search_regex}
        ]
    
    # Get global pricing config
    global_config = await get_global_pricing()
    default_price = global_config.get("price_per_seat", 2.99)
    
    # Build aggregation pipeline (ELIMINATES N+1)
    pipeline = [
        # Stage 1: Match filter
        {"$match": mongo_filter},
        
        # Stage 2: Lookup users count per condominium (single query, not N+1)
        {"$lookup": {
            "from": "users",
            "let": {"condo_id": "$id"},
            "pipeline": [
                {"$match": {
                    "$expr": {
                        "$and": [
                            {"$eq": ["$condominium_id", "$$condo_id"]},
                            {"$eq": ["$is_active", True]}
                        ]
                    }
                }},
                {"$count": "count"}
            ],
            "as": "user_count_result"
        }},
        
        # Stage 3: Add computed fields
        {"$addFields": {
            "active_users_computed": {
                "$ifNull": [
                    {"$arrayElemAt": ["$user_count_result.count", 0]},
                    {"$ifNull": ["$current_users", 0]}
                ]
            },
            "effective_price": {
                "$ifNull": [
                    "$seat_price_override",
                    {"$ifNull": ["$price_per_seat", default_price]}
                ]
            }
        }},
        
        # Stage 4: Project final fields
        {"$project": {
            "_id": 0,
            "condominium_id": "$id",
            "condominium_name": "$name",
            "admin_email": {"$ifNull": ["$admin_email", "$contact_email"]},
            "paid_seats": {"$ifNull": ["$paid_seats", 10]},
            "current_users": "$active_users_computed",
            "remaining_seats": {
                "$max": [0, {"$subtract": [{"$ifNull": ["$paid_seats", 10]}, "$active_users_computed"]}]
            },
            "billing_status": {"$ifNull": ["$billing_status", "active"]},
            "billing_cycle": {"$ifNull": ["$billing_cycle", "monthly"]},
            "billing_provider": {"$ifNull": ["$billing_provider", "manual"]},
            "next_invoice_amount": {"$ifNull": ["$next_invoice_amount", 0]},
            "next_billing_date": "$next_billing_date",
            "price_per_seat": "$effective_price",
            "seat_price_override": "$seat_price_override",
            "yearly_discount_percent": {"$ifNull": ["$yearly_discount_percent", 10]},
            "uses_override": {
                "$and": [
                    {"$ne": ["$seat_price_override", None]},
                    {"$gt": ["$seat_price_override", 0]}
                ]
            },
            "stripe_customer_id": "$stripe_customer_id",
            "stripe_subscription_id": "$stripe_subscription_id",
            "environment": "$environment",
            "is_demo": "$is_demo",
            "created_at": "$created_at"
        }}
    ]
    
    # Build sort stage
    sort_field_map = {
        "next_invoice_amount": "next_invoice_amount",
        "paid_seats": "paid_seats",
        "condominium_name": "condominium_name",
        "billing_status": "billing_status",
        "next_billing_date": "next_billing_date",
        "current_users": "current_users"
    }
    sort_field = sort_field_map.get(sort_by, "next_invoice_amount")
    sort_direction = 1 if sort_order == "asc" else -1
    pipeline.append({"$sort": {sort_field: sort_direction}})
    
    # Get total count before pagination (using same filter)
    total_count = await db.condominiums.count_documents(mongo_filter)
    
    # Add pagination
    skip = (page - 1) * page_size
    pipeline.append({"$skip": skip})
    pipeline.append({"$limit": page_size})
    
    # Execute aggregation
    condos = await db.condominiums.aggregate(pipeline).to_list(page_size)
    
    # Calculate totals for filtered results (separate aggregation for accuracy)
    totals_pipeline = [
        {"$match": mongo_filter},
        {"$lookup": {
            "from": "users",
            "let": {"condo_id": "$id"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$condominium_id", "$$condo_id"]},
                    {"$eq": ["$is_active", True]}
                ]}}},
                {"$count": "count"}
            ],
            "as": "user_count_result"
        }},
        {"$group": {
            "_id": None,
            "total_paid_seats": {"$sum": {"$ifNull": ["$paid_seats", 10]}},
            "total_active_users": {
                "$sum": {"$ifNull": [{"$arrayElemAt": ["$user_count_result.count", 0]}, {"$ifNull": ["$current_users", 0]}]}
            },
            "total_monthly_revenue": {"$sum": {"$ifNull": ["$next_invoice_amount", 0]}}
        }}
    ]
    
    totals_result = await db.condominiums.aggregate(totals_pipeline).to_list(1)
    totals = totals_result[0] if totals_result else {
        "total_paid_seats": 0,
        "total_active_users": 0,
        "total_monthly_revenue": 0
    }
    
    return {
        "condominiums": condos,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size if total_count > 0 else 0,
            "has_next": skip + page_size < total_count,
            "has_prev": page > 1
        },
        "totals": {
            "total_condominiums": total_count,
            "total_paid_seats": totals.get("total_paid_seats", 0),
            "total_active_users": totals.get("total_active_users", 0),
            "total_monthly_revenue": round(totals.get("total_monthly_revenue", 0), 2)
        }
    }


# Legacy endpoint for backwards compatibility (deprecated)
@billing_super_admin_router.get("/overview-legacy")
async def get_all_condominiums_billing_legacy(current_user = Depends(require_role("SuperAdmin"))):
    """
    DEPRECATED: Use /super-admin/billing/overview with pagination params instead.
    This endpoint is kept for backwards compatibility but will be removed.
    """
    condos = await db.condominiums.find({"is_active": True}, {"_id": 0}).to_list(1000)
    
    # Get global pricing for comparison
    global_config = await get_global_pricing()
    
    overview = []
    total_revenue = 0
    total_users = 0
    total_seats = 0
    
    for condo in condos:
        condo_id = condo.get("id")
        active_users = await count_active_users(condo_id)
        paid_seats = condo.get("paid_seats", 10)
        
        # PHASE 4: Use dynamic pricing per condo
        price_per_seat = await get_effective_seat_price(condo_id)
        monthly_revenue = round(paid_seats * price_per_seat, 2)
        
        overview.append({
            "condominium_id": condo_id,
            "condominium_name": condo.get("name", ""),
            "paid_seats": paid_seats,
            "active_users": active_users,
            "remaining_seats": max(0, paid_seats - active_users),
            "billing_status": condo.get("billing_status", "active"),
            "monthly_revenue": monthly_revenue,
            "price_per_seat": price_per_seat,
            "uses_override": condo.get("seat_price_override") is not None and condo.get("seat_price_override") > 0,
            "stripe_customer_id": condo.get("stripe_customer_id"),
            "stripe_subscription_id": condo.get("stripe_subscription_id")
        })
        
        total_revenue += monthly_revenue
        total_users += active_users
        total_seats += paid_seats
    
    return {
        "condominiums": overview,
        "totals": {
            "total_condominiums": len(condos),
            "total_paid_seats": total_seats,
            "total_active_users": total_users,
            "total_monthly_revenue": total_revenue
        }
    }


@router.patch("/super-admin/condominiums/{condo_id}/billing")
async def update_condominium_billing(
    condo_id: str,
    paid_seats: Optional[int] = None,
    billing_status: Optional[str] = None,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    current_user = Depends(require_role("SuperAdmin"))
):
    """SuperAdmin: Update condominium billing settings"""
    condo = await db.condominiums.find_one({"id": condo_id})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if paid_seats is not None:
        # Prevent downgrading below active users
        active_users = await count_active_users(condo_id)
        if paid_seats < active_users:
            raise HTTPException(
                status_code=400, 
                detail=f"No se puede reducir a {paid_seats} asientos. Hay {active_users} usuarios activos."
            )
        update_data["paid_seats"] = paid_seats
    
    if billing_status is not None:
        if billing_status not in ["active", "past_due", "cancelled", "trialing"]:
            raise HTTPException(status_code=400, detail="Estado de facturación inválido")
        update_data["billing_status"] = billing_status
    
    if stripe_customer_id is not None:
        update_data["stripe_customer_id"] = stripe_customer_id
    
    if stripe_subscription_id is not None:
        update_data["stripe_subscription_id"] = stripe_subscription_id
    
    await db.condominiums.update_one({"id": condo_id}, {"$set": update_data})
    
    await log_billing_event(
        "billing_updated_by_superadmin",
        condo_id,
        {"updates": update_data},
        current_user["id"]
    )
    
    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "billing",
        {"action": "billing_updated", "condo_id": condo_id},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id,
        user_email=current_user.get("email"),
    )
    return {"message": "Configuración de facturación actualizada", "updates": update_data}

# ==================== AUDIT MODULE ====================
