/* Bon toutou — Réglages, compartimentés : une liste, une page par sujet, et « Aller plus loin » (la suite de l'accueil).
   Les fonctions bientôt disponibles sont montrées honnêtement : rien n'est simulé. */
const noLabel = (h) => String(h || "").replace(/^\s*<div class="label">[^<]*<\/div>/, "");
const has = (k) => ((S.st.settings.plus_done || []).includes(k));
const SOON = [
  ["imap", "mail", "Relève automatique de l'adresse admin", "Tes papiers arrivent seuls dans Trier, lus sur ton ordinateur"],
  ["agenda", "calendar", "Abonnement à ton agenda", "Les échéances apparaissent toutes seules dans Calendrier, Google Agenda ou Outlook"],
  ["contacts", "name", "Contacts complets", "Coordonnées, notes et historique de chaque interlocuteur"],
  ["auto", "globe", "Récupération sur les sites des organismes", "Mot de passe dans le trousseau de ton ordinateur, jamais vu par l'IA"],
  ["save", "drive", "Sauvegarde automatique", "Une copie de ton bureau sur un disque ou un NAS"],
  ["cont", "heart", "Accès d'urgence pour une personne de confiance", "Elle demande, tu es prévenu, tu peux refuser"],
  ["bilan", "chip", "Bilan de tes dépenses", "Lu dans tes factures et relevés, sur ton ordinateur"]];

function plusSteps() {
  const st = S.st, s = st.settings, O = st.orgs || [];
  return [
    { id: "mail", lvl: 1, ic: "mail", t: "Choisir ton adresse admin", short: "adresse admin", s: "Une adresse rien que pour l'administratif : tes papiers arrivent au même endroit", min: 3, done: !!s.mail || has("mail"), sv: "mail" },
    { id: "existing", lvl: 1, ic: "folder", t: "Importer tes papiers existants", short: "importer", s: "Bon toutou en fait une copie dans Trier et propose un rangement : l'original ne bouge pas", min: 5, done: has("existing") || st.counts.docs >= 10, go: "trier" },
    { id: "orgs", lvl: 1, ic: "building", t: "Prévenir tes organismes", short: "organismes", s: `Impôts, assurance maladie, banque… ${(s.orgs_done || []).length}/${O.length} prévenus`, min: 15, done: has("orgs") || (O.length > 0 && (s.orgs_done || []).length >= O.length), sv: "orgs" },
    { id: "cal", lvl: 1, ic: "calendar", t: "Mettre tes échéances dans ton agenda", short: "agenda", s: "Un fichier .ics avec un rappel 30 jours avant chaque date", min: 1, done: has("cal"), sv: "calendrier" },
    { id: "priv", lvl: 2, ic: "lock", t: "Régler ta confidentialité", short: "confidentialité", s: "Catégorie par catégorie : ce qui ne quitte jamais ton ordinateur", min: 2, done: has("priv"), sv: "priv" },
    { id: "family", lvl: 2, ic: "kids", t: "Ajouter tes proches", short: "proches", s: "Enfants, animaux : leurs papiers rangés à leur nom", min: 2, done: (s.holders || []).length > 0 || has("family"), sv: "profil" },
    { id: "ia", lvl: 2, ic: "sparkles", t: "Installer l'IA locale", short: "IA locale", s: "Pour les papiers inhabituels. Elle tourne sur ton ordinateur", min: 5, done: !!(s.use_ollama && s.ollama_model) || has("ia"), sv: "ia" },
    { id: "cont", lvl: 2, ic: "heart", t: "Préparer la continuité", short: "continuité", s: "Une personne de confiance pour retrouver l'essentiel", min: 5, done: !!s.trusted || has("cont"), sv: "cont" }];
}
const REG = [
  ["Toi", [["profil", "user", "Profil", () => `${S.st.settings.owner || "Ton nom"} · ${S.st.settings.countries.join(", ")}${(S.st.settings.holders || []).length ? ` · ${S.st.settings.holders.length} ${plural(S.st.settings.holders.length, "proche")}` : ""}`],
           ["priv", "lock", "Confidentialité", () => `${S.st.counts.egress} ${plural(S.st.counts.egress, "sortie")} de ton ordinateur · niveaux par catégorie`],
           ["apparence", "palette", "Apparence", () => (THEMES.find((t) => t[0] === (S.st.settings.theme || "champagne")) || THEMES[0])[1]]]],
  ["Ce qui arrive et ce qui part", [["mail", "mail", "Adresse admin", () => S.st.settings.mail ? `Choisie : ${S.st.settings.mail}` : "Pas encore choisie", "relève bientôt"],
           ["calendrier", "calendar", "Calendrier", () => `${(S.st.events || []).filter((e) => !e.past).length} échéances · export .ics`],
           ["contacts", "name", "Contacts", () => "Aperçu à partir de tes documents et dossiers", "bientôt"],
           ["orgs", "building", "Organismes", () => `Checklist pour donner ta nouvelle adresse · ${(S.st.settings.orgs_done || []).length}/${(S.st.orgs || []).length}`]]],
  ["Comment Bon toutou lit tes papiers", [["ia", "sparkles", "IA locale", () => S.st.settings.use_ollama && S.st.settings.ollama_model ? `Activée · ${S.st.settings.ollama_model}` : "Facultative · tourne sur ton ordinateur"],
           ["lecture", "eye", "Lecture des documents", () => { const T = S.st.tools; return `PDF ${T.pypdf || T.pdftotext ? "✓" : "✗"} · scans et photos ${T.apple_vision || T.tesseract ? "✓" : "✗"}`; }],
           ["regles", "tag", "Mes règles et catalogue", () => `${((S.rules || {}).rules || []).length} ${plural(((S.rules || {}).rules || []).length, "règle")} · ${(S.st.packs || []).length} packs`]]],
  ["Sécurité et continuité", [["save", "drive", "Sauvegarde", () => "Ton dossier est fait de fichiers ordinaires", "bientôt"],
           ["cont", "heart", "Continuité", () => S.st.settings.trusted ? `Personne de confiance : ${S.st.settings.trusted}` : "Personne de confiance et accès d'urgence", "bientôt"],
           ["sync", "sync", "Synchronisation et index", () => `Cet appareil : ${(S.st.device || {}).name || ""}`],
           ["hist", "history", "Historique des actions", () => "Tout ce que Bon toutou a fait, annulable"]]],
  ["Bon toutou", [["maj", "up", "Version et mises à jour", () => `v${S.st.version || ""} · jamais obligatoires`],
           ["bug", "bug", "Signaler un problème", () => "Sans aucun document, relu par toi avant l'envoi"],
           ["accueil", "spark", "Premier tri guidé", () => (S.st.settings.guide || {}).fini ? "Terminé · le refaire" : "5 minutes avec tes propres papiers"]]]];

