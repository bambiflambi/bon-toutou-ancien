# Décisions structurelles — Bon toutou V0.1 (validées le 30 sept. 2026)

1. **La vérité = le dossier Finder.** L'index SQLite (`BON_TOUTOU_ADMIN/.bontoutou/index.db`) est reconstructible à partir des fichiers.
2. **Document suivi** (dans le modèle : *document maître*) = un papier qui sert toujours et vit dans le temps, avec une version actuelle et un historique.
   - Exemples : ta carte d'identité, ton RIB, ton dernier avis d'impôt, **la fiche de paie de ton travail actuel**, la facture EDF du logement actuel.
   - Chaque nouvelle fiche de paie devient la version actuelle ; les précédentes passent dans l'historique.
   - Quand la situation se termine (ex. **solde de tout compte**), le solde va directement dans `99_ARCHIVES/…/03-2_Bulletins-paie` et tout le suivi passe en « Terminé ».
   - Clé d'un suivi : `titulaire | pays | type` (carte d'identité, avis d'impôt…) ou `titulaire | pays | type | émetteur` (fiche de paie chez tel employeur, facture EDF…). Les types « sans suivi » (diplôme, amende, lettre) sont des documents indépendants.
   - Dans l'interface, on dit « document suivi ». « Document maître » reste dans les explications avancées.
3. **Anciennes versions et documents terminés** : `<PAYS>/99_ARCHIVES/<catégorie>/<sous-dossier>/`, jamais supprimés. Nom de fichier : `AAAA-MM-JJ_PAYS_CAT_Emetteur_Objet.ext`.
4. **Titulaire** : chaque document a un titulaire (V0.1 : « moi » ; enfants et animaux plus tard).
5. **Modèle de dossier** : liste de pièces, avec type(s) accepté(s), quantité (« 3 dernières ») et fraîcheur (« moins de 3 mois ») ou validité (non expiré).
6. **Preuve d'envoi** : copie figée des pièces + `manifest.json` + `PREUVE.txt` avec l'empreinte SHA-256 de chaque fichier. En cours : `<PAYS>/20_DEMARCHES/` ; une fois marqué envoyé : `<PAYS>/99_ARCHIVES/20_DEMARCHES/`.
   - « Envoyer » n'existe pas encore : **Finaliser** puis **Marquer comme envoyé**.
7. **Classement** : règles (mots-clés, émetteurs, dates) puis IA locale (Ollama, 127.0.0.1) si la confiance n'est pas élevée. L'utilisateur valide toujours avant qu'un fichier bouge.
   - Confiance affichée en mots : élevée, moyenne, à vérifier. Jamais de pourcentage. Toujours un « Pourquoi ? ».
8. **Journal et annulation** : chaque action est notée (déplacements et changements d'index), et « Annuler » la rejoue à l'envers. La vraie sécurité : **Bon toutou ne détruit rien**.
9. **Confidentialité** : les niveaux par catégorie (🔒 Local uniquement · ◐ Sur autorisation · ☁ Externe autorisé) sont appliqués par le code, pas par l'IA.
   - Un **journal des sorties** note tout document qui quitterait l'ordinateur.
   - V0.1 : aucune sortie possible ; le serveur n'écoute que 127.0.0.1 et refuse les autres hôtes.
10. **Échéances** : la date d'expiration est lue, puis confirmée par l'utilisateur. Export .ics plus tard.
11. **Sécurité disque** : FileVault. Pas de chiffrement maison en V0.1.
12. **Pays et langues** : numéros de catégorie universels, libellés de dossiers dans la langue du pays (le kit existant est utilisé tel quel).

Positionnement : **« Le dossier administratif vivant »**. Il sait quels documents tu as, lesquels sont valables, à quoi ils servent, lesquels ont été envoyés, et quelle version exacte.
