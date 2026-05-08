# -*- coding: utf-8 -*-
"""
publisher/catalog.html 자동 생성.

입력: publisher/books_master.json
출력: publisher/catalog.html (121권 카드 그리드 + 시리즈/그룹 필터 + 권 상세 모달)
"""
# PATCHED:utf8-stdout-v1
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding='utf-8')
    _sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass


import json
import html
from pathlib import Path

GROUP_ORDER = ['G01', 'G02', 'G03', 'G04', 'G05', 'G06', 'G07', 'G08', 'G09', 'G10']
GROUP_TITLES = {
    'G01': '천국과 영계',
    'G02': '알고리즘 시대의 영성',
    'G03': '겨자씨에서 산까지',
    'G04': '발자국과 눈물',
    'G05': '흉터 위의 빛',
    'G06': '광야의 외침',
    'G07': '바람과 불',
    'G08': '무릎의 자리',
    'G09': '곁에 두신 분들',
    'G10': '이미, 그러나 아직',
}


def esc(s):
    return html.escape(str(s)) if s else ''


def fmt_pubdate(s):
    if not s:
        return ''
    return s.replace('-', '.')


def fmt_price(p):
    return f'{p:,}원' if p else ''


def row_html(b):
    bid = esc(b['id'])
    cover = f'covers/{bid}.jpg'
    title = esc(b['title'])
    subtitle = esc(b.get('subtitle', '') or '')
    pub = esc(fmt_pubdate(b.get('publish_date')))
    price = esc(fmt_price(b.get('price')))
    isbn = esc(b.get('isbn') or '')

    if b['type'] == 'omnibus':
        if b['season'] == 1:
            series_label = '시즌1 · 종합책'
        else:
            series_label = f'시즌2 · {b["group"]} 종합'
    else:
        if b['season'] == 1:
            series_label = f'시즌1 · EP {b["seq"]}'
        else:
            series_label = f'시즌2 · {b["group"]} · EP {b["group_seq"]}'

    season = b['season']
    btype = b['type']
    group = b.get('group', '')
    filter_attrs = f'data-season="{season}" data-type="{btype}" data-group="{group}"'

    search_parts = [
        b.get('title', ''),
        b.get('subtitle', '') or '',
        b.get('summary', '') or '',
        b.get('keywords', '') or '',
        b.get('metaphor', '') or '',
        b.get('isbn', '') or '',
        b.get('group_name', '') or '',
        b.get('group', '') or '',
        b.get('author', '') or '',
    ]
    search_text = esc(' '.join(p for p in search_parts if p).lower())

    return f'''        <tr class="row" {filter_attrs} data-id="{bid}" data-pubdate="{esc(b.get("publish_date") or "")}" data-search="{search_text}" onclick="openBook('{bid}')">
            <td class="cell-cover"><img src="{cover}" alt="" loading="lazy"></td>
            <td class="cell-title"><strong>{title}</strong>{f"<br><span>{subtitle}</span>" if subtitle else ""}<span class="row-owned" data-owned-for="{bid}" hidden>✓ 보유</span><span class="row-progress" data-progress-for="{bid}" hidden></span></td>
            <td class="cell-series">{esc(series_label)}</td>
            <td class="cell-price">{price}</td>
            <td class="cell-pubdate">{pub}</td>
            <td class="cell-isbn">{isbn}</td>
            <td class="cell-status"><span class="status-tag"></span></td>
        </tr>'''


def card_html(b):
    bid = esc(b['id'])
    cover = f'covers/{bid}.jpg'
    title = esc(b['title'])
    subtitle = esc(b.get('subtitle', '') or '')
    pub = esc(fmt_pubdate(b.get('publish_date')))
    price = esc(fmt_price(b.get('price')))

    if b['type'] == 'omnibus':
        if b['season'] == 1:
            ep_label = '시즌1 종합'
        else:
            ep_label = f'{b["group"]} 종합'
    else:
        if b['season'] == 1:
            ep_label = f'EP {b["seq"]}'
        else:
            ep_label = f'EP {b["group_seq"]}'

    season = b['season']
    btype = b['type']
    group = b.get('group', '')
    filter_attrs = f'data-season="{season}" data-type="{btype}" data-group="{group}"'

    search_parts = [
        b.get('title', ''),
        b.get('subtitle', '') or '',
        b.get('summary', '') or '',
        b.get('keywords', '') or '',
        b.get('metaphor', '') or '',
        b.get('isbn', '') or '',
        b.get('group_name', '') or '',
        b.get('group', '') or '',
        b.get('author', '') or '',
    ]
    search_text = esc(' '.join(p for p in search_parts if p).lower())

    return f'''        <article class="card" {filter_attrs} data-id="{bid}" data-pubdate="{esc(b.get("publish_date") or "")}" data-search="{search_text}" onclick="openBook('{bid}')">
            <div class="card-cover">
                <span class="card-ep">{ep_label}</span>
                <span class="card-countdown"></span>
                <span class="card-owned" data-owned-for="{bid}" hidden>✓ 보유</span>
                <img src="{cover}" alt="{title}" loading="lazy">
            </div>
            <div class="card-body">
                <h3 class="card-title">{title}</h3>
                <p class="card-subtitle">{subtitle}</p>
                <div class="card-meta">
                    <span class="card-price">{price}</span>
                    <span class="card-pubdate">{pub}</span>
                </div>
                <div class="card-progress" data-progress-for="{bid}" hidden>
                    <div class="card-progress-bar"><div class="card-progress-fill"></div></div>
                    <span class="card-progress-text">이어보기 0%</span>
                </div>
                <p class="card-buy">자세히 보기 →</p>
            </div>
        </article>'''


