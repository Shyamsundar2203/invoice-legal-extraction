import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app import config
from app.routers import batch, extract

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="DocuExtract AI · Invoice & Legal Document Extraction API",
    description=(
        "AI-based multimodal document processing pipeline: OCR + layout + "
        "NLP extraction for invoices and legal contracts."
    ),
    version="1.0.0",
)

# Allow CORS for any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(extract.router)
app.include_router(batch.router)

frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
sample_dir = config.DATA_DIR / "sample"


@app.get("/health")
async def health():
    return {"status": "ok"}


# Explicit Frontend Web UI Routes
@app.get("/")
async def index():
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file, media_type="text/html")
    return {"message": "DocuExtract AI API", "docs": "/docs"}


@app.get("/style.css")
async def get_style():
    style_file = frontend_dir / "style.css"
    return FileResponse(style_file, media_type="text/css")


@app.get("/app.js")
async def get_app_js():
    js_file = frontend_dir / "app.js"
    return FileResponse(js_file, media_type="application/javascript")


@app.get("/sample_invoice.png")
async def get_sample_invoice():
    sample_file = sample_dir / "sample_invoice.png"
    return FileResponse(sample_file, media_type="image/png")


@app.get("/sample_contract.png")
async def get_sample_contract():
    sample_file = sample_dir / "sample_contract.png"
    return FileResponse(sample_file, media_type="image/png")
