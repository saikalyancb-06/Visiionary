"""
E2E Simulation for User's Exact Failed Task:
"find me the best selling cricket bat in flipkart"
"""
import requests
import json
from server.app.schemas.schemas import VerificationPayload
from server.app.verifier import verify_task_completion

SERVER_PLAN_URL = "http://127.0.0.1:8080/api/agent/plan"
TASK = "find me the best selling cricket bat in flipkart"

def test_homepage_search_intent_not_ad_clicking():
    print("\n--- TEST 1: Homepage Search Input Selection (MUST TYPE, NEVER CLICK AD) ---")
    homepage_elements = [
        {
            "id": "search-input-box",
            "role": "input",
            "label": "Search for Products, Brands and More",
            "bbox": [200, 20, 600, 60],
            "interactable": True,
            "sensitivity": "safe",
            "source": "dom",
            "confidence": 1.0
        },
        {
            "id": "search-submit-btn",
            "role": "button",
            "label": "Search",
            "bbox": [610, 20, 660, 60],
            "interactable": True,
            "sensitivity": "safe",
            "source": "dom",
            "confidence": 1.0
        },
        {
            "id": "ad-beardo-perfume",
            "role": "a",
            "label": "Beardo Godfather Revenge Perfume 100ml",
            "href": "https://www.flipkart.com/beardo-godfather-revenge-perfume/p/itm9ffc4bf3f?pid=PER123&ctx=ey...",
            "bbox": [100, 200, 300, 400],
            "interactable": True,
            "sensitivity": "safe",
            "source": "dom",
            "confidence": 1.0
        },
        {
            "id": "footer-gift-cards",
            "role": "a",
            "label": "Gift Cards",
            "href": "https://www.flipkart.com/the-gift-card-store?otracker=footer_navlinks",
            "bbox": [100, 800, 200, 830],
            "interactable": True,
            "sensitivity": "safe",
            "source": "dom",
            "confidence": 1.0
        }
    ]

    req_payload = {
        "session_id": "test-cricket-01",
        "step": 1,
        "instruction_sanitized": TASK,
        "page": {
            "url_sanitized": "https://www.flipkart.com",
            "title_sanitized": "Online Shopping Site for Mobiles, Electronics, Furniture, Grocery, Lifestyle, Books & More. Best Offers!",
            "viewport": {"w": 1280, "h": 720, "dpr": 1.0}
        },
        "elements": homepage_elements,
        "redactions": [],
        "privacy_report": {"detected": 0, "sensitive": 0, "redacted": 0, "uncertain_redacted": 0, "verification": "PASS", "gate": "PASS"},
        "history": []
    }

    res = requests.post(SERVER_PLAN_URL, json=req_payload)
    assert res.status_code == 200, f"Plan request failed: {res.text}"
    plan = res.json()
    first_act = plan["actions"][0]
    print("Step 1 Action:", first_act["type"], "target:", first_act.get("target"), "value:", first_act.get("value"))
    print("Reason:", plan["reasoning_summary"][:100])

    assert first_act["type"] in ("type", "search"), f"Expected type/search, got {first_act['type']}"
    if first_act.get("value") and first_act["value"].get("text"):
        assert "cricket bat" in first_act["value"]["text"].lower()
    assert first_act.get("target", {}).get("element_id") != "ad-beardo-perfume", "AGENT CLICKED BEARDO AD ON HOMEPAGE!"
    assert first_act.get("target", {}).get("element_id") != "footer-gift-cards", "AGENT CLICKED GIFT CARDS LINK ON HOMEPAGE!"
    print("[PASS] On Flipkart Homepage, agent correctly types 'cricket bat' into search box!")

