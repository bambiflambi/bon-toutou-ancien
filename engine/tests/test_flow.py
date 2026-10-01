"""Test de bout en bout du flux V0.1 sur un bureau temporaire.
    python3 -m tests.test_flow        (depuis le dossier App_v0)
"""
import os, shutil, sys, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
tmp = tempfile.mkdtemp(prefix="fm_test_")
os.environ["FREEMARKET_DATA"] = os.path.join(tmp, "appareil-A")   # données locales de l'appareil A
from freemarket.core import Bureau
from freemarket import catalog, classify
from tests.make_samples import SAMPLES, pdf

root = os.path.join(tmp, "FREEMARKET_ADMIN"); os.makedirs(root)
b = Bureau(root)
print("Outils de lecture :", b.state()["tools"])
order = ["Carte_identite_location_FINAL_v2.pdf","avis_impot_2025_FINAL(2).pdf","scan_paie_juillet.pdf","paie_aout.pdf",
         "Facture_EDF_sept.pdf","RIB LCL.pdf","contrat.pdf","IMG_4821_wof.pdf","attestation_maif_2026.pdf","truc_bizarre.pdf"]
src = os.path.join(tmp, "src"); os.makedirs(src)
for n in SAMPLES: pdf(os.path.join(src, n), SAMPLES[n])
for n in order:
    b.add_upload(n, open(os.path.join(src, n), "rb").read())
fails = 0
def check(cond, msg):
    global fails
    print(("  ✓ " if cond else "  ✗ ") + msg); fails += 0 if cond else 1
inbox = b.inbox()
for p in inbox:
    print(f"- {p['orig']:40s} → {p['type']:22s} {p['country']} {p['emitter']:20s} {p['date']} [{p['confidence']}] {p['name']}")
T = {p['orig']: p for p in inbox}
check(T["Carte_identite_location_FINAL_v2.pdf"]["type"] == "carte_identite", "carte d'identité reconnue")
check(T["Carte_identite_location_FINAL_v2.pdf"]["expiry"] == "2031-06-01", "expiration CNI lue")
check(T["avis_impot_2025_FINAL(2).pdf"]["type"] == "avis_impot" and T["avis_impot_2025_FINAL(2).pdf"]["date"] == "2025-07-28", "avis d'impôt + date")
check(T["scan_paie_juillet.pdf"]["type"] == "bulletin_paie" and T["scan_paie_juillet.pdf"]["date"] == "2026-07-31", "fiche de paie juillet, date fin de période")
check(T["IMG_4821_wof.pdf"]["country"] == "NZ" and T["IMG_4821_wof.pdf"]["type"] == "controle_vehicule", "WOF → NZ")
check(T["RIB LCL.pdf"]["type"] == "rib" and T["RIB LCL.pdf"]["emitter"] == "LCL", "RIB LCL")
check(T["truc_bizarre.pdf"]["confidence"] == "basse", "document inconnu → à vérifier")
# valider tout sauf le document inconnu
ids = [p["id"] for p in inbox if p["orig"] != "truc_bizarre.pdf"]
r = b.validate(ids); check(r["ok"] and r["done"] == 9, "9 documents rangés")
cni = [d for d in b.documents() if d["type"] == "carte_identite"][0]
check(os.path.exists(b.abs(cni["path"])) and "FR_FRANCE/01_IDENTITE/01-1_" in cni["path"], "CNI rangée dans FR_FRANCE/01_IDENTITE/01-1_…")
# 3e fiche de paie : nouvelle version du même document suivi
b.add_upload("paie_septembre.pdf", open(os.path.join(src, "paie_septembre.pdf"), "rb").read())
p = b.inbox()[-1]; check(p["mode"] == "new_version", "fiche de septembre = nouvelle version du document suivi")
r = b.validate([p["id"]]); batch = r["batch"]
paies = [d for d in b.documents() if d["type"] == "bulletin_paie"]
check(len(paies) == 1 and paies[0]["date"] if False else len(paies) == 1, "une seule fiche de paie actuelle")
check(paies[0]["versions"] == 3, "3 versions dans l'historique")
old = b.archives()["old"]; check(any("99_ARCHIVES/03_TRAVAIL-REVENUS/03-2_" in o["path"] for o in old), "anciennes fiches dans 99_ARCHIVES/03…/03-2")
# annuler puis refaire
u = b.undo(batch); check(u["ok"] and len(b.inbox()) == 2, "annulation : la fiche revient dans Trier")
check([d for d in b.documents() if d["type"] == "bulletin_paie"][0]["doc_date"] == "2026-08-31", "annulation : août redevient la version actuelle")
b.validate([x["id"] for x in b.inbox() if x["orig"] == "paie_septembre.pdf"])
# ignorer le document inconnu : gardé, pas détruit
z = [x for x in b.inbox() if x["orig"] == "truc_bizarre.pdf"][0]; b.ignore(z["id"])
check(os.path.exists(os.path.join(root, "00_A-TRIER", "_IGNORES", "truc_bizarre.pdf")), "ignoré = gardé dans 00_A-TRIER/_IGNORES")
# dossier location
did = b.create_dossier("louer_logement", "Agence Horizon", "FR")
k = b.dossier(did)
for pc in k["pieces"]: print(f"   {pc['status']:8s} {pc['label']:45s} {[d['label']+' '+d['date'] for d in pc['docs']]} {pc['problems']}")
check(k["ok"] == 7, f"location : {k['ok']}/7 pièces")
r = b.finalize(did); check(r["ok"], "dossier finalisé")
k = b.dossier(did); folder = b.abs(k["folder"])
check(os.path.exists(os.path.join(folder, "PREUVE.txt")) and os.path.exists(b.abs(k["zip"])), "paquet + PREUVE.txt + zip générés")
check(len([f for f in os.listdir(folder) if f[:2].isdigit()]) == 9, "9 fichiers copiés (7 pièces dont 3 fiches de paie)")
b.mark_sent(did)
a = b.archives(); check(len(a["sent"]) == 1 and "99_ARCHIVES/20_DEMARCHES" in a["sent"][0]["folder"], "envoyé → 99_ARCHIVES/20_DEMARCHES")
# solde de tout compte : termine le suivi des fiches de paie
b.add_upload("solde.pdf", open(os.path.join(src, "solde.pdf"), "rb").read())
p = b.inbox()[-1]; check(p["mode"] == "archive_direct" and "termine le suivi" in p["relation"], "solde de tout compte → archive + fin du suivi")
b.validate([p["id"]])
check(not [d for d in b.documents() if d["type"] == "bulletin_paie"], "plus de fiche de paie actuelle")
done = b.archives()["done"]; check(len([d for d in done if d["type"] in ("bulletin_paie", "solde_tout_compte")]) == 4, "Terminés : 3 fiches + solde, rangés dans 03-2")
# preuve : remplacée depuis ?
check(a["sent"][0]["count"] == 9, "preuve : 9 fichiers transmis")
# reconstruction de l'index depuis les fichiers
n_before = len(b.documents()); r = b.rebuild_index(); check(r["ok"] and len(b.documents()) == n_before, f"index reconstruit ({r['docs']} fichiers)")

