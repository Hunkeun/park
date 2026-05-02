# -*- coding: utf-8 -*-
# PATCHED:utf8-stdout-v1
"""
시즌1 본권 10권 표지 재생성.

ebook_robot.make_cover_image() 로 author="AI, 박헌근" 적용해 다시 그림.

source 메타: ~/Downloads/_부크크검수/{title}_{date}.epub 의 OPF
  - dc:title  → 표지 제목
  - dc:description → 표지 부제
테마 식별: 기존 ~/Downloads/전자책/커버_추출/{title}_*_표지.jpg 의 grad_top 픽셀
          색상을 COVER_THEMES.grad_top과 비교해 가장 가까운 테마 매칭.

대상 갱신:
  ~/Downloads/전자책/커버_추출/{title}_*_표지.jpg
  (책방 사이트 copy_epubs_to_publisher.py 가 sync 시 사용)

미터치:
  ~/Downloads/_부크크검수/*.epub  — 부크크 디자인 표지 정책 유지
  ~/Downloads/전자책/{title}_{date}.epub  — 책방 사이트 미사용 (참고용 보존)
"""
import os, sys, re, zipfile, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
import ebook_robot

from PIL import Image

BOOKK_DIR  = Path.home() / "Downloads" / "_부크크검수"
EXTRACT_DIR = Path.home() / "Downloads" / "전자책" / "커버_추출"
AUTHOR = "AI, 박헌근"
PUBLISHER = "AI 시대 영성"

# (title, 검수 epub 파일명, 추출 표지 파일명)
BOOKS = [
    ("AI 시대 영성 상담사를 만나다",  "AI_시대_영성_상담사를_만나다_20260412.epub",
     "AI_시대_영성_상담사를_만나다_표지.jpg"),
    ("산을 옮길만한 믿음",          "산을_옮길만한_믿음_20260412.epub",
     "산을_옮길만한_믿음_20260412_표지.jpg"),
    ("아름다운 감성을 사모하자",    "아름다운_감성을_사모하자_20260413.epub",
     "아름다운_감성을_사모하자_20260413_표지.jpg"),
    ("다수의 횡포를 직관하라",      "다수의_횡포를_직관하라_20260415.epub",
     "다수의_횡포를_직관하라_20260415_표지.jpg"),
    ("새술은 새부대에 담아야",      "새술은_새부대에_담아야_20260412.epub",
     "새술은_새부대에_담아야_20260412_표지.jpg"),
    ("카이로스와 자유의지",         "카이로스와_자유의지_20260415.epub",
     "카이로스와_자유의지_20260415_표지.jpg"),
    ("진동 에너지와 치유",          "진동_에너지와_치유_20260413.epub",
     "진동_에너지와_치유_20260413_표지.jpg"),
    ("이스라엘 어느 왕의 덤 인생",  "이스라엘_어느_왕의_덤_인생_20260415.epub",
     "이스라엘_어느_왕의_덤_인생_20260415_표지.jpg"),
    ("죽음의 역설",                 "죽음의_역설_20260413.epub",
     "죽음의_역설_20260413_표지.jpg"),
    ("이 세상과 저 세상",           "이_세상과_저_세상_20260416.epub",
     "이_세상과_저_세상_표지.jpg"),
]


def read_meta_from_epub(epub_path):
    with zipfile.ZipFile(epub_path) as z:
        opf_name = next((n for n in z.namelist() if n.endswith("content.opf")), None)
        if not opf_name:
            return None, None
        opf = z.read(opf_name).decode("utf-8", errors="replace")
        t = re.search(r"<dc:title[^>]*>([^<]+)</dc:title>", opf)
        d = re.search(r"<dc:description[^>]*>([^<]*)</dc:description>", opf, re.DOTALL)
        return (t.group(1).strip() if t else None,
                (d.group(1).strip() if d else "") or "")


def detect_theme(jpg_path):
    """기존 표지 좌상단 영역 평균 색상을 grad_top 으로 보고 가장 가까운 테마 찾기."""
    img = Image.open(jpg_path).convert("RGB")
    W, H = img.size
    # 좌상단 안전 영역 — 테두리·로고 피하고 평탄한 그라데이션 영역만
    crop = img.crop((W // 4, 30, W * 3 // 4, 90))
    px = list(crop.getdata())
    avg = tuple(sum(c[i] for c in px) // len(px) for i in range(3))

    best_name = None
    best_dist = float("inf")
    for name, th in ebook_robot.COVER_THEMES.items():
        gt = th["grad_top"]
        dist = sum((avg[i] - gt[i]) ** 2 for i in range(3))
        if dist < best_dist:
            best_dist = dist
            best_name = name
    return best_name, avg


def main():
    print(f"[정보] 시즌1 본권 10권 표지 재생성 (author={AUTHOR!r})")
    if not EXTRACT_DIR.exists():
        EXTRACT_DIR.mkdir(parents=True, exist_ok=True)

    ok = 0
    fail = 0
    for title, bookk_fn, extract_fn in BOOKS:
        bookk_path = BOOKK_DIR / bookk_fn
        extract_path = EXTRACT_DIR / extract_fn
        try:
            if not bookk_path.exists():
                print(f"[누락] 부크크검수 epub 없음: {bookk_path}")
                fail += 1
                continue
            if not extract_path.exists():
                print(f"[누락] 기존 추출 표지 없음 (테마 식별 불가): {extract_path}")
                fail += 1
                continue

            opf_title, subtitle = read_meta_from_epub(bookk_path)
            if not opf_title:
                print(f"[실패] {title}: OPF title 추출 못함")
                fail += 1
                continue

            theme, sampled = detect_theme(extract_path)
            new_path = ebook_robot.make_cover_image(
                opf_title, subtitle, AUTHOR, PUBLISHER, theme
            )
            shutil.copy2(new_path, extract_path)
            ok += 1
            print(f"[완료] {title}")
            print(f"        title='{opf_title}' / sub='{subtitle[:40]}'")
            print(f"        sampled RGB{sampled} → theme={theme}")
        except Exception as ex:
            fail += 1
            print(f"[실패] {title}: {ex}")

    print(f"\n===== 시즌1 표지 재생성: {ok}권 완료 / {fail}권 실패 =====")


if __name__ == "__main__":
    main()
