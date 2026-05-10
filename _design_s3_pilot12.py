# -*- coding: utf-8 -*-
# PATCHED:utf8-stdout-v1
"""
시즌3 12 그룹 모티프 시범 — 각 그룹 seq1 표지 12장 + 콘택트 시트 1장.

컨셉 B: 기하 추상 + 그룹 모티프.
색 체계: 5주체 색 가족 → 12 관계 색 조합 (이전 추천 그대로).
모티프: 12 그룹의 axis 의미를 추상 도형으로.

출력:
  ~/Downloads/s3_pilot/g01_seq1_cover.jpg ~ g12_seq1_cover.jpg  (각 1400x2100)
  ~/Downloads/s3_pilot/_contact_sheet.jpg  (12장 4x3 그리드)
"""
import json
import math
import os
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
OUT_DIR = Path.home() / "Downloads" / "s3_pilot"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 출판사 로고 (RGBA, 골드 톤)
LOGO_HORIZONTAL = ROOT / "logo_horizontal_gold.png"
LOGO_VERTICAL = ROOT / "logo_vertical_gold.png"

# panorama 에서 G## seq1 메타 읽음
panorama = json.loads((ROOT / "s3_panorama.json").read_text(encoding="utf-8"))


def paste_logo(img, kind, target_w, cx, cy):
    """로고(가로 or 세로)를 표지에 합성. cx,cy 는 로고 가운데 좌표.
    target_w 로 폭을 맞추고 비율 유지해서 높이 자동.
    """
    src = LOGO_HORIZONTAL if kind == "horizontal" else LOGO_VERTICAL
    logo = Image.open(src).convert("RGBA")
    ratio = target_w / logo.width
    new_h = int(logo.height * ratio)
    logo = logo.resize((target_w, new_h), Image.LANCZOS)
    x = int(cx - target_w / 2)
    y = int(cy - new_h / 2)
    img.paste(logo, (x, y), logo)
    return new_h


# ════════════════════════════════════════════════════════════════
# 색 시스템 — 12 그룹 (이전 추천 그대로)
# ════════════════════════════════════════════════════════════════
def hex_to_rgb(h):
    h = h.lstrip("#")
    return (int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16))

# (배경 상, 배경 하, 모티프 주, 모티프 광, 모티프 옅)
GROUP_COLORS = {
    "G01": ("#1C2656", "#34467C", "#D4AF37", "#F4D77E", "#F0E1AA"),  # indigo + gold
    "G02": ("#0D0F18", "#1A1620", "#7A1428", "#B22A3C", "#D4576B"),  # obsidian + crimson
    "G03": ("#3D2418", "#5C3F2E", "#C9926B", "#E8C29E", "#F2DCC4"),  # terracotta + cream
    "G04": ("#1C2656", "#3A1426", "#D4AF37", "#FFF1A0", "#B22A3C"),  # indigo vs crimson + gold lightning
    "G05": ("#1C2656", "#3D2418", "#D4AF37", "#F4D77E", "#C9926B"),  # indigo + terracotta + gold
    "G06": ("#3A1A1A", "#1F1A1A", "#A0A8B0", "#E0E4EB", "#D9404C"),  # rust + steel
    "G07": ("#2A3D2C", "#4A5C32", "#F4A574", "#F8C898", "#9DBC8A"),  # sage + sunrise
    "G08": ("#3D3A52", "#5A5670", "#E0DCEA", "#F4F0FA", "#C8B8E4"),  # pearl + lavender
    "G09": ("#0F1E5C", "#1B2A6E", "#FFF8E0", "#FFEFB8", "#D4AF37"),  # cobalt + white gold
    "G10": ("#0A0814", "#1A1226", "#9A7AB8", "#C4A8DC", "#5A2A7A"),  # midnight + violet
    "G11": ("#1A3A5C", "#2D5680", "#D4DCE6", "#F0F4FA", "#7DAED4"),  # azure + silver
    "G12": ("#0F3A2E", "#1F5A48", "#C8DCD0", "#E8F0EA", "#5C9080"),  # emerald + silver
}

