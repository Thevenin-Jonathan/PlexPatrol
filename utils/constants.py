"""
Constantes pour l'application PlexPatrol.
Ce fichier centralise toutes les chaînes de caractères, messages et clés de configuration
pour faciliter la maintenance et l'internationalisation future.
"""


# Clés de configuration
class ConfigKeys:
    # Plex Server
    PLEX_SERVER_URL = "plex_server.url"
    PLEX_TOKEN = "plex_server.token"
    CHECK_INTERVAL = "plex_server.check_interval"

    # Règles
    MAX_STREAMS = "rules.max_streams"
    TERMINATION_MESSAGE = "rules.termination_message"
    WHITELIST = "rules.whitelist"

    # Notifications
    TELEGRAM_ENABLED = "telegram.enabled"
    TELEGRAM_BOT_TOKEN = "telegram.bot_token"
    TELEGRAM_GROUP_ID = "telegram.group_id"


# Valeurs par défaut
class Defaults:
    PLEX_SERVER_URL = "http://localhost:32400"
    CHECK_INTERVAL = 30
    MAX_STREAMS = 2
    TERMINATION_MESSAGE = (
        "Votre abonnement ne vous permet pas la lecture sur plusieurs écrans."
    )


# Messages pour l'interface utilisateur
class UIMessages:
    # Titres de fenêtres
    MAIN_WINDOW_TITLE = "PlexPatrol - Moniteur de flux Plex"
    CONFIG_DIALOG_TITLE = "Configuration"
    USER_DIALOG_TITLE = "Gestion des utilisateurs"
    STATS_DIALOG_TITLE = "Statistiques détaillées"
    FIRST_TIME_SETUP_TITLE = "Configuration initiale PlexPatrol"

    # Titres de boîtes de message
    TITLE_SUCCESS = "Succès"
    TITLE_ERROR = "Erreur"
    TITLE_WARNING = "Avertissement"
    TITLE_CONFIRMATION = "Confirmation"

    # Titres de sections UI
    GROUP_USERS = "Utilisateurs"
    GROUP_USER_DETAILS = "Détails de l'utilisateur"
    GROUP_ACTIVE_SESSIONS = "Sessions actives"
    GROUP_STATS = "Statistiques"
    GROUP_LOGS = "Journal d'activité"

    # Messages de dialogue
    CONFIG_INCOMPLETE = (
        "La configuration est incomplète. Voulez-vous quitter l'application ?"
    )
    CONFIRM_EXIT = "Voulez-vous quitter l'application?\nLa surveillance sera arrêtée."
    CONFIRM_SESSION_STOP = "Voulez-vous vraiment arrêter la session de {username}?"
    CONFIRM_RESET_STATS = "Voulez-vous vraiment réinitialiser toutes les statistiques?\nCette action est irréversible."
    FIRST_TIME_SETUP_WELCOME = (
        "Bienvenue dans PlexPatrol ! Veuillez configurer l'accès à votre serveur Plex."
    )
    CONFIG_INCOMPLETE_WARNING = (
        "L'application pourrait ne pas fonctionner correctement."
    )

    # Boutons
    BTN_SAVE = "Enregistrer"
    BTN_REFRESH = "Rafraîchir"
    BTN_CLOSE = "Fermer"
    BTN_STOP = "Arrêter"
    BTN_PAUSE = "Pause"
    BTN_RESUME = "Reprendre"
    BTN_DELETE = "Supprimer"
    BTN_EXPORT = "Exporter (CSV)"
    BTN_RESET = "Réinitialiser"
    BTN_SYNC = "Synchroniser avec Plex"
    BTN_MIGRATE = "Migrer les données existantes"
    BTN_TEST_NOTIFICATION = "Tester la notification"

    # Statuts
    STATUS_ACTIVE = "Surveillance active"
    STATUS_PAUSED = "Surveillance en pause"
    STATUS_ERROR = "Erreur de connexion"

    # Messages de notification
    CONFIG_UPDATED = "Configuration mise à jour"
    STATS_REFRESHED = "Statistiques rafraîchies"
    LOGS_CLEARED = "Journal effacé"
    LOGS_SAVED = "Logs enregistrés dans {filepath}"
    STATS_EXPORTED = "Statistiques exportées dans {filepath}"
    STATS_RESET = "Statistiques réinitialisées"
    SESSIONS_REFRESHED = "Sessions rafraîchies manuellement"
    USER_UPDATED = "Utilisateur mis à jour avec succès!"
    USER_DELETE_ERROR = (
        "Une erreur s'est produite lors de la suppression de l'utilisateur: {error}"
    )
    USER_DELETED = "L'utilisateur '{username}' a été supprimé avec succès."
    SYNC_SUCCESS = "{count} utilisateurs synchronisés avec Plex."

    # Labels
    LABEL_USERNAME = "Nom d'utilisateur:"
    LABEL_MAX_STREAMS = "Nombre max de flux:"
    LABEL_EMAIL = "E-mail:"
    LABEL_PHONE = "Téléphone:"
    LABEL_WHITELIST = "Liste blanche:"
    LABEL_NOTES = "Notes:"

    # Placeholders
    PLACEHOLDER_PHONE = "0601020304"

    # Messages d'erreur
    ERROR_UPDATE_USER = "Impossible de mettre à jour l'utilisateur"
    ERROR_NO_PLEX_USERS = (
        "Aucun utilisateur Plex n'a été trouvé. Vérifiez votre connexion au serveur."
    )
    ERROR_SENDING_NOTIFICATION = "Impossible d'envoyer la notification"
    ERROR_SENDING_NOTIFICATION_DETAILS = (
        "Erreur lors de l'envoi de la notification: {error}"
    )

    # Confirmations
    CONFIRM_DELETE_USER = "Voulez-vous vraiment supprimer l'utilisateur '{username}'?"
    CONFIRM_SYNC_USERS = "Voulez-vous synchroniser {count} utilisateurs depuis Plex?\nLes utilisateurs existants seront conservés, mais leurs limites seront mises à jour si nécessaire."

    # Notifications
    TEST_NOTIFICATION_MESSAGE = (
        "Ceci est un message de test de l'application PlexPatrol"
    )
    NOTIFICATION_SENT = "Notification envoyée avec succès!"

    # Menu
    MENU_CONFIGURATION = "Configuration..."
    MENU_USERS = "Gestion des utilisateurs..."
    MENU_STATS = "Statistiques détaillées..."
    MENU_EXIT = "Quitter"
    MENU_FILE = "&Fichier"

    # Messages pour la configuration
    CONFIG_SERVER_URL_LABEL = "URL du serveur Plex:"
    CONFIG_TOKEN_LABEL = "Token d'authentification:"
    CONFIG_INTERVAL_LABEL = "Intervalle de vérification (secondes):"
    CONFIG_MAX_STREAMS_LABEL = "Nombre maximum de flux par utilisateur:"
    CONFIG_TERM_MSG_LABEL = "Message de terminaison:"
    CONFIG_TELEGRAM_ENABLE_LABEL = "Activer les notifications Telegram:"
    CONFIG_TELEGRAM_TOKEN_LABEL = "Token du bot Telegram:"
    CONFIG_TELEGRAM_GROUP_LABEL = "ID du groupe/canal Telegram:"
    CONFIG_CONNECTION_SUCCESS = "Connexion au serveur Plex réussie!"
    CONFIG_CONNECTION_ERROR = "Erreur de connexion: {error}"

    # Messages de migration
    CONFIRM_MIGRATION = "Voulez-vous migrer les données existantes vers la base de données?\nCette opération peut prendre du temps en fonction du volume de données."
    MIGRATION_SUCCESS = "Migration des données terminée!"
    MIGRATION_ERROR = "Problème lors de la migration des données."

    # Titres d'onglets et de graphiques
    TAB_DATA = "Données"
    TAB_CHARTS = "Graphiques"
    TAB_PLATFORMS = "Plateformes"
    CHART_SESSIONS_TITLE = "Répartition des arrêts de flux par utilisateur"
    CHART_PLATFORMS_TITLE = "Arrêts de flux par plateforme"


