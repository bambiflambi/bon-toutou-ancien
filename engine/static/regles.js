/* Bon toutou — règles et types créés par l'utilisateur, partage, confidentialité.
   Une règle : « quand un document contient <indice> → <champ> = <valeur> ». Visible, modifiable, jamais apprise en douce. */
const CHAMPS = { emitter: "Émetteur", type: "Type", detail: "Intitulé", country: "Pays" };
const LEVELS = [["local", "🔒 Local uniquement"], ["autorisation", "◐ Sur autorisation"], ["externe", "☁ Externe autorisé"]];

/* ---------- proposition après une correction (carte Trier, page document) */
function ruleOffer(o) {
  const ch = Object.entries(o.overrides || {}).filter(([k]) => CHAMPS[k]);
  if (!ch.length) return "";
  const key = (o.inbox || o.doc) + JSON.stringify(o.overrides);
  if ((S.offerOff || new Set()).has(key) || (S.ruleMade || new Set()).has(o.inbox || o.doc)) return "";
  const show = ([k, v]) => `${CHAMPS[k]} → <b>${esc(k === "type" ? (S.st.types[v] || {}).label || v : k === "country" ? S.st.countries[v] || v : v)}</b>`;
  return `<div class="offer"><span>Tu as corrigé ${ch.map(show).join(", ")}. <b>Faire de ta correction une règle ?</b> <span class="sub">Bon toutou l'appliquera tout seul aux prochains documents.</span></span>
    <span class="acts">${ch.map(([k, v]) => `<button class="ghost small" data-act="r-new" data-o='${esc(JSON.stringify({ inbox: o.inbox || null, doc: o.doc || null, champ: k, valeur: v, type: o.type }))}'>Créer une règle « ${CHAMPS[k]} »</button>`).join("")}
    <button class="linkbtn" data-act="r-off" data-k='${esc(key)}'>Juste cette fois</button></span></div>`;
}

