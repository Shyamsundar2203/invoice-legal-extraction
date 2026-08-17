# Training — from scratch to a production-level extraction model

The base project (`/backend`) runs immediately with a **rule-based extractor**
(regex + keyword heuristics) so you have a working API/UI with zero setup.
This folder is how you replace that baseline with a **trained ML model** for
real production accuracy.

## Why two model options are included

| | LayoutLMv3 (`train_layoutlmv3.py`) | SmolVLM (`train_smolvlm_invoice.py`) |
|---|---|---|
| Type | Layout-aware token classifier | Vision-language generative model |
| Needs | OCR words + bounding boxes + BIO labels | Just image + target JSON |
| Accuracy on structured fields | Usually higher, more stable | Good, more flexible (handles messier layouts) |
| Training cost | Cheaper, faster to converge | Needs LoRA to fit on free-tier GPU |
| Best for | Invoices/forms with fairly consistent layout | Varied/messy real-world scans, or when you don't want to build bbox annotations |

Pick one to start (LayoutLMv3 is the safer first choice), and you can swap
or ensemble both later.

## Step-by-step

### 1. Get a GPU environment
Use **Google Colab** (Runtime → Change runtime type → GPU, T4 is free) or
**Kaggle Notebooks** (GPU accelerator toggle). This repo's Docker container
does NOT include GPU/ML dependencies on purpose, to keep the base API
lightweight — training happens separately.

### 2. Install training dependencies
```bash
pip install -r training/requirements.txt
```

### 3. Get labeled data
- Fastest start: **SROIE** dataset (invoices, already labeled) —
  https://www.kaggle.com/datasets/urbikn/sroie-datasetv2
- For contracts/clauses: **CUAD** — https://www.atticusprojectai.org/cuad
- For your own documents: label with **Label Studio** (https://labelstud.io)

### 4. Prepare the dataset
```bash
python prepare_dataset.py --source sroie \
  --sroie_dir /content/SROIE2019 \
  --output_dir /content/invoice_dataset
```
This produces both the SmolVLM JSON-target format and the LayoutLMv3
BIO-tagged format from the same source images.

### 5. Train
LayoutLMv3:
```bash
python train_layoutlmv3.py \
  --data_dir /content/invoice_dataset \
  --output_dir /content/drive/MyDrive/layoutlmv3-invoice \
  --epochs 15
```
SmolVLM (LoRA):
```bash
python train_smolvlm_invoice.py \
  --data_dir /content/invoice_dataset \
  --output_dir /content/drive/MyDrive/smolvlm-invoice-adapter \
  --epochs 3 --batch_size 2
```
Save checkpoints to Google Drive (as above) so they survive the Colab
session ending.

### 6. Evaluate
```bash
python evaluate.py \
  --checkpoint /content/drive/MyDrive/layoutlmv3-invoice \
  --val_jsonl /content/invoice_dataset/val.jsonl \
  --image_dir /content/invoice_dataset/images \
  --report_out eval_report.csv
```
This gives per-field precision so you know exactly which fields need more
training data before you trust the model in production.

### 7. Wire the trained model into the backend
1. Download/copy the checkpoint folder into the backend's environment.
2. In `backend/app/pipeline/extract.py`, implement `MLExtractor.extract_invoice`
   / `extract_contract` to load your checkpoint and run inference — it has
   the exact same method signature as `RuleBasedExtractor`, so nothing else
   in the API changes.
3. Set env vars before starting the backend:
   ```bash
   export EXTRACTION_BACKEND=ml
   export CHECKPOINT_PATH=/path/to/your/checkpoint
   ```

### 8. Iterate like a real ML pipeline
- Collect the `needs_review` cases the human reviewer corrects in the UI.
- Periodically add those corrections back into your training set.
- Re-run steps 5–6 to retrain/fine-tune again. This closes the human-in-the-loop
  loop described in the original project spec.
