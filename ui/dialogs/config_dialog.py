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

        self.server_url = QLineEdit()  # Suppression de l'initialisation
        server_layout.addRow(UIMessages.CONFIG_SERVER_URL_LABEL, self.server_url)

        self.plex_token = QLineEdit()  # Suppression de l'initialisation
        server_layout.addRow(UIMessages.CONFIG_TOKEN_LABEL, self.plex_token)

        self.check_interval = QSpinBox()
        self.check_interval.setRange(10, 300)
        self.check_interval.setSuffix(" secondes")
        server_layout.addRow(UIMessages.CONFIG_INTERVAL_LABEL, self.check_interval)

        # Bouton pour tester la connexion
        test_btn = QPushButton("Tester la connexion")
        test_btn.clicked.connect(self.test_connection)
        server_layout.addRow("", test_btn)

        tabs.addTab(server_tab, "Serveur")

        # Onglet Règles
        rules_tab = QWidget()
        rules_layout = QVBoxLayout(rules_tab)

        rules_form = QFormLayout()
        self.max_streams = QSpinBox()
        self.max_streams.setRange(1, 10)
        rules_form.addRow(UIMessages.CONFIG_MAX_STREAMS_LABEL, self.max_streams)

        self.termination_message = QLineEdit()  # Suppression de l'initialisation
        rules_form.addRow(UIMessages.CONFIG_TERM_MSG_LABEL, self.termination_message)

        rules_layout.addLayout(rules_form)

        # Groupe pour la liste blanche
        whitelist_group = QGroupBox("Liste blanche (utilisateurs exemptés)")
        whitelist_layout = QVBoxLayout(whitelist_group)

        # Charger la liste des utilisateurs Plex
        from core.plex_api import get_plex_users

        self.plex_users = get_plex_users()

        # Zone de sélection des utilisateurs
        users_layout = QHBoxLayout()
        users_label = QLabel("Sélectionner un utilisateur:")
        self.user_combo = QComboBox()

        # Ajouter les utilisateurs au combobox
        if self.plex_users:
            sorted_users = sorted(
                [(uid, name) for uid, name in self.plex_users.items()],
                key=lambda x: x[1].lower(),
            )
            for user_id, username in sorted_users:
                self.user_combo.addItem(username, user_id)
            self.user_combo.setCurrentIndex(0)
        else:
            self.user_combo.addItem("Aucun utilisateur trouvé", "")
            self.user_combo.setEnabled(False)

        users_layout.addWidget(users_label)
        users_layout.addWidget(self.user_combo, 1)

        add_btn = QPushButton("Ajouter")
        add_btn.clicked.connect(self.add_to_whitelist)
        users_layout.addWidget(add_btn)

        whitelist_layout.addLayout(users_layout)

        # Liste des utilisateurs en whitelist
        whitelist_label = QLabel("Utilisateurs exemptés:")
        whitelist_layout.addWidget(whitelist_label)

        self.whitelist = QListWidget()
        self.whitelist.setAlternatingRowColors(True)
        self.whitelist.setSelectionMode(QListWidget.SingleSelection)

        whitelist_layout.addWidget(self.whitelist)

        remove_btn = QPushButton("Supprimer")
        remove_btn.clicked.connect(self.remove_from_whitelist)
        whitelist_layout.addWidget(remove_btn)

        rules_layout.addWidget(whitelist_group)
        tabs.addTab(rules_tab, "Règles")

        # Onglet Notifications
        notif_tab = QWidget()
        notif_layout = QFormLayout(notif_tab)

        self.telegram_enabled = QCheckBox("Activer les notifications Telegram")
        notif_layout.addRow(
            UIMessages.CONFIG_TELEGRAM_ENABLE_LABEL, self.telegram_enabled
        )

        self.telegram_token = QLineEdit()  # Suppression de l'initialisation
        notif_layout.addRow(UIMessages.CONFIG_TELEGRAM_TOKEN_LABEL, self.telegram_token)

        self.telegram_group = QLineEdit()  # Suppression de l'initialisation
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

        # Charger les valeurs après avoir créé tous les widgets
        self.load_settings()

        # Configurer les valeurs par défaut
        self.server_url.setText(Defaults.PLEX_SERVER_URL)
        self.check_interval.setValue(Defaults.CHECK_INTERVAL)
        self.max_streams.setValue(Defaults.MAX_STREAMS)
        self.termination_message.setText(Defaults.TERMINATION_MESSAGE)

    def add_to_whitelist(self):
        """Ajouter un utilisateur à la liste blanche"""
        if self.user_combo.currentData():
            user_id = self.user_combo.currentData()
            username = self.user_combo.currentText()

            # Vérifier si l'utilisateur est déjà dans la liste
            for i in range(self.whitelist.count()):
                item = self.whitelist.item(i)
                if item.data(Qt.UserRole) == user_id:
                    QMessageBox.warning(
                        self,
                        "Utilisateur déjà présent",
                        f"L'utilisateur {username} est déjà dans la liste blanche.",
                    )
                    return

            # Ajouter à la liste
            item = QListWidgetItem(f"{username}")
            item.setData(Qt.UserRole, user_id)
            self.whitelist.addItem(item)

    def remove_from_whitelist(self):
        """Supprimer un utilisateur de la liste blanche"""
        selected = self.whitelist.currentRow()
        if selected >= 0:
            self.whitelist.takeItem(selected)

    def accept(self):
        """Enregistrer les modifications et fermer le dialogue"""
        # Supprimer tout le code qui manipule le fichier .env

        # À la place, mettre à jour directement la configuration dans la base
        self.config_manager.set(ConfigKeys.PLEX_SERVER_URL, self.server_url.text())
        self.config_manager.set(ConfigKeys.PLEX_TOKEN, self.plex_token.text())
        self.config_manager.set(ConfigKeys.CHECK_INTERVAL, self.check_interval.value())

        self.config_manager.set(ConfigKeys.MAX_STREAMS, self.max_streams.value())
        self.config_manager.set(
            ConfigKeys.TERMINATION_MESSAGE, self.termination_message.text()
        )

        # Mettre à jour la whitelist avec les IDs utilisateurs
        whitelist_ids = []
        for i in range(self.whitelist.count()):
            user_id = self.whitelist.item(i).data(Qt.UserRole)
            whitelist_ids.append(user_id)
        self.config_manager.set(ConfigKeys.WHITELIST, whitelist_ids)

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
        # Cette méthode est redondante car vous chargez déjà les paramètres dans setup_ui
        # On peut la rendre plus simple ou la supprimer

        # Plex
        self.server_url.setText(self.config_manager.plex_server_url)
        self.plex_token.setText(self.config_manager.plex_token)
        self.check_interval.setValue(self.config_manager.check_interval)

        # Règles
        self.max_streams.setValue(self.config_manager.default_max_streams)
        self.termination_message.setText(self.config_manager.termination_message)

        # Telegram
        self.telegram_enabled.setChecked(self.config_manager.telegram_enabled)
        self.telegram_token.setText(self.config_manager.telegram_bot_token)
        self.telegram_group.setText(self.config_manager.telegram_group_id)

        # Whitelist (si nécessaire)
        self.whitelist.clear()
        whitelist_ids = self.config_manager.get("rules.whitelist", [])
        for user_id in whitelist_ids:
            username = self.plex_users.get(user_id, f"Inconnu (ID: {user_id})")
            item = QListWidgetItem(f"{username}")
            item.setData(Qt.UserRole, user_id)
            self.whitelist.addItem(item)
