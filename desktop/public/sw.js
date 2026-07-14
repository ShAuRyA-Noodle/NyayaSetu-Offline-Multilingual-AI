/*
 * NyayaSetu service worker — offline app shell + runtime caching.
 *
 * Strategy:
 *  - Navigations  -> network-first, fall back to cached app shell (SPA offline).
 *  - Static GET   -> cache-first (hashed Vite assets are immutable).
 *  - API GET      -> network-first, fall back to last cached response offline.
 *  - Non-GET      -> passthrough (writes are queued by the app's sync layer).
 *
 * This makes the web app installable and usable with no connectivity, matching
 * the offline-first design of the native/kiosk deployment.
 */
const VERSION = 'nyayasetu-v1';
const SHELL_CACHE = `${VERSION}-shell`;
const STATIC_CACHE = `${VERSION}-static`;
const API_CACHE = `${VERSION}-api`;
const SHELL_URLS = ['/', '/index.html', '/manifest.webmanifest', '/favicon.svg'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((c) => c.addAll(SHELL_URLS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

function isApi(url) {
  return url.pathname.includes('/api/');
}

async function networkFirst(request, cacheName, fallbackUrl) {
  const cache = await caches.open(cacheName);
  try {
    const res = await fetch(request);
    if (res && res.ok) cache.put(request, res.clone());
    return res;
  } catch (err) {
    const cached = await cache.match(request);
    if (cached) return cached;
    if (fallbackUrl) {
      const shell = await caches.match(fallbackUrl);
      if (shell) return shell;
    }
    throw err;
  }
}

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;
  const res = await fetch(request);
  if (res && res.ok) cache.put(request, res.clone());
  return res;
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return; // writes handled by the app sync layer

  const url = new URL(request.url);
  if (url.origin !== self.location.origin && !isApi(url)) return;

  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request, SHELL_CACHE, '/index.html'));
  } else if (isApi(url)) {
    event.respondWith(networkFirst(request, API_CACHE));
  } else {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
  }
});
