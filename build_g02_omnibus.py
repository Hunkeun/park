# -*- coding: utf-8 -*-
"""
G02 10권 종합책 "알고리즘 시대의 영혼" epub 빌더.

입력:
  - batch_books_g02_omnibus.json (메타·4부 구조)
  - tmp/g02_omnibus_extracted.json (10권 본문 추출본)
  - G02 epub 중 한 권 (CSS 추출용)

출력:
  - ~/Downloads/전자책/알고리즘_시대의_영혼_YYYYMMDD_종합책.epub

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
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from qr_util import make_qr_png_bytes, catalog_url

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PROJECT = Path(__file__).parent
META_PATH = PROJECT / "batch_books_g02_omnibus.json"
EXTRACT_PATH = PROJECT / "tmp" / "g02_omnibus_extracted.json"
SAMPLE_EPUB = Path.home() / "Downloads" / "전자책" / "AI가_묻는_신앙의_질문들_20260418.epub"
OUT_DIR = Path.home() / "Downloads" / "전자책"
OUT_BACKUP_DIR = PROJECT / "tmp"  # 보조 사본


def get_css():
    """샘플 epub에서 CSS 추출."""
    with zipfile.ZipFile(SAMPLE_EPUB, "r") as z:
        return z.read("OEBPS/styles/style.css").decode("utf-8")


def get_cover_image():
    """전용 종합책 표지 사용 (없으면 샘플로 폴백)."""
    custom = PROJECT / "tmp" / "g02_omnibus_cover.jpg"
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
  <p><strong>구성</strong>　G02 10권 종합책 (4부 70장)</p>
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
    <p>이 책은 100권 영성 시리즈 G02(AI·디지털 시대의 신앙) 10권의 본문을 거의 그대로 4부 구조로 재편집하여 한 권으로 묶은 종합본입니다.</p>
    <p>각 권의 원본 ISBN 및 출간 정보는 본문 권별 도입 페이지에 명기되어 있습니다.</p>
  </div>
</div></div>"""
    return xhtml_doc("판권", body)


def build_preface_xhtml() -> str:
    body = """<div style="padding:2em 1.5em;line-height:1.9;font-size:1em;color:#222">
<h2 style="color:#0F1E3C;border-bottom:1px solid #C8B99A;padding-bottom:0.5em">여는 글</h2>
<h3 style="color:#0F1E3C;margin-top:1.5em">알고리즘 너머의 영혼을 보며</h3>
<p>우리는 알고리즘의 시대를 살아갑니다. 아침에 눈을 뜨는 알람도, 출근길의 경로도, 점심 식당의 추천도, 퇴근 뒤 펼치는 영상의 순서도 모두 알고리즘이 빚어 놓은 흐름입니다. 보이지 않는 손이 우리의 일상을 매 순간 조용히 편집하고 있는 셈입니다.</p>
<p>그 한복판에 그리스도인이 서 있습니다. 알고리즘은 우리의 클릭 패턴을 읽지만, 새벽 세 시에 무릎을 꿇는 한 영혼의 무게는 어떤 데이터도 측정하지 못합니다. AI는 우리의 글을 흉내 낼 수 있지만, 그 글 속에 흐르는 영혼의 결을 알아보지는 못합니다. 알고리즘 너머에 영혼이 있고, 그 영혼은 결코 데이터로 환원되지 않습니다.</p>
<p>이 책은 100권 영성 시리즈의 두 번째 그룹 G02를 한 권으로 묶은 종합본입니다. AI가 묻는 신앙의 질문부터 디지털 선교의 미래까지, 알고리즘 시대를 살아가는 그리스도인의 가장 정직한 묵상을 열 갈래로 펼쳐 놓았습니다. 열 권 각각의 본문을 거의 그대로 유지하면서, 그 사이를 흐르고 있던 결을 네 갈래로 모았습니다.</p>
<p>네 갈래는 이렇게 흐릅니다. AI가 우리에게 던지는 질문, 알고리즘 너머의 신학, 디지털 일상의 영성, 그리고 교회와 선교의 미래. 이 넷은 따로 흐르는 것 같으면서도 결국 한 강을 이룹니다.</p>
<p><strong>1부 — 새 시대의 질문</strong>은 AI가 우리에게 던지는 거울 앞에서 신앙의 본질을 다시 묻고, <strong>2부 — 보이지 않는 손의 신학</strong>은 알고리즘·빅데이터·트랜스휴머니즘 한복판에서 섭리와 영혼의 자리를 응시합니다. <strong>3부 — 디지털 일상의 영성</strong>은 기도·예배·인간 존엄이 디지털 세계 안에서 어떻게 흘러야 하는가를 다루고, <strong>4부 — 교회와 선교의 미래</strong>는 AI 목회와 디지털 선교에서 교회의 다음 풍경을 봅니다.</p>
<p>이 책은 AI 시대의 모든 질문에 답하지 않습니다. 다만 그 질문들 앞에서 떠밀리지 않을 수 있는 자리, 곧 알고리즘 너머의 영혼을 정직하게 응시하는 묵상의 자리로 한 사람을 데려가려 합니다. 답을 서두르기보다 호흡을 가다듬는 자리, 새 시대 앞에서 변하지 않는 한 결을 함께 잡아 보는 자리. 이 책이 그런 자리가 되어 드린다면, G02 열 권을 한 권으로 묶은 의미는 충분할 것입니다.</p>
<p>한 번에 다 읽어내실 책이 아닙니다. 한 장씩, 한 묵상씩 호흡을 따라 가져가시면 됩니다. 이제 첫 장을 펼쳐 주십시오. 알고리즘의 한복판에서, 그러나 알고리즘에 길들여지지 않은 영혼의 자리에서, 한 호흡씩 함께 걸어가 봅시다.</p>
</div>"""
    return xhtml_doc("여는 글", body)


