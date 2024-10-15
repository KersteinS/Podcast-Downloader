import logging # classes files don't get a logger on the module level because each class gets a logger
from pathlib import Path
import webbrowser
from PyQt6.QtCore import Qt, pyqtSignal, QRunnable, QThreadPool, pyqtSlot, QObject
from PyQt6.QtWidgets import QWidget, QCheckBox, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea, QLineEdit, QStyle, QFileDialog, QDialog, QLabel, QDialogButtonBox, QMessageBox

from core.classes import PodcastAndStorage
from core.constants import LOC_HINT, LOC_INSTRUCTIONS, NEW_INSTRUCTIONS, RSS_HINT, RSS_INSTRUCTIONS
from core.download_procedure import create_or_fetch_history, download_podcasts, get_podcast_title, is_valid_url, write_history

class PDMainWidget(QWidget):
    def __init__(self, parent=None) -> None:
        self.logger = logging.getLogger(str(self))
        self.logger.debug("initializing gui")
        super().__init__(parent)
        self.download_threadpool = QThreadPool(self)
        self.download_process = None
        self.check_all_btn = QCheckBox("Select All", self)
        self.new_btn = QPushButton("Add New", self)
        self.download_btn = QPushButton("Download Selected", self)
        self.remove_btn = QPushButton("Remove Selected", self)
        self.scroll_area = QScrollArea(self)
        self.list_widget = PDListWidget(self.scroll_area)
        self.main_layout = QVBoxLayout(self) # passing self to the constructor sets the layout for self to this layout
        self.top_bar_layout = QHBoxLayout()
        self.do_configurations()
        self.do_layout()

    def do_layout(self) -> None:
        self.top_bar_layout.addWidget(self.check_all_btn)
        self.top_bar_layout.addStretch()
        self.top_bar_layout.addWidget(self.new_btn)
        self.top_bar_layout.addWidget(self.download_btn)
        self.top_bar_layout.addWidget(self.remove_btn)
        self.main_layout.addLayout(self.top_bar_layout)
        self.main_layout.addWidget(self.scroll_area)

    def do_configurations(self) -> None:
        self.setMinimumSize(500,450)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.list_widget)
        self.check_all_btn.clicked.connect(self.list_widget.toggle_select_all)
        self.download_btn.clicked.connect(self.download_selected)
        self.remove_btn.clicked.connect(self.remove_selected)
        self.remove_btn.setToolTip("Removes the selected podcast from download history. Does not delete any files!")
        self.new_btn.clicked.connect(self.add_new)
        for i in self.list_widget.items:
            i.successful_edit.connect(self.on_item_update)
        self.scroll_area.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid black }")
        PDDownloadProcess.signals.finished.connect(self.download_completed)
        PDDownloadProcess.signals.stopping.connect(self.download_canceled)

    def add_new(self):
        """C in CRUD"""
        self.logger.info("Launching new podcast dialog")
        dialog = PDNewPodcastDialog(self)
        result = dialog.exec()
        if result == 1:
            self.logger.info("Adding new podcast")
            dialog.data.title = get_podcast_title(dialog.data.rss)
            write_history(tuple(i for i in [*self.list_widget.history, dialog.data]))
            self.list_widget.reload_history()
        else:
            self.logger.info("Canceled adding new podcast")

    def download_selected(self):
        """R in CRUD"""
        to_download = [i.data for i in self.list_widget.items if i.checkbox.isChecked()]
        if len(to_download) == 0:
            self.logger.info("No podcasts selected")
            return
        self.logger.info(f"Downloading {len(to_download)} podcasts")
        for i in (self.check_all_btn, self.new_btn, self.remove_btn, *self.list_widget.items):
            i.setDisabled(True)
        self.download_process = PDDownloadProcess(to_download)
        self.download_btn.setText("Stop Download")
        self.download_btn.disconnect()
        self.download_btn.clicked.connect(self.download_process.terminate)
        self.download_threadpool.start(self.download_process)

    def download_canceled(self):
        """Supports R in CRUD"""
        self.logger.info("Canceling download")
        self.download_btn.setText("Download Selected")
        self.download_btn.setDisabled(True)

    def download_completed(self, result: int):
        """Supports R in CRUD"""
        if result == 0:
            self.logger.info("Download completed")
            self.download_btn.setText("Download Selected")
        else:
            self.logger.info("Download canceled")
            self.download_btn.setDisabled(False)
        self.download_btn.disconnect()
        self.download_btn.clicked.connect(self.download_selected)
        for i in (self.check_all_btn, self.new_btn, self.remove_btn, *self.list_widget.items):
            i.setDisabled(False)
        self.download_process = None


    def on_item_update(self, item: "PDListItem"):
        """U in CRUD"""
        self.logger.debug(f"Updating {item}")
        index = self.list_widget.items.index(item)
        self.list_widget.history[index].rss = item.data.rss
        self.list_widget.history[index].loc = item.data.loc
        self.list_widget.history[index].title = get_podcast_title(item.data.rss)
        item.checkbox.setText(item.data.title)
        write_history(self.list_widget.history)

    def remove_selected(self):
        """D in CRUD"""
        to_remove = [i for i, item in enumerate(self.list_widget.items) if item.checkbox.isChecked()]
        if len(to_remove) == 0:
            self.logger.info("No podcasts selected")
            return
        self.logger.info(f"Removing {len(to_remove)} podcasts")
        new_history = tuple(item for i, item in enumerate(create_or_fetch_history()) if i not in to_remove)
        write_history(new_history)
        self.list_widget.reload_history()

    def on_close_app(self):
        if self.download_threadpool.activeThreadCount() > 0:
            self.download_process.stop.append(1)
            self.download_threadpool.waitForDone(-1)

