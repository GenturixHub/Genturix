# GENTURIX Enterprise Platform - PRD

## Last Updated: January 28, 2026

## Vision
GENTURIX is a security and emergency platform for real people under stress. Emergency-first design, not a corporate dashboard.

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
| Residente | Panic + Visitors | `/resident` |
| Guarda | Alerts + Visitors + Access | `/guard` |
| Estudiante | Courses + Subscription | `/student` |
| Admin | Full system | `/admin/dashboard` |

---

## DEMO CREDENTIALS

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@genturix.com | Admin123! |
| Guarda | guarda1@genturix.com | Guard123! |
| Residente | residente@genturix.com | Resi123! |
| Estudiante | estudiante@genturix.com | Stud123! |

---

## COMPLETED WORK (January 28, 2026)

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
│   └── server.py           # FastAPI with visitors, multi-tenant
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── ResidentUI.js    # Panic + Visitors tabs
│       │   ├── GuardUI.js       # Alerts + Visitors + Direct + Logbook
│       │   ├── StudentUI.js     # Courses + Plan + Notifications + Profile
│       │   ├── RRHHModule.js    # Unified HR module
│       │   └── AuditModule.js   # Admin audit
│       └── services/
│           └── api.js          # All API methods including visitors
└── memory/
    └── PRD.md
```
