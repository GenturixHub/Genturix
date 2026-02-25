/**
 * GENTURIX - TanStack Query Persistence Configuration
 * 
 * Persists query cache to localStorage for instant app startup.
 * 
 * PERSISTENCE RULES:
 * ✅ PERSIST: Resident modules (profile, reservations, authorizations, directory)
 * ✅ PERSIST: Static data (areas, settings)
 * ❌ DO NOT PERSIST: Guard alerts (handled via dehydrate filter in QueryClient)
 * 
 * MAX AGE: 10 minutes (600,000ms)
 * After maxAge, cache is considered stale and will refetch
 */

import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister';

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
    });
  } catch (error) {
    console.warn('[QueryPersist] Failed to create persister:', error);
    return undefined;
  }
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
