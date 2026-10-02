"""Le moteur Bon toutou : bureau (dossier Finder), index, journal, tri, dossiers, archives.

Règles d'or
  * Le dossier Finder est la vérité. Il contient les documents ET une petite fiche par document
    (.bontoutou/meta/docs/<id>.json), synchronisables par l'outil de ton choix.
  * L'index (index.db) est local à chaque appareil, rangé hors du dossier, et se reconstruit à partir des fiches.
  * Bon toutou ne détruit rien : il déplace, copie, archive. Jamais de suppression.
  * Chaque action est notée dans le journal et peut être annulée.
  * Aucun appel réseau sauf par bontoutou/sortie.py (la seule porte de sortie, vérifiée et journalisée).
"""
import datetime as dt
import hashlib
import platform
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import uuid
import zipfile

from . import catalog, classify, ia, reader, sortie
from .catalog import CAT_FOLDERS_FR, CATEGORIES, COUNTRIES, SUB_FOLDERS_FR, TEMPLATES, TYPES

SCHEMA = """
CREATE TABLE IF NOT EXISTS docs(id TEXT PRIMARY KEY, suivi TEXT, type TEXT, label TEXT, person TEXT, country TEXT,
  cat TEXT, sub TEXT, emitter TEXT, doc_date TEXT, expiry TEXT, path TEXT, orig_name TEXT, sha TEXT, status TEXT,
  added_at TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS inbox(id TEXT PRIMARY KEY, path TEXT, orig_name TEXT, sha TEXT, source TEXT, method TEXT,
  analysis TEXT, overrides TEXT, state TEXT, added_at TEXT);
CREATE TABLE IF NOT EXISTS dossiers(id TEXT PRIMARY KEY, template TEXT, recipient TEXT, country TEXT, created_at TEXT,
  state TEXT, assign TEXT, folder TEXT, zip TEXT, manifest TEXT, finalized_at TEXT, sent_at TEXT);
CREATE TABLE IF NOT EXISTS journal(batch TEXT PRIMARY KEY, ts TEXT, label TEXT, ops TEXT, undone INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS texts(sha TEXT PRIMARY KEY, text TEXT, method TEXT);
CREATE TABLE IF NOT EXISTS meta_seen(id TEXT PRIMARY KEY, stamp TEXT);
CREATE TABLE IF NOT EXISTS egress(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, doc_id TEXT, dest TEXT, reason TEXT);
"""

FORMAT = 1  # version du format des fiches, du profil et du journal écrits par cette version
DOC_FIELDS = ("id", "suivi", "type", "label", "person", "country", "cat", "sub", "emitter", "doc_date", "expiry", "path",
              "orig_name", "sha", "status", "added_at", "note", "detail")
DOSSIER_FIELDS = ("id", "template", "recipient", "country", "created_at", "state", "assign", "folder", "zip", "manifest",
                  "finalized_at", "sent_at")
PROFILE_KEYS = ("owner", "countries", "privacy", "disabled_packs", "holders", "guide", "mail", "orgs_done", "notify", "plus_done", "trusted")          # suivent l'utilisateur sur tous ses appareils
DEVICE_KEYS = ("theme", "use_ollama", "ollama_model", "ai_mode", "ai_engine", "ai_bench", "ai_never", "maj_auto", "maj_last")      # use_ollama / ollama_model : IA locale activée / modèle (noms historiques)                      # propres à cet appareil
# Niveaux de confidentialité par défaut (catégorie -> local | autorisation | externe). Un document non trié est « local ».
DEFAULT_PRIVACY = {"01": "local", "04": "local", "05": "local", "06": "local", "09": "local", "10": "local", "13": "local",
                   "02": "autorisation", "03": "autorisation", "07": "autorisation", "12": "autorisation", "14": "autorisation",
                   "08": "externe", "11": "externe", "15": "externe"}

STATUS_LABEL = {"actuel": "Version actuelle", "ancienne_version": "Ancienne version", "termine": "Terminé"}
NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_([A-Z]{2,3})_(\d{2})_([^_]+)_(.+)\.[A-Za-z0-9]+$")


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def today():
    return dt.date.today()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def data_home():
    """Dossier des données locales de l'appareil (index, réglages de l'appareil). Jamais dans le dossier synchronisé."""
    env = os.environ.get("BONTOUTOU_DATA")
    if env:
        return env
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/Bon toutou")
    if os.name == "nt":
        return os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "Bon toutou")
    return os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "bontoutou")


def local_key(root):
    """Nom du dossier local (index, réglages de l'appareil) d'un bureau."""
    root = os.path.abspath(os.path.expanduser(root))
    return os.path.basename(root) + "-" + hashlib.sha1(os.path.realpath(root).encode()).hexdigest()[:10]


