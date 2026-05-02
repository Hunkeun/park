# -*- coding: utf-8 -*-
"""
전자책 -> 유튜브 영상 제작·업로드 로봇 (시즌 1·2 지원).

시즌 1: 기존 10권 컬렉션(AI 시대 영성 상담사 등) — 종료 상태.
시즌 2: 100권 프로젝트. G01(1~10) 영계·사후세계 — 완료. G02(11~20) AI·디지털 시대 — 완료. G03(21~30) 단단한 믿음 — 완료. G04(31~40) 성경 인물 — 진행 중.

사용법
  python ebook_video_robot.py <권수>                     # 기본 = 현재 시즌(시즌 2). 권수 = 시즌 통산 num
  python ebook_video_robot.py <권수> --season 1          # 시즌 1 (하위호환)
  python ebook_video_robot.py <권수> --season 2          # 시즌 2
  python ebook_video_robot.py <권수> --step slides       # 슬라이드만
  python ebook_video_robot.py <권수> --step video        # 영상만
  python ebook_video_robot.py <권수> --step upload       # 업로드만 (검수 후)
  python ebook_video_robot.py list --season 2            # 시즌 진행 현황 (그룹별 헤더 + 그룹 내 회차)
  python ebook_video_robot.py list                       # 현재 시즌 진행 현황
  python ebook_video_robot.py playlist --season 2 --group G02  # G02 재생목록 생성/갱신
  python ebook_video_robot.py playlist --season 2 --group G03  # G03 재생목록 생성/갱신
  python ebook_video_robot.py playlist --season 2 --group G04  # G04 재생목록 생성/갱신

정책: 영상 생성은 자동, 업로드는 검수 후 수동 분리.

전제
  - ebook_content/book_NN.py (시즌 1) 또는 book_s2_NN.py (시즌 2) 에 BOOK / SLIDES / NARRATION 정의
  - tmp/bgm/meditation_impromptu_01.mp3 존재
  - client_secret_*.json (루트), youtube_token.json (최초 1회 브라우저 인증)

콘텐츠 작성 규칙 (반드시 준수)
  - SLIDES (화면 자막: title/caption/quote/subtitle): **아라비아 숫자** 사용
      예: "마태복음 5장 15절", "고린도후서 4장 17절"
  - NARRATION (TTS 입력): **한자어 한글**로 풀어 쓰기
      예: "마태복음 오장 십오절", "고린도후서 사장 십칠절"
  - 이유: edge-tts가 아라비아 숫자를 "포장 포틴절" 식으로 기계적으로 읽어 몰입을 깸
"""
import argparse
import asyncio
import importlib
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

import edge_tts
import imageio_ffmpeg
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build as gbuild
from googleapiclient.http import MediaFileUpload
from PIL import Image
from playwright.sync_api import sync_playwright

from qr_util import SITE_BASE, book_url, make_qr_png_bytes

BASE = os.path.dirname(os.path.abspath(__file__))

# ============================================================================
# 시즌 레지스트리
# ============================================================================
SERIES_NAME = "100권 영성 묵상 시리즈"
CHANNEL_NAME = "우주나-q3"
CURRENT_SEASON = 2  # 기본 시즌 (신규 작업은 모두 시즌 2)

