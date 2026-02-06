const CACHE_NAME = '1crypten-elite-cache-v10.6.4';
const STATIC_ASSETS = [
    '/',
    'logo10D.png',
    'SoHoje1.png',
    // Removed problematic CORS asset: 'https://cdn.tailwindcss.com',
    'https://unpkg.com/react@18/umd/react.production.min.js',
    'https://unpkg.com/react-dom@18/umd/react-dom.production.min.js',
    'https://unpkg.com/react-router-dom@6/dist/umd/react-router-dom.production.min.js',
    'https://unpkg.com/framer-motion@10/dist/framer-motion.js',
    'https://unpkg.com/lucide@latest',
    'https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js',
    'https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Outfit:wght@400;700;900&family=Roboto+Mono:wght@400;700&display=swap',
    'https://fonts.googleapis.com/icon?family=Material+Icons+Round'
];

// V10.5 Improved Install Logic
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[SW] Pre-caching static assets');
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

// V10.5 Clean up old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
            );
        }).then(() => {
            return self.clients.claim();
        })
    );
});

// V10.5 Cache-First for Assets, Stale-While-Revalidate for APIs (Default)
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // If it's a static asset (logo, cdn, fonts), use Cache-First
    if (STATIC_ASSETS.includes(url.origin + url.pathname) ||
        url.hostname.includes('gstatic.com') ||
        url.hostname.includes('googleapis.com') ||
        url.hostname.includes('unpkg.com')) {

        event.respondWith(
            caches.match(event.request).then((cachedResponse) => {
                if (cachedResponse) return cachedResponse;
                return fetch(event.request).then((networkResponse) => {
                    return caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, networkResponse.clone());
                        return networkResponse;
                    });
                });
            })
        );
        return;
    }

    // Default: Network First with Fallback to Cache
    event.respondWith(
        fetch(event.request).catch(() => {
            return caches.match(event.request);
        })
    );
});

// V10.5 Push Notifications
self.addEventListener('push', (event) => {
    let data = { title: '1Crypten Alerta', body: 'Mensagem do Capitão Sniper V10.5.' };
    try {
        if (event.data) data = event.data.json();
    } catch (e) { }

    const options = {
        body: data.body,
        icon: 'logo10D.png',
        badge: 'logo10D.png',
        vibrate: [100, 50, 100],
        data: { dateOfArrival: Date.now(), primaryKey: 1 },
        actions: [
            { action: 'explore', title: 'Ver Dashboard', icon: 'logo10D.png' },
            { action: 'close', title: 'Fechar', icon: 'logo10D.png' },
        ]
    };

    event.waitUntil(self.registration.showNotification(data.title, options));
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    if (event.action === 'explore') {
        event.waitUntil(clients.openWindow('/'));
    }
});
