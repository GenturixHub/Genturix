import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { changeLanguage } from '../i18n';
import { clearPersistedCache } from '../config/queryPersister';

const AuthContext = createContext(undefined);

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Storage keys - SECURITY: refresh_token NO LONGER stored in localStorage (now httpOnly cookie)
const STORAGE_KEYS = {
  ACCESS_TOKEN: 'genturix_access_token',
  USER: 'genturix_user',
  PASSWORD_RESET: 'genturix_password_reset',
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [accessToken, setAccessToken] = useState(null);
  // SECURITY: refreshToken no longer stored in state - managed via httpOnly cookie
  const [isLoading, setIsLoading] = useState(true);
  const [passwordResetRequired, setPasswordResetRequired] = useState(false);

  // Initialize from localStorage and validate token
  useEffect(() => {
    const initializeAuth = async () => {
      console.log('[Auth] Initializing auth from storage...');
      
      const storedAccessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
      const storedUser = localStorage.getItem(STORAGE_KEYS.USER);
      const storedPasswordReset = localStorage.getItem(STORAGE_KEYS.PASSWORD_RESET);

      if (storedAccessToken && storedUser) {
        console.log('[Auth] Token found in storage, validating...');
        
        try {
          const parsedUser = JSON.parse(storedUser);
          
          // Validate token with backend
          const validationResponse = await fetch(`${API_URL}/api/profile`, {
            headers: {
              'Authorization': `Bearer ${storedAccessToken}`,
              'Content-Type': 'application/json',
            },
            credentials: 'include',  // SECURITY: Include httpOnly cookies
          });

          if (validationResponse.ok) {
            console.log('[Auth] Token valid, session restored');
            const profileData = await validationResponse.json();
            
            // Update user with fresh profile data
            const updatedUser = {
              ...parsedUser,
              full_name: profileData.full_name,
              phone: profileData.phone,
              profile_photo: profileData.profile_photo,
              language: profileData.language,
            };
            
            setAccessToken(storedAccessToken);
            setUser(updatedUser);
            setPasswordResetRequired(storedPasswordReset === 'true');
            
            // Update storage with fresh data
            localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(updatedUser));
            
            // Sync language
            if (profileData.language && ['es', 'en'].includes(profileData.language)) {
              await changeLanguage(profileData.language);
            }
          } else if (validationResponse.status === 401) {
            console.log('[Auth] Token expired, trying refresh via httpOnly cookie...');
            
            // Try to refresh token using httpOnly cookie
            try {
              const refreshResponse = await fetch(`${API_URL}/api/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',  // SECURITY: Send httpOnly cookie
                body: JSON.stringify({}),  // Empty body, token comes from cookie
              });

              if (refreshResponse.ok) {
                const refreshData = await refreshResponse.json();
                console.log('[Auth] Token refreshed successfully');
                
                localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, refreshData.access_token);
                
                setAccessToken(refreshData.access_token);
                setUser(parsedUser);
                setPasswordResetRequired(storedPasswordReset === 'true');
                
                // Sync language
                if (parsedUser.language && ['es', 'en'].includes(parsedUser.language)) {
                  await changeLanguage(parsedUser.language);
                }
              } else {
                console.log('[Auth] Refresh failed, clearing session');
                clearStorage();
              }
            } catch (refreshError) {
              console.error('[Auth] Refresh error:', refreshError);
              // Don't clear on network error - might be temporary
            }
          } else {
            // Other error - don't clear, might be network issue
            console.warn('[Auth] Validation error (non-401), keeping session:', validationResponse.status);
            setAccessToken(storedAccessToken);
            setUser(parsedUser);
            setPasswordResetRequired(storedPasswordReset === 'true');
          }
        } catch (e) {
          console.error('[Auth] Error during initialization:', e);
          // Network error - don't clear session, might be temporary
          try {
            const parsedUser = JSON.parse(storedUser);
            setAccessToken(storedAccessToken);
            setUser(parsedUser);
            setPasswordResetRequired(storedPasswordReset === 'true');
          } catch (parseError) {
            console.error('[Auth] Cannot parse stored user, clearing');
            clearStorage();
          }
        }
      } else {
        console.log('[Auth] No stored session found');
      }

      setIsLoading(false);
    };

    const clearStorage = () => {
      localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
      localStorage.removeItem(STORAGE_KEYS.USER);
      localStorage.removeItem(STORAGE_KEYS.PASSWORD_RESET);
    };

    initializeAuth();
  }, []);

  const login = async (email, password) => {
    const response = await fetch(`${API_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',  // SECURITY: Receive httpOnly cookie
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      let errorMessage = 'Login failed';
      try {
        const error = await response.json();
        errorMessage = error.detail || errorMessage;
      } catch (e) {}
      throw new Error(errorMessage);
    }

    const data = await response.json();
    console.log('[Auth] Login successful');
    
    // SECURITY: Only store access_token and user in localStorage
    // refresh_token is now sent as httpOnly cookie by backend
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, data.access_token);
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(data.user));
    localStorage.setItem(STORAGE_KEYS.PASSWORD_RESET, data.password_reset_required ? 'true' : 'false');

    setAccessToken(data.access_token);
    setUser(data.user);
    setPasswordResetRequired(data.password_reset_required || false);

    // Load user's language preference
    try {
      const profileResponse = await fetch(`${API_URL}/api/profile`, {
        headers: {
          'Authorization': `Bearer ${data.access_token}`,
          'Content-Type': 'application/json',
        },
      });
      if (profileResponse.ok) {
        const profileData = await profileResponse.json();
        if (profileData.language && ['es', 'en'].includes(profileData.language)) {
          await changeLanguage(profileData.language);
        }
      }
    } catch (langError) {
      console.warn('[Auth] Could not load language preference:', langError);
    }

    // === PUSH NOTIFICATIONS: Smart Sync for ALL roles ===
    // If permission already granted and subscription exists, silently sync with backend
    // This ensures push works after logout/login without re-prompting
    // NOTE: The actual sync is now handled by usePushNotifications hook
    // We just trigger a re-check here
    syncPushSubscription(data.access_token, data.user);

    return { user: data.user, passwordResetRequired: data.password_reset_required };
  };

  /**
   * Smart Push Sync - silently syncs existing subscription with backend
   * Called after successful login for ALL roles
   * 
   * IMPORTANT: This function NEVER calls:
   * - Notification.requestPermission() 
   * - pushManager.subscribe()
   * 
   * It ONLY syncs an EXISTING subscription if permission is already granted.
   * Manual activation happens ONLY in PushNotificationToggle component.
   * 
   * v2.0: Simplified - most sync logic now in usePushNotifications hook
   */
  const syncPushSubscription = async (token, userData) => {
    try {
      // Check if push is supported
      if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        console.log('[Push] Not supported in this browser');
        return;
      }

      // Log current permission state
      console.log('[Push] Permission:', Notification.permission);

      // Only sync if permission already granted - NEVER request permission here
      if (Notification.permission !== 'granted') {
        console.log('[Push] Permission not granted - user can activate manually from profile');
        return;
      }

      // Await service worker
      const registration = await navigator.serviceWorker.ready;
      
      // Get existing subscription - DO NOT create new one
      const existingSubscription = await registration.pushManager.getSubscription();
      
      // Log subscription state
      console.log('[Push] Existing subscription:', !!existingSubscription);

      if (!existingSubscription) {
        console.log('[Push] No existing subscription - user can activate manually from profile');
        return;
      }

      // Silently sync existing subscription with backend
      console.log(`[Push] Syncing existing subscription for role: ${userData?.roles?.join(', ')}`);
      
      const subscriptionJson = existingSubscription.toJSON();
      const response = await fetch(`${API_URL}/api/push/subscribe`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          endpoint: subscriptionJson.endpoint,
          keys: {
            p256dh: subscriptionJson.keys.p256dh,
            auth: subscriptionJson.keys.auth,
          },
          expirationTime: subscriptionJson.expirationTime,
        }),
      });

      if (response.ok) {
        console.log(`[Push] Subscription synced successfully for: ${userData?.roles?.join(', ')}`);
        // NOTE: Removed localStorage.setItem('genturix_push_enabled', 'true')
        // The hook now manages state based on backend verification
      } else {
        console.warn('[Push] Failed to sync subscription:', response.status);
      }
    } catch (error) {
      console.error('[Push] Error syncing subscription:', error);
    }
  };

  // Helper: Convert VAPID key (used by PushNotificationToggle)
  const urlBase64ToUint8Array = (base64String) => {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  };

  const changePassword = async (currentPassword, newPassword, confirmPassword = null) => {
    if (!accessToken) throw new Error('Not authenticated');
    
    // If confirmPassword not provided, use newPassword (for forced reset flow)
    const confirmPwd = confirmPassword || newPassword;
    
    const response = await fetch(`${API_URL}/api/auth/change-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPwd,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      
      // Handle Pydantic validation errors (array format)
      let errorMessage = 'Password change failed';
      
      if (Array.isArray(errorData.detail)) {
        // Pydantic returns an array of validation errors
        errorMessage = errorData.detail[0]?.msg || errorData.detail[0]?.message || 'Error de validación';
      } else if (typeof errorData.detail === 'string') {
        errorMessage = errorData.detail;
      } else if (errorData.message) {
        errorMessage = errorData.message;
      } else if (errorData.error) {
        errorMessage = errorData.error;
      }
      
      const error = new Error(errorMessage);
      error.data = errorData;
      throw error;
    }

    setPasswordResetRequired(false);
    localStorage.setItem(STORAGE_KEYS.PASSWORD_RESET, 'false');
    
    if (user) {
      const updatedUser = { ...user, password_reset_required: false };
      setUser(updatedUser);
      localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(updatedUser));
    }

    return await response.json();
  };

  const register = async (email, password, fullName, roles = ['Residente']) => {
    const response = await fetch(`${API_URL}/api/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        password,
        full_name: fullName,
        roles,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Registration failed');
    }

    return await response.json();
  };

  const logout = useCallback(async () => {
    console.log('[Auth] Manual logout');
    
    try {
      if (accessToken) {
        // IMPORTANT: Push notifications are NOT session-based
        // We do NOT unsubscribe from push on logout
        // Push is tied to the device, not the session
        // User can manually disable push in their profile settings
        
        // Call logout endpoint to invalidate refresh token and clear httpOnly cookie
        await fetch(`${API_URL}/api/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${accessToken}`,
          },
          credentials: 'include',  // SECURITY: Clear httpOnly cookie
        });
        console.log('[Auth] Logout API called');
      }
    } catch (error) {
      console.error('[Auth] Logout API error:', error);
    } finally {
      // Clear local auth state only (not push subscription)
      localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
      localStorage.removeItem(STORAGE_KEYS.USER);
      localStorage.removeItem(STORAGE_KEYS.PASSWORD_RESET);
      
      // SECURITY: Clear TanStack Query persisted cache on logout
      // This prevents data leakage between users on shared devices
      clearPersistedCache();
      
      setUser(null);
      setAccessToken(null);
      setPasswordResetRequired(false);
      
      console.log('[Auth] Logout complete - push subscription preserved');
    }
  }, [accessToken]);

  const refreshAccessToken = useCallback(async () => {
    console.log('[Auth] Refreshing access token via httpOnly cookie...');
    
    const response = await fetch(`${API_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',  // SECURITY: Send httpOnly cookie
      body: JSON.stringify({}),  // Empty body, token comes from cookie
    });

    if (!response.ok) {
      console.log('[Auth] Token refresh failed, logging out');
      await logout();
      throw new Error('Token refresh failed');
    }

    const data = await response.json();
    console.log('[Auth] Token refreshed successfully');
    
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, data.access_token);

    setAccessToken(data.access_token);

    return data.access_token;
  }, [logout]);

  const hasRole = useCallback((role) => {
    return user?.roles?.includes(role) || false;
  }, [user]);

  const hasAnyRole = useCallback((...roles) => {
    return user?.roles?.some(userRole => roles.includes(userRole)) || false;
  }, [user]);

  const refreshUser = useCallback(async () => {
    if (!accessToken) return;
    
    try {
      const response = await fetch(`${API_URL}/api/profile`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const profileData = await response.json();
        const updatedUser = {
          ...user,
          full_name: profileData.full_name,
          phone: profileData.phone,
          profile_photo: profileData.profile_photo,
          public_description: profileData.public_description,
          role_data: profileData.role_data,
          language: profileData.language,
        };
        setUser(updatedUser);
        localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(updatedUser));
        
        if (profileData.language && ['es', 'en'].includes(profileData.language)) {
          await changeLanguage(profileData.language);
        }
      }
    } catch (error) {
      console.error('[Auth] Error refreshing user:', error);
    }
  }, [accessToken, user]);

  const value = {
    user,
    accessToken,
    // SECURITY: refreshToken removed - now managed via httpOnly cookie
    isLoading,
    isAuthenticated: !!user && !!accessToken,
    passwordResetRequired,
    login,
    logout,
    register,
    changePassword,
    refreshAccessToken,
    refreshUser,
    hasRole,
    hasAnyRole,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
