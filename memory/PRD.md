# GENTURIX - Product Requirements Document

## Overview
Genturix is a multi-tenant security and condominium management platform built with React frontend and FastAPI backend.

## Multi-Tenant Security Patch (2026-02-28) ✅ COMPLETE

### PART 1: Visits Data Leak (CRITICAL) - FIXED
- **Status:** ✅ Fixed and Verified
- **File:** `backend/server.py`
- **Changes:**
  - `/authorizations/my` (line 5387) now filters by `condominium_id`
  - All visit-related endpoints verified to have tenant isolation
- **Test:** 100% pass rate on multi-tenant isolation tests

### PART 2: Audit Logs Not Recording - FIXED
- **Status:** ✅ Fixed and Verified
- **File:** `backend/server.py`
- **Changes:**
  - `log_audit_event()` now accepts `condominium_id` and `user_email` params
  - Updated access approval/rejection to include condo_id in audit logs
  - Reservation creation includes condo_id
  - Visitor check-in includes condo_id
- **Test:** Audit log created with `condominium_id=46b9d344...` after approval action

### PART 3: Profile Image Not Updating - FIXED
- **Status:** ✅ Fixed and Verified
- **Files:**
  - `frontend/src/pages/ProfilePage.js` - Added queryClient cache invalidation
- **Changes:**
  - Added `queryClient.invalidateQueries({ queryKey: profileKeys.own() })`
  - Added `queryClient.invalidateQueries({ queryKey: profileKeys.all })`
  - Proper import of `useQueryClient` and `profileKeys`
- **Test:** Profile update flow verified via Playwright

### PART 4: System Flow Logging - ADDED
- **Status:** ✅ Implemented
- **Markers Added:**
  - `[FLOW] audit_event_logged`
  - `[FLOW] profile_image_updated`
  - `[FLOW] visitor_entry_registered`
  - `[FLOW] reservation_created`

---

## System Flow Patch (2026-02-28) ✅ COMPLETE

### Password Reset Flow - Enhanced Logging
- **Status:** ✅ Enhanced with debug logging
- **File:** `backend/server.py`
- **Changes:**
  - Added `[RESET PASSWORD VERIFY]` debug logs
  - Logs email, code_hash_match, expires_at, attempt_count
  - Added `[FLOW] password_reset_success` marker
- **Verified:** Code storage, lookup, expiration, rate limiting all working

### Resident Approval Email - Enhanced Logging
- **Status:** ✅ Enhanced with flow logging
- **File:** `backend/server.py`
- **Changes:**
  - Added `[FLOW] access_request_approved` marker
  - Added `[EMAIL TRIGGER] resident_credentials` with details
  - Added explicit success/error logging for email delivery
- **Test:** Email sent successfully with ID: 176b49cd-5007-4629-a59b-eb77368d60a1

### Seat Upgrade Approval Email - NEW
- **Status:** ✅ Implemented
- **File:** `backend/server.py`
- **Changes:**
  - Added email notification when SuperAdmin approves upgrade
  - Email includes: condo name, seat counts, effective date, new amount
  - Added `[EMAIL TRIGGER] seat_upgrade_approved` logging
- **Location:** `approve_seat_upgrade()` endpoint

### Billing Events UI Panel - NEW
- **Status:** ✅ Implemented
- **Files:**
  - `frontend/src/pages/AdminBillingPage.js` - BillingEventsPanel component
  - `frontend/src/services/api.js` - getBillingEvents() method
- **Features:**
  - Displays billing event timeline
  - Color-coded event types
  - Show more/less toggle
  - Connected to `GET /api/billing/events/{condo_id}`

### billing_logs Deprecated
- **Status:** ⚠️ Marked as deprecated
- **File:** `backend/server.py`
- **Action:** Use `log_billing_engine_event()` instead
- **Existing data:** Preserved (not deleted)

---

## Previous P0 Stability Patch (2026-02-28)

