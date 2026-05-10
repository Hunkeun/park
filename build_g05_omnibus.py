# -*- coding: utf-8 -*-
"""
G05 10권 종합책 "흉터 위의 빛" epub 빌더.

입력:
  - batch_books_g05_omnibus.json (메타·4부 구조)
  - tmp/g05_omnibus_extracted.json (10권 본문 추출본)
  - G05 epub 중 한 권 (CSS 추출용)

출력:
  - ~/Downloads/전자책/흉터_위의_빛_YYYYMMDD_종합책.epub

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
META_PATH = PROJECT / "batch_books_g05_omnibus.json"
EXTRACT_PATH = PROJECT / "tmp" / "g05_omnibus_extracted.json"
SAMPLE_EPUB = Path.home() / "Downloads" / "전자책" / "상처받은_영혼의_회복_20260418.epub"
OUT_DIR = Path.home() / "Downloads" / "전자책"
OUT_BACKUP_DIR = PROJECT / "tmp"  # 보조 사본


def get_css():
    """샘플 epub에서 CSS 추출."""
    with zipfile.ZipFile(SAMPLE_EPUB, "r") as z:
        return z.read("OEBPS/styles/style.css").decode("utf-8")


def get_cover_image():
    """전용 종합책 표지 사용 (없으면 샘플로 폴백)."""
    custom = PROJECT / "tmp" / "g05_omnibus_cover.jpg"
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
  <p><strong>구성</strong>　G05 10권 종합책 (4부 70장)</p>
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
    <p>이 책은 100권 영성 시리즈 G05(내면 치유) 10권의 본문을 거의 그대로 4부 구조로 재편집하여 한 권으로 묶은 종합본입니다.</p>
    <p>각 권의 원본 ISBN 및 출간 정보는 본문 권별 도입 페이지에 명기되어 있습니다.</p>
  </div>
</div></div>"""
    return xhtml_doc("판권", body)


def build_preface_xhtml() -> str:
    body = """<div style="padding:2em 1.5em;line-height:1.9;font-size:1em;color:#222">
<h2 style="color:#0F1E3C;border-bottom:1px solid #C8B99A;padding-bottom:0.5em">여는 글</h2>
<h3 style="color:#0F1E3C;margin-top:1.5em">흉터를 안고 빛으로 걸어가는 길</h3>
<p>모든 사람은 흉터를 가지고 있습니다. 어떤 흉터는 몸에 새겨져 있고, 어떤 흉터는 마음에 새겨져 있습니다. 어떤 흉터는 시간이 흘러 옅어졌고, 어떤 흉터는 오늘도 여전히 아립니다. 그러나 그리스도인의 영성은 흉터를 부정하지 않습니다. 흉터를 정직하게 응시하면서, 그 위에 빛이 비치는 자리를 함께 만들어 가는 자세입니다.</p>
<p>이 책은 그 흉터와 빛이 만나는 자리를 차례로 따라 걷습니다. 트라우마와 몸의 기억, 감정의 결, 번아웃과 내면 아이, 그리고 용서와 관계 회복까지 — 한 영혼이 상처에서 회복으로 옮겨 가는 결을 열 갈래로 펼쳐 놓았습니다.</p>
<p>이 책은 100권 영성 시리즈의 다섯 번째 그룹 G05를 한 권으로 묶은 종합본입니다. 상처받은 영혼의 회복에서 관계의 상처를 넘어서까지, 내면 치유라는 한 단어 안에 담긴 그리스도교의 가장 깊은 묵상을 네 갈래로 모았습니다. 열 권 각각의 본문을 거의 그대로 유지하면서, 그 사이를 흐르고 있던 결을 한 호흡으로 이어 붙였습니다.</p>
<p>네 갈래는 흉터에서 빛까지 옮겨 가는 한 영혼의 결입니다. <strong>1부 — 상처를 마주하다</strong>는 트라우마와 몸의 기억을 정직하게 응시하는 자리에서 시작하고, <strong>2부 — 감정과 함께 걷다</strong>는 감정의 신학·분노·슬픔의 결을 동행하는 자세를 봅니다. <strong>3부 — 회복으로 나아가다</strong>는 번아웃과 내면 아이의 자리에서 다시 일어나는 결을 짚고, <strong>4부 — 관계 안에서 빛이 되다</strong>는 용서와 관계 회복으로 한 영혼의 치유가 마침내 다른 영혼에게 닿는 자리를 응시합니다.</p>
<p>이 책은 상처가 사라진다고 약속하지 않습니다. 흉터는 흉터로 남을 수 있습니다. 다만 그 흉터 위에 빛이 비치고, 그 빛이 다시 다른 영혼에게 흘러가는 결을 함께 따라가려 합니다. 흉터를 부정하지 않으면서, 그러나 흉터가 마지막 단어가 되도록 두지 않는 자세 — 그것이 그리스도인의 치유입니다.</p>
<p>한 번에 다 읽어내실 책이 아닙니다. 한 장씩, 한 묵상씩 호흡을 따라 가져가시면 됩니다. 이제 첫 장을 펼쳐 주십시오. 흉터를 안고 빛으로 걸어가는 길 위에서, 한 호흡씩 함께 걸어가 봅시다.</p>
</div>"""
    return xhtml_doc("여는 글", body)


