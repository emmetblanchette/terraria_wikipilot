from __future__ import annotations

import logging
import re
from html import unescape

import requests
from bs4 import BeautifulSoup

from terraria_wikipilot.models import SearchResult, WikiPage

LOGGER = logging.getLogger(__name__)


class WikiClient:
    API_URL = "https://terraria.wiki.gg/api.php"
    WIKI_BASE = "https://terraria.wiki.gg/wiki/"

    def __init__(self, timeout_seconds: int = 8, search_limit: int = 5) -> None:
        self.timeout_seconds = timeout_seconds
        self.search_limit = search_limit
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "TerrariaWikipilot/0.1"})

    def search(self, query: str) -> list[SearchResult]:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": self.search_limit,
            "format": "json",
        }
        response = self.session.get(self.API_URL, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        results: list[SearchResult] = []
        for row in payload.get("query", {}).get("search", []):
            snippet_html = row.get("snippet", "")
            snippet = BeautifulSoup(unescape(snippet_html), "html.parser").get_text(" ", strip=True)
            results.append(
                SearchResult(
                    title=row["title"],
                    pageid=row["pageid"],
                    snippet=snippet,
                )
            )
        return results

    def fetch_page(self, title: str) -> WikiPage:
        params = {
            "action": "parse",
            "page": title,
            "prop": "text",
            "format": "json",
        }
        response = self.session.get(self.API_URL, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        html = response.json()["parse"]["text"]["*"]

        soup = BeautifulSoup(html, "html.parser")
        summary = self._extract_summary(soup)
        sections = self._extract_sections(soup)
        url_title = title.replace(" ", "_")
        return WikiPage(
            title=title,
            url=f"{self.WIKI_BASE}{url_title}",
            summary=summary,
            sections=sections,
        )

    @staticmethod
    def _extract_summary(soup: BeautifulSoup) -> str:
        for paragraph in soup.select("p"):
            text = paragraph.get_text(" ", strip=True)
            if len(text) > 90:
                return re.sub(r"\s+", " ", text)
        return "No concise summary was found on this page."

    @staticmethod
    def _extract_sections(soup: BeautifulSoup) -> dict[str, str]:
        interesting = {"Drops", "Crafting", "Tips", "Notes", "History", "Trivia"}
        sections: dict[str, str] = {}
        for header in soup.select("h2, h3"):
            title = header.get_text(" ", strip=True).replace("[edit]", "").strip()
            if title not in interesting:
                continue

            pieces: list[str] = []
            for sib in header.find_next_siblings():
                if sib.name in {"h2", "h3"}:
                    break
                txt = sib.get_text(" ", strip=True)
                if txt:
                    pieces.append(txt)
                if len(" ".join(pieces)) > 400:
                    break

            if pieces:
                sections[title] = re.sub(r"\s+", " ", " ".join(pieces))[:450]
        return sections
