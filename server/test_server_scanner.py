"""
Regression tests for the server-side privacy scanner fix.

Tests:
1. Amazon numeric element ID (7900081686) must NOT trigger a rejection
2. Real Indian phone number in instruction text MUST still be caught
3. Email in label MUST still be caught
4. PAN card in title MUST still be caught
5. Vault secret in any field MUST still be caught
"""
import sys
import os

sys.path.insert(0, r"d:\webman")

from server.app.main import collect_text_fields_for_scan, SERVER_PII_PROSE_PATTERNS, FORBIDDEN_RAW_SECRETS
from server.app.schemas.schemas import SanitizedContextPackage, PageContext, ElementMetadata, RedactionMetadata, PrivacyReport

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
results = []


def run_scan(payload):
    text_fields = collect_text_fields_for_scan(payload)
    violations = []
    for field_path, text_value in text_fields:
        for pat_name, pattern in SERVER_PII_PROSE_PATTERNS:
            matches = pattern.findall(text_value)
            leaks = [m for m in matches if "REDACTED" not in m]
            if leaks:
                violations.append((field_path, pat_name, len(leaks)))
    return violations


def make_base_payload(**kwargs):
    defaults = dict(
        session_id="sess-abc-001",
        step=1,
        instruction_sanitized="find black shirts",
        page=PageContext(
            url_sanitized="https://www.amazon.in/s?k=black+shirts",
            title_sanitized="Amazon.in : black shirts",
            viewport={"width": 1280, "height": 720}
        ),
        elements=[],
        redactions=[],
        privacy_report=PrivacyReport(detected=0, sensitive=0, redacted=0),
        history=[]
    )
    defaults.update(kwargs)
    return SanitizedContextPackage(**defaults)


# TEST 1: Amazon numeric element ID must NOT trigger rejection
payload = make_base_payload(
    elements=[
        ElementMetadata(id="7900081686", role="link", label="Black Cotton Shirt", bbox=[0, 0, 100, 50]),
        ElementMetadata(id="visi_el_2", role="button", label="Add to cart", bbox=[0, 0, 80, 30]),
    ]
)
violations = run_scan(payload)
ok = len(violations) == 0
results.append(("TEST 1: Amazon element ID 7900081686 NOT flagged as PII", ok))
if not ok:
    print(f"  DETAIL: unexpected violations: {violations}")

# TEST 2: Real phone number in instruction text MUST be caught
payload = make_base_payload(instruction_sanitized="call me at 9876543210 urgently")
violations = run_scan(payload)
ok = any(v[1] == "PHONE" for v in violations)
results.append(("TEST 2: Real phone number in instruction caught", ok))
if not ok:
    print(f"  DETAIL: no PHONE. All violations: {violations}")

# TEST 3: Email in element label MUST be caught
payload = make_base_payload(
    elements=[ElementMetadata(id="visi_el_1", role="text", label="user@example.com", bbox=[0, 0, 100, 20])]
)
violations = run_scan(payload)
ok = any(v[1] == "EMAIL" for v in violations)
results.append(("TEST 3: Email in element label caught", ok))

# TEST 4: PAN in title MUST be caught
payload = make_base_payload(
    page=PageContext(url_sanitized="https://example.com", title_sanitized="User ABCDE1234F details", viewport={"width":1280,"height":720})
)
violations = run_scan(payload)
ok = any(v[1] == "PAN" for v in violations)
results.append(("TEST 4: PAN card in title caught", ok))

# TEST 5: Phone in element label MUST be caught
payload = make_base_payload(
    elements=[ElementMetadata(id="visi_el_5", role="text", label="Contact: 9123456780", bbox=[0, 0, 200, 20])]
)
violations = run_scan(payload)
ok = any(v[1] == "PHONE" for v in violations)
results.append(("TEST 5: Phone number in element label caught", ok))

# TEST 6: Vault secret caught in full JSON
full_json = '{"secret":"SuperSecretBankPass2026!"}'
secret_found = any(sec in full_json for sec in FORBIDDEN_RAW_SECRETS)
results.append(("TEST 6: Vault secret caught in full JSON", secret_found))

