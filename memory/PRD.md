# GENTURIX Enterprise Platform - PRD

## Last Updated: January 28, 2026 (Session 4 - Guard Role Critical Fixes)

## Vision
GENTURIX is a security and emergency platform for real people under stress. Emergency-first design, not a corporate dashboard.

---

## PLATFORM STATUS: 100% PRODUCTION READY ✅

### Session 4 Fixes (January 28, 2026)
- ✅ **Guard Login Fixed** - Login now works without "body stream already read" error
- ✅ **condominium_id Assignment** - All users/guards now have proper condominium_id
- ✅ **Guard UI Production Ready** - Clock In/Out, Alert Resolution, Visitor Management all working
- ✅ **Audit Logging** - All guard actions logged (login, clock, access, alerts)
- 📋 Full audit report: `/app/AUDIT_REPORT.md`
- 📋 Test report: `/app/test_reports/iteration_10.json` - 100% pass rate

---

## CORE BUSINESS MODEL

### Pricing
- **$1 per user per month** - Massive adoption model
- Premium modules (additive): +$2 School Pro, +$3 CCTV, +$5 API Access

---

## ARCHITECTURE: MULTI-TENANT (3 LAYERS)

### Layer 1: Global Platform (Super Admin)
### Layer 2: Condominium/Tenant 
### Layer 3: Module Rules

### Multi-Tenant API: `/api/condominiums/*`

---

## VISITOR ACCESS FLOW (CRITICAL)

**FLOW: Resident CREATES → Guard EXECUTES → Admin AUDITS**

### 1. Resident Pre-Registration
- Tab "Visitas" in ResidentUI
- Creates PENDING visitor record with:
  - Full name, National ID (Cédula), Vehicle plate
  - Visit type (familiar, friend, delivery, service, other)
  - Expected date/time, Notes
- Resident can CANCEL pending visitors
- Resident does NOT approve entry/exit
- Resident does NOT receive guard notifications

### 2. Guard Execution
- Tab "Visitas" in GuardUI shows expected visitors
- Search by name, plate, cédula, or resident
- Actions:
  - Confirm identity
  - Register ENTRY → Status: `entry_registered`
  - Register EXIT → Status: `exit_registered`
- Tab "Directo" for walk-in visitors (no pre-registration)

### 3. Admin Audit
- All visitor events in Auditoría module
- Shows: visitor, resident who created, guard who executed, timestamps

### Visitor API Endpoints
| Endpoint | Method | Role | Description |
|----------|--------|------|-------------|
| `/api/visitors/pre-register` | POST | Resident | Create visitor |
| `/api/visitors/my-visitors` | GET | Resident | List my visitors |
| `/api/visitors/{id}` | DELETE | Resident | Cancel pending |
| `/api/visitors/pending` | GET | Guard | Expected visitors |
| `/api/visitors/{id}/entry` | POST | Guard | Register entry |
| `/api/visitors/{id}/exit` | POST | Guard | Register exit |
| `/api/visitors/all` | GET | Admin | All visitors |

---

## EMERGENCY SYSTEM (CORE DNA)

### Panic Button - 3 Types (NOT MODIFIED)
1. 🔴 **Emergencia Médica** (RED)
2. 🟡 **Actividad Sospechosa** (AMBER)
3. 🟠 **Emergencia General** (ORANGE)

---

## UI ARCHITECTURE (Tab-Based, No Vertical Bloat)

### ResidentUI Tabs
1. **Emergencia** - Panic buttons
2. **Visitas** - Pre-register visitors

### GuardUI Tabs (Operational Panel)
1. **Alertas** - Active panic alerts with compact cards, MAPA/ATENDIDA buttons
2. **Visitas** - Pre-registered visitors (entry/exit execution)
3. **Registro** - Manual walk-in registration form
4. **Historial** - Read-only past records (Today / Last 7 days filter)

### StudentUI Tabs
1. **Cursos** - Course list with filters
2. **Plan** - Subscription & pricing ($1/user/month explained)
3. **Avisos** - Notifications
4. **Perfil** - Profile & logout

---

## MODULES

### RRHH (Unified HR Module)
- "Turnos" is a SUB-module, NOT separate
- Routes: `/rrhh` (legacy `/hr`, `/shifts` redirect here)

### Other Modules
- Security, School, Payments, Audit, Reservations, Access Control, Messaging

---

## ROLES & INTERFACES

| Role | Interface | Route |
|------|-----------|-------|
| SuperAdmin | Platform Management | `/super-admin` |
| Residente | Panic + Visitors | `/resident` |
| Guarda | Alerts + Visitors + Access | `/guard` |
| Estudiante | Courses + Subscription | `/student` |
| Admin | Full system | `/admin/dashboard` |

---

## SUPER ADMIN DASHBOARD

### Overview Tab (Resumen)
- 4 KPI Cards: Condominios, Usuarios, MRR (USD), Alertas Activas
- Quick Actions: Nuevo Condominio, Crear Demo, Ver Usuarios, Ver Auditoría
- Business model display: $1 USD/usuario/mes

### Condominios Tab
- Table: Name, Status, Users, MRR, Actions
- Search & Filter (Todos/Activos/Demo/Suspendidos)
- Status dropdown: Activar, Modo Demo, Suspender
- Create new condominium dialog

### Usuarios Tab
- Global user list across all tenants
- Filters: By condominium, By role
- Actions: Lock/Unlock users
- Stats: Total, Activos, Bloqueados

### Contenido Tab (Placeholder)
- Genturix School content management (coming soon)

