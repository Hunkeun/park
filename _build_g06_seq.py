# -*- coding: utf-8 -*-
"""G06 권 순차 빌드 헬퍼. 인자로 받은 권수 리스트를 차례로 빌드한다.

연속 2권 실패 시 자동 중단(시스템 차원 오류로 판정).
"""
import subprocess
import sys

BOOKS = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else []

if not BOOKS:
    print("usage: python _build_g06_seq.py 51 52 53 54 55 56 57 58 59 60")
    sys.exit(1)

failures = 0
results = []
for num in BOOKS:
    print(f"\n========== Building book {num} ==========", flush=True)
    r = subprocess.run(
        [sys.executable, "-X", "utf8", "ebook_video_robot.py", str(num),
         "--season", "2", "--step", "build"],
    )
    ok = r.returncode == 0
    results.append((num, ok))
    if not ok:
        failures += 1
        print(f"[FAIL] book {num} returncode={r.returncode}", flush=True)
        if failures >= 2:
            print("[중단] 연속 2권 실패 - 시스템 차원 오류로 판정", flush=True)
            break
    else:
        failures = 0

print("\n========== 결과 요약 ==========")
for num, ok in results:
    print(f"  book {num}: {'OK' if ok else 'FAIL'}")
