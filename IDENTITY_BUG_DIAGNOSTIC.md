# GENTURIX Identity Bug - Diagnostic Report
**Date:** 2026-02-28
**Bug Type:** CRITICAL - Identity Leak
**Severity:** HIGH - Security Issue

---

## PROBLEM DESCRIPTION

When a user logs out and logs in as another user, the Profile UI shows the **previous user's data** instead of the new user's data.

**Example:**
1. Login as Guard "Martin Alfaro"
2. Logout
3. Login as Resident "Christopher Campos"
4. Profile shows "Martin Alfaro" ❌

**Backend correctly identifies the user** (alerts arrive with correct name), but **frontend displays stale cached data**.

---

## ROOT CAUSE ANALYSIS

### Bug Location: `/app/frontend/src/contexts/AuthContext.js`

**Line 364-402 - logout function:**
```javascript
const logout = useCallback(async () => {
  // ...
  finally {
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.USER);
    localStorage.removeItem(STORAGE_KEYS.PASSWORD_RESET);
    
    // ✅ Clears localStorage persistence
    clearPersistedCache();
    
    // ❌ MISSING: Does NOT clear queryClient in-memory cache
    // queryClient.clear() is NOT called!
    
    setUser(null);
    setAccessToken(null);
  }
}, [accessToken]);
```

### Why This Happens:

1. **TanStack Query caches profile data in memory**
   - `useOwnProfile()` stores data with key `['profile', 'own']`
   - This data persists in the queryClient until explicitly cleared
   
2. **`clearPersistedCache()` only clears localStorage**
   - File: `/app/frontend/src/config/queryPersister.js`
   - Only removes `GENTURIX_QUERY_CACHE` from localStorage
   - Does NOT affect the queryClient's in-memory cache
   
3. **queryClient is defined in App.js, not accessible from AuthContext**
   - `queryClient` is created at line 50 in App.js
   - AuthContext cannot call `queryClient.clear()` directly

4. **ProfilePage fetches from cache on mount**
   - Uses `api.get('/profile')` which returns cached data
   - `useEffect` dependency on `isOwnProfile` doesn't trigger re-fetch
   - User state from AuthContext may be stale

---

## AFFECTED FILES

| File | Issue |
|------|-------|
| `/app/frontend/src/contexts/AuthContext.js` | Missing queryClient.clear() on logout |
| `/app/frontend/src/App.js` | queryClient not exported/accessible |
| `/app/frontend/src/config/queryPersister.js` | Only clears localStorage, not memory |
| `/app/frontend/src/pages/ProfilePage.js` | Uses fallback to `user` from context (stale) |

---

## DETAILED FLOW ANALYSIS

### Current (Broken) Flow:

```
User A logs in
    ↓
QueryClient caches profile A (memory + localStorage)
    ↓
User A logs out
    ↓
clearPersistedCache() → clears localStorage ✅
QueryClient in-memory cache → NOT CLEARED ❌
    ↓
User B logs in
    ↓
User B's token is set ✅
User B's user object is set in AuthContext ✅
    ↓
ProfilePage renders
    ↓
useEffect checks if `isOwnProfile` (uses new user B's id)
    ↓
api.get('/profile') called
    ↓
TanStack Query returns CACHED data (User A) because:
  - staleTime: 10 minutes
  - refetchOnMount: false
    ↓
Profile shows User A's data ❌
```

### Expected (Fixed) Flow:

```
User A logs in
    ↓
QueryClient caches profile A
    ↓
User A logs out
    ↓
clearPersistedCache() → clears localStorage ✅
queryClient.clear() → clears memory cache ✅
    ↓
User B logs in
    ↓
queryClient.invalidateQueries() → forces refetch ✅
    ↓
ProfilePage renders
    ↓
api.get('/profile') fetches FRESH data from server
    ↓
Profile shows User B's data ✅
```

---

## REQUIRED PATCH

### PATCH 1: Export queryClient from App.js

**File:** `/app/frontend/src/App.js`

```javascript
// Line 50 - Make queryClient exportable
export const queryClient = new QueryClient({...});
```

### PATCH 2: Clear queryClient on logout

**File:** `/app/frontend/src/contexts/AuthContext.js`

```javascript
// Import at top
import { queryClient } from '../App';

// In logout function (after clearPersistedCache)
queryClient.clear();
```

### PATCH 3: Invalidate queries on login

**File:** `/app/frontend/src/contexts/AuthContext.js`

```javascript
// In login function, after setting new user
import { queryClient } from '../App';

// After setUser(data.user)
queryClient.clear();  // Or more targeted: queryClient.invalidateQueries()
```

### ALTERNATIVE PATCH (Context-based approach):

Create a QueryClientContext to share queryClient:

**File:** `/app/frontend/src/contexts/QueryClientContext.js`

```javascript
import { createContext, useContext } from 'react';

const QueryClientContext = createContext(null);

export const useAppQueryClient = () => {
  const client = useContext(QueryClientContext);
  if (!client) throw new Error('QueryClientContext not found');
  return client;
};

export default QueryClientContext;
```

---

## RECOMMENDED IMPLEMENTATION

**Simplest Fix (Recommended):**

1. Export `queryClient` from `App.js`
2. Import and call `queryClient.clear()` in `AuthContext.logout()`
3. Call `queryClient.clear()` in `AuthContext.login()` after successful login

This ensures:
- All cached data is cleared on logout
- Fresh data is fetched for new user on login
- No stale data persists between user sessions

---

## TESTING CHECKLIST

After patch, verify:

- [ ] Login as User A → Profile shows User A ✅
- [ ] Logout
- [ ] Login as User B → Profile shows User B ✅
- [ ] Repeat 3+ times with different users
- [ ] Check browser DevTools → Application → localStorage is cleared
- [ ] Check React DevTools → TanStack Query has no stale data

---

## SECURITY IMPLICATIONS

This bug is a **data leak** between users:
- User B can see User A's profile information
- On shared devices, this exposes private data
- PII (name, phone, photo) is leaked

**Priority:** P0 - Must fix immediately

---

**DIAGNOSTIC COMPLETE**
