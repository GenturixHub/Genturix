"""
BILLING MODELS MODULE
=====================
Pydantic models and enums for billing domain.
Extracted from server.py without logic changes.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ============== BILLING ENUMS ==============

class BillingStatus(str, Enum):
    PENDING_PAYMENT = "pending_payment"  # Initial state before first payment
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    TRIALING = "trialing"
    SUSPENDED = "suspended"  # NEW: Blocked due to non-payment
    UPGRADE_PENDING = "upgrade_pending"  # NEW: Waiting for upgrade payment


class BillingCycle(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class BillingProvider(str, Enum):
    STRIPE = "stripe"
    SINPE = "sinpe"
    TICOPAY = "ticopay"
    MANUAL = "manual"


class BillingEventType(str, Enum):
    CONDOMINIUM_CREATED = "condominium_created"
    SEATS_UPGRADED = "seats_upgraded"
    SEATS_DOWNGRADED = "seats_downgraded"
    CYCLE_CHANGED = "cycle_changed"
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_FAILED = "payment_failed"
    STATUS_CHANGED = "status_changed"
    PRICE_UPDATED = "price_updated"
    UPGRADE_REQUESTED = "upgrade_requested"  # NEW
    UPGRADE_APPROVED = "upgrade_approved"    # NEW
    UPGRADE_REJECTED = "upgrade_rejected"    # NEW


class SeatUpgradeRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ============== SINPE BILLING MODELS ==============

class ConfirmPaymentRequest(BaseModel):
    """Request to confirm a SINPE/manual payment"""
    amount_paid: float = Field(..., gt=0)
    payment_reference: Optional[str] = None  # SINPE reference number
    notes: Optional[str] = None


class ConfirmPaymentResponse(BaseModel):
    """Response after payment confirmation - supports partial payments"""
    payment_id: str
    condominium_id: str
    amount_paid: float
    invoice_amount: float  # Total due for current cycle
    total_paid_cycle: float  # Total paid in current billing cycle
    balance_due: float  # Remaining balance (invoice_amount - total_paid_cycle)
    previous_status: str
    new_status: str
    next_billing_date: Optional[str] = None  # Only set when fully paid
    is_fully_paid: bool  # True if balance_due <= 0
    message: str


class PaymentHistoryResponse(BaseModel):
    """Payment record in history"""
    id: str
    condominium_id: str
    seats_at_payment: int
    amount_paid: float
    billing_cycle: str
    payment_method: str
    payment_reference: Optional[str] = None
    payment_date: str
    next_billing_date: str
    confirmed_by: str
    created_at: str


class SeatUpgradeRequestModel(BaseModel):
    """Request for more seats"""
    requested_seats: int = Field(..., ge=1, le=10000)
    reason: Optional[str] = None


class SeatUpgradeRequestResponse(BaseModel):
    """Seat upgrade request record"""
    id: str
    condominium_id: str
    condominium_name: str
    current_seats: int
    requested_seats: int
    additional_seats: int
    current_amount: float
    new_amount: float
    difference_amount: float
    status: str
    requested_by: Optional[str] = None
    approved_by: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


# ============== END SINPE BILLING MODELS ==============


class SeatUpgradeRequest(BaseModel):
    additional_seats: int = Field(..., ge=1, le=1000)
    condominium_id: Optional[str] = None  # Required for SuperAdmin to specify which condo


class SeatUpdateRequest(BaseModel):
    """Request to update seat count (up or down)"""
    new_seat_count: int = Field(..., ge=1, le=10000)
    reason: Optional[str] = None


class BillingPreviewRequest(BaseModel):
    """Request for billing preview before creation"""
    initial_units: int = Field(..., ge=1, le=10000)
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|yearly)$")
    condominium_id: Optional[str] = None  # For existing condo price override
    seat_price_override: Optional[float] = Field(default=None, gt=0, le=1000, description="Custom price per seat (optional)")
    yearly_discount_percent: Optional[float] = Field(default=None, ge=0, le=50, description="Custom yearly discount 0-50% (optional)")


class BillingPreviewResponse(BaseModel):
    """Response with calculated billing preview"""
    seats: int
    price_per_seat: float
    billing_cycle: str
    monthly_amount: float
    yearly_amount: float
    yearly_discount_percent: float
    effective_amount: float  # Based on selected cycle
    next_billing_date: str
    currency: str = "USD"


class BillingInfoResponse(BaseModel):
    condominium_id: str
    condominium_name: str
    paid_seats: int
    active_users: int
    remaining_seats: int
    billing_status: str
    stripe_subscription_id: Optional[str] = None
    price_per_seat: float = 1.0
    monthly_cost: float
    billing_period_end: Optional[str] = None
    can_create_users: bool


class SeatUsageResponse(BaseModel):
    """Response for seat usage status"""
    condominium_id: str
    paid_seats: int
    active_users: int
    remaining_seats: int
    usage_percent: float
    can_create_users: bool
    billing_status: str


class SeatReductionValidation(BaseModel):
    """Response for seat reduction validation"""
    can_reduce: bool
    current_seats: int
    active_users: int
    requested_seats: int
    excess_users: int
    message: str