### PART 1: Admin Dashboard Scroll Fix ✅ COMPLETED
- **Status:** ✅ Fixed and Verified
- **File:** `components/layout/DashboardLayout.js`
- **Change:** 
  - Changed outer container from `min-h-screen` to `h-screen overflow-hidden`
  - Inner flex container uses `h-screen` for proper height constraint
  - `main` element has `flex-1 overflow-y-auto min-h-0` for correct flex scroll behavior
- **Test Result:** scrollHeight=936, clientHeight=436, scroll from 0 to 200 worked

### PART 2: Resident Credential Email on Approval ✅ COMPLETED
- **Status:** ✅ Fixed and Verified
- **File:** `backend/server.py` - `send_access_approved_email` function (line ~13574)
- **Changes:**
  - Now uses centralized `send_email` service from `services/email_service.py`
  - Uses `get_sender()` for correct sender address
  - Uses `get_user_credentials_email_html()` template for consistent branding
  - Enhanced logging: `[EMAIL TRIGGER]`, `[EMAIL SERVICE]`, `[EMAIL SENT]`
  - Proper error handling with try/except and logging
- **Test Result:** `email_sent: true` returned from approval endpoint, email ID logged

### Email Service Health
- **Endpoint:** `GET /api/email/debug` (SuperAdmin only)
- **Status:** HEALTHY
- **Sender:** `Genturix Security <no-reply@genturix.com>`
- **Resend API:** Configured and working

---

## Previous Feature Patch (2026-02-28)

### PART 3: Forgot Password Feature
- **Status:** ✅ Implemented
- **Frontend:** `/app/frontend/src/pages/ForgotPasswordPage.js`
- **Route:** `/forgot-password`
- **Backend Endpoints:**
  - `POST /api/auth/request-password-reset` - Sends 6-digit code via email
  - `POST /api/auth/reset-password` - Validates code, updates password
- **Security:**
  - Codes expire in 10 minutes
  - Codes are hashed before storage
  - Max 5 attempts per code
  - Single use (deleted after success)
  - No email enumeration (always returns success message)

## Latest Corrective Patch (2026-02-28)

### PART 1: Carousel Reverted to Simple Swipe
- Removed: `useMotionValue`, `animate()`, `drag="x"`, `dragConstraints`, `dragElastic`
- Added: `react-swipeable` with `delta: 70`
- Behavior: Simple left/right swipe, no drag interaction
- File: `frontend/src/features/resident/ResidentHome.jsx`

### PART 2: Audit Log Multi-Tenant Isolation (CRITICAL FIX)
- `/api/audit/logs`: Now filters by `condominium_id` for non-SuperAdmin users
- `/api/audit/stats`: Now scoped by tenant
- SuperAdmin sees ALL logs, others see ONLY their condominium
- File: `backend/server.py` lines 12279-12360

### PART 3: Global Audit for SuperAdmin
- New endpoint: `GET /api/super-admin/audit/global`
- Returns enriched logs with `user_email` and `condominium_name`
- SuperAdmin only access

### PART 4: Frontend Audit Toggle
- Added `isGlobalView` toggle for SuperAdmin
- Label: "Vista Global del Sistema"
- File: `frontend/src/pages/AuditModule.js`

### PART 5: Security Verified
- `/api/authorizations`: ✅ tenant isolated
- `/api/reservations`: ✅ tenant isolated
- `/api/visits`: ✅ tenant isolated
- `/api/directory`: ✅ tenant isolated
- `/api/audit/logs`: ✅ NOW tenant isolated

### ADDITIONAL: Mobile Form Fix (JoinPage)
- Changed from `flex items-center justify-center` to `overflow-y-auto`
- Added `pb-32` for safe area spacing
- Submit button now always reachable on mobile
- File: `frontend/src/pages/JoinPage.js`

## Latest Stability Patch (2026-02-28)

