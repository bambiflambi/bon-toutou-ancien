"""Compréhension d'un document : type, pays, émetteur, date, expiration.

1. Règles (mots-clés, émetteurs connus, dates) — rapides, explicables.
2. Si la confiance reste basse et qu'une IA locale (Ollama) tourne sur l'ordinateur,
   on lui demande un avis. Ollama est local (127.0.0.1) : rien ne sort de la machine.
Chaque décision garde ses raisons, affichées dans « Pourquoi ? ».
"""
import datetime as dt
import json
import re
import unicodedata

from . import sortie

from .catalog import COUNTRIES, COUNTRY_HINTS, EMITTERS, EXPIRY_HINTS, RULES, TYPES

MONTHS = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "aout": 8,
          "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
          "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7, "august": 8,
          "september": 9, "october": 10, "november": 11, "december": 12,
          "janv": 1, "fevr": 2, "avr": 4, "juil": 7, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
          "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("’", "'")
    return re.sub(r"[ \t]+", " ", s)


def _has(hay, kw):
    """Mot-clé présent comme mot entier (évite 'rib' dans 'contribution')."""
    k = kw.strip()
    if not k:
        return False
    if not re.match(r"\w", k[0]):
        return k in hay
    return re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", hay) is not None


def _mkdate(y, m, d):
    try:
        y = int(y)
        if y < 100:
            y += 2000
        return dt.date(y, int(m), int(d))
    except Exception:
        return None


def find_dates(text):
    """Toutes les dates du texte, avec leur position."""
    t = norm(text)
    out = []
    for m in re.finditer(r"(?<!\d)(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4}|\d{2})(?!\d)", t):
        d = _mkdate(m.group(3), m.group(2), m.group(1))
        if d:
            out.append((m.start(), d))
    for m in re.finditer(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)", t):
        d = _mkdate(m.group(1), m.group(2), m.group(3))
        if d:
            out.append((m.start(), d))
    mn = "|".join(sorted(MONTHS, key=len, reverse=True))
    for m in re.finditer(r"(?<!\d)(\d{1,2})(?:er)?\s+(" + mn + r")\.?\s+(\d{4})", t):
        d = _mkdate(m.group(3), MONTHS[m.group(2)], m.group(1))
        if d:
            out.append((m.start(), d))
    for m in re.finditer(r"(" + mn + r")\.?\s+(\d{1,2}),?\s+(\d{4})", t):
        d = _mkdate(m.group(3), MONTHS[m.group(1)], m.group(2))
        if d:
            out.append((m.start(), d))
    for m in re.finditer(r"(?<![\d\w])(" + mn + r")\.?\s+(\d{4})", t):  # "mars 2025" -> fin de mois
        y, mo = int(m.group(2)), MONTHS[m.group(1)]
        nxt = dt.date(y + (mo == 12), mo % 12 + 1, 1)
        out.append((m.start(), nxt - dt.timedelta(days=1)))
    return out, t


# ---------- Dates approximatives (seulement l'année, ou le mois et l'année) ----------
# Chiffres souvent mal lus par l'OCR dans une année : O->0, I/l->1, S->5, B->8
_OCR_DIGIT = str.maketrans({"o": "0", "i": "1", "l": "1", "s": "5", "b": "8", "z": "2"})
YEAR_CTX = ("session", "annee scolaire", "annee universitaire", "promotion", "promo", "millesime", "exercice",
            "campagne", "delivre en", "obtenu en", "reussi en", "class of", "year", "annee", "saison", "cuvee")
SCHOOL_TYPES = ("assr", "diplome", "certificat")


def _fix_years(t):
    """Corrige les années abîmées par l'OCR (2O17, 2Ol7 -> 2017). Les années à un chiffre illisible (201?) restent telles quelles."""
    return re.sub(r"(?<![\w])([12][0-9oilsbz]{3})(?![\w])",
                  lambda m: m.group(1).translate(_OCR_DIGIT) if re.match(r"(19|20)\d\d$", m.group(1).translate(_OCR_DIGIT)) else m.group(1), t)


