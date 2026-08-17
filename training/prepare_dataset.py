"""
Helper to turn raw invoice images + OCR into the annotation formats expected
by train_smolvlm_invoice.py (JSON target) and train_layoutlmv3.py (BIO tags).

Two supported starting points:

1. SROIE dataset (recommended first dataset — small, well-labeled invoices):
   https://www.kaggle.com/datasets/urbikn/sroie-datasetv2
   Has per-image `key_value.json` files with ground-truth fields already,
   so this script just reshapes them into our JSONL formats.

2. Your own scanned invoices with no labels yet:
   Use Label Studio (https://labelstud.io) to draw bounding boxes and tag
   fields by hand, export as JSON, then adapt `convert_label_studio_export`
   below to match your export schema.

USAGE (Colab):
    !python prepare_dataset.py --source sroie \
        --sroie_dir /content/SROIE2019 \
        --output_dir /content/invoice_dataset

This produces:
    output_dir/
      images/                  (copied/renamed images)
      annotations.jsonl        (for SmolVLM training)
      train.jsonl, val.jsonl   (BIO-tagged, for LayoutLMv3 training)
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
from pathlib import Path

import pytesseract
from PIL import Image

FIELD_MAP = {
    "company": "vendor_name",
    "address": "vendor_address",
    "date": "invoice_date",
    "total": "grand_total",
}


def convert_sroie(sroie_dir: str, output_dir: str, val_split: float = 0.15):
    sroie_dir = Path(sroie_dir)
    output_dir = Path(output_dir)
    (output_dir / "images").mkdir(parents=True, exist_ok=True)

    img_dir = sroie_dir / "train" / "img"
    entities_dir = sroie_dir / "train" / "entities"

    smolvlm_records = []
    layoutlm_records = []

    image_files = sorted(img_dir.glob("*.jpg"))
    print(f"Found {len(image_files)} SROIE training images")

    for img_path in image_files:
        entity_path = entities_dir / f"{img_path.stem}.txt"
        if not entity_path.exists():
            continue

        raw_fields = json.loads(entity_path.read_text(encoding="utf-8"))
        fields = {FIELD_MAP.get(k, k): v for k, v in raw_fields.items()}

        dest_name = img_path.name
        shutil.copy(img_path, output_dir / "images" / dest_name)

        # --- SmolVLM-style record (whole-image -> JSON) ---
        smolvlm_records.append({"image": dest_name, "fields": fields})

        # --- LayoutLMv3-style record (word + bbox + BIO label) ---
        words, boxes, labels = _bio_tag_from_ocr(img_path, fields)
        layoutlm_records.append(
            {"image": dest_name, "words": words, "boxes": boxes, "labels": labels}
        )

    random.seed(42)
    random.shuffle(layoutlm_records)
    split_idx = int(len(layoutlm_records) * (1 - val_split))
    train_records, val_records = layoutlm_records[:split_idx], layoutlm_records[split_idx:]

    _write_jsonl(output_dir / "annotations.jsonl", smolvlm_records)
    _write_jsonl(output_dir / "train.jsonl", train_records)
    _write_jsonl(output_dir / "val.jsonl", val_records)

    print(f"Wrote {len(smolvlm_records)} SmolVLM records")
    print(f"Wrote {len(train_records)} train / {len(val_records)} val LayoutLMv3 records")


def _bio_tag_from_ocr(img_path: Path, fields: dict):
    """OCR the image, then weakly-label tokens that match a known field value."""
    image = Image.open(img_path).convert("RGB")
    w, h = image.size
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    words, boxes, labels = [], [], []
    n = len(data["text"])
    for i in range(n):
        text = data["text"][i].strip()
        if not text:
            continue
        x, y, ww, hh = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        # normalize to 0-1000 as LayoutLMv3 expects
        box = [
            int(1000 * x / w), int(1000 * y / h),
            int(1000 * (x + ww) / w), int(1000 * (y + hh) / h),
        ]
        words.append(text)
        boxes.append(box)
        labels.append(_label_for_word(text, fields))

    return words, boxes, labels


def _label_for_word(word: str, fields: dict) -> str:
    field_name_map = {
        "vendor_name": "VENDOR_NAME",
        "invoice_date": "INVOICE_DATE",
        "grand_total": "GRAND_TOTAL",
    }
    for field_key, tag in field_name_map.items():
        value = str(fields.get(field_key, ""))
        if value and word.lower() in value.lower():
            return f"B-{tag}"
    return "O"


def _write_jsonl(path: Path, records: list):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["sroie"], default="sroie")
    parser.add_argument("--sroie_dir", help="Path to extracted SROIE2019 dataset")
    parser.add_argument("--output_dir", required=True)
    args = parser.parse_args()

    if args.source == "sroie":
        if not args.sroie_dir:
            raise SystemExit("--sroie_dir is required when --source sroie")
        convert_sroie(args.sroie_dir, args.output_dir)


if __name__ == "__main__":
    main()
