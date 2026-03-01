# GENTURIX - Critical System Audit Report
## User Identity Collision + Visits PDF Export

**Date:** March 2026
**Auditor:** System Deep Audit
**Status:** ROOT CAUSES IDENTIFIED

---

## ISSUE 1: USER IDENTITY COLLISION

### Observed Behavior
When logged in as a resident, parts of the UI (Directory and other components) display Administrator account data for users with the same name.

### Root Cause Analysis

#### Finding 1: Query Keys Without User Scope (CONFIRMED)
**Location:** `/app/frontend/src/hooks/queries/useResidentQueries.js`
**Lines:** 22-31

```javascript
export const residentKeys = {
  all: ['resident'],
  notifications: () => [...residentKeys.all, 'notifications'],
  authorizations: () => [...residentKeys.all, 'authorizations'],
  directory: () => [...residentKeys.all, 'directory'],  // NO user_id!
  ...
};
```

**Problem:** Query keys are static and don't include `user_id` or `condominium_id`. When React Query persists cache to localStorage, data from User A can be loaded for User B if they share the same device or if cache isn't properly cleared.

#### Finding 2: Cache Persistence Without User Scope
**Location:** `/app/frontend/src/config/queryPersister.js`
**Lines:** 33-37

```javascript
return createSyncStoragePersister({
  storage: window.localStorage,
  key: 'GENTURIX_QUERY_CACHE',  // Single key for ALL users!
  throttleTime: 1000,
});
```

**Problem:** All users share the same localStorage cache key. The cache buster (`v2`) doesn't change between users.

#### Finding 3: Potential Race Condition on Login
**Location:** `/app/frontend/src/contexts/AuthContext.js`
**Lines:** 164-169

The `queryClient.clear()` is called during login, but there may be a race condition where old cached data is loaded before the clear completes.

### Verification
Backend queries are CORRECT - they all use `id` field:
- `/api/profile/{user_id}` - Uses `{"id": user_id}` ✅
- `/api/profile/directory/condominium` - Uses `{"id": ...}` for each user ✅
- All user queries use unique `id` field, not `name` ✅

### Fix Applied

1. **Query Keys now include condominium_id:**
```javascript
directory: (condoId) => [...residentKeys.all, 'directory', condoId],
```

2. **Cache key includes user identifier:**
```javascript
key: `GENTURIX_QUERY_CACHE_${userId || 'anonymous'}`,
```

3. **Added explicit cache clear before any data fetch on login**

---

## ISSUE 2: VISITS HISTORY PDF EXPORT BLANK

### Observed Behavior
The "Download Visits History PDF" feature consistently generates an empty PDF.

### Root Cause Analysis

#### Finding 1: Backend Returns Data Correctly (VERIFIED)
**Endpoint:** `GET /api/resident/visit-history/export`
**Test Result:**
```json
{
  "resident_name": "Residente de Prueba",
  "entries": 3,
  "total_entries": 3
}
```
✅ Backend is working correctly.

#### Finding 2: html2pdf.js Rendering Issue (ROOT CAUSE)
**Location:** `/app/frontend/src/components/ResidentVisitHistory.jsx`
**Lines:** 449-466

```javascript
const container = document.createElement('div');
container.style.cssText = `
  position: fixed;
  top: 0;
  left: 0;
  width: 800px;
  z-index: -9999;
  visibility: visible;  // PROBLEM: May not render properly
`;
```

**Problem:** `html2pdf.js` uses `html2canvas` internally which requires:
1. Element to be in the visible viewport
2. Sufficient render time
3. Proper z-index layering

The current implementation places the element at `z-index: -9999` which can cause rendering issues in some browsers.

#### Finding 3: Timing Issue
**Line:** 470
```javascript
await new Promise(resolve => setTimeout(resolve, 500));
```

500ms may not be enough for complex tables to fully render, especially on slower devices.

### Fix Applied

1. **Changed rendering approach:**
   - Use `document.body` append with proper visibility
   - Increased render wait time to 1000ms
   - Added explicit `offsetHeight` access to force layout

2. **Added blob validation:**
   - Check PDF output size before triggering download
   - Log debug info for troubleshooting

3. **Fallback mechanism:**
   - If html2pdf fails, use window.print() as fallback

---

## FILES MODIFIED

### Issue 1 - Identity Collision
1. `/app/frontend/src/hooks/queries/useResidentQueries.js`
   - Added condominium_id to directory query key
   
2. `/app/frontend/src/config/queryPersister.js`
   - Added user-scoped cache key

3. `/app/frontend/src/contexts/AuthContext.js`
   - Added synchronous cache clear with await

### Issue 2 - PDF Export
1. `/app/frontend/src/components/ResidentVisitHistory.jsx`
   - Fixed container rendering approach
   - Added debug logging
   - Increased render wait time
   - Added output validation

---

## VERIFICATION TESTS

### Identity Collision Test
1. Login as User A (resident)
2. View Directory
3. Logout
4. Login as User B (admin with same name)
5. View Directory
6. Verify User B sees their own data, not User A's

### PDF Export Test
1. Login as resident with visit history
2. Click "Export PDF"
3. Verify PDF downloads with content
4. Check PDF contains:
   - Resident name
   - Visit entries
   - Correct dates

---

## RECOMMENDATIONS

### Short Term (Applied)
- ✅ Add user scope to query keys
- ✅ Fix PDF rendering approach
- ✅ Add debug logging

### Medium Term
- Add unique constraint on `(full_name, condominium_id)` in database
- Implement PDF generation on backend (more reliable)
- Add integration tests for cache isolation

### Long Term
- Consider using backend-generated PDFs with reportlab
- Implement proper session-scoped caching
- Add E2E tests for user switching scenarios

---

**Report Generated:** March 2026
**Next Review:** After production deployment
