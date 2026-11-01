# 나만의 데일리 뉴스 브리핑 앱 — 구축 계획

작성일: 2026-10-31

## 0. 한 줄 요약

매일 06:00 KST에 **GitHub Actions(무료 cron)** 가 Python을 실행 → **Gemini API(Google 검색 그라운딩)** 로 카테고리별 조사 → 결과를 **JSON(앱용) + Google Docs(보관용)** 으로 저장 → **정적 PWA(카드뉴스 UI)** 가 JSON을 읽어 PC·안드로이드에서 표시. LLM 호출은 하루 6회(카테고리 5 + 종합 1), 나머지는 전부 Python.

```
 06:00 KST  GitHub Actions (cron)
     │
     ├─ research.py ── Gemini API ×6 (검색 그라운딩, JSON 강제 출력)
     │
     ├─ enrich.py  ── [LLM 없음] 링크 리다이렉트 해제 · og:image 썸네일 수집 · 중복/깨진 링크 제거 · 스키마 검증
     │
     ├─ build_doc.py ─ [LLM 없음] JSON → Google Docs 생성 → Drive "뉴스브리핑/2026/10/2026-10-31 뉴스브리핑"
     │
     └─ git commit  ── docs/data/2026-10-31.json + index.json 갱신 → GitHub Pages 자동 배포
                                                                          │
                                        PC 브라우저 / 안드로이드 홈화면(PWA) ◀┘
```

## 1. 왜 이 구조인가 (요청사항 대응)

| 요청 | 결정 | 이유 |
|---|---|---|
| Gemini가 매일 06:00 자동 조사 | Gemini **API** + GitHub Actions cron | Gemini 앱의 "예약 작업"은 결과가 채팅/알림으로 오고, Docs 저장은 프롬프트에 써넣는 우회법이라 매일 같은 구조로 저장되는 보장이 없음. API는 JSON 스키마를 강제할 수 있어 앱이 파싱 실패 없이 읽음 |
| 매우 상세한 조사 | 카테고리별 **별도 호출** (경제·정치·사회/사건사고·국제·산업/기술) + 종합 1회 | 한 번에 다 시키면 항목당 깊이가 얕아짐. 호출을 나누면 항목당 500~1200자 상세 + 출처 2~4개 확보 가능 |
| Google Docs로 날짜별 보관 | Python이 JSON → Docs 변환 후 지정 폴더에 저장 | 사람이 읽기 좋은 아카이브. 앱은 Docs를 직접 읽지 않고 JSON을 읽음 → 앱에 Google 로그인/권한 불필요 |
| 사진 | 기사 URL의 **og:image** 메타태그를 Python으로 수집 | LLM 토큰 0. 실패 시 카테고리 색 플레이스홀더 |
| 원문 링크 | 그라운딩이 돌려준 URL을 Python이 실제 기사 URL로 해제(리다이렉트 추적) | 그라운딩 URL은 `vertexaisearch.../grounding-api-redirect/...` 형태라 그대로 쓰면 보기 나쁨 |
| 요약 + 파급 | 항목마다 `summary`(3문장), `impact`(불릿 2~5), `watch_next`(다음에 볼 것) | 담배 한 대 시간에 읽는 분량 |
| LLM 최소화 | 하루 6회 호출, 그 외 전부 Python | 월 ~180회 그라운딩. Gemini 3 계열 무료 할당(월 5,000회)에 한참 못 미침 |
| 손 안 대도 굴러감 | GitHub Actions cron + 실패 시 1시간 뒤 재시도 cron + 실패 메일 자동 발송 | 서버·PC 상시 가동 불필요 |
| PC + 안드로이드 | 정적 PWA (GitHub Pages) | 설치 없이 URL 하나. 안드로이드 "홈 화면에 추가"로 앱처럼 사용. 오프라인 캐시 가능 |
| 간단한 인터페이스 | 날짜 선택 → 카테고리 탭 → 카드 세로 스크롤 | 카드 = 썸네일 · 제목 · 중요도 · 3문장 요약 · [파급 펼치기] · [상세 펼치기] · 원문 링크 |

## 2. 구성요소 상세

