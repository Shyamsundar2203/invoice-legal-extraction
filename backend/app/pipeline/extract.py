"""
Stage 4 - Field & Clause Extraction

Two extraction backends are provided behind the same interface
(`extract_invoice_fields` / `extract_contract_fields`):

1. RuleBasedExtractor  - regex + keyword heuristics on top of OCR text.
   Works immediately, no GPU/model download required. This is the
   default backend so the project is runnable out of the box.

2. MLExtractor          - loads a fine-tuned LayoutLMv3 / SmolVLM checkpoint
   (see /training) and does token classification. Enable it by setting
   EXTRACTION_BACKEND=ml in backend/app/config.py once you have a trained
   model checkpoint (produced by training/train_layoutlmv3.py or
   training/train_smolvlm_invoice.py run on Colab/Kaggle with GPU).

Both backends return the same schemas.InvoiceData / schemas.ContractData
so the rest of the API never has to know which one produced the result.
"""
from __future__ import annotations

import re
from typing import List, Optional

from app.pipeline.ocr import OCRWord, words_to_text
from app.schemas import ClauseSpan, ContractData, FieldValue, InvoiceData, LineItem

REVIEW_THRESHOLD = 0.85

# ---------------------------------------------------------------------------
# Regex patterns used by the rule-based backend
# ---------------------------------------------------------------------------
PATTERNS = {
    "invoice_number": re.compile(
        r"(?:invoice\s*(?:no|number|#)\s*[:\-]?\s*)([A-Za-z0-9\-\/]+)", re.I
    ),
    "invoice_date": re.compile(
        r"(?:invoice\s*date|date)\s*[:\-]?\s*"
        r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})",
        re.I,
    ),
    "due_date": re.compile(
        r"due\s*date\s*[:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})", re.I
    ),
    "grand_total": re.compile(
        r"(?:grand\s*total|total\s*due|total\s*amount|(?<!sub\s)(?<!sub)total)"
        r"\s*[:\-]?\s*\$?\s*([\d,]+\.\d{2})",
        re.I,
    ),
    "subtotal": re.compile(r"sub\s*total\s*[:\-]?\s*\$?\s*([\d,]+\.\d{2})", re.I),
    "tax_amount": re.compile(
        r"(?:tax|vat|gst)\s*(?:\(\d+%\))?\s*[:\-]?\s*\$?\s*([\d,]+\.\d{2})", re.I
    ),
}

CONTRACT_PATTERNS = {
    "effective_date": re.compile(
        r"effective\s*(?:date|as of)\s*[:\-]?\s*"
        r"([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
        re.I,
    ),
    "governing_law": re.compile(
        r"governed by the laws of\s+([A-Za-z ,]+?)(?:\.|,|\n)", re.I
    ),
    "term_duration": re.compile(
        r"term of (?:this agreement (?:shall be|is) )?"
        r"(\d+\s*(?:day|month|year)s?)",
        re.I,
    ),
}

CLAUSE_KEYWORDS = {
    "termination": ["terminate", "termination"],
    "confidentiality": ["confidential", "non-disclosure"],
    "indemnification": ["indemnify", "indemnification", "hold harmless"],
    "governing_law": ["governing law", "jurisdiction"],
    "payment_terms": ["payment terms", "invoice", "net 30", "net 60"],
    "limitation_of_liability": ["limitation of liability", "liable"],
}


def _field_from_match(match: Optional[re.Match], base_conf: float = 0.7) -> FieldValue:
    if not match:
        return FieldValue(value=None, confidence=0.0, needs_review=True)
    value = match.group(1).strip()
    return FieldValue(
        value=value, confidence=base_conf, needs_review=base_conf < REVIEW_THRESHOLD
    )


def _find_name_near_keyword(text: str, keyword: str) -> Optional[str]:
    lines = text.splitlines()
    pattern = re.compile(rf"^(?:{re.escape(keyword)})\s*[:\-]?\s*(.+)$", re.I)
    for i, line in enumerate(lines):
        line_clean = line.strip()
        m = pattern.match(line_clean)
        if m and m.group(1).strip():
            return m.group(1).strip()
        if keyword.lower() in line_clean.lower():
            # If line only contained keyword or keyword was at end, check next lines
            for candidate in lines[i + 1 : i + 3]:
                cand_clean = candidate.strip()
                if cand_clean and not any(k in cand_clean.lower() for k in ["from", "bill to", "vendor", "date", "invoice", "total"]):
                    return cand_clean
    return None



