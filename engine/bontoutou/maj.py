"""Installation, mises à jour (au choix, jamais obligatoires) et rapport de bug (volontaire, relu avant envoi)."""
import json
import os
import platform
import re

from . import __version__, catalog, ia, reader, sortie


def COUNTRY_CODES():
    return list(catalog.COUNTRIES)


def depot():
    """Dépôt public « propriétaire/nom » (pack Socle › contribution › depot). Vide tant que la page n'existe pas."""
    return (catalog.CONTRIBUTION.get("depot") or "").strip()


def setup_state():
    """Ce dont l'assistant d'installation a besoin, avant qu'un dossier existe."""
    home = os.path.expanduser("~")
    docs = os.path.join(home, "Documents")
    return {"setup": True, "version": __version__, "app": bool(os.environ.get("BONTOUTOU_APP")),
            "suggest": os.path.join(docs if os.path.isdir(docs) else home, "BON_TOUTOU_ADMIN"),
            "countries": {k: v["name"] for k, v in catalog.COUNTRIES.items()},
            "ia": {"machine": ia.machine(home), "catalogue": ia.catalogue(), "engines": ia.engines()},
            "depot": depot()}


def _vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "")[:3]) or (0,)


def check(b, consent):
    """Vérifie s'il existe une version plus récente : UNE requête vers la page publique, avec ton accord, notée au journal."""
    if not depot():
        return {"ok": False, "msg": "La page de téléchargement n'existe pas encore : aucune vérification possible pour l'instant."}
    url = f"https://api.github.com/repos/{depot()}/releases/latest"
    try:
        r = sortie.http_json(url, timeout=20, purpose="maj", consent=bool(consent), log=b.log_sortie,
                             what=f"version installée {__version__}")
    except sortie.SortieRefusee as e:
        return {"ok": False, "msg": str(e)}
    except Exception as e:
        return {"ok": False, "msg": f"Page injoignable ({type(e).__name__})"}
    tag = (r or {}).get("tag_name", "")
    notes = (r or {}).get("body") or ""
    newer = _vtuple(tag) > _vtuple(__version__)
    important = bool(re.search(r"(?im)^\s*(important|faille|s[ée]curit[ée])", notes))
    return {"ok": True, "installee": __version__, "derniere": tag.lstrip("v"), "nouvelle": newer, "important": important and newer,
            "notes": notes[:4000], "page": (r or {}).get("html_url") or f"https://github.com/{depot()}/releases"}


def bug_report(b, errors):
    """Rapport de bug SANS document ni nom de fichier : version, système, outils, compteurs, erreurs récentes.
    L'utilisateur le relit, peut le modifier, puis choisit de l'envoyer (ou non)."""
    st = b.state()
    m = st["ia"]["machine"]
    lines = [f"Bon toutou {__version__}", f"Système : {platform.system()} {platform.release()} · {platform.machine()}",
             f"Machine : {m.get('ram_go')} Go de mémoire · niveau IA {m.get('niveau')}",
             "Lecture : " + ", ".join(k for k, v in reader.tools().items() if v),
             "Moteurs IA : " + (", ".join(e["name"] for e in st["ia"]["engines"] if e["running"]) or "aucun"),
             f"Documents : {st['counts']['docs']} actuels · {st['counts']['inbox']} à trier · {st['counts']['dossiers']} dossiers",
             "Packs : " + ", ".join(f"{p['name']} {p['version']}" for p in st["packs"])]
    if st.get("catalog_warnings"):
        lines.append("Avertissements du catalogue : " + " | ".join(st["catalog_warnings"])[:800])
    if errors:
        lines.append("Erreurs récentes :")
        lines += [f"  {e['route']} : {e['error']}" for e in errors[-10:]]
    text, found = sortie.mask("\n".join(lines))
    issue = f"https://github.com/{depot()}/issues/new" if depot() else None
    c = catalog.CONTRIBUTION
    return {"ok": True, "text": text, "masque": found, "issue": issue,
            "mailto": ("mailto:" + c["email"]) if c.get("email") else None,
            "rappel": "Aucun document, aucun nom de fichier. Tu peux tout relire et modifier avant d'envoyer."}
