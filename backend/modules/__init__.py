"""
MODULES PACKAGE
===============
Modular components extracted from monolithic server.py

Available modules:
- billing: Payment processing, subscriptions, Stripe integration
- users: User management, roles, permissions (Phase 1 - structure only)
"""

from .billing import billing_router
from .users import users_router

__all__ = [
    "billing_router",
    "users_router",
]
