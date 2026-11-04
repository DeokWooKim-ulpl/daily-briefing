"""1단계 대체 (Gemini API 대신 Gemini 앱 '작업 모드'): Drive inbox 문서 → raw/YYYY-MM-DD.json

흐름:
  Gemini 앱 작업 모드가 매일 Drive "뉴스브리핑/inbox/YYYY-MM-DD.json" (Google Docs)에 JSON 텍스트를 저장
  → 이 스크립트가 Apps Script 웹앱(GET ?mode=inbox)으로 본문을 받아
  → JSON을 꺼내 검증한 뒤 research.py 와 똑같은 raw 형식으로 저장한다.
  이후 enrich.py / build_doc.py 는 그대로 동작한다 (Gemini API 호출 0회).

사용:
  python pipeline/fetch_inbox.py --date 2026-11-05
  python pipeline/fetch_inbox.py --date 2026-11-05 --strict   # 문서가 없으면 오류 종료 (마지막 재시도용)

환경변수: APPS_SCRIPT_URL, APPS_SCRIPT_SECRET (build_doc.py 와 동일)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import sys
from zoneinfo import ZoneInfo

import requests

import envload  # noqa: F401  (.env 자동 로드)
from schema import CATEGORIES, CODE_BY_NAME, Item, Synthesis

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent
RAW_DIR = ROOT / "raw"
KST = ZoneInfo("Asia/Seoul")
TIMEOUT = 120


def log(msg: str) -> None:
    print(f"[fetch_inbox] {msg}", flush=True)


# ---------- 1. Apps Script 호출 ----------
class InboxUnavailable(Exception):
    """문서를 쓸 수 없는 모든 경우 (아직 없음 / 설정 오류 / 형식 오류). 메시지에 이유."""

    def __init__(self, reason: str, waiting: bool = False):
        super().__init__(reason)
        self.waiting = waiting  # True = "아직 없음" (정상 대기), False = 설정·형식 문제 (경고)


def fetch_text(date: str) -> dict:
    """Apps Script에서 {ok, text, name, url, ...} 를 받는다."""
    url = os.environ.get("APPS_SCRIPT_URL")
    secret = os.environ.get("APPS_SCRIPT_SECRET")
    if not url or not secret:
        raise InboxUnavailable("APPS_SCRIPT_URL / APPS_SCRIPT_SECRET 환경변수가 없음")
    try:
        r = requests.get(url, params={"mode": "inbox", "date": date, "secret": secret}, timeout=TIMEOUT, allow_redirects=True)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        raise InboxUnavailable(f"Apps Script 호출 실패: {e}")
    except ValueError:
        raise InboxUnavailable(f"Apps Script 응답이 JSON이 아님 (앞 200자): {r.text[:200]}")
    if not data.get("ok"):
        if data.get("error") == "not_found":
            raise InboxUnavailable(f"{date} 문서가 아직 없음 (Gemini 앱 작업이 안 끝났거나 저장 위치가 다름)", waiting=True)
        raise InboxUnavailable(f"Apps Script 오류: {data.get('error')}")
    if "text" not in data:  # 옛 버전 Code.gs (inbox 기능 없음) 가 배포된 상태
        raise InboxUnavailable("Apps Script가 옛 버전임 — Code.gs 교체 후 '새 버전' 배포 필요")
    return data


# ---------- 2. 본문에서 JSON 꺼내기 ----------
_FENCE = re.compile(r"```[a-zA-Z]*\s*|```", re.M)


def repair_quotes(body: str) -> str:
    """문자열 안에 이스케이프 안 된 큰따옴표가 있으면 \\" 로 바꾼다.
    (예: "title": "李 "국가 미래…"…당부")  — Gemini 앱이 규칙을 어기고 자주 내는 오류.
    판정: 문자열 안에서 만난 " 다음에 공백을 건너뛴 첫 글자가 , } ] : 이면 닫는 따옴표, 아니면 내부 따옴표."""
    out, in_str, i, n = [], False, 0, len(body)
    while i < n:
        ch = body[i]
        if not in_str:
            if ch == '"':
                in_str = True
            out.append(ch)
        elif ch == "\\":  # 이스케이프 시퀀스는 그대로 두 글자 복사
            out.append(body[i : i + 2])
            i += 1
        elif ch == '"':
            k = i + 1
            while k < n and body[k] in " \t\r\n":
                k += 1
            if k >= n or body[k] in ",}]:":
                in_str = False
                out.append(ch)
            else:
                out.append('\\"')
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def extract_json(text: str) -> dict:
    """코드펜스·머리말이 섞여 있어도 첫 '{' ~ 마지막 '}' 만 잘라 파싱한다. 흔한 형식 오류는 단계적으로 보정."""
    t = _FENCE.sub("", text).replace(" ", " ").strip()
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        raise ValueError("본문에 JSON 객체({ ... })가 없음")
    body = t[i : j + 1]
    # 1차: 그대로 / 2차: 스마트 따옴표·후행 쉼표 정리 / 3차: 문자열 안 큰따옴표 이스케이프
    fixed = body.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    fixed = re.sub(r",\s*([}\]])", r"\1", fixed)
    attempts = [body, fixed, repair_quotes(fixed)]
    first_err = None
    for k, cand in enumerate(attempts, start=1):
        try:
            data = json.loads(cand, strict=False)  # strict=False: 문자열 안 실제 줄바꿈 허용
            if k > 1:
                log(f"JSON 보정 {k}단계로 파싱 성공")
            return data
        except json.JSONDecodeError as e:
            first_err = first_err or e
    raise ValueError(f"JSON 파싱 실패: {first_err}")


