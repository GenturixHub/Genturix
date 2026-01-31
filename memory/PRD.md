# GENTURIX Enterprise Platform - PRD

## Last Updated: January 31, 2026 (Session 25 - Onboarding Wizard Complete)

## Vision
GENTURIX is a security and emergency platform for real people under stress. Emergency-first design, not a corporate dashboard.

---

## PLATFORM STATUS: ✅ FULLY MOBILE-OPTIMIZED & PRODUCTION READY

### Session 25 - ONBOARDING WIZARD FOR NEW CONDOMINIUMS (January 31, 2026) ⭐⭐⭐⭐⭐ 
**100% Tests Passed (14/14 Backend + Frontend Complete)**

#### KEY ACCOMPLISHMENTS
1. **Backend Implementation (COMPLETE)**
   - ✅ GET /api/super-admin/onboarding/timezones - Returns 9 timezone options
   - ✅ POST /api/super-admin/onboarding/create-condominium - Atomic creation
   - ✅ Rollback on failure - No partial condominiums or admins
   - ✅ Admin password auto-generated (12 chars, mixed case, digits, special)
   - ✅ Admin password_reset_required=true - Forces password change
   - ✅ Security module always enabled (cannot be disabled)
   - ✅ Areas created in reservation_areas collection
   - ✅ Role validation - Only SuperAdmin can access

2. **Frontend Implementation (COMPLETE)**
   - ✅ Full-screen wizard at /super-admin/onboarding
   - ✅ 5-step flow: Info → Admin → Modules → Areas → Summary
   - ✅ Step validation - Next disabled until fields valid
   - ✅ Step skipping - Areas skipped if Reservations not enabled
   - ✅ localStorage state persistence
   - ✅ Cancel confirmation dialog
   - ✅ Credentials shown ONCE with copy button
   - ✅ Mobile-first responsive design

3. **UX Features**
   - ✅ Progress indicator with checkmarks for completed steps
   - ✅ Module toggles with "Obligatorio" badge on Security
   - ✅ Quick-add presets for common areas (Pool, Gym, etc.)
   - ✅ Warning banner before credentials display
   - ✅ Redirect to SuperAdmin dashboard after completion

4. **Test Report**: `/app/test_reports/iteration_32.json` - 100% pass rate

### Session 24 - PUSH NOTIFICATIONS FOR PANIC ALERTS (January 30, 2026) ⭐⭐⭐⭐⭐ 
**100% Tests Passed (13/13 Backend + Frontend Complete)**

#### KEY ACCOMPLISHMENTS
1. **Backend Implementation (COMPLETE)**
   - ✅ VAPID keys generated and stored in environment variables
   - ✅ GET /api/push/vapid-public-key - Returns public key for client subscription
   - ✅ POST /api/push/subscribe - Allows guards to subscribe to push notifications
   - ✅ DELETE /api/push/unsubscribe - Removes push subscription
   - ✅ GET /api/push/status - Returns subscription status
   - ✅ pywebpush integration for sending Web Push notifications
   - ✅ notify_guards_of_panic() helper sends notifications to all guards in condominium
   - ✅ Multi-tenant filtering - Only guards from same condominium receive alerts
   - ✅ Role validation - Only Guardia, Guarda, Administrador, SuperAdmin, Supervisor can subscribe
   - ✅ Automatic cleanup of expired/invalid subscriptions (410 Gone handling)

2. **Frontend Implementation (COMPLETE)**
   - ✅ Service Worker with push event handler and notification actions
   - ✅ usePushNotifications hook for subscription management
   - ✅ PushNotificationBanner - Contextual permission request in GuardUI
   - ✅ PushNotificationToggle - Settings toggle in Profile tab
   - ✅ Notification click opens /guard?alert={event_id}
   - ✅ GuardUI handles alert parameter and highlights the alert
   - ✅ Service worker message listener for PANIC_ALERT_CLICK
   - ✅ LocalStorage persistence for dismissed banner state

