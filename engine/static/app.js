/* Bon toutou v0.3 — interface locale. Tout passe par le moteur sur ton ordinateur (127.0.0.1).
   app.js : socle (état, appels, barre du haut, rendu), Trier, Documents, Dossiers, Archives.
   vues.js : Aujourd'hui, Calendrier, Contacts. reglages.js : Réglages compartimentés. */
const S = { v: "home", sv: null, st: null, inbox: [], docs: [], dossiers: [], arch: null, doc: null, dos: null,
            cc: null, q: "", at: "sent", ax: "pays", busy: "", bview: false, confirm: null, pm: false, tm: false };
const $ = (s) => document.querySelector(s);
const esc = (x) => String(x == null ? "" : x).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const M = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
const frd = (d) => (d ? `${+d.slice(8, 10)} ${M[+d.slice(5, 7) - 1]} ${d.slice(0, 4)}` : "—");
const cc = (c) => `<span class="ccchip k-${esc(c)}">${esc(c)}</span>`;
const CONF = { haute: "Confiance élevée", moyenne: "Confiance moyenne", basse: "À vérifier" };
const CATIC = { "01": "id", "02": "house", "03": "work", "04": "tax", "05": "bank", "06": "shield", "07": "umbrella", "08": "car", "09": "kids", "10": "building", "11": "name", "12": "cap", "13": "scale", "14": "spark", "15": "star" };
const catIc = (c) => IC[CATIC[c] || "folder"];
const LVL = { local: ["red", "Local uniquement", "Ne quitte jamais ton ordinateur"], autorisation: ["orange", "Sur autorisation", "Analysé à l'extérieur seulement si tu l'autorises, document par document"], externe: ["green", "Externe autorisé", "Peu sensible : pourrait être analysé à l'extérieur"] };
const LVI = { red: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>', orange: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="8"/><path d="M12 4a8 8 0 0 1 0 16z" fill="currentColor"/></svg>', green: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M7 18h10a4 4 0 0 0 .5-8A6 6 0 0 0 6 9.5 4.3 4.3 0 0 0 7 18z"/></svg>' };
const lvOf = (c) => ((S.st && S.st.settings.privacy) || {})[c] || "local";
const lvBadge = (c) => { const L = LVL[lvOf(c)]; return `<span class="lv ${L[0]}" title="${esc(L[2])}">${LVI[L[0]]}${L[1]}</span>`; };
const daysTo = (d) => Math.round((Date.parse(d) - Date.parse(S.st.today)) / 864e5);
const plural = (n, a, b) => (n > 1 ? b || a + "s" : a);

async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return r.json();
}
let toastT;
function toast(msg, undoBatch) {
  const t = $("#toast");
  t.innerHTML = esc(msg) + (undoBatch ? ` <button data-act="undo" data-b="${undoBatch}">Annuler</button>` : "");
  t.hidden = false; clearTimeout(toastT);
  toastT = setTimeout(() => (t.hidden = true), undoBatch ? 7000 : 3000);
}
function applyTheme() {
  const th = (S.st && S.st.settings && S.st.settings.theme) || "champagne";
  document.documentElement.dataset.palette = ["champagne", "graphite", "sauge"].includes(th) ? th : "champagne";
}

async function load() {
  S.st = await api("/api/state");
  applyTheme();
  if (S.st.setup) { S.v = "setup"; return render(); }
  if (S.v === "setup") S.v = "home";
  if (S.v === "trier") S.inbox = await api("/api/inbox");
  if (S.v === "docs") S.docs = await api("/api/docs");
  if (S.v === "doc") S.doc = await api("/api/doc?id=" + S.docId);
  if (S.v === "dossiers") S.dossiers = await api("/api/dossiers");
  if (S.v === "dossier") S.dos = await api("/api/dossier?id=" + S.dosId);
  if (S.v === "archives") S.arch = await api("/api/archives");
  if (S.v === "contacts") S.contacts = await api("/api/contacts");
  if (S.v === "reglages") { S.hist = await api("/api/history"); S.rules = await api("/api/rules"); }
  if (S.v === "guide") S.inbox = await api("/api/inbox");
  if (S.v === "guide" || (S.v === "trier" && S.st && !S.st.settings.guide.fini && !S.st.settings.guide.masque)) S.guide = await api("/api/guide");
  render();
  clearTimeout(S.poll);
  if (S.v === "trier" && (S.inbox || []).some((p) => p.ai_pending)) S.poll = setTimeout(async () => { if (S.v === "trier" && !document.querySelector("input:focus,select:focus")) { S.inbox = await api("/api/inbox"); render(); } else load(); }, 4000);
}
function go(v, extra = {}) {
  S.fix = false; S.pm = false; S.tm = false;
  if (v !== S.v) S.q = "";
  Object.assign(S, { v, confirm: null, sv: null }, extra);
  window.scrollTo(0, 0); load();
}

/* ------------------------------------------------ BARRE DU HAUT */
const PLUS = [["cal", "Calendrier", "calendar"], ["archives", "Archives", "archive"], ["contacts", "Contacts", "name", "aperçu"], ["reglages", "Réglages", "gear"]];
function topbar() {
  const vv = $("#ver"); if (vv && S.st) vv.textContent = "Bon toutou " + (S.st.version ? "v" + S.st.version : "") + " · local · code public AGPL-3.0";
  const setup = S.v === "setup" || (S.st && S.st.setup);
  const c = (S.st && S.st.counts) || {};
  const on = { doc: "docs", dossier: "dossiers", guide: "trier" }[S.v] || S.v;
  const plusOn = PLUS.find((x) => x[0] === on);
  const th = (S.st && S.st.settings && S.st.settings.theme) || "champagne";
  $("#topbar").innerHTML = `<button class="brand" ${setup ? "" : 'data-go="home"'}><span class="mark">${IC.dog}</span><span><b>Bon toutou</b><small class="tagline"></small></span></button>
  ${setup ? "" : `<nav class="nav">${[["home", "Aujourd'hui"], ["trier", "Trier", c.inbox], ["docs", "Documents"], ["dossiers", "Dossiers"]].map((n) => `<button class="${on === n[0] ? "on" : ""}" data-go="${n[0]}">${n[1]}${n[2] ? ` <span class="badge">${n[2]}</span>` : ""}</button>`).join("")}
    <span class="plusw"><button class="${plusOn ? "on" : ""}" data-act="plusmenu" aria-expanded="${!!S.pm}">${plusOn ? plusOn[1] : "Plus"} <span class="caret">▾</span></button>
    ${S.pm ? `<div class="pmenu">${PLUS.map((x) => `<button data-go="${x[0]}"><span class="oi">${IC[x[2]]}</span>${x[1]}${x[3] ? ` <span class="soontag">${x[3]}</span>` : ""}</button>`).join("")}</div>` : ""}</span></nav>`}
  <div class="tright">${setup ? "" : `<button class="privpill" data-go="reglages" data-sv="priv" title="Journal des sorties">${IC.lock}<span>${c.egress ? c.egress + " " + plural(c.egress, "sortie") : "Tout reste ici"}</span></button>`}
    ${setup ? "" : `<button class="iconbtn" data-act="thememenu" aria-label="Thème"><span class="sw ${th[0]}" style="width:14px;height:14px"></span></button>`}</div>
  ${S.tm ? `<div class="theme-menu">${THEMES.map((t) => `<button class="theme-opt${th === t[0] ? " on" : ""}" data-theme="${t[0]}"><i class="sw ${t[2]}"></i>${t[1]}</button>`).join("")}</div>` : ""}`;
}
const THEMES = [["champagne", "Champagne", "c"], ["graphite", "Graphite", "g"], ["sauge", "Sauge", "s"]];

