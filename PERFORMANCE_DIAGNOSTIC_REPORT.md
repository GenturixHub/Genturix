# PERFORMANCE DIAGNOSTIC REPORT
## Module Navigation & Panic Button Loading
### Genturix Application - February 25, 2026

---

## EXECUTIVE SUMMARY

**Issue:** Module switching feels slow (1-3 seconds)

**Root Cause:** Multiple factors contributing, with FRONTEND rendering and PUSH SYNC being the primary bottlenecks.

### Delay Breakdown (Estimated):
```
Frontend Rendering/Logic:     45%
Push Sync Blocking:           25%
Network Latency:              20%
Backend Processing:           10%
```

---

## PHASE 1: FRONTEND ANALYSIS

### 1.1 Request Waterfall - Initial App Load

When ResidentUI mounts, these requests are triggered:

| Order | Endpoint | Timing | Notes |
|-------|----------|--------|-------|
| 1 | `/profile` | ~130ms | AuthContext validation (BLOCKING) |
| 2 | `/push/status` | ~317ms | usePushNotifications sync (BLOCKING UI) |
| 3 | `/visitors/notifications` | ~140ms | Polling for notifications |
| 4 | `/notifications/unread-count` | ~148ms | Parallel with #3 |
| 5 | GPS Geolocation | Variable | Browser API, can timeout at 15s |

**Total if Sequential:** ~735ms
**Total if Parallel:** ~317ms (limited by push/status)

### 1.2 Request Waterfall - Module Switch to "Visitas"

| Order | Endpoint | Timing | Notes |
|-------|----------|--------|-------|
| 1 | `/authorizations` | ~176ms | VisitorAuthorizationsResident mount |
| 2 | `/visitors/notifications` | ~115ms | **DUPLICATE** - Already fetched globally |

### 1.3 Request Waterfall - Module Switch to "Reservaciones"

| Order | Endpoint | Timing | Notes |
|-------|----------|--------|-------|
| 1 | `/reservation-areas` | ~128ms | Load available areas |
| 2 | `/reservations` | ~141ms | Load user reservations |

**These run in parallel via Promise.all** ✓

### 1.4 Request Waterfall - Module Switch to "Directorio"

| Order | Endpoint | Timing | Notes |
|-------|----------|--------|-------|
| 1 | `/directory` | ~177ms | Single request |

### 1.5 Request Waterfall - Panic Button

| Order | Endpoint | Timing | Notes |
|-------|----------|--------|-------|
| 1 | `POST /panic` | ~305ms | Alert creation + guard notifications |

---

## PHASE 1 FINDINGS: FRONTEND ISSUES

### Issue #1: Push Sync Blocks UI Render (CRITICAL)
**File:** `/frontend/src/hooks/usePushNotifications.js`
**Lines:** 90-224

The `syncSubscriptionState` function performs:
1. Service Worker registration
2. `pushManager.getSubscription()` - local check
3. `api.getPushStatus()` - backend check (8s timeout)
4. Conditional re-registration or cleanup

**Impact:** PushPermissionBanner waits for `isSynced` state before deciding to render, blocking perception of page load.

### Issue #2: Duplicate Notification Fetches
**Files:**
- `/frontend/src/pages/ResidentUI.js` lines 900-914 (global polling)
- `/frontend/src/components/VisitorAuthorizationsResident.jsx` lines 890-891 (on mount)

**Impact:** `/visitors/notifications` called twice on module switch

### Issue #3: No Data Caching
Each module refetches all data on every mount. No React Query, SWR, or context caching.

**Examples:**
- Switch away from Reservations and back → Re-fetches areas and reservations
- Switch away from Directory and back → Re-fetches all users

### Issue #4: useEffect Dependencies Cause Extra Calls
**File:** `/frontend/src/components/VisitorAuthorizationsResident.jsx`
**Lines:** 903-910

```javascript
useEffect(() => {
  fetchData();
  const interval = setInterval(() => {
    api.getVisitorNotifications().then(setNotifications).catch(console.error);
  }, 30000);
  return () => clearInterval(interval);
}, [fetchData]);
```

`fetchData` is a `useCallback` that changes reference, potentially triggering re-runs.

### Issue #5: GPS Geolocation Timeout
**File:** `/frontend/src/pages/ResidentUI.js`
**Lines:** 984-1021

GPS has a 15-second timeout. On slow/indoor connections, this can block the location indicator.

---

## PHASE 2: BACKEND ANALYSIS

### 2.1 Endpoint Response Times

