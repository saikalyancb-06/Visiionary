"""
Comprehensive General Browser-Agent Architecture Test Suite (Scenarios A through P)

Validates the 23 Core Principles:
A. Discovery result -> intermediate destination -> target entity
B. Multiple entities where only one satisfies hard constraints
C. Unknown attribute requiring further inspection (3-valued logic: SATISFIED, NOT_SATISFIED, UNKNOWN)
D. Target mismatch after navigation (preserves TargetIdentity across transitions)
E. Stale element requiring re-grounding
F. Action executes but postcondition fails (ACTION_EXECUTED != GOAL_ACHIEVED)
G. Successful action with verified postcondition
H. Missing prerequisite requiring ASK_USER
I. Repeated failed action requiring recovery
J. Search result that is not the final target
K. Entity attributes distributed across multiple DOM elements
L. Multiple entity types on the same page
M. No valid target exists
N. Criterion cannot yet be established but further exploration is possible
O. Task can be completed without search
P. Task requires multiple intermediate pages
"""

import sys
import os
sys.path.insert(0, r"d:\webman")

from server.app.schemas.schemas import (
    SanitizedContextPackage, PageContext, ElementMetadata, BrowserAction, ActionTarget, VerificationPayload
)
from server.app.task_model import (
    parse_general_task, GeneralTaskModel, INTENT_FIND_INFO, INTENT_DOWNLOAD_ARTIFACT,
    INTENT_TRANSACTION, INTENT_FILL_FORM
)
from server.app.page_model import (
    classify_page_semantics, PAGE_SEARCH_DISCOVERY, PAGE_LISTING_CATALOG,
    PAGE_DETAIL_ENTITY, PAGE_FORM_INTERACTION, PAGE_TRANSACTION_CART, PAGE_CONFIRMATION_RESULT
)
from server.app.entity_model import (
    extract_semantic_entities, SemanticEntity, ENTITY_PRODUCT, ENTITY_DOCUMENT,
    ENTITY_DESTINATION
)
from server.app.entity_evaluator import (
    evaluate_candidate_constraints, evaluate_selection_criterion,
    verify_target_identity_match, STATE_SATISFIED, STATE_NOT_SATISFIED, STATE_UNKNOWN
)
from server.app.verifier import verify_task_completion
from server.app.validator import validate_action, get_action_signature
from server.app.planner import decide_next_action

results = []

def record(name: str, condition: bool):
    status = "PASS" if condition else "FAIL"
    results.append((name, condition))
    print(f"[{status}] {name}")

print("\n" + "="*70)
print("RUNNING COMPREHENSIVE ARCHITECTURE SCENARIOS (A - P)")
print("="*70 + "\n")

# SCENARIO A: Discovery result -> intermediate destination -> target entity
task_a = parse_general_task("find the latest research paper on quantum computing and download it")
elems_a = [
    ElementMetadata(id="link_1", role="a", label="Quantum Computing Directory | Open Science", href="https://openscience.org/topics/quantum", interactable=True, bbox=[10, 10, 300, 30]),
    ElementMetadata(id="link_2", role="a", label="Quantum Computing Overview 2026.pdf", href="https://openscience.org/papers/qc2026.pdf", interactable=True, bbox=[10, 50, 300, 70])
]
entities_a = extract_semantic_entities(elems_a, "Search Results", "https://search.org/q=quantum")
dest_entities = [e for e in entities_a if e.is_destination_only]
direct_entities = [e for e in entities_a if not e.is_destination_only]
record("Scenario A: Classifies discovery result as intermediate destination vs direct target", len(dest_entities) >= 1 and len(direct_entities) >= 1)


# SCENARIO B: Multiple entities where only one satisfies hard constraints
task_b = parse_general_task("find black shirt for men")
entity_b1 = SemanticEntity(entity_id="e1", title="Red Dress for Women", visible_text="Red Dress for Women cotton", attributes={"color": "red", "gender": "women", "product_type": "dress"})
entity_b2 = SemanticEntity(entity_id="e2", title="Black Shirt for Men", visible_text="Black Shirt for Men cotton", attributes={"color": "black", "gender": "men", "product_type": "shirt"})
entity_b3 = SemanticEntity(entity_id="e3", title="Blue Shirt for Men", visible_text="Blue Shirt for Men", attributes={"color": "blue", "gender": "men", "product_type": "shirt"})

