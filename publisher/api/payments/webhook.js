/**
 * 토스페이먼츠 결제 webhook 수신 (Vercel Serverless Function — fallback).
 *
 * 평소 흐름은 success.html → /api/payments/confirm 로 즉시 처리됨.
 * 그러나 사용자가 success 페이지에 도달 전 브라우저를 닫거나 네트워크가 끊기면
 * confirm 호출이 누락되어 결제는 됐는데 서가에 안 들어가는 케이스 발생 가능.
 *
 * 토스 측에 이 endpoint 를 webhook URL 로 등록해두면, 결제 상태 변경 시
 * 토스가 우리 서버로 push 함. 우리가 paymentKey 로 토스에 다시 조회해서
 * confirm 과 동일한 처리 (purchases insert + bookshelf upsert) 를 함.
 *
 * 토스 webhook 이벤트 등록 (LIVE 키 발급 후 가맹점 관리자에서):
 *   URL: https://ai-spirituality-books.vercel.app/api/payments/webhook
 *   Event: PAYMENT_STATUS_CHANGED (or DONE)
 *
 * 환경변수 (Vercel):
 *   TOSS_SECRET_KEY
 *   SUPABASE_URL
 *   SUPABASE_SERVICE_ROLE_KEY
 *
 * 토스 webhook 서명 검증은 별도 단계 (TossPayments 가 webhook secret 제공하면 추가).
 */

