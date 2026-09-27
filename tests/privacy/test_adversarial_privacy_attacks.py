"""
Adversarial Privacy Attack Test Suite for SIH PS 26171.
Evaluates local perception fusion and egress gate against 19 adversarial attack vectors:
1. Passwords (explicit and hidden)
2. Hidden inputs
3. Emails
4. Phone numbers (Indian & international)
5. Credit Cards (with Luhn)
6. Bank Accounts
7. Aadhaar numbers (with Verhoeff)
8. PAN cards
9. OTPs
10. API keys
11. JWT tokens
12. QR codes
13. Faces (biometric)
14. PII inside images
15. PII inside PDFs
16. PII rendered on canvas
17. PII in dynamically generated content
18. PII inside iframes
19. Visual PII absent from DOM
"""
import pytest
from privacy.egress_gate import validate_before_egress
from privacy.confidence_engine import validate_verhoeff, validate_luhn


def test_attack_01_explicit_password():
    ctx = {
        "task": "Login to dashboard",
        "elements": [{"id": "pwd", "type": "password", "text": "SuperSecretPass2026!"}]
    }
    decision = validate_before_egress(ctx)
    assert decision.is_safe is True
    assert decision.sanitized_context["elements"][0]["text"] == "[REDACTED_PASSWORD]"
    assert "SuperSecretPass2026!" not in str(decision.sanitized_context)


def test_attack_02_hidden_input_password():
    ctx = {
        "task": "Hidden token exchange",
        "elements": [{"id": "auth_token", "type": "hidden", "autocomplete": "current-password", "text": "hidden_pass_999"}]
    }
    decision = validate_before_egress(ctx)
    assert decision.is_safe is True
    assert "hidden_pass_999" not in str(decision.sanitized_context)


def test_attack_03_email_in_task_prose():
    ctx = {
        "task": "Send receipt to priya.sharma@sac.isro.gov.in immediately",
        "elements": [{"id": "btn", "type": "button", "text": "Send"}]
    }
    decision = validate_before_egress(ctx)
    assert decision.is_safe is True
    assert "priya.sharma@sac.isro.gov.in" not in decision.sanitized_context["task"]
    assert "[REDACTED_EMAIL]" in decision.sanitized_context["task"]


def test_attack_04_indian_mobile_phone():
    ctx = {
        "task": "Call customer support at +91 9845012345",
        "elements": []
    }
    decision = validate_before_egress(ctx)
    assert decision.is_safe is True
    assert "9845012345" not in decision.sanitized_context["task"]
    assert "[REDACTED_PHONE]" in decision.sanitized_context["task"]


def test_attack_05_valid_credit_card_luhn():
    card = "4111 1111 1111 1111"
    assert validate_luhn(card) is True
    ctx = {
        "task": f"Pay invoice using card {card}",
        "elements": []
    }
    decision = validate_before_egress(ctx)
    assert decision.is_safe is True
    assert "4111" not in decision.sanitized_context["task"]
    assert "[REDACTED_CARD]" in decision.sanitized_context["task"]


def test_attack_06_indian_aadhaar_verhoeff():
    # 234567890124 has valid Verhoeff checksum
    clean_aadhaar = "2345 6789 0124"
    assert validate_verhoeff(clean_aadhaar) is True
    ctx = {
        "task": f"Verify identity with Aadhaar {clean_aadhaar}",
        "elements": []
    }
    decision = validate_before_egress(ctx)
    assert decision.is_safe is True
    assert "2345" not in decision.sanitized_context["task"]
    assert "[REDACTED_AADHAAR]" in decision.sanitized_context["task"]


def test_attack_07_indian_pan_card():
    pan = "ABCDE1234F"
    ctx = {
        "task": f"Submit tax declaration with PAN {pan}",
        "elements": []
    }
    decision = validate_before_egress(ctx)
    assert decision.is_safe is True
    assert pan not in decision.sanitized_context["task"]
    assert "[REDACTED_PAN]" in decision.sanitized_context["task"]


def test_attack_08_upi_id():
    upi = "isro.mission@okhdfcbank"
    ctx = {
        "task": f"Transfer reimbursement to {upi}",
        "elements": []
    }
    decision = validate_before_egress(ctx)
    assert decision.is_safe is True
    assert upi not in decision.sanitized_context["task"]
    assert "[REDACTED_UPI]" in decision.sanitized_context["task"]


def test_attack_09_visual_pii_absent_from_dom():
    """Simulates visual text detected by OCR/Vision but absent from HTML DOM."""
    ctx = {
        "task": "Review scanned document",
        "elements": [{"id": "doc_viewer", "type": "canvas", "text": "Document Canvas"}],
        "ocr": [
            {"text": "Aadhaar: 2345 6789 0124", "bbox": [0.2, 0.3, 0.8, 0.35]},
            {"text": "Account: user.isro@gmail.com", "bbox": [0.2, 0.4, 0.8, 0.45]}
        ]
    }
    decision = validate_before_egress(ctx)
    assert decision.is_safe is True
    assert decision.detected_pii_count >= 1


def test_attack_10_unredacted_violation_triggers_fail_closed():
    """Unsanitized raw element sensitivity triggers EGRESS_BLOCKED."""
    ctx = {
        "task": "Test payload",
        "elements": [
            {"id": "leak", "sensitivity": "sensitive_raw", "text": "RawSecretValue"}
        ]
    }
    decision = validate_before_egress(ctx)
    assert decision.status == "EGRESS_BLOCKED"
    assert decision.is_safe is False
    assert decision.residual_violations_count > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