### Super Admin API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/super-admin/stats` | GET | Platform-wide KPIs |
| `/api/super-admin/users` | GET | All users with filters |
| `/api/super-admin/users/{id}/lock` | PUT | Lock user |
| `/api/super-admin/users/{id}/unlock` | PUT | Unlock user |
| `/api/super-admin/condominiums/{id}/make-demo` | POST | Convert to demo |
| `/api/super-admin/condominiums/{id}/status` | PATCH | Change status |
| `/api/super-admin/condominiums/{id}/pricing` | PATCH | Update pricing |

---

## DEMO CREDENTIALS

| Role | Email | Password |
|------|-------|----------|
| SuperAdmin | superadmin@genturix.com | SuperAdmin123! |
| Admin | admin@genturix.com | Admin123! |
| Guarda | guarda1@genturix.com | Guard123! |
| Residente | residente@genturix.com | Resi123! |
| Estudiante | estudiante@genturix.com | Stud123! |

---

## COMPLETED WORK (January 28, 2026)

### Session 3 - Production Release Preparation
- ✅ **New HR Role:** Added `HR` to RoleEnum - manages employees, not payments/modules
- ✅ **HR Recruitment Full Flow:**
  - `POST /api/hr/candidates` - Create candidate
  - `PUT /api/hr/candidates/{id}` - Update status (applied → interview → hired/rejected)
  - `POST /api/hr/candidates/{id}/hire` - Creates user account + guard record
  - `PUT /api/hr/candidates/{id}/reject` - Reject candidate
- ✅ **HR Employee Management:**
  - `POST /api/hr/employees` - Create employee directly (without recruitment)
  - `PUT /api/hr/employees/{id}/deactivate` - Deactivate employee + user
  - `PUT /api/hr/employees/{id}/activate` - Reactivate employee + user
- ✅ **Admin User Management:**
  - `POST /api/admin/users` - Admin creates Resident/HR/Guard/Supervisor
  - `GET /api/admin/users` - List users in admin's condominium
- ✅ **Super Admin → Condo Admin Flow:**
  - `POST /api/super-admin/condominiums/{id}/admin` - Create condo administrator
- ✅ **Frontend Recruitment Module:** Real data, no placeholders
- ✅ **Test Coverage:** 30/30 backend tests passed

### Session 3 - HR Module Production Backend
- ✅ **HR Shifts CRUD:** POST/GET/PUT/DELETE /api/hr/shifts with validations
  - Employee active validation
  - Time format validation (ISO 8601)
  - Overlap prevention
  - Multi-tenant support (condominium_id)
- ✅ **HR Clock In/Out:** POST /api/hr/clock, GET /api/hr/clock/status, /history
  - Prevents double clock-in
  - Requires clock-in before clock-out
  - Calculates hours worked
  - Updates guard total_hours
- ✅ **HR Absences:** Full workflow POST/GET/PUT (approve/reject)
  - Date validation
  - Type validation (vacaciones, permiso_medico, personal, otro)
  - Overlap prevention
  - Admin approval/rejection workflow
- ✅ **Frontend Connected:** Real API calls, no placeholder data
- ✅ **Audit Logging:** All HR actions logged

### Session 3 - Pre-Production Audit Fixes
- ✅ **P1 FIX:** Edit Employee modal in RRHH (full CRUD with PUT /api/hr/guards/{id})
- ✅ **P2 FIX:** Super Admin Quick Actions wired to tab navigation
- ✅ **P3 MARK:** RRHH placeholders as "Próximamente" (Control Horario, Ausencias, Reclutamiento, Evaluación)
- ✅ **AUDIT:** Full platform audit with 99% working status
- ✅ **NEW ENDPOINT:** PUT /api/hr/guards/{id} for updating guard details

### Session 3 - Super Admin Dashboard
- ✅ Super Admin Dashboard with 4 tabs (Resumen, Condominios, Usuarios, Contenido)
- ✅ Platform-wide KPIs (condominiums, users, MRR, alerts)
- ✅ Condominium management (list, status change, modules config, pricing)
- ✅ Global user oversight with filters and lock/unlock actions
- ✅ Content management placeholder for Genturix School
- ✅ Backend fixes: patch() method in api.js, SuperAdmin role in endpoints
- ✅ Test suite: /app/backend/tests/test_super_admin.py

### Session 2
- ✅ Visitor flow correction: Resident creates → Guard executes → Admin audits
- ✅ ResidentUI Tab "Visitas" with pre-registration form
- ✅ GuardUI Tab "Visitas" for expected visitors + "Directo" for walk-ins
- ✅ All visitor API endpoints implemented and tested
- ✅ Audit integration for all visitor events

### Session 1
- ✅ RRHH module refactor (Turnos as sub-module)
- ✅ Multi-tenant backend architecture
- ✅ Guard/Student/Resident UI refactors (tab-based)
- ✅ Student subscription tab with clear pricing

---

## BACKLOG

### P1 - High Priority
- [ ] Push notifications for panic alerts
- [ ] Dashboard statistics per condominium

### P2 - Medium Priority
- [ ] Reservations module
- [ ] CCTV integration

### P3 - Low Priority
- [ ] Native app (React Native)
- [ ] Public API with rate limiting

---

## FILE STRUCTURE

```
/app/
├── backend/
│   ├── server.py              # FastAPI with visitors, multi-tenant, super-admin
│   └── tests/
│       └── test_super_admin.py # Super Admin API tests
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── SuperAdminDashboard.js # Platform management (4 tabs)
│       │   ├── ResidentUI.js    # Panic + Visitors tabs
│       │   ├── GuardUI.js       # Alerts + Visitors + Direct + Logbook
│       │   ├── StudentUI.js     # Courses + Plan + Notifications + Profile
│       │   ├── RRHHModule.js    # Unified HR module
│       │   └── AuditModule.js   # Admin audit
│       └── services/
│           └── api.js          # All API methods including super-admin
└── memory/
    └── PRD.md
```