### 2-1. 조사 (research.py)
- 모델: 설정 시점의 Gemini Flash 최신(현재 Gemini 3 Flash 또는 2.5 Flash). 깊이가 부족하면 Pro로 교체 (호출 6회/일이므로 Pro도 월 수 달러 수준).
- `tools: [{google_search: {}}]` 그라운딩 켜고, `response_mime_type: application/json` + 스키마 지정.
- 카테고리 5개 각각 4~6개 사건 → 하루 20~30장 카드.
- 6번째 호출(그라운딩 없음): 5개 결과를 입력으로 받아 **"오늘의 핵심 5"** 와 **사건 간 연결("A 때문에 B가 흔들리고 → C 영향")** 을 생성. 앱 첫 화면에 표시.
- 조사 창: 전날 06:00 ~ 당일 06:00 KST.

### 2-2. 후처리 (enrich.py) — LLM 없음
1. 각 source URL에 `requests.head/get(allow_redirects=True)` → 최종 URL.
2. 최종 URL HTML에서 `og:image`, `og:site_name` 추출 → 카드 썸네일·언론사명.
3. 같은 사건 중복(제목 유사도) 제거, 깨진 링크(4xx/5xx) 제거, 스키마 검증(pydantic).
4. `docs/data/YYYY-MM-DD.json` 저장, `docs/data/index.json`(날짜 목록) 갱신.
- 썸네일은 저장하지 않고 URL만 보관. 핫링크 차단 사이트는 `images.weserv.nl` 프록시로 폴백.

### 2-3. Google Docs 생성 (build_doc.py) — LLM 없음
- 방식: **Apps Script 웹앱** (`apps_script/Code.gs`). Python이 JSON을 POST하면 스크립트가 본인 계정 권한으로 Doc을 만든다.
  GCP 프로젝트·OAuth 동의화면·토큰 만료(테스트 모드 7일) 문제가 없어 설정이 가장 짧다.
- Drive 폴더 구조: `뉴스브리핑/2026/10/2026-10-31 뉴스브리핑` (루트 폴더는 스크립트 속성 `ROOT_FOLDER_ID`로 지정 가능).
- 문서 구조: 오늘의 핵심 5 → 사건 연결 → 카테고리별 (제목 / 요약 / 파급 / 다음에 볼 것 / 상세 / 출처 링크 / 키워드).
- 생성된 문서 URL은 JSON `doc_url`에 기록 → 앱 상단 "문서" 버튼.
- 대안: Python에서 Google Docs API 직접 호출(OAuth refresh token). 필요해지면 build_doc.py만 바꾸면 된다.

### 2-4. 앱 (docs/ → GitHub Pages)
- 파일: `index.html`, `app.js`, `style.css`, `manifest.json`, `sw.js`. 프레임워크 없음(바닐라 JS). 빌드 단계 없음.
- 화면 1: 날짜 바(좌우 스와이프) + "오늘의 핵심 5" + 사건 연결 다이어그램(텍스트 화살표).
- 화면 2: 카테고리 탭 → 카드 리스트. 카드 탭하면 파급/상세/출처 펼침.
- 다크모드 기본(새벽·밤에 봄), 글자 크게, 한 손 조작.
- 안드로이드: Chrome에서 "홈 화면에 추가" → 전체화면 PWA. 서비스워커가 최근 7일 JSON 캐시 → 지하철에서도 열림.
- 저장소가 public이면 GitHub Pages 무료. 비공개로 두고 싶으면 Cloudflare Pages(무료)로 배포.

### 2-5. 스케줄 (.github/workflows/daily.yml)
```yaml
on:
  schedule:
    - cron: "0 21 * * *"   # 06:00 KST
    - cron: "0 22 * * *"   # 07:00 KST 재시도 (당일 파일 없을 때만 실행)
  workflow_dispatch:        # 수동 실행 버튼
```
- 실패하면 GitHub가 등록 메일로 자동 통지. 그 외 알림 없음.
- 실행 시간 약 3~5분/일 → 월 150분. 무료 한도(private 2,000분/월) 내.

## 3. 저장소 구조

```
news-brief/
├─ .github/workflows/daily.yml
├─ pipeline/
│  ├─ research.py        # Gemini 호출 → raw/YYYY-MM-DD.json
│  ├─ enrich.py          # 링크·이미지·검증 → docs/data/YYYY-MM-DD.json
│  ├─ build_doc.py       # JSON → Google Docs
│  ├─ prompts/
│  │   ├─ system.txt
│  │   ├─ category.txt
│  │   └─ synthesis.txt
│  ├─ schema.py          # pydantic 모델 (JSON 스키마의 단일 출처)
│  └─ requirements.txt   # google-genai, requests, beautifulsoup4, pydantic, google-api-python-client
└─ docs/                 # GitHub Pages 루트
   ├─ index.html  app.js  style.css  manifest.json  sw.js  icons/
   └─ data/
      ├─ index.json      # ["2026-10-31", "2026-10-30", ...]
      └─ 2026-10-31.json
```

