# -*- coding: utf-8 -*-
"""
시즌 1 10권 종합책 epub 빌더.

입력:
  - batch_books_s1_omnibus.json (메타·4부 구조)
  - tmp/s1_omnibus_extracted.json (10권 본문 추출본)
  - 시즌 1 epub 중 한 권 (CSS 추출용)

출력:
  - ~/Downloads/전자책/AI_시대를_살아가는_영성_YYYYMMDD.epub

구조 (spine 순서):
  cover → copyright → toc → preface
  → part01_intro → [b01_intro·b01_ch01~06] × 3권 (1부)
  → part02_intro → [b04_intro·b04_ch01~06] × 3권 (2부)
  → part03_intro → [b07_intro·b07_ch01~06] × 2권 (3부)
  → part04_intro → [b09_intro·b09_ch01~06] × 2권 (4부)
  → epilogue
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
META_PATH = PROJECT / "batch_books_s1_omnibus.json"
EXTRACT_PATH = PROJECT / "tmp" / "s1_omnibus_extracted.json"
SAMPLE_EPUB = Path.home() / "Downloads" / "전자책" / "AI_시대_영성_상담사를_만나다_20260412.epub"
OUT_DIR = Path.home() / "Downloads" / "전자책"
OUT_BACKUP_DIR = PROJECT / "tmp"  # 보조 사본


def get_css():
    """샘플 epub에서 CSS 추출."""
    with zipfile.ZipFile(SAMPLE_EPUB, "r") as z:
        return z.read("OEBPS/styles/style.css").decode("utf-8")


def get_cover_image():
    """전용 종합책 표지 사용 (없으면 샘플로 폴백)."""
    custom = PROJECT / "tmp" / "s1_omnibus_cover.jpg"
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
  <p><strong>구성</strong>　시즌 1 10권 종합책 (4부 60장)</p>
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
    <p>이 책은 시즌 1 10권의 본문을 거의 그대로 4부 구조로 재편집하여 한 권으로 묶은 종합본입니다.</p>
    <p>각 권의 원본 ISBN 및 출간 정보는 본문 권별 도입 페이지에 명기되어 있습니다.</p>
  </div>
</div></div>"""
    return xhtml_doc("판권", body)


def build_preface_xhtml() -> str:
    body = """<div style="padding:2em 1.5em;line-height:1.9;font-size:1em;color:#222">
<h2 style="color:#0F1E3C;border-bottom:1px solid #C8B99A;padding-bottom:0.5em">여는 글</h2>
<h3 style="color:#0F1E3C;margin-top:1.5em">시즌 1을 한 권으로 묶으며</h3>
<p>시즌 1 열 권은 AI라는 거대한 시대의 파도 앞에서 그리스도인이 어떻게 묵상의 자리에 서야 하는가를 묻는 작업이었습니다. 처음에는 한 권 한 권 따로 떨어진 기록이었지만, 시간이 흐르며 그 글들 사이에 보이지 않는 한 가닥의 실이 흐르고 있다는 것을 깨닫게 되었습니다.</p>
<p>AI는 우리 시대의 단어이자 시험입니다. 도구로 보면 도구이고, 우상으로 모시면 우상이 되며, 시험대로 마주하면 시험대가 됩니다. 분명한 한 가지는, 이 시대를 살아가는 그리스도인은 그 거대한 흐름 앞에서 자기 영혼의 중심을 어디에 두고 있는가를 매일 다시 물어야 한다는 것입니다.</p>
<p>이 책은 그 흩어졌던 빛들을 한 폭으로 모은 것입니다. 열 권의 본문을 거의 그대로 유지하면서, 다만 그 사이에 흐르고 있던 결을 네 갈래로 정리하여 다시 펼쳐 놓았습니다. 한 권씩 읽을 때 보이지 않던 결이 한 권으로 모이고 나니 비로소 또렷해진다는 것이, 종합이라는 작업이 가진 가장 정직한 보람입니다.</p>
<p>네 갈래로 모은 까닭은 단순합니다. 시대를 살아가는 영성은 한 가지 결로만 이루어지지 않기 때문입니다. 시대를 보는 눈, 그 한복판에서의 결단, 마음과 몸의 결, 그리고 모든 오늘이 영원과 닿아 있다는 자각 — 이 넷이 함께 흘러야 합니다.</p>
<p><strong>1부 — 시대를 보는 시선</strong>은 AI와 다수의 흐름 앞에서 신앙의 분별을 묻고, <strong>2부 — 믿음의 도전</strong>은 산을 옮기는 결단·카이로스·덤 인생을 지나며 흔들림 없는 자리를 짚습니다. <strong>3부 — 감성과 치유</strong>는 마음과 몸까지 닿는 영성을 보고, <strong>4부 — 종말과 영원</strong>은 두 세계 사이에 선 신자의 시선을 마지막으로 모읍니다.</p>
<p>이 책은 새 시대의 모든 질문에 답하지 않습니다. 다만 그 질문들 앞에서 흔들리지 않을 수 있는 자리, 곧 묵상의 자리로 한 사람을 데려가려 합니다. 답을 받기보다 질문을 견디는 자리, 결론을 서두르기보다 호흡을 가다듬는 자리. 이 책이 그런 자리가 되어 드린다면, 시즌 1을 한 권으로 묶은 의미는 충분할 것입니다.</p>
<p>한 번에 다 읽어내실 책이 아닙니다. 한 장씩, 한 묵상씩 호흡을 따라 가져가시면 됩니다. 이제 첫 장을 펼쳐 주십시오. 시대 한복판에서, 그러나 광야의 자리에서, 한 호흡씩 함께 걸어가 봅시다.</p>
</div>"""
    return xhtml_doc("여는 글", body)


