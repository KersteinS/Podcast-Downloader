import logging
from core.download_procedure import create_or_fetch_history, download_podcasts

logger = logging.getLogger(__name__)

def run():
    logger.info("Running console mode")
    history = create_or_fetch_history()
    download_podcasts(history)
