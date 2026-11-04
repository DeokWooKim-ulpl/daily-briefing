# Gemini 앱(작업 모드) 연동 가이드 — 검토 결론 · 흐름 · 프롬프트

갱신: 2026-11-03 (auto 모드 자동화 반영). 이 파일 하나로 끝남. (이전 `SPARK_MIGRATION.md`, `gemini_app_prompts.md` 는 여기로 통합·삭제)

---

## 1. 결론

- Gemini API 호출(조사 단계)을 **Gemini 앱의 「작업」 모드**로 대체 가능. 나머지 기능(링크·사진 정리, Google Docs 생성, 앱 배포)은 전부 그대로.
- 채팅 모드의 "예약 작업"은 결과가 채팅 안에만 남고 파일로 저장되지 않으므로 쓸 수 없음. 반드시 **작업 모드**에서 예약해야 Drive에 문서가 남음.
- 코드는 구현·검증 완료. 11월 5일에는 아래 3절 프롬프트만 넣으면 됨.

| | API 방식 (현행) | Gemini 앱 방식 (전환 후) |
|---|---|---|
| 비용 | 토큰 과금 | AI Pro 구독에 포함, 추가 0 |
| 실행 시각 | 정확 | 예약 시각 ±1시간 (Actions가 3회 재시도로 흡수) |
| JSON 형식 | API가 강제 | 프롬프트 의존. 파이프라인이 코드펜스·따옴표·쉼표 오류를 자동 보정 |
| 조사 깊이 | 분야당 출처 20~46개 (실측) | 미확인. 첫 주 비교 필요 |
| 전환·복귀 | — | **자동**(auto 모드 기본). 앱 문서가 있으면 앱, 없으면 08:30에 API. 강제하려면 GitHub 변수 `BRIEF_SOURCE` 를 `app`/`api` 로 |

---

## 2. 일의 흐름 (auto 모드 — 기본값, 설정 없이 동작)

```
Gemini 앱 작업 모드 (내 Google 계정)              GitHub Actions (서버, 자동)  — 06:00 · 07:00 · 08:30 · 09:30 · 10:30 · 12:00 KST
────────────────────────────────              ──────────────────────────────────────────────────────────────
05:30  ⓐ 예약된 작업 실행: 5개 분야 뉴스 조사       매 회차 공통:
~06:30 ⓑ Drive 뉴스브리핑/inbox/날짜.json 저장        ① fetch_inbox.py → Apps Script에 "오늘 문서 줘"
                                                      ├ 있음 → JSON 꺼내 검증 → ② enrich ③ Docs ④ 커밋·배포 → 끝 (model = gemini-app)
                                                      ├ 없음 → 조용히 종료 (다음 회차 대기)
                                                      └ 없음 + 08:30 회차 → ::warning:: 남기고 Gemini API 로 생성 (model = gemini-3.8-flash)
                                                    이미 당일 브리핑이 있는 회차:
                                                      ├ model 이 gemini-app → 20초 만에 종료
                                                      └ model 이 API → 앱 문서가 새로 생겼으면 앱 결과로 교체 (Docs 도 다시 생성)
                                                    매 회차 끝: Actions "Summary" 탭에 출처·건수·문서 저장 시각 한 줄 보고
```

- Apps Script 하나가 두 역할: **읽기**(Gemini 앱이 남긴 문서를 꺼내 줌) + **쓰기**(완성본 Docs 생성, 기존 기능). `inbox` 폴더는 첫 호출 때 자동 생성.
- Gemini 앱이 문서를 엉뚱한 폴더에 넣어도, 이름이 날짜로 시작하면 드라이브 전체에서 찾아냄.
- Apps Script 가 아직 옛 버전이거나 비밀번호가 안 맞아도 **실패하지 않음**: 경고만 남기고 08:30에 API 로 감 (= 지금과 동일한 동작). 즉 아래 체크리스트를 하나도 안 해도 서비스는 끊기지 않음.
- 앱 하단 글씨: `생성 11-05 06:02 · gemini-app · 앱 문서 11/05 05:52` → 어느 경로로 만들어졌고 Gemini 가 몇 시에 저장했는지 바로 보임.

