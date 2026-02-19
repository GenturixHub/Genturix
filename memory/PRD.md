# GENTURIX Enterprise Platform - PRD

## Last Updated: February 19, 2026 (Push Notification Production Hardening)

## Changelog

### 2026-02-19 (Session 75) - Push Notification Production Hardening ✅

- **PHASE 1: Índice Único Compuesto** ✅
  ```python
  # En initialize_indexes():
  (db.push_subscriptions, [("user_id", 1), ("endpoint", 1)], {"unique": True, "background": True})
  ```
  - Previene suscripciones duplicadas a nivel de DB
  - Log de startup: `[DB-INDEX] push_subscriptions.[('user_id', 1), ('endpoint', 1)]: user_id_1_endpoint_1`

- **PHASE 2: Cleanup Safety** ✅
  ```python
  # En POST /api/push/subscribe, antes de insert:
  await db.push_subscriptions.delete_many({
      "user_id": user_id,
      "$or": [
          {"is_active": False},
          {"endpoint": None},
          {"endpoint": ""},
          {"endpoint": {"$exists": False}}
      ]
  })
  ```

- **PHASE 3: Parallel Push Delivery** ✅
  ```python
  # En send_targeted_push_notification y notify_guards_of_panic:
  push_tasks = [send_push_notification_with_cleanup(sub, payload) for sub in subs]
  push_results = await asyncio.gather(*push_tasks, return_exceptions=True)
  ```
  - Nueva función `send_push_notification_with_cleanup()` retorna `{success, deleted, endpoint}`
  - 404/410 responses siguen eliminando suscripciones inválidas

- **PHASE 4: Structured Logging** ✅
  ```
  [PUSH-TARGETED] Complete | condo={id} | target_type={type} | 
  total_found={n} | sent={n} | failed={n} | deleted_invalid={n}
  
  [PANIC-PUSH] Complete | condo={id} | guards_found={n} | 
  sent={n} | failed={n} | excluded={n} | deleted_invalid={n}
  ```

- **NO modificado:** API responses, targeting logic, auth system, multi-tenant

- **Testing:** 100% backend (13/13 tests passed)
- **Test Report:** `/app/test_reports/iteration_83.json`

---

### 2026-02-19 (Session 75) - Persistencia Profesional de Push Notifications ✅

- **Refactor completo del ciclo de vida de Push Notifications** ✅

  **REGLAS IMPLEMENTADAS:**
  1. NUNCA llamar `Notification.requestPermission()` automáticamente
  2. Solo pedir permiso cuando usuario activa push manualmente desde perfil
  3. En login: solo sincronizar suscripción existente si `permission=granted`
  4. Logout NO toca push (no unsubscribe, no remove service worker)

  **Función `syncPushSubscription()` (AuthContext):**
  ```javascript
  // SOLO sincroniza, NUNCA:
  // - Llama Notification.requestPermission()
  // - Llama pushManager.subscribe()
  
  if (Notification.permission !== 'granted') return;
  const existingSub = await pushManager.getSubscription();
  if (!existingSub) return;
  // Sync con backend...
  ```

  **Console debug logs agregados:**
  ```javascript
  console.log('[Push] Permission:', Notification.permission);
  console.log('[Push] Existing subscription:', !!existingSub);
  ```

  **Código eliminado:**
  - `registerPushForGuard()` - llamaba requestPermission()
  - `formatSubscription()` - ya no necesaria
  - Import de `pushManager` en GuardUI y ResidentUI

  **Push activation manual:** Solo en `PushNotificationToggle.jsx` (perfil)

- **NO modificado:**
  - Backend
  - Sistema de targeting
  - Sistema de alertas de pánico

- **Testing:** 100% frontend (8/8 requirements)
- **Test Report:** `/app/test_reports/iteration_82.json`

---

### 2026-02-19 (Session 75) - Exportación de Auditoría a PDF ✅

- **Backend: Nuevo endpoint GET /api/audit/export** ✅
  - Genera PDF real con reportlab
  - Acepta query params: `from_date`, `to_date`, `event_type`
  - Aplica `tenant_filter` (Admin ve solo su condo, SuperAdmin ve todo)
  - Solo permite roles: Administrador, SuperAdmin
  - Límite: 1000 registros máximo
  - Retorna: `Response(content=pdf_bytes, media_type="application/pdf")`

  **Estructura del PDF:**
  - Título: "GENTURIX - Reporte de Auditoría"
  - Subtítulo: Condominio + Fecha de generación
  - Tabla: Fecha | Usuario | Evento | Módulo | IP
  - Footer: Total de registros
  
  **Correcciones aplicadas:**
  - SuperAdmin query vacío `{}` para ver TODOS los logs
  - Pre-fetch de nombres de usuario (muestra nombres reales, no UUIDs)
  - Logs de diagnóstico: `[AUDIT-EXPORT] Query filter:`, `Total logs encontrados:`, `PDF generado con X registros`

- **Frontend: Botón "Exportar PDF" actualizado** ✅
  - Usa `fetch` + `blob` + `createObjectURL` para descarga directa
  - Muestra toast de éxito/error
  - Estado de loading durante exportación
  - Bug corregido: localStorage key `genturix_access_token`

- **Testing:** 100% backend (12/12)
- **Test Report:** `/app/test_reports/iteration_80.json`

---

### 2026-02-19 (Session 75) - Push Notifications para Todos los Roles ✅

- **Habilitado registro push para TODOS los roles** ✅
  - Antes: Solo guardias podían registrarse a push notifications
  - Ahora: Residentes, Admin, HR, Supervisor también pueden
  
  **Cambios realizados:**
  
  1. **PushPermissionBanner.jsx actualizado:**
     - Usa `usePushNotifications` hook correctamente
     - Envía suscripción al servidor via `api.subscribeToPush()`
     - Muestra para TODOS los usuarios autenticados
     - Console log: `[Push] Subscription created for role: ${roles}`
  
  2. **ResidentUI.js simplificado:**
     - Eliminado código de suscripción automática antiguo
     - El banner maneja todo el flujo de suscripción
  
  3. **Flujo de suscripción:**
     ```
     Banner aparece (3s después de login)
     → Usuario hace clic "Activar"
     → Navegador pide permiso
     → Si permiso granted:
       → GET /api/push/vapid-public-key
       → PushManager.subscribe()
       → POST /api/push/subscribe
       → Banner de éxito "¡Notificaciones activadas!"
     ```
  
  **NO modificado:**
  - Backend (targeting sigue igual)
  - Service Worker
  - Lógica de audio

- **Testing:** Verificado via code review (push API no funciona en navegador headless)
- **Test Report:** `/app/test_reports/iteration_78.json`

---

### 2026-02-19 (Session 75) - Prevención de Entradas Duplicadas ✅

- **Validación Backend para Evitar Doble Check-in** ✅
  
  **FASE 1 - Validación por Authorization ID:**
  ```python
  existing_inside = await db.visitor_entries.find_one({
      "authorization_id": authorization_id,
      "status": "inside",
      "exit_at": None
  })
  # Si existe → HTTP 400: "El visitante ya se encuentra dentro del condominio"
  ```
  
  **FASE 2 - Validación para Entradas Manuales:**
  ```python
  existing_manual = await db.visitor_entries.find_one({
      "condominium_id": condo_id,
      "status": "inside",
      "exit_at": None,
      "authorization_id": None,
      "visitor_name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}
  })
  # Si existe → HTTP 400: "Ya existe un visitante con el nombre 'X' dentro"
  ```
  
  **FASE 3 - Frontend UI:**
  - Campo `is_visitor_inside` agregado a GET /guard/authorizations
  - Badge azul: "Ya se encuentra dentro del condominio"
  - Botón deshabilitado con texto "YA DENTRO"
  - Muestra hora de entrada si el visitante está dentro

- **Testing:** 92% backend (12/13 - 1 rate limit), 100% frontend
- **Test Report:** `/app/test_reports/iteration_77.json`
- **Bug Fixed:** Query PHASE 2 ahora usa regex case-insensitive directo

---

### 2026-02-19 (Session 75) - Notificaciones Push Directas al Residente ✅

- **Notificaciones Push con `target_user_ids`** ✅
  - El residente dueño del evento recibe push directo usando `target_user_ids=[resident_id]`
  - Implementado en 4 escenarios:
  
  **FASE 1 - Check-in de visitante:**
  ```python
  await send_targeted_push_notification(
      condominium_id=condo_id,
      title="🚪 Tu visitante ha llegado",
      body=f"{visitor_name} ha ingresado al condominio",
      target_user_ids=[resident_id],
      exclude_user_ids=[current_user["id"]]
  )
  ```
  
  **FASE 2 - Check-out de visitante:**
  ```python
  await send_targeted_push_notification(
      condominium_id=condo_id,
      title="👋 Tu visitante ha salido",
      body=f"{visitor_name} ha salido del condominio{duration_text}",
      target_user_ids=[resident_id],
      exclude_user_ids=[current_user["id"]]
  )
  ```
  
  **FASE 3 - Reservación aprobada/rechazada:**
  ```python
  await send_targeted_push_notification(
      condominium_id=condo_id,
      title="✅ Reservación aprobada" / "❌ Reservación rechazada",
      body=f"Tu reservación de {area_name}...",
      target_user_ids=[resident_id],
      exclude_user_ids=[current_user["id"]]
  )
  ```
  
  **Seguridad implementada:**
  - `exclude_user_ids=[current_user["id"]]` - Evita autonotificaciones
  - `create_and_send_notification` usa `send_push=False` para evitar duplicados
  
  **NO modificado:** `notify_guards_of_panic()` - sigue funcionando igual

- **Testing:** 27/27 pruebas pasadas (100%)
- **Test Report:** `/app/test_reports/iteration_76.json`

---

### 2026-02-19 (Session 75) - Dynamic Push Notification Targeting ✅

- **Sistema de Targeting Dinámico para Push Notifications** ✅
  - Nueva función `send_targeted_push_notification()` implementada
  - Permite targeting por:
    - **Roles específicos:** `target_roles=["Guarda", "Administrador"]`
    - **IDs de usuario:** `target_user_ids=["user-id-1", "user-id-2"]`
    - **Exclusiones:** `exclude_user_ids=["sender-id"]`
  
  **Firma de la función:**
  ```python
  async def send_targeted_push_notification(
      condominium_id: str,
      title: str,
      body: str,
      target_roles: List[str] = None,
      target_user_ids: List[str] = None,
      exclude_user_ids: List[str] = None,
      data: dict = None,
      tag: str = None,
      require_interaction: bool = False
  ) -> dict
  ```
  
  **Validaciones de seguridad:**
  - condominium_id es obligatorio
  - Al menos target_roles o target_user_ids debe estar definido
  - Verifica que el condominio existe y está activo
  - Solo envía a suscripciones activas (is_active=True)
  
  **Uso migrado a 2 eventos:**
  - Pre-registros de visitantes → target_roles=["Guarda"]
  - Reservaciones pendientes → target_roles=["Administrador", "Supervisor"]
  
  **Funciones legacy preservadas (retrocompatibilidad):**
  - `send_push_to_user()` - sigue funcionando
  - `send_push_to_guards()` - sigue funcionando
  - `send_push_to_admins()` - sigue funcionando
  - `notify_guards_of_panic()` - **NO fue modificada**

- **Testing:** 20/20 pruebas pasadas (100%)
- **Test Report:** `/app/test_reports/iteration_75.json`

---

### 2026-02-19 (Session 75) - Production Hardening Definitivo ✅

- **FASE 1: Hardening de JWT Secrets** ✅
  - Eliminados fallbacks inseguros de JWT_SECRET_KEY y JWT_REFRESH_SECRET_KEY
  - Ahora el servidor NO arranca si las variables no están configuradas
  - Validación de ENVIRONMENT: debe ser 'development' o 'production'
  - Protección: DEV_MODE no puede estar habilitado en producción

- **FASE 2: Rate Limiting en Login** ✅
  - Implementado rate limiting en memoria para prevenir brute-force
  - Configuración: 5 intentos máximos por email+IP por minuto
  - HTTP 429 después de exceder el límite
  - Mensaje: "Too many login attempts. Please try again later."

- **FASE 3: Índices Adicionales en MongoDB** ✅
  - **11 índices configurados** (todos se crean en startup):
    - `users.email` (unique)
    - `users.condominium_id`
    - `push_subscriptions.user_id`
    - `push_subscriptions.condominium_id`
    - `audit_logs.user_id`
    - `audit_logs.created_at` (TTL 90 días)
    - `reservations.condominium_id`
    - `reservations.start_time`
    - `visitor_authorizations.condominium_id`
    - `visitor_authorizations.created_by`
    - `visitor_entries.condominium_id`

- **Testing:** 17/17 pruebas pasadas (100%)
- **Test Report:** `/app/test_reports/iteration_74.json`

---

### 2026-02-18 (Session 74) - ROLLBACK: Sistema de Audio Simplificado ✅

- **Sistema de Audio Rollback Completado** ✅
  - Eliminada toda la lógica compleja de tab locks
  - Sistema simple y estable que cumple requisitos básicos
  
  **Cambios Realizados:**
  1. **GuardTabLock.js** - ELIMINADO completamente
  2. **AlertSoundManager.js** - Simplificado a versión mínima:
     - `play()` - Reproduce audio en loop
     - `stop()` - Detiene audio
     - `unlock()` - Desbloquea audio en primer gesto
     - Sin tab locks, sin coordinación entre pestañas
  3. **GuardUI.js** - Simplificado:
     - Eliminadas referencias a `hasAudioLock`
     - Eliminado banner de audio complejo
     - Audio se reproduce directamente cuando llega alerta push
     - Audio se detiene al: abrir alerta, resolver alerta, cambiar a tab Alertas
  
  **Archivos Modificados:**
  - `/app/frontend/src/utils/AlertSoundManager.js` - Versión simple
  - `/app/frontend/src/pages/GuardUI.js` - Sin tab locks
  - `/app/frontend/src/utils/GuardTabLock.js` - ELIMINADO
  
  **Comportamiento Actual:**
  - Sonido se reproduce cuando llega alerta de pánico
  - Sonido se detiene cuando el guardia atiende la alerta
  - Simple, estable, mantenible
  
---

### 2026-02-18 (Session 73) - AlertSoundManager Sistema Definitivo (SUPERSEDED)

- **AlertSoundManager Profesional Implementado** (REVERTIDO)
  
  **Características:**
  - Clase Singleton - una única instancia global
  - Pre-carga de audio (`preload='auto'`)
  - Loop automático (`loop=true`)
  - Sin errores de consola - todos los catch son silenciosos
  - Sin múltiples instancias simultáneas
  - Independiente del Service Worker
  - No depende de `document.visibilityState`
  
  **API:**
  - `unlock()` - Desbloquea audio (llamar en primer gesto de usuario)
  - `play()` - Inicia reproducción en loop
  - `stop()` - Detiene reproducción
  - `getIsPlaying()` - Estado de reproducción
  - `getIsUnlocked()` - Estado de desbloqueo
  
  **Integración en GuardUI:**
  - Desbloqueo automático en primer click/touch/keydown
  - Reproducción al recibir `NEW_PANIC_ALERT` del Service Worker
  - Detención al: marcar alerta como atendida, cerrar notificación, cambiar a tab Alertas
  - Banner de desbloqueo si autoplay está bloqueado
  
  **Seguridad:**
  - Solo rol Guarda importa/usa AlertSoundManager
  - Header.js condiciona stop() al rol Guarda
  - App.js no importa AlertSoundManager
  
  **Archivo de Audio:**
  - Ubicación: `/public/sounds/panic-alert.mp3`
  - Generado con patrón de alerta clásico (880Hz/440Hz alternado)
  
  **Archivos Modificados:**
  - `/app/frontend/src/utils/AlertSoundManager.js` - Sistema definitivo
  - `/app/frontend/src/pages/GuardUI.js` - Integración completa
  - `/app/frontend/src/components/layout/Header.js` - Condicional a rol Guarda
  - `/app/frontend/src/App.js` - Eliminado import no usado
  - `/app/frontend/public/sounds/panic-alert.mp3` - Archivo de audio creado