SEASONS = {
    1: {
        "label": "시즌 1",
        "footer_label": "시즌 1",
        "meta_label": "시즌 1",
        "content_module": "ebook_content.book_{num:02d}",
        "content_file": os.path.join("ebook_content", "book_{num:02d}.py"),
        "tmp_dir": os.path.join("tmp", "book{num:02d}_video"),
        "voice_default": "ko-KR-InJoonNeural",
        "rate_default": "-10%",
        "tags_extra": [],
        "books": [
            {"num":  1, "title": "AI 시대 영성 상담사를 만나다"},
            {"num":  2, "title": "산을 옮길만한 믿음"},
            {"num":  3, "title": "아름다운 감성을 사모하자"},
            {"num":  4, "title": "다수의 횡포를 직관하라"},
            {"num":  5, "title": "새술은 새부대에 담아야"},
            {"num":  6, "title": "카이로스와 자유의지"},
            {"num":  7, "title": "진동 에너지와 치유"},
            {"num":  8, "title": "이스라엘 어느 왕의 덤 인생"},
            {"num":  9, "title": "죽음의 역설"},
            {"num": 10, "title": "이 세상과 저 세상"},
        ],
    },
    2: {
        "label": "시즌 2",
        "content_module": "ebook_content.book_s2_{num:02d}",
        "content_file": os.path.join("ebook_content", "book_s2_{num:02d}.py"),
        "tmp_dir": os.path.join("tmp", "s2_book{num:02d}_video"),
        "rate_default": "-10%",
        "groups": {
            "G01": {
                "label": "G01(영계·사후세계)",
                "footer_label": "시즌 2 · G01",
                "meta_label": "시즌 2 · G01(영계·사후세계)",
                "voice_default": "ko-KR-SunHiNeural",
                "tags_extra": ["사후세계", "천국", "영원", "영계", "부활"],
                "playlist_title": "천국과 영계",
                "playlist_description": "100권 영성 묵상 시리즈 G01 — 영계·사후세계 10권. 천국·부활·영혼·심판 등 사후세계 핵심 주제를 한 시즌으로 묶은 묵상 영상 모음.",
                "theme": {
                    "primary": "#1a1033",   # 짙은 인디고-플럼
                    "secondary": "#2d1f52", # 미드 바이올렛
                    "accent": "#d4af37",    # 골드 (시즌 1 공통, 채널 브랜드)
                    "ink": "#f0eaf7",       # 라벤더 아이보리
                    "muted": "#a696c2",     # 블루-퍼플 그레이
                },
            },
            "G02": {
                "label": "G02(AI·디지털 시대)",
                "footer_label": "시즌 2 · G02",
                "meta_label": "시즌 2 · G02(AI·디지털 시대)",
                "voice_default": "ko-KR-SunHiNeural",
                "tags_extra": ["AI", "디지털", "알고리즘", "트랜스휴머니즘", "메타버스"],
                "playlist_title": "알고리즘 시대의 영성",
                "playlist_description": "100권 영성 묵상 시리즈 G02 — AI·디지털 시대 10권. 알고리즘·빅데이터·트랜스휴머니즘·메타버스·로봇 시대를 신앙으로 묵상하는 영상 모음.",
                "theme": {
                    "primary": "#0a1929",   # 딥 사이버 블루
                    "secondary": "#1a2942", # 미드 사이버 블루
                    "accent": "#c0c5d0",    # 실버
                    "ink": "#e8eef5",       # 콜드 아이보리
                    "muted": "#7a8595",     # 사이버 그레이
                },
            },
            "G03": {
                "label": "G03(단단한 믿음)",
                "footer_label": "시즌 2 · G03",
                "meta_label": "시즌 2 · G03(단단한 믿음)",
                "voice_default": "ko-KR-SunHiNeural",
                "tags_extra": ["믿음", "겨자씨", "산", "의심", "기적", "행함"],
                "playlist_title": "겨자씨에서 산까지",
                "playlist_description": "100권 영성 묵상 시리즈 G03 — 단단한 믿음 10권. 의심·시험·기적·두려움·행함·마지막 때를 통과해 흔들리지 않는 믿음에 이르는 묵상 영상 모음.",
                "theme": {
                    "primary": "#0f2818",   # 딥 포레스트 그린
                    "secondary": "#1f3d2a", # 미드 모스 그린
                    "accent": "#d4af37",    # 골드 (채널 공통)
                    "ink": "#eef5ec",       # 옅은 그린-아이보리
                    "muted": "#8a9a8c",     # 그린-그레이
                },
            },
            "G04": {
                "label": "G04(성경 인물)",
                "footer_label": "시즌 2 · G04",
                "meta_label": "시즌 2 · G04(성경 인물)",
                "voice_default": "ko-KR-SunHiNeural",
                "tags_extra": ["성경인물", "발자국", "눈물", "다윗", "모세", "솔로몬", "회개"],
                "playlist_title": "발자국과 눈물",
                "playlist_description": "100권 영성 묵상 시리즈 G04 — 성경 인물 10권. 다윗·바울·에스더·욥·모세·엘리야·룻·요나·막달라 마리아·솔로몬, 열 사람의 발자국과 눈물을 따라 걷는 묵상 영상 모음.",
                "theme": {
                    "primary": "#2b1810",   # 딥 에스프레소
                    "secondary": "#4a2c1d", # 미드 시에나
                    "accent": "#d4af37",    # 골드 (채널 공통)
                    "ink": "#f5ebe0",       # 웜 아이보리
                    "muted": "#a89484",     # 어스 그레이
                },
            },
            "G05": {
                "label": "G05(내면 치유)",
                "footer_label": "시즌 2 · G05",
                "meta_label": "시즌 2 · G05(내면 치유)",
                "voice_default": "ko-KR-SunHiNeural",
                "tags_extra": ["내면치유", "상처", "회복", "트라우마", "용서", "감정", "치유"],
                "playlist_title": "흉터 위의 빛",
                "playlist_description": "100권 영성 묵상 시리즈 G05 — 내면 치유 10권. 상처·트라우마·몸의 기억·감정·분노·슬픔·번아웃·내면 아이·용서·관계의 상처, 흉터 위에 비추는 빛을 따라 걷는 묵상 영상 모음.",
                "theme": {
                    "primary": "#0d1f3c",   # 딥 네이비
                    "secondary": "#1f3559", # 미드 네이비
                    "accent": "#d4af37",    # 골드 (채널 공통)
                    "ink": "#e8eef7",       # 소프트 화이트
                    "muted": "#7a8aa6",     # 블루 그레이
                },
            },
            "G06": {
                "label": "G06(시대 분별)",
                "footer_label": "시즌 2 · G06",
                "meta_label": "시즌 2 · G06(시대 분별)",
                "voice_default": "ko-KR-SunHiNeural",
                "tags_extra": ["시대분별", "광야", "진실", "미디어", "정의", "예언자", "영적용기"],
                "playlist_title": "광야의 외침",
                "playlist_description": "100권 영성 묵상 시리즈 G06 — 시대 분별 10권. 진실·미디어·포퓰리즘·시민 책임·정의·세상의 기준·영적 용기·소수의 목소리·예언자적 상상력·거짓 평화, 광야에서 외치는 분별의 자리들을 따라 걷는 묵상 영상 모음.",
                "theme": {
                    "primary": "#2a1a0e",   # 딥 더스트 (사막 어둠)
                    "secondary": "#4a2f1a", # 사막 모래
                    "accent": "#d4af37",    # 골드 (채널 공통)
                    "ink": "#f4ebd9",       # 사막 아이보리
                    "muted": "#8a7864",     # 더스트 그레이
                },
            },
        },
        "books": [
            {"num":  1, "group": "G01", "title": "천국의 문턱에서"},
            {"num":  2, "group": "G01", "title": "부활의 증거들"},
            {"num":  3, "group": "G01", "title": "영혼은 어디로 가는가"},
            {"num":  4, "group": "G01", "title": "죽음 너머의 빛"},
            {"num":  5, "group": "G01", "title": "낙원과 지옥 사이"},
            {"num":  6, "group": "G01", "title": "영계의 언어"},
            {"num":  7, "group": "G01", "title": "몸과 영혼의 경계"},
            {"num":  8, "group": "G01", "title": "마지막 심판의 의미"},
            {"num":  9, "group": "G01", "title": "영원한 생명의 실체"},
            {"num": 10, "group": "G01", "title": "천사들의 사역"},
            {"num": 11, "group": "G02", "title": "AI가 묻는 신앙의 질문들"},
            {"num": 12, "group": "G02", "title": "AI와 함께 읽는 성경"},
            {"num": 13, "group": "G02", "title": "알고리즘과 섭리"},
            {"num": 14, "group": "G02", "title": "빅데이터가 모르는 것"},
            {"num": 15, "group": "G02", "title": "트랜스휴머니즘과 영혼"},
            {"num": 16, "group": "G02", "title": "디지털 시대의 기도"},
            {"num": 17, "group": "G02", "title": "메타버스 속의 예배"},
            {"num": 18, "group": "G02", "title": "로봇 시대의 인간 존엄"},
            {"num": 19, "group": "G02", "title": "AI 목사가 올 수 있는가"},
            {"num": 20, "group": "G02", "title": "디지털 선교의 미래"},
            {"num": 21, "group": "G03", "title": "의심을 넘어선 확신"},
            {"num": 22, "group": "G03", "title": "시험 속에서 자라는 믿음"},
            {"num": 23, "group": "G03", "title": "보이지 않는 것을 보는 눈"},
            {"num": 24, "group": "G03", "title": "기적은 지금도 일어난다"},
            {"num": 25, "group": "G03", "title": "믿음의 선배들"},
            {"num": 26, "group": "G03", "title": "작은 믿음의 큰 힘"},
            {"num": 27, "group": "G03", "title": "두려움 없는 믿음"},
            {"num": 28, "group": "G03", "title": "믿음과 행함의 균형"},
            {"num": 29, "group": "G03", "title": "마지막 때의 믿음"},
            {"num": 30, "group": "G03", "title": "흔들리지 않는 닻"},
            {"num": 31, "group": "G04", "title": "다윗의 눈물"},
            {"num": 32, "group": "G04", "title": "바울의 변화"},
            {"num": 33, "group": "G04", "title": "에스더의 용기"},
            {"num": 34, "group": "G04", "title": "욥의 질문"},
            {"num": 35, "group": "G04", "title": "모세의 광야"},
            {"num": 36, "group": "G04", "title": "엘리야의 번아웃"},
            {"num": 37, "group": "G04", "title": "룻의 충성"},
            {"num": 38, "group": "G04", "title": "요나의 도망"},
            {"num": 39, "group": "G04", "title": "막달라 마리아의 사랑"},
            {"num": 40, "group": "G04", "title": "솔로몬의 지혜와 실패"},
            {"num": 41, "group": "G05", "title": "상처받은 영혼의 회복"},
            {"num": 42, "group": "G05", "title": "트라우마와 은혜"},
            {"num": 43, "group": "G05", "title": "몸의 기억, 영혼의 치유"},
            {"num": 44, "group": "G05", "title": "감정의 신학"},
            {"num": 45, "group": "G05", "title": "분노를 다스리는 법"},
            {"num": 46, "group": "G05", "title": "슬픔도 선물이다"},
            {"num": 47, "group": "G05", "title": "번아웃에서 부활로"},
            {"num": 48, "group": "G05", "title": "내면 아이의 치유"},
            {"num": 49, "group": "G05", "title": "용서의 기적"},
            {"num": 50, "group": "G05", "title": "관계의 상처를 넘어서"},
            {"num": 51, "group": "G06", "title": "진실이 불편한 시대"},
            {"num": 52, "group": "G06", "title": "미디어와 영적 분별"},
            {"num": 53, "group": "G06", "title": "포퓰리즘의 유혹"},
            {"num": 54, "group": "G06", "title": "크리스천 시민의 책임"},
            {"num": 55, "group": "G06", "title": "정의란 무엇인가 - 성경적 답"},
            {"num": 56, "group": "G06", "title": "세상의 기준 vs 하나님의 기준"},
            {"num": 57, "group": "G06", "title": "영적 용기가 필요한 시대"},
            {"num": 58, "group": "G06", "title": "소수의 목소리"},
            {"num": 59, "group": "G06", "title": "예언자적 상상력"},
            {"num": 60, "group": "G06", "title": "거짓 평화에 속지 마라"},
        ],
    },
}

