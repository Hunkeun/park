# -*- coding: utf-8 -*-
"""
G07 10권 종합책 "바람과 불" epub 빌더.

입력:
  - batch_books_g07_omnibus.json (메타·4부 구조)
  - tmp/g07_omnibus_extracted.json (10권 본문 추출본)
  - G07 epub 중 한 권 (CSS 추출용)

출력:
  - ~/Downloads/전자책/바람과_불_YYYYMMDD_종합책.epub

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
META_PATH = PROJECT / "batch_books_g07_omnibus.json"
EXTRACT_PATH = PROJECT / "tmp" / "g07_omnibus_extracted.json"
SAMPLE_EPUB = Path.home() / "Downloads" / "전자책" / "성령님을_알아가는_시간_20260419.epub"
OUT_DIR = Path.home() / "Downloads" / "전자책"
OUT_BACKUP_DIR = PROJECT / "tmp"  # 보조 사본


def get_css():
    """샘플 epub에서 CSS 추출."""
    with zipfile.ZipFile(SAMPLE_EPUB, "r") as z:
        return z.read("OEBPS/styles/style.css").decode("utf-8")


def get_cover_image():
    """전용 종합책 표지 사용 (없으면 샘플로 폴백)."""
    custom = PROJECT / "tmp" / "g07_omnibus_cover.jpg"
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
  <p><strong>구성</strong>　G07 10권 종합책 (4부 70장)</p>
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
    <p>이 책은 100권 영성 시리즈 G07(성령) 10권의 본문을 거의 그대로 4부 구조로 재편집하여 한 권으로 묶은 종합본입니다.</p>
    <p>각 권의 원본 ISBN 및 출간 정보는 본문 권별 도입 페이지에 명기되어 있습니다.</p>
  </div>
</div></div>"""
    return xhtml_doc("판권", body)


def build_preface_xhtml() -> str:
    body = """<div style="padding:2em 1.5em;line-height:1.9;font-size:1em;color:#222">
<h2 style="color:#0F1E3C;border-bottom:1px solid #C8B99A;padding-bottom:0.5em">여는 글</h2>
<h3 style="color:#0F1E3C;margin-top:1.5em">바람으로 임하시고 불로 머무시는 분</h3>
<p>성령은 바람과 불로 오십니다. 요한복음 3장에서 예수께서 니고데모에게 말씀하셨습니다. 바람이 임의로 불매 네가 그 소리는 들어도 어디서 와서 어디로 가는지 알지 못한다고. 그리고 사도행전 2장에서, 마가의 다락방 위로 급하고 강한 바람이 불어왔고 갈라진 불의 혀가 임했습니다. 바람과 불 — 그 두 상징이 성령의 결을 함께 그려냅니다.</p>
<p>바람은 자유롭게 임하시는 분이고, 불은 한 자리에 머무시며 빚으시는 분입니다. 한쪽 결만으로는 성령을 다 그릴 수 없습니다. 임하시는 자유와 머무시는 깊이가 함께 있어야 비로소 성령의 결이 또렷해집니다.</p>
<p>이 책은 그 바람과 불의 결을 차례로 따라 걷습니다. 보혜사를 만나는 자리와, 능력으로 임하시는 은사들과, 분별과 지혜의 결과, 충만에서 부흥까지의 흐름. 100권 영성 시리즈의 일곱 번째 그룹 G07을 한 권으로 묶은 종합본입니다. 성령님을 알아가는 시간에서 마지막 시대의 부흥까지, 성령이라는 한 단어 안에 담긴 그리스도교의 가장 깊은 묵상을 네 갈래로 모았습니다.</p>
<p>네 갈래는 한 영혼이 성령과 동행하는 한 길의 네 굽이입니다. <strong>1부 — 보혜사의 자리</strong>는 성령님을 알아가는 자리와 오순절의 임재에서 시작하고, <strong>2부 — 능력으로 임하시는 분</strong>은 방언·예언·치유의 은사를 통해 성령의 능력이 임하는 결을 응시합니다. <strong>3부 — 분별과 지혜의 결</strong>은 지혜의 영과 분별의 은사로 영적 자질이 빚어지는 자리를 짚고, <strong>4부 — 충만에서 부흥까지</strong>는 성령충만한 삶에서 마지막 시대의 부흥까지의 흐름을 마지막으로 모읍니다.</p>
<p>이 책은 성령에 대한 모든 질문에 답하지 않습니다. 다만 성령이 추상이 아니라 한 영혼과 함께 살아 계신 분이라는 것을, 묵상의 자리로 우리를 데려가려 합니다. 이론이 아니라 동행, 교리가 아니라 임재. 그 결로 흘러가는 자리에서 비로소 성령을 만날 수 있습니다.</p>
<p>한 번에 다 읽어내실 책이 아닙니다. 한 장씩, 한 묵상씩 호흡을 따라 가져가시면 됩니다. 이제 첫 장을 펼쳐 주십시오. 바람으로 임하시고 불로 머무시는 분을, 한 호흡씩 함께 만나 봅시다.</p>
</div>"""
    return xhtml_doc("여는 글", body)


