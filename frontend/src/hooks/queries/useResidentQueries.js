/**
 * GENTURIX - Resident Data Queries (TanStack Query v5)
 * 
 * Centralized data fetching hooks for Resident role.
 * Provides caching, background refetch, and optimistic updates.
 * 
 * Query Keys:
 * - ['resident', 'notifications'] - Visitor notifications
 * - ['resident', 'authorizations'] - Visitor authorizations  
 * - ['resident', 'reservations'] - User reservations
 * - ['resident', 'areas'] - Reservation areas
 * - ['resident', 'directory'] - Condominium directory
 * - ['resident', 'alerts'] - Panic alerts for resident
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../services/api';

// ============================================
// QUERY KEYS (Centralized for consistency)
// ============================================
export const residentKeys = {
  all: ['resident'],
  notifications: () => [...residentKeys.all, 'notifications'],
  authorizations: () => [...residentKeys.all, 'authorizations'],
  reservations: () => [...residentKeys.all, 'reservations'],
  areas: () => [...residentKeys.all, 'areas'],
  directory: () => [...residentKeys.all, 'directory'],
  alerts: () => [...residentKeys.all, 'alerts'],
  unreadCount: () => [...residentKeys.all, 'unreadCount'],
};

// ============================================
// NOTIFICATIONS QUERY
// ============================================
export function useResidentNotifications(options = {}) {
  return useQuery({
    queryKey: residentKeys.notifications(),
    queryFn: async () => {
      const data = await api.getVisitorNotifications();
      return data || [];
    },
    staleTime: 30_000,           // Fresh for 30s
    refetchInterval: 30_000,     // Poll every 30s (replaces setInterval)
    ...options
  });
}

// ============================================
// UNREAD COUNT QUERY
// ============================================
export function useUnreadNotificationCount(options = {}) {
  return useQuery({
    queryKey: residentKeys.unreadCount(),
    queryFn: async () => {
      const data = await api.get('/notifications/unread-count');
      return data?.count || 0;
    },
    staleTime: 30_000,
    refetchInterval: 30_000,
    ...options
  });
}

// ============================================
// AUTHORIZATIONS QUERY
// ============================================
export function useResidentAuthorizations(options = {}) {
  return useQuery({
    queryKey: residentKeys.authorizations(),
    queryFn: async () => {
      const data = await api.getMyAuthorizations();
      return data || [];
    },
    staleTime: 60_000,           // Fresh for 60s
    ...options
  });
}

// ============================================
// RESERVATIONS QUERIES
// ============================================
export function useReservationAreas(options = {}) {
  return useQuery({
    queryKey: residentKeys.areas(),
    queryFn: async () => {
      const data = await api.getReservationAreas();
      return (data || []).filter(a => a.is_active !== false);
    },
    staleTime: 5 * 60_000,        // Areas rarely change, 5 min cache
    refetchOnMount: false,        // Use cache on mount
    refetchOnWindowFocus: false,  // Don't refetch on focus
    ...options
  });
}

export function useMyReservations(options = {}) {
  return useQuery({
    queryKey: residentKeys.reservations(),
    queryFn: async () => {
      const data = await api.getReservations();
      return data || [];
    },
    staleTime: 5 * 60_000,        // Match areas cache - 5 min
    refetchOnMount: false,        // Use cache on mount
    refetchOnWindowFocus: false,  // Don't refetch on focus
    ...options
  });
}

// Combined hook for Reservations module
// Returns isFetching for background loading indicator (non-blocking)
// Returns isInitialLoading for first-time spinner (blocking)
export function useReservationsData(options = {}) {
  const areasQuery = useReservationAreas(options);
  const reservationsQuery = useMyReservations(options);
  
  // isInitialLoading = true ONLY when there's no cached data yet
  // This allows instant render from cache on subsequent visits
  const isInitialLoading = 
    (areasQuery.isPending && !areasQuery.data) || 
    (reservationsQuery.isPending && !reservationsQuery.data);
  
  return {
    areas: areasQuery.data || [],
    reservations: reservationsQuery.data || [],
    isLoading: isInitialLoading,           // For spinner on FIRST load only
    isFetching: areasQuery.isFetching || reservationsQuery.isFetching,  // For background indicator
    error: areasQuery.error || reservationsQuery.error,
    refetch: () => {
      areasQuery.refetch();
      reservationsQuery.refetch();
    }
  };
}

// ============================================
// DIRECTORY QUERY
// ============================================
export function useCondominiumDirectory(options = {}) {
  return useQuery({
    queryKey: residentKeys.directory(),
    queryFn: async () => {
      const data = await api.getCondominiumDirectory();
      return data;
    },
    staleTime: 5 * 60_000,       // Directory rarely changes
    ...options
  });
}

// ============================================
// RESIDENT ALERTS QUERY
// ============================================
export function useResidentAlerts(options = {}) {
  return useQuery({
    queryKey: residentKeys.alerts(),
    queryFn: async () => {
      const data = await api.getResidentAlerts();
      return data || [];
    },
    staleTime: 10_000,           // Alerts should be fresh
    refetchInterval: 30_000,     // Poll for new alerts
    ...options
  });
}

// ============================================
// MUTATIONS
// ============================================

// Create authorization mutation
export function useCreateAuthorization() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (authData) => api.createAuthorization(authData),
    onSuccess: () => {
      // Invalidate and refetch authorizations
      queryClient.invalidateQueries({ queryKey: residentKeys.authorizations() });
    }
  });
}

// Delete authorization mutation
export function useDeleteAuthorization() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (authId) => api.deleteAuthorization(authId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: residentKeys.authorizations() });
    }
  });
}

// Create reservation mutation
export function useCreateReservation() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (reservationData) => api.createReservation(reservationData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: residentKeys.reservations() });
    }
  });
}

// Cancel reservation mutation
export function useCancelReservation() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (reservationId) => api.cancelReservation(reservationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: residentKeys.reservations() });
    }
  });
}

// Mark notification as read mutation
export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (notificationId) => api.markNotificationRead(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: residentKeys.notifications() });
      queryClient.invalidateQueries({ queryKey: residentKeys.unreadCount() });
    }
  });
}

// Send panic alert mutation
export function useSendPanicAlert() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (panicData) => api.sendPanicAlert(panicData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: residentKeys.alerts() });
    }
  });
}
