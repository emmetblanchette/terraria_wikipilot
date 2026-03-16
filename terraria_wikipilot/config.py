from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(slots=True)
class AppConfig:
    hotkey: str = "ctrl+alt+t"
    width: int = 420
    expanded_height: int = 360
    collapsed_height: int = 46
    margin: int = 18
    opacity: float = 0.94
    request_timeout_seconds: int = 8
    search_limit: int = 5


def load_config() -> AppConfig:
    load_dotenv()
    return AppConfig(
        hotkey=os.getenv("WIKIPILOT_HOTKEY", "ctrl+alt+t"),
        width=int(os.getenv("WIKIPILOT_WIDTH", "420")),
        expanded_height=int(os.getenv("WIKIPILOT_EXPANDED_HEIGHT", "360")),
        collapsed_height=int(os.getenv("WIKIPILOT_COLLAPSED_HEIGHT", "46")),
        margin=int(os.getenv("WIKIPILOT_MARGIN", "18")),
        opacity=float(os.getenv("WIKIPILOT_OPACITY", "0.94")),
        request_timeout_seconds=int(os.getenv("WIKIPILOT_REQUEST_TIMEOUT", "8")),
        search_limit=int(os.getenv("WIKIPILOT_SEARCH_LIMIT", "5")),
    )
