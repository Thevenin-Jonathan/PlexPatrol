from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collecter tous les sous-modules de PyQt5
hiddenimports = collect_submodules("PyQt5")

# Ajouter des modules standard Python utilisés par PyQt5
hiddenimports += [
    "pkgutil",
    "inspect",
    "importlib",
    "importlib.machinery",
    "importlib.util",
    "encodings.idna",
]

# Collecter les fichiers de données
datas = collect_data_files("PyQt5")
