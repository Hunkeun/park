# -*- coding: utf-8 -*-
"""
G01 10권 종합책 "영원의 문턱에서" epub 빌더.

입력:
  - batch_books_g01_omnibus.json (메타·4부 구조)
  - tmp/g01_omnibus_extracted.json (10권 본문 추출본)
  - G01 epub 중 한 권 (CSS 추출용)

출력:
  - ~/Downloads/전자책/영원의_문턱에서_YYYYMMDD_종합책.epub

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
META_PATH = PROJECT / "batch_books_g01_omnibus.json"
EXTRACT_PATH = PROJECT / "tmp" / "g01_omnibus_extracted.json"
SAMPLE_EPUB = Path.home() / "Downloads" / "전자책" / "천국의_문턱에서_20260418.epub"
OUT_DIR = Path.home() / "Downloads" / "전자책"
OUT_BACKUP_DIR = PROJECT / "tmp"  # 보조 사본


def get_css():
    """샘플 epub에서 CSS 추출."""
    with zipfile.ZipFile(SAMPLE_EPUB, "r") as z:
        return z.read("OEBPS/styles/style.css").decode("utf-8")


def get_cover_image():
    """전용 종합책 표지 사용 (없으면 샘플로 폴백)."""
    custom = PROJECT / "tmp" / "g01_omnibus_cover.jpg"
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
  <p><strong>구성</strong>　G01 10권 종합책 (4부 70장)</p>
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
    <p>이 책은 100권 영성 시리즈 G01(영계·사후세계) 10권의 본문을 거의 그대로 4부 구조로 재편집하여 한 권으로 묶은 종합본입니다.</p>
    <p>각 권의 원본 ISBN 및 출간 정보는 본문 권별 도입 페이지에 명기되어 있습니다.</p>
  </div>
</div></div>"""
    return xhtml_doc("판권", body)


def build_preface_xhtml() -> str:
    body = """<div style="padding:2em 1.5em;line-height:1.9;font-size:1em;color:#222">
<h2 style="color:#0F1E3C;border-bottom:1px solid #C8B99A;padding-bottom:0.5em">여는 글</h2>
<h3 style="color:#0F1E3C;margin-top:1.5em">보이지 않는 세계의 문 앞에서</h3>
<p>모든 그리스도인은 두 세계의 경계에서 살아갑니다. 손에 잡히는 오늘과 손에 잡히지 않는 영원. 보이는 세상의 분주함과 보이지 않는 세계의 고요함. 그 두 세계 사이에 한 영혼이 다리처럼 놓여 있고, 우리는 그 다리 위에서 매일을 살아갑니다.</p>
<p>이 책은 그 다리 위에서 발걸음을 가다듬으려는 작업입니다. 죽음의 문턱부터 부활의 아침까지, 영혼의 행로부터 천사의 사역까지, 낙원과 지옥의 갈림길부터 마지막 심판의 의미까지 — 사후세계라는 한 단어 안에 담긴 그리스도교의 가장 깊은 묵상을 열 갈래로 펼쳐 놓았습니다.</p>
<p>이 책은 100권 영성 시리즈의 첫 그룹 G01을 한 권으로 묶은 종합본입니다. 열 권 각각의 본문을 거의 그대로 유지하면서, 그 사이를 흐르고 있던 결을 네 갈래로 모았습니다. 한 권씩 따로 읽을 때 보이지 않던 결이 한 권으로 모이고 나니 비로소 또렷이 드러난다는 것이, 종합이라는 작업의 가장 정직한 보람일 것입니다.</p>
<p>네 갈래는 이렇게 흐릅니다. 죽음의 문턱과 그 너머의 빛, 영혼의 정체에 대한 정직한 응시, 보이지 않는 세계의 풍경, 그리고 마지막 일들 — 부활과 심판에 이르는 영원의 자리. 이 넷은 따로 흐르는 것 같으면서도 결국 한 강을 이룹니다.</p>
<p><strong>1부 — 죽음의 문턱</strong>은 죽음 앞에 정직하게 선 자의 시선을 보고, <strong>2부 — 영혼의 정체</strong>는 영혼이 무엇이고 어디로 가는가를 묻습니다. <strong>3부 — 보이지 않는 세계</strong>는 낙원·영계·천사로 이어지는 베일 너머의 풍경을 그리고, <strong>4부 — 마지막 일들</strong>은 부활과 심판에서 모든 길이 만나는 자리를 응시합니다.</p>
<p>이 책은 사후세계의 모든 질문에 답하지 않습니다. 다만 그 질문들 앞에서 두려워하지 않을 수 있는 자리, 곧 영원의 입장에서 오늘을 다시 보는 묵상의 자리로 한 사람을 데려가려 합니다. 답을 서두르기보다 호흡을 가다듬는 자리, 두려움 너머의 약속을 함께 응시하는 자리. 이 책이 그런 자리가 되어 드린다면, G01 열 권을 한 권으로 묶은 의미는 충분할 것입니다.</p>
<p>한 번에 다 읽어내실 책이 아닙니다. 한 장씩, 한 묵상씩 호흡을 따라 가져가시면 됩니다. 이제 첫 장을 펼쳐 주십시오. 보이지 않는 세계의 문 앞에서, 그러나 두려움이 아니라 약속을 보면서, 한 호흡씩 함께 걸어가 봅시다.</p>
</div>"""
    return xhtml_doc("여는 글", body)