def approx_date(text, filename, today, type_id=None):
    """Quand aucune date complète n'est écrite. Retourne (date, précision 'mois'|'annee', explication) ou (None, None, None)."""
    t = _fix_years(norm(text) + " \n " + norm(filename.replace("_", " ")))
    ok = lambda y: 1950 <= y <= today.year
    full_years = [int(y) for y in re.findall(r"(?<![\d\w])((?:19|20)\d\d)(?![\d\w])", t) if ok(int(y))]
    mn = "|".join(sorted(MONTHS, key=len, reverse=True))

    def end_of_month(y, mo):
        d = dt.date(y + (mo == 12), mo % 12 + 1, 1) - dt.timedelta(days=1)
        return min(d, today)

    def resolve(ystr):
        """'2017' -> 2017 ; '201?' -> l'année complète du document qui commence pareil (si une seule)."""
        if ystr.isdigit():
            return int(ystr) if ok(int(ystr)) else None
        pre = re.sub(r"\D.*$", "", ystr)
        cands = sorted({y for y in full_years if str(y).startswith(pre)})
        return cands[-1] if len(pre) >= 3 and cands else None
    # 1. mois + année, même avec un chiffre illisible : « juin 201? », « 06/2017 »
    for m in re.finditer(r"(?<![\w])(" + mn + r")\.?\s+((?:19|20)[\d?]{2})", t):
        y = resolve(m.group(2))
        if y:
            return end_of_month(y, MONTHS[m.group(1)]), "mois", f"seuls le mois et l'année sont écrits ({m.group(1)} {y}) : fin du mois retenue"
    for m in re.finditer(r"(?<![\d/.\-])(0?[1-9]|1[0-2])[/.\-]((?:19|20)\d\d)(?![\d/.\-])", t):
        y = int(m.group(2))
        if ok(y):
            return end_of_month(y, int(m.group(1))), "mois", f"seuls le mois et l'année sont écrits ({m.group(1)}/{y}) : fin du mois retenue"
    # 2. année scolaire « 2016-2017 » -> fin juin de la 2e année
    for m in re.finditer(r"(?<!\d)((?:19|20)\d\d)\s*[-/]\s*((?:19|20)\d\d)(?!\d)", t):
        a, b = int(m.group(1)), int(m.group(2))
        if b == a + 1 and ok(b):
            return min(dt.date(b, 6, 30), today), "annee", f"année scolaire {a}-{b} : fin juin {b} retenue"
    # 3. année près d'un mot qui la date : « Session 2017 », « Promotion 2019 », « Exercice 2023 »
    school = type_id in SCHOOL_TYPES
    for m in re.finditer(r"(?<![\d\w])((?:19|20)\d\d)(?![\d\w])", t):
        y = int(m.group(1))
        ctx = t[max(0, m.start() - 25):m.start()]
        if ok(y) and any(c in ctx for c in YEAR_CTX):
            word = next(c for c in YEAR_CTX if c in ctx)
            if school or word in ("session", "annee scolaire", "annee universitaire", "promotion", "promo"):
                return min(dt.date(y, 6, 30), today), "annee", f"seule l'année est écrite (« {word} {y} ») : fin juin {y} retenue, à vérifier"
            return dt.date(y, 12, 31) if y < today.year else today, "annee", f"seule l'année est écrite (« {word} {y} ») : 31 décembre retenu, à vérifier"
    # 4. une seule année plausible dans tout le document
    uniq = sorted(set(full_years))
    if len(uniq) == 1:
        y = uniq[0]
        if school:
            return min(dt.date(y, 6, 30), today), "annee", f"seule l'année {y} apparaît : fin juin retenue, à vérifier"
        return (dt.date(y, 12, 31) if y < today.year else today), "annee", f"seule l'année {y} apparaît : 31 décembre retenu, à vérifier"
    return None, None, None


# ---------- Intitulé exact (detail) déduit du texte, par type ----------
ACRONYMS = {"am", "a1", "a2", "a", "b1", "be", "b", "c1", "ce", "c", "d1", "de", "d", "bts", "dut", "but", "cap", "bep", "bafa", "bafd",
            "deust", "dnb", "toeic", "toefl", "ielts", "delf", "dalf", "tcf", "cdi", "cdd", "caces", "haccp"}


def _detail(type_id, hay, fhay):
    from .catalog import DETAILS
    h = hay + " \n " + fhay
    for pat, tpl, org in DETAILS.get(type_id, []):
        m = re.search(pat, h)
        if m:
            out = tpl
            for i, g in enumerate(m.groups(), 1):
                g = (g or "").strip()
                out = out.replace("{" + str(i) + "}", g.upper() if (g in ACRONYMS or g.isdigit()) else g.title())
            return out, m.group(0).strip(), org
    return None, None, None


