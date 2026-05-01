# -*- coding: utf-8 -*-
"""
책방 사이트 단일 sync 스크립트.

순서: books_master -> qr_assets -> copy_epubs -> catalog -> previews -> vercel deploy -> verify

각 단계 진행 표시. 어느 단계든 실패하면 중단.
마지막 단계는 정합성 검증(verify_publisher.py): 외부 정본·publisher/epubs·Vercel 운영본
세 곳이 같은 버전인지 확인. 깨졌으면 즉시 알림.

옵션:
  --no-deploy    Vercel 배포 생략 (로컬만 갱신, verify는 --local-only로)
  --skip-deploy  동의어
  --skip-verify  정합성 검증 생략

실행: python sync_publisher.py
"""
# PATCHED:utf8-stdout-v1
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    _sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)
except AttributeError:
    pass


import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).parent
PUBLISHER = PROJECT / "publisher"

STAGES = [
    ("books_master", [sys.executable, "build_books_master.py"]),
    ("qr_assets",    [sys.executable, "build_qr_assets.py"]),
    ("copy_epubs",   [sys.executable, "copy_epubs_to_publisher.py"]),
    ("catalog",      [sys.executable, "build_catalog.py"]),
    ("previews",     [sys.executable, "build_previews.py"]),
]


def run_stage(name: str, cmd: list) -> None:
    started = datetime.now()
    print(f"\n--- [{name}] {started:%H:%M:%S} 시작 ---")
    result = subprocess.run(cmd, cwd=PROJECT, capture_output=False)
    if result.returncode != 0:
        elapsed = (datetime.now() - started).total_seconds()
        print(f"\n[중단] [{name}] 실패 (exit code {result.returncode}, {elapsed:.1f}s)")
        sys.exit(result.returncode)
    elapsed = (datetime.now() - started).total_seconds()
    print(f"--- [{name}] 완료 ({elapsed:.1f}s) ---")


def write_build_info() -> str:
    now = datetime.now()
    iso = now.strftime("%Y-%m-%d %H:%M:%S")

    with open(PUBLISHER / "books_master.json", encoding="utf-8") as f:
        master = json.load(f)

    info = {
        "updated_at": iso,
        "total_count": master.get("total_count", 0),
        "breakdown": master.get("breakdown", {}),
    }
    with open(PUBLISHER / "build_info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    return iso


def deploy() -> None:
    print(f"\n--- [vercel deploy] {datetime.now():%H:%M:%S} 시작 ---")
    result = subprocess.run(
        ["vercel", "deploy", "--cwd", "publisher", "--prod"],
        cwd=PROJECT, capture_output=False, shell=True,
    )
    if result.returncode != 0:
        print(f"\n[중단] [vercel deploy] 실패 (exit code {result.returncode})")
        sys.exit(result.returncode)
    print("--- [vercel deploy] 완료 ---")


def verify(local_only: bool) -> None:
    started = datetime.now()
    print(f"\n--- [verify] {started:%H:%M:%S} 시작 ---")
    cmd = [sys.executable, "-u", "verify_publisher.py", "--quiet"]
    if local_only:
        cmd.append("--local-only")
    result = subprocess.run(cmd, cwd=PROJECT, capture_output=False)
    elapsed = (datetime.now() - started).total_seconds()
    if result.returncode != 0:
        print(f"\n[경고] [verify] 정합성 검증 실패 ({elapsed:.1f}s).")
        print("  수동으로 확인: python verify_publisher.py")
        sys.exit(result.returncode)
    print(f"--- [verify] 완료 ({elapsed:.1f}s) ---")


def main():
    ap = argparse.ArgumentParser(description="책방 사이트 단일 sync 스크립트")
    ap.add_argument("--no-deploy", "--skip-deploy", action="store_true",
                    help="Vercel 배포 생략 (로컬만 갱신, verify도 로컬만)")
    ap.add_argument("--skip-verify", action="store_true",
                    help="정합성 검증 생략")
    args = ap.parse_args()

    overall_start = datetime.now()
    print(f"=== 책방 사이트 sync 시작 ({overall_start:%Y-%m-%d %H:%M:%S}) ===")

    for name, cmd in STAGES:
        run_stage(name, cmd)

    iso = write_build_info()
    print(f"\n[build_info.json] updated_at = {iso}")

    if not args.no_deploy:
        deploy()
    else:
        print("\n[건너뜀] Vercel 배포 (--no-deploy)")

    if not args.skip_verify:
        verify(local_only=args.no_deploy)
    else:
        print("\n[건너뜀] 정합성 검증 (--skip-verify)")

    elapsed = (datetime.now() - overall_start).total_seconds()
    print(f"\n=== 전체 완료 ({elapsed:.1f}s) ===")
    print(f"  마지막 갱신: {iso}")
    print(f"  사이트: https://ai-spirituality-books.vercel.app")


if __name__ == "__main__":
    main()
