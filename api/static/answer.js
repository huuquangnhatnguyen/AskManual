// Answer page: POST /ask once, render an Answer, a Refusal or an error. window.ASK comes from the server.
(() => {
  const TIMEOUT_MS = 60000;
  const out = document.getElementById("out");
  const { question, product_family, query } = window.ASK;

  function el(tag, attrs = {}, ...kids) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) k === "class" ? (n.className = v) : n.setAttribute(k, v);
    for (const kid of kids) if (kid != null) n.append(kid);
    return n;
  }

  const DOC_TITLES = window.DOC_TITLES || {};
  const title = (doc) => DOC_TITLES[doc] || doc.replace(/_/g, " ");

  async function request() {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), TIMEOUT_MS);
    try {
      const r = await fetch(`/ask${query ? "?" + query : ""}`, {
        method: "POST", headers: { "Content-Type": "application/json" }, signal: ctl.signal,
        body: JSON.stringify({ question, product_family: product_family || null }) });
      if (!r.ok) {
        let detail = "";
        try { detail = (await r.json()).detail; } catch (_) {}
        if (r.status === 504) throw new Error("The answer took too long to generate. Try again, or shorten the question.");
        throw new Error(typeof detail === "string" && detail ? `The server couldn't answer (${detail}).` : `The server answered ${r.status}.`);
      }
      return r.json();
    } catch (e) {
      if (e.name === "AbortError") throw new Error("That took too long. Check your connection and try again.");
      if (e instanceof TypeError) throw new Error("Couldn't reach the server. Check your connection.");
      throw e;
    } finally {
      clearTimeout(t);
    }
  }

  function showLoading() {
    const started = Date.now();
    const secs = el("span", { class: "mono" }, "");
    out.replaceChildren(el("div", { class: "card" },
      el("div", { class: "loading" }, el("div", { class: "spinner" }),
         el("span", {}, "Searching the manuals and checking every citation… "), secs),
      el("div", { class: "skeleton", style: "width:92%" }),
      el("div", { class: "skeleton", style: "width:74%" }),
      el("div", { class: "skeleton", style: "width:83%" })));
    const tick = setInterval(() => {
      const s = Math.floor((Date.now() - started) / 1000);
      secs.textContent = s >= 2 ? `${s}s` : "";
    }, 500);
    return () => clearInterval(tick);
  }

  function showError(msg) {
    const retry = el("button", { type: "button", class: "btn" }, "Try again");
    retry.onclick = run;
    out.replaceChildren(el("div", { class: "card error", role: "alert" },
      el("h2", {}, "Something went wrong"), el("p", {}, msg), retry));
  }

  // A page link that expands, in place, into the cropped region of the manual page.
  function cite(id, sources) {
    const s = sources[id];
    const btn = el("button", { type: "button", class: "cite", "aria-expanded": "false",
                               title: s ? `${title(s.doc_id)}${s.parent_section_title ? " › " + s.parent_section_title : ""}` : id },
                   s ? `p. ${s.page}` : "source");
    let fig = null;
    btn.onclick = () => {
      if (fig) { fig.remove(); fig = null; btn.setAttribute("aria-expanded", "false"); return; }
      const img = el("img", { alt: `Region of manual page ${s ? s.page : ""}`, src: `/evidence/${encodeURIComponent(id)}` });
      fig = el("figure", { class: "evidence" }, img,
               el("figcaption", {}, s ? `${title(s.doc_id)}, page ${s.page}${s.parent_section_title ? " · " + s.parent_section_title : ""}` : id));
      img.onerror = () => { fig.replaceWith(el("p", { class: "empty" }, "Page image unavailable.")); fig = null; };
      (btn.closest("li, p, .safety") || btn.parentElement).append(fig);
      btn.setAttribute("aria-expanded", "true");
    };
    return btn;
  }

  const NONE = () => el("p", { class: "empty" }, "Not stated in the manual.");

  function items(tag, list, render, sources) {
    if (!list.length) return NONE();
    return el(tag, {}, ...list.map((it) => el("li", {}, ...render(it), " ", cite(it.cite, sources))));
  }

  function renderAnswer(a) {
    const s = a.sources;
    const nodes = [];
    if (a.safety_warning) {
      nodes.push(el("div", { class: "safety", role: "note" },
        el("strong", {}, "⚠ SAFETY WARNING"),
        el("p", { style: "margin:0" }, `“${a.safety_warning.verbatim}” `, cite(a.safety_warning.cite, s))));
    }
    const docs = [...new Set(Object.values(s).map((x) => x.doc_id))];
    nodes.push(el("article", { class: "card answer" },
      el("section", {}, el("h2", {}, "What it means"),
         a.fault_meaning ? el("p", { class: "lead" }, a.fault_meaning.text, " ", cite(a.fault_meaning.cite, s)) : NONE()),
      el("section", {}, el("h2", {}, "Probable causes"),
         items("ul", a.probable_causes, (c) => [el("span", { class: `badge badge-${c.likelihood}` }, c.likelihood), " ", c.text], s)),
      el("section", {}, el("h2", {}, "What to do"), items("ol", a.corrective_steps, (c) => [c.text], s)),
      el("section", {}, el("h2", {}, "Tools and parts"), items("ul", a.tools_and_parts, (c) => [c.text], s)),
      el("section", { class: "sources" }, el("h2", {}, "Sources"),
         el("ul", {}, ...docs.map((d) => {
           const pages = [...new Set(Object.values(s).filter((x) => x.doc_id === d).map((x) => x.page))].sort((x, y) => x - y);
           return el("li", {}, title(d), el("span", { class: "muted" }, ` · p. ${pages.join(", ")}`));
         })))));
    out.replaceChildren(...nodes);
  }

  function renderRefusal(r) {
    const card = el("div", { class: "card refusal" },
      el("h2", {}, "Not found in these manuals"),
      el("p", { class: "muted" }, r.message));
    if (r.nearest.length) card.append(el("div", { class: "field-label", style: "margin-top:14px" }, "Closest passages, to check yourself"));
    for (const n of r.nearest) {
      card.append(el("div", { class: "near" }, el("span", { class: "where" }, `${title(n.doc_id)}, p. ${n.page}`), n.text));
    }
    card.append(el("p", { class: "small muted", style: "margin:14px 0 0" },
      "See the Manuals page for what's covered."));
    out.replaceChildren(card);
  }

  async function run() {
    const stop = showLoading();
    try {
      const res = await request();
      res.kind === "refusal" ? renderRefusal(res) : renderAnswer(res);
    } catch (e) {
      showError(e.message);
    } finally {
      stop();
    }
  }

  run();
})();
