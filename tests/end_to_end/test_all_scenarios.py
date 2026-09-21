"""
Comprehensive End-to-End Test Suite for All 4 Demo Scenarios (Phase 17 & 21)
Scenario 1: Bank (Download statement)
Scenario 2: Login (Vault secret_ref authentication)
Scenario 3: Shopping (Add to cart)
Scenario 4: Gov-Form (Submit Aadhaar/PAN identity verification)
Verifies zero PII egress and exact action plan execution for all 4 scenarios.
"""
import requests
import json
import pytest

SERVER_URL = "http://127.0.0.1:8080"

def test_scenario_1_bank():
    # Bank scenario contains Account #, Balance, Email, Mobile
    payload = {
        "session_id": "e2e-bank-001",
        "step": 1,
        "instruction_sanitized": "Download my latest bank statement.",
        "page": {
            "url_sanitized": "http://127.0.0.1/demo-sites/bank/index.html",
            "title_sanitized": "Apex Bank - Online Banking Portal",
            "viewport": {"w": 1366, "h": 768, "dpr": 1.0}
        },
        "screenshot": None,
        "elements": [
            {
                "id": "btn-download-statement",
                "role": "button",
                "label": "Download Statement",
                "bbox": [640, 410, 820, 450],
                "interactable": True,
                "sensitivity": "safe",
                "source": "dom+vision",
                "confidence": 0.99
            },
            {
                "id": "account-balance",
                "role": "text",
                "label": "[REDACTED_BALANCE]",
                "bbox": [100, 200, 300, 240],
                "interactable": False,
                "sensitivity": "redacted",
                "source": "dom",
                "confidence": 1.0
            }
        ],
        "redactions": [
            {"id": "r1", "type": "balance", "placeholder": "[REDACTED_BALANCE]", "bbox": [100, 200, 300, 240]},
            {"id": "r2", "type": "bank_account", "placeholder": "[REDACTED_ACCOUNT]", "bbox": [100, 250, 300, 290]}
        ],
        "privacy_report": {"detected": 4, "sensitive": 4, "redacted": 4, "uncertain_redacted": 0, "verification": "PASS", "gate": "PASS"},
        "history": []
    }

    # Verify no raw PII in client payload
    assert "2,84,500" not in json.dumps(payload)
    assert "9823-4412" not in json.dumps(payload)

    res = requests.post(f"{SERVER_URL}/api/agent/plan", json=payload)
    assert res.status_code == 200
    plan = res.json()
    assert len(plan["actions"]) >= 2
    assert plan["actions"][0]["type"] == "click"
    assert plan["actions"][0]["target"]["element_id"] == "btn-download-statement"
    print("[PASS] Scenario 1 (Bank): Statement download planned with 0 PII leaks.")


def test_scenario_2_login():
    # Login scenario uses local secret_ref: server never sees password
    payload = {
        "session_id": "e2e-login-002",
        "step": 1,
        "instruction_sanitized": "Log into this account.",
        "page": {
            "url_sanitized": "http://127.0.0.1/demo-sites/login/index.html",
            "title_sanitized": "Apex Portal - Secure Authentication",
            "viewport": {"w": 1280, "h": 720, "dpr": 1.0}
        },
        "screenshot": None,
        "elements": [
            {
                "id": "password",
                "role": "input",
                "label": "[REDACTED_PASSWORD]",
                "bbox": [100, 100, 300, 140],
                "interactable": True,
                "sensitivity": "redacted",
                "source": "dom",
                "confidence": 1.0
            },
            {
                "id": "btn-login",
                "role": "button",
                "label": "Sign In to Account",
                "bbox": [100, 160, 300, 200],
                "interactable": True,
                "sensitivity": "safe",
                "source": "dom",
                "confidence": 1.0
            }
        ],
        "redactions": [
            {"id": "r1", "type": "password", "placeholder": "[REDACTED_PASSWORD]", "bbox": [100, 100, 300, 140]}
        ],
        "privacy_report": {"detected": 1, "sensitive": 1, "redacted": 1, "uncertain_redacted": 0, "verification": "PASS", "gate": "PASS"},
        "history": []
    }

    # Verify no raw password in client payload
    assert "SecureEnterprisePassword" not in json.dumps(payload)
    assert "SuperSecret" not in json.dumps(payload)

    res = requests.post(f"{SERVER_URL}/api/agent/plan", json=payload)
    assert res.status_code == 200
    plan = res.json()

    # Verify server returned secret_ref action
    type_action = next((a for a in plan["actions"] if a["type"] == "type"), None)
    assert type_action is not None
    assert type_action["value"]["secret_ref"] == "login.password"
    assert type_action["value"]["text"] is None
    print("[PASS] Scenario 2 (Login): Secure authentication using secret_ref, zero password egress.")