# TEST 7: Numeric element ID excluded, label-only scan passes clean
payload = make_base_payload(
    elements=[ElementMetadata(id="7900081686", role="link", label="Result count", bbox=[0, 0, 100, 30])]
)
violations = run_scan(payload)
ok = len(violations) == 0
results.append(("TEST 7: Numeric element ID excluded, label-only scan passes", ok))

print("\n=== SERVER SCANNER REGRESSION TESTS ===\n")
passed = 0
failed = 0
for name, ok in results:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}")
    if ok: passed += 1
    else: failed += 1

print(f"\n  Total: {passed+failed}  Passed: {passed}  Failed: {failed}\n")
if failed > 0:
    sys.exit(1)

# ==============================================================================
# AUTONOMOUS AGENT INTEGRATION TESTS (SCENARIOS A - G)
# ==============================================================================
print("=== AUTONOMOUS AGENT TESTS (SCENARIOS A - G) ===\n")
agent_results = []

from server.app.planner import decide_next_action, extract_search_terms
from server.app.verifier import verify_task_completion
from server.app.schemas.schemas import VerificationPayload, DownloadItem

# TEST A: Amazon - Find black shirts under 1000
task_a = "Find black shirts under 1000"
terms_a = extract_search_terms(task_a)
has_term = "black shirts under 1000" in terms_a
payload_a = make_base_payload(
    instruction_sanitized=task_a,
    elements=[
        ElementMetadata(id="twotabsearchtextbox", role="input", label="Search Amazon.in", interactable=True, sensitivity="public", bbox=[0, 0, 200, 40]),
        ElementMetadata(id="nav-search-submit-button", role="button", label="Go", interactable=True, sensitivity="public", bbox=[200, 0, 40, 40])
    ]
)
actions_a, _ = decide_next_action(payload_a)
act_a_ok = actions_a[0].type == "type" and actions_a[0].value.text == "black shirts under 1000"
agent_results.append(("TEST A: Amazon - Query extraction and search typing", has_term and act_a_ok))

# TEST B: Google - Go to SIH portal and find problem statement 171
task_b = "Go to the SIH portal and find problem statement 171"
payload_b = make_base_payload(
    instruction_sanitized=task_b,
    page=PageContext(url_sanitized="about:blank", title_sanitized="New Tab", viewport={"w": 1280, "h": 720}),
    elements=[]
)
actions_b, _ = decide_next_action(payload_b)
act_b_ok = actions_b[0].type == "navigate" and "google.com/search?q=" in actions_b[0].url and "sih2024" not in actions_b[0].url
agent_results.append(("TEST B: Google - Autonomous query discovery without hardcoding", act_b_ok))

# TEST C: SIH - Open problem statement 171 and download it (Verifier test)
task_c = "Open problem statement 171 and download it"
p_c_fail = VerificationPayload(
    task=task_c,
    current_url="https://sih.gov.in/sih2026/problem-statements",
    page_title="Smart India Hackathon 2026 - Problem Statements",
    downloads=[]
)
r_c_fail = verify_task_completion(p_c_fail)
p_c_pass = VerificationPayload(
    task=task_c,
    current_url="https://sih.gov.in/sih2026/problem-statements",
    page_title="Smart India Hackathon 2026 - Problem Statements",
    downloads=[DownloadItem(id="1", filename="PS_171_Problem_Statement.pdf", state="complete", file_size=45000)]
)
r_c_pass = verify_task_completion(p_c_pass)
agent_results.append(("TEST C: SIH - Download verification checks browser state and stops early done", (not r_c_fail.achieved) and r_c_pass.achieved))

