/* Bon toutou — installation (premier lancement) et mises à jour / rapport de bug (Réglages).
   L'installation ne demande que ce qui est nécessaire, une chose par écran, et dit ce qu'elle fait. */
const SSTEPS = ["Bienvenue", "Ton dossier", "Ton nom", "Tes pays", "IA locale", "Internet"];
S.su = S.su || { i: 0, path: "", owner: "", countries: ["FR"] };

function setupView() {
  const st = S.st, u = S.su, i = u.i;
  const dots = SSTEPS.map((_, k) => `<span class="${k < i ? "d" : k === i ? "c" : ""}"></span>`).join("");
  const next = (lab = "Continuer", ok = true) => `<div class="gnav">${i > 0 && i < 4 ? `<button class="ghost" data-act="su-prev">←</button>` : "<span></span>"}<button class="cta" data-act="su-next" ${ok ? "" : "disabled"}>${lab}</button><span></span></div>`;
  let b = "";
  if (i === 0) b = `<div style="text-align:center"><div class="hero-dog">${IC.dog}</div><h1 style="font-size:32px">Bienvenue dans l'application, Bon toutou</h1>
    <p class="lead" style="margin:6px auto 18px">Il sait quels documents tu as, lesquels sont valables, à quoi ils servent, et exactement ce que tu as envoyé.</p>
    <div class="versus"><div class="before"><span class="h">Avant</span><s>Carte_identite.pdf</s><br><s>Carte_identite_2.pdf</s><br><s>Carte_identite_location.pdf</s><br>Carte_identite_location_FINAL_v2.pdf</div>
      <div class="after"><span class="h">Avec Bon toutou</span>2021-06-02_FR_01_Carte-identite.pdf<br><br>Une seule, toujours la bonne.<br>Réutilisée dans chaque dossier.</div></div>
    <p class="sub">Tout reste sur ton ordinateur. Bon toutou ne détruit jamais rien.</p></div>${next("Commencer")}`;
  if (i === 1) b = `<h2>Où ranger ton dossier administratif ?</h2><p class="sub">Un seul dossier, lisible même sans Bon toutou. Choisis un dossier existant ou un nouveau : Bon toutou n'accède à rien d'autre sur ton ordinateur.</p>
    ${window.__TAURI__ ? `<div class="acts" style="margin:14px 0"><button class="ghost" data-act="su-pick">Choisir un dossier…</button></div>` : ""}
    <input class="field" id="su_path" style="width:100%" value="${esc(u.path || st.suggest)}">
    <p class="sub">Si le dossier contient déjà des papiers, Bon toutou n'y touche pas : il ajoute seulement ses propres dossiers à côté, et ce que tu lui confies passe par Trier.</p>
    ${u.err ? `<div class="hint">${esc(u.err)}</div>` : ""}${next()}`;
  if (i === 2) b = `<h2>Comment t'appelles-tu ?</h2><p class="sub">Tu es le titulaire par défaut de tes papiers. Ton nom est ajouté au nom de tes pièces d'identité, santé, diplômes. Il reste sur ton ordinateur.</p>
    <input class="field" id="su_owner" style="width:100%" placeholder="Prénom Nom" value="${esc(u.owner)}">${next()}`;
  if (i === 3) b = `<h2>Tes papiers viennent de quels pays ?</h2><p class="sub">Chaque pays a ses dossiers, ses organismes et ses règles. Tu pourras en ajouter plus tard.</p>
    <div class="privgrid" style="margin:14px 0">${Object.entries(st.countries).map(([k, v]) => `<label class="chk"><input type="checkbox" data-su-cc="${k}" ${u.countries.includes(k) ? "checked" : ""}> <b>${k}</b> ${esc(v)}</label>`).join("")}</div>
    ${u.err ? `<div class="hint">${esc(u.err)}</div>` : ""}${next("Créer mon dossier", u.countries.length > 0)}`;
  if (i === 4) {
    const I = st.ia || {}, M = I.machine || {}, cat = (I.catalogue || {}).modeles || [], m = cat.find((x) => x.niveau === M.niveau && x.conseille) || cat[0] || {};
    const E = I.engines || [], integ = E.find((e) => e.id === "integre" && e.running), oll = E.find((e) => e.id === "ollama" && e.running);
    const can = (integ && m.gguf && m.gguf.sha256) || oll;
    b = `<h2>Une IA locale pour t'aider à trier ?</h2><p class="sub">Facultatif : les règles de Bon toutou suffisent pour commencer. L'IA locale aide pour les papiers inhabituels. Elle tourne sur ton ordinateur : aucun document ne sort.</p>
      <div class="card box"><b>Ton ordinateur</b> : ${esc(M.puce || "")} · ${M.ram_go || "?"} Go de mémoire<br>
        <span class="pill acc">Niveau conseillé : ${({ modeste: "Modeste", equilibre: "Équilibré", puissant: "Puissant" })[M.niveau] || "?"}</span>
        <p style="margin:10px 0 0"><b>${esc(m.nom || "")}</b> · ${esc(m.auteur || "")} (${esc(m.pays || "")}) · ${esc(m.licence || "")} · ${String(m.taille_go || "").replace(".", ",")} Go</p></div>
      ${u.dl ? `<div class="hint">${esc(u.dl)}</div>` : ""}
      <div class="acts" style="justify-content:center;margin-top:16px">
        ${can ? `<button class="cta" data-act="su-ia-get" data-m="${esc(integ ? m.id : m.ollama)}" data-e="${integ ? "integre" : "ollama"}">Télécharger maintenant</button>` : ""}
        <button class="ghost" data-act="su-ia-later">Plus tard</button><button class="linkbtn" data-act="su-ia-never">Jamais</button></div>
      ${can ? `<p class="sub" style="text-align:center">Le téléchargement est la seule sortie vers internet de l'installation. Il sera noté dans ton journal des sorties.</p>`
        : `<p class="sub" style="text-align:center">Aucun moteur d'IA n'est encore disponible ici : tu pourras l'installer depuis Réglages › IA locale.</p>`}`;
  }
  if (i === 5) b = `<h2>Bon toutou ne se connecte jamais à internet sauf si tu le demandes.</h2>
    <div class="card box"><b>Les seules exceptions possibles, toujours avec ton accord :</b>
      <div class="row" style="padding-left:0"><span>🔄</span><div class="grow"><b>Vérifier les mises à jour</b><div class="sub">Une requête vers la page publique de Bon toutou. Jamais obligatoire.</div></div></div>
      <div class="row" style="padding-left:0"><span>🧠</span><div class="grow"><b>Télécharger un modèle d'IA</b><div class="sub">Seulement si tu le demandes, fichier vérifié par son empreinte.</div></div></div>
      <div class="row" style="padding-left:0"><span>☁</span><div class="grow"><b>IA externe</b><div class="sub">Désactivée. Si un jour tu l'actives : seulement pour les catégories que tu autorises, numéros masqués.</div></div></div>
      <div class="row" style="padding-left:0"><span>🐞</span><div class="grow"><b>Rapport de bug</b><div class="sub">Volontaire, relu par toi avant l'envoi, sans aucun document.</div></div></div></div>
    <p class="sub">Chaque sortie est notée avant de partir dans Réglages › Journal des sorties.</p>
    <label class="chk"><input type="checkbox" id="su_maj" ${u.maj ? "checked" : ""}> Vérifier les mises à jour toute seule, une fois par semaine</label>
    <div class="gnav"><span></span><button class="cta" data-act="su-done">C'est prêt : commencer à trier</button><span></span></div>`;
  return `<div class="guide"><div class="gtop"><span class="sub">Installation</span><div class="dots">${dots}</div><span class="sub">${SSTEPS[i]}</span></div>${b}</div>`;
}

