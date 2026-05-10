# -*- coding: utf-8 -*-
# PATCHED:utf8-stdout-v1
"""
시즌3 132권 표지 일괄 빌더 (본권 120 + 종합권 12).

컨셉 B: 기하 추상 + 그룹 모티프 + 깊이별 색 진행.
모티프 12개와 색 시스템은 _design_s3_pilot12 와 동일.
이번 빌더의 추가 기능:
  - depth(도입/심화-1/심화-2/통합) 에 따라 BG 명도·모티프 채도 단계 조정
  - 종합권 12권 (synthesis_cell) 별도 처리: 가장 깊은 톤 + "종합권" 표기
  - 모드 선택: --pilot-g01 (G01 10권만 콘택트 시트) | --all (132권 일괄)

출력:
  ~/Downloads/s3_covers/g##_seq##_cover.jpg  (본권 120)
  ~/Downloads/s3_covers/g##_omnibus_cover.jpg (종합권 12)
  ~/Downloads/s3_covers/_contact_g##.jpg       (그룹별 11장 시트)
  ~/Downloads/s3_covers/_contact_omnibus.jpg   (종합권 12장 시트)
"""
import argparse
import colorsys
import json
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
OUT_DIR = Path.home() / "Downloads" / "s3_covers"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LOGO_HORIZONTAL = ROOT / "logo_horizontal_gold.png"

panorama = json.loads((ROOT / "s3_panorama.json").read_text(encoding="utf-8"))


# ════════════════════════════════════════════════════════════════
# 색 시스템 — 그룹 베이스 (5튜플)
# ════════════════════════════════════════════════════════════════
def hex_to_rgb(h):
    h = h.lstrip("#")
    return (int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16))


GROUP_COLORS_HEX = {
    "G01": ("#1C2656", "#34467C", "#D4AF37", "#F4D77E", "#F0E1AA"),
    "G02": ("#0D0F18", "#1A1620", "#7A1428", "#B22A3C", "#D4576B"),
    "G03": ("#3D2418", "#5C3F2E", "#C9926B", "#E8C29E", "#F2DCC4"),
    "G04": ("#1C2656", "#3A1426", "#D4AF37", "#FFF1A0", "#B22A3C"),
    "G05": ("#1C2656", "#3D2418", "#D4AF37", "#F4D77E", "#C9926B"),
    "G06": ("#3A1A1A", "#1F1A1A", "#A0A8B0", "#E0E4EB", "#D9404C"),
    "G07": ("#2A3D2C", "#4A5C32", "#F4A574", "#F8C898", "#9DBC8A"),
    "G08": ("#3D3A52", "#5A5670", "#E0DCEA", "#F4F0FA", "#C8B8E4"),
    "G09": ("#0F1E5C", "#1B2A6E", "#FFF8E0", "#FFEFB8", "#D4AF37"),
    "G10": ("#0A0814", "#1A1226", "#9A7AB8", "#C4A8DC", "#5A2A7A"),
    "G11": ("#1A3A5C", "#2D5680", "#D4DCE6", "#F0F4FA", "#7DAED4"),
    "G12": ("#0F3A2E", "#1F5A48", "#C8DCD0", "#E8F0EA", "#5C9080"),
}


def base_colors(code):
    return tuple(hex_to_rgb(x) for x in GROUP_COLORS_HEX[code])


# ════════════════════════════════════════════════════════════════
# 깊이 진행 — depth → 색 조정 factor
# ════════════════════════════════════════════════════════════════
DEPTH_FACTORS = {
    "도입":   {"bg_dl": +0.18, "main_ds": -0.15, "main_dl": +0.05},
    "심화-1": {"bg_dl": +0.06, "main_ds":  0.00, "main_dl":  0.00},
    "심화-2": {"bg_dl": -0.08, "main_ds": +0.08, "main_dl": -0.03},
    "통합":   {"bg_dl": -0.20, "main_ds": +0.18, "main_dl": -0.06},
    # 종합권은 별도 — 본권 통합보다 한 단계 더 (synthesis 라벨)
    "synthesis": {"bg_dl": -0.28, "main_ds": +0.22, "main_dl": -0.08},
}


