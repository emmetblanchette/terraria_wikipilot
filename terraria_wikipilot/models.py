from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SearchResult:
    title: str
    pageid: int
    snippet: str


@dataclass(slots=True)
class WikiPage:
    title: str
    url: str
    summary: str
    sections: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class QueryResponse:
    query: str
    page: WikiPage | None
    matches: list[SearchResult]
    error: str | None = None
