import os
import time
import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
import requests
from PyQt5.QtCore import QThread, pyqtSignal
from utils import get_app_path
from data import PlexPatrolDB, load_stats, save_stats, update_user_stats


class StreamMonitor(QThread):
    """Thread qui surveille les flux Plex et arrête les streams non autorisés"""

    # Signaux pour communiquer avec l'interface graphique
    new_log = pyqtSignal(str, str)  # message, level
    sessions_updated = pyqtSignal(dict)  # user_streams dictionary
    connection_status = pyqtSignal(bool)  # is_connected

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.is_running = True
        self.is_paused = False
        self.known_sessions = {}
        self.last_poll_time = 0
        self.consecutive_errors = 0
        self.db = PlexPatrolDB()

        # Configurer le logger
        self.setup_logger()

    def setup_logger(self):
        """Configurer le logger pour ce module"""
        self.logger = logging.getLogger("stream_monitor")
        self.logger.setLevel(logging.INFO)

        # Créer le dossier de logs s'il n'existe pas
        logs_path = os.path.join(get_app_path(), "logs")
        if not os.path.exists(logs_path):
            os.makedirs(logs_path)

        # Handler pour les fichiers
        file_handler = logging.FileHandler(
            os.path.join(logs_path, "stream_monitor.log"), encoding="utf-8"
        )
        formatter = logging.Formatter("%(asctime)s - %(levellevel)s - %(message)s")
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def run(self):
        """Méthode principale exécutée par le thread"""
        self.new_log.emit("Démarrage de la surveillance des flux Plex", "INFO")

        while self.is_running:
            try:
                if not self.is_paused:
                    self.check_sessions()
                time.sleep(self.config["plex_server"].get("check_interval", 30))
            except Exception as e:
                self.logger.error(f"Erreur dans la boucle de surveillance: {str(e)}")
                self.new_log.emit(
                    f"Erreur dans la boucle de surveillance: {str(e)}", "ERROR"
                )
                # Augmenter le temps de pause après des erreurs consécutives
                self.consecutive_errors += 1
                time.sleep(min(60, self.consecutive_errors * 5))

        self.new_log.emit("Arrêt de la surveillance des flux Plex", "INFO")

    def check_sessions(self):
        """Vérifier les sessions Plex actives"""
        try:
            # Récupérer les sessions actives
            xml_data = self.get_active_sessions()
            if xml_data:
                self.connection_status.emit(True)
                self.consecutive_errors = 0

                # Parser les sessions
                user_streams = self.parse_sessions(xml_data)

                # Mettre à jour l'interface
                self.sessions_updated.emit(user_streams)

                # Vérifier les conditions d'arrêt
                self.check_stream_conditions(user_streams)

                # Mettre à jour l'heure du dernier sondage réussi
                self.last_poll_time = time.time()
            else:
                self.consecutive_errors += 1
                if self.consecutive_errors >= 3:
                    self.connection_status.emit(False)
                    self.new_log.emit(
                        "Impossible de se connecter au serveur Plex", "ERROR"
                    )

        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification des sessions: {str(e)}")
            self.new_log.emit(
                f"Erreur lors de la vérification des sessions: {str(e)}", "ERROR"
            )
            self.consecutive_errors += 1

            if self.consecutive_errors >= 3:
                self.connection_status.emit(False)

    def get_active_sessions(self):
        """Récupérer les sessions actives depuis le serveur Plex"""
        url = f'{self.config["plex_server"]["url"]}/status/sessions'
        headers = {"X-Plex-Token": self.config["plex_server"]["token"]}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.text
            else:
                self.logger.error(f"Erreur de requête: {response.status_code}")
                self.new_log.emit(f"Erreur de requête: {response.status_code}", "ERROR")
                return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erreur de connexion: {str(e)}")
            self.new_log.emit(f"Erreur de connexion au serveur Plex: {str(e)}", "ERROR")
            return None

    def parse_sessions(self, xml_data):
        """Parser les données XML des sessions Plex"""
        user_streams = {}

        try:
            root = ET.fromstring(xml_data)

            # Parcourir toutes les sessions vidéo
            for video in root.findall(".//Video"):
                # Récupérer les informations de base
                session_id = video.find(".//Session").get("id", "")
                grandparent_title = video.get("grandparentTitle", "")
                parent_title = video.get("parentTitle", "")
                title = video.get("title", "")

                # Construire le titre complet
                if grandparent_title and parent_title:
                    # Format série: "Série - S01E01 - Titre de l'épisode"
                    media_title = f"{grandparent_title} - {parent_title} - {title}"
                elif grandparent_title:
                    # Format série sans numéro d'épisode
                    media_title = f"{grandparent_title} - {title}"
                else:
                    # Format film
                    media_title = title

                # Récupérer la section/bibliothèque
                library_section = video.get("librarySectionTitle", "Inconnu")

                # Récupérer l'état (lecture, pause)
                state = video.find(".//Player").get("state", "unknown")

                # Récupérer les informations sur l'utilisateur
                user_elem = video.find(".//User")
                username = (
                    user_elem.get("title", "Inconnu")
                    if user_elem is not None
                    else "Inconnu"
                )
                user_id = user_elem.get("id", "0") if user_elem is not None else "0"

                # Récupérer les informations sur le player
                player_elem = video.find(".//Player")
                if player_elem is not None:
                    ip_address = player_elem.get("address", "Inconnu")
                    player_id = player_elem.get("machineIdentifier", "Inconnu")
                    platform = player_elem.get("platform", "Inconnu")
                    product = player_elem.get("product", "Inconnu")
                    device = player_elem.get("device", "Inconnu")
                else:
                    ip_address = player_id = platform = product = device = "Inconnu"

                # Stocker les informations dans le dictionnaire
                stream_info = (
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
                )

                if user_id not in user_streams:
                    user_streams[user_id] = []

                user_streams[user_id].append(stream_info)

                self.db.add_or_update_user(user_id, username)
                self.db.record_session(
                    user_id,
                    session_id,
                    platform,
                    device,
                    ip_address,
                    media_title,
                    library_section,
                )

            return user_streams

        except ET.ParseError as e:
            self.logger.error(f"Erreur lors du parsing XML: {str(e)}")
            self.new_log.emit(
                f"Erreur lors du parsing des données de session: {str(e)}", "ERROR"
            )
            return {}

    def check_stream_conditions(self, user_streams):
        """Vérifier les conditions des flux et arrêter ceux qui dépassent les limites"""
        # Obtenir les paramètres
        whitelist_ids = self.config.get("rules", {}).get("whitelist", [])
        max_streams = self.config.get("rules", {}).get("max_streams", 1)

        for user_id, streams in user_streams.items():
            # Vérifier si l'utilisateur est dans la liste blanche par ID
            if user_id in whitelist_ids:
                continue

            # Obtenir le nom d'utilisateur du premier stream pour les logs
            username = streams[0][8] if streams else "Inconnu"

            # Si l'utilisateur a plus de streams que autorisé
            if len(streams) > max_streams:
                self.logger.warning(
                    f"Utilisateur {username} dépasse la limite de {max_streams} flux"
                )
                self.new_log.emit(
                    f"Utilisateur {username} dépasse la limite: {len(streams)} flux actifs",
                    "WARNING",
                )

                # Trier les streams par état (arrêter d'abord ceux qui ne sont pas en lecture)
                sorted_streams = sorted(
                    streams,
                    key=lambda x: (
                        0 if x[9] == "playing" else (1 if x[9] == "paused" else 2)
                    ),
                )

                # Arrêter les streams excédentaires
                streams_to_stop = sorted_streams[max_streams:]
                for stream in streams_to_stop:
                    session_id = stream[0]
                    platform = stream[5]
                    success = self.stop_stream(user_id, username, session_id)

                    if success:
                        self.logger.info(f"Stream {session_id} arrêté pour {username}")
                        self.new_log.emit(
                            f"Stream arrêté pour {username} sur {platform}", "SUCCESS"
                        )

                        # Mettre à jour les statistiques
                        stats = load_stats()
                        stats = update_user_stats(
                            stats,
                            username,
                            stream_count=len(streams),
                            stream_killed=True,
                            platform=platform,
                        )
                        save_stats(stats)

    def stop_stream(self, user_id, username, session_id):
        """Arrêter un stream spécifique"""
        url = f'{self.config["plex_server"]["url"]}/status/sessions/terminate'
        params = {
            "sessionId": session_id,
            "reason": self.config["rules"].get(
                "termination_message", "Dépassement du nombre de flux autorisés"
            ),
        }
        headers = {"X-Plex-Token": self.config["plex_server"]["token"]}
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                self.db.mark_session_terminated(session_id)
                return True
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erreur lors de l'arrêt du stream: {str(e)}")
            return False

    def manual_stop_stream(self, user_id, username, session_id):
        """Arrêter manuellement un stream (depuis l'interface)"""
        return self.stop_stream(user_id, username, session_id)

    def update_user_stats(self, username, stream_count):
        """Mettre à jour les statistiques d'utilisation"""
        stats_path = os.path.join(get_app_path(), "stats.json")
        stats = {}

        # Charger les statistiques existantes
        if os.path.exists(stats_path):
            try:
                with open(stats_path, "r", encoding="utf-8") as f:
                    stats = json.load(f)
            except Exception as e:
                self.logger.error(
                    f"Erreur lors du chargement des statistiques: {str(e)}"
                )

        # Créer ou mettre à jour les statistiques pour cet utilisateur
        if username not in stats:
            stats[username] = {
                "total_sessions": 0,
                "kill_count": 0,
                "platforms": {},
                "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

        # Mettre à jour le nombre total de sessions
        stats[username]["total_sessions"] += stream_count
        stats[username]["last_seen"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Enregistrer les statistiques
        try:
            with open(stats_path, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            self.logger.error(
                f"Erreur lors de l'enregistrement des statistiques: {str(e)}"
            )

    def update_kill_stats(self, username, platform):
        """Mettre à jour les statistiques d'arrêt de flux"""
        stats_path = os.path.join(get_app_path(), "stats.json")
        stats = {}

        # Charger les statistiques existantes
        if os.path.exists(stats_path):
            try:
                with open(stats_path, "r", encoding="utf-8") as f:
                    stats = json.load(f)
            except Exception as e:
                self.logger.error(
                    f"Erreur lors du chargement des statistiques: {str(e)}"
                )

        # Créer ou mettre à jour les statistiques pour cet utilisateur
        if username not in stats:
            stats[username] = {
                "total_sessions": 0,
                "kill_count": 0,
                "platforms": {},
                "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

        # Mettre à jour les statistiques d'arrêt
        stats[username]["kill_count"] += 1
        stats[username]["last_kill"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Mettre à jour les statistiques par plateforme
        if "platforms" not in stats[username]:
            stats[username]["platforms"] = {}

        if platform not in stats[username]["platforms"]:
            stats[username]["platforms"][platform] = 0

        stats[username]["platforms"][platform] += 1

        # Enregistrer les statistiques
        try:
            with open(stats_path, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            self.logger.error(
                f"Erreur lors de l'enregistrement des statistiques: {str(e)}"
            )

    def toggle_pause(self):
        """Mettre en pause ou reprendre la surveillance"""
        self.is_paused = not self.is_paused

        if self.is_paused:
            self.new_log.emit("Surveillance mise en pause", "WARNING")
        else:
            self.new_log.emit("Surveillance reprise", "INFO")

        return self.is_paused

    def stop(self):
        """Arrêter le thread proprement"""
        self.is_running = False
        self.wait()