def colors(code):
    h = GROUP_COLORS[code]
    return tuple(hex_to_rgb(x) for x in h)


# ════════════════════════════════════════════════════════════════
# 기본 유틸 (그라데이션·후광·폰트·텍스트)
# ════════════════════════════════════════════════════════════════
def font(size, bold=False):
    name = "malgunbd.ttf" if bold else "malgun.ttf"
    try:
        return ImageFont.truetype(name, size)
    except Exception:
        return ImageFont.load_default()


def vertical_gradient(w, h, top_rgb, bot_rgb):
    img = Image.new("RGB", (w, h), top_rgb)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(top_rgb[0] + (bot_rgb[0] - top_rgb[0]) * t)
        g = int(top_rgb[1] + (bot_rgb[1] - top_rgb[1]) * t)
        b = int(top_rgb[2] + (bot_rgb[2] - top_rgb[2]) * t)
        d.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def add_glow(img, cx, cy, radius, color, intensity=70):
    w, h = img.size
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    steps = 50
    for i in range(steps, 0, -1):
        r = int(radius * i / steps)
        alpha = int(intensity * (i / steps) ** 2.2)
        gd.ellipse([cx - r, cy - r, cx + r, cy + r],
                   fill=(color[0], color[1], color[2], alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=12))
    img.paste(glow, (0, 0), glow)
    return img


def starfield(img, n=220, seed=42):
    rng = random.Random(seed)
    w, h = img.size
    d = ImageDraw.Draw(img)
    for _ in range(n):
        x = rng.randint(60, w - 60)
        y = rng.randint(60, h - 60)
        a = rng.randint(30, 110)
        s = rng.choice([1, 1, 1, 2])
        d.ellipse([x, y, x + s, y + s], fill=(255, 255, 240, a))


def text_centered(draw, y, text, fnt, color, W):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    w = bbox[2] - bbox[0]
    draw.text(((W - w) // 2, y), text, font=fnt, fill=color)


# ════════════════════════════════════════════════════════════════
# 12 모티프 함수 — 각 함수: (img, cx, cy, R, palette)
#    palette = (bg_top, bg_bot, main, glow, pale)
# ════════════════════════════════════════════════════════════════

def m_g01_perichoresis(img, cx, cy, R, pal):
    """G01: 회전하는 삼각 3개 = 페리코레시스의 춤."""
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 200, GLOW, intensity=70)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse([cx - R - 40, cy - R - 40, cx + R + 40, cy + R + 40],
               outline=(*PALE, 90), width=2)
    img.paste(overlay, (0, 0), overlay)
    layers = [(-90, MAIN, 130), (-90 + 40, GLOW, 110), (-90 + 80, PALE, 90)]
    for angle, c, a in layers:
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        pts = [(cx + R * math.cos(math.radians(angle + k * 120)),
                cy + R * math.sin(math.radians(angle + k * 120))) for k in range(3)]
        ld.polygon(pts, fill=(*c, a))
        ld.line(pts + [pts[0]], fill=(*c, 200), width=4)
        img.paste(layer, (0, 0), layer)
    d = ImageDraw.Draw(img)
    d.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=GLOW)
    d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=(252, 251, 245))


