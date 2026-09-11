"""Minimal Qdrant REST client for offline indexing."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from typing import Any

from backend.ingestion.hashing import sha256_text

from .config import INDEXING_VERSION, QdrantConfig
from .embeddings import embedding_input_hash


def deterministic_point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"sih26045:{chunk_id}"))


class QdrantRestClient:
    def __init__(self, config: QdrantConfig) -> None:
        self.config = config
        self.base = config.url.rstrip("/")

    def healthcheck(self) -> None:
        self._request("GET", "/")

    def ensure_collection(self, *, vector_size: int, embedding_model: str, distance: str) -> None:
        existing = self.get_collection()
        if existing is None:
            body = {
                "vectors": {"size": vector_size, "distance": distance},
                "optimizers_config": {"default_segment_number": 2},
                "on_disk_payload": True,
            }
            self._request("PUT", f"/collections/{self.config.collection_name}", body)
            return
        vectors = existing.get("result", {}).get("config", {}).get("params", {}).get("vectors", {})
        size = vectors.get("size")
        configured_distance = vectors.get("distance")
        if size != vector_size:
            raise RuntimeError(f"Qdrant collection {self.config.collection_name} has vector size {size}, expected {vector_size}.")
        if str(configured_distance).lower() != distance.lower():
            raise RuntimeError(f"Qdrant collection {self.config.collection_name} distance is {configured_distance}, expected {distance}.")

    def get_collection(self) -> dict[str, Any] | None:
        try:
            return self._request("GET", f"/collections/{self.config.collection_name}")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            raise

    def count(self) -> int:
        result = self._request("POST", f"/collections/{self.config.collection_name}/points/count", {"exact": True})
        return int(result.get("result", {}).get("count", 0))

    def upsert_points(self, points: list[dict[str, Any]]) -> None:
        if not points:
            return
        self._request("PUT", f"/collections/{self.config.collection_name}/points?wait=true", {"points": points})

    def scroll_ids(self, limit: int = 1000) -> set[str]:
        ids: set[str] = set()
        offset: Any = None
        while True:
            body: dict[str, Any] = {"limit": limit, "with_payload": False, "with_vector": False}
            if offset is not None:
                body["offset"] = offset
            result = self._request("POST", f"/collections/{self.config.collection_name}/points/scroll", body).get("result", {})
            for point in result.get("points", []):
                ids.add(str(point["id"]))
            offset = result.get("next_page_offset")
            if offset is None:
                break
        return ids

    def delete_points(self, point_ids: list[str]) -> None:
        if point_ids:
            self._request("POST", f"/collections/{self.config.collection_name}/points/delete?wait=true", {"points": point_ids})

    def sample_payloads(self, limit: int = 5) -> list[dict[str, Any]]:
        result = self._request("POST", f"/collections/{self.config.collection_name}/points/scroll", {"limit": limit, "with_payload": True, "with_vector": False})
        return [p.get("payload", {}) for p in result.get("result", {}).get("points", [])]

    def iter_payloads(self, limit: int = 1000) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        offset: Any = None
        while True:
            body: dict[str, Any] = {"limit": limit, "with_payload": True, "with_vector": False}
            if offset is not None:
                body["offset"] = offset
            result = self._request("POST", f"/collections/{self.config.collection_name}/points/scroll", body).get("result", {})
            payloads.extend(p.get("payload", {}) for p in result.get("points", []))
            offset = result.get("next_page_offset")
            if offset is None:
                break
        return payloads

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["api-key"] = self.config.api_key
        request = urllib.request.Request(f"{self.base}{path}", data=data, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else {}


def build_payload(chunk: dict[str, Any]) -> dict[str, Any]:
    provenance = chunk.get("provenance", {})
    metadata = chunk.get("metadata", {})
    return {
        "indexing_version": INDEXING_VERSION,
        "chunk_id": chunk["chunk_id"],
        "document_id": chunk["document_id"],
        "dataset_id": chunk["dataset_id"],
        "document_name": chunk["document_name"],
        "text": chunk["text"],
        "embedding_text_hash": embedding_input_hash(chunk["embedding_text"]),
        "document_type": metadata.get("document_type"),
        "jurisdiction": metadata.get("jurisdiction"),
        "legal_domains": metadata.get("legal_domains", []),
        "provenance": provenance,
        "source_path": provenance.get("relative_path"),
        "page_start": provenance.get("pdf_page_start"),
        "page_end": provenance.get("pdf_page_end"),
        "printed_page_start": provenance.get("printed_page_start"),
        "printed_page_end": provenance.get("printed_page_end"),
        "section": provenance.get("section"),
        "subsection": provenance.get("subsection"),
        "article": provenance.get("article"),
        "chapter": provenance.get("chapter"),
        "content_collision": chunk.get("indexing", {}).get("content_collision", False),
        "collision_group_id": chunk.get("indexing", {}).get("collision_group_id"),
    }


def sync_qdrant(chunks: list[dict[str, Any]], embeddings_by_chunk: dict[str, list[float]], config: QdrantConfig, *, vector_size: int, embedding_model: str) -> int:
    client = QdrantRestClient(config)
    client.healthcheck()
    client.ensure_collection(vector_size=vector_size, embedding_model=embedding_model, distance=config.distance)
    expected_ids = {deterministic_point_id(chunk["chunk_id"]) for chunk in chunks}
    existing_ids = client.scroll_ids()
    orphaned = sorted(existing_ids - expected_ids)
    for start in range(0, len(orphaned), config.upsert_batch_size):
        client.delete_points(orphaned[start : start + config.upsert_batch_size])
    batch: list[dict[str, Any]] = []
    for chunk in chunks:
        batch.append({"id": deterministic_point_id(chunk["chunk_id"]), "vector": embeddings_by_chunk[chunk["chunk_id"]], "payload": build_payload(chunk)})
        if len(batch) >= config.upsert_batch_size:
            client.upsert_points(batch)
            batch.clear()
    if batch:
        client.upsert_points(batch)
    return client.count()
