/**
 * GuardTabLock - Sistema de bloqueo para evitar audio en múltiples pestañas
 * 
 * Solo UNA pestaña puede tener el "lock" para reproducir audio de alertas.
 * Esto evita que múltiples pestañas reproduzcan el mismo sonido simultáneamente.
 * 
 * USO:
 *   import { acquireLock, releaseLock, hasLock } from './GuardTabLock';
 *   
 *   // En inicialización de GuardUI
 *   const gotLock = acquireLock();
 *   
 *   // En logout o unmount
 *   releaseLock();
 */

const LOCK_KEY = 'guard_active_tab';
const LOCK_TIMEOUT = 30000; // 30 segundos - tiempo máximo de lock

let currentTabId = null;

/**
 * Generate unique tab ID
 */
const generateTabId = () => {
  return `tab_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

/**
 * Attempt to acquire the lock for this tab
 * @returns {boolean} True if lock was acquired
 */
export const acquireLock = () => {
  try {
    const existingLock = localStorage.getItem(LOCK_KEY);
    
    if (existingLock) {
      // Check if existing lock is stale (older than LOCK_TIMEOUT)
      const lockData = JSON.parse(existingLock);
      const lockAge = Date.now() - lockData.timestamp;
      
      if (lockAge > LOCK_TIMEOUT) {
        // Lock is stale, we can take it
        currentTabId = generateTabId();
        localStorage.setItem(LOCK_KEY, JSON.stringify({
          tabId: currentTabId,
          timestamp: Date.now()
        }));
        return true;
      }
      
      // Lock is still active and belongs to another tab
      return false;
    }
    
    // No existing lock, acquire it
    currentTabId = generateTabId();
    localStorage.setItem(LOCK_KEY, JSON.stringify({
      tabId: currentTabId,
      timestamp: Date.now()
    }));
    return true;
    
  } catch (e) {
    // localStorage error, assume we can't get lock
    return false;
  }
};

/**
 * Release the lock if this tab owns it
 */
export const releaseLock = () => {
  try {
    const existingLock = localStorage.getItem(LOCK_KEY);
    
    if (existingLock) {
      const lockData = JSON.parse(existingLock);
      
      // Only release if we own the lock
      if (lockData.tabId === currentTabId) {
        localStorage.removeItem(LOCK_KEY);
      }
    }
    
    currentTabId = null;
  } catch (e) {
    // Silent error
  }
};

/**
 * Check if this tab currently has the lock
 * @returns {boolean}
 */
export const hasLock = () => {
  try {
    const existingLock = localStorage.getItem(LOCK_KEY);
    
    if (!existingLock) {
      return false;
    }
    
    const lockData = JSON.parse(existingLock);
    return lockData.tabId === currentTabId;
    
  } catch (e) {
    return false;
  }
};

/**
 * Refresh the lock timestamp (call periodically to prevent stale lock)
 */
export const refreshLock = () => {
  try {
    if (!hasLock()) return;
    
    localStorage.setItem(LOCK_KEY, JSON.stringify({
      tabId: currentTabId,
      timestamp: Date.now()
    }));
  } catch (e) {
    // Silent error
  }
};

// Auto-release lock when tab closes
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', releaseLock);
  
  // Also release on visibility change to hidden (tab closed/switched)
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
      // Don't release immediately - user might come back
      // But stop refreshing the lock
    }
  });
}

export default {
  acquireLock,
  releaseLock,
  hasLock,
  refreshLock
};
