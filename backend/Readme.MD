# SIH26045 Backend

## Ingestion

Install:

  python -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
  # optional OCR support
  .venv/bin/python -m pip install -r requirements-ocr.txt

  Run:

  .venv/bin/python -m backend.ingestion.cli \
    --input data/raw \
    --output data/processed/embedding_ready

  Force rebuild:

  .venv/bin/python -m backend.ingestion.cli \
    --input data/raw \
    --output data/processed/embedding_ready \
    --force

## Offline Indexing

The indexing layer starts from the existing handoff artifact:

```text
data/processed/embedding_ready/chunks.jsonl
```

It does not parse PDFs and does not implement retrieval, RAG, LLM, STT, or TTS.

Install dependencies:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The default production embedding backend is Sentence Transformers with `BAAI/bge-m3`. The first run downloads the model from Hugging Face unless it is already cached locally.

Copy `.env.example` to `.env` if you want shell-level defaults, or pass CLI flags directly:

```bash
EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=32
EMBEDDING_NORMALIZE=true
```

Start local Qdrant:

```bash
docker compose -f docker-compose.qdrant.yml up -d
```

Check that it responds:

```bash
.venv/bin/python - <<'PY'
import urllib.request
print(urllib.request.urlopen("http://localhost:6333/", timeout=10).read().decode())
PY
```

Build all indexes:

```bash
.venv/bin/python -m backend.indexing.cli build
```

Validate existing indexes:

```bash
.venv/bin/python -m backend.indexing.cli validate
```

Artifacts are written to:

```text
data/processed/indexes/
  embeddings/embeddings.jsonl
  bm25/index/bm25_index.json
  bm25/metadata.json
  index_manifest.json
  index_validation_report.json
  index_validation_report.txt
```

Configuration is via environment variables or CLI flags. Important variables:

```bash
EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL=BAAI/bge-m3
# EMBEDDING_MODEL_REVISION=<optional pinned Hugging Face revision>
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=32
EMBEDDING_NORMALIZE=true

QDRANT_MODE=local
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=sih26045_chunks
QDRANT_DISTANCE=Cosine
QDRANT_UPSERT_BATCH_SIZE=128
QDRANT_TIMEOUT_SECONDS=60
```

For Qdrant Cloud:

```bash
QDRANT_MODE=cloud
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=...
QDRANT_COLLECTION_NAME=sih26045_chunks
```

Do not commit `QDRANT_API_KEY`. The index manifest records Qdrant mode, URL, collection name, distance, and batch size, but it never stores the API key.

Incremental runs reuse `data/processed/indexes/embeddings/embeddings.jsonl` when `chunk_id`, `embedding_text` hash, embedding provider, model name, model revision, normalization setting, embedding dimension, and indexing version match. Changed chunks are re-embedded, unchanged chunks are reused, and Qdrant points for chunks that disappeared from the eligible corpus are deleted from the configured collection. Use `--rebuild` to force regeneration.

Rebuild from scratch:

```bash
.venv/bin/python -m backend.indexing.cli build --rebuild
```

Build only local files without Qdrant:

```bash
.venv/bin/python -m backend.indexing.cli build --skip-qdrant
```

Validate the persisted local indexes and Qdrant payloads:

```bash
.venv/bin/python -m backend.indexing.cli validate
```

Known corpus handling:

- `Dataset_1/Patents_Act_1970_Updated.pdf` and `Dataset_1/Trade_Marks_Act_1999.pdf` are known content-collision documents. By default `INDEX_COLLISION_DOCUMENTS=true`, so both are indexed and Qdrant payloads include `content_collision=true` plus `collision_group_id`. Set `INDEX_COLLISION_DOCUMENTS=false` or pass `--index-collision-documents false` to exclude them from dense and BM25 indexes.
- `Dataset_3_TK/API_Amendment_List_2023.pdf` currently has 0 chunks due to empty extracted text/OCR unavailability. The indexing layer creates no fake embedding, BM25, or Qdrant records for it.

For constrained CI/offline environments only, a deterministic hash embedding provider is available:

```bash
.venv/bin/python -m backend.indexing.cli build \
  --embedding-provider deterministic_hash \
  --embedding-model hash-128
```

This produces deterministic dense vectors for pipeline validation, not semantic embeddings for production retrieval.
