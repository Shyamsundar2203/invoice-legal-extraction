"""
Fine-tune SmolVLM-256M/500M on invoice images for structured field extraction.

This mirrors the approach used in the reference Kaggle notebook
"Invoice Data Extraction using smolvlm" (dataset: "High-Quality Invoice
Images for OCR"), adapted into a clean, reusable training script.

WHERE TO RUN THIS:
    Google Colab (free GPU: Runtime > Change runtime type > T4 GPU) or
    Kaggle Notebooks (GPU accelerator on). This script needs internet
    access to download the base model from Hugging Face and the dataset
    from Kaggle -- neither is available in the base project's Docker
    container, which is why this lives in a separate `training/` folder.

WHAT IT DOES:
    1. Loads a base SmolVLM checkpoint (vision-language model).
    2. Loads invoice images + ground-truth JSON field annotations.
    3. Formats each example as an (image, prompt, target JSON string) pair.
    4. Fine-tunes with LoRA (parameter-efficient) so it fits on a free-tier GPU.
    5. Saves the adapter checkpoint you can load back with `extract.MLExtractor`.

USAGE (Colab cell):
    !pip install -q transformers accelerate peft bitsandbytes datasets pillow
    !python train_smolvlm_invoice.py \
        --data_dir /content/invoice_dataset \
        --output_dir /content/drive/MyDrive/smolvlm-invoice-adapter \
        --epochs 3 --batch_size 2

DATASET FORMAT EXPECTED (see prepare_dataset.py to build this from raw images):
    data_dir/
      images/
        invoice_0001.png
        invoice_0002.png
        ...
      annotations.jsonl        # one JSON object per line:
        {"image": "invoice_0001.png",
         "fields": {"invoice_number": "INV-2024-001", "invoice_date": "2024-01-15",
                     "vendor_name": "Acme Inc.", "grand_total": "1240.00", ...}}
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from PIL import Image
from torch.utils.data import Dataset

MODEL_ID = "HuggingFaceTB/SmolVLM-256M-Instruct"  # swap for -500M for higher accuracy

PROMPT_TEMPLATE = (
    "Extract the following fields from this invoice image as a JSON object with "
    "keys: invoice_number, invoice_date, due_date, vendor_name, buyer_name, "
    "subtotal, tax_amount, grand_total. If a field is not present, use null."
)


class InvoiceVLMDataset(Dataset):
    def __init__(self, data_dir: str, processor):
        self.data_dir = Path(data_dir)
        self.processor = processor
        self.examples = []
        with open(self.data_dir / "annotations.jsonl", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    self.examples.append(json.loads(line))

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        ex = self.examples[idx]
        image = Image.open(self.data_dir / "images" / ex["image"]).convert("RGB")
        target_json = json.dumps(ex["fields"], ensure_ascii=False)

        messages = [
            {
                "role": "user",
                "content": [{"type": "image"}, {"type": "text", "text": PROMPT_TEMPLATE}],
            },
            {"role": "assistant", "content": [{"type": "text", "text": target_json}]},
        ]
        prompt = self.processor.apply_chat_template(messages, add_generation_prompt=False)
        inputs = self.processor(text=prompt, images=[image], return_tensors="pt")
        inputs = {k: v.squeeze(0) for k, v in inputs.items()}
        inputs["labels"] = inputs["input_ids"].clone()
        return inputs


def collate_fn(batch, processor):
    pad_id = processor.tokenizer.pad_token_id
    max_len = max(x["input_ids"].shape[0] for x in batch)

    def pad(tensor, value):
        pad_len = max_len - tensor.shape[0]
        if pad_len <= 0:
            return tensor
        return torch.cat([tensor, torch.full((pad_len,), value, dtype=tensor.dtype)])

    input_ids = torch.stack([pad(x["input_ids"], pad_id) for x in batch])
    attention_mask = torch.stack([pad(x["attention_mask"], 0) for x in batch])
    labels = torch.stack([pad(x["labels"], -100) for x in batch])
    pixel_values = torch.stack([x["pixel_values"] for x in batch])

    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels,
        "pixel_values": pixel_values,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--model_id", default=MODEL_ID)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--lora_r", type=int, default=16)
    args = parser.parse_args()

    from functools import partial

    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForVision2Seq, AutoProcessor, Trainer, TrainingArguments

    print(f"Loading base model: {args.model_id}")
    processor = AutoProcessor.from_pretrained(args.model_id)
    model = AutoModelForVision2Seq.from_pretrained(
        args.model_id, torch_dtype=torch.bfloat16, device_map="auto"
    )

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    dataset = InvoiceVLMDataset(args.data_dir, processor)
    print(f"Loaded {len(dataset)} training examples")

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=4,
        learning_rate=args.lr,
        bf16=True,
        logging_steps=10,
        save_strategy="epoch",
        save_total_limit=2,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=partial(collate_fn, processor=processor),
    )

    trainer.train()

    model.save_pretrained(args.output_dir)
    processor.save_pretrained(args.output_dir)
    print(f"Saved fine-tuned adapter to {args.output_dir}")


if __name__ == "__main__":
    main()
