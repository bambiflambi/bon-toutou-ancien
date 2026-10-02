"""IA locale interchangeable : détection, demande (Ollama et format standard), vérification, installation d'un modèle.
    python3 -m tests.test_ia        (depuis le dossier App_v0)
Faux moteurs locaux sur 127.0.0.1 : aucun vrai modèle n'est nécessaire.
"""
import json, os, sys, tempfile, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
tmp = tempfile.mkdtemp(prefix="fm_ia_")
os.environ["BONTOUTOU_DATA"] = os.path.join(tmp, "appareil")
from bontoutou import ia, classify, sortie
from bontoutou.core import Bureau

fails = 0
def check(cond, msg):
    global fails
    print(("  ✓ " if cond else "  ✗ ") + msg); fails += 0 if cond else 1

SEEN = []
ANSWER = {"type": "passeport", "country": "FR", "emitter": "Prefecture Lyon", "date": "2024-07-23", "expiry": "2034-07-22",
          "holder": "Camille Martin", "detail": None, "why": "Le mot PASSEPORT et une date d'expiration."}
class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _j(self, o):
        b = json.dumps(o).encode(); self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path == "/api/tags": return self._j({"models": [{"name": "ministral-3:3b"}]})
        if self.path == "/v1/models": return self._j({"data": [{"id": "local-model"}]})
        self.send_response(404); self.end_headers()
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}"); SEEN.append((self.path, body))
        if self.path == "/api/generate": return self._j({"response": json.dumps(ANSWER)})
        if self.path == "/v1/chat/completions": return self._j({"choices": [{"message": {"content": "```json\n" + json.dumps(ANSWER) + "\n```"}}]})
        if self.path == "/api/pull":
            self.send_response(200); self.end_headers()
            for done in (0, 50, 100):
                self.wfile.write((json.dumps({"status": "pulling", "total": 100, "completed": done}) + "\n").encode()); self.wfile.flush()
            self.wfile.write(b'{"status":"success"}\n'); return
def serve():
    s = ThreadingHTTPServer(("127.0.0.1", 0), Fake); threading.Thread(target=s.serve_forever, daemon=True).start(); return s.server_address[1]
po, pa = serve(), serve()
ia.ENGINES[:] = [("ollama", "Ollama", f"http://127.0.0.1:{po}", "ollama"), ("lmstudio", "LM Studio", f"http://127.0.0.1:{pa}", "openai"),
                 ("jan", "Jan", "http://127.0.0.1:9", "openai")]

E_ = [e for e in ia.engines(force=True) if e["id"] != "integre"]
EI = ia.engine_by_id("integre")
check([e["running"] for e in E_[:3]] == [True, True, False] and EI and EI["running"] == ia.integre_dispo(), "détection : Ollama et LM Studio trouvés, Jan absent, moteur intégré signalé")
check(E_[0]["models"] == ["ministral-3:3b"], "modèles installés listés")
m = ia.machine(tmp); check(m["niveau"] in ("modeste", "equilibre", "puissant") and m["ram_go"] >= 0, f"machine : niveau conseillé {m['niveau']}")
cat = ia.catalogue(); check(len(cat["modeles"]) == 6 and all(x["licence"] == "Apache 2.0" for x in cat["modeles"]), "catalogue : 6 modèles, tous Apache 2.0")
check([x["auteur"] for x in cat["modeles"] if x["conseille"]] == ["Mistral AI"] * 3, "modèles conseillés : Mistral AI (France) à chaque niveau")

o = ia.ask(E_[0], "ministral-3:3b", "test", image=b"\x89PNG")
check(o["type"] == "passeport" and SEEN[-1][1]["think"] is False and SEEN[-1][1]["images"], "Ollama : réponse lue, réflexion coupée, image envoyée")
o = ia.ask(E_[1], "local-model", "test", image=b"\x89PNG")
msg = SEEN[-1][1]["messages"][1]["content"]
check(o["emitter"] == "Prefecture Lyon" and isinstance(msg, list) and msg[1]["type"] == "image_url", "format standard (LM Studio…) : réponse lue même entourée de ```json, image en data URL")
try:
    ia.ask({"url": "https://ia.exemple.org", "kind": "openai"}, "x", "test"); check(False, "moteur distant refusé")
except sortie.SortieRefusee:
    check(True, "moteur distant refusé : seule l'IA de l'ordinateur est utilisée")