def adjust_color(rgb, dl=0.0, ds=0.0):
    r, g, b = rgb[0] / 255, rgb[1] / 255, rgb[2] / 255
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = max(0.0, min(1.0, l + dl))
    s = max(0.0, min(1.0, s + ds))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (int(r * 255), int(g * 255), int(b * 255))


def colors_for_depth(code, depth_label):
    base = base_colors(code)
    f = DEPTH_FACTORS.get(depth_label, DEPTH_FACTORS["심화-1"])
    return (
        adjust_color(base[0], dl=f["bg_dl"]),
        adjust_color(base[1], dl=f["bg_dl"]),
        adjust_color(base[2], dl=f["main_dl"], ds=f["main_ds"]),
        adjust_color(base[3], dl=f["main_dl"], ds=f["main_ds"]),
        adjust_color(base[4], dl=f["main_dl"] / 2, ds=f["main_ds"] / 2),
    )


# ════════════════════════════════════════════════════════════════
# 기본 유틸
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
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(color[0], color[1], color[2], alpha))
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


def paste_logo(img, target_w, cx, cy):
    logo = Image.open(LOGO_HORIZONTAL).convert("RGBA")
    ratio = target_w / logo.width
    new_h = int(logo.height * ratio)
    logo = logo.resize((target_w, new_h), Image.LANCZOS)
    img.paste(logo, (int(cx - target_w / 2), int(cy - new_h / 2)), logo)


# ════════════════════════════════════════════════════════════════
# 12 모티프 (이전 시안과 동일, _design_s3_pilot12 에서 가져옴)
# ════════════════════════════════════════════════════════════════
def m_g01_perichoresis(img, cx, cy, R, pal):
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 200, GLOW, intensity=70)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse([cx - R - 40, cy - R - 40, cx + R + 40, cy + R + 40], outline=(*PALE, 90), width=2)
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
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 180, MAIN, intensity=60)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    pts = [(cx, cy - R), (cx + R, cy), (cx, cy + R), (cx - R, cy)]
    ld.polygon(pts, fill=(*MAIN, 120))
    ld.line(pts + [pts[0]], fill=(*PALE, 220), width=4)
    crack = [(cx - R + 60, cy - R // 2), (cx - 30, cy - 60), (cx + 30, cy + 40),
             (cx - 20, cy + 120), (cx + R - 60, cy + R // 2 + 20)]
    ld.line(crack, fill=(*GLOW, 240), width=6)
    chips = [
        [(cx + R * 0.3, cy + R * 0.55), (cx + R * 0.55, cy + R * 0.45), (cx + R * 0.45, cy + R * 0.7)],
        [(cx - R * 0.55, cy - R * 0.2), (cx - R * 0.4, cy - R * 0.05), (cx - R * 0.65, cy + R * 0.05)],
    ]
    for c in chips:
        ld.polygon(c, fill=(*GLOW, 180))
    img.paste(layer, (0, 0), layer)


def m_g03_two_arcs(img, cx, cy, R, pal):
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 180, GLOW, intensity=60)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    off = int(R * 0.5)
    ld.ellipse([cx - off - R, cy - R, cx - off + R, cy + R], outline=(*MAIN, 220), width=8)
    ld.ellipse([cx + off - R, cy - R, cx + off + R, cy + R], outline=(*MAIN, 220), width=8)
    a = Image.new("RGBA", img.size, (0, 0, 0, 0)); aa = ImageDraw.Draw(a)
    aa.ellipse([cx - off - R, cy - R, cx - off + R, cy + R], fill=(255, 255, 255, 255))
    b = Image.new("RGBA", img.size, (0, 0, 0, 0)); bb = ImageDraw.Draw(b)
    bb.ellipse([cx + off - R, cy - R, cx + off + R, cy + R], fill=(255, 255, 255, 255))
    inter_mask = ImageChops.multiply(a, b)
    inter_color = Image.new("RGBA", img.size, (*PALE, 150))
    inter = Image.composite(inter_color, Image.new("RGBA", img.size, (0, 0, 0, 0)), inter_mask.split()[3])
    layer.paste(inter, (0, 0), inter)
    ld.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=(*GLOW, 240))
    img.paste(layer, (0, 0), layer)


def m_g04_x_lightning(img, cx, cy, R, pal):
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 200, MAIN, intensity=65)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    w_beam = 24
    for ang_deg in (45, -45):
        a = math.radians(ang_deg)
        dx, dy = math.cos(a) * R, math.sin(a) * R
        nx, ny = -math.sin(a), math.cos(a)
        x1, y1 = cx - dx, cy - dy
        x2, y2 = cx + dx, cy + dy
        pts = [(x1 + nx * w_beam, y1 + ny * w_beam), (x2 + nx * w_beam, y2 + ny * w_beam),
               (x2 - nx * w_beam, y2 - ny * w_beam), (x1 - nx * w_beam, y1 - ny * w_beam)]
        ld.polygon(pts, fill=(*MAIN, 230))
    bolt = [(cx - R * 0.15, cy - R), (cx + R * 0.05, cy - R * 0.2),
            (cx - R * 0.1, cy - R * 0.15), (cx + R * 0.2, cy + R)]
    bolt_w = [(cx - R * 0.05, cy - R), (cx + R * 0.15, cy - R * 0.2),
              (cx + 0, cy - R * 0.15), (cx + R * 0.3, cy + R)]
    ld.polygon(list(bolt) + list(reversed(bolt_w)), fill=(*GLOW, 240))
    ld.line(bolt, fill=(*PALE, 240), width=3)
    img.paste(layer, (0, 0), layer)


