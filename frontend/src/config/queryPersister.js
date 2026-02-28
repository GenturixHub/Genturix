/**
 * GENTURIX - TanStack Query Persistence Configuration
 * 
 * Persists query cache to localStorage for instant app startup.
 * Behaves like a native app - loads cached data instantly, refetches in background.
 * 
 * PERSISTENCE RULES:
 * ✅ PERSIST: Resident modules (profile, reservations, authorizations, directory)
 * ✅ PERSIST: Static data (areas, settings)
 * ❌ DO NOT PERSIST: Guard alerts (handled via dehydrate filter in QueryClient)
 * 
 * MAX AGE: 7 days (604,800,000ms)
 * Cache survives reloads and days offline.
 */

import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister';

// 7 days in milliseconds
export const CACHE_MAX_AGE = 7 * 24 * 60 * 60 * 1000;

/**
 * Create localStorage persister for TanStack Query
 * Uses synchronous storage for optimal performance
 */
export const createQueryPersister = () => {
  // Check if localStorage is available (SSR safety)
  if (typeof window === 'undefined' || !window.localStorage) {
    console.warn('[QueryPersist] localStorage not available');
    return undefined;
  }
  
  try {
    return createSyncStoragePersister({
      storage: window.localStorage,
      key: 'GENTURIX_QUERY_CACHE',
      throttleTime: 1000, // Throttle writes to localStorage
    });
  } catch (error) {
    console.warn('[QueryPersist] Failed to create persister:', error);
    return undefined;
  }
};

/**
 * Persist options for PersistQueryClientProvider
 */
export const persistOptions = {
  maxAge: CACHE_MAX_AGE,
  buster: 'v2', // Change this to invalidate all cached data
};

/**
 * Clear persisted cache manually (for logout, errors, etc.)
 */
export const clearPersistedCache = () => {
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      window.localStorage.removeItem('GENTURIX_QUERY_CACHE');
      console.log('[QueryPersist] Cache cleared');
    } catch (error) {
      console.warn('[QueryPersist] Failed to clear cache:', error);
    }
  }
};

export default createQueryPersister;
