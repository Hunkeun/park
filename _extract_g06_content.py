# -*- coding: utf-8 -*-
"""G06 권 epub에서 챕터 본문 텍스트 추출 (콘텐츠 작성용 참고자료)."""
import os
import re
import sys
import zipfile
from html import unescape

EPUB_DIR = os.path.expanduser("~/Downloads/_100권_확장본_검수")


def strip_html(html):
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.S)
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S)
    html = re.sub(r"<br\s*/?>", "\n", html)
    html = re.sub(r"</p>", "\n\n", html)
    html = re.sub(r"<[^>]+>", "", html)
    html = unescape(html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


def extract(epub_fn):
    path = os.path.join(EPUB_DIR, epub_fn)
    with zipfile.ZipFile(path) as z:
        names = sorted(n for n in z.namelist() if n.startswith("OEBPS/") and n.endswith(".xhtml"))
        for n in names:
            data = z.read(n).decode("utf-8", errors="replace")
            text = strip_html(data)
            print(f"\n========== {n} ==========")
            print(text[:5000])


if __name__ == "__main__":
    extract(sys.argv[1])
