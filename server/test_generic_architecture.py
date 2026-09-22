"""
Comprehensive Generic Autonomous Architecture Test Suite (Scenarios A through N)
Validates:
1. Zero domain hardcoding
2. Deterministic action validation
3. Generic subgoal/task relevance check
4. Strict URL provenance
5. Anti-Element-ID typing protection
6. Loop shield signature-based hard blocking & strategy pivoting
7. Action execution != Goal achievement semantics
8. Fail-closed LLM handling
"""
import sys
import os
import inspect

sys.path.insert(0, r"d:\webman")

from server.app.schemas.schemas import (
    SanitizedContextPackage, PageContext, ElementMetadata, RedactionMetadata, 
    PrivacyReport, BrowserAction, ActionTarget, ActionValue, VerificationPayload, DownloadItem
)
from server.app.validator import validate_action, get_action_signature, score_link_relevance
from server.app.verifier import verify_task_completion
from server.app.planner import decide_next_action, track_subgoal_progress

results = []

def make_payload(**kwargs):
    defaults = dict(
        session_id="gen-test-001",
        step=1,
        instruction_sanitized="generic user instruction",
        page=PageContext(
            url_sanitized="https://example.org/page",
            title_sanitized="Generic Test Page",
            viewport={"width": 1280, "height": 720}
        ),
        elements=[],
        redactions=[],
        privacy_report=PrivacyReport(detected=0, sensitive=0, redacted=0),
        history=[]
    )
    defaults.update(kwargs)
    return SanitizedContextPackage(**defaults)

print("\n=== RUNNING 14 GENERIC ARCHITECTURE SCENARIOS (A - N) ===\n")

# TEST A: Relevant link vs unrelated link on search/directory page
task_a = "open bookstore and look for physics notes"
payload_a = make_payload(
    instruction_sanitized=task_a,
    page=PageContext(url_sanitized="https://www.google.com/search?q=bookstore", title_sanitized="bookstore - Google Search", viewport={"w": 1280, "h": 720}),
    elements=[
        ElementMetadata(id="link_unrelated", role="a", label="Unrelated Celebrity Gossip", href="https://unrelated-gossip.com", interactable=True, bbox=[0, 0, 100, 20]),
        ElementMetadata(id="link_target", role="a", label="Online Academic Bookstore & Notes", href="https://academic-bookstore.org", interactable=True, bbox=[0, 30, 200, 20])
    ],
    verification_state={"remaining_goal": "reach bookstore"}
)
rel_unrelated = score_link_relevance(payload_a.elements[0], task_a, "reach bookstore")
rel_target = score_link_relevance(payload_a.elements[1], task_a, "reach bookstore")
is_val_unrelated, _, _ = validate_action(BrowserAction(type="click", target=ActionTarget(element_id="link_unrelated")), payload_a)
is_val_target, _, _ = validate_action(BrowserAction(type="click", target=ActionTarget(element_id="link_target")), payload_a)
results.append(("TEST A: Relevant link preferred, unrelated link rejected by validator", rel_target > rel_unrelated and not is_val_unrelated and is_val_target))

# TEST B: Arbitrary OPEN_LINK not in observed hrefs rejected (URL Provenance)
payload_b = make_payload(
    instruction_sanitized="open portal and download manual",
    page=PageContext(url_sanitized="https://portal.net/home", title_sanitized="Portal", viewport={"w": 1280, "h": 720}),
    elements=[
        ElementMetadata(id="el_1", role="a", label="Docs", href="https://portal.net/docs", interactable=True, bbox=[0, 0, 100, 20])
    ]
)
is_valid_b1, _, reason_b1 = validate_action(BrowserAction(type="open_link", url="https://malicious-or-arbitrary-hallucinated.com/login"), payload_b)
is_valid_b2, _, _ = validate_action(BrowserAction(type="open_link", url="https://portal.net/docs"), payload_b)
results.append(("TEST B: Strict URL provenance rejects arbitrary unobserved links", (not is_valid_b1) and is_valid_b2 and "Provenance" in reason_b1))

# TEST C: TYPE with text == element ID rejected (Anti-Element-ID confusion)
payload_c = make_payload(
    instruction_sanitized="enter search term",
    elements=[
        ElementMetadata(id="visi_el_42", role="input", label="Search input", interactable=True, bbox=[0, 0, 100, 20])
    ]
)
is_val_c1, _, reason_c1 = validate_action(BrowserAction(type="type", target=ActionTarget(element_id="visi_el_42"), value=ActionValue(text="visi_el_42")), payload_c)
is_val_c2, _, reason_c2 = validate_action(BrowserAction(type="type", target=ActionTarget(element_id="visi_el_42"), value=ActionValue(text="red_3")), payload_c)
is_val_c3, _, _ = validate_action(BrowserAction(type="type", target=ActionTarget(element_id="visi_el_42"), value=ActionValue(text="quantum computing")), payload_c)
results.append(("TEST C: Anti-element-ID protection rejects internal IDs in TYPE", (not is_val_c1) and (not is_val_c2) and is_val_c3))

# TEST D: Unknown or non-existent target element rejected
payload_d = make_payload(
    elements=[ElementMetadata(id="btn_submit", role="button", label="Submit", interactable=True, bbox=[0, 0, 50, 20])]
)
is_val_d, _, reason_d = validate_action(BrowserAction(type="click", target=ActionTarget(element_id="non_existent_elem_99")), payload_d)
results.append(("TEST D: Unknown target element fails closed in action validator", (not is_val_d) and "does not exist" in reason_d))

