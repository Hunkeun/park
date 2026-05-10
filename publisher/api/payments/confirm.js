/**
 * 토스페이먼츠 결제 승인 + Supabase 기록 (Vercel Serverless Function)
 *
 * 호출 흐름:
 *   1) 사용자 결제 완료 → /payments/success.html 로 redirect (토스가 paymentKey/orderId/amount 전달)
 *   2) success.html 이 이 endpoint 로 POST → 토스 confirm API 호출 (시크릿 키)
 *   3) 검증 OK 면 purchases insert + bookshelf insert (사용자 user_id 기준)
 *
 * 환경변수 (Vercel Project Settings → Environment Variables):
 *   TOSS_SECRET_KEY                — 테스트: test_sk_docs_OEP59LybZ8Bdv6nvd4XL6GYo7pRe
 *   SUPABASE_URL                   — https://csiqzqjqwanwnkmrtxdh.supabase.co
 *   SUPABASE_SERVICE_ROLE_KEY      — Supabase 대시보드 → Settings → API → service_role 키
 *
 * Body (JSON):
 *   { paymentKey, orderId, amount, bookId, accessToken }
 *     accessToken = Supabase Auth 세션의 access_token (구매자 인증)
 *
 * 응답:
 *   200 { ok: true, purchaseId, orderId } — 결제 완료 + 서가 추가 완료
 *   4xx { ok: false, error: '...' }
 */

module.exports = async function handler(req, res) {
    // CORS (책방 사이트에서만 호출하지만 안전망)
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') return res.status(200).end();
    if (req.method !== 'POST') {
        return res.status(405).json({ ok: false, error: 'Method not allowed' });
    }

    const { paymentKey, orderId, amount, bookId, accessToken } = req.body || {};

    if (!paymentKey || !orderId || !amount || !bookId || !accessToken) {
        return res.status(400).json({ ok: false, error: '필수 파라미터 누락' });
    }

    const TOSS_SECRET = process.env.TOSS_SECRET_KEY;
    const SUPABASE_URL = process.env.SUPABASE_URL;
    const SUPABASE_SERVICE = process.env.SUPABASE_SERVICE_ROLE_KEY;

    if (!TOSS_SECRET || !SUPABASE_URL || !SUPABASE_SERVICE) {
        return res.status(500).json({ ok: false, error: '서버 환경변수 누락' });
    }

    try {
        // 1. Supabase 로 access_token 검증해서 user_id 획득
        const userResp = await fetch(`${SUPABASE_URL}/auth/v1/user`, {
            headers: {
                Authorization: `Bearer ${accessToken}`,
                apikey: SUPABASE_SERVICE,
            },
        });
        if (!userResp.ok) {
            return res.status(401).json({ ok: false, error: '로그인이 만료되었거나 인증되지 않았습니다.' });
        }
        const user = await userResp.json();
        const userId = user.id;

        // 2. books 테이블에서 가격 조회 — 클라이언트가 보낸 amount 와 일치하는지 검증
        const bookResp = await fetch(
            `${SUPABASE_URL}/rest/v1/books?book_id=eq.${encodeURIComponent(bookId)}&select=book_id,title,price`,
            { headers: { apikey: SUPABASE_SERVICE, Authorization: `Bearer ${SUPABASE_SERVICE}` } }
        );
        const books = await bookResp.json();
        if (!Array.isArray(books) || books.length === 0) {
            return res.status(404).json({ ok: false, error: '책을 찾을 수 없습니다.' });
        }
        const book = books[0];
        if (Number(book.price) !== Number(amount)) {
            return res.status(400).json({
                ok: false,
                error: `가격 불일치 (서버: ${book.price}, 결제: ${amount})`,
            });
        }

        // 3. 토스 confirm API 호출
        const auth = Buffer.from(`${TOSS_SECRET}:`).toString('base64');
        const tossResp = await fetch('https://api.tosspayments.com/v1/payments/confirm', {
            method: 'POST',
            headers: {
                Authorization: `Basic ${auth}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ paymentKey, orderId, amount }),
        });
        const tossData = await tossResp.json();
        if (!tossResp.ok) {
            return res.status(400).json({
                ok: false,
                error: tossData.message || '결제 승인 실패',
                code: tossData.code,
            });
        }

        // 3.5 같은 paymentKey 로 이미 처리된 결제 있는지 확인 (사용자가 success 페이지 새로고침 시 idempotent 응답)
        const dupResp = await fetch(
            `${SUPABASE_URL}/rest/v1/purchases?payment_id=eq.${encodeURIComponent(paymentKey)}&select=id,book_id,status`,
            { headers: { apikey: SUPABASE_SERVICE, Authorization: `Bearer ${SUPABASE_SERVICE}` } }
        );
        const dupRows = await dupResp.json();
        if (Array.isArray(dupRows) && dupRows.length > 0) {
            return res.status(200).json({
                ok: true,
                purchaseId: dupRows[0].id,
                orderId,
                bookId: dupRows[0].book_id,
                title: book.title,
                duplicate: true,
            });
        }

        // 4. purchases insert (status=completed → uq_active_purchase 보호 활성화)
        const purchaseResp = await fetch(`${SUPABASE_URL}/rest/v1/purchases`, {
            method: 'POST',
            headers: {
                apikey: SUPABASE_SERVICE,
                Authorization: `Bearer ${SUPABASE_SERVICE}`,
                'Content-Type': 'application/json',
                Prefer: 'return=representation',
            },
            body: JSON.stringify({
                user_id: userId,
                book_id: bookId,
                amount_paid: amount,
                payment_method: tossData.method || 'unknown',
                payment_id: paymentKey,
                status: 'completed',
            }),
        });
        const purchaseRows = await purchaseResp.json();
        if (!purchaseResp.ok) {
            // 23505 = unique violation (uq_active_purchase) — 이미 같은 책을 보유
            const code = purchaseRows && purchaseRows.code;
            if (code === '23505') {
                return res.status(409).json({
                    ok: false,
                    error: '이미 보유 중인 책입니다. 내 서가에서 바로 보실 수 있습니다.',
                    alreadyOwned: true,
                });
            }
            console.error('purchase insert 실패', purchaseRows);
            return res.status(500).json({ ok: false, error: 'purchases 기록 실패' });
        }
        const purchaseId = (purchaseRows && purchaseRows[0] && purchaseRows[0].id) || null;

        // 5. bookshelf upsert (이미 있으면 무시, on_conflict=user_id,book_id)
        await fetch(`${SUPABASE_URL}/rest/v1/bookshelf?on_conflict=user_id,book_id`, {
            method: 'POST',
            headers: {
                apikey: SUPABASE_SERVICE,
                Authorization: `Bearer ${SUPABASE_SERVICE}`,
                'Content-Type': 'application/json',
                Prefer: 'resolution=ignore-duplicates',
            },
            body: JSON.stringify({ user_id: userId, book_id: bookId }),
        });

        return res.status(200).json({
            ok: true,
            purchaseId,
            orderId,
            bookId,
            title: book.title,
        });
    } catch (e) {
        console.error('confirm 처리 오류', e);
        return res.status(500).json({ ok: false, error: e.message || '서버 오류' });
    }
};
