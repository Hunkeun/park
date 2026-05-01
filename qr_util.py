# -*- coding: utf-8 -*-
"""
QR 코드 생성 유틸리티 — 책방 사이트(https://ai-spirituality-books.vercel.app)
링크용 QR PNG 생성. 전자책·영상 슬라이드 양쪽에서 재사용.

사용법:
    from qr_util import make_qr_png_bytes, book_url, omnibus_url, catalog_url

    png = make_qr_png_bytes(book_url('s2-001'))           # 본권 직링크
    png = make_qr_png_bytes(omnibus_url('G01'))           # 종합책 그룹
    png = make_qr_png_bytes(catalog_url())                # 카탈로그 메인
"""
# PATCHED:utf8-stdout-v1
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding='utf-8')
    _sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

import io

import qrcode
from qrcode.constants import ERROR_CORRECT_M

SITE_BASE = "https://ai-spirituality-books.vercel.app"


def catalog_url() -> str:
    return f"{SITE_BASE}/catalog"


def book_url(book_id: str) -> str:
    """본권/종합책 직링크. catalog.html?id={id} → 자동 스크롤+모달 오픈."""
    return f"{SITE_BASE}/catalog?id={book_id}"


def omnibus_url(group: str) -> str:
    """G01~G10 종합책 직링크."""
    return f"{SITE_BASE}/catalog?id=s2-omnibus-{group}"


def s1_omnibus_url() -> str:
    return f"{SITE_BASE}/catalog?id=s1-omnibus"


def make_qr_png_bytes(
    url: str,
    box_size: int = 10,
    border: int = 2,
    error_correction=ERROR_CORRECT_M,
) -> bytes:
    """URL을 QR PNG 바이트로 변환.

    box_size: 한 모듈(셀)의 픽셀 크기. 10이면 약 290~330px (URL 길이 따라)
    border: 가장자리 흰 여백 모듈 수. 인쇄/카메라 인식 위해 최소 2 권장
    error_correction: M(15% 복원) 기본. 영상 워터마크용은 H 추천
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=error_correction,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0F1E3C", back_color="#FFFFFF")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else catalog_url()
    out = sys.argv[2] if len(sys.argv) > 2 else "qr_test.png"
    png = make_qr_png_bytes(target)
    with open(out, "wb") as f:
        f.write(png)
    print(f"[완료] {target} -> {out} ({len(png)/1024:.1f} KB)")