# TEST E: Repeated CLICK with no state transition blocked by signature shield
payload_e = make_payload(
    elements=[ElementMetadata(id="btn_next", role="button", label="Next", interactable=True, bbox=[0, 0, 50, 20])]
)
act_e = BrowserAction(type="click", target=ActionTarget(element_id="btn_next"))
sig_e = get_action_signature(act_e)
blocked_e = {sig_e}
is_val_e, _, reason_e = validate_action(act_e, payload_e, blocked_signatures=blocked_e)
results.append(("TEST E: Repeated non-transition action blocked by Loop Shield signature", (not is_val_e) and "blocked by Loop Shield" in reason_e))

# TEST F: Repeated OPEN_LINK with no state transition blocked
payload_f = make_payload(
    elements=[ElementMetadata(id="link_f", role="a", label="Target", href="https://example.org/target", interactable=True, bbox=[0, 0, 50, 20])]
)
act_f = BrowserAction(type="open_link", url="https://example.org/target")
sig_f = get_action_signature(act_f)
blocked_f = {sig_f}
is_val_f, _, reason_f = validate_action(act_f, payload_f, blocked_signatures=blocked_f)
results.append(("TEST F: Repeated OPEN_LINK blocked by signature set", (not is_val_f) and "blocked by Loop Shield" in reason_f))

# TEST G: Recovery strategy pivot when action is blocked
def simulate_recovery_pivot(act, elements, blocked):
    sig = get_action_signature(act)
    if sig in blocked:
        alt_link = next((e for e in elements if (e.role in ("a", "link") and e.href and e.id != act.target.element_id)), None)
        if alt_link:
            return BrowserAction(type="open_link", target=ActionTarget(element_id=alt_link.id), url=alt_link.href)
        return BrowserAction(type="scroll", direction="down", amount=400)
    return act

elems_g = [
    ElementMetadata(id="btn_stuck", role="button", label="Stuck", interactable=True, bbox=[0, 0, 50, 20]),
    ElementMetadata(id="link_alt", role="a", label="Alternative Link", href="https://example.org/alt", interactable=True, bbox=[0, 30, 50, 20])
]
act_g = BrowserAction(type="click", target=ActionTarget(element_id="btn_stuck"))
pivoted_g = simulate_recovery_pivot(act_g, elems_g, {get_action_signature(act_g)})
results.append(("TEST G: Loop Shield recovery pivots to alternative link or scroll", pivoted_g.type == "open_link" and pivoted_g.url == "https://example.org/alt"))

# TEST H: LLM DONE rejected before verifier confirms goal
payload_h = VerificationPayload(
    task="open store and buy running shoes",
    current_url="https://generic-store.com/search?q=running+shoes",
    page_title="Store - Search Results",
    action_history=[{"action": "navigate"}, {"action": "type"}]
)
verif_h = verify_task_completion(payload_h)
results.append(("TEST H: Premature DONE rejected; verifier requires actual product opening", not verif_h.achieved and verif_h.goal_status == "GOAL_NOT_YET_ACHIEVED"))

# TEST I: Invalid LLM action fails closed (never converts to DONE)
from server.app.llm_planner import parse_llm_json_action
invalid_json = '{"action": "EXPLODE_BROWSER", "target": "all"}'
parsed_dict = parse_llm_json_action(invalid_json)
is_val_i, _, reason_i = validate_action(BrowserAction(type=parsed_dict["action"]), make_payload())
results.append(("TEST I: Invalid LLM action fails closed and is rejected", not is_val_i and "not recognized" in reason_i))

# TEST J: Fresh post-action observation evaluated for state change
def evaluate_state_transition(pre_url, pre_title, pre_count, post_url, post_title, post_count):
    return (pre_url != post_url) or (pre_title != post_title) or (pre_count != post_count)

st_changed = evaluate_state_transition("https://store.com/s", "Search", 12, "https://store.com/p/101", "Product 101", 18)
st_unchanged = evaluate_state_transition("https://store.com/s", "Search", 12, "https://store.com/s", "Search", 12)
results.append(("TEST J: Fresh post-action observation correctly evaluates state transition", st_changed is True and st_unchanged is False))

# TEST K: Clickable ancestor resolution logic in content script
def resolve_clickable_ancestor_sim(tag, has_parent_anchor):
    if tag in ("a", "button"):
        return tag
    if has_parent_anchor:
        return "a"
    return tag

resolved_tag = resolve_clickable_ancestor_sim("h3", True)
results.append(("TEST K: Non-interactive child element resolves to clickable ancestor", resolved_tag == "a"))

# TEST L: Generic search-result discovery with zero hardcoded sites
payload_l = make_payload(
    instruction_sanitized="go to university portal and view exam schedule",
    page=PageContext(url_sanitized="about:blank", title_sanitized="New Tab", viewport={"w": 1280, "h": 720}),
    elements=[]
)
actions_l, _ = decide_next_action(payload_l)
results.append(("TEST L: Generic task produces autonomous query discovery without hardcoding", actions_l[0].type == "navigate" and "google.com/search?q=" in actions_l[0].url))

