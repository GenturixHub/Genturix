# GENTURIX - Security Architecture Document

**Version:** 1.0  
**Date:** February 2026  
**Classification:** Internal / Investor / Audit Ready  
**Author:** Security Architecture Review  

---

## Executive Summary

This document describes the current security architecture of GENTURIX, a multi-tenant SaaS platform for condominium management. It provides an honest assessment of implemented controls, known risks, and a prioritized hardening roadmap.

GENTURIX handles sensitive data including resident PII, access logs, panic alerts, and payment information. The platform operates across multiple roles (Resident, Guard, Administrator, SuperAdmin) with varying privilege levels.

---

## 1. Current Implementation

### 1.1 Authentication & Session Management

| Control | Status | Implementation |
|---------|--------|----------------|
| Password Hashing | ✅ Implemented | bcrypt with auto-generated salt |
| JWT Access Tokens | ✅ Implemented | HS256, 30-minute expiry, stored in memory (not localStorage) |
| Refresh Tokens | ✅ Implemented | httpOnly cookie, Secure flag, SameSite=Lax |
| Session Invalidation | ✅ Implemented | Logout clears cookie, token refresh tracked |
| Login Rate Limiting | ✅ Implemented | In-memory, 5 attempts/minute per email:IP |

**Token Configuration:**
```
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
COOKIE_SECURE = True (production)
COOKIE_SAMESITE = "lax"
COOKIE_HTTPONLY = True
```

**Limitations:**
- Rate limiting is in-memory only (not distributed across instances)
- No account lockout after N failed attempts (rate limit resets after window)
- No MFA/2FA implementation

### 1.2 Authorization & Access Control

| Control | Status | Implementation |
|---------|--------|----------------|
| Role-Based Access Control | ✅ Implemented | Backend-enforced via `require_role()` decorator |
| Multi-Tenant Isolation | ✅ Implemented | `condominium_id` filter on all tenant-scoped queries |
| Cross-Tenant Validation | ✅ Implemented | `validate_tenant_resource()` blocks unauthorized access |
| SuperAdmin Bypass | ✅ Implemented | SuperAdmin role bypasses tenant filters |

**Role Hierarchy:**
```
SuperAdmin > Administrador > Supervisor > Guarda > HR > Residente
```

**Tenant Isolation Pattern:**
```python
# All tenant-scoped queries include:
{"condominium_id": current_user["condominium_id"]}

# Cross-tenant access blocked with:
if resource["condominium_id"] != user["condominium_id"]:
    raise HTTPException(403, "Access denied: cross-tenant access blocked")
```

### 1.3 Audit Logging

| Control | Status | Implementation |
|---------|--------|----------------|
| Security Event Logging | ✅ Implemented | MongoDB `audit_logs` collection |
| Login/Logout Tracking | ✅ Implemented | IP, User-Agent, timestamp captured |
| Sensitive Action Logging | ✅ Implemented | 50+ event types defined |
| Cross-Tenant Attempt Logging | ✅ Implemented | `[TENANT-BLOCK]` log entries |

**Logged Event Types (partial):**
- `LOGIN_SUCCESS`, `LOGIN_FAILURE`, `LOGOUT`
- `TOKEN_REFRESH`, `PASSWORD_CHANGED`
- `PANIC_BUTTON`, `PANIC_RESOLVED`
- `USER_CREATED`, `USER_BLOCKED`, `USER_DELETED`
- `PAYMENT_INITIATED`, `PAYMENT_COMPLETED`
- `AUTHORIZATION_CREATED`, `VISITOR_CHECKIN`
- `SECURITY_ALERT`, `SEAT_LIMIT_UPDATED`

**Limitations:**
- No centralized log aggregation (SIEM)
- No real-time alerting on security events
- Logs stored in same MongoDB instance as application data

### 1.4 Payment Security (Stripe Integration)

| Control | Status | Implementation |
|---------|--------|----------------|
| Server-Side Price Calculation | ✅ Implemented | `calculate_subscription_price_dynamic()` |
| Checkout Session Creation | ✅ Implemented | Backend-only via Stripe SDK |
| Webhook Endpoint | ✅ Implemented | `/api/webhook/stripe`, `/api/webhook/stripe-subscription` |
| Webhook Signature Validation | ⚠️ Partial | SDK handles validation, but `STRIPE_WEBHOOK_SECRET` empty in .env |
| Price Manipulation Prevention | ✅ Implemented | Frontend cannot send arbitrary amounts |