# ---------- Émetteur quand aucun organisme connu n'est cité ----------
INSTITUTIONS = r"(?:docteur|college|lycee|ecole|universite|iut|institut|academie|rectorat|mairie|sous-prefecture|prefecture|ambassade|consulat|tribunal|clinique|hopital|centre hospitalier|auto-ecole|cabinet|pharmacie|agence|chambre des metiers|cci)"
_PLACE_FIX = [(r"^(si|5t|st\.|s t|saint)\s+", "St "), (r"^(ste|sainte)\s+", "Ste ")]


def _place(s):
    s = re.sub(r"[^\w' \-]", " ", s).strip()
    s = " ".join(s.split()[:4])
    for pat, rep in _PLACE_FIX:
        s = re.sub(pat, rep, s, flags=re.I)
    return s


def emitter_fallback(text):
    """Nom d'établissement (« Collège Jean Moulin », « Mairie de Rochefort »), sinon lieu « Fait à … ». Retourne (nom, explication)."""
    raw = unicodedata.normalize("NFKD", text or "")
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    m = re.search(r"\b(?i:(" + INSTITUTIONS + r"))\b[ \t]+((?:de |du |des |d'|la |le )?[A-Z][\w'\-]*(?:[ \t]+(?:de |du |des |d'|la |le )?[A-Z][\w'\-]*){0,3})", raw)
    if m:
        name = (m.group(1).title() + " " + m.group(2)).strip()
        return slugify(name)[:30], f"établissement lu dans le texte : « {name} »"
    m = re.search(r"(?i)\bfait\s+(?:a|à)\s+([A-Za-z][\w' \-]{2,40})", raw)
    if m:
        place = _place(m.group(1).split("\n")[0].split(",")[0])
        if len(place) >= 3:
            return slugify(place)[:30], f"aucun organisme reconnu : lieu d'émission « {place} » utilisé, à préciser si tu veux"
    return None, None


def _pick_dates(text, filename, today):
    dates, t = find_dates(text)
    expiry = None
    for pos, d in dates:
        ctx = t[max(0, pos - 45):pos]
        if any(h in ctx for h in EXPIRY_HINTS):
            expiry = d if expiry is None else max(expiry, d)
    past = [d for _, d in dates if dt.date(1990, 1, 1) <= d <= today]
    doc_date, why = None, None
    # période « du … au … » (fiches de paie, relevés) : on garde la fin de période
    for pos, d in dates:
        ctx = t[max(0, pos - 40):pos]
        if re.search(r"(periode|period|du)\b.*\b(au|to)\s*$", ctx) and d <= today:
            return d, expiry, "fin de la période couverte"
    # priorité : date d'émission explicite
    for pos, d in dates:
        ctx = t[max(0, pos - 40):pos]
        if d <= today and any(k in ctx for k in ("emis le", "etabli le", "date d'emission", "date :", "le ", "date de la facture",
                                                  "issue date", "date of issue", "periode du", "au ")):
            doc_date, why = d, "date lue près d'un libellé de date"
            break
    if not doc_date and past:
        doc_date, why = max(past), "date la plus récente du document"
    if not doc_date:
        fd, _ = find_dates(filename.replace("_", " "))
        fd = [d for _, d in fd if d <= today]
        if fd:
            doc_date, why = fd[0], "date lue dans le nom du fichier"
    return doc_date, expiry, why


EMPLOYMENT = ("bulletin_paie", "solde_tout_compte", "contrat_travail", "attestation_employeur")
# organismes cités dans une fiche de paie sans en être l'émetteur (cotisations, retenues)
NOT_EMPLOYER = {"URSSAF", "CPAM", "France-Travail", "DGFiP", "CAF"}


LEGAL = {"sarl", "sas", "sasu", "sa", "eurl", "sci", "snc", "selarl", "scop", "sca", "ltd", "limited", "inc", "gmbh"}
PERSONS = set()  # mots du nom du titulaire et de ses proches (mis à jour par le bureau) : une ligne qui les contient n'est jamais un employeur
_ADDR = re.compile(r"(?i)\b(rue|avenue|av\.|bd|boulevard|chemin|allee|allée|place|impasse|route|quai|cedex|bp|cs|lieu[- ]dit|zone|za|zi|"
                   r"street|st|road|rd|lane|drive|po box|private bag)\b|\b\d{4,5}\b")
