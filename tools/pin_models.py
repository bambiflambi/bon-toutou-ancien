"""Fixe les empreintes SHA-256 des modèles d'IA (fichiers GGUF) pour le moteur intégré.

Lancé par la fabrication automatique (GitHub Actions), jamais par l'app :
    python3 tools/pin_models.py engine/bontoutou/packs/modeles.json

Pour chaque modèle de la liste, on lit sur Hugging Face le dépôt officiel et le fichier voulu (quantification Q4_K_M
de préférence), puis on écrit dans la liste : adresse exacte (révision figée) + empreinte SHA-256 + nom du fichier.
L'app ne téléchargera qu'un fichier dont l'empreinte correspond exactement. Un modèle introuvable reste sans empreinte :
il n'est alors pas proposé au téléchargement (rien n'est deviné).
"""
import json
import re
import sys
import urllib.request

SOURCES = {  # identifiant Bon toutou -> (dépôt Hugging Face, motif du fichier)
    "ministral-3-3b": ("mistralai/Ministral-3-3B-Instruct-2512-GGUF", r"Q4_K_M\.gguf$"),
    "ministral-3-8b": ("mistralai/Ministral-3-8B-Instruct-2512-GGUF", r"Q4_K_M\.gguf$"),
    "ministral-3-14b": ("mistralai/Ministral-3-14B-Instruct-2512-GGUF", r"Q4_K_M\.gguf$"),
    "qwen3-vl-2b": ("Qwen/Qwen3-VL-2B-Instruct-GGUF", r"Q4_K_M\.gguf$"),
    "qwen3-vl-8b": ("Qwen/Qwen3-VL-8B-Instruct-GGUF", r"Q4_K_M\.gguf$"),
    "qwen3-vl-30b": ("Qwen/Qwen3-VL-30B-A3B-Instruct-GGUF", r"Q4_K_M\.gguf$"),
}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "bontoutou-build"}), timeout=60) as r:
        return json.loads(r.read())


def main(path):
    data = json.load(open(path, encoding="utf-8"))
    ok = 0
    for m in data["modeles"]:
        repo, pat = SOURCES.get(m["id"], (None, None))
        if not repo:
            continue
        try:
            info = get(f"https://huggingface.co/api/models/{repo}?blobs=true")
            files = [s for s in info.get("siblings", []) if re.search(pat, s["rfilename"], re.I) and "mmproj" not in s["rfilename"].lower()]
            if not files:
                raise LookupError("aucun fichier " + pat)
            f = sorted(files, key=lambda s: len(s["rfilename"]))[0]
            sha = (f.get("lfs") or {}).get("sha256")
            if not sha or len(sha) != 64:
                raise LookupError("empreinte absente")
            rev = info["sha"]
            m["gguf"] = {"fichier": f["rfilename"].split("/")[-1], "sha256": sha, "depot": repo, "revision": rev,
                         "url": f"https://huggingface.co/{repo}/resolve/{rev}/{f['rfilename']}",
                         "taille": (f.get("lfs") or {}).get("size")}
            ok += 1
            print(f"  ✓ {m['id']}: {m['gguf']['fichier']} · {sha[:12]}…")
        except Exception as e:
            m["gguf"] = None
            print(f"  ! {m['id']}: non fixé ({e}) — ne sera pas proposé au téléchargement")
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{ok}/{len(SOURCES)} modèles fixés")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "engine/bontoutou/packs/modeles.json")
