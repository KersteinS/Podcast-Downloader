import logging
import sys

from interface import console, gui

logging.basicConfig(
    handlers=[logging.StreamHandler(), logging.FileHandler("podcast-downloader.log", "w")],
    format='%(asctime)s: %(name)s.%(funcName)s %(levelname)s: %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

def handle_exception(exc_type, exc_value, exc_traceback) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        return sys.__excepthook__(exc_type, exc_value, exc_traceback)
    return logger.exception("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

def main():
    level = tuple(i.upper().replace("--LEVEL=", "") for i in sys.argv if i.upper() in ("--LEVEL=DEBUG", "--LEVEL=WARN", "--LEVEL=ERROR", "--LEVEL=CRITICAL"))
    if len(level) > 0:
        logging.getLogger().setLevel(level[-1])
    logger.info("Starting script")
    if "gui" in [i.lower() for i in sys.argv]:
        gui.run()
    else:
        console.run()
    logger.info("Completed script")
    logging.shutdown()

if __name__ == "__main__":
    main()