PART_INTROS = {
    1: {
        "headline": "보혜사를 만나는 자리",
        "paragraphs": [
            "성령은 누구이십니까. 이 물음 앞에서 우리는 자주 멈춥니다. 추상으로 머무는 답은 많지만, 한 영혼이 자기 일상에서 만나는 인격적 답은 드뭅니다. 그러나 성령은 인격이시며, 우리에게 보내신 보혜사 — 곁에 함께 부르심을 받은 분이십니다.",
            "보혜사라는 단어 자체가 그 결을 또렷이 합니다. 변호인처럼·동료처럼·친구처럼 함께 앉아 주시는 분. 멀리 계신 분이 아니라 가까이 계신 분, 그러면서도 거룩하신 분. 그 두 결이 함께 있는 자리에서 우리는 비로소 성령을 만나기 시작합니다.",
            "오순절은 그 만남의 가장 큰 사건입니다. 마가의 다락방에 모여 기도하던 자들 위로 급하고 강한 바람이 불었고, 갈라진 불의 혀가 임했습니다. 그 자리에서 베드로의 첫 설교가 흘러나왔고, 초대교회의 불꽃이 시작되었습니다. 한 번의 사건이 아니라 모든 시대로 흘러내린 임재의 시작이었습니다.",
            "그러나 오순절은 과거의 사건만은 아닙니다. 오늘도 임하시는 오순절이 있습니다. 한 영혼이 임재의 문을 열고, 거짓 자아를 내려놓고 참 자아로 서며, 말씀으로 조명하시는 그분과 친구처럼 교제하는 자리. 거기에서 오순절은 매일 일어나는 사건이 됩니다.",
            "이 부의 두 권은 보혜사를 만나는 두 결을 차례로 펼칩니다. 「성령님을 알아가는 시간」은 임재의 문을 열고 친구처럼 교제하는 자리를, 「오순절의 불」은 마가의 다락방에서 시작된 임재가 오늘도 임하는 결을 다룹니다.",
            "성령은 알게 되는 분이 아니라 만나는 분입니다. 그 만남의 자리로 함께 들어가십시오.",
        ],
        "guides": [
            "성령님이 곁에 함께 계시는 보혜사라면, 나는 그 동행을 어떤 일상에서 살아내고 있는가.",
            "오늘도 임하시는 오순절이 있다는 약속을, 내 어떤 자리에서 받아들이고 있는가.",
            "임재의 문을 연다는 것이, 내 어떤 결정과 어떤 호흡으로 살아나고 있는가.",
            "이 부를 읽으며, 보혜사를 알게 되는 자리에서 만나는 자리로 옮겨 가는 결을 따라가 보십시오.",
        ],
    },
    2: {
        "headline": "능력으로 임하시는 분",
        "paragraphs": [
            "성령은 단지 위로하시는 분이 아닙니다. 능력으로 임하시는 분이기도 합니다. 사도행전에서 성령이 임하시매 권능을 받고 증인이 된다는 약속이 그 결을 가장 또렷이 합니다. 능력은 자기를 위한 것이 아니라 증언을 위한 것이며, 화려함이 아니라 한 영혼을 살리는 결입니다.",
            "방언의 은사가 있습니다. 오순절 예루살렘에서 일어난 첫 방언은 복음의 통로였습니다. 각 사람이 자기 방언으로 듣게 되는 기적이 일어났고, 그 자리에서 복음이 사방으로 퍼졌습니다. 그러나 고린도교회의 방언은 다른 양상을 보였고, 참과 거짓을 분별하는 자세가 필요했습니다.",
            "예언의 은사도 그러합니다. 점술과 예언의 차이는 결정적입니다. 점술은 미래를 알려 주는 자리이지만, 예언은 하나님의 마음을 전하는 자리입니다. 자기를 높이는 자리가 아니라 교회를 세우는 자리. 그 결을 분별하는 자세 없이 예언은 길을 잃습니다.",
            "치유의 은사가 짚어집니다. 치유하시는 하나님의 본성에서 시작해 예수님의 치유 사역을 거쳐, 야고보서의 치유 원리에 도달합니다. 기적과 의학 사이에서, 그리고 치유되지 않을 때조차도 영혼의 치유라는 더 깊은 회복을 향해 가는 자세를 우리는 이 부에서 만납니다.",
            "이 부의 세 권은 능력으로 임하시는 세 결을 차례로 펼칩니다. 「방언의 은사」는 오순절과 고린도와 한국교회를 가로지르는 분별을, 「예언의 은사」는 하나님의 마음을 전하는 자세를, 「치유의 은사」는 영혼의 치유까지 이어지는 회복의 결을 다룹니다.",
            "능력은 자기 자랑의 자리가 아니라 한 영혼을 향한 사랑의 자리입니다. 그 결을 함께 따라가 보십시오.",
        ],
        "guides": [
            "성령이 능력으로 임하신다는 것이, 내 일상의 어떤 자리에서 증언으로 살아나고 있는가.",
            "방언과 예언과 치유의 은사를 분별하는 자세를, 나는 어떤 결로 길러 가고 있는가.",
            "치유되지 않을 때에도 영혼의 치유가 있다는 약속을, 나는 어디서 붙들고 있는가.",
            "이 부를 읽으며, 능력의 은사들이 자기 자랑이 아니라 한 영혼을 향한 사랑의 결로 흐르는 자리에 주목해 보십시오.",
        ],
    },
    3: {
        "headline": "분별과 지혜의 결",
        "paragraphs": [
            "성령은 능력의 영이실 뿐 아니라 지혜의 영이시기도 합니다. 위로부터 오는 지혜는 인간의 똑똑함과 다릅니다. 솔로몬이 어린 나이에 권력 대신 지혜를 구한 그 자리, 그 자리에서 위로부터 오는 지혜의 결이 시작됩니다. 지혜의 근본은 여호와를 경외함이라는 한 마디가 그 결의 토대입니다.",
            "지혜를 구하라, 후히 주시리라는 약속이 있습니다. 지혜는 자기 노력으로 쌓는 게 아니라 위로부터 받는 선물입니다. 그러나 받기 위해서는 구해야 합니다. 그리고 받은 지혜의 열매는 결국 온유와 긍휼로 흐릅니다. 똑똑함이 사람을 차갑게 하지만, 지혜는 사람을 부드럽게 합니다.",
            "분별의 은사는 그 지혜의 가장 정교한 결입니다. 모든 영이 하나님께 속한 것은 아닙니다. 시대의 영, 자기의 영, 다른 영들이 함께 흐르는 시대에 분별의 은사 없이 한 영혼이 흔들리지 않기는 어렵습니다.",
            "금세공사의 눈이 짚어집니다. 금세공사는 가짜 금을 한 번에 알아봅니다. 손에 익은 무게와 결을 통해. 분별도 그러합니다. 영을 시험하는 네 가지 테스트가 있고, 분별하되 정죄하지 않는다는 한 마디가 그 결의 균형을 잡습니다.",
            "이 부의 두 권은 분별과 지혜의 두 결을 응시합니다. 「지혜의 영」은 위로부터 오는 지혜의 토대를, 「분별의 은사」는 영을 시험하는 네 가지 테스트와 분별의 사람으로 살아가는 자세를 다룹니다.",
            "지혜는 머리의 일이 아니라 영의 일입니다. 분별은 똑똑함이 아니라 깨어 있음입니다. 그 두 결이 한 영혼 안에 함께 흐를 때, 능력의 은사들도 비로소 길을 잃지 않습니다.",
        ],
        "guides": [
            "위로부터 오는 지혜를 구하는 자리를, 나는 어떻게 만들고 있는가.",
            "지혜의 근본인 여호와를 경외함이, 내 일상의 어떤 결로 살아나고 있는가.",
            "영을 시험하는 분별의 자세를, 나는 어떤 자리에서 길러 가고 있는가.",
            "이 부를 읽으며, 분별과 지혜가 능력의 은사를 어떻게 길 잃지 않게 빚는가에 주목해 보십시오.",
        ],
    },
    4: {
        "headline": "충만에서 부흥까지",
        "paragraphs": [
            "성령충만은 일회적 경험이 아닙니다. 매일의 양식처럼 새롭게 채워지는 결입니다. 한 번 받고 끝나는 게 아니라, 매일 비워지고 매일 채워지는 자리. 그 결을 잃으면 우리의 영성은 점점 메말라 갑니다.",
            "성령충만을 방해하는 것들이 있습니다. 자기 의·죄·근심·불순종 — 그 모든 것이 충만의 통로를 막습니다. 그러나 통로가 열린 자리에서 성령충만의 열매가 자연스럽게 자라납니다. 매일의 영성 습관, 곧 말씀과 기도와 교제의 자리에서 충만이 빚어집니다.",
            "성령의 열매가 짚어집니다. 사랑·희락·화평·오래 참음·자비·양선·충성·온유·절제. 갈라디아서 5장의 아홉 가지 열매. 이 열매들은 우리가 노력해서 만드는 게 아니라, 포도나무에 붙어 있을 때 자연스럽게 맺히는 결입니다.",
            "그리고 마지막 시대의 부흥이 있습니다. 모든 육체 위에 성령을 부어 주신다는 요엘 2장의 약속, 사도행전 2장에서 부분적으로 성취되었지만 마지막 시대에 더 큰 결로 임할 것을 우리는 봅니다. 쇠퇴가 아닌 추수의 시대가 우리 앞에 있습니다.",
            "이 부의 세 권은 충만에서 부흥까지의 흐름을 차례로 펼칩니다. 「성령충만한 삶」은 일회적 경험을 넘어 매일 채워지는 결을, 「성령의 열매」는 포도나무에 붙어 자연스럽게 맺히는 아홉 열매를, 「마지막 시대의 부흥」은 성령의 늦은 비와 추수꾼의 부르심을 다룹니다.",
            "성령과 동행하는 한 영혼의 길은 결국 부흥의 결로 모입니다. 그 마지막 자리로 함께 들어가십시오.",
        ],
        "guides": [
            "성령충만이 일회적 경험이 아니라 매일 채워지는 결이라는 것을, 내 일상은 어떻게 살아내고 있는가.",
            "성령의 아홉 열매 가운데, 내 안에서 가장 자라야 할 결은 무엇인가.",
            "마지막 시대의 부흥이 쇠퇴가 아닌 추수라면, 나는 어떤 추수꾼의 자세로 서고 있는가.",
            "이 부를 읽으며, 충만에서 부흥까지의 흐름이 한 영혼 안에서 어떻게 빚어지는가에 주목해 보십시오.",
        ],
    },
}