### 강제 모드 (필요할 때만)
GitHub → Settings → Secrets and variables → Actions → **Variables** → `BRIEF_SOURCE`
- `app` : API 대체 생성 안 함. 문서가 없으면 그날 브리핑 없음 (비용 완전 0)
- `api` : 앱 문서 무시, 예전 방식 그대로
- 변수 없음 = `auto`

수동 실행(Actions → Run workflow)에도 같은 `source` 선택칸이 있음. 수동 실행의 auto 는 문서가 없으면 즉시 API 로 만듦.

---

## 3. Gemini 앱에 입력할 프롬프트 (11월 5일, 순서대로)

모두 Gemini 앱 프롬프트 창 위 토글을 **「작업」** 으로 두고 입력. 채팅 모드 아님.
Android 앱에 먼저 적용된 기능이라 웹·iOS에 토글이 없으면 Android 앱에서 등록. 등록 후에는 기기와 무관하게 Google 서버에서 실행됨.

### 3-A. 즉시 1회 테스트 (먼저 이것부터)

```
아래 지침대로 지금 바로 한 번 실행해 줘. 날짜는 오늘(한국 시간)로. 내 확인이나 추가 질문 없이 끝까지 진행하고, 끝나면 "완료: (문서 링크)"만 짧게 알려 줘.

[목표]
오늘(한국 시간 KST 기준) 직전 24시간(어제 06:00 ~ 오늘 06:00)의 한국·국제 뉴스를 조사해, 아래 JSON 형식의 Google Docs 문서 1개를 만든다.

[조사 범위와 개수]
- 경제(eco) 5~6건: 금리·환율·물가·증시·부동산·기업 실적·무역. 한국 중심 + 미국·중국 거시 흐름
- 정치(pol) 4~5건: 국회·정부·대통령실·정당·선거·외교안보 정책 결정. 한국 중심
- 사회·사건사고(soc) 4~5건: 대형 사고·재난·범죄·판결·노동·보건·교육 중 사회적 파급이 큰 것
- 국제(intl) 4~5건: 전쟁·분쟁·주요국 선거·정상회담·제재·국제기구 결정. 한국에 미치는 영향을 명시
- 산업·기술(tech) 4~5건: 반도체·AI·에너지·자동차·바이오·플랫폼 규제, 기업 전략 변화
- 사건을 고르기 전에 먼저 넓게 검색(한국 뉴스 + 해외 주요 매체)하고 중요도 순으로 정렬해 고른다.
- 각 사건은 서로 다른 매체의 기사 2개 이상으로 확인하고, 그 기사들의 실제 URL을 sources에 넣는다.
- 추측·미확인 내용은 쓰지 않는다. 숫자·날짜는 기사에 있는 그대로 쓴다.

[저장 위치와 형식]
- Google Drive의 "뉴스브리핑" 폴더 안 "inbox" 폴더에, 제목이 오늘 날짜인 "YYYY-MM-DD.json" 형식(예: 2026-11-05.json)의 Google Docs 문서를 새로 만든다.
- 문서 본문에는 아래 JSON 텍스트만 넣는다. 제목 줄, 인사말, 설명, 코드펜스(```), 마크다운 서식, 글머리 기호를 절대 넣지 않는다. 본문의 첫 글자는 { 이고 마지막 글자는 } 이다.
- 같은 날짜의 문서가 이미 있으면 새로 만들지 말고 그 문서의 본문을 통째로 교체한다.

