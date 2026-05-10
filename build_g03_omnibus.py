# -*- coding: utf-8 -*-
"""
G03 10권 종합책 "겨자씨와 산" epub 빌더.

입력:
  - batch_books_g03_omnibus.json (메타·4부 구조)
  - tmp/g03_omnibus_extracted.json (10권 본문 추출본)
  - G03 epub 중 한 권 (CSS 추출용)

출력:
  - ~/Downloads/전자책/겨자씨와_산_YYYYMMDD_종합책.epub

구조 (spine 순서):
  cover → copyright → toc → preface
  → part01_intro → [b01_front·b01_ch01~07] × 2권 (1부)
  → part02_intro → [b03_front·b03_ch01~07] × 3권 (2부)
  → part03_intro → [b06_front·b06_ch01~07] × 3권 (3부)
  → part04_intro → [b09_front·b09_ch01~07] × 2권 (4부)
  → epilogue → publisher
"""
import base64
import io
import json
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from qr_util import make_qr_png_bytes, catalog_url

# 안전망: 본권 EPUB 본문을 합칠 때 마크다운 펜스(```html ... ```)가
# 살아 있으면 종합책에 그대로 박힌다. ZIP 쓰기 직전 한 번 더 제거.
_FENCE_OPEN  = re.compile(r'(?m)^[ \t]*```[ \t]*[a-zA-Z][a-zA-Z0-9_-]*[ \t]*\r?\n?')
_FENCE_CLOSE = re.compile(r'(?m)^[ \t]*```[ \t]*\r?\n?')
_FENCE_INLINE = re.compile(r'```[a-zA-Z]*')


def _strip_md_fences(text: str) -> str:
    if '```' not in text:
        return text
    text = _FENCE_OPEN.sub('', text)
    text = _FENCE_CLOSE.sub('', text)
    text = _FENCE_INLINE.sub('', text)
    text = text.replace('```', '')
    return text


sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PROJECT = Path(__file__).parent
META_PATH = PROJECT / "batch_books_g03_omnibus.json"
EXTRACT_PATH = PROJECT / "tmp" / "g03_omnibus_extracted.json"
SAMPLE_EPUB = Path.home() / "Downloads" / "전자책" / "의심을_넘어선_확신_20260418.epub"
OUT_DIR = Path.home() / "Downloads" / "전자책"
OUT_BACKUP_DIR = PROJECT / "tmp"  # 보조 사본


def get_css():
    """샘플 epub에서 CSS 추출."""
    with zipfile.ZipFile(SAMPLE_EPUB, "r") as z:
        return z.read("OEBPS/styles/style.css").decode("utf-8")


def get_cover_image():
    """전용 종합책 표지 사용 (없으면 샘플로 폴백)."""
    custom = PROJECT / "tmp" / "g03_omnibus_cover.jpg"
    if custom.exists():
        return custom.read_bytes()
    with zipfile.ZipFile(SAMPLE_EPUB, "r") as z:
        return z.read("OEBPS/images/cover.jpg")


def get_logo_png():
    """로고 PNG 읽기 (판권지 등 본문 삽입용)."""
    logo = PROJECT / "logo_horizontal_black.png"
    if logo.exists():
        return logo.read_bytes()
    return None