res_b1, _, _ = evaluate_candidate_constraints(entity_b1, task_b)
res_b2, _, _ = evaluate_candidate_constraints(entity_b2, task_b)
res_b3, _, _ = evaluate_candidate_constraints(entity_b3, task_b)
record("Scenario B: Multiple entities evaluated; only exact match satisfies hard constraints", res_b1 == STATE_NOT_SATISFIED and res_b2 == STATE_SATISFIED and res_b3 == STATE_NOT_SATISFIED)


# SCENARIO C: Unknown attribute requiring further inspection (3-valued logic: SATISFIED, NOT_SATISFIED, UNKNOWN)
task_c = parse_general_task("find black cotton shirt for men")
# Card shows 'Black Shirt for Men' but material is NOT visible on the summary card
entity_c = SemanticEntity(entity_id="ec", title="Black Shirt for Men", visible_text="Black Shirt for Men $29.99", attributes={"color": "black", "gender": "men", "product_type": "shirt"})
res_c, attr_c, reason_c = evaluate_candidate_constraints(entity_c, task_c)
record("Scenario C: Unobserved attribute yields UNKNOWN (never collapsed to FALSE)", res_c == STATE_UNKNOWN and attr_c.get("material") == STATE_UNKNOWN and "material" in reason_c)


# SCENARIO D: Target mismatch after navigation (preserves TargetIdentity across transitions)
selected_target_d = {"title": "Ergonomic Wireless Mouse", "candidate_id": "item_401", "color": "black"}
arrived_entity_d = SemanticEntity(entity_id="curr_page", title="Mechanical Gaming Keyboard", visible_text="Mechanical Gaming Keyboard RGB Backlit", attributes={"product_type": "keyboard"})
match_d, reason_d = verify_target_identity_match(selected_target_d, arrived_entity_d)
record("Scenario D: Target mismatch detected after navigation when opened entity differs", match_d is False and "TARGET_MISMATCH" in reason_d)


# SCENARIO E: Stale element requiring re-grounding
payload_e = SanitizedContextPackage(
    session_id="s_e", step=2, instruction_sanitized="click download button",
    page=PageContext(url_sanitized="https://portal.org", title_sanitized="Portal", viewport={"w": 1280, "h": 720}),
    privacy_report={"detected": 0, "sensitive": 0, "redacted": 0},
    elements=[ElementMetadata(id="btn_download_fresh", role="button", label="Download File", bbox=[10, 10, 100, 30])]
)
stale_action = BrowserAction(type="click", target=ActionTarget(element_id="btn_download_stale_99"))
is_val_e, _, reason_e = validate_action(stale_action, payload_e)
record("Scenario E: Stale/non-existent element rejected by action grounding layer", not is_val_e and "does not exist" in reason_e)


# SCENARIO F: Action executes but postcondition fails (ACTION_EXECUTED != GOAL_ACHIEVED)
verif_payload_f = VerificationPayload(
    task="find black shirt and add it to cart",
    current_url="https://store.org/item/102",
    page_title="Black Cotton Shirt",
    action_history=[{"action": "click", "target": "btn_add_cart"}], # Click executed!
    screen_summary={"main_headings": ["Black Cotton Shirt", "Product Specifications"]} # No cart banner
)
verif_f = verify_task_completion(verif_payload_f)
record("Scenario F: Action executed but missing postcondition does NOT achieve goal", verif_f.achieved is False and verif_f.product_state == "ACTION_EXECUTED")


# SCENARIO G: Successful action with verified postcondition
verif_payload_g = VerificationPayload(
    task="find black shirt and add it to cart",
    current_url="https://store.org/item/102",
    page_title="Black Cotton Shirt",
    action_history=[{"action": "click", "target": "btn_add_cart"}],
    screen_summary={"main_headings": ["Black Cotton Shirt", "Added to Cart ✓", "View Cart (1)"]}
)
verif_g = verify_task_completion(verif_payload_g)
record("Scenario G: Successful action with observable postcondition completes goal", verif_g.achieved is True and verif_g.goal_status == "GOAL_ACHIEVED")


