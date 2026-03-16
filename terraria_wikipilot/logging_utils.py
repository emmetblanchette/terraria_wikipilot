"""Logging utilities for Terraria Wikipilot."""

from __future__ import annotations

import logging
import os


def setup_logging() -> None:
    """Configure application logging level and format."""
    level_name = os.getenv("WIKIPILOT_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
