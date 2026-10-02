# Brief pour Claude Code — Bon toutou

Lis d'abord `docs/DECISIONS.md` (le modèle). Le moteur et l'interface sont dans `engine/`, l'app de bureau dans `desktop/`, la fabrication dans `.github/workflows/fabrication.yml`.

## Ce que c'est
Une app locale qui range les papiers administratifs dans un vrai dossier (choisi à l'installation), avec :
- des documents suivis (version actuelle + historique) ;
- des dossiers (pièces résolues automatiquement) ;
- des preuves d'envoi figées (SHA-256).

## Architecture (étape A de l'architecture scalable, oct. 2026 — voir le doc projet « bon_toutou_architecture »)
- **Dans le dossier (synchronisable)** : les documents, une fiche par document `.bontoutou/meta/docs/<id>.json` et par dossier `.bontoutou/meta/dossiers/<id>.json`, un journal par appareil `.bontoutou/journal/<appareil>.jsonl`, `profil.json` (nom, pays, confidentialité), `sorties.jsonl`, `mes-regles.json`, `packs/` (packs importés).
- **Sur l'appareil (local, reconstructible)** : `index.db` et `reglages-appareil.json` dans `~/Library/Application Support/Bon toutou/bureaux/<bureau>-<hash>/` (ou `$BONTOUTOU_DATA`). Au démarrage, l'index récupère les fiches changées par un autre appareil (estampille `updated_at|updated_by`).
- **Format versionné** : `format: 1` partout ; on garde les champs inconnus, on ne casse jamais ce qu'une autre version a écrit.
- `bontoutou/catalog.py` : **chargeur de packs JSON** (`bontoutou/packs/` officiels → packs importés → `mes-regles.json`). Données seulement, jamais de code ; motifs trop complexes refusés hors packs officiels. Chaque type, émetteur et règle garde son origine, affichée dans « Pourquoi ? ».
- `bontoutou/sortie.py` : **la seule porte vers le réseau**. Local (127.0.0.1) autorisé ; sinon motif connu + accord + niveau de la catégorie (document non trié = 🔒), noté dans `sorties.jsonl` AVANT l'envoi. `tests/test_sortie.py` vérifie qu'aucun autre fichier n'ouvre de connexion.

- **Étape B** : `bontoutou/regles.py` (règles « contient X → champ », types perso, export / import de packs non signés, proposition avec repérage du personnel), `sortie.mask()` (masquage des numéros), confidentialité par catégorie (profil), titulaires proches et premier tri guidé (`static/guide.js`). Interface des règles : `static/regles.js`. Le texte lu est mis en cache dans l'index local (table `texts`) : pas de nouvel OCR pour appliquer une règle.

- **Étape C** : `bontoutou/ia.py` = prise unique pour l'IA locale (Ollama en API native ; LM Studio, Jan, llama.cpp serveur en format compatible OpenAI), détection de la machine et niveau conseillé, liste vérifiée `packs/modeles.json` (Mistral AI conseillé, Qwen en alternative, Apache 2.0), installation via Ollama avec accord + journal. `classify.refine_with_ai` vérifie chaque réponse (type connu, date réelle et passée, pays connu). Moteur intégré (llama.cpp en bibliothèque) et empreintes GGUF : étape D.

- **Étape D (app)** : `desktop/` (Tauri 2) choisit un port libre sur 127.0.0.1, lance le moteur embarqué `bontoutou-engine` (PyInstaller, `engine/entry.py`) avec `--port N --app --watch-pid <app>` et l'affiche ; le moteur s'arrête quand l'app se ferme. Sans dossier configuré, le moteur démarre en mode installation (`maj.setup_state`, `static/setup.js`). Mises à jour : `maj.check` (une requête vers GitHub Releases, accord + journal) ; rapport de bug sans document (`maj.bug_report`). Moteur IA intégré : `llama_cpp` (compilé en CI), modèles GGUF dont l'empreinte est fixée par `tools/pin_models.py` à la fabrication, téléchargés par `sortie.download` qui refuse toute empreinte fausse.

## Architecture (détail)
- `bontoutou/server.py` : serveur HTTP de la bibliothèque standard, **127.0.0.1 uniquement**, API JSON + fichiers statiques.
- `bontoutou/core.py` : classe `Bureau`, qui gère les chemins, l'index SQLite, le journal (annuler), le tri (`register` / `proposal` / `validate`), les documents, les dossiers (`resolve` / `finalize` / `mark_sent`), les archives et `rebuild_index`.
- `bontoutou/classify.py` : règles (type, pays, émetteur, dates, expiration) + IA locale optionnelle (Ollama).
- `bontoutou/reader.py` : extraction du texte (pypdf, puis pdftotext, puis OCR tesseract), le tout optionnel.
- `bontoutou/packs/*.json` : pays, catégories, types de documents, organismes, règles d'intitulé, démarches.
- `static/` : interface en HTML/CSS/JS pur, sans build.
- `tests/test_flow.py` : test de bout en bout (`python3 -m tests.test_flow`). `tests/make_samples.py` fabrique de faux PDF.

## Règles non négociables
1. **Ne jamais supprimer un fichier de l'utilisateur.** Déplacer, copier, archiver seulement. Tout déplacement passe par `_move()` pour être journalisé et annulable.
2. **Aucun appel réseau hors de `sortie.py`.** Le moteur passe par `Bureau.sortir()` (niveau de la catégorie + accord + journal). Jamais d'import réseau ailleurs.
3. **Python 3.9 compatible, zéro dépendance obligatoire** (le Python par défaut de macOS). `pypdf` et tesseract sont des bonus détectés à l'exécution.
4. Le dossier Finder reste lisible sans l'app. Le nommage suit `AAAA-MM-JJ_PAYS_CAT_Emetteur_Objet.ext`.
5. Interface en français. Dire « document suivi » (pas « document maître »). Confiance en mots, jamais en pourcentage. Toujours un « Pourquoi ? ».
6. Avant chaque livraison : `cd engine && for t in flow sortie regles ia app; do python3 -m tests.test_$t; done`.
7. Licence AGPL-3.0. Aucune télémétrie, jamais.

## Prochaines étapes
Voir le document de projet « bon_toutou_architecture » (plan A → E).
