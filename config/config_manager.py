import os
import json
import logging
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from utils import get_app_path


class ConfigManager:
    """Gestionnaire de configuration centralisé pour PlexPatrol utilisant SQLite"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialisation du gestionnaire de configuration"""
        load_dotenv(override=True)
        self.db_path = os.path.join(get_app_path(), "data", "plexpatrol.db")

        # Vérifie si le répertoire data existe, sinon le crée
        data_dir = os.path.dirname(self.db_path)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        self._ensure_db_exists()
        self._config_cache = {}
        self._load_config_to_cache()

    def _ensure_db_exists(self):
        """S'assure que la table de configuration existe"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS app_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            value_type TEXT NOT NULL,
            category TEXT,
            description TEXT,
            last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        conn.commit()
        conn.close()

        # Initialiser la configuration par défaut si nécessaire
        self._initialize_default_config_if_empty()

    def _initialize_default_config_if_empty(self):
        """Initialise la configuration par défaut si aucune entrée n'existe"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM app_config")
        count = cursor.fetchone()[0]
        conn.close()

        if count > 0:
            return  # La configuration existe déjà

        # Configuration par défaut
        default_config = {
            "plex_server.url": {
                "value": "http://localhost:32400",
                "type": "str",
                "category": "plex",
                "description": "URL du serveur Plex",
            },
            "plex_server.token": {
                "value": "",
                "type": "str",
                "category": "plex",
                "description": "Token d'authentification Plex",
            },
            "plex_server.check_interval": {
                "value": "30",
                "type": "int",
                "category": "plex",
                "description": "Intervalle de vérification en secondes",
            },
            "rules.max_streams": {
                "value": "2",
                "type": "int",
                "category": "rules",
                "description": "Nombre maximum de flux simultanés par défaut",
            },
            "rules.termination_message": {
                "value": "Votre abonnement ne vous permet pas la lecture sur plusieurs écrans.",
                "type": "str",
                "category": "rules",
                "description": "Message affiché lors de la terminaison d'un flux",
            },
            "telegram.enabled": {
                "value": "False",
                "type": "bool",
                "category": "notifications",
                "description": "Activer les notifications Telegram",
            },
            "telegram.bot_token": {
                "value": "",
                "type": "str",
                "category": "notifications",
                "description": "Token du bot Telegram",
            },
            "telegram.group_id": {
                "value": "",
                "type": "str",
                "category": "notifications",
                "description": "ID du groupe Telegram",
            },
        }

        # Injecter les variables d'environnement
        if os.getenv("PLEX_SERVER_URL"):
            default_config["plex_server.url"]["value"] = os.getenv("PLEX_SERVER_URL")
        if os.getenv("PLEX_TOKEN"):
            default_config["plex_server.token"]["value"] = os.getenv("PLEX_TOKEN")
        if os.getenv("TELEGRAM_BOT_TOKEN"):
            default_config["telegram.bot_token"]["value"] = os.getenv(
                "TELEGRAM_BOT_TOKEN"
            )
            default_config["telegram.enabled"]["value"] = "True"
        if os.getenv("TELEGRAM_GROUP_ID"):
            default_config["telegram.group_id"]["value"] = os.getenv(
                "TELEGRAM_GROUP_ID"
            )

        # Insérer la configuration par défaut
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for key, config in default_config.items():
            cursor.execute(
                "INSERT INTO app_config (key, value, value_type, category, description) VALUES (?, ?, ?, ?, ?)",
                (
                    key,
                    config["value"],
                    config["type"],
                    config["category"],
                    config["description"],
                ),
            )

        conn.commit()
        conn.close()
        print("Configuration par défaut initialisée dans la base de données")

    def _load_config_to_cache(self):
        """Charge la configuration depuis la BD vers le cache"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT key, value, value_type FROM app_config")
        for row in cursor.fetchall():
            key = row["key"]
            value = self._convert_value(row["value"], row["value_type"])
            self._config_cache[key] = value

        conn.close()

    def _convert_value(self, value_str, value_type):
        """Convertit une valeur de texte selon son type"""
        if value_type == "bool":
            return value_str.lower() in ("true", "1", "yes")
        elif value_type == "int":
            try:
                return int(value_str)
            except:
                return 0
        elif value_type == "float":
            try:
                return float(value_str)
            except:
                return 0.0
        elif value_type == "list":
            try:
                return json.loads(value_str)
            except:
                return []
        elif value_type == "dict":
            try:
                return json.loads(value_str)
            except:
                return {}
        else:
            return value_str

    def get(self, key, default=None):
        """Récupère une valeur de configuration"""
        # Vérifier d'abord dans le cache
        if key in self._config_cache:
            return self._config_cache[key]

        # Vérifier dans la BD si pas trouvé dans le cache
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT value, value_type FROM app_config WHERE key = ?", (key,))
        row = cursor.fetchone()

        conn.close()

        if row:
            value = self._convert_value(row[0], row[1])
            # Mettre à jour le cache
            self._config_cache[key] = value
            return value

        return default

    def set(self, key, value, commit=True):
        """Définit une valeur de configuration"""
        # Déterminer le type
        if isinstance(value, bool):
            value_type = "bool"
            value_str = str(value).lower()
        elif isinstance(value, int):
            value_type = "int"
            value_str = str(value)
        elif isinstance(value, float):
            value_type = "float"
            value_str = str(value)
        elif isinstance(value, list):
            value_type = "list"
            value_str = json.dumps(value)
        elif isinstance(value, dict):
            value_type = "dict"
            value_str = json.dumps(value)
        else:
            value_type = "str"
            value_str = str(value) if value is not None else ""

        # Mettre à jour la BD
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO app_config (key, value, value_type, last_modified) 
            VALUES (?, ?, ?, datetime('now'))
            """,
            (key, value_str, value_type),
        )

        if commit:
            conn.commit()
        conn.close()

        # Mettre à jour le cache
        self._config_cache[key] = value
        return True

    def set_many(self, config_dict):
        """Met à jour plusieurs paramètres de configuration à la fois"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            for key, value in config_dict.items():
                # Déterminer le type
                if isinstance(value, bool):
                    value_type = "bool"
                    value_str = str(value).lower()
                elif isinstance(value, int):
                    value_type = "int"
                    value_str = str(value)
                elif isinstance(value, float):
                    value_type = "float"
                    value_str = str(value)
                elif isinstance(value, list):
                    value_type = "list"
                    value_str = json.dumps(value)
                elif isinstance(value, dict):
                    value_type = "dict"
                    value_str = json.dumps(value)
                else:
                    value_type = "str"
                    value_str = str(value) if value is not None else ""

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO app_config (key, value, value_type, last_modified) 
                    VALUES (?, ?, ?, datetime('now'))
                    """,
                    (key, value_str, value_type),
                )

                # Mettre à jour le cache
                self._config_cache[key] = value

            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour multiple: {str(e)}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_category(self, category):
        """Récupère toutes les configurations d'une catégorie donnée"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT key, value, value_type FROM app_config WHERE category = ?",
            (category,),
        )
        result = {}

        for row in cursor.fetchall():
            key = row["key"].split(".")[
                -1
            ]  # Extrait seulement la dernière partie de la clé
            value = self._convert_value(row["value"], row["value_type"])
            result[key] = value

        conn.close()
        return result

    def get_all_categories(self):
        """Récupère toutes les catégories distinctes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT DISTINCT category FROM app_config WHERE category IS NOT NULL"
        )
        categories = [row[0] for row in cursor.fetchall()]

        conn.close()
        return categories

    def get_all_config(self):
        """Récupère toute la configuration sous forme de dictionnaire structuré"""
        # Recharger tout le cache depuis la BD pour s'assurer qu'il est à jour
        self._load_config_to_cache()

        result = {}
        for key, value in self._config_cache.items():
            parts = key.split(".")
            current = result

            # Naviguer à travers la structure pour placer la valeur au bon endroit
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current[part] = value
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

        return result

    def delete(self, key):
        """Supprime une configuration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM app_config WHERE key = ?", (key,))
        conn.commit()
        conn.close()

        # Supprimer du cache
        if key in self._config_cache:
            del self._config_cache[key]

        return True

    def reset_to_defaults(self):
        """Réinitialise la configuration aux valeurs par défaut"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM app_config")
        conn.commit()
        conn.close()

        # Vider le cache
        self._config_cache = {}

        # Réinitialiser avec les valeurs par défaut
        self._initialize_default_config_if_empty()
        self._load_config_to_cache()

        return True

    # Propriétés pour accéder facilement aux paramètres communs
    @property
    def plex_server_url(self):
        """URL du serveur Plex"""
        url = os.getenv("PLEX_SERVER_URL")
        if not url:
            url = self.get("plex_server.url", "http://localhost:32400")
        return url

    @property
    def plex_token(self):
        """Token d'authentification Plex"""
        token = os.getenv("PLEX_TOKEN")
        if not token:
            token = self.get("plex_server.token", "")
        return token

    @property
    def check_interval(self):
        """Intervalle de vérification des flux"""
        return self.get("plex_server.check_interval", 30)

    @property
    def default_max_streams(self):
        """Nombre maximum de flux simultanés par défaut"""
        return self.get("rules.max_streams", 2)

    @property
    def termination_message(self):
        """Message affiché lors de la terminaison d'un flux"""
        return self.get(
            "rules.termination_message",
            "Votre abonnement ne vous permet pas la lecture sur plusieurs écrans.",
        )

    @property
    def telegram_enabled(self):
        """Notifications Telegram activées"""
        return self.get("telegram.enabled", False)

    @property
    def telegram_bot_token(self):
        """Token du bot Telegram"""
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            token = self.get("telegram.bot_token", "")
        return token

    @property
    def telegram_group_id(self):
        """ID du groupe Telegram"""
        group_id = os.getenv("TELEGRAM_GROUP_ID")
        if not group_id:
            group_id = self.get("telegram.group_id", "")
        return group_id