# ---------- 3. research.py raw 형식으로 정규화 ----------
def normalize(data: dict, date: str, src: dict) -> dict:
    by_code = {c["code"]: c for c in CATEGORIES}
    categories = []
    for c in data.get("categories") or []:
        code = c.get("code") or CODE_BY_NAME.get(c.get("name", ""))
        if code not in by_code:
            log(f"알 수 없는 카테고리 건너뜀: {c.get('name')!r}/{c.get('code')!r}")
            continue
        items = []
        for k, it in enumerate(c.get("items") or [], start=1):
            it = dict(it)
            it.setdefault("id", f"{code}-{k:02d}")
            if not it.get("headline"):
                continue
            try:
                items.append(Item.model_validate(it).model_dump())
            except Exception as e:  # 항목 하나가 깨져도 나머지는 살린다
                log(f"{code} {k}번째 항목 무시: {e}")
        categories.append({"name": by_code[code]["name"], "code": code, "items": items, "grounding": [], "raw_text": ""})
    # Gemini가 빠뜨린 카테고리는 빈 블록으로 (앱 탭 순서 유지)
    have = {c["code"] for c in categories}
    for c in CATEGORIES:
        if c["code"] not in have:
            log(f"카테고리 누락: {c['name']}")
            categories.append({"name": c["name"], "code": c["code"], "items": [], "grounding": [], "raw_text": ""})
    categories.sort(key=lambda c: [x["code"] for x in CATEGORIES].index(c["code"]))

    try:
        synthesis = Synthesis.model_validate(
            {"top5": data.get("top5") or [], "connections": data.get("connections") or [], "one_liner": data.get("one_liner") or ""}
        ).model_dump(by_alias=True)
    except Exception as e:
        log(f"종합(top5/연결) 형식 오류 → enrich가 중요도순으로 대체: {e}")
        synthesis = Synthesis().model_dump(by_alias=True)

    d = dt.date.fromisoformat(date)
    return {
        "date": date,
        "generated_at": dt.datetime.now(KST).isoformat(timespec="seconds"),
        "model": "gemini-app",
        "source_doc": {"name": src.get("name"), "url": src.get("url"), "updated": src.get("updated"), "where": src.get("where")},
        "window": [f"{(d - dt.timedelta(days=1)).isoformat()} 06:00", f"{d.isoformat()} 06:00"],
        "categories": categories,
        "synthesis": synthesis,
    }


def warn(msg: str) -> None:
    """GitHub Actions 에서는 실행 요약에 노란 경고로 표시된다."""
    print(f"::warning::[fetch_inbox] {msg}", flush=True)


def _build(today: str) -> pathlib.Path:
    """문서 조회 → JSON → raw 저장. 실패는 InboxUnavailable 로 던진다."""
    src = fetch_text(today)
    log(f"문서: {src.get('name')} ({src.get('where')}, 수정 {src.get('updated')}) {len(src.get('text') or '')}자")
    RAW_DIR.mkdir(exist_ok=True)
    (RAW_DIR / f"{today}.inbox.txt").write_text(src.get("text") or "", encoding="utf-8")  # 디버그용 원문
    try:
        data = extract_json(src.get("text") or "")
    except ValueError as e:
        raise InboxUnavailable(f"{e} — 원문은 Actions 아티팩트 raw/{today}.inbox.txt 참고")
    payload = normalize(data, today, src)
    total = sum(len(c["items"]) for c in payload["categories"])
    if total == 0:
        raise InboxUnavailable("문서에 뉴스 항목이 하나도 없음")
    out = RAW_DIR / f"{today}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"저장: {out} (총 {total}건, top5 {len(payload['synthesis']['top5'])}개)")
    return out


def main(date: str | None = None, strict: bool = False) -> pathlib.Path | None:
    """성공: raw 경로. 사용 불가: None (strict 면 SystemExit). '아직 없음'은 로그만, 그 외는 경고."""
    today = date or dt.datetime.now(KST).strftime("%Y-%m-%d")
    log(f"날짜 {today}: Drive inbox 문서 조회")
    try:
        return _build(today)
    except InboxUnavailable as e:
        if strict:
            raise SystemExit(str(e))
        (log if e.waiting else warn)(f"{e} → 이번 회차 건너뜀")
        return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD (기본: 오늘 KST)")
    ap.add_argument("--strict", action="store_true", help="문서가 없으면 오류로 종료")
    a = ap.parse_args()
    main(a.date, a.strict)
