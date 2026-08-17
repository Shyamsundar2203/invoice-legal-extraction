"""
End-to-end orchestrator: ties together preprocessing, OCR, extraction,
confidence scoring, and overlay generation into a single call.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import List

from app import config
from app.pipeline import confidence as confidence_mod
from app.pipeline import extract as extract_mod
from app.pipeline import ocr as ocr_mod
from app.pipeline import overlay as overlay_mod
from app.pipeline import preprocess as preprocess_mod
from app.schemas import ContractData, InvoiceData, ProcessingResult

_extractor = extract_mod.get_extractor(
    backend=config.EXTRACTION_BACKEND, checkpoint_path=config.CHECKPOINT_PATH
)


def process_document(file_path: str, doc_type: str = "invoice") -> ProcessingResult:
    """
    Run the full pipeline on a single PDF/image file.

    doc_type: "invoice" or "contract" - selects which field schema/extractor
    to use. In a production system this would be predicted by a
    classifier; here it's passed explicitly (or defaulted) for simplicity.
    """
    start = time.perf_counter()
    document_id = str(uuid.uuid4())[:8]
    filename = Path(file_path).name

    pages = preprocess_mod.load_and_preprocess(file_path, dpi=config.OCR_DPI)

    all_words = []
    for page in pages:
        all_words.extend(ocr_mod.run_ocr(page, lang=config.OCR_LANG))

    if doc_type == "contract":
        data: InvoiceData | ContractData = _extractor.extract_contract(all_words)
    else:
        data = _extractor.extract_invoice(all_words)

    overall_conf, needs_review = confidence_mod.score_document(data)

    overlay_images = [overlay_mod.draw_overlay(p, all_words) for p in pages]
    overlay_path = str(config.OUTPUT_DIR / f"{document_id}_overlay.pdf")
    overlay_mod.save_overlay_pdf(overlay_images, overlay_path)

    raw_text = ocr_mod.words_to_text(all_words)
    elapsed_ms = (time.perf_counter() - start) * 1000

    result = ProcessingResult(
        document_id=document_id,
        filename=filename,
        doc_type=doc_type,
        processing_time_ms=round(elapsed_ms, 2),
        overall_confidence=overall_conf,
        needs_review=needs_review,
        data=json.loads(data.model_dump_json()),
        overlay_pdf_path=overlay_path,
        raw_ocr_text=raw_text,
    )

    result_path = config.OUTPUT_DIR / f"{document_id}_result.json"
    result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    return result


def process_batch(file_paths: List[str], doc_type: str = "invoice") -> List[ProcessingResult]:
    return [process_document(p, doc_type=doc_type) for p in file_paths]
