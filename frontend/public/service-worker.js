// =========================================================================
// GENTURIX Service Worker v5 - Simplified Push Notifications
// =========================================================================
// Backend is the ONLY authority for push routing.
// Service Worker only: receives push → shows notification
// NO audio, NO locks, NO role logic
// =========================================================================

const CACHE_NAME = 'genturix-v5';
const OFFLINE_URL = '/offline.html';

const STATIC_ASSETS = [
  '/',
  '/manifest.json',
  '/logo192.png',
  '/favicon.ico'
];

// =========================================================================
// INSTALL
// =========================================================================
self.addEventListener('install', (event) => {
  console.log('[SW] Installing Service Worker v5');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

// =========================================================================
// ACTIVATE
// =========================================================================
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating Service Worker v5');
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name !== CACHE_NAME)
            .map((name) => caches.delete(name))
        );
      })
      .then(() => self.clients.claim())
  );
});

// =========================================================================
// FETCH - Network first, fallback to cache
// =========================================================================
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET' || event.request.url.includes('/api/')) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
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
// PUSH - Simple handler: receive → show notification
// NO audio logic, NO role checks (backend already filtered)
// =========================================================================
self.addEventListener('push', (event) => {
  console.log('[SW] Push received');

  let notification = {
    title: 'GENTURIX',
    body: 'Nueva notificación',
    icon: '/logo192.png',
    badge: '/logo192.png',
    tag: 'genturix-notification',
    data: { url: '/' }
  };

  if (event.data) {
    try {
      const payload = event.data.json();
      notification = {
        title: payload.title || notification.title,
        body: payload.body || notification.body,
        icon: payload.icon || notification.icon,
        badge: payload.badge || notification.badge,
        tag: payload.tag || notification.tag,
        data: payload.data || notification.data
      };
    } catch (e) {
      console.error('[SW] Error parsing push:', e);
    }
  }

  const isPanic = notification.data?.type === 'panic_alert';

  const options = {
    body: notification.body,
    icon: notification.icon,
    badge: notification.badge,
    tag: notification.tag,
    renotify: true,
    requireInteraction: isPanic,
    silent: false,
    vibrate: isPanic ? [300, 100, 300, 100, 300] : [100, 50, 100],
    data: notification.data,
    actions: isPanic ? [
      { action: 'view', title: '👁️ Ver' },
      { action: 'dismiss', title: '✕' }
    ] : []
  };

  event.waitUntil(
    self.registration.showNotification(notification.title, options)
      .then(() => {
        // Notify app about new alert (for UI update, not sound)
        if (isPanic) {
          return self.clients.matchAll({ type: 'window' })
            .then((clients) => {
              clients.forEach((client) => {
                client.postMessage({
                  type: 'NEW_PANIC_ALERT',
                  data: notification.data
                });
              });
            });
        }
      })
  );
});

// =========================================================================
// NOTIFICATION CLICK
// =========================================================================
self.addEventListener('notificationclick', (event) => {
  const notification = event.notification;
  const data = notification.data || {};
  
  notification.close();

  if (event.action === 'dismiss') return;

  let targetUrl = '/';
  
  switch (data.type) {
    case 'panic_alert':
      targetUrl = '/guard?tab=alerts';
      break;
    case 'visitor_arrival':
    case 'visitor_exit':
      targetUrl = '/resident?tab=history';
      break;
    default:
      targetUrl = data.url || '/';
  }

  event.waitUntil(
    self.clients.matchAll({ type: 'window' })
      .then((clients) => {
        for (const client of clients) {
          if (client.url.includes(self.location.origin) && 'focus' in client) {
            return client.navigate(targetUrl).then(() => client.focus());
          }
        }
        return self.clients.openWindow(targetUrl);
      })
      .then(() => {
        // Notify app that notification was clicked
        return self.clients.matchAll({ type: 'window' });
      })
      .then((clients) => {
        clients.forEach((client) => {
          client.postMessage({
            type: 'NOTIFICATION_CLICKED',
            data: data
          });
        });
      })
  );
});

// =========================================================================
// NOTIFICATION CLOSE
// =========================================================================
self.addEventListener('notificationclose', (event) => {
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
// MESSAGE
// =========================================================================
self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

console.log('[SW] Service Worker v5 loaded');
