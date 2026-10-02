"""Modèles de dossiers : désormais chargés depuis le pack « demarches » (bontoutou/packs/demarches.json).

Chaque pièce :
  label  : ce qu'on te demande
  types  : types de documents acceptés (dans l'ordre de préférence)
  count  : combien (ex. 3 dernières fiches de paie)
  fresh  : ancienneté maximale en jours
  valid  : le document ne doit pas être expiré
"""
from .catalog import TEMPLATES  # noqa: F401
