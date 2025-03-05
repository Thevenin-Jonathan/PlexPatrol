import os
from datetime import datetime
from utils import get_app_path
from utils.constants import UIMessages, LogLevels, Paths
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt, QTime
from PyQt5.QtGui import QTextCursor


class LogsWidget(QWidget):
    """Widget pour afficher les logs de l'application"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Configurer l'interface utilisateur"""
        layout = QVBoxLayout(self)

        # Zone de texte pour les logs
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)
        self.log_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #1e1e1e;
                color: white;
                font-family: Consolas, Monaco, monospace;
                font-size: 10pt;
            }
        """
        )

        layout.addWidget(self.log_text)

        # Boutons d'action
        buttons_layout = QHBoxLayout()

        clear_btn = QPushButton(UIMessages.BTN_RESET)
        clear_btn.clicked.connect(self.clear_logs)
        buttons_layout.addWidget(clear_btn)

        save_btn = QPushButton(UIMessages.BTN_SAVE)
        save_btn.clicked.connect(self.save_logs)
        buttons_layout.addWidget(save_btn)

        layout.addLayout(buttons_layout)

    def add_log(self, message, level=LogLevels.INFO):
        """Ajouter un message au journal des logs"""
        current_time = QTime.currentTime().toString("hh:mm:ss")
        log_message = f"[{current_time}] [{level}] {message}"

        # Définir la couleur en fonction du niveau
        color = "white"
        if level == LogLevels.ERROR:
            color = "red"
        elif level == LogLevels.WARNING:
            color = "orange"
        elif level == LogLevels.SUCCESS:
            color = "lightgreen"

        # Ajouter le message formaté
        self.log_text.append(f'<span style="color:{color};">{log_message}</span>')

        # Faire défiler vers le bas
        self.log_text.moveCursor(QTextCursor.End)

    def clear_logs(self):
        """Effacer les logs affichés"""
        self.log_text.clear()
        self.add_log(UIMessages.LOGS_CLEARED, LogLevels.INFO)

    def save_logs(self):
        """Enregistrer les logs dans un fichier"""

        logs_dir = os.path.join(get_app_path(), "logs")
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)

        filename = f"plexpatrol_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(logs_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self.log_text.toPlainText())

            self.add_log(
                UIMessages.LOGS_SAVED.format(filepath=filepath), LogLevels.SUCCESS
            )
        except Exception as e:
            self.add_log(
                f"Erreur lors de l'enregistrement des logs: {str(e)}", LogLevels.ERROR
            )
        pass
