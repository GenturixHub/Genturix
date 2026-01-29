/**
 * GENTURIX - Condominium Modules Context
 * Provides module availability based on condominium configuration
 * Used to hide/show modules in navigation and validate access
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';

const ModulesContext = createContext(undefined);

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Map of module IDs to their navigation paths
const MODULE_PATHS = {
  security: ['/security'],
  hr: ['/rrhh', '/hr'],
  school: ['/school', '/student'],
  payments: ['/payments'],
  audit: ['/audit'],
  reservations: ['/reservations'],
  access_control: ['/access-control'],
  messaging: ['/messaging'],
};

export const ModulesProvider = ({ children }) => {
  const { user, accessToken, isAuthenticated } = useAuth();
  const [modules, setModules] = useState(null);
  const [condominiumName, setCondominiumName] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch condominium modules
  const fetchModules = useCallback(async () => {
    if (!isAuthenticated || !accessToken) {
      setModules(null);
      setIsLoading(false);
      return;
    }

    // SuperAdmin without condominium sees all modules
    if (user?.roles?.includes('SuperAdmin') && !user?.condominium_id) {
      setModules({
        security: { enabled: true },
        hr: { enabled: true },
        school: { enabled: true },
        payments: { enabled: true },
        audit: { enabled: true },
        reservations: { enabled: true },
        access_control: { enabled: true },
        messaging: { enabled: true },
      });
      setIsLoading(false);
      return;
    }

    // Fetch condominium data for regular users
    if (!user?.condominium_id) {
      setModules(null);
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/condominiums/${user.condominium_id}`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setModules(data.modules || {});
        setCondominiumName(data.name);
      } else {
        // Default to all enabled if can't fetch
        console.warn('Could not fetch condominium modules, defaulting to all enabled');
        setModules({});
      }
    } catch (error) {
      console.error('Error fetching modules:', error);
      setModules({});
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, accessToken, user?.condominium_id, user?.roles]);

  useEffect(() => {
    fetchModules();
  }, [fetchModules]);

  // Check if a specific module is enabled
  const isModuleEnabled = useCallback((moduleId) => {
    if (!modules) return true; // Default to enabled if no config
    const moduleConfig = modules[moduleId];
    return moduleConfig?.enabled !== false; // Default to true if not explicitly disabled
  }, [modules]);

  // Check if a path should be accessible based on module config
  const isPathEnabled = useCallback((path) => {
    if (!modules) return true;
    
    // Find which module this path belongs to
    for (const [moduleId, paths] of Object.entries(MODULE_PATHS)) {
      if (paths.some(p => path.startsWith(p))) {
        return isModuleEnabled(moduleId);
      }
    }
    
    // Paths not mapped to modules are always enabled
    return true;
  }, [modules, isModuleEnabled]);

  // Get all enabled modules
  const getEnabledModules = useCallback(() => {
    if (!modules) return [];
    return Object.entries(modules)
      .filter(([_, config]) => config?.enabled !== false)
      .map(([id]) => id);
  }, [modules]);

  // Get all disabled modules
  const getDisabledModules = useCallback(() => {
    if (!modules) return [];
    return Object.entries(modules)
      .filter(([_, config]) => config?.enabled === false)
      .map(([id]) => id);
  }, [modules]);

  const value = {
    modules,
    condominiumName,
    isLoading,
    isModuleEnabled,
    isPathEnabled,
    getEnabledModules,
    getDisabledModules,
    refreshModules: fetchModules,
  };

  return (
    <ModulesContext.Provider value={value}>
      {children}
    </ModulesContext.Provider>
  );
};

export const useModules = () => {
  const context = useContext(ModulesContext);
  if (context === undefined) {
    throw new Error('useModules must be used within a ModulesProvider');
  }
  return context;
};

export default ModulesContext;
