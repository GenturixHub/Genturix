/**
 * GENTURIX - Guard Data Queries (TanStack Query v5)
 * 
 * Centralized data fetching hooks for Guard role.
 * Provides caching, background refetch, and optimistic updates.
 * 
 * ARQUITECTURA DE POLLING:
 * - Alertas/Pánico: refetchInterval 5s (crítico, tiempo real)
 * - Clock Status: staleTime 15s, refetch on demand
 * - Datos estáticos (turnos, historial): staleTime 60s+
 * 
 * Query Keys:
 * - ['guard', 'alerts'] - Panic events / alerts
 * - ['guard', 'clockStatus'] - Guard clock in/out status
 * - ['guard', 'visitorEntries'] - Visitor entries (pending, inside, exits)
 * - ['guard', 'shift'] - Guard shift data
 * - ['guard', 'absences'] - Guard absences
 * - ['guard', 'history'] - Guard activity history
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../services/api';

// ============================================
// QUERY KEYS (Centralized for consistency)
// ============================================
export const guardKeys = {
  all: ['guard'],
  alerts: () => [...guardKeys.all, 'alerts'],
  clockStatus: () => [...guardKeys.all, 'clockStatus'],
  visitorEntries: () => [...guardKeys.all, 'visitorEntries'],
  shift: () => [...guardKeys.all, 'shift'],
  absences: () => [...guardKeys.all, 'absences'],
  history: (filter) => [...guardKeys.all, 'history', filter],
};

// ============================================
// ALERTS / PANIC EVENTS QUERY (CRITICAL - Real-time)
// ============================================
/**
 * Panic alerts query - This is the ONLY query with aggressive polling.
 * Guards need to see alerts in near real-time.
 * 
 * @param options - Additional query options
 * @param options.enabled - Enable/disable polling (default: true)
 */
export function useGuardAlerts(options = {}) {
  return useQuery({
    queryKey: guardKeys.alerts(),
    queryFn: async () => {
      const events = await api.getPanicEvents();
      return events || [];
    },
    staleTime: 5_000,            // Data fresh for 5s
    refetchInterval: 5_000,      // Poll every 5s (ONLY for alerts - critical)
    refetchIntervalInBackground: true, // Keep polling even when tab is not focused
    ...options
  });
}

// ============================================
// CLOCK STATUS QUERY
// ============================================
/**
 * Clock status - Shows if guard is clocked in/out.
 * Not as time-critical, uses staleTime instead of aggressive polling.
 */
export function useGuardClockStatus(options = {}) {
  return useQuery({
    queryKey: guardKeys.clockStatus(),
    queryFn: async () => {
      const status = await api.getClockStatus();
      return status;
    },
    staleTime: 15_000,           // Fresh for 15s
    // NO refetchInterval - refetch on demand or when stale
    ...options
  });
}

// ============================================
// VISITOR ENTRIES QUERY
// ============================================
/**
 * Visitor entries - pending check-ins, inside visitors, recent exits.
 * Moderate refresh rate, not as critical as alerts.
 */
export function useGuardVisitorEntries(options = {}) {
  return useQuery({
    queryKey: guardKeys.visitorEntries(),
    queryFn: async () => {
      const result = await api.getVisitsSummary();
      return result || { pending: [], inside: [], exits: [] };
    },
    staleTime: 30_000,           // Fresh for 30s
    refetchInterval: 60_000,     // Light polling every 60s for background updates
    ...options
  });
}

// ============================================
// SHIFT DATA QUERY
// ============================================
/**
 * Guard shift data - Rarely changes during a session.
 */
export function useGuardShift(options = {}) {
  return useQuery({
    queryKey: guardKeys.shift(),
    queryFn: async () => {
      const shift = await api.getGuardMyShift();
      return shift;
    },
    staleTime: 5 * 60_000,       // Fresh for 5 minutes
    // NO refetchInterval - shift data is static
    ...options
  });
}

// ============================================
// ABSENCES QUERY
// ============================================
/**
 * Guard absences - Historical data, rarely changes.
 */
export function useGuardAbsences(options = {}) {
  return useQuery({
    queryKey: guardKeys.absences(),
    queryFn: async () => {
      const absences = await api.getGuardMyAbsences();
      return absences || [];
    },
    staleTime: 60_000,           // Fresh for 60s
    // NO refetchInterval
    ...options
  });
}

// ============================================
// COMBINED SHIFT + ABSENCES (for ShiftInfoModule)
// ============================================
export function useGuardShiftData(options = {}) {
  const shiftQuery = useGuardShift(options);
  const absencesQuery = useGuardAbsences(options);
  
  return {
    shiftData: shiftQuery.data,
    absences: absencesQuery.data || [],
    isLoading: shiftQuery.isLoading || absencesQuery.isLoading,
    error: shiftQuery.error || absencesQuery.error,
    refetch: () => {
      shiftQuery.refetch();
      absencesQuery.refetch();
    }
  };
}

// ============================================
// HISTORY QUERY
// ============================================
/**
 * Guard activity history - Historical data, changes rarely.
 */
export function useGuardHistory(filter = 'today', options = {}) {
  return useQuery({
    queryKey: guardKeys.history(filter),
    queryFn: async () => {
      const history = await api.getGuardHistory();
      return history || [];
    },
    staleTime: 60_000,           // Fresh for 60s
    // NO refetchInterval - historical data
    ...options
  });
}

// ============================================
// MUTATIONS
// ============================================

/**
 * Resolve panic alert mutation
 */
export function useResolveAlert() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ alertId, notes }) => api.resolveAlert(alertId, notes),
    onSuccess: () => {
      // Invalidate alerts to refetch updated list
      queryClient.invalidateQueries({ queryKey: guardKeys.alerts() });
    }
  });
}

/**
 * Clock in/out mutation
 */
export function useClockInOut() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (action) => {
      if (action === 'in') {
        return api.clockIn();
      } else {
        return api.clockOut();
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: guardKeys.clockStatus() });
    }
  });
}

/**
 * Guard check-in visitor mutation
 */
export function useGuardCheckIn() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (checkInData) => api.guardCheckIn(checkInData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: guardKeys.visitorEntries() });
    }
  });
}

/**
 * Guard check-out visitor mutation
 */
export function useGuardCheckOut() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (entryId) => api.guardCheckOut(entryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: guardKeys.visitorEntries() });
    }
  });
}

/**
 * Create absence request mutation
 */
export function useCreateAbsence() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (absenceData) => api.createAbsence(absenceData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: guardKeys.absences() });
    }
  });
}

// ============================================
// UTILITY HOOKS
// ============================================

/**
 * Prefetch alerts - useful for preloading data
 */
export function usePrefetchGuardAlerts() {
  const queryClient = useQueryClient();
  
  return () => {
    queryClient.prefetchQuery({
      queryKey: guardKeys.alerts(),
      queryFn: () => api.getPanicEvents(),
      staleTime: 5_000
    });
  };
}

/**
 * Manual refetch all guard data
 */
export function useRefreshGuardData() {
  const queryClient = useQueryClient();
  
  return () => {
    queryClient.invalidateQueries({ queryKey: guardKeys.all });
  };
}
