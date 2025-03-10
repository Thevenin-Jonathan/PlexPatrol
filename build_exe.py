import PyInstaller.__main__
import os

# Chemin vers l'icône de l'application
icon_path = os.path.join("assets", "plexpatrol.ico")

# Paramètres PyInstaller
PyInstaller.__main__.run(
    [
        "main.py",  # Script principal
        "--name=PlexPatrol",  # Nom de l'exécutable
        "--onefile",  # Créer un seul fichier exécutable
        "--windowed",  # Application GUI sans console
        f"--icon={icon_path}",  # Icône de l'application
        "--add-data=config;config",  # Incluez le dossier config
        "--add-data=assets;assets",  # Incluez le dossier resources
        "--add-data=utils;utils",  # Ajout du dossier utils
        "--add-data=data;data",  # Ajout du dossier data si nécessaire
        "--add-data=ui;ui",  # Ajout du dossier ui
        "--add-data=core;core",  # Ajout du dossier core
        "--add-data=data/GeoLite2-City.mmdb;data",  # Ajout de la base de données GeoLite2
        # Imports cachés essentiels
        "--hidden-import=pkgutil",
        "--hidden-import=utils.constants",
        "--hidden-import=config.config_manager",
        # Imports Qt
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtWidgets.QSystemTrayIcon",
        "--hidden-import=PyQt5.QtWidgets.QMenu",
        "--hidden-import=PyQt5.QtWebEngineWidgets",
        "--hidden-import=PyQt5.QtWebEngine",
        "--hidden-import=PyQt5.QtChart",
        # Imports pour les statistiques améliorées
        "--hidden-import=geoip2",
        "--hidden-import=geoip2.database",
        "--hidden-import=sqlite3",
        "--hidden-import=json",  # Pour le traitement JSON
        "--hidden-import=datetime",  # Pour le traitement des dates
        "--hidden-import=tempfile",  # Pour les fichiers temporaires en géolocalisation
        # Support graphique avancé
        "--hidden-import=PyQt5.QtChart.QChart",
        "--hidden-import=PyQt5.QtChart.QPieSeries",
        "--hidden-import=PyQt5.QtChart.QPieSlice",
        "--hidden-import=PyQt5.QtChart.QChartView",
        "--hidden-import=PyQt5.QtChart.QBarSeries",
        "--hidden-import=PyQt5.QtChart.QBarSet",
        "--additional-hooks-dir=hooks",
        "--noconfirm",  # Ne pas demander de confirmation
        "--clean",  # Nettoyer avant la construction
    ]
)