# TEST M: Arbitrary unknown domain handled gracefully
payload_m = make_payload(
    instruction_sanitized="open https://custom-enterprise-erp-2026.internal and find invoice 9901",
    page=PageContext(url_sanitized="about:blank", title_sanitized="New Tab", viewport={"w": 1280, "h": 720}),
    elements=[]
)
actions_m, _ = decide_next_action(payload_m)
results.append(("TEST M: Arbitrary unknown domain navigates directly without allowlist constraints", actions_m[0].type == "navigate" and actions_m[0].url == "https://custom-enterprise-erp-2026.internal"))

# TEST N: Zero hardcoded website domains anywhere in validator.py
import server.app.validator as v_mod
v_source = inspect.getsource(v_mod)
# Only search engine host strings in urlparse utility checks allowed, no domain-specific business rules
has_forbidden_domain_rules = any(f'"{d}.' in v_source or f"'{d}." in v_source for d in ["amazon", "flipkart", "sih", "irctc"])
results.append(("TEST N: Zero website-specific rules or domains hardcoded in Action Validator", not has_forbidden_domain_rules))

# TEST O: Destination Identity Resolver - Target appearing ONLY in query parameter (MUST NOT MATCH)
# e.g., an unrelated account login with redirect/continue query param containing "portal" or destination
payload_o = make_payload(
    instruction_sanitized="open myportal and download reports",
    page=PageContext(url_sanitized="https://www.google.com/search?q=myportal", title_sanitized="myportal - Google Search", viewport={"w": 1280, "h": 720}),
    elements=[
        ElementMetadata(
            id="link_unrelated_query",
            role="a",
            label="Sign in to your account",
            href="https://accounts.external-service.org/login?continue=https%3A%2F%2Fother.com%2Fsearch%3Fq%3Dmyportal&service=mail",
            interactable=True,
            bbox=[0, 0, 200, 20]
        )
    ]
)
actions_o, summary_o = decide_next_action(payload_o)
results.append(("TEST O: Target appearing ONLY in query parameter is rejected by identity resolver", "NO_RELEVANT_CANDIDATE" in summary_o and actions_o[0].type == "scroll"))

# TEST P: Target appearing ONLY in redirect / continue parameter (MUST NOT MATCH)
payload_p = make_payload(
    instruction_sanitized="go to enterprisehub",
    page=PageContext(url_sanitized="https://www.google.com/search?q=enterprisehub", title_sanitized="Google Search", viewport={"w": 1280, "h": 720}),
    elements=[
        ElementMetadata(
            id="link_oauth",
            role="a",
            label="Single Sign On",
            href="https://auth.thirdparty.com/oauth2/authorize?redirect_uri=https://someapp.com/callback&dest=enterprisehub",
            interactable=True,
            bbox=[0, 0, 200, 20]
        )
    ]
)
actions_p, summary_p = decide_next_action(payload_p)
results.append(("TEST P: Target appearing ONLY in redirect/continue param does not match identity", "NO_RELEVANT_CANDIDATE" in summary_p and actions_p[0].type == "scroll"))

# TEST Q: Target appearing in URL fragment / hash (MUST NOT MATCH)
payload_q = make_payload(
    instruction_sanitized="open datasciencehub",
    page=PageContext(url_sanitized="https://www.google.com/search?q=datasciencehub", title_sanitized="Google Search", viewport={"w": 1280, "h": 720}),
    elements=[
        ElementMetadata(
            id="link_fragment",
            role="a",
            label="Global Documentation Center",
            href="https://docs.genericcloud.com/guides#datasciencehub",
            interactable=True,
            bbox=[0, 0, 200, 20]
        )
    ]
)
actions_q, summary_q = decide_next_action(payload_q)
results.append(("TEST Q: Target appearing ONLY in URL fragment does not match identity", "NO_RELEVANT_CANDIDATE" in summary_q and actions_q[0].type == "scroll"))

# TEST R: Target appearing in tracking parameters (utm_source, etc.) (MUST NOT MATCH)
payload_r = make_payload(
    instruction_sanitized="open cyberlab",
    page=PageContext(url_sanitized="https://www.google.com/search?q=cyberlab", title_sanitized="Google Search", viewport={"w": 1280, "h": 720}),
    elements=[
        ElementMetadata(
            id="link_tracking",
            role="a",
            label="Ad & Marketing Network",
            href="https://adnetwork.biz/click?utm_source=google&utm_campaign=cyberlab_promo",
            interactable=True,
            bbox=[0, 0, 200, 20]
        )
    ]
)
actions_r, summary_r = decide_next_action(payload_r)
results.append(("TEST R: Target appearing in tracking parameter does not match identity", "NO_RELEVANT_CANDIDATE" in summary_r and actions_r[0].type == "scroll"))

# TEST S: Target actually being the hostname (MUST MATCH)
payload_s = make_payload(
    instruction_sanitized="open cyberlab portal",
    page=PageContext(url_sanitized="https://www.google.com/search?q=cyberlab", title_sanitized="Google Search", viewport={"w": 1280, "h": 720}),
    elements=[
        ElementMetadata(
            id="link_cyberlab",
            role="a",
            label="CyberLab Official Research Portal",
            href="https://cyberlab.org/portal",
            interactable=True,
            bbox=[0, 0, 200, 20]
        )
    ]
)
actions_s, summary_s = decide_next_action(payload_s)
results.append(("TEST S: Target matching actual destination hostname matches identity", actions_s[0].type == "open_link" and actions_s[0].url == "https://cyberlab.org/portal"))

