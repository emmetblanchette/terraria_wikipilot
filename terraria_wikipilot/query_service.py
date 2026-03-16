from __future__ import annotations

"""Query orchestration for Terraria Wikipilot."""

import logging
import re
from typing import TypedDict

import requests

from terraria_wikipilot.models import QueryResponse, SearchResult
from terraria_wikipilot.wiki_client import WikiClient

LOGGER = logging.getLogger(__name__)

STOP_WORDS = {
    "how",
    "what",
    "where",
    "when",
    "why",
    "do",
    "i",
    "the",
    "a",
    "an",
    "is",
    "are",
    "can",
}

DEPRIORITIZED_TITLE_TERMS = {
    "ids",
    "history",
    "version",
    "console",
    "mobile",
    "old-gen",
}


class QueryInfo(TypedDict):
    """Normalized query data used by the resolver pipeline."""

    original: str
    keywords: list[str]
    entity_guess: str | None



def normalize_query(query: str) -> QueryInfo:
    """Normalize user text into keywords and a likely entity guess."""
    lowered = query.lower().replace("cthulu", "cthulhu")
    cleaned = re.sub(r"[^a-z0-9\s-]", " ", lowered)
    tokens = [token for token in cleaned.split() if token and token not in STOP_WORDS]

    entity_tokens = [token for token in tokens if token not in {"summon", "drop", "drops", "craft", "obtain", "get"}]
    entity_guess = " ".join(entity_tokens[:4]).strip() or None

    return {
        "original": query,
        "keywords": tokens,
        "entity_guess": entity_guess,
    }


def extract_keywords(query: str) -> str:
    """Backward-compatible helper that returns keyword text."""
    return " ".join(normalize_query(query)["keywords"])


class QueryService:
    """Runs normalization, page resolution, ranking, fetch, and response assembly."""

    def __init__(self, wiki_client: WikiClient) -> None:
        self.wiki_client = wiki_client
        self._resolved_cache: dict[str, str] = {}

    def ask(self, query: str) -> QueryResponse:
        """Resolve a user question into a wiki-backed response."""
        query = query.strip()
        if not query:
            return QueryResponse(query=query, page=None, matches=[], error="Please enter a question.")

        query_info = normalize_query(query)
        normalized_key = " ".join(query_info["keywords"]) or query.lower().strip()
        LOGGER.debug("Query: %s", query)
        LOGGER.debug("Normalized: %s", normalized_key)

        if normalized_key in self._resolved_cache:
            cached_title = self._resolved_cache[normalized_key]
            LOGGER.debug("Cache hit for '%s': %s", normalized_key, cached_title)
            try:
                page = self.wiki_client.fetch_page(cached_title, user_query=query)
                return QueryResponse(query=query, page=page, matches=[])
            except requests.RequestException as exc:
                LOGGER.warning("Cached page fetch failed, continuing with fresh resolve: %s", exc)

        try:
            selected, matches = self.resolve_wiki_page(query_info)
        except requests.RequestException as exc:
            LOGGER.exception("Wiki resolve failed")
            return QueryResponse(
                query=query,
                page=None,
                matches=[],
                error=f"Could not contact Terraria Wiki: {exc}",
            )

        if not selected:
            return QueryResponse(query=query, page=None, matches=matches)

        self._resolved_cache[normalized_key] = selected.title
        LOGGER.debug("Selected: %s", selected.title)

        try:
            page = self.wiki_client.fetch_page(selected.title, user_query=query)
            return QueryResponse(query=query, page=page, matches=matches)
        except requests.RequestException as exc:
            LOGGER.exception("Wiki page fetch failed")
            return QueryResponse(
                query=query,
                page=None,
                matches=matches,
                error=f"Found results but could not fetch page content: {exc}",
            )
        except (KeyError, ValueError) as exc:
            LOGGER.exception("Wiki response parse failed")
            return QueryResponse(
                query=query,
                page=None,
                matches=matches,
                error=f"Wiki response had unexpected format: {exc}",
            )

    def resolve_wiki_page(self, query_info: QueryInfo) -> tuple[SearchResult | None, list[SearchResult]]:
        """Resolve the best wiki page with direct fetch then ranked search."""
        entity_guess = query_info.get("entity_guess")
        keywords = query_info.get("keywords", [])
        keyword_query = " ".join(keywords)

        if entity_guess:
            direct = self.wiki_client.try_direct_page(entity_guess)
            if direct:
                LOGGER.debug("Direct page resolution success: %s", direct.title)
                return direct, [direct]

        search_query = entity_guess or keyword_query or query_info["original"]
        LOGGER.debug("Search query: %s", search_query)
        matches = self.wiki_client.search(search_query)
        if not matches:
            return None, []

        scored: list[tuple[int, SearchResult]] = []
        for result in matches:
            score = self._score_result(result.title, entity_guess, keywords)
            LOGGER.debug("Result score: %s score=%s", result.title, score)
            scored.append((score, result))

        scored.sort(key=lambda item: item[0], reverse=True)
        best = scored[0][1]
        return best, matches

    @staticmethod
    def _score_result(title: str, entity_guess: str | None, keywords: list[str]) -> int:
        """Compute deterministic score for a search result title."""
        title_l = title.lower()
        score = 0

        if entity_guess and title_l == entity_guess.lower():
            score += 100
        if entity_guess and entity_guess.lower() in title_l:
            score += 60

        keyword_hits = sum(1 for keyword in keywords if keyword in title_l)
        if keywords and keyword_hits == len(keywords):
            score += 30
        elif keyword_hits > 0:
            score += 10

        if any(term in title_l for term in DEPRIORITIZED_TITLE_TERMS):
            score -= 50

        return score
