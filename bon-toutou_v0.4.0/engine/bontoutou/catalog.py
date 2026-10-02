"""Catalogue Bon toutou : chargé depuis des « packs » de données (JSON), jamais du code.

Ordre de priorité (le plus fort en dernier) :
  1. packs officiels        bontoutou/packs/*.json          (livrés avec l'app, signés plus tard)
  2. packs importés          <bureau>/.bontoutou/packs/*.json (partagés par quelqu'un, avertissement)
  3. règles perso            <bureau>/.bontoutou/mes-regles.json

Un pack ne contient que des données : des mots à chercher, des endroits où ranger.
Il ne peut rien exécuter, rien envoyer, rien effacer.

Les noms exportés (TYPES, EMITTERS, DETAILS…) gardent la même identité en mémoire :
`load()` les remplit sur place, donc `from .catalog import TYPES` reste valable après un rechargement.
"""
import json
import os
import re

FORMAT = 1  # version du format des packs que cette version de Bon toutou sait lire
OFFICIAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "packs")
OFFICIAL_ORDER = ["socle", "pays-fr", "pays-nz", "pays-int", "demarches"]

COUNTRIES = {}
CATEGORIES = {}
CAT_FOLDERS_FR = {}
SUB_FOLDERS_FR = {}
COUNTRY_HINTS = {}
EMITTERS = []        # (motif, nom affiché, pays, origine)
TYPES = {}           # chaque type porte "_origin"
DETAILS = {}         # type -> [(motif, modèle, origine)]
EXPIRY_HINTS = []
TEMPLATES = {}
ORGS = []            # (pays, nom, url https ou "", note) : organismes à prévenir (packs officiels seulement)
ECHEANCES = []       # (pays, libellé, MM-JJ, catégorie, note, origine) : dates fixes de l'année (déclarations…)
RULES = []           # règles « contient X → champ = valeur » : (indice, champ, valeur, type, origine, id)
CONTRIBUTION = {}    # où envoyer une proposition (pack Socle) : {"email": ..., "url": ...}
PACKS = []           # résumé des packs chargés (pour Réglages)
WARNINGS = []        # règles refusées, packs illisibles…

LIST_FIELDS = ("kw", "fn", "must")
RULE_FIELDS = ("type", "emitter", "detail", "country")
MAX_INDICE = 120
MAX_PATTERN = 200
# quantificateur imbriqué, ex. (a+)+ : peut bloquer la recherche -> refusé hors packs officiels
NESTED = re.compile(r"\([^)]*[+*][^)]*\)\s*[+*{]")


def _origin(p):
    return f"{p.get('name', p.get('id', '?'))} {p.get('version', '')}".strip()


def _safe_pattern(pat, official):
    if not isinstance(pat, str):
        return False
    if not official and (len(pat) > MAX_PATTERN or NESTED.search(pat)):
        return False
    try:
        re.compile(pat)
        return True
    except re.error:
        return False


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            p = json.load(f)
    except Exception as e:
        WARNINGS.append(f"Pack illisible : {os.path.basename(path)} ({type(e).__name__})")
        return None
    if not isinstance(p, dict):
        return None
    try:
        if int(p.get("format", 1)) > FORMAT:
            WARNINGS.append(f"« {p.get('name', os.path.basename(path))} » vient d'une version plus récente de Bon toutou : lu en partie")
    except (TypeError, ValueError):
        pass
    return p


