from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QDialogButtonBox,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QPushButton,
    QLabel,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QWidget,
    QMessageBox,
    QCheckBox,
)
from PyQt5.QtCore import Qt
from utils.constants import UIMessages, ConfigKeys, Defaults


class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        from config.config_manager import config

        # Utiliser directement l'instance globale config
        self.config_manager = config
        self.plex_users = {}

        self.setup_ui()

    def setup_ui(self):
        """Configurer l'interface utilisateur du dialogue"""
        self.setWindowTitle(UIMessages.CONFIG_DIALOG_TITLE)
        self.resize(550, 600)

        layout = QVBoxLayout(self)

        # Onglets
        tabs = QTabWidget()

        # Onglet Serveur
        server_tab = QWidget()
        server_layout = QFormLayout(server_tab)

        self.server_url = QLineEdit()
        server_layout.addRow(UIMessages.CONFIG_SERVER_URL_LABEL, self.server_url)

        self.plex_token = QLineEdit()
        server_layout.addRow(UIMessages.CONFIG_TOKEN_LABEL, self.plex_token)

        self.check_interval = QSpinBox()
        self.check_interval.setRange(10, 300)
        self.check_interval.setSuffix(" secondes")
        server_layout.addRow(UIMessages.CONFIG_INTERVAL_LABEL, self.check_interval)

        # Ajouter le champ termination_message s'il manque
        self.termination_message_label = QLabel("Message de terminaison:")
        self.termination_message = QLineEdit()
        self.termination_message.setPlaceholderText(
            "Message à envoyer lors de la terminaison"
        )
        # Définir une valeur par défaut ou charger depuis la config
        self.termination_message.setText(
            self.config_manager.get(
                ConfigKeys.TERMINATION_MESSAGE,
                "Votre session a été terminée en raison d'une violation des règles d'utilisation",
            )
        )
        server_layout.addRow(self.termination_message_label, self.termination_message)

        # Bouton pour tester la connexion
        test_btn = QPushButton("Tester la connexion")
        test_btn.clicked.connect(self.test_connection)
        server_layout.addRow("", test_btn)

        tabs.addTab(server_tab, "Serveur")

        # Onglet Notifications
        notif_tab = QWidget()
        notif_layout = QFormLayout(notif_tab)

        self.telegram_enabled = QCheckBox("Activer les notifications Telegram")
        notif_layout.addRow(
            UIMessages.CONFIG_TELEGRAM_ENABLE_LABEL, self.telegram_enabled
        )

        self.telegram_token = QLineEdit()
        notif_layout.addRow(UIMessages.CONFIG_TELEGRAM_TOKEN_LABEL, self.telegram_token)

        self.telegram_group = QLineEdit()
        notif_layout.addRow(UIMessages.CONFIG_TELEGRAM_GROUP_LABEL, self.telegram_group)

        # Bouton pour tester les notifications
        test_notif_btn = QPushButton(UIMessages.BTN_TEST_NOTIFICATION)
        test_notif_btn.clicked.connect(self.test_notification)
        notif_layout.addRow("", test_notif_btn)

        tabs.addTab(notif_tab, "Notifications")

        layout.addWidget(tabs)

        # Boutons OK/Annuler
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Charger les paramètres
        self.load_settings()

    def accept(self):
        """Enregistrer les modifications et fermer le dialogue"""
        # À la place, mettre à jour directement la configuration dans la base
        self.config_manager.set(ConfigKeys.PLEX_SERVER_URL, self.server_url.text())
        self.config_manager.set(ConfigKeys.PLEX_TOKEN, self.plex_token.text())
        self.config_manager.set(ConfigKeys.CHECK_INTERVAL, self.check_interval.value())

        self.config_manager.set(
            ConfigKeys.TERMINATION_MESSAGE, self.termination_message.text()
        )

        self.config_manager.set(
            ConfigKeys.TELEGRAM_ENABLED, self.telegram_enabled.isChecked()
        )
        self.config_manager.set(
            ConfigKeys.TELEGRAM_BOT_TOKEN, self.telegram_token.text()
        )
        self.config_manager.set(
            ConfigKeys.TELEGRAM_GROUP_ID, self.telegram_group.text()
        )

        # Accepter le dialogue
        super().accept()

    def test_connection(self):
        """Tester la connexion au serveur Plex"""
        import requests

        url = f"{self.server_url.text()}/status/sessions"
        headers = {"X-Plex-Token": self.plex_token.text()}

        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                QMessageBox.information(
                    self, UIMessages.TITLE_SUCCESS, UIMessages.CONFIG_CONNECTION_SUCCESS
                )
            else:
                QMessageBox.warning(
                    self,
                    UIMessages.TITLE_ERROR,
                    UIMessages.CONFIG_CONNECTION_ERROR.format(
                        error=response.status_code
                    ),
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                UIMessages.TITLE_ERROR,
                UIMessages.CONFIG_CONNECTION_ERROR.format(error=str(e)),
            )

    def test_notification(self):
        """Tester l'envoi d'une notification Telegram"""
        from utils import send_telegram_notification

        message = UIMessages.TEST_NOTIFICATION_MESSAGE

        try:
            result = send_telegram_notification(message)
            if result:
                QMessageBox.information(
                    self, UIMessages.TITLE_SUCCESS, UIMessages.NOTIFICATION_SENT
                )
            else:
                QMessageBox.warning(
                    self, UIMessages.TITLE_ERROR, UIMessages.ERROR_SENDING_NOTIFICATION
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                UIMessages.TITLE_ERROR,
                UIMessages.ERROR_SENDING_NOTIFICATION_DETAILS.format(error=str(e)),
            )

    def load_settings(self):
        """Charge les paramètres de configuration dans l'interface"""
        # Plex
        self.server_url.setText(
            self.config_manager.get(
                ConfigKeys.PLEX_SERVER_URL, Defaults.PLEX_SERVER_URL
            )
        )
        self.plex_token.setText(self.config_manager.get(ConfigKeys.PLEX_TOKEN, ""))
        self.check_interval.setValue(
            self.config_manager.get(ConfigKeys.CHECK_INTERVAL, Defaults.CHECK_INTERVAL)
        )

        # Telegram
        self.telegram_enabled.setChecked(
            self.config_manager.get(ConfigKeys.TELEGRAM_ENABLED, False)
        )
        self.telegram_token.setText(
            self.config_manager.get(ConfigKeys.TELEGRAM_BOT_TOKEN, "")
        )
        self.telegram_group.setText(
            self.config_manager.get(ConfigKeys.TELEGRAM_GROUP_ID, "")
        )
