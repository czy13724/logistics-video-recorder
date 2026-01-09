// 物流视频录制管理系统 - Service Worker
// 用于PWA离线缓存和资源管理

const CACHE_NAME = 'logistics-video-v1';
const RUNTIME_CACHE = 'logistics-video-runtime';

// 需要缓存的静态资源
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/manifest.json',
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap',
    'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js'
];

// 安装事件 - 缓存静态资源
self.addEventListener('install', (event) => {
    console.log('[Service Worker] 安装中...');

    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[Service Worker] 缓存静态资源');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => self.skipWaiting())
    );
});

// 激活事件 - 清理旧缓存
self.addEventListener('activate', (event) => {
    console.log('[Service Worker] 激活中...');

    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((cacheName) => {
                        return cacheName !== CACHE_NAME && cacheName !== RUNTIME_CACHE;
                    })
                    .map((cacheName) => {
                        console.log('[Service Worker] 删除旧缓存:', cacheName);
                        return caches.delete(cacheName);
                    })
            );
        })
            .then(() => self.clients.claim())
    );
});

// 获取事件 - 网络优先策略（API请求），缓存优先策略（静态资源）
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // API请求 - 网络优先，失败时使用缓存
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    // 克隆响应并存入运行时缓存
                    const responseClone = response.clone();
                    caches.open(RUNTIME_CACHE).then((cache) => {
                        cache.put(request, responseClone);
                    });
                    return response;
                })
                .catch(() => {
                    // 网络失败，尝试从缓存获取
                    return caches.match(request);
                })
        );
        return;
    }

    // 视频流 - 直接从网络获取，不缓存视频文件
    if (url.pathname.includes('/stream')) {
        event.respondWith(fetch(request));
        return;
    }

    // 静态资源 - 缓存优先，失败时从网络获取
    event.respondWith(
        caches.match(request)
            .then((cachedResponse) => {
                if (cachedResponse) {
                    return cachedResponse;
                }

                // 缓存未命中，从网络获取
                return fetch(request).then((response) => {
                    // 只缓存成功的GET请求
                    if (!response || response.status !== 200 || request.method !== 'GET') {
                        return response;
                    }

                    // 克隆响应并存入缓存
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(request, responseClone);
                    });

                    return response;
                });
            })
    );
});

// 消息事件 - 手动触发缓存更新
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }

    if (event.data && event.data.type === 'CLEAR_CACHE') {
        event.waitUntil(
            caches.keys().then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => caches.delete(cacheName))
                );
            })
        );
    }
});

// 后台同步事件（可选）
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-videos') {
        console.log('[Service Worker] 后台同步视频数据');
        // 这里可以添加后台同步逻辑
    }
});

// 推送通知事件（可选）
self.addEventListener('push', (event) => {
    const options = {
        body: event.data ? event.data.text() : '新的视频录制完成',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/icon-72x72.png',
        vibrate: [200, 100, 200],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        }
    };

    event.waitUntil(
        self.registration.showNotification('物流视频管理', options)
    );
});

// 通知点击事件
self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    event.waitUntil(
        clients.openWindow('/')
    );
});

console.log('[Service Worker] Service Worker 已加载');