function setHead(ic, title, lead) {
  return `<div class="navline"><button class="back" data-go="reglages">← Réglages</button></div>
  <div class="settop"><span class="oi">${IC[ic]}</span><h1>${title}</h1></div>${lead ? `<p class="lead">${lead}</p>` : ""}`;
}
function soonCard(id, txt) {
  const on = (S.st.settings.notify || []).includes(id);
  return `<div class="card soonrow" style="border-top:1px solid var(--border-light)"><span class="pst" style="width:34px;height:34px;border-radius:10px;display:grid;place-items:center;background:var(--border-light);color:var(--text-tertiary)">${IC.clock}</span>
    <div class="grow"><b>${esc(txt)}</b> <span class="soontag">bientôt</span><div class="sub">Noté sur ton ordinateur seulement : quand une mise à jour l'apporte, Bon toutou te le signale.</div></div>
    <button class="ghost small${on ? " on" : ""}" data-notify="${id}">${on ? "✓ Ça m'intéresse" : "Ça m'intéresse"}</button></div>`;
}

function reglagesView() {
  const st = S.st, s = st.settings, sv = S.sv;
  if (sv === "plus") {
    const P = plusSteps(), dn = P.filter((x) => x.done).length, nx = P.find((x) => !x.done);
    const goAttr = (x) => x.sv ? `data-go="reglages" data-sv="${x.sv}"` : `data-go="${x.go}"`;
    const row = (x) => `<div class="pstep${x.done ? " done" : ""}"><span class="pst">${x.done ? "✓" : IC[x.ic]}</span><div class="grow"><b>${esc(x.t)}</b><small>${esc(x.s)}${x.min && !x.done ? ` · ${x.min} min` : ""}</small></div>
      ${x.done ? `<button class="linkbtn" ${goAttr(x)}>revoir</button>` : `<button class="cta small" ${goAttr(x)}>Commencer</button><button class="linkbtn" data-plus="${x.id}">c'est fait</button>`}</div>`;
    const grp = (t, L) => (L.length ? `<div class="label" style="margin:20px 0 8px">${t}</div><div class="card">${L.map(row).join("")}</div>` : "");
    return `${setHead("sparkles", "Aller plus loin", "La suite de ton accueil, une étape à la fois. Rien n'est obligatoire : fais ce qui t'aide, quand tu veux.")}
    <div class="card pprog"><div class="grow"><b>${dn} sur ${P.length} étapes faites</b><div class="bar ${dn === P.length ? "ok" : ""}" style="margin-top:8px"><i style="width:${Math.round((dn / P.length) * 100)}%"></i></div></div>
      ${nx ? `<button class="cta" ${goAttr(nx)}>Étape suivante : ${esc(nx.short)}</button>` : `<span class="pill ok">Tout est en place</span>`}</div>
    ${grp("Recommandé", P.filter((x) => x.lvl === 1))}${grp("Quand tu veux", P.filter((x) => x.lvl === 2))}
    <div class="label" style="margin:20px 0 8px">Bientôt disponible</div><div class="card">${SOON.map((x) => { const on = (s.notify || []).includes(x[0]);
      return `<div class="pstep soon"><span class="pst">${IC.clock}</span><div class="grow"><b>${esc(x[2])}</b><small>${esc(x[3])}</small></div><button class="ghost small${on ? " on" : ""}" data-notify="${x[0]}">${on ? "✓ Ça m'intéresse" : "Ça m'intéresse"}</button></div>`; }).join("")}</div>
    <p class="sub" style="margin-top:10px">« Ça m'intéresse » reste sur ton ordinateur : Bon toutou ne collecte rien. Les nouveautés arrivent avec les mises à jour, que tu choisis d'installer.</p>`;
  }
  if (sv === "profil") {
    const H = S.hEdit || (S.hEdit = (s.holders || []).map((h) => Object.assign({}, h)));
    return `${setHead("user", "Profil", "Ce que Bon toutou sait de toi. Ça reste dans ton dossier, sur ton ordinateur.")}
    <div class="card box"><dl class="kv"><dt>Ton nom</dt><dd><input class="field" id="owner" value="${esc(s.owner || "")}" placeholder="Prénom Nom" style="width:min(280px,100%)"><div class="sub" style="margin-top:4px">Titulaire par défaut, ajouté au nom de tes pièces d'identité, santé, diplômes.</div></dd>
      <dt>Tes pays</dt><dd>${Object.entries(st.countries).map(([k, v]) => `<label class="chk" style="display:inline-flex;margin-right:16px"><input type="checkbox" data-country="${k}" ${s.countries.includes(k) ? "checked" : ""}> ${cc(k)} ${esc(v)}</label>`).join("")}
        <div class="sub">Chaque pays a ses dossiers, ses organismes et ses échéances.</div></dd></dl></div>
    <div class="label" style="margin:22px 0 8px">Tes proches</div>
    <div class="card box"><p class="sub" style="margin-top:0">Enfants, animaux, parent dont tu t'occupes : leurs papiers seront rangés à leur nom.</p>
      ${H.map((h, k) => `<div class="rq"><select class="field small" data-hk="${k}">${[["enfant", "Enfant"], ["animal", "Animal"], ["proche", "Autre proche"]].map(([v, l]) => `<option value="${v}" ${h.genre === v ? "selected" : ""}>${l}</option>`).join("")}</select>
        <input class="field" data-hn="${k}" value="${esc(h.nom)}" placeholder="Prénom ou nom" style="flex:1"><button class="linkbtn" data-act="h-rm" data-k="${k}">retirer</button></div>`).join("") || `<div class="sub">Personne pour l'instant.</div>`}
      <div class="acts" style="margin-top:10px"><button class="ghost small" data-act="h-add">+ Ajouter quelqu'un</button><button class="cta small" data-act="h-save">Enregistrer</button></div></div>`;
  }
  if (sv === "priv") {
    const P = s.privacy || {}, E = st.sorties || [];
    return `${setHead("lock", "Confidentialité", "Chaque catégorie a son niveau. C'est toi qui décides, pas l'IA. Un document pas encore trié est toujours « Local uniquement ».")}
    <div class="card egress"><span class="oi">${IC.lock}</span><div class="grow"><b>Journal des sorties</b><small>Chaque fois que Bon toutou se connecte à internet (avec ton accord), c'est noté ici avant de partir : quoi, quand, vers où.</small></div><div class="egn"><b>${st.counts.egress}</b><small>${plural(st.counts.egress, "sortie")}</small></div></div>
    ${E.length ? `<div class="card" style="margin-bottom:16px">${E.map((e) => `<div class="row"><div class="grow"><b>${esc(e.label)}</b>${e.what ? " · " + esc(e.what) : ""}<div class="sub">${esc(e.ts.replace("T", " "))} · vers ${esc(e.dest)}</div></div></div>`).join("")}</div>` : ""}
    <div class="legend">${Object.values(LVL).map((L) => `<div class="${L[0]}"><b><span class="lvi">${LVI[L[0]]}</span>${L[1]}</b>${L[2]}</div>`).join("")}</div>
    <div class="card" style="margin-bottom:16px"><div class="switch"><span class="oi">${IC.cloud}</span><div class="grow"><b>IA externe <span class="soontag">bientôt</span></b><div class="sub">Désactivée : tout est lu sur ton ordinateur. Si elle arrive, ce sera seulement pour les catégories que tu autorises ci-dessous, numéros masqués, et avec un fournisseur sans conservation des données.</div></div><button class="tog" disabled aria-label="IA externe (bientôt)"></button></div></div>
    <div class="card"><div class="row seghead"><div class="grow label" style="margin:0">Catégorie</div><span class="label" style="margin:0">Analyse par une IA extérieure</span></div>
      ${Object.entries(st.categories).sort((a, b) => a[0].localeCompare(b[0])).map(([c, l]) => `<div class="row"><span class="oi" style="width:30px;height:30px">${catIc(c)}</span><div class="grow"><b>${esc(l)}</b></div>
        <div class="seg">${Object.entries(LVL).map(([k, L]) => `<button class="${L[0]}${(P[c] || "local") === k ? " on" : ""}" data-lv="${c}" data-l="${k}" aria-label="${L[1]}">${LVI[L[0]]}${k === "local" ? "Non" : k === "autorisation" ? "Sur autorisation" : "Oui"}</button>`).join("")}</div></div>`).join("")}</div>
    <details class="why" style="margin-top:16px" ${S.mk || S.mkIn ? "open" : ""}><summary>Essayer le masquage</summary>
      <p class="sub">Avant tout envoi, les numéros sensibles sont remplacés : IBAN, carte, sécurité sociale, passeport, n° fiscal, téléphone, e-mail.</p>
      <textarea class="field" id="mk_in" rows="3" placeholder="Colle un texte, ex. IBAN FR76 3000… · tél 06 12 34 56 78">${esc(S.mkIn || "")}</textarea>
      ${S.mk ? `<div class="hint"><b>Ce qui partirait :</b><br>${esc(S.mk.text)}${S.mk.found.length ? `<br><span class="sub">Masqué : ${esc(S.mk.found.join(", "))}</span>` : ""}</div>` : ""}
      <button class="ghost small" data-act="mk">Voir ce qui partirait</button></details>`;
  }
  if (sv === "apparence") return `${setHead("palette", "Apparence", "Trois ambiances, pour cet appareil seulement.")}
    <div class="themes">${THEMES.map((t) => `<button class="theme-opt${(s.theme || "champagne") === t[0] ? " on" : ""}" data-theme="${t[0]}"><i class="sw ${t[2]}"></i>${t[1]}</button>`).join("")}</div>`;
  if (sv === "mail") return `${setHead("mail", "Adresse admin", "Une adresse e-mail rien que pour l'administratif : impôts, banque, assurances, employeur. Tes papiers arrivent au même endroit, séparés de tes mails perso.")}
    <div class="card box"><div class="fieldwrap" style="max-width:460px"><span class="oi">${IC.mail}</span><input id="mail_in" type="email" value="${esc(s.mail || "")}" placeholder="admin@mon-domaine.fr" aria-label="Adresse admin"></div>
      <div class="acts" style="margin-top:10px"><button class="cta small" data-act="mail-save">Enregistrer</button>${s.mail ? `<button class="linkbtn" data-act="mail-clear">retirer</button>` : ""}</div>
      <p class="sub">Elle est notée dans ton dossier, sur ton ordinateur. Bon toutou ne s'y connecte pas.</p></div>
    <div class="label" style="margin:22px 0 8px">En attendant la relève automatique</div>
    <div class="card"><div class="row"><span class="oi">${IC.up}</span><div class="grow"><b>Glisse les pièces jointes dans Trier</b><div class="sub">Depuis ta messagerie, enregistre les PDF reçus puis dépose-les : Bon toutou les lit et propose un rangement.</div></div><button class="ghost small" data-go="trier">Trier</button></div>
      <div class="row"><span class="oi">${IC.building}</span><div class="grow"><b>Donne cette adresse à tes organismes</b><div class="sub">Une checklist avec les liens officiels, à ton rythme.</div></div><button class="ghost small" data-go="reglages" data-sv="orgs">Organismes</button></div></div>
    <div style="margin-top:10px">${soonCard("imap", "Relève automatique : les pièces jointes arrivent seules dans Trier")}</div>
    <p class="sub" style="margin-top:10px">Quand elle arrivera : connexion directe de ton ordinateur à ta boîte (IMAP), mot de passe gardé dans le trousseau de ton système, rien ne passe par un serveur Bon toutou.</p>`;
  if (sv === "calendrier") { const ev = (st.events || []).filter((e) => !e.past);
    return `${setHead("calendar", "Calendrier", "Les dates lues dans tes documents et les échéances de tes pays, dans l'agenda que tu utilises déjà.")}
    <div class="card box"><b>Ajouter à ton agenda</b><p class="sub" style="margin:4px 0 10px">Un fichier .ics avec ${ev.length} ${plural(ev.length, "échéance")} et un rappel 30 jours avant chacune. Ouvre-le : Calendrier (Mac), Google Agenda ou Outlook l'importent. Il est créé sur ton ordinateur, rien ne sort.</p>
      <div class="acts"><button class="cta small" data-act="ics-dl">${IC.calendar} Ajouter à mon calendrier</button><button class="ghost small" data-go="cal">Voir le calendrier</button></div>
      <p class="sub" style="margin-bottom:0">Après un nouveau document avec une date d'expiration, télécharge-le à nouveau : les dates déjà importées ne sont pas dupliquées.</p></div>
    <div class="label" style="margin:22px 0 8px">Ce qu'il contient</div>
    <div class="card">${ev.slice(0, 8).map((e) => `<div class="row">${cc(e.cc)}<div class="grow"><b>${esc(e.t)}</b><div class="sub">${e.k} · ${frd(e.d)}${e.note ? " · " + esc(e.note) : ""}</div></div></div>`).join("") || `<div class="row sub">Aucune date pour l'instant.</div>`}${ev.length > 8 ? `<div class="row sub">… et ${ev.length - 8} autres</div>` : ""}</div>
    <div style="margin-top:10px">${soonCard("agenda", "Abonnement : ton agenda se met à jour tout seul")}</div>`; }
  if (sv === "contacts") return `${setHead("name", "Contacts", "Tes interlocuteurs et ce que tu leur as transmis.")}
    <div class="card box"><b>Aperçu disponible</b><p class="sub" style="margin:4px 0 10px">Construit à partir des émetteurs de tes documents et des destinataires de tes dossiers. Rien n'est importé de ton carnet d'adresses.</p><button class="ghost small" data-go="contacts">Voir l'aperçu</button></div>
    <div style="margin-top:10px">${soonCard("contacts", "Contacts complets : coordonnées, notes, import d'un carnet (.vcf)")}</div>`;
  if (sv === "orgs") { const O = st.orgs || [], D = s.orgs_done || [];
    return `${setHead("building", "Organismes", "Facultatif : donne ta nouvelle adresse (ou ton adresse admin) aux organismes, à ton rythme. Les liens ouvrent le site officiel dans ton navigateur.")}
    <div class="card pprog" style="margin-bottom:12px"><div class="grow"><b>${D.length} sur ${O.length} prévenus</b><div class="bar ${D.length >= O.length ? "ok" : ""}"><i style="width:${O.length ? Math.round((D.length / O.length) * 100) : 0}%"></i></div></div></div>
    ${st.settings.countries.map((c) => { const L = O.filter((o) => o.cc === c); return L.length ? `<div class="label" style="margin:18px 0 8px">${cc(c)} ${esc(st.countries[c])}</div><div class="card">${L.map((o) => { const k = c + ":" + o.nom, dn = D.includes(k) || D.includes(o.nom);
      return `<label class="row orgrow${dn ? " done" : ""}" style="cursor:pointer"><input type="checkbox" data-org="${esc(k)}" ${dn ? "checked" : ""}><div class="grow"><b>${esc(o.nom)}</b><div class="sub">${esc(o.note)}</div></div>${o.url ? `<button class="ghost small" data-ext="${esc(o.url)}">Ouvrir ↗</button>` : `<span class="sub">ton espace client</span>`}</label>`; }).join("")}</div>` : ""; }).join("")}
    <p class="sub" style="margin-top:12px">Cocher reste sur ton ordinateur. Bon toutou ne se connecte pas à ces sites.</p>`; }
  if (sv === "ia") return `${setHead("sparkles", "IA locale", "Facultative : les règles de Bon toutou suffisent pour commencer. L'IA locale aide pour les papiers inhabituels, sans qu'aucun document ne sorte.")}${window.iaSection ? noLabel(iaSection()) : ""}`;
  if (sv === "lecture") { const T = st.tools, readOk = T.pypdf || T.pdftotext;
    return `${setHead("eye", "Lecture des documents", "Comment Bon toutou lit le texte de tes papiers, sur ton ordinateur.")}
    <div class="card box"><dl class="kv"><dt>Texte des PDF</dt><dd>${readOk ? "✓ disponible" : "✗ pas encore"} ${T.pypdf ? "(pypdf)" : T.pdftotext ? "(pdftotext)" : ""}</dd><dt>Scans et photos (OCR)</dt><dd>${T.apple_vision ? "✓ lecture de texte d'Apple (intégrée à macOS)" : T.tesseract ? "✓ disponible (tesseract)" : "✗ pas encore"}</dd></dl>
    ${!readOk || !(T.tesseract || T.apple_vision) ? `<div class="hint">Sans ces outils, Bon toutou ne lit que le nom des fichiers. Pour lire le contenu, dans le Terminal :<br>
      ${!readOk ? `<code>python3 -m pip install --user pypdf</code><br>` : ""}${!T.tesseract && !T.apple_vision ? `<code>brew install tesseract tesseract-lang poppler</code> (Homebrew : brew.sh)` : ""}</div>` : ""}</div>
    <div class="label" style="margin:22px 0 8px">Émetteurs</div>
    <div class="card box"><b>${st.unknown_emitters ? `${st.unknown_emitters} ${plural(st.unknown_emitters, "document rangé")} sans émetteur` : "Tous tes documents ont un émetteur"}</b>
      <p class="sub" style="margin:4px 0 10px">Bon toutou relit le texte de ces documents, sur ton ordinateur, pour retrouver l'émetteur, par exemple l'employeur d'une fiche de paie, puis range chaque document dans le dossier de son émetteur. Une seule annulation pour tout.</p>
      <button class="ghost small" data-act="redetect" ${st.unknown_emitters ? "" : "disabled"}>Retrouver les émetteurs</button></div>`; }
  if (sv === "regles") return `${setHead("tag", "Mes règles et catalogue", "Apprends à Bon toutou tes propres papiers : « si le document contient X, alors… ». Tes règles s'appliquent avant celles du catalogue.")}
    ${window.reglesSection ? noLabel(reglesSection()) : ""}
    <div class="label" style="margin:22px 0 8px">Catalogue</div>
    <div class="card">${(st.packs || []).map((p) => `<div class="row"><span class="pill ${p.kind === "officiel" ? "ok" : p.kind === "perso" ? "acc" : "warn"}">${p.kind === "officiel" ? "Officiel" : p.kind === "perso" ? "Tes règles" : "Importé"}</span><div class="grow"><b>${esc(p.name)}</b> <span class="sub">${esc(p.version || "")}</span>
      <div class="sub">${[p.types && `${p.types} ${plural(p.types, "type")}`, p.rules && `${p.rules} ${plural(p.rules, "règle")}`, p.emitters && `${p.emitters} ${plural(p.emitters, "organisme")}`, p.templates && `${p.templates} ${plural(p.templates, "démarche")}`].filter(Boolean).join(" · ")}</div></div></div>`).join("")}
      ${(st.catalog_warnings || []).length ? `<div class="hint" style="margin:8px 16px 14px">${st.catalog_warnings.map(esc).join("<br>")}</div>` : ""}</div>`;
  if (sv === "save") return `${setHead("drive", "Sauvegarde", "Ton bureau est fait de fichiers ordinaires : n'importe quel outil de sauvegarde le protège déjà.")}
    <div class="card box"><dl class="kv"><dt>Ton bureau</dt><dd class="fname">${esc(st.root)}</dd></dl>
      <div class="acts" style="margin-top:10px"><button class="ghost small" data-act="reveal" data-p=".">${IC.folder} Montrer dans le Finder</button></div>
      <p class="sub">Sur Mac, Time Machine le sauvegarde automatiquement. Tu peux aussi le copier sur un disque externe : tout y est (documents, fiches, preuves d'envoi).</p></div>
    <div style="margin-top:10px">${soonCard("save", "Sauvegarde automatique vers un disque ou un NAS, vérifiée")}</div>`;
  if (sv === "cont") return `${setHead("heart", "Continuité", "Si un jour tu ne peux plus t'occuper de tes papiers, une personne de confiance peut retrouver l'essentiel.")}
    <div class="warnbox" style="margin-bottom:14px"><b>Ce que ça n'est pas :</b> ni un testament, ni un mandat de protection future, ni une procuration. Ça donne accès à des fichiers, pas un droit juridique d'agir en ton nom. Pour cela, parle à un notaire.</div>
    <div class="card box"><b>Personne de confiance</b><p class="sub" style="margin:4px 0 10px">Juste un nom pour l'instant, gardé dans ton dossier. Dis-lui où se trouve ton bureau.</p>
      <div class="acts"><input class="field" id="trusted" value="${esc(s.trusted || "")}" placeholder="Prénom Nom" style="width:min(280px,100%)"><button class="cta small" data-act="trusted-save">Enregistrer</button></div></div>
    <div style="margin-top:10px">${soonCard("cont", "Accès d'urgence : elle demande, tu es prévenu, tu peux refuser pendant un délai")}</div>`;
  if (sv === "sync") return `${setHead("sync", "Synchronisation et index", "")}
    <div class="card box">Tes documents et leurs fiches sont dans ton dossier : tu peux le synchroniser avec l'outil de ton choix (iCloud Drive, Syncthing, un disque…). L'index de recherche, lui, reste sur cet appareil (<b>${esc(st.device ? st.device.name : "")}</b>) et se reconstruit à partir des fiches.
      <dl class="kv" style="margin-top:12px"><dt>Ton bureau</dt><dd class="fname">${esc(st.root)}</dd><dt>Index local</dt><dd class="fname">${esc(st.local_data || "")}</dd></dl>
      ${st.newer_data ? `<div class="hint">Certaines données viennent d'une version plus récente de Bon toutou : elles sont gardées intactes.</div>` : ""}
      <div style="margin-top:12px">${S.confirm === "rebuild" ? `<button class="cta small" data-act="rebuild">Confirmer la reconstruction</button> <button class="linkbtn" data-act="noconfirm">annuler</button>` : `<button class="ghost small" data-act="askrebuild">Reconstruire l'index…</button>`}</div></div>`;
  if (sv === "hist") return `${setHead("history", "Historique des actions", "Chaque rangement, correction ou archivage. La dernière action peut être annulée.")}
    <div class="card">${(S.hist || []).map((h, i) => `<div class="row"><div class="grow"><b>${esc(h.label)}</b><div class="sub">${esc(h.ts.replace("T", " "))}${h.undone ? " · annulé" : ""}</div></div>${!h.undone && i === (S.hist || []).findIndex((x) => !x.undone) ? `<button class="ghost small" data-act="undo" data-b="${h.batch}">Annuler</button>` : ""}</div>`).join("") || `<div class="row sub">Aucune action pour l'instant.</div>`}</div>`;
  if (sv === "maj") return `${setHead("up", "Version et mises à jour", "")}${window.majSection ? noLabel(majSection()).split('<div class="label">Signaler')[0] : ""}`;
  if (sv === "bug") return `${setHead("bug", "Signaler un problème", "")}<div class="card box"><span class="sub">Prépare un rapport sans aucun document ni nom de fichier, que tu relis avant de décider de l'envoyer.</span>
    <div class="acts" style="margin-top:8px"><button class="ghost small" data-act="bug-open">Préparer un rapport</button></div></div>`;
  if (sv === "accueil") { const g = s.guide || {};
    return `${setHead("spark", "Premier tri guidé", "5 minutes pour découvrir Bon toutou avec tes propres papiers : 3 documents, ton kit de base, tes proches.")}
    <div class="card box"><div class="acts"><button class="cta" data-act="g-replay">${g.fini ? "Le refaire" : g.etape ? "Reprendre" : "Commencer"}</button></div><p class="sub">Les questions déjà posées à l'installation (dossier, pays) ne sont pas reposées.</p></div>`; }

  // ---- liste principale
  const P = plusSteps(), pd = P.filter((x) => x.done).length;
  return `<h1>Réglages</h1><p class="lead">Bon toutou ${esc(st.version || "")} · tout est local : le moteur n'écoute que ton ordinateur.</p>
  <button class="plusbtn" data-go="reglages" data-sv="plus"><span class="oi">${IC.sparkles}</span><div class="grow"><b>Aller plus loin</b><small>La suite de ton accueil, pas à pas · ${pd} sur ${P.length} faites</small><div class="bar" style="margin-top:8px;max-width:280px"><i style="width:${Math.round((pd / P.length) * 100)}%"></i></div></div><span class="go">Continuer ›</span></button>
  ${REG.map(([t, L]) => `<div class="label setgroup">${t}</div><div class="card setlist">${L.map((r) => `<button class="rowbtn" data-go="reglages" data-sv="${r[0]}"><span class="oi">${IC[r[1]]}</span><div class="grow"><b>${r[2]}</b><small>${esc(r[3]())}</small></div>${r[4] ? `<span class="soontag">${r[4]}</span>` : ""}<span>›</span></button>`).join("")}</div>`).join("")}`;
}

/* ---------- liens, enregistrements */
(function () {
  const prevBind = window.bindExtra;
  window.bindExtra = function () {
    if (prevBind) prevBind();
    if (S.v !== "reglages") { S.hEdit = null; return; }
    const ow = $("#owner"); if (ow) ow.onchange = async () => { await api("/api/settings", { owner: ow.value.trim() }); toast("Nom enregistré"); load(); };
    document.querySelectorAll("[data-country]").forEach((el) => (el.onchange = async () => {
      const c = [...document.querySelectorAll("[data-country]:checked")].map((x) => x.dataset.country);
      if (!c.length) { el.checked = true; return toast("Garde au moins un pays"); }
      await api("/api/settings", { countries: c }); toast("Pays enregistrés"); load();
    }));
    document.querySelectorAll("[data-hn]").forEach((el) => (el.oninput = () => (S.hEdit[+el.dataset.hn].nom = el.value)));
    document.querySelectorAll("[data-hk]").forEach((el) => (el.onchange = () => (S.hEdit[+el.dataset.hk].genre = el.value)));
    document.querySelectorAll("[data-org]").forEach((el) => (el.onchange = async () => {
      const D = new Set(S.st.settings.orgs_done || []); el.checked ? D.add(el.dataset.org) : D.delete(el.dataset.org);
      await api("/api/settings", { orgs_done: [...D] }); load();
    }));
  };
})();
async function plusMark(id, on) {
  const D = new Set(S.st.settings.plus_done || []); on ? D.add(id) : D.delete(id);
  await api("/api/settings", { plus_done: [...D] }); return load();
}
document.addEventListener("click", async (e) => {
  const t = e.target;
  const ext = t.closest("[data-ext]"); if (ext) { e.preventDefault(); return window.openExternal ? openExternal(ext.dataset.ext) : window.open(ext.dataset.ext, "_blank"); }
  const nt = t.closest("[data-notify]"); if (nt) { const N = new Set(S.st.settings.notify || []), k = nt.dataset.notify; N.has(k) ? N.delete(k) : N.add(k);
    await api("/api/settings", { notify: [...N] }); toast(N.has(k) ? "Noté sur ton ordinateur" : "Retiré"); return load(); }
  const pl = t.closest("[data-plus]"); if (pl) return plusMark(pl.dataset.plus, true);
  const lv = t.closest("[data-lv]"); if (lv) { await api("/api/settings", { privacy: { [lv.dataset.lv]: lv.dataset.l } }); if (!has("priv")) await plusMark("priv", true); else load(); return toast("Niveau enregistré"); }
  const a = t.closest("[data-act]"); if (!a) return;
  const act = a.dataset.act;
  if (act === "h-add") { S.hEdit.push({ nom: "", genre: "enfant" }); return render(); }
  if (act === "h-rm") { S.hEdit.splice(+a.dataset.k, 1); return render(); }
  if (act === "h-save") { await api("/api/settings", { holders: S.hEdit.filter((h) => h.nom.trim()).map((h) => ({ nom: h.nom.trim(), genre: h.genre })) }); S.hEdit = null; toast("Proches enregistrés"); return load(); }
  if (act === "mail-save") { const v = $("#mail_in").value.trim(); if (v && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) return toast("Cette adresse ne semble pas valide");
    await api("/api/settings", { mail: v }); toast(v ? "Adresse admin enregistrée" : "Adresse retirée"); return load(); }
  if (act === "mail-clear") { await api("/api/settings", { mail: "" }); return load(); }
  if (act === "trusted-save") { await api("/api/settings", { trusted: $("#trusted").value.trim() }); toast("Enregistré"); return load(); }
  if (act === "ics-dl") { const r = await api("/api/export", { kind: "ics" });
    toast(r.ok ? `Fichier enregistré dans ${r.folder} : ton calendrier va proposer de l'importer` : (r.msg || "Erreur"));
    if (r.ok && !has("cal")) await plusMark("cal", true); return; }
  if (act === "g-replay") { const g = Object.assign({}, S.st.settings.guide || {}, { fini: false, masque: false, etape: (S.st.settings.guide || {}).fini ? 0 : (S.st.settings.guide || {}).etape || 0 });
    await api("/api/settings", { guide: g }); S.st.settings.guide = g; S.gids = []; return go("guide"); }
});
