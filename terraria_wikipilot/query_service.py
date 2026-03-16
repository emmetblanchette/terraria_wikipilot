from __future__ import annotations

import logging

import requests

from terraria_wikipilot.models import QueryResponse
from terraria_wikipilot.wiki_client import WikiClient

LOGGER = logging.getLogger(__name__)


class QueryService:
    def __init__(self, wiki_client: WikiClient) -> None:
        self.wiki_client = wiki_client

    def ask(self, query: str) -> QueryResponse:
        query = query.strip()
        if not query:
            return QueryResponse(query=query, page=None, matches=[], error="Please enter a question.")

        try:
            matches = self.wiki_client.search(query)
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

        try:
            page = self.wiki_client.fetch_page(matches[0].title)
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
