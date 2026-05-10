# -*- coding: utf-8 -*-
"""
G04 10권 종합책 "발자국과 눈물" epub 빌더.

입력:
  - batch_books_g04_omnibus.json (메타·4부 구조)
  - tmp/g04_omnibus_extracted.json (10권 본문 추출본)
  - G04 epub 중 한 권 (CSS 추출용)

출력:
  - ~/Downloads/전자책/발자국과_눈물_YYYYMMDD_종합책.epub

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
META_PATH = PROJECT / "batch_books_g04_omnibus.json"
EXTRACT_PATH = PROJECT / "tmp" / "g04_omnibus_extracted.json"
SAMPLE_EPUB = Path.home() / "Downloads" / "전자책" / "다윗의_눈물_20260418.epub"
OUT_DIR = Path.home() / "Downloads" / "전자책"
OUT_BACKUP_DIR = PROJECT / "tmp"  # 보조 사본


def get_css():
    """샘플 epub에서 CSS 추출."""
    with zipfile.ZipFile(SAMPLE_EPUB, "r") as z:
        return z.read("OEBPS/styles/style.css").decode("utf-8")


def get_cover_image():
    """전용 종합책 표지 사용 (없으면 샘플로 폴백)."""
    custom = PROJECT / "tmp" / "g04_omnibus_cover.jpg"
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
  <p><strong>구성</strong>　G04 10권 종합책 (4부 70장)</p>
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
    <p>이 책은 100권 영성 시리즈 G04(성경 인물) 10권의 본문을 거의 그대로 4부 구조로 재편집하여 한 권으로 묶은 종합본입니다.</p>
    <p>각 권의 원본 ISBN 및 출간 정보는 본문 권별 도입 페이지에 명기되어 있습니다.</p>
  </div>
</div></div>"""
    return xhtml_doc("판권", body)


def build_preface_xhtml() -> str:
    body = """<div style="padding:2em 1.5em;line-height:1.9;font-size:1em;color:#222">
<h2 style="color:#0F1E3C;border-bottom:1px solid #C8B99A;padding-bottom:0.5em">여는 글</h2>
<h3 style="color:#0F1E3C;margin-top:1.5em">그들도 사람이었다</h3>
<p>성경의 인물들은 박물관의 동상이 아닙니다. 그들도 우리와 같은 사람이었습니다. 두려워했고 도망쳤고 울었고 흔들렸고, 어떤 자리에서는 빛났고 어떤 자리에서는 그림자에 가려졌습니다. 그들의 발자국 위에 그들의 눈물이 함께 새겨져 있다는 사실이, 우리에게 가장 깊은 위로가 됩니다.</p>
<p>이 책은 그 발자국과 눈물을 차례로 따라 걷습니다. 광야로 내몰린 자, 가장 큰 결단의 자리에 선 자, 떠났다가 돌아온 자, 그리고 가장 높은 자리에서 흔들린 자. 열 명의 인물이 차례로 우리 앞에 나와, 자기 자리에서 한 영혼이 무엇과 마주했는가를 증언합니다.</p>
<p>이 책은 100권 영성 시리즈의 네 번째 그룹 G04를 한 권으로 묶은 종합본입니다. 모세에서 솔로몬까지, 다윗의 눈물에서 막달라 마리아의 사랑까지 — 성경 인물 열 명의 결을 네 갈래로 모았습니다. 열 권 각각의 본문을 거의 그대로 유지하면서, 그 사이를 흐르고 있던 결을 한 호흡으로 이어 붙였습니다.</p>
<p>네 갈래는 한 영혼이 통과할 수 있는 네 가지 자리입니다. <strong>1부 — 광야의 사람들</strong>은 모세·엘리야·욥처럼 연단의 시간을 통과한 자들의 발자국을 따라 걷고, <strong>2부 — 결단의 사람들</strong>은 에스더·룻·바울처럼 자기 자리를 결단한 자들의 응답을 봅니다. <strong>3부 — 눈물과 회개</strong>는 다윗·요나·막달라 마리아처럼 떠났다가 돌아온 자들의 눈물 위에 서고, <strong>4부 — 지혜와 그림자</strong>는 솔로몬이라는 한 인물 안에서 가장 높은 자리의 흔들림을 응시합니다.</p>
<p>이 책은 위인전이 아닙니다. 그들의 발자국을 칭송하기보다, 그들의 눈물을 정직하게 응시합니다. 그들이 위대했기 때문이 아니라, 그들이 우리와 같은 사람이었기 때문에 우리가 그들에게서 배웁니다. 영웅이 아닌 한 영혼의 자리에서 빛이 흘러나오는 그 결을 함께 따라가 보십시오.</p>
<p>한 번에 다 읽어내실 책이 아닙니다. 한 인물씩, 한 묵상씩 호흡을 따라 가져가시면 됩니다. 이제 첫 장을 펼쳐 주십시오. 그들의 발자국 위에 우리의 발걸음을 놓으면서, 그들의 눈물 옆에 우리의 마음을 두면서, 한 호흡씩 함께 걸어가 봅시다.</p>
</div>"""
    return xhtml_doc("여는 글", body)