PART_INTROS = {
    1: {
        "headline": "마지막 숨, 첫 빛",
        "paragraphs": [
            "사람은 누구나 죽음의 문 앞에 한 번은 섭니다. 그러나 그 문 앞에 서는 자세는 사람마다 다릅니다. 어떤 이는 두려움으로, 어떤 이는 회한으로, 어떤 이는 약속을 보면서 그 문을 마주합니다.",
            "어둠의 골짜기는 분명히 있습니다. 새벽 직전의 밤은 가장 깊고, 고난의 터널은 그 끝이 보이지 않을 때가 많습니다. 그러나 성경은 그 어둠 한복판에서도 한 가지 빛을 가리킵니다. 십자가의 그 빛, 그리고 그 빛이 지나가고 난 자리에 떠오른 부활의 아침입니다.",
            "그리스도인에게 죽음은 끝이 아닙니다. 마지막 숨이 멎는 자리에서 첫 빛이 시작되는 그 신비를, 우리는 거짓 위로의 언어가 아니라 정직한 묵상의 언어로 만나야 합니다. 두려움을 부정하지 않으면서, 그러나 두려움이 마지막 단어가 되도록 두지 않는 자세입니다.",
            "이 부의 두 권은 죽음의 문턱과 그 너머의 빛을 차례로 응시합니다. 첫 권 「천국의 문턱에서」는 죽음 앞에 선 한 영혼이 어떻게 오늘을 다시 보는가를 묻고, 두 번째 권 「죽음 너머의 빛」은 어둠과 고난의 터널을 지나 부활의 아침에 이르는 여정을 그려냅니다.",
            "죽음의 문턱은 두려움의 자리이면서 동시에 가장 또렷한 자리입니다. 그 문 앞에 서 본 사람만이 오늘이라는 하루의 무게를 진실로 측량할 수 있습니다. 마지막 숨과 첫 빛이 만나는 자리에서, 두려움 너머의 약속을 함께 응시해 보십시오.",
        ],
        "guides": [
            "죽음의 문 앞에 서 있다고 가정한다면, 나는 오늘이라는 하루를 어떻게 다시 살겠는가.",
            "어둠의 골짜기 한복판에서, 나는 새벽이 곧 온다는 약속을 어떻게 붙들고 있는가.",
            "마지막 숨이 멎는 자리에서 첫 빛이 시작된다는 한 마디를, 나는 두려움이 아니라 약속으로 받고 있는가.",
            "이 부를 읽으며, 죽음의 문턱과 그 너머의 빛이 어떻게 한 점에서 만나는가에 주목해 보십시오.",
        ],
    },
    2: {
        "headline": "영혼이라는 비밀",
        "paragraphs": [
            "영혼은 그리스도교가 가장 진지하게 다루어 온 비밀입니다. 영혼이 무엇인지, 어디서 와서 어디로 가는지, 그리고 몸과 어떤 관계인지 — 이 물음들은 단순한 신학적 호기심이 아니라 한 사람이 자기 정체를 정직하게 묻는 자리입니다.",
            "성경은 영혼을 추상이 아니라 한 영혼의 행로로 그립니다. 한 번 죽는 것이 정해진 일이며, 그 다음에는 심판이 있다는 분명한 한 마디가 있습니다. 그 사이에는 중간상태라는 신비가 놓여 있고, 마지막에는 영원의 두 길이 갈라집니다.",
            "그리고 영혼은 결코 몸과 분리된 무엇이 아닙니다. 흙으로 빚으신 사랑, 악기와 음악의 비유, 말씀이 육신이 되신 신비, 성전 된 몸 — 성경은 거듭 영혼과 몸이 한 결로 흐르는 동행자임을 증언합니다. 부활은 영혼만의 사건이 아니라 몸의 귀환입니다.",
            "그렇다면 영원한 생명은 무엇입니까. 미래 어딘가에 시작되는 것이 아니라 오늘 이 순간에 이미 들어와 있습니다. 영생은 죽은 뒤의 사건이 아니라 살아 있는 동안 시작되는 한 결의 흐름이며, 예수께서 당신이 곧 영생이라 말씀하신 그 자리가 바로 그 흐름의 근원입니다.",
            "이 부의 세 권은 각각 다른 각도에서 영혼이라는 비밀을 비춥니다. 「영혼은 어디로 가는가」는 영혼의 행로를, 「몸과 영혼의 경계」는 몸과 영혼의 통전성을, 「영원한 생명의 실체」는 오늘부터 시작되는 영생의 결을 다룹니다.",
            "영혼·몸·영생이 한 강을 이루며 흐르는 자리로 함께 들어가십시오.",
        ],
        "guides": [
            "내 영혼은 어디서 와서 어디로 가는가. 그 행로 위에 나는 지금 어느 지점에 서 있는가.",
            "몸과 영혼이 한 결로 동행한다면, 나는 내 몸을 영성의 동행자로 대하고 있는가 아니면 그릇으로만 다루고 있는가.",
            "영원한 생명이 오늘 이미 시작되어 있다는 한 마디를, 내 일상은 어떻게 증언하고 있는가.",
            "이 부를 읽으며, 영혼이라는 비밀이 추상에서 일상으로 내려오는 그 결을 따라가 보십시오.",
        ],
    },
    3: {
        "headline": "베일 너머의 풍경",
        "paragraphs": [
            "보이는 세상이 전부가 아닙니다. 그 너머에 또 한 세계가 있고, 그 세계는 우리의 일상보다 더 실재합니다. 다만 베일 한 겹이 그 풍경을 가리고 있을 뿐입니다.",
            "성경은 그 베일 너머의 풍경을 부정하지 않습니다. 낙원과 지옥은 추상이 아니라 영원의 두 갈림길이며, 영계는 신비주의의 자리가 아니라 하나님이 지금도 말씀하시는 자리입니다. 그리고 천사들은 동화의 인물이 아니라 하나님의 사자로서 보호와 섬김의 사역을 감당하고 있습니다.",
            "베일 너머를 본다는 것은 환상을 좇는 일이 아닙니다. 오히려 보이는 세상의 무게를 다시 측정하는 일입니다. 영원의 두 갈림길을 본 사람은 오늘의 한 결단을 가볍게 여기지 않고, 영계의 음성을 듣는 사람은 일상의 분주함 속에서도 영혼의 주파수를 잃지 않습니다.",
            "기도는 그 베일 너머와 잇는 통로입니다. 일방통행이 아니라 쌍방향의 대화이며, 성령의 세미한 음성을 듣는 자리이며, 꿈과 환상으로 다가오는 밤의 계시까지 분별하는 자리입니다. 분별의 은사는 베일 너머에서 들려오는 모든 소리를 가려 듣는 능력입니다.",
            "이 부의 세 권은 베일 너머의 풍경을 차례로 그려냅니다. 「낙원과 지옥 사이」는 영원의 두 갈림길을, 「영계의 언어」는 보이지 않는 세계와의 소통을, 「천사들의 사역」은 하나님의 사자들이 우리 곁에서 감당하는 사역을 다룹니다.",
            "베일이 한 겹 들리는 자리로 함께 들어가 보십시오.",
        ],
        "guides": [
            "영원의 두 갈림길이 오늘이라는 하루 안에 이미 시작되어 있다는 것을, 나는 어떻게 받아들이고 있는가.",
            "기도가 일방의 외침이 아니라 쌍방향의 대화라면, 나는 듣는 자리에 얼마만큼 머물고 있는가.",
            "천사가 동화의 인물이 아니라 하나님의 사자라면, 나는 일상에서 그 보호와 섬김을 어떻게 감지하고 있는가.",
            "이 부를 읽으며, 베일 너머의 풍경이 보이는 세상의 무게를 어떻게 다시 측량하는가에 주목해 보십시오.",
        ],
    },
    4: {
        "headline": "시간의 끝에서",
        "paragraphs": [
            "모든 흐름은 한 점에서 만납니다. 죽음의 문턱과 영혼의 행로와 베일 너머의 풍경이 결국 도달하는 그 한 점은 마지막 일들 — 부활과 심판의 자리입니다.",
            "부활은 추상이 아니라 사건입니다. 빈 무덤의 아침은 한 사람의 환상이 아니라 여러 증인이 함께 본 역사적 자리이며, 무덤이 열릴 수밖에 없었던 정황은 우연이 아니라 약속의 성취입니다. 사도 바울이 씨앗의 신학으로 풀어낸 부활의 결은, 죽음이 끝이 아니라 새로운 양식으로의 변화임을 증언합니다.",
            "두려움에서 담대함으로 — 부활이 한 영혼에게 일으키는 변화는 이 한 마디로 모입니다. 골고다 이전의 제자들과 부활 이후의 제자들이 같은 사람일 수 없었던 이유가 거기 있습니다. 그리고 우리는 그 부활의 증인으로 살도록 부름받았습니다.",
            "심판은 두려움의 단어가 아니라 회복의 단어입니다. 공의로우신 하나님 앞에서 모든 장부가 정리되는 날, 사랑과 공의가 만나는 자리, 그리고 마침내 억울함이 없는 세상이 시작되는 그 날입니다. 은혜 안에서의 책임이 어떤 무게를 가지는가를 우리는 거기서 배웁니다.",
            "이 부의 두 권은 마지막 일들을 정면으로 응시합니다. 「부활의 증거들」은 빈 무덤의 아침부터 부활의 증인으로 사는 자세까지를, 「마지막 심판의 의미」는 심판이라는 무거운 단어 앞에서 그것이 왜 사랑과 공의의 만남인가를 다룹니다.",
            "시간의 끝이 새로운 시작이 되는 그 자리로 함께 들어가십시오.",
        ],
        "guides": [
            "부활이 추상이 아니라 사건이라면, 나는 그 증거 앞에서 두려움에서 담대함으로 어떻게 옮겨 가고 있는가.",
            "심판이 두려움이 아니라 회복의 단어라면, 나는 그 날을 어떤 자세로 준비하고 있는가.",
            "은혜 안에서의 책임이라는 한 마디를, 내 일상은 어떻게 살아내고 있는가.",
            "이 부를 읽으며, 시간의 끝이 어떻게 새로운 시작과 만나는가를 따라가 보십시오.",
        ],
    },
}