3. **Panic Alert Integration**
   - ✅ POST /api/security/panic now includes push_notifications in response
   - ✅ Notification payload includes: panic type, resident name, apartment, timestamp
   - ✅ Urgent vibration pattern for mobile devices
   - ✅ requireInteraction: true - Notification stays until user dismisses

4. **UX Decisions**
   - ✅ Permission request via explicit banner (not on login)
   - ✅ Native system sound (no custom MP3 - more reliable across platforms)
   - ✅ Banner only shown when: permission != 'denied' && not subscribed && not dismissed

5. **Test Report**: `/app/test_reports/iteration_31.json` - 100% pass rate

### Session 23 - EMAIL CREDENTIALS FEATURE (January 30, 2026) ⭐⭐⭐⭐⭐ 
**100% Tests Passed (9/9 Backend + Frontend Complete) - P0 Bug Fixed**

#### KEY ACCOMPLISHMENTS
1. **Backend Implementation (COMPLETE)**
   - ✅ POST /api/admin/users with `send_credentials_email=true` generates temporary password
   - ✅ User created with `password_reset_required=true` flag
   - ✅ POST /api/auth/login returns `password_reset_required` in response
   - ✅ POST /api/auth/change-password allows user to set new password
   - ✅ Password change clears the `password_reset_required` flag
   - ✅ Resend email integration (using placeholder key - emails skipped but flow works)
   - ✅ Audit logging for user creation and password change events

2. **Frontend Implementation (COMPLETE)**
   - ✅ "Enviar credenciales por email" checkbox in Create User modal
   - ✅ CredentialsDialog shows email status (yellow warning when not sent)
   - ✅ PasswordChangeDialog appears for users with `password_reset_required=true`
   - ✅ Dialog is non-dismissible (mandatory password change)
   - ✅ Real-time password validation (8+ chars, uppercase, lowercase, number)
   - ✅ User redirected to correct dashboard after password change

3. **P0 Bug Fix (CRITICAL)**
   - **Issue**: PasswordChangeDialog was not appearing on login
   - **Root Cause**: PublicRoute in App.js redirected authenticated users before dialog could render
   - **Fix**: Modified PublicRoute to check `passwordResetRequired` flag and allow user to stay on /login
   - **Additional Fix**: Added useEffect in LoginPage.js to show dialog for already-authenticated users

4. **Security Features**
   - ✅ Temporary password never shown in API response (masked as "********")
   - ✅ Current password required to change password
   - ✅ New password must be different from current
   - ✅ Password validation rules enforced (client + server)

5. **Test Report**: `/app/test_reports/iteration_30.json` - 100% pass rate

### Session 22 - HR PERFORMANCE EVALUATION MODULE (January 30, 2026) ⭐⭐⭐⭐⭐ 
**100% Tests Passed (14/14 Backend + Frontend Complete)**

#### KEY ACCOMPLISHMENTS
1. **Backend Implementation (COMPLETE)**
   - ✅ POST /api/hr/evaluations - Create evaluation with categories
   - ✅ GET /api/hr/evaluations - List evaluations (filtered by condominium)
   - ✅ GET /api/hr/evaluations/{id} - Get specific evaluation
   - ✅ GET /api/hr/evaluable-employees - Get employees that can be evaluated
   - ✅ GET /api/hr/evaluations/employee/{id}/summary - Employee evaluation summary
   - ✅ Categories: discipline, punctuality, performance, communication (1-5 scale)
   - ✅ Multi-tenant isolation via condominium_id
   - ✅ Audit logging (evaluation_created events)

2. **Frontend Implementation (COMPLETE)**
   - ✅ EvaluacionSubmodule replaces "Coming Soon" placeholder
   - ✅ Stats cards: Evaluaciones, Promedio, Evaluados, Empleados
   - ✅ Employee cards with star ratings and evaluation count
   - ✅ StarRating component (reusable, readonly mode)
   - ✅ CreateEvaluationDialog with employee dropdown and 4 category ratings
   - ✅ EmployeeHistoryDialog showing evaluation timeline
   - ✅ EvaluationDetailDialog with full details
   - ✅ Mobile responsive layout (cards stacked, button full-width)

