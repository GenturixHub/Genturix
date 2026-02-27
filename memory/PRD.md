# GENTURIX - Product Requirements Document

## Overview
Genturix is a multi-tenant security and condominium management platform built with React frontend and FastAPI backend.

## Core Features
- Multi-tenant condominium management
- User authentication with role-based access control
- Security module (panic buttons, alerts)
- HR management (guards, shifts, attendance)
- Billing system with Stripe integration
- Visitor management
- Reservations system

## Architecture

### Backend Modularization Status

| Module | Phase | Status | Details |
|--------|-------|--------|---------|
| billing | Complete | ✅ | Fully decoupled from server.py |
| users | Phase 2A/2B | ✅ | Core functions + models migrated |
| auth | Pending | 🔜 | In server.py |
| guards | Pending | 🔜 | In server.py |
| condominiums | Pending | 🔜 | In server.py |

### Module Structure Pattern
```
backend/modules/{module_name}/
├── __init__.py      # Exports
├── models.py        # Pydantic models
├── service.py       # Business logic
├── router.py        # API endpoints (if migrated)
└── permissions.py   # RBAC logic (if needed)
```

### Users Module - Migrated Components
- **service.py**: `count_active_users`, `count_active_residents`, `update_active_user_count`, `can_create_user`
- **models.py**: `RoleEnum`, `UserStatus`, `UserCreate`, `UserResponse`, `CreateUserByAdmin`, `CreateEmployeeByHR`, `UserStatusUpdateV2`

## Frontend Components

### Admin Billing Page (NEW - 2025-02-27)
**File:** `/app/frontend/src/pages/AdminBillingPage.js`

**Components:**
- `BillingOverviewCard` - Status, balance, seats info
- `BillingActions` - Dynamic actions based on status
- `PaymentHistoryTable` - Payment history
- `SeatUpgradeSection` - Pending upgrade requests
- `SeatUpgradeDialog` - Request more seats

**Key Features:**
- NO hardcoded prices
- All data from backend billing endpoints
- Dynamic actions based on billing status
- Connected to real billing engine

## Security Hardening (Completed)
- ✅ Stripe webhook signature verification
- ✅ Fail-closed mode for production webhooks
- ✅ MongoDB indexes for performance

## User Roles
- SuperAdmin: Platform-wide access
- Administrador: Condominium-level admin
- Supervisor: HR and guard management
- HR: Human resources
- Guarda: Security operations
- Residente: Resident access
- Estudiante: Student access

## API Endpoints Prefix
All backend routes use `/api` prefix for Kubernetes ingress routing.

### Key Billing Endpoints (Admin)
- `GET /api/billing/info` - Billing status and seat info
- `GET /api/admin/seat-usage` - Seat usage details
- `GET /api/billing/history` - Payment history
- `GET /api/billing/my-pending-request` - Pending upgrade request
- `POST /api/billing/request-seat-upgrade` - Request more seats

## Environment Configuration
- Frontend: REACT_APP_BACKEND_URL
- Backend: MONGO_URL, DB_NAME, STRIPE_WEBHOOK_SECRET

## Test Credentials
- Super Admin: superadmin@genturix.com / Admin123!
- Admin Test: admin@test.com / Admin123!
- Resident: test-resident@genturix.com / Admin123!
- Guard: guarda1@genturix.com / Guard123!

---

## Changelog

### 2025-02-27 (Current Session)
- **Users Module Phase 2B:** Migrated `CreateUserByAdmin`, `CreateEmployeeByHR`, `UserStatusUpdateV2` models
- **Admin Billing Page Redesign:** Complete rewrite of payments module
  - Removed all hardcoded prices ($1 per user)
  - Connected to real billing endpoints
  - Dynamic actions based on billing status
  - New component architecture (BillingOverviewCard, BillingActions, PaymentHistoryTable, SeatUpgradeSection)
- **server.py reduced:** ~100 lines removed (16,667 → 16,561)

### 2025-02-26
- **Users Module Phase 1:** Created module structure
- **Users Module Phase 2A:** Migrated core seat engine functions
- **UI Fix:** Added overflow-y-auto to SuperAdminDashboard

### Previous Session
- Completed billing module full decoupling (Phase 2 & 3)
- Implemented Stripe webhook signature verification
- Added fail-closed security for production
- Created MongoDB performance indexes

---

## Roadmap

### P0 - Critical ✅ COMPLETED
- [x] Billing module modularization
- [x] Security hardening (webhooks)
- [x] Users module Phase 2A (core functions)
- [x] Users module Phase 2B (models)
- [x] Admin Billing Page redesign

### P1 - High Priority
- [ ] Auth module modularization
- [ ] Guards module modularization
- [ ] Frontend component refactoring (SuperAdminDashboard, GuardUI)
- [ ] UI for deleting used pre-registrations
- [ ] Configure production Resend domain

### P2 - Medium Priority
- [ ] Condominiums module modularization
- [ ] Reservations module modularization
- [ ] CCTV module implementation
- [ ] HR performance reports

### P3 - Low Priority
- [ ] Additional audit logging
- [ ] Advanced analytics dashboard

---

## Technical Notes

### Why Endpoints Stay in server.py
The user endpoints remain in server.py because:
1. Heavy dependencies on shared resources (`db`, `log_audit_event`, `send_credentials_email`)
2. Low ROI for migration vs high risk of bugs
3. The core business logic (seat engine) is already modularized
4. Models are already in the module (no duplication)

### Billing Engine Integration
The new AdminBillingPage is fully integrated with the billing engine:
- Uses `GET /api/billing/info` for status
- Uses `GET /api/admin/seat-usage` for seat info
- Uses `POST /api/billing/request-seat-upgrade` for upgrades
- NO frontend calculations - all data comes from backend