function render() {
  topbar();
  const V = { home: () => window.homeView ? homeView() : "", cal: () => window.calView ? calView() : "", contacts: () => window.contactsView ? contactsView() : "",
              trier, docs, doc: docView, dossiers, dossier: dossierView, archives, reglages: () => window.reglagesView ? reglagesView() : "",
              guide: () => window.guideView ? guideView() : "", setup: () => window.setupView ? setupView() : "" }[S.v];
  $("#app").innerHTML = V ? V() : "";
  $("#modal").innerHTML = S.modal && window.modalView ? modalView() : "";
  $("#holders").innerHTML = ((S.st && S.st.settings && S.st.settings.holders) || []).map((h) => `<option value="${esc(h.nom)}">`).join("");
  bind();
  if (window.bindExtra) bindExtra();
}

/* ------------------------------------------------ TRIER */
function typeOptions(sel) {
  const T = S.st.types, C = S.st.categories;
  return Object.entries(T).sort((a, b) => (a[1].cat + a[1].label).localeCompare(b[1].cat + b[1].label))
    .map(([k, v]) => `<option value="${k}" ${k === sel ? "selected" : ""}>${v.cat} ${esc(C[v.cat] || "")} · ${esc(v.label)}</option>`).join("");
}
function reasons(p) {
  const how = { pypdf: "texte du PDF", pdftotext: "texte du PDF", ocr: "lecture de l'image (OCR)", texte: "fichier texte" }[p.method] || "nom du fichier seulement";
  return `<details class="why"><summary>Pourquoi ?</summary><ul>${p.reasons.map((r) => `<li>${esc(r)}</li>`).join("")}<li>Lu par : ${how}</li></ul></details>`;
}
const isHi = (p) => p.confidence === "haute" && !p.duplicate && !p.overridden && !(S.solo && S.solo.has(p.id));
function trier() {
  S.solo = S.solo || new Set();
  const P = S.inbox, hi = P.filter(isHi), rest = P.filter((p) => !hi.includes(p));
  const sel = hi.filter((p) => !S.unchecked || !S.unchecked.has(p.id));
  return `<h1>Trier</h1><p class="lead">${P.length ? `${P.length} ${plural(P.length, "document")} en attente. ` : ""}Bon toutou lit tes papiers sur ton ordinateur, propose un nom et une place, et tu valides. <b>Tu peux te tromper : Bon toutou ne détruit rien.</b></p>
  <div class="addrow">
    <span class="ghost">${IC.up} Déposer des fichiers<input type="file" id="files" multiple aria-label="Déposer des fichiers"></span>
    <span class="ghost">${IC.folder} Importer un dossier<input type="file" id="dirIn" webkitdirectory multiple aria-label="Importer un dossier"></span>
    <button class="ghost" data-act="scan">${IC.sync} Relire 00_A-TRIER</button>
    ${P.length ? `<button class="ghost" data-act="reanalyze">${IC.sparkles} Relancer l'analyse</button>` : ""}
    <button class="ghost" data-go="reglages" data-sv="mail">${IC.mail} Adresse admin <span class="soontag">bientôt</span></button></div>
  <div class="dropzone" id="drop"><b>Glisse tes fichiers ou un dossier ici</b><span class="sub">PDF, photos, scans : ils sont copiés dans 00_A-TRIER, l'original reste où il est. Lu sur ton ordinateur, rien ne sort.</span></div>
  ${window.guideCard ? guideCard() : ""}
  ${S.busy ? `<div class="card busy"><span class="spin"></span>${esc(S.busy)}</div>` : ""}
  ${hi.length ? `<div class="label" style="margin-bottom:8px">En lot — confiance élevée</div><div class="card batch" style="margin-bottom:26px">${hi.map((p) => `<div class="row drow k-${esc(p.country)}">
      <input type="checkbox" data-chk="${p.id}" ${sel.includes(p) ? "checked" : ""} aria-label="Inclure">
      <div class="grow"><b>${esc(p.label)}</b> ${cc(p.country)} <span class="sub">· ${frd(p.date)}</span>
        <div class="sub">${esc(p.relation)} · → ${esc(p.dest)}</div>
        ${S.bview ? `<div class="fname sub">${esc(p.orig)} → <b>${esc(p.name)}</b></div>` : ""}</div>
      ${p.cat ? lvBadge(p.cat) : ""}<span class="conf haute">${CONF[p.confidence]}</span>${reasons(p)}<button class="linkbtn" data-act="solo" data-id="${p.id}">Modifier</button></div>`).join("")}
    <div class="bfoot"><span class="sub"><b style="color:var(--text)">${sel.length} ${plural(sel.length, "document")}</b> · confiance élevée · 0 conflit détecté</span>
      <span class="acts"><button class="ghost small" data-act="bview">${S.bview ? "Masquer le détail" : "Voir les " + sel.length}</button><button class="cta" data-act="batch" ${sel.length ? "" : "disabled"}>Valider ${sel.length} ${plural(sel.length, "document")}</button></span></div></div>` : ""}
  ${rest.length ? `<div class="label" style="margin-bottom:8px">Un par un</div>${rest.map(tcard).join("")}` : ""}
  ${!P.length && !S.busy ? `<div class="card" style="padding:28px;text-align:center"><span class="oi" style="margin:0 auto 10px;background:var(--success-light);color:var(--success)">${IC.check}</span><b>Tout est trié.</b><div class="sub">Dépose un fichier ou un dossier ci-dessus.</div></div>` : ""}`;
}
function tcard(p) {
  const exp = ["carte_identite", "passeport", "permis_conduire", "visa", "assurance_habitation", "assurance_vehicule", "assurance_voyage", "carte_grise", "controle_vehicule"].includes(p.type);
  return `<div class="card tcard ${p.confidence}">
    <div class="tt"><span class="oi">${catIc(p.cat)}</span><b>${esc(p.label)}</b>${cc(p.country)}${p.cat ? lvBadge(p.cat) : ""}<span class="conf ${p.confidence}">${CONF[p.confidence]}</span>${p.ai_pending ? `<span class="pill acc"><span class="spin" style="width:11px;height:11px"></span> IA locale en train de lire…</span>` : ""}${reasons(p)}<span class="pill n">${esc(p.source)}</span>
      ${p.duplicate ? `<span class="pill bad">Doublon exact de « ${esc(p.duplicate.label)} »</span>` : ""}
      <button class="linkbtn" data-open-inbox="${p.id}" style="margin-left:auto">Aperçu</button></div>
    <div class="edit">
      <label>Type<select class="field" data-ov="${p.id}" data-f="type">${typeOptions(p.type)}</select></label>
      <label>Pays<select class="field" data-ov="${p.id}" data-f="country">${Object.entries(S.st.countries).map(([k, v]) => `<option value="${k}" ${k === p.country ? "selected" : ""}>${k} · ${v}</option>`).join("")}</select></label>
      <label>Émetteur<input class="field" data-ov="${p.id}" data-f="emitter" value="${esc(p.emitter)}"></label>
      <label>Intitulé exact<input class="field" data-ov="${p.id}" data-f="detail" value="${esc(p.detail)}" placeholder="ex. ASSR2, Attestation de présence"></label>
      <label>Titulaire<input class="field" list="holders" data-ov="${p.id}" data-f="person" value="${esc(p.person === "moi" ? "" : p.person)}" placeholder="${esc(S.st.settings.owner || "toi")}"></label>
      <label>Date du document<input class="field" type="date" data-ov="${p.id}" data-f="date" value="${esc(p.date)}">${p.date_note ? `<small style="display:block;color:var(--warning);font-weight:500;text-transform:none;letter-spacing:0;margin-top:4px">≈ Date approximative : ${esc(p.date_note)}</small>` : ""}</label>
      ${exp ? `<label>Expire le<input class="field" type="date" data-ov="${p.id}" data-f="expiry" value="${esc(p.expiry || "")}"></label>` : ""}
    </div>
    <dl class="grid"><dt>Reçu</dt><dd class="fname" style="text-decoration:line-through;color:var(--text-tertiary)">${esc(p.orig)}</dd><dt>Nom proposé</dt><dd class="fname"><b>${esc(p.name)}</b></dd>
      <dt>Destination</dt><dd class="fname">${esc(p.dest)}</dd><dt>Document suivi</dt><dd>${esc(p.relation)}</dd></dl>
    ${window.ruleOffer ? ruleOffer({ inbox: p.id, overrides: p.overrides, type: p.type }) : ""}
    <div class="tacts"><button class="cta small" data-act="ok" data-id="${p.id}">✓ Valider</button><button class="ghost small" data-act="ignore" data-id="${p.id}">Ignorer</button>
      <span class="sub">Ignorer garde le fichier dans 00_A-TRIER/_IGNORES.</span></div></div>`;
}

/* ------------------------------------------------ DOCUMENTS */
function docRow(d) {
  const e = d.expiry ? daysTo(d.expiry) : null;
  return `<div class="row drow k-${esc(d.country)}" data-doc="${d.id}" role="button" tabindex="0" style="cursor:pointer"><span class="oi">${catIc(d.cat)}</span><div class="grow"><b>${esc(d.label)}</b> ${cc(d.country)}
    <div class="sub">${d.person && d.person !== "moi" && d.person !== S.st.settings.owner ? esc(d.person) + " · " : ""}${frd(d.doc_date)}${d.versions > 1 ? ` · ${d.versions} versions` : ""}</div></div>
    ${e !== null && e <= 365 ? `<span class="pill ${e < 0 ? "bad" : e <= 30 ? "warn" : "neutral"}">${e < 0 ? "expiré" : "expire dans " + e + " j"}</span>` : ""}${lvBadge(d.cat)}</div>`;
}
function subBlock(D, c) {
  const subs = [...new Set(D.map((d) => d.sub_folder))].sort();
  const all = S.showEmpty ? Object.keys(S.st.subs).filter((k) => k.startsWith(c + "-")).map((k) => k + "_" + S.st.subs[k]) : [];
  return [...new Set([...subs, ...all])].sort().map((s) => { const X = D.filter((d) => d.sub_folder === s);
    const E = [...new Set(X.map((d) => d.emitter_folder || ""))].sort();
    const rows = E.length > 1 || E[0] ? E.map((e) => { const Y = X.filter((d) => (d.emitter_folder || "") === e);
      return (e ? `<div class="subhead" style="padding-left:34px;text-transform:none;letter-spacing:0">${IC.folder.replace("<svg", '<svg style="width:13px;height:13px;vertical-align:-2px"')} ${esc(e.replace(/-/g, " "))} · ${Y.length}</div>` : "") + Y.map(docRow).join(""); }).join("") : X.map(docRow).join("");
    return `<div class="subhead${X.length ? "" : " empty"}">${esc(s.replace(/_/g, " ").replace(/-/g, " "))} · ${X.length || "vide"}</div>${rows}`; }).join("");
}
function catSec(c, D) {
  return `<div class="catsec${D.length ? "" : " empty"}"><div class="cathead"><span class="oi">${catIc(c)}</span><b>${c} ${esc(S.st.categories[c] || "")}</b>${D.length ? `<span class="n">${D.length}</span>` : `<span class="pill neutral">vide</span>`}</div><div class="doclist">${subBlock(D, c)}</div></div>`;
}
function docs() {
  const C = S.st.categories, q = S.q.toLowerCase(), ax = S.ax || "pays";
  const head0 = `<h1>Documents</h1><p class="lead">${S.docs.length} ${plural(S.docs.length, "document suivi", "documents suivis")}. Bon toutou garde la version actuelle et l'historique de chacun, et les réutilise dans tes dossiers sans copie.</p>
  <div class="search">${IC.search}<input id="q" value="${esc(S.q)}" placeholder="Chercher : passeport, EDF, fiche de paie…" aria-label="Chercher"></div>
  <div class="axes">${[["pays", "Par pays"], ["cat", "Par catégorie"], ["exp", "Expirent bientôt"]].map((a) => `<button class="${ax === a[0] ? "on" : ""}" data-ax="${a[0]}">${a[1]}</button>`).join("")}
    ${ax !== "exp" && !q ? `<button class="linkbtn emptytog" data-act="showempty">${S.showEmpty ? "Masquer" : "Afficher"} les catégories vides</button>` : ""}</div>`;
  const unk = S.docs.filter((d) => !d.emitter || d.emitter === "Inconnu").length;
  const banner = unk ? `<div class="card box" style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:14px;border-color:var(--warning)"><span class="oi" style="background:var(--warning-light);color:var(--warning)">${IC.search}</span><div class="grow"><b>${unk} ${plural(unk, "document")} sans émetteur</b><div class="sub">Bon toutou peut relire leur texte pour retrouver l'émetteur (l'employeur des fiches de paie) et les ranger dans son dossier. Annulable.</div></div><button class="cta small" data-act="redetect">Retrouver les émetteurs</button></div>` : "";
  const head = head0 + banner;
  if (S.busy) return head + `<div class="card busy"><span class="spin"></span>${esc(S.busy)}</div>`;
  if (!S.docs.length) return head + `<div class="card empty">Aucun document pour l'instant. Commence par <button class="linkbtn" data-go="trier">Trier</button>.</div>`;
  if (q) { const L = S.docs.filter((d) => (d.label + d.path + d.emitter).toLowerCase().includes(q)); return head + `<div class="card doclist">${L.map(docRow).join("") || `<div class="row sub">Aucun document.</div>`}</div>`; }
  if (ax === "exp") { const L = S.docs.filter((d) => d.expiry && daysTo(d.expiry) <= 365).sort((a, b) => a.expiry.localeCompare(b.expiry));
    return head + `<div class="label" style="margin-bottom:8px">Dans les 12 prochains mois · <button class="linkbtn" style="padding:0" data-go="cal">voir le calendrier</button></div><div class="card doclist">${L.map(docRow).join("") || `<div class="row sub">Rien n'expire dans l'année.</div>`}</div>`; }
  const cats = Object.keys(C).sort();
  if (ax === "cat") {
    const tiles = `<div class="groups">${cats.filter((c) => S.showEmpty || S.docs.some((d) => d.cat === c)).map((c) => { const n = S.docs.filter((d) => d.cat === c).length;
      return `<button class="group${S.gf === c ? " on" : ""}${n ? "" : " empty"}" data-gf="${c}"><span class="oi" style="width:30px;height:30px">${catIc(c)}</span><b>${c} ${esc(C[c])}</b><span class="n">${n || "vide"}</span></button>`; }).join("")}</div>`;
    const list = (S.gf && C[S.gf] ? [S.gf] : cats.filter((c) => S.showEmpty || S.docs.some((d) => d.cat === c))).map((c) => catSec(c, S.docs.filter((d) => d.cat === c))).join("");
    return head + tiles + list;
  }
  const ccs = [...new Set([...S.st.settings.countries, ...S.docs.map((d) => d.country)])];
  const cur = S.cc && ccs.includes(S.cc) ? S.cc : ccs[0];
  const tabs = `<div class="groups">${ccs.map((c) => `<button class="group cgroup k-${c}${c === cur ? " on" : ""}" data-cc="${c}">${cc(c)}<b>${esc(S.st.countries[c] || c)}</b><span class="n">${S.docs.filter((d) => d.country === c).length}</span></button>`).join("")}</div>`;
  const D = S.docs.filter((d) => d.country === cur);
  const secs = cats.filter((c) => S.showEmpty || D.some((d) => d.cat === c)).map((c) => catSec(c, D.filter((d) => d.cat === c))).join("");
  return head + tabs + `<div class="cframe k-${esc(cur)}"><div class="cframe-h">${cc(cur)}<b>${esc(cur)}_${esc((S.st.countries[cur] || "").toUpperCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/ /g, "-"))}</b><span class="sub">${S.showEmpty ? "15 catégories" : D.length + " " + plural(D.length, "document")}</span></div>${secs || `<div class="catsec"><div class="emptysubs"><span class="sub">Aucun document pour ce pays pour l'instant.</span></div></div>`}</div>`;
}
function docView() {
  const d = S.doc; if (!d) return "";
  const e = d.expiry ? daysTo(d.expiry) : null;
  return `<div class="navline"><button class="back" data-go="docs">← Documents</button></div>
  <div class="ttl" style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:6px"><span class="oi">${catIc(d.cat)}</span><h1 style="margin:0">${esc(d.label)}</h1>${cc(d.country)}${lvBadge(d.cat)}</div>
  <p class="sub" style="margin:0 0 14px"><span class="pill acc">Document suivi</span> ${d.detail ? esc(S.st.types[d.type].label) + " · " : ""}${esc(d.cat_label)} · utilisé dans ${d.used_in.length} ${plural(d.used_in.length, "dossier")}, jamais copié</p>
  <div class="card box"><dl class="kv"><dt>Fichier</dt><dd class="fname">${esc(d.path)}</dd><dt>Date</dt><dd>${frd(d.doc_date)}</dd>
    ${d.expiry ? `<dt>Expire</dt><dd>${frd(d.expiry)} ${d.expired ? '<span class="pill bad">expiré</span>' : e <= 120 ? `<span class="pill ${e <= 30 ? "warn" : "neutral"}">dans ${e} jours</span>` : ""}</dd>` : ""}<dt>Titulaire</dt><dd>${esc(d.person === "moi" ? (S.st.settings.owner || "toi") : d.person)}</dd><dt>Émetteur</dt><dd>${esc(d.emitter)}</dd>
    <dt>Sorties</dt><dd>Jamais sorti de ton ordinateur</dd><dt>Confidentialité</dt><dd>${esc(LVL[lvOf(d.cat)][2])} · <button class="linkbtn" style="padding:0" data-go="reglages" data-sv="priv">changer</button></dd><dt>Reçu sous le nom</dt><dd class="fname">${esc(d.orig_name)}</dd></dl>
    <div class="acts" style="margin-top:12px"><button class="ghost small" data-open="${esc(d.path)}">Ouvrir</button><button class="ghost small" data-act="reveal" data-p="${esc(d.path)}">Montrer dans le Finder</button><button class="ghost small" data-act="fixopen">Corriger le classement</button></div>
    ${S.fix ? `<div class="edit" style="margin-top:14px">
      <label>Type<select class="field" id="fx_type">${typeOptions(d.type)}</select></label>
      <label>Pays<select class="field" id="fx_country">${Object.entries(S.st.countries).map(([k, v]) => `<option value="${k}" ${k === d.country ? "selected" : ""}>${k} · ${v}</option>`).join("")}</select></label>
      <label>Intitulé exact<input class="field" id="fx_detail" value="${esc(d.detail || "")}" placeholder="ex. ASSR2, Attestation de présence"></label>
      <label>Titulaire<input class="field" list="holders" id="fx_person" value="${esc(d.person === "moi" ? "" : d.person)}" placeholder="${esc(S.st.settings.owner || "toi")}"></label>
      <label>Émetteur<input class="field" id="fx_emitter" value="${esc(d.emitter)}"></label>
      <label>Date du document<input class="field" type="date" id="fx_date" value="${esc(d.doc_date)}"></label>
      <label>Expire le<input class="field" type="date" id="fx_expiry" value="${esc(d.expiry || "")}"></label></div>
      <div class="acts" style="margin-top:10px"><button class="cta small" data-act="fixsave">Enregistrer</button><button class="linkbtn" data-act="fixcancel">annuler</button><span class="sub">Le fichier est renommé et déplacé au bon endroit. Annulable.</span></div>` : ""}</div>
  ${S.docOffer && S.docOffer.doc === d.id && window.ruleOffer ? `<div style="margin-top:12px">${ruleOffer(S.docOffer)}</div>` : ""}
  <div class="label" style="margin:22px 0 8px">Version actuelle et historique</div>
  <div class="card">${d.history.map((h) => `<div class="row"><span class="pill ${h.status === "actuel" ? "ok" : "neutral"}">${esc(h.status_label)}</span><div class="grow"><b>${frd(h.doc_date)}</b><div class="fname sub">${esc(h.path)}</div></div><button class="linkbtn" data-open="${esc(h.path)}">ouvrir</button></div>`).join("")}</div>
  <div class="label" style="margin:22px 0 8px">Utilisé dans</div>
  <div class="card">${d.used_in.map((u) => `<div class="row"><span class="oi">${IC.send}</span><div class="grow"><b>${esc(u.label)}</b><div class="sub">${esc(u.recipient)} · ${u.state === "envoye" ? "envoyé" : u.state === "finalise" ? "finalisé" : "en cours"}</div></div></div>`).join("") || `<div class="row sub">Pas encore utilisé.</div>`}</div>
  ${d.status === "actuel" ? `<div class="hint" style="margin-top:16px">Situation terminée (contrat fini, bail rendu, véhicule vendu) ? Toutes les versions partent dans Archives › Terminés. Rien n'est supprimé.
    ${S.confirm === "term" ? `<button class="cta small" data-act="terminate">Confirmer : terminer ce suivi</button> <button class="linkbtn" data-act="noconfirm">annuler</button>` : `<button class="ghost small" data-act="askterm">Terminer ce suivi…</button>`}</div>` : ""}`;
}

