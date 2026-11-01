# 뉴스브리핑 앱 — 설치·운영 가이드

매일 아침 6시에 Gemini가 뉴스를 조사하고, Python이 정리하고, PC·안드로이드에서 카드뉴스로 보는 개인용 앱입니다.
설계 배경은 [PLAN.md](PLAN.md), 프롬프트 원문은 [gemini_prompts.md](gemini_prompts.md)에 있습니다.

이 문서는 **처음 하는 사람 기준**으로 씁니다. 순서대로 따라오면 됩니다.

---

## 전체 그림 (1분)

```
[내 컴퓨터 또는 GitHub 서버]  매일 06:00
   ① research.py   Gemini에게 5개 분야 조사 시킴 (Google 검색 붙여서)      ← 여기만 AI 사용
   ② enrich.py     기사 링크 정리, 기사 사진 주소 수집, 중복 제거           ← 그냥 Python
   ③ build_doc.py  Google Docs 문서로도 저장 (선택)                        ← 그냥 Python
   ④ 결과 JSON 파일을 docs/data/ 에 저장 → 앱이 이 파일을 읽어서 보여줌
```

- **단계 1**: 내 컴퓨터에서 한 번 돌려본다 (API 키만 있으면 됨, 10분)
- **단계 2**: GitHub에 올려서 매일 자동으로 돌게 한다 (30분)
- **단계 3**: 휴대폰 홈 화면에 앱으로 추가 (2분)
- **단계 4**: Google Docs 자동 저장 연결 (선택, 15분)

단계 1만 해도 "내 컴퓨터에서 명령 한 번 치면 오늘 브리핑이 나오는" 상태가 됩니다.
단계 2까지 해야 손 안 대고 매일 돌아갑니다.

---

## 단계 1. 내 컴퓨터에서 한 번 실행해 보기 (10분)

### 1-1. API 키 넣기

1. 이 폴더 안의 `pipeline` 폴더 → `.env` 파일을 메모장(또는 VS Code)으로 연다.
   - 파일이 안 보이면 탐색기에서 **보기 → 표시 → 숨긴 항목** 체크. (`.`으로 시작하는 파일이라 숨겨질 수 있음)
2. `GEMINI_API_KEY=여기에_API_키` 줄에서 `여기에_API_키` 부분만 지우고 받은 키를 붙여넣는다.
   - 따옴표 없이, 앞뒤 공백 없이. 예: `GEMINI_API_KEY=AIzaSy...`
3. 저장.

> 이 `.env` 파일은 `.gitignore`에 등록되어 있어서 나중에 GitHub에 올려도 **올라가지 않습니다.** 키가 유출될 걱정은 없습니다.
> 단, 이 파일을 카톡·메일 등으로 보내지는 마세요.

### 1-2. 터미널 열기

1. 탐색기에서 이 폴더(`뉴스브리핑 앱`)를 연다.
2. 빈 곳에서 **마우스 오른쪽 클릭 → "터미널에서 열기"** (없으면 주소창에 `powershell` 입력 후 Enter).
3. 검은(또는 파란) 창이 뜨고, 경로 끝이 `뉴스브리핑 앱>` 으로 끝나면 된 것.
4. 경로가 다른 곳(예: `C:\Users\ys898>`)이면 아래를 붙여넣고 Enter 해서 이동한다. (폴더 이름에 `[6]`이 있어서 `-LiteralPath`가 꼭 필요함)
   ```powershell
   Set-Location -LiteralPath "G:\다른 컴퓨터\내 컴퓨터 (1)\내 PC\Desktop\Main\Main\[6] 김덕우 개인 폴더\09 개발·프로젝트\뉴스브리핑 앱"
   ```
   `can't open file '...build_doc.py'` 같은 오류는 거의 항상 이 위치 문제다.
