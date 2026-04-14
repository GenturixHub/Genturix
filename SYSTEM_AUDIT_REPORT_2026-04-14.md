# GENTURIX - FULL SYSTEM AUDIT REPORT
**Date:** 2026-04-14  
**Auditor:** Senior Security Engineer / SaaS Systems Architect  
**System:** Genturix SaaS Condominium Management Platform  
**Scope:** Architecture, Security, Backend, Frontend, Performance, Data Integrity  

---

## EXECUTIVE SUMMARY

**System:** 20,400-line monolithic FastAPI backend + React 19 frontend  
**Endpoints:** 239 registered routes  
**Collections:** 20+ MongoDB collections  
**Modules:** Auth, Guard/Visits, Notifications V2, Casos, Documentos, Finanzas, Reports, HR, School, Billing, Onboarding  

**Overall Assessment:** The system is **functional and operational** but carries significant architectural debt and several security gaps that MUST be addressed before aggressive scaling. The incremental development approach has produced a working product but left inconsistencies across modules.

---

## 🔴 CRITICAL ISSUES

### C1. Synchronous HTTP Calls in Async Event Loop (THREAD STARVATION)
**Risk:** Server hang / complete request starvation under load  
**Location:** `server.py` lines 19458-19492 (`_init_doc_storage`, `_put_object`, `_get_object`)  
**Detail:** The Documentos module uses `http_requests.post()`, `http_requests.put()`, `http_requests.get()` (synchronous `requests` library) inside async endpoint handlers. These calls **block the entire event loop** during file upload/download operations. With 3+ concurrent document operations, the server becomes unresponsive for ALL users.  
**Fix:** Replace `requests` with `httpx.AsyncClient` or `aiohttp` and make all storage functions `async`.

### C2. 40+ Write Endpoints Missing Audit Logs
**Risk:** Complete loss of accountability and compliance failure  
**Detail:** Out of ~100 write endpoints (POST/PUT/PATCH/DELETE), **40+ have NO audit logging**, including:  
- `POST /security/panic` — THE most critical security action  
- `POST /guard/checkin` / `PUT /guard/checkout` — Physical access control  
- `POST /reservations` — Resource booking  
- `PATCH /admin/users/{id}/status-v2` — User status changes  
- `POST /admin/users` — User creation  
- `DELETE /reservations/{id}` — Cancellations  
- `PATCH /users/{id}/roles` — Role changes  
**Fix:** Add `log_audit_event()` to every write endpoint. Priority: security/panic, guard operations, user management.

### C3. Access Token in localStorage (XSS → Full Account Takeover)
**Risk:** If any XSS occurs, attacker gets permanent access  
**Location:** `AuthContext.js` lines 12, 29, 88, 173, 440  
**Detail:** Access tokens are stored in `localStorage.setItem('genturix_access_token', ...)`. localStorage is accessible to ANY JavaScript on the page. Combined with the remaining innerHTML in ResidentVisitHistory.jsx, this creates a direct path to account takeover.  
**Mitigation:** The refresh token IS httpOnly cookie-based (good). Short-term: reduce access token TTL to 5 minutes. Long-term: move to memory-only access token with silent refresh.

---

## 🟠 HIGH PRIORITY

### H1. Monolithic Backend — 20,400 Lines in Single File
**Risk:** Deployment failures, merge conflicts, cognitive overload, impossible code review  
**Detail:** `server.py` contains 239 endpoints, 50+ Pydantic models, 100+ helper functions, ALL business logic for 15+ modules, ALL middleware, ALL configuration. A single syntax error prevents ALL modules from loading.  
**Impact:** Any change to Finanzas could break Auth. Any developer touching Guard code must parse 20K lines.  
**Recommendation:** Phase 1: Extract each `# ====` section into its own router file under `/app/backend/routes/`. Phase 2: Extract models to `/app/backend/models/`. Phase 3: Extract helpers to `/app/backend/services/`.

### H2. Inconsistent Multi-Tenant Isolation
**Risk:** Cross-tenant data leakage  
**Detail:** Most queries correctly filter by `condominium_id`, but several internal helper functions query without tenant scoping:  
- Push notification helpers query `push_subscriptions` by `user_id` only  
- User lookup in `get_current_user` queries by `user_id` without `condominium_id`  
- Password reset queries by email globally  
While these aren't direct data leaks (users have unique IDs), they represent **weak tenant boundaries** that could leak data if user IDs ever collide or if email addresses are shared across tenants.

