import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import PlexPatrolApp
from utils.logger import setup_logging
from dotenv import load_dotenv

# Initialiser le logging
setup_logging()

# Recharger les variables d'environnement
load_dotenv(override=True)


def main():
    """Point d'entrée principal"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Charger la palette sombre
    from utils.helpers import apply_dark_theme

    apply_dark_theme(app)

    window = PlexPatrolApp()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
