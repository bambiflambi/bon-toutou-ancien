"""Serveur local Bon toutou : écoute uniquement sur 127.0.0.1 (ton ordinateur), jamais sur le réseau.

Lancement :  python3 -m bontoutou.server --root "/chemin/vers/BON_TOUTOU_ADMIN"
"""
import argparse
import json
import mimetypes
import os
import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__
from . import maj
from .core import Bureau, data_home, read_json, write_json

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(os.path.dirname(HERE), "static")
B = None


ERRORS = []  # dernières erreurs (pour un rapport de bug relu par l'utilisateur)


def app_config_path():
    return os.path.join(data_home(), "config.json")


class H(BaseHTTPRequestHandler):
    server_version = "Bon toutou/" + __version__

    def log_message(self, fmt, *args):  # console discrète
        if sys.stderr is None or "/api/" in str(args[0] if args else ""):
            return
        sys.stderr.write("  " + fmt % args + "\n")

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def _file(self, path, inline=True):
        if not os.path.isfile(path):
            return self._json({"error": "introuvable"}, 404)
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Disposition", ("inline" if inline else "attachment") + "; filename*=UTF-8''" + urllib.parse.quote(os.path.basename(path)))
        self.end_headers()
        self.wfile.write(data)

    def _guard(self):
        # refuse toute requête qui ne vient pas de cette machine
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
            self._json({"error": "accès local uniquement"}, 403)
            return False
        return True

    def do_GET(self):
        if not self._guard():
            return
        u = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        p = u.path
        try:
            if p == "/" or p == "/index.html":
                return self._file(os.path.join(STATIC, "index.html"))
            if p.startswith("/static/"):
                f = os.path.normpath(os.path.join(STATIC, p[len("/static/"):]))
                if f.startswith(STATIC):
                    return self._file(f)
            if p == "/api/state":
                if B is None:
                    return self._json(maj.setup_state())
                st = B.state()
                st["version"] = __version__
                st["app"] = bool(os.environ.get("BONTOUTOU_APP"))
                return self._json(st)
            if B is None and p.startswith("/api/"):
                return self._json({"error": "installation à terminer", "setup": True}, 409)
            if p == "/api/inbox":
                return self._json(B.inbox())
            if p == "/api/docs":
                return self._json(B.documents())
            if p == "/api/doc":
                return self._json(B.document(q["id"]))
            if p == "/api/dossiers":
                return self._json(B.dossiers())
            if p == "/api/dossier":
                return self._json(B.dossier(q["id"]))
            if p == "/api/archives":
                return self._json(B.archives())
            if p == "/api/rules":
                return self._json(B.regles.state())
            if p == "/api/rules/export":
                body = json.dumps(B.regles.export(), ensure_ascii=False, indent=1).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Disposition", "attachment; filename=bon-toutou-mes-regles.json")
                self.end_headers()
                self.wfile.write(body)
                return
            if p == "/api/text":
                if q.get("doc"):
                    r = B.db.execute("SELECT sha,path FROM docs WHERE id=?", (q["doc"],)).fetchone()
                else:
                    r = B.db.execute("SELECT sha,path FROM inbox WHERE id=?", (q.get("inbox"),)).fetchone()
                return self._json({"text": B.text_of(r["sha"], r["path"])[0] if r else ""})
            if p == "/api/ia":
                from . import ia
                return self._json({"engines": ia.engines(force=q.get("force") == "1"), "pulls": ia.PULLS})
            if p == "/api/events":
                return self._json(B.events())
            if p == "/api/contacts":
                return self._json(B.contacts())
            if p == "/api/calendrier.ics":
                body = B.ics().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/calendar; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Disposition", "attachment; filename=bon-toutou-echeances.ics")
                self.end_headers()
                self.wfile.write(body)
                return
            if p == "/api/guide":
                return self._json(B.guide())
            if p == "/api/sorties":
                return self._json(B.sorties())
            if p == "/api/history":
                return self._json(B.history())
            if p == "/api/file":
                return self._file(B.abs(q["p"]), inline=q.get("dl") != "1")
            if p == "/api/inboxfile":
                r = B.db.execute("SELECT path FROM inbox WHERE id=?", (q["id"],)).fetchone()
                return self._file(B.abs(r["path"]))
        except Exception as e:  # pragma: no cover
            ERRORS.append({"route": p, "error": f"{type(e).__name__}: {e}"[:300]})
            del ERRORS[:-20]
            return self._json({"error": f"{type(e).__name__}: {e}"}, 500)
        self._json({"error": "route inconnue"}, 404)

    def do_POST(self):
        if not self._guard():
            return
        u = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        p = u.path
        try:
            if B is None and p != "/api/setup":
                return self._json({"error": "installation à terminer", "setup": True}, 409)
            if p == "/api/upload":
                iid = B.add_upload(q.get("name", "document"), self._body())
                return self._json({"ok": True, "id": iid, "duplicate": iid is None})
            if p == "/api/rules/import":
                return self._json(B.regles.import_pack(self._body().decode("utf-8", "ignore"), confirm=q.get("confirm") == "1"))
            data = json.loads(self._body() or b"{}")
            if p == "/api/setup":
                return self._json(do_setup(data))
            if B is None:
                return self._json({"error": "installation à terminer", "setup": True}, 409)
            if p == "/api/maj/check":
                return self._json(maj.check(B, data.get("consent")))
            if p == "/api/bug":
                return self._json(maj.bug_report(B, ERRORS))
            if p == "/api/bug/sent":
                B.log_sortie({"dest": data.get("dest") or "ta messagerie", "purpose": "bug", "label": "Rapport de bug",
                              "what": "rapport relu par toi", "bytes": int(data.get("bytes") or 0)})
                return self._json({"ok": True})
            R = B.regles
            if p == "/api/rules/preview":
                return self._json(R.preview(data.get("rule")))
            if p == "/api/rules/save":
                return self._json(R.save(data.get("rule")))
            if p == "/api/rules/toggle":
                return self._json(R.toggle(data["id"], data.get("actif")))
            if p == "/api/rules/delete":
                return self._json(R.delete(data["id"]))
            if p == "/api/rules/apply":
                return self._json(R.apply(data["id"], data.get("docs", [])))
            if p == "/api/rules/test":
                return self._json(R.test(data["id"], data["doc"]))
            if p == "/api/rules/remove":
                return self._json(R.remove_pack(data["file"]))
            if p == "/api/types/save":
                return self._json(R.save_type(data.get("type", {})))
            if p == "/api/rules/propose":
                return self._json(R.propose(data.get("ids"), data.get("types")))
            if p == "/api/rules/proposed":
                B.log_sortie({"dest": data.get("dest") or "ta messagerie", "purpose": "proposition", "label": "Proposition de règles",
                              "what": data.get("what", ""), "bytes": int(data.get("bytes") or 0)})
                return self._json({"ok": True})
            if p == "/api/ia/pull":
                return self._json(B.ai_pull(data.get("engine"), data.get("model"), data.get("consent")))
            if p == "/api/ia/test":
                return self._json(B.ai_test(data.get("engine"), data.get("model")))
            if p == "/api/mask":
                from .sortie import mask
                t, f = mask(data.get("text", ""))
                return self._json({"text": t, "found": f})
            if p == "/api/reanalyze":
                return self._json(B.reanalyze())
            if p == "/api/scan":
                return self._json({"ok": True, "added": B.scan_inbox()})
            if p == "/api/propose":
                return self._json(B.set_overrides(data["id"], data.get("overrides", {})))
            if p == "/api/validate":
                return self._json(B.validate(data["ids"]))
            if p == "/api/ignore":
                return self._json(B.ignore(data["id"]))
            if p == "/api/undo":
                return self._json(B.undo(data.get("batch")))
            if p == "/api/reclassify":
                return self._json(B.reclassify(data["id"], data.get("fields", {})))
            if p == "/api/redetect":
                return self._json(B.redetect())
            if p == "/api/terminate":
                return self._json(B.terminate(data["id"]))
            if p == "/api/dossier/create":
                return self._json({"id": B.create_dossier(data["template"], data.get("recipient", ""), data["country"])})
            if p == "/api/dossier/assign":
                return self._json(B.assign(data["id"], data["piece"], data.get("docs", [])))
            if p == "/api/dossier/finalize":
                return self._json(B.finalize(data["id"]))
            if p == "/api/dossier/reopen":
                return self._json(B.reopen(data["id"]))
            if p == "/api/dossier/sent":
                return self._json(B.mark_sent(data["id"]))
            if p == "/api/dossier/abandon":
                return self._json(B.abandon(data["id"]))
            if p == "/api/settings":
                return self._json(B.save_settings(data))
            if p == "/api/rebuild":
                return self._json(B.rebuild_index())
            if p == "/api/reveal":
                return self._json(B.reveal(data["p"]))
            if p == "/api/open":
                return self._json(B.open_path(data.get("p"), data.get("inbox")))
            if p == "/api/export":
                return self._json(B.export(data.get("kind"), data.get("text")))
        except Exception as e:
            ERRORS.append({"route": p, "error": f"{type(e).__name__}: {e}"[:300]})
            del ERRORS[:-20]
            return self._json({"ok": False, "error": f"{type(e).__name__}: {e}"}, 500)
        self._json({"error": "route inconnue"}, 404)


