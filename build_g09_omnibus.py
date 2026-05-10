# -*- coding: utf-8 -*-
"""
G09 10권 종합책 "곁에 두신 분들" epub 빌더.

입력:
  - batch_books_g09_omnibus.json (메타·4부 구조)
  - tmp/g09_omnibus_extracted.json (10권 본문 추출본)
  - G09 epub 중 한 권 (CSS 추출용)

출력:
  - ~/Downloads/전자책/곁에_두신_분들_YYYYMMDD_종합책.epub

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
META_PATH = PROJECT / "batch_books_g09_omnibus.json"
EXTRACT_PATH = PROJECT / "tmp" / "g09_omnibus_extracted.json"
SAMPLE_EPUB = Path.home() / "Downloads" / "전자책" / "결혼의_신학_20260419.epub"
OUT_DIR = Path.home() / "Downloads" / "전자책"
OUT_BACKUP_DIR = PROJECT / "tmp"  # 보조 사본


def get_css():
    """샘플 epub에서 CSS 추출."""
    with zipfile.ZipFile(SAMPLE_EPUB, "r") as z:
        return z.read("OEBPS/styles/style.css").decode("utf-8")


def get_cover_image():
    """전용 종합책 표지 사용 (없으면 샘플로 폴백)."""
    custom = PROJECT / "tmp" / "g09_omnibus_cover.jpg"
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
  <p><strong>구성</strong>　G09 10권 종합책 (4부 70장)</p>
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
    <p>이 책은 100권 영성 시리즈 G09(관계) 10권의 본문을 거의 그대로 4부 구조로 재편집하여 한 권으로 묶은 종합본입니다.</p>
    <p>각 권의 원본 ISBN 및 출간 정보는 본문 권별 도입 페이지에 명기되어 있습니다.</p>
  </div>
</div></div>"""
    return xhtml_doc("판권", body)


def build_preface_xhtml() -> str:
    body = """<div style="padding:2em 1.5em;line-height:1.9;font-size:1em;color:#222">
<h2 style="color:#0F1E3C;border-bottom:1px solid #C8B99A;padding-bottom:0.5em">여는 글</h2>
<h3 style="color:#0F1E3C;margin-top:1.5em">곁에 두신 분들이라는 부르심</h3>
<p>우리는 혼자 살아갈 수 없습니다. 그것은 약점이 아니라 설계입니다. 하나님은 처음부터 사람이 혼자 있는 것이 좋지 않다고 말씀하셨고, 한 영혼 옆에 또 한 영혼을 두셨습니다. 가족·친구·이웃·교회 — 그 모든 자리는 우연이 아니라 부르심입니다. 곁에 두신 분들. 그 한 마디 안에 우리의 모든 관계가 담겨 있습니다.</p>
<p>이 책은 그 곁의 사람들을 차례로 따라 걷습니다. 가장 가까운 가족의 자리, 친구와 이웃이라는 동심원, 갈등과 화해의 깊이, 그리고 공동체의 자리 — 관계라는 한 단어 안에 담긴 그리스도교의 가장 정직한 묵상을 열 갈래로 펼쳐 놓았습니다.</p>
<p>이 책은 100권 영성 시리즈의 아홉 번째 그룹 G09를 한 권으로 묶은 종합본입니다. 결혼의 신학에서 공동체로 사는 삶까지, 곁에 두신 분들이 빚어 내는 결을 네 갈래로 모았습니다. 열 권 각각의 본문을 거의 그대로 유지하면서, 그 사이를 흐르고 있던 결을 한 호흡으로 이어 붙였습니다.</p>
<p>네 갈래는 한 영혼이 곁의 사람들과 함께 살아가는 한 길의 네 굽이입니다. <strong>1부 — 가장 가까운 자리</strong>는 결혼·부모와 자녀·세대를 잇는 믿음에서 가족의 자리에 섭니다. <strong>2부 — 친구와 이웃</strong>은 우정의 은혜와 이웃을 사랑하는 방법으로 동심원을 그려 갑니다. <strong>3부 — 갈등과 화해</strong>는 용서·화해·홀로 섬을 통과하며 관계의 깊이를 응시하고, <strong>4부 — 공동체의 자리</strong>는 교회 공동체와 함께 사는 삶에서 마지막 결을 모읍니다.</p>
<p>이 책은 관계 매뉴얼이 아닙니다. 다만 곁에 두신 분들이 부르심이라는 것을, 그리고 그 부르심에 응답하는 자세가 우리의 영성을 가장 정직하게 빚는다는 것을, 묵상의 자리로 우리를 데려가려 합니다. 기술이 아니라 자세, 관계 기술이 아니라 한 영혼이 다른 영혼을 부르심으로 받아들이는 결. 그 자리에서 비로소 관계가 시작됩니다.</p>
<p>한 번에 다 읽어내실 책이 아닙니다. 한 장씩, 한 묵상씩 호흡을 따라 가져가시면 됩니다. 이제 첫 장을 펼쳐 주십시오. 곁에 두신 분들 안에서, 한 호흡씩 함께 살아내 봅시다.</p>
</div>"""
    return xhtml_doc("여는 글", body)


