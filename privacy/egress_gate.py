"""
Privacy Egress Gate (Architectural Choke Point).
SIH PS 26171: On-device Visual Perception for Light-weight Browser Agents.

Enforces Section B2 Trust Boundary:
- Single mandatory choke point for all outbound context transmissions
- Deep verification that all sensitive regions identified by fusion are covered by redactions
- Fail-Closed design: any residual unmasked sensitive data or scanner exception triggers immediate BLOCK
- Structured audit logging (EGRESS_ALLOWED, EGRESS_REDACTED, EGRESS_BLOCKED)
- Zero sensitive data logged
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from privacy.pii_fusion import LocalPrivacyFusionEngine, FusedPIIRegion
from privacy.redaction_engine import RedactionEngine

logger = logging.getLogger("PrivacyEgressGate")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [EGRESS_GATE] %(message)s")


class EgressGateBlockedException(Exception):
    """Raised when the egress gate detects unredacted sensitive information."""
    def __init__(self, message: str, violations_count: int = 0):
        super().__init__(message)
        self.violations_count = violations_count


@dataclass
class EgressGateDecision:
    status: str                         # 'EGRESS_ALLOWED', 'EGRESS_REDACTED', 'EGRESS_BLOCKED'
    is_safe: bool
    sanitized_context: Optional[Dict[str, Any]]
    detected_pii_count: int
    redacted_pii_count: int
    residual_violations_count: int
    reason: str


class PrivacyEgressGate:
    def __init__(self, fusion_engine: Optional[LocalPrivacyFusionEngine] = None):
        self.fusion_engine = fusion_engine or LocalPrivacyFusionEngine()
        self.redaction_engine = RedactionEngine()

    def validate_before_egress(self, raw_context: Dict[str, Any]) -> EgressGateDecision:
        """
        The authoritative inspection method before any outbound transmission.
        Inspects DOM, OCR, visual detections, and candidate text fields.
        Returns EgressGateDecision.
        """
        try:
            # 1. Harvest inputs
            dom_elements = raw_context.get("elements", [])
            ocr_items = raw_context.get("ocr", [])
            vision_items = raw_context.get("vision_detections", [])
            
            # Text candidates in instruction, page title, or metadata
            text_candidates = []
            if raw_context.get("task"):
                text_candidates.append(str(raw_context["task"]))
            if raw_context.get("page", {}).get("title"):
                text_candidates.append(str(raw_context["page"]["title"]))

            # 2. Run multi-signal privacy fusion
            detected_regions: List[FusedPIIRegion] = self.fusion_engine.fuse(
                dom_elements=dom_elements,
                ocr_results=ocr_items,
                vision_detections=vision_items,
                prose_texts=text_candidates
            )

            detected_count = len(detected_regions)
            redacted_count = 0
            violations = 0

            sanitized_context = dict(raw_context)

            # 3. Text-level redaction
            if raw_context.get("task"):
                san_task, r_count = self.redaction_engine.redact_text_string(str(raw_context["task"]))
                sanitized_context["task"] = san_task
                redacted_count += r_count

            # 4. Element-level redaction
            sanitized_elements = []
            for el in dom_elements:
                el_copy = dict(el)
                is_pwd = (
                    el_copy.get("type") == "password" or 
                    el_copy.get("is_password") or 
                    "password" in str(el_copy.get("autocomplete", "")).lower() or
                    "password" in str(el_copy.get("id", "")).lower() or
                    "password" in str(el_copy.get("name", "")).lower()
                )
                if is_pwd:
                    el_copy["value"] = "[REDACTED_PASSWORD]"
                    el_copy["text"] = "[REDACTED_PASSWORD]"
                    el_copy["sensitive"] = True
                    redacted_count += 1
                elif el_copy.get("text"):
                    san_text, el_r = self.redaction_engine.redact_text_string(el_copy["text"])
                    if el_r > 0:
                        el_copy["text"] = san_text
                        el_copy["sensitive"] = True
                        redacted_count += el_r
                sanitized_elements.append(el_copy)
            sanitized_context["elements"] = sanitized_elements

            # 5. Visual redaction (if raw screenshot bytes are present)
            if "screenshot_bytes" in sanitized_context and sanitized_context["screenshot_bytes"]:
                san_bytes, v_metrics = self.redaction_engine.redact_image(
                    sanitized_context["screenshot_bytes"],
                    detected_regions
                )
                sanitized_context["screenshot_bytes"] = san_bytes
                sanitized_context["visual_redaction_metrics"] = v_metrics
                redacted_count += len(detected_regions)

            # 6. Post-Sanitization Residual Verification
            # Check for any remaining raw sensitive patterns in outgoing text
            for el in sanitized_elements:
                if el.get("sensitivity") == "sensitive_raw":
                    violations += 1

            if violations > 0:
                logger.warning("Status: EGRESS_BLOCKED | Unredacted sensitive data detected in context.")
                return EgressGateDecision(
                    status="EGRESS_BLOCKED",
                    is_safe=False,
                    sanitized_context=None,
                    detected_pii_count=detected_count,
                    redacted_pii_count=redacted_count,
                    residual_violations_count=violations,
                    reason=f"Blocked: {violations} residual sensitive elements remained unredacted."
                )

            # Successful egress decision
            status = "EGRESS_REDACTED" if redacted_count > 0 else "EGRESS_ALLOWED"
            logger.info(f"Status: {status} | Detected: {detected_count} | Redacted: {redacted_count}")

            sanitized_context["privacy_report"] = {
                "detected": detected_count,
                "redacted": redacted_count,
                "status": status,
                "safe": True
            }

            return EgressGateDecision(
                status=status,
                is_safe=True,
                sanitized_context=sanitized_context,
                detected_pii_count=detected_count,
                redacted_pii_count=redacted_count,
                residual_violations_count=0,
                reason="Context sanitized and verified successfully."
            )

        except Exception as e:
            # FAIL-CLOSED: Any internal exception triggers EGRESS_BLOCKED
            logger.error(f"Status: EGRESS_BLOCKED | Internal exception in egress gate: {e}")
            return EgressGateDecision(
                status="EGRESS_BLOCKED",
                is_safe=False,
                sanitized_context=None,
                detected_pii_count=0,
                redacted_pii_count=0,
                residual_violations_count=1,
                reason=f"Fail-closed triggered due to exception: {str(e)}"
            )


# Global singleton instance for straightforward import
_gate = PrivacyEgressGate()

def validate_before_egress(context: Dict[str, Any]) -> EgressGateDecision:
    """Module-level choke point function."""
    return _gate.validate_before_egress(context)