## 4. 데이터 스키마 (앱·Docs·Gemini가 공유)

```json
{
  "date": "2026-10-31",
  "generated_at": "2026-10-31T06:04:12+09:00",
  "top5": [{"ref": "eco-01", "why": "한 줄 이유"}],
  "connections": [{"from": "eco-01", "to": "pol-02", "how": "A의 금리 결정이 B의 예산 논쟁을 격화"}],
  "categories": [
    {
      "name": "경제",
      "items": [
        {
          "id": "eco-01",
          "headline": "20자 이내",
          "importance": 4,
          "summary": "3문장 이내.",
          "impact": ["누구에게 어떤 영향", "다음 연쇄 가능성"],
          "detail": "500~1200자 배경→경과→현재→쟁점",
          "watch_next": "다음에 지켜볼 일정·지표 1문장",
          "keywords": ["금리", "환율"],
          "sources": [{"title": "...", "publisher": "연합뉴스", "url": "https://..."}],
          "image": "https://.../og.jpg"
        }
      ]
    }
  ]
}
```

## 5. 비용·토큰 추정 (월)

| 항목 | 추정 |
|---|---|
| Gemini 호출 | 6회/일 × 30일 = 180회. 입력 ~3k, 출력 ~8k 토큰/회 → Flash면 무료 티어 또는 1달러 미만, Pro면 3~6달러 |
| 검색 그라운딩 | 150회/월. Gemini 3 계열 무료 할당(월 5,000회) 내. 2.5 계열은 과금 방식이 다르니 설정 시 가격표 확인 |
| GitHub Actions / Pages | 무료 |
| Google Drive | 문서 하루 1개, 무시 가능 |

## 6. 구축 순서

1. **준비 (30분)**: Google AI Studio에서 API 키 발급, GitHub 저장소 생성, Secrets에 `GEMINI_API_KEY` 등록.
2. **조사 스크립트 (1일차)**: `research.py` 작성 → 로컬에서 1회 실행 → JSON 품질 확인(깊이·출처 수). 프롬프트 튜닝.
3. **후처리 (1일차)**: `enrich.py` → 링크 해제·og:image 성공률 확인.
4. **앱 (2일차)**: `docs/` PWA 작성 → GitHub Pages 켜기 → 안드로이드에서 홈화면 추가 테스트.
5. **Docs 연동 (3일차)**: OAuth refresh token 발급 → `build_doc.py` → Drive 폴더에 문서 생성 확인.
6. **자동화 (3일차)**: workflow 등록, `workflow_dispatch`로 수동 1회 → 다음 날 06:00 자동 실행 확인.
7. **1주 운영 후 튜닝**: 카테고리 가감, 항목 수, 모델(Flash↔Pro), 중요도 기준.

## 7. 플랜 B — Gemini 앱 "예약 작업"만으로 (코드 최소)

코드를 거의 안 쓰고 싶다면: Gemini 앱(AI Pro 구독 필요)의 예약 작업에 `gemini_prompts.md`의 B 프롬프트를 등록 → Gemini가 매일 06:00 조사 후 Drive 폴더에 Doc 저장(프롬프트에 저장 지시 포함) → Apps Script 웹앱이 해당 날짜 Doc을 읽어 JSON으로 서빙 → PWA가 표시.

한계: (1) Doc 저장이 가끔 빠질 수 있음, (2) 출력 형식이 매일 조금씩 달라져 파싱 실패 가능, (3) 사진 없음(og:image 수집 단계가 없으므로 Apps Script에서 UrlFetch로 보완 가능), (4) 예약 작업 최대 10개. 플랜 A의 앱·스키마는 그대로 재사용 가능하므로, B로 시작해서 불안정하면 A로 갈아타도 됨.

## 8. 미결 사항 (설정 시 확인)
- 저장소 public 여부(Pages 무료 조건) 또는 Cloudflare Pages 사용.
- Gemini 모델 선택(Flash로 시작 권장) 및 당시 그라운딩 가격.
- 카테고리 5개 확정 여부, 하루 카드 수(20~30).

## 9. 구현 상태 (2026-11-01)
- 파이프라인·앱·워크플로우·Apps Script 작성 완료. 설치 절차는 README.md.
- 샘플 데이터(2026-10-31, example.com 링크)로 앱 화면 확인. 실제 Gemini 호출은 API 키 등록 후 첫 실행에서 검증 필요.
