import os
import json
import logging
import sqlite3
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

    def first_time_setup(self):
        """Configuration initiale si aucune donnée n'est présente"""
        from PyQt5.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QFormLayout,
            QLineEdit,
            QDialogButtonBox,
            QLabel,
            QMessageBox,
        )

        # Vérifier si des configurations essentielles sont manquantes
        plex_url = self.get("plex_server.url")
        plex_token = self.get("plex_server.token")

        logging.info(
            f"Vérification de la configuration - URL: {plex_url}, Token présent: {'Oui' if plex_token else 'Non'}"
        )

        if (
            plex_url
            and plex_token
            and plex_url != "http://localhost:32400"
            and plex_token != ""
        ):
            logging.info("Configuration déjà présente, skip du dialogue")
            return True

        logging.info("Configuration manquante, affichage du dialogue")

        dialog = QDialog()
        dialog.setWindowTitle("Configuration initiale PlexPatrol")
        layout = QVBoxLayout(dialog)

        info = QLabel(
            "Bienvenue dans PlexPatrol ! Veuillez configurer l'accès à votre serveur Plex."
        )
        layout.addWidget(info)

        form = QFormLayout()
        url_edit = QLineEdit("http://localhost:32400")
        token_edit = QLineEdit()

        form.addRow("URL du serveur Plex:", url_edit)
        form.addRow("Token Plex:", token_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() == QDialog.Accepted:
            self.set("plex_server.url", url_edit.text())
            self.set("plex_server.token", token_edit.text())
            return True
        else:
            QMessageBox.warning(
                None,
                "Configuration incomplète",
                "L'application pourrait ne pas fonctionner correctement.",
            )
            return False

    # Propriétés pour accéder facilement aux paramètres communs
    @property
    def plex_server_url(self):
        """URL du serveur Plex"""
        return self.get("plex_server.url", "http://localhost:32400")

    @property
    def plex_token(self):
        """Token d'authentification Plex"""
        return self.get("plex_server.token", "")

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
        return self.get("telegram.bot_token", "")

    @property
    def telegram_group_id(self):
        """ID du groupe Telegram"""
        return self.get("telegram.group_id", "")


# Instance globale
config = ConfigManager()