3. **Permissions**
   - ✅ HR/Supervisor/Admin: Create and view all evaluations
   - ✅ Employees (Guard): View own evaluations only
   - ✅ Cannot evaluate yourself
   - ✅ SuperAdmin: Read-only global view

4. **Bug Fixed**
   - `hasAnyRole()` was receiving array instead of spread arguments

### Session 21 - MOBILE UX/UI HARDENING PHASE (January 30, 2026) ⭐⭐⭐⭐⭐ 
**All tests passed 100% (14/14) - Desktop 100% Unchanged**

#### KEY ACCOMPLISHMENTS
1. **Tables → Cards Conversion (PHASE 3 Complete)**
   - ✅ UserManagementPage: Cards on mobile, table on desktop
   - ✅ AuditModule: Audit log cards on mobile, table on desktop
   - ✅ SuperAdminDashboard (Condominiums): Condo cards on mobile, table on desktop
   - ✅ SuperAdminDashboard (Users): User cards on mobile, table on desktop
   - ✅ PaymentsModule: Payment history cards on mobile, table on desktop

2. **Navigation Fixes**
   - ✅ Fixed SuperAdmin mobile nav tab IDs (condos → condominiums, modules → content)
   - ✅ Added profile navigation for Super Admin mobile nav
   - ✅ All bottom nav items functional for all roles

3. **Breakpoint Verification**
   - ✅ Mobile: ≤1023px - Shows cards, bottom nav, fullscreen dialogs
   - ✅ Desktop: ≥1024px - Shows tables, sidebar, centered modals

4. **Components Enhanced**
   - `MobileCard`: Supports title, subtitle, icon, status badge, details grid, action menu
   - `MobileCardList`: Proper spacing container for cards
   - `dialog.jsx`: Fullscreen sheet on mobile (inset-0, w-full, h-full)

### Session 20 - COMPREHENSIVE MOBILE OPTIMIZATION (January 29, 2026) ⭐⭐⭐⭐⭐ 
**All 6 phases complete - 93% Test Pass Rate (14/15 passed, 1 minor) - Desktop 100% Unchanged**

#### PHASE 1 - GLOBAL MOBILE RULES
- ✅ Strict breakpoint: ≤1023px = mobile, ≥1024px = desktop
- ✅ Minimum touch targets: 44-48px on all buttons
- ✅ Full-screen modals on mobile (<640px)
- ✅ No horizontal scrolling
- ✅ Larger inputs (48px height, 16px font to prevent iOS zoom)

#### PHASE 2 - ROLE-BASED BOTTOM NAVIGATION
- ✅ **Guard**: Alertas | Visitas | **PÁNICO** (red center) | Mi Turno | Perfil
- ✅ **Resident**: **PÁNICO** (red center) | Reservas | Alertas | Personas | Perfil
- ✅ **HR**: Dashboard | Turnos | Ausencias | Personas | Perfil
- ✅ **Admin**: Dashboard | Usuarios | RRHH | Reservas | Perfil
- ✅ **Super Admin**: Dashboard | Condos | Contenido | Usuarios | Perfil (yellow/orange theme)

#### PHASE 3 - TABLES → CARDS (COMPLETE)
- ✅ User Management: Cards on mobile, table on desktop
- ✅ Audit Module: Cards on mobile, table on desktop
- ✅ Super Admin Condos: Cards on mobile, table on desktop
- ✅ Super Admin Users: Cards on mobile, table on desktop
- ✅ Payments History: Cards on mobile, table on desktop
- ✅ `MobileCard` and `MobileCardList` reusable components created
- ✅ Desktop tables remain 100% unchanged

