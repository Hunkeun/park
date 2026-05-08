# -*- coding: utf-8 -*-
# PATCHED:utf8-stdout-v1
"""publisher/sitemap.xml + robots.txt 생성.

books_master.json 의 121권 + 정적 페이지를 포함한 sitemap.
검색엔진 (Google·Naver) 색인에 사용.
"""
import io
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = Path(__file__).parent
PUBLISHER = ROOT / 'publisher'
BASE = "https://ai-spirituality-books.vercel.app"

STATIC_PAGES = [
    ('', '1.0', 'weekly'),               # 홈 (가장 중요)
    ('/catalog', '0.9', 'daily'),
    ('/library', '0.4', 'monthly'),      # 사용자 페이지 — 색인 의미 약함
    ('/payments/receipts', '0.2', 'monthly'),
]


def url_block(loc, lastmod, priority, changefreq):
    return f"""    <url>
        <loc>{loc}</loc>
        <lastmod>{lastmod}</lastmod>
        <changefreq>{changefreq}</changefreq>
        <priority>{priority}</priority>
    </url>"""


def main():
    bm = json.loads((PUBLISHER / 'books_master.json').read_text(encoding='utf-8'))
    today = datetime.now().strftime('%Y-%m-%d')

    urls = []
    for path, prio, freq in STATIC_PAGES:
        urls.append(url_block(BASE + path, today, prio, freq))

    # 책별 미리보기 — 가장 많이 색인되어야 할 페이지
    for b in bm.get('books', []):
        bid = b.get('id')
        if not bid:
            continue
        # 종합책은 우선순위 약간 높게
        prio = '0.8' if b.get('type') == 'omnibus' else '0.7'
        lastmod = b.get('publish_date') or today
        urls.append(url_block(f"{BASE}/preview/{bid}", lastmod, prio, 'monthly'))

    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>
"""
    (PUBLISHER / 'sitemap.xml').write_text(sitemap, encoding='utf-8')
    print(f"[완료] sitemap.xml — URL {len(urls)}개")

    robots = f"""# AI 시대 영성 책방
User-agent: *
Allow: /
Disallow: /api/
Disallow: /payments/success.html
Disallow: /payments/fail.html

Sitemap: {BASE}/sitemap.xml
"""
    (PUBLISHER / 'robots.txt').write_text(robots, encoding='utf-8')
    print(f"[완료] robots.txt")


if __name__ == '__main__':
    main()
