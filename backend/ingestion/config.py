"""Shared ingestion configuration."""

from __future__ import annotations

CORPUS_ID = "SIH26045"
PROCESSOR_VERSION = "1.0.0"

DATASET_DESCRIPTIONS = {
    "Dataset_1": "Indian statutory/legal foundation documents",
    "Dataset_2": "Drugs, cosmetics, consumer/regulatory documents",
    "Dataset_3_TK": "Traditional Knowledge documents",
    "Dataset_4_International": "International treaties and international TK/biodiversity documents",
    "Dataset_5_CaseLaw": "Case-law, manuals, practice/procedure, and case-study documents",
}

CONTROLLED_DOCUMENT_TYPES = {
    "Statute",
    "Amendment",
    "Rule",
    "Regulation",
    "Notification",
    "Treaty",
    "Protocol",
    "Guideline",
    "Manual",
    "Case_Law",
    "Case_Study",
    "Government_Document",
    "Other",
}