function openExternal(url) {
  const T = window.__TAURI__;
  if (T && T.opener && T.opener.openUrl) return T.opener.openUrl(url);
  window.open(url, "_blank");
}
function majSection() {
  const st = S.st, m = S.maj;
  return `<div class="label">Version et mises à jour</div>
  <div class="card box"><b>Bon toutou ${esc(st.version || "")}</b> <span class="sub">· code public, licence AGPL-3.0</span>
    <p class="sub">Les mises à jour ne sont jamais obligatoires. Vérifier envoie une seule requête à la page publique de Bon toutou, notée dans le journal des sorties.</p>
    <div class="acts"><button class="ghost small" data-act="maj-check">Vérifier les mises à jour</button>
      <label class="chk"><input type="checkbox" id="maj_auto" ${st.settings.maj_auto ? "checked" : ""}> toute seule, une fois par semaine</label></div>
    ${m ? (!m.ok ? `<div class="hint">${esc(m.msg)}</div>` : !m.nouvelle ? `<div class="hint">Tu as la dernière version (${esc(m.installee)}).</div>`
      : `<div class="hint" style="${m.important ? "background:var(--bad-bg)" : ""}"><b>${m.important ? "Important : corrige une faille · " : ""}Version ${esc(m.derniere)} disponible</b>
          <div style="white-space:pre-wrap;margin:6px 0">${esc(m.notes)}</div>
          <div class="acts"><button class="cta small" data-act="maj-open">Télécharger</button><button class="linkbtn" data-act="maj-later">Plus tard</button></div>
          <div class="sub">Tes documents ne sont jamais touchés par une mise à jour. L'ancienne version reste disponible sur la même page.</div></div>`) : ""}</div>
  <div class="label">Signaler un problème</div>
  <div class="card box"><span class="sub">Prépare un rapport sans aucun document ni nom de fichier, que tu relis avant de décider de l'envoyer.</span>
    <div class="acts" style="margin-top:8px"><button class="ghost small" data-act="bug-open">Préparer un rapport</button></div></div>`;
}
function bugModal(m) {
  const r = m.r;
  return `<h2>Rapport de problème</h2><p class="sub">${esc(r ? r.rappel : "Préparation…")}</p>
  ${r ? `<p class="sub">Décris en une phrase ce qui s'est passé, puis relis tout :</p>
    <textarea class="field mono" id="bug_txt" rows="12">Ce qui s'est passé : \n\n${esc(r.text)}</textarea>
    ${r.masque.length ? `<div class="sub">Masqué automatiquement : ${esc(r.masque.join(", "))}</div>` : ""}
    <div class="acts" style="margin-top:12px"><button class="cta" data-act="bug-copy">Copier</button>
      ${r.issue ? `<button class="ghost" data-act="bug-issue">Ouvrir un ticket public…</button>` : ""}${r.mailto ? `<button class="ghost" data-act="bug-mail">Envoyer par e-mail</button>` : ""}
      <button class="linkbtn" data-act="m-close">Annuler</button></div>
    ${r.issue ? `<p class="sub">Un ticket public est visible par tout le monde sur GitHub : n'y mets rien de personnel.</p>` : ""}` : ""}`;
}
(function () {
  const prevModal = window.modalView;
  window.modalView = function () {
    if (S.modal && S.modal.kind === "bug") return `<div class="ov" data-act="m-close-bg"><div class="modal" role="dialog">${bugModal(S.modal)}</div></div>`;
    return prevModal ? prevModal() : "";
  };
  const prevBind = window.bindExtra;
  window.bindExtra = function () {
    if (prevBind) prevBind();
    const p = $("#su_path"); if (p) p.oninput = () => (S.su.path = p.value);
    const o = $("#su_owner"); if (o) o.oninput = () => (S.su.owner = o.value);
    document.querySelectorAll("[data-su-cc]").forEach((el) => (el.onchange = () => {
      S.su.countries = [...document.querySelectorAll("[data-su-cc]:checked")].map((x) => x.dataset.suCc); render(); }));
    const mj = $("#su_maj"); if (mj) mj.onchange = () => (S.su.maj = mj.checked);
    const ma = $("#maj_auto"); if (ma) ma.onchange = async () => { await api("/api/settings", { maj_auto: ma.checked }); toast(ma.checked ? "Vérification hebdomadaire activée" : "Vérification automatique désactivée"); load(); };
    // vérification hebdomadaire, seulement si tu l'as demandée
    const st = S.st;
    if (st && !st.setup && st.settings.maj_auto && !S.majAutoDone) {
      S.majAutoDone = true;
      const last = Date.parse(st.settings.maj_last || 0) || 0;
      if (Date.now() - last > 7 * 864e5) api("/api/maj/check", { consent: true }).then(async (r) => {
        await api("/api/settings", { maj_last: new Date().toISOString() });
        if (r.ok && r.nouvelle) { S.maj = r; toast(`Bon toutou ${r.derniere} est disponible · voir Réglages`); }
      });
    }
  };
})();
document.addEventListener("click", async (e) => {
  const a = e.target.closest("[data-act]"); if (!a) return;
  const act = a.dataset.act, u = S.su;
  if (act === "su-prev") { u.i--; u.err = ""; return render(); }
  if (act === "su-pick") {
    try { const d = await window.__TAURI__.dialog.open({ directory: true, multiple: false, title: "Ton dossier administratif" }); if (d) { u.path = d; render(); } } catch (x) { u.err = "Sélecteur indisponible : écris le chemin."; render(); }
  }
  if (act === "su-next") {
    u.err = "";
    if (u.i === 1 && !(u.path || S.st.suggest)) return;
    if (u.i === 1 && !u.path) u.path = S.st.suggest;
    if (u.i === 3) {
      const r = await api("/api/setup", { path: u.path, owner: u.owner, countries: u.countries });
      if (!r.ok) { u.err = r.msg; u.i = 1; return render(); }
      S.st = await api("/api/state"); S.setupDone = true;
    }
    u.i++; return render();
  }
  if (act === "su-ia-get") {
    const r = await api("/api/ia/pull", { engine: a.dataset.e, model: a.dataset.m, consent: true });
    if (r.ok) { await api("/api/settings", { ai_engine: a.dataset.e, use_ollama: true }); u.dl = "Téléchargement lancé en arrière-plan : tu peux continuer. Choisis le modèle dans Réglages › IA locale quand il est prêt."; }
    else u.dl = r.msg;
    u.i++; return render();
  }
  if (act === "su-ia-later") { u.i++; return render(); }
  if (act === "su-ia-never") { await api("/api/settings", { ai_never: true, use_ollama: false }); u.i++; return render(); }
  if (act === "su-done") { await api("/api/settings", { maj_auto: !!u.maj }); S.v = "trier"; return load(); }
  if (act === "maj-check") { S.maj = { ok: false, msg: "Vérification…" }; render(); S.maj = await api("/api/maj/check", { consent: true }); await api("/api/settings", { maj_last: new Date().toISOString() }); return load(); }
  if (act === "maj-later") { S.maj = null; return render(); }
  if (act === "bug-open") { S.modal = { kind: "bug" }; render(); S.modal.r = await api("/api/bug", {}); return render(); }
  if (act === "bug-copy") { const t = $("#bug_txt").value; try { await navigator.clipboard.writeText(t); } catch (x) { /* sélection manuelle */ }
    await api("/api/bug/sent", { dest: "copié pour envoi manuel", bytes: t.length }); return toast("Copié"); }
  if (act === "bug-issue") { const t = $("#bug_txt").value; await api("/api/bug/sent", { dest: "github.com (ticket public)", bytes: t.length });
    openExternal(S.modal.r.issue + "?title=" + encodeURIComponent("Problème") + "&body=" + encodeURIComponent(t)); }
  if (act === "bug-mail") { const t = $("#bug_txt").value; await api("/api/bug/sent", { dest: "ta messagerie", bytes: t.length });
    openExternal(S.modal.r.mailto + "?subject=" + encodeURIComponent("Problème Bon toutou") + "&body=" + encodeURIComponent(t)); }
  if (act === "maj-open" && S.maj && S.maj.page) openExternal(S.maj.page);
});
