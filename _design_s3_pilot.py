# -*- coding: utf-8 -*-
# PATCHED:utf8-stdout-v1
"""
시즌3 표지·썸네일 시범 1장씩 (G01 seq1 "삼위일체의 신비").

컨셉 B: 기하 추상 + 그룹 모티프.
모티프: 회전하는 삼각 3개 합성 = 페리코레시스의 춤.
색: G01 indigo_gold, seq1 깊이(가장 옅은·새벽 톤).

출력:
  ~/Downloads/s3_pilot_g01_seq1_cover.jpg     (1400x2100)
  ~/Downloads/s3_pilot_g01_seq1_thumb.jpg     (1280x720)
"""
import math
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.stdout.reconfigure(encoding="utf-8")

OUT = Path.home() / "Downloads"

# ── 책 정보 (panorama G01 seq1 그대로) ──────────────────────────
TITLE       = "삼위일체의 신비"
SUBTITLE    = "한 하나님, 세 인격"
AUTHOR      = "AI, 박헌근"
SERIES_MARK = "AI 시대 영성 · 시즌 3"
GROUP_MARK  = "G01 · 1권"
PUBLISHER_MARK = "AI 시대 영성 · 2026"
THUMB_BIG   = "삼위일체"   # 썸네일용 한 단어 압축

# ── G01 indigo_gold seq1 색 (옅은·새벽 톤) ──────────────────────
BG_TOP      = (28, 38, 86)        # 짙은 인디고
BG_BOTTOM   = (52, 70, 124)       # 옅은 코발트
GOLD        = (212, 175, 55)
GOLD_GLOW   = (244, 215, 126)
GOLD_PALE   = (240, 225, 170)
WHITE       = (252, 251, 245)
WHITE_DIM   = (220, 218, 210)


def font(size, bold=False):
    name = "malgunbd.ttf" if bold else "malgun.ttf"
    try:
        return ImageFont.truetype(name, size)
    except Exception:
        return ImageFont.load_default()


def vertical_gradient(w, h, top_rgb, bot_rgb):
    """상→하 선형 그라데이션 이미지."""
    img = Image.new("RGB", (w, h), top_rgb)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(top_rgb[0] + (bot_rgb[0] - top_rgb[0]) * t)
        g = int(top_rgb[1] + (bot_rgb[1] - top_rgb[1]) * t)
        b = int(top_rgb[2] + (bot_rgb[2] - top_rgb[2]) * t)
        d.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def add_radial_glow(img, cx, cy, radius, color, intensity=80):
    """중심에서 외곽으로 옅어지는 원형 광채를 합성 (모티프 뒤 후광)."""
    w, h = img.size
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    # 동심원을 안에서 밖으로 그리며 알파 감소
    steps = 60
    for i in range(steps, 0, -1):
        r = int(radius * i / steps)
        alpha = int(intensity * (i / steps) ** 2.2)
        gd.ellipse([cx - r, cy - r, cx + r, cy + r],
                   fill=(color[0], color[1], color[2], alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=12))
    img.paste(glow, (0, 0), glow)
    return img


def draw_perichoresis(img, cx, cy, R):
    """G01 모티프: 페리코레시스의 춤.

    같은 정삼각형 3개를 0°/40°/80° 회전해 겹치고, 외곽에 가는 원으로 묶음.
    중심에 작은 황금 점 + 후광.
    """
    # 후광 (모티프 뒤)
    add_radial_glow(img, cx, cy, R + 200, GOLD_GLOW, intensity=70)

    # 외곽 원 (가는 두 줄, 페리코레시스의 영원한 춤 둘레)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse([cx - R - 40, cy - R - 40, cx + R + 40, cy + R + 40],
               outline=(GOLD_PALE[0], GOLD_PALE[1], GOLD_PALE[2], 90), width=2)
    od.ellipse([cx - R - 24, cy - R - 24, cx + R + 24, cy + R + 24],
               outline=(GOLD_PALE[0], GOLD_PALE[1], GOLD_PALE[2], 50), width=1)
    img.paste(overlay, (0, 0), overlay)

    # 회전된 정삼각형 3개
    def triangle_points(angle_deg):
        # 정삼각형 꼭지점 3개 (반지름 R, 시작각 angle_deg)
        pts = []
        for k in range(3):
            a = math.radians(angle_deg + k * 120)
            pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
        return pts

    # 3개 삼각 — 각각 다른 회전·다른 채도. 알파 합성으로 겹침.
    layers = [
        (-90, GOLD,      130),   # 위 꼭지점, 짙은 황금
        (-90 + 40, GOLD_GLOW, 110),
        (-90 + 80, GOLD_PALE, 90),
    ]
    for angle, color, alpha in layers:
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        pts = triangle_points(angle)
        ld.polygon(pts, outline=(color[0], color[1], color[2], alpha + 80),
                   fill=(color[0], color[1], color[2], alpha))
        # 외곽선 별도 (채도 강조)
        ld.line(pts + [pts[0]], fill=(color[0], color[1], color[2], 200), width=4)
        img.paste(layer, (0, 0), layer)

    # 중심점 (한 점에서 비치는 한 빛)
    od2 = ImageDraw.Draw(img)
    od2.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=GOLD_GLOW)
    od2.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=WHITE)


