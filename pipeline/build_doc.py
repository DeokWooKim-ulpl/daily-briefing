"""3단계 (LLM 없음): docs/data/YYYY-MM-DD.json → Google Docs

Apps Script 웹앱(apps_script/Code.gs)에 JSON을 POST하면 스크립트가 본인 계정으로
Drive "뉴스브리핑/YYYY/MM/YYYY-MM-DD 뉴스브리핑" 문서를 만든다.
환경변수 APPS_SCRIPT_URL / APPS_SCRIPT_SECRET 이 없으면 생략하고 정상 종료한다.
생성된 문서 URL은 JSON의 doc_url 에 기록되어 앱에서 '문서 열기' 링크로 쓰인다.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows 콘솔 한글 깨짐 방지

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "docs" / "data"


def log(msg: str) -> None:
    print(f"[build_doc] {msg}", flush=True)


def main(date: str, force: bool = False) -> str | None:
    url = os.environ.get("APPS_SCRIPT_URL")
    secret = os.environ.get("APPS_SCRIPT_SECRET")
    if not url or not secret:
        log("APPS_SCRIPT_URL / APPS_SCRIPT_SECRET 없음 → Google Docs 생성 생략")
        return None
    path = DATA_DIR / f"{date}.json"
    brief = json.loads(path.read_text(encoding="utf-8"))
    if brief.get("doc_url") and not force:
        log(f"이미 문서 있음: {brief['doc_url']}")
        return brief["doc_url"]

    r = requests.post(
        url,
        json={"secret": secret, "force": force, "brief": brief},
        timeout=(10, 300),
        allow_redirects=True,  # Apps Script는 302 → googleusercontent 로 응답을 돌려준다
    )
    try:
        data = r.json()
    except ValueError:
        raise SystemExit(f"Apps Script 응답이 JSON이 아님 (HTTP {r.status_code}): {r.text[:300]}")
    if not data.get("ok"):
        raise SystemExit(f"Apps Script 오류: {data.get('error')}")
    brief["doc_url"] = data["url"]
    path.write_text(json.dumps(brief, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"문서 생성: {data['url']}")
    return data["url"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--force", action="store_true", help="같은 날짜 문서가 있으면 지우고 다시 생성")
    a = ap.parse_args()
    main(a.date, a.force)