4. 만약 `PS C:\WINDOWS\System32\WindowsPowerShell\v1.0>` 처럼 다른 위치로 열렸으면, 아래를 붙여넣고 Enter 해서 폴더로 이동한다:
   ```
   cd -LiteralPath "G:\다른 컴퓨터\내 컴퓨터 (1)\내 PC\Desktop\Main\Main\[6] 김덕우 개인 폴더\09 개발·프로젝트\뉴스브리핑 앱"
   ```
   (`-LiteralPath`는 경로에 `[6]` 같은 대괄호가 있을 때 필요. 폴더를 옮겼다면 탐색기 주소창에서 복사한 경로를 따옴표 안에 넣으면 됨)

### 1-3. 필요한 라이브러리 설치 (최초 1회)

터미널에 아래를 붙여넣고 Enter:

```bash
python -m pip install -r pipeline/requirements.txt
```

- 1~2분 걸립니다. 마지막에 `Successfully installed ...` 또는 `Requirement already satisfied` 가 나오면 OK.
- `python`을 못 찾는다고 하면 Python이 설치 안 된 것 → https://www.python.org/downloads/ 에서 설치할 때 **"Add python.exe to PATH" 체크** 필수. (이 컴퓨터에는 3.12가 이미 있음)

### 1-4. 실행

```bash
python pipeline/run_all.py --force
```

- **5~10분** 걸립니다. Gemini가 5개 분야를 검색하며 조사하는 시간입니다. 창을 닫지 말고 기다리세요.
- 정상이면 이런 로그가 순서대로 나옵니다:

```
[research] 날짜 2026-11-01, 모델 gemini-2.5-flash, 조사 창 2026-10-31 06:00 ~ 2026-11-01 06:00
[research] 경제: 6건, 그라운딩 출처 23개, 71s
[research] 정치: 5건, 그라운딩 출처 18개, 64s
[research] 사회·사건사고: 5건, ...
[research] 국제: 5건, ...
[research] 산업·기술: 5건, ...
[research] 종합: top5 5개, 연결 4개
[research] 저장: ...\pipeline\raw\2026-11-01.json (총 26건)
[enrich] 저장: ...\docs\data\2026-11-01.json (25건, 썸네일 19건)
[enrich] index.json: 2일치
[build_doc] APPS_SCRIPT_URL / APPS_SCRIPT_SECRET 없음 → Google Docs 생성 생략   ← 단계 4 전까지는 정상
[run_all] 완료: ...\docs\data\2026-11-01.json
```

- 중간에 `JSON 추출 실패(...) → 변환 호출로 복구` 가 떠도 **정상**입니다. 자동으로 고쳐서 진행합니다.
- `--force`는 "오늘 것이 이미 있어도 다시 만들어라"는 뜻입니다. 평소엔 안 붙여도 됩니다.

### 1-5. 결과 보기

**파일로 확인**: `docs/data/` 폴더에 `오늘날짜.json` 이 생겼으면 성공.

**앱 화면으로 확인**: 같은 터미널에서

```bash
python -m http.server 8080 --directory docs
```

를 실행한 뒤 브라우저에서 **http://localhost:8080** 을 엽니다. 날짜 버튼에 오늘이 생기고 실제 뉴스 카드가 보이면 성공입니다.
(기존에 보이던 `(샘플)` 카드는 10/31 날짜의 예시 데이터입니다. 거슬리면 `docs/data/2026-10-31.json`을 지우세요. 다음 실행 때 목록이 자동 갱신됩니다.)

확인이 끝나면 터미널에서 `Ctrl + C` 로 서버를 끕니다.

### 1-6. 안 될 때

