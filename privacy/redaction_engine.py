"""
Confidence-Aware Selective Redaction Engine.
SIH PS 26171: On-device Visual Perception for Light-weight Browser Agents.

Applies selective local redaction on visual screen captures and text DOM contexts.
Preserves non-sensitive operational UI structure while enforcing zero sensitive data leakage.
"""
from __future__ import annotations

import io
import re
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw
from privacy.pii_fusion import FusedPIIRegion


class RedactionEngine:
    def __init__(self, mask_color: Tuple[int, int, int] = (20, 20, 20)):
        self.mask_color = mask_color

    def redact_text_string(self, text: str, sensitive_patterns: Optional[List[Tuple[str, str]]] = None) -> Tuple[str, int]:
        """
        Redacts sensitive tokens in prose text strings, replacing with [REDACTED_<TYPE>].
        Returns (sanitized_text, count_redacted).
        """
        if not text:
            return text, 0

        sanitized = text
        count = 0

        # Patterns to sanitize
        rules = [
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[REDACTED_EMAIL]"),
            (r"(?<!\d)(?:\+91[\-\s]?)?[6789]\d{4}[\-\s]?\d{5}(?!\d)", "[REDACTED_PHONE]"),
            (r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "[REDACTED_CARD]"),
            (r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", "[REDACTED_PAN]"),
            (r"\b[2-9]\d{3}[\-\s]?\d{4}[\-\s]?\d{4}\b", "[REDACTED_AADHAAR]"),
            (r"\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b", "[REDACTED_UPI]")
        ]

        for pat, replacement in rules:
            matches = list(re.finditer(pat, sanitized))
            if matches:
                count += len(matches)
                sanitized = re.sub(pat, replacement, sanitized)

        return sanitized, count

    def redact_image(
        self,
        image_bytes: bytes,
        sensitive_regions: List[FusedPIIRegion]
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Applies pixel-level selective bounding box masking on image bytes.
        Only masks the detected sensitive regions, leaving operational UI elements intact.
        """
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception:
            return image_bytes, {"error": "Invalid image format"}

        w, h = img.size
        draw = ImageDraw.Draw(img)
        redacted_count = 0
        total_redacted_area = 0

        for region in sensitive_regions:
            x1 = int(region.bbox[0] * w)
            y1 = int(region.bbox[1] * h)
            x2 = int(region.bbox[2] * w)
            y2 = int(region.bbox[3] * h)

            # Draw solid privacy mask box
            draw.rectangle([x1, y1, x2, y2], fill=self.mask_color)
            redacted_count += 1
            total_redacted_area += max(0, x2 - x1) * max(0, y2 - y1)

        out_buffer = io.BytesIO()
        img.save(out_buffer, format="JPEG", quality=85)
        sanitized_bytes = out_buffer.getvalue()

        total_screen_area = w * h
        redaction_coverage_pct = round((total_redacted_area / total_screen_area) * 100, 2) if total_screen_area > 0 else 0

        metrics = {
            "image_width": w,
            "image_height": h,
            "regions_masked": redacted_count,
            "redacted_area_px": total_redacted_area,
            "screen_coverage_pct": redaction_coverage_pct,
            "selective_preservation_pct": round(100.0 - redaction_coverage_pct, 2)
        }

        return sanitized_bytes, metrics

    def compute_redaction_metrics(
        self,
        ground_truth_bboxes: List[List[float]],
        predicted_bboxes: List[List[float]]
    ) -> Dict[str, float]:
        """
        Measures Redaction IoU, Leakage Rate, Over-redaction, and Under-redaction.
        """
        if not ground_truth_bboxes and not predicted_bboxes:
            return {"iou": 1.0, "leakage_rate": 0.0, "over_redaction": 0.0, "under_redaction": 0.0}

        if not ground_truth_bboxes and predicted_bboxes:
            return {"iou": 0.0, "leakage_rate": 0.0, "over_redaction": 1.0, "under_redaction": 0.0}

        if ground_truth_bboxes and not predicted_bboxes:
            return {"iou": 0.0, "leakage_rate": 1.0, "over_redaction": 0.0, "under_redaction": 1.0}

        # Calculate bounding box overlaps
        from privacy.pii_fusion import calculate_iou
        matched_gt = 0
        total_iou = 0.0

        for gt in ground_truth_bboxes:
            best_iou = max([calculate_iou(gt, pred) for pred in predicted_bboxes]) if predicted_bboxes else 0.0
            if best_iou >= 0.5:
                matched_gt += 1
            total_iou += best_iou

        mean_iou = total_iou / len(ground_truth_bboxes)
        leakage = 1.0 - (matched_gt / len(ground_truth_bboxes))
        over_redact = max(0.0, (len(predicted_bboxes) - matched_gt) / max(1, len(predicted_bboxes)))
        under_redact = 1.0 - (matched_gt / len(ground_truth_bboxes))

        return {
            "iou": round(mean_iou, 4),
            "leakage_rate": round(leakage, 4),
            "over_redaction": round(over_redact, 4),
            "under_redaction": round(under_redact, 4)
        }
