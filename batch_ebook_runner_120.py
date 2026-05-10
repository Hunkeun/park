# -*- coding: utf-8 -*-
# PATCHED:utf8-stdout-v1
"""
시즌 3 — 120권 전자책 배치 생성기 (대주제: 성경의 시선으로 파헤치는 관계의 비밀)
실행: python batch_ebook_runner_120.py
발간 순서: 라운드 방식 (G01-1, G02-1, ..., G12-1, G01-2, G02-2, ...)

시즌 2 batch_ebook_runner.py 와 다른 부분:
  - batch_books_120.json 은 {project, groups} dict 구조 (시즌2는 list)
  - 그룹 필드명 group_name → theme_name
  - ISBN 룩업 키 100-{N} → 120-{N}, 파일도 isbn_list_120books.json
  - 진행 추적 파일 분리 (batch_progress_120.json)
  - 출력 디렉토리도 분리 (~/Downloads/전자책_시즌3)
  - 발행일 2026-06-30 통일 (시즌 3 사용자 확정)

시즌 3 사후 패치 금지 원칙 (project_next_120books.md 참조):
  - ISBN 132건 사전 확보됐으므로 generation 시점에 반드시 주입
  - _patch_isbn_all.py 류 사후 패치 자매품을 시즌 3용으로 만들지 말 것
"""
import os, sys, json, datetime, threading

# ebook_robot 모듈 불러오기
sys.path.insert(0, os.path.dirname(__file__))
import ebook_robot

OUTPUT_DIR    = os.path.join(os.path.expanduser("~"), "Downloads", "전자책_시즌3")
BOOKS_JSON    = os.path.join(os.path.dirname(__file__), "batch_books_120.json")
PROGRESS_FILE = os.path.join(os.path.dirname(__file__), "batch_progress_120.json")
ISBN_FILE     = os.path.join(os.path.dirname(__file__), "isbn_list_120books.json")

AUTHOR    = "AI, 박헌근"
PUBLISHER = "AI 시대 영성"
DATE      = "2026-06-30"   # 시즌 3 발행일 (사용자 확정 2026-05-01)
CHAPTERS  = 7              # 권당 7장 / 22쪽 (project_next_120books.md)
BUGA      = "05230"        # 전자책 부가기호