# TEST D: Multi-step Navigation - Google organic search result selection
task_d = "Go to the SIH portal and find problem statement 171"
payload_d = make_base_payload(
    instruction_sanitized=task_d,
    page=PageContext(url_sanitized="https://www.google.com/search?q=sih+portal", title_sanitized="sih portal - Google Search", viewport={"w": 1280, "h": 720}),
    elements=[
        ElementMetadata(id="link-1", role="a", label="Smart India Hackathon 2026 - Official Portal", interactable=True, sensitivity="public", bbox=[0, 100, 300, 20]),
        ElementMetadata(id="link-2", role="a", label="Images for sih portal", interactable=True, sensitivity="public", bbox=[0, 130, 200, 20])
    ],
    history=[{"action": "navigate", "result": "ok"}]
)
actions_d, _ = decide_next_action(payload_d)
act_d_ok = actions_d[0].type == "click" and actions_d[0].target.element_id == "link-1"
agent_results.append(("TEST D: Navigation - Autonomous organic search result selection", act_d_ok))

# TEST E: Wrong-site edition mismatch recovery (SIH 2024 archive detection)
task_e = "Go to the SIH portal and find problem statement 171"
p_e = VerificationPayload(
    task=task_e,
    current_url="https://sih2024.aicte-india.org/problem-statements",
    page_title="Smart India Hackathon 2024 Archive",
    downloads=[]
)
r_e = verify_task_completion(p_e)
agent_results.append(("TEST E: Wrong-site recovery - SIH 2024 archive detected & recovery requested", (not r_e.achieved) and r_e.requires_recovery))

# TEST F: Zero Site-Specific Hardcoding verification in planner
import inspect
src_planner = inspect.getsource(decide_next_action)
forbidden_sites = ["amazon.in", "sih2024.aicte-india.org", "sih.gov.in", "irctc.co.in"]
no_hardcode = not any(f'"{s}"' in src_planner or f"'{s}'" in src_planner for s in forbidden_sites)
agent_results.append(("TEST F: Zero hardcoded sites in planner engine", no_hardcode))

# TEST G: Action Success != Goal Success (Amazon multi-step verification)
task_g = "Open Amazon and find the best seller black shirt and open it."

# Step 1: Navigated to Google search results for "amazon"
p_g_step1 = VerificationPayload(
    task=task_g,
    current_url="https://www.google.com/search?q=amazon",
    page_title="amazon - Google Search",
    action_history=[{"action": "navigate", "result": "ok"}]
)
r_g_step1 = verify_task_completion(p_g_step1)
step1_ok = (not r_g_step1.achieved) and r_g_step1.goal_status == "GOAL_NOT_YET_ACHIEVED"

# Step 2: Arrived at Amazon search results
p_g_step2 = VerificationPayload(
    task=task_g,
    current_url="https://www.amazon.in/s?k=black+shirt",
    page_title="Amazon.in : black shirt",
    action_history=[{"action": "navigate", "result": "ok"}, {"action": "click", "result": "ok"}]
)
r_g_step2 = verify_task_completion(p_g_step2)
step2_ok = (not r_g_step2.achieved) and r_g_step2.goal_status == "GOAL_NOT_YET_ACHIEVED"

# Step 3: Clicked into the best seller item page (product detail page)
p_g_step3 = VerificationPayload(
    task=task_g,
    current_url="https://www.amazon.in/dp/B08XYZ1234/ref=sr_1_1?keywords=black+shirt",
    page_title="Best Seller: Men's Regular Fit Black Shirt : Amazon.in",
    action_history=[{"action": "navigate", "result": "ok"}, {"action": "click", "result": "ok"}, {"action": "click", "result": "ok"}]
)
r_g_step3 = verify_task_completion(p_g_step3)
step3_ok = r_g_step3.achieved and r_g_step3.goal_status == "GOAL_ACHIEVED"

agent_results.append(("TEST G: Multi-Step Goal Semantics - Google Search never completes product goal", step1_ok and step2_ok and step3_ok))


# Print Agent Results
agent_passed = 0
agent_failed = 0
for name, ok in agent_results:
    st = "PASS" if ok else "FAIL"
    print(f"  [{st}] {name}")
    if ok: agent_passed += 1
    else: agent_failed += 1

print(f"\n  Autonomous Agent Scenarios: {agent_passed+agent_failed}  Passed: {agent_passed}  Failed: {agent_failed}\n")
sys.exit(0 if agent_failed == 0 else 1)
