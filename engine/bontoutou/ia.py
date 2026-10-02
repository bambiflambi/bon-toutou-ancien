"""IA locale interchangeable : une seule « prise » pour tous les moteurs.

  * Ollama (127.0.0.1:11434)            : API native (/api/generate), la plus fiable pour couper la « réflexion ».
  * LM Studio, Jan, llama.cpp, vLLM…      : format standard compatible OpenAI (/v1/chat/completions).
  * Moteur intégré (llama.cpp embarqué)   : arrive avec l'app (étape D), compilé pour chaque système.

Tout passe par sortie.py. Un moteur sur 127.0.0.1 ne fait rien sortir de l'ordinateur.
Installer un modèle via Ollama est en revanche une sortie (téléchargement) : accord + journal.
L'IA propose, le code vérifie (classify.refine_with_ai) : elle ne déplace jamais un fichier.
"""
import base64
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time

from . import sortie

ENGINES = [  # moteurs locaux connus : (identifiant, nom, adresse, type d'API)
    ("ollama", "Ollama", "http://127.0.0.1:11434", "ollama"),
    ("lmstudio", "LM Studio", "http://127.0.0.1:1234", "openai"),
    ("jan", "Jan", "http://127.0.0.1:1337", "openai"),
    ("llamacpp", "llama.cpp (serveur)", "http://127.0.0.1:8080", "openai"),
]
_cache = {"t": 0, "engines": None}
_LLAMA = {"path": None, "llm": None}  # moteur intégré : un seul modèle chargé à la fois


def models_dir():
    from .core import data_home
    return os.path.join(data_home(), "modeles")


def integre_dispo():
    """Le moteur intégré (llama.cpp en bibliothèque) est-il embarqué dans cette version ?"""
    try:
        import llama_cpp  # noqa: F401  — compilé et embarqué par la fabrication (étape D)
        return True
    except Exception:
        return False


def integre_models():
    d = models_dir()
    return sorted(f for f in os.listdir(d) if f.endswith(".gguf")) if os.path.isdir(d) else []
PULLS = {}  # modèle -> état du téléchargement {status, done, total, error}


def catalogue():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "packs", "modeles.json")
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return {"niveaux": {}, "modeles": []}


# ------------------------------------------------------------ la machine
def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, timeout=5).stdout.decode("utf-8", "ignore").strip()
    except Exception:
        return ""


def machine(root=None):
    """Ce que Bon toutou sait de l'ordinateur : de quoi conseiller un niveau d'IA. Rien ne sort."""
    arch = platform.machine().lower()
    ram = 0
    cpu = ""
    if sys.platform == "darwin":
        ram = int(_run(["sysctl", "-n", "hw.memsize"]) or 0)
        cpu = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
    elif sys.platform.startswith("linux"):
        try:
            for line in open("/proc/meminfo"):
                if line.startswith("MemTotal"):
                    ram = int(line.split()[1]) * 1024
        except Exception:
            pass
        try:
            cpu = next((l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")), "")
        except Exception:
            pass
    elif os.name == "nt":
        try:
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("l", ctypes.c_ulong), ("m", ctypes.c_ulong), ("t", ctypes.c_ulonglong), ("a", ctypes.c_ulonglong),
                            ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong), ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong),
                            ("e", ctypes.c_ulonglong)]
            ms = MS(); ms.l = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
            ram = ms.t
        except Exception:
            pass
        cpu = platform.processor()
    apple = sys.platform == "darwin" and arch in ("arm64", "aarch64")
    gpu = bool(shutil.which("nvidia-smi"))
    ram_go = round(ram / 1024 ** 3) if ram else 0
    try:
        free_go = round(shutil.disk_usage(root or os.path.expanduser("~")).free / 1024 ** 3)
    except OSError:
        free_go = 0
    if (apple and ram_go >= 24) or (gpu and ram_go >= 16):
        niveau = "puissant"
    elif ram_go >= 16 or (apple and ram_go >= 12):
        niveau = "equilibre"
    else:
        niveau = "modeste"
    puce = ("Puce Apple" if apple else "Intel / AMD") + (f" · {cpu}" if cpu else "")
    return {"puce": puce, "apple": apple, "gpu": gpu, "ram_go": ram_go, "coeurs": os.cpu_count() or 0, "libre_go": free_go,
            "niveau": niveau, "systeme": f"{platform.system()} {platform.release()}"}


