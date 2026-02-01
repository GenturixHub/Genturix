// GENTURIX Service Worker for PWA + Push Notifications
const CACHE_NAME = 'genturix-v2';
const OFFLINE_URL = '/offline.html';

// Assets to cache
const urlsToCache = [
  '/',
  '/static/js/bundle.js',
  '/manifest.json',
  '/logo192.png',
  '/favicon.ico',
  OFFLINE_URL
];

// Install event - cache basic assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(urlsToCache))
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.filter((cacheName) => {
          return cacheName !== CACHE_NAME;
        }).map((cacheName) => {
          return caches.delete(cacheName);
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event - network first, fallback to cache
self.addEventListener('fetch', (event) => {
  // Skip non-GET requests and API calls
  if (event.request.method !== 'GET' || event.request.url.includes('/api/')) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Clone the response and cache it
        const responseClone = response.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, responseClone);
        });
        return response;
      })
      .catch(() => {
        // Fallback to cache
        return caches.match(event.request)
          .then((response) => {
            if (response) {
              return response;
            }
            // If not in cache, return offline page for navigation requests
            if (event.request.mode === 'navigate') {
              return caches.match(OFFLINE_URL);
            }
            return new Response('', { status: 404 });
          });
      })
  );
});

// ==================== PUSH NOTIFICATION HANDLING ====================

// Handle push notification received
self.addEventListener('push', (event) => {
  console.log('[SW] Push notification received');
  
  let data = {
    title: 'GENTURIX - Nueva Notificación',
    body: 'Tienes una nueva notificación',
    icon: '/logo192.png',
    badge: '/logo192.png',
    tag: 'default',
    requireInteraction: true,
    data: {}
  };

  try {
    if (event.data) {
      const payload = event.data.json();
      data = {
        title: payload.title || data.title,
        body: payload.body || data.body,
        icon: payload.icon || data.icon,
        badge: payload.badge || data.badge,
        tag: payload.tag || data.tag,
        requireInteraction: payload.requireInteraction !== undefined ? payload.requireInteraction : true,
        data: payload.data || {}
      };
    }
  } catch (e) {
    console.error('[SW] Error parsing push data:', e);
  }

  // Determine if this is a panic alert
  const isPanicAlert = data.data.type === 'panic_alert';

  // Configure notification options
  const options = {
    body: data.body,
    icon: data.icon,
    badge: data.badge,
    tag: data.tag,
    requireInteraction: data.requireInteraction,
    vibrate: isPanicAlert 
      ? [500, 200, 500, 200, 500, 200, 500] // Longer urgent pattern for panic
      : [200, 100, 200, 100, 200],
    data: data.data,
    // Silent for panic alerts - we control sound via AlertSoundManager
    // This prevents duplicate sounds from native notification + our custom sound
    silent: isPanicAlert ? true : false,
    actions: isPanicAlert ? [
      { action: 'open', title: 'Ver Alerta' },
      { action: 'dismiss', title: 'Cerrar' }
    ] : []
  };

  // For panic alerts, send message to ONE client to play sound
  // AlertSoundManager uses localStorage lock to prevent duplicates across tabs
  if (isPanicAlert) {
    self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Only send to first visible client to avoid duplicate sounds
        // The AlertSoundManager will handle cross-tab coordination
        if (clientList.length > 0) {
          // Prefer focused/visible clients
          const visibleClient = clientList.find(c => c.visibilityState === 'visible') || clientList[0];
          visibleClient.postMessage({
            type: 'PLAY_PANIC_SOUND',
            data: data.data
          });
        }
      });
  }

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Handle notification click
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event.action);
  
  event.notification.close();
  
  // Handle dismiss action
  if (event.action === 'dismiss') {
    return;
  }
  
  // Determine URL to open
  let urlToOpen = '/';
  const notificationData = event.notification.data || {};
  
  if (notificationData.url) {
    urlToOpen = notificationData.url;
  } else if (notificationData.type === 'panic_alert') {
    urlToOpen = `/guard?alert=${notificationData.event_id}`;
  }
  
  // Open or focus the app
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Send stop sound message to ALL clients immediately
        clientList.forEach((client) => {
          client.postMessage({
            type: 'STOP_PANIC_SOUND'
          });
        });
        
        // Try to find an existing window to focus
        for (const client of clientList) {
          if (client.url.includes(self.registration.scope) && 'focus' in client) {
            // Navigate existing window to the alert
            client.postMessage({
              type: 'PANIC_ALERT_CLICK',
              data: notificationData
            });
            return client.focus();
          }
        }
        // No existing window, open a new one
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
  );
});

// Handle notification close
self.addEventListener('notificationclose', (event) => {
  console.log('[SW] Notification closed');
});

// Handle messages from the main app
self.addEventListener('message', (event) => {
  console.log('[SW] Message received:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