def m_g05_cross_pillar(img, cx, cy, R, pal):
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 220, MAIN, intensity=80)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for i in range(8):
        w = 60 - i * 4
        a = 220 - i * 18
        x1 = cx - w; x2 = cx + w
        ld.polygon([(x1, cy - R - 100), (x2, cy - R - 100),
                    (x2 + 20, cy + R + 50), (x1 - 20, cy + R + 50)],
                   fill=(*PALE, max(40, a)))
    h_beam = 28
    ld.polygon([(cx - R, cy - h_beam), (cx + R, cy - h_beam),
                (cx + R, cy + h_beam), (cx - R, cy + h_beam)], fill=(*MAIN, 230))
    ld.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], fill=(*GLOW, 220))
    img.paste(layer, (0, 0), layer)


def m_g06_shield_arrow(img, cx, cy, R, pal):
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 180, MAIN, intensity=55)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    sh = [(cx - R * 0.7, cy - R * 0.7), (cx + R * 0.7, cy - R * 0.7),
          (cx + R * 0.7, cy + R * 0.1), (cx, cy + R * 0.95),
          (cx - R * 0.7, cy + R * 0.1)]
    ld.polygon(sh, fill=(*MAIN, 170))
    ld.line(sh + [sh[0]], fill=(*PALE, 230), width=5)
    ld.line([(cx, cy - R * 0.7), (cx, cy + R * 0.95)], fill=(*PALE, 200), width=3)
    arr_start = (cx - R * 1.3, cy - R * 1.2); arr_tip = (cx - R * 0.15, cy - R * 0.05)
    ld.line([arr_start, arr_tip], fill=(*GLOW, 240), width=8)
    head = [(arr_tip[0], arr_tip[1]), (arr_tip[0] - 30, arr_tip[1] - 50),
            (arr_tip[0] + 50, arr_tip[1] - 30)]
    ld.polygon(head, fill=(*GLOW, 240))
    img.paste(layer, (0, 0), layer)


