import sqlite3
import os
import logging
from datetime import datetime
import time
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

        # Initialiser la base de données
        self.initialize_db()

    # =====================================================
    # MÉTHODES D'INITIALISATION DE LA BASE DE DONNÉES
    # =====================================================

    def initialize_db(self):
        """Initialiser la structure complète de la base de données"""
        try:
            conn = sqlite3.connect(self.db_path)

            # Créer les tables principales
            self.create_table_users(conn)
            self.create_table_sessions(conn)
            self.create_table_config(conn)
            self.create_table_platform_stats(conn)

            conn.commit()
            conn.close()

            logging.info(LogMessages.DB_INITIALIZED)
            return True
        except Exception as e:
            logging.error(LogMessages.DB_ERROR.format(error=str(e)))
            return False

    def create_table_users(self, conn):
        """Crée la table des utilisateurs Plex"""
        cursor = conn.cursor()
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
                last_seen TEXT,
                terminated_sessions INTEGER DEFAULT 0,
                last_kill TEXT,
                total_sessions INTEGER DEFAULT 0
            )
            """
        )

    def create_table_sessions(self, conn):
        """Crée la table des sessions Plex"""
        cursor = conn.cursor()
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

    def create_table_config(self, conn):
        """Crée la table de configuration"""
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

    def create_table_platform_stats(self, conn):
        """Crée la table pour les statistiques par plateforme"""
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS platform_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                count INTEGER DEFAULT 0,
                UNIQUE(user_id, platform)
            )
            """
        )

    # =====================================================
    # MÉTHODES DE GESTION DES UTILISATEURS
    # =====================================================

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
        """Ajouter ou mettre à jour un utilisateur"""
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

    def get_all_users(self, include_disabled=False):
        """Récupère tous les utilisateurs avec leurs statistiques de manière optimisée

        Args:
            include_disabled (bool): Si True, inclut les utilisateurs désactivés

        Returns:
            list: Liste des utilisateurs avec leurs statistiques
        """
        try:
            conn = sqlite3.connect(self.db_path)

            # Optimisations SQLite pour améliorer les performances
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Construction de la requête SQL de base
            query = """
            SELECT 
                u.*,
                COALESCE(s.total, 0) AS total_sessions,
                COALESCE(s.terminated, 0) AS terminated_sessions,
                COALESCE(p.platform, 'Inconnue') AS main_platform
            FROM plex_users u
            LEFT JOIN (
                -- Sous-requête pour les statistiques de sessions
                SELECT 
                    user_id, 
                    COUNT(*) as total,
                    SUM(CASE WHEN was_terminated = 1 THEN 1 ELSE 0 END) as terminated
                FROM sessions 
                GROUP BY user_id
            ) s ON u.id = s.user_id
            LEFT JOIN (
                -- Sous-requête pour déterminer la plateforme principale
                SELECT user_id, platform
                FROM (
                    SELECT 
                        user_id, 
                        platform,
                        COUNT(*) as count,
                        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY COUNT(*) DESC) as rank
                    FROM sessions
                    GROUP BY user_id, platform
                ) ranked
                WHERE rank = 1
            ) p ON u.id = p.user_id
            """

            # Ajouter la condition pour filtrer les utilisateurs désactivés si nécessaire
            if not include_disabled:
                query += " WHERE u.is_disabled = 0 OR u.is_disabled IS NULL"

            cursor.execute(query)

            # Convertir les résultats en liste de dictionnaires
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()

            return results
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des utilisateurs: {str(e)}")
            if "conn" in locals() and conn:
                conn.close()
            return []

    def delete_user(self, username):
        """Supprimer un utilisateur"""
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

    def get_user_max_streams(self, user_id):
        """Récupère la limite de flux maximale pour un utilisateur"""
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

    # =====================================================
    # MÉTHODES DE GESTION DES SESSIONS
    # =====================================================

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

    def mark_session_terminated(self, session_id):
        """Marque une session comme terminée"""
        try:
            # D'abord, récupérer les infos de la session
            session_info = self.get_session_info(session_id)
            if not session_info:
                logging.error(f"Session {session_id} introuvable")
                return False

            user_id = session_info.get("user_id")
            username = session_info.get("username")
            platform = session_info.get("platform")

            # Ensuite, mettre à jour la session
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET was_terminated = 1 WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()
            conn.close()

            # Mettre à jour les statistiques
            self.record_stream_termination(user_id, username, platform)

            return True
        except Exception as e:
            logging.error(
                f"Erreur lors du marquage de la session comme terminée: {str(e)}"
            )
            return False

    def get_session_info(self, session_id):
        """Récupère les informations d'une session"""
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

    def get_device_last_activity(self, device_id):
        """Récupère la timestamp de la dernière activité d'un appareil"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Récupérer la session la plus récente pour cet appareil
            cursor.execute(
                """
                SELECT MAX(timestamp) 
                FROM sessions 
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

    # =====================================================
    # MÉTHODES DE GESTION DES STATISTIQUES
    # =====================================================

    def record_stream_termination(self, user_id, username, platform):
        """Enregistre la terminaison d'un flux et met à jour les statistiques"""
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

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(
                f"Erreur lors de l'enregistrement de la terminaison du flux: {str(e)}"
            )
            return False

    def get_user_stats(self, user_id=None):
        """Obtenir les statistiques d'utilisation"""
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

    # =====================================================
    # MÉTHODES DE GESTION DES AUTORISATIONS
    # =====================================================

    def is_user_whitelisted(self, user_id):
        """Vérifie si un utilisateur est en liste blanche"""
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
        """Définit le statut whitelist d'un utilisateur"""
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
        """Définit le statut de désactivation d'un utilisateur"""
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

    def close(self):
        """Ferme proprement toutes les connexions à la base de données"""
        try:
            # Fermer toute connexion active
            conn = sqlite3.connect(self.db_path)
            conn.close()
        except:
            pass
