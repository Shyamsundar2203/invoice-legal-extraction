# 📄 Automated Invoice & Legal Document Extraction Pipeline

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Tesseract OCR](https://img.shields.io/badge/Tesseract_OCR-5.0%2B-green?style=for-the-badge)](https://github.com/tesseract-ocr/tesseract)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

An end-to-end AI-powered document processing pipeline (OCR + Layout Analysis + NLP Extraction) that extracts structured key-value pairs, line item tables, and contract clauses from scanned invoices and legal documents. It features automated confidence scoring, bounding-box visual overlays, human-in-the-loop review flags, batch CSV reports, and a clean Web UI.

---

## 🏛️ Pipeline Architecture

```text
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌────────────────┐     ┌──────────────┐
│  Scanned PDF │ ──▶ │ Preprocess   │ ──▶ │ Tesseract    │ ──▶ │ Field/Clause   │ ──▶ │ Confidence   │
│  or Image    │     │ Deskew/Clean │     │ OCR          │     │ Extraction     │     │ Scoring      │
└──────────────┘     └──────────────┘     └──────────────┘     └────────────────┘     └──────┬───────┘
                                                                                             │
                                     ┌───────────────────────────────────────────────────────┘
                                     ▼
                    ┌───────────────────────────────────┐
                    │  • Structured JSON Data           │
                    │  • Bounding-box Overlay PDF       │
                    │  • Batch Summary CSV              │
                    │  • Human Review Flag (<85% conf)  │
                    └───────────────────────────────────┘
```

---

## ✨ Key Features

- **Multimodal Ingestion**: Supports `.pdf`, `.png`, `.jpg`, `.jpeg`, and `.tiff`.
- **Intelligent Preprocessing**: Automated page deskewing, noise filtering, and adaptive thresholding for clear OCR scanning.
- **Invoice Extraction**: Extracts invoice number, issue date, due date, vendor, buyer, subtotal, taxes, grand total, and tabular line items.
- **Legal Contract Extraction**: Identifies contracting parties, effective dates, governing jurisdiction, term length, and key clauses (*termination, confidentiality, liability, indemnification, etc.*).
- **Confidence Scoring & Flagging**: Evaluates per-field confidence; automatically flags documents requiring human review.
- **Visual PDF Overlays**: Highlights detected words and bounding boxes in a generated overlay PDF.
- **Batch Processing**: Process multiple files in one request and export a consolidated CSV summary.
- **Interactive Web UI & Swagger Docs**: Easy-to-use web interface and auto-generated OpenAPI documentation.

---

## 📁 Repository Structure

```text
invoice-legal-extraction/
├── backend/
│   ├── app/
│   │   ├── pipeline/          # Preprocessing, OCR, extraction & scoring logic
│   │   │   ├── preprocess.py  # Image cleaning & deskewing
│   │   │   ├── ocr.py         # Cross-platform Tesseract wrapper
│   │   │   ├── extract.py     # Rule-based & ML extractor adapters
│   │   │   ├── confidence.py  # Confidence scoring heuristics
│   │   │   ├── overlay.py     # PDF bounding-box generator
│   │   │   └── orchestrator.py# End-to-end pipeline pipeline coordinator
│   │   ├── routers/           # /extract and /batch API endpoints
│   │   ├── schemas.py         # Pydantic JSON contracts
│   │   ├── config.py          # Environment settings
│   │   └── main.py            # FastAPI application entrypoint
│   ├── tests/                 # Pytest test suite
│   ├── requirements.txt       # Backend dependencies
│   └── Dockerfile             # Container definition
├── frontend/                  # Static Web UI (HTML, CSS, JS)
│   ├── index.html
│   ├── style.css
│   └── app.js
├── data/
│   ├── sample/                # Bundled test sample (sample_invoice.png)
│   ├── raw/                   # Ingested upload directory
│   └── processed/             # Output JSON results & overlay PDFs
├── training/                  # Model fine-tuning (LayoutLMv3 & SmolVLM)
├── run_app.bat                # ⚡ 1-Click Windows Launcher
├── docker-compose.yml         # Containerized local setup
└── README.md
```

---

## 🚀 Quick Start (Local Setup)

### Option 1: ⚡ 1-Click Windows Launcher (Easiest)
If you are on Windows, simply double-click **`run_app.bat`** in the project root folder.
- Automatically starts the FastAPI backend on `http://127.0.0.1:8000`
- Starts the Frontend on `http://127.0.0.1:3000`
- Opens the application directly in your default browser!

---

### Option 2: Run via Terminal

#### 1. Prerequisites
- **Python 3.10 - 3.12+**
- **Tesseract OCR**:
  - **Windows**: [Download Tesseract Installer](https://github.com/UB-Mannheim/tesseract/wiki) (Standard install at `C:\Program Files\Tesseract-OCR`)
  - **Ubuntu / Debian**: `sudo apt-get update && sudo apt-get install -y tesseract-ocr`
  - **macOS**: `brew install tesseract`

#### 2. Install Dependencies
```powershell
# Navigate to backend
cd backend
pip install -r requirements.txt
```

#### 3. Start Backend Server
```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Docs will be available at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

#### 4. Start Frontend
In a new terminal:
```powershell
cd frontend
python -m http.server 3000
```
- Web UI will be live at: [http://127.0.0.1:3000](http://127.0.0.1:3000)

---

### Option 3: Run with Docker Compose
```bash
docker compose up --build
```
- Backend API: `http://localhost:8000/docs`
- Frontend UI: `http://localhost:5173`

---

## 🌐 How to Run Globally (Public Link Sharing)

If you want to share a live link of your application with clients, colleagues, or anyone on the internet without running it only on `localhost`, choose any of these free methods:

### Method A: Instant 1-Minute Public Tunnel (Using Ngrok)
You can share your locally running app across the internet instantly:
1. Download [ngrok](https://ngrok.com/download) (Free).
2. Open terminal and run:
   ```bash
   ngrok http 3000
   ```
3. Ngrok will give you a public HTTPS URL (e.g. `https://xyz.ngrok-free.app`) that anyone in the world can open to use your app!

---

### Method B: Deploy Free on Render / Railway (Cloud Hosting)
1. Push this repository to your GitHub account (`https://github.com/Shyamsundar2203/invoice-legal-extraction`).
2. Log into [Render.com](https://render.com) or [Railway.app](https://railway.app).
3. Click **New Web Service** and select your GitHub repository.
4. Set Environment to **Docker** (Render will use the included `backend/Dockerfile`).
5. Click **Deploy** — your API will get a permanent public link (`https://invoice-extractor.onrender.com`).

---

### Method C: Free Hosting on Hugging Face Spaces
1. Create a free account on [Hugging Face](https://huggingface.co/).
2. Create a new Space, select **Docker** as SDK.
3. Link your GitHub repo or push code to Space Git repository.
4. Your document extractor will be live permanently with a public web link.

---

## 🧪 Testing Document Extraction

1. Open the Web UI at **[http://127.0.0.1:3000](http://127.0.0.1:3000)**.
2. Select the included test image:
   `data/sample/sample_invoice.png`
3. Click **"Extract Fields"**.
4. View the real-time extraction results:

```json
{
  "document_id": "01174f8c",
  "filename": "sample_invoice.png",
  "doc_type": "invoice",
  "overall_confidence": 0.65,
  "data": {
    "doc_type": "invoice",
    "invoice_number": { "value": "INV-2026-0458", "confidence": 0.7 },
    "invoice_date": { "value": "08/15/2026", "confidence": 0.7 },
    "due_date": { "value": "09/14/2026", "confidence": 0.7 },
    "vendor_name": { "value": "Acme Supplies Inc.", "confidence": 0.55 },
    "buyer_name": { "value": "Rajasthan Traders Pvt Ltd", "confidence": 0.55 },
    "subtotal": { "value": "450.00", "confidence": 0.7 },
    "tax_amount": { "value": "45.00", "confidence": 0.7 },
    "grand_total": { "value": "495.00", "confidence": 0.7 },
    "line_items": [
      { "description": "Widget A", "quantity": "10", "unit_price": "25.00", "total": "250.00" },
      { "description": "Widget B", "quantity": "5", "unit_price": "40.00", "total": "200.00" }
    ]
  }
}
```

---

## 📡 REST API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `POST /extract?doc_type=invoice\|contract` | `POST` | Upload single document (PDF/Image) & extract structured fields |
| `GET /extract/{document_id}/overlay` | `GET` | Download bounding-box visual overlay PDF |
| `POST /batch?doc_type=invoice\|contract` | `POST` | Process multiple documents simultaneously |
| `GET /batch/summary.csv` | `GET` | Export consolidated batch processing CSV summary |
| `GET /health` | `GET` | API health check endpoint |

---

## 🔬 Automated Tests

To run automated unit & pipeline integration tests:
```powershell
cd backend
python -m pytest tests/ -v
```

---

## 🧠 Training Custom ML Models

For training deep learning models (LayoutLMv3 / SmolVLM) on Google Colab or Kaggle GPUs:
- Check the complete guide in [`training/README.md`](training/README.md).
- Switch the backend in `backend/app/config.py` from `rules` to `ml` once checkpoints are generated.

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
