# GENTURIX → NOCTURNA: Cybersecurity Architecture Blueprint
## Complete Security Architecture Extraction & Reusable Design

---

## 1. AUTHENTICATION SYSTEM

### 1.1 Login Flow (Step-by-Step)
```
Client                          Backend                         MongoDB
  │                                │                                │
  ├─POST /api/auth/login──────────►│                                │
  │  {email, password}             │                                │
  │                                ├──Rate limit check (5/min)──────►
  │                                │  key = "email:client_ip"       │
  │                                │                                │
  │                                ├──find_one({email})─────────────►
  │                                │◄─────────user document─────────┤
  │                                │                                │
  │                                ├──bcrypt.checkpw()              │
  │                                │                                │
  │                                ├──Check: is_active == true      │
  │                                ├──Check: status != blocked      │
  │                                │                                │
  │                                ├──Generate refresh_token_id     │
  │                                ├──Store jti in user doc─────────►
  │                                │                                │
  │                                ├──create_access_token()         │
  │                                ├──create_refresh_token(jti)     │
  │                                │                                │
  │                                ├──log_audit_event(LOGIN)────────►
  │                                │                                │
  │◄─JSON: {access_token, user}────┤                                │
  │◄─Set-Cookie: refresh_token─────┤  (httpOnly, Secure, Lax)      │
```

### 1.2 JWT Structure

**Access Token (short-lived)**
```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "roles": ["Residente"],
  "condominium_id": "tenant-uuid",
  "exp": 1713400000,
  "iat": 1713399100,
  "type": "access"
}
```
- **Signing**: HS256 with `JWT_SECRET_KEY` (env variable, no fallback)
- **Expiry**: 15 minutes (standard), 720 minutes (guards/shift workers)

**Refresh Token (long-lived)**
```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "roles": ["Residente"],
  "condominium_id": "tenant-uuid",
  "exp": 1714003900,
  "iat": 1713399100,
  "type": "refresh",
  "jti": "unique-rotation-id"
}
```
- **Signing**: HS256 with `JWT_REFRESH_SECRET_KEY` (separate secret)
- **Expiry**: 7 days (10,080 minutes)
- **JTI**: UUID stored in DB for rotation tracking

### 1.3 Token Rotation Logic
```
Refresh Request Flow:
1. Read refresh_token from httpOnly cookie
2. Verify JWT signature + expiry + type=="refresh"
3. Extract jti (JWT ID) from payload
4. Load user from DB → compare jti with stored refresh_token_id
5. If jti ≠ stored_jti → TOKEN REUSE ATTACK DETECTED:
   a. Invalidate ALL sessions (set refresh_token_id = null)
   b. Log SECURITY_ALERT audit event
   c. Return 401
6. If jti matches → VALID:
   a. Generate new refresh_token_id
   b. Update DB with new jti
   c. Issue new access_token + new refresh_token (cookie)
   d. Old token is now permanently invalidated
```

### 1.4 Cookie Configuration
| Property | Value | Rationale |
|----------|-------|-----------|
| `httpOnly` | `true` | Prevents JavaScript access (XSS protection) |
| `secure` | `true` in production | Only sent over HTTPS |
| `sameSite` | `lax` | Prevents CSRF while allowing same-site navigation |
| `path` | `/api/auth` | Cookie only sent to auth endpoints (minimizes exposure) |
| `maxAge` | 604,800s (7 days) | Matches refresh token expiry |

### 1.5 Token Storage Locations
| Token | Backend | Frontend |
|-------|---------|----------|
| Access Token | Not stored (stateless JWT) | `localStorage` + memory |
| Refresh Token | JTI stored in `users.refresh_token_id` | httpOnly cookie (not accessible by JS) |
| User Data | MongoDB `users` collection | `localStorage` (non-sensitive fields only) |

---

## 2. AUTHORIZATION SYSTEM

### 2.1 Role-Based Access Control (RBAC)
```python
class RoleEnum(str, Enum):
    SUPER_ADMIN = "SuperAdmin"    # Platform-wide God mode
    ADMINISTRADOR = "Administrador"  # Tenant admin
    SUPERVISOR = "Supervisor"     # Read-heavy, limited writes
    HR = "HR"                     # Human resources module only
    GUARDA = "Guarda"             # Security guard (extended sessions)
    RESIDENTE = "Residente"       # Standard tenant user
    ESTUDIANTE = "Estudiante"     # School module user
```

