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
            results.append(SearchResult(title=row["title"], pageid=row["pageid"], snippet=snippet))
        return results

    def try_direct_page(self, title_guess: str) -> SearchResult | None:
        """Try direct parse by guessed entity title; return minimal result if found."""
        try_title = title_guess.strip().replace("_", " ").title()
        params = {
            "action": "parse",
            "page": try_title.replace(" ", "_"),
            "prop": "text",
            "format": "json",
        }
        response = self.session.get(self.API_URL, params=params, timeout=self.timeout_seconds)
        if response.status_code >= 400:
            return None
        payload = response.json()
        parse_data = payload.get("parse")
        if not parse_data:
            return None
        resolved_title = parse_data.get("title", try_title)
        return SearchResult(title=resolved_title, pageid=0, snippet="Direct entity match")

    def fetch_page(self, title: str, user_query: str = "") -> WikiPage:
        """Fetch and parse a page with structured section extraction."""
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
        summary = self.extract_relevant_section(user_query, sections, soup)

        url_title = title.replace(" ", "_")
        return WikiPage(
            title=title,
            url=f"{self.WIKI_BASE}{url_title}",
            summary=summary,
            sections=self._extract_interesting_sections(sections),
        )

    def extract_relevant_section(self, user_query: str, sections: dict[str, str], soup: BeautifulSoup) -> str:
        """Choose and clean the most relevant section body for the given question."""
        query_l = user_query.lower()

        if any(term in query_l for term in {"summon", "spawn", "boss"}):
            for candidate in ("Summoning", "Spawn", "Spawning"):
                if candidate in sections:
                    return self._clean_and_limit_text(sections[candidate])

        if any(term in query_l for term in {"item", "craft", "obtain", "get"}):
            for candidate in ("Obtaining", "Crafting"):
                if candidate in sections:
                    return self._clean_and_limit_text(sections[candidate])

        return self._clean_and_limit_text(self._extract_intro_paragraph(soup))

    @staticmethod
    def _extract_intro_paragraph(soup: BeautifulSoup) -> str:
        """Extract first substantial intro paragraph text."""
        for paragraph in soup.select("p"):
            text = paragraph.get_text(" ", strip=True)
            if len(text) > 80:
                return text
        return "No concise summary was found on this page."

    @staticmethod
    def _clean_and_limit_text(text: str, sentence_limit: int = 3) -> str:
        """Remove citations/formatting and keep about N complete sentences."""
        clean = re.sub(r"\[\d+\]", "", text)
        clean = re.sub(r"\s+", " ", clean).strip()
        sentences = re.split(r"(?<=[.!?])\s+", clean)
        selected = [s.strip() for s in sentences if s.strip()][:sentence_limit]
        if not selected:
            return clean[:400]
        result = " ".join(selected)
        if result and result[-1] not in ".!?":
            result += "."
        return result

    @staticmethod
    def _collect_sections(soup: BeautifulSoup) -> dict[str, str]:
        """Collect plain text for each h2/h3 section heading."""
        sections: dict[str, str] = {}
        for header in soup.select("h2, h3"):
            title = header.get_text(" ", strip=True).replace("[edit]", "").strip()
            if not title:
                continue

            parts: list[str] = []
            for sib in header.find_next_siblings():
                if sib.name in {"h2", "h3"}:
                    break
                text = sib.get_text(" ", strip=True)
                if text:
                    parts.append(text)
                if len(" ".join(parts)) > 1200:
                    break

            if parts:
                sections[title] = " ".join(parts)

        return sections

    @staticmethod
    def _extract_interesting_sections(sections: dict[str, str]) -> dict[str, str]:
        """Return concise gameplay-helpful sections for secondary display."""
        interesting = {"Summoning", "Spawn", "Spawning", "Obtaining", "Crafting", "Drops", "Notes"}
        picked: dict[str, str] = {}
        for name, body in sections.items():
            if name in interesting:
                picked[name] = WikiClient._clean_and_limit_text(body)
        return picked