def write_json(path, obj):
    """Écriture atomique (fichier temporaire puis remplacement) : jamais de fiche à moitié écrite."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def unique_path(folder, name):
    base, ext = os.path.splitext(name)
    p, i = os.path.join(folder, name), 2
    while os.path.exists(p):
        p = os.path.join(folder, f"{base}-{i}{ext}")
        i += 1
    return p


class Bureau:
    def __init__(self, root):
        self.root = os.path.abspath(os.path.expanduser(root))
        if not os.path.isdir(self.root):
            raise SystemExit(f"Dossier introuvable : {self.root}")
        self.fm = os.path.join(self.root, ".bontoutou")
        from .migration import renommer_fiches
        renommer_fiches(self.root)  # bureau créé par Freemarket (.freemarket) : renommé, rien n'est supprimé
        os.makedirs(self.fm, exist_ok=True)
        self.meta_dir = os.path.join(self.fm, "meta")
        self.inbox_dir = os.path.join(self.root, "00_A-TRIER")
        os.makedirs(self.inbox_dir, exist_ok=True)
        self.lock = threading.RLock()
        self._dirty = set()
        # ---- données locales de cet appareil (hors du dossier synchronisé)
        self.local = os.path.join(data_home(), "bureaux", local_key(self.root))
        os.makedirs(self.local, exist_ok=True)
        dev_path = os.path.join(data_home(), "appareil.json")
        self.device = read_json(dev_path, {}) or {}
        if not self.device.get("id"):
            self.device = {"format": FORMAT, "id": uuid.uuid4().hex[:8], "name": platform.node() or "appareil"}
            write_json(dev_path, self.device)
        self.journal_path = os.path.join(self.fm, "journal", f"{classify.slugify(self.device['name'])[:30]}-{self.device['id']}.jsonl")
        # ---- index local ; migration depuis l'ancienne place (.bontoutou/index.db), sans rien détruire
        db_path = os.path.join(self.local, "index.db")
        old_db = os.path.join(self.fm, "index.db")
        self.migrated = False
        if not os.path.exists(db_path) and os.path.exists(old_db):
            shutil.copy2(old_db, db_path)
            os.replace(old_db, old_db + ".migre-" + dt.date.today().strftime("%Y%m%d"))
            self.migrated = True
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        if "detail" not in [r[1] for r in self.db.execute("PRAGMA table_info(docs)")]:
            self.db.execute("ALTER TABLE docs ADD COLUMN detail TEXT")  # précision : ASSR2, « Attestation de présence Dr X »…
            self.db.commit()
        # ---- réglages : profil (synchronisé) + appareil (local)
        self.profile_path = os.path.join(self.fm, "profil.json")
        self.device_settings_path = os.path.join(self.local, "reglages-appareil.json")
        old = os.path.join(self.fm, "settings.json")
        if os.path.exists(old) and not os.path.exists(self.profile_path):
            o = read_json(old, {}) or {}
            write_json(self.profile_path, {"format": FORMAT, **{k: o[k] for k in PROFILE_KEYS if k in o}})
            write_json(self.device_settings_path, {"format": FORMAT, **{k: o[k] for k in DEVICE_KEYS if k in o}})
            os.replace(old, old + ".migre")
        self.newer_data = False
        self.settings = {"countries": ["FR", "NZ"], "use_ollama": False, "ollama_model": "", "owner": "", "ai_mode": "texte", "ai_engine": "auto", "ai_bench": {}, "ai_never": False, "maj_auto": False, "maj_last": "",
                         "privacy": dict(DEFAULT_PRIVACY), "disabled_packs": [],
                         "holders": [], "guide": {"etape": 0, "fini": False, "masque": False},
                         "mail": "", "orgs_done": [], "notify": [], "plus_done": [], "trusted": "", "theme": "champagne"}
        for pth in (self.profile_path, self.device_settings_path):
            d = read_json(pth, {}) or {}
            if int(d.get("format", 1) or 1) > FORMAT:
                self.newer_data = True
            for k, v in d.items():
                if k == "privacy" and isinstance(v, dict):
                    self.settings["privacy"].update(v)
                elif k != "format":
                    self.settings[k] = v
        # ---- catalogue : packs officiels + importés + règles perso
        catalog.load(self.fm, self.settings.get("disabled_packs") or ())
        self._persons()
        from .regles import Regles
        self.regles = Regles(self)
        # ---- fiches : première fois -> on les écrit ; sinon on récupère ce que d'autres appareils ont changé
        has_meta = os.path.isdir(os.path.join(self.meta_dir, "docs"))
        n_docs = self.db.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
        if not has_meta:
            self._export_all_meta()
        elif n_docs == 0:
            self._import_meta(full=True)
        else:
            self._import_meta(full=False)

    # ------------------------------------------------------------ chemins
    def rel(self, p):
        return os.path.relpath(p, self.root)

    def abs(self, r):
        p = os.path.abspath(os.path.join(self.root, r))
        if not (p == self.root or p.startswith(self.root + os.sep)):
            raise ValueError("chemin hors du bureau")
        return p

    def _child(self, parent, prefix, default):
        os.makedirs(parent, exist_ok=True)
        for n in sorted(os.listdir(parent)):
            if n.startswith(prefix) and os.path.isdir(os.path.join(parent, n)):
                return os.path.join(parent, n)
        p = os.path.join(parent, default)
        os.makedirs(p, exist_ok=True)
        return p

    def country_dir(self, cc):
        return self._child(self.root, COUNTRIES[cc]["folder"], COUNTRIES[cc]["folder"])

    def cat_dir(self, cc, cat):
        return self._child(self.country_dir(cc), cat + "_", CAT_FOLDERS_FR[cat])

    def sub_dir(self, cc, cat, sub):
        return self._child(self.cat_dir(cc, cat), sub + "_", sub + "_" + SUB_FOLDERS_FR.get(sub, "Divers"))

    def archive_root(self, cc):
        return self._child(self.country_dir(cc), "99_ARCHIVE", "99_ARCHIVES")

    def archive_sub(self, cc, cat, sub):
        c = os.path.basename(self.cat_dir(cc, cat))
        s = os.path.basename(self.sub_dir(cc, cat, sub))
        p = os.path.join(self.archive_root(cc), c, s)
        os.makedirs(p, exist_ok=True)
        return p

    def doc_dir(self, cc, type_id, emitter, archive=False):
        """Dossier d'un document : sous-dossier de sa catégorie, puis un dossier par émetteur pour les papiers
        d'emploi (fiches de paie, contrats…) : 03-2_Bulletins-paie/Nuances-Gourmandes/."""
        T = TYPES.get(type_id) or TYPES["autre"]
        p = self.archive_sub(cc, T["cat"], T["sub"]) if archive else self.sub_dir(cc, T["cat"], T["sub"])
        if T.get("par_emetteur") and emitter and emitter != "Inconnu":
            p = os.path.join(p, classify.slugify(emitter)[:40])
            os.makedirs(p, exist_ok=True)
        return p

    def demarches_dir(self, cc):
        return self._child(self.country_dir(cc), "20_", "20_DEMARCHES")

    def sent_dir(self, cc):
        p = os.path.join(self.archive_root(cc), os.path.basename(self.demarches_dir(cc)))
        os.makedirs(p, exist_ok=True)
        return p

    # ------------------------------------------------------------ réglages
    def save_settings(self, patch):
        with self.lock:
            for k in PROFILE_KEYS + DEVICE_KEYS:
                if k in patch:
                    if k == "privacy":
                        self.settings["privacy"].update({c: v for c, v in patch[k].items() if v in sortie.LEVELS})
                    else:
                        self.settings[k] = patch[k]
            for pth, keys in ((self.profile_path, PROFILE_KEYS), (self.device_settings_path, DEVICE_KEYS)):
                d = read_json(pth, {}) or {}          # on garde ce qu'une version plus récente aurait ajouté
                d.update({k: self.settings[k] for k in keys})
                d["format"] = max(int(d.get("format", FORMAT) or FORMAT), FORMAT)
                write_json(pth, d)
            if "disabled_packs" in patch:
                catalog.load(self.fm, self.settings.get("disabled_packs") or ())
            self._persons()
            return self.settings

    def _persons(self):
        """Les mots de ton nom et de ceux de tes proches : jamais pris pour le nom d'un employeur."""
        names = [self.settings.get("owner") or ""] + [h.get("nom", "") for h in self.settings.get("holders") or [] if isinstance(h, dict)]
        classify.PERSONS.clear()
        classify.PERSONS.update(w for n in names for w in classify.slugify(n).lower().split("-") if len(w) >= 3 and n.strip())

    def _machine(self):
        if not getattr(self, "_mach", None):
            self._mach = ia.machine(self.root)
        return self._mach

    def ai_pull(self, engine_id, model, consent):
        if not consent:
            return {"ok": False, "msg": "Il faut ton accord pour télécharger un modèle."}
        eng = ia.engine_by_id(engine_id)
        if not eng or not eng["running"]:
            return {"ok": False, "msg": "Ce moteur ne tourne pas en ce moment."}
        return ia.pull(eng, model, self.log_sortie)

    def ai_test(self, engine_id, model):
        eng = ia.engine_by_id(engine_id)
        if not eng or not eng["running"]:
            return {"ok": False, "erreur": "Ce moteur ne tourne pas en ce moment."}
        r = ia.test(eng, model)
        if r.get("ok"):  # on garde le meilleur temps mesuré (modèle déjà chargé) pour régler les délais
            b = dict(self.settings.get("ai_bench") or {})
            b[model] = min(r["secondes"], b.get(model, 1e9))
            self.save_settings({"ai_bench": b})
            r["meilleur"] = b[model]
        return r

    def _ai_secs(self):
        return float((self.settings.get("ai_bench") or {}).get(self.settings.get("ollama_model") or "", 0) or 0)

    def _ai_timeout(self, vision):
        """Délai d'attente adapté à la vitesse mesurée : un vrai document demande ~3x l'essai."""
        base = 240 if vision else 120
        s = self._ai_secs()
        return int(min(900, max(base, 3 * s + 60))) if s else base

    def reload_catalog(self):
        catalog.load(self.fm, self.settings.get("disabled_packs") or ())

    # ------------------------------------------------------------ premier tri guidé
    KIT = [("Pièce d'identité", ["carte_identite", "passeport"], "location, banque, emploi, administration"),
           ("Dernier avis d'impôt", ["avis_impot", "ird_assessment"], "location, crédit, aides"),
           ("RIB", ["rib"], "salaire, remboursements, prélèvements"),
           ("Justificatif de domicile", ["facture_energie", "quittance_loyer", "justificatif_domicile"], "banque, administration, carte grise"),
           ("Attestation d'assurance habitation", ["assurance_habitation"], "location, état des lieux")]

    def guide(self):
        have = {}
        for r in self.db.execute("SELECT type,label FROM docs WHERE status='actuel'").fetchall():
            have.setdefault(r["type"], r["label"])
        kit = [{"label": l, "types": t, "why": w, "have": next((have[x] for x in t if x in have), None)} for l, t, w in self.KIT]
        tpl = TEMPLATES.get("louer_logement", {"label": "", "pieces": []})
        reuse = [{"label": pc["label"], "have": next((have[x] for x in pc["types"] if x in have), None)} for pc in tpl["pieces"]]
        return {"guide": self.settings.get("guide") or {}, "kit": kit, "reuse": {"label": tpl["label"], "pieces": reuse},
                "holders": self.settings.get("holders") or [], "docs": len(have)}

    # ------------------------------------------------------------ fiches (synchronisées) et index (local)
    def _meta_path(self, kind, oid):
        return os.path.join(self.meta_dir, kind, oid + ".json")

    def _write_meta(self, kind, row, fields):
        path = self._meta_path(kind, row["id"])
        cur = read_json(path, {}) or {}                 # champs inconnus (version plus récente) conservés
        cur.update({k: row[k] for k in fields})
        cur.update({"format": max(int(cur.get("format", FORMAT) or FORMAT), FORMAT), "kind": kind[:-1],
                    "updated_at": dt.datetime.now().isoformat(timespec="microseconds"), "updated_by": self.device["id"]})
        write_json(path, cur)
        self._seen(row["id"], cur)

    def _seen(self, oid, m):
        self.db.execute("INSERT OR REPLACE INTO meta_seen(id,stamp) VALUES(?,?)", (oid, f"{m.get('updated_at')}|{m.get('updated_by')}"))

    def _meta_doc(self, did):
        row = self.db.execute("SELECT * FROM docs WHERE id=?", (did,)).fetchone()
        path = self._meta_path("docs", did)
        if row:
            self._write_meta("docs", row, DOC_FIELDS)
        elif os.path.exists(path):                      # ajout annulé : la fiche part avec lui
            os.remove(path)

    def _meta_dossier(self, kid):
        row = self.db.execute("SELECT * FROM dossiers WHERE id=?", (kid,)).fetchone()
        if row:
            self._write_meta("dossiers", row, DOSSIER_FIELDS)

    def _flush_meta(self):
        for did in list(self._dirty):
            self._meta_doc(did)
        self._dirty.clear()
        self._mark_synced()

    def _export_all_meta(self):
        for r in self.db.execute("SELECT id FROM docs").fetchall():
            self._meta_doc(r["id"])
        for r in self.db.execute("SELECT id FROM dossiers").fetchall():
            self._meta_dossier(r["id"])
        self._mark_synced()

    def _mark_synced(self):
        self.db.commit()

    def _sha_map(self):
        """empreinte -> chemin, pour retrouver un fichier déplacé (par toi ou par un autre appareil)."""
        m = {}
        for dirpath, dirs, files in os.walk(self.root):
            # les copies figées des dossiers envoyés (20_DEMARCHES) et la boîte à trier ne comptent pas
            dirs[:] = [d for d in dirs if not d.startswith((".", "20_", "00_A-TRIER"))]
            for f in files:
                if not f.startswith("."):
                    p = os.path.join(dirpath, f)
                    try:
                        m.setdefault(sha256(p), self.rel(p))
                    except OSError:
                        pass
        return m

    def _import_meta(self, full=False):
        """Met l'index à jour depuis les fiches. full=False : seulement celles qu'un autre appareil a changées
        (on compare l'estampille « modifiée le / par » de chaque fiche, pas l'heure du fichier : les outils de synchro la changent)."""
        seen = {} if full else {r["id"]: r["stamp"] for r in self.db.execute("SELECT id,stamp FROM meta_seen")}
        n, shas = 0, None
        for kind, fields, table in (("docs", DOC_FIELDS, "docs"), ("dossiers", DOSSIER_FIELDS, "dossiers")):
            d = os.path.join(self.meta_dir, kind)
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                if not fn.endswith(".json"):
                    continue
                m = read_json(os.path.join(d, fn))
                if not m or not m.get("id"):
                    continue
                if seen.get(m["id"]) == f"{m.get('updated_at')}|{m.get('updated_by')}":
                    continue
                vals = {k: m.get(k) for k in fields}
                if kind == "docs":
                    if vals.get("type") not in TYPES:
                        vals["type"] = "autre"
                    if vals.get("path") and not os.path.exists(self.abs(vals["path"])) and vals.get("sha"):
                        shas = shas if shas is not None else self._sha_map()
                        if vals["sha"] in shas:
                            vals["path"] = shas[vals["sha"]]
                            self._dirty.add(vals["id"])
                cols = ",".join(fields)
                self.db.execute(f"INSERT OR REPLACE INTO {table}({cols}) VALUES({','.join('?' * len(fields))})",
                                tuple(vals[k] for k in fields))
                self._seen(m["id"], m)
                n += 1
        self.db.commit()
        self._flush_meta()
        return n

    # ------------------------------------------------------------ journal des sorties
    def log_sortie(self, entry):
        e = {"format": FORMAT, "ts": now(), "device": self.device["id"], **entry}
        os.makedirs(self.fm, exist_ok=True)
        with open(os.path.join(self.fm, "sorties.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
        self.db.execute("INSERT INTO egress(ts,doc_id,dest,reason) VALUES(?,?,?,?)", (e["ts"], e.get("doc_id"), e.get("dest"), e.get("label")))
        self.db.commit()

    def sorties(self):
        out = []
        p = os.path.join(self.fm, "sorties.jsonl")
        if os.path.exists(p):
            for line in open(p, encoding="utf-8"):
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
        return list(reversed(out))

    def privacy_level(self, cat):
        """Niveau de confidentialité d'une catégorie ; None (document non trié) = local."""
        return self.settings["privacy"].get(cat, "local") if cat else "local"

    def sortir(self, url, purpose, consent=False, cat=None, **kw):
        """Seul chemin vers internet pour le moteur : passe par la porte de sortie avec le niveau de la catégorie."""
        return sortie.http(url, purpose=purpose, consent=consent, level=self.privacy_level(cat), log=self.log_sortie, **kw)

    # ------------------------------------------------------------ journal
    def _journal(self, label, ops):
        b = uuid.uuid4().hex[:12]
        ts = now()
        self.db.execute("INSERT INTO journal(batch,ts,label,ops) VALUES(?,?,?,?)", (b, ts, label, json.dumps(ops)))
        self.db.commit()
        for op in ops:
            if op["t"] in ("insert_doc", "update_doc"):
                self._dirty.add(op["id"])
        self._flush_meta()
        self._append_journal({"batch": b, "label": label, "ops": ops})
        return b

    def _append_journal(self, entry):
        """Journal de CET appareil, dans le dossier : chaque appareil écrit dans son propre fichier (pas de conflit)."""
        os.makedirs(os.path.dirname(self.journal_path), exist_ok=True)
        with open(self.journal_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"format": FORMAT, "ts": now(), "device": self.device["id"], **entry}, ensure_ascii=False) + "\n")

    def _move(self, src, dst, ops):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        ops.append({"t": "move", "src": self.rel(src), "dst": self.rel(dst)})

    def _doc_update(self, doc_id, fields, ops):
        row = self.db.execute("SELECT * FROM docs WHERE id=?", (doc_id,)).fetchone()
        ops.append({"t": "update_doc", "id": doc_id, "before": {k: row[k] for k in fields}})
        sets = ", ".join(f"{k}=?" for k in fields)
        self.db.execute(f"UPDATE docs SET {sets} WHERE id=?", (*fields.values(), doc_id))

    def undo(self, batch=None):
        with self.lock:
            if batch is None:
                r = self.db.execute("SELECT * FROM journal WHERE undone=0 ORDER BY ts DESC, rowid DESC LIMIT 1").fetchone()
            else:
                r = self.db.execute("SELECT * FROM journal WHERE batch=? AND undone=0", (batch,)).fetchone()
            if not r:
                return {"ok": False, "msg": "Rien à annuler"}
            for op in reversed(json.loads(r["ops"])):
                t = op["t"]
                if t in ("insert_doc", "update_doc"):
                    self._dirty.add(op["id"])
                if t == "move":
                    d, s = self.abs(op["dst"]), self.abs(op["src"])
                    if os.path.exists(d):
                        os.makedirs(os.path.dirname(s), exist_ok=True)
                        shutil.move(d, s if not os.path.exists(s) else unique_path(os.path.dirname(s), os.path.basename(s)))
                elif t == "insert_doc":
                    self.db.execute("DELETE FROM docs WHERE id=?", (op["id"],))
                elif t == "update_doc":
                    b = op["before"]
                    self.db.execute(f"UPDATE docs SET {', '.join(k + '=?' for k in b)} WHERE id=?", (*b.values(), op["id"]))
                elif t == "inbox":
                    self.db.execute("UPDATE inbox SET state=?, path=? WHERE id=?", (op["state"], op["path"], op["id"]))
            self.db.execute("UPDATE journal SET undone=1 WHERE batch=?", (r["batch"],))
            self.db.commit()
            self._flush_meta()
            self._append_journal({"undo": r["batch"], "label": "Annulé : " + r["label"]})
            return {"ok": True, "msg": f"Annulé : {r['label']}"}

    def history(self, limit=30):
        rows = self.db.execute("SELECT batch,ts,label,undone FROM journal ORDER BY ts DESC, rowid DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------ entrée (Trier)
    def register(self, path, source):
        with self.lock:
            sha = sha256(path)
            if self.db.execute("SELECT 1 FROM inbox WHERE sha=? AND state='a_trier'", (sha,)).fetchone():
                return None
            iid = uuid.uuid4().hex[:12]
            text, method = reader.extract(path)
            self._cache_text(sha, text, method)
            a = classify.analyze(text, os.path.basename(path), self.settings["countries"])
            if self._ai_wanted(a, text):
                a["ai_pending"] = True
            a["method"] = method
            a["excerpt"] = (text or "").strip()[:600]
            self.db.execute("INSERT INTO inbox VALUES(?,?,?,?,?,?,?,?,?,?)",
                            (iid, self.rel(path), os.path.basename(path), sha, source, method, json.dumps(a), "{}", "a_trier", now()))
            self.db.commit()
            if a.get("ai_pending"):
                self._ai_kick()
            return iid

    # ---- IA locale en arrière-plan : l'écran n'est jamais bloqué
    def _ai_wanted(self, a, text):
        if not (self.settings.get("use_ollama") and self.settings.get("ollama_model")) or a["confidence"] == "haute":
            return False
        # IA lente sur cet ordinateur (essai > 60 s) : on ne la dérange que pour les documents « à vérifier »
        if self._ai_secs() > 60 and a["confidence"] != "basse":
            return False
        # mode « texte » (ordinateur modeste) : rien à demander si aucun texte n'a pu être lu
        return self.settings.get("ai_mode") == "vision" or len((text or "").strip()) >= 20

    def _ai_kick(self):
        if getattr(self, "_ai_thread", None) and self._ai_thread.is_alive():
            return
        self._ai_thread = threading.Thread(target=self._ai_worker, daemon=True)
        self._ai_thread.start()

    def _ai_worker(self):
        while True:
            with self.lock:
                rows = [r for r in self.db.execute("SELECT * FROM inbox WHERE state='a_trier'").fetchall()
                        if json.loads(r["analysis"]).get("ai_pending")]
            if not rows:
                return
            r = rows[0]
            a = json.loads(r["analysis"])
            path = self.abs(r["path"])
            try:
                text, _ = reader.extract(path) if os.path.exists(path) else ("", "")
                vision = self.settings.get("ai_mode") == "vision"
                img = reader.page_image(path) if vision and len((text or "").strip()) < 80 else None
                eng = ia.engine_by_id(self.settings.get("ai_engine") or "auto") or {"url": None, "kind": "", "name": ""}
                a = classify.refine_with_ai(a, text, r["orig_name"], eng, self.settings["ollama_model"], self.settings["countries"],
                                            img, timeout=self._ai_timeout(vision))
            except Exception as e:
                a["reasons"].append(f"IA locale indisponible ({type(e).__name__})")
            a["ai_pending"] = False
            with self.lock:
                cur = self.db.execute("SELECT state FROM inbox WHERE id=?", (r["id"],)).fetchone()
                if cur and cur["state"] == "a_trier":
                    self.db.execute("UPDATE inbox SET analysis=? WHERE id=?", (json.dumps(a), r["id"]))
                    self.db.commit()

    def _cache_text(self, sha, text, method):
        """Texte lu, gardé sur cet appareil seulement (index local) : évite de relire / refaire l'OCR."""
        self.db.execute("INSERT OR REPLACE INTO texts(sha,text,method) VALUES(?,?,?)", (sha, (text or "")[:50000], method))

    def text_of(self, sha, path=None):
        r = self.db.execute("SELECT text,method FROM texts WHERE sha=?", (sha,)).fetchone()
        if r:
            return r["text"] or "", r["method"]
        if path and os.path.exists(self.abs(path)):
            text, method = reader.extract(self.abs(path))
            self._cache_text(sha, text, method)
            self.db.commit()
            return text or "", method
        return "", None

    def reanalyze(self, cached=False):
        """Relit tous les documents à trier avec les règles actuelles (les corrections manuelles sont gardées).
        cached=True : réutilise le texte déjà lu (rapide, pas de nouvel OCR) — après l'ajout d'une règle."""
        with self.lock:
            n = 0
            for r in self.db.execute("SELECT * FROM inbox WHERE state='a_trier'").fetchall():
                p = self.abs(r["path"])
                if not os.path.exists(p):
                    continue
                if cached:
                    text, method = self.text_of(r["sha"], r["path"])
                    method = method or r["method"]
                else:
                    text, method = reader.extract(p)
                    self._cache_text(r["sha"], text, method)
                a = classify.analyze(text, r["orig_name"], self.settings["countries"])
                if self._ai_wanted(a, text):
                    a["ai_pending"] = True
                a["method"] = method
                a["excerpt"] = (text or "").strip()[:600]
                self.db.execute("UPDATE inbox SET analysis=?, method=? WHERE id=?", (json.dumps(a), method, r["id"]))
                n += 1
            self.db.commit()
        if not cached:
            self._ai_kick()
        return {"ok": True, "n": n}

    def add_upload(self, name, data):
        safe = re.sub(r"[/\\:]", "_", os.path.basename(name)) or "document"
        p = unique_path(self.inbox_dir, safe)
        with open(p, "wb") as f:
            f.write(data)
        return self.register(p, "Dépôt")

    def scan_inbox(self):
        known = {r["path"] for r in self.db.execute("SELECT path FROM inbox WHERE state='a_trier'")}
        added = 0
        for dirpath, dirs, files in os.walk(self.inbox_dir):
            dirs[:] = [d for d in dirs if not d.startswith((".", "_"))]
            for f in files:
                if f.startswith("."):
                    continue
                p = os.path.join(dirpath, f)
                if self.rel(p) not in known and self.register(p, "Dossier 00_A-TRIER"):
                    added += 1
        return added

    PERSONAL_CATS = ("01", "06", "09", "12", "15")

    def holder(self, a):
        """Titulaire du document : le nom saisi, sinon toi (nom des Réglages)."""
        h = (a.get("person") or "").strip()
        if not h or h.lower() == "moi":
            h = (self.settings.get("owner") or "").strip() or "moi"
        return h

    def _holder_key(self, a):
        h = self.holder(a)
        own = (self.settings.get("owner") or "").strip()
        return "moi" if h == "moi" or (own and classify.slugify(h).lower() == classify.slugify(own).lower()) else classify.slugify(h).lower()

    def _suivi_key(self, a):
        mode = TYPES[a["type"]].get("suivi", "none")
        hk = self._holder_key(a)
        if mode == "type":
            return f"{hk}|{a['country']}|{a['type']}"
        if mode == "emitter":
            return f"{hk}|{a['country']}|{a['type']}|{a['emitter']}"
        return None

    def display_label(self, a):
        T = TYPES[a["type"]]
        if (a.get("detail") or "").strip():
            lab = a["detail"].strip()
            if T.get("suivi") == "emitter" and a.get("emitter") and a["emitter"] != "Inconnu":
                lab += " — " + a["emitter"].replace("-", " ")
            return lab
        lab = T["label"]
        if a["type"] in ("avis_impot", "declaration_revenus", "ird_assessment") and a.get("date"):
            lab += f" {a['date'][:4]} (revenus {a.get('income_year') or int(a['date'][:4]) - 1})"
        if T.get("suivi") == "emitter" and a.get("emitter") and a["emitter"] != "Inconnu":
            lab += " — " + a["emitter"].replace("-", " ")
        return lab

    def make_name(self, a, ext):
        T = TYPES[a["type"]]
        obj = classify.slugify(a["detail"].strip())[:50] if (a.get("detail") or "").strip() else T["slug"]
        if T.get("period") == "month":
            obj += "-" + a["date"][:7]
        elif T.get("period") == "year":
            obj += "-" + a["date"][:4]
            if a["type"] in ("avis_impot", "declaration_revenus", "ird_assessment"):
                # l'avis reçu en 2025 porte sur les revenus 2024 : on l'écrit dans le nom
                inc = a.get("income_year") or str(int(a["date"][:4]) - 1)
                obj += "-revenus-" + inc
        h = self.holder(a)
        if T["cat"] in self.PERSONAL_CATS and h != "moi":
            obj += "-" + classify.slugify(h)
        return f"{a['date']}_{a['country']}_{T['cat']}_{classify.slugify(a['emitter'])}_{obj}{ext.lower()}"

    def proposal(self, row, overrides=None):
        a = json.loads(row["analysis"])
        ov = json.loads(row["overrides"] or "{}")
        ov.update(overrides or {})
        for k in ("type", "country", "emitter", "date", "expiry", "person", "detail"):
            if ov.get(k):
                a[k] = ov[k] if k != "emitter" else classify.slugify(ov[k])
        T = TYPES[a["type"]]
        ext = os.path.splitext(row["orig_name"])[1] or ".pdf"
        name = self.make_name(a, ext)
        key = self._suivi_key(a)
        p = {"id": row["id"], "orig": row["orig_name"], "source": row["source"], "method": row["method"],
             "type": a["type"], "type_label": T["label"], "label": self.display_label(a), "country": a["country"],
             "person": self.holder(a), "personal": T["cat"] in self.PERSONAL_CATS, "detail": a.get("detail") or "",
             "ai_pending": bool(a.get("ai_pending")), "date_note": None if ov.get("date") else a.get("date_note"),
             "emitter": a["emitter"], "date": a["date"], "expiry": a.get("expiry"), "confidence": a["confidence"],
             "reasons": a["reasons"], "excerpt": a.get("excerpt", ""), "name": name, "cat": T["cat"], "sub": T["sub"],
             "suivi": key, "overridden": bool(ov), "overrides": {k: v for k, v in ov.items() if k in ("type", "emitter", "detail", "country") and v}}
        dup = self.db.execute("SELECT id,label,path FROM docs WHERE sha=?", (row["sha"],)).fetchone()
        p["duplicate"] = dict(dup) if dup else None
        cur = self.db.execute("SELECT * FROM docs WHERE suivi=? AND status='actuel'", (key,)).fetchone() if key else None
        if T.get("archive"):
            p["mode"] = "archive_direct"
            dest = self.doc_dir(a["country"], a["type"], a["emitter"], archive=True)
            p["relation"] = "Rangé directement dans les Archives"
            if T.get("ends"):
                ek = f"moi|{a['country']}|{T['ends']}|{a['emitter']}"
                e = self.db.execute("SELECT label FROM docs WHERE suivi=? AND status='actuel'", (ek,)).fetchone()
                p["ends"] = ek
                if e:
                    p["relation"] += f" · termine le suivi « {e['label']} » (toutes ses versions passent dans Archives › Terminés)"
        elif cur and a["date"] >= cur["doc_date"]:
            p["mode"] = "new_version"
            dest = self.doc_dir(a["country"], a["type"], a["emitter"])
            p["relation"] = f"Nouvelle version de « {cur['label']} » : celle du {cur['doc_date']} part dans l'historique"
        elif cur:
            p["mode"] = "old_version"
            dest = self.doc_dir(a["country"], a["type"], a["emitter"], archive=True)
            p["relation"] = f"Version plus ancienne de « {cur['label']} » : rangée directement dans l'historique"
        else:
            p["mode"] = "new"
            dest = self.doc_dir(a["country"], a["type"], a["emitter"])
            p["relation"] = "Nouveau document suivi" if key else "Nouveau document"
        p["dest"] = self.rel(dest)
        p["_a"] = a
        return p

    def set_overrides(self, iid, overrides):
        with self.lock:
            row = self.db.execute("SELECT * FROM inbox WHERE id=?", (iid,)).fetchone()
            ov = json.loads(row["overrides"] or "{}")
            ov.update({k: v for k, v in overrides.items() if k in ("type", "country", "emitter", "date", "expiry", "person", "detail")})
            self.db.execute("UPDATE inbox SET overrides=? WHERE id=?", (json.dumps(ov), iid))
            self.db.commit()
            return self._pub(self.proposal(self.db.execute("SELECT * FROM inbox WHERE id=?", (iid,)).fetchone()))

    @staticmethod
    def _pub(p):
        return {k: v for k, v in p.items() if not k.startswith("_")}

    def inbox(self):
        rows = self.db.execute("SELECT * FROM inbox WHERE state='a_trier' ORDER BY added_at").fetchall()
        P = [self.proposal(r) for r in rows]
        # plusieurs versions du même document reçues ensemble : la plus récente deviendra la version actuelle
        groups = {}
        for p in P:
            if p["suivi"] and p["mode"] in ("new", "new_version"):
                groups.setdefault(p["suivi"], []).append(p)
        for g in groups.values():
            if len(g) < 2:
                continue
            g.sort(key=lambda x: x["date"])
            for x in g[:-1]:
                x["relation"] = f"Version plus ancienne de « {x['label']} » (reçue avec {len(g) - 1} autre{'s' if len(g) > 2 else ''}) : rangée dans l'historique"
            g[-1]["relation"] += f" · la plus récente des {len(g)} versions reçues, elle devient la version actuelle"
        return [self._pub(p) for p in P]

    def validate(self, ids):
        with self.lock:
            ops, done = [], 0
            dated = []
            for iid in ids:
                r = self.db.execute("SELECT * FROM inbox WHERE id=?", (iid,)).fetchone()
                if r:
                    dated.append((self.proposal(r)["date"], iid))
            for _, iid in sorted(dated):
                row = self.db.execute("SELECT * FROM inbox WHERE id=? AND state='a_trier'", (iid,)).fetchone()
                if not row:
                    continue
                p = self.proposal(row)
                a = p["_a"]
                T = TYPES[a["type"]]
                src = self.abs(row["path"])
                if not os.path.exists(src):
                    continue
                status = "actuel"
                if p["mode"] == "new_version":
                    cur = self.db.execute("SELECT * FROM docs WHERE suivi=? AND status='actuel'", (p["suivi"],)).fetchone()
                    old = self.abs(cur["path"])
                    if os.path.exists(old):
                        tgt = unique_path(self.doc_dir(cur["country"], cur["type"], cur["emitter"], archive=True), os.path.basename(old))
                        self._move(old, tgt, ops)
                        self._doc_update(cur["id"], {"status": "ancienne_version", "path": self.rel(tgt)}, ops)
                    else:
                        self._doc_update(cur["id"], {"status": "ancienne_version"}, ops)
                elif p["mode"] == "old_version":
                    status = "ancienne_version"
                elif p["mode"] == "archive_direct":
                    status = "termine"
                    if p.get("ends"):
                        for d in self.db.execute("SELECT * FROM docs WHERE suivi=? AND status IN ('actuel','ancienne_version')", (p["ends"],)).fetchall():
                            fields = {"status": "termine"}
                            if d["status"] == "actuel" and os.path.exists(self.abs(d["path"])):
                                tgt = unique_path(self.doc_dir(d["country"], d["type"], d["emitter"], archive=True), os.path.basename(d["path"]))
                                self._move(self.abs(d["path"]), tgt, ops)
                                fields["path"] = self.rel(tgt)
                            self._doc_update(d["id"], fields, ops)
                dst = unique_path(self.abs(p["dest"]), p["name"])
                self._move(src, dst, ops)
                did = uuid.uuid4().hex[:12]
                self.db.execute("INSERT INTO docs(id,suivi,type,label,person,country,cat,sub,emitter,doc_date,expiry,path,orig_name,sha,status,added_at,note) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                (did, p["suivi"], a["type"], p["label"], self.holder(a), a["country"], T["cat"], T["sub"], a["emitter"],
                                 a["date"], a.get("expiry"), self.rel(dst), row["orig_name"], row["sha"], status, now(), None))
                if a.get("detail"):
                    self.db.execute("UPDATE docs SET detail=? WHERE id=?", (a["detail"].strip(), did))
                ops.append({"t": "insert_doc", "id": did})
                ops.append({"t": "inbox", "id": iid, "state": "a_trier", "path": row["path"]})
                self.db.execute("UPDATE inbox SET state='range', path=? WHERE id=?", (self.rel(dst), iid))
                done += 1
            if not done:
                return {"ok": False, "done": 0}
            b = self._journal(f"{done} document{'s' if done > 1 else ''} rangé{'s' if done > 1 else ''}", ops)
            return {"ok": True, "done": done, "batch": b}

    def ignore(self, iid):
        with self.lock:
            row = self.db.execute("SELECT * FROM inbox WHERE id=? AND state='a_trier'", (iid,)).fetchone()
            if not row:
                return {"ok": False}
            ops = []
            src = self.abs(row["path"])
            if os.path.exists(src):
                dst = unique_path(os.path.join(self.inbox_dir, "_IGNORES"), os.path.basename(src))
                self._move(src, dst, ops)
                newp = self.rel(dst)
            else:
                newp = row["path"]
            ops.append({"t": "inbox", "id": iid, "state": "a_trier", "path": row["path"]})
            self.db.execute("UPDATE inbox SET state='ignore', path=? WHERE id=?", (newp, iid))
            b = self._journal("Document ignoré (gardé dans 00_A-TRIER/_IGNORES)", ops)
            return {"ok": True, "batch": b}

    # ------------------------------------------------------------ documents
    def _doc_pub(self, d):
        d = dict(d)
        d["cat_label"] = CATEGORIES.get(d["cat"], "")
        parts = (d["path"] or "").replace("\\", "/").split("/")[:-1]
        subs = [x for x in parts if d.get("sub") and x.startswith(d["sub"] + "_")]
        d["sub_folder"] = subs[-1] if subs else (parts[-1] if parts else "")
        d["emitter_folder"] = parts[-1] if subs and parts and parts[-1] != subs[-1] else None
        d["status_label"] = STATUS_LABEL.get(d["status"], d["status"])
        if d["suivi"]:
            d["versions"] = self.db.execute("SELECT COUNT(*) FROM docs WHERE suivi=?", (d["suivi"],)).fetchone()[0]
        else:
            d["versions"] = 1
        d["expired"] = bool(d["expiry"] and d["expiry"] < today().isoformat())
        return d

    def documents(self):
        rows = self.db.execute("SELECT * FROM docs WHERE status='actuel' ORDER BY country, cat, sub, doc_date DESC").fetchall()
        return [self._doc_pub(r) for r in rows]

    def document(self, did):
        d = self.db.execute("SELECT * FROM docs WHERE id=?", (did,)).fetchone()
        if not d:
            return None
        out = self._doc_pub(d)
        if d["suivi"]:
            vs = self.db.execute("SELECT * FROM docs WHERE suivi=? ORDER BY doc_date DESC", (d["suivi"],)).fetchall()
            out["history"] = [self._doc_pub(v) for v in vs]
        else:
            out["history"] = [out.copy()]
        used = []
        for k in self.db.execute("SELECT * FROM dossiers WHERE state!='abandonne'").fetchall():
            ids = set()
            if k["manifest"]:
                for pc in json.loads(k["manifest"])["pieces"]:
                    ids.update(f["doc_id"] for f in pc["files"])
            else:
                for pc in self.resolve(k)["pieces"]:
                    ids.update(x["id"] for x in pc["docs"])
            if ids & {h["id"] for h in out["history"]}:
                used.append({"id": k["id"], "label": TEMPLATES[k["template"]]["label"], "recipient": k["recipient"], "state": k["state"]})
        out["used_in"] = used
        out["egress"] = []
        return out

    def reclassify(self, did, fields, ops=None):
        """Corrige un document déjà rangé : type, pays, émetteur, dates. Renomme et déplace le fichier (annulable).
        ops fourni : l'action fait partie d'un lot (une seule annulation pour tout le lot)."""
        own = ops is None
        with self.lock:
            d = self.db.execute("SELECT * FROM docs WHERE id=?", (did,)).fetchone()
            if not d:
                return {"ok": False, "msg": "Document introuvable"}
            a = {"type": d["type"], "country": d["country"], "emitter": d["emitter"], "date": d["doc_date"], "expiry": d["expiry"], "person": d["person"], "detail": d["detail"]}
            for k in ("type", "country", "emitter", "date", "expiry", "person", "detail"):
                if k in fields and fields[k] is not None:
                    a[k] = classify.slugify(fields[k]) if k == "emitter" and fields[k] else (fields[k] or None)
            if a["type"] not in TYPES or a["country"] not in COUNTRIES:
                return {"ok": False, "msg": "Type ou pays inconnu"}
            a["emitter"] = a["emitter"] or "Inconnu"
            T = TYPES[a["type"]]
            key = self._suivi_key(a)
            ops = [] if own else ops
            status = d["status"]
            # conflit : un autre document suivi actuel du même type -> le plus ancien part dans l'historique
            if key and status == "actuel":
                other = self.db.execute("SELECT * FROM docs WHERE suivi=? AND status='actuel' AND id!=?", (key, did)).fetchone()
                if other:
                    if other["doc_date"] <= a["date"]:
                        o = self.abs(other["path"])
                        if os.path.exists(o):
                            tgt = unique_path(self.doc_dir(other["country"], other["type"], other["emitter"], archive=True), os.path.basename(o))
                            self._move(o, tgt, ops)
                            self._doc_update(other["id"], {"status": "ancienne_version", "path": self.rel(tgt)}, ops)
                    else:
                        status = "ancienne_version"
            folder = self.doc_dir(a["country"], a["type"], a["emitter"], archive=status != "actuel")
            src = self.abs(d["path"])
            ext = os.path.splitext(d["path"])[1] or ".pdf"
            dst = unique_path(folder, self.make_name(a, ext)) if os.path.abspath(os.path.join(folder, self.make_name(a, ext))) != src else src
            if dst != src and os.path.exists(src):
                self._move(src, dst, ops)
            self._doc_update(did, {"type": a["type"], "label": self.display_label(a), "country": a["country"], "cat": T["cat"],
                                   "sub": T["sub"], "emitter": a["emitter"], "doc_date": a["date"], "expiry": a.get("expiry"),
                                   "suivi": key, "path": self.rel(dst), "status": status, "person": self.holder(a),
                                   "detail": (a.get("detail") or "").strip() or None}, ops)
            if not own:
                return {"ok": True, "id": did}
            b = self._journal(f"Corrigé : {self.display_label(a)}", ops)
            return {"ok": True, "batch": b, "id": did}

    def redetect(self):
        """Relit le texte (déjà en mémoire) des documents rangés sans émetteur et retrouve l'émetteur
        (l'employeur pour les fiches de paie). Renomme et range dans le dossier de l'émetteur. Une seule annulation."""
        with self.lock:
            rows = self.db.execute("SELECT * FROM docs WHERE (emitter IS NULL OR emitter='' OR emitter='Inconnu') ORDER BY doc_date").fetchall()
            ops, changes, keys = [], [], set()
            for d in rows:
                text = self.text_of(d["sha"], d["path"])[0] or ""
                if not text.strip():
                    continue
                e, _cc, _how = classify._emitter(classify.norm(text), text, d["type"])
                if not e:
                    continue
                r = self.reclassify(d["id"], {"emitter": e}, ops)
                if r.get("ok"):
                    changes.append({"label": d["label"], "emitter": e.replace("-", " ")})
                    k = self.db.execute("SELECT suivi FROM docs WHERE id=?", (d["id"],)).fetchone()["suivi"]
                    if k:
                        keys.add(k)
            # chaque employeur retrouvé a son propre suivi : sa fiche la plus récente devient la version actuelle
            for k in keys:
                L = self.db.execute("SELECT * FROM docs WHERE suivi=? AND status IN ('actuel','ancienne_version') ORDER BY doc_date DESC", (k,)).fetchall()
                for i, d in enumerate(L):
                    want = "actuel" if i == 0 else "ancienne_version"
                    if d["status"] == want:
                        continue
                    src = self.abs(d["path"])
                    folder = self.doc_dir(d["country"], d["type"], d["emitter"], archive=want != "actuel")
                    fields = {"status": want}
                    if os.path.exists(src):
                        dst = unique_path(folder, os.path.basename(src))
                        self._move(src, dst, ops)
                        fields["path"] = self.rel(dst)
                    self._doc_update(d["id"], fields, ops)
            if not changes:
                return {"ok": True, "n": 0, "changes": []}
            b = self._journal(f"Émetteur retrouvé pour {len(changes)} document{'s' if len(changes) > 1 else ''}", ops)
            return {"ok": True, "n": len(changes), "changes": changes, "batch": b}

    def terminate(self, did):
        with self.lock:
            d = self.db.execute("SELECT * FROM docs WHERE id=?", (did,)).fetchone()
            if not d:
                return {"ok": False}
            rows = self.db.execute("SELECT * FROM docs WHERE suivi=? AND status!='termine'", (d["suivi"],)).fetchall() if d["suivi"] else [d]
            ops = []
            for r in rows:
                fields = {"status": "termine"}
                if r["status"] == "actuel" and os.path.exists(self.abs(r["path"])):
                    tgt = unique_path(self.doc_dir(r["country"], r["type"], r["emitter"], archive=True), os.path.basename(r["path"]))
                    self._move(self.abs(r["path"]), tgt, ops)
                    fields["path"] = self.rel(tgt)
                self._doc_update(r["id"], fields, ops)
            b = self._journal(f"Suivi terminé : {d['label']}", ops)
            return {"ok": True, "batch": b}

    # ------------------------------------------------------------ dossiers
    def create_dossier(self, template, recipient, country):
        with self.lock:
            did = uuid.uuid4().hex[:10]
            self.db.execute("INSERT INTO dossiers(id,template,recipient,country,created_at,state,assign) VALUES(?,?,?,?,?,?,?)",
                            (did, template, recipient.strip() or "Destinataire", country, now(), "en_cours", "{}"))
            self.db.commit()
            self._meta_dossier(did)
            return did

    def resolve(self, k):
        k = dict(k)
        T = TEMPLATES[k["template"]]
        assign = json.loads(k["assign"] or "{}")
        pieces = []
        t0 = today()
        for i, pc in enumerate(T["pieces"]):
            count = pc.get("count", 1)
            docs, source = [], "auto"
            if str(i) in assign:
                docs = [self.db.execute("SELECT * FROM docs WHERE id=?", (x,)).fetchone() for x in assign[str(i)]]
                docs = [d for d in docs if d]
                source = "choisi"
            else:
                for t in pc["types"]:
                    cur = self.db.execute("SELECT * FROM docs WHERE type=? AND country=? AND status='actuel' ORDER BY doc_date DESC",
                                          (t, k["country"])).fetchall()
                    if not cur:
                        continue
                    a = cur[0]
                    if count > 1 and a["suivi"]:
                        docs = self.db.execute("SELECT * FROM docs WHERE suivi=? AND status IN ('actuel','ancienne_version') "
                                               "ORDER BY doc_date DESC LIMIT ?", (a["suivi"], count)).fetchall()
                    else:
                        docs = [a]
                    break
            problems = []
            if docs:
                newest = max(docs, key=lambda d: d["doc_date"])
                if pc.get("valid") and newest["expiry"] and newest["expiry"] < t0.isoformat():
                    problems.append(f"expiré le {newest['expiry']}")
                if pc.get("fresh"):
                    age = (t0 - dt.date.fromisoformat(newest["doc_date"])).days
                    if age > pc["fresh"]:
                        problems.append(f"trop ancien ({age} jours, maximum {pc['fresh']})")
            have = len(docs)
            st = "ok" if have >= count and not problems else ("part" if have else "missing")
            pieces.append({"i": i, "label": pc["label"], "types": pc["types"], "count": count, "have": have, "status": st,
                           "problems": problems, "source": source,
                           "docs": [{"id": d["id"], "label": d["label"], "date": d["doc_date"], "path": d["path"], "status": d["status"]} for d in docs]})
        ok = sum(1 for p in pieces if p["status"] == "ok")
        return {"id": k["id"], "template": k["template"], "label": T["label"], "recipient": k["recipient"], "country": k["country"],
                "state": k["state"], "created_at": k["created_at"], "finalized_at": k["finalized_at"], "sent_at": k["sent_at"],
                "folder": k["folder"], "zip": k["zip"], "pieces": pieces, "ok": ok, "total": len(pieces),
                "manifest": json.loads(k["manifest"]) if k["manifest"] else None}

    def dossiers(self):
        rows = self.db.execute("SELECT * FROM dossiers WHERE state IN ('en_cours','finalise') ORDER BY created_at DESC").fetchall()
        return [self.resolve(r) for r in rows]

    def dossier(self, did):
        r = self.db.execute("SELECT * FROM dossiers WHERE id=?", (did,)).fetchone()
        return self.resolve(r) if r else None

    def assign(self, did, piece, doc_ids):
        with self.lock:
            r = self.db.execute("SELECT * FROM dossiers WHERE id=?", (did,)).fetchone()
            a = json.loads(r["assign"] or "{}")
            if doc_ids:
                a[str(piece)] = doc_ids
            else:
                a.pop(str(piece), None)
            self.db.execute("UPDATE dossiers SET assign=? WHERE id=?", (json.dumps(a), did))
            self.db.commit()
            self._meta_dossier(did)
            return self.dossier(did)

    def finalize(self, did):
        with self.lock:
            k = self.dossier(did)
            if k["state"] != "en_cours":
                return {"ok": False, "msg": "Dossier déjà finalisé"}
            if k["ok"] < k["total"]:
                return {"ok": False, "msg": "Il manque des pièces"}
            name = f"{today().isoformat()}_{classify.slugify(k['label'])}_{classify.slugify(k['recipient'])}"
            folder = unique_path(self.demarches_dir(k["country"]), name)
            os.makedirs(folder)
            man = {"dossier": k["label"], "destinataire": k["recipient"], "pays": k["country"], "cree_le": k["created_at"],
                   "finalise_le": now(), "envoye_le": None, "pieces": []}
            for pc in k["pieces"]:
                files = []
                for j, d in enumerate(pc["docs"]):
                    src = self.abs(d["path"])
                    fn = f"{pc['i'] + 1:02d}_{classify.slugify(pc['label'])[:40]}{'-' + str(j + 1) if pc['count'] > 1 else ''}__{os.path.basename(src)}"
                    dst = os.path.join(folder, fn)
                    shutil.copy2(src, dst)
                    files.append({"doc_id": d["id"], "fichier": fn, "source": d["path"], "version_du": d["date"], "sha256": sha256(dst)})
                man["pieces"].append({"label": pc["label"], "files": files})
            self._write_proof(folder, man)
            self._append_journal({"label": f"Préparé pour envoi : {k['label']} → {k['recipient']} ({sum(len(p['files']) for p in man['pieces'])} fichiers)"})
            z = folder + ".zip"
            with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in sorted(os.listdir(folder)):
                    zf.write(os.path.join(folder, f), os.path.join(os.path.basename(folder), f))
            self.db.execute("UPDATE dossiers SET state='finalise', folder=?, zip=?, manifest=?, finalized_at=? WHERE id=?",
                            (self.rel(folder), self.rel(z), json.dumps(man), man["finalise_le"], did))
            self.db.commit()
            self._meta_dossier(did)
            return {"ok": True, "dossier": self.dossier(did)}

    def _write_proof(self, folder, man):
        json.dump(man, open(os.path.join(folder, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        lines = [f"PREUVE BON TOUTOU — {man['dossier']}", f"Destinataire : {man['destinataire']}",
                 f"Finalisé le : {man['finalise_le']}", f"Envoyé le : {man['envoye_le'] or '(pas encore marqué comme envoyé)'}", "",
                 "Voici exactement ce qui a été transmis :", ""]
        for pc in man["pieces"]:
            lines.append(f"• {pc['label']}")
            for f in pc["files"]:
                lines.append(f"    {f['fichier']}\n      version du {f['version_du']} · SHA-256 {f['sha256']}")
        lines += ["", "Le SHA-256 est l'empreinte du fichier : si un seul octet change, l'empreinte change."]
        open(os.path.join(folder, "PREUVE.txt"), "w", encoding="utf-8").write("\n".join(lines))

    def reopen(self, did):
        with self.lock:
            k = self.db.execute("SELECT * FROM dossiers WHERE id=?", (did,)).fetchone()
            if k["state"] != "finalise":
                return {"ok": False}
            trash = os.path.join(self.fm, "corbeille", dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
            os.makedirs(trash, exist_ok=True)
            for r in (k["folder"], k["zip"]):
                if r and os.path.exists(self.abs(r)):
                    shutil.move(self.abs(r), os.path.join(trash, os.path.basename(r)))
            self.db.execute("UPDATE dossiers SET state='en_cours', folder=NULL, zip=NULL, manifest=NULL, finalized_at=NULL WHERE id=?", (did,))
            self.db.commit()
            self._meta_dossier(did)
            return {"ok": True}

    def mark_sent(self, did):
        with self.lock:
            k = self.db.execute("SELECT * FROM dossiers WHERE id=?", (did,)).fetchone()
            if k["state"] != "finalise":
                return {"ok": False}
            dest = self.sent_dir(k["country"])
            nf = unique_path(dest, os.path.basename(k["folder"]))
            shutil.move(self.abs(k["folder"]), nf)
            nz = None
            if k["zip"] and os.path.exists(self.abs(k["zip"])):
                nz = unique_path(dest, os.path.basename(k["zip"]))
                shutil.move(self.abs(k["zip"]), nz)
            man = json.loads(k["manifest"])
            man["envoye_le"] = now()
            self._write_proof(nf, man)
            self.db.execute("UPDATE dossiers SET state='envoye', folder=?, zip=?, manifest=?, sent_at=? WHERE id=?",
                            (self.rel(nf), self.rel(nz) if nz else None, json.dumps(man), man["envoye_le"], did))
            self.db.commit()
            self._meta_dossier(did)
            self._append_journal({"label": f"Dossier marqué envoyé : {TEMPLATES.get(k['template'], {}).get('label', k['template'])} → {k['recipient']}"})
            return {"ok": True}

    def abandon(self, did):
        with self.lock:
            self.db.execute("UPDATE dossiers SET state='abandonne' WHERE id=? AND state='en_cours'", (did,))
            self.db.commit()
            self._meta_dossier(did)
            return {"ok": True}

    # ------------------------------------------------------------ archives
    def archives(self):
        sent = []
        for k in self.db.execute("SELECT * FROM dossiers WHERE state='envoye' ORDER BY sent_at DESC").fetchall():
            man = json.loads(k["manifest"])
            for pc in man["pieces"]:
                for f in pc["files"]:
                    d = self.db.execute("SELECT suivi FROM docs WHERE id=?", (f["doc_id"],)).fetchone()
                    cur = self.db.execute("SELECT doc_date FROM docs WHERE suivi=? AND status='actuel'", (d["suivi"],)).fetchone() if d and d["suivi"] else None
                    f["remplacee_depuis"] = cur["doc_date"] if cur and cur["doc_date"] > f["version_du"] else None
            sent.append({"id": k["id"], "label": TEMPLATES[k["template"]]["label"], "recipient": k["recipient"], "country": k["country"],
                         "sent_at": k["sent_at"], "folder": k["folder"], "zip": k["zip"], "manifest": man,
                         "count": sum(len(p["files"]) for p in man["pieces"])})
        old = [self._doc_pub(r) for r in self.db.execute("SELECT * FROM docs WHERE status='ancienne_version' ORDER BY doc_date DESC")]
        done = [self._doc_pub(r) for r in self.db.execute("SELECT * FROM docs WHERE status='termine' ORDER BY country, sub, doc_date DESC")]
        return {"sent": sent, "old": old, "done": done}

    # ------------------------------------------------------------ index
    def rebuild_index(self):
        """Reconstruit l'index local : d'abord depuis les fiches (titulaire, intitulé, suivi… conservés),
        puis les fichiers rangés sans fiche sont relus d'après leur nom. Rien n'est déplacé."""
        with self.lock:
            bak = os.path.join(self.local, f"index-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.bak")
            self.db.commit()
            shutil.copy2(os.path.join(self.local, "index.db"), bak)
            self.db.execute("DELETE FROM docs")
            self.db.execute("DELETE FROM dossiers")
            from_meta = self._import_meta(full=True)
            known = {r["path"] for r in self.db.execute("SELECT path FROM docs")}
            known_sha = {r["sha"] for r in self.db.execute("SELECT sha FROM docs")}
            n = 0
            for cc, C in COUNTRIES.items():
                base = os.path.join(self.root, C["folder"])
                if not os.path.isdir(base):
                    continue
                for dirpath, dirs, files in os.walk(base):
                    dirs[:] = [d for d in dirs if not d.startswith((".", "_"))]
                    relp = self.rel(dirpath)
                    parts = relp.split(os.sep)
                    if len(parts) > 1 and parts[1].startswith("20_"):
                        continue
                    if len(parts) > 2 and parts[1].startswith("99_ARCHIVE") and parts[2].startswith("20_"):
                        continue
                    in_arch = len(parts) > 1 and parts[1].startswith("99_ARCHIVE")
                    for f in files:
                        if f.startswith(".") or f.endswith(".tmp"):
                            continue
                        p = os.path.join(dirpath, f)
                        if self.rel(p) in known:
                            continue
                        h = sha256(p)
                        if h in known_sha:
                            continue
                        m = NAME_RE.match(f)
                        a = classify.analyze("", f, [cc])
                        if m:
                            a["date"], a["country"], a["emitter"] = m.group(1), m.group(2) if m.group(2) in COUNTRIES else cc, m.group(4)
                        T = TYPES[a["type"]]
                        key = self._suivi_key(a)
                        did = uuid.uuid4().hex[:12]
                        self.db.execute("INSERT INTO docs(id,suivi,type,label,person,country,cat,sub,emitter,doc_date,expiry,path,orig_name,sha,status,added_at,note) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                        (did, key, a["type"], self.display_label(a), "moi", a["country"],
                                         m.group(3) if m else T["cat"], T["sub"], a["emitter"], a["date"], None, self.rel(p), f,
                                         h, "ancienne_version" if in_arch else "actuel", now(), "reconstruit"))
                        self._dirty.add(did)
                        n += 1
            # un seul « actuel » par suivi : le plus récent
            for r in self.db.execute("SELECT suivi FROM docs WHERE status='actuel' AND suivi IS NOT NULL GROUP BY suivi HAVING COUNT(*)>1").fetchall():
                rows = self.db.execute("SELECT id FROM docs WHERE suivi=? AND status='actuel' ORDER BY doc_date DESC", (r["suivi"],)).fetchall()
                for x in rows[1:]:
                    self.db.execute("UPDATE docs SET status='ancienne_version' WHERE id=?", (x["id"],))
                    self._dirty.add(x["id"])
            self.db.commit()
            self._flush_meta()
            total = self.db.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
            return {"ok": True, "docs": total, "from_meta": from_meta, "from_names": n, "backup": bak}

    # ------------------------------------------------------------ échéances, calendrier, contacts
    def events(self, horizon_days=730):
        """Dates à venir : expirations lues dans les documents actuels + échéances fixes des packs pays actifs."""
        t0 = today()
        out = []
        for d in self.db.execute("SELECT * FROM docs WHERE status='actuel' AND expiry IS NOT NULL AND expiry!=''").fetchall():
            try:
                e = dt.date.fromisoformat(d["expiry"])
            except ValueError:
                continue
            out.append({"t": d["label"], "d": e.isoformat(), "cc": d["country"], "c": d["cat"], "k": "expire", "id": d["id"],
                        "past": e < t0})
        for cc, label, jour, cat, note, org in catalog.ECHEANCES:
            if cc and cc not in (self.settings.get("countries") or []):
                continue
            m, j = int(jour[:2]), int(jour[3:])
            for y in (t0.year, t0.year + 1):
                try:
                    e = dt.date(y, m, j)
                except ValueError:
                    continue
                if e >= t0:
                    out.append({"t": label, "d": e.isoformat(), "cc": cc or "INT", "c": cat, "k": "à faire", "note": note})
                    break
        lim = (t0 + dt.timedelta(days=horizon_days)).isoformat()
        return sorted([e for e in out if e["d"] <= lim or e.get("past")], key=lambda e: e["d"])

    def ics(self):
        """Fichier calendrier (.ics) à importer dans Calendrier, Google Agenda, Outlook… Généré ici, rien ne sort."""
        def esc_ics(x):
            return str(x).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
        stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Bon toutou//Echeances//FR", "CALSCALE:GREGORIAN",
             "X-WR-CALNAME:Bon toutou — échéances"]
        for e in self.events():
            if e.get("past"):
                continue
            d = e["d"].replace("-", "")
            nxt = (dt.date.fromisoformat(e["d"]) + dt.timedelta(days=1)).strftime("%Y%m%d")
            uid = hashlib.sha1(f"{e['t']}|{e['d']}|{e.get('id', '')}".encode()).hexdigest()[:16] + "@bontoutou"
            what = "expire" if e["k"] == "expire" else "à faire"
            L += ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{stamp}", f"DTSTART;VALUE=DATE:{d}", f"DTEND;VALUE=DATE:{nxt}",
                  f"SUMMARY:{esc_ics(e['t'] + ' — ' + what)}",
                  f"DESCRIPTION:{esc_ics((e.get('note') or 'Date lue dans tes documents par Bon toutou.') + ' Pays : ' + e['cc'])}",
                  "BEGIN:VALARM", "TRIGGER:-P30D", "ACTION:DISPLAY", f"DESCRIPTION:{esc_ics(e['t'])} dans 30 jours", "END:VALARM",
                  "END:VEVENT"]
        L.append("END:VCALENDAR")
        return "\r\n".join(L) + "\r\n"

    def contacts(self):
        """Tes interlocuteurs, tirés de tes documents (émetteurs) et de tes dossiers (destinataires), avec ce qui leur a été transmis."""
        C = {}
        for d in self.db.execute("SELECT emitter,country,cat,label,doc_date,status FROM docs").fetchall():
            if not d["emitter"] or d["emitter"] == "Inconnu":
                continue
            k = ("org", d["emitter"].lower())
            c = C.setdefault(k, {"nom": d["emitter"].replace("-", " "), "role": "Organisme émetteur", "cc": d["country"], "cat": d["cat"],
                                 "docs": 0, "dernier": "", "transmis": []})
            c["docs"] += 1
            c["dernier"] = max(c["dernier"], d["doc_date"] or "")
        for k in self.db.execute("SELECT * FROM dossiers WHERE state!='abandonne'").fetchall():
            T = TEMPLATES.get(k["template"], {"label": k["template"], "pieces": []})
            key = ("dest", (k["recipient"] or "").lower())
            c = C.setdefault(key, {"nom": k["recipient"], "role": "Destinataire de dossiers", "cc": k["country"], "cat": None,
                                   "docs": 0, "dernier": "", "transmis": []})
            n = 0
            if k["manifest"]:
                n = sum(len(p["files"]) for p in json.loads(k["manifest"])["pieces"])
            c["transmis"].append({"id": k["id"], "label": T["label"], "etat": k["state"], "date": (k["sent_at"] or k["created_at"] or "")[:10], "pieces": n})
            first = next((pc["types"][0] for pc in T["pieces"] if pc.get("types")), None)
            if not c["cat"] and first in TYPES:
                c["cat"] = TYPES[first]["cat"]
        return sorted(C.values(), key=lambda c: (c["cat"] or "99", c["nom"].lower()))

    # ------------------------------------------------------------ état général
    def state(self):
        c = lambda q: self.db.execute(q).fetchone()[0]
        return {
            "root": self.root,
            "settings": self.settings,
            "tools": reader.tools(),
            "ia": {"machine": self._machine(), "engines": ia.engines(), "catalogue": ia.catalogue(), "pulls": ia.PULLS},
            "counts": {"inbox": c("SELECT COUNT(*) FROM inbox WHERE state='a_trier'"),
                       "docs": c("SELECT COUNT(*) FROM docs WHERE status='actuel'"),
                       "old": c("SELECT COUNT(*) FROM docs WHERE status='ancienne_version'"),
                       "done": c("SELECT COUNT(*) FROM docs WHERE status='termine'"),
                       "dossiers": c("SELECT COUNT(*) FROM dossiers WHERE state IN ('en_cours','finalise')"),
                       "sent": c("SELECT COUNT(*) FROM dossiers WHERE state='envoye'"),
                       "egress": len(self.sorties())},
            "types": {k: {"label": v["label"], "cat": v["cat"]} for k, v in TYPES.items()},
            "countries": {k: v["name"] for k, v in COUNTRIES.items()},
            "categories": CATEGORIES, "subs": SUB_FOLDERS_FR,
            "templates": {k: v["label"] for k, v in TEMPLATES.items()},
            "tpl": {k: {"label": v["label"], "n": len(v.get("pieces", [])), "ic": v.get("icone", "")} for k, v in TEMPLATES.items()},
            "orgs": [{"cc": o[0], "nom": o[1], "url": o[2], "note": o[3]} for o in catalog.ORGS if o[0] in self.settings["countries"]],
            "sorties": self.sorties()[:30], "packs": catalog.PACKS, "events": self.events(),
            "local_only": c("SELECT COUNT(*) FROM docs WHERE status='actuel' AND cat IN (%s)" % ",".join(
                "'%s'" % k for k, v in self.settings["privacy"].items() if v == "local") if any(v == "local" for v in self.settings["privacy"].values()) else "SELECT 0"),
            "archives_n": c("SELECT COUNT(*) FROM docs WHERE status!='actuel'") + c("SELECT COUNT(*) FROM dossiers WHERE state='envoye'"),
            "dossiers_open": [{"id": r["id"], "label": TEMPLATES.get(r["template"], {}).get("label", r["template"]), "recipient": r["recipient"],
                               "missing": (lambda k: k["total"] - k["ok"])(self.resolve(r))}
                              for r in self.db.execute("SELECT * FROM dossiers WHERE state='en_cours' ORDER BY created_at DESC").fetchall()],
            "high": len([p for p in self.inbox() if p["confidence"] == "haute" and not p.get("duplicate")]), "catalog_warnings": catalog.WARNINGS, "newer_data": self.newer_data,
            "privacy_levels": sortie.LEVELS, "device": self.device, "local_data": self.local, "format": FORMAT,
            "today": today().isoformat(),
            "unknown_emitters": c("SELECT COUNT(*) FROM docs WHERE status!='termine' AND (emitter IS NULL OR emitter='' OR emitter='Inconnu')"),
        }

    @staticmethod
    def _launch(p, reveal=False):
        """Ouvre un fichier avec l'app par défaut de l'ordinateur (Aperçu, Calendrier…), ou le montre dans le Finder."""
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", "-R", p] if reveal else ["open", p])
            elif os.name == "nt":
                subprocess.Popen(["explorer", "/select,", p]) if reveal else os.startfile(p)  # noqa
            else:
                subprocess.Popen(["xdg-open", os.path.dirname(p) if reveal else p])
            return {"ok": True}
        except Exception as e:  # pas d'app pour ce type de fichier, système sans bureau…
            return {"ok": False, "msg": f"Impossible d'ouvrir ce fichier ici ({type(e).__name__})"}

    def reveal(self, relpath):
        return self._launch(self.abs(relpath), reveal=True)

    def open_path(self, relpath=None, inbox=None):
        """Ouvre un document (ou un fichier en attente dans Trier) avec l'app par défaut."""
        if inbox:
            r = self.db.execute("SELECT path FROM inbox WHERE id=?", (inbox,)).fetchone()
            if not r:
                return {"ok": False, "msg": "Fichier introuvable"}
            relpath = r["path"]
        p = self.abs(relpath)
        if not os.path.exists(p):
            return {"ok": False, "msg": "Fichier introuvable"}
        return self._launch(p)

    def export(self, kind, text=None):
        """Enregistre un fichier dans ton dossier Téléchargements (l'app ne sait pas « télécharger ») puis l'ouvre ou le montre.
        ics : le calendrier s'ouvre et propose l'import. regles / proposition : le fichier est montré dans le Finder."""
        if kind == "ics":
            name, data, show = "bon-toutou-echeances.ics", self.ics(), False
        elif kind == "regles":
            name, data, show = "bon-toutou-mes-regles.json", json.dumps(self.regles.export(), ensure_ascii=False, indent=1), True
        elif kind == "proposition" and text:
            name, data, show = "bon-toutou-proposition.json", str(text), True
        else:
            return {"ok": False, "msg": "Export inconnu"}
        home = os.path.expanduser("~")
        folder = next((d for d in (os.path.join(home, "Downloads"), os.path.join(home, "Téléchargements")) if os.path.isdir(d)), home)
        dst = os.path.join(folder, name)
        if os.path.exists(dst):  # on ne réécrit que notre propre export de calendrier ; jamais un autre fichier
            prev = open(dst, encoding="utf-8", errors="ignore").read(200) if kind == "ics" else ""
            if not (prev.startswith("BEGIN:VCALENDAR") and "PRODID:-//Bon toutou//" in prev):
                dst = unique_path(folder, name)
        with open(dst, "w", encoding="utf-8") as fh:
            fh.write(data)
        r = self._launch(dst, reveal=show)
        r.update({"path": dst, "folder": os.path.basename(folder)})
        return r
