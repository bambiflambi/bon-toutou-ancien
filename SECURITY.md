# Sécurité

Bon toutou est conçu pour **ne rien savoir de ses utilisateurs** : il n'y a ni serveur, ni compte, ni statistiques.

## Ce que le code garantit
- **Une seule porte de sortie vers internet** (`engine/bontoutou/sortie.py`). Un test (`tests/test_sortie.py`) refuse toute version où un autre fichier pourrait ouvrir une connexion.
- **Rien ne sort sans ton accord**, et chaque sortie est notée *avant* de partir dans le journal des sorties (Réglages).
- **Le moteur n'écoute que ton ordinateur** (127.0.0.1) et refuse toute requête venant d'ailleurs.
- **Les modèles d'IA et les fichiers téléchargés sont vérifiés par leur empreinte SHA-256.** Un fichier modifié est refusé.
- **Les packs de règles ne contiennent que des données**, jamais de code : ils ne peuvent rien exécuter, envoyer ni effacer.
- **Bon toutou ne supprime jamais un de tes documents** : il déplace, copie, archive, et tout se défait.

## Signaler une faille
Ouvre un ticket « Sécurité » sans détails exploitables, ou utilise la fonction de signalement privé de GitHub (onglet *Security* du dépôt). Une faille corrigée apparaît en rouge (« Important ») quand tu vérifies les mises à jour. Rien n'est jamais forcé.
