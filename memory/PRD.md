# GENTURIX Enterprise Platform - PRD

## Last Updated: January 29, 2026 (Session 11 - Guard Absence Requests)

## Vision
GENTURIX is a security and emergency platform for real people under stress. Emergency-first design, not a corporate dashboard.

---

## PLATFORM STATUS: 100% PRODUCTION READY ✅

### Session 11 - Guard Absence Requests (January 29, 2026) ⭐⭐ P1
- ✅ **Guard UI - New "Ausencias" Tab (COMPLETE)**:
  - New 6th tab visible for Guards with CalendarOff icon
  - Shows list of guard's own absences with status badges (Aprobada/Pendiente/Rechazada)
  - "Solicitar" button opens request form dialog
- ✅ **Absence Request Form**:
  - Fields: Type (dropdown), Start Date, End Date, Reason (required), Notes (optional)
  - Client-side validation: end_date >= start_date, reason required
  - Success/error toast notifications
  - Submit disabled while sending
- ✅ **Backend Integration**:
  - `source: "guard"` field added to track origin of absence request
  - Audit logging includes: guard_id, condominium_id, type, dates, source
  - Guards can only view their own absences via `/api/guard/my-absences`
- ✅ **HR Workflow Enhanced**:
  - HR role added to approve/reject endpoints
  - Buttons visible for Admin, Supervisor, and HR roles
  - Complete flow: Guard creates → HR sees → HR approves/rejects → Guard sees updated status
- 📋 Test report: `/app/test_reports/iteration_18.json` - 100% pass rate (17 backend + all UI tests)

### Session 10 - Panic Alert Interaction + HR Modules (January 29, 2026) ⭐⭐⭐ P0
- ✅ **Panic Alert Interactive Modal (COMPLETE)**:
  - Click on alert card opens detailed modal (no page navigation)
  - **Resident Information**: Full name, apartment/house
  - **Alert Details**: Panic type, date/time, status (active/resolved), resolver name
  - **Resident Notes**: Yellow highlighted box with emergency description (IMPORTANT)
  - **Map Integration**: Embedded OpenStreetMap with marker at GPS coordinates
  - **Actions**: "Abrir en Google Maps" button, "IR A UBICACIÓN" navigation
  - **Resolution**: Textarea for guard notes, "MARCAR COMO ATENDIDA" button
  - Resolution notes saved to both `panic_events` and `guard_history` collections
- ✅ **HR Control Horario (COMPLETE)**:
  - HR role can now access `/api/hr/clock/status` and `/api/hr/clock/history`
  - Clock history scoped by `condominium_id` for proper multi-tenancy
  - Shows real clock-in/out records with employee name, type, timestamp
- ✅ **HR Absences Module (COMPLETE)**:
  - Create new absence requests (Guards can request, HR/Admin can view)
  - Approve/Reject actions for Admin/Supervisor
  - Status badges: Pending, Approved, Rejected
- 📋 Test report: `/app/test_reports/iteration_17.json` - 100% pass rate (22 tests)

### Session 9 - Critical Guard Clock-In/Out Fix (January 29, 2026) ⭐⭐⭐ P0
- ✅ **Guard Clock-In Not Working (CRITICAL)**:
  - Root cause 1: Shift overlap validation was including `completed` shifts, blocking creation of new shifts
  - Root cause 2: SuperAdmin creating shifts set `condominium_id=null` because it was taken from the user, not the guard
  - Fix 1: Changed overlap validation to only consider `scheduled` and `in_progress` shifts
  - Fix 2: Shift creation now uses guard's `condominium_id` as fallback when user doesn't have one
  - Added detailed logging to `/api/guard/my-shift` for debugging
  - Verified end-to-end flow with real user "juas" (j@j.com)
- ✅ **Backend Improvements**:
  - `POST /api/hr/shifts`: Now allows SuperAdmin role, uses guard's condo_id as fallback
  - `GET /api/guard/my-shift`: Now logs why shifts are rejected
  - `POST /api/hr/clock`: Shift validation working correctly
- ✅ **Frontend Stability**:
  - GuardUI.js error handling verified (no crashes)
  - Clock button enabled/disabled correctly based on shift availability
- 📋 Test reports: `/app/test_reports/iteration_16.json` - 100% pass rate

