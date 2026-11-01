# Gemini API → Gemini 앱(구독) 전환 검토

작성: 2026-11-01, 갱신: 2026-11-01 (Spark → 작업 모드 명칭 변경 반영).

> **명칭 안내**: 2026-10-12~13 Gemini 4 Argon 출시와 함께 Spark 브랜드가 사라지고 Gemini 앱 프롬프트 창 위 **「채팅 / 작업(Task)」 토글**로 통합됨. 반복 작업은 별도 **「예약됨(Scheduled)」** 페이지에서 관리 [커뮤니티: 9to5Google, Chrome Unboxed]. 아래 본문의 "작업 모드"가 옛 Spark에 해당함. 근거 수준 표기: **[공식]** Google 문서·블로그 / **[커뮤니티]** 매체·블로그 / **[추정]** Claude 추정.

## 1. 결론

- **가능함.** 단, 채팅 모드의 옛 "예약 작업(Scheduled Actions)"이 아니라 **작업(Task) 모드**(옛 Spark)로 해야 함.
  - 채팅 모드 예약 작업: 결과가 Gemini 채팅 안에만 남고 파일로 저장 안 됨 → 앱 연동 불가.
  - 작업 모드: 일정(daily) 실행 + Google Docs 생성/편집 가능 + 한국 정식 출시(AI Pro 이상) → 우리 파이프라인의 "조사 단계"를 대체할 수 있음.
- **구조**: 작업 모드가 매일 Drive 폴더에 JSON 문서를 저장 → Apps Script가 그 문서를 읽어 돌려줌 → GitHub Actions는 Gemini API 없이 변환만 수행 → 앱 갱신. API 키 호출이 0건이 됨.
- **대안(더 간단)**: AI Pro 구독에 포함된 **월 $10 Google Cloud 크레딧**을 API 결제에 연결하면 현행 구조를 그대로 두고 비용만 상쇄될 가능성 있음 (실제 월 청구액은 미확인이라 상쇄 여부는 확인 필요).

## 2. 선택지 비교

| 항목 | A. 현행(API) + AI Pro 크레딧 | B. 작업 모드(옛 Spark) → Docs → 앱 | C. 채팅 모드 예약 작업 |
|---|---|---|---|
| 추가 비용 | 월 $10 크레딧 내면 0 [공식] | 0 (구독에 포함) | 0 |
| 파일 저장 | 이미 됨 | Google Docs 생성 가능 [공식·커뮤니티] | **불가** (채팅 내 결과만) [공식] |
| 실행 시각 정확도 | 정확 (cron) | 미확인 (베타) | 예약 시각 ±1시간 [커뮤니티] |
| 출력 형식 통제 | 강함 (response_schema) | 약함 (프롬프트 의존, JSON 깨질 수 있음) [추정] | 약함 |
| 한국 지원 | 해당 없음 | 한국어·국내 출시 [공식] | 가능 |
| 코드 변경 | 없음 | Apps Script 1개 함수 + run_all 분기 | 불가 |
| 리스크 | 토큰 급증 시 크레딧 초과 | 베타 안정성, 작업 일시정지, 스키마 불일치 | 연동 불가 |

## 3. 조사 근거

