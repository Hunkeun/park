# -*- coding: utf-8 -*-
# PATCHED:utf8-stdout-v1
"""EPUB 본문에 박힌 마크다운 코드 펜스(```html ... ```) 제거.

원인: 빌드 시점에 AI 응답을 ```html ... ``` 로 감싼 채 그대로 본문에 박은 잔재.
대상: s1-05.epub (ch02/ch05/epilogue) + s1-omnibus.epub (b02_ch02/b02_ch05)
방식: ZIP 풀어 내부 xhtml/html 텍스트에서 펜스 두 줄(여는 ```html, 닫는 ```)만
      라인 단위로 잘라냄. 본문 텍스트와 다른 마크업은 안 건드림.

mimetype 첫 entry STORED 보존, 나머지는 원본과 동일한 압축 옵션 유지.
"""
import re
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
EPUBS_DIR = ROOT / "publisher" / "epubs"

TARGETS = ["s1-05.epub", "s1-omnibus.epub"]
TEXT_EXT = (".xhtml", ".html")

# 시작 펜스: ```html, ```python 처럼 언어 라벨이 붙은 줄.
#   언어 라벨은 영문자로 시작하는 식별자. \r?\n 옵셔널 (혹시 EOL 누락된 케이스 방지).
OPEN_FENCE = re.compile(rb"(?m)^[ \t]*```[ \t]*[a-zA-Z][a-zA-Z0-9_-]*[ \t]*\r?\n?")
# 닫는 펜스: ``` 만 단독으로 줄 시작. 닫는 ``` 뒤에 줄바꿈 없이 다른 태그가 붙는
# 케이스도 처리(예: '</p>\r\n```</div><div...').
CLOSE_FENCE = re.compile(rb"(?m)^[ \t]*```[ \t]*\r?\n?")


def patch_text(data: bytes) -> tuple[bytes, int]:
    """data 안의 펜스 두 종류를 제거. 반환: (새 data, 제거 건수)."""
    new_data, n_open = OPEN_FENCE.subn(b"", data)
    new_data, n_close = CLOSE_FENCE.subn(b"", new_data)
    return new_data, n_open + n_close


def patch_epub(src: Path) -> tuple[int, int]:
    """반환: (이 EPUB 에서 제거된 펜스 건수, 변경된 내부 파일 수)."""
    tmp = src.with_suffix(src.suffix + ".tmp")
    total_subs = 0
    changed_files = 0
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(tmp, "w") as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            new_data = data
            if info.filename.lower().endswith(TEXT_EXT):
                if b"```" in data:
                    new_data, n = patch_text(data)
                    if n:
                        total_subs += n
                        changed_files += 1
            new_info = zipfile.ZipInfo(info.filename, info.date_time)
            new_info.compress_type = info.compress_type
            new_info.external_attr = info.external_attr
            zout.writestr(new_info, new_data)
    tmp.replace(src)
    return (total_subs, changed_files)


print("=" * 70)
print(f"마크다운 펜스 제거 — 대상 {len(TARGETS)}권")
print("=" * 70)

for name in TARGETS:
    src = EPUBS_DIR / name
    if not src.exists():
        print(f"  [스킵] {name} (파일 없음)")
        continue
    subs, files = patch_epub(src)
    if subs:
        print(f"  [완료] {name}  제거 {subs}건 ({files}개 파일)")
    else:
        print(f"  [변경없음] {name}")

print()
print("끝.")
