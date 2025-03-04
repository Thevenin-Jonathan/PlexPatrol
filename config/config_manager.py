import os
import yaml
import logging
from dotenv import load_dotenv
from datetime import datetime
from utils import get_app_path


class ConfigManager:
    """Gestionnaire de configuration centralisé pour PlexPatrol"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialisation du gestionnaire de configuration"""
        load_dotenv(override=True)
        self._config = self._load_config()

    def _load_config(self):
        """Charger la configuration depuis le fichier YAML"""
        config_path = os.path.join(get_app_path(), "config.yml")
        # ... reste du code de chargement ...

    @property
    def plex_server_url(self):
        """URL du serveur Plex"""
        url = os.getenv("PLEX_SERVER_URL")
        if not url:
            url = self._config.get("plex_server", {}).get("url", "")
        return url

    @property
    def plex_token(self):
        """Token d'authentification Plex"""
        token = os.getenv("PLEX_TOKEN")
        if not token:
            token = self._config.get("plex_server", {}).get("token", "")
        return token

    # ... autres propriétés ...


# Créer une instance globale
config = ConfigManager()


def inject_env_variables(config):
    """Injecter les variables d'environnement dans la configuration"""
    # Plex Server
    if "plex_server" in config:
        if config["plex_server"].get("url") == "ENV_VAR:PLEX_SERVER_URL":
            config["plex_server"]["url"] = os.getenv(
                "PLEX_SERVER_URL", "http://localhost:32400"
            )

        if config["plex_server"].get("token") == "ENV_VAR:PLEX_TOKEN":
            config["plex_server"]["token"] = os.getenv("PLEX_TOKEN", "")

    # Telegram
    if "telegram" in config:
        if config["telegram"].get("bot_token") == "ENV_VAR:TELEGRAM_BOT_TOKEN":
            config["telegram"]["bot_token"] = os.getenv("TELEGRAM_BOT_TOKEN", "")

        if config["telegram"].get("group_id") == "ENV_VAR:TELEGRAM_GROUP_ID":
            config["telegram"]["group_id"] = os.getenv("TELEGRAM_GROUP_ID", "")

    return config


def load_config():
    """Charger la configuration depuis le fichier YAML et les variables d'environnement"""
    config_path = os.path.join(get_app_path(), "config.yml")
    default_config = {
        "plex_server": {
            "url": "ENV_VAR:PLEX_SERVER_URL",
            "token": "ENV_VAR:PLEX_TOKEN",
            "check_interval": 30,
        },
        "rules": {
            "max_streams": 2,
            "termination_message": "Votre abonnement ne vous permet pas la lecture sur plusieurs écrans.",
            "whitelist": [],
        },
        "telegram": {
            "bot_token": "ENV_VAR:TELEGRAM_BOT_TOKEN",
            "group_id": "ENV_VAR:TELEGRAM_GROUP_ID",
        },
    }

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

                # S'assurer que la structure est complète
                if not config:
                    config = default_config
                else:
                    # S'assurer que les sections existent
                    if "plex_server" not in config:
                        config["plex_server"] = default_config["plex_server"]
                    if "rules" not in config:
                        config["rules"] = default_config["rules"]
                    if "telegram" not in config:
                        config["telegram"] = default_config["telegram"]

            # Remplacer les variables d'environnement
            config = inject_env_variables(config)
            return config
        except Exception as e:
            logging.error(f"Erreur lors du chargement de la configuration: {str(e)}")
            return inject_env_variables(default_config)
    else:
        # Créer le fichier de configuration par défaut
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    default_config, f, default_flow_style=False, allow_unicode=True
                )

            # Appliquer les variables d'environnement
            return inject_env_variables(default_config)
        except Exception as e:
            logging.error(f"Erreur lors de la création de la configuration: {str(e)}")
            return inject_env_variables(default_config)


def save_config(config):
    """Enregistrer la configuration dans le fichier YAML en excluant les informations sensibles"""
    config_path = os.path.join(get_app_path(), "config.yml")
    try:
        # Créer une copie profonde pour ne pas modifier l'original
        import copy

        save_config = copy.deepcopy(config)

        # Retirer complètement les informations sensibles du fichier config.yml
        if "plex_server" in save_config:
            # Remplacer les valeurs sensibles par des placeholders
            if "url" in save_config["plex_server"] and os.getenv("PLEX_SERVER_URL"):
                save_config["plex_server"]["url"] = "ENV_VAR:PLEX_SERVER_URL"
            if "token" in save_config["plex_server"] and os.getenv("PLEX_TOKEN"):
                save_config["plex_server"]["token"] = "ENV_VAR:PLEX_TOKEN"

        if "telegram" in save_config:
            if "bot_token" in save_config["telegram"] and os.getenv(
                "TELEGRAM_BOT_TOKEN"
            ):
                save_config["telegram"]["bot_token"] = "ENV_VAR:TELEGRAM_BOT_TOKEN"
            if "group_id" in save_config["telegram"] and os.getenv("TELEGRAM_GROUP_ID"):
                save_config["telegram"]["group_id"] = "ENV_VAR:TELEGRAM_GROUP_ID"

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(save_config, f, default_flow_style=False, allow_unicode=True)
        return True
    except Exception as e:
        logging.error(f"Erreur lors de l'enregistrement de la configuration: {str(e)}")
        return False