def m_g02_broken_diamond(img, cx, cy, R, pal):
    """G02: 깨진 마름모 — 자기 분열의 어둠."""
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 180, MAIN, intensity=60)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    # 마름모 (4 꼭지점)
    pts = [(cx, cy - R), (cx + R, cy), (cx, cy + R), (cx - R, cy)]
    ld.polygon(pts, fill=(*MAIN, 120), outline=(*PALE, 200))
    ld.line(pts + [pts[0]], fill=(*PALE, 220), width=4)
    # 균열선 (지그재그)
    crack = [
        (cx - R + 60, cy - R // 2),
        (cx - 30, cy - 60),
        (cx + 30, cy + 40),
        (cx - 20, cy + 120),
        (cx + R - 60, cy + R // 2 + 20),
    ]
    ld.line(crack, fill=(*GLOW, 240), width=6)
    # 부서진 조각 몇 개
    chips = [
        [(cx + R * 0.3, cy + R * 0.55), (cx + R * 0.55, cy + R * 0.45),
         (cx + R * 0.45, cy + R * 0.7)],
        [(cx - R * 0.55, cy - R * 0.2), (cx - R * 0.4, cy - R * 0.05),
         (cx - R * 0.65, cy + R * 0.05)],
    ]
    for c in chips:
        ld.polygon(c, fill=(*GLOW, 180))
    img.paste(layer, (0, 0), layer)


def m_g03_two_arcs(img, cx, cy, R, pal):
    """G03: 두 호의 만남 — 인간 상호 관계의 교집합."""
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 180, GLOW, intensity=60)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    # 두 큰 원 (좌·우, 약간 겹침)
    off = int(R * 0.5)
    ld.ellipse([cx - off - R, cy - R, cx - off + R, cy + R],
               outline=(*MAIN, 220), width=8)
    ld.ellipse([cx + off - R, cy - R, cx + off + R, cy + R],
               outline=(*MAIN, 220), width=8)
    # 교집합 영역 (vesica piscis) 채움
    inter = Image.new("RGBA", img.size, (0, 0, 0, 0))
    a = Image.new("RGBA", img.size, (0, 0, 0, 0))
    aa = ImageDraw.Draw(a)
    aa.ellipse([cx - off - R, cy - R, cx - off + R, cy + R], fill=(255, 255, 255, 255))
    b = Image.new("RGBA", img.size, (0, 0, 0, 0))
    bb = ImageDraw.Draw(b)
    bb.ellipse([cx + off - R, cy - R, cx + off + R, cy + R], fill=(255, 255, 255, 255))
    # 교집합 = a AND b
    from PIL import ImageChops
    inter_mask = ImageChops.multiply(a, b)
    inter_color = Image.new("RGBA", img.size, (*PALE, 150))
    inter = Image.composite(inter_color, Image.new("RGBA", img.size, (0,0,0,0)), inter_mask.split()[3])
    layer.paste(inter, (0, 0), inter)
    # 중앙에 작은 점 (만남)
    ld.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=(*GLOW, 240))
    img.paste(layer, (0, 0), layer)


def m_g04_x_lightning(img, cx, cy, R, pal):
    """G04: 교차된 X + 황금 번개 — 우주적 대결."""
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 200, MAIN, intensity=65)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    # 두 굵은 빔 (대각)
    w_beam = 24
    for ang_deg in (45, -45):
        a = math.radians(ang_deg)
        dx, dy = math.cos(a) * R, math.sin(a) * R
        # 두께를 가진 직선을 polygon으로
        nx, ny = -math.sin(a), math.cos(a)
        x1, y1 = cx - dx, cy - dy
        x2, y2 = cx + dx, cy + dy
        pts = [(x1 + nx * w_beam, y1 + ny * w_beam),
               (x2 + nx * w_beam, y2 + ny * w_beam),
               (x2 - nx * w_beam, y2 - ny * w_beam),
               (x1 - nx * w_beam, y1 - ny * w_beam)]
        ld.polygon(pts, fill=(*MAIN, 230))
    # 가운데 황금 번개 (Z 모양)
    bolt = [
        (cx - R * 0.15, cy - R),
        (cx + R * 0.05, cy - R * 0.2),
        (cx - R * 0.1,  cy - R * 0.15),
        (cx + R * 0.2,  cy + R),
    ]
    bolt_w = [
        (cx - R * 0.05, cy - R),
        (cx + R * 0.15, cy - R * 0.2),
        (cx + 0,        cy - R * 0.15),
        (cx + R * 0.3,  cy + R),
    ]
    poly = list(bolt) + list(reversed(bolt_w))
    ld.polygon(poly, fill=(*GLOW, 240))
    ld.line(bolt, fill=(*PALE, 240), width=3)
    img.paste(layer, (0, 0), layer)


