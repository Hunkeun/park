/**
 * 장바구니 (Phase 1 — 송금 + 카카오톡 신청용).
 *
 * 모든 페이지에 include되어 자동으로:
 * - localStorage 'aisb_cart'에 권 ID 배열 저장
 * - 우측 가운데 floating 카운터 버튼 주입
 * - 클릭 시 장바구니 모달 (권 목록·합계·카톡 신청)
 * - 카톡 신청 → 주문 메시지 클립보드 자동 복사 + 카카오 채널 열기
 *
 * 페이지에서 "장바구니 담기" 버튼만 따로 만들어 cartAdd(id)·cartRemove(id)·cartHas(id) 호출.
 * cart 상태 변하면 'cartChanged' 이벤트 발생 → 페이지가 자기 버튼 라벨 업데이트.
 *
 * 사용:
 *   <script src="cart.js" defer></script>           (catalog · index)
 *   <script src="../cart.js" defer></script>        (preview)
 */
(function () {
    const CART_KEY = 'aisb_cart';
    const KAKAO_URL = 'https://pf.kakao.com/_PxdHTX';
    const ACCOUNT_LINE = '농협 351-3386-4491-83 박헌근(AI 시대 영성)';

    // ─── localStorage ───────────────────────────────────────────
    function readIds() {
        try {
            const raw = localStorage.getItem(CART_KEY);
            if (!raw) return [];
            const obj = JSON.parse(raw);
            return Array.isArray(obj.ids) ? obj.ids : [];
        } catch (e) { return []; }
    }
    function writeIds(ids) {
        try {
            localStorage.setItem(CART_KEY, JSON.stringify({ ids }));
        } catch (e) { /* 무시 */ }
        window.dispatchEvent(new CustomEvent('cartChanged', { detail: { ids } }));
    }
    window.cartIds = readIds;
    window.cartHas = function (id) { return readIds().includes(id); };
    window.cartCount = function () { return readIds().length; };
    window.cartAdd = function (id) {
        const ids = readIds();
        if (!ids.includes(id)) ids.push(id);
        writeIds(ids);
    };
    window.cartRemove = function (id) {
        writeIds(readIds().filter(x => x !== id));
    };
    window.cartClear = function () { writeIds([]); };

    // ─── books_master.json fetch ────────────────────────────────
    let booksPromise = null;
    function getBooks() {
        if (booksPromise) return booksPromise;
        const isPreview = /\/preview\//.test(location.pathname);
        const url = (isPreview ? '../' : '') + 'books_master.json';
        booksPromise = fetch(url).then(r => r.json()).then(m => {
            const map = {};
            (m.books || []).forEach(b => { map[b.id] = b; });
            return map;
        }).catch(() => ({}));
        return booksPromise;
    }

    // ─── site_config.json fetch ─────────────────────────────────
    let cfgPromise = null;
    function getConfig() {
        if (cfgPromise) return cfgPromise;
        const isPreview = /\/preview\//.test(location.pathname);
        const url = (isPreview ? '../' : '') + 'site_config.json';
        cfgPromise = fetch(url).then(r => r.ok ? r.json() : null).then(c => {
            return c || { purchase_enabled: true };
        }).catch(() => ({ purchase_enabled: true }));
        return cfgPromise;
    }

    // ─── 우측 floating 카운터 버튼 ──────────────────────────────
    function injectStyles() {
        if (document.getElementById('cart-styles')) return;
        const css = document.createElement('style');
        css.id = 'cart-styles';
        css.textContent = `
            #cartFab {
                position: fixed; right: 1rem; top: 50%;
                transform: translateY(-50%); z-index: 9997;
                background: #0a192f; color: #d4af37;
                border: 1px solid rgba(212,175,55,0.5);
                border-radius: 4px; padding: 0.7rem 0.95rem;
                font-family: 'Noto Sans KR', sans-serif;
                font-size: 0.78rem; font-weight: 600; letter-spacing: 0.05rem;
                cursor: pointer; box-shadow: 0 4px 14px rgba(0,0,0,0.25);
                display: flex; flex-direction: column; align-items: center; gap: 0.2rem;
                line-height: 1.2; transition: transform 0.2s, box-shadow 0.2s;
                user-select: none;
            }
            #cartFab:hover { transform: translateY(-50%) scale(1.05); box-shadow: 0 6px 20px rgba(0,0,0,0.35); }
            #cartFab .cart-label { font-size: 0.66rem; color: rgba(255,255,255,0.7); letter-spacing: 0.15rem; }
            #cartFab .cart-num { font-size: 1.05rem; color: #d4af37; font-weight: 700; }
            #cartFab[data-empty="1"] { background: rgba(10,25,47,0.7); }
            #cartFab[data-empty="1"] .cart-num { color: rgba(212,175,55,0.55); }

            #cartModalBg {
                position: fixed; inset: 0; background: rgba(10,25,47,0.85);
                z-index: 9998; display: none; align-items: center; justify-content: center;
                padding: 2rem;
            }
            #cartModalBg.active { display: flex; }
            #cartModal {
                background: #fff; border-radius: 6px; max-width: 560px; width: 100%;
                max-height: 86vh; overflow-y: auto;
                font-family: 'Noto Serif KR', serif; color: #2c3e50;
                box-shadow: 0 24px 60px rgba(0,0,0,0.5); position: relative;
            }
            #cartModal .cm-head {
                padding: 1.6rem 2rem 1rem; border-bottom: 1px solid rgba(10,25,47,0.08);
                display: flex; align-items: baseline; justify-content: space-between; gap: 1rem;
            }
            #cartModal .cm-head h2 {
                font-family: 'Playfair Display', serif; font-size: 1.4rem; color: #0a192f;
            }
            #cartModal .cm-close {
                background: none; border: none; font-size: 1.5rem; cursor: pointer;
                color: rgba(10,25,47,0.5); position: absolute; top: 1rem; right: 1.2rem;
            }
            #cartModal .cm-close:hover { color: #0a192f; }
            #cartModal .cm-list {
                list-style: none; margin: 0; padding: 0.5rem 0;
            }
            #cartModal .cm-item {
                padding: 0.9rem 2rem; display: flex; align-items: center; gap: 1rem;
                border-bottom: 1px solid rgba(10,25,47,0.06); font-size: 0.9rem;
            }
            #cartModal .cm-item img {
                width: 42px; height: 60px; object-fit: cover; border-radius: 2px;
                box-shadow: 0 3px 8px rgba(0,0,0,0.18); flex-shrink: 0;
            }
            #cartModal .cm-item .cm-meta { flex: 1; min-width: 0; }
            #cartModal .cm-item .cm-meta strong {
                display: block; font-weight: 600; font-size: 0.93rem; color: #0a192f;
                margin-bottom: 0.15rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
            }
            #cartModal .cm-item .cm-meta span {
                font-family: 'Noto Sans KR', sans-serif; font-size: 0.72rem;
                color: #5d6d7e; letter-spacing: 0.08rem;
            }
            #cartModal .cm-item .cm-price {
                font-family: 'Playfair Display', serif; font-weight: 700;
                color: #d4af37; font-size: 1rem; flex-shrink: 0;
            }
            #cartModal .cm-item button.cm-rm {
                background: none; border: 1px solid rgba(10,25,47,0.15);
                width: 26px; height: 26px; border-radius: 50%; cursor: pointer;
                color: rgba(10,25,47,0.5); font-size: 0.85rem; flex-shrink: 0;
                display: inline-flex; align-items: center; justify-content: center;
                padding: 0;
            }
            #cartModal .cm-item button.cm-rm:hover { background: #c4302b; color: #fff; border-color: #c4302b; }
            #cartModal .cm-empty {
                text-align: center; padding: 3rem 2rem;
                color: rgba(10,25,47,0.5);
                font-family: 'Noto Sans KR', sans-serif; font-size: 0.92rem;
            }
            #cartModal .cm-foot {
                padding: 1.2rem 2rem 1.6rem; border-top: 1px solid rgba(10,25,47,0.08);
            }
            #cartModal .cm-total {
                display: flex; justify-content: space-between; align-items: baseline;
                margin-bottom: 1rem;
            }
            #cartModal .cm-total .label {
                font-family: 'Noto Sans KR', sans-serif; font-size: 0.78rem;
                letter-spacing: 0.2rem; color: #5d6d7e; text-transform: uppercase;
            }
            #cartModal .cm-total .num {
                font-family: 'Playfair Display', serif; font-size: 1.55rem;
                color: #d4af37; font-weight: 700;
            }
            #cartModal .cm-actions { display: flex; gap: 0.6rem; flex-wrap: wrap; }
            #cartModal .cm-btn {
                font-family: 'Noto Sans KR', sans-serif; font-size: 0.86rem;
                font-weight: 600; padding: 0.85rem 1.3rem; border-radius: 2px;
                cursor: pointer; letter-spacing: 0.08rem; text-decoration: none;
                border: 1px solid transparent; transition: all 0.2s;
                display: inline-flex; align-items: center; justify-content: center;
            }
            #cartModal .cm-btn.kakao {
                background: #fee500; color: #3c1e1e; flex: 1; min-width: 200px;
            }
            #cartModal .cm-btn.kakao:hover { background: #ffd900; }
            #cartModal .cm-btn.kakao:disabled { opacity: 0.4; cursor: not-allowed; }
            #cartModal .cm-btn.outline {
                background: transparent; border-color: rgba(10,25,47,0.2); color: #0a192f;
            }
            #cartModal .cm-btn.outline:hover { border-color: #c4302b; color: #c4302b; }
            #cartModal .cm-note {
                margin-top: 1rem; font-family: 'Noto Sans KR', sans-serif;
                font-size: 0.76rem; color: #5d6d7e; line-height: 1.6;
            }
            #cartModal .cm-banner {
                background: #fff8e1; border-left: 3px solid #d4af37;
                padding: 0.85rem 1.1rem;
                font-family: 'Noto Sans KR', sans-serif;
                font-size: 0.85rem; color: #5d4f3a; line-height: 1.7;
                margin: 0 2rem 1rem;
                border-radius: 2px;
            }
            #cartModal .cm-toast {
                position: fixed; bottom: 1.5rem; left: 50%; transform: translateX(-50%);
                background: #0a192f; color: #d4af37;
                padding: 0.85rem 1.4rem; border-radius: 4px;
                font-family: 'Noto Sans KR', sans-serif; font-size: 0.86rem;
                box-shadow: 0 10px 24px rgba(0,0,0,0.4); z-index: 10000;
                opacity: 0; transition: opacity 0.25s;
                pointer-events: none;
            }
            #cartModal .cm-toast.show { opacity: 1; }

            @media (max-width: 720px) {
                #cartFab { right: 0.6rem; padding: 0.55rem 0.75rem; }
                #cartFab .cart-label { font-size: 0.6rem; }
                #cartFab .cart-num { font-size: 0.95rem; }
                #cartModal .cm-item { padding: 0.8rem 1.2rem; }
                #cartModal .cm-head, #cartModal .cm-foot { padding-left: 1.2rem; padding-right: 1.2rem; }
            }
        `;
        document.head.appendChild(css);
    }

    function renderFab() {
        if (document.getElementById('cartFab')) return;
        const fab = document.createElement('button');
        fab.id = 'cartFab';
        fab.type = 'button';
        fab.title = '장바구니 보기';
        fab.innerHTML = `<span class="cart-label">CART</span><span class="cart-num">0</span>`;
        fab.addEventListener('click', openCart);
        document.body.appendChild(fab);
        updateFab();
    }

    function updateFab() {
        const fab = document.getElementById('cartFab');
        if (!fab) return;
        const n = readIds().length;
        fab.querySelector('.cart-num').textContent = n;
        fab.dataset.empty = n === 0 ? '1' : '0';
    }

    // ─── 모달 ───────────────────────────────────────────────────
    function renderModalShell() {
        if (document.getElementById('cartModalBg')) return;
        const bg = document.createElement('div');
        bg.id = 'cartModalBg';
        bg.innerHTML = `
            <div id="cartModal">
                <button class="cm-close" type="button" aria-label="닫기">×</button>
                <div class="cm-head">
                    <h2>장바구니</h2>
                </div>
                <div class="cm-banner" id="cartBanner" style="display:none"></div>
                <ul class="cm-list" id="cartList"></ul>
                <div class="cm-empty" id="cartEmpty" style="display:none">
                    장바구니가 비어 있습니다.<br>마음에 드는 책을 담아주세요.
                </div>
                <div class="cm-foot">
                    <div class="cm-total">
                        <span class="label">합계 (<span id="cartCnt">0</span>권)</span>
                        <span class="num"><span id="cartSum">0</span>원</span>
                    </div>
                    <div class="cm-actions">
                        <button type="button" class="cm-btn kakao" id="cartOrder">카카오톡으로 주문하기</button>
                        <button type="button" class="cm-btn outline" id="cartClearBtn">비우기</button>
                    </div>
                    <p class="cm-note">
                        ① "주문하기" 클릭 → 주문 내역이 클립보드에 자동 복사 + 카카오톡 채널이 열립니다.<br>
                        ② 채팅창에 붙여넣기 + 이메일 주소 적어 보내주세요.<br>
                        ③ ${ACCOUNT_LINE}로 송금 → 확인 후 EPUB 이메일 발송.
                    </p>
                </div>
                <div class="cm-toast" id="cartToast"></div>
            </div>
        `;
        bg.addEventListener('click', e => { if (e.target === bg) closeCart(); });
        bg.querySelector('.cm-close').addEventListener('click', closeCart);
        bg.querySelector('#cartClearBtn').addEventListener('click', () => {
            if (readIds().length === 0) return;
            if (confirm('장바구니를 비울까요?')) window.cartClear();
        });
        bg.querySelector('#cartOrder').addEventListener('click', orderViaKakao);
        document.body.appendChild(bg);
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape' && bg.classList.contains('active')) closeCart();
        });
    }

    function openCart() {
        renderModalShell();
        refreshCart();
        document.getElementById('cartModalBg').classList.add('active');
        document.body.style.overflow = 'hidden';
    }
    function closeCart() {
        const bg = document.getElementById('cartModalBg');
        if (bg) bg.classList.remove('active');
        document.body.style.overflow = '';
    }
    window.openCart = openCart;
    window.closeCart = closeCart;

    function refreshCart() {
        const ids = readIds();
        const list = document.getElementById('cartList');
        const empty = document.getElementById('cartEmpty');
        const cnt = document.getElementById('cartCnt');
        const sum = document.getElementById('cartSum');
        const order = document.getElementById('cartOrder');
        const banner = document.getElementById('cartBanner');
        if (!list) return;

        Promise.all([getBooks(), getConfig()]).then(([books, cfg]) => {
            list.innerHTML = '';
            let total = 0;
            const validIds = [];
            ids.forEach(id => {
                const b = books[id];
                if (!b) return;
                validIds.push(id);
                total += (b.price || 0);
                const li = document.createElement('li');
                li.className = 'cm-item';
                const isPreview = /\/preview\//.test(location.pathname);
                const cover = (isPreview ? '../' : '') + 'covers/' + id + '.jpg';
                li.innerHTML = `
                    <img src="${cover}" alt="">
                    <div class="cm-meta">
                        <strong>${escapeHtml(b.title)}</strong>
                        <span>${b.isbn || ''}</span>
                    </div>
                    <span class="cm-price">${(b.price || 0).toLocaleString()}원</span>
                    <button type="button" class="cm-rm" aria-label="제거" data-id="${id}">×</button>
                `;
                list.appendChild(li);
            });

            list.querySelectorAll('button.cm-rm').forEach(btn => {
                btn.addEventListener('click', () => window.cartRemove(btn.dataset.id));
            });

            empty.style.display = validIds.length === 0 ? 'block' : 'none';
            list.style.display = validIds.length === 0 ? 'none' : 'block';
            cnt.textContent = validIds.length;
            sum.textContent = total.toLocaleString();

            if (cfg.purchase_enabled) {
                order.textContent = '카카오톡으로 주문하기';
                order.disabled = validIds.length === 0;
                order.title = '';
                banner.style.display = 'none';
            } else {
                order.textContent = cfg.purchase_disabled_short || '구매 준비 중';
                order.disabled = true;
                order.title = cfg.purchase_disabled_note || '';
                banner.textContent = cfg.purchase_disabled_note || '';
                banner.style.display = 'block';
            }
        });
    }

    function escapeHtml(s) {
        return String(s || '').replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
        }[c]));
    }

    // ─── 카톡 주문 ───────────────────────────────────────────────
    function buildOrderMessage(books) {
        const ids = readIds().filter(id => books[id]);
        if (ids.length === 0) return '';
        const lines = ['[AI 시대 영성 책방 주문]', ''];
        lines.push(`▣ 주문 도서 (${ids.length}권)`);
        let total = 0;
        ids.forEach((id, i) => {
            const b = books[id];
            const price = (b.price || 0);
            total += price;
            lines.push(`${i + 1}. ${b.title} (${b.isbn || id}) — ${price.toLocaleString()}원`);
        });
        lines.push('');
        lines.push(`합계: ${total.toLocaleString()}원`);
        lines.push('');
        lines.push(`▣ 송금 계좌`);
        lines.push(ACCOUNT_LINE);
        lines.push('');
        lines.push(`▣ EPUB 받을 이메일 주소:`);
        lines.push(`(여기에 적어주세요)`);
        return lines.join('\n');
    }

    function showToast(msg) {
        const t = document.getElementById('cartToast');
        if (!t) return;
        t.textContent = msg;
        t.classList.add('show');
        setTimeout(() => t.classList.remove('show'), 2400);
    }

    function orderViaKakao() {
        Promise.all([getBooks(), getConfig()]).then(([books, cfg]) => {
            if (!cfg.purchase_enabled) return; // 신고 전 주문 차단
            const msg = buildOrderMessage(books);
            if (!msg) return;
            const fallback = () => {
                showToast('주문 내역 복사 실패 — 수동으로 입력해주세요');
                window.open(KAKAO_URL, '_blank', 'noopener');
            };
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(msg).then(() => {
                    showToast('주문 내역이 복사되었습니다 — 카톡 채팅창에 붙여넣어 주세요');
                    setTimeout(() => window.open(KAKAO_URL, '_blank', 'noopener'), 700);
                }).catch(fallback);
            } else {
                fallback();
            }
        });
    }

    // ─── 외부에서 cart 변경 시 반영 ────────────────────────────
    window.addEventListener('cartChanged', () => {
        updateFab();
        const bg = document.getElementById('cartModalBg');
        if (bg && bg.classList.contains('active')) refreshCart();
    });

    // ─── 초기화 ────────────────────────────────────────────────
    function init() {
        injectStyles();
        renderFab();
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
