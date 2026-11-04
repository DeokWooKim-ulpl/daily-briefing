"""GitHub Actions 실행 요약(Job Summary)용 한 줄 보고. 사용: python pipeline/summary.py --date YYYY-MM-DD"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
from zoneinfo import ZoneInfo

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "docs" / "data"


def main(date: str | None) -> None:
    date = date or dt.datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
    f = DATA_DIR / f"{date}.json"
    print(f"## 뉴스브리핑 {date}")
    if not f.exists():
        print("- 상태: 아직 없음 (Gemini 앱 문서 대기 중)")
        return
    b = json.loads(f.read_text(encoding="utf-8"))
    n = sum(len(c["items"]) for c in b.get("categories", []))
    print(f"- 상태: **있음** · 출처: `{b.get('model')}` · {n}건 · 생성 {(b.get('generated_at') or '')[:16]}")
    if b.get("doc_saved_at"):
        print(f"- Gemini 앱 문서 저장 시각: {b['doc_saved_at'][:16]}")
    if b.get("doc_url"):
        print(f"- Google Docs: {b['doc_url']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    main(ap.parse_args().date)
