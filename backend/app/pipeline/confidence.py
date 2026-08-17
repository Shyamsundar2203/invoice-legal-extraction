"""
Stage 5 - Confidence Scoring & Human-in-the-loop flagging.
Combines per-field confidence into an overall document score and decides
whether the document as a whole needs human review.
"""
from __future__ import annotations

from typing import Union

from app.schemas import ContractData, FieldValue, InvoiceData

REVIEW_THRESHOLD = 0.85


def score_document(data: Union[InvoiceData, ContractData]) -> tuple[float, bool]:
    """Returns (overall_confidence, needs_review)."""
    field_values = [
        v for v in data.__dict__.values() if isinstance(v, FieldValue)
    ]
    confidences = [f.confidence for f in field_values if f.value is not None]

    if isinstance(data, InvoiceData):
        confidences += [li.confidence for li in data.line_items]
    if isinstance(data, ContractData):
        confidences += [c.confidence for c in data.clauses]

    if not confidences:
        return 0.0, True

    overall = sum(confidences) / len(confidences)
    needs_review = overall < REVIEW_THRESHOLD or any(
        f.needs_review for f in field_values
    )
    return round(overall, 4), needs_review