PART_INTROS = {
    1: {
        "headline": "광야의 자리에서 빚어지는 영혼",
        "paragraphs": [
            "성경은 광야의 자리를 잘 알고 있습니다. 모세도, 엘리야도, 욥도 모두 광야의 시간을 통과했습니다. 어떤 광야는 지리적 공간이고, 어떤 광야는 마음의 자리이며, 어떤 광야는 두 가지가 동시에 닥친 자리이기도 합니다. 그 광야가 한 영혼을 빚습니다.",
            "광야는 외로움의 자리이지만 동시에 가장 또렷한 자리입니다. 사람의 소음이 줄어드는 자리에서 비로소 자기 영혼의 음성이 들리고, 그 음성 너머에서 하나님의 세미한 음성이 닿습니다. 도시의 혼잡함 속에서는 들리지 않던 결이 광야의 고요 속에서 비로소 들립니다.",
            "그러나 광야가 단순히 영적 휴양지인 것은 아닙니다. 광야는 무너짐의 자리이기도 합니다. 모세는 왕자의 자리에서 양 떼를 치는 자리로 떨어졌고, 엘리야는 갈멜산의 영웅에서 로뎀나무 아래의 도망자가 되었으며, 욥은 의인의 평온에서 재 위에 앉은 사람으로 내려왔습니다. 광야는 빚어지는 자리이면서 동시에 무너뜨려지는 자리입니다.",
            "그러나 그 무너짐의 자리에서 새 사람이 일어납니다. 모세는 떨기나무의 불꽃 앞에서 부르심을 받았고, 엘리야는 세미한 음성을 들었으며, 욥은 폭풍 가운데 임하신 하나님을 만났습니다. 광야의 자리에서만 가능한 만남이 있습니다.",
            "이 부의 세 권은 광야를 통과한 세 인물의 발자국을 따라갑니다. 「모세의 광야」는 왕자의 자리에서 부르심의 자리까지를, 「엘리야의 번아웃」은 영웅의 자리에서 다시 보내심의 자리까지를, 「욥의 질문」은 의인의 평온에서 폭풍 너머의 회복까지를 다룹니다.",
            "광야는 피해야 할 자리가 아니라 통과해야 할 자리입니다. 그 자리에서만 빚어지는 영혼의 결이 있다는 것을, 세 인물의 발자국 위에서 함께 발견해 보십시오.",
        ],
        "guides": [
            "내가 지금 통과하는 광야의 자리는 어디이며, 그 자리에서 들리는 세미한 음성은 무엇인가.",
            "무너짐의 자리에서 새 사람이 일어난다는 약속을, 나는 어떻게 붙들고 있는가.",
            "모세·엘리야·욥의 광야는 서로 다른 결이지만 한 결로 통합니다. 내 광야는 그 셋 중 어느 결과 가장 닮았는가.",
            "이 부를 읽으며, 광야가 어떻게 한 영혼을 빚는 자리가 되는가에 주목해 보십시오.",
        ],
    },
    2: {
        "headline": "자기 자리를 결단한 자들",
        "paragraphs": [
            "어떤 순간에는 결단이 필요합니다. 광야의 시간이 끝나고, 부르심의 음성이 들리고, 그 부르심에 응답해야 하는 자리에 한 영혼이 섭니다. 결단은 두려움 없이 일어나지 않습니다. 두려움 한복판에서 그 두려움보다 더 큰 한 마디로 응답하는 자세, 그것이 결단입니다.",
            "에스더는 죽으면 죽으리이다 한 마디로 자기 자리를 결단했습니다. 왕후의 자리는 안전한 자리였지만, 그 안전이 한 민족을 잃을 수 있다는 부르심 앞에서 그 안전을 내려놓았습니다. 이때를 위함이라는 모르드개의 한 마디가 그 결단의 자리에서 한 영혼을 빚었습니다.",
            "룻은 모압의 여인이었습니다. 시어머니 나오미를 따라 베들레헴으로 가는 결단은 단순한 가족 충성이 아니라, 자기 신을 떠나 한 분 하나님을 자기 신으로 받아들이는 결단이었습니다. 당신의 하나님이 나의 하나님이라는 한 마디 안에 그 결단의 무게가 다 담겨 있습니다.",
            "바울은 핍박자였습니다. 다메섹 도상의 빛 한 번이 그의 인생을 통째로 뒤집었습니다. 사흘의 어둠과 아나비아의 손 그리고 아라비아의 광야를 거쳐, 그는 누구나 바울이 될 수 있다는 한 마디를 자기 인생으로 증언했습니다. 가장 적대하던 자가 가장 헌신하는 자가 되는 결단의 자리가 거기 있습니다.",
            "이 부의 세 권은 결단의 세 결을 차례로 펼칩니다. 「에스더의 용기」는 안전을 내려놓는 결단을, 「룻의 충성」은 자기 신을 떠나는 결단을, 「바울의 변화」는 적대자가 헌신자가 되는 결단을 다룹니다.",
            "결단은 영웅의 자리가 아니라 한 영혼이 자기 자리를 정직하게 마주한 자리입니다. 그 결단의 무게를 함께 느껴 보십시오.",
        ],
        "guides": [
            "오늘 내게 던져진 결단의 자리는 무엇이며, 나는 그 자리에서 어떤 응답을 준비하고 있는가.",
            "에스더의 죽으면 죽으리이다와 같은 무게의 결단을, 내 일상은 어떤 자리에서 살아내고 있는가.",
            "당신의 하나님이 나의 하나님이라는 룻의 한 마디를, 나는 어디서 살아내고 있는가.",
            "이 부를 읽으며, 두려움 한복판에서의 결단이 어떻게 한 영혼을 빚는가에 주목해 보십시오.",
        ],
    },
    3: {
        "headline": "떠난 자가 돌아오는 길",
        "paragraphs": [
            "떠난다는 것은 인간의 보편적 경험입니다. 어떤 자리에서 떠나고, 어떤 약속에서 떠나고, 어떤 사랑에서 떠납니다. 그러나 성경은 떠남을 마지막 단어로 두지 않습니다. 떠난 자가 돌아오는 길이 있다는 것, 그것이 복음의 가장 깊은 결입니다.",
            "다윗은 하나님 마음에 합한 자였지만 그도 떠났습니다. 밧세바의 밤이 그의 떠남이었고, 나단의 손가락이 그의 돌아옴의 시작이었습니다. 시편 51편의 눈물은 떠난 자가 돌아오는 길에서 흘리는 가장 정직한 고백이며, 그 눈물 위에서 다시 그가 하나님 마음에 합한 자로 빚어졌습니다.",
            "요나는 더 노골적인 떠남이었습니다. 부르심의 반대 방향으로 배를 탔고, 바다의 폭풍 속에서야 멈췄으며, 물고기 배 속에서 비로소 무릎을 꿇었습니다. 두 번째 부르심은 첫 번째 부르심보다 더 깊은 자리에서 그를 일으켰습니다. 떠남이 없었다면 그 깊이는 없었을 것입니다.",
            "막달라 마리아는 떠남에서 사랑으로의 전환의 가장 아름다운 사례입니다. 일곱 귀신 들린 여인이 부활의 첫 증인이 되기까지의 거리는 측정할 수 없습니다. 많이 용서받은 자가 많이 사랑한다는 한 마디가 그녀의 인생을 한 단어로 요약합니다.",
            "이 부의 세 권은 떠남과 돌아옴의 세 결을 차례로 응시합니다. 「다윗의 눈물」은 떨어진 자가 무릎 꿇는 자리를, 「요나의 도망」은 도망친 자가 다시 보내짐을 받는 자리를, 「막달라 마리아의 사랑」은 용서받은 자의 헌신을 다룹니다.",
            "떠남이 끝이 아니라 돌아옴의 시작이라는 것을, 세 인물의 발자국과 눈물 위에서 함께 보십시오.",
        ],
        "guides": [
            "내가 떠나 있는 자리는 어디이며, 그 떠남에서 어떻게 돌아오고 있는가.",
            "다윗의 시편 51편 같은 눈물의 자리를, 나는 어떤 결로 살아내고 있는가.",
            "많이 용서받은 자가 많이 사랑한다는 한 마디를, 내 사랑은 어떻게 증언하고 있는가.",
            "이 부를 읽으며, 떠난 자가 돌아오는 길이 어떻게 새 사람으로 빚어지는가에 주목해 보십시오.",
        ],
    },
    4: {
        "headline": "가장 높은 자리의 그림자",
        "paragraphs": [
            "광야와 결단과 회개를 거쳐 온 자에게도 마지막 한 자리가 남아 있습니다. 가장 높은 자리, 가장 안정된 자리, 가장 빛나는 자리. 그 자리에서 한 영혼이 어떻게 흔들리는가의 결을, 우리는 솔로몬이라는 한 인물에게서 본다.",
            "솔로몬은 지혜를 구한 왕이었습니다. 어린 그가 권력 대신 지혜를 구한 한 마디가 하나님을 기쁘게 했고, 그 지혜는 그를 가장 높은 자리에 세웠습니다. 지혜의 절정에서 그의 영광은 시바 여왕의 방문이 증언할 만큼 빛났습니다.",
            "그러나 가장 높은 자리에서 작은 틈이 큰 균열이 됩니다. 마음을 빼앗긴 한 자리가 그를 흔들었고, 흔들리는 자리에서 그의 지혜는 점점 그림자에 가려졌습니다. 지혜자의 고백이 전도서로 남았지만, 그 고백 옆에는 찢어진 나라의 그림자가 함께 새겨져 있습니다.",
            "성경은 솔로몬의 이야기를 미화하지 않습니다. 그의 지혜와 그의 실패를 같은 무게로 증언합니다. 그것은 가장 높은 자리에 선 자에게 가장 큰 흔들림이 닥친다는 한 결을 우리에게 가르치기 위함입니다. 마음을 지키라는 한 마디가 그 결의 결론입니다.",
            "이 부의 한 권 「솔로몬의 지혜와 실패」는 그 결을 정면으로 응시합니다. 영광의 정점에서 그림자가 어떻게 시작되는가를, 그리고 그 그림자 한복판에서 우리가 무엇을 지켜야 하는가를 다룹니다.",
            "광야의 사람들과 결단의 사람들과 돌아온 자들의 발자국을 따라온 우리에게, 솔로몬은 마지막 경고이자 마지막 위로입니다. 가장 높은 자리에서도 흔들릴 수 있다는 경고와, 그러나 마음을 지키는 자는 끝까지 갈 수 있다는 위로가 그 한 인물 안에 함께 있습니다.",
        ],
        "guides": [
            "내 인생에서 가장 높은 자리는 어디이며, 그 자리에서 흔들리는 작은 틈은 무엇인가.",
            "마음을 빼앗긴 한 자리가 큰 균열이 된다는 한 마디를, 나는 일상의 어디서 분별하고 있는가.",
            "지혜자 솔로몬의 그림자가 내게 주는 경고와 위로는 무엇인가.",
            "이 부를 읽으며, 가장 높은 자리에서도 마음을 지키는 자세를 함께 새겨 보십시오.",
        ],
    },
}


