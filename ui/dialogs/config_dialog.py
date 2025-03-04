from datetime import datetime
import os
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
)
from PyQt5.QtCore import Qt
from utils import send_telegram_notification
from core import get_plex_users


class ConfigDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.plex_users = {}  # Sera rempli dans setup_ui
        self.setup_ui()

    def setup_ui(self):
        """Configurer l'interface utilisateur du dialogue"""

        # Priorité aux variables d'environnement sur les valeurs de config
        plex_url = os.getenv("PLEX_SERVER_URL", "")
        if not plex_url:
            plex_url = self.config["plex_server"].get("url", "http://localhost:32400")
            if plex_url == "ENV_VAR:PLEX_SERVER_URL":
                plex_url = ""

        plex_token = os.getenv("PLEX_TOKEN", "")
        if not plex_token:
            plex_token = self.config["plex_server"].get("token", "")
            if plex_token == "ENV_VAR:PLEX_TOKEN":
                plex_token = ""

        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not telegram_token:
            telegram_token = self.config.get("telegram", {}).get("bot_token", "")
            if telegram_token == "ENV_VAR:TELEGRAM_BOT_TOKEN":
                telegram_token = ""

        telegram_group = os.getenv("TELEGRAM_GROUP_ID", "")
        if not telegram_group:
            telegram_group = self.config.get("telegram", {}).get("group_id", "")
            if telegram_group == "ENV_VAR:TELEGRAM_GROUP_ID":
                telegram_group = ""

        self.setWindowTitle("Configuration")
        self.resize(550, 600)

        layout = QVBoxLayout(self)

        # Onglets
        tabs = QTabWidget()

        # Onglet Serveur
        server_tab = QWidget()
        server_layout = QFormLayout(server_tab)

        self.server_url = QLineEdit(plex_url)
        server_layout.addRow("URL du serveur:", self.server_url)

        self.plex_token = QLineEdit(plex_token)
        server_layout.addRow("Token Plex:", self.plex_token)

        self.check_interval = QSpinBox()
        self.check_interval.setRange(10, 300)
        self.check_interval.setValue(
            self.config["plex_server"].get("check_interval", 30)
        )
        self.check_interval.setSuffix(" secondes")
        server_layout.addRow("Intervalle de vérification:", self.check_interval)

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
        self.max_streams.setValue(self.config.get("rules", {}).get("max_streams", 1))
        rules_form.addRow("Nombre max de flux par utilisateur:", self.max_streams)

        self.termination_message = QLineEdit(
            self.config.get("rules", {}).get(
                "termination_message", "Dépassement du nombre de flux autorisés"
            )
        )
        rules_form.addRow("Message d'arrêt:", self.termination_message)

        rules_layout.addLayout(rules_form)

        # Groupe pour la liste blanche
        whitelist_group = QGroupBox("Liste blanche (utilisateurs exemptés)")
        whitelist_layout = QVBoxLayout(whitelist_group)

        # Charger la liste des utilisateurs Plex
        self.plex_users = get_plex_users(self.config)

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

        # Remplir la liste avec les utilisateurs déjà whitelistés
        whitelist_ids = self.config.get("rules", {}).get("whitelist", [])
        for user_id in whitelist_ids:
            username = self.plex_users.get(user_id, f"Inconnu (ID: {user_id})")
            item = QListWidgetItem(f"{username}")
            item.setData(Qt.UserRole, user_id)  # Stocker l'ID utilisateur
            self.whitelist.addItem(item)

        whitelist_layout.addWidget(self.whitelist)

        remove_btn = QPushButton("Supprimer")
        remove_btn.clicked.connect(self.remove_from_whitelist)
        whitelist_layout.addWidget(remove_btn)

        rules_layout.addWidget(whitelist_group)
        tabs.addTab(rules_tab, "Règles")

        # Onglet Notifications
        notif_tab = QWidget()
        notif_layout = QFormLayout(notif_tab)

        self.telegram_token = QLineEdit(telegram_token)
        notif_layout.addRow("Token du bot Telegram:", self.telegram_token)

        self.telegram_group = QLineEdit(telegram_group)
        notif_layout.addRow("ID du groupe/canal Telegram:", self.telegram_group)

        # Bouton pour tester les notifications
        test_notif_btn = QPushButton("Tester la notification")
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
        import os

        # Mettre à jour les variables d'environnement pour les données sensibles
        # et les écrire dans .env
        from utils.helpers import get_app_path

        env_file_path = os.path.join(get_app_path(), ".env")
        env_contents = []

        # Lire le fichier .env existant s'il existe
        if os.path.exists(env_file_path):
            with open(env_file_path, "r", encoding="utf-8") as f:
                env_contents = f.readlines()

        # Créer un dictionnaire pour les variables d'environnement actuelles
        env_vars = {}
        for line in env_contents:
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    env_vars[parts[0]] = parts[1]

        # Mettre à jour les variables avec les nouvelles valeurs
        env_vars["PLEX_SERVER_URL"] = self.server_url.text()
        env_vars["PLEX_TOKEN"] = self.plex_token.text()
        env_vars["TELEGRAM_BOT_TOKEN"] = self.telegram_token.text()
        env_vars["TELEGRAM_GROUP_ID"] = self.telegram_group.text()

        # Écrire le fichier .env mis à jour
        with open(env_file_path, "w", encoding="utf-8") as f:
            f.write("# Configuration PlexPatrol\n")
            f.write(
                "# Généré le " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n"
            )

            # Écrire les variables sensibles
            f.write("# Serveur Plex\n")
            f.write(f"PLEX_SERVER_URL={env_vars['PLEX_SERVER_URL']}\n")
            f.write(f"PLEX_TOKEN={env_vars['PLEX_TOKEN']}\n\n")

            f.write("# Telegram\n")
            f.write(f"TELEGRAM_BOT_TOKEN={env_vars['TELEGRAM_BOT_TOKEN']}\n")
            f.write(f"TELEGRAM_GROUP_ID={env_vars['TELEGRAM_GROUP_ID']}\n")

        # Mettre à jour la configuration (sans les données sensibles)
        if "plex_server" not in self.config:
            self.config["plex_server"] = {}

        # Les valeurs sensibles seront remplacées par des références aux variables d'environnement
        self.config["plex_server"]["url"] = "ENV_VAR:PLEX_SERVER_URL"
        self.config["plex_server"]["token"] = "ENV_VAR:PLEX_TOKEN"
        self.config["plex_server"]["check_interval"] = self.check_interval.value()

        if "rules" not in self.config:
            self.config["rules"] = {}
        self.config["rules"]["max_streams"] = self.max_streams.value()
        self.config["rules"]["termination_message"] = self.termination_message.text()

        # Mettre à jour la whitelist avec les IDs utilisateurs
        whitelist_ids = []
        for i in range(self.whitelist.count()):
            user_id = self.whitelist.item(i).data(Qt.UserRole)
            whitelist_ids.append(user_id)
        self.config["rules"]["whitelist"] = whitelist_ids

        if "telegram" not in self.config:
            self.config["telegram"] = {}
        self.config["telegram"]["bot_token"] = "ENV_VAR:TELEGRAM_BOT_TOKEN"
        self.config["telegram"]["group_id"] = "ENV_VAR:TELEGRAM_GROUP_ID"

        # Enregistrer la configuration
        from config.config_manager import save_config

        save_config(self.config)

        # Recharger les variables d'environnement pour les prendre en compte immédiatement
        from dotenv import load_dotenv

        load_dotenv(override=True)

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
                    self, "Succès", "Connexion au serveur Plex réussie!"
                )
            else:
                QMessageBox.warning(
                    self, "Erreur", f"Erreur de connexion: {response.status_code}"
                )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur de connexion: {str(e)}")

    def test_notification(self):
        """Tester l'envoi d'une notification Telegram"""

        # Créer une configuration temporaire
        temp_config = {
            "telegram": {
                "bot_token": self.telegram_token.text(),
                "group_id": self.telegram_group.text(),
            }
        }

        message = "Ceci est un message de test de l'application PlexPatrol"

        try:
            result = send_telegram_notification(temp_config, message)
            if result:
                QMessageBox.information(
                    self, "Succès", "Notification envoyée avec succès!"
                )
            else:
                QMessageBox.warning(
                    self, "Erreur", "Impossible d'envoyer la notification"
                )
        except Exception as e:
            QMessageBox.critical(
                self, "Erreur", f"Erreur lors de l'envoi de la notification: {str(e)}"
            )
