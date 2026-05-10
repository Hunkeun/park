# -*- coding: utf-8 -*-
"""
G10 10권 종합책 "이미, 그러나 아직" epub 빌더.

입력:
  - batch_books_g10_omnibus.json (메타·4부 구조)
  - tmp/g10_omnibus_extracted.json (10권 본문 추출본)
  - G10 epub 중 한 권 (CSS 추출용)

출력:
  - ~/Downloads/전자책/이미_그러나_아직_YYYYMMDD_종합책.epub

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
META_PATH = PROJECT / "batch_books_g10_omnibus.json"
EXTRACT_PATH = PROJECT / "tmp" / "g10_omnibus_extracted.json"
SAMPLE_EPUB = Path.home() / "Downloads" / "전자책" / "하나님_나라의_비전_20260419.epub"
OUT_DIR = Path.home() / "Downloads" / "전자책"
OUT_BACKUP_DIR = PROJECT / "tmp"  # 보조 사본


def get_css():
    """샘플 epub에서 CSS 추출."""
    with zipfile.ZipFile(SAMPLE_EPUB, "r") as z:
        return z.read("OEBPS/styles/style.css").decode("utf-8")


def get_cover_image():
    """전용 종합책 표지 사용 (없으면 샘플로 폴백)."""
    custom = PROJECT / "tmp" / "g10_omnibus_cover.jpg"
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
  <p><strong>구성</strong>　G10 10권 종합책 (4부 70장)</p>
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
    <p>이 책은 100권 영성 시리즈 G10(하나님 나라) 10권의 본문을 거의 그대로 4부 구조로 재편집하여 한 권으로 묶은 종합본이며, 시즌 2 100권 종합책 시리즈의 마지막 권입니다.</p>
    <p>각 권의 원본 ISBN 및 출간 정보는 본문 권별 도입 페이지에 명기되어 있습니다.</p>
  </div>
</div></div>"""
    return xhtml_doc("판권", body)


def build_preface_xhtml() -> str:
    body = """<div style="padding:2em 1.5em;line-height:1.9;font-size:1em;color:#222">
<h2 style="color:#0F1E3C;border-bottom:1px solid #C8B99A;padding-bottom:0.5em">여는 글</h2>
<h3 style="color:#0F1E3C;margin-top:1.5em">이미 임한 나라, 아직 오지 않은 완성</h3>
<p>그리스도인이 살아가는 시간은 한 줄로 흐르지 않습니다. 우리에게는 두 시간이 함께 흐릅니다. 이미 임한 나라의 시간과, 아직 오지 않은 완성의 시간. 그 두 시간 사이의 긴장 안에 우리의 모든 일상이 놓여 있습니다. 신학자들이 이미, 그러나 아직이라 부르는 그 자리.</p>
<p>예수께서는 "하나님 나라가 너희 가운데 있다"고 말씀하시면서 동시에 "그 나라가 임하소서"라고 기도하라 가르치셨습니다. 모순처럼 보이는 그 두 마디가 사실은 한 진실의 두 측면입니다. 하나님 나라는 이미 시작되었고, 아직 완성되지 않았습니다. 그 사이에 한 영혼이 살아가는 자리, 그것이 그리스도인의 시간입니다.</p>
<p>이 책은 그 두 시간의 결을 차례로 따라 걷습니다. 하나님 나라의 비전과 복음의 능력, 일상으로 흐르는 나라(예배·경제·문화), 부르심 받은 자들의 자리(제자도·선교), 그리고 종말과 완성의 자리(재림·새 하늘과 새 땅)까지 — 하나님 나라라는 한 단어 안에 담긴 그리스도교의 가장 큰 비전을 열 갈래로 펼쳐 놓았습니다.</p>
<p>이 책은 100권 영성 시리즈의 마지막 그룹 G10을 한 권으로 묶은 종합본이며, 시즌 2 100권 종합책 시리즈의 마지막 권이기도 합니다. 시즌 1의 「AI 시대를 살아가는 영성」에서 시작된 한 흐름이 100권을 통과하여 마지막 한 권에서 모든 결을 모읍니다.</p>
<p>네 갈래는 한 영혼이 두 시간 사이를 살아가는 한 길의 네 굽이입니다. <strong>1부 — 하나님 나라의 비전</strong>은 이미 시작된 나라와 복음의 능력에서 큰 그림을 그립니다. <strong>2부 — 일상으로 흐르는 나라</strong>는 예배·경제·문화에서 그 나라가 우리 일상에 어떻게 흘러내리는가를 봅니다. <strong>3부 — 부르심 받은 자들</strong>은 제자도와 선교에서 한 영혼이 그 나라의 일꾼으로 빚어지는 자리를 짚고, <strong>4부 — 종말과 완성</strong>은 재림과 새 하늘과 새 땅에서 모든 길의 마지막 자리에 도달합니다.</p>
<p>이 책은 종말 신학 입문서가 아닙니다. 다만 우리가 살아가는 오늘 한복판에 이미 임한 나라가 있다는 것을, 그리고 그 나라가 마지막에 완성된다는 것을 묵상의 자리로 우리를 데려가려 합니다. 그 두 시간의 긴장 안에서 빚어지는 자세, 그것이 그리스도인의 가장 깊은 영성입니다.</p>
<p>한 번에 다 읽어내실 책이 아닙니다. 한 장씩, 한 묵상씩 호흡을 따라 가져가시면 됩니다. 이제 첫 장을 펼쳐 주십시오. 이미 임한 나라의 결을 누리며, 아직 오지 않은 완성을 향해 한 호흡씩 함께 걸어가 봅시다.</p>
</div>"""
    return xhtml_doc("여는 글", body)