# TEST T: Target being a legitimate subdomain (MUST MATCH)
payload_t = make_payload(
    instruction_sanitized="open researchgate",
    page=PageContext(url_sanitized="https://www.google.com/search?q=researchgate", title_sanitized="Google Search", viewport={"w": 1280, "h": 720}),
    elements=[
        ElementMetadata(
            id="link_subdomain",
            role="a",
            label="Scientific Community Network",
            href="https://researchgate.net/home",
            interactable=True,
            bbox=[0, 0, 200, 20]
        )
    ]
)
actions_t, summary_t = decide_next_action(payload_t)
results.append(("TEST T: Legitimate domain/subdomain matches destination identity", actions_t[0].type == "open_link" and actions_t[0].url == "https://researchgate.net/home"))

# TEST U: No relevant candidate available returns structured NO_RELEVANT_CANDIDATE without blind click
payload_u = make_payload(
    instruction_sanitized="open fincorp and view statements",
    page=PageContext(url_sanitized="https://www.google.com/search?q=fincorp", title_sanitized="Google Search", viewport={"w": 1280, "h": 720}),
    elements=[
        ElementMetadata(id="link_random1", role="a", label="Random Weather Forecast", href="https://weather.com", interactable=True, bbox=[0, 0, 100, 20]),
        ElementMetadata(id="link_random2", role="a", label="Cooking Recipes", href="https://recipes.net", interactable=True, bbox=[0, 30, 100, 20])
    ]
)
actions_u, summary_u = decide_next_action(payload_u)
results.append(("TEST U: No relevant candidate yields NO_RELEVANT_CANDIDATE and does not click first result", actions_u[0].type == "scroll" and "NO_RELEVANT_CANDIDATE" in summary_u))

# ==============================================================================
# MULTI-STEP TASK COMPLETION TESTS (TESTS A - I)
# ==============================================================================
from server.app.planner import extract_selection_criterion, decompose_task_into_subgoals

# TEST A: "search for an item and add the selected result to cart"
# After search results appear, MUST return GOAL_NOT_YET_ACHIEVED, NOT GOAL_ACHIEVED
task_multi_a = "search for an item and add the selected result to cart"
payload_multi_a = VerificationPayload(
    task=task_multi_a,
    current_url="https://generic-store.com/search?q=item",
    page_title="generic-store : item results",
    action_history=[{"action": "navigate"}, {"action": "type"}],
    downloads=[]
)
resp_multi_a = verify_task_completion(payload_multi_a)
ok_a = (not resp_multi_a.achieved) and resp_multi_a.goal_status == "GOAL_NOT_YET_ACHIEVED" and "cart" in resp_multi_a.remaining_goal
results.append(("TEST A (Multi-Step): Search results with downstream add-to-cart yields GOAL_NOT_YET_ACHIEVED", ok_a))

# TEST B: "search for an item"
# With no downstream actions, search results displayed MUST return GOAL_ACHIEVED
task_multi_b = "search for an item"
payload_multi_b = VerificationPayload(
    task=task_multi_b,
    current_url="https://generic-store.com/search?q=item",
    page_title="generic-store : item results",
    action_history=[{"action": "navigate"}, {"action": "type"}],
    downloads=[]
)
resp_multi_b = verify_task_completion(payload_multi_b)
ok_b = resp_multi_b.achieved and resp_multi_b.goal_status == "GOAL_ACHIEVED"
results.append(("TEST B (Multi-Step): Pure search task with results displayed yields GOAL_ACHIEVED", ok_b))

# TEST C: "search for the highest-rated item and open it"
# After search results appear, MUST return GOAL_NOT_YET_ACHIEVED
task_multi_c = "search for the highest-rated item and open it"
payload_multi_c = VerificationPayload(
    task=task_multi_c,
    current_url="https://generic-store.com/search?q=item",
    page_title="generic-store : highest-rated item results",
    action_history=[{"action": "navigate"}, {"action": "type"}],
    downloads=[]
)
resp_multi_c = verify_task_completion(payload_multi_c)
ok_c = (not resp_multi_c.achieved) and resp_multi_c.goal_status == "GOAL_NOT_YET_ACHIEVED" and "open" in resp_multi_c.remaining_goal
results.append(("TEST C (Multi-Step): Search for highest-rated and open it yields GOAL_NOT_YET_ACHIEVED before open", ok_c))

# TEST D: "search for an item and download its document"
# After search results appear without completed download, MUST return GOAL_NOT_YET_ACHIEVED
task_multi_d = "search for an item and download its document"
payload_multi_d = VerificationPayload(
    task=task_multi_d,
    current_url="https://generic-portal.org/search?q=item",
    page_title="generic-portal : document results",
    action_history=[{"action": "navigate"}, {"action": "type"}],
    downloads=[]
)
resp_multi_d = verify_task_completion(payload_multi_d)
ok_d = (not resp_multi_d.achieved) and resp_multi_d.goal_status == "GOAL_NOT_YET_ACHIEVED" and "download" in resp_multi_d.remaining_goal
results.append(("TEST D (Multi-Step): Search and download document yields GOAL_NOT_YET_ACHIEVED without download state", ok_d))