PART_INTROS = {
    1: {
        "headline": "상처를 정직하게 응시하는 자리",
        "paragraphs": [
            "상처를 부정하는 신앙은 진짜 신앙이 아닙니다. 상처를 회피하는 영성은 결국 상처를 더 깊은 자리로 밀어 넣을 뿐입니다. 그리스도인의 치유는 상처를 정직하게 응시하는 자리에서 비로소 시작됩니다. 인정하지 못한 상처는 치유되지 않습니다.",
            "트라우마는 단순히 마음의 일이 아닙니다. 몸에 새겨진 상처입니다. 어둠 속에 계셨던 하나님은 그 어둠을 부정하지 않으시면서도, 그 한복판에 함께 계셨다는 사실을 우리에게 가르치십니다. 상처는 자기 죄의 결과만이 아니라 시대와 환경과 다른 사람의 무게에서도 옵니다. 그래서 상처를 자책으로만 풀어내려 하면 더 깊이 묻힙니다.",
            "성경은 우리 몸이 영혼의 거울임을 증언합니다. 몸의 기억이 있고, 그 몸의 기억이 영혼의 결을 빚습니다. 안식, 호흡, 식사, 잠 — 이 모든 것이 영적 의미를 품고 있다는 것을 우리는 너무 자주 잊어버립니다. 전인적 회복이라는 한 마디는, 결국 몸과 영혼이 한 결로 흐른다는 사실을 다시 받아들이는 자세입니다.",
            "회복은 거짓 자아의 죽음에서 시작됩니다. 강한 척, 괜찮은 척, 다 이겨낸 척 — 그 가면을 내려놓는 자리에서 진짜 치유가 시작됩니다. 있는 그대로의 나로 서다는 한 마디는 가장 단순하지만 가장 어려운 결입니다.",
            "이 부의 세 권은 상처를 정직하게 응시하는 세 결을 차례로 펼칩니다. 「상처받은 영혼의 회복」은 거짓 자아의 죽음과 안전한 둥지의 자리를, 「트라우마와 은혜」는 어둠 속에서 만나는 은혜의 결을, 「몸의 기억, 영혼의 치유」는 전인적 회복의 여정을 다룹니다.",
            "상처를 부정하지 않으면서, 그러나 상처가 마지막 단어가 되도록 두지 않는 자리. 그 자리에서 빛이 흘러들 수 있습니다.",
        ],
        "guides": [
            "내가 회피하고 있는 상처는 무엇이며, 그 상처를 어떻게 정직하게 응시하기 시작할 수 있는가.",
            "거짓 자아의 가면을 내려놓는 자리는 내 안에서 어떻게 열리고 있는가.",
            "몸의 기억과 영혼의 치유가 한 결로 흐른다면, 내 일상의 어떤 자리가 다시 빚어져야 하는가.",
            "이 부를 읽으며, 상처를 정직하게 응시하는 것이 어떻게 회복의 첫 걸음이 되는가에 주목해 보십시오.",
        ],
    },
    2: {
        "headline": "감정을 하나님 앞에 가져가는 자리",
        "paragraphs": [
            "감정은 신앙의 적이 아닙니다. 감정은 하나님이 주신 선물이며, 우리가 그분께 가져가야 할 가장 정직한 자리입니다. 감정을 억누르는 영성은 머지않아 무너지고, 감정을 부정하는 신앙은 결국 자기 자신과의 단절을 낳습니다.",
            "시편이 우리에게 가르치는 것이 그것입니다. 다윗은 분노를 토했고 슬픔을 부르짖었으며 두려움을 숨기지 않고 하나님 앞에 펼쳤습니다. 시편의 기도학은 감정의 신학의 가장 단단한 기초입니다. 기쁨도 슬픔도 분노도 두려움도 모두 하나님 앞에 가져갈 수 있습니다.",
            "분노는 두 얼굴을 가집니다. 죄로 흐를 수도 있고, 거룩한 분노가 될 수도 있습니다. 예수께서 성전을 청결하게 하실 때 보이신 거룩한 분노를 우리는 잊지 말아야 합니다. 다만 해가 지기 전에 — 그 분노가 자기 안에서 곪지 않도록 매일의 호흡으로 풀어내는 자세가 필요합니다.",
            "슬픔도 마찬가지입니다. 충분히 슬퍼하지 않은 슬픔은 사라지지 않고 다른 자리에서 다시 솟아납니다. 눈물이 기도가 될 때, 비가 내려야 꽃이 핀다는 한 마디가 우리 안에서 살아납니다. 함께 우시는 하나님 앞에서 우리의 슬픔은 더 이상 외로운 슬픔이 아닙니다.",
            "이 부의 세 권은 감정과 함께 걷는 세 결을 차례로 펼칩니다. 「감정의 신학」은 시편의 기도학과 감정을 드리는 삶을, 「분노를 다스리는 법」은 두 얼굴의 분노와 온유함의 결을, 「슬픔도 선물이다」는 슬픔의 거룩한 여정을 다룹니다.",
            "감정을 하나님 앞에 가져가는 자세, 그것이 영성의 가장 깊은 자리이자 가장 정직한 자리입니다.",
        ],
        "guides": [
            "내가 하나님 앞에 가져가지 못하고 억누르고 있는 감정은 무엇인가.",
            "분노가 죄로 흐르지 않고 거룩한 분노가 되려면, 내 안에서 어떤 결단이 필요한가.",
            "충분히 슬퍼하는 자리, 눈물이 기도가 되는 자리를, 나는 어떻게 만들고 있는가.",
            "이 부를 읽으며, 감정과 영성이 분리된 두 자리가 아니라 한 결로 흐른다는 것에 주목해 보십시오.",
        ],
    },
    3: {
        "headline": "무너진 자리에서 다시 일어나는 결",
        "paragraphs": [
            "무너지는 자리는 누구에게나 있습니다. 번아웃이 닥치고, 안에 있던 어린 나가 흔들리며, 모든 것이 멈춘 듯한 자리에 한 영혼이 섭니다. 그러나 그 자리가 끝이 아닙니다. 무너진 자리에서 다시 일어나는 결이 있다는 것, 그것이 회복의 가장 깊은 약속입니다.",
            "번아웃은 게으름이 아닙니다. 너무 오래 자기를 다 쓴 결과입니다. 광야의 로뎀나무 아래에 누운 엘리야처럼, 우리도 그 나무 아래에 누울 권리가 있습니다. 회복은 비범한 일을 하는 자리가 아니라, 안식이라는 가장 단순한 은혜를 받아들이는 자리에서 시작됩니다.",
            "겨울 나무의 침묵이 짚어집니다. 잎이 다 떨어지고 가지만 남은 나무는 죽은 것처럼 보이지만, 그 안에서는 봄을 준비하는 결이 흐르고 있습니다. 겉으로 보이는 침묵 아래 숨겨진 자라남이 있습니다. 죄책감을 내려놓고 무덤에서 정원으로 옮겨 가는 결을 우리는 그 침묵 안에서 발견합니다.",
            "그리고 우리 안에는 어린 나가 있습니다. 받지 못한 것들의 목록을 안고 자란 나무가 우리 안에 서 있습니다. 그 어린 나를 만나는 일은 자기 연민이 아니라 자기 회복의 시작입니다. 아버지라 부를 수 있는 분 앞에서, 어린 나를 안으시는 손길 안에서, 흔적마저 아름답게 하시는 하나님의 결을 우리는 발견합니다.",
            "이 부의 두 권은 무너진 자리에서의 회복의 결을 차례로 응시합니다. 「번아웃에서 부활로」는 광야의 로뎀나무 아래에서 다시 걸어가는 사람으로의 여정을, 「내면 아이의 치유」는 받지 못한 것들의 목록을 안고 자란 어린 나를 만나는 자리를 다룹니다.",
            "무너지는 자리가 마지막이 아니라 다시 일어나는 자리의 시작이라는 것을, 두 결의 회복 위에서 함께 발견해 보십시오.",
        ],
        "guides": [
            "내가 통과하고 있는 번아웃의 자리는 어디이며, 그 자리에서 가장 먼저 받아들여야 할 은혜는 무엇인가.",
            "겨울 나무의 침묵 같은 자리에서, 나는 보이지 않는 자라남을 어떻게 신뢰하고 있는가.",
            "내 안의 어린 나가 받지 못한 것들의 목록은 무엇이며, 그 목록을 어디로 가져가고 있는가.",
            "이 부를 읽으며, 무너진 자리에서 다시 일어나는 결이 어떻게 빚어지는가에 주목해 보십시오.",
        ],
    },
    4: {
        "headline": "관계라는 마지막 치유의 자리",
        "paragraphs": [
            "내면 치유의 마지막 자리는 결국 관계입니다. 한 영혼이 자기 안에서 회복되었다 해도, 그 회복이 다른 영혼에게 닿지 못하면 반쪽짜리 회복입니다. 우리는 관계 안에서 빚어졌고, 관계 안에서 상처받았으며, 결국 관계 안에서 다시 회복됩니다.",
            "용서는 그 마지막 자리에서 가장 어려운 결단입니다. 용서하지 못한 자리는 감옥과 같고, 그 감옥의 첫 번째 죄수는 용서하지 못한 자기 자신입니다. 십자가가 용서의 근원이라는 한 마디는 추상이 아니라 가장 정직한 회복의 길입니다. 상처의 이름을 부르고, 그 상처를 십자가 앞에 가져가는 자세에서 용서가 시작됩니다.",
            "용서는 한 번에 일어나지 않습니다. 일흔 번씩 일곱 번이라는 예수의 가르침은 용서가 한 사건이 아니라 평생 흐르는 결임을 가리킵니다. 그리고 자기 자신을 용서하는 용기가 종종 가장 어려운 결단입니다. 다른 사람을 용서한 자가 자기 자신을 용서하지 못한 채 살아가는 모습을 우리는 자주 봅니다.",
            "관계의 상처는 깊지만, 그 상처를 넘어서는 자리가 있습니다. 깨진 그릇의 신학은 우리에게 가르칩니다. 그릇이 깨진 자리에 새 결합제가 들어가면, 그 그릇은 깨지기 전보다 더 단단해질 수도 있다는 것입니다. 건강한 경계와 차가운 벽을 분별하면서, 공동체라는 치유의 자리에서 화해의 결이 흐릅니다.",
            "이 부의 두 권은 관계 안에서 빛이 되는 두 결을 응시합니다. 「용서의 기적」은 용서하지 못한 감옥에서 용서가 연 기적의 문까지를, 「관계의 상처를 넘어서」는 깨진 그릇의 신학에서 더 깊어지는 사랑까지를 다룹니다.",
            "흉터를 안고 빛으로 걸어가는 길은 결국 관계 안에서 완성됩니다. 그 마지막 자리로 함께 들어가십시오.",
        ],
        "guides": [
            "내가 용서하지 못한 자리는 어디이며, 그 자리의 첫 번째 죄수는 누구인가.",
            "일흔 번씩 일곱 번의 용서가 평생 흐르는 결이라면, 내 일상은 그 결을 어떻게 살아내고 있는가.",
            "건강한 경계와 차가운 벽을 분별하는 자리에서, 나는 어떤 관계를 다시 빚고 있는가.",
            "이 부를 읽으며, 관계가 어떻게 마지막 치유의 자리가 되는가에 주목해 보십시오.",
        ],
    },
}