def m_g05_cross_pillar(img, cx, cy, R, pal):
    """G05: 빛 기둥의 십자 — 구속사 중심축."""
    _, _, MAIN, GLOW, PALE = pal
    # 위에서 내려오는 빛 기둥
    add_glow(img, cx, cy, R + 220, MAIN, intensity=80)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    # 수직 빔 (위→아래, 위쪽이 더 굵고 밝음)
    for i in range(8):
        w = 60 - i * 4
        a = 220 - i * 18
        x1 = cx - w
        x2 = cx + w
        ld.polygon([(x1, cy - R - 100), (x2, cy - R - 100),
                    (x2 + 20, cy + R + 50), (x1 - 20, cy + R + 50)],
                   fill=(*PALE, max(40, a)))
    # 가로축 (구속의 만남)
    h_beam = 28
    ld.polygon([(cx - R, cy - h_beam), (cx + R, cy - h_beam),
                (cx + R, cy + h_beam), (cx - R, cy + h_beam)],
               fill=(*MAIN, 230))
    # 십자 교차점에 광채
    ld.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], fill=(*GLOW, 220))
    img.paste(layer, (0, 0), layer)


def m_g06_shield_arrow(img, cx, cy, R, pal):
    """G06: 방패와 화살 — 영적 전쟁."""
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 180, MAIN, intensity=55)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    # 방패 (위가 평평하고 아래가 뾰족한 형)
    sh = [
        (cx - R * 0.7, cy - R * 0.7),
        (cx + R * 0.7, cy - R * 0.7),
        (cx + R * 0.7, cy + R * 0.1),
        (cx,           cy + R * 0.95),
        (cx - R * 0.7, cy + R * 0.1),
    ]
    ld.polygon(sh, fill=(*MAIN, 170), outline=(*PALE, 230))
    ld.line(sh + [sh[0]], fill=(*PALE, 230), width=5)
    # 방패 가운데 줄
    ld.line([(cx, cy - R * 0.7), (cx, cy + R * 0.95)], fill=(*PALE, 200), width=3)
    # 화살 (좌상→우하 방향, 방패에 박힌 모양)
    arr_start = (cx - R * 1.3, cy - R * 1.2)
    arr_tip = (cx - R * 0.15, cy - R * 0.05)
    ld.line([arr_start, arr_tip], fill=(*GLOW, 240), width=8)
    # 화살촉
    head = [
        (arr_tip[0],            arr_tip[1]),
        (arr_tip[0] - 30,       arr_tip[1] - 50),
        (arr_tip[0] + 50,       arr_tip[1] - 30),
    ]
    ld.polygon(head, fill=(*GLOW, 240))
    img.paste(layer, (0, 0), layer)


def m_g07_leaf_on_hand(img, cx, cy, R, pal):
    """G07: 손 위의 잎 — 청지기와 창조."""
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 180, GLOW, intensity=60)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    # 손바닥(원호 + 손가락 5)
    palm_y = cy + R * 0.4
    # 손바닥 호
    ld.chord([cx - R * 0.7, palm_y - R * 0.5, cx + R * 0.7, palm_y + R * 0.5],
             0, 180, fill=(*MAIN, 200), outline=(*PALE, 230))
    # 손목
    ld.rectangle([cx - R * 0.45, palm_y, cx + R * 0.45, palm_y + R * 0.45],
                 fill=(*MAIN, 200), outline=(*PALE, 220), width=4)
    # 손가락 5개 (작은 타원)
    for i, dx in enumerate([-0.5, -0.27, -0.05, 0.18, 0.42]):
        fx = cx + R * dx
        fy = palm_y - R * 0.2
        h = R * (0.55 if i == 2 else 0.5 if i in (1,3) else 0.4)
        ld.ellipse([fx - 18, fy - h, fx + 18, fy], fill=(*MAIN, 200), outline=(*PALE, 220))
    # 잎 (손 위, 위로 자라는 모양)
    leaf_cx, leaf_cy = cx, cy - R * 0.15
    leaf = [
        (leaf_cx, leaf_cy - R * 0.65),
        (leaf_cx + R * 0.3, leaf_cy - R * 0.2),
        (leaf_cx + R * 0.18, leaf_cy + R * 0.15),
        (leaf_cx, leaf_cy),
        (leaf_cx - R * 0.18, leaf_cy + R * 0.15),
        (leaf_cx - R * 0.3, leaf_cy - R * 0.2),
    ]
    ld.polygon(leaf, fill=(*GLOW, 220), outline=(*PALE, 230))
    ld.line(leaf + [leaf[0]], fill=(*PALE, 230), width=3)
    # 잎맥 (가운데 선)
    ld.line([(leaf_cx, leaf_cy - R * 0.65), (leaf_cx, leaf_cy + R * 0.0)],
            fill=(*MAIN, 220), width=3)
    img.paste(layer, (0, 0), layer)