def xhtml_doc(title: str, body_inner: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ko">
<head><meta charset="UTF-8"/><title>{title}</title>
<link rel="stylesheet" type="text/css" href="styles/style.css"/></head>
<body>{body_inner}</body>
</html>"""


def build_cover_xhtml(title: str, subtitle: str, cover_bytes: bytes) -> str:
    # base64 data URI 인라인 (epub.js iframe 호환).
    # 옛 SVG <image xlink:href="images/cover.jpg"> 방식은 epub.js 의 blob URL
    # rewrite 가 SVG 내부 xlink:href 를 따라가지 못해 책방 reader 에서 빈 페이지로 떴음.
    cover_b64 = base64.b64encode(cover_bytes).decode("ascii")
    body = f"""
<style>
  html, body {{ margin:0; padding:0; width:100%; height:100%; background:#FFFFFF; }}
  .cover-wrap {{ width:100%; height:100%; display:flex; align-items:center; justify-content:center; padding:0; box-sizing:border-box; }}
  img {{ display:block; max-width:100%; max-height:100vh; width:auto; height:auto; object-fit:contain; }}
</style>
<div class="cover-wrap">
<img src="data:image/jpeg;base64,{cover_b64}" alt="표지"/>
</div>
"""
    return xhtml_doc("표지", body)


# PATCHED:qr-copyright-v1
def build_copyright_xhtml(meta: dict, today_iso: str) -> str:
    body = f"""<div style="padding:2em 1.5em">
<div style="padding:1em;font-size:0.88em;color:#555;line-height:2">
  <div style="text-align:center;margin-bottom:2em">
    <img src="images/logo.png" alt="AI 시대 영성" style="max-width:60%;height:auto"/>
  </div>
  <h2 style="font-size:1em;color:#0F1E3C;margin-bottom:1.5em;border-bottom:1px solid #C8B99A;padding-bottom:0.5em">판권 정보</h2>
  <p><strong>제목</strong>　{meta['title']}</p>
  <p><strong>부제</strong>　{meta['subtitle']}</p>
  <p><strong>저자</strong>　{meta['author']}</p>
  <p><strong>출판사</strong>　{meta['publisher']}</p>
  <p><strong>출판일</strong>　{today_iso}</p>
  <p><strong>ISBN</strong>　{meta['isbn'] or '(발급 대기 중)'}</p>
  <p><strong>구성</strong>　G03 10권 종합책 (4부 70장)</p>
  <div style="margin-top:1.6em;display:flex;align-items:center;gap:1em;padding:0.9em 1em;background:#FAF7EE;border:1px solid #C8B99A;border-radius:6px">
    <img src="images/qr.png" alt="책방 QR" style="width:64px;height:64px;flex-shrink:0;display:block"/>
    <div style="font-size:0.82em;color:#555;line-height:1.5">
      <div style="color:#0F1E3C;font-weight:700;margin-bottom:0.2em;letter-spacing:0.03em">전자책 책방 바로가기</div>
      <div style="color:#777">QR 스캔 → 121권 진열장</div>
      <div style="color:#888;font-size:0.92em;margin-top:0.15em">ai-spirituality-books.vercel.app</div>
    </div>
  </div>
  <div style="margin-top:2em;font-size:0.85em;color:#888;border-top:1px solid #C8B99A;padding-top:1em">
    <p>Copyright © 2026 박헌근. All rights reserved.</p>
    <p>이 책은 100권 영성 시리즈 G03(단단한 믿음) 10권의 본문을 거의 그대로 4부 구조로 재편집하여 한 권으로 묶은 종합본입니다.</p>
    <p>각 권의 원본 ISBN 및 출간 정보는 본문 권별 도입 페이지에 명기되어 있습니다.</p>
  </div>
</div></div>"""
    return xhtml_doc("판권", body)


def build_preface_xhtml() -> str:
    body = """<div style="padding:2em 1.5em;line-height:1.9;font-size:1em;color:#222">
<h2 style="color:#0F1E3C;border-bottom:1px solid #C8B99A;padding-bottom:0.5em">여는 글</h2>
<h3 style="color:#0F1E3C;margin-top:1.5em">한 알의 믿음으로 산 앞에 서다</h3>
<p>예수께서 말씀하셨습니다. 너희에게 겨자씨 한 알만 한 믿음이 있으면 이 산을 명하여 여기서 저기로 옮기라 하여도 옮길 것이라고. 한 알의 작음과 한 산의 큼이 한 문장 안에서 만납니다. 한 알이 너무 작아 보이고, 한 산은 너무 커 보입니다. 그러나 그 한 알의 믿음이 진짜라면, 산은 흔들립니다.</p>
<p>이 책은 그 한 마디 위에서 시작합니다. 우리의 믿음이 작다고 느껴질 때, 시험 한복판에서 흔들릴 때, 두려움이 마음을 짓누를 때, 그리고 마지막 순간을 향해 발걸음을 옮길 때 — 그 모든 자리에서 우리는 한 가지를 다시 묻습니다. <em>믿음이란 무엇인가, 그리고 어떻게 단단해지는가.</em></p>
<p>이 책은 100권 영성 시리즈의 세 번째 그룹 G03을 한 권으로 묶은 종합본입니다. 의심에서 확신으로, 시험에서 자라남으로, 두려움에서 담대함으로, 그리고 흔들림에서 흔들리지 않음으로 — 그리스도인의 믿음이 단단해지는 결을 열 갈래로 펼쳐 놓았습니다. 열 권 각각의 본문을 거의 그대로 유지하면서, 그 사이를 흐르고 있던 결을 네 갈래로 모았습니다.</p>
<p>네 갈래는 한 영혼이 통과해야 하는 한 길의 네 굽이입니다. <strong>1부 — 믿음의 시작</strong>은 의심을 넘어 보이지 않는 것을 보는 자리에서 시작하고, <strong>2부 — 자라는 믿음</strong>은 시험과 작음과 기적을 통해 한 알이 산이 되기까지의 결을 봅니다. <strong>3부 — 살아내는 믿음</strong>은 두려움·행함·동행자들 앞에서 믿음이 손으로 흐르는 자리를 짚고, <strong>4부 — 끝까지 가는 발걸음</strong>은 마지막 때의 자세와 흔들리지 않는 닻으로 한 영혼의 끝을 응시합니다.</p>
<p>이 책은 믿음에 대한 모든 질문에 답하지 않습니다. 다만 흔들리는 자리에서 흔들리지 않는 자리로 옮겨 갈 수 있는 한 결, 곧 단단해지는 묵상의 자리로 한 사람을 데려가려 합니다. 답을 서두르기보다 호흡을 가다듬는 자리, 작은 믿음 하나가 산 앞에서 자세를 가다듬는 자리. 이 책이 그런 자리가 되어 드린다면, G03 열 권을 한 권으로 묶은 의미는 충분할 것입니다.</p>
<p>한 번에 다 읽어내실 책이 아닙니다. 한 장씩, 한 묵상씩 호흡을 따라 가져가시면 됩니다. 이제 첫 장을 펼쳐 주십시오. 한 알의 믿음을 손에 쥔 채로, 그러나 산을 응시하는 자세로, 한 호흡씩 함께 걸어가 봅시다.</p>
</div>"""
    return xhtml_doc("여는 글", body)


PART_INTROS = {
    1: {
        "headline": "보이지 않는 것을 보는 자리",
        "paragraphs": [
            "믿음은 어디서 시작됩니까. 흥분된 결심에서도 아니고, 종교적 분위기에 휩쓸리는 자리에서도 아닙니다. 믿음은 한 사람이 자기 의심을 정직하게 마주하는 자리, 그리고 보이지 않는 실재를 향해 눈을 뜨는 자리에서 비로소 시작됩니다.",
            "성경은 의심을 적으로 그리지 않습니다. 도마는 부활하신 예수 앞에서 자기 의심을 가져왔고, 그 자리에서 가장 깊은 고백이 흘러나왔습니다. 의심 자체가 죄가 아니라, 의심을 가진 채 그분을 회피하는 자세가 죄입니다. 정직한 의심은 오히려 깊은 확신의 문이 됩니다.",
            "그리고 믿음은 본다는 일입니다. 보이는 것 너머의 실재를, 자외선처럼 우리 눈에 보이지 않지만 분명히 존재하는 한 세계를 보는 일입니다. 히브리서 11장이 말하는 믿음이란 바라는 것들의 실상이며 보지 못하는 것들의 증거입니다. 관측자가 세계를 바꾸듯, 믿는 자가 세계를 바꿉니다.",
            "이 부의 두 권은 믿음의 시작이라는 그 자리를 차례로 응시합니다. 「의심을 넘어선 확신」은 의심·도마·이뭐꼬·불 속의 금을 거치며 거짓 확신과 진짜 확신을 분별하고, 「보이지 않는 것을 보는 눈」은 자외선·차원의 문·소망의 증거를 통해 보이지 않는 실재를 응시합니다.",
            "믿음의 시작은 결심이 아니라 시선입니다. 의심을 정직하게 통과한 시선과 보이지 않는 것을 보는 시선이 만나는 자리에서, 한 영혼의 믿음이 첫 걸음을 내디딥니다.",
        ],
        "guides": [
            "내 안의 의심은 회피해야 할 적인가, 아니면 더 깊은 확신으로 가는 문인가.",
            "보이는 것 너머의 실재를 보는 눈을, 나는 어떤 자리에서 길러 가고 있는가.",
            "맹신·광신·불신 사이에서, 나는 어느 결을 살아가고 있는가.",
            "이 부를 읽으며, 의심을 통과한 자의 시선과 보이지 않는 것을 보는 자의 시선이 어떻게 한 결로 만나는가에 주목해 보십시오.",
        ],
    },
    2: {
        "headline": "한 알이 산이 되기까지",
        "paragraphs": [
            "한 알의 겨자씨가 큰 나무가 되기까지는 시간이 필요합니다. 그리고 그 자라남은 결코 평탄한 자리에서 일어나지 않습니다. 시험과 압력의 한복판에서, 작음의 자리에서, 그리고 기적이라 부르는 한 순간들의 결에서 한 알의 믿음이 산이 되어 갑니다.",
            "성경은 시험을 피해야 할 재난으로 그리지 않습니다. 야고보는 시험을 만나거든 온전히 기쁘게 여기라고 말합니다. 압력 속에서 다이아몬드가 빚어지듯, 시험 속에서 인내가 자라고 인내가 자라는 자리에서 믿음이 단단해집니다. 시험의 자리는 결코 우연이 아니라 연단의 자리입니다.",
            "작음을 두려워하지 마십시오. 겨자씨 한 알의 비밀은 크기가 아니라 대상에 있습니다. 작은 믿음이라도 살아 계신 하나님을 향하면 산이 흔들립니다. 큰 믿음 같아 보여도 자기 자신을 향하면 작은 언덕도 옮기지 못합니다.",
            "기적은 예외가 아닙니다. 성경은 기적이 비정상적 사건이 아니라 살아 계신 하나님의 서명이라고 증언합니다. 우리의 기대가 너무 낮아서 기적을 기적으로 보지 못할 때가 많을 뿐입니다. 씨앗 속에 숲이 숨겨져 있듯, 한 영혼의 일상 속에 이미 기적의 결이 흐르고 있습니다.",
            "이 부의 세 권은 한 알이 산이 되기까지의 결을 차례로 펼칩니다. 「시험 속에서 자라는 믿음」은 압력과 인내를, 「작은 믿음의 큰 힘」은 겨자씨와 산의 비밀을, 「기적은 지금도 일어난다」는 기적을 기적으로 보는 눈을 다룹니다.",
            "한 알에서 산까지의 거리는 멀어 보이지만, 그 사이에는 한 결의 자라남이 있을 뿐입니다.",
        ],
        "guides": [
            "내가 지금 통과하는 시험은 도망쳐야 할 자리인가, 아니면 인내를 자라게 하는 연단의 자리인가.",
            "내 믿음의 크기가 작다고 느낄 때, 나는 그 작음을 어디로 가져가고 있는가.",
            "기적이 예외가 아니라 일상에 흐르는 결이라면, 나는 어떤 자리에서 그 결을 알아보고 있는가.",
            "이 부를 읽으며, 한 알의 믿음이 산이 되어 가는 결을 따라가 보십시오.",
        ],
    },
    3: {
        "headline": "믿음이 손으로 흐르는 자리",
        "paragraphs": [
            "믿음은 머리에서 끝나지 않습니다. 가슴을 거쳐 손으로 흘러야 비로소 살아있는 믿음입니다. 야고보는 행함이 없는 믿음은 죽은 믿음이라고 말했습니다. 그 말은 믿음과 행함이 두 자리가 아니라, 한 결의 두 측면임을 가리킵니다.",
            "두려움은 행함을 가로막는 가장 큰 걸림돌입니다. 두려움 앞에서 우리의 손은 굳어지고 발걸음은 멈춥니다. 그러나 성경은 완전한 사랑이 두려움을 쫓아낸다고 말합니다. 빛이 들어오면 어둠이 사라지듯, 사랑받는 자의 자리에서 두려움은 자기 자리를 잃습니다.",
            "행함의 결은 다양합니다. 듣기는 속히 행하기는 즉시, 혀를 다스리는 일, 위로부터 난 지혜로 살아가는 일, 가난한 자를 돌아보는 일, 그리고 의인의 간절한 기도를 드리는 일. 이 모든 결은 결국 한 가지로 모입니다. 믿음이 손으로 흐른다는 것입니다.",
            "그리고 우리는 혼자 걷지 않습니다. 구름같은 증인들이 우리 앞에 먼저 걸어갔습니다. 아벨·에녹·노아·아브라함·모세·다윗·이름 없는 증인들의 발자국이 우리 발 앞에 놓여 있습니다. 그 발자국을 따라 걷는 것이 곧 믿음의 행함입니다.",
            "이 부의 세 권은 살아내는 믿음의 결을 차례로 짚습니다. 「두려움 없는 믿음」은 두려움을 넘어 담대함으로 가는 길을, 「믿음과 행함의 균형」은 죽은 믿음과 살아 있는 믿음의 차이를, 「믿음의 선배들」은 구름같은 증인들의 발자국을 다룹니다.",
            "믿음이 손으로 흐르는 자리에서만 한 사람의 일상이 다시 빚어집니다.",
        ],
        "guides": [
            "내 안의 두려움이 행함을 가로막는 자리는 어디이며, 나는 그 두려움을 어디로 가져가고 있는가.",
            "내 믿음은 머리에 머무는가, 가슴을 거쳐 손까지 흐르고 있는가.",
            "구름같은 증인들의 발자국 위에서, 나는 다음 발걸음을 어떻게 옮기고 있는가.",
            "이 부를 읽으며, 믿음이 손으로 흐르는 결을 따라가 보십시오.",
        ],
    },
    4: {
        "headline": "끝까지 가는 발걸음",
        "paragraphs": [
            "시작이 좋은 사람은 많지만, 끝까지 가는 사람은 적습니다. 신앙도 마찬가지입니다. 한 알의 믿음으로 시작해 산을 옮기는 능력에 이르렀어도, 그 발걸음을 끝까지 가져가지 못하면 모든 결은 흐려집니다. 끝까지 가는 발걸음, 그것이 단단한 믿음의 마지막 결입니다.",
            "성경은 마지막 때를 분명히 가리킵니다. 깨어 있으라, 충성된 종이 되라, 환난 중에 인내하라, 거룩함으로 준비하라. 이 부르심은 두려움의 부르심이 아니라 소망의 부르심입니다. 마지막 때를 바라보는 자의 눈은 두려워하는 자의 눈이 아니라 마라나타를 외치는 자의 눈입니다.",
            "그리고 한 영혼에게는 닻이 필요합니다. 폭풍이 일면 흔들리지 않는 사람은 없습니다. 감정의 파도, 의심의 풍랑, 시대의 격동이 끊임없이 우리를 흔듭니다. 그러나 영혼의 닻이 깊은 곳에 내려져 있으면, 흔들리되 무너지지 않습니다. 약속의 무게가 그 닻의 자리이며, 소망의 항구가 그 닻이 우리를 끌어당기는 방향입니다.",
            "흔들림과 흔들리지 않음은 동시에 가능합니다. 표면은 흔들려도 깊은 곳은 잔잔합니다. 그것이 그리스도인이 폭풍을 통과하는 방식입니다. 흔들림을 부정하지 않으면서, 그러나 그 흔들림이 마지막 단어가 되도록 두지 않는 자세입니다.",
            "이 부의 두 권은 끝까지 가는 발걸음의 두 결을 응시합니다. 「마지막 때의 믿음」은 깨어 있음과 마라나타의 자리를, 「흔들리지 않는 닻」은 폭풍 속에서도 흔들리지 않는 영혼의 닻을 다룹니다.",
            "한 알에서 시작해 산을 옮기고, 손으로 흐르는 자리를 거쳐, 마침내 끝까지 가는 발걸음으로 모이는 그 결에 함께 들어가십시오.",
        ],
        "guides": [
            "마지막 때를 바라보는 내 눈은 두려움의 눈인가 마라나타의 눈인가.",
            "내 영혼의 닻은 어디에 내려져 있으며, 어떤 폭풍이 와도 그 자리는 견고한가.",
            "흔들리되 무너지지 않는다는 자세를, 나는 어떤 일상에서 살아내고 있는가.",
            "이 부를 읽으며, 한 알의 믿음으로 시작한 발걸음이 어떻게 끝까지 가는 결을 따라가 보십시오.",
        ],
    },
}


# 권별 요약 (각 책 진입부 — 3단락, 약 70% 분량)
# 마지막 단락의 핵심 한 문장은 3번째 단락 끝에 흡수
BOOK_SUMMARIES = {
    1: [
        "의심은 죄가 아니라 선물이다. 첫 권은 그 단순하지만 잊기 쉬운 한 마디에서 시작한다. 도마는 부활하신 예수 앞에 자기 의심을 가지고 갔고, 그 자리에서 가장 깊은 고백이 흘러나왔다. 의심을 회피하는 자가 아니라 의심을 그분 앞에 가지고 가는 자가 진짜 확신에 이른다.",
        "저자는 맹신·광신·불신 사이의 미묘한 결을 분별한다. 우리가 확신이라 부르는 것 중에 사실은 거짓 확신이 많다. 자기 확신을 신앙으로 착각하거나, 종교적 분위기를 믿음으로 착각하거나, 무지에서 오는 안주를 확신으로 착각하는 함정들이 있다.",
        "이뭐꼬 — 이것이 무엇인가의 자세는 동양적 사유처럼 보이지만 사실은 가장 정직한 묵상의 자세다. 그리고 마지막 장은 불 속에서 나온 금이다. 의심을 통과한 확신은 비로소 단단해진다. 시련의 불을 거치지 않은 확신은 반짝일 수는 있어도 변하지 않는 가치는 가지지 못한다. 진짜 확신은 의심을 통과한 자리에서만 빚어진다.",
    ],
    2: [
        "보이지 않는다고 없는 것이 아니다. 자외선이 우리 눈에 보이지 않지만 분명히 존재하듯, 영적 실재는 우리의 일상보다 더 또렷하게 존재한다. 이 한 권은 그 보이지 않는 실재를 응시하는 눈을 길러 준다.",
        "히브리서 11장의 증언이 다시 펼쳐진다. 믿음은 바라는 것들의 실상이며 보지 못하는 것들의 증거다. 관측자가 세계를 바꾼다는 양자물리학의 통찰이, 한 영혼이 보이지 않는 것을 보기 시작할 때 그의 세계가 바뀐다는 신학적 진실과 만난다.",
        "차원의 문이 열릴 때, 우리는 보이는 세상이 전부가 아님을 깨닫는다. 마지막 장은 보이는 것에서 보이지 않는 것으로의 전환이다. 그 전환이 일어난 사람은 같은 일상을 살아도 다른 무게로 살아간다. 소망 자체가 증거이며, 보이지 않는 것을 보는 눈이 그리스도인의 정체성이다.",
    ],
    3: [
        "시험은 만나지 말아야 할 재난이 아니다. 시험은 자라남의 자리이며, 압력 속에서 다이아몬드가 빚어지는 자리다. 이 한 권은 시험을 정직하게 응시하면서, 그 안에 숨겨진 은혜의 결을 함께 짚는다.",
        "야고보는 시험을 만나거든 온전히 기쁘게 여기라고 말한다. 인내의 뿌리가 시험의 자리에서 자라나기 때문이다. 그리고 시험 한복판에서 우리에게 가장 필요한 것은 환경의 변화가 아니라 위로부터 난 지혜다. 지혜를 구하는 자에게 하나님은 후히 주신다.",
        "연단의 은혜가 짚어진다. 연단은 부서지기 위해서가 아니라 단단해지기 위해서다. 마지막 장은 완성을 향한 여정이다. 시험을 이기는 사람은 시험을 피하는 사람이 아니라 시험 한복판에서 인내를 자라게 하는 사람이다. 한 영혼의 완성은 결국 시험의 자리들이 쌓여 만들어지는 한 윤곽이다.",
    ],
    4: [
        "겨자씨 한 알의 비밀은 단순하다. 크기가 아니라 대상이다. 큰 믿음 같아 보여도 자기 자신을 향하면 작은 언덕도 옮기지 못하고, 작은 믿음이라도 살아 계신 하나님을 향하면 산이 흔들린다.",
        "산을 옮기는 믿음이라는 약속은 환상이 아니다. 다만 그 산이 무엇인지를 우리가 다시 정의해야 한다. 한 사람의 일상에서 옮겨야 할 산은 외부의 거대한 장애물이 아니라, 자기 안의 두려움·교만·습관일 때가 많다. 작다고 버리지 않고 드려진 작음에서 기적이 시작된다.",
        "뿌리내리는 시간이 있다. 한 알의 겨자씨가 큰 나무가 되기까지는 보이지 않는 자리에서의 자라남이 필요하다. 마지막 장은 공중의 새들이 깃들이는 나무다. 한 알에서 시작된 믿음이 마침내 다른 영혼들의 쉼터가 된다. 겨자씨와 산의 비밀은, 결국 한 영혼이 자기 자리에서 단단해질 때 그 그늘 아래 다른 생명이 깃든다는 한 마디다.",
    ],
    5: [
        "기적은 예외가 아니다. 우리의 기대가 너무 낮아서 기적을 기적으로 보지 못할 때가 많을 뿐이다. 이 한 권은 그 시선의 문제를 정직하게 짚는다. 살아 계신 하나님은 지금도 일하시며, 그 일하심의 흔적이 우리 일상에 흐르고 있다.",
        "씨앗 속에 숨겨진 숲이 있다. 작은 씨앗 안에 이미 큰 나무의 모든 결이 담겨 있듯, 한 영혼의 일상 속에 이미 기적의 결이 흐르고 있다. 누가 주도권을 쥐고 있는가의 물음 앞에서 우리는 다시 멈춘다. 우리의 통제력이 끝나는 자리에서 비로소 하나님의 일하심이 시작된다.",
        "치유는 살아 계신 하나님의 서명이다. 의학의 영역과 영적 영역은 분리된 두 자리가 아니라, 한 결로 흐르는 회복의 자리다. 마지막 장은 기적을 기대하는 삶이다. 기적을 기적으로 보는 눈을 가진 사람은 같은 일상을 다른 무게로 살아간다. 기적은 가끔 일어나는 사건이 아니라 깨어 있는 자에게 늘 흐르는 결이다.",
    ],
    6: [
        "두려움은 보편적이다. 그러나 두려움이 마지막 단어가 되어서는 안 된다. 이 한 권은 두려움의 정체를 직면하는 자리에서 시작한다. 두려움은 회피한다고 사라지지 않으며, 정직하게 마주하는 자리에서만 그 힘이 깨진다.",
        "완전한 사랑이 두려움을 쫓아낸다는 한 마디가 가장 깊은 자리다. 빛이 들어오면 어둠은 사라진다. 두려움을 이기는 가장 강력한 자리는 더 큰 두려움이 아니라 사랑받고 있다는 정체성이다. 염려를 기도로 바꾸는 훈련, 그 한 결이 일상의 두려움을 한 단계씩 줄여 간다.",
        "내가 너와 함께 함이라 — 이 약속이 두려움 없는 믿음의 가장 단단한 자리다. 사랑받는 자의 담대함은 자기 능력에서 오지 않고, 사랑받고 있다는 정체성에서 흘러나온다. 마지막 장은 두려움 없는 믿음으로 걸어가는 일상이다. 두려움이 사라진 자리가 아니라, 두려움이 있어도 그것에 발을 끌리지 않는 자리, 그것이 단단한 믿음의 결이다.",
    ],
    7: [
        "행함이 없는 믿음은 죽은 믿음이다. 야고보는 그 한 마디를 가장 단단하게 박아 두었다. 이 한 권은 그 한 마디 위에서 죽은 믿음과 살아 있는 믿음의 차이를 정직하게 풀어낸다. 믿음과 행함은 두 자리가 아니라 한 결의 두 측면이다.",
        "야고보서의 결이 차례로 펼쳐진다. 시험을 기쁘게 여기는 자세, 듣기는 속히 행하기는 즉시 하는 결단, 혀를 다스리는 훈련, 그리고 위로부터 난 지혜로 살아가는 자세. 이 모든 결은 결국 한 가지로 모인다. 믿음이 머리에서 가슴을 거쳐 손까지 흘러야 한다는 것이다.",
        "가난한 자를 돌아보는 일이 짚어진다. 종교적 행위가 아니라 일상의 손이다. 마지막 장은 기도하는 의인의 능력이다. 의인의 간절한 기도는 역사하는 힘이 크다. 믿음과 행함의 균형은 결국 기도의 자리에서 한 영혼이 무릎을 꿇을 때 비로소 빚어진다.",
    ],
    8: [
        "구름같은 증인들이 우리 앞에 있다. 그들은 신화 속 인물이 아니라 실제로 한 시대를 통과한 한 영혼들이다. 이 한 권은 그 발자국들을 차례로 따라간다. 그들의 발자국이 우리 발 앞에 놓여 있고, 우리는 그 위를 걷도록 부름받았다.",
        "아벨과 에녹과 노아로 시작한다. 가장 이른 시대의 증인들이 가장 단순한 결을 보여 준다. 아브라함의 순례, 모세의 선택, 다윗과 선지자들의 발걸음이 차례로 펼쳐진다. 이름이 새겨진 증인들 곁에 이름 없는 증인들도 함께 있다.",
        "마지막 장은 다음 세대에게의 부르심이다. 우리가 지금 받은 발자국은 결국 우리 다음 세대에게 넘겨야 할 발자국이기도 하다. 믿음의 선배들은 박물관의 인물이 아니라 우리에게 발자국을 넘겨준 가족이며, 우리는 그 가족의 다음 세대를 위해 다시 발자국을 남길 차례다.",
    ],
    9: [
        "마지막 때를 바라보는 눈은 두려움의 눈이 아니다. 성경은 마지막 때를 두려워하라고 말하지 않고, 깨어 있으라고 말한다. 깨어 있다는 것은 떠는 것이 아니라 분별하는 자세다. 이 한 권은 마지막 때의 자세를 정직하게 풀어낸다.",
        "충성된 종의 자세가 짚어진다. 마지막 때를 잘 살아내는 사람은 비범한 일을 하는 사람이 아니라 자기 자리에서 충성된 자다. 환난 중의 인내, 거룩함으로의 준비, 그리고 두려움이 아닌 소망으로 그 날을 바라보는 시선이 한 결로 흐른다.",
        "마라나타 — 주여 오시옵소서의 외침이 마지막 장이다. 이 외침은 두려움에 떠는 자의 외침이 아니라, 약속을 본 자의 외침이다. 마지막 때의 믿음은 결국 그분의 다시 오심을 약속으로 받아들이고 그 자리를 향해 발걸음을 멈추지 않는 자세다. 끝이 가까울수록 더 또렷이 보이는 한 결이 거기 있다.",
    ],
    10: [
        "폭풍 속에서 흔들리지 않는 사람은 없다. 그러나 흔들리되 무너지지 않는 사람은 있다. 그 차이는 영혼의 닻이 어디에 내려져 있는가에 달려 있다. 이 한 권은 폭풍 속에서도 흔들리지 않는 한 결을 응시한다.",
        "감정의 파도는 분명히 있다. 의심의 풍랑, 시대의 격동, 관계의 흔들림. 그 모든 파도는 표면에서 일어난다. 그러나 깊은 곳은 잔잔하다. 영혼의 닻은 그 깊은 곳에 내려져 있다. 약속의 무게가 그 닻의 자리이며, 그 약속이 단단할수록 닻은 더 깊이 박힌다.",
        "흔들려도 무너지지 않는다는 자세는 흔들림을 부정하는 자세가 아니다. 흔들림을 인정하면서 동시에 흔들림이 마지막 단어가 되도록 두지 않는 자세다. 마지막 장은 소망의 항구를 향한 항해다. 닻은 우리를 한 자리에 묶어 두기만 하지 않는다. 그 닻은 결국 소망의 항구로 우리를 끌어당기는 한 결의 방향이기도 하다. 단단한 믿음은 결국 그 항구를 향해 끝까지 가는 발걸음이다.",
    ],
}


# 권별 길잡이 — 그 한 권만의 좁고 깊은 화두 (부 길잡이와 차별)
BOOK_GUIDES = {
    1: [
        "내 안의 의심은 회피해야 할 적인가, 아니면 더 깊은 확신으로 가는 문인가.",
        "내가 확신이라 부르는 것 중에 사실은 거짓 확신인 자리는 어디인가.",
        "불 속에서 나온 금처럼, 내 시련의 자리는 어떻게 단단한 확신으로 빚어지고 있는가.",
    ],
    2: [
        "보이는 것 너머의 실재를 보는 눈을, 나는 어떤 자리에서 길러 가고 있는가.",
        "히브리서 11장의 증언이 추상이 아니라 일상이 되려면, 내 일상의 어떤 자리가 다시 빚어져야 하는가.",
        "관측자가 세계를 바꾼다는 한 마디가, 내 시선의 어떤 자리에서 살아나고 있는가.",
    ],
    3: [
        "내가 지금 통과하는 시험을 도망쳐야 할 자리로 보는가, 인내가 자라는 연단의 자리로 보는가.",
        "지혜를 구하라는 부르심 앞에서, 내 기도의 한 자리는 어떻게 빚어지고 있는가.",
        "완성을 향한 여정 위에서, 시험은 내게 어떤 결의 자라남을 일으키고 있는가.",
    ],
    4: [
        "내 믿음의 크기가 작다고 느낄 때, 나는 그 작음을 어디로 가져가고 있는가.",
        "겨자씨와 산의 비밀 — 크기가 아니라 대상이라는 한 마디를, 내 일상은 어떻게 살아내고 있는가.",
        "드려진 작음의 기적이, 내 일상의 어떤 자리에서 일어나고 있는가.",
    ],
    5: [
        "기적이 예외가 아니라 일상에 흐르는 결이라면, 나는 어떤 자리에서 그 결을 알아보고 있는가.",
        "내 기대가 너무 낮아서 기적을 기적으로 보지 못하는 자리는 어디인가.",
        "기적을 기대하는 삶이라는 자세가, 내 어떤 결정과 어떤 호흡 안에서 살아나고 있는가.",
    ],
    6: [
        "내 안의 두려움이 행함을 가로막는 자리는 어디이며, 나는 그 두려움을 어디로 가져가고 있는가.",
        "사랑받고 있다는 정체성이, 내 두려움 앞에서 어떤 결로 작동하고 있는가.",
        "염려를 기도로 바꾸는 훈련이, 내 일상의 어떤 자리에서 살아나고 있는가.",
    ],
    7: [
        "내 믿음은 머리에 머무는가, 가슴을 거쳐 손까지 흐르고 있는가.",
        "듣기는 속히 행하기는 즉시 — 이 결이 내 일상의 어떤 자리에서 살아나고 있는가.",
        "기도하는 의인의 능력이라는 약속을, 내 무릎의 자리는 어떻게 증언하고 있는가.",
    ],
    8: [
        "구름같은 증인들의 발자국 위에서, 나는 다음 발걸음을 어떻게 옮기고 있는가.",
        "이름 없는 증인들의 결이, 내 일상의 보이지 않는 자리에서 어떻게 닿고 있는가.",
        "다음 세대에게 내가 남길 발자국은 어떤 모양으로 빚어지고 있는가.",
    ],
    9: [
        "마지막 때를 바라보는 내 눈은 두려움의 눈인가 마라나타의 눈인가.",
        "충성된 종의 자세가, 내 자리의 어떤 결정과 어떤 일상에서 살아나고 있는가.",
        "거룩함으로 그 날을 준비한다는 것은, 내 일상의 어떤 자리에서 시작되는가.",
    ],
    10: [
        "내 영혼의 닻은 어디에 내려져 있으며, 어떤 폭풍이 와도 그 자리는 견고한가.",
        "흔들리되 무너지지 않는다는 자세를, 나는 어떤 일상에서 살아내고 있는가.",
        "소망의 항구를 향한 항해 위에서, 나는 닻과 돛을 어떻게 함께 사용하고 있는가.",
    ],
}


def build_book_front_xhtml(b: dict) -> str:
    """권 진입 — 요약 + CONTENTS를 한 xhtml에 결합. reader가 자연스럽게 2쪽으로 분할."""
    paragraphs = BOOK_SUMMARIES.get(b['order'], [])
    paragraphs_html = "\n  ".join(
        f'<p style="margin:0 0 1em;text-align:justify;word-break:keep-all">{p}</p>'
        for p in paragraphs
    )
    chapter_lines = []
    for ch in b["chapters"]:
        chapter_lines.append(
            f'<div style="margin:0.9em 0;color:#222;font-size:1em;line-height:1.5;display:flex;align-items:baseline">'
            f'<span style="color:#C8B99A;font-weight:700;letter-spacing:0.12em;font-size:0.78em;'
            f'min-width:3em;margin-right:1em;flex-shrink:0">Ch {ch["ch_no"]:02d}</span>'
            f'<span style="flex:1">{ch["title"]}</span>'
            f'</div>'
        )
    chapters_html = "\n    ".join(chapter_lines)

    guides = BOOK_GUIDES.get(b['order'], [])
    guides_html = ""
    if guides:
        items_html = "\n      ".join(
            f'<li style="font-size:0.92em;color:#0F1E3C;line-height:1.65;margin:0.4em 0;padding-left:0.5em;text-indent:-0.5em">'
            f'<span style="color:#B8962E;font-weight:700;display:inline-block;width:0.5em">·</span>{g}</li>'
            for g in guides
        )
        guides_html = f"""
<div style="background:#F8F5EC;border:1px solid #D9D0BC;border-radius:6px;padding:0.85em 1.1em;margin:1.4em auto 0;max-width:30em;page-break-inside:avoid;break-inside:avoid">
  <div style="font-size:0.76em;letter-spacing:0.25em;color:#B8962E;font-weight:700;margin-bottom:0.5em">길잡이와 함께 걸어가기</div>
  <ul style="margin:0;padding:0;list-style:none">
    {items_html}
  </ul>
</div>"""

    body = f"""<div style="padding:2em 1.5em 1.4em;line-height:1.85;font-size:1em;color:#222">

<div style="text-align:center;margin-bottom:1.5em">
  <div style="font-size:0.85em;letter-spacing:0.4em;color:#C8B99A">BOOK {b['order']:02d}</div>
  <h1 style="color:#0F1E3C;font-size:1.55em;margin:0.5em 0 0.35em;line-height:1.35">{b['title']}</h1>
  <div style="color:#888;font-size:0.88em;margin-top:0.3em">원본 ISBN {b['isbn']} · G03 제 {b['src_no']:02d} 권</div>
  <div style="margin-top:0.9em">
    <span style="display:inline-block;width:60px;border-top:1px solid #C8B99A"></span>
  </div>
</div>
<div style="">
  {paragraphs_html}
</div>
<div style="page-break-after:always;break-after:page;height:0;font-size:0;line-height:0" aria-hidden="true"></div>

<div style="max-width:30em;margin:1.8em auto 0;page-break-before:always;break-before:page;page-break-inside:avoid;break-inside:avoid">
  <div style="text-align:center;font-size:0.78em;letter-spacing:0.4em;color:#C8B99A;margin-bottom:0.6em">CONTENTS</div>
  <div style="border-top:1px solid #C8B99A;padding-top:0.6em">
    {chapters_html}
  </div>
</div>
{guides_html}

</div>"""
    return xhtml_doc(b["title"], body)


def build_part_intro_xhtml(part_no: int, part_title: str, part_subtitle: str, part_data: dict = None) -> str:
    intro = PART_INTROS.get(part_no, {})
    paragraphs_html = "\n".join(
        f'<p style="margin:0 0 0.7em">{p}</p>' for p in intro.get("paragraphs", [])
    )

    guides = intro.get("guides", [])
    guides_html = ""
    if guides:
        items_html = "\n    ".join(
            f'<li style="font-size:0.93em;color:#0F1E3C;line-height:1.7;margin:0.55em 0;padding-left:0.5em;text-indent:-0.5em">'
            f'<span style="color:#B8962E;font-weight:700;display:inline-block;width:0.5em">·</span>{g}</li>'
            for g in guides
        )
        guides_html = f"""
<div style="background:#F8F5EC;border:1px solid #D9D0BC;border-radius:6px;padding:1em 1.2em;margin:1.5em auto 0;max-width:34em;page-break-inside:avoid;break-inside:avoid">
  <div style="font-size:0.78em;letter-spacing:0.25em;color:#B8962E;font-weight:700;margin-bottom:0.6em">길잡이와 함께 걸어가기</div>
  <ul style="margin:0;padding:0;list-style:none">
    {items_html}
  </ul>
</div>"""

    body = f"""<div style="padding:1.4em 1.5em 1.2em;line-height:1.7;font-size:0.97em;color:#222">
<div style="text-align:center;margin-bottom:1.2em">
  <div style="font-size:0.85em;letter-spacing:0.4em;color:#C8B99A">PART {part_no}</div>
  <h1 style="color:#0F1E3C;font-size:1.5em;margin:0.3em 0 0.2em">{part_title}</h1>
  <div style="color:#666;font-size:0.92em">{part_subtitle}</div>
  <div style="margin-top:0.8em">
    <span style="display:inline-block;width:50px;border-top:1px solid #C8B99A"></span>
  </div>
</div>
<h3 style="color:#0F1E3C;text-align:center;font-size:1.15em;margin:0.4em 0 1em">{intro.get('headline', '')}</h3>
<div style="">
{paragraphs_html}
</div>
{guides_html}
</div>"""
    return xhtml_doc(f"{part_no}부 도입", body)


def build_chapter_xhtml(b: dict, ch: dict) -> str:
    """원본 챕터 html을 그대로 보존하되 헤더만 standalone xhtml로 감싸기."""
    body = f"""<div style="padding:1.5em">
<div style="font-size:0.8em;letter-spacing:0.2em;color:#C8B99A;margin-bottom:0.3em">
  Book {b['order']:02d} · Chapter {ch['ch_no']:02d}
</div>
{ch['html']}
</div>"""
    return xhtml_doc(ch["title"], body)


def build_epilogue_xhtml() -> str:
    body = """<div style="padding:2em 1.5em;line-height:1.9;font-size:1em;color:#222">
<h2 style="color:#0F1E3C;border-bottom:1px solid #C8B99A;padding-bottom:0.5em">닫는 글</h2>
<h3 style="color:#0F1E3C;margin-top:1.5em">한 알이 산을 옮긴 자리에서</h3>
<p>이로써 G03 열 권의 묵상이 한 권으로 닫힙니다. 의심을 넘어선 확신에서 시작해 흔들리지 않는 닻에 이르기까지, 단단한 믿음이 빚어지는 결을 네 갈래로 모아 함께 걸어왔습니다. 처음에는 흩어져 있던 한 권 한 권의 묵상이 한 호흡으로 이어 붙고 나니, 사이를 흐르고 있던 결이 비로소 또렷해졌습니다.</p>
<p>이 책이 묻고자 했던 한 가지 물음은 분명합니다. <em>한 알의 믿음이 어떻게 산을 옮기는 자리까지 자라는가.</em> 의심을 통과해 보이지 않는 것을 보는 시선과, 시험과 작음과 기적을 통해 자라는 결과, 두려움을 넘어 손으로 흐르는 행함과, 마지막 때까지 흔들리지 않는 발걸음 — 그 넷이 그 답의 네 갈래였습니다.</p>
<p><strong>1부에서 우리는 믿음의 시작</strong>을 응시했습니다. 의심은 회피해야 할 적이 아니라 깊은 확신의 문이며, 보이는 것 너머의 실재를 보는 눈이 신앙의 출발점이라는 것을 함께 보았습니다. 진짜 확신은 의심을 통과한 자리에서만 빚어지고, 보이지 않는 것을 보는 시선이 그리스도인의 정체성입니다.</p>
<p><strong>2부에서 우리는 한 알이 산이 되기까지</strong>의 결을 보았습니다. 시험은 자라남의 자리이며, 작음은 부끄러움이 아니라 비밀이며, 기적은 예외가 아니라 일상에 흐르는 결이었습니다. 겨자씨 한 알의 비밀은 크기가 아니라 대상이라는 한 마디 위에서, 한 영혼의 자라남이 시작됩니다.</p>
<p><strong>3부에서 우리는 믿음이 손으로 흐르는 자리</strong>를 짚어 보았습니다. 두려움을 넘어 담대함으로, 죽은 믿음에서 살아 있는 믿음으로, 그리고 구름같은 증인들의 발자국 위에서 다음 발걸음으로. 머리에서 시작된 믿음이 가슴을 거쳐 손까지 흘러야 비로소 살아 있는 믿음이라는 한 마디가 그 결의 핵심입니다.</p>
<p><strong>4부에서 우리는 끝까지 가는 발걸음</strong>에 도달했습니다. 마지막 때를 바라보는 눈은 두려움의 눈이 아니라 마라나타의 눈이며, 영혼의 닻은 폭풍 속에서도 우리를 흔들리되 무너지지 않게 합니다. 단단한 믿음은 결국 시작이 아니라 끝까지 가는 그 발걸음에서 완성됩니다.</p>
<p>이 책의 가장 단단한 한 마디는 표제에 이미 담겨 있습니다 — <em>겨자씨와 산.</em> 한 알의 작음과 한 산의 큼이 한 문장 안에서 만나는 그 자리에서, 단단한 믿음의 모든 결이 시작됩니다. 작음을 두려워하지 않고, 큼을 환상으로 여기지 않으며, 그 둘을 한 결로 잇는 자세 — 그것이 그리스도인이 평생 빚어 가야 할 한 길입니다.</p>
<p>이 책을 덮으신 뒤에도 묵상은 끝나지 않습니다. 한 장씩 다시 펼쳐 읽어도 좋고, 한 단락만 천천히 반복해 읽어도 좋습니다. 흔들리는 자리에서 흔들리지 않는 자리로 한 결이라도 옮겨 가셨다면, 그것만으로도 G03 열 권을 한 권으로 묶은 이유는 충분할 것입니다.</p>
<p>이제 100권 시리즈는 G04로, G05로, 그리고 마지막 G10까지 흘러갑니다. 단단한 믿음이 어떻게 빚어지는가의 결은 이 한 권에 모였습니다. 다음 그룹에서 또 다른 깊은 묵상으로 다시 만나기를 기도합니다. 주님의 평강이 여러분의 오늘 위에 충만히 임하시기를 축복합니다.</p>
</div>"""
    return xhtml_doc("닫는 글", body)


def build_publisher_xhtml(meta: dict, today_iso: str) -> str:
    body = f"""<div style="padding:3em 1.5em;line-height:1.9;font-size:0.95em;color:#333">

<div style="text-align:center;margin-bottom:2.5em">
  <img src="images/logo.png" alt="AI 시대 영성" style="max-width:55%;height:auto"/>
</div>

<h2 style="color:#0F1E3C;text-align:center;font-size:1.3em;border-bottom:1px solid #C8B99A;padding-bottom:0.6em;margin-bottom:1.5em">출판사 안내</h2>

<div style="">

<h3 style="color:#0F1E3C;font-size:1em;margin-top:1.5em;letter-spacing:0.05em">「AI 시대 영성」 출판사</h3>
<p style="margin:0.4em 0">기술의 시대 한복판에서, 흔들리지 않는 영성의 자리를 찾는 책을 펴냅니다.</p>
<p style="margin:0.4em 0;color:#666;font-size:0.92em">책방　<a href="https://ai-spirituality-books.vercel.app/catalog" style="color:#0F1E3C">ai-spirituality-books.vercel.app</a></p>
<p style="margin:0.4em 0;color:#666;font-size:0.92em">이메일　godsonphk@gmail.com</p>
<p style="margin:0.4em 0;color:#666;font-size:0.92em">카카오톡　<a href="https://pf.kakao.com/_PxdHTX" style="color:#0F1E3C">pf.kakao.com/_PxdHTX</a></p>

<h3 style="color:#0F1E3C;font-size:1em;margin-top:2em;letter-spacing:0.05em">저자 소개 — AI, 박헌근</h3>
<p style="margin:0.4em 0">AI 시대의 영성을 묻고 그 답을 묵상의 언어로 풀어내는 작가. 디지털 사회 속에서도 광야의 세미한 음성을 듣고자 하는 그리스도인의 자리를 함께 걸어가는 글을 쓴다.</p>

<h3 style="color:#0F1E3C;font-size:1em;margin-top:2em;letter-spacing:0.05em">시리즈 안내</h3>
<p style="margin:0.4em 0"><strong>시즌 1</strong>　100권 이전 10권 「AI 시대를 살아가는 영성」 (종합본)</p>
<p style="margin:0.4em 0"><strong>시즌 2</strong>　100권 영성 시리즈 G01~G10 (그룹별 종합책 10권 포함)</p>
<p style="margin:0.4em 0"><strong>시즌 3</strong>　120권 「성경의 시선으로 파헤치는 관계의 비밀」 (예정)</p>

<h3 style="color:#0F1E3C;font-size:1em;margin-top:2em;letter-spacing:0.05em">유튜브 채널</h3>
<p style="margin:0.4em 0">우주나-q3 ─ 100권 영성 시리즈 영상화 콘텐츠</p>

<div style="margin-top:2.5em;padding:1.5em;border:1px solid #C8B99A;border-radius:8px;text-align:center;background:#FAF7EE">
  <p style="margin:0 0 0.8em;color:#0F1E3C;font-weight:600;letter-spacing:0.05em">전자책 책방 바로가기</p>
  <img src="images/qr.png" alt="AI 시대 영성 책방 QR" style="width:160px;height:160px;display:block;margin:0 auto"/>
  <p style="margin:0.8em 0 0;color:#666;font-size:0.85em">스마트폰 카메라로 QR을 스캔하면<br/>121권 전자책 책방으로 이동합니다.</p>
  <p style="margin:0.6em 0 0;color:#888;font-size:0.78em">ai-spirituality-books.vercel.app</p>
</div>

<div style="margin-top:3em;padding-top:1.5em;border-top:1px solid #C8B99A;text-align:center;color:#888;font-size:0.85em">
  <p style="margin:0.3em 0">{meta['title']}</p>
  <p style="margin:0.3em 0;color:#aaa">{meta['publisher']}　·　{today_iso[:4]}</p>
  <p style="margin:1em 0;letter-spacing:0.3em;color:#C8B99A">— 끝 —</p>
</div>

</div>
</div>"""
    return xhtml_doc("출판사 안내", body)
# PATCHED:qr-v1


def build_nav_xhtml(parts):
    items = ['<li><a href="cover.xhtml">표지</a></li>',
             '<li><a href="copyright.xhtml">판권</a></li>',
             '<li><a href="toc.xhtml">차례</a></li>',
             '<li><a href="preface.xhtml">여는 글</a></li>']
    for p in parts:
        pno = p["part"]
        items.append(f'<li><a href="part{pno:02d}_intro.xhtml">{p["title"]}</a><ol>')
        for b in p["books_with_chs"]:
            items.append(f'  <li><a href="b{b["order"]:02d}_front.xhtml">{b["title"]}</a><ol>')
            for ch in b["chapters"]:
                items.append(f'    <li><a href="b{b["order"]:02d}_ch{ch["ch_no"]:02d}.xhtml">{ch["title"]}</a></li>')
            items.append('  </ol></li>')
        items.append('</ol></li>')
    items.append('<li><a href="epilogue.xhtml">닫는 글</a></li>')
    items.append('<li><a href="publisher.xhtml">출판사 안내</a></li>')

    nav = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<!DOCTYPE html>\n'
           '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ko">\n'
           '<head><meta charset="UTF-8"/><title>목차</title></head>\n'
           '<body>\n'
           '  <nav epub:type="toc" id="toc"><h1>목차</h1><ol>\n'
           + "\n".join("    " + i for i in items) +
           '\n  </ol></nav>\n'
           '  <nav epub:type="landmarks"><ol>\n'
           '    <li><a epub:type="cover" href="cover.xhtml">표지</a></li>\n'
           '    <li><a epub:type="bodymatter" href="preface.xhtml">본문 시작</a></li>\n'
           '  </ol></nav>\n'
           '</body></html>\n')
    return nav


def build_toc_xhtml(parts, meta):
    """앞쪽 차례.
    - 차례/부제는 페이지 가운데
    - 부 블록(구분선·PART·부 제목·점 항목)은 가운데에서 더 오른쪽으로 들여씀
    - 부 부제는 () 대신 ' : '로 연결
    - 점(·)은 "N부 — " 다음 첫 주제 글자(시/믿/감/종) 바로 아래에 세로 정렬
      ("1부 — " 폭 ≈ 3em → padding-left:3em)
    """
    rows = []
    for p in parts:
        book_lines = []
        for b in p.get('books_with_chs', p.get('books', [])):
            book_lines.append(
                f'<div style="margin:0.25em 0;color:#333;font-size:1em;line-height:1.5">'
                f'<span style="color:#C8B99A;font-weight:600;margin-right:0.5em">·</span>'
                f'{b["title"]}'
                f'</div>'
            )
        books_html = ''.join(book_lines)
        rows.append(f"""
<div style="margin:0.45em 0;padding:0.4em 0;border-top:1px solid #E0D5B4">
  <div style="font-size:0.7em;letter-spacing:0.4em;color:#C8B99A">PART {p['part']}</div>
  <h2 style="color:#0F1E3C;font-size:1.1em;margin:0.15em 0 0.3em;line-height:1.4">{p['title']} : <span style="font-weight:400;color:#666;font-size:0.9em;font-style:italic">{p['subtitle']}</span></h2>
  <div style="padding-left:3em">{books_html}</div>
</div>""")

    body = f"""<div style="padding:0.8em 1.5em;line-height:1.5;">
<h1 style="color:#0F1E3C;text-align:center;font-size:1.35em;margin:0.2em 0">차례</h1>
<div style="color:#666;text-align:center;margin-bottom:0.5em;font-style:italic;font-size:0.85em">{meta['subtitle']}</div>
<div style="padding-left:5em">
{''.join(rows)}
</div>
</div>"""
    return xhtml_doc("차례", body)


def main():
    with open(META_PATH, encoding="utf-8") as f:
        meta_full = json.load(f)
    with open(EXTRACT_PATH, encoding="utf-8") as f:
        extract = json.load(f)

    proj = meta_full["project"]
    structure = meta_full["structure"]

    # books_with_chs 매핑: order별로 챕터 채워넣기
    books_by_order = {b["order"]: b for b in extract["books"]}
    for p in structure["parts"]:
        p["books_with_chs"] = []
        for b in p["books"]:
            chs = books_by_order[b["order"]]["chapters"]
            p["books_with_chs"].append({
                "order": b["order"],
                "src_no": b["src_no"],
                "title": b["title"],
                "isbn": b["isbn"],
                "chapters": chs,
            })

    publish_raw = proj.get("publish_date")
    if publish_raw:
        norm = publish_raw.replace(".", "-")
        today_iso = norm                       # OPF dc:date 표준 형식 "2026-05-30"
        today_compact = norm.replace("-", "")  # 파일명 "20260530"
        today_display = norm.replace("-", ".") # 화면 표시 "2026.05.30"
    else:
        today_iso = datetime.now().strftime("%Y-%m-%d")
        today_compact = datetime.now().strftime("%Y%m%d")
        today_display = datetime.now().strftime("%Y.%m.%d")
    title_slug = proj["title"].replace(" ", "_")
    out_path = OUT_DIR / f"{title_slug}_{today_compact}_종합책.epub"
    print(f"=== 종합책 빌드 시작 ===")
    print(f"  제목: {proj['title']}")
    print(f"  부제: {proj['subtitle']}")
    print(f"  출력: {out_path}")
    print()

    # 파일 모음 dict (path -> bytes)
    files = {}

    # mimetype
    files["mimetype"] = b"application/epub+zip"

    # META-INF/container.xml
    files["META-INF/container.xml"] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
        '  <rootfiles>\n'
        '    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n'
        '  </rootfiles>\n'
        '</container>\n'
    ).encode("utf-8")

    # OEBPS/styles/style.css
    files["OEBPS/styles/style.css"] = get_css().encode("utf-8")

    # OEBPS/images/cover.jpg (placeholder from sample)
    files["OEBPS/images/cover.jpg"] = get_cover_image()

    # OEBPS/images/logo.png (판권지 등 본문에 삽입)
    logo_bytes = get_logo_png()
    if logo_bytes:
        files["OEBPS/images/logo.png"] = logo_bytes

    # OEBPS/images/qr.png (출판사 안내 페이지 — 책방 사이트 직링크)
    files["OEBPS/images/qr.png"] = make_qr_png_bytes(catalog_url(), box_size=10, border=2)

    # XHTML 페이지들
    files["OEBPS/cover.xhtml"] = build_cover_xhtml(proj["title"], proj["subtitle"], files["OEBPS/images/cover.jpg"]).encode("utf-8")
    files["OEBPS/copyright.xhtml"] = build_copyright_xhtml(proj, today_display).encode("utf-8")
    files["OEBPS/preface.xhtml"] = build_preface_xhtml().encode("utf-8")
    files["OEBPS/epilogue.xhtml"] = build_epilogue_xhtml().encode("utf-8")
    files["OEBPS/publisher.xhtml"] = build_publisher_xhtml(proj, today_display).encode("utf-8")
    files["OEBPS/toc.xhtml"] = build_toc_xhtml(structure["parts"], proj).encode("utf-8")
    files["OEBPS/nav.xhtml"] = build_nav_xhtml(structure["parts"]).encode("utf-8")

    # 부 도입 + 권 도입 + 챕터
    spine_items = [("cover-page", "cover.xhtml"),
                   ("copyright", "copyright.xhtml"),
                   ("toc-page", "toc.xhtml"),
                   ("preface", "preface.xhtml")]

    manifest_items = [
        ('cover-image', 'images/cover.jpg', 'image/jpeg', 'cover-image'),
        ('style', 'styles/style.css', 'text/css', None),
        ('nav', 'nav.xhtml', 'application/xhtml+xml', 'nav'),
        ('cover-page', 'cover.xhtml', 'application/xhtml+xml', None),
        ('copyright', 'copyright.xhtml', 'application/xhtml+xml', None),
        ('toc-page', 'toc.xhtml', 'application/xhtml+xml', None),
        ('preface', 'preface.xhtml', 'application/xhtml+xml', None),
    ]
    if logo_bytes:
        manifest_items.append(('logo-image', 'images/logo.png', 'image/png', None))
    manifest_items.append(('qr-image', 'images/qr.png', 'image/png', None))

    for p in structure["parts"]:
        pno = p["part"]
        # 부 도입 (부 안의 책·챕터 전체 목차 포함)
        intro_path = f"OEBPS/part{pno:02d}_intro.xhtml"
        files[intro_path] = build_part_intro_xhtml(pno, p["title"], p["subtitle"], p).encode("utf-8")
        manifest_items.append((f'part{pno:02d}-intro', f'part{pno:02d}_intro.xhtml', 'application/xhtml+xml', None))
        spine_items.append((f'part{pno:02d}-intro', f'part{pno:02d}_intro.xhtml'))

        for b in p["books_with_chs"]:
            order = b["order"]
            # 권 진입: 요약 + CONTENTS 결합 (reader가 자연스럽게 2쪽으로 분할)
            bf_path = f"OEBPS/b{order:02d}_front.xhtml"
            files[bf_path] = build_book_front_xhtml(b).encode("utf-8")
            manifest_items.append((f'b{order:02d}-front', f'b{order:02d}_front.xhtml', 'application/xhtml+xml', None))
            spine_items.append((f'b{order:02d}-front', f'b{order:02d}_front.xhtml'))

            # 챕터들
            for ch in b["chapters"]:
                ch_path = f"OEBPS/b{order:02d}_ch{ch['ch_no']:02d}.xhtml"
                files[ch_path] = build_chapter_xhtml(b, ch).encode("utf-8")
                ch_id = f"b{order:02d}-ch{ch['ch_no']:02d}"
                manifest_items.append((ch_id, f"b{order:02d}_ch{ch['ch_no']:02d}.xhtml", 'application/xhtml+xml', None))
                spine_items.append((ch_id, f"b{order:02d}_ch{ch['ch_no']:02d}.xhtml"))

    # epilogue
    manifest_items.append(('epilogue', 'epilogue.xhtml', 'application/xhtml+xml', None))
    spine_items.append(('epilogue', 'epilogue.xhtml'))

    # publisher info (back matter, after epilogue)
    manifest_items.append(('publisher', 'publisher.xhtml', 'application/xhtml+xml', None))
    spine_items.append(('publisher', 'publisher.xhtml'))

    # OPF 생성
    manifest_xml = []
    for item_id, href, mt, props in manifest_items:
        prop_attr = f' properties="{props}"' if props else ''
        manifest_xml.append(f'    <item id="{item_id}" href="{href}" media-type="{mt}"{prop_attr}/>')

    spine_xml = []
    for item_id, _ in spine_items:
        spine_xml.append(f'    <itemref idref="{item_id}"/>')

    isbn_id = proj.get("isbn", "") or f"omnibus-{today_compact}"
    uuid_id = f"omnibus-g03-{today_compact}-{datetime.now().strftime('%H%M%S')}"

    if proj.get("isbn"):
        identifier_line = f'<dc:identifier id="bookid">urn:isbn:{proj["isbn"]}</dc:identifier>'
    else:
        identifier_line = f'<dc:identifier id="bookid">urn:uuid:{uuid_id}</dc:identifier>'

    opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" xml:lang="ko" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    {identifier_line}
    <dc:identifier id="uuid">urn:uuid:{uuid_id}</dc:identifier>
    <dc:title>{proj['title']}</dc:title>
    <dc:creator>{proj['author']}</dc:creator>
    <dc:publisher>{proj['publisher']}</dc:publisher>
    <dc:language>ko</dc:language>
    <dc:date>{today_iso}</dc:date>
    <dc:rights>Copyright © 2026 박헌근. All rights reserved.</dc:rights>
    <dc:description>{proj['subtitle']} — G03 10권 종합본</dc:description>
    <meta name="cover" content="cover-image"/>
    <meta property="dcterms:modified">{today_iso}T00:00:00Z</meta>
    <meta property="rendition:spread">none</meta>
    <meta property="rendition:layout">reflowable</meta>
  </metadata>
  <manifest>
{chr(10).join(manifest_xml)}
  </manifest>
  <spine>
{chr(10).join(spine_xml)}
  </spine>
</package>
"""
    files["OEBPS/content.opf"] = opf.encode("utf-8")

    # 안전망: 본권에서 흘러온 마크다운 펜스가 챕터 xhtml 에 살아있으면 제거.
    fence_removed = 0
    for path in list(files.keys()):
        if not (path.endswith(".xhtml") or path.endswith(".html")):
            continue
        data = files[path]
        if isinstance(data, bytes):
            try:
                txt = data.decode("utf-8")
            except UnicodeDecodeError:
                continue
            if "```" in txt:
                new_txt = _strip_md_fences(txt)
                if new_txt != txt:
                    files[path] = new_txt.encode("utf-8")
                    fence_removed += 1
        else:
            if "```" in data:
                new_txt = _strip_md_fences(data)
                if new_txt != data:
                    files[path] = new_txt
                    fence_removed += 1
    if fence_removed:
        print(f"  [안전망] 마크다운 펜스 제거: {fence_removed}개 파일")

    # zip 생성 (mimetype은 STORED, 나머지는 DEFLATED)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    out_paths = [out_path, OUT_BACKUP_DIR / out_path.name]
    for op in out_paths:
        with zipfile.ZipFile(op, "w") as z:
            z.writestr(zipfile.ZipInfo("mimetype"), files["mimetype"], compress_type=zipfile.ZIP_STORED)
            for path, data in files.items():
                if path == "mimetype":
                    continue
                z.writestr(path, data, compress_type=zipfile.ZIP_DEFLATED)

    sz = out_path.stat().st_size
    print(f"[완료] 메인:   {out_path}")
    print(f"[완료] 백업:   {out_paths[1]}")
    print(f"  크기: {sz/1024:.1f}KB")
    print(f"  매니페스트 항목: {len(manifest_items)}개")
    print(f"  스파인 항목: {len(spine_items)}개")
    print(f"  챕터: {sum(1 for i in spine_items if 'ch' in i[0]):2d}개")
    print(f"  ISBN: {proj.get('isbn') or '(미발급, uuid 사용)'}")
    print()
    print("문안: 여는 글, 4부 도입글, 닫는 글 모두 작성 완료.")
    print("표지·로고·출판사 안내·소책자별 목차 모두 적용 완료.")
    print("ISBN 발급 시 batch_books_g03_omnibus.json의 isbn 필드에 입력 후 재빌드.")


if __name__ == "__main__":
    main()