def initialize_env_file():
    """
    Vérifie si le fichier .env existe, sinon guide l'utilisateur pour le créer

    Returns:
        bool: True si le fichier existe ou a été créé, False sinon
    """
    env_path = os.path.join(get_app_path(), ".env")

    # Vérifier si le fichier existe déjà
    if os.path.exists(env_path):
        return True

    # Le fichier n'existe pas, proposer de le créer
    from PyQt5.QtWidgets import (
        QMessageBox,
        QDialog,
        QVBoxLayout,
        QFormLayout,
        QLineEdit,
        QDialogButtonBox,
        QLabel,
    )

    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle("Configuration initiale")
    msg.setText("Certains paramètres importants ne sont pas configurés.")
    msg.setInformativeText(
        "L'application a besoin du token API et de l'URL du serveur Plex.\n"
        "Voulez-vous les configurer maintenant?"
    )

    # Créer des boutons personnalisés en français
    oui_button = msg.addButton("Oui", QMessageBox.YesRole)
    non_button = msg.addButton("Non", QMessageBox.NoRole)

    msg.exec_()

    # Vérifier quel bouton a été cliqué
    if msg.clickedButton() == oui_button:
        # Créer un dialogue pour obtenir les informations nécessaires
        dialog = QDialog()
        dialog.setWindowTitle("Configuration des paramètres sensibles")
        layout = QVBoxLayout(dialog)

        # Ajouter une explication
        info_label = QLabel(
            "Ces informations seront stockées uniquement sur votre machine."
        )
        layout.addWidget(info_label)

        form = QFormLayout()

        # Champs pour les variables sensibles
        plex_url = QLineEdit("http://localhost:32400")
        plex_token = QLineEdit()
        telegram_token = QLineEdit()
        telegram_group = QLineEdit()

        form.addRow("URL du serveur Plex:", plex_url)
        form.addRow("Token Plex:", plex_token)
        form.addRow("Token du bot Telegram (optionnel):", telegram_token)
        form.addRow("ID du groupe Telegram (optionnel):", telegram_group)

        layout.addLayout(form)

        # Ajouter un lien pour obtenir un token Plex
        help_label = QLabel(
            "Pour obtenir votre token Plex, consultez <a href='https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/'>cet article</a>"
        )
        help_label.setOpenExternalLinks(True)
        layout.addWidget(help_label)

        # Boutons OK/Annuler
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() == QDialog.Accepted:
            # Créer le fichier .env avec les informations fournies
            try:
                with open(env_path, "w", encoding="utf-8") as f:
                    f.write("# Configuration PlexPatrol\n")
                    f.write(
                        f"# Généré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    )

                    f.write("# Serveur Plex\n")
                    f.write(f"PLEX_SERVER_URL={plex_url.text()}\n")
                    f.write(f"PLEX_TOKEN={plex_token.text()}\n\n")

                    f.write("# Telegram\n")
                    f.write(f"TELEGRAM_BOT_TOKEN={telegram_token.text()}\n")
                    f.write(f"TELEGRAM_GROUP_ID={telegram_group.text()}\n")

                # Recharger les variables d'environnement
                from dotenv import load_dotenv

                load_dotenv(override=True)

                QMessageBox.information(
                    None,
                    "Configuration réussie",
                    "Le fichier .env a été créé avec succès.",
                )
                return True
            except Exception as e:
                QMessageBox.critical(
                    None, "Erreur", f"Impossible de créer le fichier .env: {str(e)}"
                )
                return False
        else:
            return False
    else:
        # L'utilisateur a refusé de créer le fichier
        QMessageBox.warning(
            None,
            "Configuration incomplète",
            "Certaines fonctionnalités peuvent ne pas fonctionner correctement.",
        )
        return False


def validate_env_variables():
    """Vérifie que les variables d'environnement nécessaires sont présentes"""
    import os
    from PyQt5.QtWidgets import QMessageBox

    missing = []

    if not os.getenv("PLEX_SERVER_URL"):
        missing.append("PLEX_SERVER_URL")

    if not os.getenv("PLEX_TOKEN"):
        missing.append("PLEX_TOKEN")

    if missing:
        QMessageBox.warning(
            None,
            "Configuration incomplète",
            f"Les variables d'environnement suivantes sont manquantes: {', '.join(missing)}\n"
            "Certaines fonctionnalités pourraient ne pas fonctionner correctement.",
        )
        return False

    return True