def m_g07_leaf_on_hand(img, cx, cy, R, pal):
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 180, GLOW, intensity=60)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    palm_y = cy + R * 0.4
    ld.chord([cx - R * 0.7, palm_y - R * 0.5, cx + R * 0.7, palm_y + R * 0.5],
             0, 180, fill=(*MAIN, 200), outline=(*PALE, 230))
    ld.rectangle([cx - R * 0.45, palm_y, cx + R * 0.45, palm_y + R * 0.45],
                 fill=(*MAIN, 200), outline=(*PALE, 220), width=4)
    for i, dx in enumerate([-0.5, -0.27, -0.05, 0.18, 0.42]):
        fx = cx + R * dx; fy = palm_y - R * 0.2
        h = R * (0.55 if i == 2 else 0.5 if i in (1, 3) else 0.4)
        ld.ellipse([fx - 18, fy - h, fx + 18, fy], fill=(*MAIN, 200), outline=(*PALE, 220))
    leaf_cx, leaf_cy = cx, cy - R * 0.15
    leaf = [(leaf_cx, leaf_cy - R * 0.65), (leaf_cx + R * 0.3, leaf_cy - R * 0.2),
            (leaf_cx + R * 0.18, leaf_cy + R * 0.15), (leaf_cx, leaf_cy),
            (leaf_cx - R * 0.18, leaf_cy + R * 0.15), (leaf_cx - R * 0.3, leaf_cy - R * 0.2)]
    ld.polygon(leaf, fill=(*GLOW, 220))
    ld.line(leaf + [leaf[0]], fill=(*PALE, 230), width=3)
    ld.line([(leaf_cx, leaf_cy - R * 0.65), (leaf_cx, leaf_cy + R * 0.0)], fill=(*MAIN, 220), width=3)
    img.paste(layer, (0, 0), layer)


def m_g08_concentric(img, cx, cy, R, pal):
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 200, GLOW, intensity=75)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for i in range(8, 0, -1):
        r = int(R * i / 8)
        alpha = int(50 + (8 - i) * 22)
        col = MAIN if i % 2 == 0 else PALE
        ld.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*col, alpha), width=4)
    ld.ellipse([cx - 28, cy - 28, cx + 28, cy + 28], fill=(*GLOW, 240))
    ld.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=(255, 255, 255, 255))
    img.paste(layer, (0, 0), layer)


def m_g09_crown_light(img, cx, cy, R, pal):
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 200, MAIN, intensity=80)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for i in range(12):
        a = math.radians(-90 + i * 30)
        x2 = cx + (R + 100) * math.cos(a); y2 = cy + (R + 100) * math.sin(a)
        ld.line([(cx, cy), (x2, y2)], fill=(*GLOW, 130), width=3)
    crown_y = cy + R * 0.1
    crown_pts = [(cx - R * 0.7, crown_y + R * 0.4), (cx - R * 0.7, crown_y),
                 (cx - R * 0.45, crown_y - R * 0.3), (cx - R * 0.2, crown_y),
                 (cx, crown_y - R * 0.5), (cx + R * 0.2, crown_y),
                 (cx + R * 0.45, crown_y - R * 0.3), (cx + R * 0.7, crown_y),
                 (cx + R * 0.7, crown_y + R * 0.4)]
    ld.polygon(crown_pts, fill=(*GLOW, 230))
    ld.line(crown_pts + [crown_pts[0]], fill=(*PALE, 240), width=5)
    ld.ellipse([cx - 22, crown_y - 30, cx + 22, crown_y + 14], fill=(*MAIN, 240))
    img.paste(layer, (0, 0), layer)


def m_g10_broken_wing(img, cx, cy, R, pal):
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 180, MAIN, intensity=60)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    L_wing = [(cx - 20, cy - R * 0.3), (cx - R * 0.9, cy - R * 0.5),
              (cx - R * 1.1, cy - R * 0.05), (cx - R * 0.8, cy + R * 0.3),
              (cx - 30, cy + R * 0.2)]
    ld.polygon(L_wing, fill=(*PALE, 200), outline=(*PALE, 240))
    for k in [0.2, 0.4, 0.6, 0.8]:
        x = cx - R * k - 50
        ld.line([(x, cy - R * 0.3), (x, cy + R * 0.15)], fill=(*MAIN, 200), width=2)
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
    ld.line([(cx + 30, cy - R * 0.4), (cx + R * 0.55, cy + R * 0.1)], fill=(*MAIN, 220), width=4)
    img.paste(layer, (0, 0), layer)


