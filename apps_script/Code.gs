/**
 * 뉴스브리핑 → Google Docs 생성 웹앱
 *
 * 설치:
 *  1. script.google.com → 새 프로젝트 → 이 파일 내용 붙여넣기
 *  2. 프로젝트 설정 → 스크립트 속성 추가:
 *       SECRET          : 아무 긴 문자열 (GitHub Secrets의 APPS_SCRIPT_SECRET 과 동일하게)
 *       ROOT_FOLDER_ID  : (선택) 문서를 넣을 Drive 폴더 ID. 비우면 내 드라이브에 "뉴스브리핑" 폴더를 만든다.
 *  3. 배포 → 새 배포 → 유형: 웹 앱 / 실행 주체: 나 / 액세스 권한: 모든 사용자 → 배포
 *  4. 웹 앱 URL을 GitHub Secrets의 APPS_SCRIPT_URL 에 등록
 *  5. (테스트) 편집기에서 testBuild 실행 → 권한 승인 → Drive에 샘플 문서 생기는지 확인
 *
 * 코드를 고치면 "배포 관리 → 새 버전"으로 다시 배포해야 반영된다.
 *
 * [Gemini 앱 작업 모드 연동]  GET ?mode=inbox&date=YYYY-MM-DD&secret=...
 *   Gemini 앱이 Drive "뉴스브리핑/inbox" 에 저장한 "YYYY-MM-DD.json" 문서의 본문 텍스트를 돌려준다.
 *   GitHub Actions 의 pipeline/fetch_inbox.py 가 이 주소를 호출한다.
 *   (테스트) 편집기에서 testInbox 실행 → 권한 승인 → 로그에 문서 본문이 찍히는지 확인
 */

const ROOT_FOLDER_NAME = '뉴스브리핑';

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    const secret = PropertiesService.getScriptProperties().getProperty('SECRET');
    if (!secret || body.secret !== secret) {
      return jsonOut({ ok: false, error: 'unauthorized' });
    }
    const url = buildDoc(body.brief, body.force === true);
    return jsonOut({ ok: true, url: url });
  } catch (err) {
    return jsonOut({ ok: false, error: String(err && err.stack || err) });
  }
}

function doGet(e) {
  const p = (e && e.parameter) || {};
  if (p.mode === 'inbox') {
    try {
      const secret = PropertiesService.getScriptProperties().getProperty('SECRET');
      if (!secret || p.secret !== secret) return jsonOut({ ok: false, error: 'unauthorized' });
      return jsonOut(readInbox(p.date));
    } catch (err) {
      return jsonOut({ ok: false, error: String(err && err.stack || err) });
    }
  }
  return jsonOut({ ok: true, message: 'news-brief doc builder. POST JSON {secret, brief, force} / GET ?mode=inbox&date=YYYY-MM-DD&secret=...' });
}

/* ---------- Gemini 앱(작업 모드) 결과 읽기 ---------- */
const INBOX_FOLDER_NAME = 'inbox';

/** 파일 본문을 문자열로. Google Docs 면 본문 텍스트, 그 외(txt/json)는 파일 내용 그대로 */
function fileText(file) {
  if (file.getMimeType() === MimeType.GOOGLE_DOCS) {
    return DocumentApp.openById(file.getId()).getBody().getText();
  }
  return file.getBlob().getDataAsString('UTF-8');
}

/** date(YYYY-MM-DD)로 inbox 문서를 찾는다. 이름이 "YYYY-MM-DD.json" 또는 "YYYY-MM-DD"로 시작하면 인정 */
function findInboxFile(date) {
  const inbox = getOrCreateFolder(rootFolder(), INBOX_FOLDER_NAME);
  let best = null;
  const consider = f => {
    if (f.isTrashed()) return;
    const name = f.getName();
    if (name.indexOf(date) !== 0) return;  // 날짜로 시작하는 이름만
    if (!best || f.getLastUpdated() > best.getLastUpdated()) best = f;
  };
  // 1) inbox 폴더 안
  const it = inbox.getFiles();
  while (it.hasNext()) consider(it.next());
  if (best) return { file: best, where: 'inbox' };
  // 2) Gemini가 다른 곳에 저장했을 때 대비: 내 드라이브 전체에서 이름으로 검색 (Docs/텍스트만)
  const q = "title contains '" + date + "' and trashed = false and (mimeType = 'application/vnd.google-apps.document' or mimeType = 'text/plain' or mimeType = 'application/json')";
  const it2 = DriveApp.searchFiles(q);
  while (it2.hasNext()) consider(it2.next());
  return best ? { file: best, where: 'search' } : null;
}

function readInbox(date) {
  if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return { ok: false, error: 'bad_date' };
  const hit = findInboxFile(date);
  if (!hit) return { ok: false, error: 'not_found', date: date };
  const f = hit.file;
  return {
    ok: true, date: date, name: f.getName(), url: f.getUrl(), where: hit.where,
    updated: f.getLastUpdated().toISOString(), text: fileText(f),
  };
}

/** 편집기에서 직접 실행해 권한 승인 + 동작 확인용. 날짜를 오늘(KST)로 바꿔서 실행 */
function testInbox() {
  const today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd');
  const r = readInbox(today);
  Logger.log(JSON.stringify({ ok: r.ok, error: r.error, name: r.name, where: r.where, len: (r.text || '').length }));
  if (r.text) Logger.log(r.text.slice(0, 500));
}