def test_search_results_best_seller_candidate_selection():
    print("\n--- TEST 2: Search Results Candidate Selection with Best Seller Criterion ---")
    results_elements = [
        {
            "id": "cand_sg_bat",
            "role": "a",
            "label": "SG Scorer Classic Kashmir Willow Cricket Bat ₹1,299 (4.4 stars)",
            "href": "https://www.flipkart.com/sg-scorer-cricket-bat/p/itm001",
            "bbox": [100, 200, 300, 450],
            "interactable": True,
            "sensitivity": "safe",
            "source": "dom",
            "confidence": 1.0
        },
        {
            "id": "badge_best_seller",
            "role": "div",
            "label": "Best Seller",
            "bbox": [100, 180, 200, 200],
            "interactable": False,
            "sensitivity": "safe",
            "source": "dom",
            "confidence": 1.0
        },
        {
            "id": "cand_ss_bat",
            "role": "a",
            "label": "SS Master 500 English Willow Cricket Bat ₹3,499 (4.1 stars)",
            "href": "https://www.flipkart.com/ss-master-cricket-bat/p/itm002",
            "bbox": [320, 200, 520, 450],
            "interactable": True,
            "sensitivity": "safe",
            "source": "dom",
            "confidence": 1.0
        }
    ]

    req_payload = {
        "session_id": "test-cricket-02",
        "step": 2,
        "instruction_sanitized": TASK,
        "page": {
            "url_sanitized": "https://www.flipkart.com/search?q=cricket+bat",
            "title_sanitized": "Cricket Bat - Buy Cricket Bat Online at Best Prices In India | Flipkart.com",
            "viewport": {"w": 1280, "h": 720, "dpr": 1.0}
        },
        "elements": results_elements,
        "redactions": [],
        "privacy_report": {"detected": 0, "sensitive": 0, "redacted": 0, "uncertain_redacted": 0, "verification": "PASS", "gate": "PASS"},
        "history": [{"action": "type", "target": "search-input-box", "text": "cricket bat"}]
    }

    res = requests.post(SERVER_PLAN_URL, json=req_payload)
    assert res.status_code == 200
    plan = res.json()
    first_act = plan["actions"][0]
    print("Step 2 Action:", first_act["type"], "target:", first_act.get("target"), "url:", first_act.get("url"))
    print("Reason:", plan["reasoning_summary"][:100])

    assert first_act["type"] in ("open_link", "click", "scroll"), f"Expected click/open_link/scroll, got {first_act['type']}"
    if first_act["type"] in ("open_link", "click"):
        target_id = first_act.get("target", {}).get("element_id") if first_act.get("target") else None
        url = first_act.get("url", "")
        assert target_id == "cand_sg_bat" or "sg-scorer" in url, f"Expected Best Seller SG Bat, got {target_id} / {url}"
        print("[PASS] On Search Results, agent selected the Best Seller SG Cricket Bat!")
    else:
        print("[PASS] On Search Results, agent intelligently decided to scroll to inspect popularity / sorting options!")

def test_verifier_goal_achieved_on_product_page():
    print("\n--- TEST 3: Verifier Confirms Goal on Opened Product Page ---")
    payload = VerificationPayload(
        task=TASK,
        current_url="https://www.flipkart.com/sg-scorer-cricket-bat/p/itm001",
        page_title="SG Scorer Classic Kashmir Willow Cricket Bat - Buy Online at Flipkart.com",
        action_history=[
            {"action": "type", "target": "search-input-box", "text": "cricket bat"},
            {"action": "click", "target": "cand_sg_bat"}
        ],
        screen_summary={"main_headings": ["SG Scorer Classic Kashmir Willow Cricket Bat", "Special price ₹1,299", "Specifications"]},
        downloads=[]
    )
    v_res = verify_task_completion(payload)
    print("Verifier outcome:", v_res.goal_status, "| reason:", v_res.reason)
    assert v_res.achieved
    assert v_res.goal_status == "GOAL_ACHIEVED"
    print("[PASS] Verifier correctly confirmed GOAL_ACHIEVED on target product page!")

if __name__ == "__main__":
    test_homepage_search_intent_not_ad_clicking()
    test_search_results_best_seller_candidate_selection()
    test_verifier_goal_achieved_on_product_page()
    print("\n========================================================")
    print("CRICKET BAT FLIPKART E2E TESTS PASSED 100%!")
    print("========================================================")