# ---------------- Étape A : fiches synchronisées, index local, catalogue en packs, journal par appareil
def docs_snapshot(bb):
    return sorted((d["id"], d["type"], d["status"], d["path"], d["person"], d["detail"] or "", d["suivi"] or "")
                  for d in map(dict, bb.db.execute("SELECT * FROM docs")))
n_docs = b.db.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
metas = os.listdir(os.path.join(root, ".freemarket", "meta", "docs"))
check(len(metas) == n_docs, f"une fiche par document ({len(metas)})")
check(len(os.listdir(os.path.join(root, ".freemarket", "meta", "dossiers"))) == 1, "une fiche pour le dossier")
check(not os.path.exists(os.path.join(root, ".freemarket", "index.db")), "l'index n'est plus dans le dossier synchronisé")
jl = os.listdir(os.path.join(root, ".freemarket", "journal"))
check(len(jl) == 1 and sum(1 for _ in open(os.path.join(root, ".freemarket", "journal", jl[0]))) >= 8, "journal de l'appareil écrit dans le dossier")
# une précision ajoutée sur l'appareil A doit survivre à un index perdu
rib = [d for d in b.documents() if d["type"] == "rib"][0]
b.reclassify(rib["id"], {"detail": "RIB compte courant", "person": "Camille Martin"})
snap_a = docs_snapshot(b)
# appareil B : aucun index, il reconstruit tout depuis les fiches
os.environ["FREEMARKET_DATA"] = os.path.join(tmp, "appareil-B")
b2 = Bureau(root)
check(docs_snapshot(b2) == snap_a, "appareil B : index reconstruit depuis les fiches, identique (titulaire, intitulé, suivi)")
check(len(b2.dossiers()) + len(b2.archives()["sent"]) == 1, "appareil B : le dossier envoyé est retrouvé")
check(len(os.listdir(os.path.join(root, ".freemarket", "journal"))) == 1, "appareil B n'a encore rien écrit dans le journal")
# B corrige un document, A le voit au prochain démarrage
cni2 = [d for d in b2.documents() if d["type"] == "carte_identite"][0]
import time; time.sleep(1.1)
b2.reclassify(cni2["id"], {"detail": "CNI recto-verso"})
check(len(os.listdir(os.path.join(root, ".freemarket", "journal"))) == 2, "chaque appareil a son propre journal")
os.environ["FREEMARKET_DATA"] = os.path.join(tmp, "appareil-A")
b3 = Bureau(root)
check(b3.document(cni2["id"])["detail"] == "CNI recto-verso", "appareil A récupère la correction faite sur B")
# fichier déplacé à la main dans le Finder : retrouvé par son empreinte
d0 = b3.document(cni2["id"]); src0 = b3.abs(d0["path"]); moved = os.path.join(os.path.dirname(src0), "deplace-a-la-main.pdf")
os.rename(src0, moved)
r = b3.rebuild_index()
check(r["ok"] and b3.document(cni2["id"])["path"].endswith("deplace-a-la-main.pdf"), "fichier déplacé à la main retrouvé (empreinte)")
check(docs_snapshot(b3) != [] and r["from_names"] == 0, "reconstruction sans doublon")
os.rename(moved, src0); b3.rebuild_index()
# migration d'un ancien bureau (index et réglages dans .freemarket, pas de fiches)
old_root = os.path.join(tmp, "ANCIEN", "FREEMARKET_ADMIN"); shutil.copytree(root, old_root)
shutil.rmtree(os.path.join(old_root, ".freemarket", "meta"))
shutil.copy2(os.path.join(b3.local, "index.db"), os.path.join(old_root, ".freemarket", "index.db"))
json.dump({"owner": "Camille", "countries": ["FR", "NZ"], "use_ollama": True, "ollama_model": "x", "ai_mode": "texte"},
          open(os.path.join(old_root, ".freemarket", "settings.json"), "w"))
