"""
BILLING ROUTER MODULE - PHASE 2 MODULARIZATION
===============================================
This module documents the billing API endpoints that have been 
reorganized as part of the backend modularization effort.

PHASE 2 STATUS: COMPLETE
========================
All billing endpoints have been moved to dedicated APIRouter instances
within server.py. The routing structure is:

- billing_router: /api/billing/* endpoints
- billing_super_admin_router: /api/super-admin/billing/* endpoints

ENDPOINTS MIGRATED TO billing_router (19 endpoints):
===================================================

SCHEDULER MANAGEMENT:
- POST /api/billing/scheduler/run-now
  Manually trigger the daily billing check (SuperAdmin only)

- GET /api/billing/scheduler/history
  Get history of billing scheduler runs (SuperAdmin only)

- GET /api/billing/scheduler/status
  Check billing scheduler status (SuperAdmin only)

BILLING OPERATIONS:
- POST /api/billing/preview
  Calculate billing preview for a condominium

- GET /api/billing/events/{condominium_id}
  Get billing event history for audit trail (SuperAdmin only)

- PATCH /api/billing/seats/{condominium_id}
  Update seat count for a condominium (SuperAdmin only)

- POST /api/billing/confirm-payment/{condominium_id}
  Confirm manual/SINPE payment with partial payment support (SuperAdmin only)

- GET /api/billing/payments/{condominium_id}
  Get payment history for a specific condominium

- GET /api/billing/payments
  Get all condominiums with pending payments (SuperAdmin only)

- GET /api/billing/balance/{condominium_id}
  Get detailed billing balance showing invoice, paid, and due amounts

SEAT UPGRADE WORKFLOW:
- POST /api/billing/request-seat-upgrade
  Request additional seats (Admin only, requires SuperAdmin approval)

- GET /api/billing/my-pending-request
  Get current admin's pending upgrade request (Admin only)

- GET /api/billing/upgrade-requests
  Get all seat upgrade requests (SuperAdmin only)

- PATCH /api/billing/approve-seat-upgrade/{request_id}
  Approve or reject a seat upgrade request (SuperAdmin only)

- GET /api/billing/seat-status/{condominium_id}
  Get current seat usage status

BILLING INFO:
- GET /api/billing/info
  Get billing info for current user's condominium

- GET /api/billing/can-create-user
  Check if condominium can create new users within seat limit

- GET /api/billing/history
  Get billing transaction history (Admin only)

- POST /api/billing/upgrade-seats
  Upgrade seats (Stripe integration)

ENDPOINTS MIGRATED TO billing_super_admin_router (2 endpoints):
==============================================================
- GET /api/super-admin/billing/overview
  Paginated billing overview with aggregation pipeline (SuperAdmin only)

- GET /api/super-admin/billing/overview-legacy
  Legacy non-paginated billing overview (deprecated)

ENDPOINTS REMAINING IN api_router (billing-related):
===================================================
These endpoints are billing-related but follow different path patterns:

- PATCH /api/super-admin/condominiums/{condo_id}/billing
  Update condominium billing settings (SuperAdmin only)

- GET /api/condominiums/{condo_id}/billing
  Get billing info for a specific condominium (Admin only)

- PUT /api/condominiums/{condominium_id}/grace-period
  Update grace period for billing suspension (SuperAdmin only)

NEXT PHASE (PHASE 3):
====================
Move the business logic from server.py into this module's service.py
file, making the router fully self-contained. This will involve:

1. Moving helper functions (calculate_billing_preview, etc.) to service.py
2. Importing service functions into router.py
3. Removing duplicated code from server.py
4. Eventually extracting router.py endpoints to this file

TESTING CHECKLIST:
=================
- [x] Scheduler endpoints: run-now, history, status
- [x] Payment operations: preview, confirm-payment, balance
- [x] Payment queries: payments (all), payments/{condo_id}
- [x] Seat management: seats, seat-status, upgrade requests
- [x] Billing info: info, can-create-user, history
- [x] Super-admin: overview, overview-legacy
- [x] Condominium-level: billing settings, grace-period
"""

# This file serves as documentation for Phase 2.
# The actual router code is in server.py (billing_router and billing_super_admin_router)
# until Phase 3 when we complete the extraction.
