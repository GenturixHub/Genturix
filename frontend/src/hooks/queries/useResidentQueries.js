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
import { useAuth } from '../../contexts/AuthContext';

// ============================================
// QUERY KEYS (Centralized for consistency)
// User-scoped to prevent identity collision
// ============================================
export const residentKeys = {
  all: ['resident'],
  // User-scoped keys to prevent data leak between users
  notifications: (userId) => [...residentKeys.all, 'notifications', userId],
  authorizations: (userId) => [...residentKeys.all, 'authorizations', userId],
  reservations: (userId) => [...residentKeys.all, 'reservations', userId],
  areas: (condoId) => [...residentKeys.all, 'areas', condoId],
  directory: (condoId) => [...residentKeys.all, 'directory', condoId],
  alerts: (userId) => [...residentKeys.all, 'alerts', userId],
  unreadCount: (userId) => [...residentKeys.all, 'unreadCount', userId],
};

// ============================================
// NOTIFICATIONS QUERY
// ============================================
export function useResidentNotifications(options = {}) {
  const { user } = useAuth();
  const userId = user?.id;
  
  return useQuery({
    queryKey: residentKeys.notifications(userId),
    queryFn: async () => {
      const data = await api.getVisitorNotifications();
      return data || [];
    },
    staleTime: 30_000,           // Fresh for 30s
    refetchInterval: 30_000,     // Poll every 30s (replaces setInterval)
    enabled: !!userId,           // Only fetch when user is logged in
    ...options
  });
}

// ============================================
// UNREAD COUNT QUERY
// ============================================
export function useUnreadNotificationCount(options = {}) {
  const { user } = useAuth();
  const userId = user?.id;
  
  return useQuery({
    queryKey: residentKeys.unreadCount(userId),
    queryFn: async () => {
      // Use the correct resident-specific endpoint
      const data = await api.get('/resident/visitor-notifications/unread-count');
      return data?.count || 0;
    },
    staleTime: 30_000,
    refetchInterval: 30_000,
    enabled: !!userId,
    ...options
  });
}

// ============================================
// AUTHORIZATIONS QUERY
// ============================================
export function useResidentAuthorizations(options = {}) {
  const { user } = useAuth();
  const userId = user?.id;
  
  return useQuery({
    queryKey: residentKeys.authorizations(userId),
    queryFn: async () => {
      const data = await api.getMyAuthorizations();
      return data || [];
    },
    staleTime: 60_000,           // Fresh for 60s
    enabled: !!userId,
    ...options
  });
}

// ============================================
// RESERVATIONS QUERIES
// ============================================
export function useReservationAreas(options = {}) {
  const { user } = useAuth();
  const condoId = user?.condominium_id;
  
  return useQuery({
    queryKey: residentKeys.areas(condoId),
    queryFn: async () => {
      const data = await api.getReservationAreas();
      return (data || []).filter(a => a.is_active !== false);
    },
    staleTime: 5 * 60_000,        // Areas rarely change, 5 min cache
    refetchOnMount: false,        // Use cache on mount
    refetchOnWindowFocus: false,  // Don't refetch on focus
    enabled: !!condoId,
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

// Delete authorization mutation with optimistic update
export function useDeleteAuthorization() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (authId) => api.deleteAuthorization(authId),
    
    // Optimistic update - remove item immediately from UI
    onMutate: async (authId) => {
      // Cancel ALL related queries to prevent stale data from overwriting
      await queryClient.cancelQueries({ queryKey: residentKeys.all });
      
      // Snapshot the previous value
      const previousAuthorizations = queryClient.getQueryData(residentKeys.authorizations());
      
      // Optimistically update: remove the deleted item
      queryClient.setQueryData(residentKeys.authorizations(), (old) => {
        if (!old) return old;
        return old.filter(auth => auth.id !== authId);
      });
      
      // Return context with the snapshotted value
      return { previousAuthorizations, deletedId: authId };
    },
    
    // On success: DON'T invalidate immediately - keep the optimistic state
    onSuccess: (data, authId, context) => {
      // The item is already removed from cache in onMutate
      // Only invalidate notifications (not authorizations!)
      queryClient.invalidateQueries({ queryKey: residentKeys.notifications() });
    },
    
    // If mutation fails, rollback to previous state
    onError: (err, authId, context) => {
      if (context?.previousAuthorizations) {
        queryClient.setQueryData(residentKeys.authorizations(), context.previousAuthorizations);
      }
    }
    
    // Removed onSettled to prevent immediate refetch that would bring back deleted item
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
