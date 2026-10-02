# Bon toutou — ton dossier administratif vivant

Bon toutou range tes papiers administratifs dans **un seul dossier sur ton ordinateur**, lisible même sans l'app.
Il sait quels documents tu as, lesquels sont valables, à quoi ils servent, et exactement ce que tu as envoyé.

**Avant** : `Carte_identite.pdf`, `Carte_identite_2.pdf`, `Carte_identite_location_FINAL_v2.pdf`…
**Avec Bon toutou** : `2021-06-02_FR_01_Prefecture_Carte-identite.pdf`. Une seule, toujours la bonne, réutilisée dans chaque dossier.

## Ce qui le rend différent
- **Zéro serveur, zéro compte, zéro statistique.** Tout se passe sur ton ordinateur. Personne, pas même l'auteur, ne sait ce que tu y ranges.
- **Rien ne sort sans ton accord.** Une seule porte vers internet, chaque sortie notée avant de partir.
- **Bon toutou ne détruit rien.** Il déplace, copie, archive ; tout se défait.
- **Une IA locale, si tu veux.** Elle tourne sur ta machine (modèles à poids ouverts, licence Apache 2.0, vérifiés par empreinte). Les règles suffisent pour commencer.
- **Synchronisation au choix.** Ton dossier contient tes documents et une petite fiche par document : iCloud, Syncthing, Nextcloud, disque externe… ou rien.
- **Mises à jour jamais obligatoires.** Une nouvelle version lit toujours les données des anciennes.

## Télécharger
Onglet **Releases** de ce dépôt : Mac (Intel et puce Apple), Windows, Linux.
Sur Mac, tant que l'app n'est pas signée par Apple : clic droit sur l'app › **Ouvrir**, une seule fois.

## Comment c'est fait
| Dossier | Contenu |
|---|---|
| `engine/` | Le moteur (Python, sans dépendance obligatoire) et l'interface (HTML/JS). Lançable seul : `cd engine && python3 -m bontoutou.server` |
| `engine/bontoutou/packs/` | Le catalogue : pays, types de documents, organismes, règles, démarches, modèles d'IA. **Des données, jamais du code.** |
| `desktop/` | L'app de bureau (Tauri) qui lance le moteur et l'affiche. |
| `tools/` | Outils de fabrication (empreintes des modèles, icône). |
| `.github/workflows/` | La fabrication automatique pour chaque système, à chaque nouvelle version. |
| `docs/` | Décisions de conception. |

Sécurité : voir [SECURITY.md](SECURITY.md). Contribuer : voir [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence
[AGPL-3.0](LICENSE). Libre de lire, d'utiliser et de modifier ; toute version redistribuée ou proposée en ligne doit rester ouverte.

---

### English
Bon toutou keeps your personal admin papers in one local folder, readable without the app. No server, no account, no telemetry; nothing leaves your computer without your consent, and every exit is logged first. Optional local AI (open-weight models, checksum-verified). Updates are never mandatory. Licensed under AGPL-3.0.