/* ------------------------------------------------ DOSSIERS */
function dossiers() {
  const T = S.st.tpl || {}, n = S.newTpl;
  return `<h1>Dossiers</h1><p class="lead">Préparer → finaliser → envoyer toi-même → garder la preuve. Tes documents suivis servent dans chaque dossier, sans copie.</p>
  <div class="label" style="margin-bottom:8px">Préparer un dossier</div>
  <div class="sits">${Object.entries(T).map(([k, t]) => `<button class="sit${n === k ? " on" : ""}" data-newtpl="${k}" ${n === k ? 'style="border-color:var(--accent);background:var(--accent-light)"' : ""}><span class="oi">${IC[t.ic] || IC.folder}</span><b>${esc(t.label)}</b><small>${t.n} ${plural(t.n, "pièce")}</small></button>`).join("")}
    <button class="sit new" data-act="sitsoon"><span class="oi">${IC.plus}</span><b>Autre situation</b><small>crée ta liste · bientôt</small></button></div>
  ${n && T[n] ? `<div class="card box finalbox" style="margin:-10px 0 26px"><b>${esc(T[n].label)}</b><div class="edit" style="margin-top:10px">
    <label>Destinataire<input class="field" id="rcp" placeholder="ex. Agence Horizon"></label>
    <label>Pays<select class="field" id="dcc">${S.st.settings.countries.map((c) => `<option value="${c}">${c} · ${esc(S.st.countries[c])}</option>`).join("")}</select></label>
    <label>&nbsp;<span class="acts"><button class="cta" data-act="newdos">Préparer</button><button class="linkbtn" data-act="notpl">annuler</button></span></label></div></div>` : ""}
  <div class="label" style="margin-bottom:8px">En cours</div>
  <div class="card">${S.dossiers.map((k) => `<button class="row rowbtn" data-dos="${k.id}"><span class="oi">${IC[(T[k.template] || {}).ic] || IC.folder}</span><div class="grow"><b>${esc(k.label)}</b> ${cc(k.country)}<div class="sub">pour ${esc(k.recipient)} · ${k.state === "finalise" ? "finalisé, à envoyer" : "en préparation"}</div>
      <div class="bar ${k.ok === k.total ? "ok" : ""}" style="max-width:260px"><i style="width:${k.total ? Math.round((100 * k.ok) / k.total) : 0}%"></i></div></div><span class="pill ${k.ok === k.total ? "ok" : "warn"}">${k.ok}/${k.total}</span><span>›</span></button>`).join("") || `<div class="row sub">Aucun dossier en cours. Choisis une situation ci-dessus.</div>`}</div>`;
}
function pieceChoice(k, pc) {
  const pool = S.allDocs || [];
  const pref = pool.filter((d) => pc.types.includes(d.type)), others = pool.filter((d) => !pc.types.includes(d.type));
  const opt = (d) => `<option value="${d.id}">${esc(d.label)} · ${frd(d.doc_date)}${d.status !== "actuel" ? " (" + d.status_label.toLowerCase() + ")" : ""}</option>`;
  return `<select class="field small" data-assign="${pc.i}"><option value="">${pc.source === "choisi" ? "Revenir au choix automatique" : "Choisir un autre document…"}</option>${pref.map(opt).join("")}${others.length ? `<optgroup label="Autres documents">${others.map(opt).join("")}</optgroup>` : ""}</select>`;
}
function dossierView() {
  const k = S.dos; if (!k) return "";
  const fin = k.state === "finalise" || k.state === "envoye";
  return `<div class="navline"><button class="back" data-go="dossiers">← Dossiers</button></div>
  <h1>${esc(k.label)}</h1><p class="lead">Pour <b>${esc(k.recipient)}</b> ${cc(k.country)} · ${k.ok} ${plural(k.ok, "pièce")} sur ${k.total} ${plural(k.ok, "prête")}. Chaque pièce est prise dans sa version valable, jamais une copie.</p>
  <div class="card" style="margin-bottom:18px">${k.pieces.map((pc) => `<div class="piece ${pc.status === "ok" ? "ok" : pc.status === "part" ? "part" : "miss"}"><span class="st ${pc.status}">${pc.status === "ok" ? "✓" : pc.status === "part" ? "!" : "–"}</span>
    <div class="grow"><b>${esc(pc.label)}</b>${pc.count > 1 ? ` <span class="sub">(${pc.have}/${pc.count})</span>` : ""}
      <small class="sub">${pc.docs.length ? pc.docs.map((d) => `${esc(d.label)} · version du ${frd(d.date)}`).join("<br>") : "introuvable dans tes documents — dépose-le dans Trier"}</small>
      ${pc.problems.length ? `<small class="sub" style="color:var(--warning)">${esc(pc.problems.join(" · "))}</small>` : ""}</div>
    ${fin ? (pc.status === "ok" ? `<span class="pill ok">Prête</span>` : "") : pieceChoice(k, pc)}</div>`).join("")}</div>
  ${fin ? `<div class="card finalbox"><span class="label">Paquet finalisé</span><b style="display:block;font-size:16px;margin:4px 0">${k.manifest.pieces.reduce((a, p) => a + p.files.length, 0)} fichiers figés pour ${esc(k.recipient)}</b>
      <small class="sub">Bon toutou n'envoie pas le mail lui-même : envoie le paquet (dossier ou ZIP), puis marque-le comme envoyé pour garder la preuve.</small>
      <div class="fname sub" style="margin:6px 0">${esc(k.folder)}</div>
      <div class="acts" style="margin-top:10px"><button class="ghost small" data-act="reveal" data-p="${esc(k.folder)}">${IC.folder} Ouvrir le paquet</button><button class="ghost small" data-act="reveal" data-p="${esc(k.zip)}">${IC.up} Montrer le ZIP</button>
      <button class="cta small" data-act="sent">✓ Marquer comme envoyé</button><button class="linkbtn" data-act="reopen">Rouvrir</button></div></div>`
    : `<div class="acts"><button class="cta" data-act="finalize" ${k.ok < k.total ? "disabled" : ""}>Finaliser le dossier</button>${k.ok < k.total ? `<span class="sub">Il manque ${k.total - k.ok} ${plural(k.total - k.ok, "pièce")}.</span>` : ""}<button class="linkbtn" data-act="abandon">Abandonner ce dossier</button></div>`}`;
}