def build():
    with open('publisher/books_master.json', encoding='utf-8') as f:
        master = json.load(f)

    s1_main = sorted([b for b in master['books'] if b['season']==1 and b['type']=='main'], key=lambda b: b['seq'])
    s1_omni = [b for b in master['books'] if b['season']==1 and b['type']=='omnibus']
    s2_main = sorted([b for b in master['books'] if b['season']==2 and b['type']=='main'], key=lambda b: b['seq'])
    s2_omni = sorted([b for b in master['books'] if b['season']==2 and b['type']=='omnibus'], key=lambda b: b['seq'])

    all_cards = []
    all_rows = []
    ordered = list(s1_main) + list(s2_main) + list(s1_omni) + list(s2_omni)
    for b in ordered:
        all_cards.append(card_html(b))
        all_rows.append(row_html(b))

    cards_html = '\n'.join(all_cards)
    rows_html = '\n'.join(all_rows)

    books_data_json = json.dumps(
        {b['id']: b for b in master['books']},
        ensure_ascii=False,
    )

    cfg_path = Path('publisher/site_config.json')
    if cfg_path.exists():
        with open(cfg_path, encoding='utf-8') as f:
            cfg = json.load(f)
    else:
        cfg = {'purchase_enabled': True}

    page = HTML_TEMPLATE.format(
        cards=cards_html,
        rows=rows_html,
        books_json=books_data_json,
        total=master['total_count'],
        s1_main_count=len(s1_main),
        s2_main_count=len(s2_main),
        omni_count=len(s1_omni) + len(s2_omni),
        purchase_enabled='true' if cfg.get('purchase_enabled') else 'false',
        purchase_short=esc(cfg.get('purchase_disabled_short', '구매 준비 중')),
        purchase_note=esc(cfg.get('purchase_disabled_note', '')),
        free_beta='true' if cfg.get('free_beta') else 'false',
        toss_client_key=esc(cfg.get('toss_client_key') or ''),
        supabase_url=esc(cfg.get('supabase_url') or ''),
        supabase_anon_key=esc(cfg.get('supabase_anon_key') or ''),
    )

    out_path = Path('publisher/catalog.html')
    out_path.write_text(page, encoding='utf-8')
    print(f'[완료] {len(all_cards)}권 카드 -> {out_path}')


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>도서 카탈로그 — AI 시대 영성</title>
    <meta name="description" content="AI 시대 영성 도서 121권 한눈에 보기. 시즌 1·2 본권 + 종합책. 검색·필터·미리보기·본문 무료 베타.">
    <link rel="canonical" href="https://ai-spirituality-books.vercel.app/catalog">
    <meta property="og:type" content="website">
    <meta property="og:title" content="도서 카탈로그 — AI 시대 영성 책방">
    <meta property="og:description" content="AI 시대 영성 도서 121권. 시즌 1·2 본권 + 종합책. 본문 무료 베타.">
    <meta property="og:image" content="https://ai-spirituality-books.vercel.app/covers/s1-omnibus.jpg">
    <meta property="og:url" content="https://ai-spirituality-books.vercel.app/catalog">
    <meta property="og:site_name" content="AI 시대 영성 책방">
    <meta property="og:locale" content="ko_KR">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:image" content="https://ai-spirituality-books.vercel.app/covers/s1-omnibus.jpg">
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#0a192f">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Noto+Serif+KR:wght@300;400;600;700&family=Noto+Sans+KR:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #0a192f;
            --secondary: #172a45;
            --accent: #d4af37;
            --accent-soft: rgba(212, 175, 55, 0.15);
            --text-main: #2c3e50;
            --text-muted: #5d6d7e;
            --white: #ffffff;
            --bg-card: #f5f2ec;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Noto Serif KR', serif;
            color: var(--text-main);
            background: var(--bg-card);
            line-height: 1.7;
            -webkit-font-smoothing: antialiased;
        }}
        header {{
            background: var(--primary);
            padding: 1.2rem 3rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        .logo {{
            display: inline-flex;
            align-items: center;
            text-decoration: none;
            gap: 0.6rem;
        }}
        .logo img {{
            height: 36px;
            width: auto;
            display: block;
        }}
        .logo span.label {{
            color: rgba(255,255,255,0.55);
            font-size: 0.68rem;
            font-family: 'Noto Sans KR', sans-serif;
            font-weight: 300;
            letter-spacing: 0.3rem;
            border-left: 1px solid rgba(212,175,55,0.4);
            padding-left: 0.7rem;
        }}
        nav a {{
            color: rgba(255,255,255,0.7);
            text-decoration: none;
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.85rem;
            letter-spacing: 0.1rem;
            margin-left: 2rem;
            transition: color 0.3s;
        }}
        nav a:hover, nav a.active {{ color: var(--accent); }}
        .page-head {{
            background: linear-gradient(135deg, var(--primary) 0%, #0d2440 60%, #1a3a5c 100%);
            padding: 5rem 2rem 3rem;
            text-align: center;
            color: var(--white);
        }}
        .page-head .label {{
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.75rem;
            letter-spacing: 0.5rem;
            color: var(--accent);
            text-transform: uppercase;
        }}
        .page-head h1 {{
            font-family: 'Playfair Display', serif;
            font-size: clamp(2rem, 4vw, 3rem);
            margin: 0.5rem 0;
        }}
        .page-head .desc {{
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.95rem;
            color: rgba(255,255,255,0.6);
            margin-top: 0.6rem;
            letter-spacing: 0.1rem;
        }}
        .page-head .divider {{
            width: 60px;
            height: 2px;
            background: var(--accent);
            margin: 1.5rem auto 0;
        }}
        .page-head .head-qr {{
            margin: 2rem auto 0;
            display: inline-flex;
            gap: 0.9rem;
            align-items: center;
            background: rgba(255,255,255,0.96);
            padding: 0.7rem 1.1rem 0.7rem 0.7rem;
            border-radius: 6px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.25);
            text-align: left;
        }}
        .page-head .head-qr img {{
            width: 76px;
            height: 76px;
            display: block;
            border-radius: 2px;
        }}
        .page-head .head-qr-text strong {{
            display: block;
            color: var(--primary);
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.05rem;
        }}
        .page-head .head-qr-text span {{
            color: var(--text-muted);
            font-size: 0.72rem;
            line-height: 1.5;
        }}
        .tabs {{
            background: var(--primary);
            padding: 0 2rem;
            display: flex;
            justify-content: center;
            gap: 0;
            flex-wrap: wrap;
            border-top: 1px solid rgba(212,175,55,0.15);
        }}
        .tab {{
            padding: 1rem 1.4rem;
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.85rem;
            color: rgba(255,255,255,0.5);
            background: none;
            border: none;
            text-decoration: none;
            letter-spacing: 0.1rem;
            border-bottom: 2px solid transparent;
            transition: all 0.3s;
            cursor: pointer;
        }}
        .tab:hover {{ color: rgba(255,255,255,0.85); }}
        .tab.active {{ color: var(--accent); border-bottom-color: var(--accent); }}
        .tabs.sub {{ background: var(--secondary); border-top: none; padding: 0 1rem; }}
        .tabs.sub .tab {{ font-size: 0.78rem; padding: 0.7rem 0.9rem; }}
        .tabs.sub.hidden {{ display: none; }}
        .catalog {{
            max-width: 1280px;
            margin: 0 auto;
            padding: 3rem 2rem 5rem;
        }}
        /* ─── SEARCH + SORT ─── */
        .search-area {{
            background: var(--white);
            border: 1px solid rgba(10,25,47,0.12);
            border-radius: 4px;
            padding: 1rem 1.1rem;
            margin-bottom: 1.6rem;
            box-shadow: 0 2px 8px rgba(10,25,47,0.04);
        }}
        .search-area-label {{
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.7rem;
            letter-spacing: 0.25rem;
            color: var(--accent);
            text-transform: uppercase;
            display: block;
            margin-bottom: 0.7rem;
        }}
        .search-scope {{
            display: inline-flex;
            gap: 0.3rem;
            margin-bottom: 0.7rem;
            flex-wrap: wrap;
        }}
        .scope-btn {{
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.78rem;
            color: var(--text-muted);
            background: transparent;
            border: 1px solid rgba(10,25,47,0.15);
            border-radius: 999px;
            padding: 0.32rem 0.85rem;
            cursor: pointer;
            letter-spacing: 0.05rem;
            transition: all 0.2s;
        }}
        .scope-btn:hover {{ color: var(--primary); border-color: var(--primary); }}
        .scope-btn.active {{
            background: var(--primary);
            color: var(--accent);
            border-color: var(--primary);
            font-weight: 500;
        }}
        .filter-bar {{
            display: flex;
            gap: 0.6rem;
            margin-bottom: 0;
            align-items: stretch;
        }}
        .search-bar {{
            position: relative;
            flex: 1;
        }}
        .search-submit {{
            background: var(--primary);
            color: var(--accent);
            border: none;
            border-radius: 4px;
            padding: 0 1.5rem;
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.88rem;
            font-weight: 500;
            cursor: pointer;
            letter-spacing: 0.15rem;
            transition: background 0.2s;
            white-space: nowrap;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
        }}
        .search-submit:hover {{ background: #06111f; }}
        .sort-row {{
            display: flex;
            justify-content: flex-end;
            margin-top: 0.9rem;
        }}
        .sort-select {{
            background: var(--white);
            border: 1px solid rgba(10,25,47,0.15);
            border-radius: 4px;
            padding: 0 1rem;
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.9rem;
            color: var(--primary);
            cursor: pointer;
            min-width: 180px;
            letter-spacing: 0.05rem;
            transition: border-color 0.3s, box-shadow 0.3s;
        }}
        .sort-select:focus {{
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(212,175,55,0.15);
        }}
        @media (max-width: 720px) {{
            .filter-bar {{ flex-direction: column; }}
            .sort-select {{ height: 48px; }}
        }}

        /* ─── VIEW TOGGLE ─── */
        .view-toggle {{
            display: inline-flex;
            background: var(--white);
            border: 1px solid rgba(10,25,47,0.15);
            border-radius: 4px;
            overflow: hidden;
        }}
        .view-btn {{
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.85rem;
            background: var(--white);
            color: var(--text-muted);
            border: none;
            padding: 0 1.1rem;
            cursor: pointer;
            letter-spacing: 0.05rem;
            transition: all 0.2s;
        }}
        .view-btn.active {{
            background: var(--primary);
            color: var(--accent);
        }}
        .view-btn:not(.active):hover {{ color: var(--primary); }}

        /* ─── TABLE VIEW ─── */
        .table-wrap {{
            background: var(--white);
            border-radius: 4px;
            box-shadow: 0 4px 20px rgba(10,25,47,0.06);
            overflow-x: auto;
            display: none;
        }}
        body[data-view="table"] .table-wrap {{ display: block; }}
        body[data-view="table"] .grid {{ display: none; }}

        .book-table {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.88rem;
            min-width: 900px;
        }}
        .book-table thead {{
            background: var(--primary);
            color: var(--accent);
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        .book-table th {{
            padding: 0.9rem 1rem;
            text-align: left;
            font-weight: 500;
            font-size: 0.78rem;
            letter-spacing: 0.15rem;
            text-transform: uppercase;
            border-bottom: 1px solid rgba(212,175,55,0.3);
            white-space: nowrap;
        }}
        .book-table tbody .row {{
            cursor: pointer;
            transition: background 0.15s;
            border-bottom: 1px solid rgba(10,25,47,0.05);
        }}
        .book-table tbody .row:hover {{ background: var(--bg-card); }}
        .book-table tbody .row.hidden {{ display: none; }}
        .book-table td {{
            padding: 0.7rem 1rem;
            vertical-align: middle;
        }}
        .cell-cover img {{
            width: 36px;
            height: 52px;
            object-fit: cover;
            box-shadow: 0 4px 10px rgba(0,0,0,0.15);
            border-radius: 2px;
            display: block;
        }}
        .cell-title strong {{
            font-family: 'Noto Serif KR', serif;
            color: var(--primary);
            font-weight: 600;
            font-size: 0.95rem;
        }}
        .cell-title span {{
            color: var(--text-muted);
            font-size: 0.78rem;
            font-style: italic;
        }}
        .cell-series {{ color: var(--accent); font-size: 0.8rem; letter-spacing: 0.05rem; white-space: nowrap; }}
        .cell-price {{ font-family: 'Playfair Display', serif; color: var(--accent); font-weight: 700; white-space: nowrap; }}
        .cell-pubdate {{ color: var(--text-muted); font-size: 0.82rem; white-space: nowrap; }}
        .cell-isbn {{ color: var(--text-muted); font-size: 0.78rem; font-family: 'Courier New', monospace; }}
        .status-tag {{
            display: inline-block;
            font-size: 0.7rem;
            padding: 0.2rem 0.6rem;
            border-radius: 999px;
            letter-spacing: 0.05rem;
        }}
        .status-tag.published {{ background: var(--accent-soft); color: #8a6e1a; }}
        .status-tag.upcoming {{ background: rgba(10,25,47,0.06); color: var(--text-muted); }}
        .row.upcoming .cell-cover img {{ filter: grayscale(0.4) brightness(0.85); }}
        .row.upcoming .cell-title strong {{ color: var(--text-muted); }}
        .search-input {{
            width: 100%;
            padding: 1rem 3rem 1rem 3rem;
            border: 1px solid rgba(10,25,47,0.15);
            border-radius: 4px;
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.95rem;
            color: var(--primary);
            background: var(--white);
            transition: border-color 0.3s, box-shadow 0.3s;
            letter-spacing: 0.05rem;
        }}
        .search-input:focus {{
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(212,175,55,0.15);
        }}
        .search-input::placeholder {{
            color: var(--text-muted);
            font-weight: 300;
        }}
        .search-icon {{
            position: absolute;
            left: 1.1rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
            font-size: 1rem;
            pointer-events: none;
        }}
        .search-clear {{
            position: absolute;
            right: 1rem;
            top: 50%;
            transform: translateY(-50%);
            background: none;
            border: none;
            color: var(--text-muted);
            font-size: 1.2rem;
            cursor: pointer;
            padding: 0.3rem;
            display: none;
            line-height: 1;
        }}
        .search-clear.active {{ display: block; }}
        .search-clear:hover {{ color: var(--primary); }}
        /* 공유 토스트 */
        .share-toast {{
            position: fixed;
            left: 50%;
            bottom: 60px;
            transform: translate(-50%, 80px);
            background: var(--primary);
            color: white;
            padding: 0.7rem 1.3rem;
            border: 1px solid var(--accent);
            border-radius: 4px;
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.88rem;
            font-weight: 700;
            box-shadow: 0 8px 22px rgba(10,25,47,0.35);
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.25s, transform 0.25s;
            z-index: 1300;
        }}
        .share-toast.show {{
            opacity: 1;
            transform: translate(-50%, 0);
        }}
        /* "이어서 읽기" 섹션 */
        .recent-books {{
            margin: 1.6rem 0 0.8rem;
            padding: 1.4rem 1.6rem;
            background: linear-gradient(135deg, var(--accent-soft) 0%, rgba(212,175,55,0.05) 100%);
            border: 1px solid rgba(212,175,55,0.25);
            border-radius: 6px;
        }}
        .recent-books[hidden] {{ display: none; }}
        .recent-books-title {{
            font-family: 'Playfair Display', serif;
            font-size: 1.15rem;
            color: var(--primary);
            margin-bottom: 1rem;
            font-weight: 700;
        }}
        .recent-books-list {{
            display: flex;
            gap: 1rem;
            overflow-x: auto;
            padding-bottom: 0.4rem;
            -webkit-overflow-scrolling: touch;
        }}
        .recent-card {{
            flex: 0 0 auto;
            display: flex;
            gap: 0.8rem;
            text-decoration: none;
            color: inherit;
            background: white;
            border: 1px solid rgba(10,25,47,0.1);
            border-radius: 4px;
            padding: 0.7rem 0.9rem 0.7rem 0.7rem;
            min-width: 240px;
            max-width: 280px;
            transition: all 0.18s;
        }}
        .recent-card:hover {{
            border-color: var(--accent);
            box-shadow: 0 4px 14px rgba(212,175,55,0.18);
            transform: translateY(-1px);
        }}
        .recent-cover {{
            width: 50px;
            height: 70px;
            flex-shrink: 0;
            background-size: cover;
            background-position: center;
            border-radius: 2px;
            box-shadow: 0 2px 6px rgba(10,25,47,0.18);
        }}
        .recent-body {{
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-width: 0;
        }}
        .recent-title {{
            font-family: 'Noto Serif KR', serif;
            font-size: 0.92rem;
            font-weight: 600;
            color: var(--primary);
            line-height: 1.4;
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }}
        .recent-progress {{
            display: flex;
            gap: 0.5rem;
            align-items: center;
            margin-top: 0.4rem;
        }}
        .recent-progress-bar {{
            flex: 1;
            height: 4px;
            background: rgba(10,25,47,0.08);
            border-radius: 2px;
            overflow: hidden;
        }}
        .recent-progress-fill {{
            height: 100%;
            background: var(--accent);
            border-radius: 2px;
        }}
        .recent-pct {{
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.72rem;
            font-weight: 800;
            color: var(--primary);
            white-space: nowrap;
        }}
        @media (max-width: 720px) {{
            .recent-books {{ padding: 1rem 0.9rem; }}
            .recent-card {{ min-width: 200px; max-width: 220px; }}
        }}
        .no-results {{
            display: none;
            text-align: center;
            padding: 4rem 2rem;
            color: var(--text-muted);
            font-family: 'Noto Sans KR', sans-serif;
        }}
        .no-results.active {{ display: block; }}
        .no-results h3 {{
            font-family: 'Playfair Display', serif;
            color: var(--primary);
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
        }}
        .no-results h3 mark {{
            background: var(--accent);
            color: var(--primary);
            padding: 0.05em 0.25em;
            border-radius: 2px;
        }}
        .no-results p {{
            font-size: 0.92rem;
            line-height: 1.7;
            max-width: 460px;
            margin: 0 auto 1.4rem;
        }}
        .no-results-actions {{
            display: inline-flex;
            gap: 0.6rem;
            flex-wrap: wrap;
            justify-content: center;
        }}
        .no-results-btn {{
            background: var(--primary);
            color: white;
            border: 1px solid var(--primary);
            padding: 0.6rem 1.2rem;
            border-radius: 3px;
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.85rem;
            cursor: pointer;
        }}
        .no-results-btn:hover {{ background: var(--accent); border-color: var(--accent); color: var(--primary); }}
        .no-results-btn.outline {{ background: transparent; color: var(--primary); }}
        .no-results-btn.outline:hover {{ background: var(--primary); color: white; }}
        .catalog-info {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-bottom: 2rem;
            padding-bottom: 1.2rem;
            border-bottom: 1px solid rgba(10,25,47,0.08);
        }}
        .catalog-info .count {{
            font-family: 'Playfair Display', serif;
            color: var(--primary);
            font-size: 1.4rem;
        }}
        .catalog-info .count em {{
            color: var(--accent);
            font-style: normal;
            font-weight: 700;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 2rem;
        }}
        .card {{
            background: var(--white);
            border-radius: 4px;
            box-shadow: 0 4px 20px rgba(10,25,47,0.06);
            overflow: hidden;
            transition: box-shadow 0.25s ease, border-color 0.25s ease;
            display: flex;
            flex-direction: column;
            cursor: pointer;
            border: 1px solid transparent;
        }}
        .card.hidden {{ display: none; }}
        @media (hover: hover) {{
            .card:hover {{
                box-shadow: 0 8px 24px rgba(10,25,47,0.10);
                border-color: rgba(212,175,55,0.35);
            }}
        }}
        /* 본문 뷰어에서 돌아왔을 때 그 책 카드 잠깐 강조 */
        @keyframes focusPulse {{
            0%   {{ box-shadow: 0 0 0 0 rgba(212,175,55,0.0); border-color: rgba(212,175,55,0.0); }}
            18%  {{ box-shadow: 0 0 0 8px rgba(212,175,55,0.45); border-color: var(--accent); }}
            55%  {{ box-shadow: 0 0 0 4px rgba(212,175,55,0.25); border-color: var(--accent); }}
            100% {{ box-shadow: 0 0 0 0 rgba(212,175,55,0.0); border-color: rgba(212,175,55,0.0); }}
        }}
        .card.focus-pulse,
        .row.focus-pulse {{
            animation: focusPulse 2.4s ease-out;
            border: 1px solid var(--accent);
        }}
        .row.focus-pulse {{ background: var(--accent-soft); }}
        /* 보유 배지 (카드) */
        .card-cover {{ position: relative; }}
        .card-owned {{
            position: absolute;
            top: 0.6rem;
            right: 0.6rem;
            background: var(--accent);
            color: var(--primary);
            padding: 0.25rem 0.6rem;
            border-radius: 12px;
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.04rem;
            box-shadow: 0 2px 6px rgba(10,25,47,0.2);
            z-index: 2;
        }}
        .card-owned[hidden] {{ display: none; }}
        /* 보유 칩 (테이블 row) */
        .row-owned {{
            display: inline-block;
            margin-left: 0.6rem;
            padding: 0.05rem 0.55rem;
            background: var(--accent);
            color: var(--primary);
            border-radius: 10px;
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.7rem;
            font-weight: 800;
            letter-spacing: 0.04rem;
            vertical-align: middle;
        }}
        .row-owned[hidden] {{ display: none; }}
        /* 그룹 탭 보유 진척 칩 */
        .tab-owned {{
            display: inline-block;
            margin-left: 0.45rem;
            font-size: 0.7rem;
            background: var(--accent);
            color: var(--primary);
            padding: 0.05rem 0.45rem;
            border-radius: 9px;
            font-weight: 800;
            letter-spacing: 0.02rem;
            vertical-align: middle;
        }}
        /* 진도 게이지 (카드) */
        .card-progress {{
            margin-top: 0.6rem;
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }}
        .card-progress[hidden] {{ display: none; }}
        .card-progress-bar {{
            flex: 1;
            height: 4px;
            background: rgba(10,25,47,0.08);
            border-radius: 2px;
            overflow: hidden;
        }}
        .card-progress-fill {{
            height: 100%;
            background: var(--accent);
            width: 0;
            transition: width 0.3s ease;
        }}
        .card-progress-text {{
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.72rem;
            color: var(--primary);
            font-weight: 700;
            white-space: nowrap;
        }}
        /* 진도 칩 (테이블 row) */
        .row-progress {{
            display: inline-block;
            margin-left: 0.6rem;
            padding: 0.05rem 0.5rem;
            background: var(--accent-soft);
            color: #8a6e1a;
            border-radius: 10px;
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.72rem;
            font-weight: 700;
            vertical-align: middle;
        }}
        .row-progress[hidden] {{ display: none; }}
        /* 발행 예정 (upcoming) */
        .card.upcoming .card-cover img {{
            filter: grayscale(0.4) brightness(0.85);
        }}
        .card.upcoming .card-buy {{
            background: #ddd6c8;
            color: #8a7f6c;
            font-weight: 500;
        }}
        .card.upcoming:hover .card-buy {{
            background: #ddd6c8;
            color: #8a7f6c;
            font-weight: 500;
        }}
        .card-countdown {{
            position: absolute;
            top: 0.8rem;
            right: 0.8rem;
            background: rgba(255,255,255,0.95);
            color: var(--primary);
            font-family: 'Playfair Display', serif;
            font-size: 0.85rem;
            font-weight: 700;
            padding: 0.3rem 0.7rem;
            border-radius: 2px;
            border: 1px solid rgba(212,175,55,0.4);
            display: none;
        }}
        .card.upcoming .card-countdown {{ display: block; }}
        .card-cover {{
            background: linear-gradient(160deg, var(--primary) 0%, #1f3559 100%);
            padding: 1.4rem;
            display: flex;
            justify-content: center;
            align-items: center;
            aspect-ratio: 3 / 3.5;
            position: relative;
            overflow: hidden;
        }}
        .card-cover img {{
            max-width: 100%;
            max-height: 100%;
            box-shadow: 0 12px 28px rgba(0,0,0,0.45);
            border-radius: 2px;
        }}
        .card-ep {{
            position: absolute;
            top: 0.8rem;
            left: 0.8rem;
            background: var(--accent);
            color: var(--primary);
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.1rem;
            padding: 0.25rem 0.7rem;
            border-radius: 2px;
        }}
        .card-body {{
            padding: 1.2rem 1.3rem 1.4rem;
            display: flex;
            flex-direction: column;
            flex: 1;
        }}
        .card-title {{
            font-family: 'Playfair Display', serif;
            font-size: 1.1rem;
            color: var(--primary);
            line-height: 1.35;
            margin-bottom: 0.3rem;
            min-height: 2.8em;
        }}
        .card-subtitle {{
            font-family: 'Noto Serif KR', serif;
            font-size: 0.78rem;
            color: var(--text-muted);
            font-style: italic;
            margin-bottom: 0.9rem;
            min-height: 1.4em;
        }}
        .card-meta {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-top: auto;
            padding-top: 0.9rem;
            border-top: 1px solid rgba(10,25,47,0.06);
        }}
        .card-price {{
            font-family: 'Playfair Display', serif;
            font-size: 1.05rem;
            color: var(--accent);
            font-weight: 700;
        }}
        .card-pubdate {{
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.72rem;
            color: var(--text-muted);
        }}
        .card-buy {{
            margin-top: 0.9rem;
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.85rem;
            color: var(--primary);
            background: var(--bg-card);
            padding: 0.65rem;
            text-align: center;
            border-radius: 2px;
            font-weight: 500;
            transition: all 0.3s;
            letter-spacing: 0.1rem;
        }}
        .card:hover .card-buy {{
            background: var(--accent);
            color: var(--primary);
            font-weight: 700;
        }}

        /* ─── MODAL ─── */
        .modal-bg {{
            position: fixed;
            inset: 0;
            background: rgba(10,25,47,0.85);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            padding: 2rem;
            overflow-y: auto;
        }}
        .modal-bg.active {{ display: flex; }}
        .modal {{
            background: var(--white);
            max-width: 920px;
            width: 100%;
            border-radius: 4px;
            display: grid;
            grid-template-columns: 320px 1fr;
            overflow: hidden;
            position: relative;
            box-shadow: 0 24px 80px rgba(0,0,0,0.5);
            margin: auto;
        }}
        .modal-close {{
            position: absolute;
            top: 0.8rem;
            right: 0.8rem;
            background: var(--primary);
            color: white;
            border: 2px solid var(--accent);
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.9rem;
            font-weight: 700;
            cursor: pointer;
            padding: 0.45rem 0.95rem;
            border-radius: 4px;
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            z-index: 10;
            transition: all 0.2s;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }}
        .modal-close:hover {{
            background: var(--accent);
            color: var(--primary);
        }}
        .modal-cover {{
            background: linear-gradient(160deg, var(--primary) 0%, #1f3559 100%);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 3rem 2rem;
            text-align: center;
        }}
        .modal-cover img {{
            width: 220px;
            box-shadow: 0 16px 36px rgba(0,0,0,0.45);
            border-radius: 4px;
            margin-bottom: 1.4rem;
        }}
        .modal-badges {{ display: flex; gap: 0.5rem; flex-wrap: wrap; justify-content: center; }}
        .modal-badge {{
            background: var(--accent);
            color: var(--primary);
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.15rem;
            padding: 0.3rem 0.9rem;
            border-radius: 2px;
        }}
        .modal-badge.outline {{
            background: transparent;
            color: var(--accent);
            border: 1px solid rgba(212,175,55,0.5);
        }}
        .modal-info {{ padding: 2.5rem; display: flex; flex-direction: column; }}
        .modal-meta {{
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.75rem;
            color: var(--accent);
            letter-spacing: 0.3rem;
            text-transform: uppercase;
            margin-bottom: 0.6rem;
        }}
        .modal-title {{
            font-family: 'Playfair Display', serif;
            font-size: 1.7rem;
            color: var(--primary);
            margin-bottom: 0.3rem;
            line-height: 1.3;
        }}
        .modal-subtitle {{
            font-family: 'Noto Serif KR', serif;
            font-size: 0.95rem;
            color: var(--text-muted);
            font-style: italic;
            margin-bottom: 1.2rem;
        }}
        .modal-divider {{
            width: 36px;
            height: 2px;
            background: var(--accent);
            margin-bottom: 1.2rem;
        }}
        .modal-summary {{
            font-size: 0.95rem;
            color: var(--text-main);
            line-height: 2;
            margin-bottom: 1.3rem;
        }}
        .modal-metaphor {{
            background: var(--accent-soft);
            border-left: 3px solid var(--accent);
            padding: 1rem 1.2rem;
            font-size: 0.88rem;
            color: var(--text-muted);
            font-style: italic;
            line-height: 1.7;
            margin-bottom: 1.4rem;
        }}
        .modal-keywords {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
            margin-bottom: 1.4rem;
        }}
        .keyword-chip {{
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.72rem;
            color: var(--text-muted);
            background: rgba(10,25,47,0.04);
            padding: 0.25rem 0.7rem;
            border-radius: 999px;
        }}
        .modal-details {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.9rem;
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.82rem;
            padding: 1.2rem 0;
            border-top: 1px solid rgba(10,25,47,0.06);
            border-bottom: 1px solid rgba(10,25,47,0.06);
            margin-bottom: 1.4rem;
        }}
        .modal-details .item .label {{
            color: var(--text-muted);
            font-size: 0.7rem;
            letter-spacing: 0.1rem;
            text-transform: uppercase;
            display: block;
            margin-bottom: 0.2rem;
        }}
        .modal-details .item .value {{
            color: var(--primary);
            font-weight: 500;
        }}
        .modal-details .item.price .value {{
            color: var(--accent);
            font-weight: 700;
            font-family: 'Playfair Display', serif;
            font-size: 1.05rem;
        }}
        .modal-actions {{ display: flex; gap: 0.6rem; flex-wrap: wrap; }}
        .purchase-note {{
            background: #fff8e1;
            border-left: 3px solid var(--accent);
            padding: 0.75rem 1rem;
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.82rem;
            color: #5d4f3a;
            line-height: 1.65;
            margin: 0.6rem 0 1rem;
            border-radius: 2px;
        }}
        .btn {{
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.88rem;
            font-weight: 500;
            padding: 0.85rem 1.4rem;
            border: none;
            border-radius: 2px;
            cursor: pointer;
            letter-spacing: 0.1rem;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s;
        }}
        .btn-primary {{
            background: var(--accent);
            color: var(--primary);
            font-weight: 700;
            flex: 1;
        }}
        .btn-primary:hover {{ background: #b8941f; }}
        .hl-term {{
            background: var(--accent);
            color: var(--primary);
            padding: 0 0.15em;
            border-radius: 2px;
            font-weight: 700;
        }}
        .resume-pct {{
            display: inline-block;
            margin-left: 0.4rem;
            background: var(--primary);
            color: white;
            padding: 0.1rem 0.5rem;
            border-radius: 10px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.02em;
        }}
        .btn-outline {{
            background: transparent;
            color: var(--primary);
            border: 1px solid rgba(10,25,47,0.2);
        }}
        .btn-outline:hover {{ border-color: var(--accent); color: var(--accent); }}
        .btn-author {{
            background: #0F1E3C;
            color: #d4af37;
            border: 1px solid #d4af37;
        }}
        .btn-author:hover {{ background: #d4af37; color: #0F1E3C; }}
        .btn-youtube {{
            background: #c4302b;
            color: #fff;
            border: 1px solid #c4302b;
            font-weight: 600;
        }}
        .btn-youtube:hover {{ background: #a52521; border-color: #a52521; color: #fff; }}
        .btn-cart {{
            background: transparent;
            color: var(--primary);
            border: 1px solid var(--accent);
            font-weight: 600;
        }}
        .btn-cart:hover {{ background: var(--accent); color: var(--primary); }}
        .btn-cart.in-cart {{
            background: var(--accent);
            color: var(--primary);
        }}
        .btn-cart.in-cart:hover {{ background: transparent; color: var(--primary); }}

        /* 구매 모달 (송금 안내) */
        .buy-modal-bg {{
            position: fixed;
            inset: 0;
            background: rgba(10,25,47,0.85);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1100;
            padding: 2rem;
        }}
        .buy-modal-bg.active {{ display: flex; }}
        /* 결제수단 선택 모달 */
        .pmp-back {{
            position: fixed;
            inset: 0;
            background: rgba(10,25,47,0.7);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1200;
            padding: 1.5rem;
            backdrop-filter: blur(2px);
        }}
        .pmp-modal {{
            background: white;
            max-width: 460px;
            width: 100%;
            border-radius: 6px;
            box-shadow: 0 24px 60px rgba(0,0,0,0.4);
            padding: 2rem 1.8rem 1.6rem;
            position: relative;
            font-family: 'Noto Sans KR', sans-serif;
        }}
        .pmp-close {{
            position: absolute;
            top: 0.6rem; right: 0.9rem;
            background: none; border: none;
            font-size: 1.6rem;
            color: var(--text-muted);
            cursor: pointer;
            line-height: 1;
        }}
        .pmp-close:hover {{ color: var(--primary); }}
        .pmp-eyebrow {{
            font-size: 0.7rem;
            letter-spacing: 0.4rem;
            color: var(--accent);
            text-transform: uppercase;
            margin-bottom: 0.4rem;
        }}
        .pmp-title {{
            font-family: 'Playfair Display', serif;
            font-size: 1.3rem;
            color: var(--primary);
            margin-bottom: 0.4rem;
        }}
        .pmp-price {{
            font-family: 'Playfair Display', serif;
            font-size: 1.4rem;
            color: var(--accent);
            font-weight: 700;
            margin-bottom: 1.4rem;
        }}
        .pmp-grid {{
            display: flex;
            flex-direction: column;
            gap: 0.6rem;
        }}
        .pmp-btn {{
            text-align: left;
            padding: 1rem 1.1rem;
            border: 1px solid rgba(10,25,47,0.18);
            border-radius: 4px;
            background: white;
            cursor: pointer;
            font-family: inherit;
            transition: all 0.18s;
        }}
        .pmp-btn:hover {{
            border-color: var(--accent);
            background: rgba(212,175,55,0.06);
            transform: translateX(2px);
        }}
        .pmp-btn .pmp-label {{
            display: block;
            font-size: 1rem;
            font-weight: 700;
            color: var(--primary);
        }}
        .pmp-btn .pmp-desc {{
            display: block;
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
        }}
        .pmp-btn:disabled {{ opacity: 0.5; cursor: wait; }}
        .pmp-spin {{
            display: inline-block;
            width: 14px;
            height: 14px;
            border: 2px solid rgba(10,25,47,0.2);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: pmp-spin 0.7s linear infinite;
            vertical-align: middle;
            margin-right: 0.4rem;
        }}
        @keyframes pmp-spin {{ to {{ transform: rotate(360deg); }} }}
        .buy-modal {{
            background: var(--white);
            max-width: 480px;
            width: 100%;
            border-radius: 4px;
            padding: 2.5rem;
            position: relative;
        }}
        .step {{ display: flex; gap: 0.8rem; margin-bottom: 0.8rem; font-size: 0.92rem; }}
        .step-num {{
            background: var(--accent);
            color: var(--primary);
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.78rem;
            flex-shrink: 0;
        }}
        .info-block {{
            background: var(--bg-card);
            border-radius: 4px;
            padding: 1.2rem;
            margin: 1.2rem 0;
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.88rem;
            line-height: 1.9;
        }}
        .info-block strong {{ color: var(--primary); }}

        @media (max-width: 720px) {{
            header {{ padding: 1rem 1.5rem; }}
            nav > a {{ display: none; }}    /* 헤더 메뉴 항목만 숨김. 사용자 chip 드롭다운 메뉴는 보존 */
            .grid {{ grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 1.2rem; }}
            .card-title {{ font-size: 1rem; }}
            .tabs {{ overflow-x: auto; flex-wrap: nowrap; padding: 0 1rem; -webkit-overflow-scrolling: touch; }}
            .tab {{ padding: 0.8rem 1rem; flex-shrink: 0; white-space: nowrap; }}
            .modal {{ grid-template-columns: 1fr; max-height: 90vh; overflow-y: auto; }}
            .modal-cover {{ padding: 2rem; }}
            .modal-cover img {{ width: 160px; }}
            .modal-info {{ padding: 1.8rem; }}
            .modal-details {{ grid-template-columns: 1fr 1fr; }}
            /* 모바일: 테이블이 좁아 의미 없음 → 자동으로 그리드 강제 */
            body[data-view="table"] .table-wrap {{ display: none; }}
            body[data-view="table"] .grid {{ display: grid; }}
        }}
    </style>
    <script src="author_mode.js" defer></script>
    <script src="cart.js" defer></script>
    <script src="beta-banner.js" defer></script>
    <script src="pwa.js" defer></script>
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
    <script src="auth.js" defer></script>
</head>
<body data-view="table">

<header>
    <a href="/" class="logo">
        <img src="logo/logo_horizontal.svg" alt="AI 시대 영성">
        <span class="label">CATALOG</span>
    </a>
    <nav>
        <a href="/">홈</a>
        <a href="/catalog" class="active">도서</a>
        <a href="/library">내 서가</a>
    </nav>
</header>

<section class="page-head">
    <span class="label">Catalog</span>
    <h1>출간 도서</h1>
    <p class="desc">{total}권의 영성 묵상 — 개인이 운영하는 독립 출판사 AI 시대 영성</p>
    <div class="divider"></div>
    <div class="head-qr">
        <img src="qr/catalog.png" alt="도서 카탈로그 QR">
        <div class="head-qr-text">
            <strong>도서 목록 공유</strong>
            <span>QR로 121권 책방<br>모바일에서 보기</span>
        </div>
    </div>
</section>

<nav class="tabs" id="seriesTabs">
    <button class="tab active" data-filter="all">전체 {total}</button>
    <button class="tab" data-filter="s1-main">시즌 1 ({s1_main_count})</button>
    <button class="tab" data-filter="s2-main">시즌 2 본권 ({s2_main_count})</button>
    <button class="tab" data-filter="omnibus">종합책 ({omni_count})</button>
</nav>

<nav class="tabs sub hidden" id="groupTabs">
    <button class="tab active" data-group="all">G01-G10 전체</button>
    <button class="tab" data-group="G01">G01 천국과 영계</button>
    <button class="tab" data-group="G02">G02 알고리즘 시대의 영성</button>
    <button class="tab" data-group="G03">G03 겨자씨에서 산까지</button>
    <button class="tab" data-group="G04">G04 발자국과 눈물</button>
    <button class="tab" data-group="G05">G05 흉터 위의 빛</button>
    <button class="tab" data-group="G06">G06 광야의 외침</button>
    <button class="tab" data-group="G07">G07 바람과 불</button>
    <button class="tab" data-group="G08">G08 무릎의 자리</button>
    <button class="tab" data-group="G09">G09 곁에 두신 분들</button>
    <button class="tab" data-group="G10">G10 이미, 그러나 아직</button>
</nav>

<div class="catalog">
    <div class="search-area">
        <span class="search-area-label">Search</span>
        <div class="search-scope" id="searchScope">
            <button class="scope-btn active" data-scope="all">전체</button>
            <button class="scope-btn" data-scope="title">제목</button>
            <button class="scope-btn" data-scope="subtitle">부제</button>
            <button class="scope-btn" data-scope="keywords">키워드</button>
            <button class="scope-btn" data-scope="summary">요약</button>
            <button class="scope-btn" data-scope="isbn">ISBN</button>
        </div>
        <div class="filter-bar">
            <div class="search-bar">
                <span class="search-icon">⌕</span>
                <input type="text" class="search-input" id="searchInput" placeholder="제목·저자·키워드 입력 — 입력하는 대로 자동 필터" autocomplete="off">
                <button class="search-clear" id="searchClear" title="지우기">×</button>
            </div>
            <button class="search-submit" id="searchSubmit">검색 ↵</button>
        </div>
        <section class="recent-books" id="recentBooks" hidden>
            <h3 class="recent-books-title">📖 이어서 읽기</h3>
            <div class="recent-books-list" id="recentBooksList"></div>
        </section>
        <div class="sort-row">
            <select class="sort-select" id="sortSelect">
                <option value="default">기본 순서 (시즌·시리즈)</option>
                <option value="resume">이어보기 우선 (최근 읽은 순)</option>
                <option value="relevance">검색 관련도순</option>
                <option value="title-asc">제목 가나다순</option>
                <option value="title-desc">제목 가나다 역순</option>
                <option value="subtitle-asc">부제 가나다순</option>
                <option value="pubdate-asc">발행일 빠른순</option>
                <option value="pubdate-desc">발행일 늦은순</option>
                <option value="price-asc">가격 낮은순</option>
                <option value="price-desc">가격 높은순</option>
            </select>
        </div>
    </div>

    <div class="catalog-info">
        <p class="count"><span id="visibleCount">{total}</span><em></em> 권 표시 중</p>
        <div style="display:flex; gap:1rem; align-items:center;">
            <p class="desc" id="filterDesc">전체 도서</p>
            <div class="view-toggle">
                <button class="view-btn" data-view="grid" title="그리드 보기">⊞ 그리드</button>
                <button class="view-btn active" data-view="table" title="테이블 보기">☰ 테이블</button>
            </div>
        </div>
    </div>

    <div class="grid" id="grid">
{cards}
    </div>

    <div class="table-wrap" id="tableWrap">
        <table class="book-table">
            <thead>
                <tr>
                    <th></th>
                    <th>제목 / 부제</th>
                    <th>시리즈</th>
                    <th>가격</th>
                    <th>발행일</th>
                    <th>ISBN</th>
                    <th>상태</th>
                </tr>
            </thead>
            <tbody id="tbody">
{rows}
            </tbody>
        </table>
    </div>

    <div class="no-results" id="noResults">
        <h3 id="noResultsTitle">검색 결과가 없습니다</h3>
        <p id="noResultsHint">다른 키워드로 시도해보세요. 제목·부제·키워드·요약·ISBN을 검색합니다.</p>
        <div class="no-results-actions">
            <button class="no-results-btn" onclick="(function(){{ document.getElementById('searchInput').value=''; document.getElementById('searchInput').dispatchEvent(new Event('input',{{bubbles:true}})); }})()">검색어 지우기</button>
            <button class="no-results-btn outline" onclick="(function(){{ document.querySelectorAll('.tabs .tab[data-filter=all]')[0]?.click(); }})()">전체 도서 보기</button>
        </div>
    </div>
</div>

<!-- 권 상세 모달 -->
<div class="modal-bg" id="bookModal" onclick="if(event.target===this) closeBook()">
    <div class="modal">
        <button class="modal-close" onclick="closeBook()" title="닫기 (ESC)">× 닫기</button>
        <div class="modal-cover">
            <img id="mCover" src="" alt="">
            <div class="modal-badges" id="mBadges"></div>
        </div>
        <div class="modal-info">
            <p class="modal-meta" id="mMeta"></p>
            <h2 class="modal-title" id="mTitle"></h2>
            <p class="modal-subtitle" id="mSubtitle"></p>
            <div class="modal-divider"></div>
            <p class="modal-summary" id="mSummary"></p>
            <div class="modal-metaphor" id="mMetaphor"></div>
            <div class="modal-keywords" id="mKeywords"></div>
            <div class="modal-details">
                <div class="item price"><span class="label">정가</span><span class="value" id="mPrice"></span></div>
                <div class="item"><span class="label">ISBN</span><span class="value" id="mIsbn"></span></div>
                <div class="item"><span class="label">발행</span><span class="value" id="mPubdate"></span></div>
                <div class="item"><span class="label">형태</span><span class="value" id="mFormat"></span></div>
            </div>
            <div id="mPurchaseNote" class="purchase-note" style="display:none"></div>
            <div class="modal-actions">
                <button class="btn btn-primary">구매하기</button>
                <a class="btn btn-primary" id="mRead" target="_blank" rel="noopener" style="display:none; background:var(--primary); color:white;">본문 보기 (무료)</a>
                <a class="btn btn-outline" id="mPreview" target="_blank" rel="noopener">미리보기</a>
                <a class="btn btn-youtube" id="mYoutube" target="_blank" rel="noopener" style="display:none">유튜브 영상 ▶</a>
                <button class="btn btn-cart" id="mCart" type="button">장바구니 담기</button>
                <button class="btn btn-outline" id="mShare" type="button" title="이 책 공유하기">🔗 공유</button>
                <a class="btn btn-author author-only" id="mDownload" download style="display:none">EPUB 다운로드</a>
                <button class="btn btn-outline" onclick="closeBook()" style="border-color:var(--primary); color:var(--primary); font-weight:600">← 책 목록으로</button>
            </div>
        </div>
    </div>
</div>

<!-- 구매 안내 모달 -->
<div class="buy-modal-bg" id="buyModal" onclick="if(event.target===this) closeBuy()">
    <div class="buy-modal">
        <button class="modal-close" onclick="closeBuy()" title="닫기 (ESC)">× 닫기</button>
        <p style="font-family:'Noto Sans KR',sans-serif; font-size:0.7rem; letter-spacing:0.4rem; color:var(--accent); text-transform:uppercase; margin-bottom:0.5rem;">Purchase</p>
        <h3 style="font-family:'Playfair Display',serif; font-size:1.4rem; color:var(--primary); margin-bottom:1.2rem;" id="bTitle"></h3>
        <p style="font-size:0.92rem; color:var(--text-muted); margin-bottom:1rem;">결제 시스템 연결 전이라 일단 송금 방식으로 진행합니다.</p>

        <div class="step"><span class="step-num">1</span><span>아래 계좌로 송금 또는 카카오페이 송금</span></div>
        <div class="step"><span class="step-num">2</span><span>이메일·송금자명·도서명을 카카오톡 채널로 보내주세요</span></div>
        <div class="step"><span class="step-num">3</span><span>확인 후 1시간 이내 EPUB 파일을 이메일로 발송</span></div>

        <div class="info-block">
            <strong>입금 계좌</strong><br>
            농협 351-3386-4491-83<br>
            예금주: 박헌근(AI 시대 영성)<br><br>
            <strong>카카오톡 채널</strong><br>
            <a href="https://pf.kakao.com/_PxdHTX" target="_blank" style="color: var(--primary); text-decoration: underline;">AI 시대 영성</a>
        </div>

        <p style="font-size:0.8rem; color:#999;">* 결제 시스템(토스페이먼츠) 가입 후 자동 결제·자동 발송으로 전환됩니다.</p>

        <div style="display:flex; gap:0.6rem; margin-top:1.2rem;">
            <a href="https://pf.kakao.com/_PxdHTX" target="_blank" class="btn btn-primary" style="flex:1;">카카오톡 채널 열기</a>
            <button class="btn btn-outline" onclick="closeBuy()">닫기</button>
        </div>
    </div>
</div>

<script>
const PURCHASE_ENABLED = {purchase_enabled};
const PURCHASE_SHORT = '{purchase_short}';
const PURCHASE_NOTE = '{purchase_note}';
const FREE_BETA = {free_beta};
const TOSS_CLIENT_KEY = '{toss_client_key}';
const SUPABASE_URL = '{supabase_url}';
const SUPABASE_ANON_KEY = '{supabase_anon_key}';
const BOOKS = {books_json};

Object.values(BOOKS).forEach(b => {{
    b._title = (b.title || '').toLowerCase();
    b._subtitle = (b.subtitle || '').toLowerCase();
    b._keywords = (b.keywords || '').toLowerCase();
    b._summary = (b.summary || '').toLowerCase();
    b._metaphor = (b.metaphor || '').toLowerCase();
    b._isbn = (b.isbn || '').toLowerCase();
    b._all = [b.title, b.subtitle, b.summary, b.keywords, b.metaphor, b.isbn, b.group_name, b.group, b.author].filter(Boolean).join(' ').toLowerCase();
}});

const $ = (id) => document.getElementById(id);
const $$ = (sel) => document.querySelectorAll(sel);

let currentSeries = 'all';
let currentGroup = 'all';
let currentSearch = '';
let currentSort = 'default';
let currentScope = 'all';

function getPubStatus(pubdateStr) {{
    if (window.isAuthorMode && window.isAuthorMode()) return {{ isPublished: true, daysLeft: 0, label: '' }};
    if (!pubdateStr) return {{ isPublished: true, daysLeft: 0, label: '' }};
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const pub = new Date(pubdateStr);
    pub.setHours(0, 0, 0, 0);
    const diffDays = Math.ceil((pub - today) / (1000 * 60 * 60 * 24));
    return {{
        isPublished: diffDays <= 0,
        daysLeft: diffDays,
        label: diffDays <= 0 ? '' : `D-${{diffDays}}`,
    }};
}}

function applyPublishStatus() {{
    $$('.card').forEach(card => {{
        const pubdate = card.dataset.pubdate;
        const status = getPubStatus(pubdate);
        const cd = card.querySelector('.card-countdown');
        const buy = card.querySelector('.card-buy');
        if (status.isPublished) {{
            card.classList.remove('upcoming');
            cd.textContent = '';
            buy.textContent = '자세히 보기 →';
        }} else {{
            card.classList.add('upcoming');
            cd.textContent = status.label;
            const pubFmt = pubdate.replace(/-/g, '.').slice(5);
            buy.textContent = `${{pubFmt}} 발행 예정`;
        }}
    }});
    $$('.row').forEach(row => {{
        const pubdate = row.dataset.pubdate;
        const status = getPubStatus(pubdate);
        const tag = row.querySelector('.status-tag');
        if (status.isPublished) {{
            row.classList.remove('upcoming');
            tag.classList.add('published');
            tag.classList.remove('upcoming');
            tag.textContent = '발행 완료';
        }} else {{
            row.classList.add('upcoming');
            tag.classList.add('upcoming');
            tag.classList.remove('published');
            tag.textContent = status.label;
        }}
    }});
}}

function shouldShow(el) {{
    const season = el.dataset.season;
    const type = el.dataset.type;
    const group = el.dataset.group;
    const q = currentSearch.toLowerCase().trim();
    let show = false;
    if (currentSeries === 'all') show = true;
    else if (currentSeries === 's1-main') show = season === '1' && type === 'main';
    else if (currentSeries === 's2-main') {{
        show = season === '2' && type === 'main';
        if (show && currentGroup !== 'all') show = group === currentGroup;
    }}
    else if (currentSeries === 'omnibus') show = type === 'omnibus';
    if (show && q) {{
        const b = BOOKS[el.dataset.id];
        const fieldKey = '_' + currentScope;
        const text = b[fieldKey] !== undefined ? b[fieldKey] : b._all;
        show = text.includes(q);
    }}
    return show;
}}

function escapeRe(s) {{ return String(s).replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&'); }}

function highlightInElement(el, q) {{
    if (!el) return;
    // 원본 텍스트는 dataset.origText 에 보존
    if (el.dataset.origText == null) el.dataset.origText = el.textContent;
    const original = el.dataset.origText;
    if (!q) {{
        el.textContent = original;
        return;
    }}
    const re = new RegExp(escapeRe(q), 'gi');
    el.innerHTML = original.replace(/[<>&]/g, c => ({{'<':'&lt;','>':'&gt;','&':'&amp;'}}[c]))
                          .replace(re, m => `<mark class="hl-term">${{m}}</mark>`);
}}

function applySearchHighlight() {{
    const q = currentSearch.toLowerCase().trim();
    // 모든 카드/row 의 제목·부제 — 보이는 것만 하이라이트, 숨겨진 건 원복
    $$('.card .card-title, .card .card-subtitle').forEach(el => {{
        const card = el.closest('.card');
        const visible = card && !card.classList.contains('hidden');
        highlightInElement(el, visible ? q : '');
    }});
    $$('.row .cell-title strong, .row .cell-title span').forEach(el => {{
        const row = el.closest('.row');
        const visible = row && !row.classList.contains('hidden');
        highlightInElement(el, visible ? q : '');
    }});
}}

function applyFilter(scrollToResults = false) {{
    let visible = 0;
    $$('.card').forEach(card => {{
        const show = shouldShow(card);
        card.classList.toggle('hidden', !show);
        if (show) visible++;
    }});
    $$('.row').forEach(row => {{
        const show = shouldShow(row);
        row.classList.toggle('hidden', !show);
    }});
    $('visibleCount').textContent = visible;
    applySearchHighlight();
    const subTabs = $('groupTabs');
    subTabs.classList.toggle('hidden', currentSeries !== 's2-main');
    const desc = {{
        'all': '전체 도서',
        's1-main': '시즌 1 — AI 시대 영성 첫 묵상 시리즈 10권',
        's2-main': '시즌 2 — 100권 영성 묵상 시리즈',
        'omnibus': '종합책 — 시리즈를 한 권으로 묶은 합본'
    }};
    let descText = desc[currentSeries] || '';
    const q = currentSearch.toLowerCase().trim();
    if (q) descText += ` · 검색: "${{currentSearch}}"`;
    $('filterDesc').textContent = descText;
    $('noResults').classList.toggle('active', visible === 0);
    if (visible === 0) {{
        const titleEl = $('noResultsTitle');
        const hintEl = $('noResultsHint');
        if (q) {{
            titleEl.innerHTML = `'<mark class="hl-term">${{currentSearch.replace(/[<>&]/g, c => ({{'<':'&lt;','>':'&gt;','&':'&amp;'}}[c]))}}</mark>' 와 일치하는 책을 찾지 못했어요`;
            hintEl.textContent = '키워드를 더 짧게 줄여보거나, 다른 표현을 시도해보세요. 제목·부제·키워드·요약·ISBN 모두 검색됩니다.';
        }} else {{
            titleEl.textContent = '이 영역에 책이 없습니다';
            hintEl.textContent = '다른 시즌·그룹 탭을 눌러 전체 도서를 둘러보세요.';
        }}
    }}
    $('searchClear').classList.toggle('active', q.length > 0);

    if (scrollToResults) {{
        // 첫 번째 보이는 카드 또는 결과 영역으로 부드럽게 스크롤
        requestAnimationFrame(() => {{
            const firstCard = document.querySelector('.card:not(.hidden)') || document.getElementById('tbody');
            if (!firstCard) return;
            const stickyH = (document.querySelector('header')?.offsetHeight || 0)
                          + (document.querySelector('.filter-bar')?.offsetHeight || 0) + 16;
            const top = firstCard.getBoundingClientRect().top + window.scrollY - stickyH;
            window.scrollTo({{ top: Math.max(0, top), behavior: 'smooth' }});
        }});
    }}
}}

const searchInput = $('searchInput');
const searchClear = $('searchClear');
const searchSubmit = $('searchSubmit');

function runSearch() {{
    currentSearch = searchInput.value;
    applyFilter();
    applySort();
}}

let _searchTimer = null;
searchInput.addEventListener('input', (e) => {{
    searchClear.classList.toggle('active', e.target.value.length > 0);
    // 즉시 입력 필터링 (debounce 220ms)
    clearTimeout(_searchTimer);
    _searchTimer = setTimeout(runSearch, 220);
}});
searchInput.addEventListener('keydown', (e) => {{
    if (e.key === 'Enter') {{
        e.preventDefault();
        clearTimeout(_searchTimer);
        runSearch();
    }} else if (e.key === 'Escape') {{
        e.preventDefault();
        searchInput.value = '';
        searchClear.classList.remove('active');
        clearTimeout(_searchTimer);
        runSearch();
    }}
}});
searchSubmit.addEventListener('click', runSearch);
searchClear.addEventListener('click', () => {{
    searchInput.value = '';
    currentSearch = '';
    searchClear.classList.remove('active');
    applyFilter();
    applySort();
    searchInput.focus();
}});

const sortSelect = $('sortSelect');
const grid = $('grid');
const tbody = $('tbody');
const originalOrder = Array.from(grid.children).map(c => c.dataset.id);

function relevanceScore(b, q) {{
    if (!q) return 0;
    const title = (b.title || '').toLowerCase();
    const subtitle = (b.subtitle || '').toLowerCase();
    const keywords = (b.keywords || '').toLowerCase();
    const summary = (b.summary || '').toLowerCase();
    const metaphor = (b.metaphor || '').toLowerCase();
    const isbn = (b.isbn || '');
    const groupName = (b.group_name || '').toLowerCase();
    let s = 0;
    if (title === q) s += 1000;
    else if (title.startsWith(q)) s += 800;
    else if (title.includes(q)) s += 600;
    if (subtitle.includes(q)) s += 400;
    if (keywords.includes(q)) s += 300;
    if (groupName.includes(q)) s += 250;
    if (summary.includes(q)) s += 200;
    if (metaphor.includes(q)) s += 150;
    if (isbn === q) s += 100;
    else if (isbn.includes(q)) s += 50;
    return s;
}}

function lastReadAt(id) {{
    try {{
        const v = parseInt(localStorage.getItem('aisb_reader_lastread_' + id) || '0', 10);
        return isFinite(v) ? v : 0;
    }} catch (e) {{ return 0; }}
}}

function sortItems(parent) {{
    const items = Array.from(parent.children);
    const q = currentSearch.toLowerCase().trim();
    const effSort = (currentSort === 'default' && q) ? 'relevance' : currentSort;
    const cmp = (a, b) => {{
        const ba = BOOKS[a.dataset.id];
        const bb = BOOKS[b.dataset.id];
        switch (effSort) {{
            case 'resume': {{
                // 진도 있는 책 먼저, 그 안에서 최근 읽은 순. 진도 0인 책은 default 순서
                const pa = readProgress(a.dataset.id);
                const pb = readProgress(b.dataset.id);
                if ((pa > 0) !== (pb > 0)) return pa > 0 ? -1 : 1;
                if (pa > 0 && pb > 0) {{
                    const ta = lastReadAt(a.dataset.id);
                    const tb = lastReadAt(b.dataset.id);
                    if (ta !== tb) return tb - ta;
                }}
                const ai = originalOrder.indexOf(a.dataset.id);
                const bi = originalOrder.indexOf(b.dataset.id);
                return ai - bi;
            }}
            case 'relevance': {{
                const sa = relevanceScore(ba, q);
                const sb = relevanceScore(bb, q);
                if (sa !== sb) return sb - sa;
                const ai = originalOrder.indexOf(a.dataset.id);
                const bi = originalOrder.indexOf(b.dataset.id);
                return ai - bi;
            }}
            case 'title-asc':    return (ba.title || '').localeCompare(bb.title || '', 'ko');
            case 'title-desc':   return (bb.title || '').localeCompare(ba.title || '', 'ko');
            case 'subtitle-asc': return (ba.subtitle || '').localeCompare(bb.subtitle || '', 'ko');
            case 'pubdate-asc':  return (ba.publish_date || '').localeCompare(bb.publish_date || '');
            case 'pubdate-desc': return (bb.publish_date || '').localeCompare(ba.publish_date || '');
            case 'price-asc':    return (ba.price || 0) - (bb.price || 0);
            case 'price-desc':   return (bb.price || 0) - (ba.price || 0);
            default: {{
                const ai = originalOrder.indexOf(a.dataset.id);
                const bi = originalOrder.indexOf(b.dataset.id);
                return ai - bi;
            }}
        }}
    }};
    items.sort(cmp);
    items.forEach(it => parent.appendChild(it));
}}

function applySort() {{
    sortItems(grid);
    sortItems(tbody);
}}

sortSelect.addEventListener('change', (e) => {{
    currentSort = e.target.value;
    applySort();
}});

$$('.view-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
        const v = btn.dataset.view;
        document.body.dataset.view = v;
        $$('.view-btn').forEach(b => b.classList.toggle('active', b.dataset.view === v));
    }});
}});

$$('.scope-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
        currentScope = btn.dataset.scope;
        $$('.scope-btn').forEach(b => b.classList.toggle('active', b.dataset.scope === currentScope));
        const placeholders = {{
            all: '제목, 부제, 키워드, ISBN으로 검색',
            title: '제목에서 검색 — 예: 믿음, 분노, 기도',
            subtitle: '부제에서 검색',
            keywords: '키워드에서 검색 — 예: 회개, 안식',
            summary: '요약에서 검색',
            isbn: 'ISBN에서 검색 — 예: 9791124569'
        }};
        searchInput.placeholder = placeholders[currentScope] || placeholders.all;
        if (currentSearch) {{
            applyFilter();
            applySort();
        }} else if (searchInput.value) {{
            runSearch();
        }}
    }});
}});

$$('#seriesTabs .tab').forEach(t => {{
    t.addEventListener('click', () => {{
        $$('#seriesTabs .tab').forEach(b => b.classList.remove('active'));
        t.classList.add('active');
        currentSeries = t.dataset.filter;
        currentGroup = 'all';
        $$('#groupTabs .tab').forEach((b,i) => b.classList.toggle('active', i===0));
        applyFilter(true);
    }});
}});

$$('#groupTabs .tab').forEach(t => {{
    t.addEventListener('click', () => {{
        $$('#groupTabs .tab').forEach(b => b.classList.remove('active'));
        t.classList.add('active');
        currentGroup = t.dataset.group;
        applyFilter(true);
    }});
}});

function openBook(id) {{
    const b = BOOKS[id];
    if (!b) return;
    const status = getPubStatus(b.publish_date);
    $('mCover').src = `covers/${{id}}.jpg`;
    $('mCover').alt = b.title;
    let metaParts = [];
    if (b.season === 1 && b.type === 'main') metaParts = ['시즌 1', `EP ${{b.seq}}`];
    else if (b.season === 2 && b.type === 'main') metaParts = ['시즌 2', b.group, `EP ${{b.group_seq}}`];
    else if (b.type === 'omnibus' && b.season === 1) metaParts = ['시즌 1', '종합책'];
    else if (b.type === 'omnibus' && b.season === 2) metaParts = ['시즌 2', `${{b.group}} 종합책`];
    $('mMeta').textContent = metaParts.join(' · ');
    if (b.group_name) $('mMeta').textContent += ` · ${{b.group_name}}`;
    $('mTitle').textContent = b.title;
    $('mSubtitle').textContent = b.subtitle || '';
    $('mSummary').textContent = b.summary || '';
    const metaphor = b.metaphor || '';
    $('mMetaphor').style.display = metaphor ? 'block' : 'none';
    $('mMetaphor').textContent = metaphor;
    const kw = (b.keywords || '').split(',').map(s => s.trim()).filter(Boolean);
    $('mKeywords').innerHTML = kw.map(k => `<span class="keyword-chip">${{k}}</span>`).join('');
    $('mPrice').textContent = b.price ? `${{b.price.toLocaleString()}}원` : '';
    $('mIsbn').textContent = b.isbn || '';
    $('mPubdate').textContent = (b.publish_date || '').replace(/-/g, '.');
    $('mFormat').textContent = b.format || '';
    const badges = [];
    badges.push(`<span class="modal-badge">${{(b.publish_date||'').replace(/-/g,'.')}}</span>`);
    if (b.type === 'main' && b.season === 2) badges.push(`<span class="modal-badge outline">${{b.group}} · EP ${{b.group_seq}}</span>`);
    else if (b.type === 'omnibus') badges.push(`<span class="modal-badge outline">종합책</span>`);
    if (!status.isPublished) badges.push(`<span class="modal-badge" style="background:#ddd6c8; color:#5d4f3a;">${{status.label}} 발행 예정</span>`);
    $('mBadges').innerHTML = badges.join('');

    const buyBtn = document.querySelector('#bookModal .btn-primary');
    const noteEl = $('mPurchaseNote');
    if (!PURCHASE_ENABLED) {{
        buyBtn.textContent = PURCHASE_SHORT;
        buyBtn.disabled = true;
        buyBtn.style.background = '#ddd6c8';
        buyBtn.style.color = '#8a7f6c';
        buyBtn.style.cursor = 'not-allowed';
        buyBtn.title = PURCHASE_NOTE;
        buyBtn.onclick = null;
        noteEl.textContent = PURCHASE_NOTE;
        noteEl.style.display = 'block';
    }} else if (status.isPublished) {{
        buyBtn.textContent = '구매하기';
        buyBtn.disabled = false;
        buyBtn.style.background = '';
        buyBtn.style.color = '';
        buyBtn.style.cursor = 'pointer';
        buyBtn.title = '';
        buyBtn.onclick = openBuy;
        noteEl.style.display = 'none';
        // 사용자가 이미 보유한 책이면 "이미 보유 (서가)" 로 텍스트만 변경 + 클릭 시 reader 직행
        getUserShelf().then(shelf => {{
            if (!shelf || shelf.size === 0) return;
            // 모달 다른 책으로 바뀐 사이라면 무시
            if ($('bookModal').dataset.id !== id) return;
            if (shelf.has(id)) {{
                buyBtn.textContent = '이미 보유 — 바로 읽기';
                buyBtn.style.background = '#0a192f';
                buyBtn.style.color = 'white';
                buyBtn.title = '서가에 있는 책';
                buyBtn.onclick = () => {{ location.href = `/reader?id=${{encodeURIComponent(id)}}`; }};
            }}
        }}).catch(() => {{}});
    }} else {{
        const pubFmt = (b.publish_date||'').replace(/-/g, '.');
        buyBtn.textContent = `${{pubFmt}} 발행 예정`;
        buyBtn.disabled = true;
        buyBtn.style.background = '#ddd6c8';
        buyBtn.style.color = '#8a7f6c';
        buyBtn.style.cursor = 'not-allowed';
        buyBtn.title = '';
        buyBtn.onclick = null;
        noteEl.style.display = 'none';
    }}

    $('mPreview').href = `preview/${{id}}.html`;
    const mRead = $('mRead');
    if (FREE_BETA && status.isPublished) {{
        mRead.href = `/reader?id=${{id}}`;
        const pct = readProgress(id);
        if (pct > 0) {{
            mRead.innerHTML = `이어보기 <span class="resume-pct">${{Math.max(1, Math.round(pct*100))}}%</span>`;
        }} else {{
            mRead.textContent = '본문 보기 (무료)';
        }}
        mRead.style.display = '';
    }} else {{
        mRead.style.display = 'none';
    }}
    const yt = $('mYoutube');
    if (b.youtube_id) {{
        yt.href = `https://youtu.be/${{b.youtube_id}}`;
        yt.textContent = '유튜브 영상 ▶';
        yt.style.display = '';
    }} else if (b.playlist_id) {{
        yt.href = `https://www.youtube.com/playlist?list=${{b.playlist_id}}`;
        yt.textContent = '재생목록 ▶';
        yt.style.display = '';
    }} else {{
        yt.style.display = 'none';
    }}
    const dl = $('mDownload');
    dl.href = `epubs/${{id}}.epub`;
    dl.style.display = (window.isAuthorMode && window.isAuthorMode()) ? '' : 'none';

    const cartBtn = $('mCart');
    if (status.isPublished) {{
        cartBtn.disabled = false;
        cartBtn.style.cursor = 'pointer';
        syncCartBtn(id);
        cartBtn.onclick = () => {{
            if (window.cartHas && window.cartHas(id)) window.cartRemove(id);
            else if (window.cartAdd) window.cartAdd(id);
        }};
    }} else {{
        cartBtn.textContent = '발행 후 담기';
        cartBtn.classList.remove('in-cart');
        cartBtn.disabled = true;
        cartBtn.style.cursor = 'not-allowed';
        cartBtn.onclick = null;
    }}

    // 공유 버튼
    const shareBtn = $('mShare');
    if (shareBtn) {{
        shareBtn.onclick = () => shareBook(id, b);
    }}

    $('bookModal').classList.add('active');
    $('bookModal').dataset.id = id;
    document.body.style.overflow = 'hidden';
}}

// 본문 뷰어 진도 읽기 (reader.js 와 같은 키 규칙)
function readProgress(id) {{
    try {{
        const cfi = localStorage.getItem('aisb_reader_cfi_' + id);
        if (!cfi) return 0;
        const pct = parseFloat(localStorage.getItem('aisb_reader_pct_' + id) || '0');
        // cfi 는 있는데 pct 가 0이면 첫 페이지에서 그쳤거나 generate 전 종료. 1% 로 표시.
        return pct > 0 ? pct : 0.01;
    }} catch (e) {{
        return 0;
    }}
}}

// 모든 카드·row 의 진도 게이지 갱신
function applyReadProgress() {{
    document.querySelectorAll('[data-progress-for]').forEach(el => {{
        const id = el.dataset.progressFor;
        const pct = readProgress(id);
        if (pct > 0) {{
            const pctText = Math.max(1, Math.round(pct * 100)) + '%';
            const fill = el.querySelector('.card-progress-fill');
            const text = el.querySelector('.card-progress-text');
            if (fill) fill.style.width = pctText;
            if (text) text.textContent = '이어보기 ' + pctText;
            // row 는 자체 텍스트만
            if (el.classList.contains('row-progress')) {{
                el.textContent = '이어보기 ' + pctText;
            }}
            el.hidden = false;
        }} else {{
            el.hidden = true;
        }}
    }});
}}

function syncCartBtn(id) {{
    const cartBtn = $('mCart');
    if (!cartBtn) return;
    if (window.cartHas && window.cartHas(id)) {{
        cartBtn.textContent = '✓ 담김 (제거)';
        cartBtn.classList.add('in-cart');
    }} else {{
        cartBtn.textContent = '장바구니 담기';
        cartBtn.classList.remove('in-cart');
    }}
}}

window.addEventListener('cartChanged', () => {{
    const bm = $('bookModal');
    if (bm && bm.classList.contains('active') && bm.dataset.id) {{
        // 발행된 권만 담기 토글 가능 — 발행 전이면 라벨 변경 안 함
        const cartBtn = $('mCart');
        if (cartBtn && !cartBtn.disabled) syncCartBtn(bm.dataset.id);
    }}
}});

function closeBook() {{
    $('bookModal').classList.remove('active');
    document.body.style.overflow = '';
}}

async function shareBook(id, b) {{
    const url = `${{location.origin}}/preview/${{id}}.html`;
    const title = `${{b.title}} — AI 시대 영성`;
    const text = (b.summary || b.subtitle || 'AI 시대 영성 책방').slice(0, 140);

    // 모바일·지원 브라우저: Web Share API (네이티브 공유 시트)
    if (navigator.share) {{
        try {{
            await navigator.share({{ title, text, url }});
            return;
        }} catch (e) {{ /* 사용자 취소 — 무시 */ }}
    }}

    // fallback: 링크 복사
    try {{
        await navigator.clipboard.writeText(url);
        showShareToast('링크가 복사되었습니다');
    }} catch (e) {{
        // clipboard API 도 안 되면 prompt
        prompt('아래 주소를 복사해서 공유해 주세요:', url);
    }}
}}

function showShareToast(msg) {{
    let toast = document.getElementById('shareToast');
    if (!toast) {{
        toast = document.createElement('div');
        toast.id = 'shareToast';
        toast.className = 'share-toast';
        document.body.appendChild(toast);
    }}
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(showShareToast._t);
    showShareToast._t = setTimeout(() => toast.classList.remove('show'), 2200);
}}

function openBuy() {{
    const id = $('bookModal').dataset.id;
    const b = BOOKS[id];
    if (!b) return;
    if (b) $('bTitle').textContent = `${{b.title}} — ${{b.price.toLocaleString()}}원`;
    // PURCHASE_ENABLED + TOSS 키 + Supabase 모두 있으면 결제수단 선택 모달.
    // 아니면 송금 안내 모달 (legacy) 표시.
    if (PURCHASE_ENABLED && TOSS_CLIENT_KEY && SUPABASE_URL && SUPABASE_ANON_KEY) {{
        showPaymentMethodPicker(b);
    }} else {{
        $('buyModal').classList.add('active');
    }}
}}

function showPaymentMethodPicker(b) {{
    let picker = document.getElementById('paymentMethodPicker');
    if (!picker) {{
        picker = document.createElement('div');
        picker.id = 'paymentMethodPicker';
        picker.className = 'pmp-back';
        document.body.appendChild(picker);
    }}
    picker.innerHTML = `
        <div class="pmp-modal" role="dialog" aria-modal="true">
            <button class="pmp-close" type="button" aria-label="닫기">×</button>
            <p class="pmp-eyebrow">결제 수단</p>
            <h3 class="pmp-title">${{b.title.replace(/</g,'&lt;')}}</h3>
            <p class="pmp-price">${{b.price.toLocaleString()}}원</p>
            <div class="pmp-grid">
                <button class="pmp-btn" data-method="CARD">
                    <span class="pmp-label">💳 신용·체크카드</span>
                </button>
                <button class="pmp-btn" data-method="EASY_PAY">
                    <span class="pmp-label">📱 간편결제</span>
                    <span class="pmp-desc">카카오페이 · 네이버페이 · 토스페이 등</span>
                </button>
                <button class="pmp-btn" data-method="TRANSFER">
                    <span class="pmp-label">🏦 계좌이체</span>
                </button>
            </div>
        </div>
    `;
    picker.style.display = 'flex';
    const close = () => {{ picker.style.display = 'none'; }};
    picker.querySelector('.pmp-close').addEventListener('click', close);
    picker.addEventListener('click', (e) => {{ if (e.target === picker) close(); }});
    picker.querySelectorAll('.pmp-btn').forEach(btn => {{
        btn.addEventListener('click', async () => {{
            const method = btn.dataset.method;
            // 모든 버튼 비활성 + 클릭한 버튼에 spinner
            picker.querySelectorAll('.pmp-btn').forEach(b => b.disabled = true);
            picker.querySelector('.pmp-close').disabled = true;
            const label = btn.querySelector('.pmp-label');
            const origLabel = label.textContent;
            label.innerHTML = `<span class="pmp-spin"></span> 결제 페이지로 이동 중…`;
            try {{
                await startTossPayment(b, method);
            }} finally {{
                // 결제 호출 결과와 무관하게 picker 닫음 (토스 페이지로 redirect 됐을 수도)
                close();
            }}
        }});
    }});
    document.addEventListener('keydown', function esc(e) {{
        if (e.key === 'Escape') {{ close(); document.removeEventListener('keydown', esc); }}
    }});
}}

let _tossPromise = null;
function loadTossSdk() {{
    if (_tossPromise) return _tossPromise;
    _tossPromise = new Promise((resolve, reject) => {{
        if (window.TossPayments) return resolve(window.TossPayments);
        const s = document.createElement('script');
        s.src = 'https://js.tosspayments.com/v2/standard';
        s.onload = () => resolve(window.TossPayments);
        s.onerror = () => reject(new Error('토스 SDK 로드 실패'));
        document.head.appendChild(s);
    }});
    return _tossPromise;
}}

async function getSupabaseSession() {{
    if (!window.supabase || !SUPABASE_URL || !SUPABASE_ANON_KEY) return null;
    if (!window._aisbSb) {{
        window._aisbSb = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {{
            auth: {{ persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }},
        }});
    }}
    const {{ data: {{ session }} }} = await window._aisbSb.auth.getSession();
    return session;
}}

// 사용자 서가 캐시 (book_id Set). PURCHASE_ENABLED + 로그인 시에만 의미 있음.
let _shelfCache = null;
let _shelfCacheUserId = null;
async function getUserShelf() {{
    const session = await getSupabaseSession();
    if (!session || !session.user) {{ _shelfCache = null; _shelfCacheUserId = null; return null; }}
    if (_shelfCache && _shelfCacheUserId === session.user.id) return _shelfCache;
    try {{
        const resp = await window._aisbSb.from('bookshelf').select('book_id');
        if (resp.error) return null;
        _shelfCacheUserId = session.user.id;
        _shelfCache = new Set((resp.data || []).map(r => r.book_id));
        return _shelfCache;
    }} catch (e) {{ return null; }}
}}
function invalidateShelfCache() {{ _shelfCache = null; _shelfCacheUserId = null; }}
window.addEventListener('aisbAuthChanged', () => {{
    invalidateShelfCache();
    applyOwnedBadges();
}});

async function applyOwnedBadges() {{
    const shelf = await getUserShelf();
    document.querySelectorAll('[data-owned-for]').forEach(el => {{
        const id = el.dataset.ownedFor;
        el.hidden = !(shelf && shelf.has(id));
    }});
    applyGroupOwnedCounts(shelf);
}}

function applyRecentBooks() {{
    const items = [];
    Object.values(BOOKS).forEach(b => {{
        const lastread = parseInt(localStorage.getItem('aisb_reader_lastread_' + b.id) || '0', 10);
        if (lastread > 0) {{
            const pct = readProgress(b.id);
            items.push({{ b, lastread, pct }});
        }}
    }});
    items.sort((x, y) => y.lastread - x.lastread);
    const top = items.slice(0, 5);
    const section = document.getElementById('recentBooks');
    const list = document.getElementById('recentBooksList');
    if (!section || !list) return;
    if (top.length === 0) {{
        section.hidden = true;
        list.innerHTML = '';
        return;
    }}
    section.hidden = false;
    list.innerHTML = top.map(({{ b, pct }}) => {{
        const pctText = Math.max(1, Math.round(pct * 100)) + '%';
        const title = (b.title || '').replace(/[<>&]/g, c => ({{'<':'&lt;','>':'&gt;','&':'&amp;'}}[c]));
        return `
            <a href="/reader?id=${{b.id}}" class="recent-card" title="${{title}} 이어보기">
                <div class="recent-cover" style="background-image:url('covers/${{b.id}}.jpg')"></div>
                <div class="recent-body">
                    <div class="recent-title">${{title}}</div>
                    <div class="recent-progress">
                        <div class="recent-progress-bar"><div class="recent-progress-fill" style="width:${{pctText}}"></div></div>
                        <span class="recent-pct">${{pctText}}</span>
                    </div>
                </div>
            </a>
        `;
    }}).join('');
}}

function applyGroupOwnedCounts(shelf) {{
    document.querySelectorAll('#groupTabs .tab[data-group]').forEach(tab => {{
        const g = tab.dataset.group;
        if (!g || g === 'all') return;
        const groupBooks = Object.values(BOOKS).filter(b => b.group === g && b.type === 'main');
        const total = groupBooks.length;
        const ownedCount = (shelf && shelf.size) ? groupBooks.filter(b => shelf.has(b.id)).length : 0;
        let chip = tab.querySelector('.tab-owned');
        if (ownedCount > 0) {{
            if (!chip) {{
                chip = document.createElement('span');
                chip.className = 'tab-owned';
                tab.appendChild(chip);
            }}
            chip.textContent = `${{ownedCount}}/${{total}}`;
        }} else if (chip) {{
            chip.remove();
        }}
    }});
}}

async function startTossPayment(b, method) {{
    method = method || 'CARD';
    // 1. 로그인 확인
    let session;
    try {{ session = await getSupabaseSession(); }} catch (e) {{ session = null; }}
    if (!session || !session.user) {{
        alert('결제 후 책을 서가에 추가하기 위해 먼저 로그인이 필요합니다.\\n로그인 모달을 엽니다.');
        if (window.aisbAuth && window.aisbAuth.openLogin) window.aisbAuth.openLogin();
        return;
    }}

    // 2. 토스 SDK 로드
    let TossPayments;
    try {{ TossPayments = await loadTossSdk(); }}
    catch (e) {{ alert('결제 시스템을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.'); return; }}

    // 3. 결제 호출
    const orderId = `order_${{b.id}}_${{Date.now()}}`;
    const customerKey = session.user.id;
    const tp = TossPayments(TOSS_CLIENT_KEY);
    const payment = tp.payment({{ customerKey }});

    try {{
        await payment.requestPayment({{
            method,
            amount: {{ currency: 'KRW', value: Number(b.price) || 0 }},
            orderId,
            orderName: b.title,
            successUrl: `${{location.origin}}/payments/success.html?bookId=${{encodeURIComponent(b.id)}}`,
            failUrl: `${{location.origin}}/payments/fail.html`,
            customerEmail: session.user.email || '',
        }});
    }} catch (e) {{
        // 사용자가 토스 모달을 닫으면 reject 됨 — 무시
        if (e && e.code !== 'USER_CANCEL') {{
            alert('결제 호출 오류: ' + (e.message || e));
        }}
    }}
}}

function closeBuy() {{
    $('buyModal').classList.remove('active');
}}

document.addEventListener('keydown', (e) => {{
    if (e.key === 'Escape') {{
        if ($('buyModal').classList.contains('active')) closeBuy();
        else if ($('bookModal').classList.contains('active')) closeBook();
    }}
}});

applyPublishStatus();
applyReadProgress();
applyOwnedBadges();
applyRecentBooks();
window.addEventListener('storage', (e) => {{
    if (!e.key) return;
    if (e.key.startsWith('aisb_reader_')) {{
        applyReadProgress();
        applyRecentBooks();
    }}
}});
document.addEventListener('visibilitychange', () => {{
    if (!document.hidden) {{
        applyReadProgress();
        applyOwnedBadges();
        applyRecentBooks();
    }}
}});

// 책 카드의 시즌/그룹에서 currentSeries·currentGroup 을 결정
function resolveSeriesGroupForBook(bookId) {{
    const card = document.querySelector(`[data-id="${{bookId}}"]`);
    if (!card) return null;
    const season = card.dataset.season;
    const type = card.dataset.type;
    const group = card.dataset.group || 'all';
    let series = 'all';
    if (type === 'omnibus') series = 'omnibus';
    else if (season === '1') series = 's1-main';
    else if (season === '2') series = 's2-main';
    return {{ series, group }};
}}

function focusBookCard(bookId) {{
    // 카드가 현재 필터 결과에 안 보이면 그 책의 시즌/그룹으로 필터 자동 전환
    const target = resolveSeriesGroupForBook(bookId);
    if (!target) return;
    const needSeriesChange = currentSeries !== target.series;
    const needGroupChange = target.series === 's2-main' && currentGroup !== target.group;
    if (needSeriesChange || needGroupChange) {{
        currentSeries = target.series;
        currentGroup = target.series === 's2-main' ? target.group : 'all';
        // 탭 active 상태 동기화
        document.querySelectorAll('.tabs .tab').forEach(t => {{
            t.classList.toggle('active', t.dataset.filter === currentSeries);
        }});
        const subTabs = document.querySelectorAll('.sub-tabs .tab');
        subTabs.forEach(t => {{
            t.classList.toggle('active', t.dataset.group === currentGroup);
        }});
        applyFilter();
    }}
    // 다음 frame 에 스크롤 (필터 토글 후 layout 안정화 대기)
    requestAnimationFrame(() => {{
        const card = document.querySelector(`[data-id="${{bookId}}"]`);
        if (!card) return;
        card.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        card.classList.add('focus-pulse');
        setTimeout(() => card.classList.remove('focus-pulse'), 2400);
    }});
}}

const params = new URLSearchParams(location.search);
const idParam = params.get('id');
const focusParam = params.get('focus');
if (idParam && BOOKS[idParam]) {{
    const card = document.querySelector(`[data-id="${{idParam}}"]`);
    if (card) card.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    setTimeout(() => openBook(idParam), 200);
}} else if (focusParam && BOOKS[focusParam]) {{
    focusBookCard(focusParam);
}}
</script>

</body>
</html>
'''


if __name__ == '__main__':
    build()
