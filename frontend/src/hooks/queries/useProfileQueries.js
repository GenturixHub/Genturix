/**
 * GENTURIX - Profile Data Queries (TanStack Query v5)
 * 
 * Centralized data fetching hooks for user profile.
 * Provides caching for instant render when navigating back to profile tab.
 * 
 * Query Keys:
 * - ['profile', 'own'] - Current user's profile
 * - ['profile', 'public', {userId}] - Public profile of another user
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../services/api';

// ============================================
// QUERY KEYS (Centralized for consistency)
// ============================================
export const profileKeys = {
  all: ['profile'],
  own: () => [...profileKeys.all, 'own'],
  public: (userId) => [...profileKeys.all, 'public', userId],
};

// ============================================
// OWN PROFILE QUERY
// ============================================
/**
 * Fetches current user's profile.
 * Uses long staleTime since profile data rarely changes.
 */
export function useOwnProfile(options = {}) {
  return useQuery({
    queryKey: profileKeys.own(),
    queryFn: async () => {
      const data = await api.get('/profile');
      return data;
    },
    staleTime: 5 * 60_000,       // Profile fresh for 5 minutes
    gcTime: 10 * 60_000,         // Keep in cache for 10 minutes
    ...options
  });
}

// ============================================
// PUBLIC PROFILE QUERY
// ============================================
/**
 * Fetches public profile of another user.
 * @param userId - The user ID to fetch
 */
export function usePublicProfile(userId, options = {}) {
  return useQuery({
    queryKey: profileKeys.public(userId),
    queryFn: async () => {
      const data = await api.getPublicProfile(userId);
      return data;
    },
    staleTime: 5 * 60_000,
    gcTime: 10 * 60_000,
    enabled: !!userId,           // Only fetch if userId is provided
    ...options
  });
}

// ============================================
// COMBINED HOOK (for EmbeddedProfile compatibility)
// ============================================
/**
 * Combined hook that fetches own profile or public profile based on userId.
 * Provides backward-compatible API for EmbeddedProfile.
 */
export function useProfile(userId = null, options = {}) {
  const isOwnProfile = !userId;
  
  const ownProfileQuery = useOwnProfile({
    ...options,
    enabled: isOwnProfile && (options.enabled !== false),
  });
  
  const publicProfileQuery = usePublicProfile(userId, {
    ...options,
    enabled: !isOwnProfile && (options.enabled !== false),
  });
  
  // Return the appropriate query based on whether viewing own or public profile
  if (isOwnProfile) {
    return {
      profile: ownProfileQuery.data,
      isLoading: ownProfileQuery.isLoading,
      error: ownProfileQuery.error,
      refetch: ownProfileQuery.refetch,
      isOwnProfile: true,
    };
  }
  
  return {
    profile: publicProfileQuery.data,
    isLoading: publicProfileQuery.isLoading,
    error: publicProfileQuery.error,
    refetch: publicProfileQuery.refetch,
    isOwnProfile: false,
  };
}

// ============================================
// MUTATIONS
// ============================================

/**
 * Update own profile mutation
 */
export function useUpdateProfile() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (formData) => api.patch('/profile', formData),
    onSuccess: (data) => {
      // Update cache with new profile data
      queryClient.setQueryData(profileKeys.own(), (old) => ({
        ...old,
        ...data,
      }));
      // Also invalidate to ensure consistency
      queryClient.invalidateQueries({ queryKey: profileKeys.own() });
    }
  });
}

/**
 * Update profile photo mutation
 */
export function useUpdateProfilePhoto() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (photoUrl) => api.patch('/profile', { profile_photo: photoUrl }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: profileKeys.own() });
    }
  });
}