# ------------------------------------------------------------ les moteurs
def engines(force=False):
    """Moteurs locaux qui tournent en ce moment, et leurs modèles installés (mis en cache 10 s)."""
    if not force and _cache["engines"] is not None and time.time() - _cache["t"] < 10:
        return _cache["engines"]
    out = []
    for eid, name, url, kind in ENGINES:
        models = None
        try:
            if kind == "ollama":
                r = sortie.http_json(url + "/api/tags", timeout=0.6)
                models = [m["name"] for m in (r or {}).get("models", [])]
            else:
                r = sortie.http_json(url + "/v1/models", timeout=0.6)
                models = [m.get("id") for m in (r or {}).get("data", []) if m.get("id")]
        except Exception:
            pass
        out.append({"id": eid, "name": name, "url": url, "kind": kind, "running": models is not None, "models": models or []})
    dispo = integre_dispo()
    out.insert(0, {"id": "integre", "name": "Moteur intégré (llama.cpp)", "url": None, "kind": "integre", "running": dispo,
                   "models": integre_models() if dispo else [],
                   "later": None if dispo else "Arrive avec l'app à télécharger : rien à installer, il est compilé pour chaque système."})
    _cache.update(t=time.time(), engines=out)
    return out


def engine_by_id(eid):
    """« auto » : le moteur intégré s'il est là, sinon le premier moteur local qui tourne (Ollama d'abord)."""
    E = engines()
    if eid in (None, "", "auto"):
        return next((e for e in E if e["running"]), next((e for e in E if e["id"] == "ollama"), None))
    return next((e for e in E if e["id"] == eid), None)


# ------------------------------------------------------------ demander
def ask(engine, model, prompt, image=None, timeout=120):
    """Envoie une demande au moteur choisi et renvoie la réponse JSON (dict). Seulement des moteurs locaux ici."""
    if engine.get("kind") == "integre":
        return _ask_integre(model, prompt, timeout)
    url = engine["url"]
    if not url or not sortie.is_local(url):
        raise sortie.SortieRefusee("Seuls les moteurs d'IA installés sur cet ordinateur sont utilisés pour l'instant.")
    if engine["kind"] == "ollama":
        payload = {"model": model, "prompt": prompt, "format": "json", "stream": False, "think": False,
                   "keep_alive": "30m",  # le modèle reste chargé 30 min : le 2e document ne repaie pas le chargement
                   "options": {"temperature": 0, "num_ctx": 4096}}
        if image:
            payload["images"] = [base64.b64encode(image).decode()]
        raw = sortie.http_json(url + "/api/generate", payload, timeout=timeout)["response"]
    else:
        content = [{"type": "text", "text": prompt}]
        if image:
            content.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(image).decode()}})
        payload = {"model": model, "temperature": 0, "messages": [
            {"role": "system", "content": "Réponds uniquement par un objet JSON valide, sans texte autour."},
            {"role": "user", "content": content if image else prompt}],
            "response_format": {"type": "json_object"}}
        r = sortie.http_json(url + "/v1/chat/completions", payload, timeout=timeout)
        raw = r["choices"][0]["message"]["content"]
    return parse_json(raw)


def _ask_integre(model, prompt, timeout):
    """llama.cpp dans le programme lui-même : aucune connexion, même locale."""
    from llama_cpp import Llama
    path = os.path.join(models_dir(), os.path.basename(model))
    if not os.path.exists(path):
        raise FileNotFoundError("Modèle absent : installe-le depuis Réglages › IA locale.")
    if _LLAMA["path"] != path:
        _LLAMA.update(path=path, llm=Llama(model_path=path, n_ctx=4096, verbose=False))
    r = _LLAMA["llm"].create_chat_completion(
        messages=[{"role": "system", "content": "Réponds uniquement par un objet JSON valide, sans texte autour."},
                  {"role": "user", "content": prompt}],
        response_format={"type": "json_object"}, temperature=0)
    return parse_json(r["choices"][0]["message"]["content"])


