# GENTURIX Enterprise Platform - PRD

## Last Updated: January 21, 2026

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

## EMERGENCY SYSTEM (CORE DNA)

### Panic Button - 3 Types
1. 🚑 **Emergencia Médica** - Medical emergency requiring immediate attention
2. 👁️ **Actividad Sospechosa** - Suspicious activity requiring verification
3. 🚨 **Emergencia General** - Other emergency requiring immediate response

### Each Panic Event:
- ✅ Captures GPS location automatically
- ✅ Registers emergency type
- ✅ Notifies ALL active guards
- ✅ Stored in Audit Logs with full details
- ✅ Vibration feedback on mobile devices

---

## ROLES & INTERFACES

| Role | Interface | Route | Description |
|------|-----------|-------|-------------|
| Residente | Full-screen panic buttons | `/resident` | Emergency-first, one-touch activation |
| Guarda | Emergency response list | `/guard` | Active alerts, GPS coords, map links |
| Estudiante | Learning portal | `/student` | Courses, progress, certificates |
| Supervisor | Admin dashboard | `/admin/dashboard` | Guards, shifts, monitoring |
| Administrador | Full system | `/admin/dashboard` | All modules access |

---

## TECH STACK

### Backend (NOT MODIFIED)
- FastAPI + MongoDB + Motor (async)
- JWT Authentication
- Stripe Integration
- RESTful API with `/api` prefix

### Frontend (PWA Mobile-First)
- React 18
- Tailwind CSS + Shadcn/UI
- Progressive Web App (PWA)
- Service Worker for offline support
- Bottom navigation (mobile) / Sidebar (desktop)

---

## PWA IMPLEMENTATION (COMPLETED)

### Configuration Files
- `/app/frontend/public/manifest.json` - PWA manifest with icons, shortcuts
- `/app/frontend/public/service-worker.js` - Cache strategy, offline support
- `/app/frontend/public/index.html` - Meta tags, iOS support, install prompt

### Mobile-First Components
- `/app/frontend/src/components/layout/BottomNav.js` - Role-based mobile navigation
- `/app/frontend/src/components/layout/DashboardLayout.js` - Adaptive layout (mobile/desktop)

### Role-Specific UIs
- `/app/frontend/src/pages/ResidentUI.js` - Emergency buttons full-screen
- `/app/frontend/src/pages/GuardUI.js` - Emergency response with maps
- `/app/frontend/src/pages/StudentUI.js` - Learning interface
- `/app/frontend/src/pages/DashboardPage.js` - Admin responsive dashboard

### PWA Features
- ✅ Installable on Android/iOS
- ✅ Safe area support (notch, home indicator)
- ✅ 44px minimum touch targets
- ✅ Vibration on emergency alerts
- ✅ Direct links to Google Maps/Apple Maps
- ✅ Direct call to 911 button
- ✅ Install prompt after 30 seconds
- ✅ Service worker with network-first cache
- ✅ PWA shortcuts for quick emergency access

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

## NEXT SESSION PRIORITIES

### 1. Security Flows Review
- [ ] Auth flow validation (JWT tokens, refresh)
- [ ] Role-based access control per UI
- [ ] Session management
- [ ] Protected routes verification

### 2. Panic Event Flow E2E
- [ ] Resident triggers panic → Guards notified
- [ ] GPS capture accuracy
- [ ] Guard resolution flow
- [ ] Audit log verification

### 3. Production Readiness Checklist
- [ ] PWA audit (Lighthouse)
- [ ] Performance optimization
- [ ] Error handling
- [ ] Environment variables
- [ ] API security headers
- [ ] Rate limiting
- [ ] Database indexes

---

## FILE STRUCTURE

```
/app/frontend/
├── public/
│   ├── manifest.json          # PWA config
│   ├── service-worker.js      # Offline support
│   ├── index.html             # Meta tags, PWA setup
│   └── icons/                 # App icons
├── src/
│   ├── index.css              # Mobile-first styles
│   ├── App.js                 # Routes with role-based redirect
│   ├── contexts/
│   │   └── AuthContext.js     # JWT auth state
│   ├── services/
│   │   └── api.js             # API client
│   ├── components/layout/
│   │   ├── BottomNav.js       # Mobile navigation
│   │   ├── Sidebar.js         # Desktop navigation
│   │   ├── Header.js          # Desktop header
│   │   └── DashboardLayout.js # Adaptive layout
│   └── pages/
│       ├── LoginPage.js       # Responsive login
│       ├── PanelSelectionPage.js
│       ├── ResidentUI.js      # Emergency buttons
│       ├── GuardUI.js         # Emergency response
│       ├── StudentUI.js       # Learning portal
│       ├── DashboardPage.js   # Admin dashboard
│       ├── SecurityModule.js  # Security management
│       ├── HRModule.js        # Human resources
│       ├── SchoolModule.js    # Genturix School
│       ├── PaymentsModule.js  # $1/user pricing
│       └── AuditModule.js     # Activity logs
```

---

## STATUS: PWA Mobile-First Architecture Complete ✅
