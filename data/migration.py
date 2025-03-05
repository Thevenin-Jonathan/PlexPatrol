import os
import json
import logging
import hashlib
from utils import get_app_path
from data import PlexPatrolDB
from config.config_manager import config


def migrate_data_to_db():
    """Migration des données depuis les fichiers JSON vers la base de données SQLite"""
    try:
        db = PlexPatrolDB()

        # Charger la configuration existante
        whitelist_ids = config.get("rules.whitelist", [])

        # Charger les statistiques existantes
        stats_path = os.path.join(get_app_path(), "stats.json")
        if os.path.exists(stats_path):
            with open(stats_path, "r", encoding="utf-8") as f:
                stats = json.load(f)

                # Migrer chaque utilisateur
                for username, user_data in stats.items():
                    # Créer l'utilisateur dans la base de données
                    # Note: nous n'avons pas l'ID utilisateur réel ici, nous utilisons donc un ID généré
                    user_id = hashlib.md5(username.encode()).hexdigest()

                    # Vérifier si l'utilisateur est dans la liste blanche
                    is_whitelisted = 1 if user_id in whitelist_ids else 0

                    # Ajouter l'utilisateur
                    db.add_or_update_user(
                        user_id=user_id,
                        username=username,
                        is_whitelisted=is_whitelisted,
                        notes="Utilisateur migré depuis stats.json",
                    )

                    # Migrer les statistiques
                    kill_count = user_data.get("kill_count", 0)
                    platforms = user_data.get("platforms", {})

                    # Créer des sessions fictives pour représenter les statistiques
                    for platform, count in platforms.items():
                        for i in range(count):
                            # Créer une session terminée pour chaque arrêt
                            session_id = f"migrated_{user_id}_{platform}_{i}"
                            db.record_session(
                                user_id=user_id,
                                session_id=session_id,
                                platform=platform,
                                device="Migration",
                                ip_address="0.0.0.0",
                                media_title="Session migrée",
                                library_section="Migration",
                            )
                            if i < kill_count:
                                db.mark_session_terminated(session_id)

                    # Pour les sessions non terminées (total_sessions - kill_count)
                    non_terminated = user_data.get("total_sessions", 0) - kill_count
                    for i in range(non_terminated):
                        session_id = f"migrated_normal_{user_id}_{i}"
                        db.record_session(
                            user_id=user_id,
                            session_id=session_id,
                            platform="Inconnu",
                            device="Migration",
                            ip_address="0.0.0.0",
                            media_title="Session migrée",
                            library_section="Migration",
                        )

        logging.info("Migration des données terminée avec succès")
        return True
    except Exception as e:
        logging.error(f"Erreur lors de la migration des données: {str(e)}")
        return False