### 2026-02-18 (Session 73) - Push Notifications Frontend Refactor ⭐⭐⭐⭐⭐

- **Frontend Push System Completely Refactored** ✅
  - Aligned with new secure backend architecture
  
  **1. Service Worker Simplified (v5):**
  - Only receives push → shows notification
  - Removed: audio logic, locks, role checks, cross-tab coordination
  - Sends `NEW_PANIC_ALERT` message to app for UI update
  - Clean notification click handling
  
  **2. Push Registration in AuthContext:**
  - On login: if `user.role === 'Guarda'` → auto-register push
  - Other roles: no auto-registration
  - Checks `Notification.permission` before prompting
  - Uses VAPID key from backend `/api/config/vapid`
  
  **3. Logout Cleanup:**
  - Calls `DELETE /api/push/unsubscribe-all`
  - Unsubscribes local Service Worker subscription
  
  **4. AlertSoundManager Simplified (v4):**
  - Simple `play()` / `stop()` methods
  - No locks, no cross-tab communication
  - HTML5 Audio element (most reliable)
  
  **5. GuardUI Audio Logic Simplified:**
  - Plays sound only if `document.visibilityState === 'visible'`
  - Shows unlock banner if autoplay blocked
  - Stops sound on notification click/close
  
  **6. PushPermissionBanner Updated:**
  - Uses static methods from PushNotificationManager
  - For non-Guard roles who want notifications
  
  **Files Modified:**
  - `/app/frontend/public/service-worker.js` - Simplified v5
  - `/app/frontend/src/utils/AlertSoundManager.js` - Simplified v4
  - `/app/frontend/src/utils/PushNotificationManager.js` - Static methods
  - `/app/frontend/src/contexts/AuthContext.js` - Push registration on login
  - `/app/frontend/src/pages/GuardUI.js` - Simplified audio handling
  - `/app/frontend/src/components/PushPermissionBanner.jsx` - Updated API

### 2026-02-18 (Session 73) - Push Notifications Security Refactor ⭐⭐⭐⭐⭐

- **Push Notifications System Completely Refactored** ✅
  - Backend is now the ONLY authority for push notification routing
  
  **1. Model push_subscriptions - Required Fields:**
  ```
  - id: str (UUID)
  - user_id: str (REQUIRED)
  - role: str (REQUIRED - primary role at subscription time)
  - condominium_id: str (REQUIRED for non-SuperAdmin)
  - endpoint: str (push service URL)
  - keys: { p256dh, auth }
  - is_active: bool
  - created_at, updated_at
  ```
  
  **2. Endpoint POST /api/push/subscribe:**
  - Validates user is authenticated
  - Validates user has condominium_id (except SuperAdmin)
  - Validates user is active (not blocked/suspended)
  - Saves role with subscription for targeting
  - Updates existing if user_id + endpoint match
  
  **3. Endpoint DELETE /api/push/unsubscribe:**
  - Removes specific subscription for current user
  - DELETE /api/push/unsubscribe-all for logout cleanup
  
  **4. Panic Alert Push - SECURITY RULES:**
  ✅ SENDS TO: Guards (role='Guarda') in SAME condo, ACTIVE only
  ❌ DOES NOT SEND TO: Sender, Residents, Admins, SuperAdmins, HR, other condos
  
  **5. Error 410 Gone Handling:**
  - Auto-deletes stale subscriptions on 404/410 response
  - Logs cleanup for monitoring
  
  **6. Security Validations:**
  - All push functions validate condominium exists
  - User must be authenticated and active
  - Role filtering enforced at backend level
  
  **7. New Maintenance Endpoint:**
  - POST /api/push/cleanup (SuperAdmin only)
  - Removes subscriptions without user_id or deleted/inactive users

### 2026-02-18 (Session 73) - Bug Fixes + Demo Wizard Enhancement ⭐⭐⭐⭐⭐

- **P2 Fix: bcrypt Warning Eliminated** ✅
  - Replaced `passlib.CryptContext` with direct `bcrypt` module usage
  - Eliminates "AttributeError: module 'bcrypt' has no attribute '__about__'" warning
  - Functions `hash_password()` and `verify_password()` now use bcrypt directly
  - No compatibility issues with bcrypt 4.x

- **P2 Fix: PostHog Console Errors Suppressed** ✅
  - Added comprehensive error suppression for PostHog-related console errors
  - Wrapped PostHog init in try-catch with silent fail
  - Added onerror handler for script loading
  - Analytics are non-critical, failures now silent

- **Enhancement: Demo Wizard with Pre-loaded Test Data** ✅
  - New endpoint: `POST /api/superadmin/condominiums/demo-with-data`
  - Creates demo condominium + admin + optional guards/residents/areas
  - New `DemoWizardDialog` component in SuperAdminDashboard
  - Features:
    - Admin user with credentials
    - 2 sample guards (optional)
    - 3 sample residents with apartments (optional)
    - Gym and Pool reservation areas (optional)
  - Shows all credentials in result table with copy button
  - **QR Code with credentials** - Scannable code containing:
    - Demo name
    - All user credentials (email/password)
    - Login URL
    - Perfect for sharing with clients during demos
  - Ideal for quick client demonstrations

### 2026-02-18 (Session 73) - Demo vs Production Condominium Endpoint Separation ⭐⭐⭐⭐⭐
- **P0 Feature: Separate Endpoints for Demo vs Production Condominiums** - FULLY VERIFIED ✅
  - Backend Testing: 100% (12/12 tests passed)
  - Frontend Testing: 100% (all features working)
  - Test report: `/app/test_reports/iteration_73.json`
  
  **Key Implementation:**
  
  1. **New Backend Models:**
     - `DemoCondominiumCreate` - Simplified model for demo condos (no billing fields)
     - `CondominiumCreate` - Production model with billing fields (paid_seats, etc.)
  
  2. **Separate Backend Endpoints:**
     - **`POST /api/superadmin/condominiums/demo`** - Creates DEMO condominiums:
       - Fixed 10 seats (hardcoded)
       - `billing_enabled=false`
       - `billing_status='demo'`
       - `environment='demo'`
       - `is_demo=true`
       - No Stripe integration
     - **`POST /api/condominiums`** - Creates PRODUCTION condominiums:
       - Configurable `paid_seats`
       - `billing_enabled=true`
       - `billing_status='active'`
       - `environment='production'`
       - `is_demo=false`
       - Stripe integration ready
  
  3. **Frontend Updates (api.js):**
     - `api.createDemoCondominium(data)` - Calls demo endpoint
     - `api.createCondominium(data)` - Calls production endpoint
  
  4. **Frontend Updates (CreateCondoDialog):**
     - Environment selector: DEMO / PRODUCCIÓN
     - "Asientos Iniciales (Paid Seats)" field - Only visible for production
     - Info panels: Yellow for demo, Green for production
     - Calls correct endpoint based on selection
  
  5. **Files Modified:**
     - `/app/backend/server.py` - New models and separate endpoints
     - `/app/frontend/src/services/api.js` - New API function `createDemoCondominium()`
     - `/app/frontend/src/pages/SuperAdminDashboard.js` - CreateCondoDialog uses correct endpoint

### 2026-02-17 (Session 71) - Password Change UI for All Roles ⭐⭐⭐⭐⭐
- **P1 Feature: Password Change UI in All User Profiles** - FULLY VERIFIED ✅
  - Backend Testing: 100% (14/14 tests passed)
  - Frontend Testing: 100% (all UI flows verified)
  - Test report: `/app/test_reports/iteration_72.json`
  
  **Implementation:**
  
  1. **Security Section in EmbeddedProfile:**
     - Added to Guard, Resident, HR, Supervisor profiles
     - Uses ChangePasswordForm with `embedded={true}` mode
     - Visible only when viewing own profile (`isOwnProfile`)
  
  2. **Form Features:**
     - Current Password field with lock icon & eye toggle
     - New Password field with real-time validation
     - Confirm Password field with match indicator
     - Security notice about session invalidation
     - Submit button disabled until valid
  
  3. **Validations (Frontend + Backend):**
     - ✅ Minimum 8 characters
     - ✅ At least one uppercase letter
     - ✅ At least one number
     - ✅ New password != current password
     - ✅ Confirm password matches new
  
  4. **Mobile Responsive:**
     - Vertical layout on small screens
     - Full-width button (100% container)
     - Clean spacing, no overflow
  
  5. **Files Modified:**
     - `/app/frontend/src/components/EmbeddedProfile.jsx` - Security section
     - `/app/frontend/src/components/ChangePasswordForm.jsx` - Embedded mode

### 2026-02-17 (Session 71) - Demo vs Production Environment Separation ⭐⭐⭐⭐⭐
- **P1 Feature: Demo vs Production Condominium Environments** - FULLY VERIFIED ✅
  - Backend Testing: 100% (12/12 tests passed)
  - Frontend Testing: 100% (badges and UI verified)
  - Test report: `/app/test_reports/iteration_71.json`
  
  **Key Implementation:**
  
  1. **Backend Condominium Model:**
     - `environment` field: "production" | "demo"
     - Demo condos: `paid_seats=10` (hardcoded), `billing_enabled=false`, `billing_status='demo'`
     - Production condos: `billing_enabled=true`, Stripe active
  
  2. **Business Rules Enforced:**
     - ✅ Demo condos cannot purchase additional seats (403 error)
     - ✅ Stripe webhooks ignore demo condominiums
     - ✅ GET /api/billing/info includes environment, is_demo, billing_enabled
  
  3. **Frontend Updates (SuperAdmin):**
     - Environment badges: **DEMO** (yellow) | **PROD** (green)
     - "Demo Rápido" button for quick demo creation with modal
     - Detailed info boxes showing demo vs production differences
  
  4. **Files Modified:**
     - `/app/backend/server.py` - Environment validation, billing info
     - `/app/frontend/src/pages/SuperAdminDashboard.js` - Badges, buttons, modal

### 2026-02-17 (Session 71) - Enterprise Admin Password Reset ⭐⭐⭐⭐⭐
- **P1 Feature: Enterprise-Grade Admin Password Reset** - FULLY VERIFIED ✅
  - Backend Testing: 100% (15/15 tests passed)
  - Frontend Testing: 100% (all UI flows verified)
  - Test report: `/app/test_reports/iteration_70.json`
  
  **Key Implementation (Enterprise-Grade):**
  
  1. **Secure Token-Based Reset (NOT temporary password):**
     - JWT token with 1-hour expiration
     - Token hash stored in DB for single-use validation
     - Email with secure link (no password in email)
  
  2. **Backend Endpoints:**
     - `POST /api/admin/users/{id}/reset-password` - Admin initiates reset
     - `GET /api/auth/verify-reset-token` - Validates token
     - `POST /api/auth/reset-password-complete` - User completes reset
  
  3. **Security Validations:**
     - ✅ Cannot reset SuperAdmin passwords
     - ✅ Cannot reset own password (use "Cambiar Contraseña")
     - ✅ Admins cannot reset other Admin passwords
     - ✅ Only same-condominium users can be reset
     - ✅ Session invalidation on reset initiation
  
  4. **Audit Trail:**
     - `PASSWORD_RESET_BY_ADMIN` event type
     - Logs: admin_id, target_user_id, tenant_id, IP, timestamp
  
  5. **Frontend Updates:**
     - Reset button (🔑) with conditional visibility
     - Confirmation modal with email destination
     - New `/reset-password` page for users
     - Invalid token handling with friendly error
  
  6. **Files Created/Modified:**
     - `/app/backend/server.py` - Reset endpoints, token functions
     - `/app/frontend/src/pages/UserManagementPage.js` - Reset button & dialog
     - `/app/frontend/src/pages/ResetPasswordPage.jsx` - NEW: Reset password form
     - `/app/frontend/src/App.js` - New route
     - `/app/frontend/src/services/api.js` - API methods

### 2026-02-17 (Session 71) - Seat Management Refactoring ⭐⭐⭐⭐⭐
- **P1 Feature: Seat Management Complete Refactor** - FULLY VERIFIED ✅
  - Backend Testing: 100% (11/11 tests passed)
  - Frontend Testing: 100% (all UI flows verified)
  - Test report: `/app/test_reports/iteration_69.json`
  
  **Key Changes Implemented:**
  
  1. **Data Model Updates:**
     - Added `UserStatus` enum: `active`, `blocked`, `suspended`
     - Added `status` field to User model (applies to ALL users)
     - `status_changed_at` timestamp for session invalidation
     - `status_reason` for blocking reason audit
  
  2. **Backend Endpoints:**
     - `GET /api/admin/seat-usage` - Returns seat_limit, active_residents, available_seats dynamically
     - `POST /api/admin/validate-seat-reduction` - Validates if seat reduction is allowed
     - `PATCH /api/admin/users/{id}/status-v2` - Block/unblock/suspend with seat management
     - `DELETE /api/admin/users/{id}` - Delete user and release seat
  
  3. **Business Rules Enforced:**
     - ✅ `activeResidents` calculated dynamically (not stored)
     - ✅ Seat reduction blocked when `activeResidents > newSeatLimit`
     - ✅ Resident activation blocked when no seats available
     - ✅ Blocking/suspending releases seat immediately
     - ✅ Session invalidation on block/suspend via `status_changed_at`
  
  4. **Frontend Updates (UserManagementPage):**
     - New "Plan de Residentes" card showing Contratados/Activos/Disponibles
     - Progress bar with color coding (green/yellow/red)
     - Status filter dropdown (Todos/Activos/Bloqueados/Suspendidos)
     - Block button (🔒) with reason field
     - Unblock button (🔓) with seat validation
     - Delete button (🗑️) with confirmation
     - Real-time counter updates after actions
  
  5. **Files Modified:**
     - `/app/backend/server.py` - New endpoints, UserStatus enum, session validation
     - `/app/frontend/src/pages/UserManagementPage.js` - Complete UI overhaul
     - `/app/frontend/src/services/api.js` - New API methods

### 2026-02-17 (Session 71) - Secure Password Change E2E Verification
- **P1 Feature: Secure Password Change** - FULLY VERIFIED ✅
  - Backend Testing: 100% (9/9 tests passed)
  - Frontend Testing: 100% (all UI flows verified)
  - Key verifications completed:
    - ✅ Incorrect current password returns 400
    - ✅ Same password rejected (new = current)
    - ✅ Password requirements enforced (8+ chars, uppercase, number)
    - ✅ Passwords mismatch validation
    - ✅ `password_changed_at` timestamp stored in DB
    - ✅ Old JWT tokens rejected with 401 after password change
    - ✅ Real-time UI validation with visual indicators
    - ✅ Success toast displayed
  - Test report: `/app/test_reports/iteration_68.json`
  - Test file: `/app/backend/tests/test_password_change.py`

### 2026-02-17 (Session 70)
- **P1 Fix:** SuperAdmin Condominiums Dropdown Scroll (Production Issue)
  - Problem: Condominiums list didn't scroll in production builds when expanded
  - Root cause: `overflow-hidden` with dynamic `maxHeight` caused clipping without scroll
  - Fixes applied:
    - Changed container from `overflow-hidden` to conditional `overflow-y: auto`
    - Added `max-height: min(60vh, 600px)` with scroll when expanded
    - Added `overscrollBehavior: contain` for mobile touch behavior
    - Added CSS rules for Radix Select dropdowns in `index.css`
    - SelectContent now has `max-h-[60vh] overflow-y-auto`
  - Verified on: Desktop (1920x800), Mobile (390x844)
  - Production-safe: No dev-only styles, works after minification

