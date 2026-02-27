import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";

// Initialize i18n
import './i18n';

// ==================== SERVICE WORKER REGISTRATION ====================
// Handles registration with forced update check after domain migration
const registerServiceWorker = async () => {
  if (!('serviceWorker' in navigator)) {
    console.log('[SW] Service Workers not supported');
    return null;
  }

  try {
    // First, unregister any old service workers from different scopes
    const registrations = await navigator.serviceWorker.getRegistrations();
    for (const registration of registrations) {
      // Check if this is an old registration we should clean up
      if (registration.scope !== `${window.location.origin}/`) {
        console.log('[SW] Unregistering old SW from scope:', registration.scope);
        await registration.unregister();
      }
    }

    // Register our service worker
    const registration = await navigator.serviceWorker.register('/service-worker.js', {
      scope: '/',
      updateViaCache: 'none' // Always check for updates
    });
    
    console.log('[SW] Service Worker registered:', registration.scope);

    // Force update check (important after domain migration)
    registration.update().catch(err => {
      console.log('[SW] Update check failed:', err);
    });

    // Listen for new service worker installation
    registration.addEventListener('updatefound', () => {
      const newWorker = registration.installing;
      console.log('[SW] New Service Worker found, installing...');
      
      newWorker?.addEventListener('statechange', () => {
        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
          console.log('[SW] New version available');
          // The new SW will skipWaiting automatically
        }
      });
    });

    return registration;
  } catch (error) {
    console.error('[SW] Service Worker registration failed:', error);
    return null;
  }
};

// Clear old caches on page load (helps after domain migration)
const clearOldCaches = async () => {
  if ('caches' in window) {
    try {
      const cacheNames = await caches.keys();
      const oldCaches = cacheNames.filter(name => 
        !name.includes('genturix-cache-v2') && 
        !name.includes('workbox')
      );
      
      for (const cacheName of oldCaches) {
        console.log('[Cache] Deleting old cache:', cacheName);
        await caches.delete(cacheName);
      }
    } catch (error) {
      console.log('[Cache] Error clearing caches:', error);
    }
  }
};

// Register SW and clear caches after DOM is ready
const initServiceWorker = async () => {
  await clearOldCaches();
  await registerServiceWorker();
};

if (document.readyState === 'complete') {
  initServiceWorker();
} else {
  window.addEventListener('load', initServiceWorker);
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