PART_INTROS = {
    1: {
        "headline": "광장과 광야 사이",
        "paragraphs": [
            "AI 시대는 광장의 시대입니다. 알고리즘은 다수의 클릭을 따라 흐르고, 트렌드는 군중의 외침을 따라 부풀어 오릅니다. 그러나 그리스도인은 광장의 흐름에 떠밀리는 존재가 아닙니다.",
            "광장은 빠르고 시끄럽습니다. 무엇이 옳은가가 아니라 무엇이 더 많이 클릭되는가가 진실의 자리에 올라섭니다. 그 자리에서 한 사람이 자기 영혼의 중심을 지킨다는 것은 결코 자연스러운 일이 아닙니다. 의도적인 선택이며, 매일 갱신해야 하는 결단입니다.",
            "성경은 광야의 자리를 잘 알고 있습니다. 모세도, 엘리야도, 세례 요한도, 그리고 예수께서도 광야의 시간을 거쳐 광장의 사람들을 만나러 오셨습니다. 광야는 외로움의 자리가 아니라, 가장 또렷이 듣는 자리입니다.",
            "이 부에서 다루는 세 권은 그 광장 한복판에서 광야의 세미한 음성을 듣는 자의 영성을 묻습니다. 첫 권은 AI라는 새 도구를 영성 상담의 자리에 어떻게 모실 것인가를 묻고, 두 번째 권은 새 시대에 새 부대를 마련하는 결단의 무게를 보며, 세 번째 권은 다수의 함성 앞에 한 사람이 직관해야 할 진실을 살핍니다.",
            "AI는 도구입니다. 도구는 사용하는 사람의 영성에 따라 축복이 되기도 하고 우상이 되기도 합니다. 새 부대는 단순히 새것이 아니라, 새 술을 담을 만한 그릇을 분별하는 자세입니다. 그리고 다수의 외침 앞에서 한 사람이 진실을 직관한다는 것은, 결국 광야에서 듣던 그 음성을 광장에서도 잃지 않는다는 뜻입니다. 광장과 광야 사이, 그 둘을 아우르는 영성을 함께 걸어 보십시오.",
        ],
        "guides": [
            "AI라는 도구 앞에서, 나는 도구의 주인으로 서 있는가 아니면 도구의 자리에 길들여지고 있는가.",
            "새 시대에 새 부대를 마련한다는 것은, 내 안의 어떤 헌 부대를 비우는 일에서 시작되는가.",
            "다수의 함성과 한 사람의 양심이 갈라지는 자리에서, 나는 지금 어디에 서 있는가.",
            "이 부를 읽으며, 광장의 흐름에 떠밀리지 않는 분별의 시선이 어떻게 길러지는가에 주목해 보십시오.",
        ],
    },
    2: {
        "headline": "산을 옮기는 결단의 자리",
        "paragraphs": [
            "성경이 말하는 믿음은 결코 추상이 아닙니다. 그것은 산을 옮기는 명령이며, 카이로스의 순간을 알아채는 분별이며, 덤으로 주어진 인생을 어떻게 쓸 것인가를 결정하는 무게입니다.",
            "믿음은 손에 잡히는 결단의 무게입니다. 한 알의 겨자씨가 산을 옮기는 능력으로 자라는 그 신비는, 결국 한 사람이 자기 자리에서 던지는 단단한 한 마디 결단에서 시작됩니다. 추상의 산은 옮겨지지 않습니다. 결단의 산만이 흔들립니다.",
            "시간도 그러합니다. 모든 시간은 동일한 육십 분이 흐르는 크로노스이지만, 그 가운데 어떤 한 순간은 카이로스가 되어 우리에게 다가옵니다. 카이로스는 인지하지 않는 자에게는 흘러가 버리는 한 점이고, 깨어 있는 자에게는 인생의 방향을 바꾸는 결단의 자리가 됩니다.",
            "그리고 인생 자체가 덤일 수 있습니다. 죽음의 문턱에서 돌아온 히스기야의 열다섯 해는 그저 연장된 시간이 아니라, 어떻게 쓰느냐의 시험이었습니다. 덤으로 주어진 인생을 살아본 사람만이, 오늘이라는 하루가 결단의 자리임을 안다는 것을 우리는 그 한 인물에게서 배웁니다.",
            "이 부의 세 권은 각각 다른 각도에서 그 결단의 자리를 비춥니다. 산을 옮길만한 믿음은 믿음의 본질 자체를, 카이로스와 자유의지는 시간의 신학을, 이스라엘 어느 왕의 덤 인생은 한 인물의 삶에서 길어 올린 결단의 의미를 다룹니다.",
            "흔들림 속에서 단단해지는 신앙의 자리로 함께 들어가십시오.",
        ],
        "guides": [
            "내가 가진 믿음의 얼굴은 진짜인가, 아니면 자기 확신이나 종교적 행위로 둔갑한 거짓 믿음인가.",
            "오늘 내게 던져진 카이로스의 순간을, 나는 알아채고 응답하고 있는가 흘려보내고 있는가.",
            "만약 오늘이 덤으로 받은 하루라면, 나는 무엇을 다시 결정하고 무엇을 내려놓겠는가.",
            "이 부를 읽으며, 한 번의 결단이 어떻게 한 사람의 일상을 매일 다시 빚어 가는지 따라가 보십시오.",
        ],
    },
    3: {
        "headline": "마음의 결을 따라",
        "paragraphs": [
            "우리는 영혼만으로 이루어진 존재가 아닙니다. 마음과 몸, 감성과 진동까지 우리의 영성은 그 모든 결을 통해 흐릅니다.",
            "차가운 이성만으로는 영성이 자라지 않습니다. 마음의 결, 감성의 자리, 그리고 몸의 진동까지 — 이 모든 결을 따라 흐를 때 비로소 영성은 한 사람의 전체를 빚어 갑니다. 머리만으로 믿는 신앙과 마음까지 닿는 신앙은 같은 단어로 부르기 어려운 두 자리입니다.",
            "성경의 인물들도 마음과 몸을 함께 가지고 있었습니다. 다윗은 시편으로 자신의 가장 깊은 감정을 토해냈고, 예수께서는 우셨고 또 한숨지으셨습니다. 영성은 감정을 억누르는 일이 아니라, 감정을 하나님 앞에 정직하게 가져가는 자리에서 깊어집니다.",
            "그리고 우리의 몸은 영혼의 그릇이 아니라 동행자입니다. 진동과 호흡, 잠과 식사, 접촉이 모두 영적인 의미를 품고 있다는 것을 우리는 너무 자주 잊어버립니다. 진동 에너지의 자리에서 만나는 치유는 신비주의가 아니라, 우리 몸까지 동참하는 회복의 자연스러운 자리입니다.",
            "이 부의 두 권은 그 안쪽을 바라봅니다. 아름다운 감성을 사모하자는 차가운 이성이 아닌 따뜻한 마음의 결을, 진동 에너지와 치유는 몸의 진동까지 닿는 회복의 자리를 살핍니다.",
            "내면의 가장 부드러운 자리에서 흐르는 영성을 함께 만나 보십시오.",
        ],
        "guides": [
            "나는 감정을 억누르고 있는가, 아니면 하나님 앞에 정직하게 가져가고 있는가.",
            "자극에서 오는 즐거움과 영혼 깊은 자리에서 솟아나는 기쁨의 결을, 나는 어떻게 분별하고 있는가.",
            "이 부를 읽으며, 영성이 머리에서 가슴을 거쳐 몸까지 흐르는 그 결을 따라가 보십시오.",
        ],
    },
    4: {
        "headline": "두 세계 사이에서",
        "paragraphs": [
            "신자의 삶은 두 세계 사이의 삶입니다. 보이는 세상과 보이지 않는 영원, 오늘의 호흡과 그 너머의 부활. 우리는 그 두 세계의 경계에서 매일을 살아갑니다.",
            "보이는 세상은 견고해 보이지만 그림자입니다. 보이지 않는 영원이 오히려 본체입니다. 그 사실을 진실로 믿을 때, 오늘 우리가 겪는 모든 일들은 그 무게가 다시 측정됩니다. 가벼운 것이 무거워지고, 무겁다고 여겼던 것이 가벼워집니다.",
            "죽음은 그 두 세계의 경계입니다. 두려워하기에 충분한 자리이지만, 그리스도인에게는 두려움이 마지막 단어가 아닙니다. 죽음의 역설은, 끝처럼 보이는 그 자리가 사실은 새로운 시작이라는 것이며, 끝과 시작이 한 점에서 만난다는 것입니다.",
            "이 세상과 저 세상은 단절된 두 공간이 아닙니다. 한 영혼이 두 세계를 잇는 다리이며, 그 다리 위에서 우리는 매일을 살아갑니다. 어느 한쪽만 보고 사는 사람과, 두 세계를 함께 바라보며 사는 사람은 같은 오늘을 다른 방식으로 삽니다.",
            "이 부의 두 권은 그 경계를 정면으로 응시합니다. 죽음의 역설은 끝처럼 보이는 그것이 어떻게 시작이 되는가를 묻고, 이 세상과 저 세상은 두 세계의 풍경을 한 호흡에 그려냅니다.",
            "마지막 페이지를 덮을 때, 두 세계가 한 빛 안에 있음을 느끼시기를 기도합니다.",
        ],
        "guides": [
            "죽음을 끝으로 보는 시선과 새로운 시작의 문으로 보는 시선의 차이는, 내 안에서 어디서 갈리는가.",
            "영원이 미래의 어딘가가 아니라 오늘 이 하루 안에 이미 시작되어 있다는 것을, 나는 어떻게 받아들이고 있는가.",
            "두 세계를 잇는 다리 위에서, 나는 어느 쪽을 더 또렷이 보고 살아가고 있는가.",
        ],
    },
}


