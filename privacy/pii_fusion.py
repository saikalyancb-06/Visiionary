"""
Local Perception & Privacy Fusion Engine.
SIH PS 26171: On-device Visual Perception for Light-weight Browser Agents.

Integrates DOM semantics, OCR, Regex, and Visual Model detections into unified,
non-overlapping sensitive regions with fused multi-modal confidence scores.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from privacy.confidence_engine import ConfidenceEngine, SignalCandidate

def calculate_iou(boxA: List[float], boxB: List[float]) -> float:
    """Computes Intersection over Union between two normalized [x1, y1, x2, y2] bboxes."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0.0, xB - xA) * max(0.0, yB - yA)
    boxAArea = max(0.0, boxA[2] - boxA[0]) * max(0.0, boxA[3] - boxA[1])
    boxBArea = max(0.0, boxB[2] - boxB[0]) * max(0.0, boxB[3] - boxB[1])
    unionArea = boxAArea + boxBArea - interArea
    if unionArea <= 0.0:
        return 0.0
    return interArea / unionArea


@dataclass
class FusedPIIRegion:
    pii_type: str
    bbox: List[float]                  # [x1, y1, x2, y2] normalized
    fused_confidence: float
    contributing_modalities: List[str]
    is_sensitive: bool = True
    surrounding_context: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LocalPrivacyFusionEngine:
    def __init__(self, confidence_threshold: float = 0.50, iou_merge_threshold: float = 0.30):
        self.conf_threshold = confidence_threshold
        self.iou_threshold = iou_merge_threshold
        self.engine = ConfidenceEngine()

    def fuse(
        self,
        dom_elements: Optional[List[Dict[str, Any]]] = None,
        ocr_results: Optional[List[Dict[str, Any]]] = None,
        vision_detections: Optional[List[Dict[str, Any]]] = None,
        prose_texts: Optional[List[str]] = None
    ) -> List[FusedPIIRegion]:
        raw_candidates: List[SignalCandidate] = []

        # 1. Harvest DOM Candidates
        if dom_elements:
            for elem in dom_elements:
                raw_candidates.extend(self.engine.evaluate_dom_element(elem))

        # 2. Harvest OCR & Text Regex Candidates
        if ocr_results:
            for item in ocr_results:
                text = item.get("text", "")
                bbox = item.get("bbox", [0.0, 0.0, 1.0, 1.0])
                raw_candidates.extend(self.engine.evaluate_text_pattern(text, bbox))

        if prose_texts:
            for txt in prose_texts:
                raw_candidates.extend(self.engine.evaluate_text_pattern(txt))

        # 3. Harvest Visual Model Detections
        if vision_detections:
            for det in vision_detections:
                raw_candidates.append(SignalCandidate(
                    source="VISION",
                    pii_type=det.get("class", "OTHER_IDENTIFIER"),
                    confidence=float(det.get("confidence", 0.70)),
                    bbox=det.get("bbox", [0.0, 0.0, 1.0, 1.0]),
                    metadata=det
                ))

        # 4. Group and Fuse Overlapping Candidates
        fused_regions: List[FusedPIIRegion] = []
        visited = set()

        for i, c1 in enumerate(raw_candidates):
            if i in visited:
                continue
            
            group = [c1]
            visited.add(i)
            
            for j, c2 in enumerate(raw_candidates):
                if j in visited:
                    continue
                # If bboxes overlap significantly or share identical PII types in close proximity
                iou = calculate_iou(c1.bbox, c2.bbox)
                if iou >= self.iou_threshold or (c1.pii_type == c2.pii_type and iou > 0.1):
                    group.append(c2)
                    visited.add(j)

            # Compute fused bounding box (enclosing box)
            x1 = min(c.bbox[0] for c in group)
            y1 = min(c.bbox[1] for c in group)
            x2 = max(c.bbox[2] for c in group)
            y2 = max(c.bbox[3] for c in group)

            # Resolve winning PII type by priority (Checksum > DOM > Regex > OCR > Vision)
            priority_order = {"CHECKSUM": 5, "DOM": 4, "REGEX": 3, "OCR": 2, "VISION": 1}
            best_cand = max(group, key=lambda c: (priority_order.get(c.source, 0), c.confidence))
            resolved_type = best_cand.pii_type

            # Bayesian multi-signal fusion
            scores = [c.confidence for c in group]
            fused_conf = self.engine.fuse_confidence_scores(scores)
            modalities = sorted(list(set(c.source for c in group)))

            if fused_conf >= self.conf_threshold:
                fused_regions.append(FusedPIIRegion(
                    pii_type=resolved_type,
                    bbox=[round(x1, 4), round(y1, 4), round(x2, 4), round(y2, 4)],
                    fused_confidence=fused_conf,
                    contributing_modalities=modalities,
                    is_sensitive=True
                ))

        return fused_regions
