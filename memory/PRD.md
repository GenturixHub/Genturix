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

| Module | Phase | Status |
|--------|-------|--------|
| billing | Complete | ✅ Fully decoupled from server.py |
| users | Phase 1 | ✅ Structure created, models defined |
| auth | Pending | 🔜 In server.py |
| guards | Pending | 🔜 In server.py |
| condominiums | Pending | 🔜 In server.py |

### Module Structure Pattern
```
backend/modules/{module_name}/
├── __init__.py      # Exports
├── models.py        # Pydantic models
├── service.py       # Business logic
├── router.py        # API endpoints
└── permissions.py   # RBAC logic (if needed)
```

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

## Environment Configuration
- Frontend: REACT_APP_BACKEND_URL
- Backend: MONGO_URL, DB_NAME, STRIPE_WEBHOOK_SECRET

## Test Credentials
- Super Admin: superadmin@genturix.com / Admin123!
- Resident: test-resident@genturix.com / Admin123!
- Guard: guarda1@genturix.com / Guard123!

---

## Changelog

### 2025-02-26
- **Users Module Phase 1:** Created module structure with models, permissions placeholder, empty router and service
- **UI Fix:** Added overflow-y-auto to SuperAdminDashboard main container

### Previous Session
- Completed billing module full decoupling (Phase 2 & 3)
- Implemented Stripe webhook signature verification
- Added fail-closed security for production
- Created MongoDB performance indexes

---

## Roadmap

### P0 - Critical
- [x] Billing module modularization
- [x] Security hardening (webhooks)
- [ ] Users module Phase 2 (move logic)
- [ ] Users module Phase 3 (cleanup server.py)

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