### Changes Applied
| Part | Description | Status |
|------|-------------|--------|
| PART 1 | Password change flow | ✅ Verified (not modified) |
| PART 2 | Double API prefix `/api/api/` | ✅ Fixed in SuperAdminDashboard.js |
| PART 3 | Swipe navigation carousel | ✅ Threshold set to 80px |
| PART 4 | PDF export | ✅ Already correct (opacity:0, z-index:-1) |
| PART 5 | Danger zone protection | ✅ Already implemented |
| PART 6 | Pricing text `$1` | ✅ Already removed |
| PART 7 | Email service (Resend) | ✅ Verified, logging added |
| PART 8 | Email debug endpoint | ✅ GET /api/email/debug working |
| PART 9 | Rate limiting | ✅ Added to change-password |
| PART 10 | Logging | ✅ Added [AUTH EVENT] logging |

### Files Modified
- `frontend/src/pages/SuperAdminDashboard.js` - Fixed `/api/api/` → `/`
- `frontend/src/features/resident/ResidentHome.jsx` - Threshold 80px
- `backend/server.py` - Rate limiting + AUTH logging

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

### 2025-02-28 (Current Session - Resend Email Integration)
- **Full Resend Email Integration Completed:**
  - Created centralized email service at `/app/backend/services/email_service.py`
  - Integrated email notifications in 5 system workflows:
    1. **Condominium Creation:** Welcome email to admin with credentials
    2. **User Account Creation:** Credentials email with login info
    3. **Password Reset:** Reset email with temporary password
    4. **Visitor Preregistration:** Notification email to guards
    5. **Emergency Alerts:** Alert email to administrators
  - Added 7 HTML email templates with Genturix branding
  - Implemented fail-safe behavior (try/except) - API never breaks if email fails
  - Added `[EMAIL SENT] <recipient>` logging for production monitoring
  - Test endpoint: `GET /api/test-email?email=` returns `{status:"sent"}` or `{status:"error"}`
  - Service status endpoint: `GET /api/email/service-status` (SuperAdmin only)
  - **SANDBOX MODE:** Currently using `onboarding@resend.dev` until `gentrix.com` domain is verified
  - When domain is verified, update `get_sender()` in email_service.py to return `DEFAULT_SENDER`
- **$1 Pricing Text Removal COMPLETED:** Removed the last remaining instance of pricing text from SuperAdminDashboard.js line 822 (MRR card footer that showed "${stats?.revenue?.price_per_user || 1}/usuario/mes")
- **All 5 Pre-Production Fixes Verified:**
  1. ✅ Carousel Interactive Drag (ResidentHome.jsx) - useMotionValue with drag='x'
  2. ✅ PDF Export Fix (ResidentVisitHistory.jsx) - html2pdf.js with opacity:0 container
  3. ✅ Danger Zone Protection (SuperAdminDashboard.js) - Password verification modal
  4. ✅ $1 Pricing Text Removed - No marketing text visible
  5. ✅ Email Service (email_service.py) - Resend integration working

### 2025-02-28 (Previous Session)
- **P0 Resident Carousel Fix:** Resolved critical mobile UX bug in ResidentHome.jsx
  - Fixed black empty space at bottom of all modules
  - Changed from viewport pixel widths to percentage-based (100/TAB_ORDER.length)%
  - Added paddingBottom to each module for bottom nav clearance
  - Removed conflicting swipe handlers from ResidentLayout
  - Improved drag physics: dragMomentum=false, dragElastic=0.15
  - Single-module transition constraint in handleDragEnd
  - Test credentials: test-resident@genturix.com / Admin123!