# 권별 요약 (각 책 진입부 — 3단락, 약 70% 분량)
# 마지막 단락의 핵심 한 문장은 3번째 단락 끝에 흡수
BOOK_SUMMARIES = {
    1: [
        "AI라는 거대한 도구가 우리의 일상을 채우는 시대에, 한 영혼의 갈증을 무엇이 채울 수 있는가를 묻는 첫 번째 묵상이다. 정보는 손끝에 닿고 알고리즘은 우리의 클릭 패턴을 읽지만, 새벽 세 시에 홀로 흘리는 한 줄 눈물의 이유는 어떤 기계도 알지 못한다.",
        "저자는 그 자리를 성경의 보혜사 자리에서 찾는다. 곁에 불러 세운 자, 변호인처럼·동료처럼·친구처럼 함께 앉아 주는 임재 그 자체가 영성 상담의 원형이다. AI는 그 자리를 대신할 수 없지만, 잘 쓰면 그 자리로 한 사람을 데려가는 도구가 될 수 있다.",
        "이어지는 장들은 수가성 우물가의 예수께서 한 여인의 갈증을 풀어 가셨던 방식—듣는 자리, 공감의 자리, 말씀이 흐르는 자리—을 오늘의 영성 상담의 자리로 가져오고, 그 자리에 서야 할 교회 지도자의 소명을 짚는다. 시대를 분별하면서 동시에 시대를 활용하는 자리, 그곳이 AI 시대의 영성 상담사가 서야 할 자리다.",
    ],
    2: [
        "마태복음 9장의 비유가 우리 시대에 다시 펼쳐진다. 새 술은 새 부대에 담아야 한다. 부대를 바꾸지 않은 채 새것을 담으면 부대가 터지고 술도 잃는다. AI가 만들어 내는 거대한 흐름 앞에서 우리가 묻는 것은 무엇을 담을 것인가가 아니라 어떤 부대에 담을 것인가다.",
        "저자는 우리 시대의 헌 부대를 '기술 우상주의'라고 짚는다. 도구를 신처럼 모시고, 알고리즘을 운명처럼 받아들이며, 효율을 절대적 가치로 추대하는 자세. 그 부대로는 결코 복음의 새 술을 담을 수 없다.",
        "새 부대는 거짓 자아를 벗고 새 사람을 입는 자리에서 시작된다. 의인은 믿음으로 살리라는 한 마디가 그 새 부대의 골격이며, 일일신 우일신의 매일의 갱신이 그 결을 빚어 간다. 새 술을 담은 새 부대로 살아간다는 것—그것이 시대의 한복판에서 그리스도인이 결단해야 할 갱신의 자리다.",
    ],
    3: [
        "군중의 함성은 우리 시대의 가장 강력한 진리 같은 것이 되어 있다. 더 많이 클릭된 것이 옳은 것처럼, 더 많이 외친 자가 정의로운 자처럼 느껴지는 자리. 그러나 성경은 다수의 외침이 진리가 아님을 정직하게 증언한다.",
        "빌라도가 손을 씻을 때 진실은 군중의 함성에 지워지지 않았다. 다만 그 자리에 서 있던 자들의 비겁이 한 영혼을 십자가로 보냈을 뿐이다. 광야에서 외치는 자의 소리는 한 사람의 외침이었고, 마틴 루터 킹의 '나에게는 꿈이 있습니다' 또한 다수의 동의를 얻기 전 한 사람의 양심이었다.",
        "침묵하시는 예수의 자리는 가장 깊은 분별이 일어나는 자리였다. 다수의 횡포 한복판에서 직관해야 할 한 가지는, 결국 나는 어느 쪽에 서 있는가다. 분별의 영성은 다수가 아니라 진실의 편에 서기로 매일 결단하는 한 영혼의 자리에서 시작된다.",
    ],
    4: [
        "한 알의 겨자씨만큼의 믿음으로 산이 옮겨질 수 있다는 예수의 말씀은, 믿음의 양보다 믿음의 본질을 묻는 약속이다. 양은 작아도 본질이 진짜이면 산이 흔들린다. 본질이 가짜이면 산이 아무리 작은 언덕이라도 옮겨지지 않는다.",
        "저자는 먼저 믿음이 무엇이 아닌가를 짚는다. 자기 확신, 긍정의 힘, 종교적 행위, 감정의 고조—이 모든 거짓 믿음의 얼굴들 너머에 진짜 믿음의 자리가 있다.",
        "진짜 믿음은 대상을 본다. 누구를 향하는 믿음인가가 그 믿음의 진위를 가른다. 자기 자신을 향한 믿음은 결국 자기 신뢰일 뿐이고, 운명을 향한 믿음은 운명론에 갇힌다. 그러나 살아 계신 하나님을 향한 믿음은 영혼을 구원으로 데려간다. 산을 옮길만한 믿음이라는 말은, 결국 한 사람의 일상이 매일 재배치되는 그 자리를 가리킨다.",
    ],
    5: [
        "시간에는 두 결이 있다. 흘러가는 크로노스와, 던져지는 카이로스. 모든 시간은 동일한 육십 분이지만 그 가운데 어떤 한 순간은 인생의 방향을 바꾸는 부름의 자리가 된다.",
        "카이로스는 인지하지 않는 자에게는 한 점이고, 깨어 있는 자에게는 결단의 자리다. 하나님의 카이로스를 받는 자리에 자유의지가 있다. 저자는 자유의지의 주체를 혼으로 짚으며, 영·혼·육의 구조 안에서 카이로스가 어떻게 한 사람을 빚어 가는가를 추적한다.",
        "시간이 던져질 때 자유의지가 응답한다는 것—그 응답이 인격적 교제의 본질이며, 하나님의 역사가 한 사람의 일상으로 흘러 들어가는 통로다. 일방적 운명론도, 일방적 자기 결정도 영성의 자리가 아니다. 오늘이라는 하루는 그 카이로스가 던져지는 자리이며, 깨어 있는 자만이 그 부름을 받는다.",
    ],
    6: [
        "히스기야는 죽음의 문 앞에서 돌아온 한 인물이다. 이사야 선지자를 통해 받은 십오 년이라는 시간은 단순한 연장이 아니라 그 시간을 어떻게 쓰느냐의 시험이었다.",
        "처음에는 잘 썼다. 성전을 다시 열고, 우상의 잔재를 기드론 시내로 흘려보냈다. 병상에서 깨달은 은혜로 한 시기를 살아냈다. 그러나 마지막에는 교만이 발목을 잡았다. 바벨론 사신 앞에서 자기 보화를 자랑한 한 순간이 그의 후손에게 무너짐의 그림자를 드리웠다.",
        "덤으로 받은 인생이라는 자각은 시작 때만 빛나는 것이 아니다. 마칠 때까지 그 자각을 잃지 않는 자만이 진실로 덤을 살아낸 자다. 한 호흡 한 호흡이 정해진 약속이 아니라 주어진 선물이라면, 오늘이라는 하루를 어떻게 쓰느냐가 결단의 자리다.",
    ],
    7: [
        "감정은 마차와 같다. 마차 자체는 좋지도 나쁘지도 않으나, 어떤 마부가 그 마차를 모는가에 따라 도착하는 자리가 달라진다. 감정을 억누르는 일이 영성이 아니다. 감정을 부정하지 않고 하나님 앞에 가져가는 자리에서 영성이 깊어진다.",
        "우리 안에는 더러운 느낌의 뿌리가 있다. 시기·분노·두려움·비교 의식. AI 시대는 그 뿌리를 더 흔든다. 끝없는 비교의 자리, 끝없는 자극의 자리, 끝없는 결핍의 감각.",
        "저자는 그 자리에서 기쁨과 즐거움을 분별한다. 즐거움은 자극에서 오고 곧 사라지지만, 기쁨은 영혼의 깊은 자리에서 솟아나 사라지지 않는다. 아름다운 감성을 회복한다는 것은 자극을 따라가는 마차가 아니라 기쁨을 향해 빚어지는 마차가 되는 일이다. 감정의 자리까지 닿는 영성, 그것이 시대의 흐름 한복판에서 우리가 회복해야 할 결이다.",
    ],
    8: [
        "성경은 우리 몸이 영혼의 그릇이 아니라 동행자임을 말한다. 진동·호흡·잠·식사·접촉이 모두 영적인 의미를 품는다. 저자는 모든 것이 진동이라는 통찰에서 시작해, 그 진동의 결을 영성의 자리로 가져온다.",
        "분노와 두려움은 저주파의 감옥이다. 그 자리에 갇힌 사람은 영혼의 호흡까지 무거워진다. 의식의 방향타는 우리가 어디에 마음을 두느냐에 있다. 마음을 두는 자리가 진동의 결을 빚는다.",
        "치유의 진동공학은 신비주의가 아니다. 우리 몸이 진동의 결로 이루어졌다면 영혼의 자리도 그 결을 따라 흐른다는 정직한 관찰이다. 내면 연금술은 그 결을 다시 빚는 자리이며, 매일 새로운 주파수로 깨어나는 일은 영혼과 몸이 함께 동참하는 회복의 자연스러운 자리다. 진동의 결까지 닿는 영성, 그것이 우리 시대가 다시 회복해야 할 결이다.",
    ],
    9: [
        "죽음은 끝처럼 보이지만 끝이 아니다. 그것은 두 세계의 경계이며, 그리스도인에게는 새로운 시작의 문이다. 저자는 그 문 앞에 정직하게 선다. 두려움 없이가 아니라 두려움 너머의 약속을 보면서.",
        "낙원은 영원한 머묾의 자리가 아니라 부활을 기다리는 중간의 자리다. 불생불멸의 역설은 한 영혼이 사라지지 않으면서도 변화한다는 신비의 표현이다. 부활은 영혼만의 사건이 아니라 몸의 귀환이다.",
        "그 자리의 핵심은 대면이다. 그분의 얼굴과 마주하는 순간, 지상에서 풀리지 않던 모든 매듭이 한 시선 안에 풀어진다. 저자는 마지막 장에서 한 가지를 단호하게 말한다. 지금 이 순간이 입장권이다. 죽음의 역설은 끝이 시작이라는 한 마디다.",
    ],
    10: [
        "이 세상과 저 세상은 단절된 두 공간이 아니다. 한 영혼이 두 세계를 잇는 다리이며, 그 다리 위에서 우리는 매일을 살아간다. 저자는 존재의 기원에서 시작한다. 우리는 우연이 아니라 부르심이다.",
        "우주에서 가장 정교한 기계인 AI도 결코 가질 수 없는 한 가지가 인간에게 있다. 부르심에 응답하는 자리. 윤회인가 차원인가의 질문은 단지 신학적 호기심이 아니다. 한 영혼이 어디로 향하고 있는가의 가장 정직한 좌표다.",
        "성경은 윤회를 말하지 않고 차원의 이동을 말한다. 낙원과 음부, 천국과 지옥은 영원의 두 갈림길이며, 그 갈림길은 오늘이라는 하루 안에 이미 시작되어 있다. 영원한 현재는 미래에 시작되는 것이 아니라, 하나님과 동행하는 오늘 이 순간에 이미 들어와 있다. 두 세계가 한 빛 안에 있다.",
    ],
}


