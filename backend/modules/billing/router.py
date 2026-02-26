"""
BILLING ROUTER MODULE - PHASE 2 MIGRATION
==========================================
API endpoints for billing operations.
Migrated from server.py as part of backend modularization.

NOTE: This module defines the endpoints but the actual execution
logic remains in server.py to avoid circular imports and maintain
compatibility. This is a structural migration step.
"""

from fastapi import APIRouter

# Create main billing router
router = APIRouter(tags=["billing"])

# These routers will be populated by server.py during app initialization
# The actual endpoint definitions remain in server.py for this phase
# to avoid circular import issues with dependencies like get_current_user, require_role, db, etc.

# In PHASE 3, the business logic will be moved to service.py and these
# endpoints will be fully self-contained here.

"""
BILLING ENDPOINTS (defined in server.py, routed via /api prefix):

SCHEDULER ADMIN:
- POST /billing/scheduler/run-now
- GET /billing/scheduler/history
- GET /billing/scheduler/status

BILLING OPERATIONS:
- POST /billing/preview
- GET /billing/events/{condominium_id}
- PATCH /billing/seats/{condominium_id}
- POST /billing/confirm-payment/{condominium_id}
- GET /billing/payments/{condominium_id}
- GET /billing/payments
- GET /billing/balance/{condominium_id}

SEAT UPGRADE:
- POST /billing/request-seat-upgrade
- GET /billing/my-pending-request
- GET /billing/upgrade-requests
- PATCH /billing/approve-seat-upgrade/{request_id}
- GET /billing/seat-status/{condominium_id}

BILLING INFO:
- GET /billing/info
- GET /billing/can-create-user
- GET /billing/history

SUPER ADMIN:
- GET /super-admin/billing/overview
- GET /super-admin/billing/overview-legacy
- PATCH /super-admin/condominiums/{condo_id}/billing

CONDOMINIUM:
- GET /condominiums/{condo_id}/billing
- PUT /condominiums/{condominium_id}/grace-period

STRIPE:
- POST /billing/upgrade-seats
"""