_NOT_NAME = re.compile(r"(?i)(bulletin|paie|salaire|periode|période|matricule|salari|emploi|qualification|coefficient|convention|"
                       r"\bdate\b|\bpage\b|n°|\bno\b|siret|siren|urssaf|\bape\b|\bnaf\b|net\b|brut|montant|payslip|pay period|pay date|"
                       r"cotisation|\btotal\b|heures|\btaux\b|\bbase\b|contrat|recu|reçu|solde|attestation|niveau|echelon|échelon|"
                       r"entree|entrée|anciennete|ancienneté|@|www\.|\btel\b|\btél\b|\bfax\b|\bird\b|tax code)")
_TITLE = re.compile(r"(?i)^(m\.|mme|mlle|monsieur|madame|mr|mrs|ms|miss)\b")


def _clean_company(raw):
    """« LE PETIT BISTROT SAS au capital de 10 000 € » -> « LE PETIT BISTROT »."""
    t = re.split(r"(?i)\b(au capital|capital de|siret|siren|rcs|n° tva|tva intra)\b", raw)[0]
    words = [w for w in re.split(r"[\s,;]+", t.strip(" -–—:.,")) if w]
    words = [w for w in words if w.lower().strip(".") not in LEGAL]
    name = " ".join(words[:5]).strip(" -–—:.,")
    return _nice(name)


def _nice(name):
    """« LE PETIT BISTROT » -> « Le Petit Bistrot » (les en-têtes sont souvent en capitales)."""
    if not name.isupper():
        return name
    small = {"DE", "DU", "DES", "LA", "LE", "LES", "ET", "D'", "L'", "AU", "AUX", "EN", "SUR", "OF", "THE", "AND"}
    out = []
    for i, w in enumerate(name.split()):
        if i and w in small:
            out.append(w.lower())
        else:
            out.append(w.capitalize() if re.search(r"[AEIOUY]", w) else w)  # LCL, SNCF restent en capitales
    return " ".join(out)


def _plausible(line):
    l = line.strip()
    if not (3 <= len(l) <= 70) or sum(c.isalpha() for c in l) < 3 or l[0].isdigit():
        return False
    if _ADDR.search(l) or _NOT_NAME.search(l) or _TITLE.search(l):
        return False
    toks = set(slugify(l).lower().split("-"))
    if PERSONS & toks:
        return False
    return True


def _employer(text):
    """Employeur d'une fiche de paie, d'un contrat… Retourne (nom, comment il a été trouvé) ou (None, None).
    1. un libellé (« Employeur : … ») ; 2. une forme juridique (SAS, SARL, Ltd…) dans l'en-tête ;
    3. la première ligne de l'en-tête au-dessus du SIRET / code APE / n° URSSAF."""
    raw = text or ""
    tok = r"[A-Z0-9][A-Za-z0-9&'\-]*"
    name_re = r"(" + tok + r"(?:[ ]" + tok + r"){0,5})"
    m = (re.search(r"(?i:employeur|raison sociale|employer|etablissement|établissement|societe|société|entreprise)\s*[:\n]\s*" + name_re, raw)
         or re.search(name_re + r",?\s+(?i:employeur|employer)\b", raw))
    if m:
        words = m.group(1).split()
        if words and words[0].lower() in ("entre", "between"):
            words = words[1:]
        out = []
        for w in words:
            if w.lower().strip(".") in LEGAL:
                break
            out.append(w)
        name = _nice(" ".join(out[:4]).strip())
        if name and _plausible(name):
            return slugify(name)[:30], "employeur indiqué dans le document"
    lines = [l.strip() for l in raw.splitlines() if l.strip()][:45]
    legal = re.compile(r"(?i)(?:^|\s)(" + "|".join(sorted(LEGAL, key=len, reverse=True)) + r")\.?(?:\s|$|,)")
    for l in lines:
        mm = legal.search(" " + l + " ")
        if mm and not _ADDR.search(l.split("capital")[0]) and not _TITLE.search(l):
            name = _clean_company(l)
            if name and _plausible(name):
                return slugify(name)[:30], f"forme juridique lue dans l'en-tête (« {l[:60]} »)"
    for i, l in enumerate(lines):
        if re.search(r"(?i)\b(siret|siren|code ape|ape\b|naf\b|urssaf|ird number|nzbn)", l):
            for c in lines[max(0, i - 6):i]:
                if _plausible(c):
                    return slugify(_clean_company(c))[:30], f"nom lu en haut du document, au-dessus du n° {re.search(r'(?i)siret|siren|ape|naf|urssaf|ird number|nzbn', l).group(0).upper()}"
            break
    return None, None


