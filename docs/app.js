/* 뉴스브리핑 PWA — 프레임워크 없음. docs/data/index.json + YYYY-MM-DD.json 만 읽는다. */
(() => {
  "use strict";

  const CAT_LABEL = { eco: "경제", pol: "정치", soc: "사회", intl: "국제", tech: "산업·기술" };
  const CAT_SHORT = { eco: "경", pol: "정", soc: "사", intl: "국", tech: "기" };
  const WEEK = ["일", "월", "화", "수", "목", "금", "토"];

  const $ = (s, el = document) => el.querySelector(s);
  const el = {
    dates: $("#dates"), tabs: $("#tabs"), main: $("#main"), status: $("#status"),
    badge: $("#badge"), docLink: $("#docLink"), meta: $("#meta"), tpl: $("#tpl-card"),
    themeSwitch: $("#themeSwitch"),
  };

  const state = { dates: [], date: null, brief: null, tab: "top", open: new Set(), view: "brief" };

  // ---------- data ----------
  async function getJSON(path) {
    const r = await fetch(path, { cache: "no-cache" });
    if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
    return r.json();
  }

  async function loadIndex() {
    state.dates = await getJSON("./data/index.json");
  }

  async function loadBrief(date) {
    state.brief = await getJSON(`./data/${date}.json`);
    state.date = date;
    state.open.clear();
  }

  function allItems() {
    const out = [];
    for (const c of state.brief.categories) for (const it of c.items) out.push({ it, cat: c });
    return out;
  }
  function findItem(id) {
    return allItems().find((x) => x.it.id === id);
  }

  // ---------- routing ----------
  function readHash() {
    const m = location.hash.replace(/^#/, "").split("/");
    if (m[0] === "archive") return { archive: true, date: null, tab: null };
    return { date: /^\d{4}-\d{2}-\d{2}$/.test(m[0]) ? m[0] : null, tab: m[1] || null };
  }
  function writeHash(push) {
    const h = `#${state.date}/${state.tab}`;
    if (location.hash !== h) (push ? history.pushState : history.replaceState).call(history, null, "", h);
  }

  // ---------- render helpers ----------
  function fmtDate(d) {  // 브라우저 시간대와 무관하게 KST 날짜 그대로 표시
    const dt = new Date(d + "T00:00:00Z");
    const diff = Math.round((new Date(todayKST() + "T00:00:00Z") - dt) / 86400000);
    const base = `${dt.getUTCMonth() + 1}/${dt.getUTCDate()} (${WEEK[dt.getUTCDay()]})`;
    return diff === 0 ? `오늘 ${base}` : diff === 1 ? `어제 ${base}` : base;
  }
  function chip(code, label) {
    const s = document.createElement("span");
    s.className = "chip";
    s.textContent = label || CAT_LABEL[code] || code;
    s.style.setProperty("--c", `var(--${code})`);
    return s;
  }
  function importance(n) {
    const on = "●".repeat(n), off = "●".repeat(5 - n);
    return `${on}<span class="off">${off}</span>`;
  }
  function paragraphs(text) {
    return String(text || "")
      .split(/\n+/)
      .map((p) => p.trim())
      .filter(Boolean)
      .map((p) => {
        const e = document.createElement("p");
        e.textContent = p;
        return e;
      });
  }

  // ---------- header ----------
  // ---------- 주 단위 (일요일 시작, KST) ----------
  function todayKST() {
    return new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);
  }
  function weekStart(d) {  // "YYYY-MM-DD" → 그 주 일요일 "YYYY-MM-DD"
    const dt = new Date(d + "T00:00:00Z");
    dt.setUTCDate(dt.getUTCDate() - dt.getUTCDay());
    return dt.toISOString().slice(0, 10);
  }
  function addDays(d, n) {
    const dt = new Date(d + "T00:00:00Z");
    dt.setUTCDate(dt.getUTCDate() + n);
    return dt.toISOString().slice(0, 10);
  }
  function shortDate(d) {
    const dt = new Date(d + "T00:00:00Z");
    return `${dt.getUTCMonth() + 1}/${dt.getUTCDate()}(${WEEK[dt.getUTCDay()]})`;
  }
  function thisWeekDates() {
    const ws = weekStart(todayKST());
    return state.dates.filter((d) => d >= ws);
  }
  function pastDates() {
    const ws = weekStart(todayKST());
    return state.dates.filter((d) => d < ws);
  }

  function renderDates() {
    el.dates.innerHTML = "";
    const week = thisWeekDates();
    const shown = [...week];
    // 지난 날짜를 보고 있으면 그 날짜 칩도 함께 표시
    if (state.view === "brief" && state.date && !shown.includes(state.date)) shown.push(state.date);
    for (const d of shown) {
      const b = document.createElement("button");
      b.textContent = fmtDate(d);
      b.className = state.view === "brief" && d === state.date ? "on" : "";
      b.onclick = () => go(d, state.tab);
      el.dates.appendChild(b);
    }
    const past = pastDates();
    if (past.length) {
      const b = document.createElement("button");
      b.innerHTML = `지난 브리핑<span class="n">${past.length}</span>`;
      b.className = "past" + (state.view === "archive" ? " on" : "");
      b.onclick = goArchive;
      el.dates.appendChild(b);
    }
    const on = $(".on", el.dates);
    if (on) on.scrollIntoView({ inline: "center", block: "nearest" });
  }

  // ---------- 지난 브리핑 (주 단위 묶음) ----------
  function renderArchive() {
    const wrap = document.createElement("section");
    wrap.className = "archive";
    const past = pastDates();
    if (!past.length) {
      wrap.innerHTML = '<p class="status">지난 브리핑이 없습니다.</p>';
      return wrap;
    }
    const groups = new Map();  // weekStart → dates(desc)
    for (const d of past) {
      const ws = weekStart(d);
      if (!groups.has(ws)) groups.set(ws, []);
      groups.get(ws).push(d);
    }
    for (const [ws, dates] of groups) {
      const h = document.createElement("h2");
      h.className = "sect";
      h.textContent = `${shortDate(ws)} ~ ${shortDate(addDays(ws, 6))} · ${dates.length}일`;
      wrap.appendChild(h);
      const ul = document.createElement("ul");
      ul.className = "weeklist";
      for (const d of dates) {
        const li = document.createElement("li");
        const b = document.createElement("button");
        b.type = "button";
        b.innerHTML = `<span class="d">${esc(shortDate(d))}</span><span class="full">${esc(d)}</span>`;
        b.onclick = () => go(d, "top");
        li.appendChild(b);
        ul.appendChild(li);
      }
      wrap.appendChild(ul);
    }
    return wrap;
  }

  function goArchive() {
    state.view = "archive";
    if (location.hash !== "#archive") history.pushState(null, "", "#archive");
    renderDates();
    el.tabs.hidden = true;
    el.badge.hidden = true;
    el.docLink.hidden = true;
    el.meta.textContent = `지난 브리핑 ${pastDates().length}일치 · 이번 주는 상단 날짜에서`;
    el.main.innerHTML = "";
    el.main.appendChild(renderArchive());
    window.scrollTo(0, 0);
  }

  function renderTabs() {
    el.tabs.innerHTML = "";
    const tabs = [{ code: "top", label: "핵심", n: state.brief.top5.length, color: "var(--top)" }];
    for (const c of state.brief.categories) {
      tabs.push({ code: c.code, label: CAT_LABEL[c.code] || c.name, n: c.items.length, color: `var(--${c.code})` });
    }
    for (const t of tabs) {
      const b = document.createElement("button");
      b.innerHTML = `${t.label}<span class="n">${t.n}</span>`;
      b.style.setProperty("--c", t.color);
      b.className = t.code === state.tab ? "on" : "";
      b.onclick = () => go(state.date, t.code);
      el.tabs.appendChild(b);
    }
    const on = $(".on", el.tabs);
    if (on) on.scrollIntoView({ inline: "nearest", block: "nearest" });
  }

  // ---------- views ----------
  function renderTop() {
    const b = state.brief;
    const frag = document.createDocumentFragment();

    const hero = document.createElement("section");
    hero.className = "hero";
    hero.innerHTML = `<p class="one"></p><p class="sub"></p>`;
    $(".one", hero).textContent = b.one_liner || `${b.date} 브리핑`;
    $(".sub", hero).textContent = `${b.date} · ${allItems().length}건`;
    frag.appendChild(hero);

    const h1 = document.createElement("h2");
    h1.className = "sect";
    h1.textContent = "오늘의 핵심";
    frag.appendChild(h1);
    const ol = document.createElement("ol");
    ol.className = "toplist";
    b.top5.forEach((t, i) => {
      const f = findItem(t.ref);
      if (!f) return;
      const li = document.createElement("li");
      li.innerHTML = `<span class="num">${i + 1}</span><div><p class="hl"></p><p class="why"></p></div>`;
      const hl = $(".hl", li);
      hl.appendChild(chip(f.cat.code));
      hl.appendChild(document.createTextNode(f.it.headline));
      $(".why", li).textContent = t.why || f.it.summary;
      li.onclick = () => openItem(f.it.id);
      ol.appendChild(li);
    });
    frag.appendChild(ol);

    if (b.connections.length) {
      const h2 = document.createElement("h2");
      h2.className = "sect";
      h2.textContent = "사건 연결";
      frag.appendChild(h2);
      const ul = document.createElement("ul");
      ul.className = "conn";
      for (const c of b.connections) {
        const a = findItem(c.from), z = findItem(c.to);
        if (!a || !z) continue;
        const li = document.createElement("li");
        const pair = document.createElement("div");
        pair.className = "pair";
        const sa = document.createElement("span"); sa.dataset.id = a.it.id; sa.textContent = a.it.headline;
        const ar = document.createElement("span"); ar.className = "arrow"; ar.textContent = "→";
        const sz = document.createElement("span"); sz.dataset.id = z.it.id; sz.textContent = z.it.headline;
        sa.onclick = () => openItem(a.it.id);
        sz.onclick = () => openItem(z.it.id);
        pair.append(sa, ar, sz);
        const how = document.createElement("p");
        how.className = "how";
        how.textContent = c.how;
        li.append(pair, how);
        ul.appendChild(li);
      }
      frag.appendChild(ul);
    }
    return frag;
  }

  function renderCategory(code) {
    const cat = state.brief.categories.find((c) => c.code === code);
    const list = document.createElement("div");
    list.className = "list";
    if (!cat || !cat.items.length) {
      list.innerHTML = `<p class="status">이 분야는 오늘 항목이 없습니다.</p>`;
      return list;
    }
    for (const it of cat.items) list.appendChild(card(it, cat));
    return list;
  }

  function card(it, cat) {
    const node = el.tpl.content.firstElementChild.cloneNode(true);
    node.classList.add(`cat-${cat.code}`);
    node.dataset.id = it.id;

    const thumb = $(".thumb", node), img = $("img", thumb);
    $(".ph", thumb).textContent = CAT_SHORT[cat.code] || "";
    if (it.image) {
      img.dataset.stage = "0";
      img.src = it.image;
      img.onerror = () => {
        if (img.dataset.stage === "0") {
          img.dataset.stage = "1";
          img.src = `https://images.weserv.nl/?url=${encodeURIComponent(it.image.replace(/^https?:\/\//, ""))}&w=800&h=400&fit=cover`;
        } else {
          thumb.classList.add("noimg");
        }
      };
    } else {
      thumb.classList.add("noimg");
    }

    $(".chip", node).textContent = CAT_LABEL[cat.code] || cat.name;
    $(".imp", node).innerHTML = importance(it.importance || 3);
    $(".imp", node).title = `중요도 ${it.importance}/5`;
    $(".hl", node).textContent = it.headline;
    $(".sum", node).textContent = it.summary;

    const more = $(".more", node);
    const impact = $(".impact", more);
    for (const x of it.impact || []) {
      const li = document.createElement("li");
      li.textContent = x;
      impact.appendChild(li);
    }
    if (!impact.children.length) impact.previousElementSibling.hidden = impact.hidden = true;

    const watch = $(".watch", more);
    if (it.watch_next) watch.innerHTML = `<b>다음에 볼 것</b> · ${esc(it.watch_next)}`;
    else watch.hidden = true;

    const detail = $(".detail", more);
    const ps = paragraphs(it.detail);
    if (ps.length) ps.forEach((p) => detail.appendChild(p));
    else detail.previousElementSibling.hidden = detail.hidden = true;

    const src = $(".src", more);
    for (const s of it.sources || []) {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = s.url; a.target = "_blank"; a.rel = "noopener";
      if (s.publisher) {
        const p = document.createElement("span"); p.className = "pub"; p.textContent = s.publisher;
        a.appendChild(p);
      }
      a.appendChild(document.createTextNode(s.title || s.url));
      li.appendChild(a);
      src.appendChild(li);
    }
    if (!src.children.length) src.previousElementSibling.hidden = src.hidden = true;

    const kw = $(".kw", more);
    if (it.keywords && it.keywords.length) kw.textContent = "# " + it.keywords.join("  # ");
    else kw.hidden = true;

    const btn = $(".toggle", node);
    const setOpen = (open) => {
      more.hidden = !open;
      node.classList.toggle("open", open);
      btn.textContent = open ? "접기" : "더 보기";
      if (open) state.open.add(it.id); else state.open.delete(it.id);
    };
    btn.onclick = () => setOpen(more.hidden);
    $(".hl", node).onclick = () => setOpen(more.hidden);
    if (state.open.has(it.id)) setOpen(true);
    return node;
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function openItem(id) {
    const f = findItem(id);
    if (!f) return;
    state.open.add(id);
    go(state.date, f.cat.code, id);
  }

  // ---------- main render ----------
  function renderMain(focusId) {
    el.main.innerHTML = "";
    el.main.appendChild(state.tab === "top" ? renderTop() : renderCategory(state.tab));
    if (focusId) {
      const node = $(`[data-id="${focusId}"]`, el.main);
      if (node) {
        node.classList.add("hi");
        setTimeout(() => node.scrollIntoView({ behavior: "smooth", block: "start" }), 30);
        setTimeout(() => node.classList.remove("hi"), 2500);
      }
    } else {
      window.scrollTo({ top: 0 });
    }
  }

  function renderChrome() {
    const b = state.brief;
    el.badge.hidden = !b.sample;
    el.docLink.hidden = !b.doc_url;
    if (b.doc_url) el.docLink.href = b.doc_url;
    const savedAt = b.doc_saved_at ? ` · 앱 문서 ${kstHM(b.doc_saved_at)}` : "";
    el.meta.textContent = `생성 ${(b.generated_at || "").replace("T", " ").slice(0, 16)}${b.model ? " · " + b.model : ""}${savedAt}`;
  }

  async function go(date, tab, focusId) {
    try {
      const fromArchive = state.view === "archive";
      state.view = "brief";
      el.tabs.hidden = false;
      if (date !== state.date) {
        el.status.textContent = "불러오는 중…";
        await loadBrief(date);
      }
      const valid = ["top", ...state.brief.categories.map((c) => c.code)];
      state.tab = valid.includes(tab) ? tab : "top";
      writeHash(fromArchive);
      renderDates();
      renderTabs();
      renderChrome();
      renderMain(focusId);
    } catch (e) {
      el.main.innerHTML = `<p class="status">불러오지 못했습니다: ${esc(e.message)}</p>`;
    }
  }

  function kstHM(iso) {  // ISO 시각 → "11/05 05:52" (KST)
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    const p = new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }).formatToParts(d);
    const g = (t) => (p.find((x) => x.type === t) || {}).value;
    return `${g("month")}/${g("day")} ${g("hour")}:${g("minute")}`;
  }

  // ---------- 테마 (밝게/어둡게) ----------
  const THEME_COLOR = { light: "#f4f5f8", dark: "#0f1115" };
  function applyTheme(theme) {
    const dark = theme === "dark";
    if (dark) document.documentElement.setAttribute("data-theme", "dark");
    else document.documentElement.removeAttribute("data-theme");
    el.themeSwitch.setAttribute("aria-checked", String(dark));
    const m = document.querySelector('meta[name="theme-color"]');
    if (m) m.setAttribute("content", THEME_COLOR[dark ? "dark" : "light"]);
    try { localStorage.setItem("theme", dark ? "dark" : "light"); } catch (_) {}
  }
  function initTheme() {
    let saved = null;
    try { saved = localStorage.getItem("theme"); } catch (_) {}
    applyTheme(saved === "dark" ? "dark" : "light");
    el.themeSwitch.addEventListener("click", () => {
      const nowDark = document.documentElement.getAttribute("data-theme") === "dark";
      applyTheme(nowDark ? "light" : "dark");
    });
  }

  async function init() {
    initTheme();
    try {
      await loadIndex();
      if (!state.dates.length) {
        el.status.textContent = "아직 브리핑이 없습니다. 첫 실행 후 다시 열어주세요.";
        return;
      }
      const h = readHash();
      const date = h.date && state.dates.includes(h.date) ? h.date : state.dates[0];
      await go(date, h.tab || "top");
      if (h.archive) goArchive();
    } catch (e) {
      el.status.textContent = `불러오지 못했습니다: ${e.message}`;
    }
    window.addEventListener("hashchange", () => {
      const h = readHash();
      if (h.archive) { if (state.view !== "archive") goArchive(); return; }
      if (h.date && (h.date !== state.date || h.tab !== state.tab || state.view !== "brief")) go(h.date, h.tab || "top");
    });
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("./sw.js").catch(() => {});
    }
  }

  init();
})();