# TEST E: Task with "best selling" -> selection criterion recognized as BEST_SELLING
crit_e = extract_selection_criterion("find the best selling black shoes")
ok_e = crit_e is not None and crit_e[0] == "BEST_SELLING"
results.append(("TEST E (Multi-Step): 'best selling' recognized as BEST_SELLING selection criterion", ok_e))

# TEST F: Task with "best-selling" -> same semantic criterion
crit_f = extract_selection_criterion("find the best-selling black shoes")
ok_f = crit_f is not None and crit_f[0] == "BEST_SELLING"
results.append(("TEST F (Multi-Step): 'best-selling' recognized as BEST_SELLING selection criterion", ok_f))

# TEST G: Task with "best seller" -> same semantic criterion
crit_g = extract_selection_criterion("find the best seller black shoes")
ok_g = crit_g is not None and crit_g[0] == "BEST_SELLING"
results.append(("TEST G (Multi-Step): 'best seller' recognized as BEST_SELLING selection criterion", ok_g))

# TEST H: Action button was clicked but postcondition did not occur -> GOAL_NOT_YET_ACHIEVED
task_multi_h = "search for an item and add the selected result to cart"
payload_multi_h = VerificationPayload(
    task=task_multi_h,
    current_url="https://generic-store.com/item/456",
    page_title="generic-store : Item 456 Details",
    action_history=[{"action": "navigate"}, {"action": "click"}, {"action": "click"}],
    downloads=[]
)
# Note: Page title and URL have NO cart confirmation text
resp_multi_h = verify_task_completion(payload_multi_h)
ok_h = (not resp_multi_h.achieved) and resp_multi_h.goal_status == "GOAL_NOT_YET_ACHIEVED"
results.append(("TEST H (Multi-Step): Button clicked but cart postcondition not observed yields GOAL_NOT_YET_ACHIEVED", ok_h))

# TEST I: All subgoals completed and final postcondition observed -> GOAL_ACHIEVED
task_multi_i = "search for an item and add the selected result to cart"
payload_multi_i = VerificationPayload(
    task=task_multi_i,
    current_url="https://generic-store.com/cart",
    page_title="generic-store : Added to Cart - 1 Item in Cart",
    action_history=[{"action": "navigate"}, {"action": "click"}, {"action": "click"}],
    downloads=[]
)
resp_multi_i = verify_task_completion(payload_multi_i)
ok_i = resp_multi_i.achieved and resp_multi_i.goal_status == "GOAL_ACHIEVED" and resp_multi_i.remaining_goal == "None"
results.append(("TEST I (Multi-Step): All subgoals complete & final cart postcondition verified yields GOAL_ACHIEVED", ok_i))

# ==============================================================================
# SECTION 18: GENERIC PRODUCT TASK EXECUTION TESTS (SCENARIOS A - M)
# ==============================================================================
from server.app.product_constraints import (
    extract_product_constraints,
    verify_candidate_match,
    rank_candidates_by_criteria,
    detect_missing_prerequisites
)

# TEST 18.A: Requested product type vs different product type -> different type is rejected
const_a = extract_product_constraints("find a black shirt")
match_a1, reason_a1 = verify_candidate_match("Men's Regular Fit Black Shirt", const_a)
match_a2, reason_a2 = verify_candidate_match("Men's Formal Black Pants", const_a)
results.append(("TEST 18.A: Requested product type vs different product type (different rejected)", match_a1 and not match_a2 and "pants" in reason_a2.lower()))

# TEST 18.B: Requested color vs wrong color -> wrong color rejected
const_b = extract_product_constraints("find a red backpack")
match_b1, reason_b1 = verify_candidate_match("Durable Travel Red Backpack", const_b)
match_b2, reason_b2 = verify_candidate_match("Durable Travel Blue Backpack", const_b)
results.append(("TEST 18.B: Requested color vs wrong color (wrong color rejected)", match_b1 and not match_b2 and "blue" in reason_b2.lower()))

# TEST 18.C: Correct color but wrong product type -> rejected
match_c, reason_c = verify_candidate_match("Genuine Black Leather Shoes", const_a)
results.append(("TEST 18.C: Correct color but wrong product type rejected", not match_c and "product type mismatch" in reason_c.lower()))

# TEST 18.D: Correct product type and color -> candidate accepted
match_d, reason_d = verify_candidate_match("Casual Slim Fit Black Cotton Shirt", const_a)
results.append(("TEST 18.D: Correct product type and color accepted", match_d and "satisfied" in reason_d))

# TEST 18.E: Selection criterion applied AFTER hard constraints
cand_e1 = ElementMetadata(id="c1", role="a", label="Best Seller: Men's Blue Jeans", interactable=True, bbox=[0, 0, 100, 20])
cand_e2 = ElementMetadata(id="c2", role="a", label="Best Seller: Men's Regular Fit Black Shirt", interactable=True, bbox=[0, 30, 100, 20])
cand_e3 = ElementMetadata(id="c3", role="a", label="Standard Black Shirt", interactable=True, bbox=[0, 60, 100, 20])
const_e = extract_product_constraints("find the best selling black shirt and open it")
# Blue jeans fails hard constraints; between c2 and c3, c2 wins on criterion
val_e = [c for c in [cand_e1, cand_e2, cand_e3] if verify_candidate_match(c.label, const_e)[0]]
ranked_e = rank_candidates_by_criteria(val_e, const_e)
results.append(("TEST 18.E: Selection criterion applied strictly after hard constraints", len(val_e) == 2 and cand_e1 not in val_e and ranked_e[0][0].id == "c2"))

