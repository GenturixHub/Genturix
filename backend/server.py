from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
import jwt
from enum import Enum
from bson import ObjectId
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'default-secret-change-in-production')
JWT_REFRESH_SECRET_KEY = os.environ.get('JWT_REFRESH_SECRET_KEY', 'default-refresh-secret')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', 30))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.environ.get('REFRESH_TOKEN_EXPIRE_MINUTES', 10080))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the main app
app = FastAPI(title="GENTURIX Enterprise Platform", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ==================== ENUMS ====================
class RoleEnum(str, Enum):
    SUPER_ADMIN = "SuperAdmin"
    ADMINISTRADOR = "Administrador"
    SUPERVISOR = "Supervisor"
    HR = "HR"  # Human Resources - manages employees, recruitment, absences
    GUARDA = "Guarda"
    RESIDENTE = "Residente"
    ESTUDIANTE = "Estudiante"

class AuditEventType(str, Enum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    PANIC_BUTTON = "panic_button"
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    PAYMENT_INITIATED = "payment_initiated"
    PAYMENT_COMPLETED = "payment_completed"
    COURSE_ENROLLED = "course_enrolled"
    CERTIFICATE_ISSUED = "certificate_issued"
    SHIFT_CREATED = "shift_created"
    # Super Admin events
    CONDO_CREATED = "condo_created"
    CONDO_UPDATED = "condo_updated"
    CONDO_DEACTIVATED = "condo_deactivated"
    MODULE_TOGGLED = "module_toggled"
    USER_LOCKED = "user_locked"
    USER_UNLOCKED = "user_unlocked"
    DEMO_RESET = "demo_reset"
    PLAN_UPDATED = "plan_updated"
    SHIFT_UPDATED = "shift_updated"
    SHIFT_DELETED = "shift_deleted"
    CLOCK_IN = "clock_in"
    CLOCK_OUT = "clock_out"
    ABSENCE_REQUESTED = "absence_requested"
    ABSENCE_APPROVED = "absence_approved"
    ABSENCE_REJECTED = "absence_rejected"
    # Recruitment events
    CANDIDATE_CREATED = "candidate_created"
    CANDIDATE_UPDATED = "candidate_updated"
    CANDIDATE_HIRED = "candidate_hired"
    CANDIDATE_REJECTED = "candidate_rejected"
    # User management events
    EMPLOYEE_CREATED = "employee_created"
    EMPLOYEE_DEACTIVATED = "employee_deactivated"
    EMPLOYEE_ACTIVATED = "employee_activated"

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
    created_at: str
    condominium_id: Optional[str] = None  # Multi-tenant support

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class RefreshTokenRequest(BaseModel):
    refresh_token: str

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

# User Management Models (for Admin/HR creating users)
class CreateUserByAdmin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    role: str  # Single role: Residente, Guarda, HR, Supervisor
    phone: Optional[str] = None

class CreateEmployeeByHR(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    badge_number: str
    phone: str
    emergency_contact: str
    hourly_rate: float

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
    name: str = Field(..., min_length=2, max_length=100)
    address: str = Field(..., min_length=5)
    contact_email: EmailStr
    contact_phone: str
    max_users: int = Field(default=100, ge=1)
    modules: Optional[CondominiumModules] = None

class CondominiumUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    max_users: Optional[int] = None
    modules: Optional[CondominiumModules] = None
    is_active: Optional[bool] = None

class CondominiumResponse(BaseModel):
    id: str
    name: str
    address: str
    contact_email: str
    contact_phone: str
    max_users: int
    current_users: int
    modules: Dict[str, Any]
    is_active: bool
    created_at: str
    price_per_user: float = 1.0  # $1 USD per user per month
    status: str = "active"  # active, demo, suspended
    is_demo: bool = False
    discount_percent: float = 0.0
    plan: str = "basic"

# ==================== HELPER FUNCTIONS ====================
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, JWT_REFRESH_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def verify_refresh_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_REFRESH_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    user = await db.users.find_one({"id": user_id})
    
    if not user or not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user

def require_role(*allowed_roles):
    async def check_role(current_user = Depends(get_current_user)):
        user_roles = current_user.get("roles", [])
        if not any(role in user_roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return check_role

async def log_audit_event(
    event_type: AuditEventType,
    user_id: Optional[str],
    module: str,
    details: dict,
    ip_address: str = "unknown",
    user_agent: str = "unknown"
):
    audit_log = {
        "id": str(uuid.uuid4()),
        "event_type": event_type.value,
        "user_id": user_id,
        "module": module,
        "details": details,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.audit_logs.insert_one(audit_log)

# ==================== AUTH ROUTES ====================
@api_router.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate, request: Request):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    
    # Validate condominium if provided
    if user_data.condominium_id:
        condo = await db.condominiums.find_one({"id": user_data.condominium_id, "is_active": True})
        if not condo:
            raise HTTPException(status_code=400, detail="Invalid or inactive condominium")
        
        # Check user limit
        current_users = await db.users.count_documents({"condominium_id": user_data.condominium_id, "is_active": True})
        if current_users >= condo.get("max_users", 100):
            raise HTTPException(status_code=400, detail="Condominium user limit reached")
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "hashed_password": hash_password(user_data.password),
        "roles": [role.value for role in user_data.roles],
        "condominium_id": user_data.condominium_id,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    # Update condominium user count
    if user_data.condominium_id:
        await db.condominiums.update_one(
            {"id": user_data.condominium_id},
            {"$inc": {"current_users": 1}}
        )
    
    await log_audit_event(
        AuditEventType.USER_CREATED,
        user_id,
        "auth",
        {"email": user_data.email, "roles": [r.value for r in user_data.roles], "condominium_id": user_data.condominium_id},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return UserResponse(
        id=user_id,
        email=user_data.email,
        full_name=user_data.full_name,
        roles=[role.value for role in user_data.roles],
        is_active=True,
        created_at=user_doc["created_at"],
        condominium_id=user_data.condominium_id
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin, request: Request):
    user = await db.users.find_one({"email": credentials.email})
    
    if not user or not verify_password(credentials.password, user.get("hashed_password", "")):
        await log_audit_event(
            AuditEventType.LOGIN_FAILURE,
            None,
            "auth",
            {"email": credentials.email, "reason": "invalid_credentials"},
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "unknown")
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.get("is_active"):
        raise HTTPException(status_code=403, detail="User account is inactive")
    
    # Include condominium_id in token for tenant-aware requests
    token_data = {
        "sub": user["id"], 
        "email": user["email"], 
        "roles": user["roles"],
        "condominium_id": user.get("condominium_id")
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    await log_audit_event(
        AuditEventType.LOGIN_SUCCESS,
        user["id"],
        "auth",
        {"email": user["email"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            full_name=user["full_name"],
            roles=user["roles"],
            is_active=user["is_active"],
            created_at=user["created_at"],
            condominium_id=user.get("condominium_id")
        )
    )

@api_router.post("/auth/refresh")
async def refresh_token(token_request: RefreshTokenRequest, request: Request):
    payload = verify_refresh_token(token_request.refresh_token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    user = await db.users.find_one({"id": payload["sub"]})
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    token_data = {"sub": user["id"], "email": user["email"], "roles": user["roles"]}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)
    
    await log_audit_event(
        AuditEventType.TOKEN_REFRESH,
        user["id"],
        "auth",
        {},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"access_token": new_access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}

@api_router.post("/auth/logout")
async def logout(request: Request, current_user = Depends(get_current_user)):
    await log_audit_event(
        AuditEventType.LOGOUT,
        current_user["id"],
        "auth",
        {},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    return {"message": "Successfully logged out"}

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        roles=current_user["roles"],
        is_active=current_user["is_active"],
        created_at=current_user["created_at"],
        condominium_id=current_user.get("condominium_id")
    )

# ==================== SECURITY MODULE ====================
@api_router.post("/security/panic")
async def trigger_panic(event: PanicEventCreate, request: Request, current_user = Depends(get_current_user)):
    panic_type_labels = {
        "emergencia_medica": "🚑 Emergencia Médica",
        "actividad_sospechosa": "👁️ Actividad Sospechosa",
        "emergencia_general": "🚨 Emergencia General"
    }
    
    panic_event = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "user_name": current_user["full_name"],
        "user_email": current_user["email"],
        "panic_type": event.panic_type.value,
        "panic_type_label": panic_type_labels.get(event.panic_type.value, "Emergencia"),
        "location": event.location,
        "latitude": event.latitude,
        "longitude": event.longitude,
        "description": event.description,
        "status": "active",
        "notified_guards": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "resolved_at": None,
        "resolved_by": None
    }
    
    await db.panic_events.insert_one(panic_event)
    
    # Notify all active guards - create notifications
    active_guards = await db.guards.find({"is_active": True}, {"_id": 0}).to_list(100)
    for guard in active_guards:
        notification = {
            "id": str(uuid.uuid4()),
            "guard_id": guard["id"],
            "guard_user_id": guard["user_id"],
            "panic_event_id": panic_event["id"],
            "panic_type": event.panic_type.value,
            "panic_type_label": panic_type_labels.get(event.panic_type.value, "Emergencia"),
            "resident_name": current_user["full_name"],
            "location": event.location,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.guard_notifications.insert_one(notification)
        panic_event["notified_guards"].append(guard["id"])
    
    # Update panic event with notified guards
    await db.panic_events.update_one(
        {"id": panic_event["id"]},
        {"$set": {"notified_guards": panic_event["notified_guards"]}}
    )
    
    # Log to audit
    await log_audit_event(
        AuditEventType.PANIC_BUTTON,
        current_user["id"],
        "security",
        {
            "panic_type": event.panic_type.value,
            "location": event.location,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "description": event.description,
            "notified_guards_count": len(active_guards)
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "message": "Alerta enviada exitosamente",
        "event_id": panic_event["id"],
        "panic_type": event.panic_type.value,
        "notified_guards": len(active_guards)
    }

@api_router.get("/security/panic-events")
async def get_panic_events(current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))):
    events = await db.panic_events.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return events

@api_router.put("/security/panic/{event_id}/resolve")
async def resolve_panic(event_id: str, current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))):
    result = await db.panic_events.update_one(
        {"id": event_id},
        {"$set": {"status": "resolved", "resolved_at": datetime.now(timezone.utc).isoformat(), "resolved_by": current_user["id"]}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Panic event resolved"}

@api_router.post("/security/access-log")
async def create_access_log(log: AccessLogCreate, request: Request, current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))):
    access_log = {
        "id": str(uuid.uuid4()),
        "person_name": log.person_name,
        "access_type": log.access_type,
        "location": log.location,
        "notes": log.notes,
        "recorded_by": current_user["id"],
        "recorded_by_name": current_user.get("full_name", "Guard"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await db.access_logs.insert_one(access_log)
    
    # Remove MongoDB _id before returning
    access_log.pop("_id", None)
    
    # Use appropriate audit event type based on access type
    audit_event = AuditEventType.ACCESS_GRANTED if log.access_type == "entry" else AuditEventType.ACCESS_DENIED
    
    await log_audit_event(
        audit_event,
        current_user["id"],
        "access",
        {"person": log.person_name, "type": log.access_type, "location": log.location, "guard": current_user.get("full_name")},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return access_log

@api_router.get("/security/access-logs")
async def get_access_logs(current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))):
    logs = await db.access_logs.find({}, {"_id": 0}).sort("timestamp", -1).to_list(100)
    return logs

# Endpoint for Residents to see their visitor notifications
@api_router.get("/resident/notifications")
async def get_resident_notifications(current_user = Depends(get_current_user)):
    """Get visitor entry/exit notifications for a resident"""
    # Get visitor records created by this resident that have been executed
    visitors = await db.visitors.find(
        {"created_by": current_user["id"], "status": {"$in": ["entry_registered", "exit_registered"]}},
        {"_id": 0}
    ).sort("updated_at", -1).to_list(20)
    
    return visitors

# ==================== VISITOR PRE-REGISTRATION MODULE ====================
# Flow: Resident creates → Guard executes → Admin audits

@api_router.post("/visitors/pre-register")
async def create_visitor_preregistration(
    visitor: VisitorPreRegistration,
    request: Request,
    current_user = Depends(get_current_user)
):
    """Resident pre-registers a visitor - creates PENDING record"""
    visitor_id = str(uuid.uuid4())
    
    visitor_doc = {
        "id": visitor_id,
        "full_name": visitor.full_name,
        "national_id": visitor.national_id,
        "vehicle_plate": visitor.vehicle_plate,
        "visit_type": visitor.visit_type.value,
        "expected_date": visitor.expected_date,
        "expected_time": visitor.expected_time,
        "notes": visitor.notes,
        "status": VisitorStatusEnum.PENDING.value,
        "created_by": current_user["id"],
        "created_by_name": current_user.get("full_name", "Resident"),
        "condominium_id": current_user.get("condominium_id"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "entry_at": None,
        "entry_by": None,
        "entry_by_name": None,
        "exit_at": None,
        "exit_by": None,
        "exit_by_name": None
    }
    
    await db.visitors.insert_one(visitor_doc)
    
    await log_audit_event(
        AuditEventType.ACCESS_GRANTED,
        current_user["id"],
        "visitors",
        {"action": "pre_registration", "visitor": visitor.full_name, "expected_date": visitor.expected_date, "resident": current_user.get("full_name")},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"id": visitor_id, "message": "Visitor pre-registered successfully", "status": "pending"}

@api_router.get("/visitors/my-visitors")
async def get_my_visitors(current_user = Depends(get_current_user)):
    """Get visitors pre-registered by the current resident"""
    visitors = await db.visitors.find(
        {"created_by": current_user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return visitors

@api_router.delete("/visitors/{visitor_id}")
async def cancel_visitor_preregistration(
    visitor_id: str,
    current_user = Depends(get_current_user)
):
    """Resident cancels their own visitor pre-registration"""
    result = await db.visitors.update_one(
        {"id": visitor_id, "created_by": current_user["id"], "status": "pending"},
        {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Visitor not found or cannot be cancelled")
    
    return {"message": "Visitor pre-registration cancelled"}

@api_router.get("/visitors/pending")
async def get_pending_visitors(
    search: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """Guard gets list of pending visitors expected today or with matching search"""
    query = {"status": {"$in": ["pending", "entry_registered"]}}
    
    visitors = await db.visitors.find(query, {"_id": 0}).sort("expected_date", -1).to_list(100)
    
    # Filter by search term if provided
    if search:
        search_lower = search.lower()
        visitors = [
            v for v in visitors 
            if search_lower in v.get("full_name", "").lower() or
               search_lower in (v.get("vehicle_plate") or "").lower() or
               search_lower in (v.get("created_by_name") or "").lower() or
               search_lower in (v.get("national_id") or "").lower()
        ]
    
    return visitors

@api_router.post("/visitors/{visitor_id}/entry")
async def register_visitor_entry(
    visitor_id: str,
    entry_data: VisitorEntry,
    request: Request,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """Guard registers visitor ENTRY"""
    visitor = await db.visitors.find_one({"id": visitor_id})
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    
    if visitor.get("status") not in ["pending", "approved"]:
        raise HTTPException(status_code=400, detail=f"Cannot register entry. Current status: {visitor.get('status')}")
    
    entry_time = datetime.now(timezone.utc).isoformat()
    
    await db.visitors.update_one(
        {"id": visitor_id},
        {"$set": {
            "status": "entry_registered",
            "entry_at": entry_time,
            "entry_by": current_user["id"],
            "entry_by_name": current_user.get("full_name", "Guard"),
            "entry_notes": entry_data.notes,
            "updated_at": entry_time
        }}
    )
    
    await log_audit_event(
        AuditEventType.ACCESS_GRANTED,
        current_user["id"],
        "visitors",
        {
            "action": "entry_registered",
            "visitor": visitor.get("full_name"),
            "visitor_id": visitor_id,
            "resident": visitor.get("created_by_name"),
            "guard": current_user.get("full_name")
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "Visitor entry registered", "entry_at": entry_time}

@api_router.post("/visitors/{visitor_id}/exit")
async def register_visitor_exit(
    visitor_id: str,
    exit_data: VisitorExit,
    request: Request,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """Guard registers visitor EXIT"""
    visitor = await db.visitors.find_one({"id": visitor_id})
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    
    if visitor.get("status") != "entry_registered":
        raise HTTPException(status_code=400, detail=f"Cannot register exit. Current status: {visitor.get('status')}")
    
    exit_time = datetime.now(timezone.utc).isoformat()
    
    await db.visitors.update_one(
        {"id": visitor_id},
        {"$set": {
            "status": "exit_registered",
            "exit_at": exit_time,
            "exit_by": current_user["id"],
            "exit_by_name": current_user.get("full_name", "Guard"),
            "exit_notes": exit_data.notes,
            "updated_at": exit_time
        }}
    )
    
    await log_audit_event(
        AuditEventType.ACCESS_DENIED,
        current_user["id"],
        "visitors",
        {
            "action": "exit_registered",
            "visitor": visitor.get("full_name"),
            "visitor_id": visitor_id,
            "resident": visitor.get("created_by_name"),
            "guard": current_user.get("full_name"),
            "duration_minutes": None  # Could calculate from entry_at
        },
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "Visitor exit registered", "exit_at": exit_time}

@api_router.get("/visitors/all")
async def get_all_visitors(
    status: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor"))
):
    """Admin gets all visitor records for audit"""
    query = {}
    if status:
        query["status"] = status
    
    visitors = await db.visitors.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return visitors

# Endpoint for Guards to write to their logbook
@api_router.get("/security/logbook")
async def get_guard_logbook(current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))):
    """Get logbook entries for guards"""
    # Get security-related audit logs and access logs as logbook
    logs = await db.access_logs.find({}, {"_id": 0}).sort("timestamp", -1).to_list(50)
    
    # Format as logbook entries
    logbook_entries = []
    for log in logs:
        logbook_entries.append({
            "id": log.get("id"),
            "event_type": log.get("access_type", "entry"),
            "timestamp": log.get("timestamp"),
            "details": {
                "person": log.get("person_name"),
                "notes": log.get("notes"),
                "location": log.get("location")
            }
        })
    
    return logbook_entries

@api_router.get("/security/active-guards")
async def get_active_guards(current_user = Depends(require_role("Administrador", "Supervisor"))):
    now = datetime.now(timezone.utc).isoformat()
    guards = await db.guards.find({"is_active": True}, {"_id": 0}).to_list(100)
    return guards

@api_router.get("/security/dashboard-stats")
async def get_security_stats(current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))):
    active_panic = await db.panic_events.count_documents({"status": "active"})
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    today_access = await db.access_logs.count_documents({"timestamp": {"$gte": today_start}})
    active_guards = await db.guards.count_documents({"is_active": True})
    total_events = await db.panic_events.count_documents({})
    
    return {
        "active_alerts": active_panic,
        "today_accesses": today_access,
        "active_guards": active_guards,
        "total_events": total_events
    }

# ==================== HR MODULE ====================
@api_router.post("/hr/guards")
async def create_guard(guard: GuardCreate, request: Request, current_user = Depends(require_role("Administrador", "HR"))):
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
    
    return guard_doc

@api_router.get("/hr/guards")
async def get_guards(current_user = Depends(require_role("Administrador", "Supervisor", "HR"))):
    query = {}
    # Filter by condominium for non-super-admins
    if "SuperAdmin" not in current_user.get("roles", []):
        condo_id = current_user.get("condominium_id")
        if condo_id:
            query["condominium_id"] = condo_id
    
    guards = await db.guards.find(query, {"_id": 0}).to_list(100)
    return guards

@api_router.get("/hr/guards/{guard_id}")
async def get_guard(guard_id: str, current_user = Depends(require_role("Administrador", "Supervisor", "HR"))):
    guard = await db.guards.find_one({"id": guard_id}, {"_id": 0})
    if not guard:
        raise HTTPException(status_code=404, detail="Guard not found")
    return guard

@api_router.put("/hr/guards/{guard_id}")
async def update_guard(
    guard_id: str,
    guard_update: GuardUpdate,
    request: Request,
    current_user = Depends(require_role("Administrador"))
):
    """Update guard/employee details"""
    guard = await db.guards.find_one({"id": guard_id})
    if not guard:
        raise HTTPException(status_code=404, detail="Guard not found")
    
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

@api_router.post("/hr/shifts")
async def create_shift(shift: ShiftCreate, request: Request, current_user = Depends(require_role("Administrador", "Supervisor", "HR"))):
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
    
    # Check for overlapping shifts
    existing_shifts = await db.shifts.find({
        "guard_id": shift.guard_id,
        "status": {"$ne": "cancelled"},
        "$or": [
            {"start_time": {"$lt": shift.end_time}, "end_time": {"$gt": shift.start_time}}
        ]
    }).to_list(100)
    
    if existing_shifts:
        raise HTTPException(status_code=400, detail="El empleado ya tiene un turno programado en ese horario")
    
    # Get condominium_id from user
    condominium_id = current_user.get("condominium_id")
    
    shift_doc = {
        "id": str(uuid.uuid4()),
        "guard_id": shift.guard_id,
        "guard_name": guard["user_name"],
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

@api_router.get("/hr/shifts")
async def get_shifts(
    status: Optional[str] = None,
    guard_id: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """Get shifts with optional filters"""
    query = {}
    
    # Filter by status if provided
    if status:
        query["status"] = status
    
    # Filter by guard if provided
    if guard_id:
        query["guard_id"] = guard_id
    
    # Guards can only see their own shifts
    if "Guarda" in current_user.get("roles", []) and "Administrador" not in current_user.get("roles", []):
        guard = await db.guards.find_one({"user_id": current_user["id"]})
        if guard:
            query["guard_id"] = guard["id"]
    
    shifts = await db.shifts.find(query, {"_id": 0}).sort("start_time", -1).to_list(100)
    return shifts

@api_router.get("/hr/shifts/{shift_id}")
async def get_shift(shift_id: str, current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))):
    """Get a single shift by ID"""
    shift = await db.shifts.find_one({"id": shift_id}, {"_id": 0})
    if not shift:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    return shift

@api_router.put("/hr/shifts/{shift_id}")
async def update_shift(
    shift_id: str,
    shift_update: ShiftUpdate,
    request: Request,
    current_user = Depends(require_role("Administrador", "Supervisor", "HR"))
):
    """Update an existing shift"""
    shift = await db.shifts.find_one({"id": shift_id})
    if not shift:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    
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

@api_router.delete("/hr/shifts/{shift_id}")
async def delete_shift(
    shift_id: str,
    request: Request,
    current_user = Depends(require_role("Administrador"))
):
    """Delete (cancel) a shift"""
    shift = await db.shifts.find_one({"id": shift_id})
    if not shift:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    
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

@api_router.post("/hr/clock")
async def clock_in_out(
    clock_req: ClockRequest,
    request: Request,
    current_user = Depends(require_role("Guarda", "Administrador", "Supervisor"))
):
    """Register clock in or clock out"""
    if clock_req.type not in ["IN", "OUT"]:
        raise HTTPException(status_code=400, detail="Tipo debe ser 'IN' o 'OUT'")
    
    # Get guard record for current user
    guard = await db.guards.find_one({"user_id": current_user["id"]})
    if not guard:
        raise HTTPException(status_code=404, detail="No tienes registro como empleado")
    
    if not guard.get("is_active", True):
        raise HTTPException(status_code=400, detail="Tu cuenta de empleado no está activa")
    
    today = datetime.now(timezone.utc).date().isoformat()
    
    # Get today's clock logs for this employee
    today_logs = await db.hr_clock_logs.find({
        "employee_id": guard["id"],
        "date": today
    }).sort("timestamp", -1).to_list(100)
    
    if clock_req.type == "IN":
        # Check if already clocked in without clocking out
        if today_logs:
            last_log = today_logs[0]
            if last_log["type"] == "IN":
                raise HTTPException(status_code=400, detail="Ya tienes una entrada registrada. Debes registrar salida primero.")
    
    elif clock_req.type == "OUT":
        # Check if there's a clock in first
        if not today_logs:
            raise HTTPException(status_code=400, detail="No tienes entrada registrada hoy. Debes registrar entrada primero.")
        
        last_log = today_logs[0]
        if last_log["type"] == "OUT":
            raise HTTPException(status_code=400, detail="Ya registraste salida. Debes registrar entrada primero.")
    
    clock_doc = {
        "id": str(uuid.uuid4()),
        "employee_id": guard["id"],
        "employee_name": guard["user_name"],
        "type": clock_req.type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "date": today,
        "condominium_id": current_user.get("condominium_id"),
        "created_at": datetime.now(timezone.utc).isoformat()
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
            out_time = datetime.fromisoformat(clock_doc["timestamp"].replace('Z', '+00:00'))
            hours_worked = round((out_time - in_time).total_seconds() / 3600, 2)
            
            # Update guard's total hours
            await db.guards.update_one(
                {"id": guard["id"]},
                {"$inc": {"total_hours": hours_worked}}
            )
    
    await log_audit_event(
        AuditEventType.CLOCK_IN if clock_req.type == "IN" else AuditEventType.CLOCK_OUT,
        current_user["id"],
        "hr",
        {"employee_id": guard["id"], "type": clock_req.type, "hours_worked": hours_worked},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        **clock_doc,
        "hours_worked": hours_worked,
        "message": f"{'Entrada' if clock_req.type == 'IN' else 'Salida'} registrada exitosamente"
    }

@api_router.get("/hr/clock/status")
async def get_clock_status(current_user = Depends(require_role("Guarda", "Administrador", "Supervisor"))):
    """Get current clock status for logged-in employee"""
    guard = await db.guards.find_one({"user_id": current_user["id"]})
    if not guard:
        return {"is_clocked_in": False, "message": "No tienes registro como empleado"}
    
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
            "employee_name": guard["user_name"]
        }
    
    last_log = today_logs[0]
    return {
        "is_clocked_in": last_log["type"] == "IN",
        "last_action": last_log["type"],
        "last_time": last_log["timestamp"],
        "employee_id": guard["id"],
        "employee_name": guard["user_name"],
        "today_logs": [{"type": l["type"], "timestamp": l["timestamp"]} for l in today_logs]
    }

@api_router.get("/hr/clock/history")
async def get_clock_history(
    employee_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """Get clock history with filters"""
    query = {}
    
    # Guards can only see their own history
    if "Guarda" in current_user.get("roles", []) and "Administrador" not in current_user.get("roles", []):
        guard = await db.guards.find_one({"user_id": current_user["id"]})
        if guard:
            query["employee_id"] = guard["id"]
    elif employee_id:
        query["employee_id"] = employee_id
    
    if start_date:
        query["date"] = {"$gte": start_date}
    if end_date:
        if "date" in query:
            query["date"]["$lte"] = end_date
        else:
            query["date"] = {"$lte": end_date}
    
    logs = await db.hr_clock_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(500)
    return logs

# ==================== HR ABSENCES ====================

@api_router.post("/hr/absences")
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
    
    absence_doc = {
        "id": str(uuid.uuid4()),
        "employee_id": guard["id"],
        "employee_name": guard["user_name"],
        "reason": absence.reason,
        "type": absence.type,
        "start_date": absence.start_date,
        "end_date": absence.end_date,
        "notes": absence.notes,
        "status": "pending",
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
        {"absence_id": absence_doc["id"], "type": absence.type, "dates": f"{absence.start_date} - {absence.end_date}"},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return absence_doc

@api_router.get("/hr/absences")
async def get_absences(
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))
):
    """Get absence requests with filters"""
    query = {}
    
    if status:
        if status not in ["pending", "approved", "rejected"]:
            raise HTTPException(status_code=400, detail="Estado inválido")
        query["status"] = status
    
    # Guards can only see their own absences
    if "Guarda" in current_user.get("roles", []) and "Administrador" not in current_user.get("roles", []):
        guard = await db.guards.find_one({"user_id": current_user["id"]})
        if guard:
            query["employee_id"] = guard["id"]
    elif employee_id:
        query["employee_id"] = employee_id
    
    absences = await db.hr_absences.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return absences

@api_router.get("/hr/absences/{absence_id}")
async def get_absence(absence_id: str, current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))):
    """Get a single absence request"""
    absence = await db.hr_absences.find_one({"id": absence_id}, {"_id": 0})
    if not absence:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return absence

@api_router.put("/hr/absences/{absence_id}/approve")
async def approve_absence(
    absence_id: str,
    request: Request,
    admin_notes: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor"))
):
    """Approve an absence request"""
    absence = await db.hr_absences.find_one({"id": absence_id})
    if not absence:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
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

@api_router.put("/hr/absences/{absence_id}/reject")
async def reject_absence(
    absence_id: str,
    request: Request,
    admin_notes: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "Supervisor"))
):
    """Reject an absence request"""
    absence = await db.hr_absences.find_one({"id": absence_id})
    if not absence:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
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

@api_router.get("/hr/payroll")
async def get_payroll(current_user = Depends(require_role("Administrador", "HR"))):
    guards = await db.guards.find({}, {"_id": 0}).to_list(100)
    payroll = []
    for guard in guards:
        payroll.append({
            "guard_id": guard["id"],
            "guard_name": guard["user_name"],
            "badge_number": guard["badge_number"],
            "hourly_rate": guard["hourly_rate"],
            "total_hours": guard.get("total_hours", 0),
            "total_pay": guard.get("total_hours", 0) * guard["hourly_rate"]
        })
    return payroll

# ==================== HR RECRUITMENT ====================

@api_router.post("/hr/candidates")
async def create_candidate(
    candidate: CandidateCreate,
    request: Request,
    current_user = Depends(require_role("Administrador", "HR"))
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

@api_router.get("/hr/candidates")
async def get_candidates(
    status: Optional[str] = None,
    position: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "HR"))
):
    """List recruitment candidates"""
    query = {}
    
    # Filter by condominium for non-super-admins
    if "SuperAdmin" not in current_user.get("roles", []):
        condo_id = current_user.get("condominium_id")
        if condo_id:
            query["condominium_id"] = condo_id
    
    if status:
        query["status"] = status
    if position:
        query["position"] = position
    
    candidates = await db.hr_candidates.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return candidates

@api_router.get("/hr/candidates/{candidate_id}")
async def get_candidate(
    candidate_id: str,
    current_user = Depends(require_role("Administrador", "HR"))
):
    """Get a single candidate"""
    candidate = await db.hr_candidates.find_one({"id": candidate_id}, {"_id": 0})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    return candidate

@api_router.put("/hr/candidates/{candidate_id}")
async def update_candidate(
    candidate_id: str,
    update: CandidateUpdate,
    request: Request,
    current_user = Depends(require_role("Administrador", "HR"))
):
    """Update candidate information"""
    candidate = await db.hr_candidates.find_one({"id": candidate_id})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
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

@api_router.post("/hr/candidates/{candidate_id}/hire")
async def hire_candidate(
    candidate_id: str,
    hire_data: HireCandidate,
    request: Request,
    current_user = Depends(require_role("Administrador", "HR"))
):
    """Hire a candidate - creates user account and guard record"""
    candidate = await db.hr_candidates.find_one({"id": candidate_id})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
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

@api_router.put("/hr/candidates/{candidate_id}/reject")
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

@api_router.post("/hr/employees")
async def create_employee_directly(
    employee: CreateEmployeeByHR,
    request: Request,
    current_user = Depends(require_role("Administrador", "HR"))
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

@api_router.put("/hr/employees/{guard_id}/deactivate")
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
    
    # Deactivate user account
    await db.users.update_one(
        {"id": guard["user_id"]},
        {"$set": {"is_active": False}}
    )
    
    await log_audit_event(
        AuditEventType.EMPLOYEE_DEACTIVATED,
        current_user["id"],
        "hr",
        {"guard_id": guard_id, "user_id": guard["user_id"], "name": guard["user_name"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": f"Empleado {guard['user_name']} desactivado"}

@api_router.put("/hr/employees/{guard_id}/activate")
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
    
    # Activate user account
    await db.users.update_one(
        {"id": guard["user_id"]},
        {"$set": {"is_active": True}}
    )
    
    await log_audit_event(
        AuditEventType.EMPLOYEE_ACTIVATED,
        current_user["id"],
        "hr",
        {"guard_id": guard_id, "user_id": guard["user_id"], "name": guard["user_name"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {"message": f"Empleado {guard['user_name']} reactivado"}

# ==================== ADMIN USER MANAGEMENT ====================

@api_router.post("/admin/users")
async def create_user_by_admin(
    user_data: CreateUserByAdmin,
    request: Request,
    current_user = Depends(require_role("Administrador", "SuperAdmin"))
):
    """Admin creates a user (Resident, HR, Guard, etc.)"""
    # Check email not in use
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # Validate role
    valid_roles = ["Residente", "HR", "Guarda", "Supervisor"]
    if user_data.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Rol inválido. Use: {', '.join(valid_roles)}")
    
    condominium_id = current_user.get("condominium_id")
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "hashed_password": hash_password(user_data.password),
        "full_name": user_data.full_name,
        "roles": [user_data.role],
        "condominium_id": condominium_id,
        "phone": user_data.phone,
        "is_active": True,
        "is_locked": False,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    await log_audit_event(
        AuditEventType.USER_CREATED,
        current_user["id"],
        "admin",
        {"user_id": user_id, "email": user_data.email, "role": user_data.role},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return {
        "message": f"Usuario {user_data.full_name} creado exitosamente",
        "user_id": user_id,
        "credentials": {
            "email": user_data.email,
            "password": "********"
        }
    }

@api_router.get("/admin/users")
async def get_users_by_admin(
    role: Optional[str] = None,
    current_user = Depends(require_role("Administrador", "SuperAdmin"))
):
    """Get users in admin's condominium"""
    query = {}
    
    # Filter by condominium for non-super-admins
    if "SuperAdmin" not in current_user.get("roles", []):
        query["condominium_id"] = current_user.get("condominium_id")
    
    if role:
        query["roles"] = role
    
    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).to_list(500)
    return users

# ==================== SCHOOL MODULE ====================
@api_router.post("/school/courses")
async def create_course(course: CourseCreate, request: Request, current_user = Depends(require_role("Administrador"))):
    course_doc = {
        "id": str(uuid.uuid4()),
        "title": course.title,
        "description": course.description,
        "duration_hours": course.duration_hours,
        "instructor": course.instructor,
        "category": course.category,
        "lessons": [],
        "enrolled_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.courses.insert_one(course_doc)
    return course_doc

@api_router.get("/school/courses")
async def get_courses(current_user = Depends(get_current_user)):
    courses = await db.courses.find({}, {"_id": 0}).to_list(100)
    return courses

@api_router.get("/school/courses/{course_id}")
async def get_course(course_id: str, current_user = Depends(get_current_user)):
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@api_router.post("/school/enroll")
async def enroll_course(enrollment: EnrollmentCreate, request: Request, current_user = Depends(get_current_user)):
    course = await db.courses.find_one({"id": enrollment.course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    existing = await db.enrollments.find_one({
        "course_id": enrollment.course_id,
        "student_id": enrollment.student_id
    })
    if existing:
        raise HTTPException(status_code=409, detail="Already enrolled")
    
    enrollment_doc = {
        "id": str(uuid.uuid4()),
        "course_id": enrollment.course_id,
        "course_title": course["title"],
        "student_id": enrollment.student_id,
        "student_name": current_user["full_name"],
        "progress": 0,
        "completed_lessons": [],
        "enrolled_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "certificate_id": None
    }
    
    await db.enrollments.insert_one(enrollment_doc)
    await db.courses.update_one({"id": enrollment.course_id}, {"$inc": {"enrolled_count": 1}})
    
    await log_audit_event(
        AuditEventType.COURSE_ENROLLED,
        current_user["id"],
        "school",
        {"course_id": enrollment.course_id, "course_title": course["title"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return enrollment_doc

@api_router.get("/school/enrollments")
async def get_my_enrollments(current_user = Depends(get_current_user)):
    enrollments = await db.enrollments.find({"student_id": current_user["id"]}, {"_id": 0}).to_list(100)
    return enrollments

@api_router.get("/school/certificates")
async def get_certificates(current_user = Depends(get_current_user)):
    certificates = await db.certificates.find({"student_id": current_user["id"]}, {"_id": 0}).to_list(100)
    return certificates

@api_router.get("/school/student-progress/{student_id}")
async def get_student_progress(student_id: str, current_user = Depends(get_current_user)):
    if current_user["id"] != student_id and "Administrador" not in current_user["roles"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    enrollments = await db.enrollments.find({"student_id": student_id}, {"_id": 0}).to_list(100)
    certificates = await db.certificates.find({"student_id": student_id}, {"_id": 0}).to_list(100)
    
    return {
        "enrollments": enrollments,
        "certificates": certificates,
        "total_courses": len(enrollments),
        "completed_courses": len([e for e in enrollments if e.get("completed_at")]),
        "total_certificates": len(certificates)
    }

# ==================== PAYMENTS MODULE ====================
# GENTURIX PRICING MODEL: $1 per user per month
# Simple, accessible, massive adoption model

class UserSubscriptionCreate(BaseModel):
    user_count: int = 1

GENTURIX_PRICE_PER_USER = 1.00  # $1 USD per user per month

def calculate_subscription_price(user_count: int) -> float:
    """Calculate price: $1 per user per month"""
    return round(user_count * GENTURIX_PRICE_PER_USER, 2)

@api_router.get("/payments/pricing")
async def get_pricing_info(current_user = Depends(get_current_user)):
    """Get GENTURIX pricing model: $1 per user per month"""
    return {
        "model": "per_user",
        "price_per_user": GENTURIX_PRICE_PER_USER,
        "currency": "usd",
        "billing_period": "monthly",
        "description": "$1 por usuario al mes",
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

@api_router.post("/payments/calculate")
async def calculate_price(subscription: UserSubscriptionCreate, current_user = Depends(get_current_user)):
    """Calculate subscription price based on user count"""
    if subscription.user_count < 1:
        raise HTTPException(status_code=400, detail="Minimum 1 user required")
    
    total = calculate_subscription_price(subscription.user_count)
    return {
        "user_count": subscription.user_count,
        "price_per_user": GENTURIX_PRICE_PER_USER,
        "total": total,
        "currency": "usd",
        "billing_period": "monthly"
    }

@api_router.post("/payments/checkout")
async def create_checkout(request: Request, current_user = Depends(get_current_user), user_count: int = 1, origin_url: str = ""):
    """Create checkout session for $1/user subscription"""
    if user_count < 1:
        raise HTTPException(status_code=400, detail="Minimum 1 user required")
    
    total_amount = calculate_subscription_price(user_count)
    
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
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": current_user["id"],
            "user_email": current_user["email"],
            "user_count": str(user_count),
            "price_per_user": str(GENTURIX_PRICE_PER_USER)
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
        "price_per_user": GENTURIX_PRICE_PER_USER,
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

@api_router.get("/payments/status/{session_id}")
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

@api_router.get("/payments/history")
async def get_payment_history(current_user = Depends(get_current_user)):
    transactions = await db.payment_transactions.find(
        {"user_id": current_user["id"]}, 
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return transactions

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    stripe_api_key = os.environ.get('STRIPE_API_KEY')
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
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

# ==================== AUDIT MODULE ====================
@api_router.get("/audit/logs")
async def get_audit_logs(
    module: Optional[str] = None,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user = Depends(require_role("Administrador"))
):
    query = {}
    if module:
        query["module"] = module
    if event_type:
        query["event_type"] = event_type
    if user_id:
        query["user_id"] = user_id
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(500)
    return logs

@api_router.get("/audit/stats")
async def get_audit_stats(current_user = Depends(require_role("Administrador"))):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    
    total_events = await db.audit_logs.count_documents({})
    today_events = await db.audit_logs.count_documents({"timestamp": {"$gte": today_start}})
    login_failures = await db.audit_logs.count_documents({"event_type": "login_failure"})
    panic_events = await db.audit_logs.count_documents({"event_type": "panic_button"})
    
    return {
        "total_events": total_events,
        "today_events": today_events,
        "login_failures": login_failures,
        "panic_events": panic_events
    }

# ==================== DASHBOARD ====================
@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user = Depends(get_current_user)):
    stats = {
        "total_users": await db.users.count_documents({}),
        "active_guards": await db.guards.count_documents({"is_active": True}),
        "active_alerts": await db.panic_events.count_documents({"status": "active"}),
        "total_courses": await db.courses.count_documents({}),
        "pending_payments": await db.payment_transactions.count_documents({"payment_status": "pending"})
    }
    return stats

@api_router.get("/dashboard/recent-activity")
async def get_recent_activity(current_user = Depends(get_current_user)):
    activities = await db.audit_logs.find({}, {"_id": 0}).sort("timestamp", -1).to_list(20)
    return activities

# ==================== USERS MANAGEMENT ====================
@api_router.get("/users")
async def get_users(current_user = Depends(require_role("Administrador"))):
    users = await db.users.find({}, {"_id": 0, "hashed_password": 0}).to_list(100)
    return users

@api_router.put("/users/{user_id}/roles")
async def update_user_roles(user_id: str, roles: List[str], current_user = Depends(require_role("Administrador"))):
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"roles": roles, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Roles updated"}

@api_router.put("/users/{user_id}/status")
async def update_user_status(user_id: str, is_active: bool, current_user = Depends(require_role("Administrador"))):
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_active": is_active, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Status updated"}

# ==================== MULTI-TENANT MODULE ====================
# Condominium/Tenant Management Endpoints (Super Admin)

@api_router.post("/condominiums", response_model=CondominiumResponse)
async def create_condominium(
    condo_data: CondominiumCreate,
    request: Request,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Create a new condominium/tenant (Super Admin only)"""
    condo_id = str(uuid.uuid4())
    
    # Initialize module config with defaults
    modules = condo_data.modules if condo_data.modules else CondominiumModules()
    
    condo_doc = {
        "id": condo_id,
        "name": condo_data.name,
        "address": condo_data.address,
        "contact_email": condo_data.contact_email,
        "contact_phone": condo_data.contact_phone,
        "max_users": condo_data.max_users,
        "current_users": 0,
        "modules": modules.model_dump(),
        "status": "active",  # active, demo, suspended
        "is_demo": False,
        "is_active": True,
        "price_per_user": 1.0,
        "discount_percent": 0,
        "free_modules": [],
        "plan": "basic",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.condominiums.insert_one(condo_doc)
    
    await log_audit_event(
        AuditEventType.CONDO_CREATED,
        current_user["id"],
        "super_admin",
        {"condo_id": condo_id, "name": condo_data.name, "action": "created"},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return CondominiumResponse(
        id=condo_id,
        name=condo_data.name,
        address=condo_data.address,
        contact_email=condo_data.contact_email,
        contact_phone=condo_data.contact_phone,
        max_users=condo_data.max_users,
        current_users=0,
        modules=modules.model_dump(),
        is_active=True,
        created_at=condo_doc["created_at"]
    )

@api_router.get("/condominiums")
async def list_condominiums(
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """List all condominiums (Super Admin only)"""
    condos = await db.condominiums.find({}, {"_id": 0}).to_list(100)
    # Enrich with default values for fields that may not exist
    for condo in condos:
        condo.setdefault("status", "active")
        condo.setdefault("is_demo", False)
        condo.setdefault("discount_percent", 0.0)
        condo.setdefault("plan", "basic")
        condo.setdefault("price_per_user", 1.0)
        # Calculate current_users from database if not set
        if condo.get("current_users", 0) == 0:
            user_count = await db.users.count_documents({"condominium_id": condo["id"], "is_active": True})
            condo["current_users"] = user_count
    return condos

@api_router.get("/condominiums/{condo_id}", response_model=CondominiumResponse)
async def get_condominium(
    condo_id: str,
    current_user = Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPERVISOR))
):
    """Get condominium details"""
    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0})
    if not condo:
        raise HTTPException(status_code=404, detail="Condominium not found")
    return condo

@api_router.patch("/condominiums/{condo_id}")
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
    
    return {"message": "Condominium updated successfully"}

@api_router.delete("/condominiums/{condo_id}")
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
    
    return {"message": "Condominium deactivated"}

@api_router.get("/condominiums/{condo_id}/users")
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

@api_router.get("/condominiums/{condo_id}/billing")
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

@api_router.patch("/condominiums/{condo_id}/modules/{module_name}")
async def update_module_config(
    condo_id: str,
    module_name: str,
    enabled: bool,
    settings: Optional[Dict[str, Any]] = None,
    current_user = Depends(require_role(RoleEnum.ADMINISTRADOR))
):
    """Enable/disable a module for a condominium"""
    valid_modules = ["security", "hr", "school", "payments", "audit", "reservations", "access_control", "messaging"]
    
    if module_name not in valid_modules:
        raise HTTPException(status_code=400, detail=f"Invalid module. Valid modules: {', '.join(valid_modules)}")
    
    update_data = {
        f"modules.{module_name}.enabled": enabled,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    if settings:
        update_data[f"modules.{module_name}.settings"] = settings
    
    result = await db.condominiums.update_one(
        {"id": condo_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Condominium not found")
    
    return {"message": f"Module '{module_name}' {'enabled' if enabled else 'disabled'} successfully"}

# ==================== SUPER ADMIN ENDPOINTS ====================

@api_router.get("/super-admin/stats")
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

@api_router.get("/super-admin/users")
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

@api_router.put("/super-admin/users/{user_id}/lock")
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

@api_router.put("/super-admin/users/{user_id}/unlock")
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

@api_router.post("/super-admin/condominiums/{condo_id}/make-demo")
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
    
    return {"message": "Condominium converted to demo mode"}

@api_router.post("/super-admin/condominiums/{condo_id}/reset-demo")
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

@api_router.patch("/super-admin/condominiums/{condo_id}/pricing")
async def update_condo_pricing(
    condo_id: str,
    discount_percent: Optional[int] = None,
    free_modules: Optional[List[str]] = None,
    plan: Optional[str] = None,
    request: Request = None,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR))
):
    """Update pricing/plan for a condominium"""
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if discount_percent is not None:
        update_data["discount_percent"] = max(0, min(100, discount_percent))
    if free_modules is not None:
        update_data["free_modules"] = free_modules
    if plan is not None:
        update_data["plan"] = plan
    
    result = await db.condominiums.update_one({"id": condo_id}, {"$set": update_data})
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Condominium not found")
    
    if request:
        await log_audit_event(
            AuditEventType.PLAN_UPDATED,
            current_user["id"],
            "super_admin",
            {"condo_id": condo_id, "changes": update_data},
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "unknown")
        )
    
    return {"message": "Pricing updated successfully"}

@api_router.patch("/super-admin/condominiums/{condo_id}/status")
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

@api_router.get("/super-admin/audit")
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

# ==================== SUPER ADMIN: CONDOMINIUM ADMIN CREATION ====================

@api_router.post("/super-admin/condominiums/{condo_id}/admin")
async def create_condominium_admin(
    condo_id: str,
    admin_data: CreateUserByAdmin,
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
        "password_hash": hash_password(admin_data.password),
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

# ==================== DEMO DATA SEEDING ====================
@api_router.post("/seed-demo-data")
async def seed_demo_data():
    """Seed demo data for testing and demonstration"""
    
    # Check if demo data already exists
    existing_demo = await db.users.find_one({"email": "admin@genturix.com"})
    if existing_demo:
        return {"message": "Demo data already exists"}
    
    # Demo Users
    demo_users = [
        {"email": "superadmin@genturix.com", "full_name": "Super Administrador", "password": "SuperAdmin123!", "roles": ["SuperAdmin"]},
        {"email": "admin@genturix.com", "full_name": "Carlos Admin", "password": "Admin123!", "roles": ["Administrador"]},
        {"email": "supervisor@genturix.com", "full_name": "María Supervisor", "password": "Super123!", "roles": ["Supervisor"]},
        {"email": "guarda1@genturix.com", "full_name": "Juan Pérez", "password": "Guard123!", "roles": ["Guarda"]},
        {"email": "guarda2@genturix.com", "full_name": "Pedro García", "password": "Guard123!", "roles": ["Guarda"]},
        {"email": "residente@genturix.com", "full_name": "Ana Martínez", "password": "Resi123!", "roles": ["Residente"]},
        {"email": "estudiante@genturix.com", "full_name": "Luis Estudiante", "password": "Stud123!", "roles": ["Estudiante"]},
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

# ==================== HEALTH CHECK ====================
@api_router.get("/")
async def root():
    return {"message": "GENTURIX Enterprise Platform API", "version": "1.0.0"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