# 권별 요약 (각 책 진입부 — 3단락, 약 70% 분량)
# 마지막 단락의 핵심 한 문장은 3번째 단락 끝에 흡수
BOOK_SUMMARIES = {
    1: [
        "상처라는 이름의 현실 앞에서 우리는 자주 회피한다. 그러나 회피는 치유가 아니다. 첫 권은 상처를 정직하게 응시하는 자리에서 시작한다. 상처 뒤에 도사린 자가 있다는 영적 분별과, 그 상처를 싸매시는 하나님의 손길을 차례로 짚는다.",
        "거짓 자아의 죽음이 회복의 시작이다. 강한 척, 괜찮은 척, 다 이겨낸 척 — 그 가면이 무너지는 자리에서 진짜 치유가 시작된다. 이미 이루어진 치유라는 한 마디가 깊다. 우리가 노력해서 만들어 내는 회복이 아니라, 십자가에서 이미 선포된 치유를 받아들이는 자리다.",
        "안전한 둥지, 하나님의 임재 안에서 상처받은 영혼이 쉼을 얻는다. 마지막 장은 있는 그대로의 나로 서다. 가장 단순하지만 가장 어려운 결이다. 회복은 결국 가면을 벗고 자기 자신으로 서는 자리에서 완성된다.",
    ],
    2: [
        "트라우마는 마음의 일이 아니라 몸에 새겨진 상처다. 첫 장이 가르치는 한 마디다. 어둠 속에 계셨던 하나님은 그 어둠을 부정하지 않으셨다. 우리가 가장 외로웠던 그 자리에 그분이 함께 계셨다는 사실을, 시간이 흐른 뒤에야 우리는 알아차린다.",
        "사탄의 전략을 분별하는 일은 신비주의가 아니라 영적 자기보호다. 트라우마를 자기 죄로만 풀어내려 하면 더 깊이 묻힌다. 안전한 품으로의 피난과 깊은 뿌리에 닿는 은혜가 차례로 짚어진다.",
        "신앙과 전문적 도움의 동행이 짚어진다. 영성과 심리학이 충돌하지 않는 자리, 그 둘이 한 결로 흐르는 자리에서 깊은 회복이 일어난다. 마지막 장 — 상처가 은총이 될 때. 상처가 사라지지 않아도, 그 상처 위에 빛이 비치면 은총이 된다.",
    ],
    3: [
        "몸은 영혼의 거울이다. 이 한 권의 첫 마디다. 우리는 너무 자주 영성을 머리의 일로만 다루어 왔다. 그러나 성경은 우리 몸이 영혼의 동행자임을 분명히 증언한다. 하나님은 전인을 치유하신다.",
        "강물처럼 흐르는 치유가 짚어진다. 한 번의 큰 사건이 아니라 매일의 결로 흐르는 회복. 스트레스와 상처의 지도를 그릴 수 있는 사람만이 자기 회복의 자리를 찾을 수 있다. 안식, 가장 거룩한 치유의 자리라는 한 마디가 가장 깊은 자리다.",
        "몸을 돌보는 것이 영성이다. 호흡과 식사와 잠과 운동이 영적 의미를 품는다. 마지막 장 — 전인적 회복의 여정을 걷다. 영혼만의 회복은 없다. 몸과 영혼이 한 결로 회복되는 자리, 그것이 그리스도교의 전인적 영성이다.",
    ],
    4: [
        "감정은 하나님의 선물이다. 첫 장이 던지는 한 마디가 이 책의 결을 정한다. 신앙이 깊을수록 감정이 사라져야 한다는 잘못된 생각을 정직하게 깨는 자리다. 시편의 기도학이 그 증거다.",
        "다윗은 분노도 슬픔도 두려움도 모두 하나님 앞에 펼쳤다. 그 정직함이 시편의 가장 깊은 결이다. 기쁨의 신학과 슬픔의 신학과 분노의 신학이 차례로 짚어진다. 두려움과 불안마저도 신학의 자리에 놓일 수 있다.",
        "마지막 장은 감정을 드리는 삶이다. 감정을 억누르는 영성이 아니라, 감정을 매일 그분 앞에 가져가는 영성. 그 자세가 한 영혼을 가장 정직하게 빚는다. 감정과 신앙은 분리된 두 자리가 아니라, 한 결로 흐르는 자리다.",
    ],
    5: [
        "분노는 두 얼굴을 가진다. 죄로 흐를 수도 있고, 거룩한 분노가 될 수도 있다. 첫 장은 그 두 얼굴을 정직하게 분별하는 자리다. 분노 자체가 죄가 아니라, 다스려지지 않은 분노가 죄로 흐른다.",
        "해가 지기 전에라는 바울의 권면이 짚어진다. 분노를 곪게 두지 않고 매일의 호흡으로 풀어내는 자세. 분노의 뿌리를 찾는 작업이 필요하다. 표면의 분노 아래에 깊은 자리에서 흐르는 다른 감정이 있을 때가 많다.",
        "예수님의 거룩한 분노가 짚어진다. 성전을 청결하게 하실 때의 분노는 거룩했다. 불을 다스리는 지혜와 용서라는 출구를 거쳐, 마지막 장은 온유한 사람의 복이다. 분노가 사라진 자리가 아니라, 분노를 다스린 자리에서 빚어지는 한 영혼의 결이다.",
    ],
    6: [
        "슬픔의 문 앞에 서면 사람들은 빨리 지나가려 한다. 그러나 충분히 슬퍼하지 않은 슬픔은 사라지지 않고 다른 자리에서 다시 솟아난다. 첫 장이 가르치는 한 마디다. 충분히 슬퍼하라.",
        "눈물이 기도가 될 때, 그 자리에서 가장 깊은 만남이 일어난다. 비가 내려야 꽃이 핀다는 한 마디가 슬픔의 신학의 핵심이다. 함께 우시는 하나님 앞에서 우리의 슬픔은 더 이상 외로운 슬픔이 아니다.",
        "애도의 거룩한 여정이 짚어진다. 애도에는 시간이 필요하다. 빠른 회복을 강요하지 않는 자리에서 진짜 회복이 시작된다. 마지막 장 — 슬픔이 남긴 선물. 슬픔은 빼앗긴 게 아니라 우리에게 선물을 남긴다. 더 깊은 영혼, 더 부드러운 마음, 더 다른 사람을 이해하는 자리. 그것이 슬픔이 남긴 결이다.",
    ],
    7: [
        "무너진 자리에서 시작한다. 번아웃은 게으름이 아니다. 너무 오래 자기를 다 쓴 결과다. 첫 장이 그 한 마디를 또렷이 박는다. 그리고 광야의 로뎀나무 아래로 우리를 데려간다. 엘리야가 누웠던 그 자리, 우리도 그 자리에 누울 권리가 있다.",
        "안식이라는 은혜가 짚어진다. 회복은 비범한 일을 하는 자리가 아니라 안식이라는 가장 단순한 은혜를 받아들이는 자리에서 시작된다. 겨울 나무의 침묵, 잎이 다 떨어진 나무가 봄을 준비하는 결을 우리는 그 안식 안에서 발견한다.",
        "죄책감을 내려놓는 일이 가장 어렵다. 무너진 자리에서 가장 먼저 떠오르는 게 죄책감이다. 그러나 그것도 내려놓아야 한다. 무덤에서 정원으로, 마지막 장은 다시 걸어가는 사람이다. 회복은 한 번의 큰 사건이 아니라 다시 걸어가는 매일의 발걸음으로 빚어진다.",
    ],
    8: [
        "내 안의 어린 나를 만나다. 첫 장이 던지는 한 마디다. 우리 안에는 아직 자라지 못한 어린 나가 있다. 받지 못한 것들의 목록을 안고 자란 그 어린 나를 만나는 일은 자기 연민이 아니라 자기 회복의 시작이다.",
        "상처 입은 채 자란 나무라는 표현이 깊다. 우리는 다 그런 나무다. 어떤 가지는 휘었고 어떤 자리는 옹이가 박혔다. 그러나 그 나무도 자랐다. 그리고 아버지라 부를 수 있는 분 앞에서, 어린 나가 비로소 안식을 얻는다.",
        "어린 나를 안으시는 손길이 짚어진다. 우리가 받지 못한 것을 그분이 채우신다. 용서, 치유의 문을 여는 열쇠가 그 다음에 온다. 마지막 장 — 흔적마저 아름답게 하시는 하나님. 흔적이 사라지지 않아도, 그 흔적이 아름다워지는 자리가 있다. 그것이 내면 아이의 치유의 가장 깊은 결이다.",
    ],
    9: [
        "용서하지 못한 감옥이 있다. 그 감옥의 첫 번째 죄수는 용서하지 못한 자기 자신이다. 첫 장이 가르치는 한 마디다. 용서는 상대를 위한 것이 아니라 먼저 자기를 위한 것이라는 결을 정직하게 풀어낸다.",
        "십자가가 용서의 근원이다. 우리가 누구를 용서한다는 것은 우리가 십자가에서 받은 용서를 흘려보내는 일이다. 상처의 이름을 부르는 일이 그 다음 단계다. 막연한 용서가 아니라 구체적 상처의 이름을 부르는 자리에서 진짜 용서가 시작된다.",
        "용서와 화해 사이가 짚어진다. 둘은 같지 않다. 용서는 한 영혼의 일이고, 화해는 두 영혼의 일이다. 일흔 번씩 일곱 번이라는 예수의 가르침과 자신을 용서하는 용기를 거쳐, 마지막 장 — 용서가 연 기적의 문. 용서는 종착점이 아니라 또 다른 자리로 들어가는 문이다.",
    ],
    10: [
        "상처받은 마음의 지도가 있다. 우리 모두 자기 지도를 가지고 있다. 어떤 길은 막혀 있고 어떤 길은 우회로다. 첫 장이 그 지도를 그리는 자리에서 시작한다. 하나님의 형상, 관계 속의 나라는 한 마디가 깊다. 우리는 관계 안에서 빚어진 존재다.",
        "깨진 그릇의 신학이 짚어진다. 깨진 자리에 새 결합제가 들어가면, 그 그릇은 깨지기 전보다 더 단단해질 수도 있다. 일본의 킨츠기 미학이 그것을 시각화한다. 우리의 관계도 그러하다. 깨진 자리가 더 단단한 자리로 빚어질 수 있다.",
        "용서라는 긴 여정과 건강한 경계와 차가운 벽의 분별이 짚어진다. 모든 관계를 회복하는 게 영성이 아니라, 어떤 관계는 거리를 두는 게 영성이다. 공동체, 치유의 자리에서 마지막 결이 흐른다. 마지막 장 — 화해, 더 깊어지는 사랑. 깨졌다가 다시 빚어진 관계가 깨지기 전보다 더 깊을 수 있다는 약속이 이 책의 결이다.",
    ],
}


