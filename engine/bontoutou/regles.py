"""Règles et types créés par l'utilisateur (fichier <bureau>/.bontoutou/mes-regles.json, même format qu'un pack).

Une règle : « quand un document contient <indice> → <champ> = <valeur> » (champ : type, émetteur, intitulé, pays).
L'indice est un texte exact choisi dans le document, jamais une formule : impossible de bloquer l'app avec.
Rien n'est appris en douce : chaque règle est créée, vue, modifiable et supprimable par l'utilisateur.
"""
import datetime as dt
import json
import os
import re
import urllib.parse
import uuid

from . import catalog, classify
from .catalog import COUNTRIES, TYPES

FORMAT = 1


def _now():
    return dt.datetime.now().isoformat(timespec="seconds")


class Regles:
    def __init__(self, bureau):
        self.b = bureau
        self.path = os.path.join(bureau.fm, "mes-regles.json")

    # ------------------------------------------------------------ fichier
    def data(self):
        d = {}
        if os.path.exists(self.path):
            try:
                d = json.load(open(self.path, encoding="utf-8"))
            except Exception:
                d = {}
        d.setdefault("format", FORMAT)
        d.setdefault("id", "perso")
        d.setdefault("name", "Mes règles")
        d.setdefault("rules", [])
        d.setdefault("types", {})
        return d

    def _save(self, d):
        d["format"] = max(int(d.get("format", FORMAT) or FORMAT), FORMAT)
        d["updated_at"] = _now()
        from .core import write_json
        write_json(self.path, d)
        self.b.reload_catalog()

    # ------------------------------------------------------------ lecture
    def sentence(self, r):
        t = f" (seulement pour : {TYPES[r['type']]['label']})" if r.get("type") in TYPES and r.get("champ") != "type" else ""
        return "Quand un document " + classify.rule_text(r["indice"], r["champ"], r["valeur"]) + t

    def state(self):
        d = self.data()
        rules = []
        for r in d["rules"]:
            rules.append({**r, "phrase": self.sentence(r)})
        types = [{"id": k, **{x: v for x, v in t.items() if not x.startswith("_")}} for k, t in d["types"].items()]
        imported = []
        imp = os.path.join(self.b.fm, "packs")
        if os.path.isdir(imp):
            for n in sorted(os.listdir(imp)):
                if n.endswith(".json"):
                    p = catalog._read(os.path.join(imp, n)) or {}
                    imported.append({"file": n, "id": p.get("id", n), "name": p.get("name", n), "version": p.get("version", ""),
                                     "types": len(p.get("types", {})), "rules": len(p.get("rules", [])),
                                     "disabled": p.get("id", n) in (self.b.settings.get("disabled_packs") or [])})
        return {"rules": rules, "types": types, "imported": imported, "contribution": dict(catalog.CONTRIBUTION),
                "warnings": list(catalog.WARNINGS)}

    # ------------------------------------------------------------ effet d'une règle
    def _hay(self, text, name):
        return classify.norm(text) + " \n " + classify.norm((name or "").replace("_", " ").replace("-", " "))

    def matches(self, r, text, name, type_id=None):
        if r.get("type") and r["champ"] != "type" and r["type"] != type_id:
            return False
        return classify._has(self._hay(text, name), classify.norm(r["indice"]))

    def _current(self, d, champ):
        return {"type": d["type"], "emitter": d["emitter"], "detail": d["detail"] or "", "country": d["country"]}[champ]

    def _target(self, r):
        return classify.slugify(r["valeur"])[:30] if r["champ"] == "emitter" else r["valeur"]

    def preview(self, r):
        """Documents rangés (actuels et anciens) que la règle changerait, et documents à trier concernés."""
        r = self._clean(r)
        if isinstance(r, str):
            return {"ok": False, "msg": r}
        docs = []
        for d in self.b.db.execute("SELECT * FROM docs WHERE status IN ('actuel','ancienne_version','termine')").fetchall():
            text, _ = self.b.text_of(d["sha"], d["path"])
            if not self.matches(r, text, d["orig_name"], d["type"]):
                continue
            cur, new = self._current(d, r["champ"]), self._target(r)
            if str(cur) != str(new):
                lab = lambda v: TYPES[v]["label"] if r["champ"] == "type" and v in TYPES else (v or "—")
                docs.append({"id": d["id"], "label": d["label"], "date": d["doc_date"],
                             "change": f"{classify.FIELD_LABEL[r['champ']]} : {lab(cur)} → {lab(new)}"})
        inbox = []
        for row in self.b.db.execute("SELECT * FROM inbox WHERE state='a_trier'").fetchall():
            text, _ = self.b.text_of(row["sha"], row["path"])
            a = json.loads(row["analysis"])
            if self.matches(r, text, row["orig_name"], a.get("type")):
                inbox.append({"id": row["id"], "orig": row["orig_name"]})
        return {"ok": True, "phrase": self.sentence(r), "docs": docs, "inbox": inbox}

    # ------------------------------------------------------------ écriture
    def _clean(self, r):
        r = {k: (str(v).strip() if isinstance(v, str) else v) for k, v in (r or {}).items()}
        if r.get("champ") not in catalog.RULE_FIELDS:
            return "Choisis ce que la règle doit fixer : type, émetteur, intitulé ou pays."
        if not r.get("indice") or len(r["indice"]) < 3:
            return "Choisis au moins un mot (3 lettres ou plus) dans le document."
        if len(r["indice"]) > catalog.MAX_INDICE:
            return "Indice trop long : garde quelques mots caractéristiques."
        if not r.get("valeur"):
            return "Indique la valeur à appliquer."
        if r["champ"] == "type" and r["valeur"] not in TYPES:
            return "Type inconnu."
        if r["champ"] == "country" and r["valeur"] not in COUNTRIES:
            return "Pays inconnu."
        if r.get("type") and r["type"] not in TYPES:
            r["type"] = None
        return {"id": r.get("id") or "r" + uuid.uuid4().hex[:8], "indice": r["indice"], "champ": r["champ"],
                "valeur": r["valeur"], "type": r.get("type") or None, "actif": r.get("actif", True) is not False,
                "cree_le": r.get("cree_le") or _now(), "source": r.get("source") or "correction"}

    def save(self, r):
        r = self._clean(r)
        if isinstance(r, str):
            return {"ok": False, "msg": r}
        d = self.data()
        d["rules"] = [x for x in d["rules"] if x.get("id") != r["id"]] + [r]
        self._save(d)
        self.b.reanalyze(cached=True)  # les documents à trier en profitent tout de suite
        return {"ok": True, "rule": {**r, "phrase": self.sentence(r)}, "preview": self.preview(r)}

    def toggle(self, rid, actif):
        d = self.data()
        for x in d["rules"]:
            if x.get("id") == rid:
                x["actif"] = bool(actif)
        self._save(d)
        self.b.reanalyze(cached=True)
        return {"ok": True}

    def delete(self, rid):
        d = self.data()
        gone = [x for x in d["rules"] if x.get("id") == rid]
        d["rules"] = [x for x in d["rules"] if x.get("id") != rid]
        d.setdefault("supprimees", []).extend({**x, "supprimee_le": _now()} for x in gone)  # gardées, au cas où
        self._save(d)
        self.b.reanalyze(cached=True)
        return {"ok": True}

    def apply(self, rid, doc_ids):
        """Applique une règle à des documents déjà rangés : un seul lot, une seule annulation."""
        r = next((x for x in self.data()["rules"] if x.get("id") == rid), None)
        if not r:
            return {"ok": False, "msg": "Règle introuvable"}
        ops, n = [], 0
        with self.b.lock:
            for did in doc_ids:
                res = self.b.reclassify(did, {r["champ"]: r["valeur"]}, ops=ops)
                n += 1 if res.get("ok") else 0
            if not n:
                return {"ok": False, "msg": "Aucun document corrigé"}
            batch = self.b._journal(f"Règle appliquée à {n} document{'s' if n > 1 else ''} : {self.sentence(r)}", ops)
        return {"ok": True, "n": n, "batch": batch}

    def test(self, rid, did):
        r = next((x for x in self.data()["rules"] if x.get("id") == rid), None)
        d = self.b.db.execute("SELECT * FROM docs WHERE id=?", (did,)).fetchone()
        if not r or not d:
            return {"ok": False, "msg": "Règle ou document introuvable"}
        text, _ = self.b.text_of(d["sha"], d["path"])
        hit = self.matches(r, text, d["orig_name"], d["type"])
        cur = self._current(d, r["champ"])
        return {"ok": True, "match": hit, "label": d["label"],
                "msg": (f"S'applique : {classify.FIELD_LABEL[r['champ']]} {cur or '—'} → {self._target(r)}" if hit and str(cur) != str(self._target(r))
                        else "S'applique, et le document est déjà comme ça" if hit else "Ne s'applique pas : l'indice n'est pas dans ce document")}

    # ------------------------------------------------------------ nouveaux types
    def save_type(self, t):
        label = (t.get("label") or "").strip()
        cat, sub = (t.get("cat") or "").strip(), (t.get("sub") or "").strip()
        if not label:
            return {"ok": False, "msg": "Donne un nom au type de document."}
        if cat not in catalog.CATEGORIES or not sub.startswith(cat + "-") or sub not in catalog.SUB_FOLDERS_FR:
            return {"ok": False, "msg": "Choisis une catégorie et un sous-dossier."}
        kw = [k.strip() for k in (t.get("kw") or []) if isinstance(k, str) and len(k.strip()) >= 3][:12]
        if not kw:
            return {"ok": False, "msg": "Choisis au moins un mot qui le reconnaît (3 lettres ou plus)."}
        tid = t.get("id") or "perso_" + classify.slugify(label).lower().replace("-", "_")[:40]
        d = self.data()
        d["types"][tid] = {"label": label, "slug": classify.slugify(label)[:40], "cat": cat, "sub": sub,
                           "suivi": t.get("suivi") if t.get("suivi") in ("type", "emitter", "none") else "none",
                           "expiry": bool(t.get("expiry")), "kw": [classify.norm(k) for k in kw], "fn": [],
                           "cree_le": d["types"].get(tid, {}).get("cree_le") or _now()}
        self._save(d)
        self.b.reanalyze(cached=True)
        return {"ok": True, "id": tid}

    # ------------------------------------------------------------ partage
    def export(self, ids=None, type_ids=None):
        d = self.data()
        rules = [x for x in d["rules"] if x.get("actif", True) and (ids is None or x["id"] in ids)]
        types = {k: v for k, v in d["types"].items() if type_ids is None or k in type_ids}
        clean = lambda x: {k: v for k, v in x.items() if k in ("id", "indice", "champ", "valeur", "type")}
        return {"format": FORMAT, "id": "partage-" + uuid.uuid4().hex[:6], "name": "Règles partagées",
                "version": dt.date.today().isoformat(), "official": False,
                "description": "Règles et types créés dans Bon toutou. Données seulement.",
                "rules": [clean(x) for x in rules], "types": types}

    def personal_flags(self, pack):
        """Repère ce qui pourrait être personnel avant un partage : à relire, retirer ou remplacer."""
        owner = [w for w in classify.norm(self.b.settings.get("owner") or "").replace("-", " ").split() if len(w) >= 3]
        holders = [classify.norm(h.get("nom", "")) for h in (self.b.settings.get("holders") or []) if h.get("nom")]
        flags = []
        vals = [(f"règle « {r['indice']} »", r["indice"]) for r in pack.get("rules", [])] + \
               [(f"règle « {r['indice']} »", r["valeur"]) for r in pack.get("rules", [])] + \
               [(f"type « {t.get('label')} »", " ".join([t.get("label", "")] + t.get("kw", []))) for t in pack.get("types", {}).values()]
        for where, v in vals:
            n = classify.norm(v)
            why = []
            if any(w in n for w in owner) or any(h and h in n for h in holders):
                why.append("ton nom ou celui d'un proche")
            if re.search(r"\d{5,}", v):
                why.append("un long numéro")
            if re.search(r"@|\brue\b|\bavenue\b|\bboulevard\b|\bchemin\b|\broad\b|\bstreet\b", n):
                why.append("une adresse")
            if why:
                flags.append(f"{where} contient peut-être {', '.join(why)}")
        return sorted(set(flags))

    def propose(self, ids=None, type_ids=None):
        pack = self.export(ids, type_ids)
        body = json.dumps(pack, ensure_ascii=False, indent=1)
        c = catalog.CONTRIBUTION
        mailto = None
        if c.get("email"):
            mailto = "mailto:" + c["email"] + "?" + urllib.parse.urlencode(
                {"subject": "Proposition de règles Bon toutou", "body": "Bonjour,\n\nVoici des règles à intégrer dans une future version :\n\n" + body}, quote_via=urllib.parse.quote)
        return {"ok": True, "pack": pack, "text": body, "flags": self.personal_flags(pack), "mailto": mailto, "url": c.get("url")}

    def import_pack(self, raw, confirm=False):
        try:
            p = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
        except Exception:
            return {"ok": False, "msg": "Ce fichier n'est pas un pack Bon toutou lisible."}
        if not isinstance(p, dict) or not (p.get("rules") or p.get("types") or p.get("emitters")):
            return {"ok": False, "msg": "Ce fichier ne contient ni règle ni type."}
        p["official"] = False
        pid = classify.slugify(str(p.get("id") or "import-" + uuid.uuid4().hex[:6])).lower()[:40]
        p["id"] = pid
        rules = [self._clean(r) for r in p.get("rules", [])]
        ok_rules = [r for r in rules if isinstance(r, dict)]
        n_docs = 0
        for d in self.b.db.execute("SELECT * FROM docs WHERE status='actuel'").fetchall():
            text, _ = self.b.text_of(d["sha"], d["path"])
            if any(self.matches(r, text, d["orig_name"], d["type"]) for r in ok_rules):
                n_docs += 1
        summary = {"ok": True, "id": pid, "name": p.get("name", pid), "types": len(p.get("types", {})),
                   "rules": len(ok_rules), "refused": len(rules) - len(ok_rules), "docs": n_docs,
                   "signed": False}
        if not confirm:
            return summary
        from .core import write_json
        write_json(os.path.join(self.b.fm, "packs", pid + ".json"), p)
        self.b.reload_catalog()
        self.b.reanalyze(cached=True)
        return summary

    def remove_pack(self, file):
        src = os.path.join(self.b.fm, "packs", os.path.basename(file))
        if not os.path.exists(src):
            return {"ok": False}
        dst_dir = os.path.join(self.b.fm, "packs", "_retires")
        os.makedirs(dst_dir, exist_ok=True)
        os.replace(src, os.path.join(dst_dir, dt.datetime.now().strftime("%Y%m%d-%H%M%S_") + os.path.basename(file)))
        self.b.reload_catalog()
        self.b.reanalyze(cached=True)
        return {"ok": True}