### H3. No Rate Limiting on Critical Endpoints
**Risk:** Abuse, automated attacks, resource exhaustion  
**Detail:** Only 8 of 239 endpoints have rate limiting. Missing from:  
- `POST /security/panic` — Could be abused for alarm flooding  
- `POST /guard/checkin` — Could be automated  
- `POST /casos` — Spam case creation  
- `POST /documentos` — Upload flood  
- `POST /notifications/v2/broadcast` — Notification spam  
- ALL financial charge creation endpoints

### H4. Frontend Components Exceeding 1000+ Lines
**Risk:** Unmaintainable, untestable, performance degradation  
**Detail:**  
- `SuperAdminDashboard.js`: **3,766 lines** (should be 10+ components)  
- `GuardUI.js`: **2,654 lines**  
- `UserManagementPage.js`: **2,371 lines**  
- `RRHHModule.js`: **2,235 lines**  
- `ResidentUI.js`: **1,415 lines** (partially superseded by ResidentHome.jsx)  

---

## 🟡 MEDIUM

### M1. Remaining innerHTML in PDF Generation
**Severity:** MEDIUM (mitigated but not eliminated)  
**Location:** `ResidentVisitHistory.jsx:459`  
**Detail:** `container.innerHTML = html` is still used. The `escapeHtml()` function was added for user-data fields, but the HTML template itself is constructed via template literals. If any new field is added without escaping, XSS returns.  
**Recommendation:** Replace `innerHTML` with a proper PDF library (html2pdf already imported — use it with DOM elements instead of raw HTML strings).

### M2. Dual Notification Systems Creating Confusion
**Detail:** V1 (`/api/notifications/*`) and V2 (`/api/notifications/v2/*`) coexist. Header.js has try/catch fallback logic that tries V2 first, falls back to V1. This creates:  
- Double maintenance burden  
- Inconsistent notification experience (V1 = panic alerts, V2 = broadcasts/cases/etc.)  
- No clear deprecation timeline  

### M3. Financial Report Uses Session-Blocking PDF Generation
**Location:** `_build_pdf_report()` — synchronous ReportLab generation  
**Detail:** For large condominiums with 500+ units, PDF generation will block the event loop for seconds. This is a sync function called from an async endpoint.  
**Fix:** Run in thread pool executor: `await asyncio.to_thread(_build_pdf_report, ...)`.

### M4. ResidentUI.js vs ResidentHome.jsx Duplication
**Detail:** Two separate resident interface files exist:  
- `/app/frontend/src/pages/ResidentUI.js` (1,415 lines) — desktop tabs  
- `/app/frontend/src/features/resident/ResidentHome.jsx` (508 lines) — actual component used by App.js  
ResidentUI.js is imported and used as a legacy desktop fallback. Both maintain separate tab configurations.

### M5. `.env` Contains Development Defaults Alongside Production Secrets
**Detail:** `DEV_MODE=true` is set in `.env` alongside production JWT secrets, Stripe keys, VAPID keys. No environment separation. If deployed as-is, dev mode features (like system reset endpoints) would be active in production.

---

## 🟢 LOW / IMPROVEMENTS

### L1. No Request Validation on Query String Periods
**Detail:** Period parameters (`YYYY-MM`) use regex validation in Pydantic models but some GET endpoints accept them as plain query strings without validation, allowing malformed inputs.

### L2. Magic Strings Throughout Codebase
**Detail:** Role names like `"Administrador"`, `"Supervisor"`, `"Guarda"` are hardcoded strings in 200+ locations. A single typo creates a silent authorization bypass.

### L3. No Pagination Limit Enforcement on Some Legacy Endpoints
**Detail:** Newer modules (Finanzas, Casos, Documentos) correctly cap `page_size` at 50. Legacy endpoints (visitor entries, notifications V1) use `to_list(None)` or arbitrary limits.

### L4. Console.log Statements in Production Frontend
**Detail:** `AuthContext.js` contains `console.log('[Auth] Refreshing access token...')` and similar debug logs that expose auth flow details in browser developer tools.

### L5. Missing `Content-Security-Policy` Header
**Detail:** Security headers include `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` but no CSP header. CSP would provide the strongest XSS mitigation.

---

## 🧠 ARCHITECTURE RECOMMENDATIONS

