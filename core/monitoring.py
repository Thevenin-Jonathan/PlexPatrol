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

    def __init__(self, db_instance=None):
        super().__init__()
        from config.config_manager import config

        self.config = config
        self.is_running = True
        self.is_paused = False
        self.known_sessions = {}
        self.last_poll_time = 0
        self.consecutive_errors = 0
        self.db = db_instance if db_instance is not None else PlexPatrolDB()

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

        cleanup_counter = 0  # Pour nettoyer périodiquement les sessions

        while self.is_running:
            try:
                if not self.is_paused:
                    self.check_sessions()

                    # Nettoyage périodique toutes les 10 vérifications
                    cleanup_counter += 1
                    if cleanup_counter >= 10:
                        self.cleanup_expired_sessions()
                        cleanup_counter = 0

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
                error_message = "Impossible de récupérer les sessions actives"
                if self.consecutive_errors >= 3:
                    self.connection_status.emit(False)
                    self.new_log.emit(
                        f"{error_message} (tentative {self.consecutive_errors})",
                        "ERROR",
                    )

                    # Tentative de reconnexion
                    if self.consecutive_errors % 5 == 0:  # Toutes les 5 erreurs
                        if (
                            self.reconnect_to_plex()
                        ):  # Utilisation de la nouvelle méthode
                            self.consecutive_errors = 0
                        else:
                            # Si la reconnexion échoue, augmenter le délai avant la prochaine tentative
                            time.sleep(min(60, self.consecutive_errors))
                else:
                    self.new_log.emit(error_message, "WARNING")

        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification des sessions: {str(e)}")
            self.new_log.emit(LogMessages.SESSION_ERROR.format(error=str(e)), "ERROR")
            self.consecutive_errors += 1

            if self.consecutive_errors >= 3:
                self.connection_status.emit(False)

    def cleanup_expired_sessions(self):
        """Nettoie les sessions expirées de la base de données"""
        try:
            # Considérer une session comme expirée après 30 minutes d'inactivité
            expiration_minutes = 30
            cleaned_count = self.db.cleanup_expired_sessions(expiration_minutes)

            if cleaned_count > 0:
                self.logger.info(
                    f"{cleaned_count} sessions expirées nettoyées de la base de données"
                )
                self.new_log.emit(
                    f"{cleaned_count} anciennes sessions nettoyées", "INFO"
                )

            return cleaned_count

        except Exception as e:
            self.logger.error(
                f"Erreur lors du nettoyage des sessions expirées: {str(e)}"
            )
            return 0

    def test_connection(self):
        """Test si la connexion au serveur Plex est active et fonctionnelle"""
        url = f"{self.config.plex_server_url}/status/sessions"
        headers = {"X-Plex-Token": self.config.plex_token}

        try:
            start_time = time.time()
            response = requests.get(url, headers=headers, timeout=5)
            response_time = time.time() - start_time

            if response.status_code == 200:
                self.logger.debug(
                    f"Connexion au serveur Plex réussie (temps: {response_time:.2f}s)"
                )
                return True
            elif response.status_code == 401:
                self.logger.error(
                    "Erreur d'authentification au serveur Plex (token invalide)"
                )
                self.new_log.emit(
                    "Erreur d'authentification au serveur Plex. Vérifiez votre token.",
                    "ERROR",
                )
                return False
            else:
                self.logger.error(
                    f"Échec de la connexion au serveur Plex: code HTTP {response.status_code}"
                )
                return False
        except requests.exceptions.Timeout:
            self.logger.error(
                "Délai d'attente dépassé lors de la connexion au serveur Plex"
            )
            return False
        except requests.exceptions.ConnectionError:
            self.logger.error("Erreur de connexion au serveur Plex")
            return False
        except Exception as e:
            self.logger.error(
                f"Erreur lors du test de connexion au serveur Plex: {str(e)}"
            )
            return False

    def reconnect_to_plex(self):
        """Tente de rétablir la connexion au serveur Plex de manière robuste"""
        self.new_log.emit("Tentative de reconnexion au serveur Plex...", "INFO")

        # Réinitialisation des ressources de connexion
        try:
            # Tenter la reconnexion
            url = f"{self.config.plex_server_url}/status/sessions"
            headers = {"X-Plex-Token": self.config.plex_token}

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                self.consecutive_errors = 0
                self.connection_status.emit(True)
                self.new_log.emit("Reconnexion réussie au serveur Plex", "SUCCESS")
                return True
            else:
                self.new_log.emit(
                    f"Échec de la reconnexion: code HTTP {response.status_code}",
                    "ERROR",
                )
                return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erreur lors de la tentative de reconnexion: {str(e)}")
            self.new_log.emit(f"Échec de la reconnexion: {str(e)}", "ERROR")
            return False

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
        # Variables pour construire un message Telegram pour tous les streams arrêtés
        successful_stops = 0
        telegram_message_parts = [f"🛑 <b>Streams arrêtés !</b>"]
        telegram_message_parts.append(f"👤 <b>Utilisateur</b>: {username}")
        telegram_message_parts.append(
            f"🔢 <b>Nombre de streams</b>: {len(sessions_to_stop)}"
        )

        for stream in sessions_to_stop:
            session_id = stream[0]
            platform = stream[5]
            device = stream[7]
            state = stream[9]
            media_title = stream[4]  # Titre du média en cours de lecture

            self.logger.info(
                f"Tentative d'arrêt du flux {session_id} ({platform}/{device}, état: {state}) pour {username}"
            )

            success = self.stop_stream(user_id, username, session_id, state)

            if success:
                successful_stops += 1
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

                # Ajouter les détails de ce stream au message Telegram
                stream_details = f"\n\n📺 <b>Stream #{successful_stops}</b>"
                stream_details += f"\n<b>Contenu</b>: {media_title}"
                stream_details += f"\n<b>Plateforme</b>: {platform}"
                stream_details += f"\n<b>Appareil</b>: {device}"
                stream_details += f"\n<b>État</b>: {state}"
                telegram_message_parts.append(stream_details)

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

        # Si des streams ont été arrêtés avec succès, envoyer une notification Telegram
        if successful_stops > 0:
            reason_msg = f"\n\n📝 <b>Raison</b>: Dépassement de limite ({len(all_streams)} streams actifs, maximum autorisé: {self.db.get_user_max_streams(user_id)})"
            telegram_message_parts.append(reason_msg)

            # Joindre toutes les parties du message
            full_telegram_message = "\n".join(telegram_message_parts)

            # Envoyer la notification Telegram
            try:
                self.send_telegram(full_telegram_message)
                self.logger.info(
                    f"Notification Telegram envoyée pour l'arrêt de {successful_stops} streams de {username}"
                )
            except Exception as e:
                self.logger.error(
                    f"Erreur lors de l'envoi de la notification Telegram: {str(e)}"
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

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                response = requests.get(url, params=params, headers=headers, timeout=10)
                if response.status_code == 200:
                    self.db.mark_session_terminated(session_id)
                    self.logger.info(
                        f"Stream {session_id} de l'utilisateur {username} arrêté avec succès"
                    )
                    return True
                else:
                    self.logger.warning(
                        f"Échec de l'arrêt du stream {session_id}: HTTP {response.status_code}"
                    )
                    retry_count += 1
                    time.sleep(1)  # Attente avant nouvelle tentative
            except requests.exceptions.Timeout:
                self.logger.warning(
                    f"Délai d'attente dépassé lors de l'arrêt du stream {session_id}"
                )
                retry_count += 1
                time.sleep(2)  # Attente plus longue en cas de timeout
            except requests.exceptions.ConnectionError:
                self.logger.error(
                    f"Erreur de connexion lors de l'arrêt du stream {session_id}"
                )
                retry_count += 1
                time.sleep(2)
            except Exception as e:
                self.logger.error(
                    f"Erreur inattendue lors de l'arrêt du stream {session_id}: {str(e)}"
                )
                return False

        # Si on arrive ici, c'est que toutes les tentatives ont échoué
        self.logger.error(
            f"Impossible d'arrêter le stream {session_id} après {max_retries} tentatives"
        )
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

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
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
                        f"Stream {session_id} arrêté pour {username} avec message: '{custom_message}'"
                    )
                    self.new_log.emit(
                        f"Stream arrêté pour {username} avec message personnalisé",
                        "SUCCESS",
                    )

                    return True

                self.logger.warning(
                    f"Échec de l'arrêt du stream {session_id}: HTTP {response.status_code}"
                )
                retry_count += 1
                time.sleep(1)  # Attente avant nouvelle tentative

            except requests.exceptions.Timeout:
                self.logger.warning(
                    f"Délai d'attente dépassé lors de l'arrêt du stream {session_id}"
                )
                retry_count += 1
                time.sleep(2)  # Attente plus longue en cas de timeout

            except requests.exceptions.ConnectionError:
                self.logger.error(
                    f"Erreur de connexion lors de l'arrêt du stream {session_id}"
                )
                retry_count += 1
                time.sleep(2)

            except Exception as e:
                self.logger.error(
                    f"Erreur inattendue lors de l'arrêt du stream {session_id}: {str(e)}"
                )
                return False

        # Si on arrive ici, c'est que toutes les tentatives ont échoué
        self.logger.error(
            f"Impossible d'arrêter le stream {session_id} après {max_retries} tentatives"
        )
        self.new_log.emit(
            f"Échec de l'arrêt du flux pour {username} après plusieurs tentatives",
            "ERROR",
        )
        return False

    def update_user_stats(self, user_id, streams):
        """
        Met à jour les statistiques d'utilisation pour un utilisateur

        Args:
            user_id: ID de l'utilisateur dans la base de données
            streams: Liste des streams actifs pour cet utilisateur
        """
        try:
            if not streams:  # Rien à faire si pas de streams
                return True

            # Vérifier si user_id est valide
            if not user_id:
                self.logger.warning(
                    "Tentative de mise à jour des statistiques avec un ID utilisateur invalide"
                )
                return False

            # Utiliser un contexte `with` pour gérer la connexion et s'assurer qu'elle est fermée
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()

                # Vérifier que l'utilisateur existe
                cursor.execute("SELECT 1 FROM plex_users WHERE id = ?", (user_id,))
                if not cursor.fetchone():
                    self.logger.warning(
                        f"Utilisateur ID {user_id} introuvable dans la base de données"
                    )
                    # Créer l'utilisateur avec des informations minimales
                    try:
                        username = (
                            streams[0][8]
                            if streams and len(streams[0]) > 8
                            else "Inconnu"
                        )
                        cursor.execute(
                            "INSERT INTO plex_users (id, username) VALUES (?, ?)",
                            (user_id, username),
                        )
                        self.logger.info(
                            f"Utilisateur {username} (ID: {user_id}) créé automatiquement"
                        )
                    except Exception as user_create_error:
                        self.logger.error(
                            f"Impossible de créer l'utilisateur: {str(user_create_error)}"
                        )
                        return False

                # Mettre à jour last_seen pour l'utilisateur
                cursor.execute(
                    """
                    UPDATE plex_users 
                    SET last_seen = datetime('now')
                    WHERE id = ?
                    """,
                    (user_id,),
                )

                # Mettre à jour le nombre total de sessions
                cursor.execute(
                    """
                    UPDATE plex_users 
                    SET total_sessions = COALESCE(total_sessions, 0) + ?
                    WHERE id = ?
                    """,
                    (len(streams), user_id),
                )

                # Enregistrer les statistiques par plateforme
                for stream in streams:
                    try:
                        # Vérifier que le stream contient suffisamment d'éléments
                        if len(stream) <= 5:
                            self.logger.warning(
                                f"Stream avec structure invalide ignoré: {stream}"
                            )
                            continue

                        platform = stream[
                            5
                        ]  # Plateforme (index 5 dans le tuple de stream)

                        # S'assurer que la plateforme n'est pas None ou vide
                        if not platform:
                            platform = "Inconnu"

                        # Vérifier si cette plateforme existe déjà pour cet utilisateur
                        cursor.execute(
                            """
                            SELECT count
                            FROM platform_stats
                            WHERE user_id = ? AND platform = ?
                            """,
                            (user_id, platform),
                        )
                        result = cursor.fetchone()

                        if result:
                            # Mettre à jour le compteur existant
                            cursor.execute(
                                """
                                UPDATE platform_stats
                                SET count = count + 1
                                WHERE user_id = ? AND platform = ?
                                """,
                                (user_id, platform),
                            )
                        else:
                            # Vérifier si la table platform_stats existe
                            cursor.execute(
                                "SELECT name FROM sqlite_master WHERE type='table' AND name='platform_stats'"
                            )
                            if not cursor.fetchone():
                                # Créer la table si elle n'existe pas
                                cursor.execute(
                                    """
                                    CREATE TABLE platform_stats (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        user_id TEXT NOT NULL,
                                        platform TEXT NOT NULL,
                                        count INTEGER DEFAULT 0,
                                        UNIQUE(user_id, platform)
                                    )
                                """
                                )
                                self.logger.info(
                                    "Table platform_stats créée automatiquement"
                                )

                            # Créer un nouveau compteur pour cette plateforme
                            cursor.execute(
                                """
                                INSERT INTO platform_stats (user_id, platform, count)
                                VALUES (?, ?, 1)
                                """,
                                (user_id, platform),
                            )
                    except Exception as stream_error:
                        # Capturer les erreurs par stream pour ne pas bloquer les autres
                        self.logger.error(
                            f"Erreur lors du traitement des stats du stream: {str(stream_error)}"
                        )
                        continue

                # Le commit est automatiquement fait par le with statement
                return True

        except sqlite3.Error as sql_error:
            self.logger.error(
                f"Erreur SQL lors de la mise à jour des statistiques: {str(sql_error)}"
            )
            return False
        except Exception as e:
            self.logger.error(
                f"Erreur lors de la mise à jour des statistiques: {str(e)}"
            )
            return False

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
