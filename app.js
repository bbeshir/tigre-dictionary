(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const PAGE_SIZE = 40;

  let vocabulary = [];
  let stats = {};
  let state = {
    q: "",
    pos: "",
    letter: "",
    sort: "default",
    onlyEnglish: false,
    page: 1,
  };

  const POS_ORDER = [
    "Verb", "Noun", "Adjective", "Proper name", "Phrase / idiom",
    "Pronoun", "Adverb", "Preposition", "Conjunction", "Numeral",
    "Interjection", "Particle", "Other", "Uncertain",
  ];

  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }
  function fmt(n) { return Number(n || 0).toLocaleString("en-US"); }

  async function init() {
    try {
      const [vRes, sRes] = await Promise.all([
        fetch("data/vocabulary.json"),
        fetch("data/stats.json"),
      ]);
      if (!vRes.ok) throw new Error("vocabulary.json: " + vRes.status);
      vocabulary = await vRes.json();
      stats = sRes.ok ? await sRes.json() : {};
      renderStats();
      renderWordOfDay();
      renderPosChips();
      renderFilterControls();
      render();
    } catch (err) {
      console.error(err);
      $("resultSummary").textContent = "Could not load the dictionary data.";
      $("results").innerHTML = `<div class="empty-state"><h3>Something went wrong</h3><p>The vocabulary data failed to load. Try reloading the page.</p></div>`;
    }
  }

  function renderStats() {
    $("statTotal").textContent = fmt(stats.total_headwords || vocabulary.length);
    $("statEnglish").textContent = fmt(stats.with_english);
    $("statPos").textContent = fmt(stats.pos_categories);
    $("aboutTotal").textContent = fmt(stats.total_headwords || vocabulary.length);
    $("footerCount").textContent = `${fmt(stats.total_headwords || vocabulary.length)} headwords indexed`;
  }

  function dayIndex() {
    const now = new Date();
    const start = new Date(now.getFullYear(), 0, 0);
    const diff = now - start;
    return Math.floor(diff / 86400000);
  }

  function renderWordOfDay() {
    const withEnglish = vocabulary.filter((e) => e.senses && e.senses.length && e.senses[0].text && e.senses[0].text.length < 70);
    if (!withEnglish.length) return;
    const idx = dayIndex() % withEnglish.length;
    const e = withEnglish[idx];
    $("wotdWord").textContent = e.headword;
    $("wotdTranslit").textContent = e.translit || "";
    $("wotdGloss").textContent = e.senses[0].text;
    $("wotdLink").href = "words/" + e.slug + ".html";
    $("wotdLink").onclick = (ev) => { ev.preventDefault(); openEntry(e); };
  }

  function renderPosChips() {
    const counts = (stats.pos_counts) || {};
    const order = POS_ORDER.filter((p) => counts[p]);
    $("posChipRow").innerHTML = order.map((p) => (
      `<button class="pos-chip" data-pos="${esc(p)}"><b>${fmt(counts[p])}</b> ${esc(p)}</button>`
    )).join("");
    $("posChipRow").querySelectorAll("[data-pos]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.pos = btn.dataset.pos;
        state.page = 1;
        $("posFilter").value = state.pos;
        document.getElementById("browse").scrollIntoView({ behavior: "smooth" });
        render();
      });
    });
  }

  function renderFilterControls() {
    const counts = (stats.pos_counts) || {};
    const order = POS_ORDER.filter((p) => counts[p]);
    $("posFilter").innerHTML = '<option value="">All parts of speech</option>' +
      order.map((p) => `<option value="${esc(p)}">${esc(p)} (${fmt(counts[p])})</option>`).join("");

    const letters = Object.keys((stats.letter_counts) || {});
    const az = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").filter((l) => letters.includes(l));
    const withHash = letters.includes("#") ? ["#", ...az] : az;
    $("letterRow").innerHTML = withHash.map((l) => (
      `<button class="letter-chip" data-letter="${esc(l)}" title="${l === '#' ? 'No transliteration recorded' : l}">${l}</button>`
    )).join("");
    $("letterRow").querySelectorAll("[data-letter]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.letter = state.letter === btn.dataset.letter ? "" : btn.dataset.letter;
        state.page = 1;
        syncControls();
        render();
      });
    });

    $("search").addEventListener("input", debounce(() => { state.q = $("search").value.trim().toLowerCase(); state.page = 1; render(); }, 150));
    $("posFilter").addEventListener("change", () => { state.pos = $("posFilter").value; state.page = 1; render(); });
    $("sortFilter").addEventListener("change", () => { state.sort = $("sortFilter").value; state.page = 1; render(); });
    $("onlyEnglish").addEventListener("change", () => { state.onlyEnglish = $("onlyEnglish").checked; state.page = 1; render(); });
    $("clearFilters").addEventListener("click", clearFilters);

    $("heroSearchForm").addEventListener("submit", (ev) => {
      ev.preventDefault();
      const val = $("heroSearch").value.trim();
      state.q = val.toLowerCase();
      $("search").value = val;
      state.page = 1;
      document.getElementById("browse").scrollIntoView({ behavior: "smooth" });
      render();
    });

    $("closeEntry").addEventListener("click", () => $("entryDialog").close());
    $("aboutLink").addEventListener("click", (ev) => { ev.preventDefault(); $("aboutDialog").showModal(); });
    $("closeAbout").addEventListener("click", () => $("aboutDialog").close());
  }

  function clearFilters() {
    state = { q: "", pos: "", letter: "", sort: "default", onlyEnglish: false, page: 1 };
    $("search").value = ""; $("heroSearch").value = "";
    $("posFilter").value = ""; $("sortFilter").value = "default"; $("onlyEnglish").checked = false;
    syncControls();
    render();
  }

  function syncControls() {
    $("letterRow").querySelectorAll(".letter-chip").forEach((b) => {
      b.classList.toggle("active", b.dataset.letter === state.letter);
    });
  }

  function debounce(fn, ms) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  }

  function filtered() {
    let d = vocabulary;
    if (state.pos) d = d.filter((e) => e.pos === state.pos);
    if (state.letter) d = d.filter((e) => e.letter === state.letter);
    if (state.onlyEnglish) d = d.filter((e) => e.has_english);
    if (state.q) d = d.filter((e) => e.search_text.includes(state.q));
    d = d.slice();
    if (state.sort === "alpha") d.sort((a, b) => (a.translit || "\uffff").localeCompare(b.translit || "\uffff"));
    else if (state.sort === "alpha-desc") d.sort((a, b) => (b.translit || "").localeCompare(a.translit || ""));
    return d;
  }

  function render() {
    const d = filtered();
    const totalPages = Math.max(1, Math.ceil(d.length / PAGE_SIZE));
    state.page = Math.min(state.page, totalPages);
    const start = (state.page - 1) * PAGE_SIZE;
    const items = d.slice(start, start + PAGE_SIZE);

    $("resultSummary").textContent = d.length
      ? `Showing ${fmt(start + 1)}–${fmt(Math.min(start + PAGE_SIZE, d.length))} of ${fmt(d.length)}`
      : "No matching headwords";
    $("emptyState").hidden = d.length > 0;
    $("results").innerHTML = items.map(rowHtml).join("");
    $("pagination").innerHTML = pagerHtml(totalPages);

    $("results").querySelectorAll("[data-id]").forEach((row) => {
      row.addEventListener("click", () => {
        const e = vocabulary.find((x) => x.id === row.dataset.id);
        if (e) openEntry(e);
      });
      row.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); row.click(); }
      });
    });
    $("pagination").querySelectorAll("[data-page]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.page = Number(btn.dataset.page);
        document.getElementById("browse").scrollIntoView({ behavior: "smooth", block: "start" });
        render();
      });
    });
  }

  function firstGloss(e) {
    if (e.senses && e.senses.length) return e.senses[0].text;
    if (e.sub_entries && e.sub_entries.length) return e.sub_entries[0].text;
    return null;
  }

  function rowHtml(e) {
    const gloss = firstGloss(e);
    const extra = (e.senses ? e.senses.length : 0) + (e.sub_entries ? e.sub_entries.length : 0);
    const moreCount = extra > 1 ? ` <span style="color:var(--ink-soft)">(+${extra - 1} more)</span>` : "";
    return `<article class="entry-row" data-id="${esc(e.id)}" tabindex="0" role="button">
      <div class="entry-main">
        <div class="entry-head">
          <b class="geez">${esc(e.headword)}</b>
          ${e.translit ? `<span class="entry-translit">${esc(e.translit)}</span>` : ""}
          <span class="entry-pos">${esc(e.pos)}</span>
        </div>
        <div class="entry-gloss ${gloss ? "" : "muted"}">${gloss ? esc(gloss) + moreCount : "No English gloss recorded"}</div>
      </div>
    </article>`;
  }

  function pagerHtml(n) {
    if (n <= 1) return "";
    const page = state.page;
    let mid = [1];
    const lo = Math.max(2, page - 2), hi = Math.min(n - 1, page + 2);
    if (lo > 2) mid.push("…");
    for (let i = lo; i <= hi; i++) mid.push(i);
    if (hi < n - 1) mid.push("…");
    if (n > 1) mid.push(n);
    const btn = (p, label, disabled) => `<button class="page-btn" data-page="${p}" ${disabled ? "disabled" : ""}>${label}</button>`;
    return btn(page - 1, "‹", page === 1) +
      mid.map((x) => x === "…" ? `<span class="page-ellipsis">…</span>` : `<button class="page-btn ${x === page ? "active" : ""}" data-page="${x}">${x}</button>`).join("") +
      btn(page + 1, "›", page === n);
  }

  function senseBlock(num, text) {
    return `<div class="sense-block">
      ${num ? `<span class="sense-num">${esc(num)}.</span>` : ""}<span class="sense-text">${esc(text)}</span>
    </div>`;
  }

  function openEntry(e) {
    let html = `<div class="detail-word geez">${esc(e.headword)}</div>`;
    if (e.translit) html += `<div class="detail-translit">${esc(e.translit)}</div>`;
    html += `<div class="detail-tags">
      <span class="tag">${esc(e.pos)}</span>
      ${e.stem_class ? `<span class="tag">${esc(e.stem_class)}</span>` : ""}
    </div>`;

    if (e.senses && e.senses.length) {
      html += e.senses.map((s) => senseBlock(s.num, s.text)).join("");
    }
    if (e.sub_entries && e.sub_entries.length) {
      html += `<div class="sub-label">Related forms</div>`;
      html += e.sub_entries.map((s) => `<div class="sense-block">
        ${s.form ? `<div class="sub-form">${esc(s.form)}</div>` : ""}
        <span class="sense-text">${esc(s.text)}</span>
      </div>`).join("");
    }
    if (!(e.senses && e.senses.length) && !(e.sub_entries && e.sub_entries.length)) {
      html += `<div class="no-gloss-note">No English gloss was recorded for this headword — it may be a cross-reference to another entry${e.etymology ? ` (compare: ${esc(e.etymology)})` : ""}.</div>`;
    }
    if (e.etymology && (e.senses && e.senses.length)) {
      html += `<div class="sense-cite" style="margin-top:10px">Etymology: ${esc(e.etymology)}</div>`;
    }
    html += `<div class="detail-actions"><a class="permalink-btn" href="words/${esc(e.slug)}.html">View full entry →</a></div>`;

    $("entryBody").innerHTML = html;
    $("entryDialog").showModal();
  }

  init();
})();