class RuleBasedExtractor:
    """Fast, dependency-free baseline extractor using regex + keyword rules."""

    def extract_invoice(self, words: List[OCRWord]) -> InvoiceData:
        text = words_to_text(words)
        avg_conf = sum(w.conf for w in words) / len(words) if words else 0.0

        data = InvoiceData(
            invoice_number=_field_from_match(PATTERNS["invoice_number"].search(text)),
            invoice_date=_field_from_match(PATTERNS["invoice_date"].search(text)),
            due_date=_field_from_match(PATTERNS["due_date"].search(text)),
            subtotal=_field_from_match(PATTERNS["subtotal"].search(text)),
            tax_amount=_field_from_match(PATTERNS["tax_amount"].search(text)),
            grand_total=_field_from_match(PATTERNS["grand_total"].search(text)),
        )

        vendor = _find_name_near_keyword(text, "from") or _find_name_near_keyword(
            text, "vendor"
        )
        buyer = _find_name_near_keyword(text, "bill to") or _find_name_near_keyword(
            text, "to"
        )
        data.vendor_name = FieldValue(
            value=vendor, confidence=0.55 if vendor else 0.0, needs_review=True
        )
        data.buyer_name = FieldValue(
            value=buyer, confidence=0.55 if buyer else 0.0, needs_review=True
        )

        data.line_items = self._extract_line_items(text)
        return data

    def _extract_line_items(self, text: str) -> List[LineItem]:
        """Very lightweight row parser: `description  qty  price  total`."""
        row_pattern = re.compile(
            r"(?P<desc>[A-Za-z][A-Za-z0-9 \-]{2,40}?)\s+"
            r"(?P<qty>\d+(?:\.\d+)?)\s+"
            r"(?P<price>[\d,]+\.\d{2})\s+"
            r"(?P<total>[\d,]+\.\d{2})\s*$"
        )
        items: List[LineItem] = []
        for line in text.splitlines():
            m = row_pattern.match(line.strip())
            if m:
                items.append(
                    LineItem(
                        description=m.group("desc").strip(),
                        quantity=m.group("qty"),
                        unit_price=m.group("price"),
                        total=m.group("total"),
                        confidence=0.6,
                    )
                )
        return items

    def extract_contract(self, words: List[OCRWord]) -> ContractData:
        text = words_to_text(words)

        data = ContractData(
            effective_date=_field_from_match(
                CONTRACT_PATTERNS["effective_date"].search(text)
            ),
            governing_law=_field_from_match(
                CONTRACT_PATTERNS["governing_law"].search(text), base_conf=0.65
            ),
            term_duration=_field_from_match(
                CONTRACT_PATTERNS["term_duration"].search(text), base_conf=0.6
            ),
        )

        parties = re.findall(
            r'"([A-Z][A-Za-z0-9 ,\.&]+)"\s*\((?:the\s*)?"?(?:Party|Client|Vendor|Company)',
            text,
        )
        if len(parties) >= 1:
            data.party_a = FieldValue(value=parties[0], confidence=0.6)
        if len(parties) >= 2:
            data.party_b = FieldValue(value=parties[1], confidence=0.6)

        data.clauses = self._extract_clauses(text)
        return data

    def _extract_clauses(self, text: str) -> List[ClauseSpan]:
        """
        Scan paragraph-by-paragraph (falling back to line-by-line when the
        OCR text reconstruction collapses blank-line paragraph breaks) and
        tag any block that mentions a known clause keyword.
        """
        clauses: List[ClauseSpan] = []
        paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
        if len(paragraphs) <= 1:
            paragraphs = [line for line in text.splitlines() if line.strip()]

        for para in paragraphs:
            para_lower = para.lower()
            for clause_type, keywords in CLAUSE_KEYWORDS.items():
                if any(kw in para_lower for kw in keywords):
                    clauses.append(
                        ClauseSpan(
                            clause_type=clause_type,
                            text=para.strip()[:800],
                            confidence=0.7,
                        )
                    )
                    break
        return clauses


class MLExtractor:
    """
    Placeholder for the trained LayoutLMv3 / SmolVLM extractor.

    Load your fine-tuned checkpoint (see training/train_layoutlmv3.py or
    training/train_smolvlm_invoice.py) here and implement extract_invoice /
    extract_contract with the same signatures as RuleBasedExtractor so it's
    a drop-in replacement. Kept separate so the base project runs without
    requiring model weights.
    """

    def __init__(self, checkpoint_path: str):
        raise NotImplementedError(
            "Load your fine-tuned model checkpoint here. See training/README.md "
            "for how to produce one, then wire it up in app/config.py by "
            "setting EXTRACTION_BACKEND=ml and CHECKPOINT_PATH=<path>."
        )

    def extract_invoice(self, words: List[OCRWord]) -> InvoiceData:
        raise NotImplementedError

    def extract_contract(self, words: List[OCRWord]) -> ContractData:
        raise NotImplementedError


def get_extractor(backend: str = "rules", checkpoint_path: str = ""):
    if backend == "ml":
        return MLExtractor(checkpoint_path)
    return RuleBasedExtractor()
