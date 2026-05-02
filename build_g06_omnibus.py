# -*- coding: utf-8 -*-
"""
G06 10권 종합책 "광야의 외침" epub 빌더.

입력:
  - batch_books_g06_omnibus.json (메타·4부 구조)
  - tmp/g06_omnibus_extracted.json (10권 본문 추출본)
  - G06 epub 중 한 권 (CSS 추출용)

출력:
  - ~/Downloads/전자책/광야의_외침_YYYYMMDD_종합책.epub

구조 (spine 순서):
  cover → copyright → toc → preface
  → part01_intro → [b01_front·b01_ch01~07] × 2권 (1부)
  → part02_intro → [b03_front·b03_ch01~07] × 3권 (2부)
  → part03_intro → [b06_front·b06_ch01~07] × 3권 (3부)
  → part04_intro → [b09_front·b09_ch01~07] × 2권 (4부)
  → epilogue → publisher
"""
import io
import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from qr_util import make_qr_png_bytes, catalog_url

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PROJECT = Path(__file__).parent
META_PATH = PROJECT / "batch_books_g06_omnibus.json"
EXTRACT_PATH = PROJECT / "tmp" / "g06_omnibus_extracted.json"
SAMPLE_EPUB = Path.home() / "Downloads" / "전자책" / "진실이_불편한_시대_20260419.epub"
OUT_DIR = Path.home() / "Downloads" / "전자책"
OUT_BACKUP_DIR = PROJECT / "tmp"  # 보조 사본


def get_css():
    """샘플 epub에서 CSS 추출."""
    with zipfile.ZipFile(SAMPLE_EPUB, "r") as z:
        return z.read("OEBPS/styles/style.css").decode("utf-8")


def get_cover_image():
    """전용 종합책 표지 사용 (없으면 샘플로 폴백)."""
    custom = PROJECT / "tmp" / "g06_omnibus_cover.jpg"
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


def build_cover_xhtml(title: str, subtitle: str) -> str:
    body = """
<style>
  html, body { margin:0; padding:0; width:100%; height:100%; background:#FFFFFF; }
  .cover-wrap { width:100%; height:100%; display:flex; align-items:center; justify-content:center; }
  .cover-wrap svg { display:block; width:60%; height:60%; }
</style>
<div class="cover-wrap">
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     version="1.1"
     viewBox="0 0 1400 2100"
     preserveAspectRatio="xMidYMid meet">
  <image width="1400" height="2100" xlink:href="images/cover.jpg"/>
</svg>
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
  <p><strong>구성</strong>　G06 10권 종합책 (4부 70장)</p>
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
    <p>이 책은 100권 영성 시리즈 G06(시대 분별) 10권의 본문을 거의 그대로 4부 구조로 재편집하여 한 권으로 묶은 종합본입니다.</p>
    <p>각 권의 원본 ISBN 및 출간 정보는 본문 권별 도입 페이지에 명기되어 있습니다.</p>
  </div>
</div></div>"""
    return xhtml_doc("판권", body)


def build_preface_xhtml() -> str:
    body = """<div style="padding:2em 1.5em;line-height:1.9;font-size:1em;color:#222">
<h2 style="color:#0F1E3C;border-bottom:1px solid #C8B99A;padding-bottom:0.5em">여는 글</h2>
<h3 style="color:#0F1E3C;margin-top:1.5em">광야에서 외치는 자의 자리</h3>
<p>광야에서 외치는 자의 소리가 있습니다. 세례 요한이 그러했고, 이사야가 그러했으며, 예레미야가 그러했습니다. 시대의 광장이 시끄러울 때, 군중의 함성이 진실을 덮을 때, 거짓 평화가 안전한 옷처럼 퍼질 때, 광야에서 한 사람의 목소리가 울려 퍼집니다. 그 한 사람이 외친 자리에서 시대의 결이 다시 또렷해집니다.</p>
<p>이 책은 그 광야의 외침을 차례로 따라 걷습니다. 진실을 분별하는 시선과, 정의를 묻는 자리와, 영적 용기로 광야에 서는 자세와, 거짓 평화 너머의 진짜 평화를 응시하는 결까지 — 시대를 향한 그리스도인의 양심을 열 갈래로 펼쳐 놓았습니다.</p>
<p>이 책은 100권 영성 시리즈의 여섯 번째 그룹 G06를 한 권으로 묶은 종합본입니다. 진실이 불편한 시대에서 거짓 평화에 속지 마라까지, 시대 분별이라는 한 단어 안에 담긴 그리스도교의 가장 정직한 묵상을 네 갈래로 모았습니다. 열 권 각각의 본문을 거의 그대로 유지하면서, 그 사이를 흐르고 있던 결을 한 호흡으로 이어 붙였습니다.</p>
<p>네 갈래는 광야에서 시작해 광장으로 흘러가는 한 영혼의 결입니다. <strong>1부 — 진실을 분별하다</strong>는 포스트 트루스 시대의 안개와 미디어와 포퓰리즘 한복판에서 진실을 분별하는 시선에서 시작하고, <strong>2부 — 정의의 자리</strong>는 두 도성의 시민으로서 성경적 정의와 시민의 책임을 응시합니다. <strong>3부 — 광야의 목소리</strong>는 영적 용기·소수의 목소리·예언자적 상상력으로 광야에서 외치는 자들의 자리를 짚고, <strong>4부 — 거짓 평화 너머</strong>는 편안함이라는 우상에 속지 않고 진짜 평화를 분별하는 마지막 자리에 도달합니다.</p>
<p>이 책은 정치적 선언이 아닙니다. 다만 그리스도인의 양심이 시대 한복판에서 어떻게 흔들리지 않을 것인가를 묻는 묵상의 자리입니다. 다수의 함성을 따라가지 않으면서, 동시에 자기 의에 갇히지 않는 자세. 그 분별의 결이 광야에서 외치는 자의 가장 깊은 자리입니다.</p>
<p>한 번에 다 읽어내실 책이 아닙니다. 한 장씩, 한 묵상씩 호흡을 따라 가져가시면 됩니다. 이제 첫 장을 펼쳐 주십시오. 광장의 한복판에서, 그러나 광야의 시선으로, 한 호흡씩 함께 걸어가 봅시다.</p>
</div>"""
    return xhtml_doc("여는 글", body)


