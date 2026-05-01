# -*- coding: utf-8 -*-
"""
publisher/epubs/{book_id}.epub로 121권 epub 복사 — 저자 모드 다운로드용.

본문은 books_master.json의 epub_filename, 표지는 cover_filename 기준.

폴더 검색 순서:
- ~/Downloads/_부크크검수/         (시즌1 본권 부크크 확장본 — 본문만)
- ~/Downloads/_100권_확장본_검수/  (시즌2 본권 부크크 확장본)
- ~/Downloads/전자책/             (시즌1 종합책 + 종합책 11권)
- tmp/                            (종합책 백업 사본)

표지 교체 (시즌1 본권 한정):
  부크크 epub 안의 cover.jpg가 부크크 양식(분홍 THE BOOKK)이므로,
  복사 시 OEBPS/images/cover.jpg를 cover_filename(원본 디자인)으로 교체.
  본문은 부크크 확장본 그대로, 표지만 원래 디자인.

실행: python copy_epubs_to_publisher.py
"""
# PATCHED:utf8-stdout-v1
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding='utf-8')
    _sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass


import io
import json
import shutil
import zipfile
from pathlib import Path

OUT_DIR = Path("publisher") / "epubs"
SEARCH_DIRS = [
    Path.home() / "Downloads" / "_부크크검수",          # 시즌1 본권 부크크 확장본
    Path.home() / "Downloads" / "_100권_확장본_검수",   # 시즌2 본권 부크크 확장본
    Path.home() / "Downloads" / "전자책",              # 종합책 11권 + 옛 일반본 폴백
    Path("tmp"),                                       # 종합책 백업 사본
]


def find_epub(filename: str) -> Path | None:
    if not filename:
        return None
    for base in SEARCH_DIRS:
        p = base / filename
        if p.exists():
            return p
    return None


def copy_with_replaced_cover(src: Path, dst: Path, cover_path: Path) -> None:
    """epub 안의 OEBPS/images/cover.jpg만 새 표지로 교체하여 저장.
    나머지 파일·메타데이터는 그대로.
    """
    new_cover_bytes = cover_path.read_bytes()
    with zipfile.ZipFile(src, "r") as zin:
        with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
            # mimetype은 항상 첫 항목 + STORED (압축 X) 권장
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "OEBPS/images/cover.jpg":
                    data = new_cover_bytes
                # mimetype은 압축 안 함
                if item.filename == "mimetype":
                    zout.writestr(item, data, compress_type=zipfile.ZIP_STORED)
                else:
                    zout.writestr(item, data)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open("publisher/books_master.json", encoding="utf-8") as f:
        master = json.load(f)

    ok = 0
    cover_replaced = 0
    miss = []
    total_bytes = 0
    for b in master["books"]:
        bid = b["id"]
        fn = b.get("epub_filename")
        src = find_epub(fn)
        if not src:
            miss.append((bid, fn))
            continue
        dst = OUT_DIR / f"{bid}.epub"

        # 시즌1 본권: 부크크 양식 표지 → 원본 디자인 표지로 교체
        is_s1_main = (b.get("season") == 1 and b.get("type") == "main")
        cover_fn = b.get("cover_filename")
        cover_dir = b.get("cover_source_dir")
        if is_s1_main and cover_fn and cover_dir:
            cover_path = Path(cover_dir) / cover_fn
            if cover_path.exists():
                copy_with_replaced_cover(src, dst, cover_path)
                cover_replaced += 1
            else:
                shutil.copy2(src, dst)
        else:
            shutil.copy2(src, dst)

        ok += 1
        total_bytes += dst.stat().st_size

    print(f"[완료] {ok}/{master['total_count']}권 복사 → {OUT_DIR}/")
    print(f"  총 용량: {total_bytes / 1024 / 1024:.1f} MB (평균 {total_bytes / max(ok,1) / 1024:.0f} KB)")
    if cover_replaced:
        print(f"  표지 교체 (시즌1 본권): {cover_replaced}권 (부크크 디자인 -> 원본 디자인)")
    if miss:
        print(f"  [경고] 누락 {len(miss)}건:")
        for bid, fn in miss[:10]:
            print(f"    - {bid}: {fn}")
        if len(miss) > 10:
            print(f"    ... 외 {len(miss) - 10}건")


if __name__ == "__main__":
    main()
