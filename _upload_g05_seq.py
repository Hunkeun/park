# -*- coding: utf-8 -*-
"""G05 권 순차 업로드 헬퍼.

인자로 받은 권수 리스트를 차례로 업로드한다.
연속 2권 실패 시 자동 중단(시스템 차원 오류로 판정).
모두 완료되면 자동으로 재생목록 등록까지 이어간다.
"""
import subprocess
import sys

BOOKS = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else []

if not BOOKS:
    print("usage: python _upload_g05_seq.py 41 42 43 44 45 46 47 48 49 50")
    sys.exit(1)

failures = 0
results = []
for num in BOOKS:
    print(f"\n========== Uploading book {num} ==========", flush=True)
    r = subprocess.run(
        [sys.executable, "-X", "utf8", "ebook_video_robot.py", str(num),
         "--season", "2", "--step", "upload"],
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

print("\n========== 업로드 결과 요약 ==========", flush=True)
ok_count = sum(1 for _, ok in results if ok)
for num, ok in results:
    print(f"  book {num}: {'OK' if ok else 'FAIL'}")
print(f"  총 {ok_count}/{len(results)} 성공", flush=True)

# 모두 성공하면 재생목록 등록까지 이어간다
if ok_count == len(BOOKS):
    print("\n========== 재생목록 등록 (G05: 흉터 위의 빛) ==========", flush=True)
    r = subprocess.run(
        [sys.executable, "-X", "utf8", "ebook_video_robot.py",
         "playlist", "--season", "2", "--group", "G05"],
    )
    if r.returncode == 0:
        print("[완료] 재생목록 등록 성공", flush=True)
    else:
        print(f"[FAIL] 재생목록 등록 실패 returncode={r.returncode}", flush=True)
else:
    print("\n[보류] 일부 권 업로드 실패 - 재생목록 등록 보류 (수동 확인 필요)", flush=True)
