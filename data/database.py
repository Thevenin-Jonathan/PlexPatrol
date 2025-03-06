import sqlite3
import os
import logging
from datetime import datetime, time
from utils import get_app_path
from utils.constants import LogMessages, Paths


class PlexPatrolDB:
    def __init__(self):
        # Créer le dossier data s'il n'existe pas déjà
        data_dir = os.path.join(get_app_path(), Paths.DATA)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        # Utiliser le chemin dans le dossier data
        self.db_path = os.path.join(data_dir, Paths.DATABASE)
        self.initialize_db()

    def initialize_db(self):
        """Initialiser la structure de la base de données"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Table des utilisateurs Plex
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS plex_users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                is_whitelisted INTEGER DEFAULT 0,
                is_disabled INTEGER DEFAULT 0,
                max_streams INTEGER DEFAULT 2,
                notes TEXT,
                last_seen TEXT
            )
            """
            )

            # Table des sessions
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                session_id TEXT UNIQUE,
                start_time TEXT,
                end_time TEXT,
                platform TEXT,
                device TEXT,
                ip_address TEXT,
                media_title TEXT,
                library_section TEXT,
                was_terminated INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES plex_users(id)
            )
            """
            )

            # Créer la table de configuration
            self.create_config_table(conn)

            conn.commit()
            conn.close()

            logging.info(LogMessages.DB_INITIALIZED)
            return True
        except Exception as e:
            logging.error(LogMessages.DB_ERROR.format(error=str(e)))
            return False

    def create_config_table(self, conn):
        """Crée la table de configuration si elle n'existe pas"""
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

    def add_or_update_user(
        self,
        user_id,
        username,
        email=None,
        phone=None,
        is_whitelisted=None,
        is_disabled=None,
        max_streams=None,
        notes=None,
    ):
        """Ajouter ou mettre à jour un utilisateur dans la base de données"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Vérifier si l'utilisateur existe déjà
            cursor.execute(
                "SELECT id, is_whitelisted, is_disabled, max_streams FROM plex_users WHERE id = ?",
                (user_id,),
            )
            existing_user = cursor.fetchone()

            if existing_user:
                # Ne pas écraser les valeurs existantes sauf si explicitement spécifiées
                if is_whitelisted is None:
                    is_whitelisted = existing_user[1]  # Utiliser la valeur existante

                if is_disabled is None:
                    is_disabled = existing_user[2]  # Utiliser la valeur existante

                if max_streams is None:
                    max_streams = existing_user[3]  # Utiliser la valeur existante

                # Mise à jour
                cursor.execute(
                    """
                    UPDATE plex_users 
                    SET username = ?, email = ?, phone = ?, is_whitelisted = ?, is_disabled = ?, 
                        max_streams = ?, notes = ?, last_seen = ? 
                    WHERE id = ?
                    """,
                    (
                        username,
                        email,
                        phone,
                        is_whitelisted,
                        is_disabled,
                        max_streams,
                        notes,
                        datetime.now().isoformat(),
                        user_id,
                    ),
                )
            else:
                # Insertion d'un nouvel utilisateur
                # Valeurs par défaut
                if is_whitelisted is None:
                    is_whitelisted = 0

                if is_disabled is None:
                    is_disabled = 0

                if max_streams is None:
                    max_streams = 2

                cursor.execute(
                    """
                    INSERT INTO plex_users (id, username, email, phone, is_whitelisted, is_disabled, max_streams, notes, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        username,
                        email,
                        phone,
                        is_whitelisted,
                        is_disabled,
                        max_streams,
                        notes,
                        datetime.now().isoformat(),
                    ),
                )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(
                f"Erreur lors de l'ajout/mise à jour de l'utilisateur: {str(e)}"
            )
            return False

    def get_all_users(self):
        """Récupère tous les utilisateurs de la base de données, avec ou sans statistiques"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Récupérer tous les utilisateurs avec statistiques (si disponibles)
            cursor.execute(
                """
            SELECT 
                u.*,
                COALESCE(COUNT(s.id), 0) AS total_sessions,
                COALESCE(SUM(CASE WHEN s.was_terminated = 1 THEN 1 ELSE 0 END), 0) AS terminated_sessions
            FROM plex_users u
            LEFT JOIN sessions s ON u.id = s.user_id
            GROUP BY u.id
            """
            )

            results = [dict(row) for row in cursor.fetchall()]

            # Pour chaque utilisateur, déterminer la plateforme principale
            for user in results:
                cursor.execute(
                    """
                SELECT platform, COUNT(*) AS count
                FROM sessions
                WHERE user_id = ?
                GROUP BY platform
                ORDER BY count DESC
                LIMIT 1
                """,
                    (user["id"],),
                )

                platform_data = cursor.fetchone()
                if platform_data:
                    user["main_platform"] = dict(platform_data)["platform"]
                else:
                    user["main_platform"] = "Inconnue"

            conn.close()
            return results
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des utilisateurs: {str(e)}")
            return []

    def delete_user(self, username):
        """Supprimer un utilisateur de la base de données"""
        try:
            # Créer une connexion et un curseur comme dans les autres méthodes
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Exécuter la requête sur la table correcte (plex_users, pas users)
            cursor.execute("DELETE FROM plex_users WHERE username = ?", (username,))

            # Commit et fermeture
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erreur lors de la suppression de l'utilisateur: {str(e)}")
            return False

    def get_user_max_streams(self, user_id):
        """
        Récupère la limite de flux maximale pour un utilisateur spécifique

        Args:
            user_id (str): ID de l'utilisateur Plex

        Returns:
            int|None: Limite de flux max si définie, None sinon
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Récupérer la limite de flux maximale pour cet utilisateur
            cursor.execute(
                "SELECT max_streams FROM plex_users WHERE id = ?", (user_id,)
            )

            result = cursor.fetchone()
            conn.close()

            # Si une limite est définie, la retourner, sinon retourner None
            if result and result[0] is not None:
                return int(result[0])
            return None
        except Exception as e:
            logging.error(
                f"Erreur lors de la récupération de la limite de flux: {str(e)}"
            )
            return None

    def is_user_whitelisted(self, user_id):
        """
        Vérifie si un utilisateur est en liste blanche dans la base de données

        Args:
            user_id (str): ID de l'utilisateur Plex

        Returns:
            bool: True si l'utilisateur est en liste blanche, False sinon
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Vérifier si l'utilisateur a is_whitelisted=1
            cursor.execute(
                "SELECT is_whitelisted FROM plex_users WHERE id = ?", (user_id,)
            )

            result = cursor.fetchone()
            conn.close()

            if result and result[0] == 1:
                return True
            return False
        except Exception as e:
            logging.error(
                f"Erreur lors de la vérification de la liste blanche: {str(e)}"
            )
            return False

    def set_user_whitelist_status(self, user_id, is_whitelisted):
        """
        Définit le statut whitelist d'un utilisateur

        Args:
            user_id (str): ID de l'utilisateur Plex
            is_whitelisted (bool): True pour ajouter à la whitelist, False sinon

        Returns:
            bool: True si réussi, False sinon
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            whitelist_value = 1 if is_whitelisted else 0

            cursor.execute(
                "UPDATE plex_users SET is_whitelisted = ? WHERE id = ?",
                (whitelist_value, user_id),
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(
                f"Erreur lors de la mise à jour du statut whitelist: {str(e)}"
            )
            return False

    def record_session(
        self,
        user_id,
        session_id,
        platform,
        device,
        ip_address,
        media_title,
        library_section,
    ):
        """Enregistrer une nouvelle session"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now().isoformat()

            # Vérifier si l'utilisateur existe, sinon le créer
            cursor.execute("SELECT id FROM plex_users WHERE id = ?", (user_id,))
            if not cursor.fetchone():
                cursor.execute(
                    """
                INSERT INTO plex_users (id, username, last_seen)
                VALUES (?, ?, ?)
                """,
                    (user_id, f"Utilisateur {user_id[:8]}", now),
                )

            # Vérifier si la session existe déjà
            cursor.execute(
                "SELECT session_id FROM sessions WHERE session_id = ?", (session_id,)
            )
            if cursor.fetchone():
                # Mettre à jour la session existante
                cursor.execute(
                    """
                UPDATE sessions 
                SET platform = ?, device = ?, ip_address = ?, media_title = ?, library_section = ?
                WHERE session_id = ?
                """,
                    (
                        platform,
                        device,
                        ip_address,
                        media_title,
                        library_section,
                        session_id,
                    ),
                )
            else:
                # Insérer une nouvelle session
                cursor.execute(
                    """
                INSERT INTO sessions 
                (user_id, session_id, start_time, platform, device, ip_address, media_title, library_section)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        user_id,
                        session_id,
                        now,
                        platform,
                        device,
                        ip_address,
                        media_title,
                        library_section,
                    ),
                )

            # Mettre à jour la dernière activité de l'utilisateur
            cursor.execute(
                """
            UPDATE plex_users SET last_seen = ? WHERE id = ?
            """,
                (now, user_id),
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Erreur lors de l'enregistrement de la session: {str(e)}")
            return False

    def record_stream_termination(self, user_id, username, platform):
        """
        Enregistre la terminaison d'un flux et met à jour les statistiques

        Args:
            user_id (str): ID de l'utilisateur Plex
            username (str): Nom d'utilisateur
            platform (str): Plateforme utilisée
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now().isoformat()

            # 1. Mettre à jour la dernière terminaison et le compteur
            cursor.execute(
                """
                UPDATE plex_users
                SET last_kill = ?, terminated_sessions = COALESCE(terminated_sessions, 0) + 1
                WHERE id = ?
                """,
                (now, user_id),
            )

            # 2. Mettre à jour ou créer les statistiques de plateforme
            cursor.execute(
                """
                INSERT OR IGNORE INTO platform_stats (user_id, platform, count)
                VALUES (?, ?, 0)
                """,
                (user_id, platform),
            )

            cursor.execute(
                """
                UPDATE platform_stats
                SET count = count + 1
                WHERE user_id = ? AND platform = ?
                """,
                (user_id, platform),
            )

            # 3. Mettre à jour la dernière terminaison
            cursor.execute(
                """
                UPDATE plex_users
                SET last_kill = ?, terminated_sessions = COALESCE(terminated_sessions, 0) + 1
                WHERE id = ?
                """,
                (datetime.now().isoformat(), user_id),
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(
                f"Erreur lors de l'enregistrement de la terminaison du flux: {str(e)}"
            )
            return False

    def mark_session_terminated(self, session_id):
        """Marquer une session comme terminée"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now().isoformat()

            cursor.execute(
                """
            UPDATE sessions 
            SET end_time = ?, was_terminated = 1
            WHERE session_id = ? AND end_time IS NULL
            """,
                (now, session_id),
            )

            conn.commit()
            conn.close()
            return (
                cursor.rowcount > 0
            )  # Retourne True si au moins une ligne a été mise à jour
        except Exception as e:
            logging.error(f"Erreur lors du marquage de fin de session: {str(e)}")
            return False

    def get_user_stats(self, user_id=None):
        """Obtenir les statistiques d'utilisation pour un utilisateur ou tous les utilisateurs"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Pour accéder aux colonnes par nom
            cursor = conn.cursor()

            if user_id:
                query = """
                SELECT 
                    u.id, u.username, 
                    COALESCE(u.total_sessions, 0) AS total_sessions,
                    COALESCE(u.terminated_sessions, 0) AS kill_count,
                    u.last_kill,
                    u.last_seen
                FROM plex_users u
                WHERE u.id = ?
                """
                cursor.execute(query, (user_id,))
            else:
                query = """
                SELECT 
                    u.id, u.username, 
                    COALESCE(u.total_sessions, 0) AS total_sessions,
                    COALESCE(u.terminated_sessions, 0) AS kill_count,
                    u.last_kill,
                    u.last_seen
                FROM plex_users u
                """
                cursor.execute(query)

            results = []
            for row in cursor.fetchall():
                user = dict(row)

                # Récupérer les plateformes pour chaque utilisateur
                cursor.execute(
                    """
                    SELECT platform, count
                    FROM platform_stats
                    WHERE user_id = ?
                    ORDER BY count DESC
                    """,
                    (user["id"],),
                )

                platforms = {}
                for platform_row in cursor.fetchall():
                    platforms[platform_row["platform"]] = platform_row["count"]

                user["platforms"] = platforms
                results.append(user)

            conn.close()
            return results
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des statistiques: {str(e)}")
            return []

    def get_user_details(self, user_id):
        """Obtenir les détails d'un utilisateur spécifique"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
            SELECT * FROM plex_users WHERE id = ?
            """,
                (user_id,),
            )

            user = cursor.fetchone()
            conn.close()

            if user:
                return dict(user)
            else:
                return None
        except Exception as e:
            logging.error(
                f"Erreur lors de la récupération des détails de l'utilisateur: {str(e)}"
            )
            return None

    def get_device_last_activity(self, device_id):
        """
        Récupère la timestamp de la dernière activité connue d'un appareil

        Args:
            device_id (str): Identifiant de l'appareil

        Returns:
            int: Timestamp de la dernière activité, ou 0 si inconnu
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Récupérer la session la plus récente pour cet appareil
            cursor.execute(
                """
                SELECT MAX(timestamp) 
                FROM plex_sessions 
                WHERE player_id = ?
                """,
                (device_id,),
            )

            result = cursor.fetchone()
            conn.close()

            if result and result[0]:
                # Convertir la date en timestamp si nécessaire
                if isinstance(result[0], str):
                    try:
                        dt = datetime.fromisoformat(result[0].replace("Z", "+00:00"))
                        return int(dt.timestamp())
                    except ValueError:
                        # Si la conversion échoue, utiliser le timestamp actuel
                        return int(time.time())
                return int(result[0])

            return 0  # Aucune activité connue
        except Exception as e:
            logging.error(
                f"Erreur lors de la récupération de l'activité de l'appareil: {str(e)}"
            )
            return 0

    def is_user_disabled(self, user_id):
        """Vérifie si un utilisateur est désactivé"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT is_disabled FROM plex_users WHERE id = ?", (user_id,)
            )
            result = cursor.fetchone()
            conn.close()
            return bool(result[0]) if result else False
        except Exception as e:
            logging.error(
                f"Erreur lors de la vérification du statut de désactivation: {str(e)}"
            )
            return False

    def set_user_disabled_status(self, user_id, is_disabled):
        """
        Définit le statut de désactivation d'un utilisateur

        Args:
            user_id (str): ID de l'utilisateur Plex
            is_disabled (bool): True pour désactiver le compte, False sinon

        Returns:
            bool: True si réussi, False sinon
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            disabled_value = 1 if is_disabled else 0

            cursor.execute(
                "UPDATE plex_users SET is_disabled = ? WHERE id = ?",
                (disabled_value, user_id),
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(
                f"Erreur lors de la mise à jour du statut de désactivation: {str(e)}"
            )
            return False

    def get_session_info(self, session_id):
        """
        Récupère les informations d'une session

        Args:
            session_id (str): L'ID de la session

        Returns:
            dict: Les informations de la session ou None si non trouvée
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Pour accéder aux colonnes par nom
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM sessions
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (session_id,),
            )

            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return None
        except Exception as e:
            logging.error(
                f"Erreur lors de la récupération des infos de session: {str(e)}"
            )
            return None
