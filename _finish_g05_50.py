# -*- coding: utf-8 -*-
# PATCHED:utf8-stdout-v1
"""G05 50번 (관계의 상처를 넘어서) 마무리 자동화.

24h 한도 회복 후 한 번 실행하면:
  1) 50번 영상 업로드
  2) 재생목록 "흉터 위의 빛"에 50번 자동 추가 (41~49는 [스킵])
  3) youtube_map.json 50번 youtube_id 채움 + status 갱신
  4) sync_publisher.py (책방 사이트 갱신 + Vercel 배포)
  5) git commit (마무리)

실행: python -X utf8 _finish_g05_50.py
"""
import sys, os, re, json, subprocess
sys.stdout.reconfigure(encoding="utf-8")

PY = [sys.executable, "-X", "utf8"]


def run(cmd, *, must_succeed=True):
    print(f"\n>>> {' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd)
    if must_succeed and r.returncode != 0:
        print(f"[중단] returncode={r.returncode}", flush=True)
        sys.exit(r.returncode)
    return r.returncode


def read_video_id(path):
    with open(path, encoding="utf-8") as f:
        first = f.readline().strip()
    m = re.match(r"video_id:\s*(\S+)", first)
    if not m:
        raise RuntimeError(f"video_id 추출 실패: {path} -> {first!r}")
    return m.group(1)


def patch_youtube_map(vid):
    p = "youtube_map.json"
    with open(p, encoding="utf-8") as f:
        txt = f.read()
    new = re.sub(
        r'("season":\s*2,\s*"num":\s*50,[^\}]*?"youtube_id":\s*)""',
        rf'\1"{vid}"',
        txt
    )
    new = re.sub(
        r'"last_updated":\s*"[^"]*"',
        '"last_updated": "2026-05-03"',
        new
    )
    new = re.sub(
        r'"status":\s*"[^"]*"',
        '"status": "시즌 1 10권 + 시즌 2 G01·G02·G03·G04·G05 50권 영상화·업로드·재생목록 정렬 완료."',
        new
    )
    if new == txt:
        print("[경고] youtube_map.json 변경 없음 — 이미 처리되었거나 패턴 불일치")
    else:
        with open(p, "w", encoding="utf-8") as f:
            f.write(new)
        print(f"[갱신] youtube_map.json (num 50 youtube_id={vid})")


def main():
    # 1) 업로드
    run(PY + ["ebook_video_robot.py", "50", "--season", "2", "--step", "upload"])

    # 2) video_id 추출
    log = os.path.join("tmp", "s2_book50_video", "youtube_upload.txt")
    if not os.path.exists(log):
        print(f"[중단] {log} 없음 — 업로드 결과 확인 필요")
        sys.exit(2)
    vid = read_video_id(log)
    print(f"\n[추출] num 50 video_id = {vid}")

    # 3) youtube_map.json 갱신
    patch_youtube_map(vid)

    # 4) 재생목록 (50번만 [추가], 41~49는 [스킵] 되는 게 정상)
    run(PY + ["ebook_video_robot.py", "playlist", "--season", "2", "--group", "G05"])

    # 5) sync_publisher.py
    run(PY + ["sync_publisher.py"])

    # 6) git commit
    files = [
        "youtube_map.json",
        "publisher/books_master.json",
        "publisher/build_info.json",
        "publisher/catalog.html",
        "publisher/preview/s2-050.html",
        "publisher/preview/s2-omnibus-G05.html",
    ]
    run(["git", "add", *files])

    msg = (
        "G05 complete — book 50 uploaded, playlist now full (10/10)\n"
        "\n"
        f"book 50 (관계의 상처를 넘어서) → https://youtu.be/{vid}\n"
        '24-hour daily upload cap delayed this from yesterday\'s G05 batch.\n'
        '"흉터 위의 빛" playlist now contains all 10 episodes in order.\n'
        "\n"
        "Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>\n"
    )
    run(["git", "commit", "-m", msg])

    print("\n========== G05 마무리 완료 ==========")
    print(f"  num 50: https://youtu.be/{vid}")
    print(f"  재생목록: https://www.youtube.com/playlist?list=PLzjKIbpRzBBBxT-5mAH8adatzUK7Eb7gn")
    print(f"  책방 사이트: https://ai-spirituality-books.vercel.app")


if __name__ == "__main__":
    main()
