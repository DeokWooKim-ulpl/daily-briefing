"""2단계 (LLM 없음): raw/YYYY-MM-DD.json → docs/data/YYYY-MM-DD.json + docs/data/index.json

- 출처 URL 리다이렉트 해제 (그라운딩 redirect → 실제 기사 주소)
- 기사 og:image / og:site_name 수집 → 카드 썸네일·매체명
- 깨진 링크(4xx) 제거, 중복 출처 제거
- 카테고리 간 중복 사건 제거 + top5/연결 id 재매핑
- 스키마 검증 후 저장, 날짜 목록(index.json) 갱신
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import difflib
import json
import pathlib
import re
import sys
from urllib.parse import urljoin

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows 콘솔 한글 깨짐 방지
from bs4 import BeautifulSoup

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from schema import Brief, CategoryBlock, Connection, TopRef  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent
RAW_DIR = ROOT / "raw"
DATA_DIR = ROOT.parent / "docs" / "data"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 NewsBriefBot/1.0"
    ),
    "Accept-Language": "ko,en;q=0.8",
}
MAX_HTML = 400_000
DEAD_STATUSES = {404, 410, 451}
_session = requests.Session()


def log(msg: str) -> None:
    print(f"[enrich] {msg}", flush=True)


# ---------- 링크 해제 · og 메타 ----------

def _detect_charset(raw: bytes, header_enc: str | None) -> str:
    if header_enc and header_enc.lower() not in ("iso-8859-1",):
        return header_enc
    m = re.search(rb'charset=["\']?\s*([\w-]+)', raw[:4000], re.I)
    return m.group(1).decode("ascii", "ignore") if m else "utf-8"


def fetch(url: str) -> dict:
    """최종 URL, 상태코드, og 메타를 반환. 실패해도 예외를 던지지 않는다."""
    out = {"url": url, "final": url, "status": None, "og": {}}
    try:
        r = _session.get(url, headers=HEADERS, timeout=(5, 12), allow_redirects=True, stream=True)
        out["final"] = r.url
        out["status"] = r.status_code
        ctype = r.headers.get("content-type", "")
        if r.status_code < 400 and ("html" in ctype or ctype == ""):
            chunks, size = [], 0
            for chunk in r.iter_content(16384):
                chunks.append(chunk)
                size += len(chunk)
                if size >= MAX_HTML:
                    break
            raw = b"".join(chunks)
            html = raw.decode(_detect_charset(raw, r.encoding), errors="replace")
            out["og"] = parse_og(html, r.url)
        r.close()
    except Exception as e:  # 타임아웃, SSL, 연결 거부 등 → 원래 URL 유지
        out["error"] = str(e)[:120]
    return out


def parse_og(html: str, base: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    og = {}

    def meta(*names):
        for n in names:
            tag = soup.find("meta", attrs={"property": n}) or soup.find("meta", attrs={"name": n})
            if tag and tag.get("content"):
                return tag["content"].strip()
        return None

    img = meta("og:image", "og:image:url", "twitter:image", "twitter:image:src")
    if img:
        og["image"] = urljoin(base, img)
    site = meta("og:site_name", "application-name", "twitter:site")
    if site:
        og["site_name"] = site.lstrip("@")
    title = meta("og:title", "twitter:title")
    if title:
        og["title"] = title
    return og


def _is_redirector(url: str) -> bool:
    return "grounding-api-redirect" in url or "vertexaisearch" in url


# ---------- 항목 처리 ----------

def enrich_item(item: dict, use_network: bool) -> dict:
    sources = item.get("sources") or []
    if not use_network:
        return item
    results = []
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(lambda s: fetch(s["url"]), sources))

    kept, seen = [], set()
    image = None
    for s, r in zip(sources, results):
        if r["status"] in DEAD_STATUSES:
            continue
        final = r["final"]
        if _is_redirector(final) and r.get("error"):
            final = s["url"]  # 해제 실패 시 원 URL 유지 (사람이 열면 열림)
        key = re.sub(r"[#?].*$", "", final).rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        og = r["og"]
        kept.append(
            {
                "title": (s.get("title") or og.get("title") or final)[:120],
                "publisher": s.get("publisher") or og.get("site_name") or "",
                "url": final,
            }
        )
        if not image and og.get("image"):
            image = og["image"]
    item["sources"] = kept
    item["image"] = image
    return item


def _norm(s: str) -> str:
    return re.sub(r"[\s\W_]+", "", s or "").lower()


def _similar(a: dict, b: dict) -> bool:
    """제목이 많이 겹치거나, 제목이 어느 정도 겹치면서 요약까지 비슷하면 같은 사건으로 본다."""
    h = difflib.SequenceMatcher(None, _norm(a["headline"]), _norm(b["headline"])).ratio()
    if h >= 0.65:
        return True
    if h < 0.4:
        return False
    s = difflib.SequenceMatcher(None, _norm(a.get("summary", ""))[:300], _norm(b.get("summary", ""))[:300]).ratio()
    return s >= 0.6


def dedupe(categories: list[dict]) -> dict[str, str]:
    """카테고리 간 같은 사건 제거. 반환: 제거된 id → 남긴 id 매핑."""
    remap: dict[str, str] = {}
    all_items = [(ci, it) for ci, c in enumerate(categories) for it in c["items"]]
    removed: set[str] = set()
    for i, (ci, a) in enumerate(all_items):
        if a["id"] in removed:
            continue
        for cj, b in all_items[i + 1 :]:
            if ci == cj or b["id"] in removed:
                continue
            if _similar(a, b):
                loser, winner = (b, a) if a["importance"] >= b["importance"] else (a, b)
                removed.add(loser["id"])
                remap[loser["id"]] = winner["id"]
                # 출처는 합친다
                urls = {s["url"] for s in winner["sources"]}
                winner["sources"] += [s for s in loser["sources"] if s["url"] not in urls]
                if loser is a:
                    break
    for c in categories:
        c["items"] = [it for it in c["items"] if it["id"] not in removed]
    if removed:
        log(f"중복 제거 {len(removed)}건: {sorted(removed)}")
    return remap


def build_brief(raw: dict, use_network: bool, sample: bool) -> Brief:
    categories = [
        {"name": c["name"], "code": c["code"], "items": [enrich_item(dict(it), use_network) for it in c["items"]]}
        for c in raw["categories"]
    ]
    remap = dedupe(categories)
    valid_ids = {it["id"] for c in categories for it in c["items"]}

    def fix(i: str) -> str | None:
        i = remap.get(i, i)
        return i if i in valid_ids else None

    syn = raw.get("synthesis") or {}
    top5, seen = [], set()
    for t in syn.get("top5") or []:
        ref = fix(t.get("ref", ""))
        if ref and ref not in seen:
            seen.add(ref)
            top5.append(TopRef(ref=ref, why=t.get("why", "")))
    if not top5:  # 종합 실패 시 중요도순 상위 5개
        ranked = sorted((it for c in categories for it in c["items"]), key=lambda x: -x["importance"])
        top5 = [TopRef(ref=it["id"], why=it["summary"].split(".")[0]) for it in ranked[:5]]

    connections = []
    for cn in syn.get("connections") or []:
        a, b = fix(cn.get("from", "")), fix(cn.get("to", ""))
        if a and b and a != b:
            connections.append(Connection(from_id=a, to=b, how=cn.get("how", "")))

    return Brief(
        date=raw["date"],
        generated_at=raw.get("generated_at") or dt.datetime.now().isoformat(timespec="seconds"),
        model=raw.get("model", ""),
        sample=sample,
        one_liner=syn.get("one_liner", ""),
        top5=top5,
        connections=connections,
        categories=[CategoryBlock(**c) for c in categories],
        doc_saved_at=(raw.get("source_doc") or {}).get("updated"),
    )


def write_index() -> list[str]:
    dates = sorted(
        (p.stem for p in DATA_DIR.glob("*.json") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem)),
        reverse=True,
    )
    (DATA_DIR / "index.json").write_text(json.dumps(dates, ensure_ascii=False), encoding="utf-8")
    return dates


def main(date: str, raw_path: pathlib.Path | None = None, use_network: bool = True, sample: bool = False) -> pathlib.Path:
    raw_path = raw_path or RAW_DIR / f"{date}.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    brief = build_brief(raw, use_network, sample)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / f"{brief.date}.json"
    out.write_text(brief.model_dump_json(by_alias=True, indent=1), encoding="utf-8")
    n_items = sum(len(c.items) for c in brief.categories)
    n_img = sum(1 for c in brief.categories for it in c.items if it.image)
    log(f"저장: {out} ({n_items}건, 썸네일 {n_img}건)")
    dates = write_index()
    log(f"index.json: {len(dates)}일치")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--raw", help="raw JSON 경로 (기본: pipeline/raw/DATE.json)")
    ap.add_argument("--no-network", action="store_true", help="링크 해제·이미지 수집 생략")
    ap.add_argument("--sample", action="store_true", help="샘플 데이터 표시")
    a = ap.parse_args()
    main(a.date, pathlib.Path(a.raw) if a.raw else None, not a.no_network, a.sample)
