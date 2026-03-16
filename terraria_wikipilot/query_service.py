from __future__ import annotations

"""Query orchestration for Terraria Wikipilot."""

import logging
import re
from difflib import SequenceMatcher

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
    "which",
    "do",
    "does",
    "did",
    "i",
    "the",
    "a",
    "an",
    "to",
    "is",
    "are",
    "can",
    "for",
    "in",
    "on",
    "of",
    "from",
    "with",
    "best",
}

DEPRIORITIZED_TITLE_TERMS = {
    "ids",
    "history",
    "version",
    "console",
    "mobile",
    "old-gen",
}



def extract_keywords(query: str) -> str:
    """Extract concise search keywords from a natural-language query."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s-]", " ", query.lower())
    cleaned = cleaned.replace("cthulu", "cthulhu")
    tokens = [tok for tok in cleaned.split() if tok and tok not in STOP_WORDS]
    return " ".join(tokens)


class QueryService:
    """Runs keyword extraction, wiki search, result ranking, and page fetch."""

    def __init__(self, wiki_client: WikiClient) -> None:
        self.wiki_client = wiki_client

    def ask(self, query: str) -> QueryResponse:
        """Resolve a user question into a wiki-backed response."""
        query = query.strip()
        if not query:
            return QueryResponse(query=query, page=None, matches=[], error="Please enter a question.")

        keywords = extract_keywords(query) or query
        LOGGER.debug("Raw query: %s", query)
        LOGGER.debug("Extracted keywords: %s", keywords)

        try:
            matches = self.wiki_client.search(keywords)
            LOGGER.debug("Search results: %s", [m.title for m in matches])
        except requests.RequestException as exc:
            LOGGER.exception("Wiki search failed")
            return QueryResponse(
                query=query,
                page=None,
                matches=[],
                error=f"Could not contact Terraria Wiki (search failed): {exc}",
            )

        if not matches:
            return QueryResponse(query=query, page=None, matches=[])

        selected = self._select_best_match(keywords, matches)
        LOGGER.debug("Selected page: %s", selected.title)

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

    def _select_best_match(self, keywords: str, matches: list[SearchResult]) -> SearchResult:
        """Rank wiki search matches by exactness and useful entity preference."""
        keywords_norm = keywords.lower().strip()
        keywords_terms = [term for term in keywords_norm.split() if term]

        for result in matches:
            if result.title.lower().strip() == keywords_norm:
                return result

        for result in matches:
            title_norm = result.title.lower()
            if keywords_norm and keywords_norm in title_norm:
                return result

        ranked = sorted(
            matches,
            key=lambda result: self._rank_score(result.title, keywords_norm, keywords_terms),
            reverse=True,
        )
        return ranked[0] if ranked else matches[0]

    @staticmethod
    def _rank_score(title: str, keywords_norm: str, keywords_terms: list[str]) -> float:
        """Score a title for relevance and down-rank auxiliary pages like IDs/History."""
        title_norm = title.lower()
        ratio = SequenceMatcher(None, keywords_norm, title_norm).ratio()

        contains_terms = sum(1 for term in keywords_terms if term in title_norm)
        contains_score = contains_terms / max(len(keywords_terms), 1)

        penalty = 0.35 if any(term in title_norm for term in DEPRIORITIZED_TITLE_TERMS) else 0.0
        return (ratio * 0.65) + (contains_score * 0.35) - penalty
