# -*- coding: utf-8 -*-
"""
종합책 표지의 저자 텍스트 patch.
기존 "박헌근" 영역을 배경 색으로 가린 뒤 "AI · 박헌근"으로 다시 그림.

_make_omnibus_cover.py와 동일한 좌표/폰트/색상 사용:
  position: (W//2 - tw//2, H - 460)
  font:     Malgun Gothic Bold 56
  color:    IVORY (244, 233, 203)
  bg:       표지 좌측 빈 공간 sample (각 표지별 추출)

사용:
  python _patch_omnibus_author.py preview tmp/s1_omnibus_cover.jpg
        → tmp/s1_omnibus_cover_patched.jpg 생성 (시범)
  python _patch_omnibus_author.py apply
        → tmp/*_omnibus_cover.jpg 11장 in-place patch
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

NEW_AUTHOR = "AI, 박헌근"
FONT_SIZE = 56
TEXT_COLOR = (244, 233, 203)  # IVORY (= _make_omnibus_cover.py)


def find_font(size):
    for p in [
        "C:/Windows/Fonts/malgunbd.ttf",
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/NanumGothicBold.ttf",
        "C:/Windows/Fonts/NanumGothic.ttf",
    ]:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def patch_one(src_path: Path, dst_path: Path):
    img = Image.open(src_path).convert("RGB")
    W, H = img.size

    # 빈 영역에서 배경 색 추출 (좌측 상단 영역 — 거의 항상 배경 색)
    bg_color = img.getpixel((W // 4, H - 430))

    draw = ImageDraw.Draw(img)
    font = find_font(FONT_SIZE)

    # 기존 "박헌근" 영역 가리기 — 충분한 여유 박스
    box_w = 280
    box_h = 100
    box_top = H - 480
    box = (W // 2 - box_w // 2, box_top, W // 2 + box_w // 2, box_top + box_h)
    draw.rectangle(box, fill=bg_color)

    # 새 텍스트 그리기 — _make_omnibus_cover.py 와 동일한 baseline
    bbox = draw.textbbox((0, 0), NEW_AUTHOR, font=font)
    tw = bbox[2] - bbox[0]
    x = (W - tw) // 2
    y = H - 460
    draw.text((x, y), NEW_AUTHOR, font=font, fill=TEXT_COLOR)

    img.save(dst_path, "JPEG", quality=92, optimize=True)
    return bg_color


def main():
    args = sys.argv[1:]
    if not args:
        print("사용법: python _patch_omnibus_author.py [preview <파일> | apply]")
        sys.exit(1)

    cmd = args[0]
    if cmd == "preview":
        if len(args) < 2:
            print("preview는 파일 인자 필요")
            sys.exit(1)
        src = Path(args[1])
        dst = src.with_name(src.stem + "_patched" + src.suffix)
        bg = patch_one(src, dst)
        print(f"[시범] {src} → {dst}")
        print(f"  배경 색 sample: RGB{bg}")

    elif cmd == "apply":
        targets = sorted(Path("tmp").glob("*_omnibus_cover.jpg"))
        if not targets:
            print("tmp/*_omnibus_cover.jpg 파일이 없음")
            sys.exit(1)
        for src in targets:
            bg = patch_one(src, src)
            print(f"[패치] {src.name}  bg=RGB{bg}")
        print(f"\n총 {len(targets)}장 patch 완료")

    else:
        print(f"알 수 없는 명령: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