| 화면에 보이는 것 | 뜻 | 해결 |
|---|---|---|
| `GEMINI_API_KEY 환경변수가 없습니다` | `.env`에 키가 안 들어감 | `.env` 파일 위치가 `pipeline` 폴더 안인지, `여기에_API_키`가 남아있지 않은지 확인 |
| `API key not valid` / `PERMISSION_DENIED` | 키가 틀림 | AI Studio에서 키를 다시 복사. 앞뒤 공백·줄바꿈 주의 |
| `429` / `RESOURCE_EXHAUSTED` / `quota` | 무료 한도 초과 | 몇 분~1시간 뒤 재시도. 계속되면 AI Studio에서 결제 계정 연결 (사용량이 적어서 월 1달러 미만) |
| `404 ... model not found` | 모델 이름이 바뀜 | `.env`의 `GEMINI_MODEL`을 현재 제공되는 이름으로 변경 (https://ai.google.dev/gemini-api/docs/models) |
| `모든 카테고리 조사가 실패했습니다` | 5개 분야 전부 실패 | 위 오류 중 하나가 원인. 위로 스크롤해서 첫 오류 메시지 확인 |
| 썸네일 0건 | 언론사가 봇 차단 | 기능에는 문제 없음. 카드가 색 배경으로 나옴 |

---

## 단계 2. GitHub에 올려서 매일 자동 실행 (30분)

### 왜 GitHub인가
- **GitHub Actions**: GitHub가 공짜로 빌려주는 서버. "매일 21:00 UTC(=06:00 한국)에 이 명령을 실행해라"를 설정 파일(`.github/workflows/daily.yml`)로 적어두면 내 컴퓨터가 꺼져 있어도 돌아갑니다. 이미 작성되어 있습니다.
- **GitHub Pages**: 저장소 안의 `docs/` 폴더를 그대로 웹사이트로 공개해 주는 기능. 앱 주소가 여기서 나옵니다.
- **Secrets**: API 키처럼 코드에 적으면 안 되는 값을 GitHub에 따로 보관하는 금고.

### 2-1. GitHub 계정 + GitHub Desktop 설치
1. https://github.com 가입/로그인.
2. https://desktop.github.com 에서 **GitHub Desktop** 설치 → 실행 → GitHub 계정으로 로그인.

> GitHub 웹사이트에서 저장소를 **미리 만들 필요 없습니다.** 아래 2-2의 "Publish" 버튼이 저장소를 자동으로 만들어 줍니다.
> (웹에서 이미 만들어 버렸다면 → 아래 "이미 웹에서 저장소를 만든 경우" 참고)

### 2-2. 이 폴더를 GitHub에 올리기 (GitHub Desktop)
1. GitHub Desktop에서 **File → Add local repository** → **Choose...** → 이 폴더(`뉴스브리핑 앱`) 선택 → **Add repository**.
   - "This directory does not appear to be a Git repository" 라는 파란 안내가 뜨면 그 안의 **create a repository** 링크 클릭 → 뜨는 창에서 아무것도 바꾸지 말고 **Create Repository**.
   - 이 시점에는 왼쪽 목록의 **"Other"** 그룹 아래에 폴더 이름으로 나타납니다. "Other"는 *아직 GitHub와 연결 안 된 내 컴퓨터의 저장소* 라는 뜻이라 정상입니다. 다음 단계에서 연결되면 내 계정 이름 아래로 옮겨집니다.
2. 위쪽 가운데 파란 버튼 **Publish repository** 클릭.
   - Name: `daily-briefing` (원하는 이름. 아래 설명의 `daily-briefing` 자리에 그 이름을 넣으면 됨)
   - **"Keep this code private" 체크 해제** ← 중요. Pages를 무료로 쓰려면 Public이어야 합니다. 앱 코드와 뉴스 요약은 공개되지만 API 키는 올라가지 않습니다. 꼭 비공개로 하려면 아래 "비공개로 하려면" 참고.
   - **Publish repository**.
3. 브라우저로 `https://github.com/내아이디/daily-briefing` 를 열어 파일들이 보이면 성공.
   - **확인**: `pipeline` 폴더 안에 `.env` 가 **없어야** 정상입니다 (`.env.example`만 있음).

#### 이미 웹에서 저장소를 만든 경우 (예: `daily-briefing`을 웹에서 먼저 만듦)
"Publish"를 하면 같은 이름이라 실패하거나 다른 이름으로 하나 더 생깁니다. 대신 **기존 저장소에 연결**합니다:
1. 위 2-2의 1번까지 똑같이 한다 (폴더 추가 → create a repository).
2. 메뉴 **Repository → Repository settings... → 왼쪽 Remote** → **Primary remote repository (origin)** 칸에
   `https://github.com/내아이디/daily-briefing.git` 입력 → **Save**.
3. 위쪽 가운데 버튼이 **Push origin** 으로 바뀌면 클릭. (안 바뀌면 GitHub Desktop을 껐다 켠다)
4. 웹에서 빈 저장소를 **Clone** 해 둔 게 있다면 그건 필요 없습니다. GitHub Desktop 왼쪽 목록에서 그 항목을 오른쪽 클릭 → **Remove** (컴퓨터에서 폴더까지 지우려면 "Also move this repository to Recycle Bin" 체크).

> 명령어가 편하면 GitHub Desktop 대신 터미널에서: `git init` → `git add .` → `git commit -m first` → `git branch -M main` → `git remote add origin https://github.com/내아이디/daily-briefing.git` → `git push -u origin main`

### 2-3. API 키 등록 (Secrets) — GitHub **웹사이트**에서
> 2-3부터 2-5까지는 GitHub Desktop이 아니라 **브라우저로 github.com에 접속해서** 합니다. GitHub Desktop에는 Settings 탭이 없습니다.

1. 브라우저에서 `https://github.com/내아이디/daily-briefing` 접속 (GitHub Desktop의 **View on GitHub** 버튼으로 열어도 됨).
   저장소 이름 아래 가로로 **Code · Issues · Pull requests · Actions · ... · Settings** 탭이 있습니다. 맨 오른쪽 **Settings** 클릭.
2. 왼쪽 메뉴 **Secrets and variables → Actions**.
3. 초록 버튼 **New repository secret**.
4. Name: `GEMINI_API_KEY` (대소문자·밑줄 정확히), Secret: 키 붙여넣기 → **Add secret**.

(Docs 연동을 할 때 같은 방법으로 `APPS_SCRIPT_URL`, `APPS_SCRIPT_SECRET` 두 개를 더 추가합니다. 단계 4 참고.)

### 2-4. 앱 주소 만들기 (Pages) — GitHub 웹사이트에서
1. 같은 저장소 페이지의 **Settings → 왼쪽 메뉴 Pages**.
2. **Build and deployment → Source**: `Deploy from a branch`.
3. **Branch**: `main` 선택, 옆 폴더 칸을 `/docs` 로 바꾸고 **Save**.
4. 1~3분 뒤 같은 페이지 위쪽에 **"Your site is live at https://내아이디.github.io/daily-briefing/"** 가 뜹니다. 이게 앱 주소입니다. 열어보면 샘플 카드가 보입니다.

### 2-5. 처음 한 번 수동 실행 — GitHub 웹사이트에서
1. 저장소 페이지 위쪽 **Actions** 탭 (Settings 왼쪽에 있음).
2. "Workflows aren't being run on this repository" 같은 안내가 보이면 초록 버튼 **I understand my workflows, go ahead and enable them** 클릭.
3. 왼쪽 목록에서 **daily-brief** 클릭 → 오른쪽 **Run workflow ▾ → Run workflow** (입력칸은 비워둠).
4. 10초쯤 뒤 새로고침하면 노란 점(실행 중)이 생깁니다. 5~10분 뒤 **초록 체크**가 되면 성공.
   - 빨간 X면 클릭 → **build** → 빨간 줄이 있는 단계를 펼쳐 오류 메시지 확인. 대부분 1-6 표의 원인과 같습니다.
5. 성공하면 저장소 첫 화면에 `brief: 2026-11-01` 같은 커밋이 자동으로 생기고, 2~3분 뒤 앱 주소를 새로고침하면 오늘 브리핑이 보입니다.

### 2-6. 이후에는
- 매일 **06:00 KST**에 자동 실행. 실패하면 **07:00**에 한 번 더 시도. (GitHub 사정으로 몇 분~수십 분 늦을 수 있음)
- 실패가 계속되면 GitHub 가입 메일로 "Run failed" 메일이 옵니다. 그때만 Actions 탭을 보면 됩니다.
- 특정 날짜를 다시 만들고 싶으면 **Run workflow** 에서 `date`에 `2026-11-05` 식으로 입력하고 `force` 체크.

### 비공개로 하려면
Private 저장소에서는 GitHub Pages가 유료(Pro)입니다. 대신 **Cloudflare Pages**(무료)에 연결하면 됩니다: https://pages.cloudflare.com → GitHub 연동 → 저장소 선택 → Build output directory `docs` → 배포. 이 경우 2-4는 건너뜁니다.

---

## 단계 3. 휴대폰에 앱으로 설치 (2분)

1. 안드로이드 **Chrome**에서 앱 주소(`https://내아이디.github.io/daily-briefing/`)를 연다.
2. 오른쪽 위 **⋮ → 홈 화면에 추가** (또는 "앱 설치").
3. 홈 화면에 주황 아이콘이 생깁니다. 열면 주소창 없는 전체 화면 앱으로 뜹니다.
4. 한 번 본 날짜는 지하철 등 오프라인에서도 열립니다. (새 날짜는 인터넷 필요)

PC에서는 Chrome 주소창 오른쪽의 **설치** 아이콘을 누르면 창 앱으로 설치됩니다. 그냥 북마크해도 됩니다.

---

## 단계 4. Google Docs 자동 저장 (선택, 15분)

매일 브리핑을 내 Google Drive에 `뉴스브리핑/2026/11/2026-11-01 뉴스브리핑` 문서로도 남기는 기능입니다.
방식: Google **Apps Script**(구글이 제공하는 무료 스크립트 서비스)에 작은 프로그램을 올려두고, 파이프라인이 거기에 결과를 보내면 그 프로그램이 내 계정으로 문서를 만듭니다. 복잡한 인증 설정이 필요 없습니다.

### 4-1. 스크립트 올리기
1. 브리핑을 저장할 Google 계정으로 https://script.google.com 접속.
2. 왼쪽 위 **새 프로젝트**.
3. 편집기에 있는 기본 코드(`function myFunction() {}`)를 전부 지우고, 이 폴더의 `apps_script/Code.gs` 파일 내용을 **전부 복사해서 붙여넣기**.
4. 위쪽 "제목 없는 프로젝트" 클릭 → 이름을 `뉴스브리핑 문서생성` 으로 → **저장**(Ctrl+S).

### 4-2. 비밀번호 설정
1. 왼쪽 메뉴 **⚙ 프로젝트 설정**.
2. 아래쪽 **스크립트 속성 → 스크립트 속성 추가**.
3. 속성: `SECRET`, 값: 아무 긴 문자열 (예: 비밀번호 생성기로 만든 30자. 이 값을 **메모**해 두세요. 2-3의 Secrets에도 똑같이 넣습니다.)
4. (선택) 문서를 특정 폴더에 넣고 싶으면 속성 `ROOT_FOLDER_ID` 추가. 값은 Drive에서 그 폴더를 열었을 때 주소창 `folders/` 뒤의 긴 문자열. 비워두면 내 드라이브 최상단에 `뉴스브리핑` 폴더를 자동으로 만듭니다.
5. **스크립트 속성 저장**.

### 4-3. 권한 승인 + 테스트
1. 왼쪽 메뉴 **< > 편집기**로 돌아감.
2. 위쪽 툴바에서 함수 선택 드롭다운(기본 `doPost`)을 **`testBuild`** 로 바꾸고 **▶ 실행**.
3. "승인 필요" 창 → **권한 검토** → 계정 선택 → "확인되지 않은 앱" 경고가 뜨면 **고급 → (프로젝트명)(으)로 이동(안전하지 않음)** → **허용**.
   (내가 만든 스크립트라 구글 심사를 안 받은 것뿐입니다.)
4. 아래 실행 로그에 `https://docs.google.com/document/d/...` 가 찍히고, Drive에 `뉴스브리핑/2000/01/2000-01-01 뉴스브리핑` 테스트 문서가 생기면 성공. (지워도 됩니다)

### 4-4. 웹앱으로 배포
1. 오른쪽 위 **배포 → 새 배포**.
2. 왼쪽 ⚙ **유형 선택 → 웹 앱**.
3. 설명: 아무거나. **실행 주체: 나**, **액세스 권한이 있는 사용자: 모든 사용자** ← 이 두 개가 중요.
4. **배포** → 또 권한 승인이 뜨면 4-3과 같이 허용.
5. **웹 앱 URL**(`https://script.google.com/macros/s/.../exec`)을 **복사**.

### 4-5. 연결 (값 두 개를 GitHub와 내 컴퓨터에 각각 넣기)

지금 손에 있어야 하는 값은 두 개입니다.
- **값 A: 웹 앱 URL** — 4-4에서 복사한 `https://script.google.com/macros/s/AKfy.../exec` (끝이 `/exec`)
- **값 B: SECRET** — 4-2에서 스크립트 속성에 넣은 문자열. `pipeline/.env`의 `APPS_SCRIPT_SECRET=` 뒤에 있는 것과 같은 값

이 두 값을 **GitHub(자동 실행용)** 와 **내 컴퓨터(수동 테스트용)** 두 곳에 넣습니다. 둘 다 해야 양쪽에서 Docs가 만들어집니다.

#### (1) GitHub Secrets에 넣기 — 브라우저
1. `https://github.com/내아이디/daily-briefing/settings/secrets/actions` 접속 (2-3에서 `GEMINI_API_KEY`를 넣었던 그 페이지).
2. **New repository secret** 클릭 → Name: `APPS_SCRIPT_URL` / Secret: 값 A 붙여넣기 → **Add secret**.
3. 다시 **New repository secret** 클릭 → Name: `APPS_SCRIPT_SECRET` / Secret: 값 B 붙여넣기 → **Add secret**.
4. 목록에 `GEMINI_API_KEY`, `APPS_SCRIPT_URL`, `APPS_SCRIPT_SECRET` 세 개가 보이면 완료.

#### (2) 내 컴퓨터 `.env`에 넣기 — 메모장
1. `pipeline/.env` 파일을 메모장으로 연다.
2. `APPS_SCRIPT_URL=` 뒤에 값 A를 붙여넣는다. (한 줄에, 따옴표·공백 없이)
3. `APPS_SCRIPT_SECRET=` 뒤에는 값 B가 이미 들어 있으면 그대로 둔다. 비어 있으면 붙여넣는다.
4. 저장. 결과는 이런 모양:
   ```
   APPS_SCRIPT_URL=https://script.google.com/macros/s/AKfycb.../exec
   APPS_SCRIPT_SECRET=aB3dE...(32자)
   ```

#### (3) 확인
터미널(1-2 참고)에서:
```bash
python pipeline/build_doc.py --date 2026-10-31 --force
```
- `[build_doc] 문서 생성: https://docs.google.com/document/d/...` 가 나오고 Drive 폴더에 `2026-10-31 뉴스브리핑` 문서가 생기면 성공. (10/31은 샘플 데이터라 내용은 샘플)
- `unauthorized` 가 나오면 값 B가 Apps Script 스크립트 속성의 `SECRET`과 다른 것. 양쪽을 다시 비교.
- 응답이 JSON이 아니라는 오류면 값 A가 `/exec`로 끝나지 않거나, 4-4에서 액세스 권한을 "모든 사용자"로 안 한 것.

> `Code.gs`를 나중에 수정하면 **배포 → 배포 관리 → ✎ → 버전: 새 버전 → 배포** 를 해야 반영됩니다. 그냥 저장만 하면 옛날 버전이 계속 돕니다.

---

## 바꾸고 싶을 때 (튜닝)

| 바꾸고 싶은 것 | 어디를 고치나 |
|---|---|
| 분야 추가/삭제, 분야당 기사 수 | `pipeline/schema.py` 맨 위 `CATEGORIES` 목록. `n_min`/`n_max`가 기사 수 |
| 조사 기준, 말투, 요약 길이 | `pipeline/prompts/system.txt` (전체 규칙), `category.txt` (분야별), `synthesis.txt` (핵심 5·연결) |
| 더 깊게 조사 (비용 ↑) | 모델을 Pro 계열로: `.env`의 `GEMINI_MODEL`, GitHub는 **Settings → Secrets and variables → Actions → Variables 탭**에 `GEMINI_MODEL` 추가 |
| 실행 시각 | `.github/workflows/daily.yml`의 `cron: "0 21 * * *"`. UTC 기준이라 한국 시간 −9시간 (05:00 KST면 `0 20`) |
| 앱 색·글자 크기 | `docs/style.css` 맨 위 `:root` 변수 |
| 앱 탭 이름 | `docs/app.js` 맨 위 `CAT_LABEL` |

프롬프트나 스키마를 고친 뒤에는 **단계 1-4**로 한 번 돌려보고 GitHub에 올리면(커밋·푸시) 다음 날부터 반영됩니다.

---

## 용어 정리

- **Gemini API 키**: Gemini를 프로그램에서 호출할 때 쓰는 비밀번호. AI Studio(https://aistudio.google.com)에서 발급.
- **그라운딩(Grounding)**: Gemini가 답하기 전에 Google 검색을 먼저 하게 하는 옵션. 이게 있어야 "오늘 뉴스"를 알 수 있음.
- **GitHub Actions**: GitHub가 제공하는 무료 자동 실행 서버. 정해진 시간에 스크립트를 돌림.
- **Secrets**: GitHub Actions가 쓸 비밀값 보관함. 코드에는 안 보임.
- **GitHub Pages**: 저장소의 폴더를 웹사이트로 공개해 주는 기능.
- **PWA**: 웹사이트를 홈 화면에 설치해 앱처럼 쓰는 방식. 앱스토어 불필요.
- **Apps Script**: 구글 서비스(Docs, Drive 등)를 자동화하는 구글의 무료 스크립트 환경.
- **JSON**: 프로그램끼리 데이터를 주고받는 텍스트 형식. `docs/data/날짜.json`이 하루치 브리핑.

---

## 폴더 구조

| 경로 | 역할 |
|---|---|
| `pipeline/run_all.py` | 전체 실행 (research → enrich → build_doc) |
| `pipeline/research.py` | Gemini 호출 (하루 6회) |
| `pipeline/enrich.py` | 링크·사진·중복 정리 (AI 안 씀) |
| `pipeline/build_doc.py` | Apps Script에 보내 Google Docs 생성 |
| `pipeline/schema.py` | 데이터 구조 + 분야 목록 |
| `pipeline/prompts/` | Gemini 프롬프트 3개 |
| `pipeline/.env` | 내 컴퓨터용 설정 (API 키). GitHub에 안 올라감 |
| `pipeline/raw/` | Gemini 원본 응답 (디버그용, 자동 생성, GitHub에 안 올라감) |
| `apps_script/Code.gs` | Apps Script에 붙여넣을 코드 |
| `docs/` | 앱 (GitHub Pages가 이 폴더를 공개) |
| `docs/data/` | 날짜별 브리핑 JSON. 하루 1개씩 쌓임 (약 50~150KB) |
| `.github/workflows/daily.yml` | 매일 자동 실행 설정 |
