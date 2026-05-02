# -*- coding: utf-8 -*-
# PATCHED:utf8-stdout-v1
"""
121권 epub 저자 표기 정책 일괄 감사.

정책 (2026-05-02):
- 판권지 "저자"   = AI, 박헌근
- 판권지 Copyright = 박헌근 (단독)
- OPF dc:creator   = AI, 박헌근
- OPF dc:rights    = 박헌근 (단독)

source: publisher/epubs/{id}.epub (책방 사이트 정본)
"""
import sys, re, zipfile, json
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

EPUB_DIR = Path("publisher/epubs")

WANT_AUTHOR    = "AI, 박헌근"
WANT_COPYRIGHT = "박헌근"           # 단독 (콤마 없음)
BAD_COPYRIGHT  = "AI, 박헌근"       # 잘못 변환된 케이스


def scan_epub(p: Path):
    issues = []
    info = {"creator": None, "rights": None, "copyright_line": None, "author_line": None}
    with zipfile.ZipFile(p) as z:
        names = z.namelist()
        opf = next((n for n in names if n.endswith("content.opf")), None)
        cr  = next((n for n in names if n.endswith("copyright.xhtml")), None)

        if opf:
            txt = z.read(opf).decode("utf-8", errors="replace")
            m = re.search(r"<dc:creator[^>]*>([^<]*)</dc:creator>", txt)
            info["creator"] = m.group(1).strip() if m else None
            m = re.search(r"<dc:rights[^>]*>([^<]*)</dc:rights>", txt)
            info["rights"] = m.group(1).strip() if m else None
        else:
            issues.append("no content.opf")

        if cr:
            txt = z.read(cr).decode("utf-8", errors="replace")
            # 판권지 "<p><strong>저자</strong>　AI, 박헌근</p>" 패턴
            m = re.search(r"<strong>\s*저자\s*</strong>[\s　:：]*([^<\n]+?)</p>", txt)
            info["author_line"] = m.group(1).strip() if m else None
            # "Copyright © 2026 박헌근. All rights reserved."
            m = re.search(r"Copyright\s*©\s*\d{4}\s+([^\.<\n]+?)\.", txt)
            info["copyright_line"] = m.group(1).strip() if m else None
        else:
            issues.append("no copyright.xhtml")

    # 정책 검증
    if info["creator"] != WANT_AUTHOR:
        issues.append(f"creator must be 'AI, 박헌근', got {info['creator']!r}")
    if not info["rights"] or "박헌근" not in info["rights"]:
        issues.append(f"rights missing 박헌근: {info['rights']!r}")
    elif "AI," in info["rights"] or "AI " in info["rights"]:
        issues.append(f"rights must be 박헌근 단독 (no 'AI'): {info['rights']!r}")
    if info["author_line"] != WANT_AUTHOR:
        issues.append(f"판권지 저자 line must be 'AI, 박헌근', got {info['author_line']!r}")
    if info["copyright_line"]:
        if BAD_COPYRIGHT in info["copyright_line"] or "AI" in info["copyright_line"]:
            issues.append(f"copyright_line must be 박헌근 단독: {info['copyright_line']!r}")
        elif info["copyright_line"].strip() != WANT_COPYRIGHT:
            issues.append(f"copyright_line={info['copyright_line']!r} (expected '박헌근')")
    return info, issues


def main():
    epubs = sorted(EPUB_DIR.glob("*.epub"))
    print(f"[정보] 검사 대상: {len(epubs)}권")
    print()

    bad = []
    for p in epubs:
        info, issues = scan_epub(p)
        if issues:
            bad.append((p.name, info, issues))

    if not bad:
        print(f"[OK] 121권 모두 정책 통과")
        print(f"     creator='AI, 박헌근' / rights='박헌근'")
        print(f"     판권지 저자='AI, 박헌근' / Copyright='박헌근'")
        return

    print(f"[경고] {len(bad)}권에 문제 발견:")
    print()
    for name, info, issues in bad:
        print(f"  {name}")
        for k, v in info.items():
            print(f"    {k}: {v!r}")
        for issue in issues:
            print(f"    ! {issue}")
        print()


if __name__ == "__main__":
    main()