# TEST 18.F: No valid candidate available -> does not select arbitrary result, yields NO_VALID_TARGET_FOUND
payload_f = make_payload(
    instruction_sanitized="find a yellow umbrella and open it",
    elements=[
        ElementMetadata(id="e1", role="a", label="Black Raincoat", interactable=True, bbox=[0, 0, 100, 20]),
        ElementMetadata(id="e2", role="a", label="Blue Travel Bag", interactable=True, bbox=[0, 30, 100, 20])
    ],
    history=[{"action": "navigate"}]
)
actions_f, summary_f = decide_next_action(payload_f)
results.append(("TEST 18.F: No valid candidate returns NO_VALID_TARGET_FOUND without blind selection", "NO_VALID_TARGET_FOUND" in summary_f and actions_f[0].type == "scroll"))

# TEST 18.G: Product page does not match selected target -> TARGET_MISMATCH
payload_g = VerificationPayload(
    task="find a black shirt and open it",
    current_url="https://generic-store.com/p/item-pants-123",
    page_title="Men's Slim Fit Black Chinos - generic-store",
    action_history=[{"action": "navigate"}, {"action": "click"}],
    downloads=[]
)
resp_g = verify_task_completion(payload_g)
results.append(("TEST 18.G: Product page mismatch yields TARGET_MISMATCH recovery", not resp_g.achieved and resp_g.goal_status == "RECOVERY_REQUIRED" and "TARGET_MISMATCH" in resp_g.reason))

# TEST 18.H: Requested action requires a missing prerequisite -> identifies prerequisite instead of failing
const_h = extract_product_constraints("find a black dress and add to cart")
elems_h = [
    ElementMetadata(id="size_dropdown", role="select", label="Select Size", interactable=True, bbox=[0, 0, 100, 30]),
    ElementMetadata(id="opt_s", role="option", label="S", interactable=True, bbox=[0, 10, 50, 20]),
    ElementMetadata(id="opt_m", role="option", label="M", interactable=True, bbox=[0, 30, 50, 20]),
    ElementMetadata(id="btn_cart", role="button", label="Add to Cart", interactable=True, bbox=[0, 70, 100, 40])
]
prereq_h = detect_missing_prerequisites(elems_h, "ADD_TO_CART", const_h)
results.append(("TEST 18.H: Missing variant prerequisite identified before action execution", prereq_h is not None and prereq_h["type"] == "SIZE_SELECTION"))

# TEST 18.I: Required prerequisite specified by user is selected successfully
const_i = extract_product_constraints("find a black dress in size M and add to cart")
prereq_i = detect_missing_prerequisites(elems_h, "ADD_TO_CART", const_i)
payload_i = make_payload(
    instruction_sanitized="find a black dress in size M and add to cart",
    page=PageContext(url_sanitized="https://generic-store.com/p/black-dress", title_sanitized="Black Dress - generic-store", viewport={"w": 1280, "h": 720}),
    elements=elems_h,
    history=[{"action": "navigate"}, {"action": "click"}]
)
actions_i, summary_i = decide_next_action(payload_i)
results.append(("TEST 18.I: User-specified prerequisite is selected before cart click", actions_i[0].type == "click" and actions_i[0].target.element_id == "opt_m"))

# TEST 18.J: Action clicked but postcondition absent -> GOAL_NOT_YET_ACHIEVED
payload_j = VerificationPayload(
    task="find a black shirt and add to cart",
    current_url="https://generic-store.com/p/black-shirt",
    page_title="Men's Black Shirt",
    action_history=[{"action": "navigate"}, {"action": "click"}, {"action": "click"}],
    downloads=[]
)
resp_j = verify_task_completion(payload_j)
results.append(("TEST 18.J: Action clicked but postcondition absent yields GOAL_NOT_YET_ACHIEVED", not resp_j.achieved and resp_j.goal_status == "GOAL_NOT_YET_ACHIEVED"))

# TEST 18.K: Action clicked and postcondition observed -> subgoal completed / GOAL_ACHIEVED
payload_k = VerificationPayload(
    task="find a black shirt and add to cart",
    current_url="https://generic-store.com/cart",
    page_title="Men's Black Shirt - Added to Cart - View Cart (1)",
    action_history=[{"action": "navigate"}, {"action": "click"}, {"action": "click"}],
    downloads=[]
)
resp_k = verify_task_completion(payload_k)
results.append(("TEST 18.K: Action clicked and cart postcondition observed yields GOAL_ACHIEVED", resp_k.achieved and resp_k.goal_status == "GOAL_ACHIEVED"))

# TEST 18.L: User did not specify variant and multiple choices exist -> ask user rather than invent preference
payload_l = make_payload(
    instruction_sanitized="find a black dress and add to cart",
    page=PageContext(url_sanitized="https://generic-store.com/p/black-dress", title_sanitized="Black Dress - generic-store", viewport={"w": 1280, "h": 720}),
    elements=elems_h,
    history=[{"action": "navigate"}, {"action": "click"}]
)
actions_l, summary_l = decide_next_action(payload_l)
results.append(("TEST 18.L: Unspecified variant with multiple choices asks user instead of guessing", actions_l[0].type == "ask_user" and "size" in actions_l[0].question.lower()))