# 권별 길잡이 — 그 한 권만의 좁고 깊은 화두 (부 길잡이와 차별)
BOOK_GUIDES = {
    1: [
        "내가 회피하고 있는 상처는 무엇이며, 그 상처를 어떤 자리에서 정직하게 응시하기 시작할 수 있는가.",
        "거짓 자아의 가면이 무너지는 자리를, 나는 어떻게 받아들이고 있는가.",
        "있는 그대로의 나로 선다는 것이, 내 일상의 어떤 자리에서 살아나고 있는가.",
    ],
    2: [
        "어둠 속에 계셨던 하나님이라는 한 마디를, 내 가장 어두웠던 자리에서 어떻게 발견하고 있는가.",
        "신앙과 전문적 도움의 동행이 충돌하지 않는 자리를, 나는 어떻게 분별하고 있는가.",
        "상처가 은총이 된다는 한 마디가, 내 흉터 위에 어떻게 빛으로 비치고 있는가.",
    ],
    3: [
        "몸이 영혼의 거울이라는 한 마디가, 내 일상의 어떤 자리를 다시 보게 하는가.",
        "안식이 가장 거룩한 치유의 자리라는 약속을, 내 일주일은 어떻게 살아내고 있는가.",
        "전인적 회복의 여정 위에서, 나는 몸을 어떻게 영성의 동행자로 대하고 있는가.",
    ],
    4: [
        "내가 하나님 앞에 가져가지 못하고 억누르고 있는 감정은 무엇인가.",
        "시편의 기도학이 가르치는 정직한 감정의 자리를, 내 기도는 어떤 결로 살아내고 있는가.",
        "감정을 드리는 삶이라는 한 마디가, 내 어떤 결정과 어떤 호흡 안에서 살아나고 있는가.",
    ],
    5: [
        "분노가 죄로 흐를 때와 거룩한 분노가 될 때의 차이를, 나는 어떻게 분별하고 있는가.",
        "내 분노의 뿌리를 정직하게 찾아본다면, 그 자리에는 무엇이 있는가.",
        "온유한 사람의 복이라는 한 마디를, 내 일상은 어떤 결로 살아내고 있는가.",
    ],
    6: [
        "내가 충분히 슬퍼하지 못하고 빨리 지나가려 했던 슬픔의 자리는 어디인가.",
        "눈물이 기도가 되는 자리를, 나는 어떤 결로 만들어 가고 있는가.",
        "슬픔이 남긴 선물이 있다면, 그 선물은 내 안에서 어떻게 자라고 있는가.",
    ],
    7: [
        "내가 통과하고 있는 번아웃의 자리는 어디이며, 그 자리에서 가장 먼저 받아들여야 할 은혜는 무엇인가.",
        "겨울 나무의 침묵 같은 자리에서, 나는 보이지 않는 자라남을 어떻게 신뢰하고 있는가.",
        "다시 걸어가는 사람이라는 정체성을, 내 어떤 발걸음에서 살아내고 있는가.",
    ],
    8: [
        "내 안의 어린 나가 받지 못한 것들의 목록은 무엇이며, 그 목록을 어디로 가져가고 있는가.",
        "아버지라 부를 수 있는 분 앞에서, 어린 나가 어떻게 안식을 얻고 있는가.",
        "흔적마저 아름답게 하시는 하나님의 결이, 내 흉터 위에 어떻게 비치고 있는가.",
    ],
    9: [
        "내가 용서하지 못한 자리는 어디이며, 그 감옥의 첫 번째 죄수는 누구인가.",
        "용서와 화해의 차이를, 나는 어떤 관계에서 분별하고 있는가.",
        "자신을 용서하는 용기가, 내 안에서 어떻게 자라고 있는가.",
    ],
    10: [
        "내 상처받은 마음의 지도에서 막힌 길과 우회로는 어디인가.",
        "깨진 그릇의 신학이 가르치는 한 마디 — 깨진 자리가 더 단단해질 수 있다는 약속을, 내 관계는 어떻게 살아내고 있는가.",
        "건강한 경계와 차가운 벽의 차이를, 내 어떤 관계에서 분별하고 있는가.",
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
  <div style="color:#888;font-size:0.88em;margin-top:0.3em">원본 ISBN {b['isbn']} · G05 제 {b['src_no']:02d} 권</div>
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
<h3 style="color:#0F1E3C;margin-top:1.5em">흉터 위에 비추는 빛</h3>
<p>이로써 G05 열 권의 묵상이 한 권으로 닫힙니다. 상처받은 영혼의 회복에서 시작해 관계의 상처를 넘어서기에 이르기까지, 내면 치유의 결을 네 갈래로 모아 함께 걸어왔습니다. 처음에는 흩어져 있던 한 권 한 권의 묵상이 한 호흡으로 이어 붙고 나니, 사이를 흐르고 있던 결이 비로소 또렷해졌습니다.</p>
<p>이 책이 묻고자 했던 한 가지 물음은 분명합니다. <em>흉터를 안고도 빛으로 걸어갈 수 있는가.</em> 상처를 정직하게 응시하는 자리와, 감정을 하나님 앞에 가져가는 자리와, 무너진 자리에서 다시 일어나는 결과, 관계 안에서 빛이 되는 자리 — 그 넷이 그 답의 네 갈래였습니다.</p>
<p><strong>1부에서 우리는 상처를 마주했습니다</strong>. 거짓 자아의 가면을 내려놓고 있는 그대로의 나로 서는 자리, 어둠 속에 함께 계셨던 하나님을 다시 발견하는 자리, 그리고 몸과 영혼이 한 결로 회복되는 전인적 영성의 자리에 함께 섰습니다. 상처를 부정하지 않는 자세, 그것이 회복의 첫 걸음이었습니다.</p>
<p><strong>2부에서 우리는 감정과 함께 걸었습니다</strong>. 시편의 기도학이 가르치는 정직한 감정의 자리, 분노의 두 얼굴을 분별하는 자리, 그리고 충분히 슬퍼하는 자리에서 눈물이 기도가 되는 결을 함께 보았습니다. 감정과 신앙은 분리된 두 자리가 아니라 한 결로 흐른다는 것을 우리는 다시 새겼습니다.</p>
<p><strong>3부에서 우리는 무너진 자리에서 다시 일어나는 결</strong>을 보았습니다. 광야의 로뎀나무 아래에서 다시 걸어가는 사람으로의 여정, 그리고 우리 안의 어린 나가 아버지의 손길 안에서 안식을 얻는 자리. 흔적마저 아름답게 하시는 하나님의 결을, 두 권의 회복 위에서 함께 발견했습니다.</p>
<p><strong>4부에서 우리는 관계 안에서 빛이 되는 자리</strong>에 도달했습니다. 용서하지 못한 감옥에서 용서가 연 기적의 문까지, 그리고 깨진 그릇의 신학에서 더 깊어지는 사랑까지. 내면 치유의 마지막 자리는 결국 관계라는 것을, 그리고 그 관계 안에서 빛이 흘러나간다는 것을 함께 보았습니다.</p>
<p>이 책의 가장 단단한 한 마디는 표제에 이미 담겨 있습니다 — <em>흉터 위의 빛.</em> 흉터는 사라지지 않을 수 있습니다. 그러나 그 흉터 위에 빛이 비치고, 그 빛이 다시 다른 영혼에게 흘러가는 결이 그리스도인의 치유의 가장 깊은 자리입니다. 흉터가 부끄러움이 아니라 증언이 되는 자리, 그것이 우리가 걸어온 길의 결론입니다.</p>
<p>이 책을 덮으신 뒤에도 묵상은 끝나지 않습니다. 한 장씩 다시 펼쳐 읽어도 좋고, 한 단락만 천천히 반복해 읽어도 좋습니다. 흉터를 회피하던 자리에서 흉터를 응시하는 자리로 한 결이라도 옮겨 가셨다면, 그것만으로도 G05 열 권을 한 권으로 묶은 이유는 충분할 것입니다.</p>
<p>이제 100권 시리즈는 G06으로, G07로, 그리고 마지막 G10까지 흘러갑니다. 흉터 위에 비추는 빛의 결은 이 한 권에 모였습니다. 다음 그룹에서 또 다른 깊은 묵상으로 다시 만나기를 기도합니다. 주님의 평강이 여러분의 오늘 위에 충만히 임하시기를 축복합니다.</p>
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
    uuid_id = f"omnibus-g05-{today_compact}-{datetime.now().strftime('%H%M%S')}"

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
    <dc:description>{proj['subtitle']} — G05 10권 종합본</dc:description>
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
    print("ISBN 발급 시 batch_books_g05_omnibus.json의 isbn 필드에 입력 후 재빌드.")


if __name__ == "__main__":
    main()
