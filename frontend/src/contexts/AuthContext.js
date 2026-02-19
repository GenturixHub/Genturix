import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { changeLanguage } from '../i18n';

const AuthContext = createContext(undefined);

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Storage keys
const STORAGE_KEYS = {
  ACCESS_TOKEN: 'genturix_access_token',
  REFRESH_TOKEN: 'genturix_refresh_token',
  USER: 'genturix_user',
  PASSWORD_RESET: 'genturix_password_reset',
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [accessToken, setAccessToken] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [passwordResetRequired, setPasswordResetRequired] = useState(false);

  // Initialize from localStorage and validate token
  useEffect(() => {
    const initializeAuth = async () => {
      console.log('[Auth] Initializing auth from storage...');
      
      const storedAccessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
      const storedRefreshToken = localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
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
            setRefreshToken(storedRefreshToken);
            setUser(updatedUser);
            setPasswordResetRequired(storedPasswordReset === 'true');
            
            // Update storage with fresh data
            localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(updatedUser));
            
            // Sync language
            if (profileData.language && ['es', 'en'].includes(profileData.language)) {
              await changeLanguage(profileData.language);
            }
          } else if (validationResponse.status === 401) {
            console.log('[Auth] Token expired, trying refresh...');
            
            // Try to refresh token
            if (storedRefreshToken) {
              try {
                const refreshResponse = await fetch(`${API_URL}/api/auth/refresh`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ refresh_token: storedRefreshToken }),
                });

                if (refreshResponse.ok) {
                  const refreshData = await refreshResponse.json();
                  console.log('[Auth] Token refreshed successfully');
                  
                  localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, refreshData.access_token);
                  localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshData.refresh_token);
                  
                  setAccessToken(refreshData.access_token);
                  setRefreshToken(refreshData.refresh_token);
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
              console.log('[Auth] No refresh token, clearing session');
              clearStorage();
            }
          } else {
            // Other error - don't clear, might be network issue
            console.warn('[Auth] Validation error (non-401), keeping session:', validationResponse.status);
            setAccessToken(storedAccessToken);
            setRefreshToken(storedRefreshToken);
            setUser(parsedUser);
            setPasswordResetRequired(storedPasswordReset === 'true');
          }
        } catch (e) {
          console.error('[Auth] Error during initialization:', e);
          // Network error - don't clear session, might be temporary
          try {
            const parsedUser = JSON.parse(storedUser);
            setAccessToken(storedAccessToken);
            setRefreshToken(storedRefreshToken);
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
      localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
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
    
    // Store in localStorage for persistence
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, data.access_token);
    localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, data.refresh_token);
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(data.user));
    localStorage.setItem(STORAGE_KEYS.PASSWORD_RESET, data.password_reset_required ? 'true' : 'false');

    setAccessToken(data.access_token);
    setRefreshToken(data.refresh_token);
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

    // === PUSH NOTIFICATIONS: Only for Guards ===
    const userRoles = data.user?.roles || [];
    const isGuard = userRoles.includes('Guarda') || userRoles.includes('Guardia');
    
    if (isGuard) {
      console.log('[Auth] User is Guard - registering push subscription');
      registerPushForGuard(data.access_token);
    } else {
      console.log('[Auth] User is not Guard - skipping push registration');
    }

    return { user: data.user, passwordResetRequired: data.password_reset_required };
  };

  /**
   * Register push subscription for Guards only
   * Called after successful login if user is a Guard
   */
  const registerPushForGuard = async (token) => {
    try {
      // Check if push is supported
      if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        console.log('[Push] Not supported in this browser');
        return;
      }

      // Check if permission already granted - don't prompt repeatedly
      if (Notification.permission === 'denied') {
        console.log('[Push] Permission denied - not prompting');
        return;
      }

      // Only request permission if not already granted
      if (Notification.permission !== 'granted') {
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
          console.log('[Push] Permission not granted');
          return;
        }
      }

      // Get VAPID key from backend
      const configResponse = await fetch(`${API_URL}/api/config/vapid`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!configResponse.ok) {
        console.warn('[Push] Could not get VAPID key');
        return;
      }
      
      const { vapid_public_key } = await configResponse.json();
      if (!vapid_public_key) {
        console.warn('[Push] No VAPID key configured');
        return;
      }

      // Get service worker registration
      const registration = await navigator.serviceWorker.ready;
      
      // Check for existing subscription
      let subscription = await registration.pushManager.getSubscription();
      
      if (!subscription) {
        // Create new subscription
        const applicationServerKey = urlBase64ToUint8Array(vapid_public_key);
        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey
        });
        console.log('[Push] New subscription created');
      } else {
        console.log('[Push] Existing subscription found');
      }

      // Send subscription to backend
      const subData = formatSubscription(subscription);
      await fetch(`${API_URL}/api/push/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ subscription: subData })
      });
      
      console.log('[Push] Subscription registered with backend');
    } catch (error) {
      console.warn('[Push] Registration failed:', error);
    }
  };

  // Helper: Convert VAPID key
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

  // Helper: Format subscription for API
  const formatSubscription = (subscription) => {
    const key = subscription.getKey('p256dh');
    const auth = subscription.getKey('auth');
    return {
      endpoint: subscription.endpoint,
      keys: {
        p256dh: key ? btoa(String.fromCharCode.apply(null, new Uint8Array(key))) : '',
        auth: auth ? btoa(String.fromCharCode.apply(null, new Uint8Array(auth))) : ''
      }
    };
  };

  const changePassword = async (currentPassword, newPassword) => {
    if (!accessToken) throw new Error('Not authenticated');
    
    const response = await fetch(`${API_URL}/api/auth/change-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Password change failed');
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
        
        // Call logout endpoint to invalidate refresh token
        await fetch(`${API_URL}/api/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${accessToken}`,
          },
        });
        console.log('[Auth] Logout API called');
      }
    } catch (error) {
      console.error('[Auth] Logout API error:', error);
    } finally {
      // Clear local auth state only (not push subscription)
      localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
      localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
      localStorage.removeItem(STORAGE_KEYS.USER);
      localStorage.removeItem(STORAGE_KEYS.PASSWORD_RESET);
      
      setUser(null);
      setAccessToken(null);
      setRefreshToken(null);
      setPasswordResetRequired(false);
      
      console.log('[Auth] Logout complete - push subscription preserved');
    }
  }, [accessToken]);

  const refreshAccessToken = useCallback(async () => {
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    console.log('[Auth] Refreshing access token...');
    
    const response = await fetch(`${API_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      console.log('[Auth] Token refresh failed, logging out');
      await logout();
      throw new Error('Token refresh failed');
    }

    const data = await response.json();
    console.log('[Auth] Token refreshed successfully');
    
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, data.access_token);
    localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, data.refresh_token);

    setAccessToken(data.access_token);
    setRefreshToken(data.refresh_token);

    return data.access_token;
  }, [refreshToken, logout]);

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
    refreshToken,
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
