self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open('thoughts-cache').then(function(cache) {
      return cache.addAll([
        '/',
        '/manifest.json',
        '/static/app.css',
        '/static/htmx@1.9.4.min.js',
        '/static/json-enc.js',
        '/static/main.js',
        '/static/manifest.json',
        '/static/service-worker.js',
        '/static/8bitcc.ico',
        '/static/8bitcc.png'
      ]);
    })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request).then(function(response) {
      return response || fetch(event.request);
    })
  );
});
