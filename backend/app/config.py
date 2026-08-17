import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR.parent / "data"))
OUTPUT_DIR = DATA_DIR / "processed"
UPLOAD_DIR = DATA_DIR / "raw"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# "rules" works out of the box (no model download).
# Set to "ml" once you've trained a model (see /training) and point
# CHECKPOINT_PATH at the resulting checkpoint directory.
EXTRACTION_BACKEND = os.getenv("EXTRACTION_BACKEND", "rules")
CHECKPOINT_PATH = os.getenv("CHECKPOINT_PATH", "")

OCR_LANG = os.getenv("OCR_LANG", "eng")
OCR_DPI = int(os.getenv("OCR_DPI", "300"))

REVIEW_THRESHOLD = float(os.getenv("REVIEW_THRESHOLD", "0.85"))
