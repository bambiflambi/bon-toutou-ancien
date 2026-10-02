"""La porte de sortie est la seule à pouvoir parler au réseau.
    python3 -m tests.test_sortie        (depuis le dossier App_v0)
"""
import os, re, sys, tempfile
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
tmp = tempfile.mkdtemp(prefix="fm_sortie_")
os.environ["BONTOUTOU_DATA"] = os.path.join(tmp, "appareil")
from bontoutou import sortie
from bontoutou.core import Bureau

fails = 0
def check(cond, msg):
    global fails
    print(("  ✓ " if cond else "  ✗ ") + msg); fails += 0 if cond else 1

# 1. Lecture du code : aucun autre fichier n'importe de quoi ouvrir une connexion
NET = re.compile(r"^\s*(import|from)\s+(urllib\.request|urllib3|http\.client|socket|ssl|requests|httpx|aiohttp|ftplib|smtplib|poplib|imaplib|telnetlib|xmlrpc|websocket)\b", re.M)
NET_USE = re.compile(r"\b(urlopen|create_connection|socket\.socket)\s*\(")
bad = []
for dirpath, _, files in os.walk(os.path.join(HERE, "bontoutou")):
    for f in files:
        if f.endswith(".py") and f != "sortie.py":
            src = open(os.path.join(dirpath, f), encoding="utf-8").read()
            if NET.search(src) or NET_USE.search(src):
                bad.append(f)
check(not bad, "aucun autre fichier que sortie.py ne peut ouvrir une connexion" + (f" (fautifs : {bad})" if bad else ""))
srv = open(os.path.join(HERE, "bontoutou", "server.py"), encoding="utf-8").read()
check('("127.0.0.1", a.port)' in srv, "le serveur n'écoute que 127.0.0.1")

# 2. Règles de la porte
def refused(**kw):
    try:
        sortie.check(**kw); return False
    except sortie.SortieRefusee:
        return True
check(not refused(url="http://127.0.0.1:11434/api/tags"), "IA locale (127.0.0.1) autorisée")
check(refused(url="https://exemple.org/x"), "adresse extérieure sans motif : refusée")
check(refused(url="https://exemple.org/x", purpose="maj"), "mise à jour sans ton accord : refusée")
check(not refused(url="https://exemple.org/x", purpose="maj", consent=True), "mise à jour avec ton accord : autorisée")
check(refused(url="https://ia.exemple/v1", purpose="ia_externe", consent=True, level="local"), "IA externe sur un document 🔒 : refusée")
check(refused(url="https://ia.exemple/v1", purpose="ia_externe", consent=True, level=None), "IA externe sur un document non trié : refusée")
check(not refused(url="https://ia.exemple/v1", purpose="ia_externe", consent=True, level="externe"), "IA externe sur un document ☁ avec accord : autorisée")

# 3. Journal : noté AVANT l'envoi, même si l'envoi échoue
root = os.path.join(tmp, "BON_TOUTOU_ADMIN"); os.makedirs(root)
b = Bureau(root)
check(b.sorties() == [], "journal des sorties vide au départ")
try:
    b.sortir("https://ia.exemple.invalid/v1", "ia_externe", consent=True, cat="01", data=b"x")
except sortie.SortieRefusee:
    pass
check(b.sorties() == [], "catégorie Identité (🔒) : rien n'est parti, rien noté")
try:
    b.sortir("https://ia.exemple.invalid/v1", "ia_externe", consent=True, cat="11", data=b"texte", what="Contrat Free", timeout=2)
except Exception:
    pass
s = b.sorties()
check(len(s) == 1 and s[0]["dest"] == "ia.exemple.invalid" and s[0]["what"] == "Contrat Free", "catégorie Contrats (☁) : sortie notée avant l'envoi")
try:
    sortie.http("https://exemple.org", purpose="maj", consent=True)
    check(False, "sortie sans journal refusée")
except sortie.SortieRefusee:
    check(True, "sortie sans journal refusée")

print("\nRÉSULTAT :", "OK" if not fails else f"{fails} échec(s)")
sys.exit(1 if fails else 0)