PART_INTROS = {
    1: {
        "headline": "가장 가까운 자리에서 시작되는 영성",
        "paragraphs": [
            "관계의 영성은 멀리서 시작되지 않습니다. 가장 가까운 자리, 곧 가족의 자리에서 시작됩니다. 그 자리는 도망칠 수 없는 자리이며, 동시에 가장 정직한 자리입니다. 우리는 가족 안에서 가장 깊이 사랑받기도 하고, 가장 깊이 상처받기도 합니다. 그 두 결이 한 자리에 함께 있는 곳, 그것이 가족입니다.",
            "결혼은 그 가장 가까운 자리의 시작입니다. 단순한 사회적 제도가 아니라 하나님이 설계하신 결합이며, 그리스도와 교회의 관계를 비추는 신비입니다. 두 영혼이 한 몸이 되는 결단, 매일의 약속을 다시 새기는 자세가 그 결의 본질입니다.",
            "부모와 자녀의 관계는 그 다음의 결입니다. 사랑의 언어를 익히고, 상처 입은 아버지상을 다시 빚으며, 훈육의 지혜를 배우는 자리. 영적 대물림은 자동이 아니라 한 부모의 의도적 결단입니다. 떠나보냄의 축복까지 흐르는 그 결은 평생의 영성을 빚습니다.",
            "그리고 세대를 잇는 믿음이 있습니다. 믿음은 유전되지 않는다는 한 마디가 가장 단단합니다. 횃불 릴레이처럼 한 세대가 다음 세대에게 직접 건네야 하는 결. 가정이라는 성소에서 그 횃불이 빚어지고, 디모데의 믿음이 그 결의 가장 정직한 사례가 됩니다.",
            "이 부의 세 권은 가장 가까운 자리의 세 결을 차례로 펼칩니다. 「결혼의 신학」은 두 영혼이 한 몸이 되는 신비를, 「부모와 자녀」는 사랑과 훈육과 떠나보냄의 흐름을, 「세대를 잇는 믿음」은 한 횃불이 다음 손으로 건네지는 자리를 다룹니다.",
            "가족이라는 자리가 영성의 가장 정직한 시험대라는 것을, 세 권의 결 위에서 함께 발견해 보십시오.",
        ],
        "guides": [
            "결혼이 사회적 제도가 아니라 신학적 결합이라면, 내 결혼의 자리는 어떤 결로 살아나고 있는가.",
            "부모와 자녀 사이의 사랑의 언어를, 나는 어떤 자리에서 익히고 있는가.",
            "믿음은 유전되지 않는다는 한 마디 앞에서, 나는 다음 세대에게 무엇을 건네고 있는가.",
            "이 부를 읽으며, 가장 가까운 자리가 어떻게 영성의 가장 정직한 시험대가 되는가에 주목해 보십시오.",
        ],
    },
    2: {
        "headline": "친구와 이웃이라는 동심원",
        "paragraphs": [
            "가족 너머의 첫 동심원에 친구가 있습니다. 친구는 가족이 아니지만 가족만큼 가까운 자리에 있는 사람들입니다. 우리가 선택한 가족이라고 부를 수도 있고, 하나님이 우리에게 보내신 또 다른 동행자라고 부를 수도 있습니다.",
            "다윗과 요나단의 우정이 그 결의 가장 깊은 모범입니다. 자기 왕좌를 양보한 요나단의 결단, 그를 향한 다윗의 한 평생의 그리움. 그 두 영혼 사이에 흐른 결이 우정의 가장 단단한 자리를 가리킵니다. 나침반 같은 친구, 쇠가 쇠를 날카롭게 하듯 서로를 빚는 자리.",
            "그리고 그 다음 동심원에 이웃이 있습니다. 누가 나의 이웃인가의 물음 앞에서 우리는 자주 멈춥니다. 강도 만난 자를 지나친 사람들과 멈춰 선 사마리아인의 차이는 단순합니다. 멈출 것인가, 지나갈 것인가. 그 한 결단이 영성의 자리를 정합니다.",
            "사마리아인이 멈춰 선 이유는 그가 더 영적이었기 때문이 아닙니다. 그가 자기 시간과 돈과 발걸음을 내어주기로 결단했기 때문입니다. 경계를 넘는 용기, 시간과 돈을 내어주는 사랑, 끝까지 책임지는 사랑. 그 셋이 함께 흐를 때 비로소 이웃 사랑의 결이 또렷해집니다.",
            "이 부의 두 권은 친구와 이웃이라는 두 결을 차례로 응시합니다. 「우정의 은혜」는 다윗과 요나단의 결과 신실함의 무게를, 「이웃을 사랑하는 방법」은 사마리아인의 멈춤과 끝까지 책임지는 사랑을 다룹니다.",
            "가족 너머의 동심원이 영성의 자리라는 것을, 두 권의 결 위에서 함께 새겨 보십시오.",
        ],
        "guides": [
            "다윗의 요나단처럼 내 곁에 신실한 친구가 있는가, 또는 내가 누구의 요나단이 되고 있는가.",
            "사마리아인이 멈춰 선 자리를, 내 일상의 어떤 자리에서 살아내고 있는가.",
            "끝까지 책임지는 사랑이라는 한 마디가, 내 어떤 결단으로 자라고 있는가.",
            "이 부를 읽으며, 친구와 이웃이라는 동심원이 영성의 자리가 되는 결을 따라가 보십시오.",
        ],
    },
    3: {
        "headline": "관계의 깊이는 갈등을 통과한 자리에서",
        "paragraphs": [
            "갈등 없는 관계는 없습니다. 가장 가까운 가족 사이에도, 가장 단단한 우정 사이에도, 가장 거룩한 공동체 안에도 갈등은 있습니다. 그러나 갈등이 관계를 끝내는 자리는 아닙니다. 갈등을 통과한 관계가 깊어지는 자리, 그것이 그리스도인의 영성이 빚어지는 가장 정직한 자리입니다.",
            "용서는 그 통과의 가장 단단한 결입니다. 한 번이 아니라 반복되는 용서, 관계의 호흡으로서의 용서. 우리가 누구를 용서한다는 것은 우리가 먼저 받은 용서를 흘려보내는 일입니다. 용서와 허용은 같지 않습니다. 잘못을 인정하면서도 다시 살아갈 길을 여는 자세, 그것이 용서의 결입니다.",
            "갈등 속의 화해는 그 다음 결입니다. 회피가 아닌 직면, 화해의 다리를 놓는 자세. 화평케 하는 자의 복은 갈등이 없는 자에게 주어진 복이 아니라, 갈등 한복판에서 화평을 만들어 가는 자에게 주어진 복입니다. 평화를 만드는 삶이 그 결의 마지막 자리입니다.",
            "그리고 모든 관계의 토대에는 홀로 섬이 있습니다. 홀로 있음의 축복, 광야로 부르시는 하나님, 외로움과 고독 사이의 분별. 자기 자신과 마주하지 못한 사람은 다른 영혼과도 진실되게 마주할 수 없습니다. 홀로 서야 함께 설 수 있다는 한 마디가 관계의 가장 깊은 토대를 가리킵니다.",
            "이 부의 세 권은 관계의 깊이가 빚어지는 세 결을 차례로 펼칩니다. 「용서하는 관계」는 반복되는 용서의 결을, 「갈등 속의 화해」는 회피가 아닌 직면의 자세를, 「홀로 서는 신앙」은 모든 관계의 토대로서의 자기 자신과 마주하는 용기를 다룹니다.",
            "갈등을 통과한 자리에서 관계가 깊어진다는 것을, 세 권의 길 위에서 함께 새겨 보십시오.",
        ],
        "guides": [
            "내가 반복해서 용서해야 할 자리는 어디이며, 그 용서를 어떤 결로 살아내고 있는가.",
            "갈등을 회피하지 않고 직면하는 자세를, 내 어떤 관계에서 살아내고 있는가.",
            "홀로 서야 함께 설 수 있다는 한 마디가, 내 어떤 자리에서 살아나고 있는가.",
            "이 부를 읽으며, 관계의 깊이가 갈등을 통과한 자리에서 빚어지는 결을 따라가 보십시오.",
        ],
    },
    4: {
        "headline": "함께 사는 공동체의 자리",
        "paragraphs": [
            "관계의 마지막 자리는 공동체입니다. 한 영혼이 다른 영혼과의 관계에서 빚어졌어도, 그 관계가 더 큰 자리 — 곧 공동체 — 안에 들어가지 못하면 반쪽짜리 영성입니다. 우리는 부르심 받은 자들의 모임 안에서 비로소 완전한 영성을 살아낼 수 있습니다.",
            "교회는 그 부르심의 자리입니다. 모자이크의 신비처럼 다양한 영혼이 한 그림을 이루는 자리, 한 몸의 지체들이 서로 다른 결로 한 결에 기여하는 자리. 불완전함 속의 은혜가 그 결의 가장 정직한 표현입니다. 완벽한 사람들의 모임이 아니라, 불완전한 사람들이 함께 있음의 거룩함을 살아내는 자리.",
            "함께 있음 자체가 거룩합니다. 우리는 자주 사역의 결과로 거룩함을 측정하려 하지만, 성경은 함께 있음 자체가 이미 거룩의 자리임을 가르칩니다. 서로 섬기는 아름다움, 영원한 공동체를 향한 자세가 그 결의 마지막입니다.",
            "공동체로 사는 삶은 결국 한 몸의 신비입니다. 혼자서는 완전할 수 없습니다. 각 지체가 자기 자리를 지키면서 서로 의존하는 용기, 함께 울고 함께 웃는 자세, 그리고 갈등마저도 품을 줄 아는 공동체. 그 공동체가 결국 세상을 향한 한 몸이 되어 흘러갑니다.",
            "이 부의 두 권은 공동체의 두 결을 응시합니다. 「교회 공동체의 아름다움」은 부르심 받은 자들의 모임이 어떻게 모자이크의 신비를 이루는가를, 「공동체로 사는 삶」은 한 몸의 신비와 세상을 향한 한 몸의 자리를 다룹니다.",
            "곁에 두신 분들이 결국 공동체로 모인다는 것을, 두 권의 결 위에서 마지막으로 새겨 보십시오.",
        ],
        "guides": [
            "내가 속한 교회 공동체에서, 나는 모자이크의 어느 자리에 놓인 한 조각인가.",
            "함께 있음 자체가 거룩하다는 한 마디가, 내 공동체 생활의 어떤 자리에서 살아나고 있는가.",
            "갈등마저 품는 공동체의 결을, 나는 어떻게 살아내고 있는가.",
            "이 부를 읽으며, 곁에 두신 분들이 어떻게 공동체로 모이는가에 주목해 보십시오.",
        ],
    },
}


