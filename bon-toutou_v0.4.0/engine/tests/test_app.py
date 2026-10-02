"""Ce que fait l'app au premier lancement : installation, redémarrage, mises à jour, rapport de bug.
    python3 -m tests.test_app        (depuis le dossier App_v0)
Lance le vrai serveur (port libre au hasard), comme l'app de bureau.
"""
import json, os, subprocess, sys, tempfile, time, urllib.request
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tmp = tempfile.mkdtemp(prefix="fm_app_")
fails = 0
def check(cond, msg):
    global fails
    print(("  ✓ " if cond else "  ✗ ") + msg); fails += 0 if cond else 1

def start():
    env = dict(os.environ, HOME=os.path.join(tmp, "home"), BONTOUTOU_DATA=os.path.join(tmp, "data"))
    os.makedirs(env["HOME"], exist_ok=True)
    p = subprocess.Popen([sys.executable, "-m", "bontoutou.server", "--port", "0", "--app"], cwd=os.path.join(tmp, "code"),
                         env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    line = p.stdout.readline().strip()
    return p, int(line.split("=")[1])
def call(port, path, body=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

# copie du code SANS config.json ni kit voisin : comme une app fraîchement installée
import shutil
os.makedirs(os.path.join(tmp, "code"))
for d in ("bontoutou", "static"):
    shutil.copytree(os.path.join(HERE, d), os.path.join(tmp, "code", d))
p, port = start()
try:
    c, st = call(port, "/api/state")
    check(st.get("setup") and st["suggest"].endswith("BON_TOUTOU_ADMIN") and st["ia"]["machine"]["niveau"], "1er lancement : assistant d'installation, dossier suggéré, niveau d'IA conseillé")
    c, r = call(port, "/api/upload?name=x.pdf", raw=b"%PDF")
    check(c == 409, "avant l'installation, rien ne peut être déposé")
    c, r = call(port, "/api/setup", {"path": os.path.join(tmp, "home"), "owner": "x"})
    check(not r["ok"], "refus d'utiliser tout le dossier personnel")
    target = os.path.join(tmp, "home", "Documents", "BON_TOUTOU_ADMIN"); os.makedirs(os.path.dirname(target))
    c, r = call(port, "/api/setup", {"path": target, "owner": "Camille Martin", "countries": ["FR", "NZ", "ZZ"]})
    check(r["ok"] and os.path.isdir(os.path.join(target, "00_A-TRIER")), "installation : dossier créé avec 00_A-TRIER")
    c, st = call(port, "/api/state")
    check(not st.get("setup") and st["settings"]["owner"] == "Camille Martin" and st["settings"]["countries"] == ["FR", "NZ"], "profil enregistré (pays inconnu ignoré)")
    check(st["version"] and st["app"], "version affichée, mode app reconnu")
    c, r = call(port, "/api/upload?name=Passeport_secret_Martin.pdf", raw=b"%PDF-1.4 PASSEPORT")
    c, r = call(port, "/api/maj/check", {"consent": False})
    check(not r["ok"] and "accord" in r["msg"], "mises à jour : sans ton accord, aucune requête n'est envoyée")
    c, r = call(port, "/api/bug", {})
    check(r["ok"] and "Passeport_secret" not in r["text"] and "Martin" not in r["text"] and "Bon toutou" in r["text"], "rapport de bug : ni nom de fichier ni nom de personne")
    c, s = call(port, "/api/sorties")
    check(s == [], "rien n'est sorti pendant l'installation")
finally:
    p.terminate(); p.wait()
p, port = start()
try:
    c, st = call(port, "/api/state")
    check(not st.get("setup") and st["counts"]["inbox"] == 1, "redémarrage : le dossier choisi est repris tout seul")
    # v0.3 : Aujourd'hui, Calendrier, Contacts, Organismes
    check(all(k in st for k in ("events", "local_only", "archives_n", "dossiers_open", "high", "tpl", "orgs")), "l'état donne tout ce qu'il faut à Aujourd'hui, au Calendrier et aux Réglages")
    check(any(e["k"] == "à faire" for e in st["events"]), "le calendrier contient les échéances du pays (déclaration de revenus…)")
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/calendrier.ics")
    with urllib.request.urlopen(req, timeout=20) as r:
        ics = r.read().decode()
    check(ics.startswith("BEGIN:VCALENDAR") and "VALARM" in ics, "export .ics : un fichier calendrier avec un rappel avant chaque échéance")
    c, ct = call(port, "/api/contacts")
    check(c == 200 and isinstance(ct, list), "contacts : liste tirée des documents et des dossiers")
    capf = os.path.join(os.path.dirname(HERE), "desktop", "src-tauri", "capabilities", "default.json")
    if os.path.exists(capf):  # dans le dépôt complet (pas dans une copie du seul moteur)
        cap = json.load(open(capf))
        allowed = [a["url"] for p_ in cap["permissions"] if isinstance(p_, dict) and p_.get("identifier") == "opener:allow-open-url" for a in p_["allow"]]
        import fnmatch
        links = [o["url"] for o in st["orgs"] if o["url"]]
        check(links and all(any(fnmatch.fnmatch(u, a) for a in allowed) for u in links), "chaque lien d'organisme est autorisé par l'app (et seulement ceux-là)")
    _s, _set = call(port, "/api/settings", {"theme": "sauge", "mail": "admin@exemple.fr", "orgs_done": ["Impôts"]})
    c, st2 = call(port, "/api/state")
    check(st2["settings"]["theme"] == "sauge" and st2["settings"]["mail"] == "admin@exemple.fr" and st2["settings"]["orgs_done"] == ["Impôts"], "réglages v0.3 enregistrés (thème, adresse admin, organismes prévenus)")
finally:
    p.terminate(); p.wait()
# Freemarket -> Bon toutou : un Mac où Freemarket était installé, bureau FREEMARKET_ADMIN avec ses fiches .freemarket
h2 = os.path.join(tmp, "home-ancien")
oldh = os.path.join(h2, ".local", "share", "freemarket")
oroot = os.path.join(h2, "Documents", "FREEMARKET_ADMIN")
os.makedirs(os.path.join(oroot, ".freemarket")); os.makedirs(oldh)
open(os.path.join(oroot, ".freemarket", "profil.json"), "w").write(json.dumps({"format": 1, "owner": "Camille Ancienne", "countries": ["FR"]}))
open(os.path.join(oroot, "mon-papier.pdf"), "w").write("%PDF")
open(os.path.join(oldh, "config.json"), "w").write(json.dumps({"format": 1, "bureau": oroot}))
env2 = {k: v for k, v in os.environ.items() if k not in ("BONTOUTOU_DATA", "FREEMARKET_DATA", "XDG_DATA_HOME")}
env2["HOME"] = h2
pm = subprocess.Popen([sys.executable, "-m", "bontoutou.server", "--port", "0", "--app"], cwd=os.path.join(tmp, "code"), env=env2,
                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    port2 = int(pm.stdout.readline().strip().split("=")[1])
    c, stm = call(port2, "/api/state")
    nroot = os.path.join(h2, "Documents", "BON_TOUTOU_ADMIN")
    check(not stm.get("setup") and stm["root"] == nroot and stm["settings"]["owner"] == "Camille Ancienne",
          "Freemarket -> Bon toutou : bureau repris et renommé BON_TOUTOU_ADMIN, réglages gardés")
    check(os.path.exists(os.path.join(nroot, "mon-papier.pdf")) and os.path.isdir(os.path.join(nroot, ".bontoutou"))
          and not os.path.exists(os.path.join(nroot, ".freemarket")) and not os.path.exists(oldh)
          and os.path.exists(os.path.join(nroot, ".bontoutou", "migration-bon-toutou.json")),
          "renommage seulement : documents intacts, fiches .bontoutou, rien supprimé, migration notée")
finally:
    pm.terminate(); pm.wait()
# l'app se ferme (même brutalement) : le moteur s'arrête aussi
parent = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
env = dict(os.environ, HOME=os.path.join(tmp, "home"), BONTOUTOU_DATA=os.path.join(tmp, "data"))
eng = subprocess.Popen([sys.executable, "-m", "bontoutou.server", "--port", "0", "--app", "--watch-pid", str(parent.pid)],
                       cwd=os.path.join(tmp, "code"), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2); alive = eng.poll() is None
parent.kill(); parent.wait()
try:
    eng.wait(timeout=8); stopped = True
except subprocess.TimeoutExpired:
    eng.kill(); stopped = False
check(alive and stopped, "l'app fermée, le moteur s'arrête tout seul (rien ne reste en arrière-plan)")
print("\nRÉSULTAT :", "OK" if not fails else f"{fails} échec(s)")
sys.exit(1 if fails else 0)