### Session 8 - Critical Multi-Tenant & Dynamic Form Fixes (January 28, 2026) ⭐⭐⭐ P0
- ✅ **Multi-Tenant Dashboard Isolation (CRITICAL)**:
  - All endpoints now filter by `condominium_id`
  - New condo admin sees ZERO data (users=1 self, guards=0, alerts=0, shifts=0)
  - Existing condo admin sees ONLY their condo's data
  - SuperAdmin sees global data
  - Fixed endpoints: `/dashboard/stats`, `/security/dashboard-stats`, `/security/panic-events`, `/security/access-logs`, `/hr/shifts`, `/hr/absences`, `/hr/guards`, `/hr/payroll`, `/users`
- ✅ **Dynamic Role Forms (CRITICAL)**:
  - Selecting role in Create User modal renders role-specific fields
  - Residente: apartment_number (required), tower_block, resident_type
  - Guarda: badge_number (required), main_location, initial_shift
  - HR: department, permission_level
  - Estudiante: subscription_plan, subscription_status
  - Supervisor: supervised_area
- ✅ **Backend Validation**:
  - Residente without apartment → 400 error
  - Guarda without badge → 400 error
  - role_data stored in user document
- 📋 Test report: `/app/test_reports/iteration_14.json` - 17/17 tests passed

### Session 7 - Production User & Credential Management (January 28, 2026)
- ✅ **Super Admin → Condo Admin Creation**:
  - Button in Condominiums table (UserPlus icon)
  - Modal with: Name, Email, Password (auto-generated), Phone
  - Credentials dialog with copy button and warning
  - Updates condominium with admin_id and admin_email
- ✅ **Role-Specific Dynamic Forms**:
  - **Residente**: Apartment (required), Tower/Block, Type (owner/tenant)
  - **Guarda**: Badge (required), Location, Shift + Creates guard record
  - **HR**: Department, Permission level
  - **Estudiante**: Subscription plan, Status
  - **Supervisor**: Supervised area
- ✅ **Backend Validation**:
  - Residente without apartment → 400 error
  - Guarda without badge → 400 error
  - Admin cannot create Admin/SuperAdmin roles
- ✅ **role_data Storage**: Stored in user document, returned in response, logged in audit
- ✅ **Immediate Login**: All created users can login immediately
- 📋 Test report: `/app/test_reports/iteration_13.json` - 100% pass rate (16/16)

### Session 6 - Condominium Admin User Management UI (January 28, 2026)
- ✅ **Full User Management Page** (`/admin/users`)
  - Stats cards: Total users, Active, Count by role
  - User table with name, email, role, status, created date
  - Search filter by name/email
  - Role filter dropdown
- ✅ **Create User Modal**:
  - Fields: Name, Email, Password (auto-generated), Role, Phone
  - Roles: Residente, Guarda, HR, Supervisor, Estudiante
  - Admin CANNOT create SuperAdmin or Administrador
  - Auto-assigns admin's condominium_id
- ✅ **Credentials Dialog**:
  - Password shown ONLY ONCE after creation
  - Warning: "Esta es la única vez que verás la contraseña"
  - Copy Credentials button (email + password)
  - Close: "He guardado las credenciales"
- ✅ **User Status Management**:
  - Toggle Active/Inactive with confirmation dialog
  - Cannot self-deactivate
- ✅ **Security & Audit**:
  - All actions logged to audit (user_created, user_updated)
  - Multi-tenancy enforced
- ✅ **Sidebar Updated**: "Usuarios" link for Administrador
- 📋 Test report: `/app/test_reports/iteration_12.json` - 100% pass rate (20/20)

### Session 5 - Role & Credential Management (January 28, 2026)
- ✅ **HR Role Implemented** - Full permissions for personnel management
- ✅ **HR Login & Redirect** - HR users login and redirect to /rrhh automatically
- ✅ **Admin User Creation Modal** - Admin can create users with ALL roles (Residente, Guarda, HR, Supervisor, Estudiante)
- ✅ **Super Admin Create Condo Admins** - POST /api/super-admin/condominiums/{id}/admin working
- ✅ **HR Recruitment Flow Complete** - Candidate → Interview → Hire → Auto-generate credentials
- ✅ **Multi-tenancy Enforced** - All users get condominium_id from creating admin
- 📋 Test report: `/app/test_reports/iteration_11.json` - 100% pass rate (23/23 tests)

