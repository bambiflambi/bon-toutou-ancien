# Contribuer

Bon toutou est sous licence **AGPL-3.0** : tu peux lire, utiliser et modifier le code. Si tu redistribues une version modifiée, ou si tu la proposes à d'autres via un réseau, tu dois publier ton code sous la même licence.

## Proposer des règles ou des types de documents (sans coder)
Dans l'app : Réglages › Mes règles › **Proposer pour une future version**. Tu relis exactement ce qui part (des règles, jamais un document) ; Bon toutou signale ce qui pourrait être personnel.
Les propositions retenues entrent dans les packs officiels (`engine/bontoutou/packs/`), livrés avec une mise à jour du catalogue.

## Ajouter un pays
Un pays = un pack JSON (`engine/bontoutou/packs/pays-xx.json`) : organismes, types, indices, noms de dossiers. Pas de code à écrire.

## Code
- Moteur : Python 3.9+, **aucune dépendance obligatoire**. Interface : HTML/CSS/JS sans outil de construction.
- Avant toute proposition : `cd engine && for t in flow sortie regles ia app; do python3 -m tests.test_$t; done`
- Règles non négociables : voir `CLAUDE.md`.