PART_INTROS = {
    1: {
        "headline": "진실을 분별하는 시선",
        "paragraphs": [
            "포스트 트루스 시대라는 말이 있습니다. 사실보다 감정이 먼저 움직이고, 진실보다 인상이 먼저 결정되는 시대. 정보는 넘치지만 진실은 더 멀리 있고, 모두가 자기 진실을 외치지만 공통의 진실은 흐려지는 자리. 그 안개 한복판에 한 그리스도인이 섭니다.",
            "성경은 분별을 성령의 은사로 봅니다. 분별은 똑똑함이 아니라 깨어 있음입니다. 가짜뉴스의 시대에 진짜 뉴스를 알아보는 일, 광야의 시험 한복판에서 떡이 떡인지 돌인지 알아보는 일 — 그것이 분별의 가장 정직한 자리입니다. 비판적 사고와 믿음이 충돌하지 않는 자리에서 진짜 분별이 자랍니다.",
            "포퓰리즘은 달콤한 강물처럼 흐릅니다. 다수의 함성이 진실의 자리에 올라서고, 인기가 정의의 자리에 올라서며, 군중의 박수가 분별의 자리에 올라서는 시대. 그 한복판에서 한 영혼이 좁은 길을 택한다는 것은 결코 자연스러운 일이 아닙니다.",
            "그래서 거울 앞에 서야 합니다. 시대를 비추는 거울이면서 동시에 자기를 비추는 거울 앞에. 우리가 시대를 비판하는 시선이 결국 자기 안의 같은 결을 비추기도 하기 때문입니다. 분별은 외부를 향하면서 동시에 내면을 향합니다.",
            "이 부의 세 권은 진실을 분별하는 세 결을 차례로 펼칩니다. 「진실이 불편한 시대」는 포스트 트루스 시대의 안개 한복판에서 진실을 마주하는 자세를, 「미디어와 영적 분별」은 정보 홍수 시대의 영혼이 어떻게 분별의 은사를 길러 가는가를, 「포퓰리즘의 유혹」은 달콤한 강물의 유혹과 좁은 길의 결단을 다룹니다.",
            "진실은 자주 불편합니다. 그러나 불편한 진실을 마주하는 자리에서만 한 영혼이 시대 한복판에서 흔들리지 않을 수 있습니다.",
        ],
        "guides": [
            "오늘 내가 마주하기 불편한 진실은 무엇이며, 그 진실을 어떻게 정직하게 응시하고 있는가.",
            "정보 홍수 속에서 분별의 은사를 길러 가는 자리를, 나는 어떻게 만들고 있는가.",
            "다수의 함성이 진리의 자리에 올라설 때, 나는 좁은 길을 어떻게 택하고 있는가.",
            "이 부를 읽으며, 시대를 분별하는 시선과 자기를 분별하는 시선이 어떻게 한 결로 만나는가에 주목해 보십시오.",
        ],
    },
    2: {
        "headline": "두 기준 사이에서",
        "paragraphs": [
            "그리스도인은 두 도성의 시민입니다. 한쪽은 우리가 발 딛고 있는 이 세상이고, 다른 한쪽은 우리가 향해 가는 하나님 나라입니다. 두 도성 사이에 어색하게 선 자, 그것이 그리스도인의 정체성이며, 그 어색함이 사실은 그의 가장 정직한 자리입니다.",
            "두 기준이 충돌하는 자리에 서면, 어느 한쪽으로 미끄러지기 쉽습니다. 세상의 기준에 길들여져 하나님의 기준을 잊거나, 하나님의 기준만 외치며 세상의 자리를 떠나거나. 그러나 성경은 그 둘 다를 거부합니다. 세상의 소금이 되라는 한 마디와 세상의 빛이 되라는 한 마디가 우리를 두 자리 사이에 묶어 둡니다.",
            "정의는 추상이 아닙니다. 미가서 6장 8절의 삼중 명령이 그 결을 또렷이 합니다. 정의를 행하며, 인자를 사랑하며, 겸손하게 너의 하나님과 함께 행하는 것. 자비 없는 정의는 폭력이 되고, 정의 없는 자비는 위선이 됩니다. 그 둘이 십자가에서 만난 자리, 그것이 성경적 정의의 핵심입니다.",
            "공동선을 추구한다는 것은 자기 진영의 승리만을 추구하지 않는다는 뜻입니다. 가난한 자와 나그네의 편에 서시는 하나님의 결이 우리에게도 흘러야 합니다. 정치와 신앙 사이에서 우리는 자주 흔들리지만, 내가 선 자리에서 작은 결단으로 시작하는 일이 결국 가장 큰 영향을 만듭니다.",
            "이 부의 세 권은 두 기준 사이의 세 결을 차례로 펼칩니다. 「크리스천 시민의 책임」은 두 도성의 시민으로서의 자세를, 「정의란 무엇인가 - 성경적 답」은 십자가에서 만나는 공의와 자비의 결을, 「세상의 기준 vs 하나님의 기준」은 두 왕국의 충돌 한복판의 분별을 다룹니다.",
            "두 기준 사이에서 흔들림은 자연스럽습니다. 그러나 그 흔들림 안에서도 한 결을 잡고 살아가는 자세, 그것이 광야에서 외치는 자의 가장 깊은 자리입니다.",
        ],
        "guides": [
            "두 도성의 시민으로서, 나는 어느 한쪽으로 미끄러지지 않고 어떻게 두 자리 사이에 서 있는가.",
            "정의를 행하며 인자를 사랑하며 겸손히 하나님과 함께 행한다는 미가의 삼중 명령이, 내 일상의 어떤 결로 살아나고 있는가.",
            "공동선을 추구하는 자세가, 내 어떤 결정과 어떤 호흡 안에서 살아나고 있는가.",
            "이 부를 읽으며, 두 기준이 충돌하는 자리에서 한 영혼이 어떻게 흔들리지 않을 수 있는가에 주목해 보십시오.",
        ],
    },
    3: {
        "headline": "광야에서 외치는 자들",
        "paragraphs": [
            "광야에서 외치는 자의 소리는 늘 한 사람의 외침에서 시작됩니다. 다수의 합창이 아닙니다. 한 사람이 자기 양심으로 시대를 향해 던지는 한 마디. 그 한 마디가 결국 시대의 결을 다시 빚는 자리에서, 우리는 광야의 외침의 본질을 발견합니다.",
            "두려움의 시대에 담대함의 원천은 어디서 옵니까. 자기 능력에서가 아니라 사랑받고 있다는 정체성에서 옵니다. 복음을 부끄러워하지 않는 삶은 자기 의로운 자세가 아니라 자기를 잊은 자세입니다. 핍박 속에서 피어나는 믿음, 대가를 치르는 제자도가 그 결의 핵심입니다.",
            "다수가 틀릴 때 한 사람이 일어섭니다. 엘리야의 고독은 외로움이 아니라 정직한 자리였습니다. 그러나 그 자리에 그만 혼자 있던 게 아니었습니다. 숨겨진 7000명, 남은 자의 계보가 시대마다 함께 있어 왔습니다. 침묵할 것인가 말할 것인가의 갈림길에서 한 영혼이 결단할 때, 작은 누룩이 시대를 바꿉니다.",
            "예언자적 상상력은 분노의 외침이 아닙니다. 제국의 의식에 길들여지지 않고 다른 세계를 상상하는 능력입니다. 애통의 영성과 거룩한 불만족이 그 토대이며, 대안 공동체의 삶이 그 열매입니다. 예언자의 마지막 자리는 비판이 아니라 소망의 선포입니다.",
            "이 부의 세 권은 광야에서 외치는 자들의 세 결을 차례로 펼칩니다. 「영적 용기가 필요한 시대」는 두려움의 시대에 담대히 서는 자세를, 「소수의 목소리」는 다수가 틀릴 때 한 사람이 일어서는 결단을, 「예언자적 상상력」은 비판을 넘어 소망을 선포하는 자리를 다룹니다.",
            "광야에서 외치는 자가 광장의 한 사람이 되는 결을, 세 권의 발자국 위에서 함께 새겨 보십시오.",
        ],
        "guides": [
            "오늘 내게 두려움이 닥치는 자리는 어디이며, 그 두려움 너머의 담대함을 나는 어디서 길어 올리고 있는가.",
            "다수가 틀릴 때 한 사람이 일어선다는 결단을, 내 일상의 어떤 자리에서 살아내고 있는가.",
            "예언자적 상상력 — 비판을 넘어 다른 세계를 상상하는 자세가, 내 어떤 호흡으로 자라고 있는가.",
            "이 부를 읽으며, 광야에서 외치는 자가 광장의 한 사람이 되는 결을 따라가 보십시오.",
        ],
    },
    4: {
        "headline": "거짓 평화 너머의 진짜 평화",
        "paragraphs": [
            "거짓 평화가 있습니다. 화산 위에 지은 집처럼 흔들림 없어 보이지만 사실은 가장 위태로운 자리. 편안함이라는 우상이 우리를 잠재우는 자리. 거짓 선지자가 평강하다 평강하다 외치는 그 자리, 성경은 그 자리를 가장 무겁게 경고합니다.",
            "샬롬의 본질은 단순히 갈등이 없는 상태가 아닙니다. 샬롬은 모든 것이 제자리에 있는 자리, 정의와 자비와 진실이 함께 흐르는 자리입니다. 갈등이 없어도 정의가 부재하면 그것은 샬롬이 아닙니다. 갈등이 있어도 정의를 향해 흐르고 있다면 그것이 진짜 평화의 결입니다.",
            "광야의 외침이 마지막에 도달하는 자리가 바로 이 거짓 평화의 분별입니다. 시대를 분별하는 시선과 두 기준 사이의 결단과 광야에서 외치는 자세가 모두 결국 한 자리로 모입니다. 거짓 평화에 속지 않고 진짜 평화를 향해 걸어가는 자리.",
            "그리고 그 진짜 평화는 십자가 위에 있습니다. 갈등을 회피하지 않으시고 정면으로 통과하신 분 안에 평화가 있습니다. 평강을 분별하는 영성은 결국 십자가 위에서 만나는 평화의 결을 자기 일상에 새기는 자세입니다.",
            "이 부의 한 권 「거짓 평화에 속지 마라」는 그 결을 정면으로 응시합니다. 거짓 평화의 정체와 편안함이라는 우상의 결을 정직하게 짚으면서, 진짜 안전으로의 초대가 어디서 시작되는가를 다룹니다.",
            "광야의 외침이 결국 진짜 평화로 이어진다는 것을, 마지막 한 권 위에서 함께 새겨 보십시오.",
        ],
        "guides": [
            "내가 진짜 평화로 알고 있던 자리가, 사실은 거짓 평화는 아니었는가.",
            "샬롬이 갈등의 부재가 아니라 정의와 자비의 흐름이라면, 내 일상의 어떤 자리에서 그 결이 살아나고 있는가.",
            "편안함이라는 우상을 분별하는 자세를, 내 어떤 결단에서 살아내고 있는가.",
            "이 부를 읽으며, 거짓 평화 너머에서 시작되는 진짜 평화를 함께 응시해 보십시오.",
        ],
    },
}


