// =========================================================================
// GENTURIX Service Worker v4 - Push Notifications + PWA
// =========================================================================
const CACHE_NAME = 'genturix-v4';
const OFFLINE_URL = '/offline.html';

// Assets to cache for offline
const STATIC_ASSETS = [
  '/',
  '/manifest.json',
  '/logo192.png',
  '/favicon.ico'
];

// =========================================================================
// INSTALL - Cache static assets
// =========================================================================
self.addEventListener('install', (event) => {
  console.log('[SW] Installing Service Worker v4');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// =========================================================================
// ACTIVATE - Clean old caches and take control
// =========================================================================
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating Service Worker v4');
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name !== CACHE_NAME)
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => self.clients.claim())
      .then(() => console.log('[SW] Service Worker v4 now active'))
  );
});

// =========================================================================
// FETCH - Network first, fallback to cache
// =========================================================================
self.addEventListener('fetch', (event) => {
  // Skip non-GET and API requests
  if (event.request.method !== 'GET' || event.request.url.includes('/api/')) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Cache successful responses
        if (response.ok) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        return caches.match(event.request)
          .then((cached) => cached || caches.match('/'));
      })
  );
});

// =========================================================================
// PUSH - Handle incoming push notifications
// =========================================================================
self.addEventListener('push', (event) => {
  console.log('[SW] Push event received');

  // Default notification data
  let notification = {
    title: 'GENTURIX',
    body: 'Nueva notificación',
    icon: '/logo192.png',
    badge: '/logo192.png',
    tag: 'genturix-notification',
    data: { url: '/' }
  };

  // Parse push payload
  if (event.data) {
    try {
      const payload = event.data.json();
      console.log('[SW] Push payload:', payload);
      
      notification = {
        title: payload.title || notification.title,
        body: payload.body || notification.body,
        icon: payload.icon || notification.icon,
        badge: payload.badge || notification.badge,
        tag: payload.tag || notification.tag,
        data: payload.data || notification.data
      };
    } catch (e) {
      console.error('[SW] Error parsing push payload:', e);
      // Try as text
      try {
        notification.body = event.data.text();
      } catch (e2) {
        console.error('[SW] Error reading push as text:', e2);
      }
    }
  }

  // Determine notification type for customization
  const notificationType = notification.data?.type || 'default';
  const isPanic = notificationType === 'panic_alert';

  // Configure notification options
  const options = {
    body: notification.body,
    icon: notification.icon,
    badge: notification.badge,
    tag: notification.tag,
    renotify: true, // Always notify even with same tag
    requireInteraction: isPanic, // Only panic needs interaction
    silent: false, // IMPORTANT: Let the system play sound
    vibrate: isPanic 
      ? [300, 100, 300, 100, 300, 100, 300] // Urgent pattern
      : [100, 50, 100], // Friendly short vibration
    data: notification.data,
    actions: isPanic ? [
      { action: 'view', title: '👁️ Ver Alerta' },
      { action: 'dismiss', title: '✕ Cerrar' }
    ] : [
      { action: 'view', title: 'Ver' }
    ]
  };

  // Show the notification
  event.waitUntil(
    self.registration.showNotification(notification.title, options)
      .then(() => {
        console.log('[SW] Notification shown:', notification.title);
        
        // For panic alerts, also notify the app to play sound
        if (isPanic) {
          return self.clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clients) => {
              if (clients.length > 0) {
                // Send to all clients to play sound
                clients.forEach(client => {
                  client.postMessage({
                    type: 'PLAY_PANIC_SOUND',
                    data: notification.data
                  });
                });
              }
            });
        }
      })
      .catch((err) => {
        console.error('[SW] Error showing notification:', err);
      })
  );
});

// =========================================================================
// NOTIFICATION CLICK - Handle user clicking on notification
// =========================================================================
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event.action);
  
  const notification = event.notification;
  const notificationData = notification.data || {};
  const action = event.action;

  // Close the notification
  notification.close();

  // Handle dismiss action
  if (action === 'dismiss') {
    return;
  }

  // Determine URL to open
  let targetUrl = notificationData.url || '/';
  
  // Route based on notification type
  switch (notificationData.type) {
    case 'panic_alert':
      targetUrl = '/guard?tab=alerts';
      break;
    case 'visitor_arrival':
    case 'visitor_exit':
      targetUrl = '/resident?tab=history';
      break;
    case 'visitor_preregistration':
      targetUrl = '/guard?tab=visits';
      break;
    case 'reservation_approved':
    case 'reservation_rejected':
    case 'reservation_pending':
      targetUrl = notificationData.url || '/resident?tab=reservations';
      break;
    default:
      targetUrl = notificationData.url || '/';
  }

  // Focus existing window or open new one
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clients) => {
        // Try to find an existing app window
        for (const client of clients) {
          if (client.url.includes(self.location.origin) && 'focus' in client) {
            // Navigate and focus
            return client.navigate(targetUrl).then(() => client.focus());
          }
        }
        // Open new window if no existing one
        return self.clients.openWindow(targetUrl);
      })
      .then(() => {
        // Notify the app that notification was clicked (to stop any sounds)
        return self.clients.matchAll({ type: 'window' });
      })
      .then((clients) => {
        clients.forEach((client) => {
          client.postMessage({
            type: 'NOTIFICATION_CLICKED',
            data: notificationData
          });
        });
      })
  );
});

// =========================================================================
// NOTIFICATION CLOSE - Handle user dismissing notification
// =========================================================================
self.addEventListener('notificationclose', (event) => {
  console.log('[SW] Notification closed by user');
  
  // Notify app to stop any sounds
  self.clients.matchAll({ type: 'window' }).then((clients) => {
    clients.forEach((client) => {
      client.postMessage({
        type: 'NOTIFICATION_CLOSED',
        data: event.notification.data
      });
    });
  });
});

// =========================================================================
// MESSAGE - Handle messages from the app
// =========================================================================
self.addEventListener('message', (event) => {
  console.log('[SW] Message received:', event.data);
  
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

console.log('[SW] Service Worker v4 script loaded');
