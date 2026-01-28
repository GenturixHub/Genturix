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
    ADMINISTRADOR = "Administrador"
    SUPERVISOR = "Supervisor"
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
    SHIFT_UPDATED = "shift_updated"

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

class ShiftCreate(BaseModel):
    guard_id: str
    start_time: str
    end_time: str
    location: str
    notes: Optional[str] = None

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
    resident_name = current_user.get("full_name", "").lower()
    
    # Get all access logs that mention this resident or are marked as visits
    logs = await db.access_logs.find({}, {"_id": 0}).sort("timestamp", -1).to_list(100)
    
    # Filter logs that might be relevant to this resident
    notifications = [
        log for log in logs 
        if log.get("notes") and (
            resident_name in log.get("notes", "").lower() or 
            "visita" in log.get("notes", "").lower()
        )
    ]
    
    return notifications[:20]

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
async def create_guard(guard: GuardCreate, request: Request, current_user = Depends(require_role("Administrador"))):
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
async def get_guards(current_user = Depends(require_role("Administrador", "Supervisor"))):
    guards = await db.guards.find({}, {"_id": 0}).to_list(100)
    return guards

@api_router.get("/hr/guards/{guard_id}")
async def get_guard(guard_id: str, current_user = Depends(require_role("Administrador", "Supervisor"))):
    guard = await db.guards.find_one({"id": guard_id}, {"_id": 0})
    if not guard:
        raise HTTPException(status_code=404, detail="Guard not found")
    return guard

@api_router.post("/hr/shifts")
async def create_shift(shift: ShiftCreate, request: Request, current_user = Depends(require_role("Administrador", "Supervisor"))):
    guard = await db.guards.find_one({"id": shift.guard_id})
    if not guard:
        raise HTTPException(status_code=404, detail="Guard not found")
    
    shift_doc = {
        "id": str(uuid.uuid4()),
        "guard_id": shift.guard_id,
        "guard_name": guard["user_name"],
        "start_time": shift.start_time,
        "end_time": shift.end_time,
        "location": shift.location,
        "notes": shift.notes,
        "status": "scheduled",
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.shifts.insert_one(shift_doc)
    
    await log_audit_event(
        AuditEventType.SHIFT_CREATED,
        current_user["id"],
        "hr",
        {"guard_id": shift.guard_id, "location": shift.location},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return shift_doc

@api_router.get("/hr/shifts")
async def get_shifts(current_user = Depends(require_role("Administrador", "Supervisor", "Guarda"))):
    shifts = await db.shifts.find({}, {"_id": 0}).sort("start_time", -1).to_list(100)
    return shifts

@api_router.get("/hr/payroll")
async def get_payroll(current_user = Depends(require_role("Administrador"))):
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
# Condominium/Tenant Management Endpoints

@api_router.post("/condominiums", response_model=CondominiumResponse)
async def create_condominium(
    condo_data: CondominiumCreate,
    current_user = Depends(require_role(RoleEnum.ADMINISTRADOR))
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
        "is_active": True,
        "price_per_user": 1.0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.condominiums.insert_one(condo_doc)
    
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
    current_user = Depends(require_role(RoleEnum.ADMINISTRADOR))
):
    """List all condominiums (Super Admin only)"""
    condos = await db.condominiums.find({}, {"_id": 0}).to_list(100)
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
    current_user = Depends(require_role(RoleEnum.ADMINISTRADOR))
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
    current_user = Depends(require_role(RoleEnum.ADMINISTRADOR))
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
