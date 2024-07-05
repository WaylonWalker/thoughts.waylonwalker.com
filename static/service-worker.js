self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open('thoughts-cache').then(function(cache) {
      return cache.addAll([
        '/',
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