# 권별 요약 (각 책 진입부 — 3단락, 약 70% 분량)
# 마지막 단락의 핵심 한 문장은 3번째 단락 끝에 흡수
BOOK_SUMMARIES = {
    1: [
        "왕자의 자리에서 양 떼를 치는 자리로. 모세의 인생은 한 마디로 광야의 인생이다. 첫 권은 그 광야의 결을 정면으로 응시한다. 그가 누렸던 권력과 안전이 한순간에 사라지고, 미디안의 우물가에서 새로 시작된 그의 인생은 양 떼를 치는 사십 년의 침묵이었다.",
        "그 침묵이 그를 빚었다. 이름 없는 자의 기도가 자라났고, 떨기나무의 불꽃 앞에 섰을 때 그는 이미 광야가 빚은 사람이 되어 있었다. 내가 누구이기에 — 라는 그의 질문은 자기 비하의 질문이 아니라, 광야가 가르친 진짜 겸손의 자리였다.",
        "마지막 장은 광야에서 광야로의 부르심이다. 미디안의 광야에서 출애굽의 광야로 옮겨진 그의 인생은, 광야가 끝나는 자리가 아니라 광야가 사역의 자리가 되는 결을 보여 준다. 모세의 광야는 한 영혼이 어떻게 빚어지는가에 대한 가장 깊은 증언이다.",
    ],
    2: [
        "갈멜산의 영웅이 로뎀나무 아래의 도망자가 되는 거리는 한 번의 위협이면 충분하다. 엘리야의 번아웃은 영웅의 자리에서 무너진 자가 어떻게 다시 일어서는가의 결을 보여 준다. 가장 큰 승리 직후에 가장 깊은 무너짐이 닥쳤다는 사실이 우리에게 위로다.",
        "로뎀나무 아래에서 그가 구한 것은 죽음이었다. 그러나 하나님은 그에게 죽음 대신 천사가 차려준 밥상을 주셨다. 영적 진단이 아니라 빵 한 덩이와 물 한 병이 먼저였다. 번아웃의 자리에 가장 먼저 닿는 은혜가 무엇인가를 이 한 권은 정직하게 가르친다.",
        "호렙산으로 가는 사십 일의 길과 세미한 음성, 그리고 다시 보내심이 차례로 펼쳐진다. 회복은 한 번의 큰 사건이 아니라 한 걸음씩의 결이다. 엘리야는 다시 일어났고, 다시 보내졌다. 번아웃이 마지막 단어가 아니라 다시 보내심의 시작이라는 한 마디가 이 책의 핵심이다.",
    ],
    3: [
        "의인의 고난이라는 가장 풀리지 않는 신학적 매듭을 욥은 자기 인생으로 풀어 간다. 재 위에 앉은 한 사람과 그를 둘러싼 친구들의 신학이 충돌하는 자리에서, 욥은 자기 항변을 멈추지 않는다. 그의 정직함이 거짓 위로보다 깊다는 것을 이 한 권은 보여 준다.",
        "친구들의 신학은 한결같이 단순하다. 네가 죄를 지었으니 고난이 왔다는 것이다. 그러나 욥은 자기를 굽히지 않는다. 자기 의를 주장하는 게 아니라, 자기가 모르는 것을 모른다고 정직하게 말한다. 그 정직함이 욥기의 가장 깊은 결이다.",
        "폭풍 가운데 임하신 하나님의 응답은 의외다. 고난의 이유를 설명하지 않으신다. 다만 그분의 광대함을 보이실 뿐이다. 그러나 욥은 그 자리에서 티끌과 재 가운데서 회개한다. 마지막 장은 고난 너머의 회복이다. 욥의 질문은 답을 받지 않았지만, 그 질문 자체가 한 영혼을 더 깊은 자리로 데려갔다.",
    ],
    4: [
        "왕후가 된 고아라는 한 마디 안에 에스더의 인생이 다 담겨 있다. 그녀는 자기 의지로 그 자리에 오른 게 아니었다. 그러나 모르드개의 한 마디 — 이때를 위함이라 — 가 그녀의 인생을 다시 정의했다.",
        "하만의 음모와 한 민족의 위기 앞에서 그녀가 던진 한 마디 — 죽으면 죽으리이다 — 는 단순한 영웅적 결단이 아니라, 자기 안전을 통째로 내려놓는 결단이었다. 왕후의 자리는 그녀에게 안전이었지만, 그 안전이 한 민족을 잃게 할 수 있다는 부르심 앞에서 그녀는 그 안전을 버렸다.",
        "금홀이 내밀어지는 자리는 결단의 무게가 응답으로 돌아오는 자리다. 부림의 기쁨은 그 결단 위에서 빚어졌다. 에스더의 용기는 결국 자기를 위한 용기가 아니라 다른 영혼들을 위한 용기였다. 그 결단의 자리가 어디인가를 이 한 권은 묻는다.",
    ],
    5: [
        "모압 땅에서 시작된 룻의 이야기는 눈물로 시작된다. 남편을 잃고 친정으로 돌아갈 것이냐, 시어머니를 따라 낯선 땅으로 갈 것이냐의 결단 앞에서 그녀가 던진 한 마디 — 당신의 하나님이 나의 하나님이라 — 가 그녀의 인생을 다시 정의했다.",
        "베들레헴에서 그녀가 한 일은 단순하다. 이삭을 줍는 자의 자리에 섰다. 가장 낮은 자리에서 가장 정직하게 일했고, 그 자리가 보아스의 그늘 아래로 그녀를 인도했다. 타작마당의 밤은 그녀의 결단의 자리이자 보아스의 결단의 자리였다.",
        "기업 무를 자의 구속이라는 신학적 결이 룻기 안에 흐른다. 그리고 마지막 장 — 다윗의 할머니 룻. 한 모압 여인이 다윗의 혈통이 되고 결국 예수의 족보에 들어가는 자리가 된다. 충성은 결국 한 영혼의 자리를 넘어 한 시대를 빚는다는 한 마디가 이 책의 결이다.",
    ],
    6: [
        "핍박자 사울에서 사도 바울로의 거리는 다메섹 도상의 빛 한 번이었다. 가장 적대하던 자가 가장 헌신하는 자가 되는 변화의 결을 이 한 권은 정면으로 응시한다. 사흘의 어둠과 아나니아의 손이 그를 다시 빚었다.",
        "아라비아의 광야에서의 시간이 짚어진다. 그가 곧바로 사역에 뛰어든 게 아니라 광야로 물러난 시간이 있었다. 모든 결단에는 광야의 시간이 필요하다는 것을 그도 보여 준다. 모세와 엘리야가 그러했듯이.",
        "과거를 안고 달린 사도라는 표현이 깊다. 그는 자기가 한때 핍박자였다는 사실을 잊지 않았다. 그 과거가 그의 사역을 더 깊게 만들었다. 마지막 장 — 누구나 바울이 될 수 있다. 그가 바울이 될 수 있었다면 누구나 그렇게 빚어질 수 있다는 약속이 이 책의 가장 단단한 한 자리다.",
    ],
    7: [
        "골리앗 앞에 선 소년이 결국 밧세바의 밤으로 떨어지는 거리는 한 번의 시선이면 충분했다. 다윗의 인생은 영광과 추락이 한 결로 짜인 직물이다. 그 가운데 가장 또렷한 결은 그의 눈물이다. 다윗은 떨어진 사람이지만, 무엇보다 회개한 사람이다.",
        "나단의 손가락이 그의 인생을 다시 빚었다. 당신이 그 사람이라는 한 마디 앞에서 그는 변명하지 않았다. 시편 51편의 눈물이 그 자리에서 흘러나왔다. 죄를 인정하는 정직함과 깊은 회개의 무게가 한 시편 안에 다 담겨 있다.",
        "아들 압살롬의 반역은 그의 인생에 드리운 가장 깊은 그림자였다. 그 그림자도 그의 회개의 일부였다. 그러나 마지막 장은 하나님 마음에 합한 자다. 떨어졌어도, 흔들렸어도, 그가 끝까지 회개의 자리에 섰기에 그분의 마음에 합한 자라는 평가를 받았다. 다윗의 눈물은 그 평가의 가장 정직한 증거다.",
    ],
    8: [
        "부르심의 음성을 받은 자가 다시스로 가는 배에 올랐다는 한 줄에 요나의 모든 결이 담겨 있다. 도망. 그것도 부르심의 정반대 방향으로의 도망. 그러나 하나님은 그를 놓지 않으셨다. 바다의 폭풍이 그의 도망을 멈추게 했다.",
        "물고기 배 속의 기도가 그의 첫 번째 무릎 꿇음이었다. 가장 어두운 자리에서 가장 또렷한 기도가 흘러나왔다. 두 번째 부르심은 첫 번째보다 더 깊은 자리에서 그를 일으켰다. 도망쳤던 자리가 더 깊은 부르심의 자리가 된 결이 거기 있다.",
        "니느웨의 회개는 의외였다. 그러나 박넝쿨 아래에서 화를 내는 요나의 모습은 더 의외다. 하나님은 그를 한 번 더 가르치셨다. 마지막 장 — 박넝쿨 아래에서. 요나는 자기가 누구를 위해 부르심을 받았는가를 그 자리에서 다시 배웠다. 도망이 마지막이 아니라 더 깊은 회복의 시작이라는 한 마디가 이 책의 결이다.",
    ],
    9: [
        "일곱 귀신 들린 여인. 막달라 마리아의 첫 모습은 그 한 마디로 요약된다. 그러나 주님을 만난 날, 그 한 사람의 인생이 통째로 다시 빚어졌다. 이 한 권은 사랑받음과 사랑함의 가장 깊은 결을 그녀에게서 본다.",
        "많이 용서받은 자의 사랑이라는 한 결이 그녀의 인생을 정의한다. 갈릴리에서 예루살렘까지 그분을 따른 발걸음, 십자가 아래 끝까지 선 여인, 그리고 부활의 첫 증인이 된 자리. 그 모든 자리가 한 결로 흐른다. 사랑받았기에 사랑한 결이다.",
        "마지막 장은 용서받은 자의 헌신이다. 그녀의 헌신은 의무에서 나온 것이 아니라 사랑에서 흘러나온 것이었다. 그래서 그 헌신은 가장 단단하면서도 가장 부드러웠다. 막달라 마리아는 한 영혼이 사랑받음의 자리에 깊이 들어갔을 때 어떤 사랑이 흘러나오는가를 보여 주는 가장 아름다운 증인이다.",
    ],
    10: [
        "지혜를 구한 왕. 어린 솔로몬의 그 한 결단이 하나님을 기쁘게 했고, 그를 가장 높은 자리에 세웠다. 이 한 권은 그 지혜의 절정과 그 절정의 그림자를 함께 응시한다. 솔로몬은 빛나는 자리와 흔들리는 자리를 모두 보여 주는 인물이다.",
        "지혜의 절정에서도 작은 틈이 큰 균열이 된다. 마음을 빼앗긴 한 자리, 그것이 그의 인생에 드리운 그림자의 시작이었다. 가장 지혜로운 자가 가장 어리석게 흔들릴 수 있다는 한 마디가 이 책의 가장 무거운 자리다.",
        "지혜자의 고백이 전도서로 남았다. 헛되고 헛되며 모든 것이 헛되다는 그 고백은, 그가 본 모든 영광이 결국 그림자였음을 증언한다. 마지막 장 — 마음을 지키라. 솔로몬이 우리에게 남긴 마지막 한 마디다. 가장 높은 자리에 선 자에게 가장 큰 흔들림이 닥친다는 경고와, 그러나 마음을 지키는 자는 끝까지 갈 수 있다는 위로가 그 한 마디 안에 함께 있다.",
    ],
}


