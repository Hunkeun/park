# -*- coding: utf-8 -*-
"""
G08 10권 종합책 "무릎의 자리" epub 빌더.

입력:
  - batch_books_g08_omnibus.json (메타·4부 구조)
  - tmp/g08_omnibus_extracted.json (10권 본문 추출본)
  - G08 epub 중 한 권 (CSS 추출용)

출력:
  - ~/Downloads/전자책/무릎의_자리_YYYYMMDD_종합책.epub

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
META_PATH = PROJECT / "batch_books_g08_omnibus.json"
EXTRACT_PATH = PROJECT / "tmp" / "g08_omnibus_extracted.json"
SAMPLE_EPUB = Path.home() / "Downloads" / "전자책" / "기도의_깊이_20260419.epub"
OUT_DIR = Path.home() / "Downloads" / "전자책"
OUT_BACKUP_DIR = PROJECT / "tmp"  # 보조 사본


def get_css():
    """샘플 epub에서 CSS 추출."""
    with zipfile.ZipFile(SAMPLE_EPUB, "r") as z:
        return z.read("OEBPS/styles/style.css").decode("utf-8")


def get_cover_image():
    """전용 종합책 표지 사용 (없으면 샘플로 폴백)."""
    custom = PROJECT / "tmp" / "g08_omnibus_cover.jpg"
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
  <p><strong>구성</strong>　G08 10권 종합책 (4부 70장)</p>
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
    <p>이 책은 100권 영성 시리즈 G08(기도) 10권의 본문을 거의 그대로 4부 구조로 재편집하여 한 권으로 묶은 종합본입니다.</p>
    <p>각 권의 원본 ISBN 및 출간 정보는 본문 권별 도입 페이지에 명기되어 있습니다.</p>
  </div>
</div></div>"""
    return xhtml_doc("판권", body)


def build_preface_xhtml() -> str:
    body = """<div style="padding:2em 1.5em;line-height:1.9;font-size:1em;color:#222">
<h2 style="color:#0F1E3C;border-bottom:1px solid #C8B99A;padding-bottom:0.5em">여는 글</h2>
<h3 style="color:#0F1E3C;margin-top:1.5em">무릎이 가르치는 것들</h3>
<p>모든 영성은 결국 무릎의 자리로 모입니다. 그것이 어떤 양식의 기도이든, 어떤 시간의 기도이든, 어떤 길이의 기도이든, 한 영혼이 자기 무릎을 꿇은 자리에서 빚어집니다. 무릎이 가르치는 것이 있고, 그 가르침은 머리로 알 수 없는 자리에서 흘러옵니다.</p>
<p>이 책은 그 무릎의 자리를 차례로 따라 걷습니다. 기도의 본질, 시간과 양식의 결, 능력으로 흐르는 기도, 그리고 무릎의 사람들이 남긴 발자국까지 — 기도라는 한 단어 안에 담긴 그리스도교의 가장 정직한 묵상을 열 갈래로 펼쳐 놓았습니다.</p>
<p>이 책은 100권 영성 시리즈의 여덟 번째 그룹 G08을 한 권으로 묶은 종합본입니다. 기도의 깊이에서 기도의 용사들까지, 무릎이 빚어 내는 결을 네 갈래로 모았습니다. 열 권 각각의 본문을 거의 그대로 유지하면서, 그 사이를 흐르고 있던 결을 한 호흡으로 이어 붙였습니다.</p>
<p>네 갈래는 한 영혼의 무릎이 깊어 가는 한 길의 네 굽이입니다. <strong>1부 — 기도의 본질</strong>은 기도의 깊이와 주기도문에서 가장 본질적인 자리에 섭니다. <strong>2부 — 시간과 양식의 결</strong>은 새벽기도·통성기도·침묵기도·관상기도가 빚는 다양한 결을 응시합니다. <strong>3부 — 능력으로 흐르는 기도</strong>는 금식기도·응답·말씀과의 동행이 어떻게 능력의 자리가 되는가를 짚고, <strong>4부 — 무릎의 사람들</strong>은 중보의 사명과 기도의 용사들이 남긴 발자국을 마지막으로 모읍니다.</p>
<p>이 책은 기도법 매뉴얼이 아닙니다. 다만 기도가 한 영혼과 살아 계신 분 사이의 교제라는 것을, 그리고 그 교제는 매뉴얼로는 결코 다 담을 수 없다는 것을, 묵상의 자리로 우리를 데려가려 합니다. 기술이 아니라 자세, 양식이 아니라 결. 그 자리에서 비로소 기도가 시작됩니다.</p>
<p>한 번에 다 읽어내실 책이 아닙니다. 한 장씩, 한 묵상씩 호흡을 따라 가져가시면 됩니다. 이제 첫 장을 펼쳐 주십시오. 무릎의 자리에서, 한 호흡씩 함께 깊어져 봅시다.</p>
</div>"""
    return xhtml_doc("여는 글", body)