def pid_alive(pid):
    if os.name == "nt":
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE
        if not h:
            return False
        r = ctypes.windll.kernel32.WaitForSingleObject(h, 0)
        ctypes.windll.kernel32.CloseHandle(h)
        return r == 0x102  # WAIT_TIMEOUT : toujours en vie
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def watch_parent(pid, srv):
    """L'app s'est fermée (même brutalement) : le moteur s'arrête aussi, rien ne reste en arrière-plan."""
    import time
    while pid_alive(pid):
        time.sleep(2)
    srv.shutdown()
    os._exit(0)


def do_setup(data):
    """Installation : crée (ou reprend) le dossier administratif choisi, puis enregistre le profil."""
    global B
    path = os.path.abspath(os.path.expanduser((data.get("path") or "").strip()))
    if not data.get("path") or not os.path.isdir(os.path.dirname(path)):
        return {"ok": False, "msg": "Choisis un emplacement qui existe sur ton ordinateur."}
    home = os.path.expanduser("~")
    if path in ("/", home) or path == os.path.dirname(home):
        return {"ok": False, "msg": "Choisis un dossier dédié, pas ton dossier personnel entier."}
    os.makedirs(path, exist_ok=True)
    B = Bureau(path)
    patch = {}
    if data.get("owner"):
        patch["owner"] = data["owner"].strip()
    if data.get("countries"):
        patch["countries"] = [c for c in data["countries"] if c in maj.COUNTRY_CODES()] or ["FR"]
    if patch:
        B.save_settings(patch)
    cfg = read_json(app_config_path(), {}) or {}
    cfg.update({"format": 1, "bureau": B.root})
    write_json(app_config_path(), cfg)
    return {"ok": True, "root": B.root}


