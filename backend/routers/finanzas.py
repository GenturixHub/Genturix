"""GENTURIX - Finanzas + Units Router (Auto-extracted from server.py)"""
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

# ==================== FINANZAS AVANZADAS ====================
# Advanced Financial Module: charges, payments, unit accounts
# Collections: charges_catalog, unit_accounts, payment_records

class ChargeType(str, Enum):
    FIXED = "fixed"
    VARIABLE = "variable"

class PaymentStatus(str, Enum):
    PAID = "paid"
    PENDING = "pending"
    OVERDUE = "overdue"
    PARTIAL = "partial"

class AccountStatus(str, Enum):
    AL_DIA = "al_dia"
    ATRASADO = "atrasado"
    ADELANTADO = "adelantado"

class ChargeCatalogCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: ChargeType = ChargeType.FIXED
    default_amount: float = Field(..., gt=0)

class ChargeCatalogUpdate(BaseModel):
    name: Optional[str] = None
    default_amount: Optional[float] = Field(None, gt=0)
    is_active: Optional[bool] = None

class ChargeCreate(BaseModel):
    unit_id: str
    charge_type_id: str
    period: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    amount_due: float = Field(..., gt=0)
    due_date: Optional[str] = None

class PaymentCreate(BaseModel):
    unit_id: str
    amount: float = Field(..., gt=0)
    payment_method: str = Field("efectivo", max_length=50)
    charge_ids: Optional[List[str]] = None
    period: Optional[str] = Field(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


def _compute_account_status(balance: float) -> str:
    if balance == 0:
        return AccountStatus.AL_DIA.value
    elif balance > 0:
        return AccountStatus.ATRASADO.value
    else:
        return AccountStatus.ADELANTADO.value


async def _recalculate_unit_balance(condo_id: str, unit_id: str):
    """Recalculate a unit's balance from source records. Single source of truth."""
    total_due = 0.0
    total_paid = 0.0

    async for rec in db.payment_records.find(
        {"condominium_id": condo_id, "unit_id": unit_id}
    ):
        total_due += rec.get("amount_due", 0)
        total_paid += rec.get("amount_paid", 0)

    balance = round(total_due - total_paid, 2)
    status = _compute_account_status(balance)
    now = datetime.now(timezone.utc).isoformat()

    await db.unit_accounts.update_one(
        {"condominium_id": condo_id, "unit_id": unit_id},
        {
            "$set": {
                "current_balance": balance,
                "status": status,
                "updated_at": now,
            },
            "$setOnInsert": {
                "id": str(uuid.uuid4()),
                "condominium_id": condo_id,
                "unit_id": unit_id,
                "resident_id": None,
                "created_at": now,
            },
        },
        upsert=True,
    )
    return balance, status


# ── Charge Catalog ──

@router.post("/finanzas/catalog")
async def create_charge_catalog(
    payload: ChargeCatalogCreate,
    request: Request,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Create a charge type in the catalog."""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="No condominium associated")

    doc = {
        "id": str(uuid.uuid4()),
        "condominium_id": condo_id,
        "name": sanitize_text(payload.name),
        "type": payload.type.value,
        "default_amount": round(payload.default_amount, 2),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.charges_catalog.insert_one(doc)

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "finanzas",
        {"action": "catalog_created", "charge_name": doc["name"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=current_user.get("email"),
    )

    safe = {k: v for k, v in doc.items() if k != "_id"}
    return safe


@router.get("/finanzas/catalog")
async def get_charge_catalog(
    current_user=Depends(get_current_user),
):
    """List charge catalog for the condominium."""
    condo_id = current_user.get("condominium_id")
    items = await db.charges_catalog.find(
        {"condominium_id": condo_id, "is_active": True}, {"_id": 0}
    ).sort("name", 1).to_list(100)
    return items


@router.patch("/finanzas/catalog/{catalog_id}")
async def update_charge_catalog(
    catalog_id: str,
    payload: ChargeCatalogUpdate,
    request: Request,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Update a charge catalog entry."""
    condo_id = current_user.get("condominium_id")
    update = {}
    if payload.name is not None:
        update["name"] = sanitize_text(payload.name)
    if payload.default_amount is not None:
        update["default_amount"] = round(payload.default_amount, 2)
    if payload.is_active is not None:
        update["is_active"] = payload.is_active

    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await db.charges_catalog.update_one(
        {"id": catalog_id, "condominium_id": condo_id}, {"$set": update}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cargo no encontrado")

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "finanzas",
        {"action": "catalog_updated", "catalog_id": catalog_id},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=current_user.get("email"),
    )

    updated = await db.charges_catalog.find_one({"id": catalog_id}, {"_id": 0})
    return updated


# ── Charges (generate charges for units) ──

@router.post("/finanzas/charges")
async def create_charge(
    payload: ChargeCreate,
    request: Request,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Create a charge for a specific unit and period."""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="No condominium associated")

    # Validate charge type exists
    charge_type = await db.charges_catalog.find_one(
        {"id": payload.charge_type_id, "condominium_id": condo_id, "is_active": True}
    )
    if not charge_type:
        raise HTTPException(status_code=404, detail="Tipo de cargo no encontrado")

    # Prevent duplicate: same unit, charge_type, period
    existing = await db.payment_records.find_one({
        "condominium_id": condo_id,
        "unit_id": payload.unit_id,
        "charge_type_id": payload.charge_type_id,
        "period": payload.period,
    })
    if existing:
        raise HTTPException(status_code=409, detail=f"Ya existe un cargo de '{charge_type['name']}' para el período {payload.period}")

    now = datetime.now(timezone.utc).isoformat()
    due_date = payload.due_date or f"{payload.period}-15T00:00:00Z"

    record = {
        "id": str(uuid.uuid4()),
        "condominium_id": condo_id,
        "unit_id": payload.unit_id,
        "resident_id": None,
        "charge_type_id": payload.charge_type_id,
        "charge_type_name": charge_type["name"],
        "period": payload.period,
        "amount_due": round(payload.amount_due, 2),
        "amount_paid": 0.0,
        "balance_after": 0.0,
        "status": PaymentStatus.PENDING.value,
        "due_date": due_date,
        "paid_at": None,
        "payment_method": None,
        "created_at": now,
        "updated_at": now,
    }

    await db.payment_records.insert_one(record)

    # Recalculate balance
    balance, acct_status = await _recalculate_unit_balance(condo_id, payload.unit_id)
    record["balance_after"] = balance
    await db.payment_records.update_one({"id": record["id"]}, {"$set": {"balance_after": balance}})

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "finanzas",
        {"action": "charge_created", "unit_id": payload.unit_id, "period": payload.period, "amount": record["amount_due"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=current_user.get("email"),
    )

    safe = {k: v for k, v in record.items() if k != "_id"}
    return safe


class BulkChargeRequest(BaseModel):
    charge_type_id: str
    period: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    due_date: Optional[str] = None
    unit_ids: Optional[List[str]] = None  # None = all existing units


@router.post("/finanzas/generate-bulk")
@limiter.limit(RATE_LIMIT_PUSH)
async def generate_bulk_charges(
    payload: BulkChargeRequest,
    request: Request,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Generate charges for all (or specified) units in the condominium. Skips duplicates."""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="No condominium associated")

    # Validate charge type
    charge_type = await db.charges_catalog.find_one(
        {"id": payload.charge_type_id, "condominium_id": condo_id, "is_active": True}
    )
    if not charge_type:
        raise HTTPException(status_code=404, detail="Tipo de cargo no encontrado")

    # Determine target units
    if payload.unit_ids and len(payload.unit_ids) > 0:
        target_units = payload.unit_ids
    else:
        # All existing unit accounts in this condominium
        accounts = await db.unit_accounts.find(
            {"condominium_id": condo_id}, {"unit_id": 1, "_id": 0}
        ).to_list(5000)
        target_units = [a["unit_id"] for a in accounts]

    if not target_units:
        return {"total_units": 0, "created_count": 0, "skipped_count": 0, "message": "No hay unidades registradas"}

    now = datetime.now(timezone.utc).isoformat()
    due_date = payload.due_date or f"{payload.period}-15T00:00:00Z"
    amount = round(charge_type["default_amount"], 2)

    created_count = 0
    skipped_count = 0

    for unit_id in target_units:
        # Check duplicate
        existing = await db.payment_records.find_one({
            "condominium_id": condo_id,
            "unit_id": unit_id,
            "charge_type_id": payload.charge_type_id,
            "period": payload.period,
        })
        if existing:
            skipped_count += 1
            continue

        record = {
            "id": str(uuid.uuid4()),
            "condominium_id": condo_id,
            "unit_id": unit_id,
            "resident_id": None,
            "charge_type_id": payload.charge_type_id,
            "charge_type_name": charge_type["name"],
            "period": payload.period,
            "amount_due": amount,
            "amount_paid": 0.0,
            "balance_after": 0.0,
            "status": PaymentStatus.PENDING.value,
            "due_date": due_date,
            "paid_at": None,
            "payment_method": None,
            "created_at": now,
            "updated_at": now,
        }
        await db.payment_records.insert_one(record)
        created_count += 1

    # Recalculate balances for all affected units
    for unit_id in target_units:
        await _recalculate_unit_balance(condo_id, unit_id)

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "finanzas",
        {
            "action": "bulk_charges_generated",
            "charge_type": charge_type["name"],
            "period": payload.period,
            "total_units": len(target_units),
            "created": created_count,
            "skipped": skipped_count,
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=current_user.get("email"),
    )

    return {
        "total_units": len(target_units),
        "created_count": created_count,
        "skipped_count": skipped_count,
        "charge_type": charge_type["name"],
        "period": payload.period,
        "amount": amount,
    }



@router.get("/finanzas/charges")
async def get_charges(
    unit_id: Optional[str] = None,
    status: Optional[str] = None,
    period: Optional[str] = None,
    page: int = 1,
    page_size: int = 30,
    current_user=Depends(get_current_user),
):
    """List charges. Admin sees all, resident sees own unit."""
    condo_id = current_user.get("condominium_id")
    roles = current_user.get("roles", [])
    is_admin = any(r in roles for r in ["Administrador", "Supervisor", "SuperAdmin"])

    query = {"condominium_id": condo_id}

    if not is_admin:
        # Resident sees charges for their unit (matched by resident_id or apartment)
        query["$or"] = [
            {"resident_id": current_user["id"]},
            {"unit_id": current_user.get("apartment", "__none__")},
        ]

    if unit_id:
        query["unit_id"] = unit_id
    if status:
        query["status"] = status
    if period:
        query["period"] = period

    skip = (max(1, page) - 1) * page_size
    total = await db.payment_records.count_documents(query)
    items = (
        await db.payment_records.find(query, {"_id": 0})
        .sort("period", -1)
        .skip(skip)
        .limit(min(page_size, 100))
        .to_list(min(page_size, 100))
    )

    return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": max(1, -(-total // page_size))}


# ── Payments ──

@router.post("/finanzas/payments")
@limiter.limit(RATE_LIMIT_PUSH)
async def register_payment(
    payload: PaymentCreate,
    request: Request,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Register a payment for a unit. Handles partial, full, and overpayment (credit)."""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="No condominium associated")

    amount_remaining = round(payload.amount, 2)
    now = datetime.now(timezone.utc).isoformat()
    applied_records = []

    if payload.charge_ids and len(payload.charge_ids) > 0:
        # Apply to specific charges
        targets = await db.payment_records.find(
            {"id": {"$in": payload.charge_ids}, "condominium_id": condo_id, "unit_id": payload.unit_id}
        ).sort("period", 1).to_list(100)
    else:
        # Apply to oldest pending/partial/overdue charges
        targets = await db.payment_records.find(
            {"condominium_id": condo_id, "unit_id": payload.unit_id, "status": {"$in": ["pending", "partial", "overdue"]}}
        ).sort("period", 1).to_list(100)

    for rec in targets:
        if amount_remaining <= 0:
            break

        remaining_due = round(rec["amount_due"] - rec["amount_paid"], 2)
        if remaining_due <= 0:
            continue

        to_apply = min(amount_remaining, remaining_due)
        new_paid = round(rec["amount_paid"] + to_apply, 2)
        new_status = PaymentStatus.PAID.value if new_paid >= rec["amount_due"] else PaymentStatus.PARTIAL.value

        update_set = {
            "amount_paid": new_paid,
            "status": new_status,
            "payment_method": payload.payment_method,
            "updated_at": now,
        }
        if new_status == PaymentStatus.PAID.value:
            update_set["paid_at"] = now

        await db.payment_records.update_one({"id": rec["id"]}, {"$set": update_set})
        amount_remaining = round(amount_remaining - to_apply, 2)
        applied_records.append({"record_id": rec["id"], "applied": to_apply, "new_status": new_status})

    # If there's remaining amount → credit / advance payment
    if amount_remaining > 0:
        credit_period = payload.period or datetime.now(timezone.utc).strftime("%Y-%m")
        credit_record = {
            "id": str(uuid.uuid4()),
            "condominium_id": condo_id,
            "unit_id": payload.unit_id,
            "resident_id": None,
            "charge_type_id": "credit",
            "charge_type_name": "Saldo a favor",
            "period": credit_period,
            "amount_due": 0.0,
            "amount_paid": round(amount_remaining, 2),
            "balance_after": 0.0,
            "status": PaymentStatus.PAID.value,
            "due_date": None,
            "paid_at": now,
            "payment_method": payload.payment_method,
            "created_at": now,
            "updated_at": now,
        }
        await db.payment_records.insert_one(credit_record)
        applied_records.append({"record_id": credit_record["id"], "applied": amount_remaining, "new_status": "credit"})

    # Recalculate balance
    balance, acct_status = await _recalculate_unit_balance(condo_id, payload.unit_id)

    await log_audit_event(
        AuditEventType.PAYMENT_COMPLETED, current_user["id"], "finanzas",
        {"action": "payment_registered", "unit_id": payload.unit_id, "total_amount": payload.amount, "applied_to": len(applied_records)},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=current_user.get("email"),
    )

    return {
        "message": "Pago registrado",
        "total_paid": payload.amount,
        "applied": applied_records,
        "new_balance": balance,
        "account_status": acct_status,
    }


@router.get("/finanzas/payments")
async def get_payments(
    unit_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 30,
    current_user=Depends(get_current_user),
):
    """List payment history."""
    condo_id = current_user.get("condominium_id")
    roles = current_user.get("roles", [])
    is_admin = any(r in roles for r in ["Administrador", "Supervisor", "SuperAdmin"])

    query = {"condominium_id": condo_id, "amount_paid": {"$gt": 0}}

    if not is_admin:
        query["$or"] = [
            {"resident_id": current_user["id"]},
            {"unit_id": current_user.get("apartment", "__none__")},
        ]
    elif unit_id:
        query["unit_id"] = unit_id

    skip = (max(1, page) - 1) * page_size
    total = await db.payment_records.count_documents(query)
    items = (
        await db.payment_records.find(query, {"_id": 0})
        .sort("updated_at", -1)
        .skip(skip)
        .limit(min(page_size, 100))
        .to_list(min(page_size, 100))
    )

    return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": max(1, -(-total // page_size))}


# ── Unit Account ──

@router.get("/finanzas/unit/{unit_id}")
async def get_unit_account(
    unit_id: str,
    current_user=Depends(get_current_user),
):
    """Get full financial status for a unit."""
    condo_id = current_user.get("condominium_id")
    roles = current_user.get("roles", [])
    is_admin = any(r in roles for r in ["Administrador", "Supervisor", "SuperAdmin"])

    if not is_admin:
        user_apt = current_user.get("apartment", "")
        if unit_id != user_apt and unit_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="No tienes acceso a esta unidad")

    # Get or create account
    account = await db.unit_accounts.find_one(
        {"condominium_id": condo_id, "unit_id": unit_id}, {"_id": 0}
    )
    if not account:
        balance, status = await _recalculate_unit_balance(condo_id, unit_id)
        account = await db.unit_accounts.find_one(
            {"condominium_id": condo_id, "unit_id": unit_id}, {"_id": 0}
        )

    # Get charge breakdown
    records = await db.payment_records.find(
        {"condominium_id": condo_id, "unit_id": unit_id}, {"_id": 0}
    ).sort("period", -1).to_list(200)

    # Breakdown by charge type
    breakdown = {}
    for rec in records:
        ct = rec.get("charge_type_name", "Otro")
        if ct not in breakdown:
            breakdown[ct] = {"total_due": 0, "total_paid": 0, "pending": 0}
        breakdown[ct]["total_due"] = round(breakdown[ct]["total_due"] + rec.get("amount_due", 0), 2)
        breakdown[ct]["total_paid"] = round(breakdown[ct]["total_paid"] + rec.get("amount_paid", 0), 2)
        breakdown[ct]["pending"] = round(breakdown[ct]["total_due"] - breakdown[ct]["total_paid"], 2)

    return {
        "account": account or {"unit_id": unit_id, "current_balance": 0, "status": "al_dia"},
        "records": records[:50],
        "breakdown": breakdown,
    }


@router.get("/finanzas/overview")
async def get_financial_overview(
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPERVISOR, RoleEnum.SUPER_ADMIN)),
):
    """Admin overview: all unit accounts with resident info, totals, overdue count."""
    condo_id = current_user.get("condominium_id")
    base = {"condominium_id": condo_id}

    accounts = await db.unit_accounts.find(base, {"_id": 0}).sort("unit_id", 1).to_list(500)

    # Build a map of apartment_number -> user info for residents in this condo
    resident_map = {}
    async for u in db.users.find(
        {"condominium_id": condo_id, "status": {"$ne": "disabled"}},
        {"_id": 0, "id": 1, "full_name": 1, "email": 1, "role_data": 1, "roles": 1, "apartment": 1}
    ):
        apt = u.get("role_data", {}).get("apartment_number", "") or u.get("apartment", "")
        if apt:
            # If multiple users share an apartment, prefer Residente role
            existing = resident_map.get(apt)
            if not existing or "Residente" in u.get("roles", []):
                resident_map[apt] = {
                    "resident_id": u["id"],
                    "resident_name": u.get("full_name", ""),
                    "resident_email": u.get("email", ""),
                }

    total_due = 0.0
    total_paid = 0.0
    overdue_count = 0
    al_dia_count = 0
    adelantado_count = 0

    # Enrich accounts with resident info
    enriched_accounts = []
    for a in accounts:
        bal = a.get("current_balance", 0)
        if bal > 0:
            overdue_count += 1
            total_due += bal
        elif bal < 0:
            adelantado_count += 1
            total_paid += abs(bal)
        else:
            al_dia_count += 1

        unit_id = a.get("unit_id", "")
        resident_info = resident_map.get(unit_id, {})
        enriched = {**a, **resident_info}
        enriched_accounts.append(enriched)

    # Global totals from records
    pipeline = [
        {"$match": base},
        {"$group": {"_id": None, "sum_due": {"$sum": "$amount_due"}, "sum_paid": {"$sum": "$amount_paid"}}},
    ]
    agg = await db.payment_records.aggregate(pipeline).to_list(1)
    global_due = round(agg[0]["sum_due"], 2) if agg else 0
    global_paid = round(agg[0]["sum_paid"], 2) if agg else 0

    return {
        "accounts": enriched_accounts,
        "summary": {
            "total_units": len(accounts),
            "al_dia": al_dia_count,
            "atrasado": overdue_count,
            "adelantado": adelantado_count,
            "global_due": global_due,
            "global_paid": global_paid,
            "global_balance": round(global_due - global_paid, 2),
        },
    }


# ── Payment Settings (SINPE / Transfer instructions) ──

class PaymentSettingsUpdate(BaseModel):
    sinpe_number: Optional[str] = Field(None, max_length=50)
    sinpe_name: Optional[str] = Field(None, max_length=100)
    bank_account: Optional[str] = Field(None, max_length=100)
    bank_name: Optional[str] = Field(None, max_length=100)
    bank_iban: Optional[str] = Field(None, max_length=50)
    additional_instructions: Optional[str] = Field(None, max_length=500)


@router.get("/finanzas/payment-settings")
async def get_payment_settings(
    current_user=Depends(get_current_user),
):
    """Get payment settings (SINPE/Transfer info) for the condominium."""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        return {}
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "payment_settings": 1})
    return condo.get("payment_settings", {}) if condo else {}


@router.put("/finanzas/payment-settings")
async def update_payment_settings(
    payload: PaymentSettingsUpdate,
    request: Request,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Update payment settings (SINPE/Transfer info) for the condominium."""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="No condominium associated")

    settings = {k: v for k, v in payload.model_dump().items() if v is not None}
    await db.condominiums.update_one(
        {"id": condo_id},
        {"$set": {"payment_settings": settings}},
    )

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "finanzas",
        {"action": "payment_settings_updated", "settings": list(settings.keys())},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=current_user.get("email"),
    )

    return {"status": "ok", "settings": settings}


# ── Assign Unit to User ──

class AssignUnitPayload(BaseModel):
    user_id: str
    unit_id: str = Field(..., min_length=1, max_length=50)


# ══════════════════════════════════════════════════════════════
# UNITS MODULE — Collection: units
# ══════════════════════════════════════════════════════════════

class UnitCreate(BaseModel):
    number: str = Field(..., min_length=1, max_length=50)


class UnitUpdate(BaseModel):
    number: Optional[str] = Field(None, min_length=1, max_length=50)


@router.get("/units")
async def list_units(
    current_user=Depends(get_current_user),
):
    """List all units for the condominium, enriched with assigned residents."""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        return {"items": []}

    units = await db.units.find(
        {"condominium_id": condo_id}, {"_id": 0}
    ).sort("number", 1).to_list(500)

    # Build resident map: unit number -> list of users
    resident_map = {}
    async for u in db.users.find(
        {"condominium_id": condo_id, "status": {"$ne": "disabled"}},
        {"_id": 0, "id": 1, "full_name": 1, "email": 1, "roles": 1, "apartment": 1, "role_data": 1}
    ):
        apt = u.get("apartment") or u.get("role_data", {}).get("apartment_number", "")
        if apt:
            if apt not in resident_map:
                resident_map[apt] = []
            resident_map[apt].append({
                "id": u["id"],
                "full_name": u.get("full_name", ""),
                "email": u.get("email", ""),
                "roles": u.get("roles", []),
            })

    # Get financial data for each unit
    account_map = {}
    async for acc in db.unit_accounts.find({"condominium_id": condo_id}, {"_id": 0}):
        account_map[acc["unit_id"]] = {
            "current_balance": acc.get("current_balance", 0),
            "status": acc.get("status", "al_dia"),
        }

    enriched = []
    for unit in units:
        num = unit["number"]
        enriched.append({
            **unit,
            "residents": resident_map.get(num, []),
            "finance": account_map.get(num, {"current_balance": 0, "status": "al_dia"}),
        })

    return {"items": enriched}


@router.post("/units")
async def create_unit(
    payload: UnitCreate,
    request: Request,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Create a new unit in the condominium."""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="No condominium associated")

    sanitized_number = sanitize_text(payload.number.strip())

    # Check duplicate
    existing = await db.units.find_one({"condominium_id": condo_id, "number": sanitized_number})
    if existing:
        raise HTTPException(status_code=409, detail=f"La unidad {sanitized_number} ya existe")

    now = datetime.now(timezone.utc).isoformat()
    unit = {
        "id": str(uuid.uuid4()),
        "condominium_id": condo_id,
        "number": sanitized_number,
        "created_at": now,
    }
    await db.units.insert_one(unit)

    # Also create a unit_account for financial tracking
    await db.unit_accounts.update_one(
        {"condominium_id": condo_id, "unit_id": sanitized_number},
        {"$setOnInsert": {
            "id": str(uuid.uuid4()),
            "condominium_id": condo_id,
            "unit_id": sanitized_number,
            "resident_id": None,
            "current_balance": 0,
            "status": "al_dia",
            "created_at": now,
            "updated_at": now,
        }},
        upsert=True,
    )

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "units",
        {"action": "unit_created", "unit_number": sanitized_number},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=current_user.get("email"),
    )

    safe = {k: v for k, v in unit.items() if k != "_id"}
    return safe


@router.delete("/units/{unit_id}")
async def delete_unit(
    unit_id: str,
    request: Request,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Delete a unit (only if no charges exist)."""
    condo_id = current_user.get("condominium_id")
    unit = await db.units.find_one({"id": unit_id, "condominium_id": condo_id})
    if not unit:
        raise HTTPException(status_code=404, detail="Unidad no encontrada")

    # Check if unit has financial records
    has_records = await db.payment_records.find_one({"condominium_id": condo_id, "unit_id": unit["number"]})
    if has_records:
        raise HTTPException(status_code=400, detail="No se puede eliminar: la unidad tiene registros financieros")

    await db.units.delete_one({"id": unit_id})
    await db.unit_accounts.delete_one({"condominium_id": condo_id, "unit_id": unit["number"]})

    # Unassign users from this unit
    await db.users.update_many(
        {"condominium_id": condo_id, "apartment": unit["number"]},
        {"$set": {"apartment": None, "role_data.apartment_number": None}},
    )

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "units",
        {"action": "unit_deleted", "unit_number": unit["number"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=current_user.get("email"),
    )

    return {"status": "ok"}


@router.put("/units/{unit_id}/assign-user")
async def assign_user_to_unit(
    unit_id: str,
    user_id: str = Query(...),
    request: Request = None,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Assign a user to a unit."""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="No condominium associated")

    unit = await db.units.find_one({"id": unit_id, "condominium_id": condo_id}, {"_id": 0})
    if not unit:
        raise HTTPException(status_code=404, detail="Unidad no encontrada")

    target_user = await db.users.find_one({"id": user_id, "condominium_id": condo_id}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    await db.users.update_one(
        {"id": user_id},
        {"$set": {"apartment": unit["number"], "role_data.apartment_number": unit["number"]}},
    )

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "units",
        {"action": "user_assigned_to_unit", "user_id": user_id, "unit": unit["number"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=current_user.get("email"),
    )

    return {"status": "ok", "unit": unit["number"], "user_id": user_id}


@router.put("/units/{unit_id}/unassign-user")
async def unassign_user_from_unit(
    unit_id: str,
    user_id: str = Query(...),
    request: Request = None,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Remove a user from a unit."""
    condo_id = current_user.get("condominium_id")
    unit = await db.units.find_one({"id": unit_id, "condominium_id": condo_id}, {"_id": 0})
    if not unit:
        raise HTTPException(status_code=404, detail="Unidad no encontrada")

    await db.users.update_one(
        {"id": user_id, "condominium_id": condo_id},
        {"$set": {"apartment": None, "role_data.apartment_number": None}},
    )

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "units",
        {"action": "user_unassigned_from_unit", "user_id": user_id, "unit": unit["number"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=current_user.get("email"),
    )

    return {"status": "ok"}


# ── Assign Unit (legacy endpoint — kept for backward compatibility) ──

@router.post("/finanzas/assign-unit")
async def assign_unit_to_user(
    payload: AssignUnitPayload,
    request: Request,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Admin assigns a unit (apartment_number) to a user."""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="No condominium associated")

    user = await db.users.find_one({"id": payload.user_id, "condominium_id": condo_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    await db.users.update_one(
        {"id": payload.user_id},
        {"$set": {
            "role_data.apartment_number": payload.unit_id,
            "apartment": payload.unit_id,
        }},
    )

    # Also ensure unit_account exists
    existing = await db.unit_accounts.find_one({"condominium_id": condo_id, "unit_id": payload.unit_id})
    if not existing:
        now = datetime.now(timezone.utc).isoformat()
        await db.unit_accounts.insert_one({
            "id": str(uuid.uuid4()),
            "condominium_id": condo_id,
            "unit_id": payload.unit_id,
            "resident_id": payload.user_id,
            "current_balance": 0,
            "status": "al_dia",
            "created_at": now,
            "updated_at": now,
        })

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "finanzas",
        {"action": "unit_assigned", "user_id": payload.user_id, "unit_id": payload.unit_id},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=current_user.get("email"),
    )

    return {"status": "ok", "user_id": payload.user_id, "unit_id": payload.unit_id}


# ── Resident Payment Request (manual) ──

class PaymentRequestCreate(BaseModel):
    amount: float = Field(..., gt=0)
    payment_method: str = Field(..., max_length=50)
    reference: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = Field(None, max_length=500)


@router.post("/finanzas/payment-request")
async def create_payment_request(
    payload: PaymentRequestCreate,
    request: Request,
    current_user=Depends(get_current_user),
):
    """Resident submits a payment request (SINPE/transfer proof)."""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="No condominium associated")

    unit_id = current_user.get("apartment", "") or current_user.get("role_data", {}).get("apartment_number", "")
    if not unit_id:
        raise HTTPException(status_code=400, detail="No tienes una unidad asignada")

    now = datetime.now(timezone.utc).isoformat()
    pr = {
        "id": str(uuid.uuid4()),
        "condominium_id": condo_id,
        "unit_id": unit_id,
        "resident_id": current_user["id"],
        "resident_name": current_user.get("full_name", ""),
        "amount": round(payload.amount, 2),
        "payment_method": sanitize_text(payload.payment_method),
        "reference": sanitize_text(payload.reference) if payload.reference else "",
        "notes": sanitize_text(payload.notes) if payload.notes else "",
        "status": "pending",
        "created_at": now,
        "reviewed_at": None,
        "reviewed_by": None,
    }
    await db.payment_requests.insert_one(pr)

    # Notify admin
    await db.notifications_v2.insert_one({
        "id": str(uuid.uuid4()),
        "condominium_id": condo_id,
        "notification_type": "finanzas",
        "title": "Nuevo comprobante de pago",
        "message": f"{current_user.get('full_name', 'Residente')} ({unit_id}) reportó un pago de ${payload.amount:.2f} vía {payload.payment_method}",
        "target_roles": ["Administrador"],
        "target_users": [],
        "read_by": [],
        "created_at": now,
    })

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "finanzas",
        {"action": "payment_request_created", "unit_id": unit_id, "amount": payload.amount, "method": payload.payment_method},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=current_user.get("email"),
    )

    safe = {k: v for k, v in pr.items() if k != "_id"}
    return safe


@router.get("/finanzas/payment-requests")
async def list_payment_requests(
    status: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    """List payment requests. Admin sees all, resident sees own."""
    condo_id = current_user.get("condominium_id")
    roles = current_user.get("roles", [])
    is_admin = any(r in roles for r in ["Administrador", "Supervisor", "SuperAdmin"])

    query = {"condominium_id": condo_id}
    if not is_admin:
        query["resident_id"] = current_user["id"]
    if status:
        query["status"] = status

    items = await db.payment_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"items": items}


@router.patch("/finanzas/payment-requests/{request_id}")
async def review_payment_request(
    request_id: str,
    action: str = Query(..., regex="^(approved|rejected)$"),
    request: Request = None,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Admin approves or rejects a payment request."""
    condo_id = current_user.get("condominium_id")
    pr = await db.payment_requests.find_one({"id": request_id, "condominium_id": condo_id}, {"_id": 0})
    if not pr:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    now = datetime.now(timezone.utc).isoformat()
    await db.payment_requests.update_one(
        {"id": request_id},
        {"$set": {"status": action, "reviewed_at": now, "reviewed_by": current_user["id"]}},
    )

    # If approved, register the actual payment
    if action == "approved":
        payment_data = PaymentCreate(
            unit_id=pr["unit_id"],
            amount=pr["amount"],
            payment_method=pr["payment_method"],
        )
        # Re-use the register_payment logic
        amount_remaining = round(pr["amount"], 2)
        pending = await db.payment_records.find(
            {"condominium_id": condo_id, "unit_id": pr["unit_id"], "status": {"$in": ["pending", "partial", "overdue"]}}
        ).sort("period", 1).to_list(100)

        for rec in pending:
            if amount_remaining <= 0:
                break
            owed = round(rec.get("amount_due", 0) - rec.get("amount_paid", 0), 2)
            if owed <= 0:
                continue
            apply = min(amount_remaining, owed)
            new_paid = round(rec.get("amount_paid", 0) + apply, 2)
            new_status = "paid" if new_paid >= rec["amount_due"] else "partial"
            await db.payment_records.update_one(
                {"id": rec["id"]},
                {"$set": {"amount_paid": new_paid, "status": new_status, "paid_at": now, "payment_method": pr["payment_method"], "updated_at": now}},
            )
            amount_remaining = round(amount_remaining - apply, 2)

        if amount_remaining > 0:
            credit_record = {
                "id": str(uuid.uuid4()),
                "condominium_id": condo_id,
                "unit_id": pr["unit_id"],
                "charge_type_name": "Saldo a favor",
                "period": datetime.now(timezone.utc).strftime("%Y-%m"),
                "amount_due": 0,
                "amount_paid": amount_remaining,
                "balance_after": 0,
                "status": "paid",
                "paid_at": now,
                "payment_method": pr["payment_method"],
                "created_at": now,
                "updated_at": now,
            }
            await db.payment_records.insert_one(credit_record)

        await _recalculate_unit_balance(condo_id, pr["unit_id"])

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "finanzas",
        {"action": f"payment_request_{action}", "request_id": request_id, "unit_id": pr["unit_id"], "amount": pr["amount"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=current_user.get("email"),
    )

    return {"status": "ok", "action": action, "request_id": request_id}


# ── Resident Financial Accounts ──

@router.get("/finanzas/residents")
async def list_resident_accounts(
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPERVISOR, RoleEnum.SUPER_ADMIN)),
):
    """List ALL residents with unit, balance, and status (even if no payments)."""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        return {"items": []}

    # Get all users in this condominium (residents)
    user_query = {"condominium_id": condo_id, "status": {"$ne": "disabled"}}
    users = await db.users.find(
        user_query,
        {"_id": 0, "id": 1, "full_name": 1, "email": 1, "roles": 1, "apartment": 1, "role_data": 1, "created_at": 1}
    ).to_list(1000)

    # Get all unit_accounts for balance lookups
    account_map = {}
    async for acc in db.unit_accounts.find({"condominium_id": condo_id}, {"_id": 0}):
        account_map[acc["unit_id"]] = acc

    items = []
    for u in users:
        apt = u.get("apartment") or u.get("role_data", {}).get("apartment_number", "")
        acct = account_map.get(apt, {}) if apt else {}
        balance = acct.get("current_balance", 0)
        fin_status = "al_dia" if balance == 0 else ("atrasado" if balance > 0 else "adelantado")

        # Apply search filter
        if search:
            q = search.lower()
            if q not in (u.get("full_name", "")).lower() and q not in (u.get("email", "")).lower() and q not in (apt or "").lower():
                continue

        # Apply status filter
        if status_filter and status_filter != "all" and fin_status != status_filter:
            continue

        items.append({
            "id": u["id"],
            "full_name": u.get("full_name", ""),
            "email": u.get("email", ""),
            "roles": u.get("roles", []),
            "unit": apt or None,
            "balance": round(balance, 2),
            "status": fin_status,
            "created_at": u.get("created_at", ""),
        })

    # Sort: atrasados first, then by name
    status_order = {"atrasado": 0, "al_dia": 1, "adelantado": 2}
    items.sort(key=lambda x: (status_order.get(x["status"], 9), x["full_name"]))

    return {"items": items, "total": len(items)}


@router.get("/finanzas/resident/{user_id}")
async def get_resident_account_detail(
    user_id: str,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPERVISOR, RoleEnum.SUPER_ADMIN)),
):
    """Get detailed financial status for a specific resident."""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="No condominium associated")

    user = await db.users.find_one(
        {"id": user_id, "condominium_id": condo_id},
        {"_id": 0, "id": 1, "full_name": 1, "email": 1, "roles": 1, "apartment": 1, "role_data": 1, "created_at": 1}
    )
    if not user:
        raise HTTPException(status_code=404, detail="Residente no encontrado")

    apt = user.get("apartment") or user.get("role_data", {}).get("apartment_number", "")

    # Get charges (payment_records with amount_due > 0)
    charges = []
    payments_applied = []
    total_due = 0.0
    total_paid = 0.0

    if apt:
        records = await db.payment_records.find(
            {"condominium_id": condo_id, "unit_id": apt}, {"_id": 0}
        ).sort("created_at", -1).to_list(500)

        for r in records:
            due = r.get("amount_due", 0)
            paid = r.get("amount_paid", 0)
            total_due += due
            total_paid += paid

            charges.append({
                "id": r.get("id", ""),
                "date": r.get("created_at", ""),
                "period": r.get("period", ""),
                "type": r.get("charge_type_name", "Cargo"),
                "amount_due": round(due, 2),
                "amount_paid": round(paid, 2),
                "status": r.get("status", "pending"),
                "payment_method": r.get("payment_method", ""),
                "paid_at": r.get("paid_at", ""),
            })

        # Get payment requests for this unit
        pay_requests = await db.payment_requests.find(
            {"condominium_id": condo_id, "unit_id": apt}, {"_id": 0}
        ).sort("created_at", -1).to_list(100)
        for pr in pay_requests:
            payments_applied.append({
                "id": pr.get("id", ""),
                "date": pr.get("created_at", ""),
                "amount": round(pr.get("amount", 0), 2),
                "method": pr.get("payment_method", ""),
                "reference": pr.get("reference", ""),
                "status": pr.get("status", ""),
                "notes": pr.get("notes", ""),
            })

    balance = round(total_due - total_paid, 2)
    fin_status = "al_dia" if balance == 0 else ("atrasado" if balance > 0 else "adelantado")

    return {
        "user": {
            "id": user["id"],
            "full_name": user.get("full_name", ""),
            "email": user.get("email", ""),
            "roles": user.get("roles", []),
            "created_at": user.get("created_at", ""),
        },
        "unit": apt or None,
        "charges": charges,
        "payments": payments_applied,
        "total_due": round(total_due, 2),
        "total_paid": round(total_paid, 2),
        "balance": balance,
        "status": fin_status,
    }


@router.get("/finanzas/resident/{user_id}/export")
async def export_resident_statement(
    user_id: str,
    format: str = Query("pdf", regex="^(pdf|csv)$"),
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Export individual resident financial statement as PDF or CSV."""
    condo_id = current_user.get("condominium_id")
    detail = await get_resident_account_detail(user_id, current_user)

    condo = await db.condominiums.find_one({"id": condo_id}, {"name": 1, "_id": 0})
    condo_name = condo.get("name", "Condominio") if condo else "Condominio"
    report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    if format == "csv":
        return _build_resident_csv(detail, condo_name, report_date)
    else:
        return _build_resident_pdf(detail, condo_name, report_date)


def _build_resident_csv(detail, condo_name, report_date):
    output = io.StringIO()
    u = detail["user"]
    output.write(f"Estado de Cuenta - {condo_name}\n")
    output.write(f"Residente: {u['full_name']}\n")
    output.write(f"Email: {u['email']}\n")
    output.write(f"Unidad: {detail['unit'] or 'Sin asignar'}\n")
    output.write(f"Generado: {report_date}\n")
    output.write(f"Total Cobrado: {detail['total_due']}\n")
    output.write(f"Total Pagado: {detail['total_paid']}\n")
    output.write(f"Balance: {detail['balance']}\n")
    sl = {"al_dia": "Al dia", "atrasado": "Atrasado", "adelantado": "Adelantado"}
    output.write(f"Estado: {sl.get(detail['status'], detail['status'])}\n\n")
    output.write("CARGOS\n")
    output.write("Fecha,Periodo,Tipo,Monto Cobrado,Monto Pagado,Estado\n")
    ss = {"paid": "Pagado", "pending": "Pendiente", "overdue": "Vencido", "partial": "Parcial"}
    for c in detail["charges"]:
        output.write(f"{c['date'][:10]},{c['period']},{c['type']},{c['amount_due']},{c['amount_paid']},{ss.get(c['status'], c['status'])}\n")
    if detail["payments"]:
        output.write("\nCOMPROBANTES DE PAGO\n")
        output.write("Fecha,Monto,Metodo,Referencia,Estado\n")
        ps = {"pending": "Pendiente", "approved": "Aprobado", "rejected": "Rechazado"}
        for p in detail["payments"]:
            output.write(f"{p['date'][:10]},{p['amount']},{p['method']},{p['reference']},{ps.get(p['status'], p['status'])}\n")
    csv_bytes = output.getvalue().encode("utf-8-sig")
    safe_name = u["full_name"].replace(" ", "_")[:30]
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="estado_cuenta_{safe_name}.csv"'},
    )


def _build_resident_pdf(detail, condo_name, report_date):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=16, spaceAfter=6)
    subtitle = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=10, textColor=colors.grey, spaceAfter=4)
    section = ParagraphStyle("Sec", parent=styles["Heading2"], fontSize=12, spaceAfter=6, spaceBefore=14)

    u = detail["user"]
    sl = {"al_dia": "Al dia", "atrasado": "Atrasado", "adelantado": "Adelantado"}
    elements = []

    elements.append(Paragraph(f"Estado de Cuenta", title_style))
    elements.append(Paragraph(f"{condo_name} - {report_date}", subtitle))
    elements.append(Spacer(1, 8))

    # Resident info
    info_data = [
        ["Residente:", u["full_name"], "Email:", u["email"]],
        ["Unidad:", detail["unit"] or "Sin asignar", "Estado:", sl.get(detail["status"], detail["status"])],
        ["Total Cobrado:", f"${detail['total_due']:,.2f}", "Total Pagado:", f"${detail['total_paid']:,.2f}"],
        ["Balance:", f"${detail['balance']:,.2f}", "", ""],
    ]
    info_tbl = Table(info_data, colWidths=[90, 180, 90, 180])
    info_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_tbl)
    elements.append(Spacer(1, 12))

    # Charges table
    ss = {"paid": "Pagado", "pending": "Pendiente", "overdue": "Vencido", "partial": "Parcial"}
    if detail["charges"]:
        elements.append(Paragraph("Cargos", section))
        ch_data = [["Fecha", "Periodo", "Tipo", "Cobrado", "Pagado", "Estado"]]
        for c in detail["charges"]:
            ch_data.append([
                c["date"][:10], c["period"], c["type"],
                f"${c['amount_due']:,.2f}", f"${c['amount_paid']:,.2f}",
                ss.get(c["status"], c["status"]),
            ])
        ch_tbl = Table(ch_data, colWidths=[70, 60, 120, 75, 75, 65])
        ch_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.25)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ALIGN", (3, 0), (4, -1), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.Color(0.97, 0.97, 0.97), colors.white]),
        ]))
        elements.append(ch_tbl)

    # Payment requests
    if detail["payments"]:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Comprobantes de Pago", section))
        ps = {"pending": "Pendiente", "approved": "Aprobado", "rejected": "Rechazado"}
        p_data = [["Fecha", "Monto", "Metodo", "Referencia", "Estado"]]
        for p in detail["payments"]:
            p_data.append([
                p["date"][:10], f"${p['amount']:,.2f}", p["method"],
                p["reference"][:20] if p["reference"] else "-", ps.get(p["status"], p["status"]),
            ])
        p_tbl = Table(p_data, colWidths=[70, 80, 100, 120, 80])
        p_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.15, 0.3, 0.2)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(p_tbl)

    doc.build(elements)
    buf.seek(0)
    safe_name = u["full_name"].replace(" ", "_")[:30]
    return Response(
        content=buf.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="estado_cuenta_{safe_name}.pdf"'},
    )


@router.get("/finanzas/report")
async def generate_financial_report(
    format: str = Query("pdf", regex="^(pdf|csv)$"),
    period: Optional[str] = Query(None, regex=r"^\d{4}-(0[1-9]|1[0-2])$"),
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Generate a financial report as PDF or CSV."""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="No condominium associated")

    # Get condominium name
    condo = await db.condominiums.find_one({"id": condo_id}, {"name": 1, "_id": 0})
    condo_name = condo.get("name", "Condominio") if condo else "Condominio"

    # Build query
    rec_query = {"condominium_id": condo_id}
    if period:
        rec_query["period"] = period

    # Aggregate per unit
    pipeline = [
        {"$match": rec_query},
        {"$group": {
            "_id": "$unit_id",
            "total_due": {"$sum": "$amount_due"},
            "total_paid": {"$sum": "$amount_paid"},
        }},
        {"$sort": {"_id": 1}},
    ]
    unit_aggs = await db.payment_records.aggregate(pipeline).to_list(5000)

    # Get account statuses
    accounts_map = {}
    async for acc in db.unit_accounts.find({"condominium_id": condo_id}, {"_id": 0}):
        accounts_map[acc["unit_id"]] = acc

    rows = []
    total_due = 0.0
    total_paid = 0.0
    total_overdue = 0.0
    total_credit = 0.0

    for u in unit_aggs:
        uid = u["_id"]
        due = round(u["total_due"], 2)
        paid = round(u["total_paid"], 2)
        bal = round(due - paid, 2)
        acct = accounts_map.get(uid, {})
        status = acct.get("status", "al_dia" if bal == 0 else ("atrasado" if bal > 0 else "adelantado"))

        total_due += due
        total_paid += paid
        if bal > 0:
            total_overdue += bal
        elif bal < 0:
            total_credit += abs(bal)

        rows.append({
            "unit_id": uid,
            "total_due": due,
            "total_paid": paid,
            "balance": bal,
            "status": status,
        })

    report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    period_label = period if period else "Todos los períodos"

    if format == "csv":
        return _build_csv_report(rows, total_due, total_paid, total_overdue, total_credit, condo_name, period_label, report_date)
    else:
        return _build_pdf_report(rows, total_due, total_paid, total_overdue, total_credit, condo_name, period_label, report_date)


def _build_csv_report(rows, total_due, total_paid, total_overdue, total_credit, condo_name, period_label, report_date):
    """Build a CSV financial report."""
    output = io.StringIO()
    output.write(f"Reporte Financiero - {condo_name}\n")
    output.write(f"Período: {period_label}\n")
    output.write(f"Generado: {report_date}\n")
    output.write(f"Total Cobrado: {total_due}\n")
    output.write(f"Total Pagado: {total_paid}\n")
    output.write(f"Total Pendiente: {total_overdue}\n")
    output.write(f"Total Crédito: {total_credit}\n")
    output.write("\n")
    output.write("Unidad,Total Cobrado,Total Pagado,Balance,Estado\n")
    status_labels = {"al_dia": "Al día", "atrasado": "Atrasado", "adelantado": "Adelantado"}
    for r in rows:
        output.write(f"{r['unit_id']},{r['total_due']},{r['total_paid']},{r['balance']},{status_labels.get(r['status'], r['status'])}\n")

    csv_bytes = output.getvalue().encode("utf-8-sig")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="reporte_financiero_{period_label}.csv"'},
    )


def _build_pdf_report(rows, total_due, total_paid, total_overdue, total_credit, condo_name, period_label, report_date):
    """Build a PDF financial report using ReportLab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=16, spaceAfter=4)
    elements.append(Paragraph(f"Reporte Financiero", title_style))
    elements.append(Paragraph(f"{condo_name}", styles["Heading2"]))
    elements.append(Spacer(1, 8))

    # Meta
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    elements.append(Paragraph(f"Período: {period_label} | Generado: {report_date}", meta_style))
    elements.append(Spacer(1, 16))

    # Summary table
    status_labels = {"al_dia": "Al día", "atrasado": "Atrasado", "adelantado": "Adelantado"}
    summary_data = [
        ["Total Cobrado", f"${total_due:,.2f}"],
        ["Total Pagado", f"${total_paid:,.2f}"],
        ["Total Pendiente", f"${total_overdue:,.2f}"],
        ["Total Crédito (a favor)", f"${total_credit:,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[2.5 * inch, 2 * inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f0f0")),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # Units table
    elements.append(Paragraph("Detalle por Unidad", styles["Heading3"]))
    elements.append(Spacer(1, 8))

    header = ["Unidad", "Cobrado", "Pagado", "Balance", "Estado"]
    data = [header]
    for r in rows:
        bal_str = f"${r['balance']:,.2f}"
        data.append([
            r["unit_id"],
            f"${r['total_due']:,.2f}",
            f"${r['total_paid']:,.2f}",
            bal_str,
            status_labels.get(r["status"], r["status"]),
        ])

    col_widths = [1.5 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("ALIGN", (1, 1), (-2, -1), "RIGHT"),
    ]

    # Color-code rows by status
    for i, r in enumerate(rows, start=1):
        if r["status"] == "atrasado":
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#fff0f0")))
        elif r["status"] == "adelantado":
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f0f8ff")))
        else:
            if i % 2 == 0:
                style_cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f8f8f8")))

    t.setStyle(TableStyle(style_cmds))
    elements.append(t)

    doc.build(elements)
    pdf_bytes = buf.getvalue()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="reporte_financiero_{period_label}.pdf"'},
    )




