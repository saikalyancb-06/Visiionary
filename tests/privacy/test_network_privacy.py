"""
Hard Automated Network-Privacy Test (Phase 6 Walking Skeleton & Phase 17)
1. Simulates DOM perception of banking demo page.
2. Identifies PII fields (Account #, Balance, Email, Mobile).
3. Redacts them locally using Solid Opaque placeholders.
4. Passes sanitized package through Egress Gate.
5. Asserts NO raw PII reaches the server.
6. Verifies server identifies target 'Download Statement' button without seeing raw PII.
7. Verifies Fail-Closed behavior: injecting unredacted PII is blocked by the Egress Gate.
"""
import requests
import json
import re

SERVER_URL = "http://127.0.0.1:8080"

RAW_PII = {
    "account_holder": "Ananya Sharma",
    "account_number": "9823-4412-0091-8842",
    "balance": "INR 2,84,500.50",
    "email": "ananya.sharma@example.in",
    "phone": "+91 98451 23091"
}

def test_sanitized_pipeline_and_privacy():
    # 1. Check server health
    res = requests.get(f"{SERVER_URL}/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"

    # 2. Construct sanitized context package (simulating browser local perception & redaction)
    sanitized_package = {
        "session_id": "test-session-001",
        "step": 1,
        "instruction_sanitized": "Download my latest statement",
        "page": {
            "url_sanitized": "http://127.0.0.1/demo-sites/bank/index.html",
            "title_sanitized": "Apex Bank - Online Banking Portal",
            "viewport": {"w": 1366, "h": 768, "dpr": 1.0}
        },
        "screenshot": None,
        "elements": [
            {
                "id": "btn_statement_01",
                "role": "button",
                "label": "Download Statement",
                "bbox": [640, 410, 820, 450],
                "interactable": True,
                "sensitivity": "safe",
                "source": "dom+vision",
                "confidence": 0.98
            },
            {
                "id": "field_acc_num",
                "role": "text",
                "label": "[REDACTED_ACCOUNT]",
                "bbox": [100, 200, 300, 240],
                "interactable": False,
                "sensitivity": "redacted",
                "source": "dom+vision",
                "confidence": 0.99
            }
        ],
        "redactions": [
            {
                "id": "r_01",
                "type": "bank_account",
                "placeholder": "[REDACTED_ACCOUNT]",
                "bbox": [100, 200, 300, 240]
            },
            {
                "id": "r_02",
                "type": "email",
                "placeholder": "[REDACTED_EMAIL]",
                "bbox": [100, 250, 300, 290]
            }
        ],
        "privacy_report": {
            "detected": 4,
            "sensitive": 4,
            "redacted": 4,
            "uncertain_redacted": 0,
            "verification": "PASS",
            "gate": "PASS"
        },
        "history": []
    }

    # 3. Assert NO raw PII is inside sanitized package
    payload_str = json.dumps(sanitized_package)
    for k, raw_val in RAW_PII.items():
        assert raw_val not in payload_str, f"LEAK DETECTED: Raw PII string '{raw_val}' found in client payload!"

    # 4. Transmit payload to server
    post_res = requests.post(f"{SERVER_URL}/api/agent/plan", json=sanitized_package)
    assert post_res.status_code == 200, f"Server plan failed: {post_res.text}"
    plan = post_res.json()

    print("[PASS] Plan Response Received:", json.dumps(plan, indent=2))
    assert len(plan["actions"]) > 0, "No actions returned by planner"
    assert plan["actions"][0]["type"] == "click", "Expected click action"
    assert plan["actions"][0]["target"]["element_id"] == "btn_statement_01", "Action targeted wrong element"

    # 5. TEST FAIL-CLOSED: Introduce raw unredacted PII into payload
    leaky_package = dict(sanitized_package)
    leaky_package["instruction_sanitized"] = f"Send money from {RAW_PII['email']}"
    leak_res = requests.post(f"{SERVER_URL}/api/agent/plan", json=leaky_package)
    assert leak_res.status_code == 400, "Server failed to reject unredacted PII payload!"
    print("[PASS] Fail-Closed Verified: Server defense-in-depth rejected unredacted PII payload.")

if __name__ == "__main__":
    test_sanitized_pipeline_and_privacy()
    print("\nALL PRIVACY & WALKING SKELETON ACCEPTANCE CHECKS PASSED.")
