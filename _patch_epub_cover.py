# -*- coding: utf-8 -*-
# PATCHED:utf8-stdout-v1
"""EPUB 안 OEBPS/cover.xhtml 을 단순 <img src="images/cover.jpg"> 형태로 교체.

원인 (이력):
  - 옛 빌더가 SVG <image xlink:href="../images/cover.jpg"> 형태였음.
    경로의 ../ 가 OEBPS 밖으로 나가 자원 매핑 깨짐 + epub.js 가 SVG xlink 매핑
    을 따라가지 못함 → 책방 reader 표지가 빈 페이지.
  - base64 data URI 인라인으로 우회 시도했으나 cover.xhtml 사이즈가 약 200KB
    가 되어 epub.js iframe srcdoc 처리에서 spine[0] 이 사라지는 증상 발생
    (첫 페이지가 cover 가 아니라 copyright 로 시작).

해결: 단순 <img src="images/cover.jpg"> 사용. cover.xhtml 은 OEBPS/cover.xhtml 위치
      이므로 OEBPS/images/cover.jpg 의 정확한 상대경로는 "images/cover.jpg" (../ 없음).
      reader.js 의 allowScriptedContent: true 와 함께 epub.js 가 ZIP 내부 자원을
      blob URL 로 매핑해 표지가 정상 표시됨.

이 스크립트는 EPUB ZIP 을 풀어서 cover.xhtml 만 새 내용으로 다시 패키징.
다른 파일(cover.jpg 본체 포함)은 그대로 보존. mimetype 파일은 표준대로 STORED 압축.

사용:
    python _patch_epub_cover.py            # 모든 epub 패치
    python _patch_epub_cover.py s2-001     # 특정 권만 (id 또는 파일명)
"""
import base64
import io
import shutil
import sys
import zipfile
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

EPUB_DIR = Path("publisher/epubs")
SITE_BASE = "https://ai-spirituality-books.vercel.app"

# 책방용 EPUB 의 cover.xhtml 은 사이트 절대 URL 로 표지 이미지를 참조한다.
# epub.js 의 ZIP image 자원 매핑이 환경에 따라 깨져 책 안에서 표지가 빈 페이지로
# 뜨는 문제 회피용. 부크크 종이책 PDF 는 별도 빌드라 영향 없고, 책방 reader 에서만
# 사용되는 책 본체 EPUB 의 표지 페이지에 대해 site 절대 URL 로 외부 fetch 시킨다.
COVER_HTML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ko">
<head><meta charset="UTF-8"/><title>표지</title>
<style>
  html, body {{ margin:0; padding:0; width:100%; height:100%; background:#FFFFFF; }}
  .cover-wrap {{ width:100%; height:100%; display:flex; align-items:center; justify-content:center; padding:0; box-sizing:border-box; }}
  img {{ display:block; max-width:100%; max-height:100vh; width:auto; height:auto; object-fit:contain; }}
</style>
</head>
<body>
<div class="cover-wrap">
<img src="{cover_url}" alt="표지"/>
</div>
</body>
</html>
"""

COVER_PATH_IN_ZIP = "OEBPS/cover.xhtml"
COVER_IMAGE_CANDIDATES = [
    "OEBPS/images/cover.jpg",
    "OEBPS/images/cover.jpeg",
    "OEBPS/images/cover.png",
]


def _mime_for(path: str) -> str:
    p = path.lower()
    if p.endswith(".png"):
        return "image/png"
    if p.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    return "application/octet-stream"


def _build_new_cover_xhtml(zin: zipfile.ZipFile, book_id: str) -> bytes | None:
    names = zin.namelist()
    for cand in COVER_IMAGE_CANDIDATES:
        if cand in names:
            cover_url = f"{SITE_BASE}/covers/{book_id}.jpg"
            return COVER_HTML_TEMPLATE.format(cover_url=cover_url).encode("utf-8")
    return None


def patch_one(epub_path: Path) -> bool:
    if not epub_path.exists():
        print(f"  [없음] {epub_path}")
        return False

    tmp = epub_path.with_suffix(".epub.tmp")
    patched = False
    book_id = epub_path.stem  # 예: "s1-01.epub" -> "s1-01"

    with zipfile.ZipFile(epub_path, "r") as zin:
        names = zin.namelist()
        if COVER_PATH_IN_ZIP not in names:
            print(f"  [스킵] {epub_path.name} (cover.xhtml 없음)")
            return False

        new_cover = _build_new_cover_xhtml(zin, book_id)
        if new_cover is None:
            print(f"  [스킵] {epub_path.name} (cover.jpg 없음)")
            return False

        # 이미 site 절대 URL 표지 형태면 skip
        existing = zin.read(COVER_PATH_IN_ZIP).decode("utf-8", errors="ignore")
        expected_url = f"{SITE_BASE}/covers/{book_id}.jpg"
        if expected_url in existing:
            print(f"  [이미패치] {epub_path.name}")
            return False

        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == "mimetype":
                    info = zipfile.ZipInfo("mimetype")
                    info.compress_type = zipfile.ZIP_STORED
                    zout.writestr(info, zin.read(item))
                    continue
                if item.filename == COVER_PATH_IN_ZIP:
                    new_info = zipfile.ZipInfo(COVER_PATH_IN_ZIP)
                    new_info.compress_type = zipfile.ZIP_DEFLATED
                    zout.writestr(new_info, new_cover)
                    patched = True
                    continue
                zout.writestr(item, zin.read(item))

    if patched:
        shutil.move(str(tmp), str(epub_path))
        print(f"  [완료] {epub_path.name}")
        return True
    else:
        if tmp.exists():
            tmp.unlink()
        return False


def main():
    print("=" * 60)
    print("EPUB cover.xhtml 일괄 패치")
    print("=" * 60)

    arg = sys.argv[1] if len(sys.argv) > 1 else None

    if arg:
        # 특정 권만
        candidates = [
            EPUB_DIR / f"{arg}.epub",
            EPUB_DIR / arg,
        ]
        for c in candidates:
            if c.exists():
                patch_one(c)
                return
        print(f"[에러] {arg} 에 해당하는 epub 을 찾을 수 없음")
        return

    targets = sorted(EPUB_DIR.glob("*.epub"))
    print(f"대상 EPUB: {len(targets)} 권\n")
    n = 0
    for ep in targets:
        if patch_one(ep):
            n += 1
    print(f"\n[종합] 패치된 EPUB: {n} / {len(targets)}")


if __name__ == "__main__":
    main()