PART_INTROS = {
    1: {
        "headline": "기도라는 가장 본질적인 자리",
        "paragraphs": [
            "기도는 무엇입니까. 우리는 너무 자주 기도를 요청의 자리로만 이해합니다. 무엇을 받고 싶고, 무엇이 이루어졌으면 하고, 무엇에서 벗어나고 싶다는 자리. 그러나 그 자리는 기도의 한 결일 뿐, 기도의 본질은 아닙니다.",
            "기도는 설득이 아닙니다. 하나님의 마음을 바꾸는 도구가 아니라, 그분과 한 영혼 사이의 교제입니다. 얕은 물에서 시작해 깊은 바다로 나아가는 한 영혼의 항해. 요청에서 교제로 옮겨 가는 흐름. 그것이 기도의 본질입니다.",
            "기도의 가장 깊은 자리에는 침묵이 있습니다. 말이 사라지고도 사라지지 않는 임재. 어둠 속의 기도라는 자리도 있습니다. 응답이 보이지 않을 때, 답이 없는 듯한 자리에서도 우리는 기도합니다. 그 어둠의 자리가 사실은 가장 깊은 자리이기도 합니다.",
            "그리고 예수께서 우리에게 가르치신 기도가 있습니다. 주기도문은 단지 외워야 할 문장이 아니라, 기도의 모든 결이 압축된 모범입니다. 하늘에 계신 우리 아버지에서 시작해, 이름·나라·뜻·양식·용서·시험·구원으로 흐르는 일곱 결. 그 일곱 결이 우리 기도 전체를 빚는 골격이 됩니다.",
            "이 부의 두 권은 기도의 가장 본질적인 자리를 차례로 펼칩니다. 「기도의 깊이」는 얕은 물에서 깊은 바다로의 흐름을, 「주기도문 깊이 읽기」는 예수께서 가르치신 기도의 일곱 결을 다룹니다.",
            "기도가 요청에서 교제로 옮겨 가는 결을, 두 권의 본질 위에서 함께 새겨 보십시오.",
        ],
        "guides": [
            "내 기도가 요청의 자리에 머물고 있는가, 교제의 자리로 흘러가고 있는가.",
            "어둠 속의 기도가 가장 깊은 자리일 수 있다는 약속을, 내 어디서 붙들고 있는가.",
            "주기도문의 일곱 결이, 내 기도의 결을 어떻게 빚어 가고 있는가.",
            "이 부를 읽으며, 기도의 본질이 한 영혼의 어떤 자리로 흘러가는가에 주목해 보십시오.",
        ],
    },
    2: {
        "headline": "시간과 양식이 빚는 기도의 결",
        "paragraphs": [
            "기도의 언어는 하나가 아닙니다. 시간이 빚는 결이 있고, 양식이 빚는 결이 있으며, 자기 영혼의 결에 가장 잘 맞는 한 결도 있습니다. 모든 기도는 결국 한 영혼이 자기 자리에서 자기 무릎으로 드리는 응답이지만, 그 응답의 양식은 다양합니다.",
            "새벽기도는 시간이 빚는 결입니다. 새벽을 깨우는 마음, 이슬처럼 내리는 은혜, 그리고 한국교회가 새벽제단으로 살아낸 결. 새벽기도가 시간인가 태도인가의 물음이 짚어집니다. 결국 새벽은 한 자세의 표현이며, 그 자세가 하루 전체를 바꾸는 결을 빚습니다.",
            "통성기도와 침묵기도는 양식이 빚는 두 결입니다. 통성기도의 불길과 침묵기도의 깊이가 같은 영혼 안에서 함께 흐를 수 있습니다. 어느 한쪽만이 진짜 기도라고 하는 순간 우리는 한쪽 결을 잃습니다. 한국교회의 통성과 가톨릭의 침묵이 충돌하는 자리가 아니라 만나는 자리가 됩니다.",
            "관상기도는 더 깊은 결입니다. 해바라기의 영성처럼, 그분의 임재를 향해 마음을 돌리는 자세. 렉시오 디비나의 네 계단을 따라 말씀과 기도가 한 결로 흐르는 자리. 마음의 센터링이 우리를 가장 깊은 침묵의 자리로 데려갑니다.",
            "이 부의 세 권은 시간과 양식이 빚는 기도의 세 결을 차례로 펼칩니다. 「새벽기도의 은혜」는 시간이 빚는 결을, 「통성기도와 침묵기도」는 두 양식이 한 영혼 안에서 만나는 자리를, 「관상기도란 무엇인가」는 가장 깊은 침묵의 결을 다룹니다.",
            "다양한 양식이 한 영혼의 결을 빚는다는 것을, 세 권의 길 위에서 함께 발견해 보십시오.",
        ],
        "guides": [
            "새벽이 시간인가 태도인가의 물음 앞에서, 나는 어떤 결로 답하고 있는가.",
            "통성기도와 침묵기도가 충돌이 아니라 한 영혼 안에서 만나는 자리라는 것을, 나는 어떻게 살아내고 있는가.",
            "관상기도의 깊이가 내 일상의 어떤 자리에 닿고 있는가.",
            "이 부를 읽으며, 시간과 양식이 빚는 기도의 결을 함께 따라가 보십시오.",
        ],
    },
    3: {
        "headline": "기도가 능력으로 흐르는 자리",
        "paragraphs": [
            "기도는 단지 마음의 자리가 아닙니다. 능력이 임하는 자리이기도 합니다. 그러나 그 능력은 자기 의지로 만드는 능력이 아니라, 위로부터 임하시는 능력입니다. 한 영혼이 자기를 비우는 자리에서, 비로소 그 능력이 흘러들 수 있습니다.",
            "금식기도는 그 비움의 가장 또렷한 양식입니다. 금식의 본질은 음식을 끊는 것이 아니라 자기를 끊는 것입니다. 영적 안테나를 세우는 자리, 육신을 내려놓는 자리, 몸과 영혼을 함께 정결하게 하는 자리. 금식은 영적 전쟁의 무기이면서 동시에 집중과 몰입의 시간입니다.",
            "응답받는 기도의 비밀이 짚어집니다. 기도는 독백이 아닙니다. 응답이 있는 대화입니다. 다만 응답의 결이 다양합니다. 즉시 주실 때, 더 좋은 것을 주실 때, 그리고 No라고 하실 때 — 그 셋이 모두 응답입니다. 기다림의 계절에 우리가 배우는 것은 응답 자체보다 그분과의 만남입니다.",
            "기도와 말씀의 동행이 짚어집니다. 두 날개의 영성. 한쪽 날개로는 날 수 없습니다. 말씀이 기도가 되고, 기도가 말씀을 여는 자리. 렉시오 디비나의 길이 그 두 날개를 함께 세우는 자세를 가르칩니다. 일상 속 동행의 리듬에서 우리의 영성이 자라납니다.",
            "이 부의 세 권은 기도가 능력으로 흐르는 세 결을 차례로 펼칩니다. 「금식기도의 능력」은 비움의 결을, 「응답받는 기도의 비밀」은 세 가지 응답의 자리를, 「기도와 말씀의 동행」은 두 날개의 영성을 다룹니다.",
            "기도가 자기 능력이 아니라 위로부터 임하시는 능력의 자리라는 것을, 세 권의 결 위에서 함께 새겨 보십시오.",
        ],
        "guides": [
            "금식의 본질이 음식을 끊는 것이 아니라 자기를 끊는 것이라면, 내 어디서 그 결단을 내리고 있는가.",
            "응답이 즉시 주실 때, 더 좋은 것을 주실 때, No라고 하실 때 — 그 셋이 모두 응답이라는 것을, 내 기도는 어떻게 받아들이고 있는가.",
            "기도와 말씀의 두 날개가, 내 일상에서 어떻게 한 결로 흐르고 있는가.",
            "이 부를 읽으며, 기도가 능력으로 흐르는 자리가 자기 의지가 아니라 비움의 자리에서 시작된다는 것에 주목해 보십시오.",
        ],
    },
    4: {
        "headline": "무릎의 사람들이 남긴 발자국",
        "paragraphs": [
            "기도는 자기 자리에서 그치지 않습니다. 다른 영혼을 향해 흐릅니다. 그것이 중보의 자리입니다. 그리고 시대마다 무릎의 사람들이 있었고, 그들의 발자국이 우리 앞에 남아 있습니다. 우리는 그 발자국 위에 우리의 무릎을 놓도록 부름받았습니다.",
            "중보기도의 본질은 다른 사람을 위해 자기 자리를 내어주는 것입니다. 영적 피뢰침처럼 한 영혼이 다른 영혼의 자리에 서서 그 자리에 임하실 은혜를 끌어내리는 자세. 아브라함이 소돔을 위해 중보한 자리, 모세가 이스라엘을 위해 대리 기도한 자리에서 우리는 그 결을 봅니다.",
            "기도의 제단에 서는 것은 가벼운 일이 아닙니다. 희생의 기도가 짚어집니다. 자기 시간을, 자기 안락을, 자기 욕구를 내려놓고 그 자리를 다른 영혼에게 내어주는 결. 그 결이 모이는 자리가 한 사람의 중보 명단입니다. 그 명단은 단순한 이름의 목록이 아니라, 한 영혼이 자기 무릎으로 떠받치는 다른 영혼들의 자리입니다.",
            "그리고 시대를 흔든 무릎의 사람들이 있었습니다. 조지 뮬러는 고아 수천 명을 기도로 길렀고, 존 녹스의 기도가 스코틀랜드를 흔들었으며, 하이드 선교사는 기도의 사도라 불렸고, 평양대부흥은 길선주 장로의 무릎에서 시작되었습니다. 역사 속 기도의 골방들이 우리에게 가르치는 것은, 무릎 꿇은 자가 결국 세상을 움직인다는 한 마디입니다.",
            "이 부의 두 권은 무릎의 사람들의 두 결을 응시합니다. 「중보기도의 사명」은 한 영혼이 다른 영혼의 자리에 서는 결을, 「기도의 용사들」은 시대를 흔든 무릎의 사람들이 남긴 발자국을 다룹니다.",
            "마지막 장 — 나도 기도의 용사가 될 수 있다는 한 마디. 무릎의 사람들은 특별한 영성의 영웅이 아니라, 자기 자리에서 무릎을 꿇은 한 영혼들이었습니다. 그 자리가 우리에게도 열려 있습니다.",
        ],
        "guides": [
            "내 중보 명단에 있는 영혼들은 누구이며, 나는 그들을 어떤 무릎으로 떠받치고 있는가.",
            "희생의 기도가 어디까지 갈 수 있는가의 물음 앞에서, 내 결단의 자리는 어디까지 자라고 있는가.",
            "역사 속 무릎의 사람들의 발자국 위에서, 나는 다음 발걸음을 어떻게 옮기고 있는가.",
            "이 부를 읽으며, 무릎 꿇은 자가 세상을 움직인다는 한 마디가 내 일상에 어떻게 닿는가에 주목해 보십시오.",
        ],
    },
}