PART_INTROS = {
    1: {
        "headline": "AI가 우리에게 던지는 거울",
        "paragraphs": [
            "AI는 우리에게 도구로 다가왔지만, 막상 그 앞에 서고 보면 도구라기보다 거울에 가깝습니다. 우리가 무엇을 묻는가에 따라 우리가 누구인가가 드러나는, 그런 거울 말입니다.",
            "AI는 정보를 제공하지만 정작 우리에게 가장 깊은 질문을 되돌려 줍니다. 이 모든 답을 받고 나면, 그래서 인간이라는 존재는 무엇인가. 무엇이 대체될 수 있고 무엇이 대체될 수 없는가. 알고리즘이 효율을 극대화하는 시대에 신앙은 어떤 자리에 서야 하는가.",
            "AI는 또한 성경 앞에 우리를 다시 세웁니다. 새로운 렌즈로 오래된 말씀을 읽는 일은, 한편으로 풍성함을 더해 주지만 다른 한편으로 우리가 말씀을 정보처럼 다루는 자리로 미끄러질 위험도 함께 안고 있습니다. 문자와 영, 정보와 증언, 분석과 묵상의 결을 다시 분별해야 하는 자리입니다.",
            "이 부의 두 권은 AI가 그리스도인에게 던지는 두 거울을 차례로 응시합니다. 「AI가 묻는 신앙의 질문들」은 AI가 우리 신앙에 던지는 본질적 물음들을 풀어내고, 「AI와 함께 읽는 성경」은 AI라는 새 렌즈 앞에서 성경을 어떻게 더 깊이 만날 것인가를 다룹니다.",
            "거울 앞에 서는 자세는 두 가지입니다. 거울에 비친 자기를 부인하거나, 그 모습 앞에서 자기를 다시 빚거나. AI가 우리에게 던지는 거울 앞에서, 그리스도인은 어느 자세를 택할 것인가를 함께 물어 봅시다.",
        ],
        "guides": [
            "AI가 우리 신앙에 던지는 가장 본질적인 질문은 무엇이며, 나는 그 질문 앞에서 어떻게 응답하고 있는가.",
            "AI가 대체할 수 있는 것과 결코 대체할 수 없는 것의 경계를, 나는 어떻게 분별하고 있는가.",
            "AI라는 새 렌즈로 성경을 읽을 때, 나는 풍성함을 얻고 있는가 아니면 정보처럼 다루는 자리로 미끄러지고 있는가.",
            "이 부를 읽으며, AI가 우리에게 던지는 거울 앞에서 신앙의 본질이 어떻게 다시 또렷해지는가에 주목해 보십시오.",
        ],
    },
    2: {
        "headline": "알고리즘 너머의 손",
        "paragraphs": [
            "보이지 않는 손이 우리의 일상을 편집합니다. 어떤 영상을 볼지, 어떤 광고에 노출될지, 어떤 친구의 소식이 먼저 도착할지를 알고리즘이 결정합니다. 우리는 자유로운 선택을 한다고 믿지만, 사실 그 선택지의 배열은 이미 누군가의 손에 의해 짜여 있습니다.",
            "그러나 알고리즘 너머에 또 한 손이 있습니다. 데이터로 환원되지 않는 그 손은, 우리가 섭리라고 부르는 한 손입니다. 알고리즘은 과거의 패턴으로 미래를 예측하지만, 섭리는 한 영혼의 미래를 위해 과거의 패턴을 깨뜨리기도 합니다. 그래서 알고리즘이 절대화되는 시대에 우리는 더 정직하게 묻습니다. 그렇다면 섭리는 무엇인가.",
            "빅데이터는 측정의 시대를 열었지만, 측정되지 않는 것이 있다는 사실을 더 또렷이 드러내기도 했습니다. 영혼은 그래프에 담기지 않고, 사랑의 무게는 공식으로 환원되지 않으며, 용서라는 불가능한 수학과 은혜라는 공식 밖의 선물은 데이터의 언어로 결코 측정되지 않습니다.",
            "트랜스휴머니즘은 인간의 한계를 결함으로 보고 업그레이드하려 합니다. 그러나 성경은 인간의 한계가 결함이 아니라 설계라고 말합니다. 연약함은 폐기물이 아니라 복음이며, 하나님의 형상은 실리콘의 형상으로 대체되지 않습니다.",
            "이 부의 세 권은 보이지 않는 손의 신학을 차례로 펼칩니다. 「알고리즘과 섭리」는 데이터 너머의 설계자를, 「빅데이터가 모르는 것」은 측정되지 않는 영적 실재를, 「트랜스휴머니즘과 영혼」은 업그레이드되지 않는 인간의 자리를 다룹니다.",
            "알고리즘이 전부인 것처럼 보이는 시대에, 그 너머의 한 손을 함께 응시해 보십시오.",
        ],
        "guides": [
            "알고리즘이 우연의 탈을 쓴 섭리를 가릴 때, 나는 그 너머의 손을 어떻게 알아보고 있는가.",
            "빅데이터가 측정하지 못하는 영적 실재 — 사랑·용서·은혜를 나는 일상에서 어떻게 증언하고 있는가.",
            "한계가 결함이 아니라 설계라는 한 마디를, 나는 내 약함 앞에서 어떻게 받아들이고 있는가.",
            "이 부를 읽으며, 알고리즘 너머의 손이 어떻게 내 오늘을 다시 빚고 있는가를 따라가 보십시오.",
        ],
    },
    3: {
        "headline": "픽셀 사이의 기도",
        "paragraphs": [
            "디지털 일상은 우리의 영성을 바꾸어 놓았습니다. 알림이 끊임없이 울리고, 화면이 한순간도 비어 있지 않으며, 우리의 주의는 끝없이 분산됩니다. 그 한복판에서 기도는 어떤 자리에 있어야 합니까.",
            "기도의 본질은 변하지 않습니다. 다만 기도가 흘러야 할 자리가 디지털의 한복판이라는 점이 새롭습니다. 알림의 홍수 속에서 가장 조용한 메시지를 듣는 자리, 다오다오 식으로 빠르게 처리하는 기도가 아니라 침묵이라는 혁명을 회복하는 자리. 디지털 시대의 기도는 도구를 바꾸는 일이 아니라 결을 회복하는 일입니다.",
            "예배 또한 새로운 자리에 섭니다. 메타버스 속의 예배는 가능한가, 가능하다면 어디까지 가능한가. 공간을 초월하는 임재의 신비를 놓치지 않으면서, 동시에 몸의 교제라는 결코 대체될 수 없는 자리도 함께 지켜야 합니다. 사진과 실재 사이에서 분별하는 자세입니다.",
            "그리고 인간 존엄이 흔들립니다. 로봇이 일을 대체하고 능력으로 한 사람의 가치가 측정되는 시대에, 흙으로 빚으신 손길과 형상의 비밀은 어떻게 회복됩니까. 진품과 모조품 사이에서, 능력 너머의 가치를 회복하는 자리에서 우리는 다시 이웃의 얼굴을 봅니다.",
            "이 부의 세 권은 디지털 일상의 영성을 차례로 응시합니다. 「디지털 시대의 기도」는 알림의 홍수 속 침묵의 자리를, 「메타버스 속의 예배」는 디지털 예배의 가능성과 한계를, 「로봇 시대의 인간 존엄」은 능력 너머의 가치를 다룹니다.",
            "픽셀 사이에서도 영성이 흐를 수 있는가 — 그 물음 앞에서 함께 호흡을 가다듬어 봅시다.",
        ],
        "guides": [
            "알림의 홍수 속에서 나는 가장 조용한 메시지를 어떻게 듣고 있는가, 아니면 그 음성을 놓치고 있는가.",
            "메타버스 속의 예배가 가능한 자리와 결코 대체되지 않는 몸의 교제의 자리를, 나는 어떻게 분별하고 있는가.",
            "능력으로 사람의 가치가 측정되는 시대에, 나는 이웃의 얼굴을 능력 너머에서 어떻게 보고 있는가.",
            "이 부를 읽으며, 디지털 일상 한복판에서도 흐를 수 있는 영성의 결을 따라가 보십시오.",
        ],
    },
    4: {
        "headline": "교회의 다음 풍경",
        "paragraphs": [
            "교회는 이천 년 동안 시대의 변화를 통과해 왔습니다. 로마의 도로 위에서 복음이 흐르던 시대, 인쇄술이 종교개혁을 일으킨 시대, 라디오와 텔레비전이 강단을 확장한 시대. 그리고 지금, AI와 디지털의 시대 앞에 교회가 서 있습니다.",
            "물음은 단순하지만 무겁습니다. AI가 강단에 설 수 있는가. 알고리즘이 말씀을 전달할 수는 있어도, 한 영혼이 한 영혼에게 증언하는 그 자리에 알고리즘이 설 수 있는가. 설교는 정보의 전달이 아니라 한 사람의 증언이며, 악보를 읽는 일과 연주하는 일이 같지 않듯 코드와 성령은 결코 같지 않습니다.",
            "그러나 디지털 시대의 부르심을 외면해서도 안 됩니다. 로마 도로가 광케이블이 된 이 시대에, 대위임령은 어떻게 새 양식으로 흘러가야 합니까. 유튜브가 디지털 강단이 되고, 소셜미디어가 일상 속 증인의 자리가 되며, 알고리즘 너머의 한 영혼을 향한 사랑이 새 선교의 결을 빚어 갑니다.",
            "교회의 다음 풍경은 둘 사이의 균형 위에 서 있습니다. 양을 아는 목자의 자리와 디지털 도구의 활용. 온라인의 확장성과 오프라인의 깊이. 약한 자를 부르시는 하나님의 부르심 앞에서, 우리는 미래의 선교사가 곧 우리 손안의 스마트폰이 될 수 있다는 사실을 다시 발견합니다.",
            "이 부의 두 권은 교회의 다음 풍경을 정면으로 응시합니다. 「AI 목사가 올 수 있는가」는 강단과 성령의 자리를 다시 묻고, 「디지털 선교의 미래」는 광케이블 시대의 대위임령을 펼쳐냅니다.",
            "교회의 다음 풍경 안에서, 변하지 않는 한 결과 변해야 하는 한 결을 함께 분별해 보십시오.",
        ],
        "guides": [
            "설교가 정보의 전달이 아니라 한 사람의 증언이라는 것을, 내 듣는 자리는 어떻게 살아내고 있는가.",
            "코드와 성령이 같지 않다는 사실 앞에서, 나는 어디까지 디지털을 활용하고 어디서부터는 멈추어야 하는가.",
            "디지털 시대의 대위임령이 내 일상에 어떻게 적용되는가 — 내 스마트폰은 도구인가 우상인가 선교사인가.",
            "이 부를 읽으며, 교회의 다음 풍경 안에서 변하지 않는 한 결과 변해야 하는 한 결을 분별해 보십시오.",
        ],
    },
}


