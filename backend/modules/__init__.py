"""
MODULES PACKAGE
===============
Modular components extracted from monolithic server.py

Available modules:
- billing: Payment processing, subscriptions, Stripe integration
- users: User management, roles, permissions (Phase 1 - structure only)
"""

# Billing module exports (no router yet - endpoints still in server.py)
from .billing import (
    BillingStatus,
    init_service as init_billing_service,
    init_scheduler as init_billing_scheduler,
)

# Users module exports (Phase 1 - structure only)
from .users import (
    users_router,
    RoleEnum,
    UserStatus,
)

__all__ = [
    # Billing
    "BillingStatus",
    "init_billing_service",
    "init_billing_scheduler",
    # Users
    "users_router",
    "RoleEnum",
    "UserStatus",
]
