from __future__ import annotations

"""Build local Terraria wiki dataset and retrieval chunks."""

import json
import logging
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

API_URL = "https://terraria.wiki.gg/api.php"
DATA_DIR = Path("data")
PAGES_PATH = DATA_DIR / "wiki_pages.json"
CHUNKS_PATH = DATA_DIR / "wiki_chunks.json"

SEED_PAGES = [
    # Bosses
    "Eye of Cthulhu",
    "Duke Fishron",
    "Queen Bee",
    "Wall of Flesh",
    # Items
    "Suspicious Looking Eye",
    "Truffle Worm",
    "Obsidian",
    "Molten Armor",
    # NPCs
    "Guide",
    "Goblin Tinkerer",
    "Nurse",
    # Biomes
    "Ocean",
    "Corruption",
    "Crimson",
    "Jungle",
    # Events / mechanics
    "Blood Moon",
    "Goblin Army",
    "Hardmode",
    "Crafting",
]

LOGGER = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


def fetch_page_html(title: str, timeout: int = 12) -> str | None:
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
    }
    try:
        response = requests.get(API_URL, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        return payload.get("parse", {}).get("text", {}).get("*")
    except Exception:
        LOGGER.exception("Failed to fetch page: %s", title)
        return None


def clean_text(text: str) -> str:
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_page_content(title: str, html: str) -> dict[str, object]:
    soup = BeautifulSoup(html, "html.parser")

    intro = ""
    for paragraph in soup.select("p"):
        txt = clean_text(paragraph.get_text(" ", strip=True))
        if len(txt) > 80:
            intro = txt
            break

    sections: list[dict[str, str]] = []
    if intro:
        sections.append({"heading": "Intro", "content": intro})

    for header in soup.select("h2, h3"):
        heading = clean_text(header.get_text(" ", strip=True).replace("[edit]", ""))
        if not heading:
            continue

        parts: list[str] = []
        for sibling in header.find_next_siblings():
            if sibling.name in {"h2", "h3"}:
                break
            txt = clean_text(sibling.get_text(" ", strip=True))
            if txt:
                parts.append(txt)
            if len(" ".join(parts)) > 1200:
                break

        content = clean_text(" ".join(parts))
        if len(content) > 40:
            sections.append({"heading": heading, "content": content})

    return {"title": title, "sections": sections}


def build_chunks(pages: list[dict[str, object]]) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    for page in pages:
        title = str(page.get("title", ""))
        for section in page.get("sections", []):
            heading = str(section.get("heading", ""))
            content = str(section.get("content", ""))
            if not content:
                continue
            chunks.append({"title": title, "section": heading, "text": content})
    return chunks


def main() -> int:
    setup_logging()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    pages: list[dict[str, object]] = []
    for title in SEED_PAGES:
        html = fetch_page_html(title)
        if not html:
            continue
        pages.append(extract_page_content(title, html))
        LOGGER.info("Indexed page: %s", title)

    PAGES_PATH.write_text(json.dumps(pages, indent=2))
    LOGGER.info("Wrote %s", PAGES_PATH)

    chunks = build_chunks(pages)
    CHUNKS_PATH.write_text(json.dumps(chunks, indent=2))
    LOGGER.info("Wrote %s", CHUNKS_PATH)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
