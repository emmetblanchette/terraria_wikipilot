from __future__ import annotations

import logging
import threading
from collections.abc import Callable

import keyboard

LOGGER = logging.getLogger(__name__)


class HotkeyManager:
    def __init__(self, hotkey: str, callback: Callable[[], None]) -> None:
        self.hotkey = hotkey
        self.callback = callback
        self._hotkey_id: int | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        try:
            self._hotkey_id = keyboard.add_hotkey(self.hotkey, self._on_hotkey)
            LOGGER.info("Registered global hotkey: %s", self.hotkey)
        except Exception:
            LOGGER.exception("Failed to register hotkey %s", self.hotkey)

    def stop(self) -> None:
        with self._lock:
            if self._hotkey_id is not None:
                keyboard.remove_hotkey(self._hotkey_id)
                self._hotkey_id = None

    def _on_hotkey(self) -> None:
        with self._lock:
            self.callback()