# 권별 요약 (각 책 진입부 — 3단락, 약 70% 분량)
# 마지막 단락의 핵심 한 문장은 3번째 단락 끝에 흡수
BOOK_SUMMARIES = {
    1: [
        "얕은 물에서 시작하다는 한 마디로 첫 권은 열린다. 우리는 모두 얕은 물에서 기도를 시작했다. 그러나 거기에 머무를 수는 없다. 깊은 바다로 나아가야 한다는 한 마디가 책 전체의 결을 정한다.",
        "기도는 설득이 아니다. 첫 장의 또렷한 한 마디다. 우리는 자주 기도를 하나님의 마음을 바꾸는 도구로 여긴다. 그러나 기도의 본질은 그 분과의 교제다. 침묵의 언어가 그 결을 가장 깊이 보여 준다.",
        "요청에서 교제로의 흐름이 짚어진다. 그리고 어둠 속의 기도라는 자리. 응답이 보이지 않을 때, 답이 없는 듯한 자리에서도 우리는 기도한다. 그 어둠이 사실은 가장 깊은 자리다. 마지막 장 — 깊은 바다로 나아가라. 기도의 깊이는 결국 한 영혼이 그 분의 임재 안에 머무는 깊이다.",
    ],
    2: [
        "하늘에 계신 우리 아버지로 시작한다. 주기도문의 첫 마디이자 모든 기도의 첫 자리다. 우리가 부를 수 있는 분이 누구이신가가 기도의 첫 자리를 정한다. 아버지라는 부르심 안에 모든 신학이 압축되어 있다.",
        "이름이 거룩히 여김을 받으시오며, 나라이 임하시오며, 뜻이 하늘에서 이룬 것같이 — 첫 세 결은 그분을 향한 결이다. 자기 요청보다 먼저 그분의 이름·나라·뜻을 구하는 자세. 그 순서가 우리 기도의 결을 다시 빚는다.",
        "일용할 양식·죄 사함·시험에 들지 않게 — 다음 세 결은 우리를 향한 결이다. 우리의 가장 정직한 필요들이 차례로 펼쳐진다. 마지막 장 — 시험에 들게 하지 마옵시며. 주기도문의 일곱 결이 한 호흡으로 우리 기도 전체를 빚는다는 것을, 이 한 권은 가장 깊은 자리에서 풀어낸다.",
    ],
    3: [
        "새벽을 깨우는 마음이 첫 장의 자리다. 새벽기도는 한국교회의 가장 깊은 영적 유산 중 하나다. 이슬처럼 내리는 은혜가 그 자리에서 흘러내린다. 한국교회와 새벽제단의 결이 짚어진다.",
        "시간인가 태도인가의 물음이 깊다. 새벽이라는 시간 자체가 거룩한 게 아니라, 새벽을 향한 한 영혼의 자세가 거룩하다. 시간이 아니라 자세, 그 자세가 일상 전체를 빚는다. 습관이 된 헌신이 결국 한 영혼의 영성을 결정한다.",
        "새벽이 바꾸는 하루가 짚어진다. 마지막 장 — 다시, 새벽으로. 한국교회가 잃어 가고 있는 새벽의 결을 다시 회복하는 자리다. 새벽은 단순한 시간이 아니라 한 영혼이 자기 자세를 매일 새롭게 정하는 거룩한 결단의 자리다.",
    ],
    4: [
        "기도의 언어는 하나가 아니다. 첫 장이 또렷이 박는 한 마디다. 통성기도가 한국교회의 결이라면, 침묵기도는 가톨릭 전통의 결이다. 그러나 둘은 충돌이 아니라 한 영혼 안에서 만나는 두 결이다.",
        "통성기도의 불길과 침묵기도의 깊이가 차례로 짚어진다. 통성은 영혼을 비우고 깊이를 여는 결이며, 침묵은 비워진 자리에 임재가 머물게 하는 결이다. 성경 속 다양한 기도의 모습이 그 두 결을 모두 증언한다.",
        "문화와 전통이 빚어낸 기도의 결, 그리고 몸으로 드리는 기도가 짚어진다. 마지막 장 — 나만의 기도 언어를 찾아서. 모든 기도의 양식이 모든 영혼에 똑같이 맞지는 않는다. 자기 영혼에 가장 맞는 기도 언어를 찾는 일이 영성의 자리이며, 그 자리에서 진짜 기도가 시작된다.",
    ],
    5: [
        "관상기도란 무엇인가의 첫 물음이다. 관상은 신비주의의 자리가 아니라 가장 정직한 임재의 자리다. 해바라기의 영성이 짚어진다. 해바라기가 해를 향해 마음을 돌리듯, 관상은 그분의 임재를 향해 마음을 돌리는 자세다.",
        "침묵, 하나님의 언어가 가장 깊은 자리다. 우리는 너무 자주 말로 채우려 하지만, 그분은 침묵으로 더 또렷이 말씀하신다. 렉시오 디비나의 네 계단 — 읽기·묵상·기도·관상이 차례로 펼쳐진다. 마음의 센터링이 그 결의 가장 정교한 양식이다.",
        "관상기도와 일상의 관계가 짚어진다. 관상은 수도원의 자리만이 아니라 일상의 자리다. 마지막 장 — 현대인에게 관상이 필요한 이유. 분주함이 신앙처럼 보이는 시대에 관상은 가장 강력한 저항이다. 멈춰서 그분 앞에 머무는 자리, 그것이 관상의 가장 깊은 결이다.",
    ],
    6: [
        "금식의 본질이 첫 장의 자리다. 금식은 음식을 끊는 것이 아니라 자기를 끊는 것이다. 그 비움의 결이 영적 안테나를 세우는 자리가 된다. 육신을 내려놓을 때 영의 감각이 살아난다는 결을 책은 정직하게 풀어낸다.",
        "몸과 영혼의 정결이 짚어진다. 금식은 영혼만의 일이 아니다. 몸과 영혼이 함께 정결해지는 자리이며, 그 자리에서 영적 전쟁의 무기가 빚어진다. 금식은 영적 무기 — 사탄의 권세를 깨뜨리는 결이다.",
        "집중과 몰입의 시간이 짚어진다. 금식의 자리에서 우리는 분주함을 내려놓고 한 자리에 집중한다. 마지막 장 — 금식 이후의 삶. 금식은 한 시기로 끝나는 게 아니라 일상으로 흘러나가야 한다. 금식이 가르치는 비움의 결이 일상의 결이 될 때, 진짜 금식이 시작된다.",
    ],
    7: [
        "기도는 독백이 아니다. 첫 장이 박는 한 마디다. 기도는 응답이 있는 대화다. 다만 응답의 결이 다양하다. 세 가지 응답의 비밀이 짚어진다. 즉시 주실 때, 더 좋은 것을 주실 때, 그리고 No라고 하실 때 — 그 셋이 모두 응답이다.",
        "No라고 하실 때의 은혜가 짚어진다. 거절도 응답이라는 것을 받아들이는 자리에서 진짜 기도가 시작된다. 기다림의 계절이 그 다음 결이다. 응답이 더디게 올 때 우리가 배우는 것은 응답 자체보다 그분과의 만남이다.",
        "하나님의 뜻을 구하는 기도와 믿음으로 드리는 기도가 짚어진다. 마지막 장 — 응답 너머의 만남. 기도의 가장 깊은 응답은 무엇을 받는 것이 아니라 누구를 만나는 것이다. 응답을 좇던 자리가 만남을 누리는 자리로 옮겨 갈 때, 기도는 비로소 깊어진다.",
    ],
    8: [
        "두 날개의 영성이 첫 장의 자리다. 기도와 말씀은 두 날개와 같다. 한쪽 날개로는 결코 날 수 없다. 둘이 함께 펼쳐질 때 한 영혼이 비로소 영적 비행을 한다. 말씀이 기도가 될 때의 결이 깊다.",
        "말씀이 기도가 되고, 기도가 말씀을 여는 자리가 짚어진다. 그 둘은 분리된 두 행위가 아니라 한 결의 두 측면이다. 렉시오 디비나의 길이 그 두 결을 한 호흡으로 잇는 가장 정교한 양식이다. 읽고·묵상하고·기도하고·관상하는 네 단계가 한 흐름을 이룬다.",
        "기울어진 날개를 세우는 자리가 짚어진다. 우리는 자주 한쪽 날개에 치우친다. 마지막 장 — 함께 나는 하늘. 기도와 말씀이 한 결로 펼쳐질 때 한 영혼이 가장 멀리 난다. 일상 속 동행의 리듬에서 우리의 영성이 깊어진다.",
    ],
    9: [
        "중보기도의 본질이 첫 장의 자리다. 중보는 다른 사람을 위해 자기 자리를 내어주는 결이다. 영적 피뢰침처럼 한 영혼이 다른 영혼의 자리에 서서 그 자리에 임하실 은혜를 끌어내리는 자세다.",
        "아브라함의 중보가 짚어진다. 소돔을 위해 흥정하듯 기도한 그 자리, 모세의 대리 기도가 그 다음 결이다. 이스라엘이 죄를 지었을 때 자기 이름을 명단에서 지워달라고까지 한 모세의 자리. 중보는 자기 안전을 내려놓는 결단이다.",
        "기도의 제단에 서다와 희생의 기도가 짚어진다. 중보는 시간과 안락과 욕구를 내려놓는 결이다. 마지막 장 — 나의 중보 명단. 단순한 이름의 목록이 아니라, 한 영혼이 자기 무릎으로 떠받치는 다른 영혼들의 자리다. 그 명단이 우리의 영성을 가장 정직하게 측량한다.",
    ],
    10: [
        "무릎 꿇은 자가 세상을 움직인다. 첫 장이 박는 한 마디가 책 전체의 결이다. 그리고 그 한 마디가 추상이 아니라 실제로 일어난 역사임을 증언하는 인물들이 차례로 등장한다.",
        "조지 뮬러는 기도만으로 고아 수천 명을 길렀다. 그의 후원자 명단에 한 사람도 없었다. 다만 그분께만 구했고, 그분이 응답하셨다. 존 녹스의 기도가 스코틀랜드를 흔들었다. '스코틀랜드를 주옵소서, 아니면 죽음을' 그의 한 마디가 한 나라를 빚었다.",
        "하이드 선교사, 평양대부흥의 길선주 장로 — 그들이 모두 무릎의 사람들이었다. 역사 속 기도의 골방들이 짚어진다. 마지막 장 — 나도 기도의 용사가 될 수 있다. 무릎의 사람들은 특별한 영적 영웅이 아니었다. 자기 자리에서 무릎을 꿇은 한 영혼들이었다. 그 자리는 우리에게도 열려 있다.",
    ],
}