### 2.2 Permission Enforcement Pattern
```python
# Dependency injection chain:
get_current_user(credentials)
  → verify_access_token(token)        # JWT signature + expiry
  → db.users.find_one({id: sub})      # User exists + is_active
  → check status ∉ [blocked, suspended]
  → check iat > status_changed_at     # Session invalidation
  → check iat > password_changed_at   # Password change invalidation
  → return user document

require_role(*allowed_roles)
  → get_current_user()
  → check user.roles ∩ allowed_roles ≠ ∅
  → return user or raise 403

# Usage:
@router.get("/admin/users")
async def list_users(user=Depends(require_role(RoleEnum.ADMINISTRADOR))):
    ...
```

### 2.3 Session Invalidation Triggers
- **Password change**: All tokens issued before `password_changed_at` are rejected
- **Account status change**: All tokens issued before `status_changed_at` are rejected
- **Logout**: `refresh_token_id` set to `null` → refresh attempts fail
- **Token reuse detection**: `refresh_token_id` set to `null` → ALL sessions killed

---

## 3. MULTI-TENANT SECURITY

### 3.1 Tenant Isolation Model
```
Every data query follows this pattern:

  db.collection.find({
      "condominium_id": current_user["condominium_id"],
      ...filters
  })

The condominium_id comes from the authenticated user document,
NOT from the request body/params. This prevents tenant ID spoofing.
```

### 3.2 Enforcement Points
| Layer | Mechanism |
|-------|-----------|
| JWT Payload | `condominium_id` embedded at login time |
| FastAPI Dependency | `get_current_user()` returns full user with `condominium_id` |
| Database Query | Every `find()`, `insert()`, `update()`, `delete()` includes tenant filter |
| Billing Middleware | Suspended tenants get 402 on write operations |
| SuperAdmin Override | SuperAdmin can query across tenants (platform operations) |

### 3.3 Billing Suspension Middleware
```python
# Middleware intercepts ALL POST/PUT/DELETE/PATCH requests:
# - Reads JWT from Authorization header
# - Checks condominium billing_status
# - If "suspended": returns 402 (Payment Required)
# - Exemptions: auth, health, billing, super-admin routes
# - SuperAdmin and demo condos are never blocked
```

### 3.4 Known Risks & Mitigations
| Risk | Status | Mitigation |
|------|--------|------------|
| Tenant ID in JWT is stale after migration | LOW | Re-login required for tenant changes |
| Aggregation queries crossing tenants | MITIGATED | All pipelines include `$match: {condominium_id}` |
| SuperAdmin data leakage | ACCEPTED | SuperAdmin is platform operator role |

---

## 4. API SECURITY

### 4.1 Rate Limiting (Dual Layer)
```
Layer 1 — slowapi (IP-based, per-endpoint):
  RATE_LIMIT_GLOBAL    = "60/minute"   # Default endpoints
  RATE_LIMIT_AUTH      = "5/minute"    # Login, register
  RATE_LIMIT_SENSITIVE = "3/minute"    # Password reset
  RATE_LIMIT_PUSH      = "10/minute"   # Push notifications

Layer 2 — Custom login brute-force (email:IP key):
  MAX_ATTEMPTS_PER_MINUTE = 5
  BLOCK_WINDOW_SECONDS = 60
  Storage: in-memory dict (resets on restart)
```

### 4.2 Input Sanitization
```python
# HTML tag stripping via bleach on all user-provided text:
SANITIZE_FIELDS = [
    "full_name", "name", "description", "message", "notes",
    "visitor_name", "title", "comment", "subject", "body", ...
]

sanitize_text(text):
  → bleach.clean(text, tags=[], strip=True)
  → truncate to max_length (default 10,000 chars)
```

