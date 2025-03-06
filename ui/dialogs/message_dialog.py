from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QComboBox,
)
from utils.constants import UIMessages


class MessageDialog(QDialog):
    """Dialogue pour saisir un message personnalisé avant d'arrêter un flux"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(UIMessages.TITLE_STOP_STREAM)
        self.resize(400, 250)

        self.setup_ui()

    def setup_ui(self):
        """Configurer l'interface du dialogue"""
        layout = QVBoxLayout()

        # Instructions
        instruction_label = QLabel(UIMessages.STOP_STREAM_INSTRUCTION)
        layout.addWidget(instruction_label)

        # Liste déroulante avec messages prédéfinis
        self.preset_combo = QComboBox()
        self.preset_combo.addItem(UIMessages.CUSTOM_MESSAGE)
        self.preset_combo.addItem(UIMessages.TERMINATION_MESSAGE_DEFAULT)
        self.preset_combo.addItem(UIMessages.TERMINATION_MESSAGE_PAUSED)
        self.preset_combo.addItem(UIMessages.TERMINATION_MESSAGE_PLAYING)
        self.preset_combo.currentIndexChanged.connect(self.preset_selected)
        layout.addWidget(self.preset_combo)

        # Zone de texte pour le message
        self.message_edit = QTextEdit()
        self.message_edit.setPlaceholderText(UIMessages.STOP_STREAM_PLACEHOLDER)
        layout.addWidget(self.message_edit)

        # Boutons
        button_layout = QHBoxLayout()

        self.ok_button = QPushButton(UIMessages.BTN_STOP)
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self.accept)

        self.cancel_button = QPushButton(UIMessages.BTN_CANCEL)
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def preset_selected(self, index):
        """Gérer la sélection d'un message prédéfini"""
        if index == 0:  # Message personnalisé
            self.message_edit.clear()
            self.message_edit.setEnabled(True)
        else:
            self.message_edit.setText(self.preset_combo.currentText())
            self.message_edit.setEnabled(False)

    def get_message(self):
        """Récupérer le message saisi"""
        return self.message_edit.toPlainText().strip()