- **P1 Feature:** Demo vs Production Tenant Logic (Removed DEV_MODE dependency)
  - Added `environment` field to tenant/condominium model: "demo" or "production"
  - Demo tenants: Never send emails, always show credentials in UI
  - Production tenants: Send credentials via Resend with secure password setup
  - New endpoint: `/api/config/tenant-environment` returns tenant-specific behavior
  - UI indicators: Blue "DEMO" badge / Green "PROD" badge on tenant list
  - Updated CreateCondoDialog with environment selector dropdown
  - Updated user creation response: `tenant_environment`, `demo_mode_notice` fields
  - Backwards compatible: existing tenants default to "demo" for safety
  - Files modified: `server.py` (CondominiumCreate/Update/Response models, create_user endpoint), 
    `SuperAdminDashboard.js`, `UserManagementPage.js`, `api.js`

- **P1 Feature:** Advanced Resident Visit History Module
  - Added "Historial" tab inside Visitas section
  - Tenant isolation: Only shows visits related to resident's authorizations
  - Display per entry: Visitor name, type (Delivery/Permanent/Visitor), entry/exit timestamps, duration, status, alerts
  - Filters: Today, Last 7 days, Last 30 days, Custom date range, By visitor type, By status
  - Search: Real-time filtering by name, document number, vehicle plate
  - Export to PDF: Includes resident name, apartment, condo, date range
  - Pagination: 20 records per page with lazy load
  - Mobile-first responsive design with card-based layout
  - Status color indicators (green=active, gray=completed)
  - Files created: `ResidentVisitHistory.jsx`, `ResidentVisitsModule.jsx`
  - Backend endpoints: `/api/resident/visit-history`, `/api/resident/visit-history/export`
  - Test results: 100% (19/19 backend tests, all frontend UI verified)

- **P0 Bug Fix:** Reservation Module Not Responsive on Mobile
  - Problem: Content was vertically constrained, CTA button not accessible due to layout overflow
  - Root cause: Fixed heights (`h-[calc(100vh-280px)]`) didn't adapt to mobile screens
  - Fixes applied:
    - Changed container from `h-full` to `min-h-0 flex-1 overflow-hidden`
    - Replaced fixed heights with `h-full` inside ScrollArea
    - Added `pb-24` padding to content for bottom nav clearance
    - Dialog: Added `max-h-[90vh] overflow-hidden flex flex-col` with internal scroll
    - DialogFooter: Made sticky with `flex-shrink-0 border-t`
  - Verified on iPhone viewport (390x844) and iPhone SE (390x667)
  - Files: `ResidentReservations.jsx`, `ResidentUI.js`

- **P0 Bug Fix:** VAPID Keys Configuration for Push Notifications
  - Root cause: `usePushNotifications.js` expected `vapid_public_key` but API returns `publicKey`
  - Fix: Updated hook to correctly destructure `publicKey` from API response
  - VAPID keys already configured in backend `.env`: VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_CLAIMS_EMAIL
  - Verified: Push subscription flow works correctly end-to-end
  - Endpoint `/api/push/vapid-public-key` returns valid VAPID public key

- **P0 Bug Fix:** Panic Alert Sending Failure
  - Root cause: `api.js` used `sessionStorage` with key `'accessToken'` while `AuthContext.js` used `localStorage` with key `'genturix_access_token'`
  - Fix: Updated `api.js` to use `localStorage` with correct storage keys
  - Tokens now correctly read for authenticated API requests
  - Verified: Residents can now send panic alerts successfully with "¡ALERTA ENVIADA!" message

- **P0 Bug Fix:** Backend Module Access Control
  - Root cause: `require_module()` dependency wasn't combined with role checks effectively
  - Fix: Created new `require_role_and_module()` combined dependency
  - Updated HR and Security endpoints to use the combined dependency
  - Verified: Disabled modules now correctly return 403 Forbidden
  - Note: Panic endpoint intentionally NOT protected by module check (critical emergency feature)

- **Test Results:** 100% pass rate (11/11 backend tests, all frontend UI flows verified)
- **Files modified:** `/app/frontend/src/services/api.js`, `/app/backend/server.py`

### 2026-02-10 (Session 69)
- **P0 UX Bug Fix:** Admin Mobile Profile/RRHH Separation
  - Fixed issue where Admin profile was rendering inside RRHH module on mobile
  - Modified `RRHHModule.js` to hide "Mi Perfil" tab for Admins
  - Admins now access profile via independent `/profile` route

- **UX Enhancement:** Admin Mobile Navigation "Más" Menu
  - Replaced "Settings" button with "Más" popup menu
  - Menu contains: Mi Perfil, Configuración, Cerrar Sesión

- **P0 Bug Fix:** Guard Alert Sound Reliability (Multiple Alerts)
  - Rewrote AlertSoundManager.js v3 with proper Web Audio API usage
  - Each alert creates NEW oscillator (never reuses)
  - Restart sound on new alert instead of blocking
  - User gesture unlock required (banner shown if blocked)
  - Files: AlertSoundManager.js, GuardUI.js, service-worker.js

- **P0 Feature:** Session Persistence
  - Changed from sessionStorage to localStorage
  - Token persists across browser close/refresh
  - Auto-validates token on app load
  - Auto-refreshes if expired but refresh_token valid
  - File: AuthContext.js

- **P0 Fix:** Push Notifications Stop on Logout
  - New endpoint: DELETE /api/push/unsubscribe-all
  - Logout now: 1) Removes DB subscriptions, 2) Unsubscribes locally, 3) Clears auth
  - Users don't receive push after logout
  - Re-subscribes automatically on next login

### 2026-02-09 (Session 68)
- **UI Fix:** Login Page Cleanup
  - Removed "Create Demo Data" button and related functionality
  - Layout changed to `h-screen overflow-hidden` for no scroll
  - Form centered vertically and horizontally
  - Reduced spacing and sizes to fit 100vh
  - Verified no scroll on desktop (1920x800) and mobile (390x844)

### 2026-02-03 (Session 67)
- **Verification:** Confirmed Admin Settings Page refactor was already completed
  - Mobile-first design with collapsible sections
  - 5 organized sections: General, Reservaciones, Visitas, Seguridad, Sistema
  - Sticky save button on mobile
  - i18n integration complete
  - Both mobile (400x800) and desktop (1920x800) views verified working

- **P1 UX Enhancement:** Premium Panic Buttons Redesign
  - New circular button design (hero button ~240px, secondary ~120px)
  - Premium gradients with shimmer effect and breathing animations
  - Clear visual hierarchy: EMERGENCIA (orange), MÉDICA (red), SEGURIDAD (yellow)
  - Micro-interactions: ripple, scale feedback, hover glow
  - Haptic feedback differentiated by button type
  - Responsive: mobile portrait, landscape, and desktop layouts
  - GPS status badge redesigned with pulse animation
  - Files: `/app/frontend/src/styles/emergency-buttons.css` (v3), `ResidentUI.js`

- **P1 Integration:** Stripe TEST/DEMO Mode Integration
  - Backend: Added STRIPE_API_KEY (sk_test_...) and STRIPE_WEBHOOK_SECRET placeholder
  - Frontend: Added REACT_APP_STRIPE_PUBLIC_KEY (pk_test_...)
  - Verified checkout flow opens Stripe in Sandbox mode
  - No real money processed, keys not exposed in logs
  - Ready for production (just replace keys)

- **P1 Hardening:** System Stability & Smoke Test
  - Verified race condition protection on all critical buttons
  - Confirmed backend defensive validation (403/409 responses)
  - Verified UX feedback (toasts, loading states) on all actions
  - Navigation safety verified (no trapped users)
  - Mobile scroll and touch areas verified
  - Smoke test passed for all 5 roles: Super Admin, Admin, RRHH, Guard, Resident
  - Status: **READY FOR DEMO / READY FOR DEPLOY**

### 2025-02-02 (Session 66)
- **P1 Enhancement:** Improved Reservations Module UX
  - **Admin Area Configuration:**
    - Added `reservation_behavior` field: EXCLUSIVE, CAPACITY, SLOT_BASED, FREE_ACCESS
    - Added `max_capacity_per_slot` for CAPACITY type areas
    - Added `slot_duration_minutes` configuration
    - Added `max_reservations_per_user_per_day` limit
    - Visual selector for behavior types in area form
    - Conditional configuration panels based on behavior
  - **Resident Reservation UX:**
    - Visual slot grid with color coding (🟢 available, 🟡 limited, 🔴 occupied)
    - Click-to-select slots (no manual time input required)
    - Read-only time display after selection with "Cambiar" option
    - Always-visible rules and conditions panel
    - Behavior-specific messaging (exclusive, capacity, slot-based)
    - Remaining capacity display for CAPACITY areas
  - **Backend Validations:**
    - CAPACITY: Check guests_count against remaining slots
    - EXCLUSIVE: Check for overlapping reservations
    - SLOT_BASED: Exact slot matching
    - FREE_ACCESS: Prevent reservations
    - Clear error messages in Spanish

- **P1 Feature:** Implemented i18n Multi-language System
  - Backend: Added `language` field to user model and `PATCH /api/profile/language` endpoint
  - Frontend: Installed and configured `react-i18next`
  - Created translation files: `/src/i18n/es.json` (Spanish) and `/src/i18n/en.json` (English)
  - Created `LanguageSelector` component with real-time language switching
  - Added language selector to user profile (EmbeddedProfile)
  - Language persists in backend and localStorage
  - Language loads automatically on login
  - Default language: Spanish (es)

- **P0 Bug Fix:** Fixed horizontal scroll on RRHH tabs in mobile view
- **P0 Bug Fix:** Fixed vertical scroll on RRHH module in mobile view

## Vision
GENTURIX is a security and emergency platform for real people under stress. Emergency-first design, not a corporate dashboard.

---

## PLATFORM STATUS: ✅ PRODUCTION READY

### Session 65 - P1 FEATURE: Condominium Settings Module (February 2, 2026) ⭐⭐⭐⭐⭐

**Feature Request:**
Crear un módulo de configuración centralizado para el Administrador que permita definir reglas globales del condominio, consumidas por otros módulos (reservas, visitas, notificaciones).

**Implementation:**

**1. Backend:**
- New collection: `condominium_settings`
- Endpoints:
  - `GET /api/admin/condominium-settings` - Get settings (Admin only)
  - `PUT /api/admin/condominium-settings` - Update settings (Admin only)
  - `GET /api/condominium-settings/public` - Read-only for all authenticated users
- Auto-creation of default settings when condominium is created

**2. Data Model:**
```json
{
  "condominium_id": "...",
  "general": {
    "timezone": "America/Mexico_City",
    "working_hours": { "start": "06:00", "end": "22:00" }
  },
  "reservations": {
    "enabled": true,
    "max_active_per_user": 3,
    "allow_same_day": true,
    "approval_required_by_default": false,
    "min_hours_advance": 1,
    "max_days_advance": 30
  },
  "visits": {
    "allow_resident_preregistration": true,
    "allow_recurrent_visits": true,
    "allow_permanent_visits": false,
    "require_id_photo": false,
    "max_preregistrations_per_day": 10
  },
  "notifications": {
    "panic_sound_enabled": true,
    "push_enabled": true,
    "email_notifications_enabled": true
  }
}
```

**3. Frontend:**
- New page: `/admin/settings` (`CondominiumSettingsPage.js`)
- 4 tabs: General | Reservaciones | Visitas | Notificaciones
- Change detection with "unsaved changes" warning
- Save/Discard buttons
- Mobile-friendly responsive design

**4. Access Control:**
- Only Administrador role can view and modify settings
- Guards and Residents cannot see "Configuración" in sidebar
- Non-admin users redirected if they try to access URL directly

**Testing Results:**
- Backend: 100% (14/14 tests passed)
- Frontend: 100% (all UI flows verified)
- Test report: `/app/test_reports/iteration_65.json`

**Files Created/Modified:**
- `/app/backend/server.py` - Models + endpoints
- `/app/frontend/src/pages/CondominiumSettingsPage.js` - New page
- `/app/frontend/src/services/api.js` - API methods
- `/app/frontend/src/App.js` - Route added
- `/app/frontend/src/components/layout/Sidebar.js` - Link updated
- `/app/frontend/src/components/layout/DashboardLayout.js` - Mobile nav updated

---

### Session 64 - P1 FEATURE: Admin Onboarding via Invite Link/QR (February 2, 2026) ⭐⭐⭐⭐⭐

**Feature Request:**
Implement a secure onboarding flow where condominium administrators can invite residents via link or QR, and approve or reject access requests.

**Implementation:**

**1. Backend Endpoints (New):**
- `POST /api/invitations` - Create invitation link (Admin)
- `GET /api/invitations` - List invitations (Admin)
- `DELETE /api/invitations/{id}` - Revoke invitation (Admin)
- `GET /api/invitations/{token}/info` - Get condo info (Public)
- `POST /api/invitations/{token}/request` - Submit access request (Public)
- `GET /api/invitations/{token}/request-status` - Check request status (Public)
- `GET /api/access-requests` - List access requests (Admin)
- `GET /api/access-requests/count` - Get pending count (Admin)
- `POST /api/access-requests/{id}/action` - Approve/Reject request (Admin)

**2. Database Collections (New):**
- `invitations`: token, condominium_id, expires_at, usage_limit_type (single/unlimited/fixed), max_uses, current_uses, is_active
- `access_requests`: invitation_id, condominium_id, full_name, email, apartment_number, status (pending_approval/approved/rejected)

**3. Frontend Components (New/Modified):**
- **UserManagementPage.js** - Added 3 tabs:
  - Usuarios (existing users table)
  - Solicitudes (access requests with badge count)
  - Invitaciones (invitation link management)
- **JoinPage.js** - New public page at `/join/{token}` for access requests
- **App.js** - Added public route for JoinPage

**4. Key Features:**
- ✅ Configurable expiration: 7 / 30 / 90 / 365 days
- ✅ Configurable usage limits: Single use / Unlimited / Fixed number
- ✅ QR code generation (qrcode.react library)
- ✅ Copy link to clipboard
- ✅ Email notifications on approve/reject (via Resend)
- ✅ Temporary password generation on approval
- ✅ Public status check for requestors
- ✅ Full audit logging

**Testing Results:**
- Backend: 100% (18/18 tests passed)
- Frontend: 100% (all UI flows verified)
- Test report: `/app/test_reports/iteration_64.json`

**Files Modified:**
- `/app/backend/server.py` - Added invitation & access request models/endpoints
- `/app/frontend/src/services/api.js` - Added API methods
- `/app/frontend/src/pages/UserManagementPage.js` - Added InvitationsSection, AccessRequestsTab
- `/app/frontend/src/pages/JoinPage.js` - New public page
- `/app/frontend/src/App.js` - Added JoinPage route

---

### Session 63 - P0 REGRESSION FIX: Alert Sound Duplication + Map Verification (February 2, 2026) ⭐⭐⭐⭐⭐

**Bug Reported:**
- Alert sound playing twice (duplicated audio trigger)
- Alert notifications not displaying embedded map/location
- Sound not stopping when guard opens/acknowledges alert

**Root Cause Analysis:**
1. **Sound Duplication:** Multiple listeners in both `App.js` (global) and `GuardUI.js` (component) were processing service worker messages. Service worker was also sending to ALL clients instead of one.
2. **Map Issue:** VERIFIED WORKING - The active test alert had `null` coordinates. Map displays correctly when coordinates are present.

**Solution:**

**1. App.js Cleanup:**
- Removed ALL sound-related service worker listeners (60+ lines)
- Now only contains PostHog error suppression

