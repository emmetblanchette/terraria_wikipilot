from __future__ import annotations

"""RAG query pipeline: normalize -> retrieve -> rank -> answer."""

import logging
import re
from dataclasses import dataclass

from terraria_wikipilot.rag_index import RAGIndex

LOGGER = logging.getLogger(__name__)

FILLER_WORDS = {
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
    "to",
}

PREFERRED_SECTIONS = ("Summoning", "Crafting", "Obtaining", "Drops")


@dataclass(slots=True)
class PipelineAnswer:
    title: str
    section: str
    bullets: list[str]
    source_url: str
    chunks: list[dict[str, str]]



def normalize_query(query: str) -> str:
    """Normalize query into concise search terms."""
    lowered = query.lower().replace("cthulu", "cthulhu")
    cleaned = re.sub(r"[^a-z0-9\s-]", " ", lowered)
    tokens = [tok for tok in cleaned.split() if tok and tok not in FILLER_WORDS]

    entity_tokens = [tok for tok in tokens if tok not in {"summon", "craft", "obtain", "drop", "drops"}]
    if entity_tokens and any(tok in tokens for tok in {"summon", "craft", "obtain", "drop", "drops"}):
        action = [tok for tok in tokens if tok in {"summon", "craft", "obtain", "drop", "drops"}][0]
        return " ".join(entity_tokens + [action])

    return " ".join(tokens)


class QueryPipeline:
    """Executes local RAG retrieval and concise answer generation."""

    def __init__(self, index: RAGIndex | None = None) -> None:
        self.index = index or RAGIndex()

    def answer(self, query: str) -> PipelineAnswer | None:
        normalized = normalize_query(query)
        LOGGER.debug("Query: %s", query)
        LOGGER.debug("Normalized: %s", normalized)

        chunks = self.index.search(normalized or query, k=5)
        LOGGER.debug("Top retrieved chunks: %s", [f"{c.get('title')}::{c.get('section')}" for c in chunks])
        if not chunks:
            return None

        ranked = sorted(chunks, key=self._chunk_rank, reverse=True)
        selected = ranked[0]
        LOGGER.debug(
            "Selected answer chunks: %s",
            [f"{c.get('title')}::{c.get('section')}" for c in ranked[:3]],
        )

        title = selected.get("title", "Terraria Wiki")
        section = selected.get("section", "Summary")

        same_topic = [chunk for chunk in ranked if chunk.get("title") == title][:3]
        bullet_lines = self._collect_bullets(same_topic)

        return PipelineAnswer(
            title=title,
            section=section,
            bullets=bullet_lines,
            source_url=f"https://terraria.wiki.gg/wiki/{title.replace(' ', '_')}",
            chunks=ranked,
        )

    @staticmethod
    def _chunk_rank(chunk: dict[str, str]) -> int:
        heading = chunk.get("section", "")
        if heading in PREFERRED_SECTIONS:
            return 100 - PREFERRED_SECTIONS.index(heading) * 10
        return 10

    @staticmethod
    def _collect_bullets(chunks: list[dict[str, str]]) -> list[str]:
        text = " ".join(chunk.get("text", "") for chunk in chunks)
        clean = re.sub(r"\[\d+\]", "", text)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|;", clean) if len(s.strip()) > 8]
        bullets: list[str] = []
        for sentence in sentences:
            if sentence not in bullets:
                bullets.append(sentence.rstrip("."))
            if len(bullets) >= 5:
                break
        return bullets
