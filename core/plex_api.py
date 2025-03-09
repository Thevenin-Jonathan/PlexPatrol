import logging
import requests
import xml.etree.ElementTree as ET


class PlexAPI:
    """Interface pour interagir avec l'API Plex"""

    def __init__(self, server_url, token):
        self.server_url = server_url
        self.token = token
        self.headers = {"X-Plex-Token": token}

    def get_active_sessions(self):
        """Récupérer les sessions actives depuis le serveur Plex"""
        url = f"{self.server_url}/status/sessions"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.content
            else:
                logging.error(
                    f"Erreur lors de la récupération des sessions: HTTP {response.status_code}"
                )
                return None
        except requests.exceptions.Timeout:
            logging.error(
                "Délai d'attente dépassé lors de la connexion au serveur Plex"
            )
            return None
        except requests.exceptions.ConnectionError:
            logging.error("Erreur de connexion au serveur Plex")
            return None
        except Exception as e:
            logging.error(
                f"Erreur inattendue lors de la récupération des sessions: {str(e)}"
            )
            return None

    def stop_stream(self, session_id, reason="Dépassement du nombre de flux autorisés"):
        """Arrêter un stream spécifique"""
        url = f"{self.server_url}/status/sessions/terminate"
        params = {
            "sessionId": session_id,
            "reason": reason,
        }

        try:
            response = requests.get(
                url, params=params, headers=self.headers, timeout=10
            )
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logging.error(f"Erreur lors de l'arrêt du stream: {str(e)}")
            return False

    def get_users(self):
        """Récupère la liste des utilisateurs Plex avec leurs IDs"""
        url = f"{self.server_url}/accounts"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
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
            logging.error(
                f"Exception lors de la récupération des utilisateurs: {str(e)}"
            )
            return {}

    def test_connection(self):
        """Tester la connexion au serveur Plex"""
        url = f"{self.server_url}/status/sessions"

        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            return response.status_code == 200
        except Exception:
            return False


def get_plex_users():
    """
    Récupère la liste des utilisateurs Plex avec leurs IDs

    Returns:
        dict: Dictionnaire {user_id: username} des utilisateurs
    """
    from config.config_manager import config

    # Utiliser la classe PlexAPI pour éviter la duplication de code
    plex_api = PlexAPI(config.plex_server_url, config.plex_token)
    return plex_api.get_users()
