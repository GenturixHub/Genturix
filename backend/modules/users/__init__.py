"""
Users Module - Genturix Platform
================================

This module handles all user-related operations including:
- User CRUD operations
- Role management
- User status management
- Permission checks

Phase 1: Structure only (models defined, no logic moved yet)
"""

from .models import (
    RoleEnum,
    UserStatus,
    UserCreate,
    UserResponse,
    UserStatusUpdate,
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
    # Router
    "users_router",
]