**2. GuardUI.js - Centralized Sound Control:**
```javascript
// Refs to track sound state
const soundAcknowledgedRef = React.useRef(false);
const soundTimeoutRef = React.useRef(null);

// Centralized stop function
const stopAlertSound = useCallback(() => {
  soundAcknowledgedRef.current = true;
  clearTimeout(soundTimeoutRef.current);
  AlertSoundManager.stop();
}, []);

// Single listener for ALL sound messages
useEffect(() => {
  const handleServiceWorkerMessage = (event) => {
    if (event.data?.type === 'PLAY_PANIC_SOUND') {
      if (soundAcknowledgedRef.current) return; // Already acknowledged
      if (AlertSoundManager.getIsPlaying()) return; // Already playing
      AlertSoundManager.play();
    }
    if (['PANIC_ALERT_CLICK','STOP_PANIC_SOUND','NOTIFICATION_CLICKED','NOTIFICATION_CLOSED'].includes(event.data?.type)) {
      stopAlertSound();
    }
  };
  navigator.serviceWorker?.addEventListener('message', handleServiceWorkerMessage);
  return () => navigator.serviceWorker?.removeEventListener('message', handleServiceWorkerMessage);
}, [stopAlertSound]);
```

**3. Service Worker Fix:**
```javascript
// Only send to ONE client (prevents multiple tabs playing)
let targetClient = clients.find(c => c.focused) || 
                   clients.find(c => c.visibilityState === 'visible') || 
                   clients[0];
if (targetClient) {
  targetClient.postMessage({ type: 'PLAY_PANIC_SOUND', data: notification.data });
}
```

**Testing Results:**

| Test | Result |
|------|--------|
| Alert modal opens | ✅ PASS |
| Map shows with coordinates | ✅ PASS |
| Map hidden without coords | ✅ PASS |
| GPS badge on cards | ✅ PASS |
| Sound stops on tab nav | ✅ PASS |
| Sound stops on click | ✅ PASS |
| Sound stops on resolve | ✅ PASS |
| Single client receives msg | ✅ PASS |
| Mobile view works | ✅ PASS |

**Files Modified:**
- `/app/frontend/src/App.js` - Removed sound listeners
- `/app/frontend/src/pages/GuardUI.js` - Centralized sound control with refs
- `/app/frontend/public/service-worker.js` - Single client messaging

**Testing Status:**
- ✅ Frontend: 100% (24/24)
- ✅ Test report: `/app/test_reports/iteration_63.json`

---

### Session 62 - P0 BUG FIX: Guard Visitas Tab Was Empty (February 2, 2026) ⭐⭐⭐⭐⭐

**Bug Reported:**
- Módulo "Visitas" del guardia estaba vacío
- No mostraba pre-registros, entradas activas, ni salidas
- Todo aparecía solo en Check-In

**Solution:**

**1. New Backend Endpoint:**
```python
@api_router.get("/guard/visits-summary")
# Returns: {pending: [], inside: [], exits: []}
# Fixed: exits query now uses "status": {"$in": ["exited", "completed"]}
```

**2. Rewritten VisitsTab Component:**
- 3 section tabs: Dentro, Pendientes, Salidas
- **Pendientes agrupados por residente** con acordeón expandible
- READ-ONLY mode (no action buttons)
- Message directing users to Check-In for actions
- VisitCard component with badges for visitor type

**3. Mobile Navigation Updated:**
- Added "Visitas" to GUARD_MOBILE_NAV

**4. Bug Fix - Exits Not Showing:**
- Changed status query from `"exited"` to `{"$in": ["exited", "completed"]}`
- Now correctly shows all exits (49 shown in test)

**Testing Results:**

| Test | Result |
|------|--------|
| 3 sections visible | ✅ PASS |
| Pendientes grouped by resident | ✅ PASS |
| Exits showing (49 today) | ✅ PASS |
| NO action buttons (READ-ONLY) | ✅ PASS |
| Mobile works | ✅ PASS |

**Files Modified:**
- `/app/backend/server.py` - Added `/guard/visits-summary` endpoint, fixed exits query
- `/app/frontend/src/services/api.js` - Added `getVisitsSummary()`
- `/app/frontend/src/pages/GuardUI.js` - Rewritten VisitsTab with Accordion, added to GUARD_MOBILE_NAV

**Testing Status:**
- ✅ Backend: 100% (2/2)
- ✅ Frontend: 100% (14/14)
- ✅ Test report: `/app/test_reports/iteration_62.json`

---

### Session 62 - UX FIX: Mobile Scroll Enhancement (February 2, 2026) ⭐⭐⭐⭐

**Issue Reported:**
- Contenido vertical potencialmente cortado en Admin/RRHH móvil
- Necesidad de asegurar scroll completo

**Solution:**
- Refactored DashboardLayout mobile to use flex layout with explicit overflow-y-auto
- Header: sticky fixed at top (flex-shrink-0)
- Content: flex-1 overflow-y-auto (scrollable area)
- BottomNav: fixed at bottom (flex-shrink-0)

**Testing Results:**
- ✅ RRHH page: scrollHeight 1024, scrolls correctly
- ✅ Dashboard page: scrollHeight 1354, full scroll
- ✅ Users page: scrollHeight 6304, scroll to 5460 (full content)
- ✅ Desktop: No regressions

---

### Session 62 - UX FIX: Remove Useless Hamburger Menu in Admin Mobile (February 2, 2026) ⭐⭐⭐

**Issue Reported:**
- Ícono de menú hamburguesa (☰) en mobile Admin no hacía nada
- Generaba confusión visual y mala UX

**Solution:**
- Eliminado el botón de menú hamburguesa del header móvil en DashboardLayout
- La navegación inferior se mantiene funcional
- Desktop no afectado

**Files Modified:**
- `/app/frontend/src/components/layout/DashboardLayout.js` - Removed hamburger button, improved flex layout for mobile

**Testing Status:**
- ✅ Verificado móvil scroll en Dashboard, RRHH, Users
- ✅ Verificado desktop sin regresiones

---

### Session 61 - P1 FEATURE: Area Rules Visibility for Residents (February 2, 2026) ⭐⭐⭐⭐⭐

**Feature Requested:**
- Mostrar las reglas de áreas comunes definidas por el admin a los residentes
- Reglas visibles en tarjetas de área y formulario de reserva
- Reglas de solo lectura para residentes

**Implementation:**

**1. AreaCard Component Updated:**
- Added expandable "Reglas del área" toggle with chevron rotation
- Blue panel with multiline rules when expanded
- Only shows toggle if area has rules defined

**2. ReservationFormDialog Updated:**
- Blue panel with "📌 Reglas del área" header before confirm button
- Multiline formatting preserved with scroll for long rules
- Gray panel with "Este espacio no tiene reglas adicionales" for areas without rules

**Testing Results:**

| Test | Result |
|------|--------|
| Toggle visible in card | ✅ PASS |
| Rules expand/collapse | ✅ PASS |
| Multiline preserved | ✅ PASS |
| Rules in form | ✅ PASS |
| No rules message | ✅ PASS |
| Read-only for residents | ✅ PASS |

**Files Modified:**
- `/app/frontend/src/components/ResidentReservations.jsx` - AreaCard, ReservationFormDialog

**Testing Status:**
- ✅ Frontend: 100% (11/11)
- ✅ Backend: 100% (2/2)
- ✅ Test report: `/app/test_reports/iteration_61.json`

---

### Session 60 - P1 FEATURE: Visitor Types for Resident Authorizations (February 2, 2026) ⭐⭐⭐⭐⭐

**Feature Requested:**
- Permitir que los residentes también puedan crear pre-registros de tipos de servicio (Delivery, Mantenimiento, etc.)
- Los mismos tipos que el guardia pero para autorizaciones del residente

**Implementation:**

**1. Resident Authorization Form Updated:**
- Added "Tipo de Persona" selector with 6 options
- Dynamic fields based on type selection
- Company is required for service types

**2. Authorization Card Updated:**
- Shows visitor type badge with color (Delivery=yellow, Maintenance=blue, etc.)
- Displays company name and service type in details section

**3. Backend Updates:**
```python
class VisitorAuthorizationCreate(BaseModel):
    visitor_type: Optional[str] = "visitor"
    company: Optional[str] = None
    service_type: Optional[str] = None
```

**Testing Results:**

| Test | Result |
|------|--------|
| 6 visitor types in form | ✅ PASS |
| Dynamic fields work | ✅ PASS |
| Company validation | ✅ PASS |
| Create Delivery authorization | ✅ PASS |
| Badge on card | ✅ PASS |
| Company displayed | ✅ PASS |
| Guard sees visitor_type | ✅ PASS |

**Files Modified:**
- `/app/frontend/src/components/VisitorAuthorizationsResident.jsx` - AuthorizationFormDialog, AuthorizationCard
- `/app/backend/server.py` - VisitorAuthorizationCreate, VisitorAuthorizationUpdate models

**Testing Status:**
- ✅ Backend: 100% (9/9)
- ✅ Frontend: 100% (7/7)
- ✅ Test report: `/app/test_reports/iteration_60.json`

---

### Session 59 - P1 FEATURE: Visitor Types for Guard Manual Check-In (February 2, 2026) ⭐⭐⭐⭐⭐

**Feature Requested:**
- Agregar roles recurrentes predefinidos al Registro Manual del Guardia
- Campos dinámicos según el tipo de visitante
- Badges de color en el historial

**Implementation:**

**1. Visitor Types Configuration:**
```jsx
const VISITOR_TYPES = {
  visitor: { label: 'Visitante', color: 'gray', icon: Users },
  delivery: { label: 'Delivery', color: 'yellow', icon: Package },
  maintenance: { label: 'Mantenimiento', color: 'blue', icon: Wrench },
  technical: { label: 'Servicio Técnico', color: 'purple', icon: Cpu },
  cleaning: { label: 'Limpieza', color: 'green', icon: Sparkles },
  other: { label: 'Otro', color: 'orange', icon: MoreHorizontal }
};
```

**2. Dynamic Fields by Type:**

| Type | Required Fields | Optional Fields |
|------|-----------------|-----------------|
| Visitor | Nombre | ID, Placa, Destino |
| Delivery | Empresa | Repartidor, Destino, Tipo Entrega |
| Mantenimiento | Empresa, Técnico, Área | ID, Tipo Servicio, Autorizado por |
| Limpieza | Empresa/Persona | ID, Horario, Área, Destino |
| Otro | Nombre | Descripción, ID, Destino |

**3. Backend Fields Added:**
```python
class FastCheckInRequest(BaseModel):
    visitor_type: Optional[str] = "visitor"
    company: Optional[str] = None
    service_type: Optional[str] = None
    authorized_by: Optional[str] = None  # resident, admin, guard
    estimated_time: Optional[str] = None
```

**Testing Results:**

| Test | Result |
|------|--------|
| 6 visitor types in UI | ✅ PASS |
| Dynamic fields work | ✅ PASS |
| Required field validation | ✅ PASS |
| Backend saves all fields | ✅ PASS |
| Color badges in visitors inside | ✅ PASS |
| Pre-registrations unchanged | ✅ PASS |

**Files Modified:**
- `/app/frontend/src/components/VisitorCheckInGuard.jsx` - ManualCheckInDialog with dynamic fields, VisitorInsideCard with badges
- `/app/backend/server.py` - FastCheckInRequest model, entry_doc fields

**Testing Status:**
- ✅ Backend: 100% (4/4)
- ✅ Frontend: 100% (11/11)
- ✅ Test report: `/app/test_reports/iteration_59.json`

---

### Session 59 - P1 UI ENHANCEMENT: Guard Pre-registrations Grouped by Resident (February 2, 2026) ⭐⭐⭐⭐⭐

**Feature Requested:**
- Agrupar los pre-registros pendientes en la UI del guardia por residente
- Reducir el desorden visual cuando hay muchas autorizaciones
- Mejorar la operatividad del guardia

**Implementation:**
- Utiliza componente Accordion de Shadcn para crear grupos colapsables
- Autorizaciones agrupadas por `created_by` (ID del residente) usando `Array.reduce()`
- Cada grupo muestra: nombre del residente, apartamento, badge con conteo de visitantes
- Grupos expandidos por defecto (`defaultValue={residentKeys}`)
- Búsqueda sigue mostrando resultados en lista plana

**Code Changes:**

```jsx
// VisitorCheckInGuard.jsx - Grouping logic
const groupedByResident = todayPreregistrations.reduce((acc, auth) => {
  const residentKey = auth.created_by || 'unknown';
  if (!acc[residentKey]) {
    acc[residentKey] = {
      resident_name: auth.created_by_name || 'Residente',
      resident_apartment: auth.resident_apartment || '',
      authorizations: []
    };
  }
  acc[residentKey].authorizations.push(auth);
  return acc;
}, {});

// Render with Accordion
<Accordion type="multiple" defaultValue={residentKeys}>
  {residentKeys.map((residentKey) => (
    <AccordionItem key={residentKey} value={residentKey}>
      <AccordionTrigger>
        {group.resident_name} - {group.authorizations.length} visitantes
      </AccordionTrigger>
      <AccordionContent>
        {group.authorizations.map(auth => <AuthorizationSearchCard ... />)}
      </AccordionContent>
    </AccordionItem>
  ))}
</Accordion>
```

**Testing Results:**

| Test | Result |
|------|--------|
| Accordion groups by resident | ✅ PASS |
| Shows resident name | ✅ PASS |
| Shows visitor count badge | ✅ PASS |
| Accordion expand/collapse | ✅ PASS |
| Default expanded | ✅ PASS |
| REGISTRAR ENTRADA button works | ✅ PASS |
| Search shows flat list | ✅ PASS |
| Clear search restores accordion | ✅ PASS |

**Files Modified:**
- `/app/frontend/src/components/VisitorCheckInGuard.jsx` - Added Accordion import, grouping logic

**Testing Status:**
- ✅ 100% frontend tests passed (15/15)
- ✅ Test report: `/app/test_reports/iteration_58.json`

---

### Session 58 - P0 CRITICAL: Resident Cannot Delete Authorization When Visitor Inside (February 2, 2026) ⭐⭐⭐⭐⭐

**Critical Bug Reported:**
- Residente podía eliminar autorizaciones incluso cuando la persona YA ESTABA DENTRO del condominio
- Esto causaba que el guarda perdiera el control de quién está adentro

**Business Rules Implemented:**

| Visitor Status | Residente Puede Eliminar? |
|----------------|---------------------------|
| PENDING | ✅ SÍ |
| EXITED | ✅ SÍ |
| **INSIDE** | ❌ **NO** |

**Backend Implementation:**

```python
# GET /api/authorizations/my - Added has_visitor_inside field
active_inside = await db.visitor_entries.find_one({
    "authorization_id": auth.get("id"),
    "status": "inside"
}, {"_id": 0, "id": 1})
auth["has_visitor_inside"] = active_inside is not None

# DELETE /api/authorizations/{auth_id} - Block when inside
if is_resident:
    active_entry = await db.visitor_entries.find_one({
        "authorization_id": auth_id,
        "status": "inside"
    })
    if active_entry:
        raise HTTPException(
            status_code=403, 
            detail="No puedes eliminar esta autorización mientras la persona esté dentro del condominio. Contacta al guarda para registrar su salida primero."
        )
```

**Frontend Implementation:**

```jsx
// VisitorAuthorizationsResident.jsx
const canDelete = !auth.has_visitor_inside;

{canDelete ? (
  <Button onClick={() => onDelete(auth)}>
    <Trash2 className="w-4 h-4" />
  </Button>
) : (
  <div className="text-yellow-400 bg-yellow-500/10">
    <Shield className="w-3.5 h-3.5 mr-1.5" />
    Dentro
  </div>
)}
```

**Testing Results:**

| Test | Result |
|------|--------|
| Backend: has_visitor_inside in response | ✅ PASS |
| Backend: DELETE returns 403 when inside | ✅ PASS |
| Backend: DELETE works when PENDING | ✅ PASS |
| Frontend: Shows "Dentro" indicator | ✅ PASS |
| Frontend: Shows delete button when not inside | ✅ PASS |
| Guard: Can see visitors inside | ✅ PASS |