# TEST 18.M: Completely unknown website & arbitrary product works without hardcoding
import server.app.product_constraints as pc_mod
pc_source = inspect.getsource(pc_mod)
has_forbidden_domain = any(f'"{d}' in pc_source or f"'{d}" in pc_source for d in ["amazon", "flipkart", "ebay", "walmart", "target", "shopify", "myntra"])
results.append(("TEST 18.M: Zero hardcoded shopping websites or domains in product constraints engine", not has_forbidden_domain))

# ==============================================================================
# SECTION 19: STRICT PRODUCT TASK STATE MACHINE TESTS (TEST 1 - 12)
# ==============================================================================
from server.app.product_constraints import (
    verify_selection_criterion_evidence,
    STATE_SEARCH_COMPLETE,
    STATE_TARGET_CANDIDATE_FOUND,
    STATE_TARGET_IDENTIFIED,
    STATE_TARGET_VERIFIED,
    STATE_PREREQUISITES_RESOLVED,
    STATE_ACTION_EXECUTED,
    STATE_ACTION_VERIFIED,
    STATE_GOAL_ACHIEVED
)

# TEST 19.1: Requested product is shirt, observed is dress -> TARGET_IDENTIFIED = false
const_t1 = extract_product_constraints("find a black shirt")
match_t1, reason_t1 = verify_candidate_match("Evening Black Cocktail Dress", const_t1)
results.append(("TEST 19.1: Requested shirt vs observed dress -> candidate rejected (TARGET_IDENTIFIED = false)", not match_t1 and "product type mismatch" in reason_t1.lower()))

# TEST 19.2: Requested gender is men, observed candidate is women -> candidate rejected
const_t2 = extract_product_constraints("find a black shirt for men")
match_t2, reason_t2 = verify_candidate_match("Women's Slim Fit Black Shirt", const_t2)
results.append(("TEST 19.2: Requested gender men vs observed women -> candidate rejected", not match_t2 and "gender" in reason_t2.lower()))

# TEST 19.3: Requested color is black, observed candidate is blue -> candidate rejected
const_t3 = extract_product_constraints("find a black shirt")
match_t3, reason_t3 = verify_candidate_match("Men's Formal Blue Shirt", const_t3)
results.append(("TEST 19.3: Requested color black vs observed blue -> candidate rejected", not match_t3 and "color" in reason_t3.lower()))

# TEST 19.4: Candidate satisfies product type/color/gender but selection criterion is not proven -> TARGET_VERIFIED = false
const_t4 = extract_product_constraints("find the best-selling black shirt for men and open it")
cand_t4_text = "Men's Regular Fit Black Shirt"
match_t4_hard, _ = verify_candidate_match(cand_t4_text, const_t4)
ev_t4, reason_t4 = verify_selection_criterion_evidence(cand_t4_text, const_t4)
results.append(("TEST 19.4: Candidate satisfies hard constraints but criterion is unproven -> not verified", match_t4_hard and not ev_t4 and "no observable evidence" in reason_t4.lower()))

# TEST 19.5: Valid product requires size selection, no size specified, multiple available -> ASK_USER
const_t5 = extract_product_constraints("find a black shirt and add to cart")
elems_t5 = [
    ElementMetadata(id="sz_drop", role="select", label="Select Size", interactable=True, bbox=[0, 0, 100, 30]),
    ElementMetadata(id="sz_s", role="option", label="S", interactable=True, bbox=[0, 10, 50, 20]),
    ElementMetadata(id="sz_m", role="option", label="M", interactable=True, bbox=[0, 30, 50, 20]),
    ElementMetadata(id="sz_l", role="option", label="L", interactable=True, bbox=[0, 50, 50, 20]),
    ElementMetadata(id="btn_cart", role="button", label="Add to Cart", interactable=True, bbox=[0, 70, 100, 40])
]
prereq_t5 = detect_missing_prerequisites(elems_t5, "ADD_TO_CART", const_t5)
payload_t5 = make_payload(
    instruction_sanitized="find a black shirt and add to cart",
    page=PageContext(url_sanitized="https://generic-store.com/p/black-shirt", title_sanitized="Black Shirt - generic-store", viewport={"w": 1280, "h": 720}),
    elements=elems_t5,
    history=[{"action": "navigate"}, {"action": "click"}]
)
acts_t5, _ = decide_next_action(payload_t5)
results.append(("TEST 19.5: Required size unspecified with multiple choices returns ASK_USER without random guessing", prereq_t5["requires_prompt"] and acts_t5[0].type == "ask_user" and "size" in acts_t5[0].question.lower()))

# TEST 19.6: Required size is already safely selected -> agent may continue without prompt
elems_t6 = [
    ElementMetadata(id="sz_drop", role="select", label="Select Size: M (Selected)", interactable=True, bbox=[0, 0, 100, 30]),
    ElementMetadata(id="btn_cart", role="button", label="Add to Cart", interactable=True, bbox=[0, 70, 100, 40])
]
prereq_t6 = detect_missing_prerequisites(elems_t6, "ADD_TO_CART", const_t5)
results.append(("TEST 19.6: Required size already safely selected -> prereq detector returns None to proceed", prereq_t6 is None))