# ============================================================================
# 영상 파이프라인 공통 설정
# ============================================================================
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FADE = 0.8
TAIL = 0.6
ZOOM_PCT = 0.08
FPS = 30
BGM_VOLUME = 0.10       # -20dB

BGM_PATH = os.path.join(BASE, "tmp", "bgm", "meditation_impromptu_01.mp3")
CLIENT_SECRET = os.path.join(
    BASE,
    "client_secret_64838088503-skud9t64cq2bb173r9rrm61ob049o3vp.apps.googleusercontent.com.json",
)
TOKEN_FILE = os.path.join(BASE, "youtube_token.json")
SCOPES = ["https://www.googleapis.com/auth/youtube"]

TAGS_COMMON = ["영성묵상", "묵상영상", "기독교묵상", "100권시리즈", "우주나"]


# ============================================================================
# 경로/컨텐츠 로더
# ============================================================================
def season_cfg(season):
    if season not in SEASONS:
        print(f"[오류] 시즌 {season} 정의 없음. 사용 가능: {sorted(SEASONS.keys())}")
        sys.exit(1)
    return SEASONS[season]


def group_cfg(season, num):
    """num 권이 속한 그룹의 메타를 반환. 시즌에 groups가 없으면 시즌 cfg 그대로."""
    cfg = season_cfg(season)
    if "groups" not in cfg:
        return cfg
    book = cfg["books"][num - 1]
    grp = book.get("group")
    if not grp:
        return cfg
    return cfg["groups"][grp]


def group_books(season, num):
    """num 권과 같은 그룹의 books 리스트(시즌 통산 num 보존). 단일 그룹이면 전체."""
    cfg = season_cfg(season)
    if "groups" not in cfg:
        return cfg["books"]
    grp = cfg["books"][num - 1].get("group")
    if not grp:
        return cfg["books"]
    return [b for b in cfg["books"] if b.get("group") == grp]


def episode_no(season, num):
    """그룹 내 회차(1부터). 단일 그룹이면 num 그대로."""
    cfg = season_cfg(season)
    if "groups" not in cfg:
        return num
    grp = cfg["books"][num - 1].get("group")
    if not grp:
        return num
    count = 0
    for b in cfg["books"]:
        if b.get("group") == grp:
            count += 1
            if b["num"] == num:
                return count
    return num


def book_dir(season, num):
    return os.path.join(BASE, season_cfg(season)["tmp_dir"].format(num=num))

def book_slides_dir(season, num):
    return os.path.join(book_dir(season, num), "slides")

def book_final_mp4(season, num):
    return os.path.join(book_dir(season, num), "full.mp4")

def book_upload_info(season, num):
    return os.path.join(book_dir(season, num), "youtube_upload.txt")

def content_file(season, num):
    return os.path.join(BASE, season_cfg(season)["content_file"].format(num=num))


def load_content(season, num):
    cfg = season_cfg(season)
    mod_name = cfg["content_module"].format(num=num)
    try:
        mod = importlib.import_module(mod_name)
    except ModuleNotFoundError:
        print(f"[오류] 내용 파일 없음: {content_file(season, num)}")
        if season == 2:
            print(f"       ebook_content/book_s2_01.py 를 복사해 {num:02d}권 내용을 작성하세요.")
        else:
            print(f"       ebook_content/book_01.py 를 복사해 {num:02d}권 내용을 작성하세요.")
        sys.exit(1)
    for k in ("BOOK", "SLIDES", "NARRATION"):
        if not hasattr(mod, k):
            print(f"[오류] {mod_name} 에 {k} 정의가 없습니다.")
            sys.exit(1)
    if len(mod.SLIDES) != len(mod.NARRATION):
        print(f"[오류] SLIDES({len(mod.SLIDES)}) != NARRATION({len(mod.NARRATION)})")
        sys.exit(1)
    return mod


