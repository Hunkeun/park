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
    const backBtn = document.getElementById('tool-back');

    let book = null;
    let rendition = null;
    let supabaseClient = null;
    let cfg = null;
    let bookData = null;

    // ─── 표지 overlay ───────────────────────────────────────────────
    // epub.js 의 ZIP 내부 image 자원 매핑이 이 환경에서 깨져 cover.xhtml 이
    // 빈 페이지로 뜬다. 표지를 epub.js iframe 밖에서 reader 가 자체 div 로
    // 표시하고, 사용자가 탭하면 epub.js 의 spine[1] (판권/서두) 부터 펼친다.
    const coverOverlay = document.createElement('div');
    coverOverlay.id = 'cover-overlay';
    coverOverlay.style.cssText = (
        'position:absolute;inset:0;background:#fdfbf7;' +
        'display:none;flex-direction:column;align-items:center;justify-content:center;' +
        'padding:1.5rem;box-sizing:border-box;z-index:5;cursor:pointer;'
    );
    coverOverlay.innerHTML = (
        '<img id="cover-overlay-img" alt="표지" ' +
            'style="max-width:100%;max-height:80vh;width:auto;height:auto;object-fit:contain;' +
            'box-shadow:0 12px 40px rgba(0,0,0,0.25);border-radius:4px;display:block;" />' +
        '<div style="margin-top:1.5rem;color:#777;font-size:0.85rem;letter-spacing:0.05rem;">' +
            '탭하여 본문 보기' +
        '</div>'
    );
    const coverOverlayImg = coverOverlay.querySelector('#cover-overlay-img');
    if (stage && stage.parentElement) stage.parentElement.appendChild(coverOverlay);

    function showCoverOverlay() {
        if (!coverOverlay || !bookId) return;
        if (coverOverlayImg && !coverOverlayImg.getAttribute('src')) {
            coverOverlayImg.src = `/covers/${bookId}.jpg`;
        }
        coverOverlay.style.display = 'flex';
    }
    function hideCoverOverlay() {
        if (coverOverlay) coverOverlay.style.display = 'none';
    }
    if (coverOverlay) {
        coverOverlay.addEventListener('click', () => {
            hideCoverOverlay();
            // 사용자가 spine[1] 위치에 있을 때만 의미. 이미 display 되어 있으므로 hide 만.
        });
    }
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
                const resp = await fetch(url, { credentials: 'omit', cache: 'no-cache' });
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

            // epub.js 로드. flow:'scrolled-doc' = 한 챕터를 세로 스크롤로 펼침.
            // 모바일·확대 환경 친화 (네이티브 스크롤로 본문 어디든 접근 가능).
            // 좌우 화살표·푸터 버튼은 챕터 단위 이동.
            setLoadingMsg('본문을 펼치고 있습니다…');
            book = ePub(arrayBuffer);
            rendition = book.renderTo('reader-area', {
                width: '100%',
                height: '100%',
                flow: 'scrolled-doc',
                manager: 'default',
                allowScriptedContent: true,
            });

            // 본문 안 짧은 클릭(드래그·선택 아님)은 집중 모드 토글로 매핑.
            // 좌/우 1/3 페이지 넘김은 스크롤 모드와 충돌해 제거.
            rendition.hooks.content.register((contents) => {
                let downX = 0, downY = 0, downT = 0;
                contents.document.addEventListener('mousedown', (e) => {
                    downX = e.clientX; downY = e.clientY; downT = Date.now();
                });
                contents.document.addEventListener('click', (e) => {
                    // 텍스트 선택 중이면 무시
                    const sel = contents.document.getSelection();
                    if (sel && sel.toString().length > 0) return;
                    // 링크·버튼·이미지는 default 유지
                    let t = e.target;
                    while (t && t !== contents.document.body) {
                        const tn = t.tagName;
                        if (tn === 'A' || tn === 'BUTTON' || tn === 'INPUT' || tn === 'IMG') return;
                        t = t.parentNode;
                    }
                    // 길게 눌렀거나 이동했으면 스크롤 의도로 보고 무시 (집중 모드 토글 안 함)
                    const dt = Date.now() - downT;
                    const dx = Math.abs(e.clientX - downX);
                    const dy = Math.abs(e.clientY - downY);
                    if (dt > 300 || dx > 6 || dy > 6) return;
                    toggleImmersive();
                });
            });

            // 진도 복원: lastCfi 가 있으면 첫 display 부터 그 위치로.
            // 그래야 "첫 페이지 잠깐 → 점프" 깜빡임 없음.
            const lastCfi = localStorage.getItem(progressKey);
            const restoredPct = parseFloat(localStorage.getItem(progressPctKey) || '0');

            // 5초 안에 display 안 끝나면 안내 메시지
            // spine[0] = cover.xhtml 은 epub.js 의 ZIP image 자원 매핑이 환경에 따라
            // 깨져 빈 페이지로 표시되는 경우가 있다. 사용자는 catalog 에서 표지를 보고
            // 진입하므로 책 안에서는 spine[1] (판권/서두) 부터 시작하는 게 자연스럽다.
            const spineItems = (book.spine && book.spine.spineItems) || [];
            const firstHref = spineItems.length > 1 ? spineItems[1].href : undefined;

            // 첫 spine render 즉시 감지: cover.xhtml 이면 overlay 표시
            // (relocated 이벤트는 book.locations.generate 후 등록되어 첫 화면 놓침)
            rendition.on('rendered', (section) => {
                const href = (section && section.href) || '';
                if (href.includes('cover.xhtml')) {
                    showCoverOverlay();
                }
            });
            let renderPromise;
            if (lastCfi) {
                renderPromise = rendition.display(lastCfi).catch(() => rendition.display(firstHref))
                    .then(() => {
                        // 복원 위치가 표지면 overlay 자동 표시
                        const loc = rendition.currentLocation && rendition.currentLocation();
                        const href = (loc && loc.start && loc.start.href) || '';
                        if (href.includes('cover.xhtml')) showCoverOverlay();
                    });
            } else {
                // 첫 진입: epub.js 는 spine[1] 부터 펼치고 사용자에게는 표지 overlay
                renderPromise = rendition.display(firstHref).then(() => showCoverOverlay());
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

            // 진도 저장 + 진행률.
            // scrolled-doc 모드에서는 페이지 개념이 없고 spine(챕터) 단위. 챕터가 바뀌면
            // 사용자가 점프했거나 TTS 가 자동 진행한 것 — TTS 자동진행 아니면 정지.
            let lastSpineHref = null;
            book.ready.then(() => book.locations.generate(1500)).then(() => {
                rendition.on('relocated', (loc) => {
                    if (loc && loc.start) {
                        // cover spine 위치는 lastCfi 에 저장 안 함 (다음 진입 때 빈 페이지로 복원되는 회귀 방지)
                        if (!(loc.start.href || '').includes('cover.xhtml')) {
                            localStorage.setItem(progressKey, loc.start.cfi);
                        }
                        localStorage.setItem(lastReadKey, String(Date.now()));
                        highlightCurrentToc(loc.start.href);
                        const ttsActive = (ttsState === 'playing' || ttsState === 'paused');
                        if (lastSpineHref && loc.start.href !== lastSpineHref &&
                            ttsActive && !ttsAdvancing) {
                            ttsCancel();
                            setTtsBtnState('idle');
                            showTtsStoppedToast();
                        }
                        lastSpineHref = loc.start.href;
                        // 표지 spine 으로 이동하면 (toc 클릭 등) overlay 로 가린다
                        if ((loc.start.href || '').includes('cover.xhtml')) {
                            showCoverOverlay();
                        } else {
                            hideCoverOverlay();
                        }
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

    // 네비게이션 — scrolled-doc 모드는 spine(챕터) 단위 이동.
    // 큰 점프이므로 jumpStack 에 직전 위치 저장 → "↶ 이전 위치" 로 복귀 가능.
    function jumpPrevChapter() {
        if (!rendition) return;
        pushJump();
        rendition.prev();
    }
    function jumpNextChapter() {
        if (!rendition) return;
        pushJump();
        rendition.next();
    }
    navPrev.addEventListener('click', jumpPrevChapter);
    navNext.addEventListener('click', jumpNextChapter);
    const footerPrevBtn = document.getElementById('footer-prev');
    const footerNextBtn = document.getElementById('footer-next');
    if (footerPrevBtn) footerPrevBtn.addEventListener('click', jumpPrevChapter);
    if (footerNextBtn) footerNextBtn.addEventListener('click', jumpNextChapter);
    document.addEventListener('keydown', (e) => {
        if (!rendition) return;
        // 위/아래 키는 브라우저 기본 스크롤. 좌우 키만 챕터 이동.
        if (e.key === 'ArrowLeft') jumpPrevChapter();
        if (e.key === 'ArrowRight') jumpNextChapter();
    });

    // ─── 점프 히스토리 (목차/책 처음 같은 큰 점프만 스택, 한 페이지 이동은 미적용) ───
    const JUMP_STACK_MAX = 10;
    const jumpStack = [];

    function getCurrentCfi() {
        try {
            const loc = rendition && rendition.currentLocation && rendition.currentLocation();
            if (loc && loc.start && loc.start.cfi) return loc.start.cfi;
        } catch (e) {}
        return null;
    }
    function pushJump() {
        const cfi = getCurrentCfi();
        if (!cfi) return;
        if (jumpStack.length && jumpStack[jumpStack.length - 1] === cfi) return;
        jumpStack.push(cfi);
        if (jumpStack.length > JUMP_STACK_MAX) jumpStack.shift();
        updateBackBtn();
    }
    function popJump() {
        if (!jumpStack.length || !rendition) return;
        const cfi = jumpStack.pop();
        rendition.display(cfi).catch(() => {});
        updateBackBtn();
    }
    function updateBackBtn() {
        if (!backBtn) return;
        backBtn.disabled = jumpStack.length === 0;
    }
    if (backBtn) backBtn.addEventListener('click', popJump);

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
                    pushJump();
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

    // 처음으로 (책의 첫 페이지). 진도는 그대로 두고 위치만 이동, 직전 위치를 점프 스택에 보관해
    // ↶ 이전 위치 로 다시 돌아올 수 있게 한다.
    function goHome() {
        if (!book || !rendition) return;
        pushJump();
        const spine = book.spine && book.spine.spineItems;
        if (spine && spine.length > 0) {
            // spine[0] (cover) 는 빈 페이지로 떠 사용자 혼란. spine[1] 부터 보여줌.
            const idx = spine.length > 1 ? 1 : 0;
            rendition.display(spine[idx].href).catch(() => {});
            if (idx === 1) showCoverOverlay();
        } else {
            rendition.display().catch(() => {});
        }
    }
    if (toolHomeBtn) toolHomeBtn.addEventListener('click', goHome);

    // ─── 본문 읽어주기 (Web Speech API TTS) ─────────────────
    // 챕터(spine item) 단위로 텍스트를 가져와 문장 단위로 발화.
    // 한 문장 끝나면 다음 문장. 챕터 끝나면 rendition.next() 로 spine 진행.
    // 일시정지/재개·속도 변경 지원. 한국어 음성 우선 선택.
    const ttsBtn = document.getElementById('tool-tts');
    const ttsRateBtn = document.getElementById('tool-tts-rate');
    const ttsRateDownBtn = document.getElementById('tool-tts-down');
    const ttsRateUpBtn = document.getElementById('tool-tts-up');
    const TTS_SUPPORTED = typeof window.speechSynthesis !== 'undefined' &&
                          typeof window.SpeechSynthesisUtterance !== 'undefined';
    const TTS_RATE_MIN = 0.5;
    const TTS_RATE_MAX = 2.5;
    const TTS_RATE_STEP = 0.1;
    let ttsState = 'idle';   // 'idle' | 'playing' | 'paused'
    let ttsRate = parseFloat(localStorage.getItem('aisb_reader_tts_rate') || '1.0');
    if (!isFinite(ttsRate)) ttsRate = 1.0;
    ttsRate = Math.max(TTS_RATE_MIN, Math.min(TTS_RATE_MAX, Math.round(ttsRate * 10) / 10));
    let ttsQueue = [];
    let ttsIdx = 0;
    let ttsCurrentUtter = null;
    let ttsKoVoice = null;
    let ttsAdvancing = false;       // 챕터 자동 진행 중
    let ttsCurrentSpineHref = null;

    function ttsAvailable() {
        if (!TTS_SUPPORTED) return false;
        return !!rendition;
    }
    function pickKoreanVoice() {
        if (!TTS_SUPPORTED) return null;
        const voices = window.speechSynthesis.getVoices() || [];
        // 우선순위: ko-KR > ko > 한국어 표시
        return voices.find(v => /^ko-KR/i.test(v.lang))
            || voices.find(v => /^ko/i.test(v.lang))
            || voices.find(v => /korean|한국/i.test(v.name))
            || null;
    }
    function ensureKoVoice() {
        if (ttsKoVoice) return;
        ttsKoVoice = pickKoreanVoice();
    }
    if (TTS_SUPPORTED) {
        // voices 는 비동기 로드되는 경우가 있어 이벤트로도 받음
        window.speechSynthesis.onvoiceschanged = () => { ttsKoVoice = pickKoreanVoice(); };
        ensureKoVoice();
    }

    function getCurrentChapterText() {
        // 현재 챕터(spine item) 본문 텍스트.
        // 블록 요소(제목·단락·인용·리스트)를 명시적으로 순회해 단락 경계를 \n\n 으로
        // 보존한다. innerText 한 번 호출로는 단락 경계가 \n 1 개로 평탄해져 TTS 가
        // 단락 사이 호흡을 잡지 못하는 케이스가 있다.
        if (!rendition || typeof rendition.getContents !== 'function') return '';
        const arr = rendition.getContents();
        if (!arr || !arr.length) return '';
        const SEL = 'h1,h2,h3,h4,h5,h6,p,li,blockquote';
        const parts = [];
        for (const c of arr) {
            try {
                const body = c.document && c.document.body;
                if (!body) continue;
                const blocks = body.querySelectorAll(SEL);
                const lines = [];
                for (const el of blocks) {
                    // 중첩된 블록은 부모 처리 시 같이 들어가므로 직계만 처리.
                    let p = el.parentElement;
                    let nested = false;
                    while (p && p !== body) {
                        if (p.matches && p.matches(SEL)) { nested = true; break; }
                        p = p.parentElement;
                    }
                    if (nested) continue;
                    const t = (el.textContent || '').replace(/\s+/g, ' ').trim();
                    if (!t) continue;
                    // 제목은 끝에 마침표를 보강해 utter 종결을 또렷하게 한다.
                    const isHeading = /^H[1-6]$/.test(el.tagName);
                    lines.push(isHeading && !/[.!?。!?…]$/.test(t) ? t + '.' : t);
                }
                if (lines.length) parts.push(lines.join('\n\n'));
                else parts.push((body.innerText || body.textContent || '').trim());
            } catch (e) {}
        }
        return parts.join('\n\n').trim();
    }
    // 성경 인용 표기를 자연스러운 한국어로 풀어 쓴다 (TTS 발화용 전처리).
    // EPUB 본문은 그대로 두고, 발화 직전 텍스트만 변환.
    // 예: "사도행전 2:7-9" -> "사도행전 이장 칠절부터 구절"
    //     "시편 23:1"     -> "시편 이십삼편 일절"   (시편은 "장" 대신 "편")
    const BIBLE_BOOKS = [
        '창세기','출애굽기','레위기','민수기','신명기','여호수아','사사기','룻기',
        '사무엘상','사무엘하','열왕기상','열왕기하','역대상','역대하','에스라','느헤미야',
        '에스더','욥기','시편','잠언','전도서','아가','이사야','예레미야애가','예레미야',
        '에스겔','다니엘','호세아','요엘','아모스','오바댜','요나','미가','나훔','하박국',
        '스바냐','학개','스가랴','말라기',
        '마태복음','마가복음','누가복음','요한복음','사도행전','로마서',
        '고린도전서','고린도후서','갈라디아서','에베소서','빌립보서','골로새서',
        '데살로니가전서','데살로니가후서','디모데전서','디모데후서','디도서','빌레몬서',
        '히브리서','야고보서','베드로전서','베드로후서',
        '요한일서','요한이서','요한삼서','유다서','요한계시록',
    ];
    // 긴 이름이 먼저 매칭되도록 정렬 (예: "예레미야애가" > "예레미야", "고린도전서" > "고린도")
    const BIBLE_BOOK_PAT = new RegExp(
        '(' + [...BIBLE_BOOKS].sort((a, b) => b.length - a.length).join('|') + ')'
        + '\\s*(\\d{1,3})\\s*[:：]\\s*(\\d{1,3})(?:\\s*[-–~−]\\s*(\\d{1,3}))?(?:\\s*절)?',
        'g'
    );
    const KO_DIGIT = ['영','일','이','삼','사','오','육','칠','팔','구'];
    function koreanNumber(n) {
        if (!isFinite(n) || n < 0) return String(n);
        if (n === 0) return '영';
        const ones = ['', '일','이','삼','사','오','육','칠','팔','구'];
        function below10000(num) {
            // 0~9999 한자어 변환 (한 자리 = '한' 같은 고유어 안 씀, 모두 한자어)
            if (num === 0) return '';
            let r = '';
            const t = Math.floor(num / 1000);
            const h = Math.floor((num % 1000) / 100);
            const tn = Math.floor((num % 100) / 10);
            const o = num % 10;
            if (t) r += (t === 1 ? '' : ones[t]) + '천';
            if (h) r += (h === 1 ? '' : ones[h]) + '백';
            if (tn) r += (tn === 1 ? '' : ones[tn]) + '십';
            if (o) r += ones[o];
            return r;
        }
        if (n < 10000) return below10000(n);
        if (n < 100000000) {
            const man = Math.floor(n / 10000);
            const rest = n % 10000;
            return below10000(man) + '만' + (rest ? below10000(rest) : '');
        }
        if (n < 1000000000000) {
            const eok = Math.floor(n / 100000000);
            const restAfterEok = n % 100000000;
            let r = below10000(eok) + '억';
            if (restAfterEok) {
                const man = Math.floor(restAfterEok / 10000);
                const sub = restAfterEok % 10000;
                if (man) r += below10000(man) + '만';
                if (sub) r += below10000(sub);
            }
            return r;
        }
        return String(n);
    }
    // 자연 호흡 보강: 접속사 앞에 쉼표를 자동 삽입.
    // OS TTS 가 쉼표·마침표에서 자연 쉼을 주므로, 본문에 호흡 부호가 부족할 때 발화 직전 보강한다.
    // 본문은 안 건드림 (검색·인쇄에는 원래 표기 유지).
    const TTS_CONJUNCTIONS = [
        '그러나','그렇지만','하지만','그런데',
        '그리고','그래서','따라서','그러므로','그러니까',
        '또한','또는','혹은','즉','곧',
        '한편','반면','다만','단',
        '게다가','더욱이','오히려','결국','마침내','결과적으로',
        '예를 들면','예컨대','다시 말해','말하자면',
    ];
    const TTS_CONJ_PAT = new RegExp(
        // 직전이 구두점·따옴표·괄호·문장 시작이 아니면(즉 평문 흐름 중간이면) 쉼표 삽입
        '(?<![,。.!?;:"\'\\)\\(\\[\\]「」『』·\\s—–\\-])\\s+(' +
        TTS_CONJUNCTIONS.map(c => c.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|') +
        ')(?=[\\s,])',
        'g'
    );
    function ttsPreprocess(text) {
        if (!text) return text;
        // 1) 줄바꿈 정규화 (탭 → 공백). 단락 경계 \n\n 은 그대로 두고 splitSentences
        //    가 1차 분할 기준으로 사용 → 단락 사이를 별 utterance 로 발화해 자연 쉼.
        let out = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').replace(/\t+/g, ' ');
        // 2) 성경 인용 한자어 한글 변환
        out = out.replace(BIBLE_BOOK_PAT, (m, book, chap, verse, verseEnd) => {
            const unit = (book === '시편') ? '편' : '장';
            const head = `${book} ${koreanNumber(parseInt(chap, 10))}${unit} ${koreanNumber(parseInt(verse, 10))}절`;
            if (verseEnd) return `${head}부터 ${koreanNumber(parseInt(verseEnd, 10))}절`;
            return head;
        });
        // 3) 영문 표제 한국어 변환 ("Chapter 03" → "삼장", "BOOK 01" → "일권", "PART 1" → "일부")
        out = out.replace(/\bChapter\.?\s*(\d+)\b/gi, (_, n) => `${koreanNumber(parseInt(n, 10))}장`);
        out = out.replace(/\bCh\.?\s*(\d+)\b/gi, (_, n) => `${koreanNumber(parseInt(n, 10))}장`);
        out = out.replace(/\bBOOK\.?\s*(\d+)\b/gi, (_, n) => `${koreanNumber(parseInt(n, 10))}권`);
        out = out.replace(/\bPART\.?\s*(\d+)\b/gi, (_, n) => `${koreanNumber(parseInt(n, 10))}부`);
        // 4) 일반 아라비아 숫자 → 한자어 한글 (소수점 먼저 처리)
        out = out.replace(/(\d+)\.(\d+)/g, (_, ip, dp) => {
            const i = parseInt(ip, 10);
            const intK = isFinite(i) ? koreanNumber(i) : ip;
            const decK = dp.split('').map(d => KO_DIGIT[parseInt(d, 10)] || d).join('');
            return intK + '점' + decK;
        });
        out = out.replace(/(\d+)/g, (m) => {
            const n = parseInt(m, 10);
            if (!isFinite(n) || n > 999999999999) return m;
            return koreanNumber(n);
        });
        // 5) 접속사 앞에 쉼표 삽입 (이미 구두점이 있으면 건너뜀)
        out = out.replace(TTS_CONJ_PAT, ', $1');
        // 6) 중복 마침표 정리. 단, 단락 경계로 만든 ". . " 시퀀스는 공백을 사이에 둔
        //    별 utterance 분리 신호이므로 합치지 않는다 (정규식이 공백 없는 ".." 만 매치).
        out = out.replace(/\.{2}(?!\.)/g, '.');
        // 5) 마침표·쉼표 뒤 공백 보장 (드물지만 안전망)
        out = out.replace(/([.,!?])([^\s,.!?…\)\]"'」』])/g, '$1 $2');
        // 6) 연속 공백 정리
        out = out.replace(/[  ]{2,}/g, ' ').trim();
        return out;
    }

    function splitSentences(text) {
        // 단락 경계(\n{2,}) 1차 분할 후, 각 단락 안에서만 종결부호 기준으로 합친다.
        // 단락 사이는 절대 합치지 않음 → 별 utterance 로 발화돼 자연 쉼이 들어간다.
        if (!text) return [];
        const SOFT = 80;
        const HARD = 240;
        const merged = [];
        const paragraphs = text.split(/\n{2,}/).map(p => p.trim()).filter(Boolean);
        for (const para of paragraphs) {
            const raw = para.split(/(?<=[\.!?。!?…])\s+|\n+/).map(s => s.trim()).filter(Boolean);
            let buf = '';
            for (const s of raw) {
                if (!buf) { buf = s; continue; }
                if (buf.length < SOFT) { buf += ' ' + s; continue; }
                if ((buf + ' ' + s).length <= HARD) { buf += ' ' + s; continue; }
                merged.push(buf);
                buf = s;
            }
            if (buf) merged.push(buf);
        }
        return merged;
    }
    function setTtsBtnState(state) {
        ttsState = state;
        if (!ttsBtn) return;
        if (state === 'playing') {
            ttsBtn.textContent = '⏸ 듣기';
            ttsBtn.classList.add('playing');
            ttsBtn.title = '일시정지';
        } else if (state === 'paused') {
            ttsBtn.textContent = '▶ 듣기';
            ttsBtn.classList.add('playing');
            ttsBtn.title = '재개';
        } else {
            ttsBtn.textContent = '🔊 듣기';
            ttsBtn.classList.remove('playing');
            ttsBtn.title = '본문 읽어주기';
        }
    }
    function ttsCancel() {
        try { window.speechSynthesis.cancel(); } catch (e) {}
        ttsCurrentUtter = null;
        ttsQueue = [];
        ttsIdx = 0;
    }
    function ttsLoadCurrentChapterQueue() {
        const text = getCurrentChapterText();
        ttsQueue = splitSentences(text);
        ttsIdx = 0;
    }
    function ttsSpeakNext() {
        if (ttsState !== 'playing') return;
        if (ttsIdx >= ttsQueue.length) {
            // 챕터 끝 — 다음 챕터로 이동 후 새 큐로 이어감
            ttsAdvancing = true;
            const beforeSpine = ttsCurrentSpineHref;
            rendition.next().then(() => {
                setTimeout(() => {
                    ttsAdvancing = false;
                    if (ttsState !== 'playing') return;
                    const after = getCurrentSpineHref();
                    if (after && after !== beforeSpine) {
                        ttsCurrentSpineHref = after;
                        ttsLoadCurrentChapterQueue();
                        if (!ttsQueue.length) { setTtsBtnState('idle'); return; }
                        ttsSpeakNext();
                    } else {
                        setTtsBtnState('idle');   // 더 갈 곳 없음
                    }
                }, 350);
            }).catch(() => {
                ttsAdvancing = false;
                setTtsBtnState('idle');
            });
            return;
        }
        const text = ttsQueue[ttsIdx++];
        if (!text) { ttsSpeakNext(); return; }
        const spoken = ttsPreprocess(text);
        const u = new SpeechSynthesisUtterance(spoken);
        u.lang = 'ko-KR';
        ensureKoVoice();
        if (ttsKoVoice) u.voice = ttsKoVoice;
        u.rate = ttsRate;
        u.pitch = 1.0;
        u.volume = 1.0;
        u.onend = () => {
            if (ttsState === 'playing') ttsSpeakNext();
        };
        u.onerror = (ev) => {
            console.warn('[reader] tts error', ev && ev.error);
            if (ttsState === 'playing') ttsSpeakNext();
        };
        ttsCurrentUtter = u;
        try { window.speechSynthesis.speak(u); } catch (e) {
            console.error('[reader] tts speak 실패', e);
            setTtsBtnState('idle');
        }
    }
    function getCurrentSpineHref() {
        try {
            const loc = rendition && rendition.currentLocation && rendition.currentLocation();
            if (loc && loc.start && loc.start.href) return loc.start.href;
        } catch (e) {}
        return null;
    }
    function ttsStartFromCurrentChapter() {
        ttsCurrentSpineHref = getCurrentSpineHref();
        ttsLoadCurrentChapterQueue();
        if (!ttsQueue.length) {
            setTtsBtnState('idle');
            return;
        }
        setTtsBtnState('playing');
        ttsSpeakNext();
    }
    function ttsToggle() {
        if (!ttsAvailable()) return;
        if (ttsState === 'idle') {
            try { window.speechSynthesis.cancel(); } catch (e) {}
            ttsStartFromCurrentChapter();
        } else if (ttsState === 'playing') {
            try { window.speechSynthesis.pause(); } catch (e) {}
            setTtsBtnState('paused');
        } else if (ttsState === 'paused') {
            try { window.speechSynthesis.resume(); } catch (e) {}
            setTtsBtnState('playing');
        }
    }
    function ttsSetRate(newRate) {
        const clamped = Math.max(TTS_RATE_MIN, Math.min(TTS_RATE_MAX, Math.round(newRate * 10) / 10));
        if (clamped === ttsRate) {
            updateRateButtons();
            return;
        }
        ttsRate = clamped;
        localStorage.setItem('aisb_reader_tts_rate', String(ttsRate));
        updateRateButtons();
        // 즉시 반영은 하지 않음 — 다음 문장부터 새 rate 적용.
        // (cancel + setTimeout 으로 즉시 갈아끼우면 일부 OS TTS 에서 비동기 경합으로 침묵 발생)
        // 사용자 체감: 라벨은 즉시 바뀌고, 보통 5~10초 안에 다음 문장에서 새 속도로 들림.
    }
    function updateRateButtons() {
        if (ttsRateBtn) ttsRateBtn.textContent = ttsRate.toFixed(1) + 'x';
        if (ttsRateDownBtn) ttsRateDownBtn.disabled = ttsRate <= TTS_RATE_MIN + 1e-6;
        if (ttsRateUpBtn) ttsRateUpBtn.disabled = ttsRate >= TTS_RATE_MAX - 1e-6;
    }

    // 초기 버튼 상태
    updateRateButtons();
    if (!TTS_SUPPORTED) {
        if (ttsBtn) {
            ttsBtn.disabled = true;
            ttsBtn.title = '이 브라우저는 음성 읽기를 지원하지 않습니다';
        }
        if (ttsRateBtn) ttsRateBtn.disabled = true;
        if (ttsRateDownBtn) ttsRateDownBtn.disabled = true;
        if (ttsRateUpBtn) ttsRateUpBtn.disabled = true;
    } else {
        if (ttsBtn) ttsBtn.addEventListener('click', ttsToggle);
        // 라벨 탭 = 1.0x 리셋
        if (ttsRateBtn) ttsRateBtn.addEventListener('click', () => ttsSetRate(1.0));
        if (ttsRateDownBtn) ttsRateDownBtn.addEventListener('click', () => ttsSetRate(ttsRate - TTS_RATE_STEP));
        if (ttsRateUpBtn) ttsRateUpBtn.addEventListener('click', () => ttsSetRate(ttsRate + TTS_RATE_STEP));
        // 페이지 떠날 때 음성 정지
        window.addEventListener('pagehide', () => { try { window.speechSynthesis.cancel(); } catch (e) {} });
        window.addEventListener('beforeunload', () => { try { window.speechSynthesis.cancel(); } catch (e) {} });
    }

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

    // TTS 가 페이지 이동으로 자동 중지됐을 때 사용자에게 짧게 안내. 같은 .restore-toast
    // 스타일 재사용.
    function showTtsStoppedToast() {
        let toast = document.getElementById('tts-stopped-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'tts-stopped-toast';
            toast.className = 'restore-toast';
            document.body.appendChild(toast);
        }
        toast.innerHTML = (
            '<span class="restore-toast-msg">페이지를 넘기셔서 본문 읽기를 멈췄어요</span>' +
            '<button type="button" class="restore-toast-close" id="tts-stopped-close" title="닫기">×</button>'
        );
        toast.classList.add('show');
        const closeBtn = toast.querySelector('#tts-stopped-close');
        if (closeBtn) closeBtn.addEventListener('click', () => toast.classList.remove('show'));
        clearTimeout(showTtsStoppedToast._t);
        showTtsStoppedToast._t = setTimeout(() => toast.classList.remove('show'), 4000);
    }

    init();
})();