PART_INTROS = {
    1: {
        "headline": "이미 임한 나라의 비전",
        "paragraphs": [
            "예수께서 첫 설교를 시작하실 때 던지신 첫 마디가 있습니다. 회개하라, 천국이 가까이 왔느니라. 그 한 마디 안에 하나님 나라의 모든 비전이 담겨 있습니다. 가까이 왔다는 것은 이미 시작되었다는 뜻이며, 회개하라는 것은 그 나라에 응답하라는 부르심입니다.",
            "하나님 나라는 추상이 아닙니다. 사탄의 권세 아래 놓인 것 같은 이 세상이 사실은 왕의 땅이라는 분명한 선언입니다. 우리는 그 나라의 시민으로서 왕·제사장·선지자의 부르심을 받았습니다. 자기 자리를 다스리고, 자기 일상을 거룩하게 드리며, 시대를 향한 분별을 외치는 자세 — 그 셋이 그리스도인의 정체성입니다.",
            "복음은 그 나라의 능력입니다. 부끄럽지 않은 복음이라는 바울의 한 마디가 그 결의 토대입니다. 복음은 종교적 정보가 아니라 하나님의 능력이며, 모든 믿는 자에게 구원을 주시는 능력입니다. 씨앗처럼 작아 보여도 결국 콘크리트를 뚫고 나오는 결을 가진 능력.",
            "그리고 그 능력은 한 영혼의 일상으로 흘러내립니다. 내 삶에 새겨진 복음의 증거가 결국 가장 큰 증언이 됩니다. 우리가 복음을 부끄러워한 순간들을 정직하게 응시하면서, 오늘 복음을 전할 기회를 다시 발견하는 자세가 우리에게 필요합니다.",
            "이 부의 두 권은 하나님 나라의 비전과 그 비전을 흐르게 하는 능력을 차례로 펼칩니다. 「하나님 나라의 비전」은 이미 시작된 나라의 결을, 「복음의 능력」은 그 나라를 흐르게 하는 복음의 결을 다룹니다.",
            "이미 임한 나라의 비전이 한 영혼의 시선을 어떻게 다시 빚는가를, 두 권의 결 위에서 함께 발견해 보십시오.",
        ],
        "guides": [
            "이미 시작된 나라가 내 일상의 어느 자리에서 살아나고 있는가.",
            "왕·제사장·선지자의 부르심이 내 어떤 결단으로 자라고 있는가.",
            "복음을 부끄러워한 순간을 정직하게 마주하면서, 오늘 복음을 전할 기회를 어떻게 만들고 있는가.",
            "이 부를 읽으며, 이미 임한 나라의 비전이 한 영혼의 시선을 어떻게 다시 빚는가에 주목해 보십시오.",
        ],
    },
    2: {
        "headline": "일상으로 흐르는 하나님 나라",
        "paragraphs": [
            "하나님 나라는 주일에만 임하는 나라가 아닙니다. 월요일에도, 일터에서도, 밥상에서도, 지갑을 여는 자리에서도 임하는 나라입니다. 일상으로 흐르지 않는 나라는 사실 어디에도 임한 적이 없습니다. 일상이 거룩한 자리가 되는 결, 그것이 하나님 나라의 가장 정직한 자리입니다.",
            "예배가 그 결의 첫 자리입니다. 예배의 재정의가 필요합니다. 주일 한 시간의 행위가 아니라 산 제물로 드리는 몸, 월요일의 영성, 일터에서 드리는 예배. 쉬지 않고 흐르는 강처럼 우리 일상 전체가 예배의 자리가 될 때 비로소 예배가 삶이 됩니다.",
            "경제도 그러합니다. 우리는 너무 자주 신앙과 경제를 분리해 왔습니다. 그러나 성경은 소유의 환상을 깨뜨리고 청지기의 정체성을 가르칩니다. 두려움에서 자유로 옮겨 가는 결, 나눔의 영성, 그리고 영원한 투자라는 자세. 하나님 나라의 경제학은 자본주의 비판이 아니라 우리 일상의 결을 다시 빚는 묵상입니다.",
            "그리고 문화가 있습니다. 두 도성의 이야기가 우리 시대에도 이어집니다. 거부가 아닌 창조의 자세, 소금과 빛의 영향력, 공동체가 곧 메시지가 되는 결. 반문화의 영성이 일상 속 하나님 나라를 빚어 갑니다.",
            "이 부의 세 권은 일상으로 흐르는 하나님 나라의 세 결을 차례로 펼칩니다. 「예배가 삶이 될 때」는 쉬지 않고 흐르는 예배의 결을, 「하나님 나라의 경제학」은 청지기의 정체성을, 「하나님 나라의 문화」는 일상 속 하나님 나라의 자리를 다룹니다.",
            "주일이 아닌 매일에 임하는 나라가 진짜 임한 나라라는 것을, 세 권의 결 위에서 함께 새겨 보십시오.",
        ],
        "guides": [
            "월요일의 영성이 내 일상의 어느 자리에서 살아나고 있는가.",
            "청지기의 정체성이 내 지갑과 시간과 재능 안에서 어떻게 흐르고 있는가.",
            "공동체가 곧 메시지라는 한 마디가, 내 어떤 자리에서 살아나고 있는가.",
            "이 부를 읽으며, 하나님 나라가 일상으로 흐른다는 결을 따라가 보십시오.",
        ],
    },
    3: {
        "headline": "부르심 받은 자들의 자리",
        "paragraphs": [
            "하나님 나라는 구경꾼들의 나라가 아닙니다. 부르심 받은 자들의 나라입니다. 그 나라의 시민이 된다는 것은 그 나라의 일꾼이 된다는 뜻입니다. 그리고 그 일꾼됨은 가벼운 자리가 아닙니다. 대가가 있는 자리입니다.",
            "예수께서는 제자가 되려면 대가를 계산하라고 말씀하셨습니다. 자기를 부인하고, 자기 십자가를 지고, 그분을 따르는 자리. 모든 것을 버리는 결단, 세상의 미움을 각오하는 자세, 그리고 끝까지 견디는 인내. 제자도는 영적 액세서리가 아니라 한 영혼의 모든 자리를 재배치하는 결입니다.",
            "그리고 그 제자도의 가장 큰 결이 선교입니다. 선교는 한 부르심을 받은 자가 다른 영혼을 향해 흘러가는 결입니다. 선교하시는 하나님이 그 결의 토대입니다. 우리가 선교하는 게 아니라 그분이 선교하시며, 우리는 그분의 선교에 동참할 뿐입니다.",
            "열방을 향한 심장 박동이 짚어집니다. 그러나 선교는 멀리 있는 자리가 아닙니다. 일상이 선교지이며, 내가 선 자리가 선교지입니다. 보내심을 받은 자의 영성이 결국 모든 일상에서 흘러나가야 진짜 선교입니다.",
            "이 부의 두 권은 부르심 받은 자들의 두 결을 응시합니다. 「제자도의 대가」는 자기 십자가를 지는 결단의 자리를, 「선교의 심장」은 보내심을 받은 자가 일상에서 흘러나가는 결을 다룹니다.",
            "부르심에 응답한 자가 어떻게 일꾼으로 빚어지는가를, 두 권의 결 위에서 함께 새겨 보십시오.",
        ],
        "guides": [
            "제자도의 대가를 계산해 본 적이 있다면, 내 결단의 무게는 어디까지 자라고 있는가.",
            "자기 십자가를 진다는 한 마디가, 내 일상의 어떤 결단으로 살아나고 있는가.",
            "내가 선 자리가 선교지라는 한 마디 앞에서, 나는 그 자리를 어떻게 살아내고 있는가.",
            "이 부를 읽으며, 부르심 받은 자가 어떻게 일꾼으로 빚어지는가에 주목해 보십시오.",
        ],
    },
    4: {
        "headline": "아직 오지 않은 완성을 기다리며",
        "paragraphs": [
            "이미 임한 나라의 결을 누리던 우리가 마지막에 도달하는 자리는 아직 오지 않은 완성의 자리입니다. 그 완성은 우리가 만드는 게 아니라 그분이 마지막에 가져오십니다. 종말은 끝이 아니라 시작이며, 재림은 두려움이 아니라 약속입니다.",
            "종말을 사는 자세는 두려움의 자세가 아닙니다. 끝을 아는 자의 시선이며, 마감이 있는 인생을 정직하게 살아내는 자세입니다. 깨어 있으라는 한 마디가 그 결의 토대입니다. 신실한 청지기의 자세, 재림의 소망 안에서 사는 결. 종말은 우리에게 자유를 줍니다 — 오늘을 영원처럼 살게 하는 자유.",
            "재림은 마라나타의 외침에서 가장 또렷이 살아납니다. 신부로 단장하는 교회의 자세, 도둑같이 오시는 주님 앞에서 깨어 있는 결단. 열 처녀의 등불과 달란트를 남긴 종의 비유가 그 결을 가르칩니다. 재림은 막연한 미래가 아니라 오늘의 자세를 정하는 약속입니다.",
            "그리고 마지막에 새 하늘과 새 땅이 도래합니다. 종말은 끝이 아닙니다. 요한계시록은 소망의 묵시이며, 새 예루살렘이 하나님의 장막으로 임합니다. 눈물도 사망도 없는 나라, 생명수 강과 생명나무가 흐르는 자리. 그 자리가 우리의 마지막 본향이며 시작점입니다.",
            "이 부의 세 권은 종말과 완성의 세 결을 차례로 펼칩니다. 「종말을 사는 자세」는 끝을 아는 자의 시선을, 「재림을 기다리며」는 신부로 단장하는 교회의 자세를, 「새 하늘과 새 땅」은 마지막 완성의 풍경을 다룹니다.",
            "마지막 장 — 마라나타, 주 예수여 오시옵소서. 100권 시리즈 전체의 마지막 한 마디이기도 합니다. 이미 임한 나라의 결을 누리며, 아직 오지 않은 완성을 기다리는 자세 — 그것이 그리스도인의 가장 깊은 자리입니다.",
        ],
        "guides": [
            "끝을 아는 자의 시선이, 내 오늘을 어떻게 다시 빚고 있는가.",
            "재림을 기다리는 자세가 막연한 미래가 아니라 오늘의 결단이라면, 내 일상은 어떻게 살아내고 있는가.",
            "새 하늘과 새 땅의 풍경이 내 어떤 자리에서 위로와 소망으로 닿고 있는가.",
            "이 부를 읽으며, 마라나타의 외침이 내 영혼에 어떤 결로 새겨지는가에 주목해 보십시오.",
        ],
    },
}