### 4.3 Error Handling (Information Leakage Prevention)
```python
# Production: minimal response
{"error": "Internal Server Error", "request_id": "uuid"}

# Development: type hint only (never stacktrace)
{"error": "Internal Server Error", "request_id": "uuid", "exception_type": "ValueError"}
```

### 4.4 Protection Matrix
| Attack | Protection | Implementation |
|--------|------------|----------------|
| SQL Injection | N/A | MongoDB (NoSQL) — no SQL queries |
| NoSQL Injection | Pydantic models | Request bodies validated via BaseModel schemas |
| XSS (Stored) | `bleach.clean()` | All user text fields sanitized before storage |
| XSS (Reflected) | CSP headers | `script-src 'self'` blocks inline injection from external |
| CSRF | `SameSite=Lax` cookie | Refresh token cookie not sent on cross-origin requests |
| Brute Force | Dual rate limiting | slowapi + custom per-email:IP limiter |
| Path Traversal | Regex validation | `".." in path` check on all file proxy endpoints |
| SSRF | Allowlist | Object Storage URLs are internal paths, not user-controlled |

---

## 5. FILE & STORAGE SECURITY

### 5.1 Upload Validation
```python
MAX_FILE_SIZE = 20 MB (documents), 5 MB (images)

BLOCKED_EXTENSIONS = {
    "exe", "bat", "cmd", "sh", "ps1", "msi", "dll",
    "vbs", "js", "jar", "py", "php", "asp", "jsp", "cgi"
}

ALLOWED_MIME_PREFIXES = {
    "application/pdf", "application/msword", "application/vnd.",
    "text/", "image/jpeg", "image/png", "image/gif", "image/webp"
}

Validation chain:
1. Check file size ≤ MAX_FILE_SIZE
2. Check extension ∉ BLOCKED_EXTENSIONS
3. Check extension ∈ ALLOWED_EXTENSIONS
4. Validate MIME type against ALLOWED_MIME_PREFIXES
5. Block dangerous MIME types (x-executable, x-sh)
6. Sanitize filename (strip path traversal, unicode normalize)
7. Generate UUID filename for storage (never use original name as path)
```

### 5.2 Storage Access Control
```
Files are NEVER publicly accessible.

Storage paths: genturix/{module}/{condominium_id}/{resource_id}/{uuid}.ext

Download flow:
  Client → GET /api/documentos/{doc_id}/download
         → Authenticate user (JWT header or token query param)
         → Verify user.condominium_id == doc.condominium_id
         → Check visibility rules (public/private/roles)
         → Proxy file bytes from Object Storage → client

Image proxy flow (for <img src> usage):
  <img src="/api/casos/image-proxy?path=...&token=...">
         → Validate token (header or query param)
         → Validate path starts with expected prefix
         → Reject path traversal (..)
         → Stream image from storage with Cache-Control
```

### 5.3 URL Exposure Model
| Risk | Status |
|------|--------|
| Direct storage URLs exposed to client | **NO** — all access through proxy |
| Storage paths predictable | LOW — UUID-based paths |
| Token in URL for image proxy | ACCEPTED — short-lived access tokens only |

---

## 6. SESSION MANAGEMENT

### 6.1 Token Expiration Strategy
| Token | TTL | Renewal |
|-------|-----|---------|
| Access Token | 15 min (standard) | Via refresh endpoint |
| Access Token (Guard) | 12 hours | Via refresh endpoint |
| Refresh Token | 7 days | Rotated on each use |

### 6.2 Refresh Flow (with Mutex)
```
Frontend Interceptor:
  API call → 401 response
    → Check: is another refresh already in progress?
      YES → await existing promise (shared mutex)
      NO  → call POST /api/auth/refresh (with credentials: 'include')
            → Store new access_token
            → Retry original request
            → If refresh fails → redirect to /login

Mutex prevents race condition where:
  - Multiple 401s trigger simultaneous refreshes
  - First refresh rotates token → second refresh fails
  - Second failure triggers logout
```

### 6.3 Logout Behavior
```python
POST /api/auth/logout:
  1. Set refresh_token_id = None in user document
  2. Clear httpOnly cookie (maxAge=0)
  3. Log LOGOUT audit event
  4. Frontend clears localStorage + memory state
```

