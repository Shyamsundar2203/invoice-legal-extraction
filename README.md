# Automated Invoice & Legal Document Extraction

AI-based multimodal document processing pipeline (OCR + Layout + NLP) that
extracts key-value pairs, tables, and clauses from scanned invoices and legal
contracts, flags low-confidence fields for human review, and outputs
structured JSON, an annotated overlay PDF, and a CSV batch summary.

Reference approach for the trainable model: [SmolVLM invoice extraction](https://www.kaggle.com/code/vermaavi/invoice-data-extraction-using-smolvlm)
(Kaggle), adapted into `training/train_smolvlm_invoice.py`, plus a
LayoutLMv3 alternative for higher-precision structured extraction.

```
┌─────────────┐   ┌──────────────┐   ┌─────────┐   ┌────────────────┐   ┌────────────┐
│  PDF/Image  │──▶│ Preprocess   │──▶│  OCR    │──▶│ Field Extract  │──▶│ Confidence │
│   upload    │   │(deskew/clean)│   │(Tesseract)│  │(rules or ML)   │   │  scoring   │
└─────────────┘   └──────────────┘   └─────────┘   └────────────────┘   └─────┬──────┘
                                                                                │
                                          ┌─────────────────────────────────────┘
                                          ▼
                          JSON  +  overlay PDF  +  CSV summary  +  human review flag
```

## What's in this repo

```
invoice-legal-extraction/
├── backend/              FastAPI service — the actual working pipeline
│   ├── app/
│   │   ├── pipeline/     preprocess → ocr → extract → confidence → overlay
│   │   ├── routers/      /extract, /batch, /batch/summary.csv
│   │   ├── main.py
│   │   └── schemas.py    Pydantic output contracts
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/             Static HTML/JS upload + results UI
├── training/             Colab/Kaggle scripts to train a real ML model
│   ├── train_layoutlmv3.py
│   ├── train_smolvlm_invoice.py
│   ├── prepare_dataset.py
│   ├── evaluate.py
│   └── README.md         full training walkthrough
├── data/                 raw/ processed/ sample/ (sample invoice included)
├── scripts/run_demo.sh   one-command smoke test
└── docker-compose.yml
```

## Quick start (rule-based baseline — works immediately, no GPU/model needed)

### Option A — Docker (recommended)
```bash
git clone <your-repo-url>.git
cd invoice-legal-extraction
docker compose up --build
```
- Backend API: http://localhost:8000/docs
- Frontend UI: http://localhost:5173

### Option B — Local Python

**Windows:** run the setup script from inside `backend/`:
```
scripts\setup_windows.bat
```
This creates a virtual environment and installs everything for you. Then:
```
venv\Scripts\activate
uvicorn app.main:app --reload
```

**Mac/Linux:**
```bash
cd backend
pip install -r requirements.txt
# Tesseract binary is required by pytesseract:
#   Ubuntu/Debian: sudo apt-get install tesseract-ocr
#   macOS:          brew install tesseract
uvicorn app.main:app --reload
```

> **Python version note:** use Python 3.10–3.12 if you can. Very new Python
> releases (3.13/3.14) sometimes don't have pre-built wheels yet for
> numpy/OpenCV/PyMuPDF, which makes pip try to compile them from source and
> fail without a C/C++ compiler. `requirements.txt` intentionally leaves
> versions unpinned so pip grabs the newest compatible wheel automatically —
> if install still fails, installing Python 3.11 side-by-side and creating
> the venv with `py -3.11 -m venv venv` is the most reliable fix on Windows.
Then open `frontend/index.html` directly in a browser (it calls
`http://localhost:8000` by default — edit `API_BASE` in `frontend/app.js`
if you're running the backend elsewhere).

### One-command demo
```bash
bash scripts/run_demo.sh
```
Runs the bundled `data/sample/sample_invoice.png` through the full pipeline
and prints the extracted JSON.

## API

| Endpoint | Method | Description |
|---|---|---|
| `/extract?doc_type=invoice\|contract` | POST (multipart file) | Extract one document, returns JSON |
| `/extract/{document_id}/overlay` | GET | Download the bounding-box overlay PDF |
| `/batch?doc_type=invoice\|contract` | POST (multipart files[]) | Extract multiple documents |
| `/batch/summary.csv` | GET | CSV report of every processed document |
| `/health` | GET | Liveness check |

Full interactive docs at `/docs` once the backend is running (FastAPI
auto-generates Swagger UI).

## Going from baseline to a real trained model

The rule-based extractor (`RuleBasedExtractor` in
`backend/app/pipeline/extract.py`) is a regex/keyword baseline — good enough
to demo the whole pipeline instantly, but not accurate enough for production
on varied real-world documents. To train and plug in a real model:

**See [`training/README.md`](training/README.md) for the full walkthrough** —
covers getting a free GPU (Colab/Kaggle), datasets (SROIE, CUAD), training
LayoutLMv3 or fine-tuning SmolVLM with LoRA, evaluating per-field accuracy,
and wiring the trained checkpoint back into the backend via
`EXTRACTION_BACKEND=ml`.

## Running tests
```bash
cd backend
pytest -v
```

## Pushing to GitHub
```bash
cd invoice-legal-extraction
git init
git add .
git commit -m "Initial commit: invoice & legal document extraction pipeline"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```
Model checkpoints are excluded via `.gitignore` (too large for git) —
push them to Hugging Face Hub, Git LFS, or keep them on Google Drive instead,
and document the checkpoint URL/path in your own fork's README.

## Notes & limitations
- The bundled extractor is rule-based on purpose, so the project is runnable
  without any model download or GPU. Expect it to correctly grab clearly
  labeled fields (`Invoice Number:`, `Grand Total:`, etc.) but to need the
  trained model for messy/varied real-world layouts.
- OCR quality depends on scan quality; very low-DPI or heavily skewed scans
  will show up as low-confidence fields flagged `needs_review`.
- `doc_type` is passed explicitly today; a production version would add a
  classifier step to auto-detect invoice vs. contract vs. other.