# 권별 요약 (각 책 진입부 — 3단락, 약 70% 분량)
# 마지막 단락의 핵심 한 문장은 3번째 단락 끝에 흡수
BOOK_SUMMARIES = {
    1: [
        "이미 시작된 나라가 첫 장의 자리다. 예수께서 첫 설교에서 선언하신 천국이 가까이 왔다는 한 마디가 책 전체의 결을 정한다. 하나님 나라는 미래의 약속이 아니라 이미 시작된 실재다.",
        "아직 완성되지 않은 나라가 그 다음 결이다. 이미와 아직의 긴장 안에 한 영혼이 살아간다. 사탄의 세상처럼 보이는 이 땅이 사실은 왕의 땅이라는 선언, 그 선언 위에서 우리는 왕·제사장·선지자로 살아갈 부르심을 받는다.",
        "나라의 가치로 결정하기와 내가 선 자리가 선교지라는 결이 짚어진다. 마지막 장 — 완성을 향한 소망. 이미와 아직 사이에 살아가는 자가 마지막에 도달하는 자리는 결국 완성을 향한 소망이다. 그 소망이 우리 오늘의 자세를 정한다.",
    ],
    2: [
        "부끄럽지 않은 복음이 첫 장의 자리다. 바울의 이 한 마디가 책 전체의 토대다. 복음을 부끄러워한 자리에서 한 영혼의 영성이 흔들리고, 부끄러워하지 않는 자리에서 비로소 단단해진다.",
        "하나님의 능력이 된 복음이 짚어진다. 복음은 종교적 정보가 아니라 능력이다. 모든 믿는 자에게 구원을 주시는 능력이며, 씨앗처럼 콘크리트를 뚫고 나오는 결을 가진 능력이다. 그 능력이 한 영혼을 다시 빚는다.",
        "내 삶에 새겨진 복음의 증거가 짚어진다. 우리가 복음을 부끄러워한 순간들을 정직하게 응시하면서, 그 안에서도 복음이 새긴 결을 발견한다. 마지막 장 — 오늘, 복음을 전할 기회. 복음은 과거의 사건이 아니라 오늘의 기회다. 한 영혼이 다른 영혼에게 흘러가는 자리, 그것이 복음의 가장 정직한 자리다.",
    ],
    3: [
        "예배의 재정의가 첫 장의 자리다. 우리는 예배를 주일 한 시간의 행위로 좁혀 왔다. 그러나 성경의 예배는 산 제물로 드리는 몸이며, 일상 전체가 예배의 자리가 된다는 결을 가르친다.",
        "월요일의 영성이 짚어진다. 일터에서 드리는 예배, 관계 속의 예배자. 주일과 일상이 분리되지 않을 때 비로소 예배가 삶이 된다. 예배를 막는 장애물 — 분주함·자기 의·세속화 — 이 무엇인가도 정직하게 응시된다.",
        "쉬지 않고 흐르는 강이 마지막 장의 결이다. 예배는 멈추지 않는 강이다. 한 영혼의 일상 전체가 그 강의 흐름이 될 때, 예배가 삶이 되는 결이 완성된다. 데살로니가전서의 쉬지 말고 기도하라는 한 마디가 결국 예배의 결로 흐른다.",
    ],
    4: [
        "소유의 환상이 첫 장의 자리다. 우리는 자주 우리가 소유한다고 착각한다. 그러나 성경은 우리가 청지기일 뿐임을 분명히 한다. 청지기의 정체성이 그 결의 토대다.",
        "하나님 나라의 경제 원리가 짚어진다. 두려움에서 자유로 옮겨 가는 결, 나눔의 영성, 소비와 절제의 분별. 자본주의 비판이 아니라 우리 일상의 결을 다시 빚는 묵상이 거기 있다.",
        "마지막 장 — 영원한 투자. 우리가 어디에 투자하느냐가 우리 마음이 어디에 있는가를 정한다. 영원한 자리에 투자하는 자세가 결국 청지기의 가장 깊은 결이다. 하나님 나라의 경제학은 결국 마음의 자리를 묻는 묵상이다.",
    ],
    5: [
        "두 도성의 이야기가 첫 장의 자리다. 아우구스티누스의 두 도성 신학이 우리 시대에도 이어진다. 우리는 두 도성 사이에 살아가는 자들이며, 그 어색함이 사실은 가장 정직한 자리다.",
        "거부가 아닌 창조가 짚어진다. 문화를 거부하는 자세도, 문화에 동화되는 자세도 모두 한쪽으로 미끄러진 자리다. 그리스도인은 문화 안에서 다른 문화를 창조하는 자리에 부르심을 받았다. 소금과 빛의 영향력, 공동체가 곧 메시지가 되는 결.",
        "반문화의 영성과 일상 속 하나님 나라가 짚어진다. 마지막 장 — 종말을 향한 순례 공동체. 우리는 정착민이 아니라 순례자이며, 우리 공동체의 자리는 종말을 향한 길 위에 있다. 그 자세가 하나님 나라의 문화의 가장 깊은 결이다.",
    ],
    6: [
        "대가를 계산하라가 첫 장의 자리다. 예수께서는 자기를 따르려는 자에게 대가를 계산하라고 분명히 말씀하셨다. 제자도는 영적 액세서리가 아니라 모든 자리를 재배치하는 결단이다.",
        "자기를 부인하라, 자기 십자가를 지라, 나를 따르라가 차례로 짚어진다. 이 셋이 제자도의 핵심이다. 자기 부인은 자기 혐오가 아니라 자기 중심의 자리에서 그분 중심의 자리로 옮겨 가는 결이다.",
        "모든 것을 버리라, 세상의 미움을 각오하라가 그 다음 결이다. 가벼운 자리가 아니다. 마지막 장 — 끝까지 견디라. 제자도의 가장 큰 시험은 시작이 아니라 끝까지 견디는 자세다. 시작이 화려한 자는 많지만 끝까지 가는 자는 적다는 결이 책의 마지막 자리다.",
    ],
    7: [
        "선교하시는 하나님이 첫 장의 자리다. 선교의 주체는 우리가 아니다. 그분이 선교하시고, 우리는 그분의 선교에 동참할 뿐이다. 그 사실이 선교의 모든 자세를 정한다.",
        "열방을 향한 심장 박동이 짚어진다. 하나님의 마음은 한 민족에 갇히지 않는다. 모든 민족을 향한 심장이 성경 전체에 흐른다. 대위임령의 재발견이 그 결의 핵심이다. 마태복음 28장이 결코 끝난 명령이 아니라 오늘도 살아 있는 부르심이다.",
        "보내심을 받은 자의 영성과 일상이 선교지라는 결이 짚어진다. 마지막 장 — 심장이 뛰는 공동체. 선교는 한 영혼의 일이 아니라 한 공동체의 일이다. 심장이 함께 뛰는 공동체에서만 진짜 선교가 흘러나간다.",
    ],
    8: [
        "끝을 아는 자의 시선이 첫 장의 자리다. 종말을 안다는 것은 두려움의 자세가 아니라 정직한 시선이다. 마감이 있는 인생을 정직하게 살아내는 자리에서 모든 결단의 무게가 다시 측량된다.",
        "깨어 있으라가 짚어진다. 종말을 사는 자의 자세는 떠는 자의 자세가 아니라 깨어 있는 자의 자세다. 신실한 청지기의 결, 재림의 소망이 그 다음 결이다.",
        "종말이 주는 자유가 마지막 장 직전의 결이다. 종말이 두려움이 아니라 자유를 주는 이유는, 모든 것이 결국 그분 안에서 완성된다는 약속 때문이다. 마지막 장 — 오늘을 영원처럼. 종말을 본 자의 가장 정직한 자세는 오늘을 영원처럼 사는 것이다.",
    ],
    9: [
        "마라나타, 주여 오시옵소서가 첫 장의 자리다. 초대교회 그리스도인의 인사말이었던 그 한 마디가 책 전체의 결을 정한다. 재림은 막연한 미래가 아니라 한 영혼의 가장 정직한 갈망이다.",
        "신부로 단장하는 교회가 짚어진다. 교회의 정체성은 신부다. 신랑이 오시는 날을 향해 자기를 단장하는 자세. 도둑같이 오시는 주님 앞에서 깨어 있는 결단이 그 다음 결이다.",
        "열 처녀의 등불과 달란트를 남긴 종이 짚어진다. 두 비유 모두 깨어 있음의 결을 가르친다. 마지막 장 — 아멘 주 예수여 오시옵소서. 요한계시록의 마지막 한 마디가 책의 마지막 한 마디로 흐른다. 재림을 기다린다는 것은 결국 그 한 마디를 매일 새롭게 외치는 자세다.",
    ],
    10: [
        "종말은 끝이 아니다가 첫 장의 자리다. 우리는 자주 종말을 무서운 마감으로만 다룬다. 그러나 성경의 종말은 끝이 아니라 시작이다. 요한계시록은 공포의 책이 아니라 소망의 묵시다.",
        "새 하늘과 새 땅의 도래가 짚어진다. 새 예루살렘이 하나님의 장막으로 임하는 광경. 눈물도 사망도 없는 나라가 그 자리의 풍경이다. 우리의 모든 눈물이 닦이고, 모든 슬픔이 끝나는 자리.",
        "생명수 강과 생명나무가 흐르는 자리가 짚어진다. 창세기 에덴이 다시 회복되는 결이다. 마지막 장 — 마라나타, 주 예수여 오시옵소서. 책의 마지막 한 마디이자, 100권 시리즈 전체의 마지막 한 마디다. 시즌 1 「AI 시대를 살아가는 영성」에서 시작된 한 흐름이 이 한 마디에서 모든 결을 모은다. 이미 임한 나라를 누리며, 아직 오지 않은 완성을 기다리는 자의 가장 정직한 외침이 거기 있다.",
    ],
}