def m_g11_parallel_arcs(img, cx, cy, R, pal):
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 180, GLOW, intensity=70)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    spread = R * 0.35
    for col, alpha, off, w in [(MAIN, 230, -spread, 12), (PALE, 230, +spread, 12)]:
        pts = []
        for k in range(60):
            t = k / 59
            y = cy - R * 0.95 + R * 1.9 * t
            x = cx + off + (R * 0.18) * math.sin(t * math.pi)
            pts.append((x, y))
        ld.line(pts, fill=(*col, alpha), width=w)
    for k in range(7):
        t = (k + 0.5) / 7
        y = cy - R * 0.85 + R * 1.7 * t
        ld.ellipse([cx - 6, y - 6, cx + 6, y + 6], fill=(*GLOW, 220))
    img.paste(layer, (0, 0), layer)


def m_g12_wind_leaf(img, cx, cy, R, pal):
    _, _, MAIN, GLOW, PALE = pal
    add_glow(img, cx, cy, R + 180, GLOW, intensity=60)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for i, (offset_y, alpha, w) in enumerate([
        (-R * 0.5, 200, 6), (-R * 0.2, 220, 8), (+R * 0.1, 200, 6), (+R * 0.4, 180, 5),
    ]):
        pts = []
        for k in range(80):
            t = k / 79
            x = cx - R + 2 * R * t
            y = cy + offset_y + math.sin(t * math.pi * 2 + i * 0.4) * (R * 0.12)
            pts.append((x, y))
        ld.line(pts, fill=(*PALE, alpha), width=w)
    leaf_cx, leaf_cy = cx + R * 0.15, cy
    leaf = [(leaf_cx, leaf_cy - R * 0.4), (leaf_cx + R * 0.25, leaf_cy - R * 0.15),
            (leaf_cx + R * 0.18, leaf_cy + R * 0.12), (leaf_cx, leaf_cy + R * 0.05),
            (leaf_cx - R * 0.18, leaf_cy + R * 0.12), (leaf_cx - R * 0.25, leaf_cy - R * 0.15)]
    ld.polygon(leaf, fill=(*MAIN, 230))
    ld.line(leaf + [leaf[0]], fill=(*PALE, 240), width=3)
    ld.line([(leaf_cx, leaf_cy - R * 0.4), (leaf_cx, leaf_cy + R * 0.05)], fill=(*GLOW, 220), width=3)
    img.paste(layer, (0, 0), layer)


MOTIF = {
    "G01": m_g01_perichoresis, "G02": m_g02_broken_diamond, "G03": m_g03_two_arcs,
    "G04": m_g04_x_lightning, "G05": m_g05_cross_pillar, "G06": m_g06_shield_arrow,
    "G07": m_g07_leaf_on_hand, "G08": m_g08_concentric, "G09": m_g09_crown_light,
    "G10": m_g10_broken_wing, "G11": m_g11_parallel_arcs, "G12": m_g12_wind_leaf,
}


# ════════════════════════════════════════════════════════════════
# 표지 빌더 (본권/종합권 통합)
# ════════════════════════════════════════════════════════════════
WHITE     = (252, 251, 245)
WHITE_DIM = (220, 218, 210)