[JSON 형식]
{
  "date": "YYYY-MM-DD",
  "one_liner": "오늘 하루를 한 문장으로 (40자 이내)",
  "top5": [
    {"ref": "eco-01", "why": "왜 오늘 가장 중요한지 1문장"}
  ],
  "connections": [
    {"from": "eco-01", "to": "intl-02", "how": "두 사건이 어떻게 연결되는지 1문장"}
  ],
  "categories": [
    {
      "name": "경제",
      "code": "eco",
      "items": [
        {
          "id": "eco-01",
          "headline": "20자 이내 제목",
          "importance": 5,
          "summary": "3문장 이내 요약",
          "impact": ["구체적 영향 경로 1", "구체적 영향 경로 2"],
          "detail": "500~1200자. 배경 → 경과 → 현재 상태 → 쟁점 순서. 문단 사이는 줄바꿈 문자(\n)로 구분",
          "watch_next": "다음에 볼 것 1문장",
          "keywords": ["키워드1", "키워드2"],
          "entities": ["기관·인물1", "기관·인물2"],
          "sources": [
            {"title": "기사 제목", "publisher": "매체명", "url": "https://..."}
          ]
        }
      ]
    }
  ]
}

[규칙]
- categories는 eco, pol, soc, intl, tech 순서로 5개를 모두 넣는다. name은 각각 "경제", "정치", "사회·사건사고", "국제", "산업·기술".
- id는 "코드-01", "코드-02" … 순서로 붙인다. importance는 1~5 정수(5가 가장 중요).
- top5는 정확히 5개, 가능하면 서로 다른 카테고리에서 고른다. connections는 3~4개.
- 문자열 안에 큰따옴표(")가 필요하면 작은따옴표(')로 바꾼다. 줄바꿈은 \n으로 쓴다.
- 마지막에 JSON 전체가 문법적으로 유효한지(괄호·쉼표·따옴표) 스스로 검사하고 고친 뒤 저장한다.
```

실행 후 확인:
1. Drive `뉴스브리핑/inbox/` 에 `오늘날짜.json` 문서가 생겼는지
2. 본문이 `{` 로 시작해 `}` 로 끝나고, 코드펜스·설명문이 없는지
3. 카테고리 5개 · top5 5개 · sources의 URL이 실제 기사인지
4. GitHub 변수 `BRIEF_SOURCE=app` 등록 (4절) → Actions → daily-brief → **Run workflow** → 앱에 오늘 날짜가 뜨는지

### 3-B. 매일 반복 예약 (3-A 통과 후)

첫 줄만 다르고 지침은 3-A와 동일. 첫 줄을 아래로 바꾸고 `[목표]`부터 `[규칙]`까지 그대로 붙여서 한 번에 입력.

```
매일 오전 5시 30분(한국 시간)에 아래 지침을 수행하는 반복 작업을 예약해 줘. 매번 내 확인이나 추가 질문 없이 끝까지 자동으로 진행하고, 실패하면 이유만 알려 줘.

[목표]
... (3-A의 [목표] ~ [규칙] 전체를 그대로) ...
```

등록 후 Gemini 앱의 **「예약됨」** 페이지에 Active로 보이면 성공.

### 3-C. (선택) 지침을 재사용 가능하게 저장

작업 모드에 지침을 저장하는 메뉴(Skill 등)가 보이면, 3-A의 `[목표]`~`[규칙]`을 "일일뉴스브리핑" 이름으로 저장해 두고 이후 예약은 아래 한 줄로 가능.

```
매일 오전 5시 30분(한국 시간)에 "일일뉴스브리핑" 지침을 실행하는 반복 작업을 예약해 줘. 내 확인 없이 끝까지 진행하고, 실패하면 이유만 알려 줘.
```

메뉴가 없으면 3-B 방식(지침 전체를 예약 프롬프트에 포함)으로 충분함.

### 3-D. 문제가 생겼을 때 수정 프롬프트

| 증상 | 조치 |
|---|---|
| 코드펜스·설명이 섞여 나옴 | 파이프라인이 자동으로 걷어내므로 대개 무시 가능. 반복되면 예약 작업을 열어 수정: `저장 형식 규칙을 고쳐 줘: 문서 본문에는 JSON만 넣고, ``` 와 설명 문장은 절대 넣지 마.` |
| 다른 폴더에 저장됨 | 드라이브 전체에서 날짜 이름으로 찾으므로 동작은 함. 반복되면: `저장 위치를 내 드라이브 > 뉴스브리핑 > inbox 폴더로 고정해 줘.` |
| 기사 수가 적음·얕음 | `조사 단계에서 카테고리마다 검색을 최소 5회 이상 하고, 각 사건에 매체 2곳 이상을 확인하도록 강화해 줘.` |
| 작업이 "권한 필요"로 멈춤 | Gemini 앱 설정 → 연결된 앱에서 Drive·Docs 켜고, 예약됨 페이지에서 작업 재개 |

---

## 4. 내가 할 일 — 자동화 후 남은 것

자동화된 것(이제 안 해도 됨): inbox 폴더 생성, GitHub 변수 등록, 수동 실행·force, 앱 결과로 교체, 매일 결과 확인용 요약.
**남은 것은 Google 계정으로 직접 로그인·승인해야 하는 6가지뿐** (어떤 도구도 대신 못 함). 총 20분 안쪽.

### 지금 (11/3~4) — Gemini 사용량과 무관

**A. Gemini 앱에 Drive·Docs 연결 (2분)**
1. gemini.google.com (또는 휴대폰 Gemini 앱) → 설정(톱니) → "연결된 앱"
2. **Google Drive**, **Google Docs** 스위치 켜기 → 권한 창이 뜨면 허용
- 확인: 두 스위치 켜짐.

**B. Apps Script 코드 교체 (3분)**
1. script.google.com → 기존 프로젝트 → `Code.gs` → 편집창 전체 선택(Ctrl+A) → 삭제
2. GitHub 저장소 → `apps_script/Code.gs` → "Raw" → 전체 복사 → 붙여넣기 → Ctrl+S
- 확인: Ctrl+F 로 `testInbox` 가 찾아짐.

**C. 권한 승인 (2분)**
1. 툴바 함수 드롭다운 → `testInbox` → ▶ 실행
2. "승인 필요" → 권한 검토 → 계정 선택 → "확인하지 않은 앱" 경고가 뜨면 **고급 → (프로젝트명)(으)로 이동(안전하지 않음)** → 허용
- 확인: 실행 로그에 `{"ok":false,"error":"not_found"}`. 이때 Drive 에 `뉴스브리핑/inbox` 폴더가 자동으로 생김.

**D. 새 버전 배포 (1분)** — 안 하면 옛 코드가 계속 돎
1. 배포 → 배포 관리 → 연필(✎) → 버전: **새 버전** → 배포
- 확인: 새 탭에 `(웹 앱 URL)?mode=inbox&date=2026-11-05` 를 열면 `{"ok":false,"error":"unauthorized"}`. (옛 코드면 `"message":"news-brief doc builder…"`)
- 못 했을 때: Actions 요약에 `Apps Script가 옛 버전임` 노란 경고가 매일 뜨고, API 로 계속 생성됨. 서비스는 안 끊김.

### 11/5 (02:54 사용량 초기화 후, 아침 아무 때나)

**E. Gemini 앱 1회 테스트 (10~20분, 대부분 대기)**
1. Gemini 앱 → 입력창 위 토글 **「작업」** → 3-A 블록 전체 붙여넣기 → 전송
2. 권한 카드가 뜨면 허용. 질문이 오면 "그대로 진행"
3. 완료 메시지(문서 링크) 대기
- 확인: Drive `뉴스브리핑/inbox/2026-11-05.json` 이 있고, 본문이 `{` 로 시작해 `}` 로 끝남.
- 그 다음은 **아무것도 안 해도 됨**: 다음 Actions 회차(09:30·10:30·12:00 중 가장 가까운 것)가 문서를 발견해 06:00에 API 로 만든 것을 앱 결과로 바꿈. 바로 보고 싶으면 Actions → daily-brief → Run workflow → 그냥 초록 버튼(기본값 auto).
- 앱에서 확인: 당겨서 새로고침 → 하단에 `gemini-app · 앱 문서 11/05 hh:mm`.

**F. 매일 반복 예약 (2분)** — E 가 성공한 뒤
1. 작업 모드 → 3-B 블록(첫 줄 + 3-A 의 `[목표]`~`[규칙]`) 붙여넣기 → 전송
2. Gemini 앱 **예약됨** 페이지에 Active, 매일 05:30
- 확인: 다음 날 아침 앱 하단이 `gemini-app` 이면 끝. `gemini-3.8-flash` 면 그날은 Gemini 가 08:30까지 문서를 못 만든 것 → 예약됨 페이지에서 상태(일시정지 여부) 확인.

### 그 뒤 — 할 일 없음
- 매일 자동. 문제가 있으면 GitHub 가 실패 메일을 보냄 (Apps Script 오류·JSON 형식 오류는 메일 없이 API 로 조용히 대체되고 Actions Summary 에 노란 경고만 남음).
- 일주일 뒤 API 기간(11/1~4)과 앱 기간 품질을 비교. 얕으면 3-D 세 번째 행 프롬프트로 조사 강화.
- API 비용을 완전히 끊고 싶으면 GitHub 변수 `BRIEF_SOURCE=app`. 그러면 Gemini 가 못 만든 날은 브리핑이 비고 08:30 이후 실패 메일 대신 "대기" 로만 남음.

## 5. 구현 내역 (참고)

| 파일 | 내용 |
|---|---|
| `apps_script/Code.gs` | `GET ?mode=inbox&date=YYYY-MM-DD&secret=…` → inbox 문서 본문 반환. `testInbox` 추가 |
| `pipeline/fetch_inbox.py` | 문서에서 JSON 추출(코드펜스·스마트따옴표·후행쉼표 보정) → 검증 → `research.py` 와 같은 raw 형식 저장 |
| `pipeline/run_all.py` | `--source auto\|app\|api` (환경변수 `BRIEF_SOURCE`, 기본 auto), `--api-fallback`, `--strict`. auto 는 API 결과를 앱 결과로 교체 |
| `pipeline/summary.py` | Actions Summary 용 한 줄 보고 (출처·건수·문서 저장 시각) |
| `pipeline/schema.py`, `enrich.py`, `docs/app.js` | `doc_saved_at` (Gemini 문서 저장 시각) 저장·앱 하단 표시 |
| `.github/workflows/daily.yml` | 06:00·07:00·08:30·09:30·10:30·12:00 KST. 08:30 만 API 대체. 수동 실행에 `source` 선택칸 |

검증: 모의 Apps Script 서버로 8경로 통과 (대기 / API 대체 분기 / API→앱 교체 / 이미 앱 결과 / 옛 Code.gs / strict 실패 / secret 불일치 / 코드펜스 혼입) (2026-11-03). 실제 Gemini 앱 출력과 Apps Script 재배포는 11월 5일 확인 필요.

---

## 6. 근거 (출처)

- 작업 모드 통합·예약됨 페이지 (2026-10-12~13) [커뮤니티]: [9to5Google](https://9to5google.com/2026/10/12/gemini-spark-task-redesign/), [Chrome Unboxed](https://chromeunboxed.com/google-is-quietly-ditching-the-spark-brand-to-merge-tasks-directly-into-gemini/)
- 한국 출시·AI Pro 이상·한국어 지원 [공식]: [Google Korea 블로그](https://blog.google/intl/ko-kr/products/gemini-spark-kr/), [ZDNet Korea](https://zdnet.co.kr/view/?no=20260730095359)
- 작업 모드 도움말 (일정 유형: once·hourly·daily·weekly…, Docs 생성) [공식]: [Google 도움말 – 작업·워크플로](https://support.google.com/gemini/answer/17094507?hl=en), [일정 관리](https://support.google.com/gemini/answer/17094710?hl=en)
- 채팅 모드 예약 작업은 파일 저장 불가, ±1시간 [공식·커뮤니티]: [Google 도움말](https://support.google.com/gemini/answer/16316416?hl=en-GB), [Android Police](https://www.androidpolice.com/geminis-scheduled-actions/)
- AI Pro 월 $10 Google Cloud 크레딧(API 결제에 사용 가능, 대안) [공식]: [Google 개발자 블로그](https://blog.google/innovation-and-ai/technology/developers-tools/gdp-premium-ai-pro-ultra/)

미확인: 작업 모드 1회 실행당 검색 횟수·시간 상한, 예약 실행의 실제 시각 편차, 웹·iOS에서의 토글 노출 여부.