### 1. Backend Modularization (Priority: IMMEDIATE)
```
/app/backend/
├── server.py          → 200 lines (app init, middleware, include_router)
├── routes/
│   ├── auth.py
│   ├── guard.py
│   ├── finanzas.py
│   ├── casos.py
│   ├── documentos.py
│   ├── notifications_v2.py
│   └── ...
├── models/
│   ├── user.py
│   ├── finanzas.py
│   └── ...
├── services/
│   ├── audit.py
│   ├── push_notification.py
│   ├── storage.py
│   └── ...
└── middleware/
    ├── auth.py
    ├── billing.py
    └── rate_limit.py
```

### 2. Async-First Storage Layer
Replace synchronous `requests` with `httpx.AsyncClient` for ALL external HTTP calls (object storage, Resend emails, push notifications).

### 3. Event-Driven Notifications
Instead of inline notification creation in every endpoint (Casos creates notif_v2, Finanzas creates notif_v2), implement an event bus pattern:
```python
await emit_event("caso.created", {caso_id, condo_id, created_by})
# Listener handles notification creation
```

### 4. Database Migration Layer
No schema versioning exists. Add a migration system (e.g., `mongomigrate`) to track collection changes across deployments.

---

## ⚡ QUICK WINS (< 2 hours each)

| # | Action | Impact |
|---|--------|--------|
| 1 | Add `log_audit_event` to `/security/panic` | Compliance fix |
| 2 | Add `log_audit_event` to `/guard/checkin` and `/guard/checkout` | Compliance fix |
| 3 | Add rate limit to `/security/panic`, `/casos`, `/documentos` | Abuse prevention |
| 4 | Remove `console.log` from AuthContext.js | Security hygiene |
| 5 | Add `Content-Security-Policy` header | XSS defense-in-depth |
| 6 | Reduce ACCESS_TOKEN_EXPIRE_MINUTES from 15 to 5 | Reduces token theft window |
| 7 | Delete or deprecate ResidentUI.js (unused) | Remove dead code |
| 8 | Run `_build_pdf_report` in thread pool | Prevent event loop blocking |

---

## 🚨 GO / NO-GO FOR SCALING

### Current State: **CONDITIONAL GO**

**CAN scale to:** 5-10 condominiums, ~500 users, ~50 concurrent requests  
**CANNOT scale to:** 100+ condominiums, 10K+ users, 500+ concurrent requests  

**Blocking Issues for Scale:**
1. **Monolithic server.py** — Single point of failure, impossible horizontal scaling without refactor
2. **Synchronous HTTP in async context** — Thread starvation at ~20 concurrent document operations
3. **No connection pooling** — MongoDB client uses default settings; needs explicit pool configuration for high concurrency

**Non-Blocking but Required for Growth:**
1. Audit log coverage for compliance
2. Rate limiting expansion
3. Frontend component decomposition
4. Background job processing for heavy operations (bulk charges, reports)

### Recommendation:
**Ship current version** for early customers (< 500 users). **Immediately start** backend modularization and async storage migration. **Block** onboarding of large condominiums (500+ units) until C1 (sync HTTP) and H1 (monolith) are resolved.

---

## REGRESSION TESTING RESULTS

| Flow | Status | Notes |
|------|--------|-------|
| Login (Admin) | ✅ PASS | Token issued, profile accessible |
| Login (Resident) | ✅ PASS | Correct role and profile |
| Login (Guard) | ✅ PASS | Shift endpoint accessible |
| Dashboard Stats | ✅ PASS | Returns expected data |
| Security Dashboard | ✅ PASS | Returns expected data |
| Notifications V2 | ✅ PASS | 22 notifications returned |
| Casos | ✅ PASS | 18 cases returned |
| Documentos | ✅ PASS | 7 documents returned |
| Finanzas Overview | ✅ PASS | 10 units tracked |
| Profile Update | ✅ PASS | User data returned |
| Health Check | ✅ PASS | Status OK |

## DATA INTEGRITY RESULTS

| Check | Status | Notes |
|-------|--------|-------|
| Orphan payment records | ✅ CLEAN | 0 orphans |
| Balance consistency | ✅ CLEAN | 10/10 balances match calculated values |
| Users without condominium | ⚠️ 3 users | SuperAdmin accounts (expected) |
| Collection sizes | ✅ HEALTHY | All collections populated appropriately |

---

*End of Audit Report*