/* ------------------------------------------------ ARCHIVES */
function archives() {
  const A = S.arch; if (!A) return "";
  const q = S.q.toLowerCase(), m = (s) => !q || s.toLowerCase().includes(q);
  const sent = A.sent.filter((e) => m(e.label + e.recipient)), old = A.old.filter((d) => m(d.label + d.path)), done = A.done.filter((d) => m(d.label + d.path));
  let body = "";
  if (S.at === "sent") body = `<p class="sub" style="margin:0 0 10px">Le paquet exact que tu as donné, à qui et quand. Figé, même si un document a été remplacé depuis.</p><div class="proofs">${sent.map((e) => `<div class="proof"><span class="label">Dossier envoyé</span><div class="pnum">${e.count} fichiers</div>
      <div>${esc(e.label)} · à <b>${esc(e.recipient)}</b> ${cc(e.country)}</div><div>le ${frd(e.sent_at.slice(0, 10))}</div>
      <p><b>Voici exactement ce qui a été transmis.</b> Ce paquet est figé : c'est ta preuve.</p>
      ${e.manifest.pieces.map((p) => `<div class="sub" style="margin-top:6px"><b style="color:var(--text)">${esc(p.label)}</b>${p.files.map((f) => `<div class="fname">version du ${frd(f.version_du)} · ${esc(f.fichier)} · SHA ${f.sha256.slice(0, 12)}…${f.remplacee_depuis ? ` <span class="pill acc">remplacée depuis par celle du ${frd(f.remplacee_depuis)}</span>` : ""}</div>`).join("")}</div>`).join("")}
      <div class="acts" style="margin-top:10px"><button class="ghost small" data-act="reveal" data-p="${esc(e.folder)}">Ouvrir dans le Finder</button><button class="linkbtn" data-open="${esc(e.folder + "/PREUVE.txt")}">PREUVE.txt</button></div></div>`).join("") || `<div class="card empty">${q ? "Aucun résultat." : "Aucun dossier envoyé pour l'instant."}</div>`}</div>`;
  if (S.at === "old") body = `<p class="sub" style="margin:0 0 10px">Quand un document est remplacé, l'ancien vient ici. Tu n'as qu'une version valable dans Documents, mais tu ne perds rien.</p><div class="card">${old.map((d) => `<div class="row drow k-${esc(d.country)}" data-doc="${d.id}" style="cursor:pointer"><span class="oi">${IC.archive}</span><div class="grow"><b>${esc(d.label)}</b> ${cc(d.country)}<div class="sub">version du ${frd(d.doc_date)}</div><div class="fname sub">${esc(d.path)}</div></div><span>›</span></div>`).join("") || `<div class="row sub">${q ? "Aucun résultat." : "Aucune ancienne version."}</div>`}</div>`;
  if (S.at === "done") { const g = [...new Set(done.map((d) => d.country + "|" + d.sub_folder))];
    body = `<p class="sub" style="margin:0 0 10px">Les documents d'une situation finie : bail terminé, contrat fini, véhicule vendu, visa expiré.</p>` + (g.map((k) => { const [c, f] = k.split("|"), L = done.filter((d) => d.country === c && d.sub_folder === f);
      return `<div class="card" style="margin-bottom:10px;overflow:hidden"><div class="ccband k-${esc(c)}">${cc(c)}<b>${esc(f.replace(/_/g, " "))}</b><span class="sub">${L.length}</span></div>${L.map((d) => `<div class="row drow k-${esc(d.country)}" data-doc="${d.id}" style="cursor:pointer"><span class="oi">${catIc(d.cat)}</span><div class="grow"><b>${esc(d.label)}</b><div class="sub">${frd(d.doc_date)}</div></div><span>›</span></div>`).join("")}</div>`; }).join("") || `<div class="card empty">Rien pour l'instant. Une situation finie (contrat, bail…) arrive ici.</div>`); }
  return `<h1>Archives</h1><p class="lead">Bon toutou ne détruit rien. Ce qui n'est plus valable ou déjà envoyé vit ici, dans le dossier <span class="fname">99_ARCHIVES</span> de chaque pays.</p>
  <div class="search">${IC.search}<input id="q" value="${esc(S.q)}" placeholder="Chercher dans les archives : ancien RIB, bail, avis d'impôt 2024…" aria-label="Chercher dans les archives"></div>
  <div class="axes">${[["sent", "Dossiers envoyés", sent.length], ["old", "Anciennes versions", old.length], ["done", "Terminés", done.length]].map((t) => `<button class="${S.at === t[0] ? "on" : ""}" data-at="${t[0]}">${t[1]} <span class="sub" style="color:inherit;opacity:.75">${t[2]}</span></button>`).join("")}</div>${body}`;
}