def build_cover(code, title, hint_or_subtitle, side_label, depth_label, out_path, seed_extra=0):
    """side_label: '1권', '2권', ..., '종합권'.  depth_label: panorama depth or 'synthesis'."""
    pal = colors_for_depth(code, depth_label)
    BG_TOP, BG_BOT, MAIN, GLOW, PALE = pal

    W, H = 1400, 2100
    img = vertical_gradient(W, H, BG_TOP, BG_BOT).convert("RGBA")
    starfield(img, n=220, seed=(hash(code) + seed_extra) % 1000)

    cx, cy = W // 2, 920
    R = 360
    MOTIF[code](img, cx, cy, R, pal)

    img = img.convert("RGB")
    d = ImageDraw.Draw(img)

    # 상단
    text_centered(d, 130, "시즌 3", font(28), GLOW, W)
    d.line([(W // 2 - 60, 175), (W // 2 + 60, 175)], fill=PALE, width=1)
    text_centered(d, 195, f"{code} · {side_label}", font(24, bold=True), WHITE_DIM, W)

    # 본문 텍스트 — 제목이 길면 폰트 약간 줄임
    title_size = 108 if len(title) <= 10 else (92 if len(title) <= 14 else 78)
    text_centered(d, 1560, title, font(title_size, bold=True), WHITE, W)
    if hint_or_subtitle:
        sub_size = 50 if len(hint_or_subtitle) <= 22 else 40
        text_centered(d, 1730, hint_or_subtitle, font(sub_size), PALE, W)

    text_centered(d, 1860, "AI, 박헌근", font(40, bold=True), WHITE_DIM, W)

    d.rectangle([28, 28, W - 28, H - 28], outline=PALE, width=2)
    d.rectangle([40, 40, W - 40, H - 40], outline=MAIN, width=1)

    img = img.convert("RGBA")
    paste_logo(img, target_w=360, cx=W // 2, cy=2000)
    img = img.convert("RGB")

    img.save(out_path, "JPEG", quality=92)


# ════════════════════════════════════════════════════════════════
# 콘택트 시트 (그룹별 + 종합권)
# ════════════════════════════════════════════════════════════════
def build_contact_sheet(paths, title, out_path, cols=None):
    n = len(paths)
    if cols is None:
        cols = 5 if n >= 10 else 4
    rows = (n + cols - 1) // cols
    cell_w, cell_h = 320, 480
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


# ════════════════════════════════════════════════════════════════
# 빌드 모드
# ════════════════════════════════════════════════════════════════
def build_group_books(code, group):
    """그룹의 본권 10권 빌드."""
    paths = []
    for b in group["base_cells"]:
        seq = b["seq"]
        out = OUT_DIR / f"{code.lower()}_seq{seq:02d}_cover.jpg"
        build_cover(code, b["title"], b.get("hint", ""), f"{seq}권", b["depth"], out, seed_extra=seq)
        paths.append(out)
        print(f"  [{code} seq{seq:02d}] {b['title'][:25]:25s}  depth={b['depth']}")
    return paths


def build_group_omnibus(code, group):
    """그룹의 종합권 1권 빌드."""
    s = group["synthesis_cell"]
    out = OUT_DIR / f"{code.lower()}_omnibus_cover.jpg"
    build_cover(code, s["title"], s.get("subtitle", ""), "종합권", "synthesis", out, seed_extra=99)
    print(f"  [{code} 종합권] {s['title'][:25]}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["pilot-g01", "all"], default="pilot-g01")
    args = ap.parse_args()

    if args.mode == "pilot-g01":
        print("=== G01 10권 깊이 진행 시범 ===")
        g = next(g for g in panorama["groups"] if g["group"]["code"] == "G01")
        paths = build_group_books("G01", g)
        build_contact_sheet(paths, "G01 삼위일체 — 본권 10권 깊이 진행 시안",
                            OUT_DIR / "_contact_g01_pilot.jpg", cols=5)
        print("\n끝.")
        return

    # all: 132권
    print("=== 시즌 3 132권 표지 일괄 빌드 ===")
    all_book_paths = []
    omnibus_paths = []
    for g in panorama["groups"]:
        code = g["group"]["code"]
        print(f"\n[{code}] {g['group']['theme_name']}")
        bp = build_group_books(code, g)
        op = build_group_omnibus(code, g)
        all_book_paths.extend(bp)
        omnibus_paths.append(op)
        # 그룹별 콘택트 시트 (본권 10 + 종합권 1 = 11장)
        build_contact_sheet(bp + [op],
                            f"{code} {g['group']['theme_name']} — 본권 10 + 종합권 1",
                            OUT_DIR / f"_contact_{code.lower()}.jpg", cols=4)
    # 종합권 12장 콘택트 시트
    build_contact_sheet(omnibus_paths, "시즌 3 — 종합권 12권",
                        OUT_DIR / "_contact_omnibus.jpg", cols=4)

    print(f"\n[완료] 총 {len(all_book_paths)} 본권 + {len(omnibus_paths)} 종합권 = {len(all_book_paths) + len(omnibus_paths)}장")


if __name__ == "__main__":
    main()