# 권별 길잡이 — 그 한 권만의 좁고 깊은 화두 (부 길잡이와 차별)
BOOK_GUIDES = {
    1: [
        "이미 시작된 나라와 아직 완성되지 않은 나라 사이에서, 나는 어느 시간을 더 또렷이 살아내고 있는가.",
        "왕·제사장·선지자의 부르심이, 내 일상의 어떤 자리에서 살아나고 있는가.",
        "내가 선 자리가 선교지라는 한 마디가, 내 어떤 결단으로 자라고 있는가.",
    ],
    2: [
        "부끄럽지 않은 복음이라는 바울의 한 마디 앞에서, 내가 부끄러워한 순간은 어디인가.",
        "복음이 종교적 정보가 아니라 하나님의 능력이라는 것을, 내 삶은 어떻게 증언하고 있는가.",
        "오늘 복음을 전할 기회가 내 어떤 자리에 놓여 있는가.",
    ],
    3: [
        "월요일의 영성이, 내 일상의 어떤 자리에서 살아나고 있는가.",
        "예배가 주일 한 시간이 아니라 쉬지 않고 흐르는 강이라면, 내 어떤 자리에서 그 강이 멈춰 있는가.",
        "산 제물로 드리는 몸이라는 한 마디가, 내 일상의 어떤 결단으로 살아나고 있는가.",
    ],
    4: [
        "내가 청지기일 뿐이라는 한 마디 앞에서, 내 소유 의식은 어떻게 다시 빚어지고 있는가.",
        "두려움에서 자유로 옮겨 가는 경제관이, 내 어떤 결단에서 자라고 있는가.",
        "영원한 투자라는 한 마디가, 내 마음의 자리를 어디로 옮기고 있는가.",
    ],
    5: [
        "두 도성의 시민으로서, 나는 어느 한쪽으로 미끄러지지 않고 어떻게 살아내고 있는가.",
        "거부가 아닌 창조의 자세가, 내 어떤 자리에서 살아나고 있는가.",
        "공동체가 곧 메시지라는 한 마디가, 내 공동체의 어떤 자리에서 흐르고 있는가.",
    ],
    6: [
        "제자도의 대가를 계산해 본 적이 있다면, 내 결단의 무게는 어디까지 자라고 있는가.",
        "자기를 부인하고 자기 십자가를 진다는 결단이, 내 어떤 일상에서 살아나고 있는가.",
        "끝까지 견디는 자세가, 내 어떤 자리에서 빚어지고 있는가.",
    ],
    7: [
        "선교의 주체가 우리가 아니라 그분이라는 한 마디가, 내 자세를 어떻게 다시 빚고 있는가.",
        "열방을 향한 심장 박동이, 내 안에서 어떤 결로 자라고 있는가.",
        "내가 선 자리가 선교지라는 약속을, 나는 어떤 일상에서 살아내고 있는가.",
    ],
    8: [
        "끝을 아는 자의 시선이, 내 오늘을 어떻게 다시 빚고 있는가.",
        "마감이 있는 인생을 정직하게 살아내는 자세가, 내 어떤 결단으로 자라고 있는가.",
        "오늘을 영원처럼 산다는 한 마디를, 나는 어떻게 살아내고 있는가.",
    ],
    9: [
        "마라나타, 주여 오시옵소서의 외침이, 내 어떤 자리에서 살아나고 있는가.",
        "신부로 단장하는 교회의 자세가, 내 공동체의 어떤 결로 흐르고 있는가.",
        "도둑같이 오시는 주님 앞에서 깨어 있는 결단이, 내 어떤 일상으로 빚어지고 있는가.",
    ],
    10: [
        "종말이 끝이 아니라 시작이라는 한 마디 앞에서, 내 종말 인식은 어떻게 다시 빚어지고 있는가.",
        "새 하늘과 새 땅의 풍경 — 눈물도 사망도 없는 나라가, 내 어떤 자리에 위로와 소망으로 닿고 있는가.",
        "마라나타라는 100권 시리즈의 마지막 한 마디를, 내 영혼은 어떤 결로 받아들이고 있는가.",
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
  <div style="color:#888;font-size:0.88em;margin-top:0.3em">원본 ISBN {b['isbn']} · G10 제 {b['src_no']:02d} 권</div>
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
<h3 style="color:#0F1E3C;margin-top:1.5em">시즌 2의 마지막 한 호흡</h3>
<p>이로써 G10 열 권의 묵상이 한 권으로 닫힙니다. 그리고 이 한 권으로 100권 영성 시리즈 시즌 2의 종합책 열 권이 모두 닫힙니다. 시즌 1 「AI 시대를 살아가는 영성」에서 시작되어, G01 「영원의 문턱에서」를 거쳐, 마지막 「이미, 그러나 아직」까지 — 한 흐름이 마침내 마지막 한 호흡으로 모입니다.</p>
<p>이 책이 묻고자 했던 한 가지 물음은 분명합니다. <em>이미 임한 나라를 누리며, 아직 오지 않은 완성을 기다리는 자의 자세는 무엇인가.</em> 하나님 나라의 비전과 복음의 능력에서 시작해, 일상으로 흐르는 나라를 거쳐, 부르심 받은 자들의 자리에 서고, 마침내 종말과 완성에 도달하는 결 — 그 넷이 그 답의 네 갈래였습니다.</p>
<p><strong>1부에서 우리는 하나님 나라의 비전</strong>을 응시했습니다. 이미 시작된 나라와 아직 완성되지 않은 나라 사이의 긴장, 그리고 그 나라를 흐르게 하는 부끄럽지 않은 복음의 능력. 이미와 아직 사이에 한 영혼이 살아간다는 결을 함께 새겼습니다.</p>
<p><strong>2부에서 우리는 일상으로 흐르는 나라</strong>를 따라 걸었습니다. 예배가 주일 한 시간이 아니라 쉬지 않고 흐르는 강이 되는 자리, 청지기의 정체성으로 빚어지는 경제관, 거부가 아닌 창조의 자세로 살아내는 문화. 하나님 나라가 일상의 결 안에 흘러내릴 때 비로소 진짜 임한 나라라는 것을 함께 보았습니다.</p>
<p><strong>3부에서 우리는 부르심 받은 자들의 자리</strong>에 섰습니다. 자기 십자가를 지는 제자도의 대가, 그리고 보내심을 받은 자가 일상에서 흘러나가는 선교의 심장. 부르심에 응답한 자가 어떻게 그 나라의 일꾼으로 빚어지는가를 함께 새겼습니다.</p>
<p><strong>4부에서 우리는 종말과 완성</strong>에 도달했습니다. 끝을 아는 자의 시선, 마라나타의 외침, 그리고 새 하늘과 새 땅의 도래. 종말이 끝이 아니라 시작이라는 결, 재림이 두려움이 아니라 약속이라는 결, 그리고 새 하늘과 새 땅이 우리의 마지막 본향이라는 결을 함께 보았습니다.</p>
<p>이 책의 가장 단단한 한 마디는 표제에 이미 담겨 있습니다 — <em>이미, 그러나 아직.</em> 그리스도인의 모든 시간이 그 두 마디 사이에 놓여 있습니다. 이미 임한 나라의 결을 누리되 아직 완성되지 않은 자리를 잊지 않는 자세, 아직 오지 않은 완성을 기다리되 이미 임한 나라를 살아내는 자세. 그 긴장이 우리의 영성을 가장 정직하게 빚습니다.</p>
<p>그리고 이 책으로 100권 시리즈가 닫힙니다. 시즌 1과 시즌 2를 한 호흡으로 잇던 흐름이 마라나타의 한 마디에서 모입니다. 시즌 1의 첫 권에서 시즌 2의 마지막 권까지, 한 영혼이 자기 시대를 살아가며 영원을 응시하는 결의 모든 결이 이 한 권에 함께 흐릅니다.</p>
<p>이 책을 덮으신 뒤에도 묵상은 끝나지 않습니다. 한 장씩 다시 펼쳐 읽어도 좋고, 한 단락만 천천히 반복해 읽어도 좋습니다. 시즌 2 종합책 열 권 전체를 한 호흡으로 다시 펼쳐 읽으셔도 좋습니다. 100권의 길이 한 영혼의 한 결로 모이는 자리, 그것이 이 시리즈의 가장 깊은 보람입니다.</p>
<p><em>마라나타, 주 예수여 오시옵소서.</em> 100권 시리즈의 마지막 한 마디가 시즌 1의 첫 마디와 만나는 자리에서, 모든 결이 한 호흡으로 모입니다. 끝까지 함께 걸어 주신 독자께 깊이 감사드립니다. 주님의 평강이 여러분의 오늘 위에 충만히 임하시기를, 그리고 이미 임한 나라의 결과 아직 오지 않은 완성의 약속이 한 영혼의 일상 안에서 매일 새롭게 살아나기를 축복합니다.</p>
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
    uuid_id = f"omnibus-g10-{today_compact}-{datetime.now().strftime('%H%M%S')}"

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
    <dc:description>{proj['subtitle']} — G10 10권 종합본</dc:description>
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
    print("ISBN 발급 시 batch_books_g10_omnibus.json의 isbn 필드에 입력 후 재빌드.")


if __name__ == "__main__":
    main()