/* ---------- fenêtre */
function modalView() {
  const m = S.modal;
  const body = { rule: ruleModal, type: typeModal, import: importModal, propose: proposeModal }[m.kind];
  return `<div class="ov" data-act="m-close-bg"><div class="modal" role="dialog">${body ? body(m) : ""}</div></div>`;
}
function words(text) {
  return (text || "").replace(/\s+/g, " ").trim().split(" ").filter(Boolean).slice(0, 320);
}
function wordCloud(m) {
  if (!m.words || !m.words.length) return `<div class="sub">${m.loading ? "Lecture du texte…" : "Pas de texte lu pour ce document : écris l'indice à la main."}</div>`;
  const [i, j] = m.sel || [-1, -1];
  return `<div class="words">${m.words.map((w, k) => `<span class="w${k >= i && k <= j ? " on" : ""}" data-w="${k}">${esc(w)}</span>`).join(" ")}</div>`;
}
function valueField(m) {
  if (m.champ === "type") return `<select class="field" id="r_val">${typeOptions(m.valeur)}</select>`;
  if (m.champ === "country") return `<select class="field" id="r_val">${Object.entries(S.st.countries).map(([k, v]) => `<option value="${k}" ${k === m.valeur ? "selected" : ""}>${k} · ${esc(v)}</option>`).join("")}</select>`;
  return `<input class="field" id="r_val" value="${esc(m.valeur || "")}" placeholder="${m.champ === "emitter" ? "ex. Lycée Audouin-Dubreuil" : "ex. ASSR2"}">`;
}
function ruleModal(m) {
  const pv = m.preview, T = S.st.types;
  return `<h2>${m.saved ? "Règle créée" : m.id ? "Modifier la règle" : "Nouvelle règle"}</h2>
  <p class="sub">Choisis les mots qui reconnaissent ce genre de document. Touche un mot, puis ses voisins pour former une expression.</p>
  ${m.words !== undefined ? wordCloud(m) : ""}
  <div class="rq"><b>Quand un document contient</b><input class="field" id="r_ind" value="${esc(m.indice || "")}" placeholder="ex. LYCEE DU PORT"></div>
  <div class="rq"><b>Alors</b><select class="field" id="r_champ">${Object.entries(CHAMPS).map(([k, v]) => `<option value="${k}" ${k === m.champ ? "selected" : ""}>${v}</option>`).join("")}</select><span>=</span>${valueField(m)}</div>
  ${m.champ !== "type" && m.type && T[m.type] ? `<label class="chk"><input type="checkbox" id="r_only" ${m.only !== false ? "checked" : ""}> Seulement pour les documents de type « ${esc(T[m.type].label)} »</label>` : ""}
  <div class="pv">${!pv ? `<span class="sub">Choisis un indice pour voir l'effet de la règle.</span>` : !pv.ok ? `<span class="sub" style="color:var(--warn)">${esc(pv.msg)}</span>`
    : `<div><b>${esc(pv.phrase)}</b></div>
      <div class="sub">${pv.inbox.length ? `S'appliquera à ${pv.inbox.length} document${pv.inbox.length > 1 ? "s" : ""} à trier. ` : ""}${pv.docs.length ? `Changerait aussi ${pv.docs.length} document${pv.docs.length > 1 ? "s" : ""} déjà rangé${pv.docs.length > 1 ? "s" : ""} :` : "Aucun document déjà rangé ne change."}</div>
      ${pv.docs.slice(0, 8).map((d) => `<div class="sub">· ${esc(d.label)} (${frd(d.date)}) — ${esc(d.change)}</div>`).join("")}${pv.docs.length > 8 ? `<div class="sub">· et ${pv.docs.length - 8} autres</div>` : ""}`}</div>
  ${m.saved ? `<div class="hint">Règle créée ✓${m.saved.docs.length ? ` · Corriger aussi les ${m.saved.docs.length} document${m.saved.docs.length > 1 ? "s" : ""} déjà rangé${m.saved.docs.length > 1 ? "s" : ""} ? Ils seront renommés et déplacés, en une seule action annulable.
      <div class="acts" style="margin-top:8px"><button class="cta small" data-act="r-apply">Corriger les ${m.saved.docs.length}</button><button class="linkbtn" data-act="m-close">Non merci</button></div>` : ""}</div>`
    : `<div class="acts" style="margin-top:14px"><button class="cta" data-act="r-save" ${pv && pv.ok ? "" : "disabled"}>${m.id ? "Enregistrer" : "Créer la règle"}</button><button class="linkbtn" data-act="m-close">${m.id ? "Annuler" : "Juste cette fois"}</button></div>`}`;
}
function typeModal(m) {
  const C = S.st.categories, subs = Object.entries(S.st.subs).filter(([k]) => k.startsWith((m.cat || "01") + "-"));
  return `<h2>Nouveau type de document</h2><p class="sub">Pour un papier que Bon toutou ne connaît pas encore (permis bateau, carte de club…).</p>
  <div class="edit" style="margin-top:10px">
    <label>Nom<input id="t_label" value="${esc(m.label || "")}" placeholder="ex. Permis bateau"></label>
    <label>Catégorie<select id="t_cat">${Object.entries(C).map(([k, v]) => `<option value="${k}" ${k === (m.cat || "01") ? "selected" : ""}>${k} ${esc(v)}</option>`).join("")}</select></label>
    <label>Sous-dossier<select id="t_sub">${subs.map(([k, v]) => `<option value="${k}" ${k === m.sub ? "selected" : ""}>${k} ${esc(v.replace(/-/g, " "))}</option>`).join("")}</select></label></div>
  <div class="rq" style="margin-top:10px"><b>Une seule version à garder ?</b>${[["type", "Oui"], ["emitter", "Oui, une par émetteur"], ["none", "Non, chacun compte"]].map(([k, v]) => `<label class="chk"><input type="radio" name="t_suivi" value="${k}" ${(m.suivi || "none") === k ? "checked" : ""}> ${v}</label>`).join("")}</div>
  <label class="chk"><input type="checkbox" id="t_exp" ${m.expiry ? "checked" : ""}> Il a une date d'expiration</label>
  <div class="rq"><b>Mots qui le reconnaissent</b><input class="field" id="t_kw" value="${esc((m.kw || []).join(", "))}" placeholder="ex. permis plaisance, option côtière" style="flex:1"></div>
  <div class="rq"><span class="sub">ou choisis-les dans un exemple :</span><select class="field small" id="t_ex"><option value="">Un document…</option>${(m.examples || []).map((d) => `<option value="${d.k}" ${d.k === m.ex ? "selected" : ""}>${esc(d.label)}</option>`).join("")}</select></div>
  ${m.words !== undefined ? wordCloud(m) : ""}
  ${m.err ? `<div class="sub" style="color:var(--warn)">${esc(m.err)}</div>` : ""}
  <div class="acts" style="margin-top:14px"><button class="cta" data-act="t-save">Créer le type</button><button class="linkbtn" data-act="m-close">Annuler</button></div>`;
}
function importModal(m) {
  const p = m.preview;
  return `<h2>Importer des règles</h2>
  ${!p ? `<p class="sub">Lecture…</p>` : !p.ok ? `<p style="color:var(--warn)">${esc(p.msg)}</p><button class="linkbtn" data-act="m-close">Fermer</button>`
    : `<p><b>${esc(p.name)}</b> ajoute ${p.types} type${p.types > 1 ? "s" : ""} et ${p.rules} règle${p.rules > 1 ? "s" : ""}${p.refused ? ` (${p.refused} refusée${p.refused > 1 ? "s" : ""} : invalides)` : ""}. Elles s'appliqueraient à ${p.docs} de tes documents.</p>
      <div class="hint">⚠ Ce pack n'est pas signé par Bon toutou : il vient de quelqu'un d'autre. Il ne contient que des mots et des endroits où ranger, il ne peut rien exécuter ni envoyer. Tu pourras le désactiver ou le retirer à tout moment.</div>
      <div class="acts" style="margin-top:14px"><button class="cta" data-act="i-ok">Importer</button><button class="linkbtn" data-act="m-close">Annuler</button></div>`}`;
}
function proposeModal(m) {
  const p = m.data;
  return `<h2>Proposer pour une future version</h2>
  <p class="sub">Voici exactement ce qui partirait : des règles et des types, jamais un document. Relis, retire ce qui est personnel, puis envoie.</p>
  ${!p ? "<p class='sub'>Préparation…</p>" : `${p.flags.length ? `<div class="hint">À vérifier avant d'envoyer :<br>${p.flags.map(esc).join("<br>")}<br>Supprime ou modifie ces règles dans « Mes règles », ou décoche-les.</div>` : ""}
    <div class="pick">${(S.rules.rules || []).filter((r) => r.actif !== false).map((r) => `<label class="chk"><input type="checkbox" data-pr="${r.id}" ${!m.ids || m.ids.includes(r.id) ? "checked" : ""}> ${esc(r.phrase)}</label>`).join("")}
      ${(S.rules.types || []).map((t) => `<label class="chk"><input type="checkbox" data-pt="${t.id}" ${!m.tids || m.tids.includes(t.id) ? "checked" : ""}> Type : ${esc(t.label)}</label>`).join("")}</div>
    <textarea class="field mono" readonly rows="8">${esc(p.text)}</textarea>
    <div class="acts" style="margin-top:12px">${p.mailto ? `<button class="cta" data-act="p-sent">Ouvrir ma messagerie</button>` : `<button class="cta" data-act="p-copy">Copier le texte</button><button class="ghost" data-act="p-file">Enregistrer en fichier</button>`}
      <button class="linkbtn" data-act="m-close">Annuler</button></div>
    ${p.mailto ? "" : `<p class="sub">L'adresse de contribution n'est pas encore définie : copie le texte ou enregistre le fichier pour l'envoyer toi-même.</p>`}`}`;
}

