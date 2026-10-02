"""La seule porte de sortie de Bon toutou vers le réseau.

Règle : aucun autre fichier du programme n'a le droit d'ouvrir une connexion
(tests/test_sortie.py le vérifie à chaque version).

  * Adresse locale (127.0.0.1, localhost) : l'IA locale. Autorisé, rien ne quitte l'ordinateur, rien à noter.
  * Toute autre adresse : refusée, sauf si
      - le motif est connu (mise à jour, modèle d'IA, IA externe, rapport de bug, proposition de règle),
      - l'utilisateur a donné son accord pour CETTE action,
      - pour l'IA externe : le niveau de confidentialité de la catégorie le permet
        (🔒 jamais · ◐ seulement avec accord explicite · ☁ autorisé) ; un document non trié est 🔒.
    Chaque sortie autorisée est notée dans le journal des sorties AVANT de partir.
"""
import json
import urllib.parse
import urllib.request

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
PURPOSES = {
    "maj": "Vérifier ou télécharger une mise à jour",
    "modele": "Télécharger un modèle d'IA",
    "ia_externe": "Demander l'avis d'une IA externe",
    "bug": "Envoyer un rapport de bug",
    "proposition": "Proposer une règle ou un type",
}
LEVELS = {"local": "🔒 Local uniquement", "autorisation": "◐ Sur autorisation", "externe": "☁ Externe autorisé"}


class SortieRefusee(Exception):
    """Une sortie a été bloquée. Le message explique pourquoi, en français."""


def is_local(url):
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    return host in LOCAL_HOSTS


def check(url, purpose=None, consent=False, level=None):
    """Lève SortieRefusee si la sortie n'est pas permise. Ne fait rien pour une adresse locale."""
    if is_local(url):
        return
    if purpose not in PURPOSES:
        raise SortieRefusee("Sortie inconnue : Bon toutou ne se connecte qu'aux adresses prévues.")
    if not consent:
        raise SortieRefusee(f"{PURPOSES[purpose]} : il faut ton accord pour cette action.")
    if purpose == "ia_externe":
        if level in (None, "local"):
            raise SortieRefusee("Ce document est « 🔒 Local uniquement » (ou pas encore trié) : il ne quitte pas ton ordinateur.")
        if level not in LEVELS:
            raise SortieRefusee("Niveau de confidentialité inconnu : sortie refusée par prudence.")


def http(url, data=None, headers=None, timeout=60, method=None, purpose=None, consent=False, level=None,
         log=None, what="", doc_id=None):
    """Requête HTTP(S) après vérification. `log(entry)` est appelé AVANT l'envoi pour toute sortie non locale."""
    check(url, purpose, consent, level)
    if not is_local(url):
        if log is None:
            raise SortieRefusee("Sortie impossible sans journal des sorties.")
        log({"dest": urllib.parse.urlparse(url).hostname, "purpose": purpose, "label": PURPOSES[purpose],
             "what": what, "doc_id": doc_id, "level": level, "bytes": len(data or b"")})
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def http_lines(url, payload, timeout=3600, **kw):
    """Réponse ligne par ligne (suivi d'un téléchargement). Mêmes vérifications que http()."""
    check(url, kw.get("purpose"), kw.get("consent", False), kw.get("level"))
    if not is_local(url):
        raise SortieRefusee("Flux réservé aux moteurs locaux.")
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for line in r:
            yield line


def download(url, dest, sha256, purpose, consent=False, log=None, what="", progress=None, timeout=60):
    """Télécharge un fichier (modèle d'IA, mise à jour) puis vérifie son empreinte SHA-256.
    Sans empreinte connue : refusé. Empreinte fausse : fichier jeté, rien n'est installé."""
    import hashlib
    import os
    if not sha256 or len(sha256) != 64:
        raise SortieRefusee("Empreinte inconnue : Bon toutou ne télécharge que des fichiers vérifiables.")
    check(url, purpose, consent)
    if log is None:
        raise SortieRefusee("Sortie impossible sans journal des sorties.")
    log({"dest": urllib.parse.urlparse(url).hostname, "purpose": purpose, "label": PURPOSES[purpose], "what": what, "bytes": 0})
    part = dest + ".part"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    h = hashlib.sha256()
    req = urllib.request.Request(url, headers={"User-Agent": "Bon toutou"})
    with urllib.request.urlopen(req, timeout=timeout) as r, open(part, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            h.update(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    if h.hexdigest() != sha256.lower():
        os.replace(part, part + ".rejete")  # gardé pour examen, jamais utilisé
        raise SortieRefusee("Empreinte différente de celle attendue : le fichier a été refusé.")
    os.replace(part, dest)
    return dest


def http_json(url, payload=None, timeout=60, **kw):
    data = json.dumps(payload).encode() if payload is not None else None
    raw = http(url, data=data, headers={"Content-Type": "application/json"} if data else None, timeout=timeout, **kw)
    return json.loads(raw.decode("utf-8", "ignore") or "null")


# ---------- Masquage : appliqué à tout texte avant qu'il quitte l'ordinateur
_MASKS = [
    ("IBAN", r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}(?:[ ]?[A-Z0-9]{1,4})?\b"),
    ("carte bancaire", r"\b(?:\d{4}[ -]?){3}\d{4}\b"),
    ("n° de sécurité sociale", r"\b[12][ ]?\d{2}[ ]?(?:0[1-9]|1[0-2]|[2-9]\d)[ ]?(?:\d{2}|2[AB])[ ]?\d{3}[ ]?\d{3}(?:[ ]?\d{2})?\b"),
    ("e-mail", r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    ("téléphone", r"(?:\+\d{2,3}[ .]?|\b0)\d(?:[ .-]?\d{2}){4}\b|\+64[ ]?\d{1,2}[ ]?\d{3}[ ]?\d{3,4}\b"),
    ("n° de passeport", r"\b\d{2}[A-Z]{2}\d{5}\b|\b[A-Z]{1,2}\d{6,7}\b"),
    ("n° fiscal", r"\b[0-3]\d{12}\b|\b\d{2,3}-?\d{3}-?\d{3}\b"),
]


def mask(text):
    """Remplace les numéros sensibles par [nature masquée]. Retourne (texte masqué, liste des natures masquées)."""
    import re
    found = []
    out = text or ""
    for label, pat in _MASKS:
        out, n = re.subn(pat, f"[{label} masqué]", out)
        if n:
            found.append(f"{label} ×{n}")
    return out, found
