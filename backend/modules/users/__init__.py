"""
Users Module - Genturix Platform
================================

This module handles all user-related operations including:
- User CRUD operations
- Role management
- User status management
- Seat management (billing integration)

Phase 2A: Core seat engine functions migrated
"""

from .models import (
    RoleEnum,
    UserStatus,
    UserCreate,
    UserResponse,
    UserStatusUpdate,
    UserUpdate,
    UserListResponse,
    CreateUserByAdmin,
    CreateEmployeeByHR,
    UserStatusUpdateV2,
)

from .service import (
    # Database setup
    set_db,
    set_logger,
    get_db,
    get_logger,
    # Core seat engine functions
    count_active_users,
    count_active_residents,
    update_active_user_count,
    can_create_user,
)

from .router import users_router

__all__ = [
    # Enums
    "RoleEnum",
    "UserStatus",
    # Models
    "UserCreate",
    "UserResponse",
    "UserStatusUpdate",
    "UserUpdate",
    "UserListResponse",
    "CreateUserByAdmin",
    "CreateEmployeeByHR",
    "UserStatusUpdateV2",
    # Service setup
    "set_db",
    "set_logger",
    "get_db",
    "get_logger",
    # Core seat engine
    "count_active_users",
    "count_active_residents",
    "update_active_user_count",
    "can_create_user",
    # Router
    "users_router",
]
