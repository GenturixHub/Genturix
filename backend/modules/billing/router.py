"""
BILLING ROUTER MODULE
=====================
API endpoints for billing operations.
Migrated from server.py - PHASE 2 of backend modularization.

All billing endpoints are now centralized here.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from typing import Optional, Tuple
from datetime import datetime, timezone, timedelta
import uuid
import logging

# Import models from billing module
from .models import (
    BillingStatus,
    BillingCycle,
    BillingProvider,
    BillingEventType,
    SeatUpgradeRequestStatus,
    ConfirmPaymentRequest,
    ConfirmPaymentResponse,
    PaymentHistoryResponse,
    SeatUpgradeRequestModel,
    SeatUpgradeRequestResponse,
    SeatUpgradeRequest,
    SeatUpdateRequest,
    BillingPreviewRequest,
    BillingPreviewResponse,
    BillingInfoResponse,
    SeatUsageResponse,
    SeatReductionValidation,
)

# Create router with billing prefix and tags
router = APIRouter(prefix="/billing", tags=["billing"])

# SuperAdmin router for billing overview endpoints
super_admin_router = APIRouter(prefix="/super-admin", tags=["super-admin-billing"])

# Condominium billing router
condo_router = APIRouter(prefix="/condominiums", tags=["condominiums-billing"])

# Logger
logger = logging.getLogger(__name__)

# ==================== DEPENDENCIES (will be injected from server.py) ====================
# These will be set by init_router() called from server.py

db = None
get_current_user = None
require_role = None
RoleEnum = None

# Helper functions from server.py
calculate_billing_preview = None
calculate_invoice = None
log_billing_engine_event = None
send_billing_notification_email = None
run_daily_billing_check = None
billing_scheduler = None
get_billing_info = None
can_create_user = None
count_active_residents = None
count_active_users = None
get_effective_seat_price = None
get_global_pricing = None
log_billing_event = None

# Constants
DEFAULT_GRACE_PERIOD_DAYS = 5


def init_router(
    database,
    current_user_dep,
    require_role_dep,
    role_enum,
    calc_billing_preview_fn,
    calc_invoice_fn,
    log_billing_event_fn,
    send_billing_email_fn,
    run_daily_check_fn,
    scheduler_instance,
    get_billing_info_fn,
    can_create_user_fn,
    count_residents_fn,
    count_users_fn,
    get_seat_price_fn,
    get_global_pricing_fn,
    log_billing_event_simple_fn,
):
    """
    Initialize router with dependencies from server.py.
    This is called once during app startup to inject all required dependencies.
    """
    global db, get_current_user, require_role, RoleEnum
    global calculate_billing_preview, calculate_invoice, log_billing_engine_event
    global send_billing_notification_email, run_daily_billing_check, billing_scheduler
    global get_billing_info, can_create_user, count_active_residents, count_active_users
    global get_effective_seat_price, get_global_pricing, log_billing_event
    
    db = database
    get_current_user = current_user_dep
    require_role = require_role_dep
    RoleEnum = role_enum
    calculate_billing_preview = calc_billing_preview_fn
    calculate_invoice = calc_invoice_fn
    log_billing_engine_event = log_billing_event_fn
    send_billing_notification_email = send_billing_email_fn
    run_daily_billing_check = run_daily_check_fn
    billing_scheduler = scheduler_instance
    get_billing_info = get_billing_info_fn
    can_create_user = can_create_user_fn
    count_active_residents = count_residents_fn
    count_active_users = count_users_fn
    get_effective_seat_price = get_seat_price_fn
    get_global_pricing = get_global_pricing_fn
    log_billing_event = log_billing_event_simple_fn


# ==================== SCHEDULER ADMIN ENDPOINTS ====================

@router.post("/scheduler/run-now")
async def run_billing_scheduler_now(
    current_user = Depends(lambda: require_role(RoleEnum.SUPER_ADMIN))
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


@router.get("/scheduler/history")
async def get_scheduler_run_history(
    limit: int = Query(30, ge=1, le=100),
    current_user = Depends(lambda: require_role(RoleEnum.SUPER_ADMIN))
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


@router.get("/scheduler/status")
async def get_scheduler_status(
    current_user = Depends(lambda: require_role(RoleEnum.SUPER_ADMIN))
):
    """
    SuperAdmin: Check billing scheduler status.
    """
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


# ==================== BILLING PREVIEW ====================

@router.post("/preview", response_model=BillingPreviewResponse)
async def get_billing_preview_endpoint(
    preview_request: BillingPreviewRequest,
    current_user = Depends(lambda: require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
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


# ==================== BILLING EVENTS ====================

@router.get("/events/{condominium_id}")
async def get_billing_events(
    condominium_id: str,
    limit: int = 50,
    current_user = Depends(lambda: require_role(RoleEnum.SUPER_ADMIN))
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


# ==================== SEAT MANAGEMENT ====================

@router.patch("/seats/{condominium_id}")
async def update_condominium_seats(
    condominium_id: str,
    request: Request,
    seat_update: SeatUpdateRequest,
    current_user = Depends(lambda: require_role(RoleEnum.SUPER_ADMIN))
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


# ==================== PAYMENT CONFIRMATION ====================

@router.post("/confirm-payment/{condominium_id}", response_model=ConfirmPaymentResponse)
async def confirm_sinpe_payment(
    condominium_id: str,
    request: Request,
    payment_data: ConfirmPaymentRequest,
    current_user = Depends(lambda: require_role(RoleEnum.SUPER_ADMIN))
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
        except:
            billing_cycle_start = now - timedelta(days=30)
    else:
        billing_cycle_start = now - timedelta(days=30)
    
    # Calculate total paid in current billing cycle
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
            new_status = "past_due"
        elif previous_status == "active":
            new_status = "past_due"
        else:
            new_status = previous_status
        
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


# ==================== PAYMENT HISTORY ====================

@router.get("/payments/{condominium_id}")
async def get_payment_history(
    condominium_id: str,
    limit: int = 50,
    current_user = Depends(lambda: require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
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


@router.get("/payments")
async def get_all_pending_payments(
    status: Optional[str] = None,
    current_user = Depends(lambda: require_role(RoleEnum.SUPER_ADMIN))
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


# ==================== BILLING BALANCE ====================

@router.get("/balance/{condominium_id}")
async def get_billing_balance(
    condominium_id: str,
    current_user = Depends(lambda: require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """
    Get detailed billing balance for a condominium.
    Shows invoice amount, total paid in current cycle, and balance due.
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
        except:
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

