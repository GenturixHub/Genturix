"""GENTURIX Core — Enums"""
from enum import Enum

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
    PANIC_RESOLVED = "panic_resolved"
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
    # Performance evaluation events
    EVALUATION_CREATED = "evaluation_created"
    EVALUATION_UPDATED = "evaluation_updated"
    # Credential email events
    CREDENTIALS_EMAIL_SENT = "credentials_email_sent"
    CREDENTIALS_EMAIL_FAILED = "credentials_email_failed"
    PASSWORD_CHANGED = "password_changed"
    # Condominium management events
    CONDOMINIUM_DELETED = "condominium_deleted"
    # Visitor Authorization events
    AUTHORIZATION_CREATED = "authorization_created"
    AUTHORIZATION_UPDATED = "authorization_updated"
    AUTHORIZATION_DEACTIVATED = "authorization_deactivated"
    VISITOR_CHECKIN = "visitor_checkin"
    VISITOR_CHECKOUT = "visitor_checkout"
    VISITOR_ARRIVAL_NOTIFIED = "visitor_arrival_notified"
    VISITOR_EXIT_NOTIFIED = "visitor_exit_notified"
    # User status events
    USER_BLOCKED = "user_blocked"
    USER_UNBLOCKED = "user_unblocked"
    USER_SUSPENDED = "user_suspended"
    USER_DELETED = "user_deleted"
    # Seat management events
    SEAT_LIMIT_UPDATED = "seat_limit_updated"
    SEAT_REDUCTION_BLOCKED = "seat_reduction_blocked"
    # Password reset events
    PASSWORD_RESET_BY_ADMIN = "password_reset_by_admin"
    PASSWORD_RESET_TOKEN_USED = "password_reset_token_used"
    # Security events
    SECURITY_ALERT = "security_alert"
    # Pricing events
    PRICING_GLOBAL_UPDATED = "pricing_global_updated"
    PRICING_OVERRIDE_UPDATED = "pricing_override_updated"

# ==================== USER STATUS ENUM ====================
class UserStatus(str, Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    SUSPENDED = "suspended"

