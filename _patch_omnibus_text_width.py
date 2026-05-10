# -*- coding: utf-8 -*-
# PATCHED:utf8-stdout-v1
"""종합책 11권 EPUB 안 본문 wrap div 의 inline max-width 제거.

원인: 종합책 빌더가 b{N}_front / part{N}_intro / publisher / epilogue 의 본문
      div 에 inline `max-width:32~36em;margin:0 auto` 를 박았는데, 책방 reader
      (epub.js scrolled-doc) 환경에서 좁게 wrap 되어 본권 대비 폭이 좁아 보임
      ("종합책이 세로로 길게" 인상).
해결: 본문 wrap div 의 max-width 제거. 부모 padding 안에서 100% 채움 → 본권
      ch01.xhtml 과 같은 흐름.
유지: CONTENTS·길잡이 카드형(margin 가운데 정렬 + padding/border) 은 디자인
      요소이므로 그대로 둠. 패턴이 `margin:0 auto` 가 아니므로 자동 제외.

사용:
    python _patch_omnibus_text_width.py
"""
import io
import shutil
import sys
import zipfile
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

EPUB_DIR = Path("publisher/epubs")

# 본문 wrap 패턴 — margin:0 auto 가 핵심 식별자 (카드형은 margin 0 이 아님)
BODY_PATTERNS = [
    'max-width:32em;margin:0 auto',
    'max-width:34em;margin:0 auto',
    'max-width:36em;margin:0 auto',
]


def patch_xhtml(text: str) -> tuple[str, int]:
    n = 0
    for pat in BODY_PATTERNS:
        if pat in text:
            n += text.count(pat)
            text = text.replace(pat, '')
    return text, n


def patch_one(epub_path: Path) -> int:
    if not epub_path.exists():
        print(f"  [없음] {epub_path}")
        return 0

    tmp = epub_path.with_suffix(".epub.tmp")
    total_replacements = 0

    with zipfile.ZipFile(epub_path, "r") as zin:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item)
                # mimetype 은 STORED 로 보존
                if item.filename == "mimetype":
                    info = zipfile.ZipInfo("mimetype")
                    info.compress_type = zipfile.ZIP_STORED
                    zout.writestr(info, data)
                    continue
                # xhtml 만 본문 max-width 제거
                if item.filename.endswith(".xhtml"):
                    text = data.decode("utf-8", errors="ignore")
                    new_text, n = patch_xhtml(text)
                    if n > 0:
                        total_replacements += n
                        data = new_text.encode("utf-8")
                zout.writestr(item, data)

    if total_replacements > 0:
        shutil.move(str(tmp), str(epub_path))
        print(f"  [완료] {epub_path.name}  ({total_replacements} 곳 풀림)")
    else:
        if tmp.exists():
            tmp.unlink()
        print(f"  [변경없음] {epub_path.name}")
    return total_replacements


def main():
    print("=" * 60)
    print("종합책 EPUB 본문 max-width 제거")
    print("=" * 60)
    targets = sorted(EPUB_DIR.glob("*omnibus*.epub"))
    print(f"대상: {len(targets)} 권\n")
    total = 0
    n_changed = 0
    for ep in targets:
        replaced = patch_one(ep)
        total += replaced
        if replaced > 0:
            n_changed += 1
    print(f"\n[종합] {n_changed}/{len(targets)} 권 패치, 총 {total} 곳 풀림")


if __name__ == "__main__":
    main()
