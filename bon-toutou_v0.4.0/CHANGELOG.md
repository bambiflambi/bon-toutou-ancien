# Journal des versions

Les mises à jour ne sont jamais obligatoires. Une nouvelle version lit toujours les données des anciennes.

## 0.4.0 — Freemarket devient Bon toutou
- **Nouveau nom : Bon toutou**, avec une tête de chien provisoire comme icône. Au premier lancement, tout ce que Freemarket avait créé est repris en le **renommant seulement** (rien n'est supprimé) : données de l'appareil, fiches (`.freemarket` → `.bontoutou`), et le bureau `FREEMARKET_ADMIN` → `BON_TOUTOU_ADMIN` (un bureau nommé autrement garde son nom). Ce qui a été fait est noté dans `.bontoutou/migration-bon-toutou.json`.
- **Le bouton « Ouvrir » marche dans l'app** : le document s'ouvre avec l'app habituelle de ton ordinateur (Aperçu…). Même chose pour l'aperçu dans Trier et PREUVE.txt.
- Calendrier, export des règles, proposition : le fichier est enregistré dans ton dossier Téléchargements (l'app ne savait pas « télécharger »), puis ouvert ou montré.
- **Fiches de paie** : l'employeur est retrouvé même sans la mention « Employeur : » (nom en haut du document au-dessus du SIRET, forme juridique SAS / SARL / Ltd…). Ton nom et celui de tes proches ne sont jamais pris pour un employeur.
- **Un sous-dossier par entreprise** pour les fiches de paie, contrats de travail, soldes de tout compte et attestations employeur : `03-2_Bulletins-paie/Le-Petit-Bistrot/`. Chaque employeur a sa propre fiche de paie actuelle.
- **Retrouver les émetteurs** (Documents, ou Réglages › Lecture) : pour les documents déjà rangés sans émetteur, Bon toutou relit leur texte et les range dans le bon dossier. Une seule annulation pour tout.

## 0.3.0 — l'interface de la maquette
- Nouvelle page **Aujourd'hui** : jusqu'à 3 choses à faire (trier, compléter ou finaliser un dossier, renouveler un document), les 6 prochains mois d'échéances, les 4 raccourcis et ce qui reste sur ton ordinateur.
- Nouveau **Calendrier** sur 12 mois : expirations lues dans tes documents et grandes échéances de tes pays (déclaration de revenus, IR3). Export **.ics** avec un rappel 30 jours avant, créé sur ton ordinateur.
- **Contacts** (aperçu) : tes interlocuteurs tirés de tes documents et de tes dossiers, avec ce que tu leur as transmis.
- **Réglages compartimentés** : une page par sujet (Profil, Confidentialité, Apparence, Adresse admin, Calendrier, Contacts, Organismes, IA locale, Lecture, Mes règles, Sauvegarde, Continuité, Synchronisation, Historique, Mises à jour, Signaler un problème) et **Aller plus loin**, la suite de l'accueil pas à pas.
- **Organismes** : checklist avec les liens officiels (impots.gouv.fr, ameli, CAF, myIR…), ouverts dans ton navigateur ; l'app n'autorise que ces liens-là.
- Ce qui arrive bientôt (relève de l'adresse admin, abonnement agenda, sauvegarde, accès d'urgence…) est affiché honnêtement ; « Ça m'intéresse » reste sur ton ordinateur.
- Trois ambiances : Champagne, Graphite, Sauge. Aucune police ni ressource chargée depuis internet.
- Documents par pays avec toutes les catégories (vides comprises), Dossiers en cartes, Trier et Archives restylés.

## 0.2.0 — première version téléchargeable
- App de bureau (Mac Intel et puce Apple, Windows, Linux) : plus de Terminal, plus d'installation manuelle.
- Installation guidée : dossier, nom, pays, IA locale (au choix), et ce qui peut sortir sur internet (rien sans ton accord).
- Fiches synchronisables, index local, catalogue en packs, une seule porte de sortie vers internet.
- Règles personnelles, nouveaux types, partage de packs, confidentialité par catégorie, premier tri guidé.
- IA locale interchangeable (moteur intégré llama.cpp, Ollama, LM Studio, Jan) avec une liste de modèles vérifiés par empreinte.
- Vérification des mises à jour et rapport de bug, toujours à ta demande.