# 권별 요약 (각 책 진입부 — 3단락, 약 70% 분량)
# 마지막 단락의 핵심 한 문장은 3번째 단락 끝에 흡수
BOOK_SUMMARIES = {
    1: [
        "AI가 우리 앞에 도구로 다가왔지만, 막상 그 앞에 서고 보면 거울에 가깝다. 첫 권은 AI가 신앙에 던지는 첫 번째 질문에서 시작한다. 모든 답을 받고 나면, 그래서 인간이라는 존재는 무엇인가.",
        "저자는 지도와 길 사이의 차이를 짚는다. 지도는 정보이지만 길은 걸음이며, AI는 지도를 정교하게 그리지만 한 사람이 그 길을 걷는 일은 결코 대신할 수 없다. 대체될 수 있는 것과 대체될 수 없는 것의 경계가 거기서 또렷해진다.",
        "하나님의 필요는 줄어드는가. AI가 모든 답을 주는 시대에 신앙은 사치인가. 저자는 그 질문 앞에서 멈추지 않고 한 걸음 더 들어간다. 인간이라는 소명, 질문을 품은 신앙, 본질로 돌아가는 자리 — 그 세 자리에서 답이 빚어진다. AI가 묻는 첫 번째 질문은 결국 우리에게 본질을 다시 묻는 한 거울이다.",
    ],
    2: [
        "AI는 새로운 렌즈로 다가온다. 오래된 말씀을 새 렌즈로 읽는다는 것은 풍성함일 수도 있고 위험일 수도 있다. 이 한 권은 그 둘 사이의 결을 정직하게 분별한다. 현미경으로 생명을 분해하는 일과 생명을 살리는 일이 같지 않듯, 분석과 묵상은 같은 자리가 아니다.",
        "문자와 영의 차이가 짚어진다. AI는 문자를 처리하는 데 능하지만, 그 문자 너머에서 흐르는 영의 결은 알아보지 못한다. 질문하는 독자, 곧 묵상의 자리에 서는 한 영혼만이 말씀과 영의 결을 동시에 만질 수 있다.",
        "공동체와 알고리즘이 갈라지는 자리에서, 그리고 성령의 조명 아래에서 성경 읽기의 본질이 다시 또렷해진다. AI는 우리 성경 읽기를 풍성하게 할 수 있지만, 결코 우리 성경 읽기를 대체할 수는 없다. 새 렌즈는 도구이지 주체가 아니라는 한 마디가 이 책의 결이다.",
    ],
    3: [
        "데이터 너머에 한 설계자가 있다. 알고리즘이 우리 일상을 편집하는 시대에, 섭리는 어디로 갔는가. 이 한 권은 그 물음을 가장 정직한 자리에서 묻는다. 알고리즘은 과거의 패턴으로 미래를 예측하지만, 섭리는 한 영혼의 미래를 위해 과거의 패턴을 깨뜨리기도 한다.",
        "최적 경로를 아시는 하나님과 우연의 탈을 쓴 섭리가 짚어진다. 우리가 우연이라 부르는 자리에 사실은 한 손길이 있었다는 것을, 시간이 지나야 비로소 알아보게 되는 결을 저자는 차분히 풀어 간다.",
        "예측 불가능한 세계에서 신뢰한다는 것은 무엇인가. 두 세계관 — 데이터의 세계관과 섭리의 세계관 — 이 충돌하는 자리에서 우리는 어디에 발을 딛는가. 마지막 장은 목적지가 있는 여정이다. 알고리즘은 효율을 계산하지만, 섭리는 한 영혼의 목적지를 향한 길을 빚어 간다. 두 손이 결코 같지 않다.",
    ],
    4: [
        "측정의 시대다. 무엇이든 데이터로 환원하고, 무엇이든 그래프로 표현한다. 그러나 측정되지 않는 것이 있다는 사실을 빅데이터는 더 또렷이 드러내기도 했다. 이 한 권은 그 측정 너머의 자리를 응시한다.",
        "영혼은 그래프에 담기지 않고, 사랑의 무게는 공식으로 환원되지 않는다. 용서라는 불가능한 수학과 은혜라는 공식 밖의 선물 — 이 두 자리에서 데이터의 한계가 가장 또렷이 드러난다. 빅데이터는 의미를 측정할 수 없고, 바람의 방향은 알 수 있어도 그 의미는 측정하지 못한다.",
        "마지막 장은 하나님의 시선으로 나를 보는 일이다. 빅데이터는 우리를 패턴으로 본다. 하나님은 우리를 한 영혼으로 보신다. 그 차이가 결국 측정의 시대를 살아가는 그리스도인이 잃지 말아야 할 한 결이다.",
    ],
    5: [
        "트랜스휴머니즘은 인간을 업그레이드하려 한다. 그러나 그 유혹의 한복판에서 우리는 다시 묻는다. 인간의 한계는 결함인가 설계인가. 이 한 권은 그 물음을 정직하게 다룬다.",
        "하나님의 형상과 실리콘의 형상은 같지 않다. 영혼은 데이터가 아니며, 원작과 복제본이 결코 같은 가치를 가지지 않는다. 트랜스휴머니즘은 인간을 향상시킨다고 약속하지만, 사실은 인간을 다른 무엇으로 대체하려는 시도이기도 하다.",
        "연약함의 복음이 되살아난다. 한계는 결함이 아니라 설계라는 한 마디가, 약함을 폐기하려는 시대의 한복판에서 가장 깊은 위로가 된다. 마지막 장은 업그레이드되지 않는 인간이다. 그리스도인은 업그레이드의 대상이 아니라 사랑받는 대상이며, 약함은 폐기되어야 할 결함이 아니라 은혜가 흐르는 자리다.",
    ],
    6: [
        "알림의 홍수 속에서 가장 조용한 메시지를 듣는 일은 가능한가. 디지털 시대의 기도는 도구를 바꾸는 일이 아니라 결을 회복하는 일이다. 이 한 권은 그 결을 정직하게 짚는다.",
        "아날로그 기도와 디지털 기도가 갈라지는 자리, 다오다오 식으로 빠르게 처리하는 기도의 함정, 그리고 AI 시대의 분별 — 저자는 그 셋을 차례로 다룬다. 기도가 정보처럼 다뤄질 위험을 정확히 짚으면서, 그 위험을 넘어서는 결을 함께 그린다.",
        "침묵이라는 혁명이 회복된다. 알림이 끊임없이 울리는 시대에 침묵은 단순한 부재가 아니라 가장 능동적인 자리다. 마지막 장은 변하지 않는 대화다. 도구는 변해도 대화의 본질은 변하지 않는다. 디지털 시대에 우리가 회복해야 할 것은 새로운 기도법이 아니라 변하지 않는 기도의 결이다.",
    ],
    7: [
        "메타버스 시대가 도래했다. 가상의 공간에서 예배는 가능한가. 이 한 권은 그 물음 앞에서 정직하게 멈춘다. 예배란 무엇인가를 다시 묻고, 그 본질이 디지털 공간에서도 흐를 수 있는 자리와 결코 흐를 수 없는 자리를 분별한다.",
        "공간을 초월하는 임재의 신비는 분명히 있다. 하나님의 임재는 물리적 공간에 갇히지 않는다. 그러나 동시에 몸의 교제, 곧 한 사람과 한 사람이 같은 공간에서 호흡을 나누는 그 자리는 결코 대체될 수 없다.",
        "사진과 실재 사이에서 우리는 분별해야 한다. 디지털 예배는 사진처럼 실재의 한 측면을 담을 수는 있지만 실재 그 자체는 아니다. 마지막 장은 임재를 경험하는 자리로 우리를 데려간다. 메타버스가 가능한 자리는 가능한 대로, 결코 대체할 수 없는 자리는 그 자리대로 — 그 분별 위에서 디지털 시대의 예배가 빚어진다.",
    ],
    8: [
        "로봇이 일을 대체하는 시대에 인간 존엄은 어디서 빛나는가. 이 한 권은 형상의 비밀에서 시작한다. 하나님의 형상은 능력이 아니라 부르심이며, 진품과 모조품의 차이는 외관이 아니라 본질이다.",
        "흙으로 빚으신 손길이 다시 짚어진다. 능력으로 한 사람의 가치를 측정하는 시대에, 일이 사라진 자리에서 인간의 존엄은 어떻게 회복되는가. 저자는 그 회복의 결을 능력 너머의 가치에서 찾는다. 사람은 무엇을 할 수 있는가가 아니라 누구인가로 측정된다.",
        "이웃의 얼굴이 다시 떠오른다. 효율이 모든 것을 결정하는 시대에 이웃의 얼굴을 기억한다는 것은 일종의 영적 저항이다. 마지막 장은 기계 시대의 순례자다. 인간은 기계와 경쟁하는 존재가 아니라, 기계가 결코 가지지 못하는 한 결 — 부르심을 받은 순례자라는 정체성으로 살아간다.",
    ],
    9: [
        "AI 목사가 올 수 있는가. 이 한 권은 그 물음을 정면으로 다룬다. 알고리즘은 강단에 설 수 있는가, 설교는 정보의 전달인가 한 영혼의 증언인가 — 그 두 물음 안에 답의 결이 이미 담겨 있다.",
        "악보를 읽는 자와 악보를 연주하는 자는 같지 않다. AI는 설교의 형식을 흉내 낼 수 있지만, 그 안에 흐르는 한 영혼의 호흡과 성령의 임재는 흉내 낼 수 없다. 성령은 코드에 임하시지 않는다 — 이 한 마디가 이 책의 가장 단단한 자리다.",
        "약한 자를 부르시는 하나님의 결이 다시 빛난다. AI가 완벽한 설교를 흉내 낼 수 있다 해도, 하나님은 여전히 약한 한 영혼을 부르신다. 양을 아는 목자, 그 한 영혼을 알아보는 시선이 강단의 본질이다. 마지막 장은 AI 시대에 참 목자를 기다리는 자세다. 강단의 풍경은 변할 수 있어도, 강단에 서야 할 자의 본질은 변하지 않는다.",
    ],
    10: [
        "디지털 시대의 대위임령은 무엇인가. 이 한 권은 그 물음을 가장 큰 자리에서 다룬다. 로마 도로 위에서 복음이 흐르던 시대가 광케이블 위에서 복음이 흐르는 시대로 바뀌었을 뿐이라는 통찰에서 시작한다.",
        "유튜브가 디지털 강단이 되고, 소셜미디어가 일상 속 증인의 자리가 되며, 알고리즘 너머의 한 영혼이 새 선교의 대상이 된다. 저자는 그 새 풍경을 두려움이 아니라 부르심으로 받아들인다. 도구는 새로워도 사명은 변하지 않는다.",
        "온라인과 오프라인의 거룩한 균형이 짚어진다. 온라인은 확장성을 주지만 오프라인은 깊이를 준다. 둘 중 하나만이 아니라 둘 다가 필요하며, 그 균형 위에 디지털 시대의 선교가 서 있다. 마지막 장은 우리 손안의 스마트폰이 미래의 선교사가 될 수 있다는 한 마디다. 도구는 영혼을 가지지 않지만, 그 도구를 든 한 영혼은 광케이블 위에서도 사명을 살아낼 수 있다.",
    ],
}


