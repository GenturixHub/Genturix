/**
 * GENTURIX - TanStack Query Persistence Configuration
 * 
 * Persists query cache to localStorage for instant app startup.
 * Excludes critical real-time data (Guard alerts) from persistence.
 * 
 * PERSISTENCE RULES:
 * ✅ PERSIST: Resident modules (profile, reservations, authorizations, directory)
 * ✅ PERSIST: Static data (areas, settings)
 * ❌ DO NOT PERSIST: Guard alerts (real-time critical data)
 * ❌ DO NOT PERSIST: Clock status (must be fresh)
 * ❌ DO NOT PERSIST: Mutations (only queries)
 * 
 * MAX AGE: 10 minutes (600,000ms)
 * After maxAge, cache is considered stale and will refetch
 */

import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister';

// Keys that should NOT be persisted (real-time critical data)
const NON_PERSISTENT_KEYS = [
  'guard',           // All guard queries (alerts are critical)
  'clockStatus',     // Must always be fresh
  'alerts',          // Real-time alerts
  'unreadCount',     // Should reflect current state
];

/**
 * Check if a query should be persisted
 * @param {Object} query - The query object
 * @returns {boolean} - Whether to persist
 */
const shouldPersistQuery = (query) => {
  const queryKey = query.queryKey;
  
  // Don't persist if queryKey is empty or invalid
  if (!queryKey || !Array.isArray(queryKey) || queryKey.length === 0) {
    return false;
  }
  
  // Check if any part of the key matches non-persistent keys
  const keyString = queryKey.join('.');
  for (const nonPersistKey of NON_PERSISTENT_KEYS) {
    if (keyString.includes(nonPersistKey)) {
      return false;
    }
  }
  
  // Only persist successful queries with data
  if (query.state.status !== 'success' || !query.state.data) {
    return false;
  }
  
  return true;
};

/**
 * Create localStorage persister for TanStack Query
 * Uses synchronous storage for optimal performance
 */
export const createQueryPersister = () => {
  // Check if localStorage is available
  if (typeof window === 'undefined' || !window.localStorage) {
    console.warn('[QueryPersist] localStorage not available, skipping persistence');
    return null;
  }
  
  try {
    return createSyncStoragePersister({
      storage: window.localStorage,
      key: 'GENTURIX_QUERY_CACHE',
      // Serialize with filtering
      serialize: (client) => {
        // Filter out non-persistent queries before serializing
        const filteredClient = {
          ...client,
          clientState: {
            ...client.clientState,
            queries: client.clientState.queries.filter(shouldPersistQuery),
          },
        };
        return JSON.stringify(filteredClient);
      },
      deserialize: (cachedString) => {
        return JSON.parse(cachedString);
      },
    });
  } catch (error) {
    console.warn('[QueryPersist] Failed to create persister:', error);
    return null;
  }
};

/**
 * Persistence options for PersistQueryClientProvider
 */
export const persistOptions = {
  maxAge: 10 * 60 * 1000, // 10 minutes in milliseconds
  buster: 'v1',           // Cache buster - increment to invalidate all cached data
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
