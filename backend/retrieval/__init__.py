"""Retrieval module for IP-SAKTI Sahayak.

Submodules:
    query       — Query processing and legal reference detection
    models      — RetrievedChunk data model with full provenance
    bm25        — BM25 retriever over persisted index
    dense       — Dense retriever via Qdrant
    hybrid      — Hybrid RRF retriever
    filters     — Optional metadata filtering
    config      — Configuration dataclasses
"""