# Instance globale
config = ConfigManager()


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

                # Mettre à jour la configuration dans la base de données
                config = ConfigManager()

                # Plex
                if plex_url.text():
                    config.set("plex_server.url", plex_url.text())
                if plex_token.text():
                    config.set("plex_server.token", plex_token.text())

                # Telegram
                if telegram_token.text():
                    config.set("telegram.bot_token", telegram_token.text())
                    config.set("telegram.enabled", True)
                if telegram_group.text():
                    config.set("telegram.group_id", telegram_group.text())

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
    """Vérifie que les variables d'environnement nécessaires sont présentes et les applique à la configuration"""
    import os
    from PyQt5.QtWidgets import QMessageBox

    config_manager = ConfigManager()
    missing = []

    if not os.getenv("PLEX_SERVER_URL") and not config_manager.get("plex_server.url"):
        missing.append("PLEX_SERVER_URL")

    if not os.getenv("PLEX_TOKEN") and not config_manager.get("plex_server.token"):
        missing.append("PLEX_TOKEN")

    if missing:
        QMessageBox.warning(
            None,
            "Configuration incomplète",
            f"Les informations de configuration suivantes sont manquantes: {', '.join(missing)}\n"
            "Certaines fonctionnalités pourraient ne pas fonctionner correctement.",
        )
        return False

    # Appliquer les variables d'environnement en priorité, si présentes
    if os.getenv("PLEX_SERVER_URL"):
        config_manager.set("plex_server.url", os.getenv("PLEX_SERVER_URL"))
    if os.getenv("PLEX_TOKEN"):
        config_manager.set("plex_server.token", os.getenv("PLEX_TOKEN"))
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        config_manager.set("telegram.bot_token", os.getenv("TELEGRAM_BOT_TOKEN"))
        config_manager.set("telegram.enabled", True)
    if os.getenv("TELEGRAM_GROUP_ID"):
        config_manager.set("telegram.group_id", os.getenv("TELEGRAM_GROUP_ID"))

    return True
