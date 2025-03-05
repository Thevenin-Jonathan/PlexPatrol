import sqlite3
import os
import json
import logging
from datetime import datetime
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
                max_streams INTEGER DEFAULT 2,
                notes TEXT,
                last_seen TEXT
            )
            """
            )

            # Vérifier si la colonne "phone" existe déjà
            cursor.execute("PRAGMA table_info(plex_users)")
            columns = [col[1] for col in cursor.fetchall()]

            # Si la colonne "phone" n'existe pas, l'ajouter
            if "phone" not in columns:
                cursor.execute("ALTER TABLE plex_users ADD COLUMN phone TEXT")
                logging.info("Colonne 'phone' ajoutée à la table plex_users")

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
        is_whitelisted=0,
        max_streams=None,
        notes=None,
    ):
        """Ajouter ou mettre à jour un utilisateur dans la base de données"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Vérifier si l'utilisateur existe déjà
            cursor.execute("SELECT id FROM plex_users WHERE id = ?", (user_id,))
            exists = cursor.fetchone()

            if exists:
                # Mise à jour de l'utilisateur existant
                if max_streams is None:  # Ne pas modifier max_streams si non spécifié
                    cursor.execute(
                        """
                    UPDATE plex_users 
                    SET username = ?, email = ?, phone = ?, is_whitelisted = ?, notes = ?, last_seen = ? 
                    WHERE id = ?
                    """,
                        (
                            username,
                            email,
                            phone,
                            is_whitelisted,
                            notes,
                            datetime.now().isoformat(),
                            user_id,
                        ),
                    )
                else:
                    cursor.execute(
                        """
                    UPDATE plex_users 
                    SET username = ?, email = ?, phone = ?, is_whitelisted = ?, max_streams = ?, notes = ?, last_seen = ? 
                    WHERE id = ?
                    """,
                        (
                            username,
                            email,
                            phone,
                            is_whitelisted,
                            max_streams,
                            notes,
                            datetime.now().isoformat(),
                            user_id,
                        ),
                    )
            else:
                # Ajout d'un nouvel utilisateur
                if max_streams is None:
                    max_streams = 2  # Valeur par défaut

                cursor.execute(
                    """
                INSERT INTO plex_users (id, username, email, phone, is_whitelisted, max_streams, notes, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        user_id,
                        username,
                        email,
                        phone,
                        is_whitelisted,
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
                cursor.execute(
                    """
                SELECT 
                    u.id, u.username, 
                    COUNT(s.id) AS total_sessions,
                    SUM(CASE WHEN s.was_terminated = 1 THEN 1 ELSE 0 END) AS terminated_sessions,
                    u.last_seen,
                    u.is_whitelisted,
                    u.max_streams
                FROM plex_users u
                LEFT JOIN sessions s ON u.id = s.user_id
                WHERE u.id = ?
                GROUP BY u.id
                """,
                    (user_id,),
                )
            else:
                cursor.execute(
                    """
                SELECT 
                    u.id, u.username, 
                    COUNT(s.id) AS total_sessions,
                    SUM(CASE WHEN s.was_terminated = 1 THEN 1 ELSE 0 END) AS terminated_sessions,
                    u.last_seen,
                    u.is_whitelisted,
                    u.max_streams
                FROM plex_users u
                LEFT JOIN sessions s ON u.id = s.user_id
                GROUP BY u.id
                """
                )

            results = [dict(row) for row in cursor.fetchall()]

            # Pour chaque utilisateur, récupérer sa plateforme principale
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
                    user["main_platform"] = platform_data["platform"]
                else:
                    user["main_platform"] = "Inconnue"

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