### 6.4 Session Invalidation Events
| Event | Action |
|-------|--------|
| Logout | Clear cookie + nullify refresh_token_id |
| Password change | Set `password_changed_at` → old tokens rejected by iat check |
| Account blocked | Set `status_changed_at` → old tokens rejected by iat check |
| Token reuse detected | Nullify refresh_token_id → ALL sessions killed |

---

## 7. FRONTEND SECURITY

### 7.1 Token Storage
| Data | Location | Risk |
|------|----------|------|
| `access_token` | `localStorage` + React state | XSS can steal; mitigated by 15-min expiry |
| `refresh_token` | httpOnly cookie | Not accessible by JavaScript |
| `user` object | `localStorage` (non-sensitive) | Display data only, no secrets |

### 7.2 API Call Security
```javascript
// All API calls go through ApiService.request():
headers['Authorization'] = `Bearer ${accessToken}`;
credentials: 'include'  // Always send cookies

// File downloads on mobile:
const isMobile = /Android|iPhone|iPad/i.test(navigator.userAgent);
if (isMobile) {
    window.location.href = `${url}?token=${accessToken}`;  // Direct navigation
} else {
    fetch(url, {headers, credentials}).then(blob => download);  // Blob method
}
```

### 7.3 401 Interceptor
```javascript
// Shared module-level mutex:
let _refreshPromise = null;

export async function refreshToken() {
    if (_refreshPromise) return _refreshPromise;  // Deduplicate
    _refreshPromise = fetch('/api/auth/refresh', {credentials: 'include'})
        .then(resp => resp.ok ? resp.json().access_token : null)
        .finally(() => _refreshPromise = null);
    return _refreshPromise;
}
```

---

## 8. HEADERS & INFRASTRUCTURE

### 8.1 Security Headers (Applied via Middleware)
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
X-Request-ID: {uuid}  (per-request traceability)

Content-Security-Policy:
  default-src 'self';
  script-src 'self' 'unsafe-inline' 'unsafe-eval';
  style-src 'self' 'unsafe-inline' fonts.googleapis.com cdnjs.cloudflare.com;
  font-src 'self' fonts.gstatic.com cdnjs.cloudflare.com;
  img-src 'self' data: blob: https:;
  connect-src 'self' *.emergentagent.com *.stripe.com *.genturix.com;
  frame-src *.stripe.com;
```

### 8.2 CORS Configuration
```python
# Production: explicit allowlist
allow_origins = [
    "https://genturix.com",
    "https://www.genturix.com",
    "https://app.genturix.com",
    FRONTEND_URL
]
# Development: adds localhost:3000
allow_credentials = True  # Required for httpOnly cookies
allow_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
allow_headers = ["Authorization", "Content-Type", "X-Requested-With", "Accept"]
```

### 8.3 API Documentation
```python
# Production: docs disabled
docs_url = None if ENVIRONMENT == "production" else "/docs"
redoc_url = None if ENVIRONMENT == "production" else "/redoc"
```

---

## 9. KNOWN WEAKNESSES

| # | Weakness | Severity | Description | Recommended Fix |
|---|----------|----------|-------------|-----------------|
| 1 | Access token in localStorage | MEDIUM | XSS can steal the 15-min access token | Move to memory-only; rely on cookie refresh on reload |
| 2 | CSP allows `unsafe-inline` + `unsafe-eval` | MEDIUM | Reduces CSP effectiveness against XSS | Use nonces for inline scripts; remove eval |
| 3 | In-memory rate limiting (login) | LOW | Resets on server restart; no cross-instance sharing | Move to Redis for distributed rate limiting |
| 4 | Token in URL for mobile downloads | LOW | Token visible in server logs / browser history | Use short-lived download tokens (1-min expiry, single-use) |
| 5 | No request body size limit at app level | LOW | Large payloads could cause memory issues | Add `max_request_size` middleware |
| 6 | Refresh token rotation race window | LOW | ~1ms window where old + new tokens both valid | Already mitigated by frontend mutex |

---

## 10. REUSABLE SECURITY BLUEPRINT FOR NOCTURNA

### 10.1 Recommended Auth Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    NOCTURNA AUTH                         │
│                                                         │
│  Login: email + bcrypt password → access + refresh      │
│                                                         │
│  Access Token:                                          │
│    • Storage: memory ONLY (not localStorage)            │
│    • TTL: 15 minutes                                    │
│    • Claims: sub, email, roles, tenant_id, type, iat    │
│    • Signing: HS256 with env-only secret (no fallback)  │
│                                                         │
│  Refresh Token:                                         │
│    • Storage: httpOnly cookie (Secure, SameSite=Lax)    │
│    • TTL: 7 days                                        │
│    • Rotation: new JTI on each refresh                  │
│    • Reuse detection: invalidates ALL sessions          │
│    • Cookie path: /api/auth (minimal scope)             │
│                                                         │
│  Session Kill Triggers:                                 │
│    • Logout (clear cookie + nullify jti)                │
│    • Password change (iat < password_changed_at)        │
│    • Account lock (iat < status_changed_at)             │
│    • Token reuse (nuclear: kill all sessions)           │
└─────────────────────────────────────────────────────────┘
```

