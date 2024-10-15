import logging
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QStyle

from core.constants import APP_TITLE
from interface.classes import PDMainWidget

logger = logging.getLogger(__name__)

def run():
    logger.info("Running gui mode")
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setCentralWidget(PDMainWidget(window))
    window.setWindowTitle(APP_TITLE)
    window.setWindowIcon(window.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
    app.aboutToQuit.connect(window.centralWidget().on_close_app)
    window.show()
    app.exec()
