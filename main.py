import logging
import sys
from PyQt6.QtCore import qFatal
from PyQt6.QtWidgets import QApplication

from interface import console, gui

logger: logging.Logger # not strictly necessary, but added for clarity

def configure_logger():
    root = logging.getLogger()
    sh, fh = logging.StreamHandler(), logging.FileHandler("podcast-downloader.log", "w")
    formatter = logging.Formatter('%(asctime)s: %(name)s.%(funcName)s %(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S')
    sh.setFormatter(formatter)
    fh.setFormatter(formatter)
    root.setLevel(logging.INFO)
    root.addHandler(sh)
    root.addHandler(fh)

def handle_exception(exc_type, exc_value, exc_traceback) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    else:
        logger.exception("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback)) # do not need to declare global logger
    if QApplication.instance() != None:
        qFatal(None)

sys.excepthook = handle_exception

def main():
    configure_logger()
    global logger # strictly necessary
    logger = logging.getLogger(__name__)
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
