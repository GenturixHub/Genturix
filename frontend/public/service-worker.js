// =========================================================================
// GENTURIX Service Worker v13 - PUSH + SMART CACHE
// =========================================================================
// Handles push notifications with intelligent caching for static assets.
// Uses Stale-While-Revalidate for JS, CSS, icons, fonts.
// API calls are NEVER cached.
// =========================================================================

// IMPORTANT: Increment this version on each deploy
const SW_VERSION = '13.0.0';
const CACHE_NAME = 'genturix-cache-v13';

// List of valid caches (all others will be deleted)
const CACHE_WHITELIST = [CACHE_NAME];

// Static assets to cache (Stale-While-Revalidate)
const STATIC_ASSET_PATTERNS = [
  /\.js$/,
  /\.css$/,
  /\.woff2?$/,
  /\.ttf$/,
  /\.otf$/,
  /\/icons\//,
  /\/manifest\.json$/,
  /\/logo\d+\.png$/,
  /\.svg$/
];

// Patterns to NEVER cache
const NO_CACHE_PATTERNS = [
  /\/api\//,
  /chrome-extension/,
  /sockjs-node/,
  /hot-update/
];

// Check if request should use cache
function shouldCache(url) {
  const urlStr = url.toString();
  
  // Never cache API or dynamic content
  if (NO_CACHE_PATTERNS.some(pattern => pattern.test(urlStr))) {
    return false;
  }
  
  // Cache static assets
  return STATIC_ASSET_PATTERNS.some(pattern => pattern.test(urlStr));
}

// =========================================================================
// INSTALL - Force immediate activation (skipWaiting)
// =========================================================================
self.addEventListener('install', (event) => {
  console.log(`[SW v${SW_VERSION}] Installing...`);
  
  // Force the waiting service worker to become the active service worker
  // This ensures new SW takes over immediately after domain migration
  self.skipWaiting();
});

// =========================================================================
// ACTIVATE - Clean old caches and claim all clients
// =========================================================================
self.addEventListener('activate', (event) => {
  console.log(`[SW v${SW_VERSION}] Activating...`);
  
  event.waitUntil(
    Promise.all([
      // Clean up old caches from previous domain/version
      caches.keys().then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => {
            if (!CACHE_WHITELIST.includes(cacheName)) {
              console.log(`[SW v${SW_VERSION}] Deleting old cache:`, cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      }),
      // Take control of all clients immediately
      self.clients.claim()
    ]).then(() => {
      console.log(`[SW v${SW_VERSION}] Activated and controlling all clients`);
      // Force check for updates after activation (helps with domain migration)
      self.registration.update();
    })
  );
});

// =========================================================================
// MESSAGE - Handle messages from client
// =========================================================================
self.addEventListener('message', (event) => {
  if (event.data) {
    switch (event.data.type) {
      case 'SKIP_WAITING':
        console.log(`[SW v${SW_VERSION}] Received SKIP_WAITING message`);
        self.skipWaiting();
        break;
      case 'GET_VERSION':
        event.ports[0]?.postMessage({ version: SW_VERSION });
        break;
      case 'CLEAR_CACHE':
        caches.keys().then(keys => {
          keys.forEach(key => caches.delete(key));
          console.log(`[SW v${SW_VERSION}] All caches cleared`);
        });
        break;
    }
  }
});

// =========================================================================
// PUSH - Receive and display push notification
// =========================================================================
self.addEventListener('push', (event) => {
  let data = {
    title: 'GENTURIX',
    body: 'Nueva notificación',
    icon: '/logo192.png',
    badge: '/logo192.png',
    tag: 'genturix-notification',
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
      console.error(`[SW v${SW_VERSION}] Push data parse error:`, e);
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
// NOTIFICATION CLICK - Open or focus window
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
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      // Try to focus existing window
      for (const client of clients) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
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

// =========================================================================
// FETCH - Stale-While-Revalidate for static assets, network-only for API
// =========================================================================
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // Skip non-GET requests
  if (event.request.method !== 'GET') return;
  
  // Skip non-http(s) requests
  if (!url.protocol.startsWith('http')) return;
  
  // Check if this is a cacheable static asset
  if (shouldCache(url)) {
    // Stale-While-Revalidate strategy
    event.respondWith(
      caches.open(CACHE_NAME).then(cache => {
        return cache.match(event.request).then(cachedResponse => {
          const fetchPromise = fetch(event.request).then(networkResponse => {
            // Only cache successful responses
            if (networkResponse && networkResponse.status === 200) {
              cache.put(event.request, networkResponse.clone());
            }
            return networkResponse;
          }).catch(() => {
            // Network failed, return cached if available
            return cachedResponse;
          });
          
          // Return cached immediately, update in background
          return cachedResponse || fetchPromise;
        });
      })
    );
  }
  // For API and dynamic content: let browser handle normally (no interception)
});
