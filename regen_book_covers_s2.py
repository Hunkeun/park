# -*- coding: utf-8 -*-
# PATCHED:utf8-stdout-v1
"""
시즌2 본권 100권 표지 재생성.

ebook_robot.make_cover_image() 로 author="AI, 박헌근" 적용해 다시 그림.
- {title}_{date}_cover.jpg (독립 파일) 교체
- {title}_{date}.epub, {title}_{date}_logo.epub 내부 OEBPS/images/cover.jpg 교체

source 데이터: batch_books.json (10그룹×10권 = 100권)
"""
import os, sys, json, shutil, tempfile, zipfile, re
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
import ebook_robot

BASE = Path(__file__).parent
BOOKS_DIR = Path.home() / "Downloads" / "전자책"
EXT_DIR   = Path.home() / "Downloads" / "_100권_확장본_검수"  # 책방 사이트 정본
AUTHOR = "AI, 박헌근"
PUBLISHER = "AI 시대 영성"


def title_to_prefix(title):
    return title.replace(" ", "_")


def find_epubs(title):
    """일반본(전자책/) + 확장본 검수본(_100권_확장본_검수/) 모두 찾기."""
    prefix = title_to_prefix(title)
    pat = re.compile(rf"^{re.escape(prefix)}_\d{{8}}(?:_logo)?\.epub$")
    found = [f for f in BOOKS_DIR.iterdir() if pat.match(f.name)]
    if EXT_DIR.exists():
        found += [f for f in EXT_DIR.iterdir() if pat.match(f.name)]
    return found


def find_cover_jpgs(title):
    prefix = title_to_prefix(title)
    pat = re.compile(rf"^{re.escape(prefix)}_\d{{8}}_cover\.jpg$")
    return [f for f in BOOKS_DIR.iterdir() if pat.match(f.name)]


def replace_cover_in_epub(epub_path, new_cover_path):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        with zipfile.ZipFile(epub_path) as z:
            z.extractall(tmp)
        cover_in = tmp / "OEBPS" / "images" / "cover.jpg"
        if not cover_in.parent.exists():
            return False
        shutil.copy2(new_cover_path, cover_in)

        new_epub = epub_path.with_suffix(".epub.new")
        with zipfile.ZipFile(new_epub, "w") as z:
            mimetype = tmp / "mimetype"
            if mimetype.exists():
                z.write(mimetype, "mimetype", zipfile.ZIP_STORED)
            for root, dirs, files in os.walk(tmp):
                for f in files:
                    if f == "mimetype":
                        continue
                    full = Path(root) / f
                    arc = full.relative_to(tmp).as_posix()
                    z.write(full, arc, zipfile.ZIP_DEFLATED)
        os.replace(new_epub, epub_path)
    return True


def main():
    with open(BASE / "batch_books.json", encoding="utf-8") as f:
        groups = json.load(f)

    all_books = []
    for g in groups:
        for b in g["books"]:
            all_books.append({
                "title": b["title"],
                "subtitle": b["subtitle"],
                "cover_theme": g["cover_theme"],
            })

    print(f"[정보] 시즌2 본권 100권 표지 재생성 (author={AUTHOR!r})")

    ok = 0
    skip = 0
    fail = 0
    for book in all_books:
        epubs = find_epubs(book["title"])
        jpgs = find_cover_jpgs(book["title"])
        if not epubs and not jpgs:
            skip += 1
            print(f"[건너뜀] {book['title']} (epub/jpg 없음)")
            continue
        try:
            new_path = ebook_robot.make_cover_image(
                book["title"], book["subtitle"], AUTHOR, PUBLISHER, book["cover_theme"]
            )
            for j in jpgs:
                shutil.copy2(new_path, j)
            for e in epubs:
                replace_cover_in_epub(e, new_path)
            ok += 1
            print(f"[완료] {book['title']}  (epub {len(epubs)} / jpg {len(jpgs)})")
        except Exception as ex:
            fail += 1
            print(f"[실패] {book['title']}: {ex}")

    print(f"\n===== 표지 재생성: {ok}권 완료 / {fail}권 실패 / {skip}권 미생성 =====")


if __name__ == "__main__":
    main()