### 예약 작업(Scheduled Actions)
- AI Pro/Ultra 또는 자격 있는 Workspace 플랜, 계정당 활성 10개 [공식 도움말 요약, 커뮤니티]
- 결과는 Gemini 안 알림/채팅으로 전달. Drive·Docs 저장 기능 설명 없음. "이메일로 보내줘"는 한 블로그만 주장, 두 블로그는 불가 → **미확인**
- 실행은 "예약 시각 이후 1시간 이내" [커뮤니티]
- 출처: [How-To Geek](https://www.howtogeek.com/gemini-scheduled-actions-are-finally-live/), [Android Police](https://www.androidpolice.com/geminis-scheduled-actions/), [Google 도움말](https://support.google.com/gemini/answer/16316416?hl=en-GB), [Datastudios](https://www.datastudios.org/post/google-gemini-s-new-scheduled-actions-what-it-is-how-it-works-and-why-it-matters)

### 작업(Task) 모드 — 옛 Gemini Spark
- 2026-10-12~13: Spark가 메인 앱으로 통합. 프롬프트 창 위 「Chat / Task」 버튼, 반복 작업은 「Scheduled」 페이지(Active·Paused·Completed·Suggested) [커뮤니티: [9to5Google](https://9to5google.com/2026/10/12/gemini-spark-task-redesign/), [Chrome Unboxed](https://chromeunboxed.com/google-is-quietly-ditching-the-spark-brand-to-merge-tasks-directly-into-gemini/), [layer3labs](https://www.layer3labs.io/guides/what-happened-to-gemini-spark)]
- Android 먼저 적용, iOS·웹은 순차 [커뮤니티]. Google AI Pro/Ultra 전용 [공식 요금제 페이지 요약]
- 개인 계정 + AI Pro/Ultra. 한국 정식 출시(2026-07-30, 영어·한국어) [공식: [Google Korea 블로그](https://blog.google/intl/ko-kr/products/gemini-spark-kr/), [ZDNet Korea](https://zdnet.co.kr/view/?no=20260730095359)]
- 구성: Task(목표) / Schedule(시간·Gmail 트리거; once·hourly·daily·weekly…) / Skill(재사용 지침) [공식 도움말 요약]
- Docs 생성·편집, Drive 검색·관리, Gmail 연동 가능 [커뮤니티: [DataCamp](https://www.datacamp.com/blog/gemini-spark), [aiagentslibrary](https://www.aiagentslibrary.com/blog/gemini-spark-tasks-skills-schedules/)]
- 동시 작업 15개, 활성 일정 50개 [커뮤니티]. "작업이 결정·권한·로그인을 필요로 하면 일시정지" [커뮤니티]
- 실행 시각 정확도, 1회 실행당 검색 깊이 제한: **미확인**
- 출처: [Google 도움말 Spark](https://support.google.com/gemini/answer/17094507?hl=en), [Spark 일정](https://support.google.com/gemini/answer/17094710?hl=en), [9to5Google](https://9to5google.com/2026/07/23/gemini-spark-google-ai-pro-us/), [jeffsu 튜토리얼](https://www.jeffsu.org/gemini-spark-tutorial/)

### AI Pro 크레딧 (대안 A)
- AI Pro 월 $10, Ultra 월 $100 Google Cloud 크레딧. Gemini API에 사용 가능 [공식: [Google 개발자 블로그](https://blog.google/innovation-and-ai/technology/developers-tools/gdp-premium-ai-pro-ultra/), [AI Studio 안내](https://aistudio.google.com/learn/use-google-ai-plan-credits-in-ai-studio)]
- 활성화에 최소 $5 결제(선불) 필요, 구독 본인만 사용 가능 [공식·커뮤니티]
- 현 파이프라인 사용량: 하루 그라운딩 호출 6회(≈ 월 180회). 그라운딩 무료 한도 월 5,000회 주장 [커뮤니티, 유료 티어 기준]. 토큰 비용은 로그에 없어 **미확인** → Google Cloud 콘솔 청구 내역 확인 필요
- 출처: [eesel 가격 정리](https://www.eesel.ai/blog/gemini-3-8-flash-pricing), [morphllm](https://www.morphllm.com/gemini-api-pricing)

## 4. 플랜 B 설계 (작업 모드 → 앱)

```
[Gemini 작업 모드]  매일 05:30 KST 예약
   └ 조사 → Drive "뉴스브리핑/inbox/YYYY-MM-DD.json" (Google Docs, 본문은 JSON 텍스트만)
[Apps Script]   doGet?mode=raw&date=YYYY-MM-DD  → 해당 Docs 본문을 그대로 반환 (SECRET 검사)
[GitHub Actions] 06:30 KST (+07:30 재시도)
   └ fetch_from_drive.py: 본문 받아 JSON 파싱 → raw/YYYY-MM-DD.json
   └ enrich.py → build_doc.py (기존 그대로, Gemini 호출 없음)
```

- 작업 모드가 만든 JSON이 깨지면 Actions가 실패 메일을 보내고, 그날은 전날 브리핑이 유지됨.
- JSON 수선용으로만 Gemini API 무료 티어(그라운딩 없음, 하루 1회)를 남겨둘 수 있음. 선택.
- 코드 작업량: Apps Script `doGet` 확장 + Python 파일 1개 + 워크플로우 2줄. 반나절.

## 5. Gemini 앱에 입력할 프롬프트

### 5-1. 사전 준비 (한 번)
1. Drive 내 드라이브에 폴더 `뉴스브리핑/inbox` 생성 (Apps Script가 만든 `뉴스브리핑` 폴더 아래).
2. Gemini 앱 → 설정 → 연결된 앱에서 Google Drive·Docs 켜기.
3. Gemini 앱 프롬프트 창 위 토글을 **「작업(Task)」** 으로 전환 (Android에 먼저 적용됨. 웹·iOS에 없으면 Android 앱에서 등록하면 됨. 등록 후에는 기기와 무관하게 Google 클라우드에서 실행).

### 5-2. Skill 등록 프롬프트 (지침 저장)

작업 모드에서 아래를 그대로 붙여 넣음. Skill은 작업 설정(옛 Spark 설정)에 저장됨. (Skill 메뉴가 안 보이면 5-3의 일정 프롬프트 안에 이 본문을 통째로 넣어도 됨.)

```
"일일뉴스브리핑"이라는 Skill을 만들어 저장해 줘. 지침은 다음과 같아.

[목표]
오늘(KST 기준) 직전 24시간의 한국·국제 뉴스를 조사해 아래 JSON 형식의 Google Docs 문서 1개를 만든다.

[조사 범위와 개수]
- 경제(eco) 5~6건: 금리·환율·물가·증시·부동산·기업 실적·무역. 한국 중심 + 미국·중국 거시 흐름
- 정치(pol) 4~5건: 국회·정부·대통령실·정당·선거·외교안보 정책. 한국 중심
- 사회·사건사고(soc) 4~5건: 대형 사고·재난·범죄·판결·노동·보건·교육 중 파급이 큰 것
- 국제(intl) 4~5건: 전쟁·분쟁·주요국 선거·정상회담·제재·국제기구. 한국에 미치는 영향 명시
- 산업·기술(tech) 4~5건: 반도체·AI·에너지·자동차·바이오·플랫폼 규제
- 각 사건은 서로 다른 매체 기사 2개 이상으로 확인하고, 기사 URL을 sources에 넣는다.
- 추측·미확인 내용은 쓰지 않는다. 숫자는 기사에 있는 그대로 쓴다.

[저장 위치와 형식]
- Google Drive 폴더 "뉴스브리핑/inbox" 안에 제목이 "YYYY-MM-DD.json"인 Google Docs 문서를 새로 만든다 (오늘 날짜, 예: 2026-11-02.json).
- 문서 본문에는 아래 JSON 텍스트만 넣는다. 제목·머리말·설명·코드펜스(```)·마크다운을 절대 넣지 않는다. 본문 첫 글자는 { 이고 마지막 글자는 } 이다.
- 같은 날짜 문서가 이미 있으면 새로 만들지 말고 그 문서 본문을 통째로 교체한다.

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
      "name": "경제", "code": "eco",
      "items": [
        {
          "id": "eco-01",
          "headline": "20자 이내",
          "importance": 5,
          "summary": "3문장 이내",
          "impact": ["구체적 영향 경로 1", "구체적 영향 경로 2"],
          "detail": "500~1200자. 배경 → 경과 → 현재 상태 → 쟁점. 문단은 줄바꿈으로 구분",
          "watch_next": "다음에 볼 것 1문장",
          "keywords": ["키워드1", "키워드2"],
          "entities": ["기관·인물1"],
          "sources": [{"title": "기사 제목", "publisher": "매체명", "url": "https://..."}]
        }
      ]
    }
  ]
}

[규칙]
- categories는 eco, pol, soc, intl, tech 순서로 5개 모두 넣는다. name은 각각 "경제", "정치", "사회·사건사고", "국제", "산업·기술".
- id는 "코드-01", "코드-02" 순서. importance는 1~5 정수.
- top5는 정확히 5개, 서로 다른 카테고리를 우선. connections는 3~4개.
- 문자열 안의 큰따옴표는 작은따옴표로 바꾼다. JSON이 유효한지 마지막에 스스로 검사한다.
- 완료되면 "완료: 문서 링크"만 짧게 보고한다.
```

### 5-3. 예약 등록 프롬프트

작업 모드에서 입력. 등록 후 「예약됨(Scheduled)」 페이지에 Active로 보이면 성공.

```
매일 오전 5시 30분(한국 시간)에 "일일뉴스브리핑" Skill을 실행하는 반복 작업을 예약해 줘.
내 확인을 기다리지 말고 끝까지 자동으로 진행하고, 실패하면 이유만 알려 줘.
```

Skill 기능이 없을 때는 아래 한 문장 뒤에 5-2의 `[목표]`부터 `[규칙]`까지 붙여서 한 번에 입력함.

```
매일 오전 5시 30분(한국 시간)에 아래 지침을 수행하는 반복 작업을 만들어 줘. 내 확인 없이 자동으로 끝까지 진행해.
```

### 5-4. 첫 테스트 프롬프트 (지금 바로 1회)

```
"일일뉴스브리핑" Skill을 지금 한 번 실행해 줘. 날짜는 오늘로.
```

실행 후 확인할 것:
1. Drive `뉴스브리핑/inbox/YYYY-MM-DD.json` 문서가 생겼는지
2. 본문이 `{`로 시작해 `}`로 끝나는지, 코드펜스가 없는지
3. 카테고리 5개·top5 5개·sources URL이 실제 기사인지
4. 걸린 시간과 "일시정지(권한 요청)" 여부

## 6. 리스크와 대응

| 리스크 | 가능성 | 대응 |
|---|---|---|
| JSON 형식 깨짐 (코드펜스·설명문 섞임) | 중 | 파서에서 첫 `{`~마지막 `}`만 추출. 그래도 실패하면 API 무료 티어로 수선 1회 |
| 실행 시각 지연 | 중 | Actions를 06:30·07:30·08:30 3회 시도, 파일 없으면 종료 |
| 작업이 권한 요청으로 멈춤 | 중 | 첫 1~2회는 직접 지켜보고 승인. 프롬프트에 "확인 없이 진행" 명시 |
| 기사 깊이가 API(그라운딩 46개 출처)보다 얕음 | 미확인 | 첫 주 품질 비교 후 결정. 얕으면 플랜 A로 복귀 |
| 작업 모드 정책·UI 변경 (10월에도 개편됨) | 저 | 현행 API 코드는 지우지 않고 환경변수로 전환 가능하게 유지 |

## 7. 미확인 항목 (직접 확인 필요)
- 현재 Gemini API 월 청구액 (Google Cloud 콘솔 → 결제)
- 작업 모드 1회 실행당 검색 횟수·시간 상한
- 예약 실행의 실제 시각 편차
- 웹·iOS에서 작업 토글·Skill 메뉴 노출 여부 (보도 기준 Android 우선)