#### PHASE 4 - ROLE-SPECIFIC ADJUSTMENTS
- ✅ Guard: Large tappable alert cards, prominent panic buttons
- ✅ Resident: Emergency buttons 48px+, clear status indicators
- ✅ HR: Compact mobile header, simplified forms
- ✅ Super Admin: Stats cards 2x2 grid, touch-friendly quick actions

#### PHASE 5 - VISUAL CONSISTENCY
- ✅ No new colors (existing palette only)
- ✅ No clipped buttons or overlapping elements
- ✅ Consistent icon sizes and spacing

#### PHASE 6 - VERIFICATION
- ✅ iPhone viewport (390x844): All features working
- ✅ Desktop viewport (1920x800): 100% unchanged
- ✅ No horizontal scrolling on any page

### Session 17-19 - PRE-DEPLOYMENT CONSOLIDATION ⭐⭐⭐⭐⭐ FINAL
**All 8 Critical Points Verified - 35/35 Backend Tests Passed**

- ✅ **1. SISTEMA DE PERFILES - COMPLETE**:
  - Avatar component in Sidebar shows `profile_photo` (with letter fallback)
  - Avatar in Topbar for all roles
  - `refreshUser()` updates state globally after PATCH /profile
  - No layout mixing between roles (Guard stays in GuardUI, HR in RRHHModule)

- ✅ **2. DIRECTORIO DE PERSONAS - COMPLETE**:
  - ResidentUI: Has "Personas" tab (5 tabs total)
  - GuardUI: Has "Personas" tab (8 tabs total)
  - RRHHModule: Has "Directorio de Personas" and "Mi Perfil" tabs
  - All show users grouped by role with search and lightbox

- ✅ **3. NAVEGACIÓN SIN DEAD-ENDS - COMPLETE**:
  - Guard: 8 tabs (Alertas, Visitas, Mi Turno, Ausencias, Registro, Historial, Personas, Perfil)
  - HR: All tabs including Personas and Mi Perfil stay within RRHH layout
  - Profile is a TAB, not a route escape

- ✅ **4. CAMPANITA DE NOTIFICACIONES - FUNCTIONAL**:
  - Shows real alert count from `/api/security/panic-events`
  - Shows "No hay alertas activas" when empty
  - NOT static - updates with real data

- ✅ **5. MÓDULOS DESHABILITADOS OCULTOS - COMPLETE**:
  - `ModulesContext.js` filters Sidebar and Dashboard
  - School module (disabled) NOT visible anywhere
  - Reservations module (enabled) visible in Sidebar

- ✅ **6. RESERVACIONES FUNCIONAL - COMPLETE**:
  - Admin: Create/edit/delete areas, approve/reject reservations
  - Resident: View areas, create reservations
  - Guard: View today's reservations
  - Multi-tenant enforced

- ✅ **7. SEGURIDAD DE ROLES - VERIFIED**:
  - All endpoints enforce `condominium_id`
  - Resident cannot access admin endpoints (403)
  - No data leaks between condominiums

- ✅ **8. E2E TESTING - COMPLETE**:
  - Guard login -> Profile edit -> Return to Alerts: OK
  - All 8 tabs navigable without dead-ends
  - Profile sync verified

- 📋 Test report: `/app/test_reports/iteration_24.json` - 100% pass rate (35/35)

### Session 16 - CRITICAL CONSOLIDATION (January 29, 2026) ⭐⭐⭐⭐⭐ PRE-DEPLOYMENT
**All 6 Parts Verified - 31/31 Tests Passed**

- ✅ **PART 1: Global Profile System - COMPLETE**:
  - Avatar component added to Sidebar (clickable, navigates to /profile)
  - Avatar shows in topbar for all roles
  - `refreshUser()` function in AuthContext updates state after profile edit
  - Profile photos sync across all views (directory, cards, miniatures)
  - All roles have access to profile editing

- ✅ **PART 2: Guard Navigation - COMPLETE**:
  - GuardUI has 8 tabs: Alertas, Visitas, Mi Turno, Ausencias, Registro, Historial, **Personas**, **Perfil**
  - No dead-ends - Guard can navigate freely between all tabs
  - Stays on /guard URL (no external redirects to admin layouts)
  - Personas shows ProfileDirectory, Perfil shows EmbeddedProfile

