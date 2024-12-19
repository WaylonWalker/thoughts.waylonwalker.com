// Force clean break from old service workers
const FORCE_RESET = '2024-12-19';
const KILL_SWITCH = false;  // Set to true to unregister all service workers
let CACHE_NAME = 'thoughts-cache-' + FORCE_RESET;

// Initialize service worker
async function initServiceWorker() {
  if (KILL_SWITCH) {
    // Unregister itself and clear all caches
    await self.registration.unregister();
    const cacheNames = await caches.keys();
    await Promise.all(
      cacheNames.map(cacheName => {
        console.log('Killing cache:', cacheName);
        return caches.delete(cacheName);
      })
    );
    return;
  }

  // Normal service worker initialization
  self.addEventListener('message', function(event) {
    if (event.data && event.data.type === 'APP_VERSION') {
      CACHE_NAME = 'thoughts-cache-v' + event.data.version + '-' + FORCE_RESET;
      
      // Clear all old caches
      caches.keys().then(function(cacheNames) {
        return Promise.all(
          cacheNames.map(function(cacheName) {
            if (!cacheName.includes(FORCE_RESET)) {
              console.log('Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      });
    }
  });

  self.addEventListener('install', function(event) {
    // Force activation by skipping waiting
    self.skipWaiting();
    
    event.waitUntil(
      caches.open(CACHE_NAME).then(function(cache) {
        const urlsToCache = [
          '/app.css',  // No query string needed, versioning handled by cache name
          '/static/htmx@1.9.4.min.js',
          '/static/json-enc.js',
          '/static/8bitcc.ico',
          '/static/8bitcc.png'
        ];
        
        // Cache each URL individually to handle failures gracefully
        return Promise.all(
          urlsToCache.map(url => 
            cache.add(url).catch(error => {
              console.error('Failed to cache:', url, error);
              // Continue even if one file fails
              return Promise.resolve();
            })
          )
        );
      })
    );
  });

  self.addEventListener('activate', function(event) {
    // Take control of all pages immediately
    event.waitUntil(clients.claim());
    
    // Clear old caches on activation
    event.waitUntil(
      caches.keys().then(function(cacheNames) {
        return Promise.all(
          cacheNames.map(function(cacheName) {
            if (!cacheName.includes(FORCE_RESET)) {
              console.log('Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
    );
  });

  self.addEventListener('fetch', function(event) {
    if (event.request.url.includes('service-worker.js')) {
      event.respondWith(fetch(event.request));
    } else {
      event.respondWith(
        caches.match(event.request, {
          ignoreSearch: true  // Ignore query strings when matching cache
        }).then(function(response) {
          return response || fetch(event.request);
        })
      );
    }
  });
}

// Start the service worker
initServiceWorker();