# 권별 요약 (각 책 진입부 — 3단락, 약 70% 분량)
# 마지막 단락의 핵심 한 문장은 3번째 단락 끝에 흡수
BOOK_SUMMARIES = {
    1: [
        "하나님이 설계한 결혼이 첫 장의 자리다. 결혼은 사회적 제도가 아니라 창조의 신비다. 두 영혼이 한 몸이 되는 결합. 그 결합이 그리스도와 교회의 관계를 비추는 거룩한 거울이라는 결을 책은 풀어낸다.",
        "일부일처와 하나님의 공의가 짚어진다. 결혼은 한 사람을 향한 평생의 약속이며, 그 약속이 빚는 안전한 둘레가 두 영혼이 자라는 자리가 된다. 신부 된 교회와 신랑 되신 그리스도의 비유 안에서, 결혼의 가장 깊은 신학이 드러난다.",
        "열 처녀의 지혜와 이혼과 멍에의 신학이 펼쳐진다. 결혼의 기쁨과 함께 결혼의 고통도 정직하게 다룬다. 마지막 장 — 결혼을 앞둔 자녀에게. 결혼이 사랑으로 시작되어 약속으로 자라고 신비로 완성되는 결을 가르치는 한 어른의 목소리가 거기 있다.",
    ],
    2: [
        "하나님의 부모됨이 첫 장의 자리다. 우리가 누군가의 부모가 되기 전에, 우리에게 하나님 아버지가 계셨다는 사실이 모든 부모됨의 근본이다. 그분의 부모됨을 닮는 결이 우리의 부모됨의 결을 정한다.",
        "사랑의 언어가 짚어진다. 같은 사랑이라도 자녀마다 받아들이는 결이 다르다. 그 다름을 인정하지 못한 사랑은 자주 어긋난다. 그리고 상처 입은 아버지상의 회복이 다음 결이다. 우리 자신의 아버지상이 회복되어야 우리 자녀의 아버지상도 빚어진다.",
        "훈육의 지혜와 영적 대물림이 차례로 펼쳐진다. 떠나보냄의 축복이 깊다. 자녀를 끝까지 붙들고 있는 사랑이 아니라, 때가 되면 떠나보내는 사랑. 그것이 가장 큰 사랑이다. 마지막 장 — 믿음의 유산. 부모가 자녀에게 남길 수 있는 가장 큰 유산이 무엇인가의 물음에 대한 답이 거기 있다.",
    ],
    3: [
        "믿음은 유전되지 않는다. 첫 장의 결정적 한 마디다. 부모가 신앙인이라고 해서 자녀가 자동으로 신앙인이 되는 게 아니다. 횃불 릴레이처럼 한 세대가 다음 세대에게 직접 건네야 하는 결이 있다.",
        "아브라함의 언약이 짚어진다. 한 사람의 믿음이 한 가문의 결을 정하고, 그 가문의 결이 한 민족의 결로 자라난 사례. 가정이라는 성소가 그 결의 토대다. 디모데의 믿음이 외할머니 로이스와 어머니 유니게에게서 시작되었다는 사실이 그 결의 가장 또렷한 증언이다.",
        "세대 차이를 넘어가는 자세가 짚어진다. 다른 세대의 언어를 배우고, 다른 세대의 결을 존중하면서, 핵심의 결을 함께 잇는 자세. 마지막 장 — 다음 세대에게 남기는 것. 우리가 남길 수 있는 가장 단단한 유산은 재산이 아니라 한 영혼의 결이라는 것을 책은 가장 정직하게 풀어낸다.",
    ],
    4: [
        "영혼의 동반자가 첫 장의 자리다. 친구는 가족이 아니지만 가족만큼 가까운 자리에 있는 사람이다. 우리가 선택한 가족, 또는 하나님이 우리에게 보내신 또 다른 동행자. 그 자리의 결을 책은 정직하게 응시한다.",
        "다윗과 요나단의 우정이 짚어진다. 자기 왕좌를 양보한 요나단의 결단, 그를 향한 다윗의 한 평생의 그리움. 그 두 영혼 사이에 흐른 결이 우정의 가장 깊은 모범이다. 나침반 같은 친구, 신실함의 무게가 그 결을 빚는다.",
        "쇠가 쇠를 날카롭게 하듯, 친구는 서로를 빚어 가는 자리다. 함께 기도하는 자리가 그 결의 가장 깊은 자리다. 마지막 장 — 나는 누군가의 요나단인가. 친구를 받기만 하는 자리가 아니라 누군가의 친구가 되어 주는 자리가 우정의 진짜 자리다.",
    ],
    5: [
        "누가 나의 이웃인가의 첫 물음에서 책은 시작한다. 율법교사의 자기 의를 정직하게 풀어내는 자리. 예수께서 그에게 답하신 사마리아인의 비유가 책 전체의 결을 정한다.",
        "강도 만난 자를 지나친 사람들이 짚어진다. 제사장과 레위인은 종교적 정결을 위해 그 자리를 지나갔다. 그러나 사마리아인은 멈췄다. 그 한 결단의 차이가 결국 영성의 자리를 정한다. 사마리아인이 멈춰 선 이유가 그가 더 영적이었기 때문이 아니라, 그가 자기 시간과 자기 자리를 내어주기로 결단했기 때문이다.",
        "경계를 넘는 용기, 시간과 돈을 내어주는 사랑, 끝까지 책임지는 사랑이 차례로 짚어진다. 마지막 장 — 가서 너도 이와 같이 하라. 예수의 한 마디가 우리에게 던져진다. 이웃 사랑은 알고 있는 자리가 아니라 살아내는 자리다.",
    ],
    6: [
        "용서, 한 번이 아닌 반복의 길이 첫 장의 자리다. 일곱 번이라도 충분하지 않다고 베드로가 물었을 때, 예수께서는 일흔 번씩 일곱 번이라 답하셨다. 용서는 사건이 아니라 길이라는 한 마디가 책 전체의 결을 정한다.",
        "관계의 호흡으로서의 용서가 짚어진다. 호흡처럼 매일 들이쉬고 내쉬어야 하는 결. 내가 먼저 받은 용서가 그 흐름의 근원이다. 우리가 누구를 용서한다는 것은 우리가 십자가에서 받은 용서를 흘려보내는 일이다.",
        "용서와 허용 사이가 짚어진다. 둘은 같지 않다. 잘못을 용서한다고 해서 잘못을 허용하는 게 아니다. 상처받은 마음의 정직한 고백, 용납하는 공동체의 능력이 차례로 펼쳐진다. 마지막 장 — 끝나지 않는 용서의 여정. 용서는 종착점이 아니라 평생 걷는 길이다.",
    ],
    7: [
        "갈등의 실체가 첫 장의 자리다. 갈등 없는 관계는 없다는 정직한 진단에서 책은 시작한다. 갈등을 부정하거나 숨기는 영성은 깊어지지 않는다. 갈등을 정직하게 마주하는 자리에서 비로소 화해가 가능하다.",
        "회피가 아닌 직면이 짚어진다. 우리는 자주 갈등을 회피한다. 그것이 평화처럼 보이지만 사실은 거짓 평화다. 화해의 다리를 놓는 자세, 그리고 용서의 능력이 그 다음 결이다. 화평케 하는 자의 복은 갈등이 없는 자에게 주어진 복이 아니다.",
        "관계의 회복이 짚어진다. 회복은 갈등 이전으로 돌아가는 게 아니라 갈등을 통과한 더 깊은 자리로 옮겨 가는 것이다. 마지막 장 — 평화를 만드는 삶. 평화는 받는 게 아니라 만드는 것이다. 그것이 화평케 하는 자의 가장 깊은 자리다.",
    ],
    8: [
        "홀로 있음의 축복이 첫 장의 자리다. 우리는 너무 자주 홀로 있음을 외로움으로만 다룬다. 그러나 성경은 홀로 있음을 축복의 자리로도 본다. 광야로 부르시는 하나님의 결이 그 자리에서 시작된다.",
        "고요한 물에 비친 하늘이 짚어진다. 분주한 물에서는 하늘이 비치지 않는다. 자기 안의 분주함이 가라앉을 때 비로소 하늘이 비친다. 외로움과 고독 사이의 분별이 깊다. 외로움은 결핍의 자리이지만 고독은 충만의 자리다.",
        "홀로 서야 함께 설 수 있다는 한 마디가 책의 가장 단단한 결이다. 자기 자신과 마주하지 못한 사람은 다른 영혼과도 진실되게 마주할 수 없다. 자기 자신과 마주하는 용기가 모든 관계의 토대다. 마지막 장 — 홀로, 그러나 혼자가 아닌. 진짜 홀로 섬은 외로움이 아니라 그분과의 동행 안에서 얻는 자리다.",
    ],
    9: [
        "부르심 받은 자들의 모임이 첫 장의 자리다. 교회는 단순한 단체가 아니다. 한 영혼 한 영혼이 하나님의 부르심으로 그 자리에 모인 자들의 모임이다. 그 사실이 교회의 본질을 정한다.",
        "모자이크의 신비가 짚어진다. 다양한 색깔과 모양의 조각들이 한 그림을 이루는 모자이크처럼, 다양한 영혼이 한 교회를 이룬다. 한 몸의 지체들 — 머리·손·발·눈·귀가 모두 다른 자리이지만 한 몸이다. 그 다양성이 교회의 아름다움이다.",
        "불완전함 속의 은혜가 짚어진다. 교회는 완벽한 사람들의 모임이 아니다. 불완전한 사람들이 함께 있음의 거룩함을 살아내는 자리다. 서로 섬기는 아름다움이 그 결의 핵심이다. 마지막 장 — 영원한 공동체를 향하여. 우리가 지금 살아가는 교회는 결국 영원한 공동체의 미리 맛봄이다.",
    ],
    10: [
        "혼자서는 완전할 수 없다. 첫 장의 한 마디가 책 전체의 결이다. 우리는 관계 안에서 빚어진 존재이며, 관계 너머에서 우리의 정체성은 존재할 수 없다. 한 몸의 신비가 그 토대다.",
        "각 지체의 자리가 짚어진다. 모든 지체가 같은 자리를 차지할 수 없고, 모든 지체가 다른 자리를 차지해야 한다. 서로 의존하는 용기가 그 다음 결이다. 자기 충족이라는 거짓 신화에서 벗어나, 서로에게 의존할 줄 아는 자세가 진짜 영성의 자리다.",
        "함께 울고 함께 웃다, 갈등을 품는 공동체가 차례로 펼쳐진다. 갈등이 없는 공동체가 아니라, 갈등을 품을 줄 아는 공동체가 진짜 공동체다. 마지막 장 — 세상을 향한 한 몸. 공동체는 자기 안에 갇히지 않는다. 결국 세상을 향해 흘러나간다. 그 흐름이 곁에 두신 분들의 마지막 결이다.",
    ],
}


