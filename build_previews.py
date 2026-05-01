# -*- coding: utf-8 -*-
"""
publisher/preview/{id}.html 빌더 — 121권 epub에서 목차 + 첫 챕터 추출.

생성물:
- publisher/preview/{id}.html (정적 페이지 121개)
- 사이트 디자인 통일 (네이비 + 골드)
- 헤더(표지·메타) + 목차 + 첫 챕터 본문 + 구매 안내

소스 epub 폴더:
- ~/Downloads/_100권_확장본_검수 (시즌2 본권)
- ~/Downloads/전자책 (시즌1 본권)
- tmp/ (종합책)
"""
# PATCHED:utf8-stdout-v1
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding='utf-8')
    _sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass


import json
import os
import zipfile
from pathlib import Path

from bs4 import BeautifulSoup


SEARCH_DIRS = [
    Path(os.path.expanduser('~/Downloads/_100권_확장본_검수')),
    Path(os.path.expanduser('~/Downloads/전자책')),
    Path('tmp'),
]

SKIP_TOC_KEYWORDS = ['cover.xhtml', 'copyright.xhtml', 'toc.xhtml', 'nav.xhtml', 'titlepage', 'title.xhtml']
NAV_CANDIDATES = ['OEBPS/nav.xhtml', 'OPS/nav.xhtml', 'nav.xhtml', 'OEBPS/toc.xhtml', 'OPS/toc.xhtml']
CHAPTER_CANDIDATES = [
    'OEBPS/ch01.xhtml', 'OPS/ch01.xhtml', 'ch01.xhtml',
    'OEBPS/chapter01.xhtml', 'OPS/chapter01.xhtml',
    'OEBPS/chapter1.xhtml', 'OEBPS/c01.xhtml',
    'OEBPS/preface.xhtml', 'OEBPS/intro.xhtml',
    'OEBPS/Section0001.xhtml',
]


def find_epub_path(filename):
    if not filename:
        return None
    for d in SEARCH_DIRS:
        p = d / filename
        if p.exists():
            return p
    return None


def first_match(names, candidates):
    for c in candidates:
        if c in names:
            return c
    return None


def find_first_body_chapter(z, names):
    """OPF spine을 분석해 cover/copyright/toc 이후의 첫 본문 챕터 찾기."""
    container = None
    if 'META-INF/container.xml' in names:
        container = z.read('META-INF/container.xml').decode('utf-8')
    if not container:
        return None
    soup = BeautifulSoup(container, 'xml')
    rootfile = soup.find('rootfile')
    if not rootfile:
        return None
    opf_path = rootfile.get('full-path')
    if opf_path not in names:
        return None
    opf = BeautifulSoup(z.read(opf_path).decode('utf-8'), 'xml')
    manifest = {item.get('id'): item.get('href') for item in opf.find_all('item')}
    base = os.path.dirname(opf_path)

    spine_items = opf.find('spine').find_all('itemref') if opf.find('spine') else []
    for item in spine_items:
        idref = item.get('idref')
        href = manifest.get(idref)
        if not href:
            continue
        full = (base + '/' + href).lstrip('/') if base else href
        low = href.lower()
        if any(k in low for k in ['cover', 'copyright', 'toc', 'nav', 'titlepage', 'title.x']):
            continue
        if full in names:
            return full
    return None


def extract_preview(epub_path):
    with zipfile.ZipFile(epub_path) as z:
        names = z.namelist()

        nav_path = first_match(names, NAV_CANDIDATES)
        nav_html = z.read(nav_path).decode('utf-8') if nav_path else ''

        ch_path = first_match(names, CHAPTER_CANDIDATES)
        if not ch_path:
            ch_path = find_first_body_chapter(z, names)

        if not ch_path:
            return None, None
        ch_html = z.read(ch_path).decode('utf-8')

    toc_items = []
    if nav_html:
        soup = BeautifulSoup(nav_html, 'html.parser')
        nav_el = soup.find(attrs={'epub:type': 'toc'}) or soup.find('nav', id='toc') or soup.find('nav') or soup
        for li in nav_el.find_all('li'):
            a = li.find('a')
            if not a:
                continue
            href = a.get('href', '')
            title = a.get_text(strip=True)
            if any(k in href.lower() for k in SKIP_TOC_KEYWORDS):
                continue
            if not title:
                continue
            toc_items.append({'href': href, 'title': title})

    soup = BeautifulSoup(ch_html, 'html.parser')
    body = soup.find('body')
    if body:
        for tag in body.find_all(True):
            if tag.has_attr('style'):
                del tag['style']
            if tag.has_attr('class'):
                tag['class'] = [c for c in tag['class'] if not c.startswith('font-') and not c.startswith('size-')]
        for img in body.find_all('img'):
            img.extract()
        body_inner = body.decode_contents()
    else:
        body_inner = ''

    return toc_items, body_inner