**Files Modified:**
- `/app/backend/server.py` - GET /api/authorizations/my + DELETE endpoint
- `/app/frontend/src/components/VisitorAuthorizationsResident.jsx` - Conditional delete

**Testing Status:**
- ✅ 100% backend tests passed (9/9)
- ✅ 100% frontend tests passed
- ✅ Test report: `/app/test_reports/iteration_57.json`

---

### Session 57 - P0 UX Fix: Resident Profile Directory Modal (February 2, 2026) ⭐⭐⭐⭐⭐

**Reported Issue:**
- Rol RESIDENTE: Al hacer clic en un perfil del directorio → vista aislada sin navegación
- Usuario quedaba "atrapado" y debía cerrar sesión para salir

**Root Cause:**
- `ProfileDirectory` navegaba a `/profile/{id}` cuando `embedded=true`
- La página `/profile/{id}` no tiene navegación del rol

**Solution Implemented:**
Cuando `embedded=true`, los perfiles ahora se muestran en un **MODAL** en lugar de navegar a página separada.

**Code Changes:**

```jsx
// ProfileDirectory.jsx - NEW handleViewProfile logic
const handleViewProfile = async (userId, userBasicInfo) => {
  if (onViewProfile) {
    onViewProfile(userId);  // Parent handler
  } else if (embedded) {
    // EMBEDDED MODE: Show profile in modal (no navigation)
    setProfileModalUser(userBasicInfo);
    setProfileModalOpen(true);
    // Optionally fetch full profile data
    const fullProfile = await api.getPublicProfile(userId);
    setProfileModalUser(prev => ({ ...prev, ...fullProfile }));
  } else {
    navigate(`/profile/${userId}`);  // Non-embedded: normal navigation
  }
};
```

**Modal Features:**
- ✅ Botón volver (←) - data-testid="profile-modal-back"
- ✅ Botón cerrar (X)
- ✅ Avatar con inicial o foto
- ✅ Nombre y badges de rol
- ✅ Teléfono (clickable para llamar)
- ✅ Email (clickable para enviar correo)
- ✅ Unidad/apartamento
- ✅ Descripción pública

**Testing Results:**

| Test | Desktop | Mobile |
|------|---------|--------|
| Click perfil abre modal | ✅ PASS | ✅ PASS |
| URL permanece en /resident | ✅ PASS | ✅ PASS |
| Modal tiene botón volver | ✅ PASS | ✅ PASS |
| Navegación visible después de cerrar | ✅ PASS | ✅ PASS |
| Bottom nav visible (mobile) | N/A | ✅ PASS |
| Ver múltiples perfiles sin quedar atrapado | ✅ PASS | ✅ PASS |
| Reload mantiene en /resident | ✅ PASS | ✅ PASS |

**Files Modified:**
- `/app/frontend/src/components/ProfileDirectory.jsx` - Modal para perfiles embedded

**Testing Status:**
- ✅ 100% frontend tests passed
- ✅ Test report: `/app/test_reports/iteration_56.json`

**Note:** Este fix también beneficia al rol GUARDIA que usa el mismo componente `ProfileDirectory` con `embedded={true}`.

---

### Session 56 - P0 Bug [object Object] al crear 4ta área: VERIFIED FIXED (February 2, 2026)

**Reported Issue:**
- "Error [object Object] al crear la 4ta área común"
- Las primeras 3 áreas se crean bien, la 4ta falla

**Investigation Results:**

| Test | Result |
|------|--------|
| Create 5 areas via API | ✅ All created successfully |
| Create 6 areas via API | ✅ All created successfully |
| Create 4 areas via UI | ✅ All created successfully |
| Create reservation in 8th area | ✅ Works correctly |
| [object Object] error | ❌ NOT reproduced |

**Root Cause & Fix:**
- **Root cause:** Error objects were previously displayed directly without extracting `.message`
- **Fix applied in Session 53:** Added robust error handling pattern
- **Pattern:** `error?.message || (typeof error === 'string' ? error : 'Error al guardar')`

**Files with error handling (verified):**
- `ReservationsModule.js` - handleSaveArea() line ~881-895
- `ReservationsModule.js` - handleCreateReservation() line ~911-920
- `AreaFormDialog` - handleSave() line ~418-437

**Testing Status:**
- ✅ 100% backend tests passed
- ✅ 100% frontend UI tests passed
- ✅ Test report: `/app/test_reports/iteration_55.json`

**Conclusion:** Bug was already fixed in Session 53. No additional code changes needed.

---

### Session 55 - P0 Bug Investigation: Guard Visitas Module (February 2, 2026) ⭐⭐⭐⭐⭐

**Reported Issue:**
- "El módulo carga correctamente, el formulario permite ingresar datos, pero NO se crea ningún registro real"

**Investigation Results:**

| Test | Result |
|------|--------|
| Backend POST /api/guard/checkin | ✅ Works - Creates record in visitor_entries |
| Visitor appears in history | ✅ Works - Shows in GET /api/guard/history |
| Visitor appears in "inside" | ✅ Works - Shows in GET /api/guard/visitors-inside |
| Checkout flow | ✅ Works - POST /api/guard/checkout/{id} |

**Root Cause Analysis:**
The issue was **NOT a bug**, but **user confusion** between two tabs:

| Tab | Purpose | Has Manual Entry? |
|-----|---------|-------------------|
| **Visitas** | Shows pre-registered visitors (authorizations) | ❌ No - only shows existing pre-registrations |
| **Check-In** | Search visitors, manual entry, visitors inside | ✅ Yes - "Entrada Manual (Sin Autorización)" button |

**UX Improvement Implemented:**
Added helpful message in "Visitas" tab:
> "💡 Aquí ves pre-registros. Para entrada manual sin pre-registro, usa la pestaña **Check-In**"

**Correct Manual Entry Flow:**
1. Guard logs in
2. Navigate to **Check-In** tab
3. Click **"Entrada Manual (Sin Autorización)"** button
4. Fill visitor name (required) and optional fields
5. Click **"REGISTRAR ENTRADA"**
6. Toast: "⚠️ Entrada manual registrada" appears
7. Visitor appears in "DENTRO DEL CONDOMINIO" section

**Testing Status:**
- ✅ 100% backend tests passed
- ✅ 100% frontend UI tests passed
- ✅ Test report: `/app/test_reports/iteration_54.json`

**Files Modified:**
- `/app/frontend/src/pages/GuardUI.js` - Added UX hint in VisitsTab, improved error toasts

---

### Session 54 - P0 FEATURE: Sistema de Cancelación de Reservaciones (February 1, 2026) ⭐⭐⭐⭐⭐

**Feature Implemented:**
Sistema completo de cancelación de reservaciones para residentes y administradores con reglas de negocio específicas.

**Business Rules:**

| Rol | Puede Cancelar | Restricciones |
|-----|----------------|---------------|
| Residente | Solo sus propias reservaciones | Status: pending/approved, NO iniciada |
| Admin | Cualquier reservación del condominio | Excepto status: completed |

**Backend Implementation:**

```python
# DELETE /api/reservations/{reservation_id}
# Soft delete - cambia status a 'cancelled', NO borra físicamente

# Campos actualizados al cancelar:
{
    "status": "cancelled",
    "cancelled_at": "2026-02-01T14:30:00Z",
    "cancelled_by": "user_id",
    "cancelled_by_role": "Administrador|Residente",
    "cancellation_reason": "Opcional - solo admin"
}
```

**Endpoint Response:**
```json
{
  "message": "Reservación cancelada exitosamente. El espacio ha sido liberado.",
  "reservation_id": "uuid",
  "cancelled_by": "resident|admin"
}
```

**Validation Errors:**
- 403: "Solo puedes cancelar tus propias reservaciones"
- 400: "No se puede cancelar una reservación ya completada"
- 400: "Esta reservación ya fue cancelada"
- 400: "No puedes cancelar una reservación que ya inició o está en progreso"

**Frontend Implementation:**

**1. ResidentReservations.jsx:**
- `MyReservationCard` - Botón "Cancelar Reservación" visible solo si:
  - Status es `pending` o `approved`
  - Fecha/hora de inicio NO ha pasado
- Modal de confirmación con info de la reservación
- Toast: "Reservación cancelada. El espacio ha sido liberado."

**2. ReservationsModule.js (Admin):**
- Nueva pestaña "Todas" - muestra todas las reservaciones aprobadas
- `ReservationCard` - Botón "Cancelar Reservación" (naranja)
- Modal con campo de motivo opcional
- Mensaje: "El residente recibirá una notificación con este motivo."
- Toast de éxito al cancelar

**Files Modified:**
- `/app/backend/server.py` - DELETE endpoint (~línea 6840)
- `/app/frontend/src/services/api.js` - cancelReservation method
- `/app/frontend/src/components/ResidentReservations.jsx` - cancel flow
- `/app/frontend/src/pages/ReservationsModule.js` - admin cancel flow + "Todas" tab

**Testing Status:**
- ✅ 100% backend API tests passed
- ✅ 100% frontend UI tests passed
- ✅ Test report: `/app/test_reports/iteration_53.json`

---

### Session 53 - P0 FIX: Reservations [object Object] Bug (February 1, 2026) ⭐⭐⭐⭐⭐

**Problem:**
- Al crear/editar áreas o reservaciones, en caso de error se mostraba `[object Object]` en vez del mensaje de error real
- El error afectaba tanto al Admin (creación de áreas) como al Residente (creación de reservaciones)
- Los handlers no tenían try-catch apropiado, causando que errores no manejados mostraran objetos crudos

**Root Cause:**
- Los handlers `handleSaveArea()`, `handleCreateReservation()`, `handleUpdateReservation()` en `ReservationsModule.js` no tenían manejo de errores
- El handler `handleCreateReservation()` en `ResidentReservations.jsx` tampoco tenía try-catch
- Cuando ocurría un error, el objeto de error se pasaba directamente a `toast.error()` sin extraer `.message`

**Solution Implemented:**

**1. ReservationsModule.js - Error Handling:**
```javascript
// handleSaveArea - Line 814
const handleSaveArea = async (formData, areaId) => {
  try {
    // ... API calls
    toast.success('Área creada/actualizada');
    fetchData();
  } catch (error) {
    const errorMessage = error?.message || (typeof error === 'string' ? error : 'Error al guardar área');
    toast.error(errorMessage);
    throw error;
  }
};

// handleCreateReservation - Line 838
const handleCreateReservation = async (formData) => {
  try {
    await api.createReservation(formData);
    toast.success('Reservación creada');
    fetchData();
  } catch (error) {
    const errorMessage = error?.message || (typeof error === 'string' ? error : 'Error al crear reservación');
    toast.error(errorMessage);
    throw error;
  }
};

// handleUpdateReservation - Line 856
const handleUpdateReservation = async (reservationId, status, notes) => {
  try {
    await api.updateReservationStatus(reservationId, { status, admin_notes: notes });
    toast.success(`Reservación ${status === 'approved' ? 'aprobada' : 'rechazada/cancelada'}`);
    fetchData();
  } catch (error) {
    const errorMessage = error?.message || (typeof error === 'string' ? error : 'Error al actualizar');
    toast.error(errorMessage);
  }
};
```

**2. ResidentReservations.jsx - Error Handling:**
```javascript
// handleCreateReservation - Line 703
const handleCreateReservation = async (reservationData) => {
  try {
    await api.createReservation(reservationData);
    toast.success('Reservación creada exitosamente');
    loadData();
  } catch (error) {
    const errorMessage = error?.message || (typeof error === 'string' ? error : 'Error al crear');
    toast.error(errorMessage);
    throw error;
  }
};
```

**3. Dialog Catch Blocks Updated:**
- `AreaFormDialog.handleSave()` - Line 374
- `ReservationFormDialog.handleSave()` - Line 613 (both files)
- All use: `error?.message || (typeof error === 'string' ? error : 'Fallback message')`

**Files Modified:**
- `/app/frontend/src/pages/ReservationsModule.js` - 4 handlers updated
- `/app/frontend/src/components/ResidentReservations.jsx` - 2 handlers updated

**Testing Status:**
- ✅ 100% backend API tests passed (17/17)
- ✅ 100% frontend UI tests passed
- ✅ NO [object Object] in any error scenario
- ✅ All toast messages show readable Spanish text
- ✅ Test report: `/app/test_reports/iteration_52.json`

**Toast Messages Verified:**
| Action | Toast Message |
|--------|---------------|
| Área creada | "Área creada" |
| Área actualizada | "Área actualizada" |
| Área eliminada | "Área eliminada" |
| Reservación creada | "Reservación creada exitosamente" |
| Reservación aprobada | "Reservación aprobada" |
| Reservación rechazada | "Reservación rechazada" |
| Reservación cancelada | "Reservación cancelada" |
| Error (cualquiera) | Mensaje legible en español |

---

### Session 52 - P0 FIX: Push Notifications Not Working (February 1, 2026) ⭐⭐⭐⭐⭐

**Problem:**
- No llegaban push notifications
- No visual, no sonido
- Afectaba tanto a Guardia como a Residente

**Root Cause:**
- Service Worker NO estaba siendo registrado en `index.js`
- El endpoint VAPID devolvía `vapid_public_key` pero frontend esperaba `publicKey`

**Solution Implemented:**

**1. Service Worker Registration (index.js):**
```javascript
// NEW: Service Worker registration added
const registerServiceWorker = async () => {
  const registration = await navigator.serviceWorker.register('/service-worker.js');
  console.log('[SW] Service Worker registered:', registration.scope);
};
window.addEventListener('load', registerServiceWorker);
```

**2. Service Worker Rewritten (service-worker.js v4):**
```javascript
// Push handler with friendly notifications
self.addEventListener('push', (event) => {
  const options = {
    body: payload.body,
    icon: '/logo192.png',
    silent: false, // Let system play sound
    vibrate: isPanic ? [300,100,300] : [100,50,100], // Friendly short vibration
    requireInteraction: isPanic, // Only panic needs interaction
    tag: payload.tag // Prevents duplicates
  };
  self.registration.showNotification(title, options);
});
```

**3. New PushNotificationManager Utility:**
- `/app/frontend/src/utils/PushNotificationManager.js`
- Clean API for permission request, subscription, and format

**4. Push Permission Banner:**
- `/app/frontend/src/components/PushPermissionBanner.jsx`
- Friendly banner asking users to enable notifications
- Shows on first load if permission is `default`
- Can be dismissed for 1 hour

**5. Backend Fix:**
- Fixed VAPID key response: `vapid_public_key` → `publicKey`
- Residents can now subscribe to push (was guards-only)

**Files Created/Modified:**
- `/app/frontend/src/index.js` - Added SW registration
- `/app/frontend/public/service-worker.js` - Complete rewrite v4
- `/app/frontend/src/utils/PushNotificationManager.js` - NEW
- `/app/frontend/src/components/PushPermissionBanner.jsx` - NEW
- `/app/frontend/src/pages/ResidentUI.js` - Added push subscription
- `/app/frontend/src/pages/GuardUI.js` - Added push subscription

