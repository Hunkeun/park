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
            <td class="cell-title"><strong>{title}</strong>{f"<br><span>{subtitle}</span>" if subtitle else ""}</td>
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
                <img src="{cover}" alt="{title}" loading="lazy">
            </div>
            <div class="card-body">
                <h3 class="card-title">{title}</h3>
                <p class="card-subtitle">{subtitle}</p>
                <div class="card-meta">
                    <span class="card-price">{price}</span>
                    <span class="card-pubdate">{pub}</span>
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

    page = HTML_TEMPLATE.format(
        cards=cards_html,
        rows=rows_html,
        books_json=books_data_json,
        total=master['total_count'],
        s1_main_count=len(s1_main),
        s2_main_count=len(s2_main),
        omni_count=len(s1_omni) + len(s2_omni),
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
            font-family: 'Playfair Display', serif;
            font-size: 1.4rem;
            color: var(--accent);
            letter-spacing: 0.1rem;
            text-decoration: none;
        }}
        .logo span {{
            color: rgba(255,255,255,0.7);
            font-size: 0.78rem;
            font-family: 'Noto Sans KR', sans-serif;
            font-weight: 300;
            letter-spacing: 0.2rem;
            display: block;
            margin-top: -0.2rem;
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
            transition: transform 0.3s, box-shadow 0.3s;
            display: flex;
            flex-direction: column;
            cursor: pointer;
        }}
        .card.hidden {{ display: none; }}
        .card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 16px 36px rgba(10,25,47,0.12);
        }}
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
            top: 1rem;
            right: 1.2rem;
            background: rgba(255,255,255,0.9);
            border: none;
            font-size: 1.4rem;
            color: var(--primary);
            cursor: pointer;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10;
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
            nav a {{ display: none; }}
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
</head>
<body data-view="table">

<header>
    <a href="index.html" class="logo">
        AI 시대 영성
        <span>PUBLISHER</span>
    </a>
    <nav>
        <a href="index.html">홈</a>
        <a href="catalog.html" class="active">도서</a>
        <a href="index.html#contact">연락처</a>
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
                <input type="text" class="search-input" id="searchInput" placeholder="검색어 입력 후 엔터 (또는 검색 버튼)" autocomplete="off">
                <button class="search-clear" id="searchClear" title="지우기">×</button>
            </div>
            <button class="search-submit" id="searchSubmit">검색 ↵</button>
        </div>
        <div class="sort-row">
            <select class="sort-select" id="sortSelect">
                <option value="default">기본 순서 (시즌·시리즈)</option>
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
        <h3>검색 결과가 없습니다</h3>
        <p>다른 키워드로 시도해보세요. 제목·부제·키워드·요약·ISBN을 검색합니다.</p>
    </div>
</div>

<!-- 권 상세 모달 -->
<div class="modal-bg" id="bookModal" onclick="if(event.target===this) closeBook()">
    <div class="modal">
        <button class="modal-close" onclick="closeBook()">×</button>
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
            <div class="modal-actions">
                <button class="btn btn-primary">구매하기</button>
                <a class="btn btn-outline" id="mPreview" target="_blank" rel="noopener">미리보기</a>
                <a class="btn btn-youtube" id="mYoutube" target="_blank" rel="noopener" style="display:none">유튜브 영상 ▶</a>
                <a class="btn btn-author author-only" id="mDownload" download style="display:none">EPUB 다운로드</a>
                <button class="btn btn-outline" onclick="closeBook()">닫기</button>
            </div>
        </div>
    </div>
</div>

<!-- 구매 안내 모달 -->
<div class="buy-modal-bg" id="buyModal" onclick="if(event.target===this) closeBuy()">
    <div class="buy-modal">
        <button class="modal-close" onclick="closeBuy()">×</button>
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

function applyFilter() {{
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
    $('searchClear').classList.toggle('active', q.length > 0);
}}

const searchInput = $('searchInput');
const searchClear = $('searchClear');
const searchSubmit = $('searchSubmit');

function runSearch() {{
    currentSearch = searchInput.value;
    applyFilter();
    applySort();
}}

searchInput.addEventListener('input', (e) => {{
    searchClear.classList.toggle('active', e.target.value.length > 0);
}});
searchInput.addEventListener('keydown', (e) => {{
    if (e.key === 'Enter') {{
        e.preventDefault();
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

function sortItems(parent) {{
    const items = Array.from(parent.children);
    const q = currentSearch.toLowerCase().trim();
    const effSort = (currentSort === 'default' && q) ? 'relevance' : currentSort;
    const cmp = (a, b) => {{
        const ba = BOOKS[a.dataset.id];
        const bb = BOOKS[b.dataset.id];
        switch (effSort) {{
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
        applyFilter();
    }});
}});

$$('#groupTabs .tab').forEach(t => {{
    t.addEventListener('click', () => {{
        $$('#groupTabs .tab').forEach(b => b.classList.remove('active'));
        t.classList.add('active');
        currentGroup = t.dataset.group;
        applyFilter();
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
    if (status.isPublished) {{
        buyBtn.textContent = '구매하기';
        buyBtn.disabled = false;
        buyBtn.style.background = '';
        buyBtn.style.color = '';
        buyBtn.style.cursor = 'pointer';
        buyBtn.onclick = openBuy;
    }} else {{
        const pubFmt = (b.publish_date||'').replace(/-/g, '.');
        buyBtn.textContent = `${{pubFmt}} 발행 예정`;
        buyBtn.disabled = true;
        buyBtn.style.background = '#ddd6c8';
        buyBtn.style.color = '#8a7f6c';
        buyBtn.style.cursor = 'not-allowed';
        buyBtn.onclick = null;
    }}

    $('mPreview').href = `preview/${{id}}.html`;
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
    $('bookModal').classList.add('active');
    $('bookModal').dataset.id = id;
    document.body.style.overflow = 'hidden';
}}

function closeBook() {{
    $('bookModal').classList.remove('active');
    document.body.style.overflow = '';
}}

function openBuy() {{
    const id = $('bookModal').dataset.id;
    const b = BOOKS[id];
    if (b) $('bTitle').textContent = `${{b.title}} — ${{b.price.toLocaleString()}}원`;
    $('buyModal').classList.add('active');
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

const params = new URLSearchParams(location.search);
const idParam = params.get('id');
if (idParam && BOOKS[idParam]) {{
    const card = document.querySelector(`.card[data-id="${{idParam}}"]`);
    if (card) card.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    setTimeout(() => openBook(idParam), 200);
}}
</script>

</body>
</html>
'''


if __name__ == '__main__':
    build()