- **Carousel Page Indicators:** Added visual dots above bottom nav (5 dots, active=cyan)
- **Pre-production Patch Set (3 fixes):**
  1. **Visitor Preregistration Notifications:** Guards now receive notifications when residents create authorizations. Added logic in `POST /api/authorizations` to create `guard_notifications` entries and send push notifications.
  2. **PDF Download Fix:** Changed `ResidentVisitHistory.jsx` from `window.print()` to `html2pdf.js` with `.save()` for automatic file download.
  3. **Privacy Section in Profile:** Added Privacy section with Accordion for "Cambiar Contraseña" in `EmbeddedProfile.jsx`. Works for all roles (resident, guard, admin, superadmin).
- **Stability Patch Set (4 fixes):**
  1. **Interactive Swipe Carousel:** Restored fully interactive drag using `useMotionValue` - content follows finger during drag, snaps on release.
  2. **Persistent 7-Day Cache:** TanStack Query cache now persists to localStorage for 7 days. App loads cached data instantly, background refetch updates data.
  3. **Service Worker API Cache:** v15 adds StaleWhileRevalidate for API GET requests (/api/profile, /api/notifications, /api/directory, /api/visits, /api/authorizations) with 24h expiry.
  4. **PWA Icons 85% Size:** Regenerated all icons with logo filling 85% of canvas for larger visual presence in Android launcher.
- **Carousel Navigation Fix:**
  - Removed conflicting `animate()` calls that prevented interactive drag
  - Simplified drag logic to use distance-based threshold (80px) instead of velocity
  - Removed dot indicators completely (bottom nav already shows position)
  - Clean UI without blue circle overlay
- **PDF Export Fix:**
  - Fixed blank PDF issue caused by html2canvas capturing hidden content
  - Container now uses `position: fixed; opacity: 0` instead of `position: absolute; left: -9999px`
  - Added 300ms delay before capture to ensure DOM renders
  - Added `backgroundColor: '#ffffff'` to html2canvas options
  - PDF now contains full visit history content (verified: 3KB+ file with data)
- **Pre-Production Security & Stability Patch:**
  1. **Resend Email:** Already configured and functional (resend==2.21.0)
  2. **Carousel Swipe:** Improved threshold to 20% of viewport width for natural feel
  3. **PDF Export:** Already fixed (visible container, 300ms delay)
  4. **Danger Zone Protection:** SuperAdmin system reset now requires password verification:
     - Hidden behind "Acceder a Controles Avanzados" button
     - Modal requires SuperAdmin password verification
     - Confirmation requires typing "DELETE SYSTEM"
  5. **Price Text Removed:** Eliminated "$1 USD / usuario / mes" marketing text from SuperAdmin dashboard
- **Production Email Service (Resend):**
  - Created centralized email service at `/app/backend/services/email_service.py`
  - Standard sender: `Genturix Security <no-reply@genturix.com>`
  - Email templates: welcome, password reset, notifications, emergency alerts
  - Test endpoints: `GET /api/test-email?email=...` and `GET /api/email/service-status`
  - Async sending with proper error handling and logging
  - Compatible with Railway environment variables (RESEND_API_KEY)

### 2025-02-27 (Previous Session)
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
- [x] PWA manifest.json fix (2025-02-27)
  - Added `"id": "/"` for PWA identity
  - Removed broken `screenshots` section (files didn't exist)
  - Removed broken `shortcuts` section (icons didn't exist)
  - All 8 icons verified and accessible
- [x] **Resident Carousel Layout Fix (2025-02-28)**
  - Fixed black empty space at bottom of modules
  - Implemented percentage-based widths instead of viewport pixels
  - Added proper paddingBottom for bottom nav clearance
  - Improved drag physics: single-module transitions, dragMomentum=false
  - All 5 modules verified working (Emergency, Visits, Reservations, Directory, Profile)
- [x] **Carousel Page Indicators (2025-02-28)**
  - Added visual dot indicators showing current module position
  - 5 dots positioned above bottom nav (fixed position)
  - Active dot: cyan (#22d3ee), 5px
  - Inactive dots: white/20% opacity, 3px
  - Clickable for direct navigation between modules
  - Smooth 0.2s transition animation

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
