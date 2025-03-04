import os
import logging
from datetime import datetime
from utils import get_app_path
import sys


def setup_logging():
    """Configurer le système de journalisation"""
    logs_dir = os.path.join(get_app_path(), "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    log_file = os.path.join(
        logs_dir, f"PlexPatrol_{datetime.now().strftime('%Y%m%d')}.log"
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