# 권별 길잡이 — 그 한 권만의 좁고 깊은 화두 (부 길잡이와 차별)
BOOK_GUIDES = {
    1: [
        "AI가 내 신앙에 던지는 가장 본질적인 질문 한 가지는 무엇이며, 나는 그 앞에서 어떻게 응답하고 있는가.",
        "AI에 대체될 수 있는 내 일과 결코 대체될 수 없는 내 자리는 어떻게 갈라지는가.",
        "AI 시대에 본질로 돌아간다는 것은, 내 일상의 어떤 자리를 다시 차지한다는 뜻인가.",
    ],
    2: [
        "AI라는 새 렌즈로 성경을 읽을 때, 나는 풍성함을 얻고 있는가 아니면 정보처럼 다루고 있는가.",
        "문자와 영의 차이를 분별한다는 것은, 내 성경 읽기의 어떤 자리에서 가장 또렷이 드러나는가.",
        "성령의 조명 아래에서 묵상한다는 것은, AI의 빠른 답변과 어떻게 다른 자리인가.",
    ],
    3: [
        "알고리즘이 우연의 탈을 쓴 섭리를 가릴 때, 나는 그 너머의 손을 어떻게 알아보고 있는가.",
        "예측 불가능한 세계에서 신뢰한다는 것은, 내 어떤 결정과 어떤 호흡 안에서 살아나고 있는가.",
        "데이터의 세계관과 섭리의 세계관이 충돌할 때, 나는 어느 발에 무게를 싣고 서 있는가.",
    ],
    4: [
        "내 일상의 어떤 자리에서 빅데이터로 측정되지 않는 영적 실재가 가장 또렷이 흐르고 있는가.",
        "사랑·용서·은혜를 데이터처럼 다루려는 시대의 압력 앞에서, 나는 어떤 자리를 지키고 있는가.",
        "하나님의 시선으로 나를 본다는 것은, 자기 평가와 데이터 평가 너머의 어떤 자리를 가리키는가.",
    ],
    5: [
        "한계가 결함이 아니라 설계라는 한 마디 앞에서, 나는 내 약함을 어떻게 다시 보고 있는가.",
        "업그레이드의 유혹이 일상에 스며들 때, 나는 그것을 어떻게 분별하고 있는가.",
        "연약함의 복음 — 약함이 폐기물이 아니라 은혜의 자리라는 것을, 내 어디서 살아내고 있는가.",
    ],
    6: [
        "알림의 홍수 속에서 가장 조용한 메시지를 듣는 자리를, 나는 어떻게 만들고 있는가.",
        "다오다오 식으로 빠르게 처리하는 기도의 함정에서, 나는 어떻게 침묵의 자리로 옮겨 가고 있는가.",
        "도구는 변해도 변하지 않는 대화의 결을, 내 기도는 어떻게 지키고 있는가.",
    ],
    7: [
        "디지털 예배가 가능한 자리와 결코 대체되지 않는 몸의 교제의 자리를, 나는 어떻게 분별하고 있는가.",
        "사진과 실재 사이의 차이가, 내 예배에 어떤 자리에서 드러나고 있는가.",
        "공간을 초월하는 임재의 신비를, 나는 디지털 도구를 어떻게 사용하면서 만나고 있는가.",
    ],
    8: [
        "능력으로 한 사람의 가치가 측정되는 시대에, 나는 이웃의 얼굴을 어떻게 보고 있는가.",
        "일이 사라진 자리에서 인간의 존엄을 회복한다는 것은, 내 일상의 어떤 자리에서 시작되는가.",
        "기계 시대의 순례자라는 정체성이, 내 어떤 결정과 어떤 자세로 드러나고 있는가.",
    ],
    9: [
        "성령이 코드에 임하시지 않는다는 한 마디 앞에서, 나는 강단을 어떻게 다시 보고 있는가.",
        "설교가 정보가 아니라 한 영혼의 증언이라는 것을, 듣는 자리에서 나는 어떻게 살아내고 있는가.",
        "약한 자를 부르시는 하나님의 결이, AI 완벽함의 시대에 내게 어떻게 다가오는가.",
    ],
    10: [
        "내 손안의 스마트폰은 도구인가 우상인가 선교사인가 — 오늘 그것은 어느 자리에 있는가.",
        "온라인의 확장성과 오프라인의 깊이 사이의 거룩한 균형을, 나는 어떻게 살아내고 있는가.",
        "디지털 시대의 대위임령이 내 일상에 어떤 부르심으로 다가오고 있는가.",
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
  <div style="color:#888;font-size:0.88em;margin-top:0.3em">원본 ISBN {b['isbn']} · G02 제 {b['src_no']:02d} 권</div>
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
<h3 style="color:#0F1E3C;margin-top:1.5em">영혼의 자리는 변하지 않는다</h3>
<p>이로써 G02 열 권의 묵상이 한 권으로 닫힙니다. AI가 던지는 첫 번째 질문에서 시작해 디지털 선교의 미래에 이르기까지, 알고리즘 시대를 살아가는 그리스도인의 가장 정직한 묵상을 네 갈래로 모아 함께 걸어왔습니다. 처음에는 흩어져 있던 한 권 한 권의 묵상이 한 호흡으로 이어 붙고 나니, 사이를 흐르고 있던 결이 비로소 또렷해졌습니다.</p>
<p>이 책이 묻고자 했던 한 가지 물음은 분명합니다. <em>알고리즘의 한복판에서 신자는 무엇으로 떠밀리지 않을 것인가.</em> AI가 던지는 거울 앞에 서는 자세와, 알고리즘 너머의 손을 응시하는 눈과, 디지털 일상에서 영성의 결을 회복하는 자리와, 교회의 다음 풍경을 분별하는 시선 — 그 넷이 그 답의 네 갈래였습니다.</p>
<p><strong>1부에서 우리는 새 시대의 질문</strong> 앞에 함께 섰습니다. AI는 우리에게 답을 주는 도구일 뿐 아니라, 우리에게 본질을 다시 묻는 거울이기도 했습니다. 대체될 수 있는 것과 결코 대체될 수 없는 것의 경계, 그리고 새 렌즈로 오래된 말씀을 만나는 자리에서 신앙의 본질이 다시 또렷해졌습니다.</p>
<p><strong>2부에서 우리는 보이지 않는 손의 신학</strong>을 응시했습니다. 알고리즘이 우리 일상을 편집하는 시대에, 그 너머에 또 한 손이 있다는 것을 우리는 다시 보았습니다. 빅데이터로 측정되지 않는 영적 실재 — 사랑·용서·은혜의 자리, 그리고 업그레이드되지 않는 인간의 약함이 결함이 아니라 은혜의 자리라는 것을 함께 만났습니다.</p>
<p><strong>3부에서 우리는 디지털 일상의 영성</strong>을 짚어 보았습니다. 알림의 홍수 속에서도 가장 조용한 메시지를 듣는 자리, 메타버스 시대에도 결코 대체되지 않는 몸의 교제의 자리, 그리고 능력으로 사람의 가치가 측정되는 시대에도 이웃의 얼굴을 알아보는 자리 — 그 셋이 디지털 시대의 영성의 결입니다.</p>
<p><strong>4부에서 우리는 교회의 다음 풍경</strong>을 그렸습니다. AI가 강단에 설 수 있는가, 디지털 선교는 어디까지 가능한가. 두 물음 앞에서 우리는 변하지 않는 한 결과 변해야 하는 한 결을 분별했습니다. 성령은 코드에 임하시지 않고, 양을 아는 목자의 자리는 결코 대체되지 않으며, 그러나 우리 손안의 스마트폰은 미래의 선교사가 될 수 있다는 그 결을 함께 보았습니다.</p>
<p>이 책의 가장 단단한 한 마디는 표제에 이미 담겨 있습니다 — <em>알고리즘 시대의 영혼.</em> 알고리즘은 시대의 단어이지만, 영혼은 시대를 가로질러 변하지 않는 자리입니다. 도구는 변해도 영혼의 자리는 변하지 않습니다. 이 한 마디 위에 그리스도인이 디지털 시대를 살아가는 모든 결단이 놓여 있습니다.</p>
<p>이 책을 덮으신 뒤에도 묵상은 끝나지 않습니다. 한 장씩 다시 펼쳐 읽어도 좋고, 한 단락만 천천히 반복해 읽어도 좋습니다. AI라는 단어가 두려움의 단어로 다가오던 자리에서 그것을 분별의 자리로 옮겨 가셨다면, 그것만으로도 G02 열 권을 한 권으로 묶은 이유는 충분할 것입니다.</p>
<p>이제 100권 시리즈는 G03으로, G04로, 그리고 마지막 G10까지 흘러갑니다. 알고리즘 시대의 영혼이 어떻게 빚어지는가의 결은 이 한 권에 모였습니다. 다음 그룹에서 또 다른 깊은 묵상으로 다시 만나기를 기도합니다. 주님의 평강이 여러분의 오늘 위에 충만히 임하시기를 축복합니다.</p>
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
    uuid_id = f"omnibus-g02-{today_compact}-{datetime.now().strftime('%H%M%S')}"

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
    <dc:description>{proj['subtitle']} — G02 10권 종합본</dc:description>
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
    print("ISBN 발급 시 batch_books_g02_omnibus.json의 isbn 필드에 입력 후 재빌드.")


if __name__ == "__main__":
    main()
