from __future__ import annotations

"""Global hotkey management with platform-specific diagnostics."""

import logging
import platform
import threading
from collections.abc import Callable

import keyboard

LOGGER = logging.getLogger(__name__)

MACOS_ACCESSIBILITY_MESSAGE = (
    "Global hotkeys require Accessibility permission.\n"
    "Add Terminal or Python to:\n"
    "System Settings → Privacy & Security → Accessibility"
)


class HotkeyManager:
    """Registers and unregisters the global overlay hotkey."""

    def __init__(self, hotkey: str, callback: Callable[[], None]) -> None:
        self.hotkey = hotkey
        self.callback = callback
        self._hotkey_id: int | None = None
        self._lock = threading.Lock()
        self.error_message: str | None = None

    def start(self) -> bool:
        """Start listening for global hotkeys. Returns True on success."""
        try:
            self._hotkey_id = keyboard.add_hotkey(self.hotkey, self._on_hotkey)
            LOGGER.info("Registered global hotkey: %s", self.hotkey)
            self.error_message = None
            return True
        except Exception as exc:
            LOGGER.exception("Failed to register hotkey %s", self.hotkey)
            if platform.system() == "Darwin":
                self.error_message = MACOS_ACCESSIBILITY_MESSAGE
            else:
                self.error_message = (
                    f"Could not register global hotkey '{self.hotkey}'. "
                    f"Reason: {exc}"
                )
            return False

    def stop(self) -> None:
        """Stop listening for global hotkeys."""
        with self._lock:
            if self._hotkey_id is not None:
                keyboard.remove_hotkey(self._hotkey_id)
                self._hotkey_id = None

    def _on_hotkey(self) -> None:
        with self._lock:
            self.callback()