def _emitter(hay, text, type_id):
    if type_id in EMPLOYMENT:
        e, how = _employer(text)
        if e:
            return e, None, how
    for pat, name, cc, org in EMITTERS:
        if type_id in EMPLOYMENT and name in NOT_EMPLOYER:
            continue
        if _has(hay, norm(pat)):
            return name, cc, org
    return None, None, None


FIELD_LABEL = {"type": "Type", "emitter": "Émetteur", "detail": "Intitulé", "country": "Pays"}


def rule_hits(hay, champ, type_id=None):
    """Règles « contient X » qui s'appliquent : la plus prioritaire d'abord (perso, puis importées, puis officielles)."""
    out = []
    for ind, ch, val, rtype, org, rid in RULES:
        if ch == champ and (not rtype or rtype == type_id or champ == "type") and _has(hay, norm(ind)):
            out.append((ind, val, org, rid))
    return out


def rule_text(ind, champ, val):
    lab = TYPES[val]["label"] if champ == "type" and val in TYPES else COUNTRIES.get(val, {}).get("name", val) if champ == "country" else val
    return f"contient « {ind} » → {FIELD_LABEL[champ]} : {lab}"


def slugify(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")
    return s or "Inconnu"


def analyze(text, filename, countries, today=None):
    """Retourne une proposition complète + raisons."""
    today = today or dt.date.today()
    hay = norm(text)
    fhay = norm(filename.replace("_", " ").replace("-", " "))
    reasons = []
    scores = {}
    hits = {}
    for tid, T in TYPES.items():
        if tid == "autre":
            continue
        h = [k for k in T.get("kw", []) if _has(hay, norm(k))]
        f = [k for k in T.get("fn", []) if _has(fhay, norm(k))]
        sc = 2 * len(h) + len(f)
        if sc:
            scores[tid] = sc
            hits[tid] = (h, f)
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    type_id = ranked[0][0] if ranked else "autre"
    top = ranked[0][1] if ranked else 0
    second = ranked[1][1] if len(ranked) > 1 else 0
    # une facture d'énergie/télécom est plus précise qu'une facture générique
    if type_id == "facture" and scores.get("facture_energie", 0) >= 2:
        type_id = "facture_energie"
    # formulaire vierge (Cerfa) : il cite souvent l'avis d'impôt, la fiche de paie… sans en être un
    if (_has(hay, "cerfa") or _has(fhay, "cerfa")) and "formulaire" in TYPES and type_id not in ("aide_juridictionnelle", "formulaire"):
        type_id = "aide_juridictionnelle" if "aide_juridictionnelle" in scores else "formulaire"
        top = scores.get(type_id, 2)
    # « solde de tout compte » contient souvent aussi les mots d'une fiche de paie : il gagne s'il est présent
    if "solde_tout_compte" in scores and scores["solde_tout_compte"] >= 2:
        type_id, top = "solde_tout_compte", max(top, scores["solde_tout_compte"])
    forced = None
    for ind, val, org, rid in rule_hits(hay + " \n " + fhay, "type"):
        if val in TYPES:
            forced = (ind, val, org)
            type_id, top = val, max(top, 4)
            break
    if forced:
        reasons.append(f"{forced[2]} : {rule_text(forced[0], 'type', forced[1])}")
    if type_id != "autre" and not forced:
        h, f = hits.get(type_id, ([], []))
        if h:
            reasons.append("Le document contient « " + "», «".join(h[:3]) + " »" + f" [{TYPES[type_id].get('_origin', '')}]")
        if f:
            reasons.append("Le nom du fichier évoque « " + "», «".join(f[:2]) + " »")

    # Pays
    cscore = {c: sum(1 for k in COUNTRY_HINTS[c] if _has(hay, k.strip()) or (k.strip() in ("€",) and k in hay)) for c in COUNTRIES}
    emitter, ecc, eorg = _emitter(re.sub(r"\S+@\S+|www\.\S+", " ", hay) + " " + fhay, text, type_id)  # une adresse e-mail (x@orange.fr) ne désigne pas l'émetteur
    if ecc:
        cscore[ecc] = cscore.get(ecc, 0) + 2
    allowed = TYPES[type_id].get("countries")
    if allowed:
        for c in cscore:
            if c not in allowed:
                cscore[c] = -99
    best_c = max(cscore.items(), key=lambda x: x[1])
    if best_c[1] > 0:
        country = best_c[0]
        reasons.append(f"Indices de pays : {COUNTRIES[country]['name']}")
    else:
        country = (allowed or countries or ["FR"])[0]
        reasons.append(f"Pays non trouvé dans le texte : {COUNTRIES[country]['name']} par défaut")
    emitter_approx = False
    both = hay + " \n " + fhay
    rh = rule_hits(both, "emitter", type_id)
    if rh:
        emitter, eorg = slugify(rh[0][1])[:30], None
        reasons.append(f"{rh[0][2]} : {rule_text(rh[0][0], 'emitter', rh[0][1])}")
    rc = rule_hits(both, "country", type_id)
    if rc and rc[0][1] in COUNTRIES:
        best_c = (rc[0][1], 99)
        country = rc[0][1]
        reasons.append(f"{rc[0][2]} : {rule_text(rc[0][0], 'country', rc[0][1])}")
    if emitter and rh:
        pass
    elif emitter:
        reasons.append(f"Émetteur reconnu : {emitter}" + (f" [{eorg}]" if eorg else ""))
    elif text.strip():
        emitter, ewhy = emitter_fallback(text)
        if emitter:
            emitter_approx = True
            reasons.append("Émetteur : " + ewhy)

    doc_date, expiry, dwhy = _pick_dates(text, filename, today)
    precision, date_note = ("jour", None) if doc_date else (None, None)
    if doc_date:
        reasons.append(f"Date : {doc_date.isoformat()} ({dwhy})")
    else:
        doc_date, precision, awhy = approx_date(text, filename, today, type_id)
        if doc_date:
            date_note = awhy
            reasons.append(f"Date approximative : {doc_date.isoformat()} ({awhy})")
        else:
            reasons.append("Aucune date trouvée : date du jour par défaut")
    if expiry and TYPES[type_id].get("expiry"):
        reasons.append(f"Date d'expiration lue : {expiry.isoformat()}")
    else:
        expiry = expiry if TYPES[type_id].get("expiry") else None

    # Confiance
    pts = 0
    pts += 3 if top >= 4 else 2 if top >= 2 else 1 if top >= 1 else 0
    pts += 1 if top - second >= 2 else 0
    pts += 1 if best_c[1] > 0 else 0
    pts += 1 if emitter and not emitter_approx else 0
    pts += 1 if doc_date and precision in ("jour", "mois") else 0
    if not text.strip():
        pts = min(pts, 3)
        reasons.append("Contenu non lu : analyse du nom de fichier seulement")
    level = "haute" if pts >= 6 else "moyenne" if pts >= 4 else "basse"
    if type_id == "autre":
        level = "basse"
    if forced and level == "basse":
        level = "moyenne"
    must = TYPES[type_id].get("must")
    if must and text.strip() and not any(m in hay for m in must):
        level = "moyenne" if level == "haute" else level
        reasons.append("Mot-clé décisif absent (ex. « " + must[0] + " ») : à vérifier")
    if type_id == "formulaire":
        level = "basse" if level == "basse" else "moyenne"
        reasons.append("Formulaire administratif : s'il est vierge, garde-le seulement si tu en as besoin")
    income_year = None
    if type_id in ("avis_impot", "declaration_revenus", "ird_assessment"):
        m = re.search(r"revenus?\s+(?:de\s+|des\s+|percus\s+en\s+)?(20\d\d)", hay + " " + fhay)
        income_year = m.group(1) if m else None
        if income_year:
            reasons.append(f"Porte sur les revenus {income_year}")
    detail, dsrc, dorg = _detail(type_id, hay, fhay)
    rd = rule_hits(both, "detail", type_id)
    if rd:
        detail, dsrc, dorg = rd[0][1], rd[0][0], rd[0][2]
    if detail:
        reasons.append(f"Intitulé déduit : {detail} (lu : « {dsrc[:40]} ») [{dorg}]")
    return {
        "income_year": income_year, "detail": detail, "date_precision": precision, "date_note": date_note,
        "emitter_approx": emitter_approx,
        "type": type_id, "country": country, "emitter": emitter or "Inconnu",
        "date": (doc_date or today).isoformat(), "date_found": precision == "jour",
        "expiry": expiry.isoformat() if expiry else None,
        "confidence": level, "reasons": reasons, "engine": "règles",
    }


# ---------- IA locale (moteur interchangeable : voir ia.py) ----------
def build_prompt(text, filename, countries):
    ids = [t for t in TYPES]
    return (
        "Tu es l'assistant de rangement d'une personne. Tu lis UN document administratif et tu réponds UNIQUEMENT en JSON "
        "avec les clés : "
        '"type" (une valeur parmi : ' + ", ".join(ids) + '), '
        '"country" (' + ", ".join(COUNTRIES) + " : pays de l'organisme qui a émis le document), "
        '"emitter" (organisme émetteur, court, ex. DGFiP, Immigration NZ, nom de l\'employeur), '
        '"date" (AAAA-MM-JJ : date d\'émission du document), '
        '"expiry" (AAAA-MM-JJ si le document a une date de fin de validité, sinon null), '
        '"holder" (nom de la personne concernée, sinon null), '
        '"detail" (intitulé exact et court du document, ex. "ASSR2", "Working Holiday Visa - demande", sinon null), '
        '"why" (une phrase en français expliquant ce qui t\'a permis de décider).\n'
        f"Pays de cette personne : {', '.join(countries)}.\n"
        f"Nom du fichier : {filename}\n"
        + (f"Texte extrait :\n{(text or '')[:3500]}" if (text or "").strip() else "Pas de texte extrait : lis l'image.")
    )


def refine_with_ai(result, text, filename, engine, model, countries, image=None, timeout=300):
    """Demande l'avis de l'IA locale, puis VÉRIFIE chaque réponse : l'IA propose, le code décide."""
    from . import ia
    ask = lambda img: ia.ask(engine, model, build_prompt(text, filename, countries), img, timeout)
    try:
        o = ask(image)
    except Exception as e:
        timed_out = type(e).__name__ in ("timeout", "TimeoutError") or "timed out" in str(e)
        if image and not timed_out and (text or "").strip():  # modèle sans vision : on réessaie avec le texte seul
            try:
                o = ask(None)
                image = None
            except Exception as e2:
                result["reasons"].append(f"IA locale indisponible ({type(e2).__name__})")
                return result
        else:
            result["reasons"].append("IA locale : trop lente sur cet ordinateur, abandonnée" if timed_out
                                     else f"IA locale indisponible ({type(e).__name__})")
            return result
    if not isinstance(o, dict):
        result["reasons"].append("IA locale : réponse illisible, ignorée")
        return result
    model_name = model
    def isdate(v, future_ok=False):
        try:
            d = dt.date.fromisoformat(str(v or ""))
        except ValueError:
            return False
        return dt.date(1950, 1, 1) <= d and (future_ok or d <= dt.date.today())
    if o.get("type") in TYPES and o["type"] != "autre":
        result["type"] = o["type"]
    if o.get("country") in COUNTRIES:
        result["country"] = o["country"]
    if o.get("emitter") and (result["emitter"] == "Inconnu" or result.get("emitter_approx")):
        result["emitter"] = slugify(str(o["emitter"]))[:30]
        result["emitter_approx"] = False
    if isdate(o.get("date")) and not result["date_found"]:
        # l'IA ne remplace une date approximative que si elle reste dans la même année
        if not result.get("date_precision") or o["date"][:4] == result["date"][:4]:
            result["date"] = o["date"]
    if isdate(o.get("expiry"), future_ok=True) and not result.get("expiry") and TYPES[result["type"]].get("expiry"):
        result["expiry"] = o["expiry"]
    if o.get("holder"):
        result["holder_seen"] = str(o["holder"])[:60]
    if o.get("detail") and not result.get("detail"):
        result["detail"] = str(o["detail"])[:60]
    how = "a regardé la page" if image else "a lu le texte"
    result["reasons"].append(f"IA locale ({model_name} · {engine.get('name', '')}) {how} : {str(o.get('why') or 'avis donné')[:200]}")
    result["engine"] = "règles + IA locale"
    if result["type"] != "autre" and result["confidence"] == "basse":
        result["confidence"] = "moyenne"
    return result
