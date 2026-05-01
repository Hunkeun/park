# -*- coding: utf-8 -*-
"""
publisher 사이트 정합성 검증 도구.

세 곳이 같은 버전을 가리켜야 한다는 단일 정본 원칙 검증:
  1) books_master.json ↔ publisher/epubs/   파일 존재 + orphan 검출
  2) 외부 정본          ↔ publisher/epubs/   SHA256
                                              (시즌1 본권은 zip 본문 SHA — cover.jpg 제외)
  3) publisher/epubs/   ↔ Vercel 운영 사이트 샘플 N권 SHA256

사용 예:
  python verify_publisher.py                    # 3종 검증, 원격 5권 샘플
  python verify_publisher.py --local-only       # 외부·로컬 비교만
  python verify_publisher.py --remote-only      # Vercel 운영본 비교만
  python verify_publisher.py --sample 0         # 121권 전수 원격 검증 (느림)
  python verify_publisher.py --quiet            # OK면 한 줄, 깨졌을 때만 상세

종료 코드: 0 모든 검증 통과 / 1 정합성 실패
"""
# PATCHED:utf8-stdout-v1
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

import argparse
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

SITE = "https://ai-spirituality-books.vercel.app"

SEARCH_DIRS = [
    Path.home() / "Downloads" / "_부크크검수",
    Path.home() / "Downloads" / "_100권_확장본_검수",
    Path.home() / "Downloads" / "전자책",
    Path("tmp"),
]

DEFAULT_SAMPLE = ["s1-01", "s1-omnibus", "s2-001", "s2-050", "s2-omnibus-G05"]
COVER_PATH_IN_EPUB = "OEBPS/images/cover.jpg"

PUBLISHER = Path("publisher")
EPUBS_DIR = PUBLISHER / "epubs"
MASTER_PATH = PUBLISHER / "books_master.json"