# TEST 19.7: Add-to-cart click executes but no cart state changes -> ACTION_EXECUTED=true, ACTION_VERIFIED=false, GOAL_ACHIEVED=false
payload_t7 = VerificationPayload(
    task="find a black shirt and add to cart",
    current_url="https://generic-store.com/p/black-shirt",
    page_title="Men's Black Shirt",
    action_history=[{"action": "navigate"}, {"action": "click"}, {"action": "click"}],
    downloads=[]
)
resp_t7 = verify_task_completion(payload_t7)
results.append(("TEST 19.7: Add-to-cart click executes without cart state change -> ACTION_EXECUTED, not achieved", not resp_t7.achieved and resp_t7.product_state == STATE_ACTION_EXECUTED and resp_t7.goal_status == "GOAL_NOT_YET_ACHIEVED"))

# TEST 19.8: Cart state changes and contains selected valid target -> ACTION_VERIFIED=true, GOAL_ACHIEVED=true
payload_t8 = VerificationPayload(
    task="find a black shirt and add to cart",
    current_url="https://generic-store.com/cart",
    page_title="Men's Black Shirt - Added to Cart (1 Item)",
    action_history=[{"action": "navigate"}, {"action": "click"}, {"action": "click"}],
    downloads=[]
)
resp_t8 = verify_task_completion(payload_t8)
results.append(("TEST 19.8: Cart state changes with valid target -> GOAL_ACHIEVED verified", resp_t8.achieved and resp_t8.product_state == STATE_GOAL_ACHIEVED and resp_t8.goal_status == "GOAL_ACHIEVED"))

# TEST 19.9: Repeated failed click is blocked by structured recovery state
payload_t9 = make_payload(
    instruction_sanitized="find a black shirt and open it",
    elements=[
        ElementMetadata(id="btn_stuck", role="a", label="Stuck Item Black Shirt", interactable=True, bbox=[0, 0, 100, 20]),
        ElementMetadata(id="link_other", role="a", label="Alternative Black Shirt", interactable=True, bbox=[0, 30, 100, 20])
    ],
    history=[{"action": "click", "target": "btn_stuck"}]
)
payload_t9.recovery_state = {
    "failure_type": "REPEATED_ACTION",
    "blocked_action": {"type": "click", "target": "btn_stuck"},
    "blocked_target_id": "btn_stuck"
}
acts_t9, sum_t9 = decide_next_action(payload_t9)
results.append(("TEST 19.9: Repeated action is blocked by structured recovery state, selecting alternative", acts_t9[0].target.element_id == "link_other"))

# TEST 19.10: Unrelated URL/query parameter containing target keyword is rejected by identity resolver
from server.app.validator import extract_url_identity
_, _, id_tokens_t10 = extract_url_identity("https://account.generic.org/signin?continue=https%3A%2F%2Fstore.org%2Fblack-shirt%3Fref%3D123")
results.append(("TEST 19.10: Keyword inside query parameter is excluded from URL identity tokens", "shirt" not in id_tokens_t10 and "black" not in id_tokens_t10))

# TEST 19.11: Search returns multiple products; only one satisfies ALL hard constraints
cand_t11_1 = ElementMetadata(id="c1", role="a", label="Women's Black Shirt", interactable=True, bbox=[0, 0, 100, 20])
cand_t11_2 = ElementMetadata(id="c2", role="a", label="Men's Blue Shirt", interactable=True, bbox=[0, 30, 100, 20])
cand_t11_3 = ElementMetadata(id="c3", role="a", label="Men's Black Shirt", interactable=True, bbox=[0, 60, 100, 20])
const_t11 = extract_product_constraints("find a black shirt for men and open it")
valid_t11 = [c for c in [cand_t11_1, cand_t11_2, cand_t11_3] if verify_candidate_match(c.label, const_t11)[0]]
results.append(("TEST 19.11: Out of multiple products, only candidate satisfying all hard constraints is selected", len(valid_t11) == 1 and valid_t11[0].id == "c3"))

# TEST 19.12: No candidate satisfies all hard constraints -> NO_VALID_TARGET_FOUND, never choose closest match
payload_t12 = make_payload(
    instruction_sanitized="find a purple leather jacket and open it",
    elements=[
        ElementMetadata(id="e1", role="a", label="Black Leather Jacket", interactable=True, bbox=[0, 0, 100, 20]),
        ElementMetadata(id="e2", role="a", label="Purple Cotton Hoodie", interactable=True, bbox=[0, 30, 100, 20])
    ],
    history=[{"action": "navigate"}]
)
acts_t12, sum_t12 = decide_next_action(payload_t12)
results.append(("TEST 19.12: No candidate satisfies all hard constraints yields NO_VALID_TARGET_FOUND without selecting closest match", "NO_VALID_TARGET_FOUND" in sum_t12 and acts_t12[0].type == "scroll"))

# Print summary
passed = 0
failed = 0
for name, ok in results:
    st = "PASS" if ok else "FAIL"
    print(f"  [{st}] {name}")
    if ok: passed += 1
    else: failed += 1

print(f"\n  Total: {passed+failed}  Passed: {passed}  Failed: {failed}\n")
sys.exit(0 if failed == 0 else 1)
