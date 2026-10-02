/* Bon toutou — premier tri guidé (facultatif, depuis Trier). 7 écrans, chacun peut être passé ; on reprend où on s'est arrêté.
   Les questions déjà posées à l'installation (pays, emplacement du bureau, confidentialité) ne sont pas reposées. */
const GSTEPS = ["Trois documents", "Résultat", "Réutiliser", "Tes proches", "Papiers existants", "Kit de base", "C'est prêt"];

function guideCard() {
  const g = S.st.settings.guide || {};
  if (g.fini || g.masque) return "";
  return `<div class="card box gcard"><div class="grow"><b>Premier tri guidé · 5 minutes</b><div class="sub">Donne 3 papiers à Bon toutou et découvre ce qu'il en fait, puis prépare ton kit de base.${g.etape ? ` Tu t'étais arrêté à « ${GSTEPS[g.etape] || ""} ».` : ""}</div></div>
    <span class="acts"><button class="cta small" data-act="g-start">${g.etape ? "Reprendre" : "Commencer"}</button><button class="linkbtn" data-act="g-hide">Je me débrouille</button></span></div>`;
}
async function gSave(patch) {
  const g = Object.assign({}, S.st.settings.guide || {}, patch);
  await api("/api/settings", { guide: g });
  S.st.settings.guide = g;
}
function guideView() {
  const g = S.st.settings.guide || {}, i = g.etape || 0, G = S.guide || { kit: [], reuse: { pieces: [] }, holders: [] };
  const dots = GSTEPS.map((_, k) => `<span class="${k < i ? "d" : k === i ? "c" : ""}"></span>`).join("");
  const nav = (next = "Continuer", can = true, later = true) => `<div class="gnav">${i > 0 ? `<button class="ghost" data-act="g-prev">←</button>` : "<span></span>"}
    <button class="cta" data-act="g-next" ${can ? "" : "disabled"}>${next}</button>${later ? `<button class="linkbtn" data-act="g-next">Plus tard</button>` : "<span></span>"}</div>`;
  let body = "";
  if (i === 0) {
    const ids = S.gids || [];
    body = `<h2>Donne-moi 3 documents.</h2><p class="sub">Par exemple un avis d'impôt, une facture, une pièce d'identité. Ils sont lus sur ton ordinateur et copiés dans 00_A-TRIER : l'original ne bouge pas.</p>
      <div class="slots">${[0, 1, 2].map((k) => ids[k] ? `<div class="slot done"><b>✓ Reçu</b><small>${esc(ids[k].name)}</small></div>`
        : `<label class="slot"><input type="file" data-gslot="${k}" hidden><b>Document ${k + 1}</b><small>${S.gbusy === k ? "Lecture…" : "Touche pour choisir"}</small></label>`).join("")}</div>
      ${nav(ids.length ? `Voir ce que Bon toutou en fait (${ids.length})` : "Continuer", ids.length > 0)}`;
  }
  if (i === 1) {
    const ids = (S.gids || []).map((x) => x.id), P = (S.inbox || []).filter((p) => ids.includes(p.id));
    body = `<h2>Voilà ce que Bon toutou en fait.</h2><p class="sub">Un nom clair, une seule place. Tu n'as plus qu'à valider. Si une proposition est fausse, corrige-la dans Trier.</p>
      ${P.map((p) => `<div class="card box" style="margin-bottom:8px"><b>${esc(p.label)}</b> ${cc(p.country)} <span class="conf ${p.confidence}">${CONF[p.confidence]}</span>
        <div class="fname sub" style="text-decoration:line-through">${esc(p.orig)}</div><div class="fname"><b>${esc(p.name)}</b></div><div class="sub">→ ${esc(p.dest)}</div></div>`).join("")
        || (S.gdone ? `<div class="hint">Rangés ✓ Une seule version, au bon endroit.</div>` : `<p class="sub">Aucun document en attente.</p>`)}
      ${P.length ? `<div class="acts" style="justify-content:center;margin-top:10px"><button class="cta" data-act="g-validate">Valider les ${P.length}</button><button class="linkbtn" data-act="g-trier">Corriger dans Trier</button></div>` : ""}
      ${nav("Continuer", true, false)}`;
  }
  if (i === 2) {
    body = `<h2>Ce que Bon toutou sait déjà réutiliser.</h2><p class="sub">Tes documents peuvent servir dans n'importe quel dossier, sans copie. Un exemple : ${esc(G.reuse.label.toLowerCase())}.</p>
      <div class="card">${G.reuse.pieces.map((p) => `<div class="piece"><span class="st ${p.have ? "ok" : "missing"}">${p.have ? "✓" : "–"}</span><div class="grow"><b>${esc(p.label)}</b><div class="sub">${p.have ? "trouvé : " + esc(p.have) : "à ajouter plus tard"}</div></div></div>`).join("")}</div>
      ${nav()}`;
  }
  if (i === 3) {
    const H = S.gholders || G.holders.slice();
    S.gholders = H;
    body = `<h2>Tu gères aussi les papiers de…</h2><p class="sub">Enfants, animaux : leurs papiers seront rangés à leur nom. Personne d'autre ? Continue simplement.</p>
      <div class="card box">${H.map((h, k) => `<div class="rq"><select class="field small" data-gh-kind="${k}">${[["enfant", "Enfant"], ["animal", "Animal"], ["proche", "Autre proche"]].map(([v, l]) => `<option value="${v}" ${h.genre === v ? "selected" : ""}>${l}</option>`).join("")}</select>
          <input class="field" data-gh-nom="${k}" value="${esc(h.nom)}" placeholder="Prénom ou nom" style="flex:1"></div>`).join("")}
        <button class="linkbtn" data-act="g-addh">+ ajouter quelqu'un</button></div>
      ${nav()}`;
  }
  if (i === 4) {
    body = `<h2>Tu as déjà des papiers quelque part ?</h2><p class="sub">Choisis un dossier : Bon toutou en fait une copie dans Trier pour te proposer un rangement. Ton dossier d'origine reste intact.</p>
      <div class="acts" style="justify-content:center"><label class="ghost" style="cursor:pointer">Choisir un dossier<input type="file" id="g_dir" webkitdirectory multiple hidden></label></div>
      ${S.gdir ? `<div class="hint">${S.gdir}</div>` : ""}
      ${nav()}`;
  }
  if (i === 5) {
    const ok = G.kit.filter((k) => k.have).length;
    body = `<h2>Ton kit de base</h2><p class="sub">Ces 5 documents sont demandés dans presque toutes les démarches. Quand ils sont là, la plupart des dossiers se préparent en un clic.</p>
      <p><span class="pill ${ok === 5 ? "ok" : "acc"}">${ok === 5 ? "Kit complet ✓" : `${ok} sur 5 déjà dans ton bureau`}</span></p>
      <div class="card">${G.kit.map((k, n) => `<div class="row"><span class="st ${k.have ? "ok" : "missing"}">${k.have ? "✓" : "–"}</span><div class="grow"><b>${esc(k.label)}</b><div class="sub">${k.have ? esc(k.have) : "Demandé pour : " + esc(k.why)}</div></div>
        ${k.have ? "" : `<label class="ghost small" style="cursor:pointer">Déposer<input type="file" data-gkit="${n}" hidden></label>`}</div>`).join("")}</div>
      <p class="sub">Les documents déposés ici attendent dans Trier que tu les valides. Pas sous la main ? Continue.</p>
      ${nav()}`;
  }
  if (i === 6) {
    body = `<div style="text-align:center"><div class="bigok">✓</div><h2>Ton bureau est prêt.</h2>
      <p class="sub">Trier ce qui arrive → Documents, une seule version de chaque → Dossiers, assemblés en quelques clics.</p>
      <div class="acts" style="justify-content:center;margin-top:14px"><button class="cta" data-act="g-end">Voir mes documents</button></div>
      <p class="sub">Tes règles, la confidentialité et la synchronisation : dans Réglages, quand tu veux.</p></div>`;
  }
  return `<div class="guide"><div class="gtop"><button class="linkbtn" data-act="g-quit">Quitter le guide</button><div class="dots">${dots}</div><span class="sub">${GSTEPS[i]}</span></div>${body}</div>`;
}
async function gUpload(file) {
  const r = await (await fetch("/api/upload?name=" + encodeURIComponent(file.name), { method: "POST", body: file })).json();
  return r;
}
async function gGo(k) {
  await gSave({ etape: Math.max(0, Math.min(6, k)) });
  if (k === 1) S.inbox = await api("/api/inbox");
  S.guide = await api("/api/guide");
  window.scrollTo(0, 0); render();
}
function bindGuide() {
  if (S.v !== "guide") return;
  document.querySelectorAll("[data-gslot]").forEach((el) => (el.onchange = async () => {
    const f = el.files[0]; if (!f) return; S.gbusy = +el.dataset.gslot; render();
    const r = await gUpload(f); S.gbusy = null;
    S.gids = S.gids || [];
    if (r.id) S.gids.push({ id: r.id, name: f.name }); else toast(r.duplicate ? "Déjà reçu : ce fichier attend déjà dans Trier" : "Fichier illisible");
    render();
  }));
  document.querySelectorAll("[data-gkit]").forEach((el) => (el.onchange = async () => {
    const f = el.files[0]; if (!f) return; await gUpload(f); toast("Reçu · il t'attend dans Trier"); S.guide = await api("/api/guide"); render();
  }));
  document.querySelectorAll("[data-gh-nom],[data-gh-kind]").forEach((el) => (el.onchange = () => {
    const k = +(el.dataset.ghNom || el.dataset.ghKind);
    if (el.dataset.ghNom !== undefined) S.gholders[k].nom = el.value.trim(); else S.gholders[k].genre = el.value;
  }));
  const d = $("#g_dir"); if (d) d.onchange = async () => {
    const F = [...d.files].filter((f) => !f.name.startsWith("."));
    let n = 0; for (let k = 0; k < F.length; k++) { S.gdir = `Copie ${k + 1}/${F.length} : ${esc(F[k].name)}`; render(); const r = await gUpload(F[k]); if (r.id) n++; }
    S.gdir = `${n} fichier${n > 1 ? "s" : ""} copié${n > 1 ? "s" : ""} dans Trier · ton dossier d'origine n'a pas bougé.`; render();
  };
}
const _bindExtra = window.bindExtra;
window.bindExtra = function () { if (_bindExtra) _bindExtra(); bindGuide(); };
document.addEventListener("click", async (e) => {
  const a = e.target.closest("[data-act]"); if (!a) return;
  const act = a.dataset.act, i = ((S.st && S.st.settings && S.st.settings.guide) || {}).etape || 0;
  if (act === "g-start") { S.gids = S.gids || []; return go("guide"); }
  if (act === "g-hide") { await gSave({ masque: true }); toast("D'accord · tu peux le reprendre dans Réglages"); return load(); }
  if (act === "g-quit") { return go("trier"); }
  if (act === "g-prev") return gGo(i - 1);
  if (act === "g-next") {
    if (i === 3 && S.gholders) await api("/api/settings", { holders: S.gholders.filter((h) => h.nom) });
    return gGo(i + 1);
  }
  if (act === "g-addh") { S.gholders.push({ nom: "", genre: "enfant" }); return render(); }
  if (act === "g-validate") { const ids = (S.gids || []).map((x) => x.id); const r = await api("/api/validate", { ids }); S.gdone = r.ok; S.inbox = await api("/api/inbox"); await load(); return toast(r.ok ? `${r.done} rangé${r.done > 1 ? "s" : ""}` : "Rien à valider", r.batch); }
  if (act === "g-trier") return go("trier");
  if (act === "g-end") { await gSave({ fini: true, etape: 6 }); return go("docs"); }
});