os.environ["FREEMARKET_DATA"] = os.path.join(tmp, "appareil-C")
b4 = Bureau(old_root)
fmo = os.path.join(old_root, ".freemarket")
check(b4.migrated and not os.path.exists(os.path.join(fmo, "index.db")) and any(f.startswith("index.db.migre-") for f in os.listdir(fmo)),
      "migration : index déplacé hors du dossier, l'ancien gardé (renommé)")
check(len(os.listdir(os.path.join(fmo, "meta", "docs"))) == n_docs, "migration : fiches créées pour tous les documents")
check(b4.settings["owner"] == "Camille" and b4.settings["use_ollama"] and os.path.exists(os.path.join(fmo, "profil.json")),
      "migration : réglages répartis (profil synchronisé / appareil local)")
# catalogue : règles perso (types, intitulés, émetteurs), priorité et origine affichée
json.dump({"format": 1, "types": {
             "permis_bateau": {"label": "Permis bateau", "slug": "Permis-bateau", "cat": "01", "sub": "01-3", "suivi": "type",
                               "kw": ["permis plaisance", "permis bateau"], "details": [["option (cotiere|hauturiere)", "Permis bateau {1}"]]},
             "assr": {"details": [["\\bgroupe ([a-z])\\b", "ASSR groupe {1}"], ["(a+)+b", "piege"]]}},
           "emitters": [["kiwi harvest", "Kiwi-Harvest-Ltd", "NZ"]]},
          open(os.path.join(fmo, "mes-regles.json"), "w"), ensure_ascii=False)
catalog.load(fmo)
r = classify.analyze("PERMIS PLAISANCE option côtière delivre le 12/05/2019 par Kiwi Harvest", "x.jpg", ["FR", "NZ"])
check(r["type"] == "permis_bateau" and r["detail"] == "Permis bateau Cotiere", "règle perso : nouveau type + intitulé")
check(r["emitter"] == "Kiwi-Harvest-Ltd" and any("Règle perso" in x for x in r["reasons"]), "règle perso : émetteur, origine visible dans « Pourquoi ? »")
check(any("refusée" in w for w in catalog.WARNINGS), "règle perso trop complexe refusée")
check(any(p["kind"] == "perso" for p in catalog.PACKS) and len([p for p in catalog.PACKS if p["kind"] == "officiel"]) == 5, "5 packs officiels + perso chargés")
catalog.load(os.path.join(root, ".freemarket"))

print("\nRÉSULTAT :", "OK" if not fails else f"{fails} échec(s)", "· bureau de test :", root)
sys.exit(1 if fails else 0)
