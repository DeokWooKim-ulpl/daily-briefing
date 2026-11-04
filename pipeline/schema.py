"""데이터 스키마 — Gemini 출력, enrich 결과, 앱 JSON, Google Docs가 모두 이 구조를 공유한다."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# 카테고리 정의 (research.py가 순회, 앱 탭 순서와 동일)
CATEGORIES = [
    {
        "name": "경제",
        "code": "eco",
        "desc": "금리·환율·물가·증시·부동산·기업 실적·무역. 한국 중심 + 미국·중국 거시 흐름",
        "n_min": 5,
        "n_max": 6,
    },
    {
        "name": "정치",
        "code": "pol",
        "desc": "국회·정부·대통령실·정당·선거·외교안보 정책 결정. 한국 중심",
        "n_min": 4,
        "n_max": 5,
    },
    {
        "name": "사회·사건사고",
        "code": "soc",
        "desc": "대형 사고·재난·범죄·판결·노동·보건·교육 중 사회적 파급이 큰 것",
        "n_min": 4,
        "n_max": 5,
    },
    {
        "name": "국제",
        "code": "intl",
        "desc": "전쟁·분쟁·주요국 선거·정상회담·제재·국제기구 결정. 한국에 미치는 영향을 명시",
        "n_min": 4,
        "n_max": 5,
    },
    {
        "name": "산업·기술",
        "code": "tech",
        "desc": "반도체·AI·에너지·자동차·바이오·플랫폼 규제, 기업 전략 변화",
        "n_min": 4,
        "n_max": 5,
    },
]
CODE_BY_NAME = {c["name"]: c["code"] for c in CATEGORIES}


class Source(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str = ""
    publisher: str = ""
    url: str


class Item(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    headline: str
    importance: int = 3
    summary: str = ""
    impact: List[str] = Field(default_factory=list)
    detail: str = ""
    watch_next: str = ""
    keywords: List[str] = Field(default_factory=list)
    entities: List[str] = Field(default_factory=list)
    sources: List[Source] = Field(default_factory=list)
    image: Optional[str] = None  # enrich.py가 og:image로 채움

    @field_validator("importance", mode="before")
    @classmethod
    def _clamp(cls, v):
        try:
            v = int(round(float(v)))
        except (TypeError, ValueError):
            return 3
        return max(1, min(5, v))

    @field_validator("impact", "keywords", "entities", mode="before")
    @classmethod
    def _listify(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [s.strip("-• ").strip() for s in v.splitlines() if s.strip()]
        return [str(x) for x in v if str(x).strip()]


class CategoryResult(BaseModel):
    """research.py의 카테고리별 Gemini 응답."""
    model_config = ConfigDict(extra="ignore")
    date: str = ""
    category: str = ""
    items: List[Item] = Field(default_factory=list)


class TopRef(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ref: str
    why: str = ""


class Connection(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    from_id: str = Field(alias="from")
    to: str
    how: str = ""


class Synthesis(BaseModel):
    """research.py의 종합(6번째) 응답."""
    model_config = ConfigDict(extra="ignore")
    top5: List[TopRef] = Field(default_factory=list)
    connections: List[Connection] = Field(default_factory=list)
    one_liner: str = ""


class CategoryBlock(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    code: str
    items: List[Item] = Field(default_factory=list)


class Brief(BaseModel):
    """앱이 읽는 최종 JSON (docs/data/YYYY-MM-DD.json)."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    date: str
    generated_at: str
    model: str = ""
    sample: bool = False
    one_liner: str = ""
    top5: List[TopRef] = Field(default_factory=list)
    connections: List[Connection] = Field(default_factory=list)
    categories: List[CategoryBlock] = Field(default_factory=list)
    doc_url: Optional[str] = None
    doc_saved_at: Optional[str] = None  # Gemini 앱 문서가 Drive 에 저장된 시각 (app 모드일 때만)