**Current Configuration:**
```
STRIPE_API_KEY = sk_test_... (test mode)
STRIPE_WEBHOOK_SECRET = (empty)
```

### 1.5 Push Notifications (VAPID)

| Control | Status | Implementation |
|---------|--------|----------------|
| VAPID Key Pair | ✅ Configured | Public/private keys in environment |
| Subscription Storage | ✅ Implemented | MongoDB with user_id, role, condominium_id |
| Invalid Subscription Cleanup | ✅ Implemented | Auto-delete on 404/410 only |
| Tenant-Scoped Delivery | ✅ Implemented | Guards only receive alerts from their condominium |

### 1.6 Email Service (Resend)

| Control | Status | Implementation |
|---------|--------|----------------|
| API Key Configuration | ✅ Configured | `RESEND_API_KEY` in environment |
| Sender Domain | ⚠️ Test Mode | Using `onboarding@resend.dev` |
| Email Delivery | ⚠️ Limited | Only delivers to verified addresses |

### 1.7 Data Protection

| Control | Status | Implementation |
|---------|--------|----------------|
| Password Storage | ✅ Secure | bcrypt hashed, never logged |
| MongoDB ObjectId Exclusion | ✅ Implemented | `{"_id": 0}` projection on queries |
| Sensitive Data in Responses | ✅ Implemented | `hashed_password` excluded from user responses |

### 1.8 CORS Configuration

| Control | Status | Implementation |
|---------|--------|----------------|
| Origin Allowlist | ✅ Implemented | Environment-based origin list |
| Credentials Support | ✅ Enabled | `allow_credentials=True` |
| Methods/Headers | ⚠️ Permissive | `allow_methods=["*"]`, `allow_headers=["*"]` |

---

## 2. Known Risks

### 2.1 Critical (P0)

| Risk ID | Description | Impact | Current State |
|---------|-------------|--------|---------------|
| R-001 | **Stripe webhook secret not configured** | Attackers could forge webhook calls to activate seats without payment | `STRIPE_WEBHOOK_SECRET` is empty |
| R-002 | **Resend domain not verified** | Credential emails cannot reach production users | Using test domain `resend.dev` |

### 2.2 High (P1)

| Risk ID | Description | Impact | Current State |
|---------|-------------|--------|---------------|
| R-003 | **No security headers** | XSS, clickjacking, MIME sniffing attacks | No CSP, X-Frame-Options, X-Content-Type-Options |
| R-004 | **In-memory rate limiting** | Rate limits not enforced in multi-instance deployment | Single-process rate limit dict |
| R-005 | **Permissive CORS** | Potential for malicious origins if allowlist misconfigured | `allow_methods=["*"]`, `allow_headers=["*"]` |
| R-006 | **No account lockout** | Sustained brute-force beyond rate limit window | Rate limit resets after 60 seconds |

### 2.3 Medium (P2)

| Risk ID | Description | Impact | Current State |
|---------|-------------|--------|---------------|
| R-007 | **No MFA/2FA** | Single-factor authentication for all roles | Not implemented |
| R-008 | **Audit logs in application DB** | Log tampering if DB compromised | Same MongoDB instance |
| R-009 | **No real-time alerting** | Delayed detection of security incidents | Logs only, no SIEM/alerting |
| R-010 | **JWT secret rotation** | No documented rotation procedure | Static `JWT_SECRET` in environment |
| R-011 | **Monolithic backend** | Large attack surface, difficult to isolate failures | Single `server.py` (~15,000 lines) |

### 2.4 Low (P3)

| Risk ID | Description | Impact | Current State |
|---------|-------------|--------|---------------|
| R-012 | **No request ID correlation** | Difficult to trace requests across logs | Partial implementation |
| R-013 | **Service Worker caching** | Stale security patches if SW not updated | Manual update mechanism |

---

## 3. Hardening Roadmap

### Phase 0: Production Blockers (Before Go-Live)

