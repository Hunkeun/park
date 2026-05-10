/**
 * 무료 베타 안내 배너.
 *
 * site_config.json 의 free_beta=true 일 때 모든 페이지 상단에 노출.
 * 토스 LIVE 후 false 로 전환만 하면 자동으로 사라짐.
 *
 * 의존: 없음 (자체 fetch).
 * 주입 위치: <body> 최상단 (header 위).
 */
(function () {
    if (window.__aisbBetaBanner) return;
    window.__aisbBetaBanner = true;

    function inject(message) {
        // 이미 reader 등에 자체 베타 표시가 있으면 중복 방지
        if (document.getElementById('aisb-beta-banner') ||
            document.getElementById('beta-flag')) return;

        const style = document.createElement('style');
        style.textContent = `
            #aisb-beta-banner {
                background: linear-gradient(90deg, #d4af37 0%, #b8941f 100%);
                color: #0a192f;
                text-align: center;
                font-family: 'Noto Sans KR', sans-serif;
                font-size: 0.78rem;
                font-weight: 700;
                letter-spacing: 0.08rem;
                padding: 0.5rem 1rem;
                position: relative;
                z-index: 200;
                box-shadow: 0 1px 4px rgba(0,0,0,0.1);
            }
            #aisb-beta-banner .close {
                position: absolute;
                right: 1rem;
                top: 50%;
                transform: translateY(-50%);
                background: rgba(10,25,47,0.15);
                border: none;
                color: #0a192f;
                width: 22px;
                height: 22px;
                border-radius: 50%;
                cursor: pointer;
                font-size: 0.85rem;
                line-height: 1;
                display: inline-flex;
                align-items: center;
                justify-content: center;
            }
            #aisb-beta-banner .close:hover { background: rgba(10,25,47,0.3); }
            @media (max-width: 720px) {
                #aisb-beta-banner { font-size: 0.7rem; padding: 0.45rem 2rem 0.45rem 0.6rem; }
            }
        `;
        document.head.appendChild(style);

        const div = document.createElement('div');
        div.id = 'aisb-beta-banner';
        div.innerHTML = `
            ${message}
            <button class="close" type="button" aria-label="닫기">×</button>
        `;
        if (document.body.firstChild) {
            document.body.insertBefore(div, document.body.firstChild);
        } else {
            document.body.appendChild(div);
        }

        // 세션 동안 한 번 닫기
        if (sessionStorage.getItem('aisb_beta_dismissed') === '1') {
            div.style.display = 'none';
        }
        div.querySelector('.close').addEventListener('click', () => {
            div.style.display = 'none';
            sessionStorage.setItem('aisb_beta_dismissed', '1');
        });
    }

    function loadAndInject() {
        const isPreview = /\/preview\//.test(location.pathname);
        const url = (isPreview ? '../' : '') + 'site_config.json';
        fetch(url)
            .then(r => r.ok ? r.json() : null)
            .then(cfg => {
                if (!cfg || !cfg.free_beta) return;
                const msg = cfg.free_beta_message ||
                    '무료 베타 운영 중 — 정식 오픈 전, 모든 본문을 자유롭게 보실 수 있습니다';
                inject(msg);
            })
            .catch(() => {});
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadAndInject);
    } else {
        loadAndInject();
    }
})();
