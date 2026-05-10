# -*- coding: utf-8 -*-
# PATCHED:utf8-stdout-v1
"""
시즌3 132권 유튜브 썸네일 일괄 빌드 (본권 120 + 종합권 12).

표지 빌더(_design_s3_covers)와 동일한 디자인 언어:
  - 같은 그룹 색·깊이 진행
  - 같은 12 그룹 모티프
  - 같은 출판사 로고
  - 16:9 비율 1280x720, 좌측 모티프 / 우측 텍스트

출력:
  ~/Downloads/s3_thumbs/g##_seq##_thumb.jpg     (본권 120)
  ~/Downloads/s3_thumbs/g##_omnibus_thumb.jpg   (종합권 12)
  ~/Downloads/s3_thumbs/_contact_g##.jpg
  ~/Downloads/s3_thumbs/_contact_omnibus.jpg
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# 표지 빌더에서 디자인 시스템 가져옴 (모티프·색·로고·폰트·유틸)
from _design_s3_covers import (
    MOTIF, colors_for_depth, vertical_gradient, starfield, paste_logo,
    font, panorama, WHITE, WHITE_DIM,
)


def build_thumb_contact_sheet(paths, title, out_path, cols=3):
    """썸네일(16:9)용 콘택트 시트 — 셀 크기를 가로 비율로."""
    n = len(paths)
    rows = (n + cols - 1) // cols
    cell_w, cell_h = 480, 270    # 16:9 비율
    pad = 18
    sheet_w = cols * cell_w + (cols + 1) * pad
    sheet_h = rows * cell_h + (rows + 1) * pad + 70
    sheet = Image.new("RGB", (sheet_w, sheet_h), (15, 15, 22))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 22), title, font=font(28, bold=True), fill=(240, 220, 160))
    for i, p in enumerate(paths):
        r = i // cols; c = i % cols
        x = pad + c * (cell_w + pad)
        y = 70 + pad + r * (cell_h + pad)
        thumb = Image.open(p).resize((cell_w, cell_h), Image.LANCZOS)
        sheet.paste(thumb, (x, y))
    sheet.save(out_path, "JPEG", quality=90)
    print(f"  [콘택트시트] {out_path.name}")

OUT_DIR = Path.home() / "Downloads" / "s3_thumbs"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def build_thumb(code, title, subtitle, side_label, depth_label, out_path, seed_extra=0):
    pal = colors_for_depth(code, depth_label)
    BG_TOP, BG_BOT, MAIN, GLOW, PALE = pal

    W, H = 1280, 720
    img = vertical_gradient(W, H, BG_TOP, BG_BOT).convert("RGBA")
    starfield(img, n=120, seed=(hash(code) + seed_extra) % 1000)

    # 좌측 모티프 — 표지 모티프 그대로지만 더 작게(R=240) 좌측에 배치
    cx, cy = 320, H // 2
    R = 240
    MOTIF[code](img, cx, cy, R, pal)

    img = img.convert("RGB")
    d = ImageDraw.Draw(img)

    # 우측 텍스트 영역 (x=620~)
    text_x = 620

    # 시즌·그룹 라벨
    d.text((text_x, 70), "시즌 3", font=font(28), fill=GLOW)
    d.line([(text_x, 118), (text_x + 380, 118)], fill=PALE, width=1)
    d.text((text_x, 132), f"{code} · {side_label}", font=font(24, bold=True), fill=WHITE_DIM)

    # 권 제목 (큰 글씨, 길이에 따라 폰트 자동)
    title_size = 92 if len(title) <= 8 else (76 if len(title) <= 12 else 60)
    d.text((text_x, 215), title, font=font(title_size, bold=True), fill=WHITE)

    # 부제
    if subtitle:
        sub_size = 36 if len(subtitle) <= 22 else 28
        # 두 줄 자동 분할 (짧으면 한 줄, 길면 두 줄)
        if len(subtitle) <= 24:
            d.text((text_x, 360), subtitle, font=font(sub_size), fill=GLOW)
        else:
            # 22자쯤에서 자르거나 ' '로 끊기
            parts = []
            words = subtitle.split(" ")
            line = ""
            for w in words:
                if len(line) + len(w) + 1 > 22 and line:
                    parts.append(line)
                    line = w
                else:
                    line = (line + " " + w).strip()
            if line:
                parts.append(line)
            for i, p in enumerate(parts[:2]):
                d.text((text_x, 360 + i * 42), p, font=font(sub_size), fill=GLOW)

    # 저자 / 발행처는 로고로 마무리
    d.text((text_x, 510), "AI, 박헌근", font=font(28, bold=True), fill=WHITE_DIM)

    # 액자 한 줄
    d.rectangle([18, 18, W - 18, H - 18], outline=PALE, width=2)

    # 출판사 로고 (썸네일은 작게, 우측 하단)
    img = img.convert("RGBA")
    paste_logo(img, target_w=240, cx=W - 160, cy=H - 60)
    img = img.convert("RGB")

    img.save(out_path, "JPEG", quality=92)


def build_group_book_thumbs(code, group):
    paths = []
    for b in group["base_cells"]:
        seq = b["seq"]
        out = OUT_DIR / f"{code.lower()}_seq{seq:02d}_thumb.jpg"
        build_thumb(code, b["title"], b.get("hint", ""), f"{seq}권",
                    b["depth"], out, seed_extra=seq)
        paths.append(out)
    return paths


def build_group_omnibus_thumb(code, group):
    s = group["synthesis_cell"]
    out = OUT_DIR / f"{code.lower()}_omnibus_thumb.jpg"
    build_thumb(code, s["title"], s.get("subtitle", ""), "종합권",
                "synthesis", out, seed_extra=99)
    return out


def main():
    print("=== 시즌 3 132권 썸네일 일괄 빌드 ===")
    omnibus_paths = []
    for g in panorama["groups"]:
        code = g["group"]["code"]
        print(f"\n[{code}] {g['group']['theme_name']}")
        bp = build_group_book_thumbs(code, g)
        op = build_group_omnibus_thumb(code, g)
        omnibus_paths.append(op)
        for i, p in enumerate(bp + [op], 1):
            print(f"  {p.name}")
        # 그룹별 콘택트 시트 (썸네일 11장 = 본권 10 + 종합권 1, 16:9 라 가로 길게)
        build_thumb_contact_sheet(bp + [op],
                            f"{code} {g['group']['theme_name']} — 썸네일 11장",
                            OUT_DIR / f"_contact_{code.lower()}.jpg", cols=3)
    # 종합권 12장 콘택트 시트
    build_thumb_contact_sheet(omnibus_paths, "시즌 3 — 종합권 썸네일 12장",
                        OUT_DIR / "_contact_omnibus.jpg", cols=3)
    print(f"\n[완료] 본권 120 + 종합권 12 = 132 썸네일")


if __name__ == "__main__":
    main()
