// =========================================================================
// GENTURIX Service Worker v6 - MINIMAL PUSH ONLY
// =========================================================================
// Este Service Worker SOLO maneja notificaciones push.
// NO intercepta fetch, NO usa cache, NO tiene lógica offline.
// =========================================================================

// =========================================================================
// INSTALL - Solo skipWaiting
// =========================================================================
self.addEventListener('install', (event) => {
  self.skipWaiting();
});

// =========================================================================
// ACTIVATE - Solo clients.claim
// =========================================================================
self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

// =========================================================================
// PUSH - Recibir y mostrar notificación
// =========================================================================
self.addEventListener('push', (event) => {
  let data = {
    title: 'GENTURIX',
    body: 'Nueva notificación',
    icon: '/logo192.png',
    badge: '/logo192.png',
    tag: 'genturix',
    data: {}
  };

  if (event.data) {
    try {
      const payload = event.data.json();
      data = {
        title: payload.title || data.title,
        body: payload.body || data.body,
        icon: payload.icon || data.icon,
        badge: payload.badge || data.badge,
        tag: payload.tag || data.tag,
        data: payload.data || {}
      };
    } catch (e) {
      // Parse error - use defaults
    }
  }

  const options = {
    body: data.body,
    icon: data.icon,
    badge: data.badge,
    tag: data.tag,
    renotify: true,
    requireInteraction: data.data?.type === 'panic_alert',
    vibrate: data.data?.type === 'panic_alert' ? [300, 100, 300] : [100],
    data: data.data
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
      .then(() => {
        // Notify open tabs about new alert
        if (data.data?.type === 'panic_alert') {
          return self.clients.matchAll({ type: 'window' }).then((clients) => {
            clients.forEach((client) => {
              client.postMessage({ type: 'NEW_PANIC_ALERT', data: data.data });
            });
          });
        }
      })
  );
});

// =========================================================================
// NOTIFICATION CLICK - Abrir o enfocar ventana
// =========================================================================
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'dismiss') return;

  const data = event.notification.data || {};
  let url = '/';

  if (data.type === 'panic_alert') {
    url = '/guard?tab=alerts';
  } else if (data.url) {
    url = data.url;
  }

  event.waitUntil(
    self.clients.matchAll({ type: 'window' }).then((clients) => {
      // Try to focus existing window
      for (const client of clients) {
        if ('focus' in client) {
          return client.navigate(url).then(() => client.focus());
        }
      }
      // Open new window if none exists
      return self.clients.openWindow(url);
    }).then(() => {
      // Notify that notification was clicked
      return self.clients.matchAll({ type: 'window' }).then((clients) => {
        clients.forEach((client) => {
          client.postMessage({ type: 'NOTIFICATION_CLICKED', data: data });
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
      client.postMessage({ type: 'NOTIFICATION_CLOSED', data: event.notification.data });
    });
  });
});