PREVIEW_TEMPLATE = '''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} 미리보기 — AI 시대 영성</title>
    <meta name="description" content="{summary}">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Noto+Serif+KR:wght@300;400;500;600;700&family=Noto+Sans+KR:wght@300;400;500;700&display=swap" rel="stylesheet">
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
            line-height: 1.95;
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
        nav a:hover {{ color: var(--accent); }}

        .preview-head {{
            background: linear-gradient(135deg, var(--primary) 0%, #0d2440 60%, #1a3a5c 100%);
            padding: 4rem 2rem 3rem;
            color: var(--white);
        }}
        .head-inner {{
            max-width: 920px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 200px 1fr;
            gap: 3rem;
            align-items: center;
        }}
        .head-cover img {{
            width: 100%;
            box-shadow: 0 16px 36px rgba(0,0,0,0.5);
            border-radius: 4px;
        }}
        .head-info .label {{
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.75rem;
            letter-spacing: 0.4rem;
            color: var(--accent);
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }}
        .head-info h1 {{
            font-family: 'Playfair Display', serif;
            font-size: clamp(1.8rem, 4vw, 2.8rem);
            line-height: 1.3;
            margin-bottom: 0.5rem;
        }}
        .head-info .subtitle {{
            font-family: 'Noto Serif KR', serif;
            font-size: 1.1rem;
            color: rgba(255,255,255,0.7);
            font-style: italic;
            margin-bottom: 1.5rem;
        }}
        .head-divider {{
            width: 48px;
            height: 2px;
            background: var(--accent);
            margin: 1rem 0 1.4rem;
        }}
        .head-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 1.6rem;
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.85rem;
        }}
        .head-meta .item .label {{
            color: rgba(255,255,255,0.5);
            font-size: 0.7rem;
            letter-spacing: 0.1rem;
        }}
        .head-meta .item .value {{
            color: var(--white);
            font-weight: 500;
        }}
        .head-meta .item.price .value {{
            color: var(--accent);
            font-weight: 700;
            font-family: 'Playfair Display', serif;
            font-size: 1.1rem;
        }}
        .head-qr {{
            margin-top: 1.6rem;
            display: inline-flex;
            gap: 0.9rem;
            align-items: center;
            background: rgba(255,255,255,0.96);
            padding: 0.7rem 1rem 0.7rem 0.7rem;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.18);
        }}
        .head-qr img {{
            width: 76px;
            height: 76px;
            display: block;
            border-radius: 2px;
        }}
        .head-qr-text {{
            font-family: 'Noto Sans KR', sans-serif;
            line-height: 1.45;
        }}
        .head-qr-text strong {{
            display: block;
            color: var(--primary);
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.05rem;
        }}
        .head-qr-text span {{
            color: var(--text-muted);
            font-size: 0.72rem;
        }}

        .body-wrap {{
            max-width: 760px;
            margin: 0 auto;
            padding: 4rem 2rem 3rem;
        }}
        .section-label {{
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.7rem;
            letter-spacing: 0.4rem;
            color: var(--accent);
            text-transform: uppercase;
            display: block;
            margin-bottom: 0.8rem;
        }}
        .section-title {{
            font-family: 'Playfair Display', serif;
            font-size: 1.7rem;
            color: var(--primary);
            border-bottom: 2px solid var(--accent);
            padding-bottom: 0.6rem;
            display: inline-block;
            margin-bottom: 2rem;
        }}

        /* 목차 */
        .toc {{
            background: var(--white);
            border-radius: 4px;
            padding: 2rem 2.4rem;
            margin-bottom: 4rem;
            box-shadow: 0 4px 16px rgba(10,25,47,0.06);
        }}
        .toc ol {{
            list-style: none;
            counter-reset: chapter;
        }}
        .toc li {{
            counter-increment: chapter;
            padding: 0.7rem 0;
            border-bottom: 1px solid rgba(10,25,47,0.06);
            font-family: 'Noto Serif KR', serif;
            font-size: 1rem;
            color: var(--primary);
            display: flex;
            align-items: baseline;
            gap: 1rem;
        }}
        .toc li::before {{
            content: counter(chapter, decimal-leading-zero);
            font-family: 'Playfair Display', serif;
            color: var(--accent);
            font-weight: 700;
            font-size: 0.9rem;
            min-width: 2rem;
            letter-spacing: 0.05rem;
        }}
        .toc li:last-child {{ border-bottom: none; }}

        /* 본문 */
        .chapter {{
            background: var(--white);
            border-radius: 4px;
            padding: 3rem 2.6rem;
            box-shadow: 0 4px 16px rgba(10,25,47,0.06);
            margin-bottom: 2rem;
        }}
        .chapter h2 {{
            font-family: 'Playfair Display', serif;
            font-size: 1.6rem;
            color: var(--primary);
            margin-bottom: 0.8rem;
            line-height: 1.35;
        }}
        .chapter h3, .chapter .ch-sub {{
            font-family: 'Playfair Display', serif;
            font-size: 1.15rem;
            color: var(--primary);
            margin-top: 2rem;
            margin-bottom: 0.8rem;
            font-weight: 600;
        }}
        .chapter .ch-num {{
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.7rem;
            letter-spacing: 0.4rem;
            color: var(--accent);
            text-transform: uppercase;
            display: block;
            margin-bottom: 0.6rem;
        }}
        .chapter .ch-divider {{
            width: 40px;
            height: 2px;
            background: var(--accent);
            margin: 1.4rem 0 2rem;
        }}
        .chapter p {{
            font-size: 1rem;
            color: var(--text-main);
            line-height: 2.05;
            margin-bottom: 1.2rem;
            text-align: justify;
        }}
        .chapter .scripture {{
            background: var(--accent-soft);
            border-left: 3px solid var(--accent);
            padding: 1.2rem 1.4rem;
            margin: 1.6rem 0;
            font-style: italic;
            border-radius: 0 4px 4px 0;
        }}
        .chapter .scripture p {{
            margin-bottom: 0.4rem;
            color: var(--text-main);
        }}
        .chapter .scripture cite {{
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.82rem;
            color: var(--text-muted);
            font-style: normal;
            letter-spacing: 0.05rem;
        }}
        .chapter strong {{ color: var(--primary); font-weight: 700; }}

        .preview-end {{
            text-align: center;
            margin-top: 3rem;
            padding: 3rem 2rem;
            background: var(--white);
            border-radius: 4px;
            border: 1px dashed rgba(212,175,55,0.4);
        }}
        .preview-end p {{
            font-family: 'Noto Sans KR', sans-serif;
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-bottom: 1.6rem;
            letter-spacing: 0.1rem;
        }}
        .preview-end strong {{
            color: var(--primary);
            font-weight: 500;
        }}
        .btn-buy {{
            display: inline-block;
            background: var(--accent);
            color: var(--primary);
            padding: 1rem 2.5rem;
            border-radius: 2px;
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.95rem;
            font-weight: 700;
            letter-spacing: 0.2rem;
            text-decoration: none;
            transition: all 0.3s;
        }}
        .btn-buy:hover {{ background: #b8941f; transform: translateY(-2px); }}
        .btn-author {{
            background: var(--primary);
            color: var(--accent);
            border: 1px solid var(--accent);
        }}
        .btn-author:hover {{ background: var(--accent); color: var(--primary); }}
        .btn-youtube {{
            background: #c4302b;
            color: #fff;
            border: 1px solid #c4302b;
        }}
        .btn-youtube:hover {{ background: #a52521; border-color: #a52521; color: #fff; transform: translateY(-2px); }}

        footer {{
            background: #06111f;
            padding: 2rem 3rem;
            text-align: center;
            margin-top: 3rem;
        }}
        footer p {{
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 0.75rem;
            color: rgba(255,255,255,0.3);
            letter-spacing: 0.05rem;
        }}

        @media (max-width: 720px) {{
            header {{ padding: 1rem 1.5rem; }}
            nav a {{ display: none; }}
            .head-inner {{ grid-template-columns: 1fr; gap: 2rem; }}
            .head-cover {{ max-width: 220px; margin: 0 auto; }}
            .head-info {{ text-align: center; }}
            .head-meta {{ justify-content: center; }}
            .head-divider {{ margin: 1rem auto 1.4rem; }}
            .body-wrap {{ padding: 2.5rem 1.2rem 2rem; }}
            .toc, .chapter {{ padding: 2rem 1.5rem; }}
        }}
    </style>
    <script src="../author_mode.js" defer></script>
</head>
<body>

<header>
    <a href="../index.html" class="logo">
        AI 시대 영성
        <span>PUBLISHER</span>
    </a>
    <nav>
        <a href="../index.html">홈</a>
        <a href="../catalog.html">도서</a>
        <a href="../catalog.html?id={book_id}">이 책 카드</a>
    </nav>
</header>

<section class="preview-head">
    <div class="head-inner">
        <div class="head-cover">
            <img src="../covers/{book_id}.jpg" alt="{title} 표지">
        </div>
        <div class="head-info">
            <p class="label">미리보기 · {series_label}</p>
            <h1>{title}</h1>
            <p class="subtitle">{subtitle}</p>
            <div class="head-divider"></div>
            <div class="head-meta">
                <div class="item price"><span class="label">정가</span><span class="value">{price_fmt}</span></div>
                <div class="item"><span class="label">발행</span><span class="value">{pubdate_fmt}</span></div>
                <div class="item"><span class="label">ISBN</span><span class="value">{isbn}</span></div>
                <div class="item"><span class="label">저자</span><span class="value">{author}</span></div>
            </div>
            <div class="head-qr">
                <img src="../qr/{book_id}.png" alt="이 책 QR">
                <div class="head-qr-text">
                    <strong>이 책 바로가기</strong>
                    <span>QR로 책방에서 즉시 구매</span>
                </div>
            </div>
        </div>
    </div>
</section>

<div class="body-wrap">
    <span class="section-label">Contents</span>
    <h2 class="section-title">목차</h2>
    <div class="toc">
        <ol>
{toc_items}
        </ol>
    </div>

    <span class="section-label">First Chapter</span>
    <h2 class="section-title">제1장 미리보기</h2>
    <div class="chapter">
{body_html}
    </div>

    <div class="preview-end">
        <p><strong>여기까지가 미리보기입니다.</strong><br>전체 본문은 구매 후 EPUB 파일로 받아보실 수 있습니다.</p>
        <a href="../catalog.html?id={book_id}" class="btn-buy">구매하기</a>
        {youtube_block}
        <a href="../epubs/{book_id}.epub" download class="btn-buy btn-author author-only" style="display:none;margin-left:0.6rem">EPUB 다운로드</a>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {{
    if (window.isAuthorMode && window.isAuthorMode()) {{
        document.querySelectorAll('.author-only').forEach(function(el) {{
            el.style.display = '';
        }});
    }}
}});
</script>

<footer>
    <p>&copy; 2026 AI 시대 영성 출판사. 무단 전재·복제·배포 금지.</p>
</footer>

</body>
</html>
'''