class PDListWidget(QWidget):
    def __init__(self, parent: QWidget) -> None:
        self.logger = logging.getLogger(str(self))
        self.logger.debug("Initializing list")
        super().__init__(parent)
        self.list_layout = QVBoxLayout(self)
        self.history = create_or_fetch_history()
        self.items = list[PDListItem]()
        self.fill_items()
        self.list_layout.setContentsMargins(0,0,0,0)
        self.list_layout.setSpacing(0)

    def fill_items(self):
        self.items.clear()
        for i in reversed(range(self.list_layout.count())):
            taken = self.list_layout.takeAt(i)
            if hasattr(taken, "deleteLater"):
                taken.deleteLater()
        for item in self.history:
            self.items.append(PDListItem(self, item))
            self.list_layout.addWidget(self.items[-1])
        self.list_layout.addStretch()
        for item in self.items[:-2]:
            item.setStyleSheet("PDListItem { border-bottom: 1px solid black }")

    def reload_history(self):
        self.history = create_or_fetch_history()
        self.fill_items()

    def toggle_select_all(self, value: bool):
        for i in self.items:
            if i.checkbox.isEnabled():
                i.checkbox.setChecked(value)

class PDListItem(QWidget):
    successful_edit = pyqtSignal(QWidget)
    def __init__(self, parent: QWidget, data: PodcastAndStorage) -> None:
        self.logger = logging.getLogger(str(self))
        self.logger.debug(f"initializing list item with {data}")
        self.data = data
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.checkbox = QCheckBox(data.title, self)
        self.rss_widget = PDRssWidget(data.rss, self)
        self.loc_widget = PDLocWidget(data.loc, self)
        self.item_layout = QVBoxLayout(self)
        self.item_layout.addWidget(self.checkbox)
        self.item_layout.addWidget(self.rss_widget)
        self.item_layout.addWidget(self.loc_widget)
        self.rss_widget.textbox.editingFinished.connect(self.on_rss_edit_finish)
        self.loc_widget.textbox.editingFinished.connect(self.on_loc_edit_finish)

    def on_rss_edit_finish(self):
        self.logger.debug("RSS edited")
        if not is_valid_url(self.rss_widget.textbox.text()):
            QMessageBox.warning(self, "Invalid RSS URL", "RSS URL is not valid! Podcasts will not be downloaded for this entry.")
            self.logger.info("RSS URL is not valid! Podcasts will not be downloaded for this entry.")
            self.checkbox.setChecked(False)
            self.checkbox.setDisabled(True)
        elif self.loc_widget.textbox.text() != "" and Path(self.loc_widget.textbox.text()).exists():
            if self.checkbox.isEnabled() == False:
                self.checkbox.setDisabled(False)
            self.data.rss = self.rss_widget.textbox.text()
            self.successful_edit.emit(self)

    def on_loc_edit_finish(self):
        self.logger.debug("Loc edited")
        if self.loc_widget.textbox.text() == "" or not Path(self.loc_widget.textbox.text()).exists():
            QMessageBox.warning(self, "Invalid Save Path", "The entered folder path is not valid! Podcasts will not be downloaded for this entry.")
            self.logger("The entered folder path is not valid! Podcasts will not be downloaded for this entry.")
            self.checkbox.setChecked(False)
            self.checkbox.setDisabled(True)
        elif is_valid_url(self.rss_widget.textbox.text()):
            if self.checkbox.isEnabled() == False:
                self.checkbox.setDisabled(False)
            self.data.loc = self.loc_widget.textbox.text()
            self.successful_edit.emit(self)

