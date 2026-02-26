"""
Users Module - API Router
=========================

API endpoints for user management.

NOTE: Endpoints will be migrated here in Phase 2.
      Currently, all user endpoints remain in server.py.

Planned endpoints:
- GET    /api/users              - List users (admin)
- GET    /api/users/{id}         - Get user by ID
- POST   /api/users              - Create user
- PUT    /api/users/{id}         - Update user
- DELETE /api/users/{id}         - Delete user (soft)
- PUT    /api/users/{id}/status  - Update user status
- POST   /api/users/{id}/reset-password - Reset password
"""

from fastapi import APIRouter

# Create router with prefix and tags
users_router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

# ==================== ENDPOINTS ====================
# Endpoints will be added in Phase 2

# @users_router.get("")
# async def list_users():
#     """List all users with filtering"""
#     pass

# @users_router.get("/{user_id}")
# async def get_user(user_id: str):
#     """Get user by ID"""
#     pass

# @users_router.post("")
# async def create_user():
#     """Create a new user"""
#     pass

# @users_router.put("/{user_id}")
# async def update_user(user_id: str):
#     """Update user"""
#     pass

# @users_router.delete("/{user_id}")
# async def delete_user(user_id: str):
#     """Soft delete user"""
#     pass

# @users_router.put("/{user_id}/status")
# async def update_user_status(user_id: str):
#     """Update user status"""
#     pass
