"""
Stage 4 - Field & Clause Extraction Engine
Implements RuleBasedExtractor (Regex + Heuristics + Math Verification + Risk Engine)
and MLExtractor adapter (LayoutLMv3 / SmolVLM).
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from app.pipeline.ocr import OCRWord, words_to_text
from app.schemas import (
    ClauseSpan,
    ContractData,
    FieldValue,
    InvoiceData,
    LineItem,
    MathValidation,
    RiskFlag,
)

REVIEW_THRESHOLD = 0.85

# Multi-currency symbols
CURRENCY_MAP = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "₹": "INR",
    "¥": "JPY",
    "C$": "CAD",
    "A$": "AUD",
}

PATTERNS = {
    "invoice_number": re.compile(
        r"(?:invoice\s*(?:no|number|#|id)\s*[:\-]?\s*)([A-Za-z0-9\-\/]+)", re.I
    ),
    "invoice_date": re.compile(
        r"(?:invoice\s*date|date|bill\s*date)\s*[:\-]?\s*"
        r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})",
        re.I,
    ),
    "due_date": re.compile(
        r"(?:due\s*date|payment\s*due)\s*[:\-]?\s*"
        r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})",
        re.I,
    ),
    "grand_total": re.compile(
        r"(?:grand\s*total|total\s*due|total\s*amount|total\s*payable|(?<!sub\s)(?<!sub)total)"
        r"\s*[:\-]?\s*[\$€£₹¥]?\s*([\d,]+\.\d{2})",
        re.I,
    ),
    "subtotal": re.compile(
        r"(?:sub\s*total|net\s*amount)\s*[:\-]?\s*[\$€£₹¥]?\s*([\d,]+\.\d{2})", re.I
    ),
    "tax_amount": re.compile(
        r"(?:tax|vat|gst|sales\s*tax)\s*(?:\(\d+%\))?\s*[:\-]?\s*[\$€£₹¥]?\s*([\d,]+\.\d{2})",
        re.I,
    ),
    "tax_id": re.compile(
        r"(?:tax\s*id|gstin|ein|vat\s*no|tax\s*#)\s*[:\-]?\s*([A-Za-z0-9\-]+)", re.I
    ),
}

CONTRACT_PATTERNS = {
    "effective_date": re.compile(
        r"(?:effective\s*(?:date|as\s*of)?|dated)\s*[:\-]?\s*"
        r"([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
        re.I,
    ),
    "governing_law": re.compile(
        r"governed\s+by\s+(?:the\s+)?laws?\s*of\s+([A-Za-z ,]+?)(?:\.|,|\n|$)", re.I
    ),
    "term_duration": re.compile(
        r"(?:term\s*(?:duration)?\s*[:\-]?\s*(?:of\s*(?:this\s*agreement\s*)?(?:shall\s*be|is|shal\s*be)\s*)?|term\s*of\s*(?:this\s*agreement\s*(?:shall\s*be|is|shal\s*be)\s*)?)(\d+\s*(?:day|month|year)s?)",
        re.I,
    ),
}

CLAUSE_KEYWORDS = {
    "termination": ["terminate", "termination", "cancelation", "cancel"],
    "confidentiality": ["confidential", "non-disclosure", "secret", "proprietary"],
    "indemnification": ["indemnify", "indemnification", "hold harmless"],
    "governing_law": ["governing law", "jurisdiction", "venue"],
    "payment_terms": ["payment terms", "invoice", "net 30", "net 60", "late fee"],
    "limitation_of_liability": ["limitation of liability", "liable", "consequential damages"],
    "intellectual_property": ["intellectual property", "ownership", "work for hire", "ip rights"],
}


def _detect_currency(text: str) -> Tuple[str, str]:
    """Auto-detect currency symbol and ISO 4217 code."""
    for symbol, code in CURRENCY_MAP.items():
        if symbol in text:
            return symbol, code
    if re.search(r"\bUSD\b|\bDollars\b", text, re.I):
        return "$", "USD"
    if re.search(r"\bEUR\b|\bEuros\b", text, re.I):
        return "€", "EUR"
    if re.search(r"\bGBP\b|\bPounds\b", text, re.I):
        return "£", "GBP"
    if re.search(r"\bINR\b|\bRupees\b", text, re.I):
        return "₹", "INR"
    return "$", "USD"


def _clean_amount(val_str: Optional[str]) -> Optional[float]:
    if not val_str:
        return None
    try:
        clean = re.sub(r"[^\d\.]", "", val_str)
        return float(clean)
    except (ValueError, TypeError):
        return None


def _validate_financial_math(
    subtotal: Optional[str],
    tax_amount: Optional[str],
    grand_total: Optional[str],
    line_items: List[LineItem],
) -> MathValidation:
    """Automated double-entry reconciliation engine."""
    sub_val = _clean_amount(subtotal)
    tax_val = _clean_amount(tax_amount) or 0.0
    total_val = _clean_amount(grand_total)

    # Calculate line items sum
    item_total_sum = sum(
        _clean_amount(item.total) or 0.0 for item in line_items if item.total
    )

    if sub_val is not None and total_val is not None:
        calc_total = round(sub_val + tax_val, 2)
        diff = abs(calc_total - total_val)
        is_balanced = diff < 0.05

        if is_balanced:
            msg = f"Math Verified: Subtotal ({sub_val:.2f}) + Tax ({tax_val:.2f}) = Grand Total ({total_val:.2f})"
        else:
            msg = f"Discrepancy Detected: Subtotal + Tax = {calc_total:.2f} but extracted Total is {total_val:.2f} (diff: {diff:.2f})"

        return MathValidation(
            is_valid=is_balanced,
            subtotal=sub_val,
            tax_amount=tax_val,
            calculated_grand_total=calc_total,
            extracted_grand_total=total_val,
            discrepancy=diff,
            line_items_sum=round(item_total_sum, 2) if item_total_sum > 0 else None,
            message=msg,
        )

    return MathValidation(
        is_valid=True,
        subtotal=sub_val,
        tax_amount=tax_val,
        extracted_grand_total=total_val,
        message="Partial amounts extracted; reconciliation skipped.",
    )


def _analyze_contract_risks(clauses: List[ClauseSpan], text: str) -> Tuple[List[RiskFlag], str]:
    """Scan legal clauses for high-liability and unfavorable legal obligations."""
    flags: List[RiskFlag] = []
    text_lower = text.lower()

    for c in clauses:
        c_text = c.text.lower()
        if c.clause_type == "limitation_of_liability":
            if "unlimited" in c_text or "no limitation" in c_text or "uncapped" in c_text:
                flags.append(
                    RiskFlag(
                        clause_type="limitation_of_liability",
                        risk_level="HIGH",
                        reason="Uncapped liability detected. Exposure not limited to contract value.",
                        recommendation="Cap liability to the fees paid over the preceding 12 months.",
                    )
                )
        elif c.clause_type == "termination":
            if "immediate" in c_text and "without notice" in c_text:
                flags.append(
                    RiskFlag(
                        clause_type="termination",
                        risk_level="MEDIUM",
                        reason="Immediate termination for convenience without reasonable cure period.",
                        recommendation="Require standard 30 days written notice with 15-day right to cure.",
                    )
                )
        elif c.clause_type == "indemnification":
            if "sole expense" in c_text or "broad form" in c_text or "hold harmless" in c_text:
                flags.append(
                    RiskFlag(
                        clause_type="indemnification",
                        risk_level="MEDIUM",
                        reason="Broad indemnification clause without negligence/fault limitation.",
                        recommendation="Limit indemnity strictly to gross negligence and willful misconduct.",
                    )
                )

    if not any(c.clause_type == "confidentiality" for c in clauses):
        flags.append(
            RiskFlag(
                clause_type="confidentiality",
                risk_level="LOW",
                reason="No explicit Confidentiality or NDA clause identified.",
                recommendation="Attach standard Mutual Non-Disclosure Addendum.",
            )
        )

    highest_risk = "LOW"
    if any(f.risk_level == "HIGH" for f in flags):
        highest_risk = "HIGH"
    elif any(f.risk_level == "MEDIUM" for f in flags):
        highest_risk = "MEDIUM"

    return flags, highest_risk


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
            for candidate in lines[i + 1 : i + 3]:
                cand_clean = candidate.strip()
                if cand_clean and not any(
                    k in cand_clean.lower()
                    for k in ["from", "bill to", "vendor", "date", "invoice", "total"]
                ):
                    return cand_clean
    return None


class RuleBasedExtractor:
    """Fast, production-hardened baseline extractor."""

    def extract_invoice(self, words: List[OCRWord]) -> InvoiceData:
        text = words_to_text(words)
        currency_sym, currency_code = _detect_currency(text)

        inv_num = _field_from_match(PATTERNS["invoice_number"].search(text))
        inv_date = _field_from_match(PATTERNS["invoice_date"].search(text))
        due_date = _field_from_match(PATTERNS["due_date"].search(text))
        subtotal = _field_from_match(PATTERNS["subtotal"].search(text))
        tax_amount = _field_from_match(PATTERNS["tax_amount"].search(text))
        grand_total = _field_from_match(PATTERNS["grand_total"].search(text))
        tax_id = _field_from_match(PATTERNS["tax_id"].search(text))

        vendor = _find_name_near_keyword(text, "from") or _find_name_near_keyword(
            text, "vendor"
        )
        buyer = _find_name_near_keyword(text, "bill to") or _find_name_near_keyword(
            text, "to"
        )

        vendor_field = FieldValue(
            value=vendor, confidence=0.6 if vendor else 0.0, needs_review=True
        )
        buyer_field = FieldValue(
            value=buyer, confidence=0.6 if buyer else 0.0, needs_review=True
        )

        line_items = self._extract_line_items(text)
        math_check = _validate_financial_math(
            subtotal.value, tax_amount.value, grand_total.value, line_items
        )

        return InvoiceData(
            currency_symbol=currency_sym,
            currency_code=currency_code,
            invoice_number=inv_num,
            invoice_date=inv_date,
            due_date=due_date,
            vendor_name=vendor_field,
            vendor_tax_id=tax_id,
            buyer_name=buyer_field,
            subtotal=subtotal,
            tax_amount=tax_amount,
            grand_total=grand_total,
            line_items=line_items,
            math_validation=math_check,
        )

    def _extract_line_items(self, text: str) -> List[LineItem]:
        row_pattern = re.compile(
            r"(?P<desc>[A-Za-z][A-Za-z0-9 \-]{2,40}?)\s+"
            r"(?P<qty>\d+(?:\.\d+)?)\s+"
            r"[\$€£₹¥]?(?P<price>[\d,]+\.\d{2})\s+"
            r"[\$€£₹¥]?(?P<total>[\d,]+\.\d{2})\s*$"
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
                        confidence=0.65,
                    )
                )
        return items

    def extract_contract(self, words: List[OCRWord]) -> ContractData:
        text = words_to_text(words)

        eff_date = _field_from_match(CONTRACT_PATTERNS["effective_date"].search(text))
        gov_law = _field_from_match(
            CONTRACT_PATTERNS["governing_law"].search(text), base_conf=0.65
        )
        term_dur = _field_from_match(
            CONTRACT_PATTERNS["term_duration"].search(text), base_conf=0.65
        )

        parties = re.findall(
            r'["“]?([A-Za-z0-9 ,\.&]{3,40}?)(?:["”]|:)?\s*\(\s*(?:the\s*)?(?:Party\s*[AB]|Client|Vendor|Company|Customer)\b',
            text,
            re.I,
        )
        if not parties:
            m_between = re.search(
                r"by\s*and\s*between\s*[:\-]?\s*([A-Za-z0-9 ,\.&]+?)\s+(?:and|&)\s+([A-Za-z0-9 ,\.&]+?)(?:\.|\n|\()",
                text,
                re.I,
            )
            if m_between:
                parties = [m_between.group(1).strip(), m_between.group(2).strip()]

        stop_words = {"the", "and", "or", "of", "in", "by", "for", "party a", "party b"}
        cleaned_parties = []
        for p in parties:
            clean = re.sub(r'^[^\w]+|[^\w\.]+$', "", p).strip()
            if len(clean) > 2 and clean.lower() not in stop_words:
                cleaned_parties.append(clean)

        party_a = (
            FieldValue(value=cleaned_parties[0], confidence=0.65)
            if len(cleaned_parties) >= 1
            else FieldValue()
        )
        party_b = (
            FieldValue(value=cleaned_parties[1], confidence=0.65)
            if len(cleaned_parties) >= 2
            else FieldValue()
        )

        clauses = self._extract_clauses(text)
        risk_flags, risk_score = _analyze_contract_risks(clauses, text)

        # Detect Title
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title = lines[0] if lines else "Legal Agreement"

        return ContractData(
            contract_title=title[:60],
            party_a=party_a,
            party_b=party_b,
            effective_date=eff_date,
            governing_law=gov_law,
            term_duration=term_dur,
            clauses=clauses,
            risk_flags=risk_flags,
            overall_risk_score=risk_score,
        )

    def _extract_clauses(self, text: str) -> List[ClauseSpan]:
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
    def __init__(self, checkpoint_path: str):
        raise NotImplementedError(
            "Load your fine-tuned model checkpoint here. See training/README.md"
        )

    def extract_invoice(self, words: List[OCRWord]) -> InvoiceData:
        raise NotImplementedError

    def extract_contract(self, words: List[OCRWord]) -> ContractData:
        raise NotImplementedError


def get_extractor(backend: str = "rules", checkpoint_path: str = ""):
    if backend == "ml":
        return MLExtractor(checkpoint_path)
    return RuleBasedExtractor()
