/* Freemarket V0.1 — interface locale. Tout passe par le serveur local (127.0.0.1). */
const S = { v: "trier", st: null, inbox: [], docs: [], dossiers: [], arch: null, doc: null, dos: null,
            cc: null, q: "", at: "sent", busy: "", bview: false, confirm: null };
const $ = (s) => document.querySelector(s);
const esc = (x) => String(x == null ? "" : x).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const M = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
const frd = (d) => (d ? `${+d.slice(8, 10)} ${M[+d.slice(5, 7) - 1]} ${d.slice(0, 4)}` : "—");
const cc = (c) => `<span class="cc ${c}">${c}</span>`;
const CONF = { haute: "Confiance élevée", moyenne: "Confiance moyenne", basse: "À vérifier" };

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

async function load() {
  S.st = await api("/api/state");
  if (S.st.setup) { S.v = "setup"; return render(); }
  if (S.v === "setup") S.v = "trier";
  if (S.v === "trier") S.inbox = await api("/api/inbox");
  if (S.v === "docs") S.docs = await api("/api/docs");
  if (S.v === "doc") S.doc = await api("/api/doc?id=" + S.docId);
  if (S.v === "dossiers") S.dossiers = await api("/api/dossiers");
  if (S.v === "dossier") S.dos = await api("/api/dossier?id=" + S.dosId);
  if (S.v === "archives") S.arch = await api("/api/archives");
  if (S.v === "reglages") { S.hist = await api("/api/history"); S.rules = await api("/api/rules"); }
  if (S.v === "guide") S.inbox = await api("/api/inbox");
  if (S.v === "guide" || (S.v === "trier" && S.st && !S.st.settings.guide.fini && !S.st.settings.guide.masque)) S.guide = await api("/api/guide");
  render();
  clearTimeout(S.poll);
  if (S.v === "trier" && (S.inbox || []).some((p) => p.ai_pending)) S.poll = setTimeout(async () => { if (S.v === "trier" && !document.querySelector("input:focus,select:focus")) { S.inbox = await api("/api/inbox"); render(); } else load(); }, 4000);
}
function go(v, extra = {}) { S.fix = false; if (v !== S.v) S.q = ""; Object.assign(S, { v, confirm: null }, extra); window.scrollTo(0, 0); load(); }

