# -*- coding: utf-8 -*-
"""
publisher 사이트 라우팅 정합성 정적 검증.

2026-05-08 오전 사건 재발 방지: Vercel cleanUrls(true) + Service Worker가
충돌해 페이지 이동이 깨졌던 사고. 같은 패턴이 다시 들어오지 못하게
sync 단계에서 정적 분석으로 차단한다.

검사 항목:
  1) publisher/sw.js 의 fetch 핸들러가 navigation 요청을 즉시 우회
     - `req.mode === 'navigate'` 비교 + early return
     - 이 우회가 모든 respondWith() 호출보다 앞 (= 정말 early)
  2) publisher/**/*.html 의 href / src 속성에 .html 직접 링크 금지
     (예: href="/catalog.html", href="index.html",
          <link rel="canonical" href=".../preview/x.html">)
  3) 빌더 파이썬 소스(build_catalog.py / build_previews.py / build_sitemap.py)
     안의 문자열 리터럴에 .html 직접 링크 금지
     - 절대 경로(`/foo/bar.html`) 또는 자기 도메인 절대 URL만 차단
     - 출력 파일 경로 (`Path('publisher/catalog.html')`, `f'{bid}.html'`)는 통과

종료 코드: 0 통과 / 1 실패 (sync_publisher.py 가 실패 시 중단)
"""
# PATCHED:utf8-stdout-v1
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

import re
from pathlib import Path

ROOT = Path(__file__).parent
PUBLISHER = ROOT / "publisher"
SW_PATH = PUBLISHER / "sw.js"
VERCELIGNORE = PUBLISHER / ".vercelignore"

BUILDER_FILES = [
    ROOT / "build_catalog.py",
    ROOT / "build_previews.py",
    ROOT / "build_sitemap.py",
]

OWN_DOMAIN = "ai-spirituality-books.vercel.app"

violations: list[str] = []


def vercel_ignored_names() -> set[str]:
    """publisher/.vercelignore 에 등록된 파일명(맨 앞 디렉토리 없이) 집합.
    Vercel 배포에 안 올라가는 파일은 운영 라우팅과 무관하므로 검사 제외.
    """
    if not VERCELIGNORE.exists():
        return set()
    names = set()
    for line in VERCELIGNORE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # 단순 파일명만 처리 (이 프로젝트 vercelignore 가 그 정도 형태)
        names.add(line)
    return names


def report(msg: str) -> None:
    violations.append(msg)


# ─── 1) SW navigation bypass ──────────────────────────────────────────────

def extract_fetch_handler_body(src: str) -> str | None:
    m = re.search(
        r"addEventListener\(\s*['\"]fetch['\"]\s*,\s*(?:\([^)]*\)|\w+)\s*=>\s*\{",
        src,
    )
    if not m:
        return None
    start = m.end()
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        c = src[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    if depth != 0:
        return None
    return src[start:i - 1]


def check_sw_navigation_bypass() -> None:
    if not SW_PATH.exists():
        report(f"[SW] {SW_PATH} 가 없음")
        return
    src = SW_PATH.read_text(encoding="utf-8")
    body = extract_fetch_handler_body(src)
    if body is None:
        report("[SW] publisher/sw.js: fetch 이벤트 리스너를 찾을 수 없거나 본문 괄호 짝이 맞지 않음")
        return

    nav_match = re.search(r"\.?\s*mode\s*===?\s*['\"]navigate['\"]", body)
    if not nav_match:
        report("[SW] fetch 핸들러에 navigation 우회 코드(`mode === 'navigate'`)가 없음")
        return

    # 비교 직후 200자 안에 return 키워드가 있어야 함
    tail = body[nav_match.end(): nav_match.end() + 200]
    if "return" not in tail:
        report("[SW] navigation 비교 직후 early return 이 보이지 않음")
        return

    # respondWith 보다 앞에 와야 진짜 early
    rw_match = re.search(r"respondWith\s*\(", body)
    if rw_match and nav_match.start() > rw_match.start():
        report("[SW] navigate bypass 가 첫 respondWith() 호출보다 뒤에 있음 — early return 위치가 깨짐")


# ─── 2) HTML 내부 링크 ────────────────────────────────────────────────────

# href="..." / src="..." 패턴 (큰따옴표·작은따옴표 모두)
HTML_ATTR_RE = re.compile(
    r"""(?:href|src)\s*=\s*(["'])([^"']+?)\1""",
    re.IGNORECASE,
)


def is_bad_html_link(value: str) -> bool:
    """href/src 값에 .html 이 들어 있으면 차단.

    제외:
      - 명시적 외부 도메인이지만 자기 도메인이 아닌 경우는 통과 (예: 외부 블로그 .html 링크)
      - 단순 .html 종료 또는 .html?... .html#... 모두 차단
    """
    # .html 자체가 없으면 통과
    if not re.search(r"\.html(?:[?#]|$)", value, re.IGNORECASE):
        return False
    # 외부 도메인 (자기 도메인 아닌 경우) 은 허용
    m = re.match(r"https?://([^/]+)", value, re.IGNORECASE)
    if m and m.group(1).lower() != OWN_DOMAIN:
        return False
    return True


def check_html_links() -> None:
    if not PUBLISHER.exists():
        report(f"[HTML] {PUBLISHER} 가 없음")
        return
    ignored = vercel_ignored_names()
    for path in sorted(PUBLISHER.rglob("*.html")):
        if path.name in ignored:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="replace")
        for m in HTML_ATTR_RE.finditer(text):
            value = m.group(2)
            if is_bad_html_link(value):
                line_no = text.count("\n", 0, m.start()) + 1
                rel = path.relative_to(ROOT).as_posix()
                report(f"[HTML] {rel}:{line_no}  .html 직접 링크: {value!r}")


# ─── 3) 빌더 소스 ─────────────────────────────────────────────────────────

# 출력될 가능성이 높은 절대 .html 패턴만 차단:
#   - 따옴표 안에 슬래시로 시작하는 .html       ('/foo/bar.html')
#   - 자기 도메인 절대 URL .html               ('https://ai-spirituality-books.vercel.app/.../x.html')
BAD_BUILDER_PATTERNS = [
    re.compile(r"""(["'])(/[^"'\n]*\.html(?:[?#][^"'\n]*)?)\1"""),
    re.compile(
        rf"""(["'])(https?://{re.escape(OWN_DOMAIN)}/[^"'\n]*\.html(?:[?#][^"'\n]*)?)\1""",
        re.IGNORECASE,
    ),
]


def check_builders() -> None:
    for path in BUILDER_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for pat in BAD_BUILDER_PATTERNS:
            for m in pat.finditer(text):
                value = m.group(2)
                line_no = text.count("\n", 0, m.start()) + 1
                rel = path.relative_to(ROOT).as_posix()
                report(f"[BUILDER] {rel}:{line_no}  .html 직접 링크 출력: {value!r}")


# ─── 메인 ─────────────────────────────────────────────────────────────────

def main() -> None:
    check_sw_navigation_bypass()
    check_html_links()
    check_builders()

    if violations:
        print(f"[실패] 라우팅 정합성 위반 {len(violations)}건")
        for v in violations:
            print(f"  - {v}")
        print()
        print("배경: 2026-05-08 사건. 자세한 원인은 memory/project_publisher_routing_sw.md 참고.")
        print("해결: 모든 내부 페이지 링크는 클린 URL(예: /catalog, /library, /reader?id=...).")
        sys.exit(1)

    print("[OK] 라우팅 정합성 통과 (SW navigation bypass · HTML 링크 · 빌더 출력)")


if __name__ == "__main__":
    main()