# l'IA propose, le code vérifie
r = classify.analyze("", "scan.jpg", ["FR", "NZ"])
ANSWER.update(type="type_invente", date="2099-13-45", country="XX")
r2 = classify.refine_with_ai(dict(r, reasons=list(r["reasons"])), "", "scan.jpg", E_[0], "ministral-3:3b", ["FR", "NZ"])
check(r2["type"] == r["type"] and r2["date"] == r["date"] and r2["country"] == r["country"], "réponse invalide de l'IA (type inventé, date impossible, pays inconnu) : ignorée")
ANSWER.update(type="passeport", date="2024-07-23", country="FR")
r3 = classify.refine_with_ai(dict(r, reasons=list(r["reasons"])), "", "scan.jpg", E_[0], "ministral-3:3b", ["FR", "NZ"])
check(r3["type"] == "passeport" and r3["expiry"] == "2034-07-22" and any("Ollama" in x for x in r3["reasons"]), "réponse valide : appliquée, « Pourquoi ? » nomme le modèle et le moteur")

# installer un modèle : accord + journal AVANT
root = os.path.join(tmp, "BON_TOUTOU_ADMIN"); os.makedirs(root); b = Bureau(root)
check(not b.ai_pull("ollama", "ministral-3:8b", False)["ok"], "sans ton accord : pas de téléchargement")
check(not b.ai_pull("ollama", "modele-inconnu:1b", True)["ok"], "modèle hors de la liste vérifiée : refusé")
r = b.ai_pull("ollama", "ministral-3:8b", True)
for _ in range(50):
    if ia.PULLS.get("ministral-3:8b", {}).get("status") != "en cours": break
    time.sleep(0.1)
s = b.sorties()
check(r["ok"] and ia.PULLS["ministral-3:8b"]["status"] == "fini" and ia.PULLS["ministral-3:8b"]["done"] == 100, "téléchargement suivi jusqu'au bout")
check(len(s) == 1 and s[0]["purpose"] == "modele" and "Ministral 3 · 8B" in s[0]["what"], "la sortie (Ollama télécharge) est notée dans le journal")
t = b.ai_test("lmstudio", "local-model"); check(t["ok"] and t["secondes"] >= 0, "essai chronométré du modèle")

check(SEEN and any(x[1].get("keep_alive") == "30m" for x in SEEN if x[0] == "/api/generate"), "le modèle reste chargé 30 min entre deux documents")
b.save_settings({"use_ollama": True, "ollama_model": "ministral-3:3b", "ai_bench": {"ministral-3:3b": 75}})
check(b._ai_timeout(False) == 285, "délai adapté à la vitesse mesurée (75 s → 285 s)")
check(not b._ai_wanted({"confidence": "moyenne"}, "x" * 50) and b._ai_wanted({"confidence": "basse"}, "x" * 50), "IA lente : sollicitée seulement pour les documents « à vérifier »")

# moteur intégré : téléchargement GGUF seulement avec une empreinte, et vérifiée
r = ia.pull(EI, "ministral-3-3b", b.log_sortie)
check(not r["ok"] and "empreinte" in r["msg"], "modèle sans empreinte fixée : pas de téléchargement")
import hashlib
class Blob(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Length", "11"); self.end_headers(); self.wfile.write(b"hello model")
sb = ThreadingHTTPServer(("127.0.0.1", 0), Blob); threading.Thread(target=sb.serve_forever, daemon=True).start()
u = f"http://127.0.0.1:{sb.server_address[1]}/m.gguf"
good = hashlib.sha256(b"hello model").hexdigest()
d1 = sortie.download(u, os.path.join(tmp, "m", "ok.gguf"), good, "modele", consent=True, log=b.log_sortie)
check(open(d1, "rb").read() == b"hello model", "téléchargement vérifié : empreinte conforme, fichier installé")
try:
    sortie.download(u, os.path.join(tmp, "m", "bad.gguf"), "0" * 64, "modele", consent=True, log=b.log_sortie); check(False, "x")
except sortie.SortieRefusee:
    check(not os.path.exists(os.path.join(tmp, "m", "bad.gguf")) and os.path.exists(os.path.join(tmp, "m", "bad.gguf.part.rejete")),
          "empreinte fausse : fichier refusé, gardé à part, jamais utilisé")

print("\nRÉSULTAT :", "OK" if not fails else f"{fails} échec(s)")
sys.exit(1 if fails else 0)
