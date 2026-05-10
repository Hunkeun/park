/**
 * AI 시대 영성 책방 — Service Worker
 *
 * 전략:
 *   - 페이지 navigation 요청 (mode === 'navigate'): SW 캐시 우회, 항상 네트워크
 *     (Vercel cleanUrls 308 리다이렉트와 SW 캐시가 충돌해 navigation 실패하는 문제 회피)
 *   - JS / CSS / 폰트 / 사이트 설정 정적 자원: stale-while-revalidate
 *     (즉시 캐시 응답으로 빠르고, 백그라운드에서 새 버전 자동 수집 → 다음 방문에 반영)
 *   - books_master / build_info / site_config JSON: stale-while-revalidate
 *   - 표지·QR 이미지: cache-first (한 번 받으면 영구)
 *   - EPUB · /api · Supabase · TossPayments: 캐시 안 함 (network-only)
 *
 * Cache 버전: 코드 변경 시 CACHE_VERSION 만 바꾸면 모든 옛 캐시 일괄 폐기
 */

const CACHE_VERSION = 'aisb-v2-2026-05-10d';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const COVERS_CACHE = `${CACHE_VERSION}-covers`;
const DATA_CACHE = `${CACHE_VERSION}-data`;

// HTML 페이지는 더 이상 사전 캐시하지 않는다 (cleanUrls 308 충돌 방지).
// 정적 JS/이미지 일부만 install 시 미리 받아두어 첫 화면 빠르게.
const PRECACHE_FILES = [
    '/auth.js',
    '/cart.js',
    '/author_mode.js',
    '/beta-banner.js',
    '/pwa.js',
    '/manifest.json',
    '/logo/logo_horizontal.svg',
    '/logo/logo_vertical_gold.png',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => cache.addAll(PRECACHE_FILES).catch(() => {}))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => !k.startsWith(CACHE_VERSION)).map(k => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const req = event.request;
    if (req.method !== 'GET') return;

    // navigation 요청 (페이지 이동/주소창 입력)은 SW 가 절대 끼어들지 않는다.
    // Vercel cleanUrls 가 308 리다이렉트를 반환하는데, SW 캐시가 끼면 navigation 이 깨진다.
    if (req.mode === 'navigate') return;

    const url = new URL(req.url);

    // 외부 자원·EPUB·API 는 캐시 안 함
    if (url.origin !== location.origin ||
        url.pathname.startsWith('/epubs/') ||
        url.pathname.startsWith('/api/') ||
        url.pathname.startsWith('/payments/')) {
        return;
    }

    // JS 자원은 SW 가 끼지 않는다. 브라우저가 reader.js / cart.js 등을
    // Vercel 의 max-age=0 must-revalidate 정책으로 매번 etag 검증해 최신을 받는데,
    // SW 의 stale-while-revalidate 가 끼면 첫 응답이 옛 캐시본이 되어 새 배포가
    // 한 사이클 늦게 적용된다. 본문 fetch 옵션 같은 핵심 로직 변경이 즉시 반영되도록
    // JS 는 통과 시킨다.
    if (url.pathname.endsWith('.js')) {
        return;
    }

    // 표지·QR 이미지: cache-first (영구)
    if (url.pathname.startsWith('/covers/') || url.pathname.startsWith('/qr/')) {
        event.respondWith(cacheFirst(req, COVERS_CACHE));
        return;
    }

    // 데이터 JSON: stale-while-revalidate
    if (url.pathname === '/books_master.json' ||
        url.pathname === '/build_info.json' ||
        url.pathname === '/site_config.json') {
        event.respondWith(staleWhileRevalidate(req, DATA_CACHE));
        return;
    }

    // JS/CSS/폰트 등 정적 자원: stale-while-revalidate
    // (cache-first 였던 것을 swr 로 바꿔 새 배포 자동 반영)
    event.respondWith(staleWhileRevalidate(req, STATIC_CACHE));
});

async function cacheFirst(req, cacheName) {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(req);
    if (cached) return cached;
    try {
        const resp = await fetch(req);
        if (resp.ok) cache.put(req, resp.clone()).catch(() => {});
        return resp;
    } catch (e) {
        // 오프라인 + 캐시 없음 — 빈 응답
        return new Response('오프라인이며 캐시되지 않은 자원입니다.', { status: 503 });
    }
}

async function staleWhileRevalidate(req, cacheName) {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(req);
    const fetchPromise = fetch(req).then(resp => {
        if (resp.ok) cache.put(req, resp.clone()).catch(() => {});
        return resp;
    }).catch(() => cached);
    return cached || fetchPromise;
}