def m_g08_concentric(img, cx, cy, R, pal):
    """G08: 동심원 합창 — 천사 공동체."""
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 200, GLOW, intensity=75)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    # 점점 커지는 8개 원
    for i in range(8, 0, -1):
        r = int(R * i / 8)
        alpha = int(50 + (8 - i) * 22)
        col = MAIN if i % 2 == 0 else PALE
        ld.ellipse([cx - r, cy - r, cx + r, cy + r],
                   outline=(*col, alpha), width=4)
    # 중심 빛 점
    ld.ellipse([cx - 28, cy - 28, cx + 28, cy + 28], fill=(*GLOW, 240))
    ld.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=(255, 255, 255, 255))
    img.paste(layer, (0, 0), layer)


def m_g09_crown_light(img, cx, cy, R, pal):
    """G09: 왕관 빛 — 보좌 앞 시종."""
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 200, MAIN, intensity=80)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    # 빛줄기 12개 (왕관 광선)
    for i in range(12):
        a = math.radians(-90 + i * 30)
        x2 = cx + (R + 100) * math.cos(a)
        y2 = cy + (R + 100) * math.sin(a)
        ld.line([(cx, cy), (x2, y2)], fill=(*GLOW, 130), width=3)
    # 왕관 (5 꼭지)
    crown_y = cy + R * 0.1
    crown_pts = [
        (cx - R * 0.7, crown_y + R * 0.4),
        (cx - R * 0.7, crown_y),
        (cx - R * 0.45, crown_y - R * 0.3),
        (cx - R * 0.2, crown_y),
        (cx,            crown_y - R * 0.5),
        (cx + R * 0.2, crown_y),
        (cx + R * 0.45, crown_y - R * 0.3),
        (cx + R * 0.7, crown_y),
        (cx + R * 0.7, crown_y + R * 0.4),
    ]
    ld.polygon(crown_pts, fill=(*GLOW, 230), outline=(*PALE, 240))
    ld.line(crown_pts + [crown_pts[0]], fill=(*PALE, 240), width=5)
    # 가운데 보석
    ld.ellipse([cx - 22, crown_y - 30, cx + 22, crown_y + 14], fill=(*MAIN, 240))
    img.paste(layer, (0, 0), layer)


def m_g10_broken_wing(img, cx, cy, R, pal):
    """G10: 부서진 날개 — 하늘의 전쟁."""
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 180, MAIN, intensity=60)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    # 왼쪽 날개 (정상)
    L_wing = [
        (cx - 20, cy - R * 0.3),
        (cx - R * 0.9, cy - R * 0.5),
        (cx - R * 1.1, cy - R * 0.05),
        (cx - R * 0.8, cy + R * 0.3),
        (cx - 30, cy + R * 0.2),
    ]
    ld.polygon(L_wing, fill=(*PALE, 200), outline=(*PALE, 240))
    # 깃털 라인
    for k in [0.2, 0.4, 0.6, 0.8]:
        x = cx - R * k - 50
        ld.line([(x, cy - R * 0.3), (x, cy + R * 0.15)], fill=(*MAIN, 200), width=2)
    # 오른쪽 날개 (부서짐, 조각)
    chunks = [
        [(cx + 20, cy - R * 0.3), (cx + R * 0.5, cy - R * 0.4),
         (cx + R * 0.4, cy - R * 0.1), (cx + 30, cy - R * 0.1)],
        [(cx + R * 0.55, cy - R * 0.05), (cx + R * 0.8, cy + R * 0.05),
         (cx + R * 0.65, cy + R * 0.2)],
        [(cx + R * 0.85, cy - R * 0.6), (cx + R * 0.95, cy - R * 0.45),
         (cx + R * 0.75, cy - R * 0.4)],
    ]
    for c in chunks:
        ld.polygon(c, fill=(*GLOW, 200), outline=(*PALE, 200))
    # 부서진 틈 균열
    ld.line([(cx + 30, cy - R * 0.4), (cx + R * 0.55, cy + R * 0.1)],
            fill=(*MAIN, 220), width=4)
    img.paste(layer, (0, 0), layer)


