from __future__ import annotations

"""Query service that answers from local RAG knowledge base."""

import logging

from terraria_wikipilot.models import QueryResponse, SearchResult, WikiPage
from terraria_wikipilot.query_pipeline import QueryPipeline

LOGGER = logging.getLogger(__name__)


class QueryService:
    """Uses local retrieval pipeline instead of live wiki search."""

    def __init__(self, _wiki_client=None, query_pipeline: QueryPipeline | None = None) -> None:
        self.query_pipeline = query_pipeline or QueryPipeline()

    def ask(self, query: str) -> QueryResponse:
        """Answer the user question from local indexed wiki chunks."""
        query = query.strip()
        if not query:
            return QueryResponse(query=query, page=None, matches=[], error="Please enter a question.")

        answer = self.query_pipeline.answer(query)
        if not answer:
            return QueryResponse(
                query=query,
                page=None,
                matches=[],
                error=(
                    "No local wiki knowledge available. Run `python build_knowledge_base.py` "
                    "to index pages first."
                ),
            )

        sections = {answer.section: " ".join(f"• {line}" for line in answer.bullets)} if answer.bullets else {}
        page = WikiPage(
            title=answer.title,
            url=answer.source_url,
            summary=(answer.bullets[0] if answer.bullets else "No concise answer available."),
            sections=sections,
        )

        matches = [SearchResult(title=chunk.get("title", ""), pageid=0, snippet=chunk.get("section", "")) for chunk in answer.chunks[:5]]
        return QueryResponse(query=query, page=page, matches=matches)
