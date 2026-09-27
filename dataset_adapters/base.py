"""
Unified Data Schema and Base Adapter for Visiionary Browser Agent.
Implements the normalized intermediate representation, UI Taxonomy (34 classes),
and PII Taxonomy (26 classes including Indian context).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from abc import ABC, abstractmethod


# =====================================================================
# 1. Unified UI Label Taxonomy (34 Categories)
# =====================================================================
UI_TAXONOMY: List[str] = [
    "button",
    "link",
    "text",
    "heading",
    "input",
    "password_input",
    "search",
    "checkbox",
    "radio",
    "select",
    "dropdown",
    "menu",
    "tab",
    "navigation",
    "sidebar",
    "toolbar",
    "table",
    "list",
    "image",
    "icon",
    "avatar",
    "notification",
    "dialog",
    "modal",
    "scroll",
    "slider",
    "calendar",
    "date_picker",
    "pagination",
    "code",
    "chart",
    "video",
    "window",
    "other"
]

UI_LABEL_TO_ID: Dict[str, int] = {label: idx for idx, label in enumerate(UI_TAXONOMY)}
ID_TO_UI_LABEL: Dict[int, str] = {idx: label for idx, label in enumerate(UI_TAXONOMY)}


# =====================================================================
# 2. Unified PII Taxonomy (26 Categories with Indian Context)
# =====================================================================
PII_TAXONOMY: List[str] = [
    "PERSON",
    "EMAIL",
    "PHONE",
    "ADDRESS",
    "PASSWORD",
    "OTP",
    "CREDIT_CARD",
    "DEBIT_CARD",
    "BANK_ACCOUNT",
    "IFSC",
    "UPI_ID",
    "AADHAAR",
    "PAN",
    "PASSPORT",
    "DRIVERS_LICENSE",
    "DATE_OF_BIRTH",
    "FINANCIAL_VALUE",
    "API_KEY",
    "ACCESS_TOKEN",
    "JWT",
    "SECRET",
    "PRIVATE_MESSAGE",
    "FACE",
    "QR_CODE",
    "USERNAME",
    "OTHER_IDENTIFIER"
]

PII_LABEL_TO_ID: Dict[str, int] = {label: idx for idx, label in enumerate(PII_TAXONOMY)}
ID_TO_PII_LABEL: Dict[int, str] = {idx: label for idx, label in enumerate(PII_TAXONOMY)}


# =====================================================================
# 3. Action Types Taxonomy
# =====================================================================
ACTION_TYPES: List[str] = [
    "CLICK",
    "TYPE",
    "SCROLL",
    "SELECT",
    "HOVER",
    "PRESS",
    "NAVIGATE",
    "WAIT",
    "TERMINATE"
]


# =====================================================================
# 4. Data Classes for Normalized Schema
# =====================================================================
@dataclass
class UIElement:
    bbox: List[float]  # [x1, y1, x2, y2] normalized to [0, 1]
    type: str          # Must be in UI_TAXONOMY
    text: Optional[str] = None
    interactable: bool = False
    sensitive: bool = False
    pii_type: Optional[str] = None

    def validate(self) -> bool:
        if len(self.bbox) != 4:
            return False
        x1, y1, x2, y2 = self.bbox
        if not (0.0 <= x1 <= 1.0 and 0.0 <= y1 <= 1.0 and 0.0 <= x2 <= 1.0 and 0.0 <= y2 <= 1.0):
            return False
        if x2 < x1 or y2 < y1:
            return False
        if self.type not in UI_TAXONOMY:
            self.type = "other"
        return True


@dataclass
class PIIAnnotation:
    bbox: List[float]  # [x1, y1, x2, y2] normalized to [0, 1]
    type: str          # Must be in PII_TAXONOMY
    confidence: float = 1.0
    text: Optional[str] = None  # Redacted or masked if stored

    def validate(self) -> bool:
        if len(self.bbox) != 4:
            return False
        x1, y1, x2, y2 = self.bbox
        if not (0.0 <= x1 <= 1.0 and 0.0 <= y1 <= 1.0 and 0.0 <= x2 <= 1.0 and 0.0 <= y2 <= 1.0):
            return False
        if x2 < x1 or y2 < y1:
            return False
        if self.type not in PII_TAXONOMY:
            self.type = "OTHER_IDENTIFIER"
        return True


@dataclass
class ActionAnnotation:
    type: str  # CLICK, TYPE, etc.
    target_bbox: Optional[List[float]] = None
    value: Optional[str] = None
    direction: Optional[str] = None


@dataclass
class UnifiedSample:
    sample_id: str
    source_dataset: str
    image: Optional[str] = None               # File path or reference
    image_bytes: Optional[bytes] = None       # Optional in-memory bytes
    width: int = 1280
    height: int = 720
    elements: List[UIElement] = field(default_factory=list)
    pii: List[PIIAnnotation] = field(default_factory=list)
    task: Optional[str] = None
    action: Optional[ActionAnnotation] = None
    dom: Optional[str] = None
    accessibility_tree: Optional[str] = None

    def to_dict(self, include_bytes: bool = False) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "sample_id": self.sample_id,
            "source_dataset": self.source_dataset,
            "image": self.image,
            "width": self.width,
            "height": self.height,
            "elements": [asdict(e) for e in self.elements],
            "pii": [asdict(p) for p in self.pii],
            "task": self.task,
            "action": asdict(self.action) if self.action else None,
            "dom": self.dom,
            "accessibility_tree": self.accessibility_tree
        }
        if include_bytes and self.image_bytes is not None:
            d["image_bytes_len"] = len(self.image_bytes)
        return d


# =====================================================================
# 5. Base Adapter Interface
# =====================================================================
class BaseDatasetAdapter(ABC):
    def __init__(self, name: str, source_dir: Path):
        self.name = name
        self.source_dir = Path(source_dir)

    @abstractmethod
    def count_samples(self) -> int:
        """Return total raw samples found."""
        pass

    @abstractmethod
    def iter_samples(self, limit: Optional[int] = None):
        """Yield UnifiedSample instances."""
        pass

    def validate_sample(self, sample: UnifiedSample) -> Tuple[bool, List[str]]:
        """Validate sample dimensions, bounding boxes, and taxonomy labels."""
        errors = []
        if sample.width <= 0 or sample.height <= 0:
            errors.append(f"Invalid dimensions: {sample.width}x{sample.height}")

        valid_elements = []
        for el in sample.elements:
            if el.validate():
                valid_elements.append(el)
            else:
                errors.append(f"Invalid UI element bbox: {el.bbox}")
        sample.elements = valid_elements

        valid_pii = []
        for p in sample.pii:
            if p.validate():
                valid_pii.append(p)
            else:
                errors.append(f"Invalid PII bbox: {p.bbox}")
        sample.pii = valid_pii

        return (len(errors) == 0, errors)