# 권별 요약 (각 책 진입부 — 3단락, 약 70% 분량)
# 마지막 단락의 핵심 한 문장은 3번째 단락 끝에 흡수
BOOK_SUMMARIES = {
    1: [
        "죽음의 문 앞에 한 영혼이 선다. 그 자리는 두려움의 자리이지만 동시에 가장 또렷한 자리다. 그 문 앞에 서 본 사람만이 오늘이라는 하루의 무게를 진실로 측량할 수 있다. 첫 권은 그 문턱에서 시작한다.",
        "저자는 죽음을 회피하지 않고 정면으로 응시한다. 그러면서도 두려움을 마지막 단어로 두지 않는다. 번데기가 나비가 되듯, 찰나가 영원과 만나듯, 죽음의 문턱은 끝이 아니라 다른 양식의 시작이라는 것을 그리스도인의 시선으로 풀어 간다.",
        "걱정의 크기를 다시 재고, 부활의 빛 아래에서 오늘의 선택을 다시 한다. 천국의 문턱에 선 자의 시선으로 일상을 보면 모든 것이 다르게 측량된다. 가벼운 것이 무거워지고 무거운 것이 가벼워지는 자리, 그것이 이 책이 독자를 데려가려는 묵상의 자리다.",
    ],
    2: [
        "어둠의 골짜기는 분명히 있다. 새벽 직전의 밤은 가장 깊고, 고난의 터널은 끝이 보이지 않을 때가 많다. 그러나 성경은 그 어둠 한복판에서도 한 빛을 가리킨다. 십자가의 그 빛이며, 그 빛이 지나간 자리에 떠오른 부활의 아침이다.",
        "저자는 어둠을 부정하지 않고 그 결을 따라간다. 어둠이 없는 자리에서 빛은 빛이 아니다. 가장 깊은 어둠이 가장 또렷한 빛을 알아보게 하는 결을 그리스도인의 시선으로 풀어낸다.",
        "마지막 장은 빛이신 하나님과의 동행이다. 영광의 소망이 단지 미래의 장식이 아니라 오늘의 발걸음을 가볍게 하는 한 결의 빛이라는 것을 정직한 묵상의 언어로 증언한다. 죽음 너머의 빛은 죽음 이후가 아니라 오늘 이미 비추기 시작한 빛이다.",
    ],
    3: [
        "죽음이란 무엇인가. 영혼은 어디서 와서 어디로 가는가. 이 한 권은 그 두 물음을 가장 정직한 자리에서 묻는다. 한 번 죽는 것이 정해진 일이며 그 다음에는 심판이 있다는 성경의 한 마디를 신학적 추상이 아니라 한 영혼의 행로로 그려낸다.",
        "중간상태의 신비가 짚어진다. 낙원과 음부, 그 사이의 시간은 단순한 대기실이 아니라 부활을 기다리는 한 결의 자리다. 그리고 심판대 앞에서, 천국과 지옥이라는 영원의 두 갈림길 앞에서 한 영혼이 어떻게 서는가를 묻는다.",
        "마지막 장은 오늘을 사는 영원의 사람이다. 영원이 미래의 어딘가가 아니라 오늘의 한복판에 이미 들어와 있다는 것을 안 사람은, 한 호흡 한 호흡을 다른 무게로 살아간다. 영혼의 행로를 본 사람만이 오늘을 영원의 입장으로 살 수 있다.",
    ],
    4: [
        "성경은 우리 몸을 영혼의 그릇이 아니라 동행자로 본다. 흙으로 빚으신 사랑, 곧 인간의 육체는 결코 폄하되어야 할 재료가 아니라 영혼과 함께 한 결을 이루는 신비다. 저자는 그 신비를 악기와 음악의 비유로 풀어낸다.",
        "말씀이 육신이 되신 성육신의 사건은 몸과 영혼의 통전성을 가장 깊이 증언한다. 우리 몸이 성전이 된다는 한 마디는, 몸이 영혼을 위한 도구가 아니라 영성이 흐르는 자리 그 자체임을 가리킨다. 연약함 속의 은혜는 그 자리에서 발견되는 결이다.",
        "마지막은 부활의 소망과 전인적 예배다. 부활은 영혼만의 사건이 아니라 몸의 귀환이며, 예배는 머리만의 동의가 아니라 몸과 마음과 영이 함께 드리는 한 결의 응답이다. 몸과 영혼의 경계라는 제목은 결국 그 둘이 결코 분리되지 않는다는 한 마디로 모인다.",
    ],
    5: [
        "영원한 생명은 미래 어딘가에 시작되는 것이 아니다. 영생은 오늘 이미 시작되어 있다. 이 한 권은 그 단순하지만 잊기 쉬운 한 마디를 가장 깊은 자리에서 풀어낸다. 씨앗 안에 이미 영원이 담겨 있듯, 오늘이라는 하루 안에 영생이 이미 들어와 있다.",
        "예수께서는 당신이 곧 영생이라 말씀하셨다. 영생은 한 교리가 아니라 한 인격이며, 한 약속이 아니라 한 현존이다. 저자는 그 한 인격과의 동행이 영생의 본질임을 약속의 말씀들을 차례로 붙들며 보여준다.",
        "지금 누리는 영원한 생명, 죽음을 이기는 생명, 그리고 영원을 품고 오늘을 사는 자세 — 이 셋이 한 결로 흐른다. 영생을 안 사람은 죽음 앞에서 떨지 않고, 영원을 품은 사람은 오늘을 가볍게 살지 않는다. 영생은 죽은 뒤의 사건이 아니라 살아 있는 동안의 결이다.",
    ],
    6: [
        "영원의 두 문이 있다. 낙원과 지옥, 그것은 동화의 비유가 아니라 성경이 가장 진지하게 증언하는 두 갈림길이다. 이 한 권은 그 두 문을 추상이 아니라 실재로 마주한다.",
        "낙원은 영원한 머묾의 자리가 아니라 부활을 기다리는 중간의 자리이며, 지옥은 응징의 무대가 아니라 하나님의 임재가 닿지 않는 자리의 정직한 표현이다. 저자는 그 둘을 흥미 본위의 묘사가 아니라 신학의 정직함으로 짚는다.",
        "심판대 앞에서, 오늘의 선택, 구원의 확신, 그리고 영원을 품은 삶이 차례로 펼쳐진다. 영원의 두 갈림길은 죽은 뒤에 갈라지는 것이 아니라 오늘이라는 하루의 결단들이 쌓여 만들어지는 길이다. 그 길 위에 오늘의 발걸음이 있다.",
    ],
    7: [
        "하나님은 지금도 말씀하신다. 영계는 신비주의의 자리가 아니라 하나님의 음성이 지금도 흘러오는 자리다. 다만 우리가 영혼의 주파수를 그 음성에 맞추지 못할 때 그 자리는 닫혀 있는 듯 보인다.",
        "기도는 일방의 외침이 아니라 쌍방향의 대화다. 성령의 세미한 음성, 꿈과 환상으로 다가오는 밤의 계시까지 — 영계의 언어는 다양한 결로 흐른다. 저자는 그 결을 미신적 자극이 아니라 분별의 영성으로 다룬다.",
        "마지막은 듣는 자에서 전하는 자로의 전환이다. 영계의 음성을 듣는 자리는 자기 안에 닫혀 있는 자리가 아니라, 그 음성을 한 시대 한 사람에게 전하기 위한 통로의 자리다. 분별의 은사는 영계의 모든 소리를 가려 듣는 능력이며, 듣는 자리가 곧 보내심의 자리가 된다.",
    ],
    8: [
        "천사는 동화의 인물이 아니다. 성경은 천사를 하나님의 사자로, 곧 하나님의 명령을 수행하는 영적 존재로 분명히 증언한다. 이 한 권은 그 존재를 신비주의도 합리주의도 아닌 자리에서 정직하게 다룬다.",
        "천사의 사역은 다양하다. 계시를 전하는 사역, 보호하는 사역, 하나님의 군대로서 영적 전쟁을 감당하는 사역, 그리고 섬김의 영으로 우리 일상에 함께하는 사역. 그 모든 사역이 하나님의 뜻 안에서 한 결로 흐른다는 것을 차례로 살핀다.",
        "예수 그리스도와 천사의 관계가 짚어지면서 한 가지가 분명해진다. 천사는 결코 경배의 대상이 아니라 함께 그분을 경배하는 동료다. 마지막은 천사와 함께 사는 일상이다. 보이지 않지만 우리 곁에서 사역하는 그 영들의 결을 감지하며 사는 자세가 무엇인지를 묻는다.",
    ],
    9: [
        "빈 무덤의 아침은 한 사람의 환상이 아니라 여러 증인이 함께 본 역사적 자리다. 이 한 권은 부활을 추상이 아니라 사건으로 다룬다. 증인들의 목소리가 어떻게 한 결로 모이는가를 차례로 짚는다.",
        "무덤이 열릴 수밖에 없었던 정황들이 정리되고, 사도 바울의 씨앗 신학을 통해 부활의 결이 풀려나간다. 한 알의 씨앗이 죽지 않으면 한 알 그대로 있고 죽으면 많은 열매를 맺는다는 그 한 마디 안에 부활의 핵심이 담겨 있다.",
        "두려움에서 담대함으로 — 부활이 한 영혼에게 일으키는 변화는 이 한 마디로 모인다. 골고다 이전의 제자들과 부활 이후의 제자들이 같은 사람일 수 없었던 이유가 거기 있다. 마지막은 나의 죽음과 부활 신앙, 그리고 부활의 증인으로 사는 자세다. 부활을 본 사람은 결코 같은 자리에 머물지 못한다.",
    ],
    10: [
        "심판이라는 단어는 무겁다. 그러나 그 무게는 두려움의 무게가 아니라 회복의 무게다. 이 한 권은 그 단어 앞에서 정직하게 멈춘다. 공의로우신 하나님 앞에서 모든 장부가 정리되는 날을, 한 영혼의 두려움이 아니라 한 시대의 회복으로 본다.",
        "사랑과 공의는 분리되지 않는다. 심판은 사랑이 마침내 공의로 완성되는 자리이며, 은혜 안에서의 책임은 그 둘이 만나는 자리에서 한 영혼에게 부여되는 무게다. 저자는 그 무게를 회피하지 않고 정직하게 풀어낸다.",
        "억울함이 없는 세상이 시작된다. 모든 눈물이 닦이고, 가려진 진실이 드러나며, 늦었다고 여겼던 정의가 마침내 자기 자리를 찾는 그 날이다. 마지막 장은 그 날을 준비하는 오늘이다. 그 날을 본 사람은 오늘이라는 하루를 결코 가볍게 살지 못한다.",
    ],
}


