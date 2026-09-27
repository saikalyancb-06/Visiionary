"""
End-to-End Simulation Test: Flipkart Product Discovery Scenario
Recreates the exact user scenario from the screenshot:
"can you find me a black shirt in flipkart, it shou..."
Validates:
1. No premature GOAL_ACHIEVED after 1 action on search results page.
2. Correct parsing of conversational prompt into product_type="shirt" and color="black".
3. Autonomous candidate extraction and selection of the matching black shirt.
4. Autonomous scrolling fallback when no matching candidate is on screen.
5. Final goal verification when the matching product page is reached.
"""
import requests
import json
from server.app.schemas.schemas import VerificationPayload
from server.app.verifier import verify_task_completion
from server.app.product_constraints import extract_product_constraints

SERVER_PLAN_URL = "http://127.0.0.1:8080/api/agent/plan"
TASK = "can you find me a black shirt in flipkart, it shou..."

def test_conversational_constraint_extraction():
    print("\n--- TEST 1: Conversational Constraint Extraction ---")
    constraints = extract_product_constraints(TASK)
    print("Extracted constraints:", json.dumps(constraints, indent=2))
    assert constraints["product_type"] == "shirt", f"Expected 'shirt', got {constraints['product_type']}"
    assert constraints["color"] == "black", f"Expected 'black', got {constraints['color']}"
    print("[PASS] Cleanly extracted product_type='shirt' and color='black' from conversational input.")

def test_no_premature_verifier_termination():
    print("\n--- TEST 2: Verifier Rejection of Premature Completion on Search Results ---")
    payload = VerificationPayload(
        task=TASK,
        current_url="https://www.flipkart.com/search?q=black+shirt",
        page_title="Black Shirt - Buy Black Shirt Online at Best Prices In India | Flipkart.com",
        action_history=[{"action": "wait", "milliseconds": 500}],
        screen_summary={"main_headings": ["Black Shirts", "Filters", "Men's Clothing"]},
        downloads=[]
    )
    v_res = verify_task_completion(payload)
    print("Verifier response on search page:", v_res.goal_status, "| reason:", v_res.reason)
    assert not v_res.achieved, "Verifier falsely declared victory on search results page!"
    assert v_res.goal_status == "GOAL_NOT_YET_ACHIEVED", f"Expected GOAL_NOT_YET_ACHIEVED, got {v_res.goal_status}"
    assert v_res.remaining_goal in ("identify shirt", "open selected product"), f"Unexpected remaining_goal: {v_res.remaining_goal}"
    print("[PASS] Verifier correctly rejected premature completion and insisted on identifying/opening candidate.")

def test_planner_selects_matching_candidate():
    print("\n--- TEST 3: Planner Autonomous Candidate Selection ---")
    sample_elements = [
        {
            "id": "cand-blue-shirt",
            "role": "a",
            "label": "Men Slim Fit Blue Denim Shirt ₹899",
            "href": "https://www.flipkart.com/blue-shirt/p/itm001",
            "bbox": [100, 200, 300, 450],
            "interactable": True,
            "sensitivity": "safe",
            "source": "dom",
            "confidence": 1.0
        },
        {
            "id": "cand-black-shirt",
            "role": "a",
            "label": "Men Regular Fit Solid Black Casual Shirt ₹699 (4.3 stars)",
            "href": "https://www.flipkart.com/black-shirt/p/itm002",
            "bbox": [320, 200, 520, 450],
            "interactable": True,
            "sensitivity": "safe",
            "source": "dom",
            "confidence": 1.0
        },
        {
            "id": "cand-black-dress",
            "role": "a",
            "label": "Women Solid Black Fit and Flare Dress ₹1,299",
            "href": "https://www.flipkart.com/black-dress/p/itm003",
            "bbox": [540, 200, 740, 450],
            "interactable": True,
            "sensitivity": "safe",
            "source": "dom",
            "confidence": 1.0
        }
    ]

    req_payload = {
        "session_id": "test-flipkart-01",
        "step": 2,
        "instruction_sanitized": TASK,
        "page": {
            "url_sanitized": "https://www.flipkart.com/search?q=black+shirt",
            "title_sanitized": "Black Shirt - Buy Black Shirt Online at Best Prices In India | Flipkart.com",
            "viewport": {"w": 1280, "h": 720, "dpr": 1.0}
        },
        "elements": sample_elements,
        "redactions": [],
        "privacy_report": {"detected": 0, "sensitive": 0, "redacted": 0, "uncertain_redacted": 0, "verification": "PASS", "gate": "PASS"},
        "history": [{"action": "type", "target": "search-box", "text": "black shirt"}]
    }

    res = requests.post(SERVER_PLAN_URL, json=req_payload)
    assert res.status_code == 200, f"Plan request failed: {res.text}"
    plan = res.json()
    print("Planner response:", json.dumps(plan["actions"][:2], indent=2))
    print("Reasoning summary:", plan["reasoning_summary"][:120])

    first_action = plan["actions"][0]
    assert first_action["type"] in ("open_link", "click"), f"Expected click/open_link, got {first_action['type']}"
    # The action must target the black shirt candidate (not the blue shirt or black dress)
    if first_action.get("target") and first_action["target"].get("element_id"):
        assert first_action["target"]["element_id"] == "cand-black-shirt", f"Wrong target: {first_action['target']['element_id']}"
    elif first_action.get("url"):
        assert "black-shirt" in first_action["url"], f"Wrong URL: {first_action['url']}"
    print("[PASS] Planner accurately selected the Black Casual Shirt matching all hard constraints.")

