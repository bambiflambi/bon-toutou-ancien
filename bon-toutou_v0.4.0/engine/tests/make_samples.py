"""Fabrique des faux documents PDF (texte réel, lisible) pour tester Bon toutou.

    python3 tests/make_samples.py  /chemin/de/sortie
Aucune dépendance : le PDF est écrit à la main.
"""
import os
import sys


def pdf(path, lines):
    def esc(s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = "BT /F1 11 Tf 50 790 Td 15 TL\n" + "\n".join(f"({esc(l)}) '" for l in lines) + "\nET"
    cb = content.encode("latin-1", "replace")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(cb) + cb + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    out = b"%PDF-1.4\n"
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    x = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offs)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, x)
    with open(path, "wb") as f:
        f.write(out)


SAMPLES = {
    "Carte_identite_location_FINAL_v2.pdf": ["REPUBLIQUE FRANCAISE", "CARTE NATIONALE D'IDENTITE", "Nom : MARTIN",
                                             "Delivree le : 02/06/2021 par la Prefecture", "Date d'expiration : 01/06/2031"],
    "avis_impot_2025_FINAL(2).pdf": ["Direction generale des Finances publiques - DGFiP", "AVIS D'IMPOT 2025",
                                     "Impot sur le revenu des revenus de 2024", "Revenu fiscal de reference : 21 480 EUR",
                                     "Etabli le 28/07/2025", "impots.gouv.fr"],
    "scan_paie_juillet.pdf": ["BULLETIN DE PAIE", "Employeur : Nuances Gourmandes SARL", "SIRET 812 345 678 00012",
                              "Periode du 01/07/2026 au 31/07/2026", "Salaire brut 2 150,00", "Net a payer 1 684,20 EUR"],
    "paie_aout.pdf": ["BULLETIN DE PAIE", "Employeur : Nuances Gourmandes SARL", "Periode du 01/08/2026 au 31/08/2026",
                         "Salaire brut 2 150,00", "Net a payer 1 684,20 EUR"],
    "paie_septembre.pdf": ["BULLETIN DE PAIE", "Employeur : Nuances Gourmandes SARL", "Periode du 01/09/2026 au 30/09/2026",
                      "Salaire brut 2 150,00", "Net a payer 1 690,02 EUR"],
    "Facture_EDF_sept.pdf": ["EDF - Electricite de France", "Votre facture d'electricite", "Date de la facture : 12/09/2026",
                             "Consommation : 212 kWh", "Montant TTC : 64,90 EUR"],
    "RIB LCL.pdf": ["LCL - Le Credit Lyonnais", "RELEVE D'IDENTITE BANCAIRE", "IBAN FR76 3000 2012 3400 0012 3456 789",
                    "BIC CRLYFRPP", "Edite le 10/01/2026"],
    "contrat.pdf": ["CONTRAT DE TRAVAIL A DUREE INDETERMINEE", "Entre Nuances Gourmandes SARL, employeur,",
                    "et M. Martin", "Periode d'essai : 2 mois", "Fait a Lyon le 15/12/2025"],
    "IMG_4821_wof.pdf": ["WARRANT OF FITNESS", "New Zealand Transport Agency - Waka Kotahi", "Vehicle: Toyota Hiace",
                         "Inspection date: 12/04/2026", "Expiry date: 12/10/2026"],
    "solde.pdf": ["RECU POUR SOLDE DE TOUT COMPTE", "Employeur : Nuances Gourmandes SARL", "Fin de contrat le 30/09/2026",
                  "Somme versee : 2 480,00 EUR", "Fait le 30/09/2026"],
    "attestation_maif_2026.pdf": ["MAIF", "ATTESTATION D'ASSURANCE HABITATION", "Multirisque habitation",
                                  "Etablie le 15/01/2026", "Valable jusqu'au 15/01/2027"],
    "truc_bizarre.pdf": ["Merci pour votre visite", "A bientot"],
}

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "samples"
    os.makedirs(out, exist_ok=True)
    for name, lines in SAMPLES.items():
        pdf(os.path.join(out, name), lines)
    print(f"{len(SAMPLES)} documents d'exemple dans {out}")
