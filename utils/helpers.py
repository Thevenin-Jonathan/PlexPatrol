from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette


def get_app_path():
    """Obtenir le chemin de base de l'application, même si empaqueté avec PyInstaller"""
    import sys
    import os

    if getattr(sys, "frozen", False):
        # PyInstaller crée un dossier temporaire et met les fichiers dedans
        return sys._MEIPASS
    else:
        # Mode développement: le script s'exécute directement
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def apply_dark_theme(app):
    """Appliquer un thème sombre à l'application"""
    return apply_dark_palette(app)


def apply_dark_palette(app):
    """Appliquer un thème sombre à l'application"""
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)

    app.setPalette(dark_palette)

    # Styles supplémentaires
    app.setStyleSheet(
        """
        QToolTip { 
            color: #ffffff; 
            background-color: #2a82da; 
            border: 1px solid white; 
        }
        QPushButton {
            padding: 6px 12px;
            border-radius: 4px;
            background-color: #2a82da;
            color: white;
        }
        QPushButton:hover {
            background-color: #3a92ea;
        }
        QPushButton:pressed {
            background-color: #1a72ca;
        }
        QTableWidget {
            border: 1px solid #444444;
            gridline-color: #444444;
        }
        QHeaderView::section {
            background-color: #2a82da;
            color: white;
            padding: 4px;
        }
        QTabWidget::pane {
            border: 1px solid #444444;
        }
        QTabBar::tab {
            background-color: #353535;
            padding: 8px 16px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            color: white;
        }
        QTabBar::tab:selected {
            background-color: #2a82da;
        }
        QGroupBox {
            border: 1px solid #444444;
            border-radius: 4px;
            margin-top: 1em;
            padding: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 3px;
            background-color: #353535;
        }
    """
    )