function nav() {
  const vv = $("#ver"); if (vv && S.st) vv.textContent = (S.st.version ? "v" + S.st.version + " · " : "") + "LOCAL";
  if (S.v === "setup" || (S.st && S.st.setup)) { $("#nav").innerHTML = ""; return; }
  const c = S.st ? S.st.counts : {};
  const items = [["trier", "Trier", c.inbox], ["docs", "Documents"], ["dossiers", "Dossiers"], ["archives", "Archives"], ["reglages", "Réglages"]];
  const on = { doc: "docs", dossier: "dossiers" }[S.v] || S.v;
  $("#nav").innerHTML = items.map((i) => `<button class="${on === i[0] ? "on" : ""}" data-go="${i[0]}">${i[1]}${i[2] ? `<span class="badge">${i[2]}</span>` : ""}</button>`).join("");
}
function render() {
  nav();
  const V = { trier, docs, doc: docView, dossiers, dossier: dossierView, archives, reglages, guide: () => window.guideView ? guideView() : "", setup: () => window.setupView ? setupView() : "" }[S.v];
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
function trier() {
  S.solo = S.solo || new Set();
  const P = S.inbox, hi = P.filter((p) => p.confidence === "haute" && !p.duplicate && !p.overridden && !S.solo.has(p.id)), rest = P.filter((p) => !hi.includes(p));
  const sel = hi.filter((p) => !S.unchecked || !S.unchecked.has(p.id));
  return `<h1>Trier</h1><p class="lead">Dépose tes papiers tels quels. Freemarket les lit sur ton ordinateur, propose un nom et une place, et tu valides. <b>Tu peux te tromper : Freemarket ne détruit rien.</b></p>
  <div class="drop" id="drop"><b>Glisse tes fichiers ici</b><span class="sub">PDF, photos, scans — ils sont copiés dans 00_A-TRIER, l'original reste où il est.</span>
    <div class="acts" style="justify-content:center;margin-top:12px"><label class="cta" style="cursor:pointer">Choisir des fichiers<input type="file" id="files" multiple hidden></label><button class="ghost" data-act="scan">Relire le dossier 00_A-TRIER</button>${S.inbox.length ? `<button class="ghost" data-act="reanalyze">Relancer l'analyse</button>` : ""}</div></div>
  <p class="promise">🔒 Lu sur ton ordinateur. Aucun document ne quitte ta machine.</p>
  ${window.guideCard ? guideCard() : ""}
  ${S.busy ? `<div class="card busy"><span class="spin"></span>${esc(S.busy)}</div>` : ""}
  ${hi.length ? `<div class="label">En lot — confiance élevée</div><div class="card batch">${hi.map((p) => `<div class="row strip-${p.country}">
      <input type="checkbox" data-chk="${p.id}" ${sel.includes(p) ? "checked" : ""}>
      <div class="grow"><b>${esc(p.label)}</b> ${cc(p.country)} <span class="sub">· ${frd(p.date)}</span>
        <div class="sub">${esc(p.relation)} · → ${esc(p.dest)}</div>
        ${S.bview ? `<div class="fname sub">${esc(p.orig)} → <b>${esc(p.name)}</b></div>` : ""}</div>
      <span class="conf">${CONF[p.confidence]}</span>${reasons(p)}<button class="linkbtn" data-act="solo" data-id="${p.id}" style="margin-left:8px">Modifier</button></div>`).join("")}
    <div class="bfoot"><span class="sub"><b style="color:var(--text)">${sel.length} document${sel.length > 1 ? "s" : ""}</b> · confiance élevée · 0 conflit détecté</span>
      <span class="acts"><button class="ghost small" data-act="bview">${S.bview ? "Masquer le détail" : "Voir les " + sel.length}</button><button class="cta" data-act="batch" ${sel.length ? "" : "disabled"}>Valider ${sel.length} document${sel.length > 1 ? "s" : ""}</button></span></div></div>` : ""}
  ${rest.length ? `<div class="label">Un par un</div>${rest.map(tcard).join("")}` : ""}
  ${!P.length && !S.busy ? `<div class="card empty">Rien à trier. Dépose des fichiers ci-dessus.</div>` : ""}`;
}
function tcard(p) {
  const T = S.st.types, exp = ["carte_identite", "passeport", "permis_conduire", "visa", "assurance_habitation", "assurance_vehicule", "assurance_voyage", "carte_grise", "controle_vehicule"].includes(p.type);
  return `<div class="card tcard ${p.confidence}">
    <div class="tt"><b>${esc(p.label)}</b>${cc(p.country)}<span class="conf ${p.confidence}">${CONF[p.confidence]}</span>${p.ai_pending ? `<span class="pill acc"><span class="spin" style="width:11px;height:11px"></span> IA locale en train de lire…</span>` : ""}${reasons(p)}<span class="pill n">${esc(p.source)}</span>
      ${p.duplicate ? `<span class="pill bad">Doublon exact de « ${esc(p.duplicate.label)} »</span>` : ""}
      <a class="linkbtn" href="/api/inboxfile?id=${p.id}" target="_blank" style="margin-left:auto">Aperçu</a></div>
    <div class="edit">
      <label>Type<select data-ov="${p.id}" data-f="type">${typeOptions(p.type)}</select></label>
      <label>Pays<select data-ov="${p.id}" data-f="country">${Object.entries(S.st.countries).map(([k, v]) => `<option value="${k}" ${k === p.country ? "selected" : ""}>${k} · ${v}</option>`).join("")}</select></label>
      <label>Émetteur<input data-ov="${p.id}" data-f="emitter" value="${esc(p.emitter)}"></label>
      <label>Intitulé exact<input data-ov="${p.id}" data-f="detail" value="${esc(p.detail)}" placeholder="ex. ASSR2, Attestation de présence"></label>
      <label>Titulaire<input list="holders" data-ov="${p.id}" data-f="person" value="${esc(p.person === "moi" ? "" : p.person)}" placeholder="${esc(S.st.settings.owner || "toi")}"></label>
      <label>Date du document<input type="date" data-ov="${p.id}" data-f="date" value="${esc(p.date)}">${p.date_note ? `<small style="display:block;color:#9a6b00;font-weight:400;text-transform:none;letter-spacing:0;margin-top:4px">≈ Date approximative : ${esc(p.date_note)}</small>` : ""}</label>
      ${exp ? `<label>Expire le<input type="date" data-ov="${p.id}" data-f="expiry" value="${esc(p.expiry || "")}"></label>` : ""}
    </div>
    <dl class="grid"><dt>Reçu</dt><dd class="fname">${esc(p.orig)}</dd><dt>Nom proposé</dt><dd class="fname"><b>${esc(p.name)}</b></dd>
      <dt>Destination</dt><dd class="fname">${esc(p.dest)}</dd><dt>Document suivi</dt><dd>${esc(p.relation)}</dd></dl>
    ${window.ruleOffer ? ruleOffer({ inbox: p.id, overrides: p.overrides, type: p.type }) : ""}
    <div class="acts"><button class="cta small" data-act="ok" data-id="${p.id}">✓ Valider</button><button class="ghost small" data-act="ignore" data-id="${p.id}">Ignorer</button>
      <span class="sub">Ignorer garde le fichier dans 00_A-TRIER/_IGNORES.</span></div></div>`;
}

/* ------------------------------------------------ DOCUMENTS */
function docs() {
  const C = S.st.categories, q = S.q.toLowerCase();
  let L = S.docs.filter((d) => !q || (d.label + d.path + d.emitter).toLowerCase().includes(q));
  const ccs = [...new Set(S.docs.map((d) => d.country))];
  const cur = S.cc && ccs.includes(S.cc) ? S.cc : ccs[0];
  if (!q && cur) L = L.filter((d) => d.country === cur);
  const cats = [...new Set(L.map((d) => d.cat))].sort();
  return `<h1>Documents</h1><p class="lead">${S.docs.length} documents suivis. Freemarket garde la version actuelle et l'historique de chacun, et les réutilise dans tes dossiers sans copie.</p>
  <input class="search" id="q" placeholder="Chercher : passeport, EDF, fiche de paie…" value="${esc(S.q)}">
  ${q ? "" : `<div class="tabs">${ccs.map((c) => `<button class="${c === cur ? "on" : ""}" data-cc="${c}">${c} · ${esc(S.st.countries[c])}</button>`).join("")}</div>`}
  ${cats.map((c) => { const D = L.filter((d) => d.cat === c), subs = [...new Set(D.map((d) => d.sub_folder))];
    return `<div class="card sec"><div class="cathead"><span>${c} ${esc(C[c])}</span><span class="sub">${D.length}</span></div>
      ${subs.map((s) => `<div class="subhead">${esc(s.replace(/_/g, " "))} · ${D.filter((d) => d.sub_folder === s).length}</div>${D.filter((d) => d.sub_folder === s).map(docRow).join("")}`).join("")}</div>`; }).join("")
    || `<div class="card empty">Aucun document pour l'instant. Commence par Trier.</div>`}`;
}
function docRow(d) {
  const e = d.expiry ? Math.round((Date.parse(d.expiry) - Date.parse(S.st.today)) / 864e5) : null;
  return `<div class="row strip-${d.country}" data-doc="${d.id}" style="cursor:pointer"><div class="grow"><b>${esc(d.label)}</b> ${cc(d.country)}
    <div class="sub">${d.person && d.person !== "moi" && d.person !== S.st.settings.owner ? esc(d.person) + " · " : ""}${frd(d.doc_date)}${d.versions > 1 ? ` · ${d.versions} versions` : ""}</div></div>
    ${e !== null ? `<span class="pill ${e < 0 ? "bad" : e <= 60 ? "warn" : "n"}">${e < 0 ? "expiré" : "expire dans " + e + " j"}</span>` : ""}<span>›</span></div>`;
}
function docView() {
  const d = S.doc; if (!d) return "";
  return `<button class="ghost small" data-go="docs">← Documents</button>
  <h1 style="margin-top:14px">${esc(d.label)}</h1><p class="lead"><span class="pill acc">Document suivi</span> ${cc(d.country)} · ${d.detail ? esc(S.st.types[d.type].label) + " · " : ""}${esc(d.cat_label)} · utilisé dans ${d.used_in.length} dossier${d.used_in.length > 1 ? "s" : ""}, jamais copié</p>
  <div class="card box"><dl class="kv"><dt>Fichier</dt><dd class="fname">${esc(d.path)}</dd><dt>Date</dt><dd>${frd(d.doc_date)}</dd>
    ${d.expiry ? `<dt>Expire</dt><dd>${frd(d.expiry)} ${d.expired ? '<span class="pill bad">expiré</span>' : ""}</dd>` : ""}<dt>Titulaire</dt><dd>${esc(d.person === "moi" ? (S.st.settings.owner || "toi") : d.person)}</dd><dt>Émetteur</dt><dd>${esc(d.emitter)}</dd>
    <dt>Sorties</dt><dd>Jamais sorti de ton ordinateur</dd><dt>Reçu sous le nom</dt><dd class="fname">${esc(d.orig_name)}</dd></dl>
    <div class="acts" style="margin-top:12px"><a class="ghost small" href="/api/file?p=${encodeURIComponent(d.path)}" target="_blank" style="text-decoration:none">Ouvrir</a><button class="ghost small" data-act="reveal" data-p="${esc(d.path)}">Montrer dans le Finder</button><button class="ghost small" data-act="fixopen">Corriger le classement</button></div>
    ${S.fix ? `<div class="edit" style="margin-top:14px">
      <label>Type<select id="fx_type">${typeOptions(d.type)}</select></label>
      <label>Pays<select id="fx_country">${Object.entries(S.st.countries).map(([k, v]) => `<option value="${k}" ${k === d.country ? "selected" : ""}>${k} · ${v}</option>`).join("")}</select></label>
      <label>Intitulé exact<input id="fx_detail" value="${esc(d.detail || "")}" placeholder="ex. ASSR2, Attestation de présence"></label>
      <label>Titulaire<input list="holders" id="fx_person" value="${esc(d.person === "moi" ? "" : d.person)}" placeholder="${esc(S.st.settings.owner || "toi")}"></label>
      <label>Émetteur<input id="fx_emitter" value="${esc(d.emitter)}"></label>
      <label>Date du document<input type="date" id="fx_date" value="${esc(d.doc_date)}"></label>
      <label>Expire le<input type="date" id="fx_expiry" value="${esc(d.expiry || "")}"></label></div>
      <div class="acts" style="margin-top:10px"><button class="cta small" data-act="fixsave">Enregistrer</button><button class="linkbtn" data-act="fixcancel">annuler</button><span class="sub">Le fichier est renommé et déplacé au bon endroit. Annulable.</span></div>` : ""}</div>
  ${S.docOffer && S.docOffer.doc === d.id && window.ruleOffer ? `<div style="margin-top:12px">${ruleOffer(S.docOffer)}</div>` : ""}
  <div class="label">Version actuelle et historique</div>
  <div class="card">${d.history.map((h) => `<div class="row"><span class="pill ${h.status === "actuel" ? "ok" : "n"}">${esc(h.status_label)}</span><div class="grow"><b>${frd(h.doc_date)}</b><div class="fname sub">${esc(h.path)}</div></div><a class="linkbtn" href="/api/file?p=${encodeURIComponent(h.path)}" target="_blank">ouvrir</a></div>`).join("")}</div>
  <div class="label">Utilisé dans</div>
  <div class="card">${d.used_in.map((u) => `<div class="row"><div class="grow"><b>${esc(u.label)}</b><div class="sub">${esc(u.recipient)} · ${u.state === "envoye" ? "envoyé" : u.state === "finalise" ? "finalisé" : "en cours"}</div></div></div>`).join("") || `<div class="row sub">Pas encore utilisé.</div>`}</div>
  ${d.status === "actuel" ? `<div class="hint" style="margin-top:16px">Situation terminée (contrat fini, bail rendu, véhicule vendu) ? Toutes les versions partent dans Archives › Terminés. Rien n'est supprimé.
    ${S.confirm === "term" ? `<button class="cta small" data-act="terminate">Confirmer : terminer ce suivi</button> <button class="linkbtn" data-act="noconfirm">annuler</button>` : `<button class="ghost small" data-act="askterm">Terminer ce suivi…</button>`}</div>` : ""}`;
}

/* ------------------------------------------------ DOSSIERS */
function dossiers() {
  return `<h1>Dossiers</h1><p class="lead">Préparer → finaliser → envoyer toi-même → garder la preuve. Chaque pièce est prise dans sa version actuelle, sans copie dans ton rangement.</p>
  <div class="card box"><b>Nouveau dossier</b><div class="edit" style="margin-top:10px">
    <label>Situation<select id="tpl">${Object.entries(S.st.templates).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join("")}</select></label>
    <label>Destinataire<input id="rcp" placeholder="Agence Horizon"></label>
    <label>Pays<select id="dcc">${S.st.settings.countries.map((c) => `<option value="${c}">${c} · ${esc(S.st.countries[c])}</option>`).join("")}</select></label>
    <label>&nbsp;<button class="cta" data-act="newdos">Préparer</button></label></div></div>
  <div class="label">En cours</div>
  <div class="card">${S.dossiers.map((k) => `<div class="row" data-dos="${k.id}" style="cursor:pointer"><div class="grow"><b>${esc(k.label)}</b> ${cc(k.country)}<div class="sub">pour ${esc(k.recipient)} · ${k.state === "finalise" ? "finalisé, à envoyer" : "en préparation"}</div></div><span class="pill ${k.ok === k.total ? "ok" : "warn"}">${k.ok}/${k.total}</span><span>›</span></div>`).join("") || `<div class="row sub">Aucun dossier en cours.</div>`}</div>`;
}
function pieceChoice(k, pc) {
  const pool = S.allDocs || [];
  const pref = pool.filter((d) => pc.types.includes(d.type)), others = pool.filter((d) => !pc.types.includes(d.type));
  const opt = (d) => `<option value="${d.id}">${esc(d.label)} · ${frd(d.doc_date)}${d.status !== "actuel" ? " (" + d.status_label.toLowerCase() + ")" : ""}</option>`;
  return `<select class="field small" data-assign="${pc.i}"><option value="">${pc.source === "choisi" ? "Revenir au choix automatique" : "Choisir un autre document…"}</option>${pref.map(opt).join("")}${others.length ? `<optgroup label="Autres documents">${others.map(opt).join("")}</optgroup>` : ""}</select>`;
}
function dossierView() {
  const k = S.dos; if (!k) return "";
  const fin = k.state === "finalise";
  return `<button class="ghost small" data-go="dossiers">← Dossiers</button>
  <h1 style="margin-top:14px">${esc(k.label)}</h1><p class="lead">Pour <b>${esc(k.recipient)}</b> ${cc(k.country)} · ${k.ok} pièce${k.ok > 1 ? "s" : ""} sur ${k.total} prête${k.ok > 1 ? "s" : ""}.</p>
  <div class="card">${k.pieces.map((pc) => `<div class="piece"><span class="st ${pc.status}">${pc.status === "ok" ? "✓" : pc.status === "part" ? "!" : "–"}</span>
    <div class="grow"><b>${esc(pc.label)}</b>${pc.count > 1 ? ` <span class="sub">(${pc.have}/${pc.count})</span>` : ""}
      <div class="sub">${pc.docs.length ? pc.docs.map((d) => `${esc(d.label)} · version du ${frd(d.date)}`).join("<br>") : "introuvable dans tes documents — dépose-le dans Trier"}</div>
      ${pc.problems.length ? `<div class="sub" style="color:var(--warn)">${esc(pc.problems.join(" · "))}</div>` : ""}</div>
    ${fin ? "" : pieceChoice(k, pc)}</div>`).join("")}</div>
  ${fin ? `<div class="proof" style="margin-top:14px"><div class="label" style="margin:0">Paquet finalisé</div><b style="font-size:16px">${k.manifest.pieces.reduce((a, p) => a + p.files.length, 0)} fichiers figés pour ${esc(k.recipient)}</b>
      <div class="sub">Freemarket n'envoie pas le mail lui-même : envoie le paquet (dossier ou ZIP), puis marque-le comme envoyé pour garder la preuve.</div>
      <div class="fname sub" style="margin:6px 0">${esc(k.folder)}</div>
      <div class="acts"><button class="ghost small" data-act="reveal" data-p="${esc(k.folder)}">Ouvrir le paquet dans le Finder</button><a class="ghost small" style="text-decoration:none" href="/api/file?p=${encodeURIComponent(k.zip)}&dl=1">Télécharger le ZIP</a>
      <button class="cta small" data-act="sent">✓ Marquer comme envoyé</button><button class="linkbtn" data-act="reopen">Rouvrir</button></div></div>`
    : `<div class="acts" style="margin-top:14px"><button class="cta" data-act="finalize" ${k.ok < k.total ? "disabled" : ""}>Finaliser le dossier</button>${k.ok < k.total ? `<span class="sub">Il manque ${k.total - k.ok} pièce${k.total - k.ok > 1 ? "s" : ""}.</span>` : ""}<button class="linkbtn" data-act="abandon">Abandonner ce dossier</button></div>`}`;
}

/* ------------------------------------------------ ARCHIVES */
function archives() {
  const A = S.arch; if (!A) return "";
  const q = S.q.toLowerCase(), m = (s) => !q || s.toLowerCase().includes(q);
  const sent = A.sent.filter((e) => m(e.label + e.recipient)), old = A.old.filter((d) => m(d.label + d.path)), done = A.done.filter((d) => m(d.label + d.path));
  let body = "";
  if (S.at === "sent") body = sent.map((e) => `<div class="proof"><div class="label" style="margin:0">Dossier envoyé</div><div class="n">${e.count} fichiers</div>
      <div>${esc(e.label)} · à <b>${esc(e.recipient)}</b> ${cc(e.country)}</div><div>le ${frd(e.sent_at.slice(0, 10))}</div>
      <p style="margin:8px 0"><b>Voici exactement ce qui a été transmis.</b> <span class="sub">Ce paquet est figé : c'est ta preuve.</span></p>
      ${e.manifest.pieces.map((p) => `<div class="sub" style="margin-top:6px"><b style="color:var(--text)">${esc(p.label)}</b>${p.files.map((f) => `<div class="fname">version du ${frd(f.version_du)} · ${esc(f.fichier)} · SHA ${f.sha256.slice(0, 12)}…${f.remplacee_depuis ? ` <span class="pill acc">remplacée depuis par celle du ${frd(f.remplacee_depuis)}</span>` : ""}</div>`).join("")}</div>`).join("")}
      <div class="acts" style="margin-top:10px"><button class="ghost small" data-act="reveal" data-p="${esc(e.folder)}">Ouvrir dans le Finder</button><a class="linkbtn" target="_blank" href="/api/file?p=${encodeURIComponent(e.folder + "/PREUVE.txt")}">PREUVE.txt</a></div></div>`).join("") || `<div class="card empty">Aucun dossier envoyé pour l'instant.</div>`;
  if (S.at === "old") body = `<div class="card">${old.map((d) => `<div class="row strip-${d.country}" data-doc="${d.id}" style="cursor:pointer"><div class="grow"><b>${esc(d.label)}</b> ${cc(d.country)}<div class="sub">version du ${frd(d.doc_date)}</div><div class="fname sub">${esc(d.path)}</div></div><span>›</span></div>`).join("") || `<div class="row sub">Aucune ancienne version.</div>`}</div>`;
  if (S.at === "done") { const g = [...new Set(done.map((d) => d.country + "|" + d.sub_folder))];
    body = g.map((k) => { const [c, f] = k.split("|"), L = done.filter((d) => d.country === c && d.sub_folder === f);
      return `<div class="card sec"><div class="cathead"><span>${cc(c)} ${esc(f.replace(/_/g, " "))}</span><span class="sub">${L.length}</span></div>${L.map((d) => `<div class="row strip-${d.country}" data-doc="${d.id}" style="cursor:pointer"><div class="grow"><b>${esc(d.label)}</b><div class="sub">${frd(d.doc_date)}</div></div></div>`).join("")}</div>`; }).join("") || `<div class="card empty">Rien pour l'instant. Une situation finie (contrat, bail…) arrive ici.</div>`; }
  return `<h1>Archives</h1><p class="lead">Freemarket ne détruit rien. Ce qui n'est plus valable ou déjà envoyé vit ici, dans le dossier 99_ARCHIVES de chaque pays.</p>
  <input class="search" id="q" placeholder="Chercher dans les archives…" value="${esc(S.q)}">
  <div class="tabs">${[["sent", "Dossiers envoyés", sent.length], ["old", "Anciennes versions", old.length], ["done", "Terminés", done.length]].map((t) => `<button class="${S.at === t[0] ? "on" : ""}" data-at="${t[0]}">${t[1]} · ${t[2]}</button>`).join("")}</div>${body}`;
}

/* ------------------------------------------------ RÉGLAGES */
function reglages() {
  const st = S.st, T = st.tools;
  const readOk = T.pypdf || T.pdftotext;
  return `<h1>Réglages</h1><p class="lead">Freemarket ${esc(st.version || "")} : tout est local. Le moteur n'écoute que ton ordinateur (127.0.0.1).</p>
  <div class="card box"><dl class="kv"><dt>Bureau</dt><dd class="fname">${esc(st.root)}</dd>
    <dt>Ton nom</dt><dd><input class="field" id="owner" value="${esc(st.settings.owner || "")}" placeholder="Prénom Nom" style="width:260px"> <span class="sub">Titulaire par défaut, ajouté au nom de tes pièces d'identité, santé, diplômes.</span></dd>
    <dt>Pays actifs</dt><dd>${Object.entries(st.countries).map(([k, v]) => `<label style="margin-right:12px"><input type="checkbox" data-country="${k}" ${st.settings.countries.includes(k) ? "checked" : ""}> ${k} · ${esc(v)}</label>`).join("")}</dd></dl></div>
  ${window.privacySection ? privacySection() : ""}
  ${window.reglesSection ? reglesSection() : ""}
  <div class="label">Journal des sorties</div>
  <div class="card box">${(st.sorties || []).length ? `<b style="font-size:22px">${st.counts.egress}</b> sortie${st.counts.egress > 1 ? "s" : ""} de ton ordinateur, toutes avec ton accord.
      ${st.sorties.map((e) => `<div class="row"><div class="grow"><b>${esc(e.label)}</b>${e.what ? " · " + esc(e.what) : ""}<div class="sub">${esc(e.ts.replace("T", " "))} · vers ${esc(e.dest)}${e.level ? " · " + esc(st.privacy_levels[e.level] || e.level) : ""}</div></div></div>`).join("")}`
    : `<b>Rien n'est sorti de ton ordinateur.</b><div class="sub">Freemarket ne se connecte à internet que par une seule porte, et seulement avec ton accord : mise à jour, modèle d'IA, IA externe, rapport de bug. Chaque sortie serait notée ici avant de partir : quoi, quand, vers où.</div>`}</div>
  <div class="label">Lecture des documents</div>
  <div class="card box"><dl class="kv"><dt>Texte des PDF</dt><dd>${readOk ? "✓ disponible" : "✗ pas encore"} ${T.pypdf ? "(pypdf)" : T.pdftotext ? "(pdftotext)" : ""}</dd><dt>Scans et photos (OCR)</dt><dd>${T.apple_vision ? "✓ lecture de texte d'Apple (intégrée à macOS)" : T.tesseract ? "✓ disponible (tesseract)" : "✗ pas encore"}</dd></dl>
    ${!readOk || !(T.tesseract || T.apple_vision) ? `<div class="hint">Sans ces outils, Freemarket ne lit que le nom des fichiers. Pour lire le contenu, dans le Terminal :<br>
      ${!readOk ? `<code>python3 -m pip install --user pypdf</code><br>` : ""}${!T.tesseract ? `<code>brew install tesseract tesseract-lang poppler</code> (Homebrew : brew.sh)` : ""}</div>` : ""}</div>
  ${window.iaSection ? iaSection() : ""}
  ${window.majSection ? majSection() : ""}
  <div class="label">Historique des actions</div>
  <div class="card">${(S.hist || []).map((h, i) => `<div class="row"><div class="grow"><b>${esc(h.label)}</b><div class="sub">${esc(h.ts.replace("T", " "))}${h.undone ? " · annulé" : ""}</div></div>${!h.undone && i === (S.hist || []).findIndex((x) => !x.undone) ? `<button class="ghost small" data-act="undo" data-b="${h.batch}">Annuler</button>` : ""}</div>`).join("") || `<div class="row sub">Aucune action pour l'instant.</div>`}</div>
  <div class="label">Catalogue</div>
  <div class="card">${(st.packs || []).map((p) => `<div class="row"><div class="grow"><b>${esc(p.name)}</b> <span class="sub">${esc(p.version || "")}</span>
      <div class="sub">${p.kind === "officiel" ? "Officiel" : p.kind === "perso" ? "Tes règles" : "Importé (non vérifié)"}${p.types ? ` · ${p.types} type${p.types > 1 ? "s" : ""}` : ""}${p.rules ? ` · ${p.rules} règle${p.rules > 1 ? "s" : ""}` : ""}${p.emitters ? ` · ${p.emitters} organisme${p.emitters > 1 ? "s" : ""}` : ""}${p.templates ? ` · ${p.templates} démarche${p.templates > 1 ? "s" : ""}` : ""}</div></div></div>`).join("")}
    ${(st.catalog_warnings || []).length ? `<div class="hint">${st.catalog_warnings.map(esc).join("<br>")}</div>` : ""}</div>
  ${!st.settings.guide.fini || st.settings.guide.masque ? `<div class="label">Premier tri guidé</div><div class="card box">5 minutes pour découvrir Freemarket avec tes propres papiers. <button class="ghost small" data-act="g-start">${st.settings.guide.etape ? "Reprendre" : "Commencer"}</button></div>` : ""}
  <div class="label">Index et synchronisation</div>
  <div class="card box">Tes documents et leurs fiches sont dans ton dossier : tu peux le synchroniser avec l'outil de ton choix (iCloud, Syncthing, disque…). L'index de recherche, lui, reste sur cet appareil (${esc(st.device ? st.device.name : "")}) et se reconstruit à partir des fiches.
    ${st.newer_data ? `<div class="hint">Certaines données viennent d'une version plus récente de Freemarket : elles sont gardées intactes.</div>` : ""}
    <div style="margin-top:10px">${S.confirm === "rebuild" ? `<button class="cta small" data-act="rebuild">Confirmer la reconstruction</button> <button class="linkbtn" data-act="noconfirm">annuler</button>` : `<button class="ghost small" data-act="askrebuild">Reconstruire l'index…</button>`}</div></div>`;
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
  toast(ok ? `${ok} fichier${ok > 1 ? "s" : ""} lu${ok > 1 ? "s" : ""} · à toi de valider` : "Aucun fichier lu");
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
  document.querySelectorAll("[data-country]").forEach((el) => (el.onchange = async () => {
    const c = [...document.querySelectorAll("[data-country]:checked")].map((x) => x.dataset.country);
    if (c.length) { await api("/api/settings", { countries: c }); load(); }
  }));
  const ow = $("#owner"); if (ow) ow.onchange = async () => { await api("/api/settings", { owner: ow.value.trim() }); toast("Nom enregistré"); load(); };
  const am = $("#aimode"); if (am) am.onchange = async () => { await api("/api/settings", { ai_mode: am.value }); toast("Réglage enregistré"); load(); };

}
document.addEventListener("click", async (e) => {
  const t = e.target;
  const g = t.closest("[data-go]"); if (g) return go(g.dataset.go);
  const dc = t.closest("[data-doc]"); if (dc) return go("doc", { docId: dc.dataset.doc });
  const ds = t.closest("[data-dos]"); if (ds) { S.allDocs = null; return openDos(ds.dataset.dos); }
  const c = t.closest("[data-cc]"); if (c) { S.cc = c.dataset.cc; return render(); }
  const at = t.closest("[data-at]"); if (at) { S.at = at.dataset.at; return render(); }
  const a = t.closest("[data-act]"); if (!a) return;
  const act = a.dataset.act;
  if (act === "scan") { S.busy = "Lecture du dossier 00_A-TRIER…"; render(); const r = await api("/api/scan", {}); S.busy = ""; await load(); toast(`${r.added} nouveau${r.added > 1 ? "x" : ""} fichier${r.added > 1 ? "s" : ""} trouvé${r.added > 1 ? "s" : ""}`); }
  if (act === "reanalyze") { S.busy = "Nouvelle analyse des documents à trier…"; render(); const r = await api("/api/reanalyze", {}); S.busy = ""; await load(); toast(`${r.n} document${r.n > 1 ? "s" : ""} relu${r.n > 1 ? "s" : ""}`); }
  if (act === "solo") { S.solo = S.solo || new Set(); S.solo.add(a.dataset.id); render(); }
  if (act === "bview") { S.bview = !S.bview; render(); }
  if (act === "batch") { const ids = S.inbox.filter((p) => p.confidence === "haute" && !p.duplicate && !p.overridden && !(S.solo && S.solo.has(p.id)) && !(S.unchecked && S.unchecked.has(p.id))).map((p) => p.id);
    const r = await api("/api/validate", { ids }); await load(); if (r.ok) toast(`${r.done} documents rangés`, r.batch); }
  if (act === "ok") { const r = await api("/api/validate", { ids: [a.dataset.id] }); await load(); if (r.ok) toast("Rangé", r.batch); }
  if (act === "ignore") { const r = await api("/api/ignore", { id: a.dataset.id }); await load(); toast("Ignoré · gardé dans 00_A-TRIER/_IGNORES", r.batch); }
  if (act === "undo") { const r = await api("/api/undo", { batch: a.dataset.b }); $("#toast").hidden = true; await load(); toast(r.msg); }
  if (act === "reveal") api("/api/reveal", { p: a.dataset.p });
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
  if (act === "newdos") { const r = await api("/api/dossier/create", { template: $("#tpl").value, recipient: $("#rcp").value, country: $("#dcc").value }); openDos(r.id); }
  if (act === "finalize") { const r = await api("/api/dossier/finalize", { id: S.dos.id }); if (!r.ok) return toast(r.msg); S.dos = r.dossier; await load(); toast("Paquet généré · envoie-le puis marque-le comme envoyé"); }
  if (act === "sent") { await api("/api/dossier/sent", { id: S.dos.id }); S.at = "sent"; go("archives"); toast("Marqué comme envoyé · la preuve est dans Archives"); }
  if (act === "reopen") { await api("/api/dossier/reopen", { id: S.dos.id }); await load(); toast("Dossier rouvert · l'ancien paquet est gardé dans .freemarket/corbeille"); }
  if (act === "abandon") { await api("/api/dossier/abandon", { id: S.dos.id }); go("dossiers"); }
  if (act === "ollama") { await api("/api/settings", { use_ollama: a.checked }); load(); }
});
async function openDos(id) {
  S.dosId = id;
  const docs = await api("/api/docs"), ar = await api("/api/archives");
  S.allDocs = [...docs, ...ar.old];
  go("dossier");
}
load();
