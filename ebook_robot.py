# -*- coding: utf-8 -*-
"""
전자책 쓰기 로봇 - 신앙/묵상 전자책 자동 생성기
실행: python ebook_robot.py
"""
import os, sys, json, zipfile, threading, subprocess, textwrap, datetime, base64
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from PIL import Image, ImageDraw, ImageFont
import bible_verify

# ════════════════════════════════════════════════════════════════
# 설정
# ════════════════════════════════════════════════════════════════
DEFAULT_OUTPUT = os.path.join(os.path.expanduser("~"), "Downloads", "전자책")
TMP_DIR = os.path.join(os.path.dirname(__file__), "tmp_epub")
CLAUDE_CMD = "claude"   # claude CLI 명령어

# 출판사 책방 사이트 (판권·에필로그·QR 등 EPUB 안에 박히는 표준 URL).
# 옛 GitHub Pages → 2026-05-09 Vercel 도메인으로 통일 (시즌2 본권 100권은 옛 도메인 잔존,
# 정식 오픈 시점에 일괄 패치 — project_official_launch_todo.md #8 참조).
PUBLISHER_URL = "https://ai-spirituality-books.vercel.app/catalog"

GENRE_PROMPTS = {
    "신앙/묵상": "기독교 신앙과 영성을 주제로 한 묵상 전자책",
}