# Messages de log
class LogMessages:
    # Démarrage et arrêt
    MONITOR_START = "Démarrage de la surveillance des flux Plex"
    MONITOR_STOP = "Arrêt de la surveillance des flux Plex"

    # Erreurs
    DB_ERROR = "Erreur lors de l'initialisation de la base de données: {error}"
    SESSION_ERROR = "Erreur lors de la vérification des sessions: {error}"
    CONNECTION_ERROR = "Erreur de connexion au serveur Plex: {error}"
    XML_PARSE_ERROR = "Erreur lors du parsing des données de session: {error}"
    PLEX_USERS_ERROR = "Erreur lors du chargement des utilisateurs Plex: {error}"
    STATS_EXPORT_ERROR = "Erreur lors de l'exportation des statistiques: {error}"
    # Succès
    DB_INITIALIZED = "Base de données initialisée avec succès"
    PLEX_USERS_LOADED = "Chargement de {count} utilisateurs Plex réussi"

    # Avertissements
    USER_STREAM_LIMIT = "Utilisateur {username} dépasse la limite: {count} flux actifs"

    # Actions
    STREAM_STOPPED = "Stream arrêté pour {username} sur {platform}"
    STREAM_MANUAL_STOP = "Session {session_id} arrêtée manuellement"

    # Messages liés à Telegram
    TELEGRAM_CONFIG_INCOMPLETE = "Configuration Telegram incomplète"
    TELEGRAM_ERROR = "Erreur lors de l'envoi du message Telegram: {code}"
    TELEGRAM_EXCEPTION = "Exception lors de l'envoi du message Telegram: {error}"


# Types de severité pour les logs
class LogLevels:
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


# Noms des colonnes dans les tableaux
class TableColumns:
    # Sessions
    SESSIONS = [
        "Utilisateur",
        "Titre",
        "Section",
        "État",
        "Appareil",
        "Plateforme",
        "IP",
        "Actions",
    ]

    # Statistiques
    STATS = [
        "Utilisateur",
        "Arrêts de flux",
        "Dernier arrêt",
        "Plateforme la plus utilisée",
        "Taux d'arrêts",
    ]

    # Utilisateurs
    USERS = [
        "Nom d'utilisateur",
        "Téléphone",
        "Flux max",
        "Liste blanche",
        "Sessions totales",
        "Streams arrêtés",
        "Dernière activité",
        "Actions",
    ]


# Chemins pour les fichiers et dossiers
class Paths:
    ASSETS = "assets"
    LOGS = "logs"
    DATA = "data"
    EXPORTS = "exports"
    ICON = "plexpatrol_icon.png"
    DATABASE = "plexpatrol.db"
    STATS_FILE = "stats.json"
