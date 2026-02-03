const CACHE_NAME = '1crypten-sniper-v7.1';
const ASSETS = [
    '/',
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
        }).then(() => {
            return self.clients.claim();
        })
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        fetch(event.request).catch(() => {
            return caches.match(event.request);
        })
    );
});

// V7.1 Push Notifications
self.addEventListener('push', (event) => {
    const data = event.data ? event.data.json() : { title: '1Crypten Alerta', body: 'Mensagem do Capitão Sniper V7.1.' };

    const options = {
        body: data.body,
        icon: '/logo10D.png',
        badge: '/logo10D.png',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            { action: 'explore', title: 'Ver Sniper Dash', icon: '/logo10D.png' },
            { action: 'close', title: 'Fechar', icon: '/logo10D.png' },
        ]
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    if (event.action === 'explore') {
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});
