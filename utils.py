import os
import json
import yaml
import sys
import requests
import logging
from datetime import datetime


def get_app_path():
    """Obtenir le chemin de l'application, fonctionne même avec PyInstaller"""
    if getattr(sys, "frozen", False):
        # Si l'application est compilée avec PyInstaller
        return os.path.dirname(sys.executable)
    else:
        # Si l'application est exécutée en développement
        return os.path.dirname(os.path.abspath(__file__))


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
    """
    Vérifier que les variables d'environnement essentielles sont définies

    Returns:
        bool: True si toutes les variables requises sont définies, False sinon
    """
    required_vars = ["PLEX_SERVER_URL", "PLEX_TOKEN"]
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        from PyQt5.QtWidgets import QMessageBox

        QMessageBox.warning(
            None,
            "Variables manquantes",
            f"Les infos suivantes ne sont pas définies dans les paramètres:\n\n"
            f"{', '.join(missing_vars)}\n\n"
            f"Certaines fonctionnalités peuvent ne pas fonctionner correctement.",
        )
        return False

    return True


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


def load_stats():
    """Charger les statistiques d'utilisation"""
    stats_path = os.path.join(get_app_path(), "stats.json")

    if not os.path.exists(stats_path):
        return {}

    try:
        with open(stats_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Erreur lors du chargement des statistiques: {str(e)}")
        return {}


def save_stats(stats):
    """Enregistrer les statistiques d'utilisation"""
    stats_path = os.path.join(get_app_path(), "stats.json")
    try:
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
        return True
    except Exception as e:
        logging.error(f"Erreur lors de l'enregistrement des statistiques: {str(e)}")
        return False


def update_user_stats(
    stats, username, stream_count=1, stream_killed=False, platform=None
):
    """
    Mettre à jour les statistiques d'un utilisateur

    Args:
        stats (dict): Dictionnaire des statistiques
        username (str): Nom de l'utilisateur
        stream_count (int): Nombre de flux détectés
        stream_killed (bool): Si un flux a été arrêté
        platform (str): Plateforme utilisée (si flux arrêté)

    Returns:
        dict: Statistiques mises à jour
    """
    if username not in stats:
        stats[username] = {
            "total_sessions": 0,
            "kill_count": 0,
            "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "platforms": {},
        }

    # Mettre à jour les statistiques de base
    stats[username]["total_sessions"] += stream_count
    stats[username]["last_seen"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Si un flux a été arrêté
    if stream_killed:
        stats[username]["kill_count"] += 1
        stats[username]["last_kill"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Mettre à jour les statistiques par plateforme
        if platform:
            if platform not in stats[username]["platforms"]:
                stats[username]["platforms"][platform] = 0
            stats[username]["platforms"][platform] += 1

    return stats


def get_plex_users(config):
    """
    Récupère la liste des utilisateurs Plex avec leurs IDs

    Args:
        config (dict): Configuration contenant l'URL et le token Plex

    Returns:
        dict: Dictionnaire {user_id: username} des utilisateurs
    """
    import requests
    import xml.etree.ElementTree as ET
    import logging

    url = f"{config['plex_server']['url']}/accounts"
    headers = {"X-Plex-Token": config["plex_server"]["token"]}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            # Parser la réponse XML
            root = ET.fromstring(response.text)

            # Extraire les informations des utilisateurs
            users = {}
            for user in root.findall(".//Account"):
                user_id = user.get("id")
                username = user.get("name")
                if user_id and username:
                    users[user_id] = username

            return users
        else:
            logging.error(
                f"Erreur lors de la récupération des utilisateurs: {response.status_code}"
            )
            return {}
    except Exception as e:
        logging.error(f"Exception lors de la récupération des utilisateurs: {str(e)}")
        return {}


def send_telegram_notification(config, message):
    """
    Envoyer une notification Telegram

    Args:
        config (dict): Configuration avec les paramètres Telegram
        message (str): Message à envoyer

    Returns:
        bool: True si le message a été envoyé avec succès, False sinon
    """
    bot_token = config["telegram"].get("bot_token", "")
    group_id = config["telegram"].get("group_id", "")

    if not bot_token or not group_id:
        logging.warning("Configuration Telegram incomplète, notification non envoyée")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": group_id, "text": message, "parse_mode": "HTML"}

    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            return True
        else:
            logging.error(
                f"Erreur lors de l'envoi du message Telegram: {response.status_code}"
            )
            return False
    except Exception as e:
        logging.error(f"Exception lors de l'envoi du message Telegram: {str(e)}")
        return False


def format_stream_info(stream):
    """
    Formater les informations d'un flux pour l'affichage

    Args:
        stream (tuple): Informations du flux

    Returns:
        str: Texte formaté
    """
    (
        session_id,
        ip_address,
        player_id,
        library_section,
        media_title,
        platform,
        product,
        device,
        username,
        state,
    ) = stream

    return (
        f"<b>Utilisateur:</b> {username}\n"
        f"<b>Média:</b> {media_title}\n"
        f"<b>Section:</b> {library_section}\n"
        f"<b>État:</b> {state}\n"
        f"<b>Appareil:</b> {device} ({platform})\n"
        f"<b>IP:</b> {ip_address}"
    )


def setup_logging():
    """Configurer le système de journalisation"""
    logs_dir = os.path.join(get_app_path(), "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    log_file = os.path.join(
        logs_dir, f"PlexPatrol_{datetime.now().strftime('%Y%m%d')}.log"
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