# 권별 길잡이 — 그 한 권만의 좁고 깊은 화두 (부 길잡이와 차별)
BOOK_GUIDES = {
    1: [
        "내 기도가 얕은 물에 머물고 있는가, 깊은 바다로 나아가고 있는가.",
        "기도가 설득이 아니라 교제라는 한 마디 앞에서, 내 기도의 자세는 어떻게 다시 빚어지고 있는가.",
        "어둠 속의 기도가 가장 깊은 자리일 수 있다는 약속을, 나는 어디서 붙들고 있는가.",
    ],
    2: [
        "주기도문의 첫 자리 — 하늘에 계신 우리 아버지가, 내 기도의 첫 자세를 어떻게 빚고 있는가.",
        "주기도문의 일곱 결이 내 기도 전체를 빚는다면, 내가 가장 자주 잊는 결은 어느 것인가.",
        "자기 요청보다 먼저 그분의 이름·나라·뜻을 구하는 순서를, 내 기도는 어떻게 살아내고 있는가.",
    ],
    3: [
        "새벽이 시간인가 태도인가의 물음 앞에서, 나는 어떤 결로 답하고 있는가.",
        "이슬처럼 내리는 은혜라는 표현이, 내 어떤 자리에서 가장 또렷이 닿고 있는가.",
        "새벽이 바꾸는 하루의 결을, 나는 어떻게 일상에서 살아내고 있는가.",
    ],
    4: [
        "통성기도와 침묵기도가 한 영혼 안에서 만나는 자리를, 나는 어떻게 살아내고 있는가.",
        "성경 속 다양한 기도의 모습 가운데, 내 영혼에 가장 잘 맞는 결은 무엇인가.",
        "나만의 기도 언어를 찾는 여정이, 내 어떤 결단으로 자라고 있는가.",
    ],
    5: [
        "해바라기의 영성처럼 그분의 임재를 향해 마음을 돌리는 자세가, 내 일상의 어떤 자리에서 살아나고 있는가.",
        "침묵이 하나님의 언어라면, 나는 그 언어를 어떻게 듣고 있는가.",
        "분주함이 신앙처럼 보이는 시대에, 멈춰서 그분 앞에 머무는 자리를 나는 어떻게 만들고 있는가.",
    ],
    6: [
        "금식의 본질이 음식이 아니라 자기를 끊는 것이라면, 내 일상에서 자기를 끊는 자리는 어디인가.",
        "영적 안테나를 세우는 자리가, 내 어떤 결단에서 자라고 있는가.",
        "금식 이후의 삶이 진짜 금식이라는 한 마디를, 나는 어떻게 살아내고 있는가.",
    ],
    7: [
        "세 가지 응답 — 즉시·더 좋은 것·No 가운데, 내가 가장 받아들이기 어려운 응답은 무엇인가.",
        "기다림의 계절이 응답을 좇는 자리에서 만남을 누리는 자리로 옮겨 가는 결을, 나는 어떻게 살고 있는가.",
        "응답 너머의 만남이라는 한 마디가, 내 기도의 결을 어떻게 다시 빚고 있는가.",
    ],
    8: [
        "기도와 말씀의 두 날개 가운데, 내 안에서 더 기울어진 쪽은 어느 날개인가.",
        "말씀이 기도가 되고 기도가 말씀을 여는 자리를, 내 묵상은 어떻게 살아내고 있는가.",
        "렉시오 디비나의 네 단계가, 내 일상의 어떤 결로 자라고 있는가.",
    ],
    9: [
        "내 중보 명단에 있는 영혼들은 누구이며, 나는 그들을 어떤 무릎으로 떠받치고 있는가.",
        "아브라함의 흥정 같은 중보, 모세의 대리 같은 중보가, 내 어떤 자리에서 자라고 있는가.",
        "희생의 기도가 어디까지 갈 수 있는가의 물음 앞에서, 내 결단의 자리는 어디까지 자라고 있는가.",
    ],
    10: [
        "무릎 꿇은 자가 세상을 움직인다는 한 마디가, 내 어디서 살아나고 있는가.",
        "조지 뮬러·존 녹스·하이드·길선주의 무릎이, 내 무릎의 자세를 어떻게 다시 빚고 있는가.",
        "나도 기도의 용사가 될 수 있다는 마지막 한 마디를, 어떤 결단으로 받아들이고 있는가.",
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
  <div style="color:#888;font-size:0.88em;margin-top:0.3em">원본 ISBN {b['isbn']} · G08 제 {b['src_no']:02d} 권</div>
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
<h3 style="color:#0F1E3C;margin-top:1.5em">무릎의 자리에서 시작되는 모든 것</h3>
<p>이로써 G08 열 권의 묵상이 한 권으로 닫힙니다. 기도의 깊이에서 시작해 기도의 용사들에 이르기까지, 무릎의 자리가 빚어 내는 결을 네 갈래로 모아 함께 걸어왔습니다. 처음에는 흩어져 있던 한 권 한 권의 묵상이 한 호흡으로 이어 붙고 나니, 사이를 흐르고 있던 결이 비로소 또렷해졌습니다.</p>
<p>이 책이 묻고자 했던 한 가지 물음은 분명합니다. <em>무릎이 가르치는 것을, 한 영혼이 어떻게 받아들이고 살아낼 것인가.</em> 기도의 본질을 응시하는 자리와, 시간과 양식이 빚는 결과, 능력으로 흐르는 기도의 자리와, 무릎의 사람들이 남긴 발자국 — 그 넷이 그 답의 네 갈래였습니다.</p>
<p><strong>1부에서 우리는 기도의 본질</strong>을 응시했습니다. 기도가 설득이 아니라 교제라는 한 마디, 얕은 물에서 깊은 바다로 나아가는 흐름, 그리고 예수께서 가르치신 주기도문의 일곱 결을 함께 새겼습니다. 기도는 요청에서 교제로 옮겨 가는 자리라는 결이 우리에게 깊이 남았습니다.</p>
<p><strong>2부에서 우리는 시간과 양식의 결</strong>을 따라 걸었습니다. 새벽기도의 은혜, 통성과 침묵의 만남, 그리고 관상의 깊이를 함께 보았습니다. 기도의 언어는 하나가 아니며, 자기 영혼에 가장 맞는 결을 찾는 일이 영성의 자리라는 것을 다시 새겼습니다.</p>
<p><strong>3부에서 우리는 기도가 능력으로 흐르는 자리</strong>에 도달했습니다. 금식이라는 비움의 결, 세 가지 응답의 비밀, 그리고 기도와 말씀의 두 날개. 능력은 자기 의지로 만드는 게 아니라 비움의 자리에서 위로부터 임하신다는 것을 함께 보았습니다.</p>
<p><strong>4부에서 우리는 무릎의 사람들이 남긴 발자국</strong>을 따라갔습니다. 중보의 사명과 시대를 흔든 기도의 용사들. 무릎 꿇은 자가 세상을 움직인다는 한 마디가 추상이 아니라 역사로 증언된 자리였습니다.</p>
<p>이 책의 가장 단단한 한 마디는 표제에 이미 담겨 있습니다 — <em>무릎의 자리.</em> 모든 영성은 결국 그 자리에서 시작됩니다. 어떤 양식이든, 어떤 시간이든, 어떤 길이의 기도이든, 한 영혼이 자기 무릎을 꿇은 자리에서 비로소 진짜가 시작됩니다. 무릎이 가르치는 것을 머리로는 결코 알 수 없습니다.</p>
<p>이 책을 덮으신 뒤에도 묵상은 끝나지 않습니다. 한 장씩 다시 펼쳐 읽어도 좋고, 한 단락만 천천히 반복해 읽어도 좋습니다. 기도를 매뉴얼로만 다루던 자리에서 한 영혼의 자세로 만나는 자리로 한 결이라도 옮겨 가셨다면, 그것만으로도 G08 열 권을 한 권으로 묶은 이유는 충분할 것입니다.</p>
<p>이제 100권 시리즈는 G09로, 그리고 마지막 G10까지 흘러갑니다. 무릎의 자리에서 시작되는 모든 것의 결은 이 한 권에 모였습니다. 다음 그룹에서 또 다른 깊은 묵상으로 다시 만나기를 기도합니다. 주님의 평강이 여러분의 오늘 위에 충만히 임하시기를 축복합니다.</p>
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
    uuid_id = f"omnibus-g08-{today_compact}-{datetime.now().strftime('%H%M%S')}"

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
    <dc:description>{proj['subtitle']} — G08 10권 종합본</dc:description>
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
    print("ISBN 발급 시 batch_books_g08_omnibus.json의 isbn 필드에 입력 후 재빌드.")


if __name__ == "__main__":
    main()