def m_g11_parallel_arcs(img, cx, cy, R, pal):
    """G11: 두 호의 동행 — 보호하는 동행자."""
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 180, GLOW, intensity=70)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    # 두 평행한 호 (위에서 아래로 향함)
    spread = R * 0.35
    for i, (col, alpha, off, w) in enumerate([
        (MAIN, 230, -spread, 12),
        (PALE, 230, +spread, 12),
    ]):
        # bezier 흉내: 곡선을 다중 polygon line 으로
        pts = []
        for k in range(60):
            t = k / 59
            # 곡선: y는 t에 따라 진행, x는 위쪽에서 살짝 모임
            y = cy - R * 0.95 + R * 1.9 * t
            x = cx + off + (R * 0.18) * math.sin(t * math.pi)
            pts.append((x, y))
        ld.line(pts, fill=(*col, alpha), width=w)
    # 두 호 사이 공간에 작은 점들 (걸음의 자취)
    for k in range(7):
        t = (k + 0.5) / 7
        y = cy - R * 0.85 + R * 1.7 * t
        ld.ellipse([cx - 6, y - 6, cx + 6, y + 6], fill=(*GLOW, 220))
    img.paste(layer, (0, 0), layer)


def m_g12_wind_leaf(img, cx, cy, R, pal):
    """G12: 바람과 잎 — 자연을 다스리는 손길."""
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 180, GLOW, intensity=60)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    # 바람결 곡선 4개 (큰 sin 곡선)
    for i, (offset_y, alpha, w) in enumerate([
        (-R * 0.5, 200, 6),
        (-R * 0.2, 220, 8),
        (+R * 0.1, 200, 6),
        (+R * 0.4, 180, 5),
    ]):
        pts = []
        for k in range(80):
            t = k / 79
            x = cx - R + 2 * R * t
            y = cy + offset_y + math.sin(t * math.pi * 2 + i * 0.4) * (R * 0.12)
            pts.append((x, y))
        ld.line(pts, fill=(*PALE, alpha), width=w)
    # 잎 한 장 (가운데서 약간 우측, 바람 타고 흔들림)
    leaf_cx, leaf_cy = cx + R * 0.15, cy
    leaf = [
        (leaf_cx,                    leaf_cy - R * 0.4),
        (leaf_cx + R * 0.25,         leaf_cy - R * 0.15),
        (leaf_cx + R * 0.18,         leaf_cy + R * 0.12),
        (leaf_cx,                    leaf_cy + R * 0.05),
        (leaf_cx - R * 0.18,         leaf_cy + R * 0.12),
        (leaf_cx - R * 0.25,         leaf_cy - R * 0.15),
    ]
    ld.polygon(leaf, fill=(*MAIN, 230), outline=(*PALE, 240))
    ld.line(leaf + [leaf[0]], fill=(*PALE, 240), width=3)
    ld.line([(leaf_cx, leaf_cy - R * 0.4), (leaf_cx, leaf_cy + R * 0.05)],
            fill=(*GLOW, 220), width=3)
    img.paste(layer, (0, 0), layer)


MOTIF = {
    "G01": m_g01_perichoresis,
    "G02": m_g02_broken_diamond,
    "G03": m_g03_two_arcs,
    "G04": m_g04_x_lightning,
    "G05": m_g05_cross_pillar,
    "G06": m_g06_shield_arrow,
    "G07": m_g07_leaf_on_hand,
    "G08": m_g08_concentric,
    "G09": m_g09_crown_light,
    "G10": m_g10_broken_wing,
    "G11": m_g11_parallel_arcs,
    "G12": m_g12_wind_leaf,
}