# 권별 길잡이 — 그 한 권만의 좁고 깊은 화두 (부 길잡이와 차별)
BOOK_GUIDES = {
    1: [
        "결혼이 사회적 제도가 아니라 창조의 신비라면, 내 결혼의 자리는 어떤 결로 살아나고 있는가.",
        "그리스도와 교회의 관계를 비추는 결혼이라는 거울 앞에서, 내 결혼은 무엇을 비추고 있는가.",
        "이혼과 멍에의 신학 앞에서, 결혼의 약속을 매일 다시 새기는 자세를 나는 어떻게 살아내고 있는가.",
    ],
    2: [
        "하나님의 부모됨을 닮는 결이, 내 부모됨의 어떤 자리에서 살아나고 있는가.",
        "사랑의 언어가 자녀마다 다르다는 것을, 나는 어떻게 받아들이고 있는가.",
        "떠나보냄의 축복 — 때가 되면 자녀를 떠나보내는 사랑의 결을, 나는 어떻게 준비하고 있는가.",
    ],
    3: [
        "믿음은 유전되지 않는다는 한 마디 앞에서, 나는 다음 세대에게 무엇을 직접 건네고 있는가.",
        "디모데의 믿음이 외할머니와 어머니에게서 시작되었듯, 내 믿음의 뿌리는 누구의 자리에서 흘러왔는가.",
        "다음 세대에게 남길 가장 큰 유산이 한 영혼의 결이라면, 나는 어떤 결을 빚어 가고 있는가.",
    ],
    4: [
        "다윗의 요나단처럼 내 곁에 신실한 친구가 있는가, 또는 내가 누구의 요나단이 되고 있는가.",
        "쇠가 쇠를 날카롭게 하듯, 나를 빚어 주는 친구의 결이 내 어떤 자리에서 살아나고 있는가.",
        "함께 기도하는 자리가 우정의 가장 깊은 자리라면, 내 우정은 그 자리에 닿고 있는가.",
    ],
    5: [
        "누가 나의 이웃인가의 물음 앞에서, 내가 지나치고 있는 강도 만난 자는 누구인가.",
        "사마리아인이 멈춰 선 결단을, 내 일상의 어떤 자리에서 살아내고 있는가.",
        "끝까지 책임지는 사랑이라는 한 마디가, 내 어떤 결단으로 자라고 있는가.",
    ],
    6: [
        "용서가 사건이 아니라 길이라는 한 마디 앞에서, 내 용서의 길은 어디를 걷고 있는가.",
        "용서와 허용 사이의 차이를, 나는 어떤 관계에서 분별하고 있는가.",
        "내가 먼저 받은 용서가 흘러나가는 통로로서의 내 용서를, 나는 어떻게 살아내고 있는가.",
    ],
    7: [
        "갈등을 회피하는 자리에서 직면하는 자리로, 나는 어떻게 옮겨 가고 있는가.",
        "화평케 하는 자가 갈등 없는 자가 아니라 갈등 한복판에서 평화를 만드는 자라면, 나는 어디서 그 자리에 서고 있는가.",
        "관계의 회복이 갈등 이전으로 돌아가는 게 아니라 더 깊은 자리로 옮겨 가는 것이라면, 나는 어떤 회복의 자리에 도달하고 있는가.",
    ],
    8: [
        "홀로 있음이 외로움이 아니라 축복일 수 있다는 한 마디가, 내 어디서 살아나고 있는가.",
        "외로움과 고독 사이의 분별을, 내 일상은 어떻게 살아내고 있는가.",
        "홀로 서야 함께 설 수 있다는 한 마디가, 내 관계의 토대를 어떻게 다시 빚고 있는가.",
    ],
    9: [
        "부르심 받은 자들의 모임이라는 한 마디 앞에서, 나는 어떤 부르심의 자리에 서 있는가.",
        "모자이크의 신비처럼, 내 자리는 그림 전체에서 어떤 색깔의 조각인가.",
        "불완전한 사람들이 함께 있음의 거룩함을, 나는 어떻게 살아내고 있는가.",
    ],
    10: [
        "혼자서는 완전할 수 없다는 한 마디 앞에서, 내 자기 충족의 자리는 어떻게 다시 빚어지고 있는가.",
        "서로 의존하는 용기가, 내 어떤 관계에서 자라고 있는가.",
        "갈등을 품는 공동체의 결이, 내 공동체 생활에서 어떻게 살아나고 있는가.",
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
  <div style="color:#888;font-size:0.88em;margin-top:0.3em">원본 ISBN {b['isbn']} · G09 제 {b['src_no']:02d} 권</div>
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
<h3 style="color:#0F1E3C;margin-top:1.5em">곁에 두신 분들이 빚는 영성</h3>
<p>이로써 G09 열 권의 묵상이 한 권으로 닫힙니다. 결혼의 신학에서 시작해 공동체로 사는 삶에 이르기까지, 곁에 두신 분들이 빚어 내는 결을 네 갈래로 모아 함께 걸어왔습니다. 처음에는 흩어져 있던 한 권 한 권의 묵상이 한 호흡으로 이어 붙고 나니, 사이를 흐르고 있던 결이 비로소 또렷해졌습니다.</p>
<p>이 책이 묻고자 했던 한 가지 물음은 분명합니다. <em>곁에 두신 분들이 부르심이라는 것을, 한 영혼이 어떻게 받아들이고 살아낼 것인가.</em> 가장 가까운 자리에서 시작되는 가족의 결과, 친구와 이웃이라는 동심원과, 갈등과 화해를 통과한 깊이와, 공동체로 모이는 마지막 자리 — 그 넷이 그 답의 네 갈래였습니다.</p>
<p><strong>1부에서 우리는 가장 가까운 자리</strong>에 함께 섰습니다. 결혼의 신학에서 부모와 자녀의 사랑의 언어를 거쳐 세대를 잇는 믿음의 횃불 릴레이까지. 가장 가까운 자리가 영성의 가장 정직한 시험대라는 것을 함께 새겼습니다.</p>
<p><strong>2부에서 우리는 친구와 이웃</strong>이라는 동심원을 그려 갔습니다. 다윗과 요나단의 신실함, 사마리아인이 멈춰 선 자리. 친구와 이웃이 가족 너머의 영성의 자리라는 것을, 두 권의 결 위에서 다시 보았습니다.</p>
<p><strong>3부에서 우리는 갈등과 화해</strong>를 통과했습니다. 반복되는 용서의 길, 회피가 아닌 직면의 화해, 그리고 모든 관계의 토대로서의 홀로 섬. 갈등을 통과한 자리에서 관계가 깊어진다는 것을 함께 새겼습니다.</p>
<p><strong>4부에서 우리는 공동체의 자리</strong>에 도달했습니다. 부르심 받은 자들의 모임으로서의 교회, 한 몸의 신비를 살아내는 공동체. 곁에 두신 분들이 결국 공동체로 모인다는 것을, 두 권의 마지막 결 위에서 함께 보았습니다.</p>
<p>이 책의 가장 단단한 한 마디는 표제에 이미 담겨 있습니다 — <em>곁에 두신 분들.</em> 우리 곁에 있는 사람들은 우연이 아닙니다. 부르심입니다. 가족도, 친구도, 이웃도, 교회 공동체도 모두 그분이 곁에 두신 분들입니다. 그 부르심을 받아들이는 자세에서 우리의 영성이 가장 정직하게 빚어집니다.</p>
<p>이 책을 덮으신 뒤에도 묵상은 끝나지 않습니다. 한 장씩 다시 펼쳐 읽어도 좋고, 한 단락만 천천히 반복해 읽어도 좋습니다. 관계를 우연으로 다루던 자리에서 부르심으로 받아들이는 자리로 한 결이라도 옮겨 가셨다면, 그것만으로도 G09 열 권을 한 권으로 묶은 이유는 충분할 것입니다.</p>
<p>이제 100권 시리즈는 마지막 G10을 향해 흘러갑니다. 곁에 두신 분들이 빚는 영성의 결은 이 한 권에 모였습니다. 마지막 그룹에서 또 다른 깊은 묵상으로 다시 만나기를 기도합니다. 주님의 평강이 여러분의 오늘 위에 충만히 임하시기를 축복합니다.</p>
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
    uuid_id = f"omnibus-g09-{today_compact}-{datetime.now().strftime('%H%M%S')}"

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
    <dc:description>{proj['subtitle']} — G09 10권 종합본</dc:description>
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
    print("ISBN 발급 시 batch_books_g09_omnibus.json의 isbn 필드에 입력 후 재빌드.")


if __name__ == "__main__":
    main()
