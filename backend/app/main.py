import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import batch, extract

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Invoice & Legal Document Extraction API",
    description=(
        "AI-based multimodal document processing pipeline: OCR + layout + "
        "NLP extraction for invoices and legal contracts."
    ),
    version="1.0.0",
)

# Allow the local frontend (or any origin during development) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(extract.router)
app.include_router(batch.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {
        "message": "Invoice & Legal Document Extraction API",
        "docs": "/docs",
        "endpoints": ["/extract", "/batch", "/batch/summary.csv", "/health"],
    }
