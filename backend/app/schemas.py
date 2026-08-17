"""
Pydantic schemas for the Invoice & Legal Document Extraction pipeline.
These define the structured JSON contract returned by the API and
written to disk for every processed document.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class FieldValue(BaseModel):
    """A single extracted field with its confidence + source location."""
    value: Optional[str] = None
    confidence: float = 0.0
    needs_review: bool = False
    bbox: Optional[List[float]] = None  # [x0, y0, x1, y1] in pixel coords


class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[str] = None
    unit_price: Optional[str] = None
    total: Optional[str] = None
    confidence: float = 0.0


class InvoiceData(BaseModel):
    doc_type: str = "invoice"
    invoice_number: FieldValue = Field(default_factory=FieldValue)
    invoice_date: FieldValue = Field(default_factory=FieldValue)
    due_date: FieldValue = Field(default_factory=FieldValue)
    vendor_name: FieldValue = Field(default_factory=FieldValue)
    buyer_name: FieldValue = Field(default_factory=FieldValue)
    subtotal: FieldValue = Field(default_factory=FieldValue)
    tax_amount: FieldValue = Field(default_factory=FieldValue)
    grand_total: FieldValue = Field(default_factory=FieldValue)
    line_items: List[LineItem] = Field(default_factory=list)


class ClauseSpan(BaseModel):
    clause_type: str
    text: str
    confidence: float = 0.0


class ContractData(BaseModel):
    doc_type: str = "contract"
    party_a: FieldValue = Field(default_factory=FieldValue)
    party_b: FieldValue = Field(default_factory=FieldValue)
    effective_date: FieldValue = Field(default_factory=FieldValue)
    governing_law: FieldValue = Field(default_factory=FieldValue)
    term_duration: FieldValue = Field(default_factory=FieldValue)
    clauses: List[ClauseSpan] = Field(default_factory=list)


class ProcessingResult(BaseModel):
    document_id: str
    filename: str
    doc_type: str
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: float = 0.0
    overall_confidence: float = 0.0
    needs_review: bool = False
    data: dict  # InvoiceData or ContractData serialized
    overlay_pdf_path: Optional[str] = None
    raw_ocr_text: Optional[str] = None


class BatchSummaryRow(BaseModel):
    document_id: str
    filename: str
    doc_type: str
    overall_confidence: float
    needs_review: bool
    processing_time_ms: float
    status: str
