"""
Pydantic schemas for the DocuExtract AI Enterprise Pipeline.
Defines data models for extracted financial entities, legal contract clauses,
math reconciliation, and risk analysis.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class FieldValue(BaseModel):
    """A single extracted field with confidence and optional pixel bounding box."""
    value: Optional[str] = None
    confidence: float = 0.0
    needs_review: bool = False
    bbox: Optional[List[float]] = None  # [x0, y0, x1, y1] in pixel coordinates


class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[str] = None
    unit_price: Optional[str] = None
    total: Optional[str] = None
    confidence: float = 0.0


class MathValidation(BaseModel):
    """Automated ledger & financial reconciliation analysis."""
    is_valid: bool = True
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    calculated_grand_total: Optional[float] = None
    extracted_grand_total: Optional[float] = None
    discrepancy: float = 0.0
    line_items_sum: Optional[float] = None
    message: str = "Ledger balances verified."


class InvoiceData(BaseModel):
    doc_type: str = "invoice"
    currency_symbol: str = "$"
    currency_code: str = "USD"
    invoice_number: FieldValue = Field(default_factory=FieldValue)
    invoice_date: FieldValue = Field(default_factory=FieldValue)
    due_date: FieldValue = Field(default_factory=FieldValue)
    vendor_name: FieldValue = Field(default_factory=FieldValue)
    vendor_tax_id: FieldValue = Field(default_factory=FieldValue)
    buyer_name: FieldValue = Field(default_factory=FieldValue)
    subtotal: FieldValue = Field(default_factory=FieldValue)
    tax_amount: FieldValue = Field(default_factory=FieldValue)
    grand_total: FieldValue = Field(default_factory=FieldValue)
    line_items: List[LineItem] = Field(default_factory=list)
    math_validation: Optional[MathValidation] = None


class ClauseSpan(BaseModel):
    clause_type: str
    text: str
    confidence: float = 0.0


class RiskFlag(BaseModel):
    clause_type: str
    risk_level: str  # "HIGH", "MEDIUM", "LOW"
    reason: str
    recommendation: str


class ContractData(BaseModel):
    doc_type: str = "contract"
    contract_title: Optional[str] = "Legal Agreement"
    party_a: FieldValue = Field(default_factory=FieldValue)
    party_b: FieldValue = Field(default_factory=FieldValue)
    effective_date: FieldValue = Field(default_factory=FieldValue)
    governing_law: FieldValue = Field(default_factory=FieldValue)
    term_duration: FieldValue = Field(default_factory=FieldValue)
    clauses: List[ClauseSpan] = Field(default_factory=list)
    risk_flags: List[RiskFlag] = Field(default_factory=list)
    overall_risk_score: str = "LOW"  # "LOW", "MEDIUM", "HIGH"


class OCRWordSchema(BaseModel):
    text: str
    conf: float
    bbox: List[float]


class ProcessingResult(BaseModel):
    document_id: str
    filename: str
    doc_type: str
    detected_language: str = "en"
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: float = 0.0
    overall_confidence: float = 0.0
    needs_review: bool = False
    data: dict  # InvoiceData or ContractData serialized
    overlay_pdf_path: Optional[str] = None
    ocr_words: List[OCRWordSchema] = Field(default_factory=list)
    raw_ocr_text: Optional[str] = None


class BatchSummaryRow(BaseModel):
    document_id: str
    filename: str
    doc_type: str
    overall_confidence: float
    needs_review: bool
    processing_time_ms: float
    status: str
