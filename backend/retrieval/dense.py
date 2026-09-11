"""Dense (semantic) retriever backed by Qdrant.

Uses the same embedding model/config that was used during indexing so that
query vectors are in the same space as indexed vectors.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.indexing.config import EmbeddingConfig, QdrantConfig
from backend.indexing.embeddings import make_embedder, Embedder
from backend.indexing.qdrant_index import QdrantRestClient

from .models import RetrievedChunk

LOG = logging.getLogger(__name__)


class DenseRetriever:
    """Embeds a query and searches Qdrant for nearest-neighbour chunks."""

    def __init__(
        self,
        qdrant_config: QdrantConfig | None = None,
        embedding_config: EmbeddingConfig | None = None,
        *,
        embedder: Embedder | None = None,
    ) -> None:
        if qdrant_config is None:
            qdrant_config = QdrantConfig()
        if embedding_config is None:
            embedding_config = EmbeddingConfig()

        self.client = QdrantRestClient(qdrant_config)
        self.collection = qdrant_config.collection_name
        self.embedder = embedder or make_embedder(embedding_config)
        LOG.info(
            "DenseRetriever: collection=%s, embedder=%s, dim=%d",
            self.collection,
            embedding_config.model,
            self.embedder.dimension,
        )

    def search(
        self,
        query: str,
        top_k: int = 30,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """Embed *query* and search Qdrant, returning top-k results with provenance."""
        query_vector = self.embedder.encode([query])[0]

        body: dict[str, Any] = {
            "vector": query_vector,
            "limit": top_k,
            "with_payload": True,
        }
        if filters:
            body["filter"] = self._build_qdrant_filter(filters)

        response = self.client._request(
            "POST",
            f"/collections/{self.collection}/points/search",
            body,
        )
        points = response.get("result", [])

        results: list[RetrievedChunk] = []
        for rank, point in enumerate(points):
            payload = point.get("payload", {})
            score = point.get("score", 0.0)
            rc = RetrievedChunk.from_qdrant_payload(payload, score=score)
            rc.dense_rank = rank + 1
            results.append(rc)

        return results

    @staticmethod
    def _build_qdrant_filter(filters: dict[str, Any]) -> dict[str, Any]:
        """Translate simple key=value filters into Qdrant filter format."""
        must: list[dict[str, Any]] = []
        for key, value in filters.items():
            if isinstance(value, list):
                must.append({"key": key, "match": {"any": value}})
            else:
                must.append({"key": key, "match": {"value": value}})
        return {"must": must} if must else {}
