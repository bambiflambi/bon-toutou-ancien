"""Lecture du contenu d'un fichier, uniquement sur l'ordinateur.

Ordre d'essai :
  PDF   : pypdf (si installé) -> pdftotext (poppler) -> OCR tesseract si le PDF est un scan
  Image : tesseract (OCR)
  Texte : lecture directe
Si aucun outil n'est installé, Bon toutou se contente du nom du fichier (et le dit).
Aucun appel réseau ici.
"""
import os
import shutil
import subprocess
import sys
import tempfile

IMG_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".webp", ".bmp"}


def _ocrmac():
    try:
        from ocrmac import ocrmac  # lecture de texte d'Apple (framework Vision) via pyobjc, sans compilation
        return ocrmac
    except Exception:
        return None


def _ocr_vision(path):
    """Lecture de texte intégrée à macOS. 100 % locale. PDF scanné : 1re page convertie en image par sips."""
    om = _ocrmac()
    if not om:
        return ""
    src = path
    with tempfile.TemporaryDirectory() as d:
        if path.lower().endswith(".pdf") and shutil.which("sips"):
            src = os.path.join(d, "p.png")
            _run(["sips", "-s", "format", "png", path, "--out", src], 60)
            if not os.path.exists(src):
                return ""
        try:
            res = om.OCR(src, recognition_level="accurate", language_preference=["fr-FR", "en-US"]).recognize()
            return "\n".join(r[0] for r in res)
        except Exception:
            return ""


def tools():
    """Outils de lecture disponibles sur cette machine."""
    t = {"apple_vision": _ocrmac() is not None, "pypdf": False, "pdftotext": bool(shutil.which("pdftotext")),
         "pdftoppm": bool(shutil.which("pdftoppm")), "tesseract": bool(shutil.which("tesseract"))}
    try:
        import pypdf  # noqa: F401
        t["pypdf"] = True
    except Exception:
        pass
    return t


def _run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return r.stdout.decode("utf-8", "ignore")
    except Exception:
        return ""


def _tess_langs():
    out = _run(["tesseract", "--list-langs"], 10)
    langs = [l.strip() for l in out.splitlines()[1:] if l.strip()]
    want = [l for l in ("fra", "eng") if l in langs]
    return "+".join(want) if want else None


def _ocr_image(path):
    t = _ocr_vision(path)
    if t.strip():
        return t
    if not shutil.which("tesseract"):
        return ""
    cmd = ["tesseract", path, "stdout"]
    lang = _tess_langs()
    if lang:
        cmd += ["-l", lang]
    return _run(cmd, 120)


def _pdf_text(path):
    text = ""
    try:
        import pypdf
        r = pypdf.PdfReader(path)
        text = "\n".join((p.extract_text() or "") for p in r.pages[:6])
        if len(text.strip()) > 30:
            return text, "pypdf"
    except Exception:
        pass
    if shutil.which("pdftotext"):
        text = _run(["pdftotext", "-l", "6", "-layout", path, "-"])
        if len(text.strip()) > 30:
            return text, "pdftotext"
    # Scan : lecture Apple d'abord, sinon rasterisation + tesseract
    t = _ocr_vision(path)
    if t.strip():
        return t, "ocr"
    if shutil.which("pdftoppm") and shutil.which("tesseract"):
        with tempfile.TemporaryDirectory() as d:
            _run(["pdftoppm", "-r", "200", "-l", "2", "-png", path, os.path.join(d, "p")], 120)
            parts = [_ocr_image(os.path.join(d, f)) for f in sorted(os.listdir(d)) if f.endswith(".png")]
            text = "\n".join(parts)
            if text.strip():
                return text, "ocr"
    return text, ("pdf-sans-texte" if not text.strip() else "pdf")


def extract(path):
    """Retourne (texte, méthode)."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return _pdf_text(path)
    if ext in IMG_EXT:
        t = _ocr_image(path)
        return t, ("ocr" if t.strip() else "image-sans-ocr")
    if ext in (".txt", ".md", ".csv"):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(20000), "texte"
        except Exception:
            return "", "illisible"
    return "", "format-non-lu"


def page_image(path, max_side=896):
    """Image PNG (octets) de la 1re page, pour l'IA locale qui « voit ». Uniquement des outils locaux.
    macOS : sips (intégré). Sinon : pdftoppm. Retourne None si impossible."""
    ext = os.path.splitext(path)[1].lower()
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "p.png")
        if shutil.which("sips"):
            _run(["sips", "-s", "format", "png", "-Z", str(max_side), path, "--out", out], 60)
        elif ext == ".pdf" and shutil.which("pdftoppm"):
            _run(["pdftoppm", "-r", "150", "-l", "1", "-png", "-singlefile", path, os.path.join(d, "p")], 60)
        elif ext in (".png", ".jpg", ".jpeg"):
            with open(path, "rb") as f:
                return f.read()
        if os.path.exists(out):
            with open(out, "rb") as f:
                return f.read()
    return None
