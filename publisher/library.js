/**
 * 내 서가 페이지 (Stage 2).
 *
 * 로직:
 *   1. 로그인 상태 확인
 *      - 비로그인 → 로그인 안내 + 로그인 모달 (auth.js)
 *      - 로그인됨 → bookshelf 조회
 *   2. bookshelf JOIN books → 카드 그리드 렌더링
 *   3. 미리보기 = 공개 URL 다운로드. 본권 = signed URL (Stage 3 활성화 후)
 *
 * 의존:
 *   - auth.js (Supabase 클라이언트 초기화)
 *   - site_config.json (supabase_url, supabase_anon_key, purchase_enabled)
 */
(function () {
    const main = document.getElementById('lib-main');

    let supabase = null;
    let cfg = null;

    async function loadConfig() {
        if (cfg) return cfg;
        cfg = await fetch('site_config.json').then(r => r.json()).catch(() => null);
        return cfg;
    }

    async function getClient() {
        if (supabase) return supabase;
        const c = await loadConfig();
        if (!c || !c.supabase_url || !c.supabase_anon_key) return null;
        if (typeof window.supabase === 'undefined' || !window.supabase.createClient) {
            return null;
        }
        supabase = window.supabase.createClient(c.supabase_url, c.supabase_anon_key, {
            auth: {
                persistSession: true,
                autoRefreshToken: true,
                detectSessionInUrl: true,
            },
        });
        return supabase;
    }

    function htmlEscape(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    // 본문 뷰어 진도 (catalog·reader 와 같은 키 규칙)
    function readProgress(id) {
        try {
            const cfi = localStorage.getItem('aisb_reader_cfi_' + id);
            if (!cfi) return 0;
            const pct = parseFloat(localStorage.getItem('aisb_reader_pct_' + id) || '0');
            return pct > 0 ? pct : 0.01;
        } catch (e) { return 0; }
    }

    function applyReadProgress() {
        document.querySelectorAll('.lib-card-progress[data-progress-for]').forEach(el => {
            const id = el.dataset.progressFor;
            const pct = readProgress(id);
            if (pct > 0) {
                const pctText = Math.max(1, Math.round(pct * 100)) + '%';
                const fill = el.querySelector('.lib-card-progress-fill');
                const text = el.querySelector('.lib-card-progress-text');
                if (fill) fill.style.width = pctText;
                if (text) text.textContent = '이어보기 ' + pctText;
                el.hidden = false;
            } else {
                el.hidden = true;
            }
        });
    }

    function renderEmptyState(loggedIn) {
        if (!loggedIn) {
            main.innerHTML = `
                <div class="lib-state">
                    <h3>로그인이 필요합니다</h3>
                    <p>
                        구매하신 책은 사용자 계정에 묶여 있어 어느 기기에서든 같은 서가가 보입니다.<br>
                        이메일 매직 링크로 30초 안에 로그인하실 수 있습니다.
                    </p>
                    <button class="cta" id="lib-login-cta">로그인 / 가입</button>
                    <a href="/catalog" class="cta secondary">먼저 카탈로그 둘러보기</a>
                </div>
            `;
            const btn = document.getElementById('lib-login-cta');
            btn.addEventListener('click', () => {
                if (window.aisbAuth && window.aisbAuth.openLogin) {
                    window.aisbAuth.openLogin();
                }
            });
            return;
        }
        // 로그인 + 빈 서가
        main.innerHTML = `
            <div class="lib-state">
                <h3>아직 서가에 책이 없습니다</h3>
                <p>
                    카탈로그에서 마음에 드는 책을 둘러보세요.<br>
                    정식 구매 기능은 통신판매업 신고증 발급 후 활성화됩니다.
                </p>
                <a href="/catalog" class="cta">전체 도서 카탈로그</a>
            </div>
        `;
    }

    function publicCoverUrl(book) {
        if (!cfg || !book) return '';
        if (book.cover_path) {
            return `${cfg.supabase_url}/storage/v1/object/public/${book.cover_path}`;
        }
        return `covers/${book.book_id}.jpg`;
    }

    function publicPreviewUrl(book) {
        if (!cfg || !book || !book.preview_path) return '';
        return `${cfg.supabase_url}/storage/v1/object/public/${book.preview_path}`;
    }

    async function getSignedEpubUrl(book) {
        const c = await getClient();
        if (!c || !book.epub_path) return null;
        const path = book.epub_path.replace(/^epubs\//, '');
        const { data, error } = await c.storage.from('epubs')
            .createSignedUrl(path, 60 * 30);  // 30분
        if (error) {
            console.error('signed URL 발급 실패', error);
            return null;
        }
        return data.signedUrl;
    }

    function lastReadAt(id) {
        try {
            const v = parseInt(localStorage.getItem('aisb_reader_lastread_' + id) || '0', 10);
            return isFinite(v) ? v : 0;
        } catch (e) { return 0; }
    }

    function sortRows(rows, mode) {
        const arr = rows.slice();
        switch (mode) {
            case 'resume':
                arr.sort((x, y) => {
                    const a = x.books, b = y.books;
                    if (!a || !b) return 0;
                    const pa = readProgress(a.book_id);
                    const pb = readProgress(b.book_id);
                    if ((pa > 0) !== (pb > 0)) return pa > 0 ? -1 : 1;
                    if (pa > 0 && pb > 0) {
                        const ta = lastReadAt(a.book_id);
                        const tb = lastReadAt(b.book_id);
                        if (ta !== tb) return tb - ta;
                    }
                    return new Date(y.added_at) - new Date(x.added_at);
                });
                break;
            case 'title-asc':
                arr.sort((x, y) => (x.books?.title || '').localeCompare(y.books?.title || '', 'ko'));
                break;
            case 'pubdate-desc':
                arr.sort((x, y) => (y.books?.published_at || '').localeCompare(x.books?.published_at || ''));
                break;
            case 'added-desc':
            default:
                arr.sort((x, y) => new Date(y.added_at) - new Date(x.added_at));
                break;
        }
        return arr;
    }

    let _shelfRows = [];
    let _sortMode = (function () {
        try { return localStorage.getItem('aisb_lib_sort') || 'added-desc'; } catch (e) { return 'added-desc'; }
    })();

    function renderShelf(rows) {
        const stats = document.getElementById('lib-stats');
        const count = document.getElementById('lib-count');
        if (stats && count) {
            stats.style.display = 'inline-flex';
            count.textContent = rows.length;
        }
        const toolbar = document.getElementById('lib-toolbar');
        if (toolbar) toolbar.style.display = '';
        _shelfRows = rows;
        rows = sortRows(rows, _sortMode);

        const purchaseEnabled = cfg && cfg.purchase_enabled;
        const freeBeta = cfg && cfg.free_beta;
        const epubButtonLabel = purchaseEnabled ? '본권 받기' : '본권 (준비 중)';

        const html = rows.map(r => {
            const b = r.books;
            if (!b) return '';
            const cover = publicCoverUrl(b);
            const previewOk = !!b.preview_path;
            const meta = [
                b.season ? `시즌 ${b.season}` : '',
                b.group_code || '',
            ].filter(Boolean).join(' · ');
            const status = r.read_status === 'read' ? '읽음' :
                           r.read_status === 'reading' ? '읽는 중' :
                           r.last_read_at ? '읽는 중' : '신규';
            const readBtn = freeBeta
                ? `<a class="lib-card-btn primary" href="/reader?id=${htmlEscape(b.book_id)}">본문 보기</a>`
                : '';
            return `
                <div class="lib-card" data-book-id="${htmlEscape(b.book_id)}">
                    <div class="lib-card-cover" style="background-image:url('${htmlEscape(cover)}')"></div>
                    <div class="lib-card-body">
                        <span class="lib-card-status">${htmlEscape(status)}</span>
                        <div class="lib-card-title">${htmlEscape(b.title)}</div>
                        <div class="lib-card-meta">${htmlEscape(meta)}</div>
                        <div class="lib-card-progress" data-progress-for="${htmlEscape(b.book_id)}" hidden>
                            <div class="lib-card-progress-bar"><div class="lib-card-progress-fill"></div></div>
                            <span class="lib-card-progress-text">이어보기 0%</span>
                        </div>
                        <div class="lib-card-actions">
                            ${readBtn}
                            ${previewOk ? `<a class="lib-card-btn" href="${htmlEscape(publicPreviewUrl(b))}" download>미리보기</a>` : ''}
                            ${freeBeta ? '' : `<button class="lib-card-btn primary epub-btn" ${purchaseEnabled ? '' : 'disabled'}>${htmlEscape(epubButtonLabel)}</button>`}
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        main.innerHTML = `<div class="lib-grid">${html}</div>`;
        applyReadProgress();

        // 본권 받기 버튼 → signed URL 열기 (purchase_enabled일 때만)
        main.querySelectorAll('.epub-btn:not([disabled])').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const card = e.target.closest('.lib-card');
                const id = card.getAttribute('data-book-id');
                const row = rows.find(r => r.books && r.books.book_id === id);
                if (!row) return;
                btn.disabled = true;
                btn.textContent = '발급 중…';
                try {
                    const u = await getSignedEpubUrl(row.books);
                    if (u) {
                        window.open(u, '_blank');
                    } else {
                        alert('다운로드 링크 발급에 실패했습니다.');
                    }
                } finally {
                    btn.disabled = !cfg.purchase_enabled;
                    btn.textContent = epubButtonLabel;
                }
            });
        });
    }

    async function loadShelf() {
        const c = await getClient();
        if (!c) {
            main.innerHTML = '<div class="lib-state"><p>설정을 불러오지 못했습니다.</p></div>';
            return;
        }

        const { data: { user } } = await c.auth.getUser();
        if (!user) {
            renderEmptyState(false);
            return;
        }

        const { data, error } = await c.from('bookshelf')
            .select('id, added_at, last_read_at, read_status, books(*)')
            .order('added_at', { ascending: false });

        if (error) {
            main.innerHTML = `
                <div class="lib-state">
                    <h3>서가를 불러올 수 없습니다</h3>
                    <p>${htmlEscape(error.message || '알 수 없는 오류')}</p>
                </div>
            `;
            return;
        }

        if (!data || data.length === 0) {
            renderEmptyState(true);
            return;
        }

        renderShelf(data);
    }

    // 정렬 드롭다운
    document.addEventListener('DOMContentLoaded', () => {
        const sel = document.getElementById('lib-sort');
        if (!sel) return;
        sel.value = _sortMode;
        sel.addEventListener('change', (e) => {
            _sortMode = e.target.value;
            try { localStorage.setItem('aisb_lib_sort', _sortMode); } catch (e) {}
            if (_shelfRows.length) renderShelf(_shelfRows);
        });
    });

    // 인증 상태 변화 시 자동 갱신
    window.addEventListener('aisbAuthChanged', () => {
        loadShelf();
    });

    // 다른 탭/뷰어에서 진도 변경 시 게이지만 갱신
    window.addEventListener('storage', (e) => {
        if (!e.key) return;
        if (e.key.startsWith('aisb_reader_')) applyReadProgress();
    });
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) applyReadProgress();
    });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadShelf);
    } else {
        loadShelf();
    }
})();
