import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { changeLanguage } from '../i18n';

const AuthContext = createContext(undefined);

const API_URL = process.env.REACT_APP_BACKEND_URL;

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [accessToken, setAccessToken] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [passwordResetRequired, setPasswordResetRequired] = useState(false);

  useEffect(() => {
    const storedAccessToken = sessionStorage.getItem('accessToken');
    const storedRefreshToken = sessionStorage.getItem('refreshToken');
    const storedUser = sessionStorage.getItem('user');
    const storedPasswordReset = sessionStorage.getItem('passwordResetRequired');

    if (storedAccessToken && storedUser) {
      setAccessToken(storedAccessToken);
      setRefreshToken(storedRefreshToken);
      try {
        setUser(JSON.parse(storedUser));
        setPasswordResetRequired(storedPasswordReset === 'true');
      } catch (e) {
        console.error('Error parsing stored user:', e);
      }
    }

    setIsLoading(false);
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
      } catch (e) {
        // Response body may already be consumed
      }
      throw new Error(errorMessage);
    }

    const data = await response.json();
    
    sessionStorage.setItem('accessToken', data.access_token);
    sessionStorage.setItem('refreshToken', data.refresh_token);
    sessionStorage.setItem('user', JSON.stringify(data.user));
    sessionStorage.setItem('passwordResetRequired', data.password_reset_required ? 'true' : 'false');

    setAccessToken(data.access_token);
    setRefreshToken(data.refresh_token);
    setUser(data.user);
    setPasswordResetRequired(data.password_reset_required || false);

    return { user: data.user, passwordResetRequired: data.password_reset_required };
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

    // Clear password reset flag
    setPasswordResetRequired(false);
    sessionStorage.setItem('passwordResetRequired', 'false');
    
    // Update user object
    if (user) {
      const updatedUser = { ...user, password_reset_required: false };
      setUser(updatedUser);
      sessionStorage.setItem('user', JSON.stringify(updatedUser));
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
    try {
      if (accessToken) {
        await fetch(`${API_URL}/api/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${accessToken}`,
          },
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      sessionStorage.removeItem('accessToken');
      sessionStorage.removeItem('refreshToken');
      sessionStorage.removeItem('user');
      sessionStorage.removeItem('passwordResetRequired');
      
      setUser(null);
      setAccessToken(null);
      setRefreshToken(null);
      setPasswordResetRequired(false);
    }
  }, [accessToken]);

  const refreshAccessToken = useCallback(async () => {
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await fetch(`${API_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      await logout();
      throw new Error('Token refresh failed');
    }

    const data = await response.json();
    
    sessionStorage.setItem('accessToken', data.access_token);
    sessionStorage.setItem('refreshToken', data.refresh_token);

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

  // Refresh user data from server (after profile updates)
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
        // Merge profile data with existing user data
        const updatedUser = {
          ...user,
          full_name: profileData.full_name,
          phone: profileData.phone,
          profile_photo: profileData.profile_photo,
          public_description: profileData.public_description,
          role_data: profileData.role_data,
        };
        setUser(updatedUser);
        sessionStorage.setItem('user', JSON.stringify(updatedUser));
      }
    } catch (error) {
      console.error('Error refreshing user:', error);
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
