"""
Multi-Signal Confidence Engine for Local Privacy Fusion.
SIH PS 26171: On-device Visual Perception for Light-weight Browser Agents.

Combines 5 independent detection modalities:
1. DOM Semantics (input type, autocomplete, aria tags, name/id hints)
2. Deterministic Regex & Mathematical Checksums (Verhoeff for Aadhaar, Luhn for Credit Cards)
3. OCR Text Extracted from Visual Canvas
4. Local Visual PII Detector Model Predictions
5. Accessibility Tree Roles and States
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

# Verhoeff tables for 12-digit Indian Aadhaar validation
VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]
VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

def validate_verhoeff(num_str: str) -> bool:
    digits = [int(c) for c in num_str if c.isdigit()]
    if not digits:
        return False
    c = 0
    for i, item in enumerate(reversed(digits)):
        c = VERHOEFF_D[c][VERHOEFF_P[i % 8][item]]
    return c == 0

def validate_luhn(card_str: str) -> bool:
    digits = [int(d) for d in re.sub(r"\D", "", card_str)]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = digit * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += digit
    return checksum % 10 == 0


@dataclass
class SignalCandidate:
    source: str         # 'DOM', 'REGEX', 'CHECKSUM', 'OCR', 'VISION', 'A11Y'
    pii_type: str       # Unified PII category
    confidence: float   # 0.0 - 1.0
    bbox: List[float]   # [x1, y1, x2, y2] normalized
    text: Optional[str] = None
    metadata: Dict[str, Any] = None


class ConfidenceEngine:
    # Modality baseline priors
    PRIORS = {
        "DOM_EXPLICIT_PASSWORD": 0.999,
        "DOM_AUTOCOMPLETE_CARD": 0.98,
        "DOM_INPUT_TYPE": 0.85,
        "CHECKSUM_VERIFIED": 0.995,
        "REGEX_HIGH_ENTROPY": 0.90,
        "REGEX_PATTERN": 0.80,
        "VISION_DETECTION": 0.75,
        "OCR_MATCH": 0.85,
        "A11Y_ROLE": 0.80
    }

    @staticmethod
    def evaluate_dom_element(elem: Dict[str, Any]) -> List[SignalCandidate]:
        candidates = []
        tag = elem.get("tagName", elem.get("tag", "")).lower()
        itype = elem.get("type", "").lower()
        autocomplete = elem.get("autocomplete", "").lower()
        name_id = f"{elem.get('id', '')} {elem.get('name', '')} {elem.get('placeholder', '')}".lower()
        bbox = elem.get("bbox", [0.0, 0.0, 1.0, 1.0])

        # Password input -> absolute certainty
        if itype == "password" or "password" in autocomplete:
            candidates.append(SignalCandidate(
                source="DOM",
                pii_type="PASSWORD",
                confidence=ConfidenceEngine.PRIORS["DOM_EXPLICIT_PASSWORD"],
                bbox=bbox,
                metadata={"field": "password"}
            ))

        # Credit card autocomplete / name hints
        if "cc-number" in autocomplete or "card-number" in name_id:
            candidates.append(SignalCandidate(
                source="DOM",
                pii_type="CREDIT_CARD",
                confidence=ConfidenceEngine.PRIORS["DOM_AUTOCOMPLETE_CARD"],
                bbox=bbox,
                metadata={"field": "cc-number"}
            ))

        # Email field
        if itype == "email" or "email" in autocomplete or "email" in name_id:
            candidates.append(SignalCandidate(
                source="DOM",
                pii_type="EMAIL",
                confidence=0.92,
                bbox=bbox,
                metadata={"field": "email"}
            ))

        # Phone field
        if itype == "tel" or "tel" in autocomplete or "phone" in name_id or "mobile" in name_id:
            candidates.append(SignalCandidate(
                source="DOM",
                pii_type="PHONE",
                confidence=0.90,
                bbox=bbox,
                metadata={"field": "tel"}
            ))

        return candidates

    @staticmethod
    def evaluate_text_pattern(text: str, bbox: Optional[List[float]] = None) -> List[SignalCandidate]:
        if not text:
            return []
        candidates = []
        bbox = bbox or [0.0, 0.0, 1.0, 1.0]

        # 1. Email Pattern
        email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
        if email_match:
            candidates.append(SignalCandidate(
                source="REGEX",
                pii_type="EMAIL",
                confidence=ConfidenceEngine.PRIORS["REGEX_PATTERN"],
                bbox=bbox,
                text=email_match.group(0)
            ))

        # 2. Indian Mobile Number (10 digits starting with 6, 7, 8, 9)
        phone_match = re.search(r"(?<!\d)(?:\+91[\-\s]?)?[6789]\d{4}[\-\s]?\d{5}(?!\d)", text)
        if phone_match:
            candidates.append(SignalCandidate(
                source="REGEX",
                pii_type="PHONE",
                confidence=0.88,
                bbox=bbox,
                text=phone_match.group(0)
            ))

        # 3. Aadhaar Number (12 digits with Verhoeff verification)
        aadhaar_match = re.search(r"\b[2-9]\d{3}[\-\s]?\d{4}[\-\s]?\d{4}\b", text)
        if aadhaar_match:
            clean_aadhaar = re.sub(r"\D", "", aadhaar_match.group(0))
            if len(clean_aadhaar) == 12 and validate_verhoeff(clean_aadhaar):
                candidates.append(SignalCandidate(
                    source="CHECKSUM",
                    pii_type="AADHAAR",
                    confidence=ConfidenceEngine.PRIORS["CHECKSUM_VERIFIED"],
                    bbox=bbox,
                    text="[REDACTED_AADHAAR]"
                ))

        # 4. PAN Card (5 uppercase + 4 digits + 1 uppercase)
        pan_match = re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", text)
        if pan_match:
            candidates.append(SignalCandidate(
                source="REGEX",
                pii_type="PAN",
                confidence=0.95,
                bbox=bbox,
                text="[REDACTED_PAN]"
            ))

        # 5. Credit Card (13-19 digits with Luhn verification)
        card_match = re.search(r"\b(?:\d{4}[-\s]?){3}\d{4}\b", text)
        if card_match:
            clean_card = re.sub(r"\D", "", card_match.group(0))
            if validate_luhn(clean_card):
                candidates.append(SignalCandidate(
                    source="CHECKSUM",
                    pii_type="CREDIT_CARD",
                    confidence=ConfidenceEngine.PRIORS["CHECKSUM_VERIFIED"],
                    bbox=bbox,
                    text="[REDACTED_CARD]"
                ))

        # 6. UPI ID
        upi_match = re.search(r"\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b", text)
        if upi_match and not email_match:
            candidates.append(SignalCandidate(
                source="REGEX",
                pii_type="UPI_ID",
                confidence=0.85,
                bbox=bbox,
                text="[REDACTED_UPI]"
            ))

        return candidates

    @staticmethod
    def fuse_confidence_scores(scores: List[float]) -> float:
        """
        Bayesian Independent Multi-Signal Fusion.
        P(PII | s1, s2, ...) = 1 - product(1 - P(si))
        """
        if not scores:
            return 0.0
        neg_product = 1.0
        for s in scores:
            neg_product *= (1.0 - min(0.999, max(0.01, s)))
        return float(round(1.0 - neg_product, 4))