### 10.2 Recommended Middleware Stack
```python
# Order matters — first registered = outermost layer

1. RequestID Middleware        # Generate UUID per request
2. Security Headers Middleware # X-Frame-Options, CSP, nosniff
3. Billing Block Middleware    # Suspend write ops for unpaid tenants
4. CORS Middleware            # Explicit origin allowlist
5. Rate Limiting              # slowapi per-endpoint limits
6. Global Exception Handler   # Safe error responses, no stack traces

# Per-endpoint:
7. get_current_user           # JWT validation + user lookup
8. require_role(*roles)       # RBAC enforcement
9. sanitize_text()            # Input sanitization
10. log_audit_event()         # Write operation audit trail
```

### 10.3 Recommended Multi-Tenant Enforcement
```python
# RULE: tenant_id NEVER comes from the request.
# It ALWAYS comes from the authenticated user document.

async def get_current_user(token) -> User:
    payload = verify_jwt(token)
    user = await db.users.find_one({"id": payload["sub"]})
    return user  # user.tenant_id is the source of truth

# Every database operation:
async def list_items(user=Depends(get_current_user)):
    tenant_id = user["tenant_id"]  # From auth, NOT from request
    return await db.items.find({"tenant_id": tenant_id}).to_list()
```

### 10.4 Recommended File Storage Model
```
Upload:
  1. Validate size, extension, MIME type
  2. Sanitize filename (strip path traversal chars)
  3. Generate UUID-based storage path: {app}/{module}/{tenant_id}/{uuid}.ext
  4. Store via internal Object Storage API (never expose storage URLs)
  5. Save storage path + metadata in MongoDB

Download:
  1. Authenticate user (JWT or token query param for <img> tags)
  2. Load document metadata from DB
  3. Verify tenant_id matches
  4. Check visibility rules (public/private/role-based)
  5. Proxy file bytes from storage → client
  6. NEVER redirect to a storage URL
```

### 10.5 Recommended Audit Logging
```python
# Every write operation MUST include:
await log_audit_event(
    event_type=AuditEventType.RESOURCE_CREATED,
    user_id=user["id"],
    module="module_name",
    details={"action": "create", "resource_id": id, ...},
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent"),
    tenant_id=user["tenant_id"],
    user_email=user["email"],
)

# Stored in: audit_logs collection
# Fields: id, event_type, user_id, user_email, tenant_id,
#          module, details, ip_address, user_agent, timestamp
```

### 10.6 Environment Variable Requirements
```bash
# MANDATORY (app crashes without these):
JWT_SECRET_KEY=<random-64-char>
JWT_REFRESH_SECRET_KEY=<different-random-64-char>
MONGO_URL=<connection-string>
DB_NAME=<database-name>
ENVIRONMENT=production|development

# RECOMMENDED:
FRONTEND_URL=https://app.nocturna.com
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_MINUTES=10080

# SECURITY: No fallback values for secrets.
# Missing secrets = crash on startup (fail-fast).
```

---

*Generated: 2026-04-18 | Source: Genturix v1.0.0 | Target: Nocturna SaaS Platform*
