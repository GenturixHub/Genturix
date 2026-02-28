// =========================================================================
// GENTURIX Service Worker v16 - PUSH + SMART CACHE + API STALE-WHILE-REVALIDATE
// =========================================================================
// Handles push notifications with intelligent caching for static assets.
// Uses Stale-While-Revalidate for JS, CSS, icons, fonts AND select API endpoints.
// POST/PUT/DELETE requests are NEVER cached.
// v16: Fixed Android notification icons with explicit icon/badge paths
// =========================================================================

// IMPORTANT: Increment this version on each deploy
const SW_VERSION = '16.0.0';
const CACHE_NAME = 'genturix-cache-v16';
const API_CACHE_NAME = 'genturix-api-cache-v16';

// Notification icons with version suffix to bypass Android cache
const NOTIFICATION_ICON = '/icons/notification-icon-v2.png';
const NOTIFICATION_BADGE = '/icons/badge-72-v2.png';

// List of valid caches (all others will be deleted)
const CACHE_WHITELIST = [CACHE_NAME, API_CACHE_NAME];

// API cache duration: 24 hours
const API_CACHE_MAX_AGE = 24 * 60 * 60 * 1000;

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

// API endpoints to cache with Stale-While-Revalidate (GET only)
const CACHEABLE_API_PATTERNS = [
  /\/api\/profile/,
  /\/api\/notifications/,
  /\/api\/directory/,
  /\/api\/visits/,
  /\/api\/authorizations/,
  /\/api\/resident\/reservations/,
  /\/api\/areas/,
  /\/api\/settings/
];

// Patterns to NEVER cache
const NO_CACHE_PATTERNS = [
  /chrome-extension/,
  /sockjs-node/,
  /hot-update/
];

// Check if request should use static asset cache
function shouldCacheStatic(url) {
  const urlStr = url.toString();
  
  // Never cache these
  if (NO_CACHE_PATTERNS.some(pattern => pattern.test(urlStr))) {
    return false;
  }
  
  // Cache static assets
  return STATIC_ASSET_PATTERNS.some(pattern => pattern.test(urlStr));
}

