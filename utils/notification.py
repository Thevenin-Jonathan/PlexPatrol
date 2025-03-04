import requests
import logging


def send_telegram_notification(config, message):
    """
    Envoyer une notification Telegram

    Args:
        config (dict): Configuration avec les paramètres Telegram
        message (str): Message à envoyer

    Returns:
        bool: True si le message a été envoyé avec succès, False sinon
    """
    bot_token = config["telegram"].get("bot_token", "")
    group_id = config["telegram"].get("group_id", "")

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
            logging.error(
                f"Erreur lors de l'envoi du message Telegram: {response.status_code}"
            )
            return False
    except Exception as e:
        logging.error(f"Exception lors de l'envoi du message Telegram: {str(e)}")
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
