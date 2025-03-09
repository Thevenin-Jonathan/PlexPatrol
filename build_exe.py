import PyInstaller.__main__
import os

# Chemin vers l'icône de l'application (créez ou utilisez une icône existante)
icon_path = os.path.join("assets", "plexpatrol.ico")

# Répertoires à inclure
data_dirs = [
    ("assets", "assets"),  # Incluez tous les fichiers de ressources
]

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
        "--hidden-import=pkgutil",
        "--hidden-import=utils.constants",  # Important: ajout explicite de ce module
        "--hidden-import=config.config_manager",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtWidgets.QSystemTrayIcon",
        "--hidden-import=PyQt5.QtWidgets.QMenu",
        "--hidden-import=PyQt5.QtWebEngineWidgets",
        "--hidden-import=PyQt5.QtWebEngine",
        "--hidden-import=PyQt5.QtChart",
        "--hidden-import=geoip2",
        "--hidden-import=geoip2.database",
        "--additional-hooks-dir=hooks",
        "--noconfirm",  # Ne pas demander de confirmation
        "--clean",  # Nettoyer avant la construction
    ]
)