# 권별 요약 (각 책 진입부 — 3단락, 약 70% 분량)
# 마지막 단락의 핵심 한 문장은 3번째 단락 끝에 흡수
BOOK_SUMMARIES = {
    1: [
        "거울 앞에 서다는 한 마디로 첫 권은 시작한다. 시대를 비추는 거울이면서 동시에 자기를 비추는 거울. 포스트 트루스 시대의 안개 한복판에서 우리는 그 거울 앞에 서야 한다. 정보는 넘치지만 진실은 더 멀리 있는 시대다.",
        "말씀이 육신이 되셨다는 한 마디가 안개를 가른다. 추상이 아니라 실재로 임하신 분이 있다. AI가 진실의 적인가 동반자인가의 물음 앞에서, 도구는 그것을 사용하는 자의 영성에 따라 다른 자리를 차지한다.",
        "불편해도 말해야 하는 자리가 있다. 진실은 자주 불편하지만, 불편한 진실을 마주하지 않는 영성은 깊어지지 않는다. 마지막 장 — 행동하는 믿음과 전자책을 쓰는 이유. 진실을 마주한 자가 침묵하지 않고 한 영혼이 다른 영혼에게 글로 다가가는 자리가 거기 있다.",
    ],
    2: [
        "정보 홍수 시대의 영혼이 첫 장의 자리다. 우리는 매일 수천 건의 정보를 마주하지만, 그 정보들이 우리 영혼을 자라게 하지는 않는다. 분별은 성령의 은사다. 똑똑함이 아니라 깨어 있음의 자리에서 자라는 능력.",
        "가짜뉴스와 광야의 시험이 짚어진다. 광야의 시험은 떡이 떡인지 돌인지를 알아보는 일이었다. 우리 시대의 시험도 같다. 좋은 씨앗을 고르는 농부의 시선을 우리에게 가르치는 자리다.",
        "비판적 사고와 믿음의 균형, SNS 시대의 마음 지키기, 그리고 진리의 영을 따라 걷는 자세가 차례로 펼쳐진다. 마지막 장은 진리의 영을 따라 걷다. 분별은 외부를 향하면서 동시에 내면을 향한다. 그 두 시선이 함께 흐를 때, 정보 홍수 시대에도 영혼이 흔들리지 않는다.",
    ],
    3: [
        "달콤한 강물의 유혹이 첫 장의 자리다. 포퓰리즘은 갈증을 풀어 주는 듯한 강물의 모습으로 다가온다. 그러나 그 강물은 우리를 떠밀고 가서, 결국 진실의 자리에서 멀어지게 한다.",
        "소수로 선 예언자들이 짚어진다. 거짓 선지자의 언어는 늘 다수의 박수를 받았고, 진짜 선지자는 늘 외롭게 한 자리에 섰다. 인기를 선택한 왕들과 진리를 전하는 지혜가 대비된다. 인기가 분별의 기준이 되는 시대에, 그리스도인은 무엇을 분별의 자리로 삼는가.",
        "용기의 근원은 자기 능력에서 오지 않는다. 사랑받고 있다는 정체성에서 흘러나온다. 마지막 장은 좁은 길을 택하는 리더. 모두가 가는 넓은 길을 떠나, 좁은 길에 서는 결단. 그 자리에서 한 영혼이 시대 한복판에서 흔들리지 않는 자세를 잡는다.",
    ],
    4: [
        "두 도성의 시민이 첫 장의 자리다. 그리스도인은 어색하게 두 자리 사이에 선 자다. 그 어색함이 사실은 가장 정직한 자리다. 어느 한쪽으로 미끄러지지 않고 두 자리 사이에 머무는 결단이 시민의 책임의 출발점이다.",
        "세상의 소금과 세상의 빛이 짚어진다. 소금은 자기를 드러내지 않으면서 결을 바꾸고, 빛은 자기를 비추면서 결을 바꾼다. 그 두 결이 한 영혼 안에 함께 흐를 때, 그리스도인의 사회적 자리가 빚어진다.",
        "공동선의 추구, 정의와 긍휼의 균형, 정치와 신앙 사이가 차례로 펼쳐진다. 마지막 장은 내가 선 자리에서. 거대한 변화는 결국 한 사람의 작은 결단에서 시작된다. 그 자리가 어디인가를 정직하게 묻는 자세, 그것이 시민의 책임의 가장 단단한 결이다.",
    ],
    5: [
        "정의란 무엇인가. 이 한 권은 그 가장 큰 물음을 성경의 시선으로 풀어낸다. 공의로우신 하나님이 정의의 출발점이다. 정의는 인간의 발명이 아니라 하나님의 본질에서 흘러나오는 결이다.",
        "자비 없는 정의는 폭력이다. 이 한 마디가 가장 깊은 자리다. 정의가 자비와 분리되는 순간, 그것은 보복이 되거나 위선이 된다. 미가서 6장 8절의 삼중 명령 — 정의를 행하며, 인자를 사랑하며, 겸손하게 하나님과 함께 행하는 것 — 이 정의의 결을 또렷이 한다.",
        "가난한 자와 나그네의 편에 서시는 하나님이 짚어진다. 정의가 추상이 아니라 한 영혼이 어디에 서느냐의 자리임을 가르친다. 마지막 장 — 정의를 살아내는 제자의 길. 정의는 외치는 자리가 아니라 살아내는 자리다. 십자가에서 공의와 자비가 만나는 결을 자기 일상에 새기는 자세다.",
    ],
    6: [
        "두 왕국의 실재가 첫 장의 자리다. 우리는 두 왕국 사이에서 살아간다. 그 사실을 잊는 순간, 우리의 영성은 한쪽 왕국에 길들여지기 시작한다. 세상의 기준을 해부하는 작업이 그래서 필요하다.",
        "하나님의 기준을 배운다는 것은 시간이 걸리는 일이다. 한 번에 익히는 게 아니라 매일의 묵상으로 빚어진다. 충돌의 현장이 짚어진다. 두 기준이 부딪히는 자리에서 우리는 어느 발에 무게를 싣는가.",
        "두 주인을 섬길 수 없다는 예수의 한 마디가 가장 단단한 자리다. 성경적 세계관의 눈으로 시대를 보는 자세, 마지막 장은 하나님의 기준으로 살아가기다. 두 기준 사이의 흔들림이 끝나지 않더라도, 한 결을 향해 매일의 결단을 쌓아 가는 자세, 그것이 그리스도인의 가장 정직한 자리다.",
    ],
    7: [
        "두려움의 시대다. 첫 장의 진단이 정직하다. 우리 시대는 거대한 두려움이 가득한 시대다. 그러나 두려움의 시대에 그리스도인은 두려움이 아닌 다른 결로 살아가도록 부름받았다. 담대함의 원천이 어디서 오는가의 물음에 이 책은 답한다.",
        "복음을 부끄러워하지 않는 삶이 짚어진다. 부끄러움은 자기 의식이 강할수록 커진다. 자기를 잊은 자리에서 복음이 자유롭게 흐른다. 핍박 속에서 피어나는 믿음의 결도 같다. 환경이 영성을 결정하지 않는다는 것을 핍박의 자리들이 증언한다.",
        "대가를 치르는 제자도와 시대를 분별하는 증인이 차례로 펼쳐진다. 마지막 장 — 담대히 서라. 두려움이 사라지지 않아도, 그 두려움 너머의 자리에 서는 자세. 그것이 영적 용기다. 두려움 없는 자리가 아니라 두려움보다 더 큰 한 마디로 응답하는 자리다.",
    ],
    8: [
        "다수가 틀릴 때 한 사람이 일어선다. 첫 장이 던지는 한 마디다. 다수가 진리의 자리에 올라선 시대에, 한 영혼이 정직하게 자기 자리를 지키는 결을 묵상한다. 엘리야의 고독이 짚어진다.",
        "엘리야는 자기만 남았다고 생각했지만, 숨겨진 7000명이 있었다. 우리도 그렇다. 자기만 외롭게 서 있다고 느낄 때, 시대 곳곳에 같은 결로 서 있는 영혼들이 있다. 남은 자의 계보가 그 위로다.",
        "작은 누룩의 능력과 침묵할 것인가 말할 것인가의 갈림길이 짚어진다. 마지막 장 — 나도 그 한 사람. 다른 누군가가 일어서기를 기다리지 않고, 내가 그 한 사람이 되는 결단. 광야에서 외치는 자의 가장 정직한 자리다.",
    ],
    9: [
        "예언자의 눈이 첫 장의 자리다. 예언자는 미래를 점치는 자가 아니라 시대의 결을 보는 자다. 제국의 의식 vs 예언자적 의식이 짚어진다. 우리가 길들여진 자리와 그 자리를 깨는 자리의 차이를 정직하게 분별한다.",
        "애통의 영성이 짚어진다. 예언자는 분노만 외치는 자가 아니라, 먼저 애통하는 자다. 시대를 향해 외치기 전에 시대를 위해 우는 자리에서 진짜 예언자가 시작된다. 하나님 나라의 청사진이 그 다음 결이다.",
        "거룩한 불만족과 대안 공동체의 삶이 짚어진다. 비판만 하는 자가 아니라 다른 세계를 살아내는 자가 진짜 예언자다. 마지막 장 — 소망의 선포. 예언자의 마지막 자리는 비판이 아니라 소망이다. 다른 세계가 가능하다는 한 마디를 자기 일상으로 살아내는 자, 그것이 예언자적 상상력의 가장 깊은 결이다.",
    ],
    10: [
        "거짓 평화의 정체가 첫 장이다. 거짓 평화는 갈등의 부재로 위장한 채 가장 깊은 곳에서 무너지는 자리다. 화산 위에 지은 집처럼, 표면은 평온해 보이지만 그 아래는 가장 위태로운 자리다.",
        "샬롬의 본질이 짚어진다. 샬롬은 갈등의 부재가 아니라 모든 것이 제자리에 있는 자리다. 정의와 자비와 진실이 함께 흐르는 자리. 편안함이라는 우상이 그 본질을 가린다. 거짓 선지자의 언어가 그 우상을 지킨다.",
        "평강을 분별하는 영성이 짚어진다. 평화처럼 보이는 자리가 사실은 거짓 평화일 수 있고, 갈등처럼 보이는 자리가 진짜 평화로 가는 길일 수도 있다. 마지막 장 — 진짜 안전으로의 초대. 거짓 평화 너머에서 시작되는 진짜 평화는 십자가 위에 있다. 갈등을 회피하지 않으시고 정면으로 통과하신 분 안에서, 우리는 진짜 안전을 발견한다.",
    ],
}