class PDLineEditAndButton(QWidget):
    def __init__(self, text: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.logger = logging.getLogger(str(self))
        self.logger.debug(f"initializing widget with {text}")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.textbox = QLineEdit(text, self)
        self.icon_btn = QPushButton(self)
        self.icon_btn.clicked.connect(self.on_click)
        self.subitem_layout = QHBoxLayout(self)
        self.do_layout()
        self.subitem_layout.setContentsMargins(0,0,0,0)

    def do_layout(self):
        self.subitem_layout.addWidget(self.textbox)
        self.subitem_layout.addWidget(self.icon_btn)

    def on_click(self):
        # to be re-implemented in subclases
        pass

class PDRssWidget(PDLineEditAndButton):
    def __init__(self, text: str, parent: QWidget) -> None:
        super().__init__(text, parent)
        self.textbox.setPlaceholderText(RSS_HINT)
        self.textbox.setToolTip(RSS_HINT)
        self.icon_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        self.icon_btn.setToolTip("Open RSS feed in web browser")

    def on_click(self):
        self.logger.debug("RSS button clicked.")
        if is_valid_url(self.textbox.text()):
            webbrowser.open(self.textbox.text())

class PDLocWidget(PDLineEditAndButton):
    def __init__(self, text: str, parent: QWidget) -> None:
        super().__init__(text, parent)
        self.textbox.setPlaceholderText(LOC_HINT)
        self.textbox.setToolTip(LOC_HINT)
        self.icon_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        self.icon_btn.setToolTip("Browse for save folder")

    def on_click(self):
        self.logger.debug("Loc button clicked")
        selection = QFileDialog()
        folder = selection.getExistingDirectory(directory=self.textbox.text())
        if folder:
            folder = Path(folder).resolve()
            self.textbox.setText(str(folder))
        selection.deleteLater()

class PDNewPodcastDialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Podcast")
        self.data = PodcastAndStorage("", "", "")
        self.instructions = QLabel(NEW_INSTRUCTIONS, self)
        self.rss_widget = PDRssWidget("", self)
        self.rss_widget.textbox.setPlaceholderText(RSS_INSTRUCTIONS)
        self.rss_widget.textbox.setToolTip(RSS_INSTRUCTIONS)
        self.loc_widget = PDLocWidget("", self)
        self.loc_widget.textbox.setPlaceholderText(LOC_INSTRUCTIONS)
        self.loc_widget.textbox.setToolTip(LOC_INSTRUCTIONS)
        buttons = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.button_box = QDialogButtonBox(buttons)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setDisabled(True)
        self.dialog_layout = QVBoxLayout(self)
        self.dialog_layout.addWidget(self.instructions)
        self.dialog_layout.addWidget(self.rss_widget)
        self.dialog_layout.addWidget(self.loc_widget)
        self.dialog_layout.addWidget(self.button_box)
        self.rss_widget.textbox.textChanged.connect(self.on_changed)
        self.loc_widget.textbox.textChanged.connect(self.on_changed)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def on_changed(self, text: str):
        if is_valid_url(self.rss_widget.textbox.text()) and self.loc_widget.textbox.text() != "" and Path(self.loc_widget.textbox.text()).exists():
            self.button_box.button(QDialogButtonBox.StandardButton.Ok).setDisabled(False)
            self.data = PodcastAndStorage("", self.rss_widget.textbox.text(), self.loc_widget.textbox.text())
        elif self.button_box.button(QDialogButtonBox.StandardButton.Ok).isEnabled():
            self.button_box.button(QDialogButtonBox.StandardButton.Ok).setDisabled(True)

class PDDownloadSignals(QObject):
    stopping = pyqtSignal()
    finished = pyqtSignal(int)

class PDDownloadProcess(QRunnable):
    signals = PDDownloadSignals()
    def __init__(self, podcasts: tuple[PodcastAndStorage]) -> None:
        super().__init__()
        self.stop = []
        self.podcasts = podcasts

    def terminate(self):
        self.stop.append(1)
        self.signals.stopping.emit()

    @pyqtSlot()
    def run(self):
        self.signals.finished.emit(download_podcasts(self.podcasts, self.stop))
