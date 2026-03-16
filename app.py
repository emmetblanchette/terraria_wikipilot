from __future__ import annotations

"""Application entrypoint for Terraria Wikipilot overlay."""

import sys

from PySide6.QtWidgets import QApplication

from terraria_wikipilot.config import load_config
from terraria_wikipilot.hotkey_manager import HotkeyManager
from terraria_wikipilot.logging_utils import setup_logging
from terraria_wikipilot.overlay.window import OverlayWindow
from terraria_wikipilot.query_service import QueryService


def main() -> int:
    """Start the Qt app and wire all services."""
    setup_logging()
    config = load_config()

    app = QApplication(sys.argv)
    query_service = QueryService()

    window = OverlayWindow(config, query_service)
    hotkey_manager = HotkeyManager(config.hotkey, window.toggle_visible)
    hotkey_ok = hotkey_manager.start()
    if not hotkey_ok and hotkey_manager.error_message:
        window.answer_box.setPlainText(hotkey_manager.error_message)
        window.set_status_message("Global hotkey unavailable")

    window.show()
    exit_code = app.exec()

    hotkey_manager.stop()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