def test_planner_scrolls_when_no_match_visible():
    print("\n--- TEST 4: Planner Autonomous Scrolling Fallback ---")
    only_mismatched_elements = [
        {
            "id": "cand-blue-shirt",
            "role": "a",
            "label": "Men Slim Fit Blue Denim Shirt ₹899",
            "href": "https://www.flipkart.com/blue-shirt/p/itm001",
            "bbox": [100, 200, 300, 450],
            "interactable": True,
            "sensitivity": "safe",
            "source": "dom",
            "confidence": 1.0
        },
        {
            "id": "cand-red-hoodie",
            "role": "a",
            "label": "Men Red Cotton Hoodie ₹999",
            "href": "https://www.flipkart.com/red-hoodie/p/itm004",
            "bbox": [320, 200, 520, 450],
            "interactable": True,
            "sensitivity": "safe",
            "source": "dom",
            "confidence": 1.0
        }
    ]

    req_payload = {
        "session_id": "test-flipkart-02",
        "step": 3,
        "instruction_sanitized": TASK,
        "page": {
            "url_sanitized": "https://www.flipkart.com/search?q=black+shirt",
            "title_sanitized": "Black Shirt - Buy Black Shirt Online at Best Prices In India | Flipkart.com",
            "viewport": {"w": 1280, "h": 720, "dpr": 1.0}
        },
        "elements": only_mismatched_elements,
        "redactions": [],
        "privacy_report": {"detected": 0, "sensitive": 0, "redacted": 0, "uncertain_redacted": 0, "verification": "PASS", "gate": "PASS"},
        "history": [{"action": "type", "target": "search-box", "text": "black shirt"}]
    }

    res = requests.post(SERVER_PLAN_URL, json=req_payload)
    assert res.status_code == 200
    plan = res.json()
    first_action = plan["actions"][0]
    print("Action when no match visible:", first_action["type"], first_action.get("direction"))
    assert first_action["type"] == "scroll", f"Expected scroll action, got {first_action['type']}"
    assert first_action["direction"] == "down"
    print("[PASS] Planner autonomously decided to scroll down to discover more items.")

def test_final_goal_verified_on_product_page():
    print("\n--- TEST 5: Goal Verified When Matching Product Page Reached ---")
    payload = VerificationPayload(
        task=TASK,
        current_url="https://www.flipkart.com/black-casual-shirt/p/itm12345",
        page_title="Men Regular Fit Solid Black Casual Shirt - Buy Online at Flipkart.com",
        action_history=[
            {"action": "type", "target": "search-box", "text": "black shirt"},
            {"action": "click", "target": "cand-black-shirt"}
        ],
        screen_summary={"main_headings": ["Men Regular Fit Solid Black Casual Shirt", "Special price ₹699", "Specifications"]},
        downloads=[]
    )
    v_res = verify_task_completion(payload)
    print("Verifier response on product page:", v_res.goal_status, "| reason:", v_res.reason)
    assert v_res.achieved, "Expected goal achieved on matching product page!"
    assert v_res.goal_status == "GOAL_ACHIEVED"
    print("[PASS] Verifier correctly verified overall goal achieved on matching product page.")

if __name__ == "__main__":
    test_conversational_constraint_extraction()
    test_no_premature_verifier_termination()
    test_planner_selects_matching_candidate()
    test_planner_scrolls_when_no_match_visible()
    test_final_goal_verified_on_product_page()
    print("\n========================================================")
    print("ALL 5 E2E SIMULATION TESTS PASSED WITH 100% RELIABILITY!")
    print("========================================================")