def parse_json(raw):
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw).strip()
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.S).strip()
    try:
        return json.loads(raw)
    except ValueError:
        m = re.search(r"\{.*\}", raw, re.S)
        return json.loads(m.group(0)) if m else {}


def test(engine, model):
    """Petit essai chronométré, pour savoir si ce modèle est utilisable sur cet ordinateur."""
    t0 = time.time()
    try:
        o = ask(engine, model, 'Réponds en JSON : {"ok": true, "langue": "<la langue de cette phrase>"}', timeout=180)
        return {"ok": bool(o), "secondes": round(time.time() - t0, 1), "reponse": o}
    except Exception as e:
        return {"ok": False, "secondes": round(time.time() - t0, 1), "erreur": f"{type(e).__name__}: {e}"[:200]}


# ------------------------------------------------------------ installer un modèle (via Ollama)
def pull(engine, model, log):
    """Installe un modèle de la liste vérifiée. C'est une SORTIE : notée avant.
    Moteur intégré : fichier GGUF téléchargé puis vérifié par son empreinte SHA-256 (fixée à la fabrication).
    Ollama : c'est Ollama qui télécharge depuis son registre et vérifie ses propres empreintes."""
    if engine["kind"] == "integre":
        return _pull_gguf(model, log)
    if engine["kind"] != "ollama":
        return {"ok": False, "msg": "Installation automatique possible seulement avec Ollama pour l'instant."}
    if PULLS.get(model, {}).get("status") == "en cours":
        return {"ok": True, "deja": True}
    cat = {m["ollama"]: m for m in catalogue().get("modeles", [])}
    if model not in cat:
        return {"ok": False, "msg": "Ce modèle n'est pas dans la liste vérifiée de Bon toutou."}
    log({"dest": "registry.ollama.ai (via Ollama)", "purpose": "modele", "label": sortie.PURPOSES["modele"],
         "what": f"{cat[model]['nom']} · {cat[model]['taille_go']} Go", "bytes": 0})
    PULLS[model] = {"status": "en cours", "done": 0, "total": int(cat[model]["taille_go"] * 1024 ** 3)}

    def work():
        try:  # appel LOCAL vers Ollama ; c'est Ollama qui télécharge depuis son registre
            for line in sortie.http_lines(engine["url"] + "/api/pull", {"model": model, "stream": True}):
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                if ev.get("error"):
                    raise RuntimeError(ev["error"])
                if ev.get("total"):
                    PULLS[model].update(done=ev.get("completed", 0), total=ev["total"])
                PULLS[model]["etape"] = ev.get("status", "")
            PULLS[model]["status"] = "fini"
            _cache["engines"] = None
        except Exception as e:
            PULLS[model].update(status="erreur", error=f"{type(e).__name__}: {e}"[:200])
    threading.Thread(target=work, daemon=True).start()
    return {"ok": True}


def _pull_gguf(model_id, log):
    m = next((x for x in catalogue().get("modeles", []) if x["id"] == model_id or (x.get("gguf") or {}).get("fichier") == model_id), None)
    g = (m or {}).get("gguf") or {}
    if not m or not g.get("url") or not g.get("sha256"):
        return {"ok": False, "msg": "Ce modèle sera téléchargeable avec la version publiée de l'app (empreinte pas encore fixée)."}
    key = g["fichier"]
    if PULLS.get(key, {}).get("status") == "en cours":
        return {"ok": True, "deja": True}
    PULLS[key] = {"status": "en cours", "done": 0, "total": int(m["taille_go"] * 1024 ** 3)}

    def work():
        try:
            sortie.download(g["url"], os.path.join(models_dir(), key), g["sha256"], "modele", consent=True, log=log,
                            what=f"{m['nom']} · {m['taille_go']} Go",
                            progress=lambda d, t: PULLS[key].update(done=d, total=t or PULLS[key]["total"]))
            PULLS[key]["status"] = "fini"
            _cache["engines"] = None
        except Exception as e:
            PULLS[key].update(status="erreur", error=f"{type(e).__name__}: {e}"[:200])
    threading.Thread(target=work, daemon=True).start()
    return {"ok": True}
