from __future__ import annotations

"""Lightweight semantic retrieval index for local Terraria wiki chunks."""

import json
import logging
import math
import pickle
import re
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


class RAGIndex:
    """Loads wiki chunks, builds embeddings, and serves semantic top-k search."""

    def __init__(
        self,
        chunks_path: str = "data/wiki_chunks.json",
        embeddings_path: str = "data/wiki_embeddings.pkl",
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.chunks_path = Path(chunks_path)
        self.embeddings_path = Path(embeddings_path)
        self.model_name = model_name
        self.chunks: list[dict[str, str]] = []
        self.embeddings: list[list[float]] = []
        self._model: Any | None = None
        self._load()

    def _load(self) -> None:
        if not self.chunks_path.exists():
            LOGGER.warning("Chunks file missing: %s", self.chunks_path)
            self.chunks = []
            self.embeddings = []
            return

        self.chunks = json.loads(self.chunks_path.read_text())
        cached = self._load_cached_embeddings()
        if cached is not None:
            self.embeddings = cached
            return

        self.embeddings = self._encode_texts([self._chunk_to_text(chunk) for chunk in self.chunks])
        self._save_cached_embeddings(self.embeddings)

    def _load_cached_embeddings(self) -> list[list[float]] | None:
        if not self.embeddings_path.exists():
            return None

        try:
            payload = pickle.loads(self.embeddings_path.read_bytes())
            if payload.get("chunks_count") == len(self.chunks):
                LOGGER.info("Loaded cached embeddings from %s", self.embeddings_path)
                return payload.get("embeddings", [])
        except Exception:
            LOGGER.exception("Failed reading cached embeddings, rebuilding")
        return None

    def _save_cached_embeddings(self, embeddings: list[list[float]]) -> None:
        try:
            self.embeddings_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"chunks_count": len(self.chunks), "embeddings": embeddings}
            self.embeddings_path.write_bytes(pickle.dumps(payload))
            LOGGER.info("Saved embeddings cache to %s", self.embeddings_path)
        except Exception:
            LOGGER.exception("Failed saving embeddings cache")

    def _encode_texts(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        if model is None:
            return [self._cheap_embed(text) for text in texts]

        vectors = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]

    def _get_model(self):
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            LOGGER.info("Loaded sentence-transformers model: %s", self.model_name)
            return self._model
        except Exception:
            LOGGER.warning("sentence-transformers unavailable, using lexical fallback embeddings")
            return None

    @staticmethod
    def _cheap_embed(text: str) -> list[float]:
        terms = re.findall(r"[a-z0-9]+", text.lower())
        bins = [0.0] * 64
        for term in terms:
            bins[hash(term) % 64] += 1.0
        norm = math.sqrt(sum(v * v for v in bins)) or 1.0
        return [v / norm for v in bins]

    @staticmethod
    def _chunk_to_text(chunk: dict[str, str]) -> str:
        return f"{chunk.get('title', '')} {chunk.get('section', '')} {chunk.get('text', '')}".strip()

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    def search(self, query: str, k: int = 5) -> list[dict[str, str]]:
        """Return top-k most relevant chunks."""
        if not self.chunks or not self.embeddings:
            return []

        model = self._get_model()
        q_vec = (
            model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0].tolist()
            if model is not None
            else self._cheap_embed(query)
        )

        scored = [
            (self._cosine(q_vec, chunk_vec), chunk)
            for chunk, chunk_vec in zip(self.chunks, self.embeddings)
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in scored[:k]]
