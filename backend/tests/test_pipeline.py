"""
Basic tests for the extraction pipeline. Run with:
    cd backend && pytest -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.pipeline.extract import RuleBasedExtractor
from app.pipeline.ocr import OCRWord


def _fake_words(text: str):
    """Turn a plain multi-line string into a fake OCRWord list for testing
    without needing an actual image / Tesseract call."""
    words = []
    for line_num, line in enumerate(text.splitlines()):
        for word in line.split(" "):
            if word:
                words.append(
                    OCRWord(text=word, conf=0.9, bbox=[0, 0, 10, 10],
                             line_num=line_num, block_num=0)
                )
    return words


def test_invoice_number_extraction():
    text = "Invoice Number: INV-2026-0091\nInvoice Date: 08/17/2026\nGrand Total: $1,240.00"
    words = _fake_words(text)
    extractor = RuleBasedExtractor()
    data = extractor.extract_invoice(words)
    assert data.invoice_number.value == "INV-2026-0091"
    assert data.grand_total.value == "1,240.00"


def test_contract_clause_detection():
    text = (
        "This Agreement shall terminate upon 30 days written notice.\n\n"
        "Each party agrees to keep all confidential information secret.\n\n"
        "This Agreement is governed by the laws of Delaware."
    )
    words = _fake_words(text)
    extractor = RuleBasedExtractor()
    data = extractor.extract_contract(words)
    clause_types = {c.clause_type for c in data.clauses}
    assert "termination" in clause_types
    assert "confidentiality" in clause_types


def test_empty_document_flags_review():
    from app.pipeline.confidence import score_document
    from app.schemas import InvoiceData

    empty = InvoiceData()
    overall, needs_review = score_document(empty)
    assert needs_review is True