def load_isbn():
    if os.path.exists(ISBN_FILE):
        with open(ISBN_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_books():
    """batch_books_120.json → 라운드 순서 책 리스트.

    시즌 3 구조: {project, groups: [{group, group_code, relation, theme_name,
                                     cover_theme, books: [{seq, title, hint,
                                     subtitle, keywords, insight, metaphor,
                                     questions}]}]}
    """
    with open(BOOKS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    groups = data["groups"]
    max_seq = max(len(g["books"]) for g in groups)
    ordered = []
    for seq in range(1, max_seq + 1):
        for group in groups:
            for book in group["books"]:
                if book["seq"] == seq:
                    ordered.append({
                        "group_num":   group["group"],
                        "group_name":  group["theme_name"],     # 시즌 3은 theme_name
                        "group_code":  group.get("group_code", f"G{group['group']:02d}"),
                        "relation":    group.get("relation", ""),
                        "cover_theme": group["cover_theme"],
                        "seq":         book["seq"],
                        "title":       book["title"],
                        "subtitle":    book.get("subtitle") or book.get("hint", ""),
                        "keywords":    book["keywords"],
                        "insight":     book["insight"],
                        "metaphor":    book["metaphor"],
                        "questions":   book["questions"],
                    })
    return ordered


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def book_key(book):
    return f"G{book['group_num']:02d}_S{book['seq']:02d}"


def make_draft(book):
    return f"""[인사이트] {book['insight']}

[비유] {book['metaphor']}

[영성 질문] {book['questions']}
"""


def log_print(msg):
    sys.stdout.buffer.write((msg + "\n").encode("utf-8"))
    sys.stdout.buffer.flush()


def generate_book(book, global_num, total, serial=None):
    log_print(f"\n{'='*60}")
    log_print(f"[{global_num}/{total}] {book['title']}  ({book['group_code']} {book['group_name']} {book['seq']}번)")
    log_print(f"{'='*60}")

    isbn_map = load_isbn()
    isbn_key = f"120-{serial}" if serial else None
    isbn = isbn_map.get(isbn_key, "") if isbn_key else ""
    if isbn:
        log_print(f"[ISBN] {isbn_key} → {isbn}")
    else:
        # 시즌 3는 사전 확보 132건이라 ISBN 누락은 사고. 빌드 중단해 사용자 인지.
        raise RuntimeError(
            f"[ISBN 누락] 키={isbn_key} / 책={book['title']}. "
            f"isbn_list_120books.json 확인 필요. 시즌 3는 사후 패치 금지."
        )

    params = {
        "title":         book["title"],
        "subtitle":      book["subtitle"],
        "author":        AUTHOR,
        "publisher":     PUBLISHER,
        "keywords":      book["keywords"],
        "chapter_count": str(CHAPTERS),
        "draft":         make_draft(book),
        "output_dir":    OUTPUT_DIR,
        "isbn":          isbn,
        "buga":          BUGA,
        "cover_theme":   book["cover_theme"],
    }

    result = {"done": False, "path": None, "error": None}
    event = threading.Event()

    def done_fn(path):
        result["done"] = True
        result["path"] = path
        event.set()

    def progress_fn(pct):
        pass

    thread = threading.Thread(
        target=ebook_robot.run_generation,
        args=(params, log_print, progress_fn, done_fn)
    )
    thread.start()
    event.wait()
    thread.join()

    if result["path"]:
        log_print(f"[완료] {result['path']}")
        return result["path"]
    else:
        log_print(f"[실패] {book['title']}")
        return None


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    books    = load_books()
    progress = load_progress()
    total    = len(books)

    log_print(f"[시즌 3 배치 생성기] 총 {total}권 / 출력: {OUTPUT_DIR}")
    log_print(f"  발행일: {DATE} / 출판사: {PUBLISHER} / 부가기호: {BUGA}")
    log_print(f"  ISBN 사전 확보: {ISBN_FILE}")

    remaining = [(i, b) for i, b in enumerate(books) if book_key(b) not in progress]
    log_print(f"[대기] {len(remaining)}권 남음 / 완료: {total - len(remaining)}권")

    if not remaining:
        log_print("[완료] 모든 책이 이미 생성되었습니다.")
        return

    start_input = input(f"시작 번호를 입력하세요 (1~{len(remaining)}, 엔터=처음부터): ").strip()
    start_idx = 0
    if start_input.isdigit():
        start_idx = max(0, int(start_input) - 1)

    # serial = 그룹 블록 순서 (시즌 2와 동일한 그룹 블록 매핑):
    #   120-1~10  = G01 S01~S10
    #   120-11~20 = G02 S01~S10
    #   ...
    #   120-111~120 = G12 S01~S10
    # 수식: serial = (group_num - 1) * 10 + seq
    for i, (original_idx, book) in enumerate(remaining[start_idx:], start=1):
        global_num = total - len(remaining) + start_idx + i
        key = book_key(book)
        serial = (book["group_num"] - 1) * 10 + book["seq"]

        try:
            path = generate_book(book, global_num, total, serial=serial)
        except RuntimeError as e:
            log_print(f"[중단] {e}")
            log_print(f"[중단] {book['title']} 생성 중단. 사용자 조치 후 재실행.")
            break

        if path:
            progress[key] = {
                "title":      book["title"],
                "group_code": book["group_code"],
                "path":       path,
                "date":       str(datetime.date.today()),
            }
            save_progress(progress)
        else:
            log_print(f"[주의] {book['title']} 생성 실패. 계속합니까? (엔터=계속, q=중단): ")
            ans = input().strip().lower()
            if ans == "q":
                break

    log_print("\n[배치 완료]")
    done_count = sum(1 for v in progress.values())
    log_print(f"완료: {done_count}/{total}권")


if __name__ == "__main__":
    main()
