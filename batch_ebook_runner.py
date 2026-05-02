# -*- coding: utf-8 -*-
"""
100권 전자책 배치 생성기
실행: python batch_ebook_runner.py
발간 순서: 라운드 방식 (그룹1-1, 그룹2-1, ..., 그룹10-1, 그룹1-2, ...)
"""
import os, sys, json, datetime, threading

# ebook_robot 모듈 불러오기
sys.path.insert(0, os.path.dirname(__file__))
import ebook_robot

OUTPUT_DIR  = os.path.join(os.path.expanduser("~"), "Downloads", "전자책")
BOOKS_JSON  = os.path.join(os.path.dirname(__file__), "batch_books.json")
PROGRESS_FILE = os.path.join(os.path.dirname(__file__), "batch_progress.json")
ISBN_FILE   = os.path.join(os.path.dirname(__file__), "isbn_list.json")


def load_isbn():
    if os.path.exists(ISBN_FILE):
        with open(ISBN_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

AUTHOR    = "AI, 박헌근"
PUBLISHER = "AI 시대 영성"
DATE      = "2026-04-25"
CHAPTERS  = 7
BUGA      = "05230"


def load_books():
    with open(BOOKS_JSON, encoding="utf-8") as f:
        groups = json.load(f)
    # 라운드 순서로 재정렬: seq=1 전체 → seq=2 전체 → ...
    max_seq = max(len(g["books"]) for g in groups)
    ordered = []
    for seq in range(1, max_seq + 1):
        for group in groups:
            for book in group["books"]:
                if book["seq"] == seq:
                    ordered.append({
                        "group_num":   group["group"],
                        "group_name":  group["group_name"],
                        "cover_theme": group["cover_theme"],
                        "seq":         book["seq"],
                        "title":       book["title"],
                        "subtitle":    book["subtitle"],
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
    log_print(f"[{global_num}/{total}] {book['title']} ({book['group_name']} {book['seq']}번)")
    log_print(f"{'='*60}")

    isbn_map = load_isbn()
    isbn = isbn_map.get(f"100-{serial}", "") if serial else ""
    if isbn:
        log_print(f"[ISBN] 100-{serial} → {isbn}")

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

    log_print(f"[배치 생성기] 총 {total}권 / 출력: {OUTPUT_DIR}")

    # 시작 번호 선택
    remaining = [(i, b) for i, b in enumerate(books) if book_key(b) not in progress]
    log_print(f"[대기] {len(remaining)}권 남음 / 완료: {total - len(remaining)}권")

    if not remaining:
        log_print("[완료] 모든 책이 이미 생성되었습니다.")
        return

    # 시작 번호 입력
    start_input = input(f"시작 번호를 입력하세요 (1~{len(remaining)}, 엔터=처음부터): ").strip()
    start_idx = 0
    if start_input.isdigit():
        start_idx = max(0, int(start_input) - 1)

    # serial = 그룹 블록 순서 (2026-04-24 정책 전환).
    # isbn_list.json 의 "100-N" 키는 그룹 블록 기준:
    #   100-1~10  = G01 S01~S10
    #   100-11~20 = G02 S01~S10
    #   ...
    #   100-91~100 = G10 S01~S10
    # 수식: serial = (group_num - 1) * 10 + seq
    for i, (original_idx, book) in enumerate(remaining[start_idx:], start=1):
        global_num = total - len(remaining) + start_idx + i
        key = book_key(book)
        serial = (book["group_num"] - 1) * 10 + book["seq"]

        path = generate_book(book, global_num, total, serial=serial)

        if path:
            progress[key] = {
                "title": book["title"],
                "path":  path,
                "date":  str(datetime.date.today())
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