function jsonOut(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function getOrCreateFolder(parent, name) {
  const it = parent.getFoldersByName(name);
  return it.hasNext() ? it.next() : parent.createFolder(name);
}

function rootFolder() {
  const id = PropertiesService.getScriptProperties().getProperty('ROOT_FOLDER_ID');
  if (id) return DriveApp.getFolderById(id);
  return getOrCreateFolder(DriveApp.getRootFolder(), ROOT_FOLDER_NAME);
}

const CAT_CODE_TO_LABEL = { eco: '경제', pol: '정치', soc: '사회·사건사고', intl: '국제', tech: '산업·기술' };

function buildDoc(brief, force) {
  const parts = brief.date.split('-'); // YYYY-MM-DD
  const folder = getOrCreateFolder(getOrCreateFolder(rootFolder(), parts[0]), parts[1]);
  const title = brief.date + ' 뉴스브리핑';

  const existing = folder.getFilesByName(title);
  while (existing.hasNext()) {
    const f = existing.next();
    if (!force) return f.getUrl();
    f.setTrashed(true);
  }

  const doc = DocumentApp.create(title);
  DriveApp.getFileById(doc.getId()).moveTo(folder);
  const body = doc.getBody();
  const H = DocumentApp.ParagraphHeading;
  const itemsById = {};
  (brief.categories || []).forEach(c => (c.items || []).forEach(it => { itemsById[it.id] = { it: it, cat: c }; }));

  body.appendParagraph(title).setHeading(H.TITLE);
  if (brief.one_liner) body.appendParagraph('한 줄 요약: ' + brief.one_liner).setItalic(true);
  body.appendParagraph('생성: ' + (brief.generated_at || '') + (brief.model ? '  ·  모델: ' + brief.model : ''))
      .setFontSize(9).setForegroundColor('#888888');

  // 오늘의 핵심 5
  if (brief.top5 && brief.top5.length) {
    body.appendParagraph('오늘의 핵심 5').setHeading(H.HEADING1);
    brief.top5.forEach((t, i) => {
      const e = itemsById[t.ref];
      const label = e ? '[' + e.cat.name + '] ' + e.it.headline : t.ref;
      const p = body.appendParagraph((i + 1) + '. ' + label + (t.why ? ' — ' + t.why : ''));
      p.editAsText().setBold(0, label.length + 2, true);
    });
  }

  // 사건 연결
  if (brief.connections && brief.connections.length) {
    body.appendParagraph('사건 연결').setHeading(H.HEADING1);
    brief.connections.forEach(cn => {
      const a = itemsById[cn.from], b = itemsById[cn.to];
      const line = (a ? a.it.headline : cn.from) + ' → ' + (b ? b.it.headline : cn.to) + ': ' + (cn.how || '');
      body.appendListItem(line).setGlyphType(DocumentApp.GlyphType.BULLET);
    });
  }

  // 카테고리별
  (brief.categories || []).forEach(c => {
    body.appendParagraph(c.name || CAT_CODE_TO_LABEL[c.code] || c.code).setHeading(H.HEADING1);
    (c.items || []).forEach(it => {
      body.appendParagraph(it.headline + '  ' + '★'.repeat(it.importance || 0) + '☆'.repeat(5 - (it.importance || 0)))
          .setHeading(H.HEADING2);
      if (it.summary) body.appendParagraph(it.summary);

      if (it.impact && it.impact.length) {
        body.appendParagraph('파급').setHeading(H.HEADING3);
        it.impact.forEach(x => body.appendListItem(x).setGlyphType(DocumentApp.GlyphType.BULLET));
      }
      if (it.watch_next) {
        const p = body.appendParagraph('다음에 볼 것: ' + it.watch_next);
        p.editAsText().setBold(0, 7, true);
      }
      if (it.detail) {
        body.appendParagraph('상세').setHeading(H.HEADING3);
        String(it.detail).split(/\n+/).forEach(para => { if (para.trim()) body.appendParagraph(para.trim()); });
      }
      if (it.sources && it.sources.length) {
        body.appendParagraph('원문').setHeading(H.HEADING3);
        it.sources.forEach(s => {
          const label = (s.publisher ? '[' + s.publisher + '] ' : '') + (s.title || s.url);
          const li = body.appendListItem(label).setGlyphType(DocumentApp.GlyphType.BULLET);
          li.editAsText().setLinkUrl(s.url);
        });
      }
      if (it.keywords && it.keywords.length) {
        body.appendParagraph('키워드: ' + it.keywords.join(', ')).setFontSize(9).setForegroundColor('#888888');
      }
    });
  });

  doc.saveAndClose();
  return doc.getUrl();
}

/** 편집기에서 직접 실행해 권한 승인 + 동작 확인용 */
function testBuild() {
  const sample = {
    date: '2000-01-01',
    generated_at: new Date().toISOString(),
    model: 'test',
    one_liner: '테스트 문서',
    top5: [{ ref: 'eco-01', why: '테스트' }],
    connections: [{ from: 'eco-01', to: 'pol-01', how: '테스트 연결' }],
    categories: [
      { name: '경제', code: 'eco', items: [{ id: 'eco-01', headline: '테스트 사건', importance: 4, summary: '요약.',
        impact: ['영향 1', '영향 2'], detail: '상세 문단 1.\n상세 문단 2.', watch_next: '내일 발표',
        keywords: ['테스트'], sources: [{ title: '예시 기사', publisher: '예시', url: 'https://example.com' }] }] },
      { name: '정치', code: 'pol', items: [{ id: 'pol-01', headline: '테스트 사건 2', importance: 3, summary: '요약 2.',
        impact: [], detail: '', watch_next: '', keywords: [], sources: [] }] }
    ]
  };
  Logger.log(buildDoc(sample, true));
}
