/**
 * 저자 모드 — 발행 전 권도 활성화 상태로 보기.
 * 진입: ?author=phk2026 한 번 방문 → localStorage 저장
 * 해제: ?author=off 또는 우상단 배지 클릭 → confirm → 해제
 *
 * 사용:
 *   <script src="author_mode.js" defer></script> (catalog · index)
 *   <script src="../author_mode.js" defer></script> (preview)
 *
 * 전역: window.isAuthorMode() — 모든 페이지에서 호출 가능
 */
(function () {
    const AUTHOR_KEY = 'phk2026';
    const STORAGE_KEY = 'aisb_author_mode';

    // URL 파라미터 처리 (즉시)
    try {
        const url = new URL(window.location.href);
        const param = url.searchParams.get('author');
        if (param === AUTHOR_KEY) {
            localStorage.setItem(STORAGE_KEY, '1');
            url.searchParams.delete('author');
            history.replaceState({}, '', url.toString());
        } else if (param === 'off') {
            localStorage.removeItem(STORAGE_KEY);
            url.searchParams.delete('author');
            history.replaceState({}, '', url.toString());
        }
    } catch (e) {
        // 안전 가드
    }

    window.isAuthorMode = function () {
        try { return localStorage.getItem(STORAGE_KEY) === '1'; } catch (e) { return false; }
    };

    function renderBadge() {
        if (!window.isAuthorMode()) return;
        if (document.getElementById('authorBadge')) return;
        const badge = document.createElement('div');
        badge.id = 'authorBadge';
        badge.innerHTML = '저자 모드 <span style="opacity:0.65;font-weight:400;margin-left:0.2rem">✕</span>';
        badge.style.cssText = [
            'position:fixed', 'top:4rem', 'right:0.8rem', 'z-index:9999',
            'background:#d4af37', 'color:#0a192f', 'font-weight:700',
            'padding:0.3rem 0.65rem', 'border-radius:3px', 'font-size:0.68rem',
            'letter-spacing:0.04rem', 'cursor:pointer',
            'box-shadow:0 3px 8px rgba(0,0,0,0.25)',
            'font-family:"Noto Sans KR",sans-serif', 'user-select:none',
            'opacity:0.9',
        ].join(';');
        badge.title = '클릭하면 저자 모드 해제';
        badge.addEventListener('click', function () {
            if (confirm('저자 모드를 해제할까요?\n(미발행 권이 다시 D-N 카운트다운으로 표시됩니다)')) {
                localStorage.removeItem(STORAGE_KEY);
                location.reload();
            }
        });
        document.body.appendChild(badge);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', renderBadge);
    } else {
        renderBadge();
    }

    // === 빌드 시각 표시 (모든 페이지 우하단 작은 회색 텍스트) ===
    function renderBuildInfo() {
        if (document.getElementById('buildInfo')) return;

        // preview 페이지는 ../build_info.json, 그 외는 build_info.json
        const path = location.pathname;
        const isPreview = /\/preview\//.test(path);
        const url = (isPreview ? '../' : '') + 'build_info.json';

        fetch(url, { cache: 'no-store' })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (info) {
                if (!info || !info.updated_at) return;
                const tag = document.createElement('div');
                tag.id = 'buildInfo';
                tag.textContent = '갱신 ' + info.updated_at;
                tag.style.cssText = [
                    'position:fixed', 'bottom:0.5rem', 'right:0.6rem', 'z-index:9998',
                    'color:rgba(255,255,255,0.45)',
                    'background:rgba(10,25,47,0.55)',
                    'padding:0.18rem 0.5rem', 'border-radius:3px',
                    'font-size:0.62rem', 'letter-spacing:0.02rem',
                    'font-family:"Noto Sans KR",sans-serif',
                    'pointer-events:none', 'user-select:none',
                ].join(';');
                document.body.appendChild(tag);
            })
            .catch(function () { /* 무시 */ });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', renderBuildInfo);
    } else {
        renderBuildInfo();
    }
})();