# SCENARIO H: Missing prerequisite requiring ASK_USER
from server.app.product_constraints import detect_missing_prerequisites
task_h = parse_general_task("find black shirt and add it to cart") # No size specified!
elems_h = [
    ElementMetadata(id="sel_sz", role="select", label="Select Size", bbox=[10, 10, 100, 20]),
    ElementMetadata(id="opt_s", role="option", label="Small", bbox=[10, 30, 50, 20]),
    ElementMetadata(id="opt_m", role="option", label="Medium", bbox=[10, 50, 50, 20]),
    ElementMetadata(id="opt_l", role="option", label="Large", bbox=[10, 70, 50, 20])
]
prereq_h = detect_missing_prerequisites(elems_h, "ADD_TO_CART", task_h.to_dict())
record("Scenario H: Missing prerequisite with multiple options triggers ASK_USER prompt", prereq_h is not None and prereq_h.get("requires_prompt") is True)


# SCENARIO I: Repeated failed action requiring recovery
sig_i = get_action_signature(BrowserAction(type="click", target=ActionTarget(element_id="btn_retry")))
blocked_i = {sig_i}
payload_i = SanitizedContextPackage(
    session_id="s_i", step=3, instruction_sanitized="click button",
    page=PageContext(url_sanitized="https://site.org", title_sanitized="Site", viewport={"w": 1280, "h": 720}),
    privacy_report={"detected": 0, "sensitive": 0, "redacted": 0},
    elements=[ElementMetadata(id="btn_retry", role="button", label="Retry", bbox=[10, 10, 50, 20])]
)
is_val_i, _, reason_i = validate_action(BrowserAction(type="click", target=ActionTarget(element_id="btn_retry")), payload_i, blocked_signatures=blocked_i)
record("Scenario I: Repeated action without state change blocked by signature shield", is_val_i is False and "blocked by Loop Shield" in reason_i)


# SCENARIO J: Search result that is not the final target
task_j = parse_general_task("go to university portal and download physics syllabus")
elems_j = [
    ElementMetadata(id="res_1", role="a", label="Physics Department Homepage | University Portal", href="https://uni.edu/dept/physics", bbox=[10, 10, 300, 30]),
    ElementMetadata(id="res_2", role="a", label="Unrelated Chemistry Research", href="https://uni.edu/dept/chem", bbox=[10, 50, 300, 30])
]
sem_j = classify_page_semantics(elems_j, "Search Results", "https://search.engine.com/q=physics+syllabus")
record("Scenario J: Search results page classified as SEARCH_DISCOVERY rather than target state", sem_j.semantic_state == PAGE_SEARCH_DISCOVERY)


# SCENARIO K: Entity attributes distributed across multiple DOM elements
# e.g., Title in h2, Price in span, Badge in div, Link in a
elems_k = [
    ElementMetadata(id="title_k", role="h2", label="Pro Wireless Headset", bbox=[20, 20, 220, 50]),
    ElementMetadata(id="price_k", role="span", label="$149.99", bbox=[20, 55, 100, 75]),
    ElementMetadata(id="badge_k", role="div", label="#1 Best Seller in Audio", bbox=[20, 80, 180, 100]),
    ElementMetadata(id="link_k", role="a", label="View Headset Details", href="https://store.org/p/headset-pro", bbox=[20, 105, 200, 130])
]
entities_k = extract_semantic_entities(elems_k, "Store Catalog", "https://store.org/catalog")
# Should synthesize into 1 aggregated entity with price, badge, and href
card_k = next((e for e in entities_k if "Headset" in e.title or "Headset" in e.visible_text), None)
record("Scenario K: Entity attributes across multiple DOM nodes aggregated into 1 entity", card_k is not None and card_k.attributes.get("price") == "$149.99" and len(card_k.badges) > 0 and card_k.href == "https://store.org/p/headset-pro")


# SCENARIO L: Multiple entity types on the same page (e.g. document link, product card, and form control)
elems_l = [
    ElementMetadata(id="doc_1", role="a", label="User Manual Specification.pdf", href="https://store.org/manual.pdf", bbox=[10, 10, 200, 30]),
    ElementMetadata(id="prod_1", role="a", label="Deluxe Wireless Mouse", href="https://store.org/p/mouse-deluxe", bbox=[10, 50, 200, 80]),
    ElementMetadata(id="inp_email", role="input", label="Newsletter signup email", bbox=[10, 100, 200, 120])
]
entities_l = extract_semantic_entities(elems_l, "Mixed Resource Page", "https://store.org/resources")
types_l = set(e.semantic_type for e in entities_l)
record("Scenario L: Multiple entity types coexisting on page categorized distinctly", ENTITY_DOCUMENT in types_l and ENTITY_PRODUCT in types_l)