# 권별 길잡이 — 그 한 권만의 좁고 깊은 화두 (부 길잡이와 차별)
BOOK_GUIDES = {
    1: [
        "왕자의 자리에서 내려와 양 떼를 치는 모세의 사십 년이, 내 인생의 어떤 자리에 닮아 있는가.",
        "이름 없는 자의 기도가 빚어지는 자리를, 나는 어떤 일상에서 살아내고 있는가.",
        "내가 누구이기에 — 라는 모세의 질문을 자기 비하가 아니라 진짜 겸손으로 살아내려면, 내게 무엇이 필요한가.",
    ],
    2: [
        "갈멜산의 영웅이 로뎀나무 아래의 도망자가 되는 거리가, 내 인생의 어떤 자리에서 일어나고 있는가.",
        "번아웃의 자리에 가장 먼저 닿는 은혜가 빵 한 덩이라면, 내 회복은 어디서 시작되어야 하는가.",
        "다시 보내심이라는 약속을, 내 무너진 자리는 어떻게 붙들고 있는가.",
    ],
    3: [
        "의인의 고난이라는 풀리지 않는 매듭 앞에서, 나는 욥처럼 정직하게 묻고 있는가 친구들처럼 거짓 위로를 주고 있는가.",
        "폭풍 가운데 임하시는 하나님이 답을 주지 않으시고 그분 자신을 보이실 때, 나는 그 자리에서 어떻게 응답하는가.",
        "티끌과 재 가운데서 회개한다는 욥의 자리가, 내 어떤 자리와 닮아 있는가.",
    ],
    4: [
        "이때를 위함이라는 한 마디가, 내 인생의 어떤 자리에 던져져 있는가.",
        "죽으면 죽으리이다 — 에스더의 결단의 무게를, 내 일상은 어떤 결로 살아내고 있는가.",
        "안전의 자리를 내려놓는 결단이, 내게 던져진 부르심 앞에서 어떻게 빚어지고 있는가.",
    ],
    5: [
        "당신의 하나님이 나의 하나님이라는 룻의 한 마디를, 나는 어디서 살아내고 있는가.",
        "이삭을 줍는 자의 자리에 선다는 것은, 내 일상의 어떤 결로 드러나는가.",
        "한 영혼의 충성이 한 시대를 빚는다는 약속이, 내 작은 자리에 어떻게 닿고 있는가.",
    ],
    6: [
        "다메섹 도상의 빛 같은 한 번의 만남이, 내 인생의 어떤 자리에서 일어났는가 또는 일어날 수 있는가.",
        "과거를 안고 달린 사도라는 표현이, 내 과거를 부정하지 않으면서도 어떻게 그 위에서 살아갈 수 있는지를 가르치는가.",
        "누구나 바울이 될 수 있다는 약속을, 내 옆의 한 영혼에게 어떻게 적용하고 있는가.",
    ],
    7: [
        "골리앗 앞에 선 소년이 밧세바의 밤으로 떨어지는 거리가, 내 인생의 어떤 자리와 닮아 있는가.",
        "나단의 손가락 같은 한 마디 앞에서, 나는 변명하지 않고 정직하게 무릎 꿇을 수 있는가.",
        "시편 51편 같은 눈물의 자리를, 내 회개는 어떤 결로 살아내고 있는가.",
    ],
    8: [
        "내가 도망친 부르심의 자리는 어디이며, 그 도망에서 어떻게 돌아오고 있는가.",
        "물고기 배 속의 기도 같은 가장 어두운 자리에서의 기도를, 나는 어떻게 살아내고 있는가.",
        "두 번째 부르심이 첫 번째보다 더 깊을 수 있다는 약속이, 내 인생의 어떤 자리에서 살아나고 있는가.",
    ],
    9: [
        "많이 용서받은 자가 많이 사랑한다는 한 마디를, 내 사랑은 어떻게 증언하고 있는가.",
        "십자가 아래 끝까지 선 여인의 자리가, 내 헌신의 어떤 결로 닿고 있는가.",
        "부활의 첫 증인이라는 자리가, 사랑받은 자의 헌신이 어떻게 가장 단단한 증언이 되는지를 어떻게 가르치는가.",
    ],
    10: [
        "지혜를 구한 왕의 어린 결단이, 내 일상의 어떤 결정에서 살아나고 있는가.",
        "마음을 빼앗긴 한 자리가 큰 균열이 된다는 솔로몬의 경고를, 나는 어디서 분별하고 있는가.",
        "마음을 지키라는 마지막 한 마디를, 내 인생의 어떤 자리에서 가장 또렷이 새기고 있는가.",
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
  <div style="color:#888;font-size:0.88em;margin-top:0.3em">원본 ISBN {b['isbn']} · G04 제 {b['src_no']:02d} 권</div>
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
<h3 style="color:#0F1E3C;margin-top:1.5em">그들의 발자국 위에 서서</h3>
<p>이로써 G04 열 권의 묵상이 한 권으로 닫힙니다. 모세의 광야에서 시작해 솔로몬의 그림자에 이르기까지, 성경 인물 열 명의 발자국과 눈물을 네 갈래로 모아 함께 걸어왔습니다. 처음에는 흩어져 있던 한 권 한 권의 묵상이 한 호흡으로 이어 붙고 나니, 사이를 흐르고 있던 결이 비로소 또렷해졌습니다.</p>
<p>이 책이 묻고자 했던 한 가지 물음은 분명합니다. <em>그들의 발자국 위에 우리의 발걸음을 어떻게 놓을 것인가.</em> 광야의 자리에서 빚어진 영혼들과, 자기 자리를 결단한 자들과, 떠났다가 돌아온 자들과, 가장 높은 자리에서 흔들린 자 — 그 넷이 그 답의 네 갈래였습니다.</p>
<p><strong>1부에서 우리는 광야의 사람들</strong>을 만났습니다. 모세는 왕자의 자리에서 양 떼의 자리로 내려왔고, 엘리야는 갈멜산의 영웅에서 로뎀나무 아래의 도망자가 되었으며, 욥은 의인의 평온에서 재 위에 앉은 자리로 떨어졌습니다. 그러나 그 광야의 자리에서 그들은 다시 빚어졌습니다. 떨기나무의 불꽃, 세미한 음성, 폭풍 가운데 임하신 하나님 — 광야는 무너짐의 자리이면서 동시에 만남의 자리였습니다.</p>
<p><strong>2부에서 우리는 결단의 사람들</strong>을 보았습니다. 에스더는 죽으면 죽으리이다라는 한 마디로 안전을 내려놓았고, 룻은 당신의 하나님이 나의 하나님이라는 한 마디로 자기 신을 떠났으며, 바울은 다메섹 도상의 빛 한 번으로 핍박자에서 사도가 되었습니다. 결단은 두려움 없이 일어나지 않습니다. 두려움 한복판에서 그 두려움보다 더 큰 한 마디로 응답하는 자세, 그것이 결단입니다.</p>
<p><strong>3부에서 우리는 떠난 자가 돌아오는 길</strong>을 함께 걸었습니다. 다윗은 밧세바의 밤에서 시편 51편의 눈물로 돌아왔고, 요나는 다시스로의 도망에서 두 번째 부르심으로 돌아왔으며, 막달라 마리아는 일곱 귀신의 자리에서 부활의 첫 증인의 자리로 옮겨졌습니다. 떠남이 마지막 단어가 아니라 돌아옴의 시작이라는 것이, 복음의 가장 깊은 결입니다.</p>
<p><strong>4부에서 우리는 가장 높은 자리의 그림자</strong>를 응시했습니다. 솔로몬은 지혜의 절정에서 작은 틈이 큰 균열이 되는 결을 살아냈습니다. 가장 높은 자리에서도 흔들릴 수 있다는 경고와, 그러나 마음을 지키는 자는 끝까지 갈 수 있다는 위로가 그 한 인물 안에 함께 있었습니다.</p>
<p>이 책의 가장 단단한 한 마디는 표제에 이미 담겨 있습니다 — <em>발자국과 눈물.</em> 그들이 위대했기 때문이 아니라, 그들이 우리와 같은 사람이었기 때문에 우리가 그들에게서 배웁니다. 발자국은 그들이 걸어간 길이고, 눈물은 그 길 위에 흘린 가장 정직한 흔적입니다. 그 둘을 함께 응시하는 자세에서, 우리의 다음 발걸음이 빚어집니다.</p>
<p>이 책을 덮으신 뒤에도 묵상은 끝나지 않습니다. 한 인물씩 다시 펼쳐 읽어도 좋고, 한 단락만 천천히 반복해 읽어도 좋습니다. 그들의 발자국 위에 한 걸음이라도 우리의 발걸음을 놓으셨다면, 그것만으로도 G04 열 권을 한 권으로 묶은 이유는 충분할 것입니다.</p>
<p>이제 100권 시리즈는 G05로, G06으로, 그리고 마지막 G10까지 흘러갑니다. 성경 인물의 발자국과 눈물이 어떻게 우리에게 닿는가의 결은 이 한 권에 모였습니다. 다음 그룹에서 또 다른 깊은 묵상으로 다시 만나기를 기도합니다. 주님의 평강이 여러분의 오늘 위에 충만히 임하시기를 축복합니다.</p>
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
    uuid_id = f"omnibus-g04-{today_compact}-{datetime.now().strftime('%H%M%S')}"

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
    <dc:description>{proj['subtitle']} — G04 10권 종합본</dc:description>
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
    print("ISBN 발급 시 batch_books_g04_omnibus.json의 isbn 필드에 입력 후 재빌드.")


if __name__ == "__main__":
    main()
