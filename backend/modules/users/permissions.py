"""
Users Module - Permission Logic
================================

User-specific permission logic will be defined here.

This module will contain:
- Role-based access control (RBAC) helpers
- Permission checks for user operations
- Condominium-scoped access validation

Permission Matrix:
------------------
| Action              | SuperAdmin | Admin | Supervisor | HR  | Guard | Resident |
|---------------------|------------|-------|------------|-----|-------|----------|
| Create User         | ✓ (any)    | ✓     | ✓          | ✓   | ✗     | ✗        |
| View All Users      | ✓ (any)    | ✓     | ✓          | ✓   | ✗     | ✗        |
| Edit User           | ✓ (any)    | ✓     | ✓ (guards) | ✓   | ✗     | ✗        |
| Delete User         | ✓ (any)    | ✓     | ✗          | ✗   | ✗     | ✗        |
| Block/Unblock       | ✓ (any)    | ✓     | ✗          | ✗   | ✗     | ✗        |
| Reset Password      | ✓ (any)    | ✓     | ✓ (guards) | ✓   | ✗     | ✗        |
| Change Own Password | ✓          | ✓     | ✓          | ✓   | ✓     | ✓        |
| View Own Profile    | ✓          | ✓     | ✓          | ✓   | ✓     | ✓        |
"""

from typing import List, Optional
from .models import RoleEnum


# ==================== ROLE HIERARCHIES ====================
ADMIN_ROLES = [RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR]
MANAGEMENT_ROLES = [RoleEnum.SUPER_ADMIN, RoleEnum.ADMINISTRADOR, RoleEnum.SUPERVISOR, RoleEnum.HR]
ALL_ROLES = list(RoleEnum)


# ==================== PERMISSION CHECKS ====================
# These functions will be implemented as needed

def can_create_user(actor_roles: List[str], target_condominium_id: Optional[str] = None) -> bool:
    """Check if actor can create users"""
    # SuperAdmin can create anywhere
    if RoleEnum.SUPER_ADMIN.value in actor_roles:
        return True
    # Admin, Supervisor, HR can create in their condominium
    return any(role in actor_roles for role in [
        RoleEnum.ADMINISTRADOR.value,
        RoleEnum.SUPERVISOR.value,
        RoleEnum.HR.value
    ])


def can_view_users(actor_roles: List[str]) -> bool:
    """Check if actor can view user list"""
    management_values = [r.value for r in MANAGEMENT_ROLES]
    return any(role in management_values for role in actor_roles)


def can_edit_user(
    actor_roles: List[str],
    actor_condominium_id: Optional[str],
    target_roles: List[str],
    target_condominium_id: Optional[str]
) -> bool:
    """Check if actor can edit target user"""
    # SuperAdmin can edit anyone
    if RoleEnum.SUPER_ADMIN.value in actor_roles:
        return True
    
    # Must be in same condominium
    if actor_condominium_id != target_condominium_id:
        return False
    
    # Admin can edit anyone in their condo
    if RoleEnum.ADMINISTRADOR.value in actor_roles:
        return True
    
    # Supervisor/HR can only edit guards
    if any(role in actor_roles for role in [RoleEnum.SUPERVISOR.value, RoleEnum.HR.value]):
        return RoleEnum.GUARDA.value in target_roles
    
    return False


def can_delete_user(actor_roles: List[str]) -> bool:
    """Check if actor can delete users"""
    admin_values = [r.value for r in ADMIN_ROLES]
    return any(role in admin_values for role in actor_roles)


def can_manage_user_status(actor_roles: List[str]) -> bool:
    """Check if actor can block/unblock users"""
    admin_values = [r.value for r in ADMIN_ROLES]
    return any(role in admin_values for role in actor_roles)
