"""
Fine-tune LayoutLMv3 for token-classification-based invoice field extraction.

This is the alternative/complementary approach to the SmolVLM script:
LayoutLMv3 jointly encodes text + 2D layout position + image patches, and is
typically more precise (and much cheaper to run) than a generative VLM for
this kind of structured key-value extraction, at the cost of needing
word-level bounding-box annotations (BIO-tagged) rather than a single JSON
target.

WHERE TO RUN THIS: Google Colab / Kaggle with a GPU. Needs internet access
to pull the base checkpoint from Hugging Face and (optionally) the SROIE
dataset.

USAGE:
    !pip install -q transformers datasets seqeval accelerate
    !python train_layoutlmv3.py \
        --data_dir /content/sroie_prepared \
        --output_dir /content/drive/MyDrive/layoutlmv3-invoice \
        --epochs 15

DATASET FORMAT EXPECTED (produced by prepare_dataset.py):
    data_dir/
      train.jsonl / val.jsonl, each line:
        {"image": "invoice_0001.png",
         "words": ["Invoice", "Number", ":", "INV-2024-001", ...],
         "boxes": [[x0,y0,x1,y1], ...],          # normalized 0-1000
         "labels": ["O", "O", "O", "B-INVOICE_NUMBER", ...]}
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from torch.utils.data import Dataset

LABEL_LIST = [
    "O",
    "B-INVOICE_NUMBER", "I-INVOICE_NUMBER",
    "B-INVOICE_DATE", "I-INVOICE_DATE",
    "B-DUE_DATE", "I-DUE_DATE",
    "B-VENDOR_NAME", "I-VENDOR_NAME",
    "B-BUYER_NAME", "I-BUYER_NAME",
    "B-SUBTOTAL", "I-SUBTOTAL",
    "B-TAX_AMOUNT", "I-TAX_AMOUNT",
    "B-GRAND_TOTAL", "I-GRAND_TOTAL",
    "B-LINE_ITEM", "I-LINE_ITEM",
]
LABEL2ID = {l: i for i, l in enumerate(LABEL_LIST)}
ID2LABEL = {i: l for i, l in enumerate(LABEL_LIST)}


class LayoutLMDataset(Dataset):
    def __init__(self, jsonl_path: str, image_dir: str, processor):
        self.image_dir = Path(image_dir)
        self.processor = processor
        self.examples = []
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    self.examples.append(json.loads(line))

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        ex = self.examples[idx]
        image = Image.open(self.image_dir / ex["image"]).convert("RGB")
        words = ex["words"]
        boxes = ex["boxes"]
        labels = [LABEL2ID[l] for l in ex["labels"]]

        encoding = self.processor(
            image,
            words,
            boxes=boxes,
            word_labels=labels,
            truncation=True,
            padding="max_length",
            max_length=512,
            return_tensors="pt",
        )
        return {k: v.squeeze(0) for k, v in encoding.items()}


def compute_metrics(eval_pred):
    from seqeval.metrics import f1_score, precision_score, recall_score

    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=2)

    true_predictions = [
        [ID2LABEL[p] for (p, l) in zip(pred, label) if l != -100]
        for pred, label in zip(predictions, labels)
    ]
    true_labels = [
        [ID2LABEL[l] for (p, l) in zip(pred, label) if l != -100]
        for pred, label in zip(predictions, labels)
    ]

    return {
        "precision": precision_score(true_labels, true_predictions),
        "recall": recall_score(true_labels, true_predictions),
        "f1": f1_score(true_labels, true_predictions),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", required=True, help="Dir with train.jsonl/val.jsonl + images/")
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--model_id", default="microsoft/layoutlmv3-base")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch_size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=5e-5)
    args = parser.parse_args()

    from transformers import (
        AutoProcessor,
        LayoutLMv3ForTokenClassification,
        Trainer,
        TrainingArguments,
    )

    data_dir = Path(args.data_dir)
    processor = AutoProcessor.from_pretrained(args.model_id, apply_ocr=False)
    model = LayoutLMv3ForTokenClassification.from_pretrained(
        args.model_id, num_labels=len(LABEL_LIST), id2label=ID2LABEL, label2id=LABEL2ID
    )

    train_dataset = LayoutLMDataset(data_dir / "train.jsonl", data_dir / "images", processor)
    val_dataset = LayoutLMDataset(data_dir / "val.jsonl", data_dir / "images", processor)
    print(f"Train examples: {len(train_dataset)} | Val examples: {len(val_dataset)}")

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.lr,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        save_total_limit=2,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )

    trainer.train()
    metrics = trainer.evaluate()
    print("Final validation metrics:", metrics)

    model.save_pretrained(args.output_dir)
    processor.save_pretrained(args.output_dir)
    print(f"Saved fine-tuned model to {args.output_dir}")


if __name__ == "__main__":
    main()