@router.post("/request-seat-upgrade")
async def request_seat_upgrade(
    request_data: SeatUpgradeRequestModel,
    current_user = Depends(lambda: require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN))
):
    """
    SINPE BILLING: Request additional seats for a condominium.
    Admin can request, but SuperAdmin must approve.
    """
    condo_id = current_user.get("condominium_id")
    
    # SuperAdmin should use direct methods instead
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


@router.get("/my-pending-request")
async def get_my_pending_request(
    current_user = Depends(lambda: require_role(RoleEnum.ADMINISTRADOR))
):
    """
    Get the current admin's pending seat upgrade request, if any.
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


@router.get("/upgrade-requests")
async def get_upgrade_requests(
    status: Optional[str] = "pending",
    current_user = Depends(lambda: require_role(RoleEnum.SUPER_ADMIN))
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


@router.patch("/approve-seat-upgrade/{request_id}")
async def approve_seat_upgrade(
    request_id: str,
    approve: bool = True,
    current_user = Depends(lambda: require_role(RoleEnum.SUPER_ADMIN))
):
    """
    SINPE BILLING: Approve or reject a seat upgrade request.
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
                "billing_status": "upgrade_pending",
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


# ==================== SEAT STATUS ====================

async def check_seat_limit(condominium_id: str) -> dict:
    """
    SEAT PROTECTION: Check if condominium can create more users.
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


@router.get("/seat-status/{condominium_id}")
async def get_seat_status(
    condominium_id: str,
    current_user = Depends(lambda: get_current_user)
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


# ==================== BILLING INFO ====================

@router.get("/info")
async def get_condominium_billing_info(current_user = Depends(lambda: get_current_user)):
    """Get billing information for the current user's condominium"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asociado a un condominio")
    
    billing_info = await get_billing_info(condo_id)
    if not billing_info:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    
    return billing_info


@router.get("/can-create-user")
async def check_can_create_user_endpoint(
    role: str = "Residente",
    current_user = Depends(lambda: require_role("Administrador", "SuperAdmin"))
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


# ==================== BILLING HISTORY ====================

@router.get("/history")
async def get_billing_history_endpoint(current_user = Depends(lambda: require_role("Administrador"))):
    """Get billing transaction history for the condominium"""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="Usuario no asociado a un condominio")
    
    transactions = await db.billing_transactions.find(
        {"condominium_id": condo_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return transactions


# ==================== SUPER ADMIN BILLING OVERVIEW ====================

@super_admin_router.get("/billing/overview")
async def get_all_condominiums_billing(
    current_user = Depends(lambda: require_role("SuperAdmin")),
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
    OPTIMIZED v2.0 with backend pagination.
    """
    global_config = await get_global_pricing()
    default_price = global_config.get("price_per_seat", 2.99)
    
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
    
    # Build aggregation pipeline
    pipeline = [
        {"$match": mongo_filter},
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
    
    # Get total count
    total_count = await db.condominiums.count_documents(mongo_filter)
    
    # Add pagination
    skip = (page - 1) * page_size
    pipeline.append({"$skip": skip})
    pipeline.append({"$limit": page_size})
    
    # Execute aggregation
    condos = await db.condominiums.aggregate(pipeline).to_list(page_size)
    
    # Calculate totals
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


@super_admin_router.get("/billing/overview-legacy")
async def get_all_condominiums_billing_legacy(current_user = Depends(lambda: require_role("SuperAdmin"))):
    """
    DEPRECATED: Use /super-admin/billing/overview with pagination params instead.
    """
    condos = await db.condominiums.find({"is_active": True}, {"_id": 0}).to_list(1000)
    
    global_config = await get_global_pricing()
    
    overview = []
    total_revenue = 0
    total_users = 0
    total_seats = 0
    
    for condo in condos:
        condo_id = condo.get("id")
        active_users = await count_active_users(condo_id)
        paid_seats = condo.get("paid_seats", 10)
        
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


@super_admin_router.patch("/condominiums/{condo_id}/billing")
async def update_condominium_billing(
    condo_id: str,
    paid_seats: Optional[int] = None,
    billing_status: Optional[str] = None,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    current_user = Depends(lambda: require_role("SuperAdmin"))
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
    
    return {"message": "Configuración de facturación actualizada", "updates": update_data}


# ==================== CONDOMINIUM BILLING ====================

@condo_router.get("/{condo_id}/billing")
async def get_condominium_billing(
    condo_id: str,
    current_user = Depends(lambda: require_role(RoleEnum.ADMINISTRADOR))
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
