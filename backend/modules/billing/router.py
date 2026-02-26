"""
BILLING ROUTER MODULE
=====================
API endpoints for billing operations.

NOTE: Endpoints remain in server.py for now to avoid breaking changes.
This file serves as documentation of billing-related endpoints.

Billing Endpoints in server.py:
- POST /api/billing/confirm-payment/{condominium_id}
- GET /api/billing/info
- GET /api/billing/preview
- GET /api/billing/balance/{condominium_id}
- GET /api/billing/payments
- GET /api/billing/payments/{condominium_id}
- POST /api/billing/upgrade-seats
- POST /api/billing/request-seat-upgrade
- GET /api/super-admin/billing/overview
- POST /api/billing/scheduler/run-now
- GET /api/billing/scheduler/status
- GET /api/billing/scheduler/history
- PUT /api/condominiums/{condominium_id}/grace-period

TODO: Migrate these endpoints to this router in a future phase.
"""

from fastapi import APIRouter

# Placeholder router - endpoints will be migrated here in future
router = APIRouter(prefix="/billing", tags=["billing"])

# Future: Add endpoints here
