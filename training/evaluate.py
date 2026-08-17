"""
Evaluate a fine-tuned model checkpoint against a held-out validation set and
produce a per-field accuracy report + confusion summary.

USAGE:
    !python evaluate.py --checkpoint /content/drive/MyDrive/layoutlmv3-invoice \
        --val_jsonl /content/invoice_dataset/val.jsonl \
        --image_dir /content/invoice_dataset/images \
        --report_out /content/eval_report.csv
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def evaluate_layoutlmv3(checkpoint: str, val_jsonl: str, image_dir: str):
    import torch
    from PIL import Image
    from transformers import AutoProcessor, LayoutLMv3ForTokenClassification

    processor = AutoProcessor.from_pretrained(checkpoint, apply_ocr=False)
    model = LayoutLMv3ForTokenClassification.from_pretrained(checkpoint)
    model.eval()

    id2label = model.config.id2label

    per_field_correct = {}
    per_field_total = {}

    with open(val_jsonl, encoding="utf-8") as f:
        examples = [json.loads(line) for line in f if line.strip()]

    for ex in examples:
        image = Image.open(Path(image_dir) / ex["image"]).convert("RGB")
        words, boxes, gold_labels = ex["words"], ex["boxes"], ex["labels"]

        encoding = processor(
            image, words, boxes=boxes, truncation=True,
            padding="max_length", max_length=512, return_tensors="pt",
        )
        with torch.no_grad():
            outputs = model(**encoding)
        preds = outputs.logits.argmax(-1).squeeze().tolist()
        pred_labels = [id2label[p] for p in preds[: len(gold_labels)]]

        for gold, pred in zip(gold_labels, pred_labels):
            field = gold.split("-")[-1] if gold != "O" else "O"
            per_field_total[field] = per_field_total.get(field, 0) + 1
            if gold == pred:
                per_field_correct[field] = per_field_correct.get(field, 0) + 1

    rows = []
    for field, total in per_field_total.items():
        correct = per_field_correct.get(field, 0)
        rows.append(
            {"field": field, "correct": correct, "total": total,
             "accuracy": round(correct / total, 4) if total else 0.0}
        )
    return pd.DataFrame(rows).sort_values("field")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--val_jsonl", required=True)
    parser.add_argument("--image_dir", required=True)
    parser.add_argument("--report_out", default="eval_report.csv")
    args = parser.parse_args()

    df = evaluate_layoutlmv3(args.checkpoint, args.val_jsonl, args.image_dir)
    df.to_csv(args.report_out, index=False)
    print(df.to_string(index=False))
    print(f"\nSaved report to {args.report_out}")


if __name__ == "__main__":
    main()