- ✅ **PART 3: Module Visibility - COMPLETE**:
  - `ModulesContext.js` provides `isModuleEnabled()` function
  - Sidebar filters navigation items by module availability
  - Disabled modules completely hidden (not just disabled UI)
  - Module toggle endpoint fixed to accept SuperAdmin role
  - School module toggle works without errors

- ✅ **PART 4: Reservations Module - COMPLETE**:
  - **Backend**: Full CRUD for Areas and Reservations with audit logging
  - **Admin**: Create/edit/delete areas, approve/reject reservations (4 tabs)
  - **Resident**: View areas, create reservations, see status (2 tabs)
  - **Guard**: View today's reservations read-only
  - Multi-tenant: All endpoints validate `condominium_id`
  - Overlap detection prevents double-booking

- ✅ **PART 5: School Toggle - COMPLETE**:
  - `PATCH /api/condominiums/{id}/modules/school?enabled=true/false`
  - No "error updating module" errors
  - State persists correctly in MongoDB

- ✅ **PART 6: Data Consistency - COMPLETE**:
  - All endpoints enforce `condominium_id` isolation
  - No test/demo data leaks between condominiums
  - Profile photos scoped to user's condominium
  - New condominiums start with zero data

- 📋 Test report: `/app/test_reports/iteration_23.json` - 100% pass rate (31/31)

### Session 15 - Resident Personas + Profile Sync + Guard Navigation Fix (January 29, 2026) ⭐⭐⭐ CRITICAL FIX
**3 UX/Sync Issues Resolved:**

- ✅ **PROBLEMA 1: Residentes NO pueden ver perfiles - FIXED**:
  - ResidentUI now has **5 tabs**: Emergencia, Mis Alertas, Visitas, **Personas**, **Perfil**
  - "Personas" tab uses ProfileDirectory component
  - Shows all condo users grouped by role: Admin, Supervisor, Guardias, Residentes
  - Search by name, email, phone
  - Photo lightbox on click
  - Navigate to user profile on card click

- ✅ **PROBLEMA 2: Fotos de perfil NO se sincronizan - FIXED**:
  - Added `refreshUser()` function to AuthContext
  - ProfileDirectory has `userPhotoKey` dependency in useEffect
  - Automatic refetch when user photo changes
  - Header immediately reflects profile updates

- ✅ **PROBLEMA 3: Guard queda atrapado en Perfil - FIXED**:
  - GuardUI has **8 tabs**: Alertas, Visitas, Mi Turno, Ausencias, Registro, Historial, Personas, Perfil
  - All tabs remain visible when viewing Perfil
  - Guard can navigate freely between ALL tabs
  - No Admin layout, no external redirects

- ✅ **Backend Fix:**
  - CondominiumResponse model fields made optional (contact_email, contact_phone, etc.)
  - CreateUserByAdmin model accepts condominium_id for SuperAdmin user creation

- 📋 Test report: `/app/test_reports/iteration_22.json` - 100% pass rate

### Session 14 - Guard Navigation + Module Visibility + Profile Directory (January 29, 2026) ⭐⭐⭐ CRITICAL FIX
**3 Issues Resolved:**

- ✅ **ISSUE 1: Guard Profile Navigation (UX Bug) - FIXED**:
  - GuardUI now has 8 tabs: Alertas, Visitas, Mi Turno, Ausencias, Registro, Historial, **Personas**, **Perfil**
  - Guard can access and edit profile without leaving Guard navigation
  - EmbeddedProfile component (`/app/frontend/src/components/EmbeddedProfile.jsx`)
  - No logout/reload required to return to dashboard

- ✅ **ISSUE 2: Module Visibility Per Condominium (Architecture Bug) - FIXED**:
  - Created `ModulesContext.js` to provide module availability
  - Sidebar now filters navigation items based on `enabled_modules` config
  - DashboardPage "Accesos Rápidos" respects module config
  - If `school: { enabled: false }`, it's completely hidden (not disabled UI)
  - Backend `CondominiumModules` model enforces module config

