const CACHE_NAME = 'helpdeskit-static-v4';
const OFFLINE_URL = '/offline';

const PRECACHE_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/manifest.json',
  '/static/img/icons/icon-192.svg',
  '/static/img/icons/icon-512.svg',
  OFFLINE_URL
];

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    // Cache assets but ignore failures so install does not fail due to 404s
    await Promise.all(PRECACHE_ASSETS.map(async (url) => {
      try {
        const res = await fetch(url);
        if (!res || !res.ok) throw new Error('bad response');
        await cache.put(url, res.clone());
      } catch (err) {
        console.warn('SW: failed to cache', url, err);
      }
    }));
  })());
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
    ))
  );
  self.clients.claim();
});

// Simple runtime caching strategy
self.addEventListener('fetch', event => {
  const { request } = event;
  // Network-first for API
  if (request.url.includes('/api/')) {
    event.respondWith(
      fetch(request).then(res => {
        // optionally cache API responses here
        return res;
      }).catch(() => caches.match(request))
    );
    return;
  }

  // For navigation, try network first then cache, fallback to offline page
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).then(response => response).catch(() => caches.match(OFFLINE_URL))
    );
    return;
  }

  // For other assets: cache-first
  event.respondWith(
    caches.match(request).then(cached => cached || fetch(request).catch(() => caches.match(OFFLINE_URL)))
  );
});