# 권별 길잡이 — 그 한 권만의 좁고 깊은 화두 (부 길잡이와 차별)
BOOK_GUIDES = {
    1: [
        "오늘 내가 마주하기 불편한 진실은 무엇이며, 그 진실 앞에서 나는 어떤 자세를 취하고 있는가.",
        "포스트 트루스 시대의 안개 한복판에서, 나는 어떤 거울 앞에 서서 자기를 비추고 있는가.",
        "행동하는 믿음이 정보의 시대에 어떤 결로 살아나고 있는가.",
    ],
    2: [
        "분별이 성령의 은사라면, 나는 그 은사를 어떤 자리에서 길러 가고 있는가.",
        "정보 홍수 속에서 좋은 씨앗을 고르는 농부의 시선을, 내 일상은 어떻게 살아내고 있는가.",
        "비판적 사고와 믿음의 균형이, 내 안에서 어떻게 한 결로 흐르고 있는가.",
    ],
    3: [
        "달콤한 강물의 유혹이 내 일상의 어디에서 흐르고 있으며, 나는 그 흐름에서 어떻게 멈추고 있는가.",
        "다수의 박수를 받는 자리와 진리를 향한 좁은 길의 자리에서, 나는 어느 길에 발을 딛고 있는가.",
        "용기의 근원이 자기 능력이 아니라 사랑받음이라면, 그 정체성을 나는 어디서 길어 올리고 있는가.",
    ],
    4: [
        "두 도성의 시민으로서, 나는 어느 한쪽으로 미끄러지지 않고 어떻게 두 자리 사이에 서 있는가.",
        "세상의 소금과 빛이 되는 자세가, 내 일상의 어떤 자리에서 살아나고 있는가.",
        "내가 선 자리에서 시작하는 작은 결단을, 오늘 어떻게 만들고 있는가.",
    ],
    5: [
        "자비 없는 정의는 폭력이라는 한 마디가, 내 정의 감각의 어떤 자리를 다시 빚고 있는가.",
        "미가의 삼중 명령 — 정의·자비·겸손한 동행을, 내 일상은 어떻게 살아내고 있는가.",
        "가난한 자와 나그네의 편에 서시는 하나님의 결이, 내 어떤 자리에서 흐르고 있는가.",
    ],
    6: [
        "세상의 기준에 길들여진 자리와 하나님의 기준을 따르는 자리가, 내 일상에서 어떻게 충돌하고 있는가.",
        "두 주인을 섬길 수 없다는 한 마디 앞에서, 내가 매일 다시 결단해야 할 자리는 어디인가.",
        "성경적 세계관의 눈으로 시대를 본다는 것이, 내 시선의 어떤 결을 다시 빚고 있는가.",
    ],
    7: [
        "두려움의 시대 한복판에서, 내가 길어 올려야 할 담대함의 원천은 어디에 있는가.",
        "복음을 부끄러워하지 않는 삶이, 내 어떤 일상에서 살아나고 있는가.",
        "대가를 치르는 제자도가, 내게 던져진 결단의 자리에서 어떻게 빚어지고 있는가.",
    ],
    8: [
        "다수가 틀릴 때 한 사람이 일어선다는 결단을, 내 일상의 어떤 자리에서 살아내고 있는가.",
        "엘리야가 자기만 남았다고 느꼈을 때 숨겨진 7000명이 있었다는 약속이, 내 외로움의 자리에 어떻게 닿고 있는가.",
        "나도 그 한 사람이 된다는 결단이, 내 어떤 호흡으로 자라고 있는가.",
    ],
    9: [
        "예언자의 눈이 시대의 결을 본다는 것이, 내 시선의 어떤 자리에서 자라고 있는가.",
        "애통의 영성이 분노보다 먼저 와야 한다는 결을, 나는 어떻게 살아내고 있는가.",
        "비판이 아니라 소망의 선포가 예언자의 마지막 자리라는 한 마디를, 내 어디서 새기고 있는가.",
    ],
    10: [
        "내가 진짜 평화로 알고 있던 자리가, 사실은 거짓 평화는 아니었는가.",
        "샬롬이 갈등의 부재가 아니라 정의·자비·진실의 흐름이라면, 그 흐름은 내 어디서 살아나고 있는가.",
        "편안함이라는 우상을 분별하고 진짜 안전으로 들어가는 자세가, 내 어떤 결단으로 빚어지고 있는가.",
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
  <div style="color:#888;font-size:0.88em;margin-top:0.3em">원본 ISBN {b['isbn']} · G06 제 {b['src_no']:02d} 권</div>
  <div style="margin-top:0.9em">
    <span style="display:inline-block;width:60px;border-top:1px solid #C8B99A"></span>
  </div>
</div>
<div style="max-width:32em;margin:0 auto">
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
<div style="max-width:34em;margin:0 auto">
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
<h3 style="color:#0F1E3C;margin-top:1.5em">광야의 외침이 닿는 자리</h3>
<p>이로써 G06 열 권의 묵상이 한 권으로 닫힙니다. 진실이 불편한 시대에서 시작해 거짓 평화에 속지 마라까지, 시대 분별의 결을 네 갈래로 모아 함께 걸어왔습니다. 처음에는 흩어져 있던 한 권 한 권의 묵상이 한 호흡으로 이어 붙고 나니, 사이를 흐르고 있던 결이 비로소 또렷해졌습니다.</p>
<p>이 책이 묻고자 했던 한 가지 물음은 분명합니다. <em>광장의 한복판에서 광야의 시선을 어떻게 잃지 않을 것인가.</em> 진실을 분별하는 시선과, 정의의 자리에 서는 자세와, 광야에서 외치는 자의 결과, 거짓 평화 너머의 진짜 평화를 응시하는 결 — 그 넷이 그 답의 네 갈래였습니다.</p>
<p><strong>1부에서 우리는 진실을 분별했습니다</strong>. 포스트 트루스 시대의 안개 한복판에서 거울 앞에 서는 자세, 정보 홍수 속에서 분별의 은사를 길러 가는 자리, 그리고 포퓰리즘의 달콤한 강물에서 좁은 길로 발걸음을 옮기는 결단을 함께 보았습니다. 분별은 외부와 내면을 동시에 향한다는 것을 우리는 다시 새겼습니다.</p>
<p><strong>2부에서 우리는 정의의 자리</strong>에 섰습니다. 두 도성의 시민으로서의 자세, 자비 없는 정의는 폭력이 된다는 한 마디, 그리고 두 기준이 충돌하는 자리에서의 분별을 함께 응시했습니다. 정의가 추상이 아니라 한 영혼이 어디에 서느냐의 자리임을, 미가의 삼중 명령 위에서 다시 보았습니다.</p>
<p><strong>3부에서 우리는 광야에서 외치는 자들</strong>을 만났습니다. 두려움의 시대에 담대함의 원천을 길어 올리는 자리, 다수가 틀릴 때 한 사람이 일어서는 결단의 자리, 그리고 비판을 넘어 소망을 선포하는 예언자적 상상력의 자리. 광야의 외침은 결국 한 사람의 결단에서 시작된다는 것을 함께 보았습니다.</p>
<p><strong>4부에서 우리는 거짓 평화 너머</strong>에 도달했습니다. 거짓 평화의 정체와 편안함이라는 우상의 결을 분별하면서, 진짜 안전이 시작되는 자리를 응시했습니다. 갈등을 회피하지 않으시고 십자가 위에서 진짜 평화를 이루신 분 안에서, 우리는 광야의 외침의 마지막 결을 발견했습니다.</p>
<p>이 책의 가장 단단한 한 마디는 표제에 이미 담겨 있습니다 — <em>광야의 외침.</em> 광장의 한복판에서 광야의 시선을 잃지 않는 자세, 다수의 함성에 떠밀리지 않는 자세, 거짓 평화에 속지 않고 진짜 평화를 향해 걸어가는 자세. 그 자세가 시대 한복판에서 그리스도인이 잃지 말아야 할 한 결입니다.</p>
<p>이 책을 덮으신 뒤에도 묵상은 끝나지 않습니다. 한 장씩 다시 펼쳐 읽어도 좋고, 한 단락만 천천히 반복해 읽어도 좋습니다. 다수의 함성에 떠밀리던 자리에서 광야의 시선으로 한 결이라도 옮겨 가셨다면, 그것만으로도 G06 열 권을 한 권으로 묶은 이유는 충분할 것입니다.</p>
<p>이제 100권 시리즈는 G07로, G08로, 그리고 마지막 G10까지 흘러갑니다. 광야의 외침이 닿는 자리의 결은 이 한 권에 모였습니다. 다음 그룹에서 또 다른 깊은 묵상으로 다시 만나기를 기도합니다. 주님의 평강이 여러분의 오늘 위에 충만히 임하시기를 축복합니다.</p>
</div>"""
    return xhtml_doc("닫는 글", body)


def build_publisher_xhtml(meta: dict, today_iso: str) -> str:
    body = f"""<div style="padding:3em 1.5em;line-height:1.9;font-size:0.95em;color:#333">

<div style="text-align:center;margin-bottom:2.5em">
  <img src="images/logo.png" alt="AI 시대 영성" style="max-width:55%;height:auto"/>
</div>

<h2 style="color:#0F1E3C;text-align:center;font-size:1.3em;border-bottom:1px solid #C8B99A;padding-bottom:0.6em;margin-bottom:1.5em">출판사 안내</h2>

<div style="max-width:34em;margin:0 auto">

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

    body = f"""<div style="padding:0.8em 1.5em;line-height:1.5;max-width:36em;margin:0 auto">
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
    files["OEBPS/cover.xhtml"] = build_cover_xhtml(proj["title"], proj["subtitle"]).encode("utf-8")
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
    uuid_id = f"omnibus-g06-{today_compact}-{datetime.now().strftime('%H%M%S')}"

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
    <dc:description>{proj['subtitle']} — G06 10권 종합본</dc:description>
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
    print("ISBN 발급 시 batch_books_g06_omnibus.json의 isbn 필드에 입력 후 재빌드.")


if __name__ == "__main__":
    main()
