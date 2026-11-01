"""1단계: Gemini API(Google 검색 그라운딩)로 카테고리별 조사 → pipeline/raw/YYYY-MM-DD.json

LLM 호출은 카테고리 5회 + 종합 1회 = 하루 6회.
그라운딩 호출에는 JSON 강제 옵션을 쓰지 않고(모델·버전에 따라 도구와 동시 사용이 막힘)
텍스트에서 JSON을 추출한다. 파싱에 실패하면 그라운딩 없는 '변환 전용' 호출로 1회 복구한다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import sys
import time
from zoneinfo import ZoneInfo

from google import genai

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows 콘솔 한글 깨짐 방지
from google.genai import types

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import envload  # noqa: E402,F401  (.env 자동 로드)
from schema import CATEGORIES, CategoryResult, Synthesis  # noqa: E402

KST = ZoneInfo("Asia/Seoul")
ROOT = pathlib.Path(__file__).resolve().parent
PROMPTS = ROOT / "prompts"
RAW_DIR = ROOT / "raw"

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
SYNTH_MODEL = os.environ.get("GEMINI_SYNTH_MODEL", MODEL)
MAX_OUTPUT_TOKENS = int(os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", "24000"))
RETRIES = 2


def log(msg: str) -> None:
    print(f"[research] {msg}", flush=True)


def fill(template: str, **kw) -> str:
    """str.format 대신 단순 치환 (프롬프트 안에 JSON 중괄호가 있어서)."""
    for k, v in kw.items():
        template = template.replace("{" + k + "}", str(v))
    return template


def load_prompt(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8")


def extract_json(text: str):
    """모델 텍스트에서 첫 '{' ~ 마지막 '}' 구간을 JSON으로 파싱."""
    if not text:
        raise ValueError("empty response")
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.S)
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in response")
    return json.loads(t[start : end + 1])


def call_grounded(client: genai.Client, system: str, user: str):
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.3,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
    resp = client.models.generate_content(model=MODEL, contents=user, config=cfg)
    text = resp.text or ""
    grounding = []
    try:
        gm = resp.candidates[0].grounding_metadata
        for ch in gm.grounding_chunks or []:
            if ch.web and ch.web.uri:
                grounding.append({"title": ch.web.title or "", "url": ch.web.uri})
    except Exception:  # grounding_metadata가 없을 수 있음
        pass
    return text, grounding


def repair_json(client: genai.Client, text: str, schema_model):
    """그라운딩 없이, 스키마 강제 모드로 텍스트를 JSON으로 변환만 시킨다."""
    cfg = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema_model,
        temperature=0,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
    prompt = (
        "다음 텍스트를 내용 변경·추가·삭제 없이 지정된 JSON 스키마에 맞게 변환만 하라.\n\n" + text
    )
    resp = client.models.generate_content(model=MODEL, contents=prompt, config=cfg)
    return json.loads(resp.text or "")


def research_category(client, cat: dict, today: str, window_start: str, window_end: str) -> dict:
    system = fill(load_prompt("system.txt"), window_start=window_start, window_end=window_end)
    user = fill(
        load_prompt("category.txt"),
        today=today,
        category=cat["name"],
        category_desc=cat["desc"],
        category_code=cat["code"],
        n_min=cat["n_min"],
        n_max=cat["n_max"],
    )
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            t0 = time.time()
            text, grounding = call_grounded(client, system, user)
            try:
                data = extract_json(text)
            except Exception as e:
                log(f"{cat['name']}: JSON 추출 실패({e}) → 변환 호출로 복구")
                data = repair_json(client, text, CategoryResult)
            result = CategoryResult.model_validate(data)
            # id 누락/중복 방지: 순서대로 다시 부여
            for i, item in enumerate(result.items, 1):
                item.id = f"{cat['code']}-{i:02d}"
            log(f"{cat['name']}: {len(result.items)}건, 그라운딩 출처 {len(grounding)}개, {time.time() - t0:.0f}s")
            return {
                "name": cat["name"],
                "code": cat["code"],
                "items": [i.model_dump() for i in result.items],
                "grounding": grounding,
                "raw_text": text,
            }
        except Exception as e:  # 네트워크·할당량·검증 실패 등
            last_err = e
            log(f"{cat['name']}: 시도 {attempt} 실패: {e}")
            time.sleep(10 * attempt)
    log(f"{cat['name']}: 포기 (빈 결과로 진행) — {last_err}")
    return {"name": cat["name"], "code": cat["code"], "items": [], "grounding": [], "raw_text": "", "error": str(last_err)}


def synthesize(client, categories: list, today: str) -> dict:
    compact = [
        {
            "id": it["id"],
            "category": c["name"],
            "headline": it["headline"],
            "importance": it["importance"],
            "summary": it["summary"],
            "impact": it["impact"],
        }
        for c in categories
        for it in c["items"]
    ]
    if not compact:
        return Synthesis().model_dump(by_alias=True)
    prompt = fill(
        load_prompt("synthesis.txt"),
        today=today,
        all_category_json=json.dumps(compact, ensure_ascii=False, indent=0),
    )
    cfg = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=Synthesis,
        temperature=0.2,
        max_output_tokens=4000,
    )
    for attempt in range(1, RETRIES + 1):
        try:
            resp = client.models.generate_content(model=SYNTH_MODEL, contents=prompt, config=cfg)
            syn = Synthesis.model_validate(json.loads(resp.text or ""))
            log(f"종합: top5 {len(syn.top5)}개, 연결 {len(syn.connections)}개")
            return syn.model_dump(by_alias=True)
        except Exception as e:
            log(f"종합: 시도 {attempt} 실패: {e}")
            time.sleep(10 * attempt)
    return Synthesis().model_dump(by_alias=True)


def main(date: str | None = None, only: list[str] | None = None) -> pathlib.Path:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY 환경변수가 없습니다.")
    client = genai.Client(api_key=api_key)

    now = dt.datetime.now(KST)
    today = date or now.strftime("%Y-%m-%d")
    d = dt.date.fromisoformat(today)
    window_start = f"{(d - dt.timedelta(days=1)).isoformat()} 06:00"
    window_end = f"{d.isoformat()} 06:00"
    log(f"날짜 {today}, 모델 {MODEL}, 조사 창 {window_start} ~ {window_end}")

    cats = [c for c in CATEGORIES if not only or c["code"] in only]
    categories = [research_category(client, c, today, window_start, window_end) for c in cats]
    synthesis = synthesize(client, categories, today)

    RAW_DIR.mkdir(exist_ok=True)
    out = RAW_DIR / f"{today}.json"
    payload = {
        "date": today,
        "generated_at": now.isoformat(timespec="seconds"),
        "model": MODEL,
        "window": [window_start, window_end],
        "categories": categories,
        "synthesis": synthesis,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(len(c["items"]) for c in categories)
    log(f"저장: {out} (총 {total}건)")
    if total == 0:
        raise SystemExit("모든 카테고리 조사가 실패했습니다.")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD (기본: 오늘 KST)")
    ap.add_argument("--only", nargs="*", help="카테고리 코드만 (예: eco pol) — 테스트용")
    a = ap.parse_args()
    main(a.date, a.only)
