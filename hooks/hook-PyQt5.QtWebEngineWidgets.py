from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
)
import os
from PyQt5.QtCore import QLibraryInfo

# Collecte les fichiers de données pour QtWebEngine
datas = collect_data_files("PyQt5", include_py_files=True)
binaries = collect_dynamic_libs("PyQt5")

# Ajouter QtWebEngineProcess
src = os.path.join(
    QLibraryInfo.location(QLibraryInfo.LibraryExecutablesPath), "QtWebEngineProcess*"
)
datas.append((src, "."))

# Récupérer toutes les ressources nécessaires pour QtWebEngine
qwe_path = QLibraryInfo.location(QLibraryInfo.DataPath)
resources_path = os.path.join(qwe_path, "resources")
translations_path = os.path.join(qwe_path, "translations")

if os.path.exists(resources_path):
    datas.append((resources_path, "PyQt5/Qt/resources"))

if os.path.exists(translations_path):
    datas.append((translations_path, "PyQt5/Qt/translations"))

# Ressources spécifiques pour les cartes de géolocalisation
qtwe_resources = os.path.join(qwe_path, "qtwebengine_resources.pak")
if os.path.exists(qtwe_resources):
    datas.append((qtwe_resources, "PyQt5/Qt"))