**Testing Status:**
- ✅ Service Worker registers correctly
- ✅ Permission prompt shows on user action
- ✅ Backend sends push (verified in logs)
- ✅ Notifications stored in DB
- ⚠️ Real device test needed (Playwright can't accept permission prompts)

---

### Session 52 - Contextual Push Notifications (February 1, 2026) ⭐⭐⭐⭐⭐

**Objective:**
Implementar notificaciones push contextuales basadas en eventos reales del sistema.

**Events with Push Notifications:**

| Event | Target User | Push Message |
|-------|-------------|--------------|
| Check-in | Resident | 🚪 Tu visitante ha llegado: {nombre} |
| Check-out | Resident | 👋 Tu visitante ha salido: {nombre} (duración) |
| Pre-registration | Guards | 📋 Nuevo visitante preregistrado |
| Reservation created (auto-approved) | Resident | ✅ Reservación confirmada |
| Reservation pending | Admins | 📅 Nueva reservación pendiente |
| Reservation approved | Resident | ✅ Reservación aprobada |
| Reservation rejected | Resident | ❌ Reservación rechazada (motivo) |

**Duplicate Prevention:**
```python
# Check for duplicate within 1 minute window
duplicate_check = {
    "type": notification_type,
    "user_id": user_id,
    "created_at": {"$gte": 1_minute_ago}
}
```
- ✅ VAPID key endpoint works
- ✅ Notifications appear in bell dropdown
- ✅ No duplicate notifications

---

### Session 52 - P0 UX: Emergency Hero Action Layout (February 1, 2026) ⭐⭐⭐⭐⭐

**Objective:**
Rediseñar la interfaz de botones de pánico con layout premium tipo "Hero Action".

**New Layout Structure:**
```
┌─────────────────────────────────────┐
│         GPS Status Badge            │
├─────────────────────────────────────┤
│                                     │
│    ┌───────────────────────────┐    │
│    │                           │    │
│    │   ⚠️  EMERGENCIA GENERAL  │    │  ← HERO (50-60%)
│    │      Necesito ayuda       │    │
│    │                           │    │
│    └───────────────────────────┘    │
│                                     │
│    ┌───────────┐  ┌───────────┐     │
│    │  ♥ MÉDICA │  │ 👁 SOSP.  │     │  ← Secondary Grid
│    └───────────┘  └───────────┘     │
│                                     │
└─────────────────────────────────────┘
```

**Implementation:**
1. **Hero Button (Emergencia General):**
   - ~50-60% del área visible
   - Forma pill expandida (border-radius: 2rem)
   - Icono 5-7rem con fondo circular oscuro
   - Gradiente premium naranja con glassmorphism
   - Breathing animation sutil

2. **Secondary Buttons Grid:**
   - Grid horizontal 1fr 1fr
   - Texto reducido: "MÉDICA" / "SOSPECHOSA"
   - Iconos protagónicos
   - Diferenciación clara de colores

3. **UX Enhancements:**
   - Ripple effect al tap
   - Haptic feedback diferenciado (Hero: [50,30,50], Secondary: 30)
   - Scale feedback al presionar
   - Animaciones de breathing/pulse

**Files Modified:**
- `/app/frontend/src/styles/emergency-buttons.css` - Complete rewrite
- `/app/frontend/src/pages/ResidentUI.js` - New HeroEmergencyButton & SecondaryEmergencyButton components

**Rollback:**
- Backup: `/app/frontend/src/styles/emergency-buttons-v1-legacy.css`

**Testing Results:**
- ✅ Tap inmediato (sin delay)
- ✅ 3 acciones funcionan correctamente
- ✅ Mobile y desktop responsive
- ✅ No afecta otros módulos

---

### Session 52 - THEME UPDATE: Purple → Blue/Teal (February 1, 2026) ⭐⭐⭐⭐⭐

**Objective:**
Actualizar la paleta de colores de la aplicación basándose en el logo GENTURIX:
- Reemplazar el morado por azul/teal (#4A90A4 primary)
- Mantener dark mode intacto
- Preservar colores semánticos (rojo, verde, amarillo)
- Permitir rollback fácil

**Implementation:**

**1. Theme System Centralizado:**
```css
/* /app/frontend/src/styles/theme.css */
:root {
    --primary: 193 45% 47%;           /* #4A90A4 - Main brand color */
    --primary-foreground: 210 40% 98%;
    --secondary: 193 52% 68%;          /* #80CBDC - Lighter accent */
    --ring: 193 45% 47%;
}
/* Paleta V1 (purple) comentada para rollback */
```

**2. Components Updated:**
- `GenturixLogo.jsx` - SVG gradient actualizado
- `ProfilePage.js`, `SecurityModule.js`, `GuardUI.js`, etc. - `purple-xxx` → `cyan-xxx`
- `PanelSelectionPage.js`, `UserManagementPage.js` - Role colors
- Total: ~30 archivos actualizados

**3. Rollback Instructions:**
```css
/* En /app/frontend/src/styles/theme.css:
   1. Comentar bloque V2 (azul/teal)
   2. Descomentar bloque V1 (purple)
*/
```

**4. Colors Changed:**
- Primary/Accent: `#7C3AED` (purple) → `#4A90A4` (teal)
- Icon accents: `purple-400/500` → `cyan-400/500`
- Badges/Tags: Updated to cyan family

**5. Colors Preserved (No Changes):**
- ❌ Destructive/Error: Red
- ✅ Success: Green
- ⚠️ Warning: Yellow/Orange
- 🔵 Info: Blue
- Background/Foreground: Dark theme colors

**Files Created/Modified:**
- `/app/frontend/src/styles/theme.css` (NEW - centralized theme)
- `/app/frontend/src/components/GenturixLogo.jsx` (Updated gradient)
- Multiple `.js` and `.jsx` files with hardcoded purple colors

---

### Session 52 - P0 BUG FIX: Registro Manual Admin No Persistía (February 1, 2026) ⭐⭐⭐⭐⭐

**Problem:**
El formulario de "Registro Manual de Accesos" existía en la UI del Administrador pero NO persistía el registro al enviarlo:
- ❌ No se creaba ningún access_log real en backend
- ❌ No había feedback claro (éxito o error)
- ❌ El registro no aparecía inmediatamente en la lista
- ✅ El flujo funcionaba desde el rol Guardia

**Root Cause:**
- Backend no guardaba `condominium_id` → rompía multi-tenant
- Backend no identificaba la fuente (`source`) del registro
- Frontend no mostraba toast de confirmación
- Frontend no refrescaba la lista después de crear

**Solution Implemented:**

**1. Backend - POST /api/security/access-log:**
```python
# Ahora guarda campos adicionales críticos:
access_log = {
    "condominium_id": current_user.get("condominium_id"),  # Multi-tenant
    "source": "manual_admin" | "manual_supervisor" | "manual_guard",  # Auditoría
    "status": "inside" | "outside",  # Estado del acceso
    "recorded_by_name": current_user.get("full_name")  # Quien registró
}

# Audit log mejorado:
{
    "action": "manual_access_created",
    "performed_by_role": "ADMIN",
    "condominium_id": "..."
}
```

**2. Frontend - SecurityModule.js:**
```javascript
// handleCreateAccessLog ahora:
- Muestra toast.success('✅ Registro creado correctamente')
- Muestra toast.error() en caso de fallo
- Llama fetchData() para refrescar lista inmediatamente
- Estado de loading con spinner
```

**Testing Agent Verification:**
- Backend: 100% (12/12 tests)
- Frontend: 100% (Admin flow verified via Playwright)
- Multi-tenant: ✅ Guard ve registros de Admin en mismo condo
- Auditoría: ✅ audit_logs con action='manual_access_created'
- **Test Report:** `/app/test_reports/iteration_51.json`

---

### Session 51 - RESERVATIONS SYSTEM EXTENDED (February 1, 2026) ⭐⭐⭐⭐⭐

**Feature: Extensión del Sistema de Reservas por Tipo de Área**

Implementación incremental del sistema de reservas con lógica por tipo de área, sin romper flujos existentes.

**Fases Implementadas:**

**FASE 1 - Modelo de Datos (Backend):**
```python
# Nuevos campos en AreaCreate/AreaUpdate (backward compatible)
reservation_behavior: "exclusive" | "capacity" | "slot_based" | "free_access"
max_capacity_per_slot: int | null
max_reservations_per_user_per_day: int | null
```

**FASE 2 - Lógica por Tipo de Área:**
- **EXCLUSIVE** (default): 1 reserva bloquea área (Rancho, Salón)
- **CAPACITY**: Múltiples reservas hasta max_capacity (Gimnasio, Piscina)
- **SLOT_BASED**: Slots fijos, 1 reserva = 1 slot (Canchas)
- **FREE_ACCESS**: No permite reservas, acceso libre

**FASE 3 - Backend:**
- `GET /api/reservations/smart-availability/{area_id}?date=YYYY-MM-DD`
- Retorna slots con `remaining_slots`, `total_capacity`, `status`
- Validación de capacidad para tipo CAPACITY
- Validación de límite por usuario

**FASE 4 - Frontend:**
- Slots clickeables con colores: verde (disponible), amarillo (pocos cupos), rojo (lleno)
- Badge de tipo de área: Exclusivo, Por cupo, Por turno, Acceso libre
- Muestra cupos restantes para áreas tipo CAPACITY
- FREE_ACCESS: Oculta botón "Reservar"

**Archivos Modificados:**
- `/app/backend/server.py` - Nuevos campos y endpoint smart-availability
- `/app/frontend/src/services/api.js` - Método getSmartAvailability
- `/app/frontend/src/components/ResidentReservations.jsx` - UI actualizada

**Testing:** PENDIENTE USER VERIFICATION

---

### Session 51 - Campanita Residente IMPLEMENTADA

**Implementación completa del sistema de notificaciones para residentes:**
- Badge dinámico con conteo de no leídas
- Dropdown con lista real de notificaciones
- Marca automáticamente como leídas después de 2 segundos
- Sincronización con backend cada 30 segundos
- Endpoint: `GET /api/resident/visitor-notifications/unread-count`

---

### Session 50 - P0 BUG FIX: Sonido de Alerta Continúa (February 1, 2026) ⭐⭐⭐⭐⭐

**Problem:**
El sonido de alerta de emergencia continúa reproduciéndose incluso después de que el guardia abre/atiende la alerta. Esto genera:
- Estrés innecesario
- Mala UX
- Confusión (parece que la alerta sigue activa)

**Root Cause:**
- No había control centralizado del audio
- Múltiples instancias de audio podían reproducirse simultáneamente
- No se llamaba a stop() en todos los puntos de interacción

**Solution Implemented:**

**1. AlertSoundManager (Singleton)**
```javascript
// /app/frontend/src/utils/AlertSoundManager.js
AlertSoundManager.play()   // Inicia sonido en loop
AlertSoundManager.stop()   // Detiene inmediatamente
AlertSoundManager.reset()  // Stop + reset state
AlertSoundManager.getIsPlaying() // Estado actual
```

**2. Integración en GuardUI.js:**
- `handleOpenAlert()` - Detiene sonido al abrir alerta desde lista
- `handleResolve()` - Detiene sonido al marcar alerta como atendida
- `handleTabChange()` - Detiene sonido al cambiar a pestaña Alertas
- `useEffect cleanup` - Detiene sonido al desmontar componente
- URL param handler - Detiene sonido al navegar via `?alert=id`

**3. Integración en Header.js:**
- `handleDropdownOpenChange()` - Detiene sonido al abrir campanita

**4. Service Worker:**
- `notificationclick` - Envía `STOP_PANIC_SOUND` a todos los clientes

**5. App.js:**
- Listener para `STOP_PANIC_SOUND` message
- Auto-stop safety net (30 segundos max)

**Testing Agent Verification:**
- Frontend: 100% success rate
- Todos los puntos de integración verificados
- **Test Report:** `/app/test_reports/iteration_50.json`

---

### Session 49 - P0 BUG FIX: RRHH Empleado Duplicado (February 1, 2026) ⭐⭐⭐⭐⭐

**Problem:** Empleado duplicado en Evaluaciones que no permitía ser evaluado

**Root Cause:**
- 8 guardias sin `user_id` (registros huérfanos)
- 6 evaluaciones huérfanas (employee_id inexistente)

**Solution Implemented:**

**1. HR Data Integrity Validation Endpoints:**
```
GET  /api/hr/validate-integrity     # Detect issues
POST /api/hr/cleanup-invalid-guards # Clean up (SuperAdmin only, dry_run support)
GET  /api/hr/evaluable-employees    # Only valid employees
```

**2. Enhanced GET /api/hr/guards:**
- Default filters: `user_id != null`, `is_active = true`
- Enriches with `_is_evaluable` and `_validation_status`
- Optional `include_invalid=true` to see all records

**3. Frontend EmployeeEvaluationCard:**
- Shows "No evaluable" badge for invalid employees
- Hides "Evaluar" button for non-evaluable employees
- Visual differentiation (red border) for invalid records

**Data Cleanup Performed:**
- 8 guards deactivated (`is_active=false`, `deactivation_reason="no_user_id"`)
- Preserves historical data (no deletions)

**Testing Agent Verification:**
- Backend: 100% (16/16 tests)
- Frontend: 100% (all UI tests)
- **Test Report:** `/app/test_reports/iteration_49.json`

---

### Session 48 - P0/P1 Bug Fixes VERIFIED (February 1, 2026) ⭐⭐⭐⭐⭐

#### 🔴 P0 FIX: Admin "Registro de Accesos" Empty
**Problem:** Módulo de Seguridad no mostraba información

**Solution:**
- Unified endpoint `/api/security/access-logs` combining:
  - `access_logs` collection (manual entries)
  - `visitor_entries` collection (guard check-ins)
- Enhanced UI with entry type badges (Temporal, Extendido, Recurrente, Permanente)
- Added authorization info (resident name, vehicle plate, guard name)

#### 🔴 P0 FIX: Admin "Actividad Reciente" Empty
**Problem:** Dashboard no mostraba actividad

**Solution:**
- Enhanced endpoint `/api/dashboard/recent-activity` combining:
  - `audit_logs` (logins, user actions)
  - `visitor_entries` (check-ins)
  - `panic_events` (alerts)
  - `reservations` (bookings)
- ActivityItem component shows different icons and colors per event type
- Relative timestamps (Ahora, 1m, 5h, etc.)

#### 🟠 P1 FIX: Residente Pre-registros State
**Problem:** Pre-registros no reflejaban estado después de check-in

**Solution:**
- Enhanced `/api/authorizations/my` with:
  - `status: "used"` / `"pending"`
  - `was_used: boolean`
  - `used_at: timestamp`
  - `used_by_guard: string`
- Frontend separates authorizations into 3 sections:
  - **Pendientes**: Active, not used
  - **Utilizadas**: Check-in completed (blue badge "✓ Ingresó")
  - **Expiradas**: Inactive, not used

**Testing Agent Verification:**
- Backend: 100% (16/16 tests)
- Frontend: 100% (all UI tests)
- **Test Report:** `/app/test_reports/iteration_48.json`

---

### Session 47 - P0 BUG FIX: Campanita de Notificaciones Estática (February 1, 2026) ⭐⭐⭐⭐⭐

**Problem:**
El badge de la campanita siempre mostraba el mismo número y no se actualizaba al:
- Abrir las notificaciones
- Marcarlas como leídas
- Cambiar de vista o refrescar

**Solution Implemented:**

**1. Backend - New Notification Endpoints (server.py):**
```python
GET  /api/notifications           # Lista notificaciones con campo 'read'
GET  /api/notifications/unread-count  # Contador exacto de no leídas
PUT  /api/notifications/{id}/read     # Marcar individual como leída
PUT  /api/notifications/mark-all-read # Marcar todas como leídas
```

**2. Frontend - Dynamic Header.js:**
- `unreadCount` state actualizado por polling cada 30 segundos
- Badge dinámico: `{unreadCount > 0 && <span>{unreadCount}</span>}`
- Auto-mark-as-read después de 2 segundos de visualizar dropdown
- Botones de refresh y mark-all-read en dropdown
- Toast notifications para feedback de acciones

**3. Database Schema:**
- Colección `guard_notifications` con campo `read: boolean`
- `read_at: ISO timestamp` cuando se marca como leída

**Testing Agent Verification:**
- Backend: 92% (12/13 tests)
- Frontend: 100% (all UI tests)
- ✅ Badge desaparece cuando count=0
- ✅ Auto-mark-as-read funciona
- ✅ Estado persiste después de refrescar página

**Files Modified:**
- `/app/backend/server.py` - Nuevos endpoints (líneas 3076-3212)
- `/app/frontend/src/components/layout/Header.js` - Componente rediseñado
- `/app/frontend/src/services/api.js` - Nuevos métodos API

**Test Report:** `/app/test_reports/iteration_47.json`

---

### Session 46 - Latest Updates (February 1, 2026)

#### ⭐ NEW: UX Reservaciones - Slots de Tiempo Clickeables

**Implementación:**
- Grid visual de slots de hora con estados: Disponible (verde), Ocupado (rojo), Seleccionado (púrpura)
- Clic en slot disponible auto-llena los campos "Hora Inicio" y "Hora Fin"
- Toast de confirmación mostrando el rango seleccionado
- Badges "Auto-llenado" en los campos de tiempo
- Leyenda actualizada con indicador de "Seleccionado"
- Texto animado "← Clic para seleccionar" como guía UX

**Archivos modificados:**
- `/app/frontend/src/components/ResidentReservations.jsx`

#### 🔧 FIX: Error "Mi Turno" (TypeError: datetime)

**Problema:**
- Error 500 "Internal Server Error" al cargar pestaña "Mi Turno"
- Causa: `TypeError: can't subtract offset-naive and offset-aware datetimes`

**Solución:**
- Se corrigió el parsing de fechas para asegurar que siempre sean timezone-aware
- Se agregó lógica para manejar diferentes formatos de ISO timestamps

**Archivos modificados:**
- `/app/backend/server.py` (líneas 3195-3228, 3843-3858)

#### ⭐ NEW: Historial Visual de Check-ins para Guardias

**Componente:** `GuardHistoryVisual.jsx`
- Dashboard visual con análisis de actividad
- Tarjetas de estadísticas: Entradas, Salidas, Hora Pico, Total
- Gráfico de barras de actividad por hora (24h)
- Filtros: Hoy, Últimos 7 días, Últimos 30 días
- Hora actual resaltada en verde

#### 🔴 P0 BUG FIXED: Check-In Duplicados (VERIFIED)

- Triple verificación en backend para prevenir re-uso
- Protección anti-doble-clic en frontend
- Botón muestra "YA PROCESADO" cuando está bloqueado
- Testing agent: 100% tests pasados

---

### Session 41 - P0 CRITICAL FIX: Reservations Module (February 1, 2026) ⭐⭐⭐⭐⭐

#### 🔴 P0 BUG FIXED: Residents Cannot Make Reservations

**Problem:** 
- Residents couldn't reserve any common area
- Always showed "No hay disponibilidad para esta fecha"
- "Crear Reservación" button was permanently disabled

**Root Cause:**
The backend `/reservations/availability/{area_id}` endpoint was missing the `is_available` field that the frontend was checking. The frontend was checking `availability.is_available` but the backend only returned:
- `is_day_allowed`
- `slots_remaining`
- `occupied_slots`

**Solution Implemented:**

**1. Backend - Complete availability response:**
```python
return {
    "is_available": is_day_allowed and slots_remaining > 0,  # NEW
    "is_day_allowed": is_day_allowed,
    "day_name": day_name,
    "slots_remaining": slots_remaining,
    "time_slots": [...],  # NEW - visual availability
    "message": None if is_available else "Fecha no disponible..."  # NEW
}
```

**2. Backend - Generate time slots for visual display:**
- Generates hourly slots from `available_from` to `available_until`
- Marks each slot as "available" or "occupied" based on existing reservations

**3. Frontend - Visual availability module:**
- Shows green/red indicators for each time slot
- Clear message about why date is unavailable
- Legend: "Disponible" / "Ocupado"

**Files Modified:**
- `/app/backend/server.py` - Enhanced availability endpoint
- `/app/frontend/src/components/ResidentReservations.jsx` - Visual availability

**Verification Results:**
- ✅ `is_available: True` for valid dates with slots
- ✅ `is_available: False` for past dates (with message)
- ✅ Time slots correctly show occupied/available
- ✅ Reservations created successfully
- ✅ "Crear Reservación" button enabled when available

---

### Earlier Fix: Resend Email Integration

#### ✅ EMAIL INTEGRATION ACTIVATED

**Provider:** Resend
**Mode:** DEMO (testing)
**Sender:** onboarding@resend.dev

**Email Flows Implemented:**

1. **User Creation with Credentials**
   - When admin creates a user with `send_credentials_email: true`
   - Email contains: full name, email, temporary password, login link
   - User is flagged for `password_reset_required`

2. **Password Reset by Admin** (NEW)
   - Endpoint: `POST /admin/users/{user_id}/reset-password`
   - Generates new temporary password
   - Sends email with new password
   - Flags user for password reset on next login

**Environment Variables:**
```
RESEND_API_KEY=re_MHqNnsKg_... (configured)
SENDER_EMAIL=onboarding@resend.dev
```

**Email Toggle:**
- Email sending can be enabled/disabled via Super Admin
- `POST /config/email-status` with `{"email_enabled": true/false}`
- When disabled: credentials shown in response, no email sent

**Verification Results:**
- ✅ User creation → Email sent successfully
- ✅ Password reset → Email sent successfully
- ✅ API key not exposed in logs
- ✅ Graceful fallback when email disabled

---

### Earlier P0 Fix: Check-In Duplicate Prevention

#### 🔴 P0 BUG FIXED: Preregistros se reutilizan infinitamente

**Problem:** Pre-registrations could be used infinite times:
1. Guard clicks "Registrar Entrada"
2. Entry is registered
3. Pre-registration stays visible and clickable
4. Multiple duplicate entries can be created

**Root Cause:**
1. Backend `authorization_marked_used` response only checked for `temporary`, not `extended`
2. Frontend only removed item from list if `authorization_marked_used` was true
3. Backend didn't verify against `visitor_entries` collection before allowing check-in

**Complete Solution:**

**1. Backend - Triple verification before check-in:**
```python
# Check 1: Status is "used"
if auth_status == "used": raise 409

# Check 2: checked_in_at is set  
if authorization.get("checked_in_at"): raise 409

# Check 3: Entry exists in visitor_entries
if await db.visitor_entries.find_one({"authorization_id": auth_id}): raise 409
```

**2. Backend - Response includes extended:**
```python
"authorization_marked_used": auth_type in ["temporary", "extended"]
```

**3. Frontend - Always remove after success:**
```javascript
// ALWAYS remove after successful check-in, don't depend on flag
if (payload.authorization_id) {
    setTodayPreregistrations(prev => prev.filter(a => a.id !== payload.authorization_id));
}
```

**4. Frontend - Processing state prevents double-click:**
```javascript
const [processingAuthId, setProcessingAuthId] = useState(null);
// Button shows "PROCESANDO..." and is disabled during check-in
```

**Files Modified:**
- `/app/backend/server.py` - Triple verification, response fix
- `/app/frontend/src/components/VisitorCheckInGuard.jsx` - Always remove, disable button

**Verification Results:**
- ✅ First check-in: Success
- ✅ Second check-in: HTTP 409 "Esta autorización ya fue utilizada"
- ✅ Item disappears from list immediately
- ✅ Button disabled during processing
- ✅ PERMANENT authorizations can still be reused (correct behavior)

---

### Earlier P0 Fix: Guard Double Profile View

#### 🔴 P0 BUG FIXED: Doble Interfaz de Perfil sin Retorno (COMPLETE FIX)

**Problem:** Guard role had TWO different profile views:
1. ✅ Integrated profile via bottom "Perfil" tab (correct)
2. ❌ Isolated profile via top avatar → `/profile` route (incorrect - no navigation, trapped user)

**Root Cause:**
1. Avatar click handlers in `GuardUI.js` navigated to `/profile`
2. The `/profile` route in `App.js` was available to ALL authenticated users
3. Guards could access ProfilePage which has DashboardLayout (wrong layout for guards)

**Complete Solution:**

**1. GuardUI.js - Click handlers fixed (earlier)**
- Avatar and profile button now use `setActiveTab('profile')` instead of `navigate('/profile')`

**2. App.js - Route-level protection (NEW)**
- Created `ProfilePageOrRedirect` component
- If user role is ONLY "Guarda", redirects to `/guard?tab=profile`
- Other roles continue to use normal ProfilePage

**3. GuardUI.js - URL parameter handling (NEW)**
- Added support for `?tab=profile` URL parameter
- When redirected from `/profile`, automatically opens the Profile tab

**Files Modified:**
- `/app/frontend/src/App.js` - Added ProfilePageOrRedirect component
- `/app/frontend/src/pages/GuardUI.js` - Added tab URL parameter handling

**Verification Results:**
- ✅ Avatar click stays on `/guard` (embedded profile)
- ✅ Direct navigation to `/profile` redirects to `/guard?tab=profile`
- ✅ Profile tab shows EmbeddedProfile with "Volver al Panel" button
- ✅ Bottom navigation always visible
- ✅ Works on desktop AND mobile
- ✅ Guard can NEVER get trapped in an isolated view

---

### Earlier Fixes in this Session:

**Problem:** The History tab showed 0 events even though there were check-ins and alerts.

**Root Cause:**
- `/guard/history` endpoint queried `guard_history` collection but check-ins were in `visitor_entries`
- Filter was too restrictive (`entry_by = current_user.id`) - guards couldn't see entries from other guards

**Solution Implemented:**
1. Modified `/guard/history` endpoint to aggregate from multiple sources:
   - `visitor_entries` → visit_entry, visit_exit events
   - `panic_events` (status=resolved) → alert_resolved events
   - `hr_clock_logs` → clock_in, clock_out events
   - `shifts` (status=completed) → shift_completed events
2. Removed overly restrictive filtering - guards now see ALL condominium activity
3. Updated frontend HistoryTab to display new event types with proper icons/colors

**Files Modified:**
- `/app/backend/server.py` (lines 3096-3195)
- `/app/frontend/src/pages/GuardUI.js` (HistoryTab component)

#### 🔴 P0 BUG #3 FIXED: Pre-registros EXTENDED no desaparecen después de check-in

**Problem:** After checking in a visitor with an EXTENDED authorization, the pre-registration remained visible in "PRE-REGISTROS PENDIENTES".

**Root Cause:**
Only TEMPORARY authorizations were being marked as `status: "used"` after check-in. EXTENDED authorizations kept `status: "pending"`.

**Solution Implemented:**
1. Modified check-in logic to mark EXTENDED authorizations as "used" after check-in
2. Updated reuse blocking to include EXTENDED authorizations
3. PERMANENT and RECURRING authorizations still allow multiple uses (as intended)

**Code Change:**
```python
# Before: only temporary was marked
if auth_type_value == "temporary":
    update_data["$set"]["status"] = "used"

# After: temporary AND extended are marked
if auth_type_value in ["temporary", "extended"]:
    update_data["$set"]["status"] = "used"
```

**Files Modified:**
- `/app/backend/server.py` (lines 2528-2538, 2598-2602)

**Verification Results:**
- ✅ Avatar click stays on `/guard` (desktop + mobile)
- ✅ Profile button stays on `/guard`
- ✅ "Volver al Panel" button visible and functional
- ✅ History now shows 22+ events (visitor entries)
- ✅ EXTENDED authorization marked as "used" after check-in
- ✅ Authorization removed from pending list after check-in

---

### Session 40 - P0 BUG FIX: Guard Check-In Duplicates (February 1, 2026) ⭐⭐⭐⭐⭐

#### 🔴 P0 BUG FIXED: Pre-registros Duplicados en Guard Check-In

**Problem:** Pre-registration remained visible after check-in, allowing infinite reuse of the same authorization.

**Root Cause:**
- Authorizations had no `status` field to track usage
- `/guard/authorizations` returned all active auths without filtering used ones
- Check-in endpoint didn't block reuse

**Solution Implemented:**

1. **Authorization Status Tracking:**
   - Added `status` field: "pending" → "used"
   - Added `checked_in_at`, `checked_in_by`, `checked_in_by_name` fields

2. **Backend Enforcement:**
   - `GET /guard/authorizations` filters `status="pending"` by default
   - `POST /guard/checkin` returns HTTP 409 if auth already used
   - Only TEMPORARY authorizations are marked as "used"
   - PERMANENT authorizations can be used multiple times

3. **New Endpoint:**
   - `GET /guard/entries-today` - Returns today's check-ins

4. **Frontend Updates:**
   - `handleCheckInSubmit` removes auth from list immediately
   - Handles 409 error with toast and removes auth from list
   - New "INGRESADOS HOY" collapsible section

**Verification Results:**
- ✅ Backend: 100% (13/13 tests passed)
- ✅ Frontend: 100% (all UI tests passed)
- ✅ Second check-in blocked with 409
- ✅ Auth removed from list after check-in

**Test Report:** `/app/test_reports/iteration_45.json`

---

### Session 34 - CRITICAL MOBILE FREEZE BUG FIX (January 31, 2026) ⭐⭐⭐⭐⭐

#### 🔴 ROOT CAUSE IDENTIFIED & FIXED
**Problem:** Mobile screens were freezing - inputs not accepting typing, selects not opening, buttons unresponsive.

**Root Cause:** z-index conflict between Dialog components (z-[70]) and Select/Popover/Dropdown components (z-50). When a Select was inside a Dialog, its dropdown rendered BEHIND the dialog, making it invisible and unclickable.

**Solution Applied:**
1. Changed z-index from `z-50` to `z-[100]` for all floating UI components:
   - SelectContent
   - PopoverContent
   - DropdownMenuContent
   - DropdownMenuSubContent
   - TooltipContent

2. Added CSS rules in `mobile.css` to ensure pointer-events work:
   - `pointer-events: auto` on all dialog children
   - `touch-action: auto` on inputs and interactive elements
   - Disabled pointer-events on non-interactive elements (labels, divs) in dialogs

**Files Modified:**
- `/app/frontend/src/components/ui/select.jsx` - z-[100], touch-action, pointer-events
- `/app/frontend/src/components/ui/popover.jsx` - z-[100]
- `/app/frontend/src/components/ui/dropdown-menu.jsx` - z-[100]
- `/app/frontend/src/components/ui/tooltip.jsx` - z-[100]
- `/app/frontend/src/styles/mobile.css` - pointer-events rules for dialogs

#### ✅ ADMIN/SUPERVISOR MOBILE LOGOUT FIX
**Problem:** Admin and Supervisor users could not logout on mobile because the ProfilePage component lacked a logout button (it was only in the header dropdown, hidden on mobile).

**Solution:** Added a "Cerrar Sesión" button at the bottom of ProfilePage, visible only on mobile (lg:hidden), with a confirmation dialog.

**File Modified:** `/app/frontend/src/pages/ProfilePage.js`

---

### Testing Results (Session 34)
```
Frontend Tests: 92% (11/12 passed)
z-index Verification: ✅ All components verified
Mobile Form Freeze: ✅ FIXED
Select Dropdowns: ✅ Visible above dialogs
Panic Alert Flow: ✅ Working
Logout (All Roles): ✅ Working
```

---

### Session 33 - FINAL PRE-DEPLOYMENT HARDENING (January 31, 2026) ⭐⭐⭐⭐⭐

#### ✅ EMAIL NORMALIZATION (CRITICAL - FIXED)
All email handling is now case-insensitive (industry standard):
- `juan@gmail.com`, `Juan@gmail.com`, `JUAN@gmail.com` all work identically
- Backend normalizes with `email.lower().strip()` on:
  - Login endpoint
  - User creation (Admin)
  - Onboarding wizard (Super Admin)
  - Validation endpoint

**Files Modified:** `/app/backend/server.py`

#### ✅ SUPER ADMIN FIXES
- Module toggle working (HR, School, Reservations, etc.)
- Refresh button functional
- API: `PATCH /api/condominiums/{id}/modules/{module}?enabled=true|false`

#### ✅ HR MODULE FIXES
- **Shift deletion added** with confirmation dialog
- ShiftCard now has delete button (trash icon)
- TurnosSubmodule handles `onDeleteShift` callback
- API: `DELETE /api/hr/shifts/{id}`

**Files Modified:** `/app/frontend/src/pages/RRHHModule.js`

#### ✅ MOBILE LOGOUT (ALL ROLES)
- Logout button added to EmbeddedProfile component
- Confirmation dialog before logout
- Available in Guard, Resident, HR profiles

**Files Modified:** `/app/frontend/src/components/EmbeddedProfile.jsx`

#### ✅ MOBILE UX IMPROVEMENTS
- Panic buttons: horizontal layout, reduced height (90px mobile)
- All 3 buttons visible on small screens (iPhone SE)
- Forms not freezing on mobile

---

### Testing Summary (Session 33)
```
Backend: 92% (12 passed, 1 conflict, 1 skipped)
Frontend: 100%
Features Verified: 8/8 ✅
```

---

### Session 32 - P1 UX & CONSISTENCY (January 31, 2026) ⭐⭐⭐⭐

#### 1. ✅ PROFILE IMAGE CONSISTENCY (VERIFIED)
- Profile photos sync correctly across:
  - Sidebar (collapsed and expanded)
  - Topbar
  - Profile edit view
  - EmbeddedProfile component
- `refreshUser()` called after photo updates
- Works for Admin, HR, Guard, Resident

#### 2. ✅ PROFILE NAVIGATION (IMPROVED)
**File Modified:** `/app/frontend/src/pages/ProfilePage.js`
- Added "Volver al Dashboard" button (always visible)
- Smart routing: returns to correct dashboard based on role:
  - SuperAdmin → /super-admin
  - Admin → /admin/dashboard
  - Guard → /guard
  - Resident → /resident
  - HR/Supervisor → /hr
  - Student → /student

#### 3. ✅ RESIDENT PANIC BUTTON MOBILE UX (IMPROVED)
**File Modified:** `/app/frontend/src/pages/ResidentUI.js`
- Buttons repositioned higher on screen
- Reduced height: 90px mobile, 110px tablet, 130px desktop
- Horizontal layout: icon left, text right
- GPS status now sticky at top
- All buttons fully visible on small screens (iPhone SE tested)
- Reduced gaps and padding

#### 4. ✅ CREDENTIALS TEST MODE (ALREADY IMPLEMENTED)
**Files:** `/app/backend/.env`, `/app/backend/server.py`
- `DEV_MODE=true` bypasses email-based password reset
- When DEV_MODE or email toggle disabled:
  - No forced password reset on first login
  - Password shown in UI after user creation
- Works without RESEND_API_KEY

---

### Session 31 - P0 CORE FUNCTIONAL FIXES (January 31, 2026) ⭐⭐⭐⭐⭐

#### 1. ✅ RESIDENT RESERVATIONS UI (COMPLETE)
**New Component:** `/app/frontend/src/components/ResidentReservations.jsx`
- View available common areas (Piscina, Salón, etc.)
- Check real-time availability
- Create reservations with date/time selection
- Cancel pending reservations
- See status: pending/approved/rejected
- Integrated into ResidentUI as new "Reservas" tab

**Files Modified:**
- `/app/frontend/src/pages/ResidentUI.js` - Added Reservas tab
- `/app/frontend/src/services/api.js` - Added `getReservationAvailability`, `updateReservation`
- `/app/backend/server.py` - SuperAdmin can now create areas for any condo

#### 2. ✅ ADMIN RESERVATION APPROVAL (VERIFIED)
- Approve/Reject buttons already existed in ReservationsModule
- Working correctly for Admin role

#### 3. ⏳ GUARD VISITOR AUTHORIZATIONS (EXISTING)
- VisitorCheckInGuard component already handles:
  - Temporary authorizations
  - Recurring authorizations
  - Permanent authorizations
  - Quick check-in/check-out

#### 4. ✅ GUARD NAVIGATION FIX (VERIFIED)
- ProfilePage.js already has back button (navigate(-1))
- EmbeddedProfile works in tab context

#### 5. ✅ PUSH NOTIFICATION SOUND (IMPLEMENTED)
**Files Modified:**
- `/app/frontend/public/service-worker.js` - Sends PLAY_PANIC_SOUND message
- `/app/frontend/src/App.js` - Web Audio API panic sound generator
  - Plays alert tone on panic notification
  - Repeats every 2 seconds until acknowledged
  - Auto-stops after 30 seconds
  - `window.stopPanicSound()` available globally

#### 6. ✅ MAP UX IMPROVEMENTS
**File Modified:** `/app/frontend/src/pages/GuardUI.js`
- Reduced map height on mobile: 150px (was 200px)
- Stacked buttons on mobile
- Truncated coordinates display
- No horizontal scroll

#### 7. ✅ SUPER ADMIN FIXES (VERIFIED)
- Create Condominium: Working via onboarding wizard
- Module Enable/Disable: API endpoint working correctly
- Refresh button: Connected to fetchData, working

---

### Session 30 - CRITICAL P0 MOBILE FIX (January 31, 2026) ⭐⭐⭐⭐⭐

#### P0 BUG FIXED: Mobile Form Freeze
**Root Cause:** CSS rules in `mobile.css` were globally overriding Radix Dialog positioning with `!important`, causing z-index conflicts and blocking touch events.

**Changes Made:**
1. **`/app/frontend/src/styles/mobile.css`**:
   - Removed aggressive global dialog overrides
   - Fixed `overflow-x: hidden` to not affect modal children
   - Added `touch-action: auto` and `user-select: text` for form inputs in dialogs

2. **`/app/frontend/src/components/ui/dialog.jsx`**:
   - Updated z-index hierarchy: Overlay z-60, Content z-70, Close button z-80
   - Changed mobile breakpoint from `max-sm` (≤640px) to `max-lg` (≤1023px)
   - Added `touchAction: auto` inline style for proper mobile touch handling
   - Added padding bottom for BottomNav clearance

3. **`/app/frontend/src/components/ui/sheet.jsx`**:
   - Updated z-index to match dialog hierarchy (z-60/z-70)
   - Added `overflow-y: auto` to side variants
   - Added touch action styles for mobile

4. **`/app/frontend/src/components/layout/BottomNav.js`**:
   - Clarified z-index (50) to stay below dialogs (60+)
   - Added `pointer-events: auto` for explicit touch handling

#### VERIFIED WORKING ON MOBILE:
- ✅ Login form
- ✅ Onboarding wizard (country/timezone selection)
- ✅ Resident dashboard & visitor authorization modal
- ✅ All form inputs editable
- ✅ All buttons responsive
- ✅ BottomNav navigation
- ✅ Modal scroll
- ✅ Desktop unchanged

---

#### ALSO FIXED: Onboarding Wizard Errors
- Pre-validation endpoint for name/email availability
- Auto-timezone mapping on country selection
- 25+ countries with Central America support

#### WHAT WAS IMPLEMENTED
A development mode flag (`DEV_MODE=true`) that changes behavior for easier testing without compromising production security.

#### DEV_MODE BEHAVIOR (When `DEV_MODE=true`)
| Feature | DEV_MODE=true | DEV_MODE=false (Production) |
|---------|---------------|----------------------------|
| Password Reset on First Login | ❌ Disabled | ✅ Required |
| Show Generated Password in API | ✅ Visible | ❌ Masked (********) |
| Show Password in UI | ✅ With DEV MODE badge | ❌ Hidden |
| Email Delivery Blocking | ❌ No blocking | ✅ Required |

#### FILES MODIFIED
- `/app/backend/.env` - Added `DEV_MODE=true`
- `/app/backend/server.py`:
  - Added DEV_MODE config variable
  - Added `/config/dev-mode` endpoint
  - Modified user creation to skip `password_reset_required` in DEV_MODE
  - Modified API response to include password when DEV_MODE=true
  - Modified onboarding wizard to use DEV_MODE
- `/app/frontend/src/services/api.js` - Added `getDevModeStatus` method
- `/app/frontend/src/pages/UserManagementPage.js`:
  - Updated CredentialsDialog to show DEV MODE badge
  - Updated to display password from API response

#### API ENDPOINT
```
GET /api/config/dev-mode
Response: {
  "dev_mode": true,
  "features": {
    "skip_password_reset": true,
    "show_generated_passwords": true,
    "skip_email_validation": true
  }
}
```

#### HOW TO USE IN PRODUCTION
1. Set `DEV_MODE=false` in `/app/backend/.env`
2. Restart backend service
3. All security features will be enforced

---

### Session 28 - FULL PLATFORM HARDENING (January 31, 2026) ⭐⭐⭐⭐⭐
**Pre-Production Stability & Regression Testing Complete**

#### HARDENING SUMMARY
| Category | Tests | Status |
|----------|-------|--------|
| Role Logins | 7/7 | ✅ All roles working |
| Backend CRUD | 33/33 | ✅ 100% Pass |
| Frontend Forms | 100% | ✅ All verified |
| Mobile Responsive | 100% | ✅ All viewports working |
| Security Fixes | 3 | ✅ Password exposure fixed |
| Lint Errors Fixed | 4 | ✅ All resolved |

#### SECURITY FIXES APPLIED
1. ✅ Fixed `hashed_password` exposure in `/admin/users` endpoint
2. ✅ Fixed `hashed_password` exposure in `/profile/{user_id}` endpoint  
3. ✅ Fixed `hashed_password` exposure in profile update response
4. ✅ Fixed `navigate` prop missing in SuperAdminDashboard CondominiumsTab

#### COMPONENTS VERIFIED WORKING
- **User Management**: Create, Update Status, Activate/Deactivate
- **Areas CRUD**: Create, Update, Delete (soft)
- **Reservations**: Create, Approve/Reject
- **Visitor Authorizations**: All 4 types, Guard Check-in/out
- **HR Module**: Absences, Evaluations, Clock in/out
- **Security**: Panic alerts, Resolution, History
- **Mobile Navigation**: Bottom nav on all roles
- **Desktop Navigation**: Sidebar on all modules

#### ROLES TESTED END-TO-END
- ✅ **SuperAdmin**: Dashboard, Condominiums, Users, Content, Onboarding Wizard
- ✅ **Admin**: Dashboard, Users, Security, HR, Reservations, Audit
- ✅ **HR**: Absences, Evaluations, Shifts, Recruitment, Directory
- ✅ **Guard**: Alerts, Check-in, Mi Turno, Visitors, Profile
- ✅ **Resident**: Panic, Authorizations, History, Directory, Profile
- ✅ **Student**: Courses, Subscription, Notifications, Profile

#### TEST REPORTS
- `/app/test_reports/iteration_35.json` - UI/Navigation Testing
- `/app/test_reports/iteration_36.json` - CRUD Forms Testing
- `/app/test_reports/iteration_37.json` - Mobile/Desktop Responsive Testing

---

### Session 27 - ADVANCED VISITOR AUTHORIZATION SYSTEM (January 31, 2026) ⭐⭐⭐⭐⭐ 
**100% Tests Passed (25/25 Backend + Frontend Complete)**

#### KEY ACCOMPLISHMENTS
1. **Authorization Types (Resident)**
   - ✅ TEMPORARY: Single date or date range (Yellow badge)
   - ✅ PERMANENT: Always allowed, e.g., family (Green badge)
   - ✅ RECURRING: Specific days of week (Blue badge)
   - ✅ EXTENDED: Date range + time windows (Purple badge)
   - ✅ MANUAL: Guard entry without authorization (Gray badge)
   - ✅ Fields: visitor_name, identification_number, vehicle_plate, valid_from, valid_to, allowed_days, allowed_hours, notes

2. **Resident Endpoints**
   - ✅ POST /api/authorizations - Create authorization
   - ✅ GET /api/authorizations/my - Get own authorizations
   - ✅ PATCH /api/authorizations/{id} - Update authorization
   - ✅ DELETE /api/authorizations/{id} - Soft delete (deactivate)
   - ✅ Auto-assign color_code based on authorization type

3. **Guard Fast Check-in/Check-out**
   - ✅ GET /api/guard/authorizations?search= - Search by name/ID/plate
   - ✅ POST /api/guard/checkin - Register visitor entry
   - ✅ POST /api/guard/checkout/{entry_id} - Register visitor exit
   - ✅ GET /api/guard/visitors-inside - List visitors currently inside
   - ✅ Authorization validation (date/day/time checks)
   - ✅ Entry timestamp and duration tracking

4. **Resident Notifications**
   - ✅ Notification on visitor arrival (check-in)
   - ✅ Notification on visitor exit (check-out)
   - ✅ GET /api/resident/visitor-notifications - Get notifications
   - ✅ PUT /api/resident/visitor-notifications/{id}/read - Mark as read
   - ✅ Unread count badge in UI

5. **Audit & History**
   - ✅ GET /api/authorizations/history - Full entry/exit log
   - ✅ GET /api/authorizations/stats - Authorization statistics
   - ✅ Filter by authorization, resident, visitor, date range

6. **Frontend - Resident UI**
   - ✅ New "Autorizaciones" tab in ResidentUI
   - ✅ VisitorAuthorizationsResident component
   - ✅ Color-coded authorization cards
   - ✅ Create/Edit form with type-specific fields
   - ✅ Notifications panel with bell icon
   - ✅ Active/Inactive sections

7. **Frontend - Guard UI**
   - ✅ New "Check-In" tab in GuardUI
   - ✅ VisitorCheckInGuard component
   - ✅ High-contrast search interface
   - ✅ One-tap REGISTRAR ENTRADA button
   - ✅ Visitors inside list with SALIDA button
   - ✅ Manual entry without authorization option
   - ✅ Entry time and duration display

8. **Test Report**: `/app/test_reports/iteration_34.json` - 100% pass rate

### Session 26 - RESERVATIONS & COMMON AREAS MODULE (January 31, 2026) ⭐⭐⭐⭐⭐ 
**100% Tests Passed (22/22 Backend + Frontend Complete)**

#### KEY ACCOMPLISHMENTS
1. **Common Areas Management (Admin)**
   - ✅ GET /api/reservations/areas - List areas
   - ✅ POST /api/reservations/areas - Create with all fields
   - ✅ PATCH /api/reservations/areas/{id} - Edit area
   - ✅ DELETE /api/reservations/areas/{id} - Soft delete
   - ✅ Fields: name, type, capacity, description, rules, hours, allowed_days, requires_approval, max_reservations_per_day

2. **Reservations (Resident)**
   - ✅ POST /api/reservations - Create reservation
   - ✅ GET /api/reservations/availability/{area_id}?date=YYYY-MM-DD - Check availability
   - ✅ Validation: Day restrictions, hour limits, capacity, max per day, overlap detection
   - ✅ Auto-approve or pending based on area settings

3. **Approval Flow (Admin)**
   - ✅ PATCH /api/reservations/{id} - Approve/reject
   - ✅ GET /api/reservations?status=pending - List pending
   - ✅ Admin notes on approval/rejection
   - ✅ Audit logging for all actions

4. **Guard View**
   - ✅ GET /api/reservations/today - Today's approved reservations
   - ✅ Read-only access

5. **Module Visibility**
   - ✅ Sidebar item hidden when module disabled
   - ✅ API returns 403 when module disabled
   - ✅ Module check handles both boolean and dict formats

6. **Frontend**
   - ✅ Tabs: Áreas, Mis Reservas, Pendientes (admin only)
   - ✅ Area form with day selector (L M X J V S D)
   - ✅ Reservation form with availability check
   - ✅ Mobile-first responsive design
   - ✅ Area cards with complete info
   - ✅ Reservation cards with status badges

7. **Test Report**: `/app/test_reports/iteration_33.json` - 100% pass rate

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
