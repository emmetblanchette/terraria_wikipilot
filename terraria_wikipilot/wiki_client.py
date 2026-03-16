from __future__ import annotations

"""Terraria Wiki API and content extraction client."""

import logging
import re
from html import unescape

import requests
from bs4 import BeautifulSoup

from terraria_wikipilot.models import SearchResult, WikiPage

LOGGER = logging.getLogger(__name__)


class WikiClient:
    """Client for searching and fetching Terraria wiki pages."""

    API_URL = "https://terraria.wiki.gg/api.php"
    WIKI_BASE = "https://terraria.wiki.gg/wiki/"

    def __init__(self, timeout_seconds: int = 8, search_limit: int = 5) -> None:
        self.timeout_seconds = timeout_seconds
        self.search_limit = search_limit
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "TerrariaWikipilot/0.1"})

    def search(self, query: str) -> list[SearchResult]:
        """Search wiki pages using MediaWiki query API."""
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

    def fetch_page(self, title: str, user_query: str = "") -> WikiPage:
        """Fetch and parse a page, prioritizing query-relevant answer text."""
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
        sections = self._collect_sections(soup)
        intro_summary = self._extract_intro_summary(soup)
        summary = self._extract_focused_summary(user_query, intro_summary, sections)
        interesting_sections = self._extract_interesting_sections(sections)

        url_title = title.replace(" ", "_")
        return WikiPage(
            title=title,
            url=f"{self.WIKI_BASE}{url_title}",
            summary=summary,
            sections=interesting_sections,
        )

    @staticmethod
    def _extract_intro_summary(soup: BeautifulSoup) -> str:
        """Extract the first substantial intro paragraph."""
        for paragraph in soup.select("p"):
            text = paragraph.get_text(" ", strip=True)
            if len(text) > 90:
                return re.sub(r"\s+", " ", text)
        return "No concise summary was found on this page."

    @staticmethod
    def _collect_sections(soup: BeautifulSoup) -> dict[str, str]:
        """Collect section text by heading name."""
        sections: dict[str, str] = {}
        for header in soup.select("h2, h3"):
            title = header.get_text(" ", strip=True).replace("[edit]", "").strip()
            if not title:
                continue

            pieces: list[str] = []
            for sib in header.find_next_siblings():
                if sib.name in {"h2", "h3"}:
                    break
                txt = sib.get_text(" ", strip=True)
                if txt:
                    pieces.append(txt)
                if len(" ".join(pieces)) > 700:
                    break

            if pieces:
                sections[title] = re.sub(r"\s+", " ", " ".join(pieces))[:700]
        return sections

    def _extract_focused_summary(
        self,
        user_query: str,
        intro_summary: str,
        sections: dict[str, str],
    ) -> str:
        """Prefer sections that best answer the user question; fallback to intro."""
        query_l = user_query.lower()
        section_names = {name.lower(): name for name in sections}

        preferred_order = self._preferred_sections_for_query(query_l, section_names)
        for section_name in preferred_order:
            body = sections.get(section_name)
            if body:
                return body[:450]

        for name, body in sections.items():
            if any(term in name.lower() for term in ["overview", "behavior", "notes", "tips"]):
                return body[:450]

        return intro_summary

    @staticmethod
    def _preferred_sections_for_query(query_l: str, section_names: dict[str, str]) -> list[str]:
        """Determine section priorities from question intent and page type clues."""
        preferred: list[str] = []

        if any(term in query_l for term in {"summon", "spawn", "boss"}):
            preferred += [section_names.get("summoning", ""), section_names.get("spawning", "")]

        if any(term in query_l for term in {"drop", "loot"}):
            preferred += [section_names.get("drops", ""), section_names.get("loot", "")]

        if any(term in query_l for term in {"craft", "recipe", "make"}):
            preferred += [section_names.get("crafting", ""), section_names.get("recipes", "")]

        if any(term in query_l for term in {"get", "obtain", "find", "farm"}):
            preferred += [section_names.get("obtaining", ""), section_names.get("acquisition", "")]

        # Generic boss/item-style priorities as backup.
        preferred += [
            section_names.get("summoning", ""),
            section_names.get("crafting", ""),
            section_names.get("obtaining", ""),
            section_names.get("drops", ""),
        ]

        return [name for name in preferred if name]

    @staticmethod
    def _extract_interesting_sections(sections: dict[str, str]) -> dict[str, str]:
        """Return concise set of gameplay-helpful sections for display."""
        interesting = {
            "Summoning",
            "Spawning",
            "Drops",
            "Loot",
            "Crafting",
            "Recipes",
            "Obtaining",
            "Tips",
            "Notes",
            "Trivia",
        }
        result: dict[str, str] = {}
        for title, body in sections.items():
            if title in interesting:
                result[title] = body[:450]
        return result