module.exports = async function handler(req, res) {
    // 토스 webhook 은 POST. 다른 메소드는 거부.
    if (req.method !== 'POST') {
        return res.status(405).json({ ok: false, error: 'Method not allowed' });
    }

    const TOSS_SECRET = process.env.TOSS_SECRET_KEY;
    const SUPABASE_URL = process.env.SUPABASE_URL;
    const SUPABASE_SERVICE = process.env.SUPABASE_SERVICE_ROLE_KEY;

    if (!TOSS_SECRET || !SUPABASE_URL || !SUPABASE_SERVICE) {
        console.error('[webhook] 환경변수 누락');
        return res.status(500).json({ ok: false, error: '서버 환경변수 누락' });
    }

    const body = req.body || {};
    // 토스 webhook payload — 결제 상태 변경 이벤트.
    // PAYMENT.DONE 또는 status === 'DONE' 일 때 처리.
    const eventType = body.eventType || body.type || '';
    const data = body.data || body;
    const paymentKey = data.paymentKey;
    const orderId = data.orderId;
    const status = (data.status || '').toUpperCase();

    if (!paymentKey || !orderId) {
        // 형식 부족 — 200 OK 로 답하되 처리 안 함 (토스가 retry 안 하도록)
        console.log('[webhook] paymentKey/orderId 누락', body);
        return res.status(200).json({ ok: true, skipped: true });
    }

    // DONE / 완료 이벤트만 처리. 다른 상태는 로그만.
    if (status && status !== 'DONE') {
        console.log(`[webhook] status=${status} — 처리 스킵`, paymentKey);
        return res.status(200).json({ ok: true, skipped: true, status });
    }

    try {
        // 1. 이미 처리된 paymentKey 인지 확인
        const dupResp = await fetch(
            `${SUPABASE_URL}/rest/v1/purchases?payment_id=eq.${encodeURIComponent(paymentKey)}&select=id,book_id,status`,
            { headers: { apikey: SUPABASE_SERVICE, Authorization: `Bearer ${SUPABASE_SERVICE}` } }
        );
        const dupRows = await dupResp.json();
        if (Array.isArray(dupRows) && dupRows.length > 0) {
            console.log('[webhook] 이미 처리됨', paymentKey, dupRows[0].id);
            return res.status(200).json({ ok: true, alreadyProcessed: true });
        }

        // 2. 토스 confirm API 로 결제 정보 조회 (orderId 기준 GET 또는 confirm 재시도)
        // GET /v1/payments/{paymentKey} 로 결제 상세 조회
        const auth = Buffer.from(`${TOSS_SECRET}:`).toString('base64');
        const tossResp = await fetch(`https://api.tosspayments.com/v1/payments/${encodeURIComponent(paymentKey)}`, {
            headers: { Authorization: `Basic ${auth}` },
        });
        const tossData = await tossResp.json();
        if (!tossResp.ok) {
            console.error('[webhook] 토스 조회 실패', tossData);
            return res.status(500).json({ ok: false, error: 'Toss 조회 실패' });
        }

        // 결제 완료 상태가 아니면 스킵
        if (tossData.status !== 'DONE') {
            console.log('[webhook] toss status=' + tossData.status + ' — 처리 스킵');
            return res.status(200).json({ ok: true, skipped: true, status: tossData.status });
        }

        // 3. orderId 에서 bookId 추출 (catalog 의 startTossPayment 가 `order_<bookId>_<ts>` 형식으로 만듦)
        let bookId = null;
        const m = String(orderId).match(/^order_([^_]+(?:_[^_]+)?)_\d+$/);
        if (m) bookId = m[1];
        if (!bookId) {
            // metadata 등 다른 곳에서 추출 시도
            console.error('[webhook] orderId 에서 bookId 추출 실패', orderId);
            return res.status(400).json({ ok: false, error: 'orderId 형식 인식 불가' });
        }

        // 4. books 테이블에서 가격·user_id 등 조회
        const bookResp = await fetch(
            `${SUPABASE_URL}/rest/v1/books?book_id=eq.${encodeURIComponent(bookId)}&select=book_id,title,price`,
            { headers: { apikey: SUPABASE_SERVICE, Authorization: `Bearer ${SUPABASE_SERVICE}` } }
        );
        const books = await bookResp.json();
        if (!Array.isArray(books) || books.length === 0) {
            return res.status(404).json({ ok: false, error: '책을 찾을 수 없습니다.' });
        }
        const book = books[0];

        // 5. tossData.totalAmount 와 books.price 가 일치하는지 확인
        if (Number(book.price) !== Number(tossData.totalAmount)) {
            console.error('[webhook] 금액 불일치', book.price, tossData.totalAmount);
            return res.status(400).json({ ok: false, error: '금액 불일치' });
        }

        // 6. user_id — webhook 은 인증 정보 없으니 customerKey 또는 metadata 에서.
        // 토스 v2 의 payment.requestPayment 에서 customerKey 를 user_id 로 보냈음.
        const userId = tossData.customerKey || (tossData.customer && tossData.customer.customerKey);
        if (!userId) {
            console.error('[webhook] customerKey 없음', tossData);
            return res.status(400).json({ ok: false, error: 'customerKey 누락' });
        }

        // 7. purchases insert
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
                amount_paid: tossData.totalAmount,
                payment_method: tossData.method || 'unknown',
                payment_id: paymentKey,
                status: 'completed',
            }),
        });
        const purchaseRows = await purchaseResp.json();
        if (!purchaseResp.ok) {
            const code = purchaseRows && purchaseRows.code;
            // 23505 = unique violation (uq_active_purchase) — 이미 보유. webhook 은 idempotent 로 OK 응답.
            if (code === '23505') {
                console.log('[webhook] 이미 보유 (race condition)', userId, bookId);
                return res.status(200).json({ ok: true, alreadyOwned: true });
            }
            console.error('[webhook] purchase insert 실패', purchaseRows);
            return res.status(500).json({ ok: false, error: 'purchases 기록 실패' });
        }
        const purchaseId = (purchaseRows && purchaseRows[0] && purchaseRows[0].id) || null;

        // 8. bookshelf upsert
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

        console.log('[webhook] 처리 완료', purchaseId, bookId, userId);
        return res.status(200).json({ ok: true, purchaseId, bookId, fallback: true });
    } catch (e) {
        console.error('[webhook] 처리 오류', e);
        return res.status(500).json({ ok: false, error: e.message || '서버 오류' });
    }
};