def main():
    global B
    ap = argparse.ArgumentParser(description="Bon toutou — ton dossier administratif vivant")
    ap.add_argument("--root", help="dossier administratif (sinon : celui choisi à l'installation)")
    ap.add_argument("--port", type=int, default=8765, help="0 = un port libre au hasard (utilisé par l'app)")
    ap.add_argument("--data", help="dossier des données locales de l'appareil")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--app", action="store_true", help="lancé par l'app de bureau")
    ap.add_argument("--watch-pid", type=int, help="s'arrêter quand ce programme (l'app) se ferme")
    a = ap.parse_args()
    if a.data:
        os.environ["BONTOUTOU_DATA"] = a.data
    if a.app:
        os.environ["BONTOUTOU_APP"] = "1"
    if not a.root:
        from .migration import depuis_freemarket
        depuis_freemarket()  # Freemarket -> Bon toutou : on renomme, on ne supprime rien
    root = a.root or (read_json(app_config_path(), {}) or {}).get("bureau")
    if not root:  # ancien prototype : App_v0/config.json ou kit voisin
        cfg_path = os.path.join(os.path.dirname(HERE), "config.json")
        cfg = read_json(cfg_path, {}) or {}
        root = cfg.get("root")
        if root and not os.path.isabs(os.path.expanduser(root)):
            root = os.path.normpath(os.path.join(os.path.dirname(HERE), root))
        if not root:
            guess = os.path.join(os.path.dirname(os.path.dirname(HERE)), "Kit_v0_Rangement", "BON_TOUTOU_ADMIN")
            root = guess if os.path.isdir(guess) else None
    if root and os.path.isdir(os.path.expanduser(root)):
        B = Bureau(root)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    port = srv.server_address[1]
    url = f"http://127.0.0.1:{port}/"
    try:
        print(f"BONTOUTOU_PORT={port}", flush=True)  # utile en ligne de commande (port 0 = choisi au hasard)
        print(f"\n  Bon toutou {__version__}\n  Bureau : {B.root if B else '(installation à faire)'}\n  Ouvre : {url}\n"
              "  (Ctrl+C pour arrêter — rien n'est accessible depuis le réseau)\n", flush=True)
    except (AttributeError, OSError, ValueError):
        pass  # app sans console (Windows) : pas de sortie texte, ce n'est pas grave
    if a.watch_pid:
        threading.Thread(target=watch_parent, args=(a.watch_pid, srv), daemon=True).start()
    if not a.no_browser and not a.app:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Bon toutou arrêté.")


if __name__ == "__main__":
    main()
