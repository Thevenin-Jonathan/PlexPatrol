from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# Collecte les fichiers de données pour QtWebEngine
datas = collect_data_files("PyQt5", include_py_files=True)
binaries = collect_dynamic_libs("PyQt5")

# Vérifiez s'il y a un dossier QtWebEngineProcess dans le système
import os
from PyQt5.QtCore import QLibraryInfo

src = os.path.join(
    QLibraryInfo.location(QLibraryInfo.LibraryExecutablesPath), "QtWebEngineProcess*"
)
datas += [(src, ".")]

# Obtenez les ressources de QtWebEngine
qwe_path = QLibraryInfo.location(QLibraryInfo.DataPath) + "/resources"
datas += [(qwe_path, "PyQt5/Qt/resources")]