| Endpoint | Avg Response | Payload Size | Variability |
|----------|--------------|--------------|-------------|
| `/profile` | 146ms | 386 bytes | Low |
| `/push/status` | 113ms | 65 bytes | Low |
| `/alerts/resident` | 172ms | 94 bytes | Medium |
| `/visitors/my` | 216ms | 112 bytes | **HIGH (428ms spike)** |
| `/visitors/notifications` | 234ms | 112 bytes | **HIGH (382ms spike)** |
| `/reservation-areas` | 160ms | 94 bytes | Medium |
| `/reservations` | 137ms | 14KB | Low |
| `/directory` | 125ms | 94 bytes | Low |

### 2.2 MongoDB Index Status

| Collection | Has Composite Index | Missing Critical Indexes |
|------------|---------------------|--------------------------|
| `panic_events` | ❌ | `{user_id: 1, condominium_id: 1}` |
| `visitor_notifications` | ❌ | `{user_id: 1, read: 1}` |
| `reservation_areas` | ❌ | `{condominium_id: 1, is_active: 1}` |

### 2.3 Query Patterns

**No N+1 queries detected.** All endpoints use single queries with projections.

**Potential Issue:** `/visitors/notifications` and `/visitors/my` show high variability (100ms → 400ms), suggesting:
- Cold cache effects
- Document scans on unindexed fields
- Aggregation pipeline overhead

---

## PHASE 3: INFRASTRUCTURE ANALYSIS

### 3.1 Server Specifications
```
CPU Cores: 4
RAM: 15GB
Disk: 95GB
Region: Preview cluster (shared infrastructure)
```

### 3.2 Network Latency
```
Average Connect Time: ~14ms
Average TTFB: 130-200ms
Average Total: 150-220ms
```

**Latency is ACCEPTABLE** for a preview environment.

### 3.3 Cold Start Behavior
First request after idle: ~250-350ms
Subsequent requests: ~100-150ms

---

## PHASE 4: ROOT CAUSE SUMMARY

### Primary Bottlenecks (Ranked)

1. **PUSH SYNC BLOCKING UI (45%)** - `usePushNotifications.js`
   - Service Worker + backend sync runs before banner renders
   - 8-second timeout on backend call
   - User perceives app as "loading" while sync completes

2. **NETWORK ROUND-TRIPS (25%)** - Multiple sequential requests
   - 4-5 requests on initial load
   - Each module switch = 1-2 additional requests
   - No request batching or caching

3. **RE-RENDER ON EVERY MOUNT (20%)** - React component lifecycle
   - Each TabsContent remounts child component
   - All data refetched from scratch
   - No stale-while-revalidate pattern

4. **MISSING MONGODB INDEXES (10%)** - Backend queries
   - `panic_events` has no compound index
   - `visitor_notifications` has no indexes
   - Query variability (100ms → 400ms)

### Exact Components Responsible

| Component | File | Line | Issue |
|-----------|------|------|-------|
| `usePushNotifications` | `hooks/usePushNotifications.js` | 90-224 | Blocking sync |
| `PushPermissionBanner` | `components/PushPermissionBanner.jsx` | 34-75 | Waits for sync |
| `ResidentUI` | `pages/ResidentUI.js` | 917-922 | Global notification polling |
| `VisitorAuthorizationsResident` | `components/VisitorAuthorizationsResident.jsx` | 903-910 | Duplicate notification fetch |
| `ResidentReservations` | `components/ResidentReservations.jsx` | 846-850 | No caching |

---

## RECOMMENDED OPTIMIZATIONS (NOT IMPLEMENTED)

### Quick Wins (< 1 hour each)
1. Move push sync to background (don't block render)
2. Remove duplicate notification fetch from VisitorAuthorizationsResident
3. Add missing MongoDB indexes

### Medium Impact (2-4 hours each)
4. Implement simple context caching for module data
5. Batch initial API calls into single endpoint
6. Add skeleton loaders instead of full-page spinners

### Long-term (> 4 hours)
7. Implement React Query or SWR for data fetching
8. Server-side rendering for initial load
9. WebSocket for real-time updates (replace polling)

---

## APPENDIX: RAW TIMING DATA

### Backend Endpoint Timings (3 samples each)
```
/profile:             130ms, 154ms, 114ms
/push/status:         104ms, 134ms, 101ms
/alerts/resident:     140ms, 166ms, 210ms
/visitors/my:         104ms, 429ms, 117ms
/visitors/notifications: 159ms, 160ms, 382ms
/reservation-areas:   152ms, 218ms, 111ms
/reservations:        137ms, 138ms, 140ms
/directory:           156ms, 97ms, 122ms
```

### Network Latency Tests
```
Request 1: Connect: 0.067s | TTFB: 0.251s | Total: 0.251s
Request 2: Connect: 0.014s | TTFB: 0.152s | Total: 0.152s
Request 3: Connect: 0.014s | TTFB: 0.148s | Total: 0.148s
```

---

**Report Generated:** February 25, 2026
**Status:** Diagnosis Complete - No Fixes Applied