def text_centered(draw, y, text, fnt, color, W):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    w = bbox[2] - bbox[0]
    draw.text(((W - w) // 2, y), text, font=fnt, fill=color)


def make_cover():
    W, H = 1400, 2100
    img = vertical_gradient(W, H, BG_TOP, BG_BOTTOM).convert("RGBA")

    # 미세 노이즈 텍스처(별빛 점) — 신비 톤
    import random
    random.seed(42)
    nd = ImageDraw.Draw(img)
    for _ in range(220):
        x = random.randint(60, W - 60)
        y = random.randint(60, H - 60)
        a = random.randint(30, 110)
        s = random.choice([1, 1, 1, 2])
        nd.ellipse([x, y, x + s, y + s], fill=(255, 255, 240, a))

    # 모티프 (중앙 약간 위쪽)
    cx, cy = W // 2, 920
    R = 360
    draw_perichoresis(img, cx, cy, R)

    # 하단 텍스트 영역
    img = img.convert("RGB")
    d = ImageDraw.Draw(img)

    # 상단 시리즈 마크 + 권 번호
    fs_mark = font(28)
    fs_groupmark = font(24, bold=True)
    text_centered(d, 130, SERIES_MARK, fs_mark, GOLD_GLOW, W)
    # 가는 골드 라인
    d.line([(W // 2 - 60, 175), (W // 2 + 60, 175)], fill=GOLD_PALE, width=1)
    text_centered(d, 195, GROUP_MARK, fs_groupmark, WHITE_DIM, W)

    # 제목 (강한 임팩트)
    fs_title = font(108, bold=True)
    text_centered(d, 1560, TITLE, fs_title, WHITE, W)

    # 부제
    fs_sub = font(50)
    text_centered(d, 1730, SUBTITLE, fs_sub, GOLD_PALE, W)

    # 저자 + 출판사 마크
    fs_author = font(40, bold=True)
    text_centered(d, 1900, AUTHOR, fs_author, WHITE_DIM, W)
    fs_pub = font(22)
    text_centered(d, 2000, PUBLISHER_MARK, fs_pub, GOLD_GLOW, W)

    # 가장자리 가는 액자
    d.rectangle([28, 28, W - 28, H - 28], outline=GOLD_PALE, width=2)
    d.rectangle([40, 40, W - 40, H - 40], outline=GOLD, width=1)

    out = OUT / "s3_pilot_g01_seq1_cover.jpg"
    img.save(out, "JPEG", quality=92)
    print(f"[표지] {out}")


def make_thumb():
    W, H = 1280, 720
    img = vertical_gradient(W, H, BG_TOP, BG_BOTTOM).convert("RGBA")

    # 별빛 노이즈
    import random
    random.seed(11)
    nd = ImageDraw.Draw(img)
    for _ in range(120):
        x = random.randint(40, W - 40)
        y = random.randint(40, H - 40)
        a = random.randint(40, 110)
        s = random.choice([1, 1, 2])
        nd.ellipse([x, y, x + s, y + s], fill=(255, 255, 240, a))

    # 좌측 모티프 (썸네일에 맞게 작게)
    cx, cy = 320, H // 2
    R = 220
    draw_perichoresis(img, cx, cy, R)

    img = img.convert("RGB")
    d = ImageDraw.Draw(img)

    # 우측 텍스트
    text_x = 620

    # 시즌·그룹 작은 마크
    d.text((text_x, 90), SERIES_MARK, font=font(28), fill=GOLD_GLOW)
    d.line([(text_x, 138), (text_x + 380, 138)], fill=GOLD_PALE, width=1)
    d.text((text_x, 152), GROUP_MARK, font=font(24, bold=True), fill=WHITE_DIM)

    # 큰 한 단어 (압축 제목)
    d.text((text_x, 230), THUMB_BIG, font=font(140, bold=True), fill=WHITE)
    # 제목 정자(작게)
    d.text((text_x, 410), TITLE, font=font(46, bold=True), fill=GOLD_GLOW)
    # 부제
    d.text((text_x, 480), SUBTITLE, font=font(34), fill=GOLD_PALE)

    # 저자/출판사
    d.text((text_x, 600), AUTHOR + " · " + PUBLISHER_MARK, font=font(24), fill=WHITE_DIM)

    # 가장자리 가는 액자 (썸네일은 한 줄만)
    d.rectangle([18, 18, W - 18, H - 18], outline=GOLD_PALE, width=2)

    out = OUT / "s3_pilot_g01_seq1_thumb.jpg"
    img.save(out, "JPEG", quality=92)
    print(f"[썸네일] {out}")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    make_cover()
    make_thumb()
    print("끝.")
