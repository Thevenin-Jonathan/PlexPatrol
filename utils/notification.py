import requests
import logging

from utils.constants import LogMessages


def send_telegram_notification(message):
    """
    Envoyer une notification Telegram

    Args:
        config (dict): Configuration avec les paramètres Telegram
        message (str): Message à envoyer

    Returns:
        bool: True si le message a été envoyé avec succès, False sinon
    """
    from config.config_manager import config

    if not config.telegram_enabled:
        logging.warning("Notifications Telegram désactivées, message non envoyé")
        return False

    bot_token = config.telegram_bot_token
    group_id = config.telegram_group_id

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
            logging.error(LogMessages.TELEGRAM_ERROR.format(code=response.status_code))
            return False
    except Exception as e:
        logging.error(LogMessages.TELEGRAM_EXCEPTION.format(error=str(e)))
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
