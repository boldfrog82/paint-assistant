"""Lightweight retrieval helpers used by the AI chat endpoint."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence

from .build_index import DEFAULT_INDEX_PATH


@dataclass
class RetrievedChunk:
    """Represents a piece of context retrieved for a query."""

    text: str
    score: float
    metadata: Dict[str, Any]


def _normalise_text(value: str) -> str:
    return " ".join(value.lower().split())


class RetrievalPipeline:
    """Simple retriever that scores pre-built text chunks."""

    def __init__(self, *, index_path: Path | None = None) -> None:
        path = index_path or DEFAULT_INDEX_PATH
        if not path.exists():
            raise FileNotFoundError(
                "Retrieval index not found. Run 'python -m src.rag.build_index' first."
            )

        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)

        self._records: List[Dict[str, Any]] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            text = str(entry.get("text", ""))
            metadata = entry.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
            self._records.append({"text": text, "metadata": dict(metadata)})

    @staticmethod
    def _score_text(text: str, tokens: Sequence[str]) -> float:
        lowered = text.lower()
        score = 0.0
        for token in tokens:
            if not token:
                continue
            occurrences = lowered.count(token)
            if occurrences:
                score += float(occurrences)
        return score

    def get_contexts(
        self,
        query: str,
        *,
        top_k: int = 18,
        rerank_k: int = 5,
    ) -> List[RetrievedChunk]:
        """Return the highest scoring chunks for *query*."""

        del rerank_k  # The pipeline is intentionally simple for now.

        tokens = [token for token in _normalise_text(query).split() if token]
        if not tokens:
            return []

        ranked: List[RetrievedChunk] = []
        for record in self._records:
            text = record.get("text", "")
            metadata = record.get("metadata", {})
            score = self._score_text(text, tokens)
            if score <= 0:
                continue
            ranked.append(
                RetrievedChunk(
                    text=text,
                    score=score,
                    metadata=dict(metadata),
                )
            )

        if not ranked:
            # Fall back to the first few records to provide context even without matches.
            for record in self._records[:top_k]:
                ranked.append(
                    RetrievedChunk(
                        text=record.get("text", ""),
                        score=0.0,
                        metadata=dict(record.get("metadata", {})),
                    )
                )

        ranked.sort(key=lambda chunk: chunk.score, reverse=True)
        return ranked[:top_k]


__all__ = ["RetrievedChunk", "RetrievalPipeline", "DEFAULT_INDEX_PATH"]
