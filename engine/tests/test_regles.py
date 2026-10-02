"""Règles et types créés par l'utilisateur, partage, masquage.
    python3 -m tests.test_regles        (depuis le dossier App_v0)
"""
import os, sys, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
tmp = tempfile.mkdtemp(prefix="fm_regles_")
os.environ["BONTOUTOU_DATA"] = os.path.join(tmp, "appareil")
from bontoutou.core import Bureau
from bontoutou.sortie import mask
from tests.make_samples import SAMPLES, pdf

fails = 0
def check(cond, msg):
    global fails
    print(("  ✓ " if cond else "  ✗ ") + msg); fails += 0 if cond else 1

root = os.path.join(tmp, "BON_TOUTOU_ADMIN"); os.makedirs(root)
src = os.path.join(tmp, "src"); os.makedirs(src)
for n in SAMPLES: pdf(os.path.join(src, n), SAMPLES[n])
b = Bureau(root); b.save_settings({"owner": "Camille Martin"})
for n in ["scan_paie_juillet.pdf", "paie_aout.pdf", "RIB LCL.pdf", "contrat.pdf", "truc_bizarre.pdf"]:
    b.add_upload(n, open(os.path.join(src, n), "rb").read())
b.validate([p["id"] for p in b.inbox() if p["orig"] != "truc_bizarre.pdf"])
R = b.regles

# 1. Règle d'émetteur née d'une correction : aperçu, création, application en un lot annulable
rule = {"indice": "Nuances Gourmandes", "champ": "emitter", "valeur": "Nuances Gourmandes Lyon"}
pv = R.preview(rule)
check(pv["ok"] and len(pv["docs"]) == 3, f"aperçu : la règle changerait 3 documents rangés ({len(pv['docs'])})")
check(pv["phrase"].startswith("Quand un document contient « Nuances Gourmandes » → Émetteur"), "la règle s'écrit en clair")
r = R.save(rule); rid = r["rule"]["id"]
check(r["ok"] and os.path.exists(os.path.join(root, ".bontoutou", "mes-regles.json")), "règle enregistrée dans mes-regles.json")
ap = R.apply(rid, [d["id"] for d in pv["docs"]])
paie = [d for d in b.documents() if d["type"] == "bulletin_paie"][0]
check(ap["ok"] and ap["n"] == 3 and paie["emitter"] == "Nuances-Gourmandes-Lyon" and "Nuances-Gourmandes-Lyon" in paie["path"], "appliquée : fichiers renommés")
check(paie["versions"] == 2, "le suivi des fiches de paie reste entier (2 versions)")
b.undo(ap["batch"])
check([d for d in b.documents() if d["type"] == "bulletin_paie"][0]["emitter"] == "Nuances-Gourmandes", "une seule annulation défait tout le lot")
# 2. La règle sert aux nouveaux documents
b.add_upload("paie_septembre.pdf", open(os.path.join(src, "paie_septembre.pdf"), "rb").read())
p = [x for x in b.inbox() if x["orig"] == "paie_septembre.pdf"][0]
check(p["emitter"] == "Nuances-Gourmandes-Lyon" and any("Règle perso" in x for x in p["reasons"]), "nouveau document : la règle s'applique, « Pourquoi ? » le dit")
# 3. Règle de type + intitulé limité à un type
r2 = R.save({"indice": "Merci pour votre visite", "champ": "type", "valeur": "facture"})
t = [x for x in b.inbox() if x["orig"] == "truc_bizarre.pdf"][0]
check(t["type"] == "facture" and t["confidence"] != "basse", "règle de type : le document inconnu devient une facture")
R.save({"indice": "periode d'essai", "champ": "detail", "valeur": "CDI avec essai", "type": "contrat_travail"})
check(R.preview({"indice": "periode d'essai", "champ": "detail", "valeur": "CDI avec essai", "type": "contrat_travail"})["docs"][0]["change"].startswith("Intitulé"), "intitulé limité au type Contrat")
# 4. Essayer, désactiver, supprimer (gardée dans « supprimees »)
rib = [d for d in b.documents() if d["type"] == "rib"][0]
check(not R.test(rid, rib["id"])["match"], "essayer sur un document : ne s'applique pas au RIB")
R.toggle(r2["rule"]["id"], False)
check([x for x in b.inbox() if x["orig"] == "truc_bizarre.pdf"][0]["type"] != "facture", "règle désactivée : plus d'effet")
R.delete(r2["rule"]["id"])
d = R.data(); check(len(d["rules"]) == 2 and len(d["supprimees"]) == 1, "règle supprimée, mais gardée dans l'historique du fichier")
# 5. Nouveau type
nt = R.save_type({"label": "Permis bateau", "cat": "01", "sub": "01-3", "suivi": "type", "expiry": False, "kw": ["permis plaisance", "option côtière"]})
pdf(os.path.join(src, "bateau.pdf"), ["PERMIS PLAISANCE", "Option cotiere", "Delivre le 12/05/2019"])
b.add_upload("bateau.pdf", open(os.path.join(src, "bateau.pdf"), "rb").read())
p = [x for x in b.inbox() if x["orig"] == "bateau.pdf"][0]
check(nt["ok"] and p["type"] == nt["id"] and "01_IDENTITE" in p["dest"], "nouveau type : reconnu et rangé dans 01 › Permis")
# 6. Partage : export -> import ailleurs avec aperçu ; proposition avec repérage du personnel
R.save({"indice": "Martin", "champ": "detail", "valeur": "Contrat de Camille", "type": "contrat_travail"})
pr = R.propose()
check(any("ton nom" in f for f in pr["flags"]), "proposition : ton nom est signalé avant le partage")
check(pr["mailto"] is None and json.loads(pr["text"])["rules"], "pas d'adresse de contribution : texte prêt à copier")
pack = R.export()
os.environ["BONTOUTOU_DATA"] = os.path.join(tmp, "autre-appareil")
root2 = os.path.join(tmp, "AUTRE", "BON_TOUTOU_ADMIN"); os.makedirs(root2)
b2 = Bureau(root2)
b2.add_upload("paie_aout.pdf", open(os.path.join(src, "paie_aout.pdf"), "rb").read())
b2.validate([x["id"] for x in b2.inbox()])
pv2 = b2.regles.import_pack(json.dumps(pack))
check(pv2["ok"] and pv2["rules"] == 3 and pv2["types"] == 1 and pv2["docs"] == 1 and not pv2["signed"], "import : aperçu (3 règles, 1 type, 1 document concerné, non signé)")
b2.regles.import_pack(json.dumps(pack), confirm=True)
check(any(p["kind"] == "importe" for p in b2.state()["packs"]), "pack importé chargé, marqué « non vérifié »")
rm = b2.regles.remove_pack(b2.regles.state()["imported"][0]["file"])
check(rm["ok"] and os.path.isdir(os.path.join(root2, ".bontoutou", "packs", "_retires")), "pack retiré : gardé dans packs/_retires")
check(b2.regles.import_pack('{"rules":[{"indice":"x","champ":"emitter","valeur":"y"}]}')["rules"] == 0, "règle trop courte refusée à l'import")
# 7. Masquage avant toute sortie
m, f = mask("IBAN FR76 3000 2012 3400 0012 3456 789 · tél 06 12 34 56 78 · pm@exemple.fr · net 1 684,20")
check("FR76" not in m and "06 12" not in m and "@" not in m and "1 684,20" in m, "masquage : IBAN, téléphone, e-mail masqués ; montants gardés")

print("\nRÉSULTAT :", "OK" if not fails else f"{fails} échec(s)")
sys.exit(1 if fails else 0)