# ════════════════════════════════════════════════════════════════
# Claude CLI 호출
# ════════════════════════════════════════════════════════════════
def call_claude(prompt: str, log_fn=None, retries: int = 5) -> str:
    """claude -p 명령으로 텍스트 생성 (실패 시 최대 5회 재시도)"""
    import time
    for attempt in range(1, retries + 1):
        if log_fn:
            log_fn(f"[AI] 생성 중{'...' if attempt == 1 else f' (재시도 {attempt}/{retries})...'}")
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            result = subprocess.run(
                [CLAUDE_CMD, "-p", prompt],
                capture_output=True,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,
                startupinfo=si,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode != 0:
                err = result.stderr.strip()
                out = result.stdout.strip()
                if attempt < retries:
                    if log_fn:
                        log_fn(f"[주의] API 오류 발생, 30초 후 재시도... ({attempt}/{retries}) ({out or err})")
                    time.sleep(30)
                    continue
                raise RuntimeError(f"claude 오류 (returncode={result.returncode})\nstderr: {err}\nstdout: {out}")
            return _strip_code_fence(result.stdout.strip())
        except FileNotFoundError:
            raise RuntimeError("claude 명령어를 찾을 수 없습니다. Claude Code가 설치되어 있는지 확인하세요.")
        except subprocess.TimeoutExpired:
            if attempt < retries:
                if log_fn:
                    log_fn(f"[주의] 응답 시간 초과, 재시도 중... ({attempt}/{retries})")
                continue
            raise RuntimeError("응답 시간이 초과되었습니다 (10분 초과). 다시 시도해 주세요.")


def _strip_code_fence(text: str) -> str:
    """```html ... ``` 또는 ``` ... ``` 코드블록 마커 제거"""
    import re
    # ```html\n...\n``` 형태
    text = re.sub(r'^```[a-zA-Z]*\s*\n?', '', text)
    text = re.sub(r'\n?```\s*$', '', text)
    # 혹시 중간에도 있으면 제거
    text = re.sub(r'```[a-zA-Z]*', '', text)
    text = re.sub(r'```', '', text)
    return text.strip()


def _clean_html_refs(text: str) -> str:
    """AI 생성 본문에서 URL/파일명 잔재 제거"""
    import re
    # http(s):// URL 제거
    text = re.sub(r'https?://\S+', '', text)
    # 단독으로 서있는 파일명 패턴 제거 (예: chapter.html, ref.pdf)
    text = re.sub(r'\b\w[\w\-]*\.(html|htm|pdf|txt|xhtml|docx?)\b', '', text, flags=re.IGNORECASE)
    # 빈 괄호 정리 (파일명이 제거된 자리)
    text = re.sub(r'\(\s*\)', '', text)
    text = re.sub(r'\[\s*\]', '', text)
    return text.strip()


# ════════════════════════════════════════════════════════════════
# 1단계: 목차 생성
# ════════════════════════════════════════════════════════════════
def generate_outline(title, subtitle, keywords, chapter_count, draft, log_fn) -> list:
    """챕터 목차 생성. draft 있으면 초안 기반, 없으면 새로 생성."""
    if draft.strip():
        draft_context = f"\n\n[참고할 초안]\n{draft[:3000]}"
    else:
        draft_context = ""

    prompt = textwrap.dedent(f"""
        당신은 기독교 신앙/묵상 전자책 전문 작가입니다.
        아래 정보를 바탕으로 전자책 목차를 생성해주세요.

        제목: {title}
        부제: {subtitle}
        키워드: {keywords}
        챕터 수: {chapter_count}{draft_context}

        반드시 아래 JSON 형식만 출력하세요. 다른 설명 없이 JSON만 출력하세요:
        {{
          "chapters": [
            {{"num": 1, "title": "챕터 제목", "subtitle": "부제목", "theme": "핵심 주제 한 문장"}},
            {{"num": 2, "title": "챕터 제목", "subtitle": "부제목", "theme": "핵심 주제 한 문장"}}
          ]
        }}
    """).strip()

    log_fn("[1단계] 목차 생성 중...")
    raw = call_claude(prompt, log_fn)

    # JSON 파싱 (마크다운 코드블록 제거)
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(raw)
        chapters = data["chapters"]
        log_fn(f"[완료] 목차 {len(chapters)}개 챕터 생성됨")
        return chapters
    except Exception:
        # 파싱 실패 시 기본 목차 생성
        log_fn("[주의] 목차 파싱 실패 - 기본 목차 사용")
        return [{"num": i+1, "title": f"{i+1}장", "subtitle": "", "theme": keywords}
                for i in range(int(chapter_count))]


# ════════════════════════════════════════════════════════════════
# 2단계: 챕터 본문 생성
# ════════════════════════════════════════════════════════════════
def generate_chapter(book_title, chapter_info, draft_section, log_fn) -> str:
    """챕터 본문 HTML 생성"""
    num   = chapter_info["num"]
    title = chapter_info["title"]
    theme = chapter_info.get("theme", "")

    draft_part = f"\n\n[참고 초안 (이 내용을 발전시켜 쓰세요)]\n{draft_section[:2000]}" if draft_section.strip() else ""

    prompt = textwrap.dedent(f"""
        당신은 기독교 신앙/묵상 전자책 전문 작가입니다.
        아래 챕터를 깊이 있고 풍성하게 집필해주세요.

        책 제목: {book_title}
        챕터: {num}장 - {title}
        핵심 주제: {theme}{draft_part}

        성경 인용 원칙 (이 책의 핵심):
        - 이 책은 신앙·묵상서다. 성경 인용은 분량 채우기가 아니라 본문의 중심축이다.
        - **반드시 한 챕터에 최소 3개 이상, 가능하면 4~5개**의 성경 말씀을 인용할 것.
          따옴표로 실제 본문을 옮기는 직접 인용과, 구절 번호·주제만 언급하는 간접 인용을 섞어
          풍성하게 활용하되, 그 중 **직접 인용이 최소 2개 이상** 있어야 한다.
        - 널리 알려진 구절(요한복음 3:16, 시편 23:1, 로마서 8:28, 빌립보서 4:13 등)을
          적극 활용하라. 익숙한 구절이 독자에게 울림을 준다.
        - 구절 번호와 따옴표 본문은 반드시 일치해야 한다.
          다른 구절의 내용을 임의의 번호에 붙이지 말 것(예: 출애굽기 14:14의 내용을 시편 46:10이라 표기 금지).
        - 여러 구절을 섞어 가짜 합성구를 만들지 말 것.
        - 존재하지 않는 장·절을 만들지 말 것(예: 창세기 51장, 에스더 9장을 넘어선 절).
        - 기억이 모호한 구절이 있다면, 그 구절은 쓰지 말고 **잘 아는 다른 구절로 대체하여 총 인용 수는 유지**할 것.

        집필 요건:
        - 위 성경 인용 원칙을 최우선으로 지킬 것.
        - 소제목 2~3개로 내용 구조화
        - 독자에게 깊은 묵상을 이끄는 내용
        - 실생활 적용 포함
        - 분량: 1200~1500자 (한국어 기준)
        - 본문 마지막에 이 챕터 주제에 맞는 묵상 질문 2~3개를 반드시 포함

        아래 HTML 태그만 사용해서 출력하세요 (다른 설명 없이 HTML만):
        - <p> : 본문 단락
        - <div class="ch-sub">소제목</div> : 소제목
        - <div class="quote"><p>인용구</p></div> : 인용/묵상 블록
        - <div class="scripture"><p>말씀</p><cite>출처</cite></div> : 성경 구절
        - <strong>강조어</strong> : 강조
        - 묵상 질문은 반드시 아래 형식으로 본문 맨 끝에 추가:
          <div class="meditation-q">
            <p class="mq-title">묵상 질문</p>
            <p class="mq-item">1. 질문 내용</p>
            <p class="mq-item">2. 질문 내용</p>
            <p class="mq-item">3. 질문 내용</p>
          </div>

        절대 금지 사항:
        - URL, 웹 주소(.com/.html/.org 등) 포함 금지
        - 파일명(.html/.pdf/.txt 등) 포함 금지
        - 외부 참고 링크나 각주 번호 포함 금지
        - 허구의 참고문헌이나 학술 인용 금지
    """).strip()

    log_fn(f"[생성 중] {num}장: {title}")
    raw = call_claude(prompt, log_fn)
    return _clean_html_refs(raw)


# ════════════════════════════════════════════════════════════════
# 3단계: 에필로그 생성
# ════════════════════════════════════════════════════════════════
def generate_epilogue(book_title, chapters, log_fn) -> str:
    chapter_list = "\n".join([f"- {c['num']}장: {c['title']}" for c in chapters])
    prompt = textwrap.dedent(f"""
        당신은 기독교 신앙/묵상 전자책 전문 작가입니다.
        아래 전자책의 에필로그를 따뜻하고 감동적으로 집필해주세요.

        책 제목: {book_title}
        챕터 목록:
        {chapter_list}

        에필로그 요건:
        - 전체 내용을 아우르는 마무리
        - 독자를 격려하는 축복의 말
        - 하나님과의 관계를 강조
        - 분량: 700~900자

        HTML 태그만 사용해서 출력하세요:
        - <p>, <div class="quote"><p></p></div>, <strong>, <div class="scripture"><p></p><cite></cite></div>

        절대 금지: URL, 파일명(.html/.pdf 등), 외부 링크, 허구의 인용문 포함 금지
    """).strip()

    log_fn("[생성 중] 에필로그...")
    raw = call_claude(prompt, log_fn)
    return _clean_html_refs(_strip_code_fence(raw))


# ════════════════════════════════════════════════════════════════
# 표지 색상 테마
# ════════════════════════════════════════════════════════════════
COVER_THEMES = {
    "황금 (기본)": {
        "grad_top":    (252, 240, 178),
        "grad_bot":    (205, 162, 65),
        "accent":      (135, 95,  18),
        "accent2":     (160, 118, 30),
        "text_title":  (38,  26,  5),
        "text_sub":    (108, 76,  22),
        "text_tag":    (100, 68,  14),
        "text_author": (38,  26,  5),
        "text_pub":    (140, 105, 35),
    },
    "남색 (Navy)": {
        "grad_top":    (15,  30,  60),
        "grad_bot":    (5,   12,  30),
        "accent":      (184, 150, 46),
        "accent2":     (210, 175, 80),
        "text_title":  (240, 230, 200),
        "text_sub":    (184, 150, 46),
        "text_tag":    (150, 120, 40),
        "text_author": (240, 230, 200),
        "text_pub":    (160, 130, 60),
    },
    "초록 (Forest)": {
        "grad_top":    (220, 240, 215),
        "grad_bot":    (80,  130, 70),
        "accent":      (40,  90,  30),
        "accent2":     (60,  120, 50),
        "text_title":  (20,  60,  10),
        "text_sub":    (50,  100, 40),
        "text_tag":    (60,  110, 45),
        "text_author": (20,  60,  10),
        "text_pub":    (60,  110, 45),
    },
    "자주 (Burgundy)": {
        "grad_top":    (245, 225, 230),
        "grad_bot":    (140, 40,  70),
        "accent":      (100, 20,  45),
        "accent2":     (130, 35,  60),
        "text_title":  (60,  10,  25),
        "text_sub":    (110, 30,  55),
        "text_tag":    (120, 40,  60),
        "text_author": (60,  10,  25),
        "text_pub":    (120, 40,  60),
    },
    "회색 (Slate)": {
        "grad_top":    (240, 240, 242),
        "grad_bot":    (150, 155, 165),
        "accent":      (60,  70,  90),
        "accent2":     (90,  100, 115),
        "text_title":  (30,  35,  50),
        "text_sub":    (70,  80,  100),
        "text_tag":    (80,  90,  110),
        "text_author": (30,  35,  50),
        "text_pub":    (80,  90,  110),
    },
}

THEME_NAMES = list(COVER_THEMES.keys())


# ════════════════════════════════════════════════════════════════
# 표지 이미지 생성
# ════════════════════════════════════════════════════════════════
def make_cover_image(title, subtitle, author, publisher, theme_name="황금 (기본)") -> str:
    os.makedirs(TMP_DIR, exist_ok=True)
    th = COVER_THEMES.get(theme_name, COVER_THEMES["황금 (기본)"])

    W, H = 1400, 2100
    img = Image.new("RGB", (W, H), color=th["grad_top"])
    draw = ImageDraw.Draw(img)

    gr_top, gr_bot = th["grad_top"], th["grad_bot"]
    for y in range(H):
        t = y / H
        r = int(gr_top[0] + (gr_bot[0] - gr_top[0]) * t)
        g = int(gr_top[1] + (gr_bot[1] - gr_top[1]) * t)
        b = int(gr_top[2] + (gr_bot[2] - gr_top[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    gold = th["accent"]
    draw.rectangle([70, 70, W - 70, H - 70], outline=gold, width=3)
    draw.rectangle([80, 80, W - 80, H - 80], outline=th["accent2"], width=1)

    cx = W // 2

    # 십자가 — 중앙보다 약간 위
    draw.rectangle([cx - 7, 280, cx + 7, 410], fill=gold)
    draw.rectangle([cx - 48, 328, cx + 48, 354], fill=gold)

    # 구분선
    draw.rectangle([cx - 55, 468, cx + 55, 471], fill=gold)

    try:
        fb = "malgunbd.ttf"
        fr = "malgun.ttf"
        f_tag   = ImageFont.truetype(fr,  32)
        f_title2= ImageFont.truetype(fb,  62)
        f_sub   = ImageFont.truetype(fr,  38)
        f_auth  = ImageFont.truetype(fb,  54)
        f_small = ImageFont.truetype(fr,  28)
    except Exception:
        f_tag = f_title2 = f_sub = f_auth = f_small = ImageFont.load_default()

    def ctext(y, text, font, color):
        bb = draw.textbbox((0,0), text, font=font)
        w = bb[2] - bb[0]
        draw.text(((W - w) // 2, y), text, font=font, fill=color)

    # 태그
    ctext(498, "신앙 · 묵상 전자책", f_tag, th["text_tag"])

    # 제목 줄 나누기
    lines = []
    if len(title) > 14:
        mid = len(title) // 2
        for i in range(mid, 0, -1):
            if title[i] in " ,·":
                lines = [title[:i].strip(), title[i:].strip()]
                break
        if not lines:
            lines = [title[:mid], title[mid:]]
    else:
        lines = [title]

    y_title = 580
    for line in lines:
        ctext(y_title, line, f_title2, th["text_title"])
        y_title += 100

    # 부제목
    if subtitle:
        draw.rectangle([cx - 40, y_title + 20, cx + 40, y_title + 23], fill=gold)
        ctext(y_title + 48, subtitle[:26], f_sub, th["text_sub"])
        if len(subtitle) > 26:
            ctext(y_title + 100, subtitle[26:52], f_sub, th["text_sub"])

    # 저자 — 기존 H-260에서 H-300으로 40px 위로 이동 (로고 자리 확보)
    ctext(H - 300, author, f_auth, th["text_author"])

    # 출판사 로고 삽입 (배경 밝기에 따라 검정/크림 자동 선택)
    _paste_publisher_logo(img, th, f_small)

    path = os.path.join(TMP_DIR, "cover.jpg")
    img.save(path, "JPEG", quality=92)
    return path


def _paste_publisher_logo(img, theme, year_font):
    """표지 하단에 'AI 시대 영성' 가로 로고 + 연도를 배치.

    배경 그라디언트 밝기에 따라 로고/텍스트 색을 자동 선택.
    make_logo.py 로 생성된 logo_horizontal_black.png 를 마스터로 사용하고
    알파 픽셀을 원하는 색으로 치환.
    """
    from PIL import Image as _Image, ImageDraw as _ImageDraw
    W, H = img.size
    LOGO_H = 75
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(base_dir, "logo_horizontal_black.png")
    if not os.path.exists(logo_path):
        return  # 로고 파일 없으면 건너뜀 (기존 동작 유지)

    # 배경 그라디언트 루미넌스 계산 (로고 영역)
    gr_top, gr_bot = theme["grad_top"], theme["grad_bot"]
    lum_samples = []
    for y in (1900, 1930, 1960):
        t = y / H
        r = gr_top[0] + (gr_bot[0] - gr_top[0]) * t
        g = gr_top[1] + (gr_bot[1] - gr_top[1]) * t
        b = gr_top[2] + (gr_bot[2] - gr_top[2]) * t
        lum_samples.append(0.299 * r + 0.587 * g + 0.114 * b)
    luma = sum(lum_samples) / len(lum_samples)
    fg = (245, 240, 225) if luma < 120 else (20, 20, 20)

    # 로고 로드 + 틴트 + 리사이즈
    logo = _Image.open(logo_path).convert("RGBA")
    px = logo.load()
    for yy in range(logo.height):
        for xx in range(logo.width):
            _r, _g, _b, _a = px[xx, yy]
            if _a > 0:
                px[xx, yy] = (*fg, _a)
    ratio = LOGO_H / logo.height
    logo = logo.resize((int(logo.width * ratio), LOGO_H), _Image.LANCZOS)

    # 로고 + 연도 묶음을 저자명 수직축(가로 중앙)에 맞춰 좌우 대칭 배치
    ly = 1895
    img_rgba = img.convert("RGBA")
    draw = _ImageDraw.Draw(img_rgba)
    year_text = "· " + str(datetime.date.today().year)
    tbb = draw.textbbox((0, 0), year_text, font=year_font)
    year_w = tbb[2] - tbb[0]
    year_h = tbb[3] - tbb[1]
    gap = 14
    block_w = logo.width + gap + year_w
    lx = (W - block_w) // 2
    img_rgba.paste(logo, (lx, ly), logo)
    text_y = ly + (LOGO_H - year_h) // 2 - tbb[1]
    draw.text((lx + logo.width + gap, text_y),
              year_text, font=year_font, fill=fg)

    # RGB로 되돌려서 원본 img 에 합성 결과 복사
    result = img_rgba.convert("RGB")
    img.paste(result)


# ════════════════════════════════════════════════════════════════
# EPUB CSS
# ════════════════════════════════════════════════════════════════
EPUB_CSS = """
@charset "UTF-8";
:root { --gold:#B8962E; --dark:#0F1E3C; --accent:#5C3D2E; --bg-soft:#F7F3EC; --border:#C8B99A; }
body { font-family:'Malgun Gothic','맑은 고딕','Apple SD Gothic Neo',sans-serif; font-size:1em; line-height:1.85; color:#1E1E1E; margin:0; padding:0; }
h2.ch-title { font-size:1.3em; font-weight:700; color:var(--dark); line-height:1.4; margin:0.5em 0 0.3em; }
.ch-num { font-size:0.7em; letter-spacing:4px; color:var(--gold); text-transform:uppercase; display:block; margin-bottom:0.3em; }
.ch-divider { width:2.5em; height:3px; background:var(--gold); margin:0.8em 0 1.5em; }
.ch-sub { font-size:1em; font-weight:700; color:var(--dark); margin:1.5em 0 0.5em; border-left:3px solid var(--gold); padding-left:0.5em; }
p { margin:0 0 1em; text-align:justify; word-break:keep-all; }
strong { font-weight:700; color:var(--accent); }
.quote { background:var(--bg-soft); border-left:4px solid var(--gold); padding:1em 1.2em; margin:1.5em 0; border-radius:0 4px 4px 0; }
.quote p { font-style:italic; color:var(--accent); margin-bottom:0; }
.scripture { background:#EEF2F7; border-radius:4px; padding:0.9em 1em; margin:1.2em 0; }
.scripture p { font-size:0.95em; color:#2C3E50; margin-bottom:0; font-style:italic; }
.scripture cite { display:block; font-size:0.82em; color:var(--gold); font-style:normal; font-weight:700; margin-top:0.5em; text-align:right; }
.meditation-q { background:var(--bg-soft); border:1px solid var(--border); border-radius:6px; padding:1.2em 1.4em; margin:2em 0 0.5em; page-break-inside:avoid; break-inside:avoid; }
.mq-title { font-size:0.78em; font-weight:700; letter-spacing:3px; color:var(--gold); margin-bottom:0.8em; }
.mq-item { font-size:0.93em; color:var(--accent); line-height:1.7; margin-bottom:0.5em; padding-left:1.4em; text-indent:-1.4em; }
.mq-item:last-child { margin-bottom:0; }
.commitment { background:var(--dark); border-radius:6px; padding:1.4em 1.5em; margin:1.5em 0; }
.commitment h3 { font-size:0.78em; font-weight:700; letter-spacing:3px; color:var(--gold); text-transform:uppercase; margin-bottom:1em; }
.commitment-item { display:flex; gap:0.6em; align-items:flex-start; margin-bottom:0.9em; color:rgba(255,255,255,0.88); font-size:0.95em; line-height:1.7; }
.commitment-item:last-child { margin-bottom:0; }
.c-num { min-width:1.5em; height:1.5em; background:var(--gold); color:var(--dark); border-radius:50%; font-size:0.82em; font-weight:700; text-align:center; line-height:1.5em; flex-shrink:0; }
.commitment-item em { color:#E8C97A; font-style:normal; font-weight:700; }
"""

def wrap_xhtml(title, body):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ko">
<head><meta charset="UTF-8"/><title>{title}</title>
<link rel="stylesheet" type="text/css" href="styles/style.css"/></head>
<body><div style="padding:2em 1.5em">{body}</div></body>
</html>"""


# ════════════════════════════════════════════════════════════════
# EPUB 패키징
# ════════════════════════════════════════════════════════════════
def build_epub(meta, chapters_data, output_path, log_fn):
    """chapters_data: [{"info": {...}, "html": "..."}]"""
    cover_path = make_cover_image(
        meta["title"], meta["subtitle"], meta["author"], meta["publisher"],
        meta.get("cover_theme", "황금 (기본)")
    )
    log_fn("[패키징] EPUB 파일 생성 중...")

    uid = f"urn:uuid:ebook-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

    # ISBN이 있으면 교보 리더 등 ISBN 기반 색인에 잡히도록 기본 식별자로 사용
    isbn_val = str(meta.get("isbn") or "").strip()
    if isbn_val:
        identifier_block = (
            f'<dc:identifier id="bookid">urn:isbn:{isbn_val}</dc:identifier>\n'
            f'    <dc:identifier id="uuid">{uid}</dc:identifier>'
        )
    else:
        identifier_block = f'<dc:identifier id="bookid">{uid}</dc:identifier>'

    # content.opf
    manifest_items = "\n".join([
        f'    <item id="ch{c["info"]["num"]:02d}" href="ch{c["info"]["num"]:02d}.xhtml" media-type="application/xhtml+xml"/>'
        for c in chapters_data
    ])
    spine_items = "\n".join([
        f'    <itemref idref="ch{c["info"]["num"]:02d}"/>'
        for c in chapters_data
    ])

    opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" xml:lang="ko" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    {identifier_block}
    <dc:title>{meta['title']}</dc:title>
    <dc:creator>{meta['author']}</dc:creator>
    <dc:publisher>{meta['publisher']}</dc:publisher>
    <dc:language>ko</dc:language>
    <dc:date>{meta['date']}</dc:date>
    <dc:rights>Copyright © {meta['date'][:4]} {meta['author']}. All rights reserved.</dc:rights>
    <dc:description>{meta['subtitle']}</dc:description>
    <meta name="cover" content="cover-image"/>
    <meta property="dcterms:modified">{meta['date']}T00:00:00Z</meta>
    <meta property="rendition:spread">none</meta>
    <meta property="rendition:layout">reflowable</meta>
  </metadata>
  <manifest>
    <item id="cover-image" href="images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>
    <item id="publisher-logo" href="images/publisher_logo.png" media-type="image/png"/>
    <item id="style"       href="styles/style.css"  media-type="text/css"/>
    <item id="nav"         href="nav.xhtml"          media-type="application/xhtml+xml" properties="nav"/>
    <item id="cover-page"  href="cover.xhtml"        media-type="application/xhtml+xml"/>
    <item id="copyright"   href="copyright.xhtml"    media-type="application/xhtml+xml"/>
    <item id="toc-page"    href="toc.xhtml"          media-type="application/xhtml+xml"/>
{manifest_items}
    <item id="epilogue"    href="epilogue.xhtml"     media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="cover-page" properties="rendition:page-spread-center"/>
    <itemref idref="copyright"/>
    <itemref idref="toc-page"/>
{spine_items}
    <itemref idref="epilogue"/>
  </spine>
</package>"""

    # nav.xhtml
    toc_links = "\n".join([
        f'      <li><a href="ch{c["info"]["num"]:02d}.xhtml">{c["info"]["num"]}. {c["info"]["title"]}</a></li>'
        for c in chapters_data
    ])
    nav = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ko">
<head><meta charset="UTF-8"/><title>목차</title></head>
<body>
  <nav epub:type="toc" id="toc"><h1>목차</h1><ol>
      <li><a href="cover.xhtml">표지</a></li>
      <li><a href="copyright.xhtml">판권</a></li>
      <li><a href="toc.xhtml">차례</a></li>
{toc_links}
      <li><a href="epilogue.xhtml">에필로그</a></li>
  </ol></nav>
  <nav epub:type="landmarks"><ol>
      <li><a epub:type="cover" href="cover.xhtml">표지</a></li>
      <li><a epub:type="bodymatter" href="ch01.xhtml">본문 시작</a></li>
  </ol></nav>
</body></html>"""

    # 표지 xhtml — base64 data URI 인라인 (epub.js iframe 호환).
    # 옛 SVG <image xlink:href="../images/cover.jpg"> 방식은 epub.js 의 blob URL
    # rewrite 가 SVG 내부 xlink:href 를 따라가지 못해 책방 reader 에서 빈 페이지로 떴음.
    with open(cover_path, "rb") as _cf:
        _cover_b64 = base64.b64encode(_cf.read()).decode("ascii")
    cover_xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ko">
<head><meta charset="UTF-8"/><title>표지</title>
<style>
  html, body {{ margin:0; padding:0; width:100%; height:100%; background:#FFFFFF; }}
  .cover-wrap {{ width:100%; height:100%; display:flex; align-items:center; justify-content:center; padding:0; box-sizing:border-box; }}
  img {{ display:block; max-width:100%; max-height:100vh; width:auto; height:auto; object-fit:contain; }}
</style>
</head>
<body>
<div class="cover-wrap">
<img src="data:image/jpeg;base64,{_cover_b64}" alt="표지"/>
</div>
</body>
</html>"""

    # 판권 xhtml
    isbn_str = meta.get("isbn") or "신청 중"
    copyright_xhtml = wrap_xhtml("판권", f"""
<div style="text-align:center;margin:0 0 1.6em 0;"><img src="images/publisher_logo.png" alt="AI 시대 영성" style="height:60px;"/></div>
<div style="padding:1em;font-size:0.88em;color:#555;line-height:2">
  <h2 style="font-size:1em;color:#0F1E3C;margin-bottom:1.5em;border-bottom:1px solid #C8B99A;padding-bottom:0.5em">판권 정보</h2>
  <p><strong>제목</strong>　{meta['title']}</p>
  <p><strong>부제</strong>　{meta['subtitle']}</p>
  <p><strong>저자</strong>　{meta['author']}</p>
  <p><strong>출판사</strong>　{meta['publisher']}</p>
  <p><strong>출판일</strong>　{meta['date']}</p>
  <p><strong>ISBN</strong>　{isbn_str}</p>
  <p><strong>부가기호</strong>　{meta.get('buga', '05230')}</p>
  <p><strong>홈페이지</strong>　{PUBLISHER_URL}</p>
  <p><strong>이메일</strong>　godsonphk@gmail.com</p>
  <div style="margin-top:2em;font-size:0.85em;color:#888;border-top:1px solid #C8B99A;padding-top:1em">
    <p>Copyright © {meta['date'][:4]} {meta['author']}. All rights reserved.</p>
    <p>이 책의 저작권은 저자에게 있습니다. 저작권법에 의해 보호를 받는 저작물이므로 저자의 허락 없이 무단 전재와 복제를 금합니다.</p>
  </div>
</div>""")

    # 목차 xhtml
    toc_items = "\n".join([
        f'<div style="display:flex;gap:3mm;padding:3.5mm 0;border-bottom:1px solid #E8E0D0;font-size:0.95em"><span style="color:#B8962E;font-weight:700;min-width:8mm">{c["info"]["num"]:02d}</span><span>{c["info"]["title"]}</span></div>'
        for c in chapters_data
    ])
    toc_xhtml = wrap_xhtml("차례", f"""
<span style="font-size:0.7em;letter-spacing:4px;color:#B8962E;text-transform:uppercase;display:block;margin-bottom:4mm">Contents</span>
<h2 class="ch-title">차례</h2>
<div style="width:2.5em;height:3px;background:#B8962E;margin:0.8em 0 1.5em"></div>
{toc_items}
<div style="padding:3.5mm 0;font-size:0.95em"><span style="color:#B8962E;font-weight:700;min-width:8mm;margin-right:3mm">★</span><span>에필로그</span></div>
""")

    # 챕터 xhtml 생성
    chapter_files = {}
    for c in chapters_data:
        num   = c["info"]["num"]
        title = c["info"]["title"]
        sub   = c["info"].get("subtitle", "")
        sub_line = f'<div class="ch-sub" style="font-size:1em;color:#5C3D2E;margin-bottom:0.3em">{sub}</div>' if sub else ""
        body = f"""
<span class="ch-num">Chapter {num:02d}</span>
<h2 class="ch-title">{title}</h2>
{sub_line}
<div class="ch-divider"></div>
{c['html']}"""
        chapter_files[f"ch{num:02d}.xhtml"] = wrap_xhtml(title, body)

    # EPUB ZIP 생성
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as epub:
        epub.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip",
                      compress_type=zipfile.ZIP_STORED)
        epub.writestr("META-INF/container.xml", """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>""")
        epub.writestr("OEBPS/content.opf",       opf)
        epub.writestr("OEBPS/nav.xhtml",          nav)
        epub.writestr("OEBPS/styles/style.css",   EPUB_CSS)
        epub.write(cover_path,                    "OEBPS/images/cover.jpg")
        logo_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo_horizontal_black.png")
        if os.path.exists(logo_png):
            epub.write(logo_png,                  "OEBPS/images/publisher_logo.png")
        epub.writestr("OEBPS/cover.xhtml",        cover_xhtml)
        epub.writestr("OEBPS/copyright.xhtml",    copyright_xhtml)
        epub.writestr("OEBPS/toc.xhtml",          toc_xhtml)
        for fname, content in chapter_files.items():
            epub.writestr(f"OEBPS/{fname}", content)
        epub.writestr("OEBPS/epilogue.xhtml",     chapters_data[-1].get("epilogue_html", ""))

    # 표지 이미지를 epub과 같은 폴더에 별도 저장
    import shutil
    cover_out = os.path.splitext(output_path)[0] + "_cover.jpg"
    shutil.copy2(cover_path, cover_out)
    log_fn(f"[표지] 저장됨: {os.path.basename(cover_out)}")

    size_kb = os.path.getsize(output_path) // 1024
    log_fn(f"[완료] EPUB 저장: {output_path} ({size_kb} KB)")
    return output_path


# ════════════════════════════════════════════════════════════════
# 메인 생성 흐름
# ════════════════════════════════════════════════════════════════
def run_generation(params, log_fn, progress_fn, done_fn):
    """별도 스레드에서 실행"""
    try:
        title        = params["title"]
        subtitle     = params["subtitle"]
        author       = params["author"]
        publisher    = params["publisher"]
        keywords     = params["keywords"]
        chapter_count= int(params["chapter_count"])
        draft        = params["draft"]
        output_dir   = params["output_dir"]
        isbn         = params["isbn"]
        buga         = params.get("buga", "05230")

        total_steps = chapter_count + 4  # 목차 + 챕터들 + 에필로그 + 패키징
        step = [0]

        def tick(msg):
            step[0] += 1
            log_fn(msg)
            progress_fn(int(step[0] / total_steps * 100))

        # 1. 목차
        chapters = generate_outline(title, subtitle, keywords, chapter_count, draft, tick)
        tick(f"[목차] {len(chapters)}개 챕터 확정")

        # 2. 초안 분할 (draft 있으면 챕터별로 나누기)
        draft_sections = split_draft(draft, len(chapters)) if draft.strip() else [""] * len(chapters)

        # 3. 챕터별 생성
        chapters_data = []
        for i, ch in enumerate(chapters):
            html = generate_chapter(title, ch, draft_sections[i], log_fn)
            chapters_data.append({"info": ch, "html": html})
            tick(f"[완료] {ch['num']}장: {ch['title']}")

        # 4. 에필로그
        epilogue_html = generate_epilogue(title, chapters, log_fn)
        epi_body = f"""
<span class="ch-num">Epilogue</span>
<h2 class="ch-title">에필로그</h2>
<div class="ch-divider"></div>
{epilogue_html}
<div style="text-align:center;margin-top:3em;padding:1.5em;border-top:1px solid #C8B99A;border-bottom:1px solid #C8B99A;background:#faf8f4;page-break-inside:avoid;break-inside:avoid">
  <p style="font-size:0.78em;color:#B8962E;letter-spacing:2px;margin-bottom:0.8em">PUBLISHER</p>
  <p style="font-weight:700;color:#0F1E3C;font-size:1em">{publisher}</p>
  <p style="font-size:0.85em;color:#555;margin-top:0.5em">{PUBLISHER_URL}</p>
  <p style="font-size:0.85em;color:#555;margin-top:0.3em">godsonphk@gmail.com</p>
  <p style="font-size:0.8em;color:#999;letter-spacing:2px;margin-top:0.8em">{publisher} · {datetime.date.today().year}</p>
</div>"""
        chapters_data[-1]["epilogue_html"] = wrap_xhtml("에필로그", epi_body)
        tick("[완료] 에필로그 생성")

        # 4.5. 성경 인용 검증 (형식 오류는 저장 차단, 본문 대조 의심은 리뷰 파일)
        all_text = bible_verify.strip_html(
            " ".join(cd["html"] for cd in chapters_data) + " " + epilogue_html
        )
        report = bible_verify.verify_text(all_text)
        log_fn(f"[성경검증] 총 {report['total']}건 인용  "
               f"형식OK {report['ok_format']}/{report['total']}  "
               f"본문OK {report['ok_content']}/{report['ok_format']}")
        if report["format_errors"]:
            log_fn(f"[오류] 존재하지 않는 성경 구절 {len(report['format_errors'])}건 — 저장 중단")
            for e in report["format_errors"]:
                log_fn(f"  - {e['raw']}  →  {e['problem']}")
            raise RuntimeError(
                f"성경 인용 형식 오류 {len(report['format_errors'])}건. "
                "로그에서 확인 후 다시 생성하세요."
            )

        # 5. EPUB 패키징
        safe_title = "".join(c for c in title[:30] if c not in r'\/:*?"<>|').strip().replace(" ", "_")
        if not safe_title:
            safe_title = "ebook"
        filename = f"{safe_title}_{datetime.date.today().strftime('%Y%m%d')}.epub"
        output_path = os.path.join(output_dir, filename)

        # 본문 대조 의심이 있으면 epub 옆에 리뷰 파일 생성
        if report["content_flags"]:
            review_path = os.path.splitext(output_path)[0] + "_citation_review.txt"
            bible_verify.write_review_file(review_path, title, report)
            log_fn(f"[주의] 본문 대조 의심 {len(report['content_flags'])}건 — "
                   f"리뷰 파일 생성: {os.path.basename(review_path)}")

        meta = {
            "title": title, "subtitle": subtitle,
            "author": author, "publisher": publisher,
            "date": str(datetime.date.today()), "isbn": isbn, "buga": buga,
            "cover_theme": params.get("cover_theme", "황금 (기본)")
        }
        build_epub(meta, chapters_data, output_path, log_fn)
        progress_fn(100)
        done_fn(output_path)

    except Exception as e:
        import traceback
        err_detail = traceback.format_exc()
        log_fn(f"[오류] {e}")
        log_fn(f"[상세]\n{err_detail}")
        # 로그 파일 저장
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"ebook_robot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"[오류] {e}\n\n{err_detail}")
        log_fn(f"[로그 저장] {log_path}")
        done_fn(None)


def split_draft(draft, n):
    """초안을 n개 섹션으로 분할"""
    if not draft.strip():
        return [""] * n
    lines = draft.strip().split("\n")
    chunk = max(1, len(lines) // n)
    sections = []
    for i in range(n):
        start = i * chunk
        end = start + chunk if i < n - 1 else len(lines)
        sections.append("\n".join(lines[start:end]))
    return sections


# ════════════════════════════════════════════════════════════════
# GUI
# ════════════════════════════════════════════════════════════════
class EbookRobotApp:
    def __init__(self, root, prefill=None, on_book_done=None, batch_info=None, on_generation_start=None):
        self.root = root
        self.root.title("전자책 쓰기 로봇")
        self.root.geometry("760x720")
        self.root.resizable(True, True)
        self.root.configure(bg="#F5F3EE")
        self.on_book_done = on_book_done
        self.on_generation_start = on_generation_start
        self.batch_info = batch_info
        self._build_ui()
        if prefill:
            self._apply_prefill(prefill)

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame",       background="#F5F3EE")
        style.configure("TLabel",       background="#F5F3EE", font=("맑은 고딕", 10))
        style.configure("TLabelframe",  background="#F5F3EE", font=("맑은 고딕", 10, "bold"))
        style.configure("TLabelframe.Label", background="#F5F3EE", foreground="#0F1E3C", font=("맑은 고딕", 10, "bold"))
        style.configure("Run.TButton",  font=("맑은 고딕", 12, "bold"), foreground="white", background="#0F1E3C", padding=10)
        style.map("Run.TButton", background=[("active", "#1A2E5C")])
        style.configure("TEntry",       font=("맑은 고딕", 10), padding=5)
        style.configure("TCombobox",    font=("맑은 고딕", 10))
        style.configure("TProgressbar", troughcolor="#E0D8CC", background="#B8962E", thickness=14)
        style.configure("Vertical.TScrollbar", troughcolor="#C8D4E0",
                        background="#1A3A6B", arrowcolor="#E8F0F8", width=18)
        style.map("Vertical.TScrollbar",
                  background=[("active", "#2A5A9B"), ("!active", "#1A3A6B")])

        # ── 헤더 ──────────────────────────────────────────────
        hdr = tk.Frame(self.root, bg="#0F1E3C", pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="전자책 쓰기 로봇",
                 font=("맑은 고딕", 15, "bold"), fg="#B8962E", bg="#0F1E3C").pack()
        tk.Label(hdr, text="신앙 · 묵상 전자책 자동 생성기",
                 font=("맑은 고딕", 9), fg="#888888", bg="#0F1E3C").pack()
        if self.batch_info:
            tk.Label(hdr, text=self.batch_info,
                     font=("맑은 고딕", 9, "bold"), fg="#AACCFF", bg="#0F1E3C").pack(pady=(2, 0))

        # ── 스크롤 가능한 메인 영역 ───────────────────────────
        canvas = tk.Canvas(self.root, bg="#F5F3EE", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical",
                                  style="Vertical.TScrollbar", command=canvas.yview)
        self.scroll_frame = ttk.Frame(canvas)
        self.scroll_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 마우스 휠 스크롤
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self._build_form(self.scroll_frame)

    def _build_form(self, parent):
        pad = {"padx": 12, "pady": 4}

        # ── 기본 정보 ─────────────────────────────────────────
        f1 = ttk.LabelFrame(parent, text="  책 기본 정보  ", padding=8)
        f1.pack(fill="x", **pad)

        fields = [
            ("제목 *",    "title",    "혼미케 하는 영을 결박하라"),
            ("부제목",    "subtitle", ""),
            ("저자명 *",  "author",   "AI, 박헌근"),
            ("출판사 *",  "publisher","AI 시대 영성"),
            ("ISBN",      "isbn",     "신청 중"),
            ("부가기호",  "buga",     "05230"),
        ]
        self.vars = {}
        for label, key, default in fields:
            row = ttk.Frame(f1)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=label, width=10, anchor="e").pack(side="left", padx=(0, 8))
            v = tk.StringVar(value=default)
            self.vars[key] = v
            ttk.Entry(row, textvariable=v, font=("맑은 고딕", 10)).pack(side="left", fill="x", expand=True)

        # ── 책 내용 설정 ──────────────────────────────────────
        f2 = ttk.LabelFrame(parent, text="  책 내용 설정  ", padding=8)
        f2.pack(fill="x", **pad)

        row1 = ttk.Frame(f2)
        row1.pack(fill="x", pady=2)
        ttk.Label(row1, text="장르", width=10, anchor="e").pack(side="left", padx=(0, 8))
        self.vars["genre"] = tk.StringVar(value="신앙/묵상")
        cb = ttk.Combobox(row1, textvariable=self.vars["genre"],
                          values=["신앙/묵상"], state="readonly", width=20)
        cb.pack(side="left")
        ttk.Label(row1, text="  (다음 버전에서 확장 예정)", foreground="#999").pack(side="left")

        row2 = ttk.Frame(f2)
        row2.pack(fill="x", pady=2)
        ttk.Label(row2, text="챕터 수 *", width=10, anchor="e").pack(side="left", padx=(0, 8))
        self.vars["chapter_count"] = tk.StringVar(value="6")
        ttk.Spinbox(row2, from_=3, to=12, textvariable=self.vars["chapter_count"],
                    width=5, font=("맑은 고딕", 10)).pack(side="left")
        ttk.Label(row2, text="  개  (3~12개 권장)", foreground="#666").pack(side="left")

        row3 = ttk.Frame(f2)
        row3.pack(fill="x", pady=2)
        ttk.Label(row3, text="키워드 *", width=10, anchor="e").pack(side="left", padx=(0, 8))
        self.vars["keywords"] = tk.StringVar(value="AI, 기술 우상주의, 영성, 분별, 성령, 묵상")
        ttk.Entry(row3, textvariable=self.vars["keywords"],
                  font=("맑은 고딕", 10)).pack(side="left", fill="x", expand=True)

        # ── 초안 입력 ─────────────────────────────────────────
        f3 = ttk.LabelFrame(parent, text="  초안 붙여넣기  (없으면 비워두면 AI가 처음부터 작성)  ", padding=8)
        f3.pack(fill="x", **pad)
        self.draft_text = scrolledtext.ScrolledText(
            f3, height=6, font=("맑은 고딕", 9),
            wrap="word", relief="flat", borderwidth=1,
            background="white", foreground="#333"
        )
        self.draft_text.pack(fill="x")
        ttk.Button(f3, text="초안 파일 불러오기",
                   command=self._load_draft_file).pack(anchor="e", pady=(6, 0))

        # ── 출력 설정 ─────────────────────────────────────────
        f4 = ttk.LabelFrame(parent, text="  출력 설정  ", padding=8)
        f4.pack(fill="x", **pad)

        row_theme = ttk.Frame(f4)
        row_theme.pack(fill="x", pady=2)
        ttk.Label(row_theme, text="표지 색상", width=10, anchor="e").pack(side="left", padx=(0, 8))
        self.vars["cover_theme"] = tk.StringVar(value=THEME_NAMES[0])
        ttk.Combobox(row_theme, textvariable=self.vars["cover_theme"],
                     values=THEME_NAMES, state="readonly", width=22).pack(side="left")

        row_out = ttk.Frame(f4)
        row_out.pack(fill="x", pady=2)
        ttk.Label(row_out, text="저장 위치", width=10, anchor="e").pack(side="left", padx=(0, 8))
        self.vars["output_dir"] = tk.StringVar(value=DEFAULT_OUTPUT)
        ttk.Entry(row_out, textvariable=self.vars["output_dir"],
                  font=("맑은 고딕", 10)).pack(side="left", fill="x", expand=True)
        ttk.Button(row_out, text="찾아보기",
                   command=self._browse_output).pack(side="left", padx=(6, 0))

        # ── 실행 버튼 ─────────────────────────────────────────
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", padx=16, pady=10)
        self.run_btn = ttk.Button(btn_frame, text="전자책 생성 시작",
                                  style="Run.TButton", command=self._start)
        self.run_btn.pack(fill="x", ipady=6)

        # ── 진행 상황 ─────────────────────────────────────────
        f5 = ttk.LabelFrame(parent, text="  진행 상황  ", padding=8)
        f5.pack(fill="x", **pad)

        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(f5, variable=self.progress_var,
                                             maximum=100, length=400)
        self.progress_bar.pack(fill="x", pady=(0, 8))

        self.progress_label = ttk.Label(f5, text="대기 중...", foreground="#666")
        self.progress_label.pack(anchor="w")

        self.log_area = scrolledtext.ScrolledText(
            f5, height=8, font=("Consolas", 9),
            state="disabled", wrap="word", relief="flat",
            background="#1E1E2E", foreground="#A8E6CF"
        )
        self.log_area.pack(fill="x", pady=(8, 0))

        # ── 하단 여백 ─────────────────────────────────────────
        ttk.Frame(parent).pack(pady=10)

    def _apply_prefill(self, prefill):
        for key in ("title", "subtitle", "author", "publisher", "isbn", "buga",
                    "keywords", "chapter_count", "cover_theme", "output_dir"):
            if key in prefill and key in self.vars:
                self.vars[key].set(prefill[key])
        if "draft" in prefill:
            self.draft_text.delete("1.0", tk.END)
            self.draft_text.insert("1.0", prefill["draft"])

    def _load_draft_file(self):
        path = filedialog.askopenfilename(
            title="초안 파일 선택",
            filetypes=[("텍스트 파일", "*.txt"), ("모든 파일", "*.*")]
        )
        if path:
            with open(path, encoding="utf-8", errors="replace") as f:
                content = f.read()
            self.draft_text.delete("1.0", tk.END)
            self.draft_text.insert("1.0", content)

    def _browse_output(self):
        d = filedialog.askdirectory(title="저장 폴더 선택")
        if d:
            self.vars["output_dir"].set(d)

    def _log(self, msg):
        self.root.after(0, self._append_log, msg)

    def _append_log(self, msg):
        self.log_area.configure(state="normal")
        self.log_area.insert(tk.END, msg + "\n")
        self.log_area.see(tk.END)
        self.log_area.configure(state="disabled")

    def _set_progress(self, val):
        self.root.after(0, lambda: [
            self.progress_var.set(val),
            self.progress_label.configure(text=f"진행률: {val}%")
        ])

    def _start(self):
        # 입력 검증
        required = {"title": "제목", "author": "저자명", "publisher": "출판사", "keywords": "키워드"}
        for key, label in required.items():
            if not self.vars[key].get().strip():
                messagebox.showwarning("입력 오류", f"[{label}]을(를) 입력해주세요.")
                return

        self.run_btn.configure(state="disabled", text="생성 중... (수 분 소요)")
        title = self.vars.get("title")
        if title:
            self.root.title(f"[생성중] {title.get()}")
        self.root.lower()  # 생성 시작 시 창을 뒤로 보내기
        if self.on_generation_start:
            self.on_generation_start()
        self.progress_var.set(0)
        self.log_area.configure(state="normal")
        self.log_area.delete("1.0", tk.END)
        self.log_area.configure(state="disabled")

        params = {k: v.get() for k, v in self.vars.items()}
        params["draft"] = self.draft_text.get("1.0", tk.END)

        thread = threading.Thread(
            target=run_generation,
            args=(params, self._log, self._set_progress, self._on_done),
            daemon=True
        )
        thread.start()

    def _on_done(self, output_path):
        def _update():
            self.run_btn.configure(state="normal", text="전자책 생성 시작")
            if output_path:
                self.progress_label.configure(text="완료!", foreground="#2ECC71")
                title = self.vars.get("title")
                if title:
                    self.root.title(f"[완료] {title.get()}")
                self.root.lift()  # 완료 시 창을 앞으로
                result = messagebox.askyesno(
                    "생성 완료",
                    f"전자책이 완성되었습니다!\n\n{output_path}\n\n파일을 열어볼까요?"
                )
                if result:
                    os.startfile(output_path)
                if self.on_book_done:
                    self.on_book_done(output_path)
            else:
                self.progress_label.configure(text="오류 발생 — 다시 시도하세요", foreground="#E74C3C")
                self.run_btn.configure(state="normal", text="다시 생성")
                messagebox.showerror("오류", "생성 중 오류가 발생했습니다.\n로그를 확인한 후 '다시 생성' 버튼을 눌러주세요.")
        self.root.after(0, _update)


# ════════════════════════════════════════════════════════════════
# 실행
# ════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # 중복 실행 방지 (락 파일 방식)
    import tempfile, atexit
    lock_path = os.path.join(tempfile.gettempdir(), "ebook_robot.lock")
    try:
        lock_fd = open(lock_path, "x")  # 이미 존재하면 FileExistsError
        atexit.register(lambda: (lock_fd.close(), os.remove(lock_path)))
    except FileExistsError:
        import tkinter.messagebox as mb
        _r = tk.Tk(); _r.withdraw()
        mb.showwarning("중복 실행", "전자책 로봇이 이미 실행 중입니다.")
        _r.destroy()
        sys.exit(0)
    root = tk.Tk()
    app = EbookRobotApp(root)
    root.mainloop()
