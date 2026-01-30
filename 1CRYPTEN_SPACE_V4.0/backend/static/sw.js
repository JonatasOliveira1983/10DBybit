const CACHE_NAME = '1crypten-space-v4-v3';
const ASSETS = [
    '/',
    '/dashboard',
    '/logo10D.png',
    '/SoHoje1.png'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS);
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
            );
        })
    );
});

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // 1. Bypass Service Worker for all API and system calls
    if (url.pathname.startsWith('/api/') ||
        url.pathname === '/banca' ||
        url.pathname === '/health' ||
        url.hostname.includes('firebaseio.com')) {
        return; // Let the browser handle it normally
    }

    // 2. Standard Fetch with safe Cache fallback
    event.respondWith(
        fetch(event.request).catch(async () => {
            const cachedResponse = await caches.match(event.request);
            if (cachedResponse) return cachedResponse;

            // Fallback for navigation requests (SPA)
            if (event.request.mode === 'navigate') {
                return caches.match('/');
            }

            // Return a simple empty response or error if nothing else works
            // to avoid "Failed to convert value to 'Response'" type error
            return new Response('Network error occurred', {
                status: 408,
                headers: { 'Content-Type': 'text/plain' }
            });
        })
    );
});
