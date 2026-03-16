from __future__ import annotations

import logging
import webbrowser
from collections import deque

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from terraria_wikipilot.config import AppConfig
from terraria_wikipilot.query_service import QueryService
from terraria_wikipilot.summarizer import format_response

LOGGER = logging.getLogger(__name__)


class WorkerSignals(QObject):
    finished = Signal(object)


class QueryWorker(QRunnable):
    def __init__(self, service: QueryService, query: str) -> None:
        super().__init__()
        self.service = service
        self.query = query
        self.signals = WorkerSignals()

    def run(self) -> None:
        response = self.service.ask(self.query)
        self.signals.finished.emit(response)


class OverlayWindow(QMainWindow):
    def __init__(self, config: AppConfig, query_service: QueryService) -> None:
        super().__init__()
        self.config = config
        self.query_service = query_service
        self.thread_pool = QThreadPool()
        self.recent_queries: deque[str] = deque(maxlen=10)
        self.last_source_url: str | None = None
        self.collapsed = False

        self.setWindowTitle("Terraria Wikipilot")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setWindowOpacity(self.config.opacity)

        self._build_ui()
        self._apply_theme()
        self.anchor_bottom_right()

    def _build_ui(self) -> None:
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        title_row = QHBoxLayout()
        title = QLabel("🌲 Terraria Wikipilot")
        title.setObjectName("titleLabel")
        self.loading_label = QLabel("")
        self.loading_label.setObjectName("statusLabel")

        self.collapse_btn = QPushButton("–")
        self.collapse_btn.setFixedWidth(26)
        self.collapse_btn.clicked.connect(self.toggle_collapsed)

        hide_btn = QPushButton("✕")
        hide_btn.setFixedWidth(26)
        hide_btn.clicked.connect(self.hide)

        title_row.addWidget(title)
        title_row.addStretch(1)
        title_row.addWidget(self.loading_label)
        title_row.addWidget(self.collapse_btn)
        title_row.addWidget(hide_btn)

        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Ask Terraria Wiki…")
        self.query_input.returnPressed.connect(self.submit_query)

        input_row = QHBoxLayout()
        self.ask_btn = QPushButton("Ask")
        self.ask_btn.clicked.connect(self.submit_query)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_view)
        input_row.addWidget(self.query_input)
        input_row.addWidget(self.ask_btn)
        input_row.addWidget(clear_btn)

        recent_row = QHBoxLayout()
        recent_label = QLabel("Recent")
        self.recent_combo = QComboBox()
        self.recent_combo.currentTextChanged.connect(self._on_recent_selected)
        recent_row.addWidget(recent_label)
        recent_row.addWidget(self.recent_combo)

        action_row = QHBoxLayout()
        self.copy_link_btn = QPushButton("Copy Link")
        self.copy_link_btn.clicked.connect(self.copy_link)
        self.copy_link_btn.setEnabled(False)
        self.open_link_btn = QPushButton("Open Page")
        self.open_link_btn.clicked.connect(self.open_link)
        self.open_link_btn.setEnabled(False)
        action_row.addWidget(self.copy_link_btn)
        action_row.addWidget(self.open_link_btn)
        action_row.addStretch(1)

        self.answer_box = QPlainTextEdit()
        self.answer_box.setReadOnly(True)
        self.answer_box.setPlainText("Ready. Press Enter after typing a question.")

        self.expandable_widgets = [
            self.query_input,
            self.ask_btn,
            clear_btn,
            self.recent_combo,
            self.answer_box,
            self.copy_link_btn,
            self.open_link_btn,
        ]

        outer.addLayout(title_row)
        outer.addLayout(input_row)
        outer.addLayout(recent_row)
        outer.addLayout(action_row)
        outer.addWidget(self.answer_box)
        self.setCentralWidget(root)
        self.resize(self.config.width, self.config.expanded_height)

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: rgba(22, 30, 24, 236);
                border: 1px solid #4f6953;
                border-radius: 10px;
            }
            QLabel#titleLabel { color: #c9e8b5; font-weight: bold; }
            QLabel#statusLabel { color: #9ac98d; }
            QLineEdit, QPlainTextEdit, QComboBox {
                background-color: rgba(12, 18, 13, 210);
                color: #e6f5df;
                border: 1px solid #3e5a42;
                border-radius: 6px;
                padding: 6px;
            }
            QPushButton {
                background-color: #3c5d41;
                color: #efffe7;
                border: 1px solid #587f5f;
                border-radius: 6px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #4b7353;
            }
            """
        )

    def anchor_bottom_right(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return
        geometry = screen.availableGeometry()
        width = self.width()
        height = self.height()
        self.move(
            geometry.x() + geometry.width() - width - self.config.margin,
            geometry.y() + geometry.height() - height - self.config.margin,
        )

    def toggle_collapsed(self) -> None:
        self.collapsed = not self.collapsed
        for widget in self.expandable_widgets:
            widget.setVisible(not self.collapsed)
        self.collapse_btn.setText("+" if self.collapsed else "–")
        target_height = self.config.collapsed_height if self.collapsed else self.config.expanded_height
        self.resize(self.config.width, target_height)
        self.anchor_bottom_right()

    def toggle_visible(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()
            self.anchor_bottom_right()

    def submit_query(self) -> None:
        query = self.query_input.text().strip()
        if not query:
            return
        self._set_loading(True)
        worker = QueryWorker(self.query_service, query)
        worker.signals.finished.connect(self._on_query_complete)
        self.thread_pool.start(worker)

    def _on_query_complete(self, response: object) -> None:
        self._set_loading(False)
        formatted = format_response(response)
        self.answer_box.setPlainText(formatted)

        if response.page:
            self.last_source_url = response.page.url
            self.copy_link_btn.setEnabled(True)
            self.open_link_btn.setEnabled(True)
        else:
            self.last_source_url = None
            self.copy_link_btn.setEnabled(False)
            self.open_link_btn.setEnabled(False)

        if response.query and response.query not in self.recent_queries:
            self.recent_queries.appendleft(response.query)
            self._refresh_recent()

    def _set_loading(self, is_loading: bool) -> None:
        self.ask_btn.setEnabled(not is_loading)
        self.loading_label.setText("Loading…" if is_loading else "")

    def _refresh_recent(self) -> None:
        current = self.recent_combo.currentText()
        self.recent_combo.blockSignals(True)
        self.recent_combo.clear()
        self.recent_combo.addItems(list(self.recent_queries))
        index = self.recent_combo.findText(current)
        if index >= 0:
            self.recent_combo.setCurrentIndex(index)
        self.recent_combo.blockSignals(False)

    def _on_recent_selected(self, value: str) -> None:
        if value:
            self.query_input.setText(value)

    def clear_view(self) -> None:
        self.query_input.clear()
        self.answer_box.setPlainText("Cleared.")

    def copy_link(self) -> None:
        if self.last_source_url:
            QGuiApplication.clipboard().setText(self.last_source_url)
            self.loading_label.setText("Link copied")

    def open_link(self) -> None:
        if self.last_source_url:
            webbrowser.open(self.last_source_url)
