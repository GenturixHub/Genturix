# GENTURIX Production Deployment Guide

## Target Infrastructure
- **Frontend:** Vercel
- **Backend:** Railway (FastAPI)
- **Database:** MongoDB Atlas

---

## 1. Production Deployment Checklist

### 1.1 MongoDB Atlas Setup (FIRST)
1. Create MongoDB Atlas cluster (M10+ recommended for production)
2. Create database user with readWrite permissions
3. Whitelist Railway IPs or use 0.0.0.0/0 for dynamic IPs
4. Get connection string: `mongodb+srv://user:pass@cluster.mongodb.net/genturix?retryWrites=true&w=majority`

### 1.2 Railway Backend Deployment (SECOND)
**Required Environment Variables:**
```bash
# Database (REQUIRED)
MONGO_URL=mongodb+srv://user:pass@cluster.mongodb.net/genturix?retryWrites=true&w=majority
DB_NAME=genturix_production

# Environment (REQUIRED)
ENVIRONMENT=production

# Security (REQUIRED - generate strong secrets)
JWT_SECRET_KEY=<generate-256-bit-random-string>
JWT_REFRESH_SECRET_KEY=<generate-256-bit-random-string>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_MINUTES=10080

# Frontend URL (REQUIRED for CORS)
FRONTEND_URL=https://your-app.vercel.app

# Stripe (REQUIRED for payments)
STRIPE_API_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Email (REQUIRED for notifications)
RESEND_API_KEY=re_...
SENDER_EMAIL=noreply@yourdomain.com

# Push Notifications (REQUIRED)
VAPID_PUBLIC_KEY=<your-vapid-public-key>
VAPID_PRIVATE_KEY=<your-vapid-private-key>
VAPID_CLAIMS_EMAIL=admin@yourdomain.com

# Optional
LOG_LEVEL=INFO
```

**Railway Configuration:**
- Start Command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/api/health`
- Readiness Check Path: `/api/readiness`

### 1.3 Vercel Frontend Deployment (THIRD)
**Required Environment Variables:**
```bash
REACT_APP_BACKEND_URL=https://your-backend.railway.app
REACT_APP_STRIPE_PUBLIC_KEY=pk_live_...
```

**Build Settings:**
- Framework: Create React App
- Build Command: `yarn build`
- Output Directory: `build`
- Install Command: `yarn install`

---

## 2. Post-Deploy Validation Checklist

### 2.1 Health & Readiness Tests
```bash
# Health (should return 200)
curl https://your-backend.railway.app/api/health

# Readiness (should return 200 with status: ready)
curl https://your-backend.railway.app/api/readiness
```

### 2.2 Authentication Test
```bash
# Login test
curl -X POST https://your-backend.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"superadmin@genturix.com","password":"SuperAdmin123!"}'
```

### 2.3 Multi-Tenant Test
- Login as SuperAdmin
- Create a test condominium
- Login as Admin of that condominium
- Verify data isolation

### 2.4 Stripe Test
- Go to Payments section
- Start checkout flow
- Verify webhook at Railway logs
- Confirm seat upgrade

### 2.5 Push Notification Test
- Enable push notifications in profile
- Trigger panic alert from Resident
- Verify Guard receives notification

### 2.6 PDF Export Test
- Go to Audit module
- Click "Export PDF"
- Verify PDF downloads

### 2.7 CORS Verification
- Open browser console on frontend
- Verify no CORS errors
- Test all API endpoints

---

## 3. Rollback Strategy

### 3.1 Quick Rollback (Railway)
```bash
# Railway CLI
railway rollback --service backend

# Or via Railway Dashboard:
# 1. Go to Deployments
# 2. Click "..." on previous deployment
# 3. Select "Redeploy"
```

### 3.2 Vercel Rollback
```bash
# Via Dashboard:
# 1. Go to Deployments
# 2. Click "..." on previous deployment
# 3. Select "Promote to Production"
```

### 3.3 Emergency: Disable Features

**Disable Pricing Override (if causing issues):**
```javascript
// MongoDB Shell
db.system_config.updateOne(
  { id: "global_pricing" },
  { $set: { default_seat_price: 1.50 } }
);
db.condominiums.updateMany(
  {},
  { $unset: { seat_price_override: 1 } }
);
```

**Disable Push Notifications (if failing):**
```bash
# Set empty VAPID keys in Railway
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
# Restart service
```

**Enable Maintenance Mode:**
```bash
# Set in Railway
MAINTENANCE_MODE=true
```

---

## 4. Security Checklist

- [ ] JWT secrets are 256-bit random strings
- [ ] DEV_MODE is NOT set (or false)
- [ ] ENVIRONMENT=production
- [ ] Stripe keys are LIVE keys (not test)
- [ ] MongoDB user has minimal required permissions
- [ ] FRONTEND_URL is set to production domain
- [ ] CORS allows only production frontend
- [ ] /docs and /redoc are disabled
- [ ] Rate limiting is active on login endpoint
- [ ] All passwords are hashed with bcrypt

---

## 5. Monitoring & Alerts

### Railway Logs
```bash
railway logs --service backend -f
```

### Key Log Patterns to Monitor
```
[STARTUP] - Application startup
[CORS] - CORS configuration
[READINESS] - Dependency checks
[DB-INDEX] - Database index creation
[PUSH] - Push notification delivery
[AUDIT] - Security events
```

### Critical Alerts to Configure
1. Health check failures
2. Readiness check failures
3. High error rate (5xx)
4. Database connection failures
5. Stripe webhook failures

---

## 6. External Services Required

| Service | Purpose | Required Keys |
|---------|---------|---------------|
| MongoDB Atlas | Database | MONGO_URL |
| Stripe | Payments | STRIPE_API_KEY, STRIPE_WEBHOOK_SECRET |
| Resend | Email | RESEND_API_KEY |
| VAPID | Push Notifications | VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY |

---

## 7. Order of Deployment

1. **MongoDB Atlas** - Create cluster, get connection string
2. **Railway Backend** - Deploy with all env vars
3. **Stripe Webhook** - Configure webhook URL: `https://backend.railway.app/api/webhook/stripe`
4. **Vercel Frontend** - Deploy with REACT_APP_BACKEND_URL
5. **DNS** - Point custom domains
6. **Validation** - Run all post-deploy tests

---

## 8. Audit Confirmation

This deployment was audited on: February 20, 2026

**Confirmations:**
- ✅ No business logic changed
- ✅ No auth logic changed
- ✅ No multi-tenant logic modified
- ✅ No billing logic modified
- ✅ Infrastructure hardening only
- ✅ MongoDB Atlas compatible
- ✅ Railway ready
- ✅ Vercel ready
- ✅ Stripe production ready

**Files Modified (Infrastructure Only):**
- `/app/backend/server.py` - MongoDB client config, CORS config, bug fix (undefined condo_id)
- `/app/backend/requirements.txt` - Added missing reportlab dependency

**Known Production Requirements:**
- ENVIRONMENT=production disables /docs, /redoc
- DEV_MODE cannot be enabled in production
- JWT secrets are mandatory (no defaults)
- FRONTEND_URL required for CORS in production