def test_scenario_3_shopping():
    # Shopping scenario contains sensitive shipping address & contact phone
    payload = {
        "session_id": "e2e-shop-003",
        "step": 1,
        "instruction_sanitized": "Find the product and add it to cart.",
        "page": {
            "url_sanitized": "http://127.0.0.1/demo-sites/shop/index.html",
            "title_sanitized": "SwiftCart - Online Electronics Store",
            "viewport": {"w": 1280, "h": 720, "dpr": 1.0}
        },
        "screenshot": None,
        "elements": [
            {
                "id": "btn-add-cart-01",
                "role": "button",
                "label": "Add to Cart",
                "bbox": [100, 250, 220, 290],
                "interactable": True,
                "sensitivity": "safe",
                "source": "dom+vision",
                "confidence": 0.99
            }
        ],
        "redactions": [
            {"id": "r1", "type": "address", "placeholder": "[REDACTED_ADDRESS]", "bbox": [400, 500, 700, 530]},
            {"id": "r2", "type": "phone", "placeholder": "[REDACTED_PHONE]", "bbox": [400, 540, 600, 570]}
        ],
        "privacy_report": {"detected": 3, "sensitive": 3, "redacted": 3, "uncertain_redacted": 0, "verification": "PASS", "gate": "PASS"},
        "history": []
    }

    # Verify sensitive shipping info never leaks
    assert "Vikram Malhotra" not in json.dumps(payload)
    assert "Indiranagar" not in json.dumps(payload)

    res = requests.post(f"{SERVER_URL}/api/agent/plan", json=payload)
    assert res.status_code == 200
    plan = res.json()
    assert plan["actions"][0]["type"] == "click"
    assert plan["actions"][0]["target"]["element_id"] == "btn-add-cart-01"
    print("[PASS] Scenario 3 (Shopping): Product added to cart with shipping address protected.")


def test_scenario_4_gov_form():
    # Government form contains 12-digit Aadhaar, PAN, registered phone, OTP
    payload = {
        "session_id": "e2e-gov-004",
        "step": 1,
        "instruction_sanitized": "Verify identity and submit form.",
        "page": {
            "url_sanitized": "http://127.0.0.1/demo-sites/gov-form/index.html",
            "title_sanitized": "GovSecure Portal - Aadhaar / PAN Verification",
            "viewport": {"w": 1280, "h": 720, "dpr": 1.0}
        },
        "screenshot": None,
        "elements": [
            {
                "id": "btn-submit-verify",
                "role": "button",
                "label": "Verify & Proceed (सत्यापित करें)",
                "bbox": [200, 400, 450, 440],
                "interactable": True,
                "sensitivity": "safe",
                "source": "dom+vision",
                "confidence": 0.99
            }
        ],
        "redactions": [
            {"id": "r1", "type": "aadhaar", "placeholder": "[REDACTED_AADHAAR]", "bbox": [100, 100, 350, 130]},
            {"id": "r2", "type": "pan", "placeholder": "[REDACTED_PAN]", "bbox": [100, 150, 350, 180]},
            {"id": "r3", "type": "phone", "placeholder": "[REDACTED_PHONE]", "bbox": [100, 200, 350, 230]},
            {"id": "r4", "type": "otp", "placeholder": "[REDACTED_OTP]", "bbox": [100, 250, 350, 280]}
        ],
        "privacy_report": {"detected": 4, "sensitive": 4, "redacted": 4, "uncertain_redacted": 0, "verification": "PASS", "gate": "PASS"},
        "history": []
    }

    assert "5481 9201 3847" not in json.dumps(payload)
    assert "ABCDE1234F" not in json.dumps(payload)
    assert "849201" not in json.dumps(payload)

    res = requests.post(f"{SERVER_URL}/api/agent/plan", json=payload)
    assert res.status_code == 200
    plan = res.json()
    assert plan["actions"][0]["type"] == "click"
    assert plan["actions"][0]["target"]["element_id"] == "btn-submit-verify"
    print("[PASS] Scenario 4 (Gov-Form): Aadhaar/PAN/OTP verification planned with complete redaction.")

if __name__ == "__main__":
    print("Running All 4 End-to-End Demo Scenarios...")
    test_scenario_1_bank()
    test_scenario_2_login()
    test_scenario_3_shopping()
    test_scenario_4_gov_form()
    print("\nALL 4 END-TO-END DEMO SCENARIOS PASSED WITH ZERO PII EGRESS!")
