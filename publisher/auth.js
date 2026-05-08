/**
 * Supabase Auth 연동 (Stage 1).
 *
 * 책방 사이트 헤더 우측에 로그인 버튼·사용자 메뉴 주입.
 * 로그인 = 이메일 매직 링크.
 *
 * 사용:
 *   <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
 *   <script src="auth.js" defer></script>
 *
 * 필수 site_config.json 필드:
 *   supabase_url, supabase_anon_key, auth_enabled (true)
 *
 * 외부 API:
 *   window.aisbAuth.getUser()       Promise<User|null>
 *   window.aisbAuth.signOut()       Promise<void>
 *   window.aisbAuth.openLogin()     로그인 모달 열기
 *   on('aisbAuthChanged', e => e.detail.user)
 */
(function () {
    if (window.aisbAuth) return;  // 중복 로드 방지

    let supabase = null;
    let configPromise = null;

    function getConfig() {
        if (configPromise) return configPromise;
        const isPreview = /\/preview\//.test(location.pathname);
        const url = (isPreview ? '../' : '') + 'site_config.json';
        configPromise = fetch(url).then(r => r.ok ? r.json() : null).catch(() => null);
        return configPromise;
    }

    async function ensureClient() {
        if (supabase) return supabase;
        const cfg = await getConfig();
        if (!cfg || !cfg.auth_enabled || !cfg.supabase_url || !cfg.supabase_anon_key) {
            return null;
        }
        if (typeof window.supabase === 'undefined' || !window.supabase.createClient) {
            console.warn('[aisbAuth] supabase-js CDN이 로드되지 않음');
            return null;
        }
        supabase = window.supabase.createClient(cfg.supabase_url, cfg.supabase_anon_key, {
            auth: {
                persistSession: true,
                autoRefreshToken: true,
                detectSessionInUrl: true,
            },
        });
        return supabase;
    }

    async function getUser() {
        const c = await ensureClient();
        if (!c) return null;
        const { data: { user } } = await c.auth.getUser();
        return user;
    }

    async function signOut() {
        const c = await ensureClient();
        if (!c) return;
        await c.auth.signOut();
        renderHeader(null);
        window.dispatchEvent(new CustomEvent('aisbAuthChanged', { detail: { user: null } }));
    }

    async function sendMagicLink(email) {
        const c = await ensureClient();
        if (!c) throw new Error('Supabase 미초기화');
        const redirectTo = location.origin + location.pathname;
        const { error } = await c.auth.signInWithOtp({
            email,
            options: { emailRedirectTo: redirectTo },
        });
        if (error) throw error;
    }

    // ─── 스타일 주입 ───────────────────────────────────────────
    function injectStyles() {
        if (document.getElementById('aisb-auth-styles')) return;
        const css = document.createElement('style');
        css.id = 'aisb-auth-styles';
        css.textContent = `
.aisb-auth-btn {
    font-family: 'Noto Sans KR', sans-serif;
    font-size: 0.8rem;
    letter-spacing: 0.1rem;
    color: rgba(255,255,255,0.85);
    background: transparent;
    border: 1px solid rgba(212,175,55,0.5);
    padding: 0.45rem 1rem;
    border-radius: 2px;
    cursor: pointer;
    margin-left: 1.5rem;
    transition: all 0.3s;
}
.aisb-auth-btn:hover {
    background: rgba(212,175,55,0.15);
    border-color: #d4af37;
    color: #d4af37;
}
.aisb-user-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    margin-left: 1.5rem;
    position: relative;
}
.aisb-user-chip .label {
    font-family: 'Noto Sans KR', sans-serif;
    font-size: 0.78rem;
    color: rgba(255,255,255,0.75);
    letter-spacing: 0.05rem;
    cursor: pointer;
    padding: 0.4rem 0.7rem;
    border: 1px solid rgba(212,175,55,0.3);
    border-radius: 2px;
}
.aisb-user-chip .label:hover {
    color: #d4af37;
    border-color: #d4af37;
}
.aisb-user-chip .menu {
    display: none;
    position: absolute;
    top: calc(100% + 0.4rem);
    right: 0;
    background: #fdfbf7;
    border: 1px solid rgba(10,25,47,0.15);
    border-radius: 4px;
    box-shadow: 0 8px 24px rgba(10,25,47,0.18);
    min-width: 180px;
    z-index: 200;
}
.aisb-user-chip.open .menu { display: block; }
.aisb-user-chip .menu a, .aisb-user-chip .menu button {
    display: block;
    width: 100%;
    text-align: left;
    padding: 0.7rem 1rem;
    font-family: 'Noto Sans KR', sans-serif;
    font-size: 0.85rem;
    color: #2c3e50;
    background: none;
    border: none;
    border-bottom: 1px solid rgba(10,25,47,0.08);
    cursor: pointer;
    text-decoration: none;
}
.aisb-user-chip .menu a:last-child, .aisb-user-chip .menu button:last-child {
    border-bottom: none;
}
.aisb-user-chip .menu a:hover, .aisb-user-chip .menu button:hover {
    background: rgba(212,175,55,0.08);
    color: #0a192f;
}

.aisb-modal-back {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(10,25,47,0.7);
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    backdrop-filter: blur(4px);
}
.aisb-modal {
    background: #fdfbf7;
    border-radius: 6px;
    box-shadow: 0 30px 60px rgba(0,0,0,0.4);
    max-width: 400px;
    width: 100%;
    padding: 2.4rem 2rem;
    font-family: 'Noto Sans KR', sans-serif;
    position: relative;
}
.aisb-modal h3 {
    font-family: 'Playfair Display', serif;
    font-size: 1.5rem;
    color: #0a192f;
    margin-bottom: 0.5rem;
}
.aisb-modal .modal-sub {
    font-size: 0.88rem;
    color: #5d6d7e;
    margin-bottom: 1.6rem;
    line-height: 1.7;
}
.aisb-modal label {
    display: block;
    font-size: 0.8rem;
    color: #5d6d7e;
    margin-bottom: 0.4rem;
    letter-spacing: 0.05rem;
}
.aisb-modal input[type="email"] {
    width: 100%;
    padding: 0.8rem 0.9rem;
    border: 1px solid rgba(10,25,47,0.2);
    border-radius: 3px;
    font-size: 0.95rem;
    font-family: inherit;
    color: #2c3e50;
    background: white;
    margin-bottom: 1rem;
    box-sizing: border-box;
}
.aisb-modal input[type="email"]:focus {
    outline: none;
    border-color: #d4af37;
    box-shadow: 0 0 0 3px rgba(212,175,55,0.15);
}
.aisb-modal .submit {
    width: 100%;
    padding: 0.85rem;
    background: #0a192f;
    color: white;
    border: none;
    border-radius: 3px;
    font-family: inherit;
    font-size: 0.95rem;
    letter-spacing: 0.1rem;
    cursor: pointer;
    transition: background 0.3s;
}
.aisb-modal .submit:hover { background: #1a3a5c; }
.aisb-modal .submit:disabled { background: #999; cursor: wait; }
.aisb-modal .close {
    position: absolute;
    top: 0.6rem; right: 0.9rem;
    font-size: 1.5rem;
    background: none; border: none;
    color: #5d6d7e;
    cursor: pointer;
    line-height: 1;
}
.aisb-modal .close:hover { color: #0a192f; }
.aisb-modal .status {
    margin-top: 1rem;
    padding: 0.8rem;
    border-radius: 3px;
    font-size: 0.85rem;
    line-height: 1.6;
}
.aisb-modal .status.ok {
    background: rgba(40,180,80,0.1);
    color: #1a6b30;
    border: 1px solid rgba(40,180,80,0.25);
}
.aisb-modal .status.err {
    background: rgba(200,50,50,0.08);
    color: #8a1a1a;
    border: 1px solid rgba(200,50,50,0.2);
}
.aisb-modal .footnote {
    margin-top: 1.4rem;
    font-size: 0.75rem;
    color: #888;
    line-height: 1.6;
    border-top: 1px solid rgba(10,25,47,0.08);
    padding-top: 1rem;
}
.aisb-modal .resend-block {
    margin-top: 1rem;
    padding-top: 0.8rem;
    border-top: 1px dashed rgba(10,25,47,0.12);
}
.aisb-modal .resend-hint {
    font-size: 0.78rem;
    color: #5d6d7e;
    margin-bottom: 0.4rem;
    font-weight: 700;
}
.aisb-modal .resend-tips {
    list-style: disc;
    padding-left: 1.2rem;
    font-size: 0.74rem;
    color: #5d6d7e;
    line-height: 1.6;
    margin-bottom: 0.7rem;
}
.aisb-modal .resend-tips code {
    background: rgba(10,25,47,0.06);
    padding: 0 0.3rem;
    border-radius: 2px;
    font-size: 0.92em;
}
.aisb-modal .resend-btn {
    width: 100%;
    padding: 0.6rem;
    background: transparent;
    color: #0a192f;
    border: 1px solid rgba(10,25,47,0.25);
    border-radius: 3px;
    font-family: inherit;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.2s;
}
.aisb-modal .resend-btn:disabled {
    opacity: 0.55;
    cursor: not-allowed;
}
.aisb-modal .resend-btn:not(:disabled):hover {
    background: #0a192f;
    color: white;
}
        `;
        document.head.appendChild(css);
    }

    // ─── 헤더에 버튼/메뉴 주입 ─────────────────────────────────
    function findNav() {
        return document.querySelector('header nav') || document.querySelector('header');
    }

    function clearAuthEls() {
        document.querySelectorAll('.aisb-auth-btn, .aisb-user-chip').forEach(el => el.remove());
    }

    function renderHeader(user) {
        const nav = findNav();
        if (!nav) return;
        clearAuthEls();
        if (!user) {
            const btn = document.createElement('button');
            btn.className = 'aisb-auth-btn';
            btn.textContent = '로그인';
            btn.addEventListener('click', openLogin);
            nav.appendChild(btn);
        } else {
            const chip = document.createElement('span');
            chip.className = 'aisb-user-chip';
            const display = user.email
                ? user.email.replace(/@.*$/, '@…')
                : '내 서가';
            chip.innerHTML = `
                <span class="label">${display}</span>
                <div class="menu">
                    <a href="/library">내 서가</a>
                    <a href="/payments/receipts">구매 내역</a>
                    <button class="signout">로그아웃</button>
                </div>
            `;
            const label = chip.querySelector('.label');
            const menu = chip.querySelector('.menu');
            label.addEventListener('click', () => chip.classList.toggle('open'));
            chip.querySelector('.signout').addEventListener('click', async () => {
                await signOut();
            });
            document.addEventListener('click', (e) => {
                if (!chip.contains(e.target)) chip.classList.remove('open');
            });
            nav.appendChild(chip);
        }
    }

    // ─── 로그인 모달 ─────────────────────────────────────────
    function openLogin() {
        if (document.querySelector('.aisb-modal-back')) return;

        const back = document.createElement('div');
        back.className = 'aisb-modal-back';
        back.innerHTML = `
            <div class="aisb-modal">
                <button class="close" aria-label="닫기">×</button>
                <h3>로그인 / 가입</h3>
                <p class="modal-sub">
                    이메일 주소만 알려 주세요.<br>
                    매직 링크를 보내드리니 메일함에서 클릭하시면 자동으로 로그인됩니다.
                </p>
                <label for="aisb-email">이메일</label>
                <input type="email" id="aisb-email" placeholder="you@example.com" autocomplete="email" autofocus />
                <button class="submit">매직 링크 받기</button>
                <div class="status" style="display:none"></div>
                <div class="footnote">
                    가입과 로그인이 같은 흐름입니다. 첫 방문이면 자동으로 계정이 만들어집니다.
                </div>
            </div>
        `;
        document.body.appendChild(back);

        const close = () => back.remove();
        back.querySelector('.close').addEventListener('click', close);
        back.addEventListener('click', (e) => {
            if (e.target === back) close();
        });
        document.addEventListener('keydown', function esc(e) {
            if (e.key === 'Escape') {
                close();
                document.removeEventListener('keydown', esc);
            }
        });

        const submit = back.querySelector('.submit');
        const status = back.querySelector('.status');
        const input = back.querySelector('#aisb-email');

        const send = async (isResend) => {
            const email = (input.value || '').trim();
            if (!email || !email.includes('@')) {
                status.style.display = 'block';
                status.className = 'status err';
                status.textContent = '이메일 형식이 올바르지 않습니다.';
                return;
            }
            submit.disabled = true;
            submit.textContent = isResend ? '다시 보내는 중…' : '보내는 중…';
            status.style.display = 'none';
            try {
                await sendMagicLink(email);
                status.style.display = 'block';
                status.className = 'status ok';
                status.innerHTML = `
                    <strong>${email}</strong> 로 매직 링크를 ${isResend ? '다시 ' : ''}보냈습니다.<br>
                    메일함에서 링크를 클릭하면 이 페이지로 돌아와 로그인됩니다.
                    <div class="resend-block" id="aisb-resend-block">
                        <p class="resend-hint">메일이 안 도착하셨나요?</p>
                        <ul class="resend-tips">
                            <li>스팸·정크 폴더를 확인하세요</li>
                            <li>발신자 <code>noreply@mail.app.supabase.io</code> 검색</li>
                            <li>최대 1~2분 지연될 수 있습니다</li>
                        </ul>
                        <button type="button" class="resend-btn" id="aisb-resend-btn" disabled>
                            <span id="aisb-resend-label">30초 후 재발송 가능</span>
                        </button>
                        <button type="button" class="resend-btn outline" id="aisb-change-email" style="margin-top:0.4rem;">다른 이메일로 시도</button>
                    </div>
                `;
                submit.textContent = '전송 완료';
                input.disabled = true;

                // 30초 쿨다운 후 재발송 버튼 활성화
                const resendBtn = back.querySelector('#aisb-resend-btn');
                const resendLabel = back.querySelector('#aisb-resend-label');
                let remaining = 30;
                const tick = () => {
                    if (remaining <= 0) {
                        resendBtn.disabled = false;
                        resendLabel.textContent = '매직 링크 다시 보내기';
                        return;
                    }
                    resendLabel.textContent = `${remaining}초 후 재발송 가능`;
                    remaining--;
                    setTimeout(tick, 1000);
                };
                tick();
                resendBtn.addEventListener('click', () => send(true));

                // "다른 이메일로 시도" — 입력칸 다시 활성화 + 초기화
                const changeBtn = back.querySelector('#aisb-change-email');
                if (changeBtn) changeBtn.addEventListener('click', () => {
                    input.disabled = false;
                    input.value = '';
                    input.focus();
                    status.style.display = 'none';
                    submit.disabled = false;
                    submit.textContent = '매직 링크 받기';
                });
            } catch (e) {
                status.style.display = 'block';
                status.className = 'status err';
                status.textContent = '전송 실패: ' + (e.message || e);
                submit.disabled = false;
                submit.textContent = '매직 링크 받기';
            }
        };
        submit.addEventListener('click', () => send(false));
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') send(false);
        });
    }

    // ─── 초기화 ──────────────────────────────────────────────
    async function init() {
        injectStyles();
        const c = await ensureClient();
        if (!c) {
            // auth_enabled false 거나 설정 누락 — 헤더 변경 안 함
            return;
        }

        // 현재 세션 확인
        const { data: { session } } = await c.auth.getSession();
        renderHeader(session ? session.user : null);

        // 세션 변화 감지
        c.auth.onAuthStateChange((event, session) => {
            const u = session ? session.user : null;
            renderHeader(u);
            window.dispatchEvent(new CustomEvent('aisbAuthChanged', { detail: { user: u } }));
            if (event === 'SIGNED_IN') {
                // 매직 링크 클릭 직후 들어온 ?token, ?type 파라미터 정리
                if (location.hash || location.search.includes('token')) {
                    history.replaceState(null, '', location.pathname);
                }
            }
        });
    }

    // 외부 API 노출
    window.aisbAuth = { getUser, signOut, openLogin };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