def sha256_path(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def epub_body_sha(p: Path, exclude=(COVER_PATH_IN_EPUB,)) -> str:
    """epub zip 안의 모든 항목을 path 정렬 후 SHA256.
    표지 교체에 영향받지 않게 cover.jpg를 제외할 수 있음.
    """
    h = hashlib.sha256()
    with zipfile.ZipFile(p, "r") as z:
        for name in sorted(z.namelist()):
            if name in exclude:
                continue
            data = z.read(name)
            h.update(name.encode("utf-8"))
            h.update(b"\x00")
            h.update(hashlib.sha256(data).digest())
    return h.hexdigest()


def find_external(fn: str):
    if not fn:
        return None
    for d in SEARCH_DIRS:
        p = d / fn
        if p.exists():
            return p
    return None


def http_get(url: str, timeout: int = 30) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


# ─── 검증 단계 ────────────────────────────────────────────────────────────

def check_master_vs_epubs(master, quiet=False):
    """books_master.json에 등록된 권이 epubs/에 모두 있는지 + orphan 없는지."""
    expected = {b["id"] for b in master["books"]}
    have = {p.stem for p in EPUBS_DIR.glob("*.epub")} if EPUBS_DIR.exists() else set()
    missing = sorted(expected - have)
    orphans = sorted(have - expected)
    if not quiet:
        print(f"[1] books_master ↔ publisher/epubs/")
        print(f"    등록 {len(expected)}권 / 파일 {len(have)}개")
    if missing:
        print(f"    [실패] 누락 {len(missing)}권: {missing[:10]}")
    if orphans:
        print(f"    [경고] orphan {len(orphans)}개: {orphans[:10]}")
    if not quiet and not missing and not orphans:
        print(f"    [OK] 일치")
    return (not missing, missing, orphans)


def check_external_vs_pub(master, quiet=False):
    """외부 정본 vs publisher/epubs/."""
    s1_main_match = 0
    s1_main_diff = []
    s1_main_skip = []
    other_match = 0
    other_diff = []
    other_skip = []
    pub_missing = []

    for b in master["books"]:
        bid = b["id"]
        pub = EPUBS_DIR / f"{bid}.epub"
        if not pub.exists():
            pub_missing.append(bid)
            continue
        ext = find_external(b.get("epub_filename"))
        is_s1_main = (b.get("season") == 1 and b.get("type") == "main")

        if not ext:
            (s1_main_skip if is_s1_main else other_skip).append(bid)
            continue

        if is_s1_main:
            # cover.jpg 제외하고 본문 zip SHA 비교 (표지 교체 영향 차단)
            ext_sha = epub_body_sha(ext)
            pub_sha = epub_body_sha(pub)
            if ext_sha == pub_sha:
                s1_main_match += 1
            else:
                s1_main_diff.append((bid, ext_sha[:12], pub_sha[:12]))
        else:
            ext_sha = sha256_path(ext)
            pub_sha = sha256_path(pub)
            if ext_sha == pub_sha:
                other_match += 1
            else:
                ext_size = ext.stat().st_size
                pub_size = pub.stat().st_size
                other_diff.append((bid, ext_sha[:12], pub_sha[:12], ext_size, pub_size))

    s1_total = sum(1 for b in master["books"] if b.get("season") == 1 and b.get("type") == "main")
    other_total = len(master["books"]) - s1_total
    s1_compared = s1_total - len(s1_main_skip) - sum(1 for b in master["books"] if b.get("season")==1 and b.get("type")=="main" and b["id"] in pub_missing)
    other_compared = other_total - len(other_skip) - sum(1 for b in master["books"] if not (b.get("season")==1 and b.get("type")=="main") and b["id"] in pub_missing)

    if not quiet:
        print(f"[2] 외부 정본 ↔ publisher/epubs/")
        print(f"    시즌1 본권 (zip 본문 SHA, cover.jpg 제외): {s1_main_match}/{s1_total}")
        print(f"    그 외 (전체 SHA): {other_match}/{other_total}")
    if s1_main_diff:
        print(f"    [실패] 시즌1 본문 불일치 {len(s1_main_diff)}권:")
        for bid, e, p in s1_main_diff:
            print(f"      {bid}: ext {e} vs pub {p}")
    if other_diff:
        print(f"    [실패] 본문 불일치 {len(other_diff)}권 (publisher 캐시 stale):")
        for bid, e, p, es, ps in other_diff[:20]:
            print(f"      {bid}: ext {es:>9d}B {e} vs pub {ps:>9d}B {p}")
    if s1_main_skip or other_skip:
        skipped = s1_main_skip + other_skip
        print(f"    [경고] 외부 정본 못 찾아 비교 skip {len(skipped)}권: {skipped[:10]}")
    if pub_missing and not quiet:
        # check_master_vs_epubs에서 이미 보고했으므로 여기선 한 줄
        print(f"    [정보] publisher 캐시 없음 {len(pub_missing)}권은 이전 단계에서 보고")
    if not quiet and not s1_main_diff and not other_diff:
        print(f"    [OK] 일치")
    ok = (not s1_main_diff and not other_diff)
    return ok, s1_main_diff, other_diff, s1_main_skip + other_skip


def check_remote(master, sample, quiet=False):
    """Vercel 운영 사이트 epub과 로컬 publisher/epubs/ SHA256 비교."""
    if sample == 0:
        ids = [b["id"] for b in master["books"]]
    else:
        # 우선 사용자가 지정한 기본 샘플, 그 다음 부족분은 master에서 첫 N개 추가
        ids = [bid for bid in DEFAULT_SAMPLE if (EPUBS_DIR / f"{bid}.epub").exists()]
        if len(ids) < sample:
            for b in master["books"]:
                if b["id"] not in ids and (EPUBS_DIR / f'{b["id"]}.epub').exists():
                    ids.append(b["id"])
                    if len(ids) >= sample:
                        break
        ids = ids[:sample]

    if not quiet:
        kind = "전수" if sample == 0 else f"샘플 {len(ids)}권"
        print(f"[3] publisher/epubs/ ↔ Vercel ({kind})")

    diffs = []
    fails = []
    for bid in ids:
        local = EPUBS_DIR / f"{bid}.epub"
        if not local.exists():
            fails.append((bid, "로컬 파일 없음"))
            continue
        local_sha = sha256_path(local)
        url = f"{SITE}/epubs/{bid}.epub"
        try:
            data = http_get(url)
        except Exception as e:
            fails.append((bid, f"다운로드 실패: {e}"))
            continue
        remote_sha = sha256_bytes(data)
        if local_sha == remote_sha:
            if not quiet and sample != 0:
                print(f"    {bid:>20s}: [OK] {local_sha[:12]}")
        else:
            diffs.append((bid, local_sha[:12], remote_sha[:12]))
            print(f"    {bid:>20s}: [MISMATCH] local {local_sha[:12]} / remote {remote_sha[:12]}")

    if fails:
        print(f"    [경고] 검증 못한 {len(fails)}권:")
        for bid, msg in fails[:5]:
            print(f"      {bid}: {msg}")
    if not quiet and not diffs and not fails:
        print(f"    [OK] {len(ids)}권 모두 일치")
    return (not diffs, diffs, fails)


# ─── 메인 ─────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="publisher 사이트 정합성 검증")
    ap.add_argument("--local-only", action="store_true", help="원격(Vercel) 검증 생략")
    ap.add_argument("--remote-only", action="store_true", help="로컬·외부 검증 생략")
    ap.add_argument("--sample", type=int, default=5,
                    help="원격 샘플 권 수 (기본 5, 0 = 121권 전수)")
    ap.add_argument("--quiet", action="store_true", help="OK면 한 줄, 깨졌을 때만 상세")
    args = ap.parse_args()

    if not MASTER_PATH.exists():
        print(f"[실패] {MASTER_PATH} 없음. sync_publisher.py 먼저 실행하세요.")
        sys.exit(1)

    with open(MASTER_PATH, encoding="utf-8") as f:
        master = json.load(f)

    if not args.quiet:
        print(f"=== publisher 정합성 검증 ({master['total_count']}권) ===")

    overall = True

    if not args.remote_only:
        ok1, _, _ = check_master_vs_epubs(master, args.quiet)
        overall = overall and ok1
        ok2, _, _, _ = check_external_vs_pub(master, args.quiet)
        overall = overall and ok2

    if not args.local_only:
        ok3, _, _ = check_remote(master, args.sample, args.quiet)
        overall = overall and ok3

    if args.quiet:
        print("[OK] 정합성 통과" if overall else "[실패] 정합성 깨짐 (위 출력 참고)")
    else:
        print()
        print("=== 결과: " + ("[OK] 모든 검증 통과" if overall else "[실패] 정합성 깨짐") + " ===")

    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