# 권별 길잡이 — 그 한 권만의 좁고 깊은 화두 (부 길잡이와 차별)
BOOK_GUIDES = {
    1: [
        "내가 죽음의 문 앞에 서 있다고 가정하면, 오늘이라는 하루를 어떻게 다시 살겠는가.",
        "번데기와 나비의 비유처럼, 지금 내가 벗어야 할 옷과 입어야 할 옷은 무엇인가.",
        "부활의 빛 아래에서 내가 다시 측량해야 할 걱정의 크기는 어떤 것인가.",
    ],
    2: [
        "내가 지금 통과하고 있는 어둠의 골짜기는 어디이며, 그 골짜기 끝에 약속된 빛을 나는 어떻게 붙들고 있는가.",
        "고난이라는 터널 안에서 십자가의 빛은 내게 어떤 결로 보이고 있는가.",
        "영광의 소망이 미래의 장식이 아니라 오늘의 발걸음을 가볍게 한다면, 그 빛은 내 어떤 일상에 닿고 있는가.",
    ],
    3: [
        "한 번 죽는 것이 정해진 일이라는 한 마디 앞에서, 나는 오늘을 어떤 무게로 살고 있는가.",
        "중간상태의 신비를 한 영혼의 행로로 받아들인다면, 그 사이의 시간을 나는 어떻게 그리고 있는가.",
        "오늘을 사는 영원의 사람이라는 표현이, 내 한 호흡 한 호흡에 어떻게 닿고 있는가.",
    ],
    4: [
        "흙으로 빚으신 사랑이라는 한 마디가, 내 몸을 보는 시선을 어떻게 바꾸고 있는가.",
        "성전 된 몸을 살아간다는 것은, 내 일상의 어떤 자리에서 가장 분명하게 드러나는가.",
        "전인적 예배 — 머리·가슴·몸이 함께 드리는 응답을, 나는 오늘 어떻게 살아내고 있는가.",
    ],
    5: [
        "영생이 미래가 아니라 오늘 이미 시작되어 있다는 것을, 내 일상은 어떻게 증언하고 있는가.",
        "예수께서 곧 영생이라는 한 마디를, 나는 한 교리가 아니라 한 인격으로 만나고 있는가.",
        "영원을 품고 오늘을 산다는 자세는, 내 어떤 결정과 어떤 관계 안에서 드러나는가.",
    ],
    6: [
        "영원의 두 갈림길이 오늘의 결단들로 빚어진다는 것을, 나는 어떻게 받아들이고 있는가.",
        "낙원이 영원한 머묾이 아니라 부활을 기다리는 중간의 자리라면, 그 결을 나는 어떻게 그리고 있는가.",
        "구원의 확신이 안주의 자리가 아니라 책임의 자리라면, 나는 어떤 결단으로 그 자리에 서 있는가.",
    ],
    7: [
        "하나님은 지금도 말씀하신다는 약속 앞에서, 나는 듣는 자리에 얼마만큼 머물고 있는가.",
        "기도가 일방의 외침이 아니라 쌍방향의 대화라는 것을, 내 기도는 어떻게 살아내고 있는가.",
        "듣는 자에서 전하는 자로의 전환이, 내 일상의 어떤 부르심으로 다가오고 있는가.",
    ],
    8: [
        "천사가 동화의 인물이 아니라 하나님의 사자라면, 나는 일상에서 그 보호와 섬김을 어떻게 감지하고 있는가.",
        "섬김의 영들이 우리 곁에서 사역한다는 것을, 나는 두려움이 아니라 위안으로 받고 있는가.",
        "예수 그리스도와 함께 그분을 경배하는 동료로서의 천사들을, 나는 어떤 자리에서 만나고 있는가.",
    ],
    9: [
        "빈 무덤의 아침이 한 사람의 환상이 아니라 사건이라는 사실 앞에서, 내 부활 신앙은 어떤 무게를 갖는가.",
        "씨앗 신학 — 죽지 않으면 한 알 그대로 있고 죽으면 많은 열매를 맺는다는 그 결을, 나는 어떻게 살아내고 있는가.",
        "두려움에서 담대함으로의 변화가, 내 안에서 어떤 자리에서 일어나고 있는가.",
    ],
    10: [
        "심판이 두려움이 아니라 회복의 단어라면, 나는 그 날을 어떤 자세로 준비하고 있는가.",
        "사랑과 공의가 한 점에서 만난다는 것을, 내 관계와 결정 안에서 어떻게 살아내고 있는가.",
        "은혜 안에서의 책임이라는 무게를, 나는 가볍게 받지도 무겁게 짓눌리지도 않는 자리에서 감당하고 있는가.",
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
  <div style="color:#888;font-size:0.88em;margin-top:0.3em">원본 ISBN {b['isbn']} · G01 제 {b['src_no']:02d} 권</div>
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
<h3 style="color:#0F1E3C;margin-top:1.5em">영원의 문 안에서</h3>
<p>이로써 G01 열 권의 묵상이 한 권으로 닫힙니다. 천국의 문턱에서 시작해 마지막 심판의 의미까지, 사후세계라는 한 단어 안에 담긴 그리스도교의 가장 깊은 묵상을 네 갈래로 모아 함께 걸어왔습니다. 처음에는 흩어져 있던 한 권 한 권의 묵상이 한 호흡으로 이어 붙고 나니, 사이를 흐르고 있던 결이 비로소 또렷해졌습니다.</p>
<p>이 책이 묻고자 했던 한 가지 물음은 분명합니다. <em>영원의 문 앞에서 신자는 무엇으로 두려워하지 않을 것인가.</em> 죽음의 문턱을 응시하는 시선과, 영혼의 정체를 정직하게 묻는 자세와, 베일 너머의 풍경을 분별하는 눈과, 부활과 심판에서 모든 길이 만나는 자리를 바라보는 시선 — 그 넷이 그 답의 네 갈래였습니다.</p>
<p><strong>1부에서 우리는 죽음의 문턱</strong>에 함께 섰습니다. 어둠의 골짜기와 고난의 터널이 분명히 있지만, 그 끝에는 십자가의 빛과 부활의 아침이 있다는 것을 차례로 보았습니다. 죽음의 문턱은 두려움의 자리이면서 동시에 가장 또렷한 자리이며, 그 자리에 서 본 사람만이 오늘이라는 하루의 무게를 진실로 측량할 수 있습니다.</p>
<p><strong>2부에서 우리는 영혼이라는 비밀</strong>을 응시했습니다. 영혼이 무엇이고 어디로 가는가, 몸과 영혼은 분리된 것이 아니라 한 결로 동행하는가, 그리고 영원한 생명은 미래가 아니라 오늘 이미 시작되어 있는가 — 이 세 물음 앞에서 우리는 영혼·몸·영생이 결국 한 강을 이루며 흐른다는 것을 함께 보았습니다.</p>
<p><strong>3부에서 우리는 베일 너머의 풍경</strong>을 그렸습니다. 영원의 두 갈림길은 추상이 아니라 오늘의 결단들로 빚어지는 길이며, 영계의 음성은 신비주의가 아니라 분별의 영성으로 듣는 자리입니다. 그리고 천사들은 동화의 인물이 아니라 하나님의 사자로서 우리 곁에서 보호와 섬김의 사역을 감당하고 있습니다.</p>
<p><strong>4부에서 우리는 시간의 끝</strong>에 도달했습니다. 부활은 추상이 아니라 사건이며, 두려움에서 담대함으로의 변화가 한 영혼에게 일어나는 자리입니다. 심판은 두려움의 단어가 아니라 회복의 단어이며, 사랑과 공의가 마침내 한 점에서 만나는 자리입니다. 시간의 끝은 끝이 아니라 새로운 시작의 문이라는 것을 우리는 함께 보았습니다.</p>
<p>이 책을 덮으신 뒤에도 묵상은 끝나지 않습니다. 한 장씩 다시 펼쳐 읽어도 좋고, 한 단락만 천천히 반복해 읽어도 좋습니다. 사후세계라는 단어가 무거워서 피하던 자리에서 그 단어 앞에 정직하게 서는 자리로 옮겨 가셨다면, 그것만으로도 G01 열 권을 한 권으로 묶은 이유는 충분할 것입니다.</p>
<p>이제 100권 시리즈는 G02로, G03으로, 그리고 마지막 G10까지 흘러갑니다. 그러나 모든 갈래의 가장 깊은 토대는 이 첫 그룹의 한 권에 놓여 있습니다. 영원의 입장에서 오늘을 다시 보는 시선이 모든 다음 묵상의 뿌리가 될 것이기 때문입니다.</p>
<p>이 책을 끝까지 읽어 주신 독자께 감사드리며, 다음 그룹에서 또 다른 깊은 묵상으로 다시 만나기를 기도합니다. 주님의 평강이 여러분의 오늘 위에 충만히 임하시기를 축복합니다.</p>
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
    uuid_id = f"omnibus-g01-{today_compact}-{datetime.now().strftime('%H%M%S')}"

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
    <dc:description>{proj['subtitle']} — G01 10권 종합본</dc:description>
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
    print("ISBN 발급 시 batch_books_g01_omnibus.json의 isbn 필드에 입력 후 재빌드.")


if __name__ == "__main__":
    main()