# 권별 요약 (각 책 진입부 — 3단락, 약 70% 분량)
# 마지막 단락의 핵심 한 문장은 3번째 단락 끝에 흡수
BOOK_SUMMARIES = {
    1: [
        "성령님은 누구이신가의 물음에서 첫 권은 시작한다. 추상의 답이 아니라 한 영혼이 만나는 인격적 답을 향해 책은 흘러간다. 임재의 문을 열고 거짓 자아와 참 자아의 차이를 분별하는 자리에서, 비로소 성령과의 동행이 시작된다.",
        "말씀으로 조명하시는 분이 짚어진다. 성령은 새 계시를 주시는 분이 아니라 이미 주신 말씀을 매일 새롭게 비추시는 분이다. 그 말씀의 빛 안에서 한 영혼이 자기 자리를 다시 발견한다. 친구처럼 교제하다는 한 마디가 깊다. 보혜사는 멀리 계신 분이 아니라 친구처럼 곁에 있는 분이다.",
        "은사는 관계의 열매다. 은사를 좇는 것이 아니라 관계를 깊이 하는 자리에서 은사가 자연스럽게 따라온다. 마지막 장 — 오늘, 성령님과 동행하다. 성령은 알게 되는 분이 아니라 매일 동행하는 분이라는 것을, 이 한 권은 가장 정직한 자리에서 풀어낸다.",
    ],
    2: [
        "마가의 다락방이 첫 장의 자리다. 백이십여 명이 한자리에 모여 기도하던 그 자리에서, 약속하신 성령이 임하셨다. 급하고 강한 바람이 불어오고 갈라진 불의 혀가 임하는 광경이 짚어진다. 그 사건이 단지 한 번으로 끝난 게 아니라 모든 시대로 흘러내린 결을 우리는 본다.",
        "방언과 복음의 통로가 짚어진다. 오순절 방언의 본질은 자기 과시가 아니라 복음을 듣는 자에게 자기 방언으로 닿게 하는 것이었다. 베드로의 첫 설교가 그 자리에서 흘러나왔고, 삼천 명이 회개하며 초대교회의 불꽃이 시작되었다.",
        "초대교회의 불꽃이 어떻게 오늘까지 흘러왔는가가 짚어진다. 마지막 장 — 오늘도 임하시는 오순절. 오순절은 박물관에 보관된 사건이 아니라 매일 임하시는 임재의 사건이다. 한 영혼이 마음을 열 때, 마가의 다락방은 오늘도 다시 열린다.",
    ],
    3: [
        "방언이란 무엇인가의 첫 물음에서 책은 시작한다. 오순절 예루살렘의 방언과 고린도교회의 방언이 같은 단어로 불리지만 결은 달랐다. 그 차이를 정직하게 분별하는 자리에서 방언의 본질이 또렷해진다.",
        "참 방언과 거짓 방언의 분별이 짚어진다. 모든 방언이 성령의 방언은 아니다. 통변의 은사와의 관계, 그리고 타 종교의 방언 현상이 차례로 비교된다. 분별은 비판을 위한 것이 아니라 진짜를 지키기 위한 것이다.",
        "마지막 장 — 한국교회 방언의 재해석. 한국교회에 깊이 뿌리내린 방언의 결을 정직하게 다시 보는 자리다. 방언은 영적 자랑의 도구가 아니라 한 영혼의 가장 정직한 기도의 자리다. 그 본질로 돌아가는 자세를 이 책은 묻는다.",
    ],
    4: [
        "예언이란 무엇인가의 첫 물음이다. 점술과 예언의 차이가 즉시 짚어진다. 점술은 미래를 알려 주는 자리이지만, 예언은 하나님의 마음을 전하는 자리다. 그 차이를 분별하지 못하면 예언은 길을 잃는다.",
        "성령의 은사로서의 예언과 교회를 세우는 예언이 짚어진다. 자기 권위를 세우는 예언이 아니라 교회를 세우는 예언, 한 영혼을 위로하고 권면하는 예언. 그 결이 또렷해진다.",
        "예언의 분별과 예언의 등대가 펼쳐진다. 모든 예언을 다 받아들이는 것도, 모든 예언을 다 거부하는 것도 영성의 자리가 아니다. 마지막 장 — 하나님의 마음을 전하는 자. 예언자는 자기 말을 하는 자가 아니라 하나님의 마음을 자기 입으로 내는 자다. 그 자리의 무게를 정직하게 짚는다.",
    ],
    5: [
        "치유하시는 하나님이 첫 장의 자리다. 치유는 신비주의가 아니라 하나님의 본성에서 흘러나오는 결이다. 예수님의 치유 사역이 그것을 가장 또렷이 보여 준다. 신체적 치유와 영적 치유가 분리되지 않고 한 결로 흐르는 자리다.",
        "치유의 은사와 야고보서의 치유 원리가 짚어진다. 장로들을 청하여 기름을 바르며 기도하라는 한 마디가 가장 단단한 자리다. 치유는 한 사람의 카리스마가 아니라 공동체의 기도와 함께 일어나는 결이다.",
        "기적과 의학 사이에서 분별이 필요하다. 의학을 거부하는 영성도, 의학만 의지하는 신앙도 모두 한쪽으로 미끄러진 자세다. 치유되지 않을 때조차 영혼의 치유라는 더 깊은 자리가 있다는 것을 마지막 장이 가르친다. 치유의 마지막 결은 신체가 아니라 영혼이다.",
    ],
    6: [
        "위로부터 오는 지혜가 첫 장의 자리다. 인간의 똑똑함이 아니라 위로부터 받는 지혜. 그 차이를 야고보서가 가장 또렷이 한다. 솔로몬의 기도가 그 출발점이다. 권력 대신 지혜를 구한 한 어린 왕의 결단이 시대를 빚었다.",
        "지혜의 근본은 여호와를 경외함이다. 이 한 마디가 가장 단단한 토대다. 자기를 의지하지 않고 그분을 경외하는 자리에서 지혜가 시작된다. 성령은 지혜의 영이시다. 지혜는 결국 성령의 은사이며, 위로부터 오는 선물이다.",
        "구하라, 후히 주시리라는 약속이 짚어진다. 그리고 분별의 은사가 지혜의 결의 한 자리로 자연스럽게 이어진다. 마지막 장 — 온유와 긍휼의 열매. 지혜는 결국 온유와 긍휼로 흐른다. 똑똑함이 사람을 차갑게 하지만, 지혜는 사람을 부드럽게 한다.",
    ],
    7: [
        "모든 영이 하나님께 속한 것은 아니다. 첫 장의 한 마디가 분별의 출발점이다. 시대의 영, 자기의 영, 다른 영들이 함께 흐르는 자리에서 한 영혼이 진짜를 알아보려면 분별의 은사가 필요하다.",
        "금세공사의 눈이 짚어진다. 금세공사는 가짜 금을 한 번에 알아본다. 손에 익은 무게와 결을 통해. 분별도 그러하다. 한 번에 익히는 게 아니라 매일의 훈련으로 빚어진다. 거짓 선지자를 분별하라는 한 마디가 단단하다.",
        "영을 시험하는 네 가지 테스트가 짚어진다. 그리고 분별하되 정죄하지 않는다는 한 마디가 균형을 잡는다. 분별은 비판의 자리가 아니라 보호의 자리다. 마지막 장 — 분별의 사람으로 살아가기. 분별의 은사는 한 사람을 분별의 사람으로 빚는다. 그 자세가 시대 한복판에서 한 영혼을 흔들리지 않게 한다.",
    ],
    8: [
        "성령충만이란 무엇인가. 첫 장이 그 정의를 정직하게 다시 짚는다. 일회적 경험을 넘어서, 매일의 양식처럼 새롭게 채워지는 결이라는 결론에 책은 도달한다. 한 번 받고 끝나는 게 아니라 매일 비워지고 매일 채워지는 자리.",
        "성령충만을 방해하는 것들이 짚어진다. 자기 의·죄·근심·불순종 — 그 모든 것이 충만의 통로를 막는다. 그러나 통로가 열린 자리에서 자연스럽게 충만의 열매가 자라난다. 노력으로 만드는 게 아니라 통로를 여는 자세다.",
        "매일의 영성 습관이 짚어진다. 말씀과 기도와 교제의 자리. 마지막 장 — 성령충만한 삶의 열매를 맺으며. 성령충만은 감정의 고조가 아니라 일상의 결이다. 매일 비워지고 매일 채워지는 자리, 그것이 성령충만한 삶의 가장 정직한 자리다.",
    ],
    9: [
        "열매 맺는 삶의 비밀이 첫 장의 자리다. 우리는 너무 자주 열매를 만들려고 애쓴다. 그러나 성경은 열매를 만들라고 말하지 않는다. 포도나무에 붙어 있으라고 말한다. 붙어 있는 자리에서 열매가 자연스럽게 자라난다.",
        "사랑이 모든 열매의 뿌리다. 갈라디아서 5장의 아홉 열매 가운데 사랑이 첫째 자리에 있는 것은 우연이 아니다. 사랑의 뿌리에서 희락과 화평이 자라고, 오래 참음과 자비와 양선이 자라며, 충성과 온유가 자라고, 마침내 절제로 완성된다.",
        "마지막 장 — 포도나무에 붙어있으라. 이 책의 가장 단단한 결이다. 열매를 노력으로 만들 수 없다. 다만 포도나무에 붙어 있으면 된다. 그 단순한 자세가 결국 가장 깊은 영성의 결이다.",
    ],
    10: [
        "마지막 시대의 약속이 첫 장의 자리다. 요엘 2장에서 약속하신 모든 육체 위에 성령을 부어 주신다는 약속이, 사도행전 2장에서 부분적으로 성취되었지만 마지막 시대에 더 큰 결로 임할 것을 우리는 본다.",
        "쇠퇴가 아닌 추수의 시대가 짚어진다. 시대가 어두워질수록 그리스도인은 쇠퇴를 보지만, 성경은 그 어둠 한복판에서 추수의 약속을 가리킨다. 성령의 늦은 비, 모든 육체 위에 부어지는 성령, 꿈과 환상의 세대가 차례로 펼쳐진다.",
        "마지막 장 — 마라나타, 주여 오시옵소서. 추수꾼으로 부름받은 자의 마지막 외침이다. 두려움의 외침이 아니라 약속을 본 자의 외침. 마지막 시대의 부흥은 결국 그분의 다시 오심을 향한 추수의 결이다. 그 결로 시즌의 마지막 한 권이 닫힌다.",
    ],
}


