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
    env = dict(os.environ, HOME=os.path.join(tmp, "home"), FREEMARKET_DATA=os.path.join(tmp, "data"))
    os.makedirs(env["HOME"], exist_ok=True)
    p = subprocess.Popen([sys.executable, "-m", "freemarket.server", "--port", "0", "--app"], cwd=os.path.join(tmp, "code"),
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
for d in ("freemarket", "static"):
    shutil.copytree(os.path.join(HERE, d), os.path.join(tmp, "code", d))
p, port = start()
try:
    c, st = call(port, "/api/state")
    check(st.get("setup") and st["suggest"].endswith("FREEMARKET_ADMIN") and st["ia"]["machine"]["niveau"], "1er lancement : assistant d'installation, dossier suggéré, niveau d'IA conseillé")
    c, r = call(port, "/api/upload?name=x.pdf", raw=b"%PDF")
    check(c == 409, "avant l'installation, rien ne peut être déposé")
    c, r = call(port, "/api/setup", {"path": os.path.join(tmp, "home"), "owner": "x"})
    check(not r["ok"], "refus d'utiliser tout le dossier personnel")
    target = os.path.join(tmp, "home", "Documents", "FREEMARKET_ADMIN"); os.makedirs(os.path.dirname(target))
    c, r = call(port, "/api/setup", {"path": target, "owner": "Camille Martin", "countries": ["FR", "NZ", "ZZ"]})
    check(r["ok"] and os.path.isdir(os.path.join(target, "00_A-TRIER")), "installation : dossier créé avec 00_A-TRIER")
    c, st = call(port, "/api/state")
    check(not st.get("setup") and st["settings"]["owner"] == "Camille Martin" and st["settings"]["countries"] == ["FR", "NZ"], "profil enregistré (pays inconnu ignoré)")
    check(st["version"] and st["app"], "version affichée, mode app reconnu")
    c, r = call(port, "/api/upload?name=Passeport_secret_Martin.pdf", raw=b"%PDF-1.4 PASSEPORT")
    c, r = call(port, "/api/maj/check", {"consent": True})
    check(not r["ok"] and "pas encore" in r["msg"], "mises à jour : pas de page publique encore, rien n'est envoyé")
    c, r = call(port, "/api/bug", {})
    check(r["ok"] and "Passeport_secret" not in r["text"] and "Martin" not in r["text"] and "Freemarket" in r["text"], "rapport de bug : ni nom de fichier ni nom de personne")
    c, s = call(port, "/api/sorties")
    check(s == [], "rien n'est sorti pendant l'installation")
finally:
    p.terminate(); p.wait()
p, port = start()
try:
    c, st = call(port, "/api/state")
    check(not st.get("setup") and st["counts"]["inbox"] == 1, "redémarrage : le dossier choisi est repris tout seul")
finally:
    p.terminate(); p.wait()
# l'app se ferme (même brutalement) : le moteur s'arrête aussi
parent = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
env = dict(os.environ, HOME=os.path.join(tmp, "home"), FREEMARKET_DATA=os.path.join(tmp, "data"))
eng = subprocess.Popen([sys.executable, "-m", "freemarket.server", "--port", "0", "--app", "--watch-pid", str(parent.pid)],
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
