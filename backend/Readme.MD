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
