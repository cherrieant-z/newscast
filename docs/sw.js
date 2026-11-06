const CACHE_NAME = 'newscast-pwa-v3';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // 对大体积音频文件走网络流式，避免占满浏览器缓存限额
  if (event.request.url.includes('.mp3') || event.request.url.includes('/audio/')) {
    return;
  }

  // 针对 reports.json 数据：优先网络，失败则读取离线缓存 (Network-first with Cache fallback)
  if (event.request.url.includes('reports.json') || event.request.url.includes('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response && response.status === 200) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          }
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // 页面文档：网络优先。
  // 之前用「缓存优先」，改了页面手机上却一直显示旧版，因为第一次打开永远先拿缓存。
  // 改成网络优先后，每次打开都是最新的，断网时才退回缓存。
  if (event.request.mode === 'navigate' || event.request.url.endsWith('.html')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response && response.status === 200) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          }
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // 其他静态资源（图标、CSS、JS）：缓存优先，后台自动更新
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const fetchPromise = fetch(event.request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, networkResponse.clone()));
        }
        return networkResponse;
      }).catch(() => {});
      return cached || fetchPromise;
    })
  );
});
