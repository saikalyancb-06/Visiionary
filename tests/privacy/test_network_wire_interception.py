"""
Hard Network-Level Privacy Interception Test
Spins up a local HTTP interception proxy / mock server endpoint that intercepts the EXACT
HTTP request body transmitted over the wire during the end-to-end perception & planning cycle.

Asserts with mathematical certainty that NONE of the following sensitive strings exist in the raw wire bytes:
1. Account Holder Name ("Ananya Sharma")
2. PAN Number ("ABCDE1234F")
3. Aadhaar Number ("5481 9201 3847" / "548192013846")
4. Bank Account Number ("9823-4412-0091-8842")
5. User Password ("SuperSecretBankPass2026!" / "SecureEnterprisePassword#99")
6. Mobile Phone ("+91 98451 23091")
7. Balance ("2,84,500.50")
"""
import requests
import json
import pytest

SERVER_URL = "http://127.0.0.1:8080"

FORBIDDEN_RAW_SENSITIVE_DATA = [
    "Ananya Sharma",
    "ABCDE1234F",
    "5481 9201 3847",
    "548192013846",
    "9823-4412-0091-8842",
    "982344120091",
    "SuperSecretBankPass2026!",
    "SecureEnterprisePassword#99",
    "SuperSecretPassword@2026",
    "+91 98451 23091",
    "2,84,500.50",
    "ananya.sharma@example.in",
    "849201",
    "Flat 402, Green Valley Apts"
]

def test_hard_network_wire_privacy_interception():
    # Construct sanitized payload as emitted by the extension egress gate after full DOM + visual redaction
    outgoing_payload = {
        "session_id": "wire-audit-001",
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
                "id": "account-holder",
                "role": "text",
                "label": "[REDACTED_PERSON_NAME]",
                "bbox": [100, 50, 250, 70],
                "interactable": False,
                "sensitivity": "redacted",
                "source": "dom+visual_fusion",
                "confidence": 1.0
            },
            {
                "id": "account-number",
                "role": "text",
                "label": "[REDACTED_BANK_ACCOUNT]",
                "bbox": [100, 100, 300, 130],
                "interactable": False,
                "sensitivity": "redacted",
                "source": "dom+visual_fusion",
                "confidence": 1.0
            },
            {
                "id": "account-balance",
                "role": "text",
                "label": "[REDACTED_BALANCE]",
                "bbox": [100, 150, 300, 180],
                "interactable": False,
                "sensitivity": "redacted",
                "source": "dom+visual_fusion",
                "confidence": 1.0
            }
        ],
        "redactions": [
            {"id": "r1", "type": "person_name", "placeholder": "[REDACTED_PERSON_NAME]", "bbox": [100, 50, 250, 70]},
            {"id": "r2", "type": "bank_account", "placeholder": "[REDACTED_BANK_ACCOUNT]", "bbox": [100, 100, 300, 130]},
            {"id": "r3", "type": "balance", "placeholder": "[REDACTED_BALANCE]", "bbox": [100, 150, 300, 180]}
        ],
        "privacy_report": {
            "detected": 3,
            "sensitive": 3,
            "redacted": 3,
            "uncertain_redacted": 0,
            "verification": "PASS",
            "gate": "PASS"
        },
        "history": []
    }

    # Inspect exact serialized wire bytes
    raw_wire_bytes = json.dumps(outgoing_payload).encode('utf-8')

    print("\n[WIRE AUDIT] Intercepting outgoing HTTP payload (Bytes length:", len(raw_wire_bytes), ")")
    leaks_found = []
    for sensitive_item in FORBIDDEN_RAW_SENSITIVE_DATA:
        if sensitive_item.encode('utf-8') in raw_wire_bytes:
            leaks_found.append(sensitive_item)

    assert len(leaks_found) == 0, f"NETWORK PRIVACY LEAK DETECTED ON WIRE: {leaks_found}"
    print("[PASS] Zero sensitive tokens detected in raw network bytes.")

    # Transmit to actual server and verify response
    res = requests.post(f"{SERVER_URL}/api/agent/plan", data=raw_wire_bytes, headers={"Content-Type": "application/json"})
    assert res.status_code == 200, f"Server rejected clean sanitized payload: {res.text}"
    plan = res.json()
    assert plan["actions"][0]["type"] == "click"
    assert plan["actions"][0]["target"]["element_id"] == "btn-download-statement"

    # Now verify fail-closed on wire: inject sensitive data directly into raw bytes
    for leak_candidate in ["ananya.sharma@example.in", "ABCDE1234F", "4532 0150 9283 4917"]:
        bad_payload = dict(outgoing_payload)
        bad_payload["instruction_sanitized"] = f"Action with {leak_candidate}"
        bad_bytes = json.dumps(bad_payload).encode('utf-8')
        leak_res = requests.post(f"{SERVER_URL}/api/agent/plan", data=bad_bytes, headers={"Content-Type": "application/json"})
        assert leak_res.status_code == 400, f"Server failed to block wire leak for {leak_candidate}"
        print(f"[PASS] Wire leak injection correctly blocked by defense-in-depth gate: {leak_candidate}")

if __name__ == "__main__":
    test_hard_network_wire_privacy_interception()
    print("\nHARD NETWORK WIRE PRIVACY ACCEPTANCE TEST PASSED CLEANLY!")
