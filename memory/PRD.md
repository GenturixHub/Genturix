# GENTURIX Enterprise Platform - PRD

## Last Updated: January 28, 2026

## Vision
GENTURIX is a security and emergency platform for real people under stress. Emergency-first design, not a corporate dashboard.

---

## CORE BUSINESS MODEL

### Pricing
- **$1 per user per month** - Massive adoption model
- No corporate plans, no SaaS pricing
- Premium modules (additive):
  - +$2 Genturix School Pro
  - +$3 CCTV Integration
  - +$5 API Access

---

## ARCHITECTURE: MULTI-TENANT (3 LAYERS)

### Layer 1: Global Platform
- Super Admin controls
- Tenant (Condominium) management
- Module configuration per tenant

### Layer 2: Condominium/Tenant
- Each condominium has its own configuration
- Enabled/disabled modules
- User limits and billing

### Layer 3: Module Rules
- Each module has specific settings
- Role-based access within modules

### Multi-Tenant API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/condominiums` | POST | Create new condominium |
| `/api/condominiums` | GET | List all condominiums |
| `/api/condominiums/{id}` | GET | Get condominium details |
| `/api/condominiums/{id}` | PATCH | Update condominium |
| `/api/condominiums/{id}` | DELETE | Deactivate condominium |
| `/api/condominiums/{id}/users` | GET | Get condominium users |
| `/api/condominiums/{id}/billing` | GET | Get billing info |
| `/api/condominiums/{id}/modules/{module}` | PATCH | Enable/disable module |

---

## EMERGENCY SYSTEM (CORE DNA)

### Panic Button - 3 Types with Psychological Color Coding
1. 🔴 **Emergencia Médica** (RED) - Life threat, critical
2. 🟡 **Actividad Sospechosa** (AMBER/YELLOW) - Caution, observation
3. 🟠 **Emergencia General** (ORANGE) - Urgent, immediate action

### Each Panic Event:
- ✅ Captures GPS location automatically
- ✅ Registers emergency type
- ✅ Notifies ALL active guards
- ✅ Stored in Audit Logs with full details
- ✅ Vibration feedback on mobile devices
- ✅ Full-screen, touch-optimized buttons (min 120px height)
- ✅ Glow/pulse animations for urgency

---

## MODULES

### RRHH (Recursos Humanos) - Central Module
**IMPORTANTE: RRHH es el ÚNICO módulo de personal. Turnos NO es módulo separado.**

Sub-módulos dentro de RRHH:
1. **Solicitudes de Ausencia** - Vacaciones, permisos, aprobaciones
2. **Control Horario** - Entrada/salida, ajustes, reportes
3. **Planificación de Turnos** - Creación, asignación, calendario
4. **Reclutamiento** - Candidatos, pipeline, contratación
5. **Onboarding/Offboarding** - Accesos, equipos, desactivación
6. **Evaluación de Desempeño** - Evaluaciones, feedback, historial

**Rutas:**
- `/rrhh` → Módulo RRHH principal
- `/hr` → Redirige a `/rrhh` (legacy)
- `/shifts` → Redirige a `/rrhh` (legacy)

### Otros Módulos
- **Security** - Emergencias, accesos, monitoreo
- **Genturix School** - Cursos, progreso, certificados
- **Payments** - Stripe integration, $1/usuario/mes
- **Audit** - Logs de eventos del sistema
- **Reservations** - (Disabled by default)
- **Access Control** - Control de acceso
- **Messaging** - (Disabled by default)

---

## ROLES & INTERFACES

| Role | Interface | Route | Description |
|------|-----------|-------|-------------|
| Residente | Full-screen panic buttons | `/resident` | Emergency-first, one-touch activation |
| Guarda | Emergency response list | `/guard` | Active alerts, GPS coords, map links |
| Estudiante | Learning portal | `/student` | Courses, progress, certificates |
| Supervisor | Admin dashboard + RRHH | `/admin/dashboard`, `/rrhh` | Guards, shifts, monitoring |
| Administrador | Full system | `/admin/dashboard` | All modules access |

---

## TECH STACK

### Backend
- FastAPI + MongoDB + Motor (async)
- JWT Authentication with condominium_id
- Stripe Integration
- RESTful API with `/api` prefix
- Multi-tenant architecture

### Frontend (PWA Mobile-First)
- React 18
- Tailwind CSS + Shadcn/UI
- Progressive Web App (PWA)
- Service Worker for offline support
- Bottom navigation (mobile) / Sidebar (desktop)

---

## DEMO CREDENTIALS

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@genturix.com | Admin123! |
| Supervisor | supervisor@genturix.com | Super123! |
| Guarda | guarda1@genturix.com | Guard123! |
| Residente | residente@genturix.com | Resi123! |
| Estudiante | estudiante@genturix.com | Stud123! |

---

## COMPLETED WORK

### January 28, 2026
- ✅ Refactorización módulo RRHH - Turnos ahora es submódulo
- ✅ Eliminado ShiftsModule.js y HRModule.js (redundantes)
- ✅ Implementada arquitectura Multi-Tenant en backend
- ✅ Endpoints de gestión de condominios (CRUD)
- ✅ Endpoint de facturación por condominio
- ✅ Endpoint para habilitar/deshabilitar módulos
- ✅ Token JWT incluye condominium_id
- ✅ Redirecciones /hr y /shifts a /rrhh
- ✅ Testing completo (100% backend, 100% frontend)

### Previous Sessions
- ✅ PWA completo con manifest, service worker, icons
- ✅ Botón de pánico con 3 tipos y colores
- ✅ UIs específicas por rol (Resident, Guard, Student)
- ✅ Integración Stripe para pagos
- ✅ Sistema de autenticación JWT
- ✅ Navegación adaptativa (Sidebar/BottomNav)

---

## BACKLOG / FUTURE TASKS

### P1 - High Priority
- [ ] Push notifications para alertas de pánico
- [ ] Dashboard de estadísticas por condominio
- [ ] Reportes de facturación exportables

### P2 - Medium Priority
- [ ] Integración con servicios de mensajería
- [ ] Sistema de reservaciones
- [ ] Integración CCTV

### P3 - Low Priority
- [ ] App nativa (React Native)
- [ ] API pública con rate limiting
- [ ] Integraciones con IoT

---

## FILE STRUCTURE

```
/app/
├── backend/
│   ├── server.py           # FastAPI app with multi-tenant
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── public/
│   │   ├── manifest.json
│   │   ├── service-worker.js
│   │   └── index.html
│   └── src/
│       ├── App.js          # Routes with redirects
│       ├── pages/
│       │   ├── RRHHModule.js    # Central HR module
│       │   ├── ResidentUI.js    # Panic buttons
│       │   ├── GuardUI.js       # Emergency response
│       │   └── ...
│       └── components/
│           └── layout/
│               ├── Sidebar.js
│               └── BottomNav.js
└── memory/
    └── PRD.md
```