def _apply(p, kind):
    """Ajoute un pack au catalogue. kind : officiel | importe | perso."""
    official = kind == "officiel"
    org = "Règle perso" if kind == "perso" else _origin(p)
    COUNTRIES.update(p.get("countries", {}))
    CATEGORIES.update(p.get("categories", {}))
    CAT_FOLDERS_FR.update(p.get("cat_folders", {}))
    SUB_FOLDERS_FR.update(p.get("sub_folders", {}))
    for cc, hints in p.get("country_hints", {}).items():
        COUNTRY_HINTS.setdefault(cc, [])
        COUNTRY_HINTS[cc].extend(h for h in hints if h not in COUNTRY_HINTS[cc])
    for h in p.get("expiry_hints", []):
        if h not in EXPIRY_HINTS:
            EXPIRY_HINTS.append(h)
    em = [(e[0], e[1], e[2], org) for e in p.get("emitters", [])
          if isinstance(e, (list, tuple)) and len(e) >= 3 and isinstance(e[0], str) and e[0].strip()]
    if official:
        EMITTERS.extend(em)
    else:
        EMITTERS[:0] = em  # les émetteurs perso / importés sont essayés en premier
    n_rules = 0
    for tid, t in p.get("types", {}).items():
        if not isinstance(t, dict):
            continue
        t = dict(t)
        details = t.pop("details", [])
        if tid in TYPES:  # le pack complète un type existant
            cur = TYPES[tid]
            for k, v in t.items():
                if k in LIST_FIELDS and isinstance(v, list):
                    cur[k] = list(dict.fromkeys(list(cur.get(k, [])) + v))
                elif not k.startswith("_"):
                    cur[k] = v
            if t and not official:
                cur["_origin"] = org
        else:
            if not all(k in t for k in ("label", "slug", "cat", "sub")):
                WARNINGS.append(f"Type « {tid} » incomplet dans {org} : ignoré")
                continue
            t.setdefault("suivi", "none")
            t.setdefault("kw", [])
            t.setdefault("fn", [])
            t["_origin"] = org
            TYPES[tid] = t
        ok = []
        for d in details:
            if isinstance(d, (list, tuple)) and len(d) >= 2 and _safe_pattern(d[0], official):
                ok.append((d[0], d[1], org))
            else:
                WARNINGS.append(f"Règle refusée dans {org} (trop complexe ou invalide) : {str(d)[:60]}")
        if ok:
            DETAILS.setdefault(tid, [])
            if official:
                DETAILS[tid].extend(ok)
            else:
                DETAILS[tid][:0] = ok
        n_rules += len(ok)
    for k, v in p.get("templates", {}).items():
        TEMPLATES[k] = v
    for cc in p.get("countries", {}) or [None]:
        for e in p.get("echeances", []):
            if isinstance(e, dict) and re.match(r"^\d{2}-\d{2}$", str(e.get("jour", ""))) and e.get("label"):
                ECHEANCES.append((cc, e["label"], e["jour"], e.get("cat"), e.get("note", ""), org))
        if official:  # un lien vers un site ne vient que d'un pack officiel (jamais d'un pack importé)
            for o in p.get("organismes", []):
                url = str(o.get("url") or "") if isinstance(o, dict) else ""
                if isinstance(o, dict) and o.get("nom") and (not url or re.match(r"^https://[a-z0-9.-]+/[^\s\"'<>]*$", url)):
                    ORGS.append((cc, o["nom"], url, o.get("note", "")))
    if official and isinstance(p.get("contribution"), dict):
        CONTRIBUTION.update(p["contribution"])
    # règles simples : un indice (texte exact, jamais une formule) -> un champ
    n_simple = 0
    for r in p.get("rules", []):
        if not isinstance(r, dict) or r.get("actif") is False:
            continue
        ind, champ, val = str(r.get("indice") or "").strip(), r.get("champ"), str(r.get("valeur") or "").strip()
        if not ind or len(ind) > MAX_INDICE or champ not in RULE_FIELDS or not val:
            WARNINGS.append(f"Règle ignorée dans {org} : {str(r)[:60]}")
            continue
        new = (ind, champ, val, r.get("type") or None, org, r.get("id"))
        if official:
            RULES.append(new)
        else:
            RULES.insert(0, new)
        n_simple += 1
    PACKS.append({"id": p.get("id", "perso" if kind == "perso" else "?"),
                  "name": p.get("name", "Mes règles" if kind == "perso" else "?"),
                  "version": p.get("version", ""), "kind": kind, "types": len(p.get("types", {})),
                  "rules": n_rules + n_simple, "emitters": len(em), "templates": len(p.get("templates", {}))})


def load(bureau_fm=None, disabled=()):
    """(Re)charge tout le catalogue. bureau_fm = dossier .bontoutou du bureau (packs importés + règles perso)."""
    for d in (COUNTRIES, CATEGORIES, CAT_FOLDERS_FR, SUB_FOLDERS_FR, COUNTRY_HINTS, TYPES, DETAILS, TEMPLATES):
        d.clear()
    for l in (EMITTERS, EXPIRY_HINTS, PACKS, WARNINGS, RULES, ECHEANCES, ORGS):
        del l[:]
    CONTRIBUTION.clear()
    names = [n[:-5] for n in os.listdir(OFFICIAL_DIR) if n.endswith(".json")]
    for pid in [x for x in OFFICIAL_ORDER if x in names] + sorted(x for x in names if x not in OFFICIAL_ORDER):
        if pid == "modeles":  # liste des modèles d'IA : lue par ia.py, pas un pack de rangement
            continue
        p = _read(os.path.join(OFFICIAL_DIR, pid + ".json"))
        if p and p.get("id", pid) not in disabled:
            _apply(p, "officiel")
    if bureau_fm:
        imp = os.path.join(bureau_fm, "packs")
        if os.path.isdir(imp):
            for n in sorted(os.listdir(imp)):
                if n.endswith(".json"):
                    p = _read(os.path.join(imp, n))
                    if p and p.get("id", n) not in disabled:
                        _apply(p, "importe")  # jamais considéré comme officiel, même s'il le prétend
        perso = os.path.join(bureau_fm, "mes-regles.json")
        if os.path.exists(perso):
            p = _read(perso)
            if p and "perso" not in disabled:
                _apply(p, "perso")
    if "autre" not in TYPES:
        TYPES["autre"] = dict(label="Autre document", slug="Document", cat="11", sub="11-1", suivi="none", kw=[], fn=[], _origin="Socle")
    return PACKS


load()