# 권별 길잡이 — 그 한 권만의 좁고 깊은 화두 (부 길잡이와 차별)
BOOK_GUIDES = {
    1: [
        "AI라는 도구가 채울 수 없는 내 영혼의 갈증은 어디서 오는가.",
        "내 곁에 함께 앉아 주는 보혜사의 자리를, 나는 누구에게서 누리고 있는가.",
        "수가성 우물가의 한 시선처럼, 내 갈증의 진짜 자리를 비춰 줄 한 사람은 있는가.",
    ],
    2: [
        "내가 비워야 할 헌 부대는, 지금 내 안의 어떤 자리인가.",
        "기술과 효율을 절대화하는 흐름 앞에서, 내 신앙의 새 부대는 어떻게 빚어지고 있는가.",
        "일일신 우일신 — 오늘 내가 새로워지는 자리는 어디인가.",
    ],
    3: [
        "다수의 함성이 옳음의 기준이 된 자리에서, 나는 어느 편에 서 있는가.",
        "침묵하는 자리에서 분별이 익는다는 것을, 나는 얼마나 견디고 있는가.",
        "내 안에 광야의 한 사람의 외침이 자라고 있는가, 광장의 함성을 따라가고 있는가.",
    ],
    4: [
        "내 믿음의 대상은 누구인가 — 자기 신뢰인가, 운명인가, 살아 계신 하나님인가.",
        "겨자씨만 한 양이라도 본질이 진짜라면 산이 흔들린다는 약속을, 나는 어떻게 살고 있는가.",
        "내 일상이 매일 재배치되는 그 자리, 곧 산이 옮겨지는 자리는 어디인가.",
    ],
    5: [
        "오늘 내게 던져진 카이로스의 한 점을, 나는 알아채고 있는가.",
        "자유의지로 응답하는 자리가 인격적 교제의 본질이라는 것을, 내 일상은 어떻게 증언하는가.",
        "운명론도 자기 결정도 아닌 그 사이의 자리에, 나는 깨어 서 있는가.",
    ],
    6: [
        "오늘이 덤으로 받은 하루라면, 나는 무엇을 다시 결정하겠는가.",
        "처음의 은혜를 마칠 때까지 잃지 않는다는 것은, 어떤 매일의 결단인가.",
        "히스기야의 마지막 한 순간이 후손에게 그림자를 드리웠듯, 내 마무리는 누구에게 어떻게 흐를 것인가.",
    ],
    7: [
        "나는 감정을 억누르고 있는가, 하나님 앞에 정직하게 가져가고 있는가.",
        "자극의 즐거움과 영혼 깊은 자리의 기쁨, 그 둘을 나는 어떻게 분별하고 있는가.",
        "마음의 결이 따뜻해지는 자리에서, 나는 누구를 만나고 있는가.",
    ],
    8: [
        "내 마음이 두는 자리가 진동의 결을 빚는다면, 나는 오늘 어디에 마음을 두고 있는가.",
        "분노와 두려움의 저주파에서 벗어나는 자리는, 내 안에서 어떻게 열리는가.",
        "영성이 머리·가슴·몸까지 흐르는 그 결이, 내 일상에 어떻게 닿고 있는가.",
    ],
    9: [
        "죽음을 끝으로 보는 시선과 시작의 문으로 보는 시선, 내 안에서 어느 쪽이 더 또렷한가.",
        "낙원이 영원한 머묾이 아니라 부활을 기다리는 중간의 자리라면, 나는 그 사이를 어떻게 살고 있는가.",
        "지금 이 순간이 영원의 입장권이라는 한 마디를, 나는 어떻게 받아들이고 있는가.",
    ],
    10: [
        "나는 우연이 아니라 부르심이라는 한 마디를, 내 일상은 어떻게 증언하는가.",
        "윤회가 아닌 차원의 이동이라는 성경의 시선이, 내 오늘에 어떻게 닿고 있는가.",
        "두 세계가 한 빛 안에 있다는 것을, 나는 어느 자리에서 느끼고 있는가.",
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
  <div style="color:#888;font-size:0.88em;margin-top:0.3em">원본 ISBN {b['isbn']} · 시즌 1 제 {b['src_no']:02d} 권</div>
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
<h3 style="color:#0F1E3C;margin-top:1.5em">시즌 1을 마치며</h3>
<p>이로써 시즌 1 열 권의 묵상이 한 권으로 닫힙니다. 처음에 흩어진 점들로 시작했던 글이 어느덧 한 폭의 그림이 되어 우리 앞에 놓였습니다. 한 권 한 권을 따로 쓰던 자리에서는 보이지 않던 결이, 열 권을 한 호흡으로 이어 붙이고 보니 비로소 또렷이 드러났습니다. 그 결이 이 책이 독자 앞에 내놓는 가장 정직한 선물일 것입니다.</p>
<p>시즌 1이 묻고자 했던 한 가지 물음은 분명합니다. <em>AI라는 시대의 한복판에서 신자는 무엇으로 흔들리지 않을 것인가.</em> 시대를 보는 시선과, 산을 옮기는 결단과, 마음의 결을 살피는 감성과, 두 세계의 경계를 응시하는 시선이 그 답의 네 갈래였습니다. 네 갈래는 따로 흐르는 것 같으면서도 결국 한 강을 이룹니다.</p>
<p><strong>1부에서 우리는 광장과 광야 사이</strong>를 함께 걸었습니다. AI가 만들어 내는 거대한 광장의 흐름 한복판에서 한 사람의 영혼이 광야의 세미한 음성을 듣는다는 것은 어떻게 가능한가를 물었습니다. 흐름에 떠밀리지 않는 자세, 새 부대를 마련하는 결단, 다수의 함성 너머의 진실을 직관하는 눈—그 셋이 모일 때 비로소 영성은 시대를 살아가는 힘이 됩니다.</p>
<p><strong>2부에서 우리는 결단의 자리</strong>에 섰습니다. 산을 옮기는 믿음은 추상이 아니라 한 순간의 무게이며, 카이로스는 우리에게 던져진 시간의 부름이고, 덤으로 주어진 인생은 어떻게 쓰느냐가 모든 것을 결정합니다. 흔들림 속에서 단단해지는 신앙이란 그 결단들이 쌓여 만들어지는 한 사람의 윤곽입니다.</p>
<p><strong>3부와 4부는 우리를 안쪽으로, 그리고 너머로</strong> 데려갔습니다. 마음과 몸의 결까지 흐르는 영성, 그리고 이 세상과 저 세상 사이를 응시하는 시선. 영성은 머리에서 시작되어 가슴을 거쳐 영원에 닿는 한 가닥의 강이라는 것을 우리는 함께 보았습니다. 그 강이 흐르는 자리에서만 죽음조차 끝이 아닌 문이 됩니다.</p>
<p>이제 시즌 2가 시작됩니다. 시즌 2는 100권의 묵상으로 더 깊은 갈래를 펼쳐낼 것입니다. 그러나 그 모든 갈래의 뿌리는 시즌 1의 이 한 권에 닿아 있습니다. 시즌 2의 첫 자리는 영계와 사후세계입니다. 천국의 문턱·부활의 증거·영혼의 행로·심판과 영원에 이르는 묵상은, 시즌 1이 묻던 "흔들리지 않는 자리"의 가장 깊은 토대를 다시 세우는 작업이 될 것입니다. 시즌 1이 시대 앞에서의 흔들리지 않음을 물었다면, 시즌 2는 영원 앞에서의 흔들리지 않음을 묻습니다.</p>
<p>이 책을 덮으신 뒤에도 묵상은 끝나지 않습니다. 한 장씩 다시 펼쳐 읽어도 좋고, 한 단락만 천천히 반복해 읽어도 좋습니다. 묵상의 한 호흡 한 호흡이 우리의 안과 밖을 함께 빚어 가기 때문입니다. 책장을 덮을 때마다 한 줄이라도 마음 한구석에 남는다면, 시즌 1이 한 권으로 묶인 이유는 충분합니다.</p>
<p>이 책을 끝까지 읽어 주신 독자께 감사드리며, 다음 시즌에서 또 다른 깊은 묵상으로 다시 만나기를 기도합니다. 주님의 평강이 여러분의 오늘 위에 충만히 임하시기를 축복합니다.</p>
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
    uuid_id = f"omnibus-s1-{today_compact}-{datetime.now().strftime('%H%M%S')}"

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
    <dc:description>{proj['subtitle']} — 시즌 1 10권 종합본</dc:description>
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
    # bytes 로 들어 있는 항목은 utf-8 디코드 후 검사 → 다시 인코드.
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
    print("ISBN 발급 시 batch_books_s1_omnibus.json의 isbn 필드에 입력 후 재빌드.")


if __name__ == "__main__":
    main()
