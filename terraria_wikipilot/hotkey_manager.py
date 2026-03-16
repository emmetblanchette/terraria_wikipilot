from __future__ import annotations

"""Global hotkey management with macOS-focused reliability improvements."""

import logging
import platform
import threading
from collections.abc import Callable

import keyboard

LOGGER = logging.getLogger(__name__)

MACOS_ACCESSIBILITY_MESSAGE = (
    "Global hotkeys require Accessibility permission.\n"
    "Add your terminal or Python interpreter to:\n"
    "System Settings → Privacy & Security → Accessibility"
)


class HotkeyManager:
    """Registers and unregisters a global overlay hotkey."""

    def __init__(self, hotkey: str, callback: Callable[[], None]) -> None:
        self.hotkey = hotkey
        self.callback = callback
        self._hotkey_id: int | None = None
        self._lock = threading.Lock()
        self.error_message: str | None = None

        self._platform = platform.system()
        self._pynput_listener = None
        self._pynput_hotkey = None

    def start(self) -> bool:
        """Start global hotkey listening and return registration success."""
        LOGGER.info("Registering global hotkey %s", self.hotkey)
        if self._platform == "Darwin":
            return self._start_with_pynput()
        return self._start_with_keyboard()

    def _start_with_keyboard(self) -> bool:
        try:
            self._hotkey_id = keyboard.add_hotkey(self.hotkey, self._on_hotkey)
            LOGGER.info("Registered global hotkey with keyboard: %s", self.hotkey)
            self.error_message = None
            return True
        except Exception as exc:
            LOGGER.exception("Failed to register hotkey %s", self.hotkey)
            self.error_message = f"Could not register global hotkey '{self.hotkey}'. Reason: {exc}"
            return False

    def _start_with_pynput(self) -> bool:
        """Use pynput on macOS, which is generally more reliable than keyboard hooks."""
        try:
            from pynput import keyboard as pynput_keyboard

            self._pynput_hotkey = pynput_keyboard.HotKey(
                pynput_keyboard.HotKey.parse(self.hotkey.replace("ctrl", "<ctrl>").replace("alt", "<alt>")),
                self._on_hotkey,
            )

            def for_canonical(func):
                return lambda key: func(self._pynput_listener.canonical(key))

            self._pynput_listener = pynput_keyboard.Listener(
                on_press=for_canonical(self._pynput_hotkey.press),
                on_release=for_canonical(self._pynput_hotkey.release),
            )
            self._pynput_listener.start()
            LOGGER.info("Registered global hotkey with pynput: %s", self.hotkey)
            self.error_message = None
            return True
        except Exception:
            LOGGER.exception("Failed to register macOS hotkey %s", self.hotkey)
            self.error_message = MACOS_ACCESSIBILITY_MESSAGE
            return False

    def stop(self) -> None:
        """Stop listening for global hotkeys."""
        with self._lock:
            if self._hotkey_id is not None:
                keyboard.remove_hotkey(self._hotkey_id)
                self._hotkey_id = None
            if self._pynput_listener is not None:
                self._pynput_listener.stop()
                self._pynput_listener = None
                self._pynput_hotkey = None

    def _on_hotkey(self) -> None:
        with self._lock:
            self.callback()
