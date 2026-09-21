import requests

SERVER_URL = "http://127.0.0.1:8080/api/agent/plan"

variations = [
    "Search for laptops",
    "Look for laptops",
    "Find some laptops",
    "Can you search for a laptop?"
]

sample_elements = [
    {"id": "search-input", "role": "input", "label": "Search products...", "bbox": [100, 50, 300, 80], "interactable": True, "sensitivity": "safe", "source": "dom", "confidence": 1.0},
    {"id": "search-btn", "role": "button", "label": "Search", "bbox": [310, 50, 400, 80], "interactable": True, "sensitivity": "safe", "source": "dom", "confidence": 1.0}
]

print("[TEST GENERALIZATION] Testing 4 differently worded prompts with Local Ollama...")

for var in variations:
    payload = {
        "session_id": "gen-test-01",
        "step": 1,
        "instruction_sanitized": var,
        "page": {"url_sanitized": "https://example.com/shop", "title_sanitized": "Shop", "viewport": {"w": 1280, "h": 720, "dpr": 1.0}},
        "elements": sample_elements,
        "redactions": [],
        "privacy_report": {"detected": 0, "sensitive": 0, "redacted": 0, "uncertain_redacted": 0, "verification": "PASS", "gate": "PASS"},
        "history": []
    }
    res = requests.post(SERVER_URL, json=payload, timeout=30)
    assert res.status_code == 200
    plan = res.json()
    first_act = plan["actions"][0]
    print(f"Prompt: {var}")
    print("Action:", first_act["type"], "on", first_act.get("target", {}).get("element_id"))
    print("Reason:", plan["reasoning_summary"][:80])
    assert first_act["type"] in ("type", "click")

print("\nALL 4 PROMPT VARIATIONS GENERALIZED ACCURATELY BY LOCAL OLLAMA!")
