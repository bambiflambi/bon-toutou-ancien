"""Freemarket s'appelle maintenant Bon toutou.

Au premier lancement de Bon toutou, on reprend ce que Freemarket avait créé, en RENOMMANT seulement
(jamais de suppression, règle n° 1) :
  1. les données de cet appareil : « Application Support/Freemarket » -> « Application Support/Bon toutou » ;
  2. les fiches du bureau : « .freemarket » -> « .bontoutou » ;
  3. le bureau lui-même s'il porte le nom par défaut : « FREEMARKET_ADMIN » -> « BON_TOUTOU_ADMIN »
     (un bureau que tu as nommé autrement garde son nom) ;
  4. l'index local de cet appareil suit le bureau (sinon il serait reconstruit, plus lentement).
Ce qui a été fait est noté dans <bureau>/.bontoutou/migration-bon-toutou.json. Si un renommage est impossible
(dossier ouvert, disque en lecture seule…), on ne force rien : Bon toutou continue avec l'ancien nom.
"""
import datetime as dt
import os
import sys

from .core import data_home, local_key, read_json, write_json

OLD_FM, NEW_FM = ".freemarket", ".bontoutou"
OLD_ROOT, NEW_ROOT = "FREEMARKET_ADMIN", "BON_TOUTOU_ADMIN"


def old_data_home():
    env = os.environ.get("FREEMARKET_DATA")
    if env:
        return env
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/Freemarket")
    if os.name == "nt":
        return os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "Freemarket")
    return os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "freemarket")


def _note(root, notes):
    if not notes or not root:
        return
    p = os.path.join(root, NEW_FM, "migration-bon-toutou.json")
    d = read_json(p, {}) or {}
    d.setdefault("format", 1)
    d.setdefault("etapes", []).extend({"date": dt.datetime.now().isoformat(timespec="seconds"), "fait": n} for n in notes)
    try:
        write_json(p, d)
    except OSError:
        pass


def renommer_fiches(root, notes=None):
    """« .freemarket » -> « .bontoutou » dans un bureau. Ne fait rien si c'est déjà fait (ou si les deux existent)."""
    old, new = os.path.join(root, OLD_FM), os.path.join(root, NEW_FM)
    if os.path.isdir(old) and not os.path.exists(new):
        try:
            os.rename(old, new)
            msg = f"fiches renommées : {OLD_FM} -> {NEW_FM}"
            if notes is None:
                _note(root, [msg])
            else:
                notes.append(msg)
        except OSError:
            pass


def depuis_freemarket():
    """Appelé au démarrage. Retourne la liste de ce qui a été renommé (vide si rien à faire)."""
    notes = []
    new_home, old_home = data_home(), old_data_home()
    if not os.environ.get("BONTOUTOU_DATA") and os.path.isdir(old_home) and not os.path.exists(new_home):
        try:
            os.makedirs(os.path.dirname(new_home), exist_ok=True)
            os.rename(old_home, new_home)
            notes.append(f"données de l'appareil renommées : {old_home} -> {new_home}")
        except OSError:
            return notes
    cfg_path = os.path.join(data_home(), "config.json")
    cfg = read_json(cfg_path, {}) or {}
    root = cfg.get("bureau")
    if not root or not os.path.isdir(root):
        return notes
    renommer_fiches(root, notes)
    if os.path.basename(os.path.normpath(root)) == OLD_ROOT:
        new_root = os.path.join(os.path.dirname(os.path.normpath(root)), NEW_ROOT)
        if not os.path.exists(new_root):
            old_key = local_key(root)
            try:
                os.rename(root, new_root)
            except OSError:
                _note(root, notes)
                return notes
            notes.append(f"bureau renommé : {root} -> {new_root}")
            lo, ln = os.path.join(data_home(), "bureaux", old_key), os.path.join(data_home(), "bureaux", local_key(new_root))
            if os.path.isdir(lo) and not os.path.exists(ln):
                try:
                    os.rename(lo, ln)
                    notes.append("index de cet appareil repris tel quel")
                except OSError:
                    pass
            cfg.update({"format": 1, "bureau": new_root})
            write_json(cfg_path, cfg)
            root = new_root
    _note(root, notes)
    return notes
