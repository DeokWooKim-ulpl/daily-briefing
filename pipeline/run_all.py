"""전체 파이프라인: research → enrich → build_doc

사용:
  python pipeline/run_all.py                 # 오늘(KST) 브리핑. 이미 있으면 건너뜀 (재시도 cron 대비)
  python pipeline/run_all.py --force         # 있어도 다시 생성
  python pipeline/run_all.py --date 2026-11-01
  python pipeline/run_all.py --skip-research # raw가 이미 있을 때 enrich/doc만

pipeline/.env 파일이 있으면 읽는다 (로컬 테스트용, git에 올리지 말 것).
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import pathlib
import sys
from zoneinfo import ZoneInfo

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows 콘솔 한글 깨짐 방지

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def load_dotenv(path: pathlib.Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> None:
    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--skip-research", action="store_true")
    ap.add_argument("--skip-doc", action="store_true")
    a = ap.parse_args()

    date = a.date or dt.datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
    data_file = ROOT.parent / "docs" / "data" / f"{date}.json"
    if data_file.exists() and not a.force:
        print(f"[run_all] {date} 브리핑이 이미 있음 → 종료 (--force 로 재생성)")
        return

    import enrich  # noqa: E402
    import research  # noqa: E402

    if not a.skip_research:
        research.main(date)
    enrich.main(date)
    if not a.skip_doc:
        import build_doc  # noqa: E402

        build_doc.main(date, force=a.force)
    print(f"[run_all] 완료: {data_file}")


if __name__ == "__main__":
    main()
