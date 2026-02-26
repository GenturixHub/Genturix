"""
Users Module - Pydantic Models
==============================

Contains all user-related data models and schemas.

NOTE: These models are DUPLICATED from server.py during Phase 1.
      In Phase 2, server.py will import from this module.
      In Phase 3, duplicates in server.py will be removed.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


# ==================== ROLE ENUM ====================
class RoleEnum(str, Enum):
    """
    Platform roles with hierarchical permissions.
    
    Hierarchy:
    - SuperAdmin: Platform-wide access, multi-tenant management
    - Administrador: Condominium-level full access
    - Supervisor: HR and guard management
    - HR: Human resources, recruitment, absences
    - Guarda: Security operations
    - Residente: Resident access
    - Estudiante: Student/learning access
    """
    SUPER_ADMIN = "SuperAdmin"
    ADMINISTRADOR = "Administrador"
    SUPERVISOR = "Supervisor"
    HR = "HR"
    GUARDA = "Guarda"
    RESIDENTE = "Residente"
    ESTUDIANTE = "Estudiante"


# ==================== USER STATUS ENUM ====================
class UserStatus(str, Enum):
    """User account status"""
    ACTIVE = "active"
    BLOCKED = "blocked"
    SUSPENDED = "suspended"


# ==================== USER MODELS ====================
class UserCreate(BaseModel):
    """Schema for creating a new user"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    roles: List[RoleEnum] = [RoleEnum.RESIDENTE]
    condominium_id: Optional[str] = None


class UserResponse(BaseModel):
    """Schema for user response (excludes sensitive data)"""
    id: str
    email: str
    full_name: str
    roles: List[str]
    is_active: bool
    status: str = "active"
    created_at: str
    condominium_id: Optional[str] = None
    password_reset_required: bool = False


class UserStatusUpdate(BaseModel):
    """Schema for updating user status"""
    status: UserStatus
    reason: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    roles: Optional[List[RoleEnum]] = None
    is_active: Optional[bool] = None
    status: Optional[UserStatus] = None


class UserListResponse(BaseModel):
    """Schema for paginated user list"""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