# ============================================================================
# 슬라이드 CSS (book01 디자인 시스템 원형 그대로)
# ============================================================================
CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Noto+Serif+KR:wght@300;400;600;700&family=Noto+Sans+KR:wght@300;400;600&display=swap');
:root {
  --primary: #0a192f;
  --secondary: #172a45;
  --accent: #d4af37;
  --accent-soft: rgba(212, 175, 55, 0.18);
  --ink: #e8ecf1;
  --muted: #9aa6b5;
}
html, body {
  width: 1920px; height: 1080px;
  background: var(--primary);
  color: var(--ink);
  font-family: 'Noto Serif KR', serif;
  overflow: hidden;
}
.slide {
  width: 1920px; height: 1080px;
  padding: 110px 140px;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background:
    radial-gradient(1100px 700px at 85% 15%, rgba(212,175,55,0.07), transparent 60%),
    radial-gradient(900px 600px at 10% 95%, rgba(23,42,69,0.9), transparent 70%),
    linear-gradient(135deg, #0a192f 0%, #172a45 100%);
}
.num-chip {
  display: inline-block;
  font-family: 'Noto Sans KR', sans-serif;
  font-size: 22px; letter-spacing: 6px; font-weight: 600;
  color: var(--accent);
  padding: 10px 22px;
  border: 1.5px solid var(--accent);
  border-radius: 4px;
  margin-bottom: 44px;
  width: fit-content;
}
h1.title {
  font-family: 'Noto Serif KR', serif;
  font-weight: 700;
  font-size: 88px;
  line-height: 1.18;
  letter-spacing: -2px;
  margin-bottom: 36px;
}
h2.sub {
  font-family: 'Noto Sans KR', sans-serif;
  font-weight: 300;
  font-size: 38px;
  color: var(--muted);
  letter-spacing: -0.5px;
  margin-bottom: 50px;
}
.gold { color: var(--accent); }
.rule {
  width: 120px; height: 3px; background: var(--accent);
  margin: 40px 0;
}
.footer {
  position: absolute; left: 140px; right: 140px; bottom: 60px;
  display: flex; justify-content: space-between;
  font-family: 'Noto Sans KR', sans-serif;
  font-size: 20px; color: var(--muted); letter-spacing: 2px;
}
.footer .brand { color: var(--accent); font-weight: 600; }

/* COVER */
.cover {
  align-items: center; text-align: center;
  background:
    radial-gradient(900px 900px at 50% 45%, rgba(212,175,55,0.12), transparent 65%),
    linear-gradient(180deg, #0a192f 0%, #050d1c 100%);
}
.cover .tag {
  font-family: 'Noto Sans KR', sans-serif;
  font-size: 22px; letter-spacing: 8px;
  color: var(--accent); font-weight: 600; text-transform: uppercase;
  margin-bottom: 70px;
}
.cover h1 {
  font-size: 130px; font-weight: 700; line-height: 1.08;
  letter-spacing: -3px; margin-bottom: 30px;
}
.cover h1 .accent { color: var(--accent); }
.cover .desc {
  font-family: 'Noto Sans KR', sans-serif;
  font-size: 32px; color: var(--muted);
  margin-top: 60px; font-weight: 300; letter-spacing: -0.5px;
}
.cover .stripe {
  width: 180px; height: 4px; background: var(--accent); margin-top: 80px;
}

/* SECTION (quote) */
.quote-big {
  font-size: 54px; line-height: 1.5; font-weight: 400;
  white-space: pre-line;
  padding-left: 40px;
  border-left: 6px solid var(--accent);
  margin-top: 30px;
}
.caption {
  font-family: 'Noto Sans KR', sans-serif;
  font-size: 28px; color: var(--muted); margin-top: 50px; font-weight: 300;
}

/* COMPARE */
.compare-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 60px;
  margin-top: 30px;
}
.compare-card {
  padding: 50px 55px;
  border: 1px solid rgba(212,175,55,0.25);
  background: rgba(212,175,55,0.04);
  border-radius: 8px;
}
.compare-card.right { background: rgba(212,175,55,0.10); border-color: var(--accent); }
.compare-card .label {
  font-family: 'Noto Sans KR', sans-serif;
  font-size: 26px; letter-spacing: 2px;
  color: var(--accent); font-weight: 600; margin-bottom: 30px;
}
.compare-card ul { list-style: none; }
.compare-card li {
  font-size: 30px; line-height: 1.5; padding: 14px 0;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.compare-card li:last-child { border-bottom: none; }

/* THREE CARDS */
.three-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 36px;
  margin-top: 30px;
}
.three-card {
  padding: 48px 40px;
  background: rgba(212,175,55,0.06);
  border-top: 3px solid var(--accent);
  border-radius: 6px;
  min-height: 320px;
}
.three-card h4 {
  font-size: 34px; color: var(--accent); font-weight: 700;
  margin-bottom: 24px; letter-spacing: -0.5px;
}
.three-card p {
  font-size: 26px; line-height: 1.6; color: var(--ink); font-weight: 300;
  font-family: 'Noto Sans KR', sans-serif;
}

/* FINALE */
.finale { align-items: center; text-align: center; }
.finale h1 { font-size: 80px; line-height: 1.25; white-space: pre-line; margin-bottom: 60px; }
.finale .quote-center {
  font-size: 42px; color: var(--accent); font-style: italic;
  line-height: 1.6; white-space: pre-line;
  max-width: 1500px;
}
.finale .cta {
  margin-top: 80px; font-family: 'Noto Sans KR', sans-serif;
  font-size: 24px; letter-spacing: 4px; color: var(--muted); font-weight: 600;
}
"""


# ============================================================================
# 렌더러
# ============================================================================
def _footer_html(season, book_title_footer, num):
    gcfg = group_cfg(season, num)
    series_footer = f"{SERIES_NAME} · {gcfg['footer_label']} · {episode_no(season, num)}편"
    return (
        f'<div class="footer"><span>{book_title_footer}</span>'
        f'<span class="brand">{series_footer}</span></div>'
    )


# ── 표지 배경 variation ────────────────────────────────────────────────
# 권별로 조금씩 다른 배경 구도·각도·빛 위치. `bg_variant` (slide 혹은 BOOK 필드)
# 로 지정하거나, 없으면 num(권 번호) 기반 자동 순환.
COVER_BG_VARIANTS = [
    # 0: 중앙-중심 은은한 골드 섬광
    "radial-gradient(900px 900px at 50% 45%, rgba(212,175,55,0.12), transparent 65%), "
    "linear-gradient(180deg, var(--primary) 0%, #050d1c 100%)",
    # 1: 좌상단 섬광 + 기울어진 그라데이션
    "radial-gradient(1000px 1000px at 25% 30%, rgba(212,175,55,0.15), transparent 65%), "
    "linear-gradient(160deg, var(--primary) 0%, var(--secondary) 100%)",
    # 2: 우상단 섬광
    "radial-gradient(900px 900px at 75% 30%, rgba(212,175,55,0.13), transparent 65%), "
    "linear-gradient(200deg, var(--primary) 0%, #050d1c 100%)",
    # 3: 아래쪽에서 피어오르는 광채
    "radial-gradient(1200px 700px at 50% 85%, rgba(212,175,55,0.14), transparent 60%), "
    "linear-gradient(175deg, var(--secondary) 0%, var(--primary) 100%)",
    # 4: 좁은 세로 기둥 형태의 빛
    "radial-gradient(600px 1400px at 50% 50%, rgba(212,175,55,0.13), transparent 65%), "
    "linear-gradient(180deg, var(--primary) 0%, #050d1c 100%)",
    # 5: 좌하단 광채 + 역방향 그라데이션
    "radial-gradient(1000px 1000px at 30% 80%, rgba(212,175,55,0.15), transparent 65%), "
    "linear-gradient(220deg, var(--primary) 0%, var(--secondary) 100%)",
    # 6: 우하단 광채
    "radial-gradient(1000px 1000px at 70% 80%, rgba(212,175,55,0.15), transparent 65%), "
    "linear-gradient(140deg, var(--primary) 0%, var(--secondary) 100%)",
    # 7: 중앙에서 넓게 퍼지는 헤일로
    "radial-gradient(1400px 1400px at 50% 50%, rgba(212,175,55,0.16), transparent 70%), "
    "linear-gradient(180deg, var(--primary) 0%, #050d1c 100%)",
    # 8: 대각선 이중 광채 (좌상 + 우하)
    "radial-gradient(700px 700px at 25% 25%, rgba(212,175,55,0.14), transparent 65%), "
    "radial-gradient(700px 700px at 75% 75%, rgba(212,175,55,0.11), transparent 65%), "
    "linear-gradient(180deg, var(--primary) 0%, var(--secondary) 100%)",
    # 9: 위에서 쏟아지는 빛 폭포
    "radial-gradient(1500px 700px at 50% 0%, rgba(212,175,55,0.20), transparent 60%), "
    "linear-gradient(180deg, var(--primary) 0%, #050d1c 100%)",
]


def render_cover(s, footer, num=1, season=2):
    idx = s.get("bg_variant")
    if idx is None:
        idx = (num - 1) % len(COVER_BG_VARIANTS)
    bg = COVER_BG_VARIANTS[idx % len(COVER_BG_VARIANTS)]
    qr_src = _qr_data_url(season, num)
    return f"""
    <div class="slide cover" style="background: {bg};">
      <div class="tag">{s['tag']}</div>
      <h1>{s['title_main']}<br><span class="accent">{s['title_accent']}</span>{s['title_sub']}</h1>
      <div class="stripe"></div>
      <div class="desc">{s['desc']}</div>
      <div class="qr-block" style="position:absolute;bottom:7vh;right:5vw;text-align:center;background:rgba(255,255,255,0.96);padding:1.4vh 1.6vh 1vh;border-radius:1.2vh;box-shadow:0 0.6vh 2vh rgba(0,0,0,0.18)">
        <img src="{qr_src}" alt="책방 QR" style="width:14vh;height:14vh;display:block"/>
        <div style="margin-top:0.6vh;color:#0F1E3C;font-size:1.5vh;font-weight:700;letter-spacing:0.05em">AI 시대 책방</div>
        <div style="color:#666;font-size:1.2vh">스캔 → 이 책 바로가기</div>
      </div>
    </div>"""


def render_section(s, footer):
    return f"""
    <div class="slide">
      <span class="num-chip">{s['num']}</span>
      <h1 class="title">{s['title']}</h1>
      <div class="rule"></div>
      <div class="quote-big">{s['quote']}</div>
      <div class="caption">{s['caption']}</div>
      {footer}
    </div>"""


def render_compare(s, footer):
    def ul(items):
        return "".join(f"<li>{i}</li>" for i in items)
    return f"""
    <div class="slide">
      <span class="num-chip">{s['num']}</span>
      <h1 class="title">{s['title']}</h1>
      <h2 class="sub">{s['subtitle']}</h2>
      <div class="compare-grid">
        <div class="compare-card"><div class="label">{s['left_label']}</div><ul>{ul(s['left_items'])}</ul></div>
        <div class="compare-card right"><div class="label">{s['right_label']}</div><ul>{ul(s['right_items'])}</ul></div>
      </div>
      {footer}
    </div>"""


def render_three(s, footer):
    cards = "".join(
        f'<div class="three-card"><h4>{t}</h4><p>{d}</p></div>'
        for t, d in s["items"]
    )
    return f"""
    <div class="slide">
      <span class="num-chip">{s['num']}</span>
      <h1 class="title">{s['title']}</h1>
      <div class="rule"></div>
      <div class="three-grid">{cards}</div>
      {footer}
    </div>"""


def _book_id(season, num):
    return f"s{season}-{num:03d}" if season == 2 else f"s{season}-{num:02d}"


def _qr_data_url(season, num):
    """finale 슬라이드용 QR (책방 직링크) base64 data URL."""
    import base64

    url = book_url(_book_id(season, num))
    png = make_qr_png_bytes(url, box_size=10, border=2)
    b64 = base64.b64encode(png).decode("ascii")
    return f"data:image/png;base64,{b64}"


def render_finale(s, footer, season=2, num=1):
    qr_src = _qr_data_url(season, num)
    return f"""
    <div class="slide finale">
      <span class="num-chip">{s['num']}</span>
      <h1>{s['title']}</h1>
      <div class="quote-center">"{s['quote']}"</div>
      <div class="cta">{s['cta']}</div>
      <div class="qr-block" style="position:absolute;bottom:7vh;right:5vw;text-align:center;background:rgba(255,255,255,0.96);padding:1.4vh 1.6vh 1vh;border-radius:1.2vh;box-shadow:0 0.6vh 2vh rgba(0,0,0,0.18)">
        <img src="{qr_src}" alt="책방 QR" style="width:14vh;height:14vh;display:block"/>
        <div style="margin-top:0.6vh;color:#0F1E3C;font-size:1.5vh;font-weight:700;letter-spacing:0.05em">AI 시대 책방</div>
        <div style="color:#666;font-size:1.2vh">스캔 → 이 책 바로가기</div>
      </div>
    </div>"""


RENDERERS = {
    "cover": render_cover,
    "section": render_section,
    "compare": render_compare,
    "three": render_three,
    "finale": render_finale,
}


def _theme_override(theme):
    """시즌별 theme을 CSS :root 변수로 주입. None이면 기본(시즌 1) 색상 유지."""
    if not theme:
        return ""
    lines = "\n".join(f"  --{k}: {v};" for k, v in theme.items())
    return f"\n:root {{\n{lines}\n}}\n"


def _build_html(slide, footer, theme=None, num=1, season=2):
    kind = slide["kind"]
    if kind == "cover":
        body = render_cover(slide, footer, num, season)
    elif kind == "finale":
        body = render_finale(slide, footer, season, num)
    else:
        body = RENDERERS[kind](slide, footer)
    style = CSS + _theme_override(theme)
    return (
        '<!doctype html>\n'
        '<html lang="ko"><head><meta charset="utf-8"><style>' + style + '</style></head>'
        f"<body>{body}</body></html>"
    )


# ============================================================================
# STEP 1: 슬라이드 렌더
# ============================================================================
def step_slides(season, num, content):
    cfg = season_cfg(season)
    gcfg = group_cfg(season, num)
    out_dir = book_slides_dir(season, num)
    os.makedirs(out_dir, exist_ok=True)
    book = content.BOOK
    slides = content.SLIDES
    theme = gcfg.get("theme")
    footer_left = (
        book.get("footer_left")
        or book.get("title_short")
        or cfg["books"][num - 1]["title"]
    )
    footer = _footer_html(season, footer_left, num)

    print(f"== 슬라이드 {len(slides)}장 렌더 ==")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        for idx, s in enumerate(slides, start=1):
            html = _build_html(s, footer, theme, num, season)
            page.set_content(html, wait_until="networkidle")
            out = os.path.join(out_dir, f"slide_{idx:02d}_{s['kind']}.png")
            page.screenshot(
                path=out,
                full_page=False,
                clip={"x": 0, "y": 0, "width": 1920, "height": 1080},
            )
            print(f"  [완료] {idx:02d}/{len(slides)} -> {os.path.basename(out)}")
        browser.close()
    print(f"[슬라이드 완료] {out_dir}")


# ============================================================================
# STEP 2: TTS + Ken Burns + 크로스페이드 + BGM = 영상
# ============================================================================
async def _gen_tts(text, mp3, voice, rate):
    if os.path.exists(mp3) and os.path.getsize(mp3) > 0:
        return
    comm = edge_tts.Communicate(text, voice=voice, rate=rate)
    await comm.save(mp3)


def _probe_duration(path):
    r = subprocess.run(
        [FFMPEG, "-i", path, "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="ignore",
    )
    for line in r.stderr.splitlines():
        if "Duration:" in line:
            d = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = d.split(":")
            return float(h) * 3600 + float(m) * 60 + float(s)
    raise RuntimeError(f"duration probe failed: {path}")


def _make_clip(slide_png, out_mp4, duration):
    total = int(duration * FPS)
    zexpr = f"'min(zoom+{ZOOM_PCT/total:.6f},{1.0+ZOOM_PCT})'"
    vf = (
        f"scale=5000:-2,"
        f"zoompan=z={zexpr}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={total}:s=1920x1080:fps={FPS}"
    )
    cmd = [
        FFMPEG, "-y",
        "-loop", "1", "-i", slide_png,
        "-t", f"{duration:.3f}",
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "veryfast", "-crf", "20",
        "-an", out_mp4,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0:
        print(r.stderr[-800:])
        raise RuntimeError(f"clip build failed: {slide_png}")


def _concat_xfade(info, out_mp4):
    n = len(info)
    inputs = []
    for it in info:
        inputs += ["-i", it["clip"]]
    for it in info:
        inputs += ["-i", it["mp3"]]

    filters = []
    cum = 0.0
    cur = "[0:v]"
    for i in range(1, n):
        cum += info[i - 1]["duration"] - FADE
        nxt = f"[v{i}]"
        filters.append(
            f"{cur}[{i}:v]xfade=transition=fade:duration={FADE}:offset={cum:.3f}{nxt}"
        )
        cur = nxt
    v_out = cur

    a_cum = 0.0
    a_parts = []
    for i in range(n):
        idx = n + i
        ms = int(a_cum * 1000)
        lbl = f"[a{i}]"
        filters.append(f"[{idx}:a]adelay={ms}|{ms}{lbl}")
        a_parts.append(lbl)
        a_cum += info[i]["duration"] - FADE
    filters.append("".join(a_parts) + f"amix=inputs={n}:normalize=0[aout]")

    total = sum(it["duration"] for it in info) - FADE * (n - 1)
    cmd = [
        FFMPEG, "-y", *inputs,
        "-filter_complex", ";".join(filters),
        "-map", v_out, "-map", "[aout]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{total:.3f}", out_mp4,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0:
        print(r.stderr[-1500:])
        raise RuntimeError("xfade concat failed")
    return total


def _mix_bgm(video, bgm, out, dur):
    fc = (
        f"[1:a]aloop=loop=-1:size=2e9,atrim=0:{dur:.3f},volume={BGM_VOLUME}[bgm];"
        f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0,"
        f"afade=t=in:st=0:d=2,afade=t=out:st={dur-2:.3f}:d=2[aout]"
    )
    cmd = [
        FFMPEG, "-y",
        "-i", video, "-i", bgm,
        "-filter_complex", fc,
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest", out,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0:
        print(r.stderr[-1500:])
        raise RuntimeError("bgm mix failed")


def step_video(season, num, content):
    cfg = season_cfg(season)
    slides_d = book_slides_dir(season, num)
    if not os.path.isdir(slides_d) or not os.listdir(slides_d):
        print(f"[오류] 슬라이드 없음 — 먼저 --step slides 실행: {slides_d}")
        sys.exit(1)
    if not os.path.exists(BGM_PATH):
        print(f"[오류] BGM 없음: {BGM_PATH}")
        sys.exit(1)

    out_dir = book_dir(season, num)
    os.makedirs(out_dir, exist_ok=True)
    book = content.BOOK
    gcfg = group_cfg(season, num)
    voice = book.get("tts_voice", gcfg["voice_default"])
    rate = book.get("tts_rate", cfg["rate_default"])
    n = len(content.SLIDES)

    print(f"== 1. TTS {n}장 ({voice}, rate {rate}) ==")
    info = []
    for i, (slide, text) in enumerate(zip(content.SLIDES, content.NARRATION), start=1):
        base = f"slide_{i:02d}_{slide['kind']}"
        mp3 = os.path.join(out_dir, f"{base}.mp3")
        print(f"  [TTS] {base}  ({len(text)}자)")
        asyncio.run(_gen_tts(text, mp3, voice, rate))
        dur = _probe_duration(mp3) + TAIL
        info.append({"slide": f"{base}.png", "mp3": mp3, "duration": round(dur, 3)})

    print(f"\n== 2. Ken Burns 클립 {n}개 ==")
    for i, it in enumerate(info):
        clip = os.path.join(out_dir, f"clip_{i:02d}.mp4")
        png = os.path.join(slides_d, it["slide"])
        print(f"  [{it['duration']:5.2f}s] {it['slide']}")
        _make_clip(png, clip, it["duration"])
        it["clip"] = clip

    xfade = os.path.join(out_dir, "_xfade.mp4")
    print(f"\n== 3. 크로스페이드 합성 ==")
    total = _concat_xfade(info, xfade)
    final = book_final_mp4(season, num)
    print(f"\n== 4. BGM 믹스 ==")
    _mix_bgm(xfade, BGM_PATH, final, total)
    size_mb = os.path.getsize(final) / 1024 / 1024
    print(f"\n[영상 완료] {final}")
    print(f"  {total:.1f}초 ({total/60:.1f}분), {size_mb:.1f}MB")


# ============================================================================
# STEP 3: 유튜브 업로드
# ============================================================================
def _get_yt():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        refreshed = False
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                refreshed = True
            except Exception as e:
                print(f"[알림] 토큰 자동 갱신 실패({e}). 브라우저로 재인증합니다.")
        if not refreshed:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return gbuild("youtube", "v3", credentials=creds)


def _chapter_title(slide):
    if "chapter_title" in slide:
        return slide["chapter_title"]
    k = slide["kind"]
    if k == "cover":
        return "표지"
    if k == "finale":
        return "마무리"
    return slide.get("title", "")


def _build_chapters(season, num, content):
    cum = 0.0
    lines = []
    for i, slide in enumerate(content.SLIDES, start=1):
        mm = int(cum // 60)
        ss = int(cum % 60)
        lines.append(f"{mm:02d}:{ss:02d} {_chapter_title(slide)}")
        mp3 = os.path.join(book_dir(season, num), f"slide_{i:02d}_{slide['kind']}.mp3")
        dur = _probe_duration(mp3) + TAIL
        cum += dur - FADE
    return "\n".join(lines)


def _make_thumb(slide_png):
    out = slide_png.rsplit(".", 1)[0] + "_thumb.jpg"
    img = Image.open(slide_png).convert("RGB")
    img.thumbnail((1280, 720), Image.LANCZOS)
    img.save(out, "JPEG", quality=88)
    return out


def _compose_description(season, num, content, chapters):
    cfg = season_cfg(season)
    gcfg = group_cfg(season, num)
    book = content.BOOK
    n = len(content.SLIDES)
    title = cfg["books"][num - 1]["title"]
    intro = book.get("description_intro", "")
    hashtags = book.get("hashtags", "#영성묵상 #100권시리즈 #우주나")

    cur_grp = cfg["books"][num - 1].get("group")
    ep = episode_no(season, num)

    prev_hint = ""
    next_hint = ""
    if num > 1 and cfg["books"][num - 2].get("group") == cur_grp:
        prev_hint = f"\n▶ 이전 회\n{gcfg['footer_label']} · {ep-1}편 — {cfg['books'][num-2]['title']}\n"
    if num < len(cfg["books"]) and cfg["books"][num].get("group") == cur_grp:
        next_hint = f"\n▶ 다음 회 예고\n{gcfg['footer_label']} · {ep+1}편 — {cfg['books'][num]['title']}\n"

    return (
        f"{intro}\n\n"
        f"이 영상은 동명의 전자책 '{title}'을 {n}장의 묵상으로 정리한\n"
        f"'{SERIES_NAME}' {gcfg['meta_label']} · {ep}편입니다.\n\n"
        f"▶ 챕터\n{chapters}\n"
        f"{prev_hint}{next_hint}\n"
        f"▶ Music\n"
        f"\"Meditation Impromptu 01\" by Kevin MacLeod (incompetech.com)\n"
        f"Licensed under Creative Commons: By Attribution 4.0\n"
        f"https://creativecommons.org/licenses/by/4.0/\n\n"
        f"{hashtags}\n"
    )


def step_upload(season, num, content):
    cfg = season_cfg(season)
    final = book_final_mp4(season, num)
    if not os.path.exists(final):
        print(f"[오류] 영상 없음 — 먼저 --step video 실행: {final}")
        sys.exit(1)

    chapters = _build_chapters(season, num, content)
    print("[챕터 타임스탬프]")
    print(chapters)
    print()

    book = content.BOOK
    gcfg = group_cfg(season, num)
    ep = episode_no(season, num)
    title_fallback = f"{cfg['books'][num-1]['title']} | {SERIES_NAME} · {gcfg['footer_label']} · {ep}편"
    title = book.get("title_long") or title_fallback
    description = _compose_description(season, num, content, chapters)
    tags = TAGS_COMMON + list(gcfg.get("tags_extra", [])) + list(book.get("tags_extra", []))
    privacy = book.get("privacy", "public")

    yt = _get_yt()
    cover_png = os.path.join(book_slides_dir(season, num), "slide_01_cover.png")
    thumb = _make_thumb(cover_png)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "27",
            "defaultLanguage": "ko",
            "defaultAudioLanguage": "ko",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(final, chunksize=-1, resumable=True, mimetype="video/mp4")
    print(f"[업로드 시작] {final}")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"  {int(status.progress() * 100)}% 업로드됨...")

    vid = resp["id"]
    yt.thumbnails().set(
        videoId=vid,
        media_body=MediaFileUpload(thumb, mimetype="image/jpeg"),
    ).execute()

    url = f"https://youtu.be/{vid}"
    print(f"\n[완료] {url}")
    print(f"  공개범위: {privacy} / 채널: {CHANNEL_NAME}")

    with open(book_upload_info(season, num), "w", encoding="utf-8") as f:
        f.write(f"video_id: {vid}\nurl: {url}\nprivacy: {privacy}\n")
    return url


# ============================================================================
# STEP 4: 재생목록 (시즌 단위)
# ============================================================================
def playlist_state_file(season, group=None):
    if group:
        path = os.path.join(BASE, "tmp", f"season{season}_{group.lower()}_playlist.txt")
        legacy = os.path.join(BASE, "tmp", f"season{season}_playlist.txt")
        if group == "G01" and not os.path.exists(path) and os.path.exists(legacy):
            return legacy
        return path
    return os.path.join(BASE, "tmp", f"season{season}_playlist.txt")


def _read_video_id(season, num):
    info = book_upload_info(season, num)
    if not os.path.exists(info):
        return None
    with open(info, encoding="utf-8") as f:
        for line in f:
            if line.startswith("video_id:"):
                return line.split("video_id:", 1)[1].strip()
    return None


def step_playlist(season, group=None):
    cfg = season_cfg(season)
    if "groups" in cfg:
        if not group:
            print(f"[오류] 시즌 {season}는 그룹 구조입니다. --group G01|G02|G03|G04 인자를 지정하세요.")
            sys.exit(1)
        gmeta = cfg["groups"].get(group)
        if not gmeta:
            print(f"[오류] 시즌 {season}에 그룹 {group} 정의 없음. 사용 가능: {sorted(cfg['groups'].keys())}")
            sys.exit(1)
        pl_title = gmeta.get("playlist_title")
        pl_desc = gmeta.get("playlist_description", "")
        books = [b for b in cfg["books"] if b.get("group") == group]
    else:
        pl_title = cfg.get("playlist_title")
        pl_desc = cfg.get("playlist_description", "")
        books = cfg["books"]

    if not pl_title:
        print(f"[오류] playlist_title이 정의되어 있지 않습니다.")
        sys.exit(1)

    items = []
    missing = []
    for b in books:
        n = b["num"]
        vid = _read_video_id(season, n)
        if vid:
            items.append((n, b["title"], vid))
        else:
            missing.append((n, b["title"]))

    if missing:
        print(f"[알림] 업로드되지 않은 권 {len(missing)}개:")
        for n, t in missing:
            print(f"  {n:2d}. {t}")
        if not items:
            print("[중단] 추가할 영상이 없습니다.")
            return
        print(f"[계속] 업로드된 {len(items)}편만 재생목록에 추가합니다.\n")

    yt = _get_yt()

    state = playlist_state_file(season, group)
    pl_id = None
    if os.path.exists(state):
        with open(state, encoding="utf-8") as f:
            for line in f:
                if line.startswith("playlist_id:"):
                    pl_id = line.split("playlist_id:", 1)[1].strip()
                    break

    just_created = False
    if not pl_id:
        print(f"[재생목록 생성] {pl_title}")
        body = {
            "snippet": {
                "title": pl_title,
                "description": pl_desc,
                "defaultLanguage": "ko",
            },
            "status": {"privacyStatus": "public"},
        }
        resp = yt.playlists().insert(part="snippet,status", body=body).execute()
        pl_id = resp["id"]
        os.makedirs(os.path.dirname(state), exist_ok=True)
        with open(state, "w", encoding="utf-8") as f:
            f.write(f"playlist_id: {pl_id}\ntitle: {pl_title}\n")
        print(f"  생성됨: https://www.youtube.com/playlist?list={pl_id}\n")
        just_created = True
    else:
        print(f"[재생목록 재사용] {pl_id}\n")

    existing_ids = set()
    if not just_created:
        # 기존 항목 조회는 재사용 시에만. 신규 생성 직후는 API 캐시 미스로 404 위험.
        page = None
        while True:
            kwargs = {"part": "contentDetails", "playlistId": pl_id, "maxResults": 50}
            if page:
                kwargs["pageToken"] = page
            try:
                resp = yt.playlistItems().list(**kwargs).execute()
            except Exception as e:
                print(f"[알림] 기존 항목 조회 실패({e}). 빈 재생목록으로 간주하고 진행합니다.")
                break
            for it in resp.get("items", []):
                existing_ids.add(it["contentDetails"]["videoId"])
            page = resp.get("nextPageToken")
            if not page:
                break

    for n, title, vid in items:
        if vid in existing_ids:
            print(f"  [스킵] {n:2d}편 (이미 포함): {title}")
            continue
        body = {
            "snippet": {
                "playlistId": pl_id,
                "resourceId": {"kind": "youtube#video", "videoId": vid},
            }
        }
        yt.playlistItems().insert(part="snippet", body=body).execute()
        print(f"  [추가] {n:2d}편 -> {title} ({vid})")

    print(f"\n[완료] https://www.youtube.com/playlist?list={pl_id}")


# ============================================================================
# 진행 현황
# ============================================================================
def cmd_list(season):
    cfg = season_cfg(season)
    print(f"== {SERIES_NAME} · {cfg['label']} · 발행 순서 ==")
    last_grp = None
    for b in cfg["books"]:
        num = b["num"]
        grp = b.get("group")
        if "groups" in cfg and grp and grp != last_grp:
            gmeta = cfg["groups"].get(grp, {})
            print(f"\n[{gmeta.get('label', grp)}]")
            last_grp = grp
        content_ok = os.path.exists(content_file(season, num))
        video_ok = os.path.exists(book_final_mp4(season, num))
        upload_ok = os.path.exists(book_upload_info(season, num))
        url = ""
        if upload_ok:
            with open(book_upload_info(season, num), encoding="utf-8") as f:
                for line in f:
                    if line.startswith("url:"):
                        url = line.split("url:", 1)[1].strip()
                        break
        marks = [
            "[내용]" if content_ok else "[   ]",
            "[영상]" if video_ok else "[   ]",
            "[업로드]" if upload_ok else "[    ]",
        ]
        ep = episode_no(season, num)
        print(f"  {num:2d}. (ep{ep:2d}) {' '.join(marks)}  {b['title']}  {url}")


# ============================================================================
# CLI
# ============================================================================
def main():
    ap = argparse.ArgumentParser(description="전자책 유튜브 영상 제작·업로드 로봇")
    ap.add_argument("target", help="권수(시즌 통산 num), 'list', 또는 'playlist'")
    ap.add_argument(
        "--season", type=int, choices=sorted(SEASONS.keys()), default=CURRENT_SEASON,
        help=f"시즌 번호 (기본 {CURRENT_SEASON}). 1=기존 10권, 2=100권 시리즈(G01 1~10, G02 11~20, G03 21~30, G04 31~40)",
    )
    ap.add_argument(
        "--step",
        choices=["slides", "video", "upload", "build"],
        default="build",
        help="단계 선택 (기본 build = 슬라이드+영상, 업로드 제외). 업로드는 검수 후 --step upload 로 별도 실행.",
    )
    ap.add_argument(
        "--group", default=None,
        help="playlist 대상 그룹 (예: G01, G02, G03, G04). 시즌 2처럼 다중 그룹 시즌에서 playlist 인자와 함께 사용.",
    )
    args = ap.parse_args()

    season = args.season
    cfg = season_cfg(season)
    books = cfg["books"]

    if args.target == "list":
        cmd_list(season)
        return

    if args.target == "playlist":
        step_playlist(season, args.group)
        return

    try:
        num = int(args.target)
    except ValueError:
        print("[오류] 권수는 숫자(1~10), 'list', 또는 'playlist'")
        sys.exit(1)
    if not (1 <= num <= len(books)):
        print(f"[오류] 권수 범위 1~{len(books)}")
        sys.exit(1)

    content = load_content(season, num)
    gcfg = group_cfg(season, num)
    ep = episode_no(season, num)
    label_prefix = gcfg.get("footer_label", cfg["label"])
    print(f"== {label_prefix} · {ep}편 (num {num}) · {books[num-1]['title']} ==\n")

    if args.step in ("slides", "build"):
        step_slides(season, num, content)
    if args.step in ("video", "build"):
        step_video(season, num, content)
    if args.step == "upload":
        if os.path.exists(book_upload_info(season, num)):
            with open(book_upload_info(season, num), encoding="utf-8") as f:
                existing = f.read()
            print(f"\n[주의] 이미 업로드된 권입니다.\n{existing}")
            print(f"재업로드하려면 {book_upload_info(season, num)} 삭제 후 재실행.")
            return
        step_upload(season, num, content)
    if args.step == "build":
        print("\n[완료] 영상 생성 끝. 검수 후 업로드는 아래 명령으로 실행하세요.")
        print(f"  python ebook_video_robot.py {num} --season {season} --step upload")


if __name__ == "__main__":
    main()