# 권별 길잡이 — 그 한 권만의 좁고 깊은 화두 (부 길잡이와 차별)
BOOK_GUIDES = {
    1: [
        "성령님이 곁에 함께 계시는 보혜사라면, 나는 그 동행을 어떤 일상에서 살아내고 있는가.",
        "임재의 문을 연다는 것이, 내 어떤 결정과 어떤 호흡으로 살아나고 있는가.",
        "은사가 관계의 열매라는 한 마디 앞에서, 나는 무엇을 먼저 구하고 있는가.",
    ],
    2: [
        "마가의 다락방에서 일어난 임재가 오늘도 임하신다는 약속을, 나는 어떤 자리에서 받아들이고 있는가.",
        "오순절 방언이 자기 과시가 아니라 복음의 통로였다는 결을, 나는 어떻게 새기고 있는가.",
        "베드로의 첫 설교가 흘러나오기까지의 길을, 내 어떤 결단으로 따라가고 있는가.",
    ],
    3: [
        "참 방언과 거짓 방언의 분별을, 나는 어떤 결로 길러 가고 있는가.",
        "방언이 영적 자랑의 도구가 아니라 가장 정직한 기도의 자리라는 한 마디를, 내 기도는 어떻게 살아내고 있는가.",
        "한국교회 방언의 재해석이 가르치는 본질의 자리를, 나는 어떻게 새기고 있는가.",
    ],
    4: [
        "점술과 예언의 차이를, 나는 일상의 어떤 자리에서 분별하고 있는가.",
        "교회를 세우는 예언과 자기 권위를 세우는 예언의 차이를, 나는 어떻게 가려 듣고 있는가.",
        "하나님의 마음을 전하는 자의 자리에서, 나는 어떤 결의 책임을 받아들이고 있는가.",
    ],
    5: [
        "치유하시는 하나님이 신체적 치유와 영적 치유를 한 결로 다루신다면, 내 어떤 자리에서 그 결이 흐르고 있는가.",
        "야고보서의 치유 원리 — 장로들을 청하여 기도하라는 한 마디를, 내 공동체는 어떻게 살아내고 있는가.",
        "치유되지 않을 때 영혼의 치유가 더 깊은 자리라는 약속을, 나는 어디서 붙들고 있는가.",
    ],
    6: [
        "위로부터 오는 지혜와 인간의 똑똑함의 차이를, 나는 내 안에서 어떻게 분별하고 있는가.",
        "지혜의 근본인 여호와를 경외함이, 내 일상의 어떤 자리에서 살아나고 있는가.",
        "지혜가 결국 온유와 긍휼로 흐른다는 결을, 내 사람을 대하는 자세에서 살아내고 있는가.",
    ],
    7: [
        "모든 영이 하나님께 속한 것은 아니라는 한 마디 앞에서, 나는 어떤 영을 분별하고 있는가.",
        "분별하되 정죄하지 않는 자세를, 내 어떤 관계에서 살아내고 있는가.",
        "분별의 사람으로 살아간다는 것이, 내 일상의 어떤 결로 자라고 있는가.",
    ],
    8: [
        "성령충만이 일회적 경험이 아니라 매일 채워지는 결이라는 것을, 내 일상은 어떻게 살아내고 있는가.",
        "성령충만을 방해하는 것들 — 자기 의·죄·근심·불순종 가운데, 내 통로를 가장 막는 것은 무엇인가.",
        "매일의 영성 습관 — 말씀·기도·교제가, 내 어떤 자리에서 자라고 있는가.",
    ],
    9: [
        "포도나무에 붙어있으라는 한 마디 앞에서, 나는 열매를 만들려는 자리에서 붙어 있으려는 자리로 어떻게 옮겨 가고 있는가.",
        "사랑이 모든 열매의 뿌리라면, 내 일상의 어떤 자리에서 사랑이 가장 또렷이 흐르고 있는가.",
        "성령의 아홉 열매 가운데, 내 안에서 가장 자라야 할 결은 무엇인가.",
    ],
    10: [
        "쇠퇴가 아닌 추수의 시대라는 약속을, 나는 어떤 자리에서 받아들이고 있는가.",
        "모든 육체 위에 부어지는 성령의 약속이, 내 어떤 동역의 자리에서 살아나고 있는가.",
        "마라나타, 주여 오시옵소서의 외침을, 나는 두려움이 아니라 약속의 자리에서 어떻게 외치고 있는가.",
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
  <div style="color:#888;font-size:0.88em;margin-top:0.3em">원본 ISBN {b['isbn']} · G07 제 {b['src_no']:02d} 권</div>
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
<h3 style="color:#0F1E3C;margin-top:1.5em">바람과 불이 함께 흐르는 자리</h3>
<p>이로써 G07 열 권의 묵상이 한 권으로 닫힙니다. 성령님을 알아가는 시간에서 시작해 마지막 시대의 부흥에 이르기까지, 성령의 결을 네 갈래로 모아 함께 걸어왔습니다. 처음에는 흩어져 있던 한 권 한 권의 묵상이 한 호흡으로 이어 붙고 나니, 사이를 흐르고 있던 결이 비로소 또렷해졌습니다.</p>
<p>이 책이 묻고자 했던 한 가지 물음은 분명합니다. <em>바람과 불이 함께 임하시는 보혜사를, 한 영혼이 어떻게 만나고 동행할 것인가.</em> 보혜사를 만나는 자리와, 능력으로 임하시는 분을 응시하는 결과, 분별과 지혜로 영성을 빚는 자리와, 충만에서 부흥까지의 흐름 — 그 넷이 그 답의 네 갈래였습니다.</p>
<p><strong>1부에서 우리는 보혜사를 만났습니다</strong>. 임재의 문을 열고 거짓 자아 너머의 참 자아로 서는 자리, 말씀으로 조명하시는 분과 친구처럼 교제하는 자리, 그리고 마가의 다락방에서 시작된 임재가 오늘도 임하시는 결을 함께 보았습니다. 성령은 알게 되는 분이 아니라 만나는 분이라는 한 마디가 그 결의 핵심이었습니다.</p>
<p><strong>2부에서 우리는 능력으로 임하시는 분</strong>을 응시했습니다. 방언과 예언과 치유의 은사가 자기 자랑의 자리가 아니라 한 영혼을 향한 사랑의 결로 흐른다는 것을 함께 새겼습니다. 능력은 증언을 위한 것이며, 화려함이 아니라 한 사람을 살리는 결입니다.</p>
<p><strong>3부에서 우리는 분별과 지혜의 결</strong>에 도달했습니다. 위로부터 오는 지혜와 분별의 은사가 능력의 은사들을 길 잃지 않게 빚는다는 것을 함께 보았습니다. 지혜는 머리의 일이 아니라 영의 일이며, 분별은 똑똑함이 아니라 깨어 있음이라는 한 마디가 그 결의 토대였습니다.</p>
<p><strong>4부에서 우리는 충만에서 부흥까지</strong>의 흐름을 따라갔습니다. 일회적 경험이 아니라 매일 채워지는 충만의 결, 노력으로 만들지 않고 포도나무에 붙어 자연스럽게 맺히는 아홉 열매, 그리고 쇠퇴가 아닌 추수의 시대를 향해 걸어가는 마지막 부흥의 자리에 함께 섰습니다.</p>
<p>이 책의 가장 단단한 한 마디는 표제에 이미 담겨 있습니다 — <em>바람과 불.</em> 바람은 자유롭게 임하시는 분이고, 불은 한 자리에 머무시며 빚으시는 분입니다. 그 두 결이 함께 흐를 때 비로소 성령의 결이 또렷해집니다. 임하시는 자유와 머무시는 깊이가 한 영혼 안에 함께 있을 때, 우리의 영성이 비로소 살아납니다.</p>
<p>이 책을 덮으신 뒤에도 묵상은 끝나지 않습니다. 한 장씩 다시 펼쳐 읽어도 좋고, 한 단락만 천천히 반복해 읽어도 좋습니다. 성령을 추상으로만 다루던 자리에서 한 인격으로 만나는 자리로 한 결이라도 옮겨 가셨다면, 그것만으로도 G07 열 권을 한 권으로 묶은 이유는 충분할 것입니다.</p>
<p>이제 100권 시리즈는 G08로, G09로, 그리고 마지막 G10까지 흘러갑니다. 바람과 불이 함께 흐르는 자리의 결은 이 한 권에 모였습니다. 다음 그룹에서 또 다른 깊은 묵상으로 다시 만나기를 기도합니다. 주님의 평강이 여러분의 오늘 위에 충만히 임하시기를 축복합니다.</p>
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
    uuid_id = f"omnibus-g07-{today_compact}-{datetime.now().strftime('%H%M%S')}"

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
    <dc:description>{proj['subtitle']} — G07 10권 종합본</dc:description>
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
    print("ISBN 발급 시 batch_books_g07_omnibus.json의 isbn 필드에 입력 후 재빌드.")


if __name__ == "__main__":
    main()
