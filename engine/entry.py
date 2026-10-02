"""Point d'entrée du moteur empaqueté (PyInstaller) : lancé par l'app de bureau avec --port 0 --app."""
from bontoutou.server import main

if __name__ == "__main__":
    main()