- ✅ **ISSUE 3: Global Profile System (Core Feature) - IMPLEMENTED**:
  - New endpoint: `GET /api/profile/directory/condominium`
  - Returns users grouped by role: Administrador, Supervisor, HR, Guarda, Residente
  - ProfileDirectory component (`/app/frontend/src/components/ProfileDirectory.jsx`)
  - Searchable directory with photo lightbox
  - Guard/Resident/HR/Admin can see all users in their condominium

- 📋 Test report: `/app/test_reports/iteration_21.json` - All tests passed

### Session 13 - Guard Profile Access & Photo Lightbox (January 29, 2026) ⭐⭐ P1
- ✅ **Guard Profile Access (COMPLETE)**:
  - Guard UI header now has clickable avatar (`data-testid="guard-profile-avatar"`)
  - Added profile button (User icon) in header (`data-testid="guard-profile-btn"`)
  - Both navigate to `/profile` page
  - Avatar border color changes with clock status (green=clocked in, gray=not)
- ✅ **Photo Lightbox Modal (COMPLETE)**:
  - Clicking profile photo opens full-screen modal
  - Zoom icon appears on avatar hover (only when photo exists)
  - Modal shows full-size image with user info overlay (name + role badges)
  - Close button (`data-testid="photo-modal-close-btn"`) to dismiss
  - Works for all roles: Guard, Resident, HR, Admin, SuperAdmin
- ✅ **Read-Only Profile View**:
  - `/profile/:userId` shows other user's profile
  - Title changes to "Perfil de Usuario"
  - Back button "Volver" appears
  - Edit button hidden
- 📋 Test report: `/app/test_reports/iteration_20.json` - 100% pass rate (18/18 tests)

### Session 12 - Unified User Profile Module (January 29, 2026) ⭐⭐ P1
- ✅ **Unified Profile Page (COMPLETE)**:
  - `/profile` route shows own profile (editable)
  - `/profile/:userId` route shows other user's profile (read-only)
  - Editable fields: Name, Phone, Photo, Public Description
  - New "Descripción Pública" section visible for all users
- ✅ **Backend Endpoints**:
  - `GET /api/profile` - Returns full profile with role_data
  - `PATCH /api/profile` - Updates name, phone, photo, public_description
  - `GET /api/profile/{user_id}` - Returns public profile (limited fields)
- ✅ **Multi-Tenant Validation (CRITICAL)**:
  - Users can ONLY view profiles within their own condominium
  - Different condominium → 403 Forbidden
  - SuperAdmin can view ANY profile (global access)
- ✅ **Frontend ProfilePage.js**:
  - Detects view/edit mode via `useParams()` userId
  - Back button "Volver" appears for other profiles
  - Edit button hidden when viewing other profiles
  - Role badges displayed for all roles
- ✅ **API Service**: `getPublicProfile(userId)` method added
- 📋 Test report: `/app/test_reports/iteration_19.json` - 100% pass rate (14 backend + all UI tests)

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
- [x] ~~Push notifications for panic alerts~~ (COMPLETED - Session 24)
- [x] ~~Performance evaluations in RRHH~~ (COMPLETED - Session 22)
- [x] ~~Email credentials for new users~~ (COMPLETED - Session 23)
- [x] ~~Onboarding wizard for new condominiums~~ (COMPLETED - Session 25)

### P2 - Medium Priority
- [ ] Dashboard statistics per condominium
- [x] ~~Reservations module~~ (COMPLETED - Session 16)
- [ ] CCTV integration

### P3 - Low Priority
- [ ] Fix PostHog console error (cosmetic, recurring)
- [ ] Native app (React Native)
- [ ] Public API with rate limiting
- [ ] HR periodic performance reports
- [ ] Custom notification sounds (Phase 2)

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
