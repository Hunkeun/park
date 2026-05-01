# -*- coding: utf-8 -*-
"""
publisher/qr/ 폴더에 책방 페이지용 QR PNG 일괄 생성.

생성 대상:
- main.png         → 홈페이지 URL (/)
- catalog.png      → 카탈로그 URL (/catalog)
- {book_id}.png    → 각 권 카탈로그 직링크 (/catalog?id={book_id}) — 121장

각 미리보기 페이지(preview/{id}.html)에서 같은 PNG 재사용 → 모바일 QR 스캔 시
카탈로그에서 그 책 모달이 자동 오픈됨.
"""
# PATCHED:utf8-stdout-v1
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding='utf-8')
    _sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass


import json
from pathlib import Path

from qr_util import SITE_BASE, book_url, catalog_url, kakao_url, make_qr_png_bytes

QR_DIR = Path("publisher") / "qr"


def build():
    QR_DIR.mkdir(parents=True, exist_ok=True)

    pairs = [
        ("main.png", SITE_BASE + "/"),
        ("catalog.png", catalog_url()),
        ("kakao.png", kakao_url()),
    ]

    with open("publisher/books_master.json", encoding="utf-8") as f:
        master = json.load(f)
    for b in master["books"]:
        pairs.append((f'{b["id"]}.png', book_url(b["id"])))

    total_bytes = 0
    for name, url in pairs:
        png = make_qr_png_bytes(url, box_size=10, border=2)
        (QR_DIR / name).write_bytes(png)
        total_bytes += len(png)

    print(f"[완료] {len(pairs)}장 QR 생성 → {QR_DIR}/")
    print(f"  메인 3장 (사이트·카탈로그·카톡 채널) + 책 {len(pairs) - 3}장")
    print(f"  총 용량: {total_bytes / 1024:.1f} KB (평균 {total_bytes / len(pairs):.0f} bytes)")


if __name__ == "__main__":
    build()