// Check if API request should be cached
function shouldCacheAPI(url) {
  const urlStr = url.toString();
  return CACHEABLE_API_PATTERNS.some(pattern => pattern.test(urlStr));
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
// PUSH - Receive and display push notification with correct icons
// =========================================================================
self.addEventListener('push', (event) => {
  // Default notification data with versioned icons to bypass Android cache
  let data = {
    title: 'GENTURIX',
    body: 'Nueva notificación',
    icon: NOTIFICATION_ICON,
    badge: NOTIFICATION_BADGE,
    tag: 'genturix-notification',
    data: {}
  };

  if (event.data) {
    try {
      const payload = event.data.json();
      data = {
        title: payload.title || data.title,
        body: payload.body || data.body,
        // Always use our versioned icons to override any cached ones
        icon: NOTIFICATION_ICON,
        badge: NOTIFICATION_BADGE,
        tag: payload.tag || `genturix-${Date.now()}`,
        data: payload.data || {}
      };
    } catch (e) {
      console.error(`[SW v${SW_VERSION}] Push data parse error:`, e);
    }
  }

  // Determine notification type for customization
  const notificationType = data.data?.type || 'default';
  const isPanicAlert = notificationType === 'panic_alert';
  const isVisitor = notificationType === 'visitor_authorization' || notificationType === 'visitor_entry';
  const isReservation = notificationType === 'reservation';

  // Build notification options with actions
  const options = {
    body: data.body,
    icon: data.icon,
    badge: data.badge,
    tag: data.tag,
    renotify: true,
    requireInteraction: isPanicAlert,
    vibrate: isPanicAlert ? [300, 100, 300, 100, 300] : [200, 100, 200],
    data: data.data,
    // Actions for user interaction
    actions: isPanicAlert ? [
      { action: 'view', title: 'Ver Alerta', icon: NOTIFICATION_ICON },
      { action: 'dismiss', title: 'Cerrar' }
    ] : [
      { action: 'open', title: 'Ver', icon: NOTIFICATION_ICON },
      { action: 'dismiss', title: 'Cerrar' }
    ]
  };

  console.log(`[SW v${SW_VERSION}] Showing notification: ${data.title} (type: ${notificationType})`);

  event.waitUntil(
    self.registration.showNotification(data.title, options)
      .then(() => {
        // Notify open tabs about new alert
        if (isPanicAlert) {
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
// NOTIFICATION CLICK - Open or focus window based on action
// =========================================================================
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  // Handle dismiss action
  if (event.action === 'dismiss') {
    console.log(`[SW v${SW_VERSION}] Notification dismissed by user`);
    return;
  }

  const data = event.notification.data || {};
  let url = '/';

  // Determine URL based on notification type and action
  if (data.type === 'panic_alert') {
    url = '/guard?tab=alerts';
  } else if (data.type === 'visitor_authorization') {
    url = '/resident?tab=authorizations';
  } else if (data.type === 'visitor_entry') {
    url = '/resident?tab=visits';
  } else if (data.type === 'reservation') {
    url = '/resident?tab=reservations';
  } else if (data.url) {
    url = data.url;
  }

  console.log(`[SW v${SW_VERSION}] Notification clicked (action: ${event.action || 'default'}) → navigating to ${url}`);

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
// FETCH - Stale-While-Revalidate for static assets AND cacheable API endpoints
// =========================================================================
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // Skip non-GET requests (POST, PUT, DELETE are never cached)
  if (event.request.method !== 'GET') return;
  
  // Skip non-http(s) requests
  if (!url.protocol.startsWith('http')) return;
  
  // Skip requests we should never cache
  if (NO_CACHE_PATTERNS.some(pattern => pattern.test(url.toString()))) return;
  
  // Strategy 1: Static assets - Stale-While-Revalidate
  if (shouldCacheStatic(url)) {
    event.respondWith(
      caches.open(CACHE_NAME).then(cache => {
        return cache.match(event.request).then(cachedResponse => {
          const fetchPromise = fetch(event.request).then(networkResponse => {
            if (networkResponse && networkResponse.status === 200) {
              cache.put(event.request, networkResponse.clone());
            }
            return networkResponse;
          }).catch(() => cachedResponse);
          
          return cachedResponse || fetchPromise;
        });
      })
    );
    return;
  }
  
  // Strategy 2: Cacheable API endpoints - Stale-While-Revalidate with 24h expiry
  if (shouldCacheAPI(url)) {
    event.respondWith(
      caches.open(API_CACHE_NAME).then(async cache => {
        const cachedResponse = await cache.match(event.request);
        
        // Check if cached response is still valid (24h)
        let cacheValid = false;
        if (cachedResponse) {
          const cachedDate = cachedResponse.headers.get('sw-cached-at');
          if (cachedDate) {
            const age = Date.now() - parseInt(cachedDate, 10);
            cacheValid = age < API_CACHE_MAX_AGE;
          }
        }
        
        // Always try network in background
        const networkPromise = fetch(event.request).then(networkResponse => {
          if (networkResponse && networkResponse.status === 200) {
            // Clone and add cache timestamp header
            const headers = new Headers(networkResponse.headers);
            headers.set('sw-cached-at', Date.now().toString());
            
            const responseToCache = new Response(networkResponse.clone().body, {
              status: networkResponse.status,
              statusText: networkResponse.statusText,
              headers: headers
            });
            
            cache.put(event.request, responseToCache);
          }
          return networkResponse;
        }).catch(() => {
          // Network failed, return cached if available
          return cachedResponse;
        });
        
        // Return cached immediately if valid, otherwise wait for network
        if (cachedResponse && cacheValid) {
          return cachedResponse;
        }
        
        return networkPromise;
      })
    );
    return;
  }
  
  // For other requests: let browser handle normally (no interception)
});
