const CACHE_NAME = '1crypten-space-v4-v1';
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
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request).then((response) => {
            return response || fetch(event.request);
        })
    );
});