# SCENARIO M: No valid target exists
task_m = parse_general_task("find blue silk shirt for men")
elems_m = [
    ElementMetadata(id="p1", role="a", label="Red Cotton Shirt for Women", href="https://store.org/p/1", bbox=[10, 10, 200, 30]),
    ElementMetadata(id="p2", role="a", label="Green Denim Jacket", href="https://store.org/p/2", bbox=[10, 50, 200, 80])
]
entities_m = extract_semantic_entities(elems_m, "Catalog", "https://store.org/catalog")
valid_m = [e for e in entities_m if evaluate_candidate_constraints(e, task_m)[0] == STATE_SATISFIED]
record("Scenario M: Invariant upheld when zero observed entities satisfy hard constraints", len(valid_m) == 0)


# SCENARIO N: Criterion cannot yet be established but further exploration is possible
task_n = parse_general_task("find the best-selling black shirt for men")
entity_n = SemanticEntity(entity_id="en", title="Black Shirt for Men", visible_text="Black Shirt for Men $19.99", attributes={"color": "black", "gender": "men", "product_type": "shirt"}, badges=[])
crit_verified_n, reason_n = evaluate_selection_criterion(entity_n, task_n)
record("Scenario N: Comparative criterion without empirical badge flagged CRITERION_UNVERIFIED", crit_verified_n is False and "NO observable evidence" in reason_n)


# SCENARIO O: Task can be completed without search
# e.g., Directly clicking on an accessible portal link or table item already present on screen
task_o = parse_general_task("click on problem statement 171")
elems_o = [
    ElementMetadata(id="row_170", role="td", label="Problem Statement 170", bbox=[10, 10, 200, 30]),
    ElementMetadata(id="row_171", role="td", label="Problem Statement 171: Smart Healthcare", bbox=[10, 40, 300, 60], interactable=True)
]
payload_o = SanitizedContextPackage(
    session_id="s_o", step=1, instruction_sanitized=task_o.raw_task,
    page=PageContext(url_sanitized="https://portal.gov/statements", title_sanitized="Statements Grid", viewport={"w": 1280, "h": 720}),
    privacy_report={"detected": 0, "sensitive": 0, "redacted": 0},
    elements=elems_o
)
actions_o, reason_o = decide_next_action(payload_o)
record("Scenario O: Task executes directly on focal target without searching", any(a.target and a.target.element_id == "row_171" for a in actions_o))


# SCENARIO P: Task requires multiple intermediate pages
# Page 1: Search Discovery -> Page 2: Category Listing -> Page 3: Item Detail
sem_p1 = classify_page_semantics([ElementMetadata(id="search_bar", role="input", label="Search input", bbox=[10, 10, 200, 30])], "Search", "https://search.com")
sem_p2 = classify_page_semantics([ElementMetadata(id=f"card_{i}", role="a", label=f"Category Item {i}", href=f"/item/{i}", bbox=[10, i*30, 200, (i*30)+20]) for i in range(5)], "Category Catalog", "https://store.com/c/apparel")
sem_p3 = classify_page_semantics([ElementMetadata(id="btn_buy", role="button", label="Add to Cart", bbox=[10, 10, 100, 40])], "Product Details", "https://store.com/item/42")

record("Scenario P: Correct multi-stage semantic transitions recognized across intermediate pages", sem_p1.semantic_state == PAGE_SEARCH_DISCOVERY and sem_p2.semantic_state == PAGE_LISTING_CATALOG and sem_p3.semantic_state == PAGE_DETAIL_ENTITY)

print("\n" + "="*70)
passed_count = sum(1 for _, ok in results if ok)
total_count = len(results)
print(f"RESULTS: {passed_count}/{total_count} SCENARIOS PASSED")
print("="*70 + "\n")
assert passed_count == total_count, "Some generic architecture scenarios failed!"