| Priority | Action | Risk Addressed | Effort |
|----------|--------|----------------|--------|
| P0-1 | **Configure `STRIPE_WEBHOOK_SECRET`** in Railway environment | R-001 | 15 min |
| P0-2 | **Verify production domain in Resend** and update `SENDER_EMAIL` | R-002 | 30 min |
| P0-3 | **Switch Stripe API key** from `sk_test_` to `sk_live_` | R-001 | 5 min |

### Phase 1: Critical Security Hardening (Week 1-2)

| Priority | Action | Risk Addressed | Effort |
|----------|--------|----------------|--------|
| P1-1 | **Add security headers middleware** | R-003 | 2 hours |

```python
# Recommended middleware
from starlette.middleware import Middleware
from starlette.responses import Response

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(self)"
    return response
```

| Priority | Action | Risk Addressed | Effort |
|----------|--------|----------------|--------|
| P1-2 | **Implement Redis-based rate limiting** | R-004 | 4 hours |
| P1-3 | **Restrict CORS methods/headers** to required values | R-005 | 1 hour |
| P1-4 | **Add account lockout** after 10 failed attempts (30-min lockout) | R-006 | 2 hours |

### Phase 2: Enhanced Security (Week 3-4)

| Priority | Action | Risk Addressed | Effort |
|----------|--------|----------------|--------|
| P2-1 | **Implement TOTP-based 2FA** for Admin/SuperAdmin roles | R-007 | 8 hours |
| P2-2 | **Configure separate audit log storage** (separate collection/DB) | R-008 | 4 hours |
| P2-3 | **Document JWT secret rotation procedure** | R-010 | 2 hours |
| P2-4 | **Add Slack/email alerting** for critical security events | R-009 | 4 hours |

### Phase 3: Architecture Improvements (Month 2+)

| Priority | Action | Risk Addressed | Effort |
|----------|--------|----------------|--------|
| P3-1 | **Modularize backend** into separate route files | R-011 | 16+ hours |
| P3-2 | **Implement request ID correlation** across all logs | R-012 | 4 hours |
| P3-3 | **Add CSP header** with strict policy | R-003 | 4 hours |
| P3-4 | **Implement API versioning** for breaking changes | - | 8 hours |

---

## 4. Compliance Considerations

### 4.1 Data Residency

- **Current:** MongoDB Atlas (region configurable)
- **Recommendation:** Document data residency for LATAM compliance

### 4.2 Data Retention

- **Current:** No automated data retention policy
- **Recommendation:** Implement 90-day audit log rotation, 7-year financial record retention

### 4.3 Right to Deletion (GDPR/LFPDPPP)

- **Current:** Manual deletion via SuperAdmin
- **Recommendation:** Implement automated PII anonymization endpoint

---

## 5. Security Testing Recommendations

| Test Type | Frequency | Scope |
|-----------|-----------|-------|
| SAST (Static Analysis) | CI/CD | All code changes |
| DAST (Dynamic Scanning) | Weekly | Production endpoints |
| Penetration Testing | Annually | Full application |
| Dependency Scanning | CI/CD | `requirements.txt`, `package.json` |

---

## 6. Incident Response

### 6.1 Current Capabilities

- Audit logs available in MongoDB
- Manual log review via DB queries
- No automated alerting

### 6.2 Recommended Improvements

1. Define incident classification (P1-P4)
2. Establish on-call rotation
3. Configure PagerDuty/Opsgenie integration
4. Document runbooks for common incidents

---

## Appendix A: Environment Variables (Security-Critical)

| Variable | Purpose | Rotation Frequency |
|----------|---------|-------------------|
| `JWT_SECRET` | Token signing | Annually (with migration) |
| `STRIPE_API_KEY` | Payment processing | On compromise |
| `STRIPE_WEBHOOK_SECRET` | Webhook validation | On compromise |
| `RESEND_API_KEY` | Email delivery | On compromise |
| `VAPID_PRIVATE_KEY` | Push encryption | On compromise |
| `MONGO_URL` | Database connection | On compromise |

---

## Appendix B: Security Contacts

| Role | Responsibility |
|------|----------------|
| Security Lead | Architecture decisions, incident escalation |
| DevOps | Infrastructure, secrets management |
| Backend Lead | Authentication, authorization code |

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-25 | Security Review | Initial document |

---

*This document reflects the actual state of the GENTURIX security architecture as of the date above. It is intended for internal use, investor due diligence, and external audit purposes.*
