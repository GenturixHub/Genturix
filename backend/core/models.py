"""GENTURIX Core — Pydantic Models"""
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import List, Optional, Dict, Any
from .imports import *
from .enums import *

# ==================== MODELS ====================
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    roles: List[RoleEnum] = [RoleEnum.RESIDENTE]
    condominium_id: Optional[str] = None  # Multi-tenant support

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    roles: List[str]
    is_active: bool
    status: str = "active"  # active, blocked, suspended
    created_at: str
    condominium_id: Optional[str] = None  # Multi-tenant support
    password_reset_required: bool = False  # True if user needs to change password
    apartment: Optional[str] = None  # Unit number (e.g., A-102)
    role_data: Optional[dict] = None  # Additional role-specific data

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None  # DEPRECATED: Now sent as httpOnly cookie
    token_type: str = "bearer"
    user: UserResponse
    password_reset_required: bool = False  # Flag for frontend to show password change dialog

class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None  # Optional - can come from httpOnly cookie instead

# Password Change Model
class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password meets security requirements"""
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v

# Profile Models
class ProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    roles: List[str]
    is_active: bool
    created_at: str
    condominium_id: Optional[str] = None
    condominium_name: Optional[str] = None
    phone: Optional[str] = None
    profile_photo: Optional[str] = None
    public_description: Optional[str] = None
    role_data: Optional[Dict[str, Any]] = None
    language: str = "es"  # User's preferred language

class PublicProfileResponse(BaseModel):
    """Public profile visible to other users in same condominium"""
    id: str
    full_name: str
    roles: List[str]
    profile_photo: Optional[str] = None
    public_description: Optional[str] = None
    condominium_name: Optional[str] = None
    # Only show phone if user opted in
    phone: Optional[str] = None

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    profile_photo: Optional[str] = None
    public_description: Optional[str] = None

# Language Model
class LanguageUpdate(BaseModel):
    language: str = Field(..., pattern="^(es|en)$", description="Language code: 'es' or 'en'")

# Security Module Models
class PanicType(str, Enum):
    MEDICAL_EMERGENCY = "emergencia_medica"
    SUSPICIOUS_ACTIVITY = "actividad_sospechosa"
    GENERAL_EMERGENCY = "emergencia_general"

class PanicEventCreate(BaseModel):
    panic_type: PanicType
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None

class AccessLogCreate(BaseModel):
    person_name: str
    access_type: str  # entry, exit
    location: str
    notes: Optional[str] = None

class PanicResolveRequest(BaseModel):
    notes: Optional[str] = None

# HR Module Models
class GuardCreate(BaseModel):
    user_id: str
    badge_number: str
    phone: str
    emergency_contact: str
    hire_date: str
    hourly_rate: float

class GuardUpdate(BaseModel):
    badge_number: Optional[str] = None
    phone: Optional[str] = None
    emergency_contact: Optional[str] = None
    hourly_rate: Optional[float] = None
    is_active: Optional[bool] = None

class ShiftCreate(BaseModel):
    guard_id: str
    start_time: str
    end_time: str
    location: str
    notes: Optional[str] = None

class ShiftUpdate(BaseModel):
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None  # scheduled, in_progress, completed, cancelled

class ClockRequest(BaseModel):
    type: str  # "IN" or "OUT"

class AbsenceCreate(BaseModel):
    reason: str
    type: str  # vacaciones, permiso_medico, personal, otro
    start_date: str
    end_date: str
    notes: Optional[str] = None

class AbsenceAction(BaseModel):
    action: str  # approve, reject
    admin_notes: Optional[str] = None

# Performance Evaluation Models
class EvaluationCategory(BaseModel):
    discipline: int = Field(..., ge=1, le=5)
    punctuality: int = Field(..., ge=1, le=5)
    performance: int = Field(..., ge=1, le=5)
    communication: int = Field(..., ge=1, le=5)

class EvaluationCreate(BaseModel):
    employee_id: str
    categories: EvaluationCategory
    comments: Optional[str] = None

class EvaluationUpdate(BaseModel):
    categories: Optional[EvaluationCategory] = None
    comments: Optional[str] = None

# Recruitment Models
class CandidateCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    position: str  # Guarda, Supervisor
    experience_years: int = 0
    notes: Optional[str] = None
    documents: Optional[List[str]] = None  # URLs to documents

class CandidateUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    position: Optional[str] = None
    experience_years: Optional[int] = None
    notes: Optional[str] = None
    status: Optional[str] = None  # applied, interview, hired, rejected

class HireCandidate(BaseModel):
    badge_number: str
    hourly_rate: float
    password: str = Field(..., min_length=8)

# Condominium Deletion Model (Super Admin only)
class CondominiumDeleteRequest(BaseModel):
    password: str = Field(..., min_length=1, description="Super Admin password for verification")

# NOTE: CreateUserByAdmin and CreateEmployeeByHR models moved to modules/users/models.py
# Imported at top of file from modules.users.models

# School Module Models
class CourseCreate(BaseModel):
    title: str
    description: str
    duration_hours: int
    instructor: str
    category: str

class EnrollmentCreate(BaseModel):
    course_id: str
    student_id: str

class LessonProgressUpdate(BaseModel):
    course_id: str
    lesson_id: str
    completed: bool

# Payments Module Models
class PaymentPackage(BaseModel):
    package_id: str
    origin_url: str

class CheckoutStatusRequest(BaseModel):
    session_id: str

# ==================== VISITOR PRE-REGISTRATION MODELS ====================
class VisitTypeEnum(str, Enum):
    FAMILIAR = "familiar"
    DELIVERY = "delivery"
    SERVICE = "service"
    FRIEND = "friend"
    OTHER = "other"

class VisitorStatusEnum(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    ENTRY_REGISTERED = "entry_registered"
    EXIT_REGISTERED = "exit_registered"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class AuthorizationTypeEnum(str, Enum):
    TEMPORARY = "temporary"      # Single date or date range
    PERMANENT = "permanent"      # Always allowed
    RECURRING = "recurring"      # Specific days of week
    EXTENDED = "extended"        # Date range + time windows

class AuthorizationColorEnum(str, Enum):
    GREEN = "green"       # Permanent visitors
    BLUE = "blue"         # Recurring visitors
    YELLOW = "yellow"     # Temporary visitors
    PURPLE = "purple"     # Extended visitors
    GRAY = "gray"         # Expired/Inactive

class AuthorizationStatusEnum(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"

# New model for advanced visitor authorizations
class VisitorAuthorizationCreate(BaseModel):
    visitor_name: str = Field(..., min_length=2, max_length=100)
    identification_number: Optional[str] = None
    vehicle_plate: Optional[str] = None
    authorization_type: AuthorizationTypeEnum = AuthorizationTypeEnum.TEMPORARY
    valid_from: Optional[str] = None  # YYYY-MM-DD
    valid_to: Optional[str] = None    # YYYY-MM-DD
    allowed_days: Optional[List[str]] = None  # ["Lunes", "Martes", etc.]
    allowed_hours_from: Optional[str] = None  # HH:MM
    allowed_hours_to: Optional[str] = None    # HH:MM
    notes: Optional[str] = None
    # Visitor type fields (Delivery, Maintenance, Technical, Cleaning, Other)
    visitor_type: Optional[str] = "visitor"
    company: Optional[str] = None
    service_type: Optional[str] = None

class VisitorAuthorizationUpdate(BaseModel):
    visitor_name: Optional[str] = None
    identification_number: Optional[str] = None
    vehicle_plate: Optional[str] = None
    authorization_type: Optional[AuthorizationTypeEnum] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    allowed_days: Optional[List[str]] = None
    allowed_hours_from: Optional[str] = None
    allowed_hours_to: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    # Visitor type fields
    visitor_type: Optional[str] = None
    company: Optional[str] = None
    service_type: Optional[str] = None

# Fast Check-in by Guard
class FastCheckInRequest(BaseModel):
    authorization_id: Optional[str] = None  # If pre-authorized
    visitor_name: Optional[str] = None      # Manual entry if not authorized
    identification_number: Optional[str] = None
    vehicle_plate: Optional[str] = None
    destination: Optional[str] = None       # Apartment/House visiting
    notes: Optional[str] = None
    # New fields for visitor types (Delivery, Maintenance, etc.)
    visitor_type: Optional[str] = "visitor"  # visitor, delivery, maintenance, technical, cleaning, other
    company: Optional[str] = None            # Company name for delivery/maintenance/technical/cleaning
    service_type: Optional[str] = None       # Type of service (package, food, repair, etc.)
    authorized_by: Optional[str] = None      # Who authorized: resident, admin, guard
    estimated_time: Optional[str] = None     # Estimated time for cleaning

# Check-out by Guard  
class FastCheckOutRequest(BaseModel):
    notes: Optional[str] = None

class VisitorPreRegistration(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    national_id: Optional[str] = None  # Cedula
    vehicle_plate: Optional[str] = None
    visit_type: VisitTypeEnum = VisitTypeEnum.FRIEND
    expected_date: str  # ISO format date
    expected_time: Optional[str] = None
    notes: Optional[str] = None

class VisitorEntry(BaseModel):
    visitor_id: str
    notes: Optional[str] = None

class VisitorExit(BaseModel):
    visitor_id: str
    notes: Optional[str] = None

# ==================== DEVELOPER PROFILE MODEL ====================
class DeveloperProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=150)
    bio: Optional[str] = Field(None, max_length=2000)
    photo_url: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = Field(None, max_length=500)
    linkedin: Optional[str] = Field(None, max_length=500)
    github: Optional[str] = Field(None, max_length=500)

# ==================== RESERVATIONS MODELS ====================
class AreaTypeEnum(str, Enum):
    POOL = "pool"
    GYM = "gym"
    TENNIS = "tennis"
    BBQ = "bbq"
    SALON = "salon"
    CINEMA = "cinema"
    PLAYGROUND = "playground"
    OTHER = "other"

# NEW: Reservation behavior types (Phase 1)
class ReservationBehaviorEnum(str, Enum):
    EXCLUSIVE = "exclusive"      # 1 reserva bloquea el área (Rancho, Salón) - DEFAULT/LEGACY
    CAPACITY = "capacity"        # Múltiples reservas hasta max_capacity (Gimnasio, Piscina)
    SLOT_BASED = "slot_based"    # Slots fijos, 1 reserva = 1 slot (Canchas)
    FREE_ACCESS = "free_access"  # No se permiten reservas (áreas abiertas)

class ReservationModeEnum(str, Enum):
    BY_HOUR = "por_hora"      # Gym: 1 hour slots
    BLOCK = "bloque"          # Ranch: Full block reservation
    FLEXIBLE = "flexible"     # Pool: Configurable duration

class ReservationStatusEnum(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class AreaCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    area_type: AreaTypeEnum = AreaTypeEnum.OTHER
    capacity: int = Field(..., gt=0)
    description: Optional[str] = None
    rules: Optional[str] = None
    available_from: str = "06:00"  # Opening time HH:MM
    available_until: str = "22:00"  # Closing time HH:MM
    requires_approval: bool = False
    reservation_mode: str = "flexible"  # por_hora | bloque | flexible
    min_duration_hours: int = 1  # Minimum reservation duration
    max_duration_hours: int = 4  # Maximum reservation duration (renamed from max_hours_per_reservation)
    max_reservations_per_day: int = 10
    slot_duration_minutes: int = 60  # Duration of each slot (for visual display)
    allowed_days: List[str] = Field(default=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
    is_active: bool = True
    condominium_id: Optional[str] = None  # For SuperAdmin to specify condo
    # NEW: Phase 1 fields with backward-compatible defaults
    reservation_behavior: Optional[str] = "exclusive"  # exclusive | capacity | slot_based | free_access
    max_capacity_per_slot: Optional[int] = None  # For CAPACITY type: max people per time slot
    max_reservations_per_user_per_day: Optional[int] = None  # Limit per user per day

class AreaUpdate(BaseModel):
    name: Optional[str] = None
    area_type: Optional[AreaTypeEnum] = None
    capacity: Optional[int] = None
    description: Optional[str] = None
    rules: Optional[str] = None
    available_from: Optional[str] = None
    available_until: Optional[str] = None
    requires_approval: Optional[bool] = None
    reservation_mode: Optional[str] = None
    min_duration_hours: Optional[int] = None
    max_duration_hours: Optional[int] = None
    max_reservations_per_day: Optional[int] = None
    slot_duration_minutes: Optional[int] = None
    allowed_days: Optional[List[str]] = None
    is_active: Optional[bool] = None
    # NEW: Phase 1 fields
    reservation_behavior: Optional[str] = None
    max_capacity_per_slot: Optional[int] = None
    max_reservations_per_user_per_day: Optional[int] = None

class ReservationCreate(BaseModel):
    area_id: str
    date: str  # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    purpose: Optional[str] = None
    guests_count: int = 1

class ReservationUpdate(BaseModel):
    status: ReservationStatusEnum
    admin_notes: Optional[str] = None

# ==================== MULTI-TENANT MODELS ====================
# Configuración de módulos habilitados por condominio
class ModuleConfig(BaseModel):
    enabled: bool = False
    settings: Dict[str, Any] = {}

class CondominiumModules(BaseModel):
    security: ModuleConfig = ModuleConfig(enabled=True)
    hr: ModuleConfig = ModuleConfig(enabled=True)
    school: ModuleConfig = ModuleConfig(enabled=False)
    payments: ModuleConfig = ModuleConfig(enabled=True)
    audit: ModuleConfig = ModuleConfig(enabled=True)
    reservations: ModuleConfig = ModuleConfig(enabled=False)
    access_control: ModuleConfig = ModuleConfig(enabled=True)
    messaging: ModuleConfig = ModuleConfig(enabled=False)

class CondominiumCreate(BaseModel):
    """Model for creating PRODUCTION condominiums only"""
    name: str = Field(..., min_length=2, max_length=100)
    address: str = Field(..., min_length=5)
    contact_email: EmailStr
    contact_phone: str
    max_users: int = Field(default=100, ge=1)
    modules: Optional[CondominiumModules] = None
    # Billing fields for production - ENHANCED
    initial_units: int = Field(default=10, ge=1, le=10000, description="Number of billable seats")
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|yearly)$")
    billing_provider: str = Field(default="stripe", pattern="^(stripe|sinpe|ticopay|manual)$")
    billing_email: Optional[EmailStr] = None  # Separate email for invoices
    # Legacy field - kept for backward compatibility
    paid_seats: Optional[int] = None  # Will default to initial_units if not provided

class DemoCondominiumCreate(BaseModel):
    """Model for creating DEMO condominiums - simplified, no billing"""
    name: str = Field(..., min_length=2, max_length=100)
    address: str = Field(default="Demo Address")
    contact_email: EmailStr
    contact_phone: str = Field(default="")
    # Demo always has fixed 10 seats, no billing

class CondominiumUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    max_users: Optional[int] = None
    modules: Optional[CondominiumModules] = None
    is_active: Optional[bool] = None
    paid_seats: Optional[int] = None
    environment: Optional[str] = Field(default=None, pattern="^(demo|production)$")

class CondominiumResponse(BaseModel):
    id: str
    name: str
    address: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    max_users: int = 100
    current_users: int = 0
    modules: Dict[str, Any] = {}
    is_active: bool = True
    created_at: str
    price_per_user: float = 1.0  # $1 USD per user per month (legacy)
    status: str = "active"  # active, demo, suspended
    is_demo: bool = False
    discount_percent: float = 0.0
    plan: str = "basic"
    # Environment: "demo" or "production"
    environment: str = "production"
    # SaaS Billing Fields - ENHANCED
    billing_model: str = "per_seat"
    paid_seats: int = 10  # How many users are paid for
    price_per_seat: float = 1.50  # Dynamic price per seat
    billing_cycle: str = "monthly"  # monthly or yearly
    billing_provider: str = "stripe"  # stripe, sinpe, ticopay, manual
    billing_email: Optional[str] = None  # Email for invoices
    billing_status: str = "pending_payment"  # pending_payment, active, past_due, cancelled, trialing
    next_invoice_amount: float = 0.0  # Calculated monthly/yearly total
    next_billing_date: Optional[str] = None
    billing_started_at: Optional[str] = None
    yearly_discount_percent: float = 10.0  # Default 10% discount for yearly
    grace_period_days: int = 5  # Days after due date before suspension
    # Computed fields
    active_users: int = 0  # Real count of active users (excluding SuperAdmin)
    remaining_seats: int = 10  # paid_seats - active_users
    # Legacy Stripe fields (for future integration)
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    billing_period_end: Optional[str] = None

# SaaS Billing Models - Now imported from modules.billing.models
# (BillingStatus, BillingCycle, BillingProvider, BillingEventType, 
#  SeatUpgradeRequestStatus, ConfirmPaymentRequest, ConfirmPaymentResponse,
#  PaymentHistoryResponse, SeatUpgradeRequestModel, SeatUpgradeRequestResponse,
#  SeatUpgradeRequest, SeatUpdateRequest, BillingPreviewRequest, 
#  BillingPreviewResponse, BillingInfoResponse)

# Local alias for backward compatibility
SeatUpgradeRequest = BillingSeatUpgradeRequest

# Push Notification Models
class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str

class PushSubscriptionData(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys
    expirationTime: Optional[str] = None

class PushSubscriptionRequest(BaseModel):
    subscription: PushSubscriptionData

class PushNotificationPayload(BaseModel):
    title: str
    body: str
    icon: Optional[str] = "/logo192.png"
    badge: Optional[str] = "/logo192.png"
    tag: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    requireInteraction: bool = True
    urgency: str = "high"

# ==================== PUSH SUBSCRIPTION DOCUMENT SCHEMA ====================
# Each push_subscription document MUST have:
# - id: str (UUID)
# - user_id: str (REQUIRED - owner of subscription)
# - role: str (REQUIRED - user's primary role at subscription time)
# - condominium_id: str (REQUIRED - tenant scope)
# - endpoint: str (push service URL)
# - keys: { p256dh: str, auth: str }
# - is_active: bool
# - created_at: str (ISO datetime)
# - updated_at: str (ISO datetime)
# ===========================================================================

# ==================== INVITATION & ACCESS REQUEST MODELS ====================
class InvitationUsageLimitEnum(str, Enum):
    SINGLE = "single"           # 1 uso (default)
    UNLIMITED = "unlimited"     # Ilimitado hasta expirar
    FIXED = "fixed"             # Número fijo de usos

class InvitationCreate(BaseModel):
    expiration_days: int = Field(default=7, ge=1, le=365)  # 7, 30, o custom
    expiration_date: Optional[str] = None  # Custom date override (ISO format)
    usage_limit_type: InvitationUsageLimitEnum = InvitationUsageLimitEnum.SINGLE
    max_uses: int = Field(default=1, ge=1, le=1000)  # Only used if usage_limit_type is FIXED
    notes: Optional[str] = None  # Admin notes for this invitation

class InvitationResponse(BaseModel):
    id: str
    token: str
    condominium_id: str
    condominium_name: str
    created_by_id: str
    created_by_name: str
    expires_at: str
    usage_limit_type: str
    max_uses: int
    current_uses: int
    is_active: bool
    is_expired: bool
    notes: Optional[str] = None
    created_at: str
    invite_url: str

class AccessRequestCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    apartment_number: str = Field(..., min_length=1, max_length=50)
    tower_block: Optional[str] = None
    resident_type: str = Field(default="owner")  # owner, tenant
    notes: Optional[str] = None  # Message from requestor

class AccessRequestResponse(BaseModel):
    id: str
    invitation_id: str
    condominium_id: str
    condominium_name: str
    full_name: str
    email: str
    phone: Optional[str] = None
    apartment_number: str
    tower_block: Optional[str] = None
    resident_type: str
    notes: Optional[str] = None
    status: str  # pending_approval, approved, rejected
    status_message: Optional[str] = None  # Rejection reason or welcome message
    created_at: str
    processed_at: Optional[str] = None
    processed_by_id: Optional[str] = None
    processed_by_name: Optional[str] = None

class AccessRequestAction(BaseModel):
    action: str  # approve, reject
    message: Optional[str] = None  # Rejection reason or welcome message
    send_email: bool = True  # Send notification email to requestor

# ==================== CONDOMINIUM SETTINGS MODELS ====================
class WorkingHours(BaseModel):
    start: str = "06:00"
    end: str = "22:00"

class GeneralSettings(BaseModel):
    timezone: str = "America/Mexico_City"
    working_hours: WorkingHours = WorkingHours()
    condominium_name_display: Optional[str] = None  # Override display name

class ReservationSettings(BaseModel):
    enabled: bool = True
    max_active_per_user: int = Field(default=3, ge=1, le=20)
    allow_same_day: bool = True
    approval_required_by_default: bool = False
    min_hours_advance: int = Field(default=1, ge=0, le=72)  # Minimum hours in advance to reserve
    max_days_advance: int = Field(default=30, ge=1, le=365)  # Maximum days in advance to reserve

class VisitSettings(BaseModel):
    allow_resident_preregistration: bool = True
    allow_recurrent_visits: bool = True
    allow_permanent_visits: bool = False
    require_id_photo: bool = False
    max_preregistrations_per_day: int = Field(default=10, ge=1, le=50)

class NotificationSettings(BaseModel):
    panic_sound_enabled: bool = True
    push_enabled: bool = True
    email_notifications_enabled: bool = True

class CondominiumSettingsModel(BaseModel):
    general: GeneralSettings = GeneralSettings()
    reservations: ReservationSettings = ReservationSettings()
    visits: VisitSettings = VisitSettings()
    notifications: NotificationSettings = NotificationSettings()

class CondominiumSettingsUpdate(BaseModel):
    general: Optional[GeneralSettings] = None
    reservations: Optional[ReservationSettings] = None
    visits: Optional[VisitSettings] = None
    notifications: Optional[NotificationSettings] = None

class CondominiumSettingsResponse(BaseModel):
    condominium_id: str
    condominium_name: str
    general: GeneralSettings
    reservations: ReservationSettings
    visits: VisitSettings
    notifications: NotificationSettings
    updated_at: str
    created_at: str

# Helper function to get default settings
def get_default_condominium_settings() -> dict:
    """Get default condominium settings as dict"""
    return {
        "general": GeneralSettings().model_dump(),
        "reservations": ReservationSettings().model_dump(),
        "visits": VisitSettings().model_dump(),
        "notifications": NotificationSettings().model_dump()
    }

