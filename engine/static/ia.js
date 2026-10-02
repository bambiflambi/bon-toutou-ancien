/* Bon toutou — IA locale interchangeable : la machine, les moteurs, les modèles (liste vérifiée), l'installation avec accord. */
const NIV = { modeste: "Modeste", equilibre: "Équilibré", puissant: "Puissant" };
function iaSection() {
  const st = S.st, I = st.ia || {}, M = I.machine || {}, cat = I.catalogue || { modeles: [], niveaux: {} };
  const engs = I.engines || [];
  let sel = st.settings.ai_engine || "auto";
  if (sel === "auto") sel = (engs.find((e) => e.running) || engs.find((e) => e.id === "ollama") || {}).id;
  const eng = engs.find((e) => e.id === sel) || engs[0] || {};
  const running = engs.filter((e) => e.running);
  const inst = new Set(eng.models || []), pulls = I.pulls || {};
  const known = new Set(cat.modeles.flatMap((m) => [m.ollama, (m.gguf || {}).fichier]));
  const others = (eng.models || []).filter((m) => !known.has(m));
  const row = (m) => {
    const key = eng.kind === "integre" ? (m.gguf || {}).fichier : m.ollama;   // nom du modèle pour ce moteur
    const canGet = (eng.kind === "ollama" && eng.running) || (eng.kind === "integre" && eng.running && m.gguf && m.gguf.sha256);
    const p = pulls[key], has = !!key && (inst.has(key) || inst.has(key + ":latest")), used = st.settings.ollama_model === key;
    const heavy = M.ram_go && m.memoire_go > M.ram_go;
    return `<div class="row ${m.niveau === M.niveau ? "fit" : ""}"><div class="grow"><b>${esc(m.nom)}</b>${m.conseille ? ` <span class="pill acc">conseillé</span>` : ""}${used ? ` <span class="pill ok">utilisé</span>` : ""}
      <div class="sub">${esc(m.auteur)} · ${esc(m.pays)} · ${esc(m.licence)} · ${String(m.taille_go).replace(".", ",")} Go${m.vision ? " · lit aussi les images" : ""}${heavy ? ` · <span style="color:var(--warn)">trop lourd pour ${M.ram_go} Go de mémoire</span>` : ""}</div>
      ${p && p.status === "en cours" ? `<div class="bar"><i style="width:${p.total ? Math.round((100 * p.done) / p.total) : 2}%"></i></div><div class="sub">${/verif|sha256|digest/i.test(p.etape || "") ? "vérification de l'empreinte" : "téléchargement"} · ${p.total ? Math.round((100 * p.done) / p.total) : 0} %</div>` : ""}
      ${p && p.status === "erreur" ? `<div class="sub" style="color:var(--warn)">Échec : ${esc(p.error)}</div>` : ""}
      ${S.iatest && S.iatest.model === key ? `<div class="sub">${esc(S.iatest.msg)}</div>` : (st.settings.ai_bench || {})[key] ? `<div class="sub">Mesuré sur ton ordinateur : ${String(st.settings.ai_bench[key]).replace(".", ",")} s</div>` : ""}
      ${eng.kind === "integre" && !(m.gguf && m.gguf.sha256) ? `<div class="sub">Téléchargeable avec la version publiée (empreinte fixée à la fabrication).</div>` : ""}</div>
      ${has ? `${used ? "" : `<button class="ghost small" data-act="ia-use" data-m="${esc(key)}">Utiliser</button>`}<button class="linkbtn" data-act="ia-test" data-m="${esc(key)}">Tester</button>`
        : canGet && !(p && p.status === "en cours") ? `<button class="ghost small" data-act="ia-get" data-m="${esc(m.id)}">Installer · ${String(m.taille_go).replace(".", ",")} Go</button>` : ""}</div>`;
  };
  const levels = ["modeste", "equilibre", "puissant"];
  return `<div class="label">IA locale (optionnelle)</div>
  <div class="card box"><dl class="kv"><dt>Ton ordinateur</dt><dd>${esc(M.puce || "")} · ${M.ram_go || "?"} Go de mémoire · ${M.libre_go || "?"} Go libres<br>
      <span class="pill acc">Niveau conseillé : ${NIV[M.niveau] || "?"}</span> <span class="sub">${esc((cat.niveaux[M.niveau] || {}).machine || "")}</span></dd>
    <dt>Moteur</dt><dd>${engs.map((e) => `<label class="chk"><input type="radio" name="ia_eng" value="${e.id}" ${e.id === sel ? "checked" : ""} ${e.kind === "integre" && !e.running ? "disabled" : ""}>
      <b>${esc(e.name)}</b> <span class="sub">${e.kind === "integre" && !e.running ? esc(e.later) : e.running ? `en marche · ${e.models.length} modèle${e.models.length > 1 ? "s" : ""} installé${e.models.length > 1 ? "s" : ""}` : "pas lancé"}</span></label>`).join("")}
      ${running.length ? "" : `<div class="hint">Aucun moteur d'IA ne tourne sur cet ordinateur. Le plus simple pour l'instant : installer Ollama (ollama.com), puis revenir ici. Avec l'app à télécharger, le moteur sera intégré.</div>`}
      <button class="linkbtn" data-act="ia-refresh">Relancer la détection</button></dd></dl>
    <label class="chk" style="margin-top:10px"><input type="checkbox" data-act="ollama" ${st.settings.use_ollama ? "checked" : ""}> Demander un avis à l'IA locale quand la confiance n'est pas élevée</label>
    <div style="margin-top:6px">Ce qu'elle regarde : <select class="field small" id="aimode"><option value="texte" ${st.settings.ai_mode !== "vision" ? "selected" : ""}>Le texte lu seulement (rapide)</option><option value="vision" ${st.settings.ai_mode === "vision" ? "selected" : ""}>Le texte et l'image de la page (machine puissante)</option></select></div>
    <div class="sub" style="margin-top:6px">Le moteur tourne sur ton ordinateur : aucun document ne sort. Chaque réponse de l'IA est vérifiée par Bon toutou avant d'être proposée.</div></div>
  <div class="card" style="margin-top:8px">${levels.map((l) => { const L = cat.modeles.filter((m) => m.niveau === l); return L.length ? `<div class="subhead">${NIV[l]}${l === M.niveau ? " · conseillé pour ton ordinateur" : ""}</div>${L.map(row).join("")}` : ""; }).join("")}
    ${others.length ? `<div class="subhead">Autres modèles installés · hors liste vérifiée</div>${others.map((o) => `<div class="row"><div class="grow"><b>${esc(o)}</b>${st.settings.ollama_model === o ? ` <span class="pill ok">utilisé</span>` : ""}<div class="sub">Installé par toi dans ${esc(eng.name)}. Bon toutou ne connaît pas sa provenance.</div>${S.iatest && S.iatest.model === o ? `<div class="sub">${esc(S.iatest.msg)}</div>` : ""}</div>
      ${st.settings.ollama_model === o ? "" : `<button class="ghost small" data-act="ia-use" data-m="${esc(o)}">Utiliser</button>`}<button class="linkbtn" data-act="ia-test" data-m="${esc(o)}">Tester</button></div>`).join("")}` : ""}
    <div class="bfoot"><span class="sub">Poids ouverts, licence Apache 2.0. Mistral AI est une entreprise française ; Qwen est développé par Alibaba (Chine). Dans les deux cas, le modèle tourne entièrement sur ton ordinateur.</span></div></div>`;
}
function iaEngId() { const E = S.st.ia.engines || []; const s = S.st.settings.ai_engine || "auto"; return s === "auto" ? (E.find((e) => e.running) || { id: "ollama" }).id : s; }
function iaConsent(m) {
  const M = S.st.ia.machine || {}, heavy = M.ram_go && m.memoire_go > M.ram_go;
  return `<h2>Installer ${esc(m.nom)} ?</h2>
  <p>${String(m.taille_go).replace(".", ",")} Go à télécharger. ${iaEngId() === "integre" ? "Bon toutou le télécharge depuis Hugging Face, puis vérifie son empreinte : un fichier modifié est refusé." : "Ollama va le télécharger depuis son registre (registry.ollama.ai) et vérifier lui-même l'empreinte de chaque fichier."}</p>
  <div class="hint">C'est une sortie vers internet : elle sera notée dans ton journal des sorties. <b>Aucun de tes documents n'est envoyé</b>, seul le modèle arrive.</div>
  ${heavy ? `<div class="hint" style="background:var(--warn-bg)">Ton ordinateur a ${M.ram_go} Go de mémoire : ce modèle en demande environ ${m.memoire_go}. Il risque d'être très lent.</div>` : ""}
  <div class="acts" style="margin-top:14px"><button class="cta" data-act="ia-get-ok" data-m="${esc(iaEngId() === "integre" ? m.id : m.ollama)}">Télécharger</button><button class="linkbtn" data-act="m-close">Annuler</button></div>`;
}
(function () {
  const prevModal = window.modalView;
  window.modalView = function () {
    if (S.modal && S.modal.kind === "ia") return `<div class="ov" data-act="m-close-bg"><div class="modal" role="dialog">${iaConsent(S.modal.m)}</div></div>`;
    return prevModal ? prevModal() : "";
  };
  const prevBind = window.bindExtra;
  window.bindExtra = function () {
    if (prevBind) prevBind();
    document.querySelectorAll("[name=ia_eng]").forEach((el) => (el.onchange = async () => { await api("/api/settings", { ai_engine: el.value }); load(); }));
    clearTimeout(S.iaPoll);
    const P = (S.st && S.st.ia && S.st.ia.pulls) || {};
    if (S.v === "reglages" && Object.values(P).some((p) => p.status === "en cours")) S.iaPoll = setTimeout(load, 2000);
  };
})();
document.addEventListener("click", async (e) => {
  const a = e.target.closest("[data-act]"); if (!a) return;
  const act = a.dataset.act, engs0 = (S.st && S.st.ia && S.st.ia.engines) || [];
  let eng = (S.st && S.st.settings && S.st.settings.ai_engine) || "auto"; if (eng === "auto") eng = (engs0.find((e) => e.running) || { id: "ollama" }).id;
  if (act === "ia-refresh") { await api("/api/ia?force=1"); return load(); }
  if (act === "ia-use") { await api("/api/settings", { ollama_model: a.dataset.m, use_ollama: true }); toast("Modèle choisi · l'IA locale est activée"); return load(); }
  if (act === "ia-test") { S.iatest = { model: a.dataset.m, msg: "Essai en cours… (jusqu'à 3 minutes sur un ordinateur modeste)" }; render();
    const r = await api("/api/ia/test", { engine: eng, model: a.dataset.m });
    S.iatest = { model: a.dataset.m, msg: r.ok ? `Répond en ${String(r.secondes).replace(".", ",")} s${r.meilleur < r.secondes ? ` (meilleur : ${String(r.meilleur).replace(".", ",")} s)` : ""}${r.meilleur > 60 ? " · lent : l'IA ne sera sollicitée que pour les documents « à vérifier »" : r.meilleur > 20 ? " · correct" : " · rapide"}` : `Ne répond pas (${r.erreur || "erreur"})` }; return render(); }
  if (act === "ia-get") { const m = S.st.ia.catalogue.modeles.find((x) => x.id === a.dataset.m); S.modal = { kind: "ia", m }; return render(); }
  if (act === "ia-get-ok") { const r = await api("/api/ia/pull", { engine: eng, model: a.dataset.m, consent: true }); S.modal = null; await load(); return toast(r.ok ? "Téléchargement lancé · noté dans le journal des sorties" : r.msg); }
});