### Session 4 Fixes (January 28, 2026)
- ✅ **Guard Login Fixed** - Login now works without "body stream already read" error
- ✅ **condominium_id Assignment** - All users/guards now have proper condominium_id
- ✅ **Guard UI Production Ready** - Clock In/Out, Alert Resolution, Visitor Management all working
- ✅ **Audit Logging** - All guard actions logged (login, clock, access, alerts)

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

### Session 5 - Role & Credential Management (Production Ready)
- ✅ **HR Role Complete:**
  - HR users can login independently with their own credentials
  - Auto-redirect to /rrhh on login
  - Access to all RRHH submodules (Shifts, Absences, Recruitment, etc.)
  - Cannot access payments, system config, or super admin features
- ✅ **Admin User Creation Modal:**
  - Unified "Crear Usuario" button in Admin Dashboard
  - Fields: Full Name, Email, Password (with Generate), Role, Phone
  - Role dropdown: Residente, Guarda, HR, Supervisor, Estudiante
  - Auto-assigns admin's condominium_id to new users
- ✅ **Super Admin User Creation:**
  - POST /api/super-admin/condominiums/{id}/admin creates condo admins
  - Can assign HR or Admin users to any condominium
- ✅ **HR Recruitment Flow (No Placeholders):**
  - Create candidates: POST /api/hr/candidates
  - Schedule interview: PUT /api/hr/candidates/{id}
  - Hire candidate: POST /api/hr/candidates/{id}/hire
  - Auto-generate credentials for hired guard/employee
  - Immediate role and condominium assignment
- ✅ **Login Redirects (All Roles):**
  - Admin → /admin/dashboard
  - HR → /rrhh
  - Supervisor → /rrhh
  - Guard → /guard
  - Resident → /resident
  - Student → /student
- ✅ **Security & Multi-Tenancy:**
  - Every created user has condominium_id
  - HR/Admin only see users from their condominium
  - Super Admin sees all

### Session 4 - Guard Role Critical Fixes (PRODUCTION BLOCKER)
- ✅ **Guard Login Fixed:** Resolved "body stream already read" error
- ✅ **condominium_id Bug Fixed:** 
  - Created `POST /api/admin/fix-orphan-users` endpoint
  - Fixed 23 users and 14 guards without condominium_id
  - Updated `seed_demo_data` to assign condominium_id to all demo users
- ✅ **Guard UI Production Ready:**
  - Clock In/Out working with status banner ("En turno" / "Sin fichar")
  - Alert resolution decreases active count correctly
  - Visitor Entry/Exit buttons working
  - Manual entry form creates access logs
  - History tab shows completed alerts and visits
- ✅ **Audit Logging Complete:**
  - login_success events logged
  - clock_in/clock_out events logged
  - access_granted/access_denied events logged
- ✅ **Test Coverage:** 100% pass rate (16/16 backend tests, all UI features)

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
- [ ] Performance evaluations in RRHH (marked "Coming Soon")

### P2 - Medium Priority
- [ ] Dashboard statistics per condominium
- [ ] Reservations module
- [ ] CCTV integration

### P3 - Low Priority
- [ ] Fix PostHog console error (cosmetic)
- [ ] Native app (React Native)
- [ ] Public API with rate limiting

---

## FILE STRUCTURE

```
/app/
├── backend/
│   ├── server.py              # FastAPI with visitors, multi-tenant, super-admin, fix-orphan-users
│   └── tests/
│       ├── test_super_admin.py # Super Admin API tests
│       └── test_guard_ui.py    # Guard UI tests (16 tests)
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── SuperAdminDashboard.js # Platform management (4 tabs)
│       │   ├── ResidentUI.js    # Panic + Visitors tabs
│       │   ├── GuardUI.js       # Alerts + Visitors + Registro + Historial (PRODUCTION READY)
│       │   ├── StudentUI.js     # Courses + Plan + Notifications + Profile
│       │   ├── RRHHModule.js    # Unified HR module
│       │   └── AuditModule.js   # Admin audit
│       └── services/
│           └── api.js          # All API methods including super-admin
├── test_reports/
│   └── iteration_10.json       # Guard UI test results (100% pass)
└── memory/
    └── PRD.md
```