def series_label(b):
    if b['type'] == 'omnibus':
        if b['season'] == 1:
            return '시즌 1 종합책'
        return f'시즌 2 · {b["group"]} 종합책'
    if b['season'] == 1:
        return f'시즌 1 · EP {b["seq"]}'
    return f'시즌 2 · {b["group"]} · EP {b["group_seq"]}'


def build():
    with open('publisher/books_master.json', encoding='utf-8') as f:
        master = json.load(f)

    out_dir = Path('publisher/preview')
    out_dir.mkdir(parents=True, exist_ok=True)

    ok = 0
    fail = []
    no_chapter = []

    for b in master['books']:
        bid = b['id']
        epub_name = b.get('epub_filename')
        epub_path = find_epub_path(epub_name)
        if not epub_path:
            fail.append((bid, f'epub 위치 못 찾음: {epub_name}'))
            continue

        try:
            toc_items, body_inner = extract_preview(epub_path)
        except Exception as e:
            fail.append((bid, f'추출 실패: {e}'))
            continue

        if body_inner is None:
            no_chapter.append((bid, '첫 챕터 못 찾음'))
            continue

        toc_html = '\n'.join(
            f'            <li>{item["title"]}</li>'
            for item in (toc_items or [])
        )
        if not toc_html.strip():
            toc_html = '            <li style="color:#999">목차 정보 없음</li>'

        yt_id = b.get('youtube_id')
        pl_id = b.get('playlist_id')
        if yt_id:
            youtube_block = (
                f'<a href="https://youtu.be/{yt_id}" target="_blank" rel="noopener" '
                f'class="btn-buy btn-youtube" style="margin-left:0.6rem">유튜브 영상 ▶</a>'
            )
        elif pl_id:
            youtube_block = (
                f'<a href="https://www.youtube.com/playlist?list={pl_id}" target="_blank" rel="noopener" '
                f'class="btn-buy btn-youtube" style="margin-left:0.6rem">재생목록 ▶</a>'
            )
        else:
            youtube_block = ''

        page = PREVIEW_TEMPLATE.format(
            title=b['title'].replace('"', '&quot;'),
            subtitle=b.get('subtitle') or '',
            summary=(b.get('summary') or '')[:160].replace('"', '&quot;'),
            book_id=bid,
            series_label=series_label(b),
            price_fmt=f'{b.get("price", 0):,}원',
            pubdate_fmt=(b.get('publish_date') or '').replace('-', '.'),
            isbn=b.get('isbn') or '',
            author=b.get('author') or '',
            toc_items=toc_html,
            body_html=body_inner,
            youtube_block=youtube_block,
        )
        (out_dir / f'{bid}.html').write_text(page, encoding='utf-8')
        ok += 1

    print(f'[완료] 미리보기 페이지: {ok}/{master["total_count"]}')
    if no_chapter:
        print(f'  [본문 없음] {len(no_chapter)}건:')
        for bid, msg in no_chapter[:10]:
            print(f'    {bid}: {msg}')
    if fail:
        print(f'  [실패] {len(fail)}건:')
        for bid, msg in fail[:10]:
            print(f'    {bid}: {msg}')


if __name__ == '__main__':
    build()