# ════════════════════════════════════════════════════════════════
# 표지 빌더
# ════════════════════════════════════════════════════════════════
def build_cover(code, seq_meta):
    pal = colors(code)
    BG_TOP, BG_BOT, MAIN, GLOW, PALE = pal
    WHITE = (252, 251, 245)
    WHITE_DIM = (220, 218, 210)

    W, H = 1400, 2100
    img = vertical_gradient(W, H, BG_TOP, BG_BOT).convert("RGBA")
    starfield(img, n=220, seed=hash(code) % 100)

    cx, cy = W // 2, 920
    R = 360
    MOTIF[code](img, cx, cy, R, pal)

    # 상단 시즌 마크는 RGBA 단계에서 합성 (가는 글자, 별빛 위에 자연스럽게)
    img = img.convert("RGB")
    d = ImageDraw.Draw(img)

    text_centered(d, 130, "시즌 3", font(28), GLOW, W)
    d.line([(W // 2 - 60, 175), (W // 2 + 60, 175)], fill=PALE, width=1)
    text_centered(d, 195, f"{code} · {seq_meta['seq']}권", font(24, bold=True), WHITE_DIM, W)

    # 본문 텍스트
    text_centered(d, 1560, seq_meta["title"], font(108, bold=True), WHITE, W)
    text_centered(d, 1730, seq_meta["hint"], font(50), PALE, W)
    text_centered(d, 1860, "AI, 박헌근", font(40, bold=True), WHITE_DIM, W)

    # 가장자리 액자
    d.rectangle([28, 28, W - 28, H - 28], outline=PALE, width=2)
    d.rectangle([40, 40, W - 40, H - 40], outline=MAIN, width=1)

    # 출판사 로고 (가로형, 하단 가운데, 폭 360px → 높이 ~120px)
    img = img.convert("RGBA")
    paste_logo(img, "horizontal", target_w=360, cx=W // 2, cy=2000)
    img = img.convert("RGB")

    out = OUT_DIR / f"{code.lower()}_seq1_cover.jpg"
    img.save(out, "JPEG", quality=92)
    print(f"  [{code}] {out.name}  '{seq_meta['title']}'")
    return out


# ════════════════════════════════════════════════════════════════
# 콘택트 시트 (12장 4x3)
# ════════════════════════════════════════════════════════════════
def build_contact_sheet(paths):
    cell_w, cell_h = 360, 540
    cols, rows = 4, 3
    pad = 20
    bg = (15, 15, 22)
    sheet_w = cols * cell_w + (cols + 1) * pad
    sheet_h = rows * cell_h + (rows + 1) * pad + 60
    sheet = Image.new("RGB", (sheet_w, sheet_h), bg)
    d = ImageDraw.Draw(sheet)
    d.text((pad, 18), "시즌 3 — 12 그룹 모티프 시안 (각 그룹 seq1 표지)",
           font=font(28, bold=True), fill=(240, 220, 160))
    for i, p in enumerate(paths):
        r = i // cols
        c = i % cols
        x = pad + c * (cell_w + pad)
        y = 60 + pad + r * (cell_h + pad)
        thumb = Image.open(p).resize((cell_w, cell_h), Image.LANCZOS)
        sheet.paste(thumb, (x, y))
    out = OUT_DIR / "_contact_sheet.jpg"
    sheet.save(out, "JPEG", quality=90)
    print(f"\n[콘택트시트] {out}")
    return out


def main():
    print(f"출력 디렉토리: {OUT_DIR}")
    paths = []
    for g in panorama["groups"]:
        code = g["group"]["code"]
        seq1 = next(b for b in g["base_cells"] if b["seq"] == 1)
        p = build_cover(code, seq1)
        paths.append(p)
    build_contact_sheet(paths)
    print("\n끝.")


if __name__ == "__main__":
    main()
