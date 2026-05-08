/**
 * 본문 뷰어 (Stage 4 — 무료 베타).
 *
 * URL: reader.html?id={book_id}[&p=preview]
 *   ?id=s2-001 …    본권 (epubs 버킷)
 *   ?id=s2-001&p=preview …  미리보기 (previews 버킷, 인증 불필요)
 *
 * 동작:
 *   1) site_config + books_master 로드
 *   2) book_id 매칭 → epub URL 결정
 *      - p=preview : preview_path 공개 URL
 *      - 본권      : free_beta=true 면 epubs 직접 SELECT (anon). 아니면 signed URL (Auth 필요)
 *   3) epub.js 렌더 (페이징, 글자크기, 다크/라이트, 진도 저장)
 */
(function () {
    const params = new URLSearchParams(location.search);
    const bookId = params.get('id');
    const isPreview = params.get('p') === 'preview';

    const stage = document.getElementById('reader-area');
    const loadingEl = document.getElementById('loading-state');
    const errorEl = document.getElementById('error-state');
    const errorMsgEl = document.getElementById('error-msg');
    const titleTextEl = document.getElementById('reader-title-text');
    const titleMetaEl = document.getElementById('reader-title-meta');
    const navPrev = document.getElementById('nav-prev');
    const navNext = document.getElementById('nav-next');
    const progressFill = document.getElementById('progress-fill');
    const fontDownBtn = document.getElementById('font-down');
    const fontUpBtn = document.getElementById('font-up');
    const themeBtn = document.getElementById('theme-toggle');
    const toolHomeBtn = document.getElementById('tool-home');
    const immersiveBtn = document.getElementById('tool-immersive');
    const immersiveExitBtn = document.getElementById('immersive-exit');
    const betaFlag = document.getElementById('beta-flag');
    const tocBtn = document.getElementById('tool-toc');
    const tocPanel = document.getElementById('toc-panel');
    const tocOverlay = document.getElementById('toc-overlay');
    const tocCloseBtn = document.getElementById('toc-close');
    const tocListEl = document.getElementById('toc-list');

    let book = null;
    let rendition = null;
    let supabaseClient = null;
    let cfg = null;
    let bookData = null;
    let fontSize = parseInt(localStorage.getItem('aisb_reader_font') || '110', 10);  // %
    let darkMode = localStorage.getItem('aisb_reader_dark') === '1';
    let immersive = localStorage.getItem('aisb_reader_immersive') === '1';

    // 진도 저장 키. catalog 와 공유 (window.AISB_PROGRESS_KEY 동일 규칙).
    const progressKey = 'aisb_reader_cfi_' + bookId + (isPreview ? '_p' : '');
    const progressPctKey = 'aisb_reader_pct_' + bookId + (isPreview ? '_p' : '');
    const lastReadKey = 'aisb_reader_lastread_' + bookId + (isPreview ? '_p' : '');

    function showError(msg) {
        loadingEl.style.display = 'none';
        errorEl.style.display = 'flex';
        errorMsgEl.textContent = msg;
        console.error('[reader]', msg);
    }

    function setLoadingMsg(msg) {
        const p = loadingEl.querySelector('p');
        if (p) p.textContent = msg;
        console.log('[reader]', msg);
    }

    function applyDark() {
        if (darkMode) {
            document.body.classList.add('dark');
            themeBtn.textContent = '낮';
            themeBtn.classList.add('active');
            if (rendition) {
                rendition.themes.override('color', '#e8e1d2');
                rendition.themes.override('background', '#14222e');
            }
        } else {
            document.body.classList.remove('dark');
            themeBtn.textContent = '밤';
            themeBtn.classList.remove('active');
            if (rendition) {
                rendition.themes.override('color', '#2c3e50');
                rendition.themes.override('background', '#fdfbf7');
            }
        }
    }

    function applyFont() {
        if (rendition) rendition.themes.fontSize(fontSize + '%');
    }

    async function loadConfig() {
        const r = await fetch('site_config.json').catch(() => null);
        if (!r || !r.ok) throw new Error('설정을 불러올 수 없습니다');
        return r.json();
    }

    async function loadMaster() {
        const r = await fetch('books_master.json').catch(() => null);
        if (!r || !r.ok) throw new Error('도서 정보를 불러올 수 없습니다');
        return r.json();
    }

    function findBook(master, id) {
        const items = master.books || [];
        return items.find(b => b.id === id || b.book_id === id);
    }

    function publicUrl(path) {
        if (!cfg || !path) return null;
        return `${cfg.supabase_url}/storage/v1/object/public/${path}`;
    }

    function getClient() {
        if (supabaseClient) return supabaseClient;
        if (!cfg || !cfg.supabase_url || !cfg.supabase_anon_key) return null;
        if (typeof window.supabase === 'undefined' || !window.supabase.createClient) return null;
        supabaseClient = window.supabase.createClient(cfg.supabase_url, cfg.supabase_anon_key, {
            auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
        });
        return supabaseClient;
    }

    async function getEpubUrl(b) {
        if (isPreview) {
            const u = publicUrl(b.preview_path);
            if (u) return u;
            // fallback: previews/<id>.epub
            return publicUrl(`previews/${b.id || b.book_id}.epub`);
        }
        // 본권
        if (cfg.free_beta) {
            // anon SELECT 허용된 상태라면 createSignedUrl 또는 public URL 둘 다 가능
            const c = getClient();
            const path = (b.epub_path || `epubs/${b.id || b.book_id}.epub`).replace(/^epubs\//, '');
            if (c) {
                const { data, error } = await c.storage.from('epubs').createSignedUrl(path, 60 * 30);
                if (!error && data && data.signedUrl) return data.signedUrl;
            }
            // signed 실패 시 public URL 시도 (버킷이 public 으로 전환됐을 수도)
            return publicUrl(b.epub_path || `epubs/${b.id || b.book_id}.epub`);
        }
        // 정식 오픈 후: 인증된 사용자 + 구매자만
        const c = getClient();
        if (!c) return null;
        const { data: { user } } = await c.auth.getUser();
        if (!user) {
            showError('로그인이 필요합니다. 로그인하신 뒤 다시 열어주세요.');
            return null;
        }
        const path = (b.epub_path || `epubs/${b.id || b.book_id}.epub`).replace(/^epubs\//, '');
        const { data, error } = await c.storage.from('epubs').createSignedUrl(path, 60 * 30);
        if (error) {
            showError('본문 접근 권한이 없습니다. 구매하신 뒤 다시 열어주세요.');
            return null;
        }
        return data.signedUrl;
    }

    // "← 책 목록" 링크들에 focus={bookId} 붙여서 catalog 가 그 책 위치로 스크롤하게 함
    function attachFocusToCatalogLinks() {
        if (!bookId) return;
        const focus = encodeURIComponent(bookId);
        document.querySelectorAll('a[href="/catalog"], a[href="catalog.html"]').forEach(a => {
            a.href = `/catalog?focus=${focus}`;
        });
    }

    async function init() {
        if (!bookId) {
            showError('책 식별자가 없습니다. URL 을 확인해 주세요.');
            return;
        }
        attachFocusToCatalogLinks();

        try {
            cfg = await loadConfig();
            const master = await loadMaster();
            bookData = findBook(master, bookId);
            if (!bookData) {
                showError(`'${bookId}' 책을 찾을 수 없습니다.`);
                return;
            }

            // 헤더 업데이트
            titleTextEl.textContent = bookData.title || bookId;
            const metaParts = [];
            if (bookData.season) metaParts.push(`시즌 ${bookData.season}`);
            if (bookData.group_code) metaParts.push(bookData.group_code);
            if (isPreview) metaParts.push('미리보기');
            titleMetaEl.textContent = metaParts.length ? '· ' + metaParts.join(' · ') : '';
            document.title = `${bookData.title} — AI 시대 영성`;

            if (cfg.free_beta && !isPreview) {
                betaFlag.style.display = 'block';
            }

            setLoadingMsg('본문 주소를 받고 있습니다…');
            const url = await getEpubUrl(bookData);
            if (!url) return;  // showError already called

            // 라이브러리 로드 확인
            if (typeof ePub === 'undefined') {
                showError('뷰어 라이브러리를 불러오지 못했습니다. 페이지를 새로고침해 주세요.');
                return;
            }

            // fetch로 직접 받아 ArrayBuffer 로 epub.js 에 전달 (가장 안정적)
            setLoadingMsg('본문을 내려받고 있습니다…');
            let arrayBuffer;
            try {
                const resp = await fetch(url, { credentials: 'omit' });
                if (!resp.ok) {
                    showError(`본문 받기 실패 (HTTP ${resp.status}). 잠시 후 다시 시도해 주세요.`);
                    return;
                }
                arrayBuffer = await resp.arrayBuffer();
                if (!arrayBuffer || arrayBuffer.byteLength < 1024) {
                    showError('본문 파일이 비어 있습니다.');
                    return;
                }
                console.log('[reader] epub bytes:', arrayBuffer.byteLength);
            } catch (e) {
                console.error(e);
                showError('네트워크 오류로 본문을 받지 못했습니다: ' + (e.message || e));
                return;
            }

            // epub.js 로드
            setLoadingMsg('본문을 펼치고 있습니다…');
            book = ePub(arrayBuffer);
            rendition = book.renderTo('reader-area', {
                width: '100%',
                height: '100%',
                spread: 'none',           // 단일 페이지 (모바일 친화 + 표지 처리 자연스러움)
                manager: 'default',
                allowScriptedContent: false,
            });

            // 본문 가운데 1/3 탭으로 집중 모드 토글, 좌측 1/3 = 이전, 우측 1/3 = 다음
            // 모바일 친화 패턴 (Kindle·iBooks). epub.js content hook 으로 iframe 안 click 잡음
            rendition.hooks.content.register((contents) => {
                contents.document.addEventListener('click', (e) => {
                    // 텍스트 선택 중이면 무시
                    const sel = contents.document.getSelection();
                    if (sel && sel.toString().length > 0) return;
                    // 링크·버튼은 default 유지
                    let t = e.target;
                    while (t && t !== contents.document.body) {
                        const tn = t.tagName;
                        if (tn === 'A' || tn === 'BUTTON' || tn === 'INPUT' || tn === 'IMG') return;
                        t = t.parentNode;
                    }
                    const w = contents.document.documentElement.clientWidth;
                    const x = e.clientX;
                    const ratio = x / w;
                    if (ratio < 0.33) rendition.prev();
                    else if (ratio > 0.67) rendition.next();
                    else toggleImmersive();
                });
            });

            // 진도 복원: lastCfi 가 있으면 첫 display 부터 그 위치로.
            // 그래야 "첫 페이지 잠깐 → 점프" 깜빡임 없음.
            const lastCfi = localStorage.getItem(progressKey);
            const restoredPct = parseFloat(localStorage.getItem(progressPctKey) || '0');

            // 5초 안에 display 안 끝나면 안내 메시지
            let renderPromise;
            if (lastCfi) {
                renderPromise = rendition.display(lastCfi).catch(() => rendition.display());
            } else {
                renderPromise = rendition.display();
            }
            const timeoutId = setTimeout(() => {
                setLoadingMsg('본문을 펼치는 데 시간이 걸리고 있습니다…');
            }, 5000);
            try {
                await renderPromise;
            } catch (e) {
                console.error(e);
                showError('본문을 펼치지 못했습니다: ' + (e.message || e));
                clearTimeout(timeoutId);
                return;
            }
            clearTimeout(timeoutId);

            loadingEl.style.display = 'none';
            navPrev.style.display = 'block';
            navNext.style.display = 'block';

            // 진도가 복원됐으면 토스트로 안내 + "처음부터" 버튼
            if (lastCfi) {
                showRestoreToast(restoredPct);
            }

            // 진도 저장 + 진행률
            book.ready.then(() => book.locations.generate(1500)).then(() => {
                rendition.on('relocated', (loc) => {
                    if (loc && loc.start) {
                        localStorage.setItem(progressKey, loc.start.cfi);
                        localStorage.setItem(lastReadKey, String(Date.now()));
                        highlightCurrentToc(loc.start.href);
                    }
                    const pct = (loc && loc.start && loc.start.percentage) || 0;
                    progressFill.style.width = (pct * 100).toFixed(1) + '%';
                    if (pct > 0) {
                        localStorage.setItem(progressPctKey, pct.toFixed(4));
                    }
                });
            }).catch(() => {});

            // 목차 로드
            book.loaded.navigation.then((nav) => {
                renderToc(nav.toc);
            }).catch((err) => {
                console.warn('[reader] 목차 로딩 실패', err);
                tocListEl.innerHTML = '<p style="padding:1.2rem; color:var(--text-muted); font-size:0.85rem;">이 책은 목차 정보가 없습니다.</p>';
            });

            applyFont();
            applyDark();
        } catch (e) {
            console.error(e);
            showError(e.message || '본문 로딩 중 오류가 발생했습니다.');
        }
    }

    // 네비게이션
    navPrev.addEventListener('click', () => rendition && rendition.prev());
    navNext.addEventListener('click', () => rendition && rendition.next());
    document.addEventListener('keydown', (e) => {
        if (!rendition) return;
        if (e.key === 'ArrowLeft') rendition.prev();
        if (e.key === 'ArrowRight') rendition.next();
    });

    // 글자 크기
    fontDownBtn.addEventListener('click', () => {
        fontSize = Math.max(80, fontSize - 10);
        localStorage.setItem('aisb_reader_font', fontSize);
        applyFont();
    });
    fontUpBtn.addEventListener('click', () => {
        fontSize = Math.min(200, fontSize + 10);
        localStorage.setItem('aisb_reader_font', fontSize);
        applyFont();
    });

    // 다크 토글
    themeBtn.addEventListener('click', () => {
        darkMode = !darkMode;
        localStorage.setItem('aisb_reader_dark', darkMode ? '1' : '0');
        applyDark();
    });

    // ─── 목차 ───────────────────────────────────────────
    function escapeHtml(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function buildTocList(items) {
        if (!items || !items.length) return '';
        return '<ul>' + items.map(it => {
            const sub = (it.subitems && it.subitems.length) ? buildTocList(it.subitems) : '';
            return `<li data-href="${escapeHtml(it.href || '')}"><a href="#" data-href="${escapeHtml(it.href || '')}">${escapeHtml(it.label.trim())}</a>${sub}</li>`;
        }).join('') + '</ul>';
    }

    function resolveSpineHref(href) {
        if (!book || !book.spine || !book.spine.spineItems || !href) return href;
        const base = href.split('#')[0];
        // 정확 매칭, 끝부분 매칭, basename 매칭 순으로 탐색
        const items = book.spine.spineItems;
        let hit = items.find(it => it.href === base);
        if (hit) return hit.href;
        hit = items.find(it => it.href.endsWith('/' + base) || it.href.endsWith(base));
        if (hit) return hit.href;
        const baseName = base.split('/').pop();
        hit = items.find(it => (it.href.split('/').pop() === baseName));
        return hit ? hit.href : href;
    }

    function renderToc(toc) {
        if (!toc || !toc.length) {
            tocListEl.innerHTML = '<p style="padding:1.2rem; color:var(--text-muted); font-size:0.85rem;">이 책은 목차 정보가 없습니다.</p>';
            return;
        }
        tocListEl.innerHTML = buildTocList(toc);
        tocListEl.querySelectorAll('a[data-href]').forEach(a => {
            a.addEventListener('click', (e) => {
                e.preventDefault();
                const href = a.getAttribute('data-href');
                if (rendition && href) {
                    const target = resolveSpineHref(href);
                    console.log('[reader] toc click', href, '->', target);
                    rendition.display(target).catch(err => {
                        console.error('[reader] display 실패', err);
                    });
                    closeToc();
                }
            });
        });
    }

    function highlightCurrentToc(href) {
        if (!href || !tocListEl) return;
        tocListEl.querySelectorAll('li').forEach(li => li.classList.remove('current'));
        // href 가 #fragment 포함 시 baseHref 까지만 비교
        const base = href.split('#')[0];
        const li = tocListEl.querySelector(`li[data-href^="${base}"]`);
        if (li) li.classList.add('current');
    }

    function openToc() {
        tocPanel.classList.add('open');
        tocOverlay.classList.add('open');
        tocPanel.setAttribute('aria-hidden', 'false');
    }
    function closeToc() {
        tocPanel.classList.remove('open');
        tocOverlay.classList.remove('open');
        tocPanel.setAttribute('aria-hidden', 'true');
    }
    if (tocBtn) tocBtn.addEventListener('click', () => {
        if (tocPanel.classList.contains('open')) closeToc(); else openToc();
    });
    if (tocCloseBtn) tocCloseBtn.addEventListener('click', closeToc);
    if (tocOverlay) tocOverlay.addEventListener('click', closeToc);
    document.addEventListener('keydown', (e) => {
        if (e.key !== 'Escape') return;
        if (tocPanel.classList.contains('open')) {
            closeToc();
        } else {
            toggleImmersive();
        }
    });

    // ─── 읽기 집중 모드 ─────────────────────────────────
    function applyImmersive() {
        if (immersive) {
            document.body.classList.add('immersive');
            if (immersiveBtn) {
                immersiveBtn.classList.add('active');
                immersiveBtn.textContent = '⛶ 해제';
            }
        } else {
            document.body.classList.remove('immersive');
            if (immersiveBtn) {
                immersiveBtn.classList.remove('active');
                immersiveBtn.textContent = '⛶ 집중';
            }
        }
        // epub.js 가 컨테이너 크기 변화에 즉시 반응하도록 resize 이벤트
        if (rendition) {
            try { rendition.resize(); } catch (e) {}
        }
    }
    function toggleImmersive() {
        immersive = !immersive;
        localStorage.setItem('aisb_reader_immersive', immersive ? '1' : '0');
        applyImmersive();
    }
    if (immersiveBtn) immersiveBtn.addEventListener('click', toggleImmersive);
    if (immersiveExitBtn) immersiveExitBtn.addEventListener('click', toggleImmersive);
    // 페이지 로드 직후 한 번 적용 (저장된 상태 복원)
    applyImmersive();

    // 처음으로 (책의 첫 페이지)
    function goHome() {
        if (!book) return;
        // 진도 초기화 (이 책만)
        localStorage.removeItem(progressKey);
        localStorage.removeItem(progressPctKey);
        localStorage.removeItem(lastReadKey);
        const spine = book.spine && book.spine.spineItems;
        if (spine && spine.length > 0) {
            rendition.display(spine[0].href);
        } else {
            rendition.display();
        }
    }
    if (toolHomeBtn) toolHomeBtn.addEventListener('click', goHome);

    // ─── 진도 복원 토스트 ─────────────────────────────────
    function showRestoreToast(pct) {
        let toast = document.getElementById('restore-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'restore-toast';
            toast.className = 'restore-toast';
            document.body.appendChild(toast);
        }
        const pctText = pct > 0
            ? Math.max(1, Math.round(pct * 100)) + '% 지점'
            : '이전 위치';
        toast.innerHTML = `
            <span class="restore-toast-msg">${pctText}부터 이어서 봅니다</span>
            <button type="button" class="restore-toast-btn" id="restore-toast-home">처음부터</button>
            <button type="button" class="restore-toast-close" id="restore-toast-close" title="닫기">×</button>
        `;
        toast.classList.add('show');
        const homeBtn = toast.querySelector('#restore-toast-home');
        const closeBtn = toast.querySelector('#restore-toast-close');
        if (homeBtn) homeBtn.addEventListener('click', () => {
            goHome();
            hideRestoreToast();
        });
        if (closeBtn) closeBtn.addEventListener('click', hideRestoreToast);
        // 8초 후 자동 사라짐
        clearTimeout(showRestoreToast._t);
        showRestoreToast._t = setTimeout(hideRestoreToast, 8000);
    }
    function hideRestoreToast() {
        const toast = document.getElementById('restore-toast');
        if (toast) toast.classList.remove('show');
    }

    init();
})();
