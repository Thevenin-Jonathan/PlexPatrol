import os
import sqlite3
import time
import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
import requests
from PyQt5.QtCore import QThread, pyqtSignal
from utils import get_app_path
from data import PlexPatrolDB
from utils.constants import LogMessages, UIMessages


class StreamMonitor(QThread):
    """Thread qui surveille les flux Plex et arrête les streams non autorisés"""

    # Signaux pour communiquer avec l'interface graphique
    new_log = pyqtSignal(str, str)  # message, level
    sessions_updated = pyqtSignal(dict)  # user_streams dictionary
    connection_status = pyqtSignal(bool)  # is_connected

    def __init__(self):
        super().__init__()
        from config.config_manager import config

        self.config = config
        self.is_running = True
        self.is_paused = False
        self.known_sessions = {}
        self.last_poll_time = 0
        self.consecutive_errors = 0
        self.db = PlexPatrolDB()

        # Ajouter l'import des notifications
        from utils.notification import send_telegram_notification

        self.send_telegram = send_telegram_notification

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
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def run(self):
        """Démarrer la surveillance des flux Plex en arrière-plan"""
        self.is_running = True
        self.new_log.emit(LogMessages.MONITOR_START, "INFO")

        while self.is_running:
            try:
                if not self.is_paused:
                    self.check_sessions()
                time.sleep(self.config.check_interval)
            except Exception as e:
                self.logger.error(f"Erreur dans la boucle de surveillance: {str(e)}")
                self.new_log.emit(
                    f"Erreur dans la boucle de surveillance: {str(e)}", "ERROR"
                )
                # Augmenter le temps de pause après des erreurs consécutives
                self.consecutive_errors += 1
                time.sleep(min(60, self.consecutive_errors * 5))

        self.new_log.emit("Arrêt de la surveillance des flux Plex", "INFO")

    def stop(self):
        """Arrêter le thread de surveillance proprement"""
        self.is_running = False

        # Réveiller le thread s'il est en attente dans sleep()
        self.wait(100)  # Attendre un peu pour laisser le thread se terminer

    def check_sessions(self):
        """Vérifier les sessions actives et agir si nécessaire"""
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
            self.new_log.emit(LogMessages.SESSION_ERROR.format(error=str(e)), "ERROR")
            self.consecutive_errors += 1

            if self.consecutive_errors >= 3:
                self.connection_status.emit(False)

    def get_active_sessions(self):
        """Récupérer les sessions actives depuis le serveur Plex"""
        url = f"{self.config.plex_server_url}/status/sessions"
        headers = {"X-Plex-Token": self.config.plex_token}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200 and response.text:
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
                try:
                    # Récupérer les informations de base
                    session_elem = video.find(".//Session")
                    if session_elem is None:
                        # Ignorer les streams sans session ID
                        continue

                    session_id = session_elem.get("id", "")
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

                    # Récupérer les informations sur le player
                    player_elem = video.find(".//Player")
                    if player_elem is None:
                        # Ignorer les streams sans information de lecteur
                        continue

                    # Récupérer l'état (lecture, pause)
                    state = player_elem.get("state", "unknown")
                    ip_address = player_elem.get("address", "Inconnu")
                    player_id = player_elem.get("machineIdentifier", "Inconnu")
                    platform = player_elem.get("platform", "Inconnu")
                    product = player_elem.get("product", "Inconnu")
                    device = player_elem.get("device", "Inconnu")

                    # Récupérer les informations sur l'utilisateur
                    user_elem = video.find(".//User")
                    if user_elem is None:
                        # Utiliser des valeurs par défaut si l'utilisateur n'est pas trouvé
                        username = "Inconnu"
                        user_id = "0"
                    else:
                        username = user_elem.get("title", "Inconnu")
                        user_id = user_elem.get("id", "0")

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
                except Exception as inner_e:
                    # Capturer les erreurs spécifiques à un stream pour ne pas interrompre le traitement
                    self.logger.error(
                        f"Erreur lors du traitement d'un stream: {str(inner_e)}"
                    )
                    # Continuer avec le stream suivant

            return user_streams

        except ET.ParseError as e:
            self.logger.error(f"Erreur lors du parsing XML: {str(e)}")
            self.new_log.emit(
                f"Erreur lors du parsing des données de session: {str(e)}", "ERROR"
            )
            return {}

    def check_stream_conditions(self, user_streams):
        """
        Vérifier les conditions des flux et arrêter ceux qui dépassent les limites
        """
        for user_id, streams in user_streams.items():
            # Obtenir le nom d'utilisateur du premier stream pour les logs
            username = streams[0][8] if streams else "Inconnu"

            # Vérifier si le compte est désactivé
            if self.db.is_user_disabled(user_id):
                self.logger.warning(
                    f"Tentative de lecture sur compte désactivé : {username}"
                )

                # Récupérer les informations du premier stream pour la notification
                stream = streams[0]
                title = stream[4]  # media_title
                platform = stream[5]  # platform
                ip = stream[1]  # ip_address

                # Envoyer une notification Telegram
                notification = UIMessages.DISABLED_USER_ATTEMPT.format(
                    username=username, title=title, platform=platform, ip=ip
                )
                self.send_telegram(notification)

                # Ajouter ce log pour l'interface
                self.new_log.emit(
                    f"Tentative de lecture détectée sur compte désactivé : {username}",
                    "WARNING",
                )

                # Arrêter tous les streams avec le message spécifique
                for stream in streams:
                    session_id = stream[0]
                    self.stop_stream_with_message(
                        user_id,
                        username,
                        session_id,
                        UIMessages.ACCOUNT_DISABLED_MESSAGE,
                    )

                continue  # Passer à l'utilisateur suivant

            # Récupérer la limite personnalisée de l'utilisateur
            max_streams = self.db.get_user_max_streams(user_id)
            if max_streams is None:
                continue  # Pas de limite définie pour cet utilisateur

            # Nombre total de flux pour cet utilisateur (unique par appareil + IP)
            unique_streams = {}

            # Séparation des flux par état
            paused_streams = []
            playing_streams = []
            other_streams = []

            for stream in streams:
                session_id = stream[0]
                ip_address = stream[1]
                player_id = stream[2]
                state = stream[9]  # état du stream (playing, paused, etc.)

                # Créer une clé unique basée sur l'ID de l'appareil et l'adresse IP
                stream_key = f"{player_id}_{ip_address}"

                # Ajouter à notre dictionnaire pour compter les flux uniques
                unique_streams[stream_key] = stream

                # Classifier selon l'état
                if state == "playing":
                    playing_streams.append(stream)
                elif state == "paused":
                    paused_streams.append(stream)
                else:
                    other_streams.append(stream)

            # Nombre total de flux uniques
            stream_count = len(unique_streams)

            # Vérifier si l'utilisateur dépasse sa limite
            if stream_count > max_streams:
                self.logger.warning(
                    f"Utilisateur {username} dépasse la limite: {stream_count} flux actifs (max: {max_streams})"
                )
                self.new_log.emit(
                    f"Utilisateur {username} dépasse la limite: {stream_count} flux actifs (max: {max_streams})",
                    "WARNING",
                )

                # Initialiser la liste des flux à arrêter
                streams_to_stop = []

                # 1. Prendre d'abord les flux en pause
                if paused_streams:
                    # Calculer combien de flux en pause on doit arrêter
                    streams_to_stop_count = stream_count - max_streams
                    paused_to_stop = min(streams_to_stop_count, len(paused_streams))
                    streams_to_stop.extend(paused_streams[:paused_to_stop])

                    self.logger.info(
                        f"Arrêt de {paused_to_stop} flux en pause pour {username}"
                    )

                # 2. Si on a encore besoin d'arrêter des flux, prendre ceux en lecture
                else:
                    # Cas où tous les flux sont en lecture: les arrêter TOUS
                    self.logger.info(
                        f"Tous les flux sont en lecture - Arrêt de TOUS les flux ({len(playing_streams)}) pour {username}"
                    )
                    streams_to_stop.extend(
                        playing_streams
                    )  # Ajouter tous les flux en lecture
                    streams_to_stop.extend(
                        other_streams
                    )  # Ajouter également tous les autres flux

                # Arrêter les flux sélectionnés
                self.stop_sessions(streams_to_stop, user_id, username, streams)

    def stop_sessions(self, sessions_to_stop, user_id, username, all_streams):
        """
        Arrêter les sessions spécifiées et mettre à jour les statistiques

        Args:
            sessions_to_stop: Liste des sessions à arrêter
            user_id: ID de l'utilisateur
            username: Nom d'utilisateur
            all_streams: Toutes les sessions de l'utilisateur pour les statistiques
        """
        for stream in sessions_to_stop:
            session_id = stream[0]
            platform = stream[5]
            device = stream[7]
            state = stream[9]

            self.logger.info(
                f"Tentative d'arrêt du flux {session_id} ({platform}/{device}, état: {state}) pour {username}"
            )

            success = self.stop_stream(user_id, username, session_id, state)

            if success:
                self.logger.info(f"Stream {session_id} arrêté pour {username}")
                # Utiliser un message différent selon l'état du flux
                if state == "playing":
                    log_message = LogMessages.STREAM_STOPPED_PLAYING.format(
                        username=username, platform=platform, device=device
                    )
                elif state == "paused":
                    log_message = LogMessages.STREAM_STOPPED_PAUSED.format(
                        username=username, platform=platform, device=device
                    )
                else:
                    log_message = LogMessages.STREAM_STOPPED_OTHER.format(
                        username=username, platform=platform, device=device, state=state
                    )

                self.new_log.emit(log_message, "SUCCESS")

                # Mettre à jour les statistiques directement en base de données
                self.db.record_stream_termination(user_id, username, platform)
            else:
                self.logger.warning(
                    f"Échec de l'arrêt du flux {session_id} pour {username}"
                )
                self.new_log.emit(
                    LogMessages.STREAM_STOP_FAILED.format(
                        username=username, platform=platform
                    ),
                    "ERROR",
                )

    def stop_stream(self, user_id, username, session_id, state="playing"):
        """
        Arrêter un stream spécifique avec un message adapté à l'état du flux

        Args:
            user_id: ID de l'utilisateur
            username: Nom de l'utilisateur
            session_id: ID de la session à arrêter
            state: État du flux (playing, paused, etc.)
        """
        url = f"{self.config.plex_server_url}/status/sessions/terminate"

        # Sélectionner le message en fonction de l'état du flux
        if state == "paused":
            reason = UIMessages.TERMINATION_MESSAGE_PAUSED
        elif state == "playing":
            reason = UIMessages.TERMINATION_MESSAGE_PLAYING
        else:
            reason = self.config.termination_message  # Message par défaut

        params = {"sessionId": session_id, "reason": reason}
        headers = {"X-Plex-Token": self.config.plex_token}

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                self.db.mark_session_terminated(session_id)
                return True
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erreur lors de l'arrêt du stream: {str(e)}")
            return False

    def stop_stream_with_message(self, user_id, username, session_id, custom_message):
        """
        Arrêter un stream spécifique avec un message personnalisé

        Args:
            user_id: ID de l'utilisateur
            username: Nom de l'utilisateur
            session_id: ID de la session à arrêter
            custom_message: Message personnalisé à afficher
        """
        url = f"{self.config.plex_server_url}/status/sessions/terminate"

        params = {"sessionId": session_id, "reason": custom_message}
        headers = {"X-Plex-Token": self.config.plex_token}

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                self.db.mark_session_terminated(session_id)

                # Récupérer les informations sur le flux depuis la base de données
                session_info = self.db.get_session_info(session_id)

                platform = "Inconnu"
                if session_info:
                    platform = session_info.get("platform", "Inconnu")

                # Enregistrer la terminaison pour les statistiques
                self.db.record_stream_termination(user_id, username, platform)

                # Ajouter ces lignes pour les logs d'interface
                self.logger.info(
                    f"Stream {session_id} arrêté pour {username} (compte désactivé)"
                )
                self.new_log.emit(
                    f"Stream arrêté pour {username} (compte désactivé)", "SUCCESS"
                )

                return True
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erreur lors de l'arrêt du stream: {str(e)}")
            return False

    def manual_stop_stream(self, user_id, username, session_id, state="playing"):
        """Arrêter manuellement un stream (depuis l'interface)"""
        return self.stop_stream(user_id, username, session_id, state)

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