/* ---------- Réglages : Mes règles + confidentialité */
function reglesSection() {
  const R = S.rules || { rules: [], types: [], imported: [] };
  return `<div class="label">Mes règles</div>
  <div class="card">${R.rules.map((r) => `<div class="row"><input type="checkbox" data-rt="${r.id}" ${r.actif !== false ? "checked" : ""} title="Active">
      <div class="grow"><b style="${r.actif === false ? "opacity:.5" : ""}">${esc(r.phrase)}</b>${S.rtest && S.rtest.id === r.id ? `<div class="sub">${esc(S.rtest.msg)}</div>` : ""}</div>
      <select class="field small" data-rtry="${r.id}"><option value="">Essayer sur…</option>${(S.allDocsLite || []).map((d) => `<option value="${d.id}">${esc(d.label)}</option>`).join("")}</select>
      <button class="linkbtn" data-act="r-edit" data-id="${r.id}">Modifier</button><button class="linkbtn" data-act="r-del" data-id="${r.id}">Supprimer</button></div>`).join("")
    || `<div class="row sub">Aucune règle. Quand tu corriges un document, Bon toutou te proposera d'en faire une règle.</div>`}
    ${R.types.map((t) => `<div class="row"><span class="pill acc">Type perso</span><div class="grow"><b>${esc(t.label)}</b><div class="sub">${esc(t.cat)} › ${esc(t.sub)} · reconnu par : ${esc((t.kw || []).join(", "))}</div></div></div>`).join("")}
    <div class="bfoot"><span class="acts"><button class="ghost small" data-act="t-new">+ Nouveau type de document</button></span>
      <span class="acts"><button class="ghost small" data-act="r-export">Exporter</button>
        <label class="ghost small" style="cursor:pointer">Importer<input type="file" id="r_import" accept=".json,application/json" hidden></label>
        <button class="ghost small" data-act="p-open" ${R.rules.length || R.types.length ? "" : "disabled"}>Proposer pour une future version</button></span></div></div>
  ${R.imported.length ? `<div class="card" style="margin-top:8px">${R.imported.map((p) => `<div class="row"><span class="pill warn">Importé · non vérifié</span><div class="grow"><b>${esc(p.name)}</b> <span class="sub">${esc(p.version)} · ${p.types} type(s) · ${p.rules} règle(s)</span></div>
      <label class="chk"><input type="checkbox" data-pk="${esc(p.id)}" ${p.disabled ? "" : "checked"}> actif</label><button class="linkbtn" data-act="i-rm" data-f="${esc(p.file)}">Retirer</button></div>`).join("")}</div>` : ""}`;
}
function privacySection() {
  const st = S.st, P = st.settings.privacy || {};
  return `<div class="label">Confidentialité par catégorie</div>
  <div class="card box"><p class="sub" style="margin-top:0">Ce qui pourrait sortir de ton ordinateur si un jour tu actives une IA externe. Tant qu'elle n'est pas activée, rien ne sort, quel que soit le réglage. Un document pas encore trié est toujours 🔒.</p>
    <div class="privgrid">${Object.entries(st.categories).sort((a, b) => a[0].localeCompare(b[0])).map(([c, l]) => `<label><span>${c} ${esc(l)}</span><select class="field small" data-priv="${c}">${LEVELS.map(([k, v]) => `<option value="${k}" ${(P[c] || "local") === k ? "selected" : ""}>${v}</option>`).join("")}</select></label>`).join("")}</div>
    <details class="why" style="margin-top:12px" ${S.mk || S.mkIn ? "open" : ""}><summary>Essayer le masquage</summary>
      <p class="sub">Avant tout envoi, les numéros sensibles sont remplacés : IBAN, carte, sécurité sociale, passeport, n° fiscal, téléphone, e-mail.</p>
      <textarea class="field" id="mk_in" rows="3" style="width:100%" placeholder="Colle un texte, ex. IBAN FR76 3000… · tél 06 12 34 56 78">${esc(S.mkIn || "")}</textarea>
      ${S.mk ? `<div class="hint"><b>Ce qui partirait :</b><br>${esc(S.mk.text)}${S.mk.found.length ? `<br><span class="sub">Masqué : ${esc(S.mk.found.join(", "))}</span>` : ""}</div>` : ""}
      <button class="ghost small" data-act="mk">Voir ce qui partirait</button></details></div>`;
}

/* ---------- logique */
async function openRule(o) {
  const m = { kind: "rule", champ: o.champ || "emitter", valeur: o.valeur || "", type: o.type || null, indice: o.indice || "", id: o.id || null,
              only: o.only !== undefined ? o.only : o.champ === "detail", src: o.inbox || o.doc || null, words: o.inbox || o.doc ? [] : undefined, loading: !!(o.inbox || o.doc) };
  S.modal = m; render();
  if (o.inbox || o.doc) {
    const t = await api("/api/text?" + (o.inbox ? "inbox=" + o.inbox : "doc=" + o.doc));
    m.words = words(t.text); m.loading = false; render();
  }
  if (m.indice) rulePreview();
}
let pvT;
function ruleData() {
  const m = S.modal;
  return { id: m.id || undefined, indice: m.indice, champ: m.champ, valeur: m.valeur, type: m.champ !== "type" && m.type && m.only !== false ? m.type : null };
}
function rulePreview() {
  clearTimeout(pvT);
  pvT = setTimeout(async () => { if (!S.modal || S.modal.kind !== "rule") return; S.modal.preview = await api("/api/rules/preview", { rule: ruleData() }); render(); }, 250);
}
function bindExtra() {
  const m = S.modal;
  if (m && (m.kind === "rule" || m.kind === "type")) {
    document.querySelectorAll("[data-w]").forEach((el) => (el.onclick = () => {
      const k = +el.dataset.w;
      if (m.kind === "type") { m.kw = m.kw || []; const w = m.words[k].replace(/[.,;:()«»"]/g, ""); if (w.length >= 3 && !m.kw.includes(w)) m.kw.push(w); return render(); }
      let [i, j] = m.sel || [-1, -1];
      if (i < 0) [i, j] = [k, k]; else if (k === j + 1) j = k; else if (k === i - 1) i = k; else if (k >= i && k <= j) [i, j] = [k, k]; else [i, j] = [k, k];
      m.sel = [i, j]; m.indice = m.words.slice(i, j + 1).join(" ").replace(/^[.,;:()«»"]+|[.,;:()«»"]+$/g, ""); m.saved = null; render(); rulePreview();
    }));
  }
  if (m && m.kind === "rule") {
    const ind = $("#r_ind"); if (ind) ind.oninput = () => { m.indice = ind.value; m.sel = null; rulePreview(); };
    const ch = $("#r_champ"); if (ch) ch.onchange = () => { m.champ = ch.value; m.valeur = m.champ === "type" ? m.type || "autre" : m.champ === "country" ? "FR" : ""; render(); rulePreview(); };
    const v = $("#r_val"); if (v) (v.tagName === "SELECT" ? (v.onchange = () => { m.valeur = v.value; rulePreview(); }) : (v.oninput = () => { m.valeur = v.value; rulePreview(); }));
    const o = $("#r_only"); if (o) o.onchange = () => { m.only = o.checked; rulePreview(); };
  }
  if (m && m.kind === "type") {
    const sync = () => { m.label = $("#t_label").value; m.cat = $("#t_cat").value; m.sub = $("#t_sub").value; m.expiry = $("#t_exp").checked;
      m.suivi = (document.querySelector("[name=t_suivi]:checked") || {}).value; m.kw = $("#t_kw").value.split(",").map((x) => x.trim()).filter(Boolean); };
    ["#t_label", "#t_kw", "#t_sub", "#t_exp"].forEach((s) => { const el = $(s); if (el) el.onchange = sync; });
    document.querySelectorAll("[name=t_suivi]").forEach((el) => (el.onchange = sync));
    const c = $("#t_cat"); if (c) c.onchange = () => { sync(); m.sub = null; render(); };
    const ex = $("#t_ex"); if (ex) ex.onchange = async () => { sync(); m.ex = ex.value; if (!ex.value) { m.words = undefined; return render(); }
      m.words = []; m.loading = true; render(); const t = await api("/api/text?" + ex.value); m.words = words(t.text); m.loading = false; render(); };
  }
  if (m && m.kind === "propose") {
    document.querySelectorAll("[data-pr],[data-pt]").forEach((el) => (el.onchange = async () => {
      m.ids = [...document.querySelectorAll("[data-pr]:checked")].map((x) => x.dataset.pr);
      m.tids = [...document.querySelectorAll("[data-pt]:checked")].map((x) => x.dataset.pt);
      m.data = await api("/api/rules/propose", { ids: m.ids, types: m.tids }); render();
    }));
  }
  document.querySelectorAll("[data-rt]").forEach((el) => (el.onchange = async () => { await api("/api/rules/toggle", { id: el.dataset.rt, actif: el.checked }); toast(el.checked ? "Règle activée" : "Règle désactivée"); load(); }));
  document.querySelectorAll("[data-rtry]").forEach((el) => (el.onchange = async () => { if (!el.value) return; const r = await api("/api/rules/test", { id: el.dataset.rtry, doc: el.value }); S.rtest = { id: el.dataset.rtry, msg: `${r.label} : ${r.msg}` }; render(); }));
  document.querySelectorAll("[data-priv]").forEach((el) => (el.onchange = async () => { await api("/api/settings", { privacy: { [el.dataset.priv]: el.value } }); toast("Niveau enregistré"); load(); }));
  document.querySelectorAll("[data-pk]").forEach((el) => (el.onchange = async () => {
    const dis = new Set(S.st.settings.disabled_packs || []); el.checked ? dis.delete(el.dataset.pk) : dis.add(el.dataset.pk);
    await api("/api/settings", { disabled_packs: [...dis] }); load(); }));
  const mk = $("#mk_in"); if (mk) mk.oninput = () => (S.mkIn = mk.value);
  const imp = $("#r_import"); if (imp) imp.onchange = async () => {
    const f = imp.files[0]; if (!f) return; S.importRaw = await f.text(); S.modal = { kind: "import" }; render();
    S.modal.preview = await (await fetch("/api/rules/import", { method: "POST", body: S.importRaw })).json(); render(); };
  if (S.v === "reglages" && !S.allDocsLite) api("/api/docs").then((d) => { S.allDocsLite = d; if (S.v === "reglages") render(); });
}
document.addEventListener("click", async (e) => {
  const a = e.target.closest("[data-act]"); if (!a) return;
  const act = a.dataset.act, m = S.modal;
  if (act === "m-close-bg" && e.target === a) { S.modal = null; return render(); }
  if (act === "m-close") { S.modal = null; await load(); return; }
  if (act === "r-off") { S.offerOff = S.offerOff || new Set(); S.offerOff.add(a.dataset.k); return render(); }
  if (act === "r-new") return openRule(JSON.parse(a.dataset.o));
  if (act === "r-edit") { const r = S.rules.rules.find((x) => x.id === a.dataset.id); return openRule({ ...r, only: !!r.type }); }
  if (act === "r-del") { await api("/api/rules/delete", { id: a.dataset.id }); toast("Règle supprimée (gardée dans l'historique de mes-regles.json)"); return load(); }
  if (act === "r-save") {
    const r = await api("/api/rules/save", { rule: ruleData() });
    if (!r.ok) { m.preview = { ok: false, msg: r.msg }; return render(); }
    m.id = r.rule.id; m.saved = { docs: r.preview.docs || [] };
    if (m.src) { S.ruleMade = S.ruleMade || new Set(); S.ruleMade.add(m.src); }
    if (!m.saved.docs.length) { S.modal = null; await load(); return toast("Règle créée · elle s'appliquera aux prochains documents"); }
    return render();
  }
  if (act === "r-apply") { const r = await api("/api/rules/apply", { id: m.id, docs: m.saved.docs.map((d) => d.id) }); S.modal = null; await load(); return toast(r.ok ? `${r.n} document${r.n > 1 ? "s" : ""} corrigé${r.n > 1 ? "s" : ""}` : r.msg, r.batch); }
  if (act === "t-new") {
    const inbox = (await api("/api/inbox")).map((p) => ({ k: "inbox=" + p.id, label: "À trier : " + p.orig }));
    const docs = (S.allDocsLite || []).map((d) => ({ k: "doc=" + d.id, label: d.label }));
    S.modal = { kind: "type", cat: "01", examples: [...inbox, ...docs] }; return render();
  }
  if (act === "t-save") {
    const g = (s) => $(s); m.label = g("#t_label").value; m.cat = g("#t_cat").value; m.sub = g("#t_sub").value; m.expiry = g("#t_exp").checked;
    m.suivi = (document.querySelector("[name=t_suivi]:checked") || {}).value; m.kw = g("#t_kw").value.split(",").map((x) => x.trim()).filter(Boolean);
    const r = await api("/api/types/save", { type: { label: m.label, cat: m.cat, sub: m.sub, suivi: m.suivi, expiry: m.expiry, kw: m.kw } });
    if (!r.ok) { m.err = r.msg; return render(); }
    S.modal = null; await load(); return toast(`Type « ${m.label} » créé · les documents à trier ont été relus`);
  }
  if (act === "i-ok") { const r = await (await fetch("/api/rules/import?confirm=1", { method: "POST", body: S.importRaw })).json(); S.modal = null; await load(); return toast(r.ok ? "Pack importé · marqué « non vérifié »" : r.msg); }
  if (act === "i-rm") { await api("/api/rules/remove", { file: a.dataset.f }); toast("Pack retiré · gardé dans .bontoutou/packs/_retires"); return load(); }
  if (act === "p-open") { S.modal = { kind: "propose" }; render(); S.modal.data = await api("/api/rules/propose", {}); return render(); }
  if (act === "p-copy") { try { await navigator.clipboard.writeText(m.data.text); } catch (x) { /* sélection manuelle */ }
    await api("/api/rules/proposed", { dest: "copié pour envoi manuel", what: `${m.data.pack.rules.length} règle(s), ${Object.keys(m.data.pack.types).length} type(s)`, bytes: m.data.text.length }); return toast("Copié · colle-le dans un e-mail"); }
  if (act === "p-sent" && window.openExternal) openExternal(m.data.mailto);
  if (act === "p-file") { const r = await api("/api/export", { kind: "proposition", text: m.data.text }); toast(r.ok ? `Enregistré dans ${r.folder}` : (r.msg || "Erreur")); }
  if (act === "p-sent" || act === "p-file") { api("/api/rules/proposed", { dest: act === "p-sent" ? "ta messagerie" : "fichier enregistré", what: `${m.data.pack.rules.length} règle(s), ${Object.keys(m.data.pack.types).length} type(s)`, bytes: m.data.text.length }); }
  if (act === "r-export") { const r = await api("/api/export", { kind: "regles" }); return toast(r.ok ? `Tes règles sont enregistrées dans ${r.folder}` : (r.msg || "Erreur")); }
  if (act === "mk") { S.mk = await api("/api/mask", { text: $("#mk_in").value }); return render(); }
});
