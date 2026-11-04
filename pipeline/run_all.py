"""전체 파이프라인: research → enrich → build_doc

사용:
  python pipeline/run_all.py                 # 오늘(KST) 브리핑. 이미 있으면 건너뜀 (재시도 cron 대비)
  python pipeline/run_all.py --force         # 있어도 다시 생성
  python pipeline/run_all.py --date 2026-11-01
  python pipeline/run_all.py --skip-research # raw가 이미 있을 때 enrich/doc만
  python pipeline/run_all.py --source app    # 조사 단계를 Gemini 앱(작업 모드) 결과로 대체 (API 호출 없음)
  python pipeline/run_all.py --source app --strict  # 앱 문서가 없으면 오류
  python pipeline/run_all.py --source auto   # 앱 문서 있으면 그걸로, 없으면 조용히 종료(대기)
  python pipeline/run_all.py --source auto --api-fallback  # 앱 문서 없으면 API 로 생성 (마지막 회차용)

--source 를 생략하면 환경변수 BRIEF_SOURCE (auto | app | api, 기본 auto) 를 따른다.
auto 모드에서는 이미 API 로 만든 당일 브리핑이 있어도, 앱 문서가 나중에 생기면 앱 결과로 바꿔치기한다.

pipeline/.env 파일이 있으면 읽는다 (로컬 테스트용, git에 올리지 말 것).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys
from zoneinfo import ZoneInfo

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows 콘솔 한글 깨짐 방지

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


import envload  # noqa: E402,F401  (.env 자동 로드)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--skip-research", action="store_true")
    ap.add_argument("--skip-doc", action="store_true")
    ap.add_argument("--source", choices=["auto", "app", "api"], default=os.environ.get("BRIEF_SOURCE", "auto"))
    ap.add_argument("--strict", action="store_true", help="--source app 에서 문서가 없으면 오류로 종료")
    ap.add_argument("--api-fallback", action="store_true", help="--source auto 에서 앱 문서가 없으면 API 로 생성")
    a = ap.parse_args()

    date = a.date or dt.datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
    data_file = ROOT.parent / "docs" / "data" / f"{date}.json"

    existing_model = None
    if data_file.exists():
        try:
            existing_model = json.loads(data_file.read_text(encoding="utf-8")).get("model", "")
        except Exception:
            existing_model = ""
    if existing_model is not None and not a.force:
        # auto 모드: API 결과가 있어도 앱 문서가 새로 생겼으면 교체. 이미 앱 결과면 끝.
        if a.source == "auto" and existing_model != "gemini-app":
            print(f"[run_all] {date} 브리핑 있음 (model={existing_model}) → 앱 문서가 생겼는지 확인")
        else:
            print(f"[run_all] {date} 브리핑이 이미 있음 (model={existing_model}) → 종료 (--force 로 재생성)")
            return

    import enrich  # noqa: E402

    if not a.skip_research:
        use_app = a.source in ("app", "auto")
        got_app = False
        if use_app:
            import fetch_inbox  # noqa: E402

            got_app = fetch_inbox.main(date, strict=(a.source == "app" and a.strict)) is not None
        if not got_app:
            if a.source == "api" or (a.source == "auto" and a.api_fallback and existing_model is None):
                if a.source == "auto":
                    print("::warning::[run_all] 앱 문서 없음 → Gemini API 로 대체 생성")
                import research  # noqa: E402

                research.main(date)
            else:
                print(f"[run_all] {date}: Gemini 앱 문서 대기 중 → 종료 (다음 회차에서 다시 확인)")
                return
    enrich.main(date)
    if not a.skip_doc:
        import build_doc  # noqa: E402

        build_doc.main(date, force=a.force or existing_model is not None)
    print(f"[run_all] 완료: {data_file}")


if __name__ == "__main__":
    main()