/* ------------------------------------------------ ÉVÉNEMENTS */
async function upload(files) {
  const F = [...files].filter((f) => f && !f.name.startsWith("."));
  let ok = 0;
  for (let i = 0; i < F.length; i++) {
    S.busy = `Lecture ${i + 1}/${F.length} : ${F[i].name}`; render();
    try { await fetch("/api/upload?name=" + encodeURIComponent(F[i].name), { method: "POST", body: F[i] }); ok++; }
    catch (e) { console.warn("illisible", F[i].name, e); }
  }
  S.busy = ""; await load();
  toast(ok ? `${ok} ${plural(ok, "fichier")} ${plural(ok, "lu")} · à toi de valider` : "Aucun fichier lu");
}
/* Dossiers glissés : on parcourt leur contenu (sous-dossiers compris). */
function readEntry(entry) {
  return new Promise((res) => {
    if (entry.isFile) return entry.file((f) => res([f]), () => res([]));
    if (!entry.isDirectory) return res([]);
    const rd = entry.createReader(), all = [];
    const next = () => rd.readEntries(async (batch) => {
      if (!batch.length) { const nested = await Promise.all(all.map(readEntry)); return res(nested.flat()); }
      all.push(...batch); next();
    }, () => res([]));
    next();
  });
}
async function dropped(dt) {
  const entries = [...(dt.items || [])].map((it) => it.webkitGetAsEntry && it.webkitGetAsEntry()).filter(Boolean);
  if (!entries.length) return upload(dt.files);
  S.busy = "Lecture du contenu glissé…"; render();
  const files = (await Promise.all(entries.map(readEntry))).flat();
  upload(files);
}
function bind() {
  const d = $("#drop");
  if (d) {
    d.ondragover = (e) => { e.preventDefault(); d.classList.add("over"); };
    d.ondragleave = () => d.classList.remove("over");
    d.ondrop = (e) => { e.preventDefault(); d.classList.remove("over"); dropped(e.dataTransfer); };
  }
  const f = $("#files"); if (f) f.onchange = () => upload(f.files);
  const di = $("#dirIn"); if (di) di.onchange = () => upload(di.files);
  const q = $("#q"); if (q) q.oninput = () => { S.q = q.value; const pos = q.selectionStart; render(); const n = $("#q"); n.focus(); n.setSelectionRange(pos, pos); };
  document.querySelectorAll("[data-ov]").forEach((el) => (el.onchange = async () => {
    await api("/api/propose", { id: el.dataset.ov, overrides: { [el.dataset.f]: el.value } }); load();
  }));
  document.querySelectorAll("[data-chk]").forEach((el) => (el.onchange = () => {
    S.unchecked = S.unchecked || new Set(); el.checked ? S.unchecked.delete(el.dataset.chk) : S.unchecked.add(el.dataset.chk); render();
  }));
  document.querySelectorAll("[data-assign]").forEach((el) => (el.onchange = async () => {
    S.dos = await api("/api/dossier/assign", { id: S.dos.id, piece: +el.dataset.assign, docs: el.value ? [el.value] : [] }); render();
  }));
  document.querySelectorAll("[data-doc][tabindex]").forEach((el) => (el.onkeydown = (e) => { if (e.key === "Enter") go("doc", { docId: el.dataset.doc }); }));
}
document.addEventListener("click", async (e) => {
  const t = e.target;
  if (S.pm && !t.closest(".plusw")) { S.pm = false; topbar(); }
  if (S.tm && !t.closest(".theme-menu,[data-act=thememenu]")) { S.tm = false; topbar(); }
  const op = t.closest("[data-open],[data-open-inbox]");
  if (op) { const r = await api("/api/open", op.dataset.openInbox ? { inbox: op.dataset.openInbox } : { p: op.dataset.open }); if (!r.ok) toast(r.msg || "Impossible d'ouvrir ce fichier"); return; }
  const g = t.closest("[data-go]"); if (g) return go(g.dataset.go, g.dataset.sv ? { sv: g.dataset.sv } : {});
  const dc = t.closest("[data-doc]"); if (dc) return go("doc", { docId: dc.dataset.doc });
  const ds = t.closest("[data-dos]"); if (ds) { S.allDocs = null; return openDos(ds.dataset.dos); }
  const c = t.closest("[data-cc]"); if (c) { S.cc = c.dataset.cc; return render(); }
  const at = t.closest("[data-at]"); if (at) { S.at = at.dataset.at; return render(); }
  const ax = t.closest("[data-ax]"); if (ax) { S.ax = ax.dataset.ax; S.gf = null; return render(); }
  const gf = t.closest("[data-gf]"); if (gf) { S.gf = S.gf === gf.dataset.gf ? null : gf.dataset.gf; return render(); }
  const nt = t.closest("[data-newtpl]"); if (nt) { S.newTpl = S.newTpl === nt.dataset.newtpl ? null : nt.dataset.newtpl; render(); const r = $("#rcp"); if (r) r.focus(); return; }
  const th = t.closest("[data-theme]"); if (th) { await api("/api/settings", { theme: th.dataset.theme }); S.st.settings.theme = th.dataset.theme; S.tm = false; applyTheme(); return render(); }
  const a = t.closest("[data-act]"); if (!a) return;
  const act = a.dataset.act;
  if (act === "plusmenu") { S.pm = !S.pm; S.tm = false; return topbar(); }
  if (act === "thememenu") { S.tm = !S.tm; S.pm = false; return topbar(); }
  if (act === "showempty") { S.showEmpty = !S.showEmpty; return render(); }
  if (act === "sitsoon") return toast("Bientôt : tu décris la situation, Bon toutou propose la liste des pièces");
  if (act === "notpl") { S.newTpl = null; return render(); }
  if (act === "scan") { S.busy = "Lecture du dossier 00_A-TRIER…"; render(); const r = await api("/api/scan", {}); S.busy = ""; await load(); toast(`${r.added} ${plural(r.added, "nouveau", "nouveaux")} ${plural(r.added, "fichier")} ${plural(r.added, "trouvé")}`); }
  if (act === "reanalyze") { S.busy = "Nouvelle analyse des documents à trier…"; render(); const r = await api("/api/reanalyze", {}); S.busy = ""; await load(); toast(`${r.n} ${plural(r.n, "document")} ${plural(r.n, "relu")}`); }
  if (act === "solo") { S.solo = S.solo || new Set(); S.solo.add(a.dataset.id); render(); }
  if (act === "bview") { S.bview = !S.bview; render(); }
  if (act === "batch") { const ids = S.inbox.filter((p) => isHi(p) && !(S.unchecked && S.unchecked.has(p.id))).map((p) => p.id);
    const r = await api("/api/validate", { ids }); await load(); if (r.ok) toast(`${r.done} documents rangés`, r.batch); }
  if (act === "ok") { const r = await api("/api/validate", { ids: [a.dataset.id] }); await load(); if (r.ok) toast("Rangé", r.batch); }
  if (act === "ignore") { const r = await api("/api/ignore", { id: a.dataset.id }); await load(); toast("Ignoré · gardé dans 00_A-TRIER/_IGNORES", r.batch); }
  if (act === "undo") { const r = await api("/api/undo", { batch: a.dataset.b }); $("#toast").hidden = true; await load(); toast(r.msg); }
  if (act === "reveal") { const r = await api("/api/reveal", { p: a.dataset.p }); if (!r.ok) toast(r.msg || "Impossible d'ouvrir le dossier"); }
  if (act === "redetect") { S.busy = "Relecture des documents sans émetteur…"; render(); const r = await api("/api/redetect", {}); S.busy = ""; await load();
    toast(r.n ? `Émetteur retrouvé pour ${r.n} ${plural(r.n, "document")} · rangés dans leur dossier` : "Aucun émetteur retrouvé : corrige-les un par un avec « Corriger le classement »", r.batch); }
  if (act === "askterm") { S.confirm = "term"; render(); }
  if (act === "askrebuild") { S.confirm = "rebuild"; render(); }
  if (act === "noconfirm") { S.confirm = null; render(); }
  if (act === "fixopen") { S.fix = true; render(); }
  if (act === "fixcancel") { S.fix = false; render(); }
  if (act === "fixsave") { const f = (k) => $("#fx_" + k).value; const before = S.doc;
    const ch = {}; [["type", "type"], ["emitter", "emitter"], ["detail", "detail"], ["country", "country"]].forEach(([k, c]) => { const v = f(k).trim(); if (v && v !== String(before[c] || "")) ch[k] = v; });
    S.docOffer = Object.keys(ch).length ? { doc: before.id, overrides: ch, type: f("type") } : null;
    const r = await api("/api/reclassify", { id: S.doc.id, fields: { type: f("type"), country: f("country"), emitter: f("emitter"), date: f("date"), expiry: f("expiry"), person: f("person"), detail: f("detail") } }); S.fix = false; await load(); toast(r.ok ? "Corrigé · fichier renommé et déplacé" : (r.msg || "Erreur"), r.batch); }
  if (act === "terminate") { const r = await api("/api/terminate", { id: S.doc.id }); S.confirm = null; await load(); toast("Suivi terminé · tout est dans Archives › Terminés", r.batch); }
  if (act === "rebuild") { const r = await api("/api/rebuild", {}); S.confirm = null; await load(); toast(`Index reconstruit : ${r.docs} fichiers`); }
  if (act === "newdos") { const r = await api("/api/dossier/create", { template: S.newTpl, recipient: $("#rcp").value, country: $("#dcc").value }); S.newTpl = null; openDos(r.id); }
  if (act === "finalize") { const r = await api("/api/dossier/finalize", { id: S.dos.id }); if (!r.ok) return toast(r.msg); S.dos = r.dossier; await load(); toast("Paquet généré · envoie-le puis marque-le comme envoyé"); }
  if (act === "sent") { await api("/api/dossier/sent", { id: S.dos.id }); S.at = "sent"; go("archives"); toast("Marqué comme envoyé · la preuve est dans Archives"); }
  if (act === "reopen") { await api("/api/dossier/reopen", { id: S.dos.id }); await load(); toast("Dossier rouvert · l'ancien paquet est gardé dans .bontoutou/corbeille"); }
  if (act === "abandon") { await api("/api/dossier/abandon", { id: S.dos.id }); go("dossiers"); }
  if (act === "ollama") { await api("/api/settings", { use_ollama: a.checked }); load(); }
});
async function openDos(id) {
  S.dosId = id;
  const docs = await api("/api/docs"), ar = await api("/api/archives");
  S.allDocs = [...docs, ...ar.old];
  go("dossier");
}
window.addEventListener("DOMContentLoaded", load);
