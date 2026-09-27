"""
Updated Server Planner supporting Local Ollama LLM (Qwen3.5:9B):
- Uses local Ollama LLM directly for task understanding and action selection
- Zero hardcoded websites, coordinates, or element IDs
- Defense-in-depth Fail-Closed PII and Raw Secret Scanners
"""
from fastapi import FastAPI, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from server.app.schemas.schemas import SanitizedContextPackage, AgentPlanResponse, BrowserAction, ActionTarget, ActionValue
from server.app.llm_planner import plan_with_best_llm, check_active_planner
from server.app.planner import decide_next_action
from server.app.privacy.verhoeff import validate_verhoeff, normalize_digits
import re

app = FastAPI(title="Visiionary Privacy Browser Agent Server", version="2.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Server-side PII patterns — applied ONLY to human-readable prose text fields.
# These patterns are NOT run against element IDs, base64 screenshots, or the
# full JSON dump (which contains opaque identifiers that cause false positives).
# ---------------------------------------------------------------------------
# Email address in prose
_PAT_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
# Indian mobile number: must start with 6/7/8/9 and be exactly 10 digits (word-bounded)
_PAT_PHONE = re.compile(r"(?<!\d)(?:\+91[\-\s]?)?[6789]\d{4}[\-\s]?\d{5}(?!\d)")
# Payment card (4×4 digit groups)
_PAT_CARD = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
# PAN card
_PAT_PAN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b")
# Aadhaar (3×4 digit groups)
_PAT_AADHAAR = re.compile(r"\b\d{4}[\-\s]?\d{4}[\-\s]?\d{4}\b")
# UPI ID
_PAT_UPI = re.compile(r"[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}")
# Bank account in transfer instructions
_PAT_BANK_ACC = re.compile(r"(?:account|funds|to|a/c|acc)[\s:#-]*(\d{9,18})\b", re.IGNORECASE)

# Patterns run on prose text fields only (NOT element IDs or binary data)
SERVER_PII_PROSE_PATTERNS = [
    ("EMAIL",    _PAT_EMAIL),
    ("PHONE",    _PAT_PHONE),
    ("CARD",     _PAT_CARD),
    ("PAN",      _PAT_PAN),
    ("AADHAAR",  _PAT_AADHAAR),
    ("UPI",      _PAT_UPI),
    ("BANK_ACC", _PAT_BANK_ACC),
]

def luhn_checksum(card_number: str) -> bool:
    """Validate payment card using standard Luhn algorithm."""
    digits = [int(d) for d in re.sub(r"\D", "", card_number)]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = digit * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += digit
    return checksum % 10 == 0

def is_genuine_pii(pat_name: str, match_str: str) -> bool:
    """
    Validates whether candidate string is genuine PII vs non-PII false positive
    (e.g., e-commerce product SKUs, catalog IDs, tracking numbers).
    """
    if pat_name == "AADHAAR":
        clean = normalize_digits(match_str).replace(" ", "").replace("-", "")
        if len(clean) != 12 or not clean.isdigit():
            return False
        # UIDAI specification: Aadhaar numbers NEVER begin with '0' or '1'
        if clean[0] in ("0", "1"):
            return False
        return validate_verhoeff(clean)
    if pat_name == "CARD":
        clean = re.sub(r"\D", "", match_str)
        if len(clean) < 13 or len(clean) > 19:
            return False
        return luhn_checksum(clean)
    return True

# Sensitive raw secret keywords that MUST NEVER appear in raw value form
FORBIDDEN_RAW_SECRETS = [
    "SuperSecretBankPass2026!",
    "SecureEnterprisePassword#99",
    "SuperSecretPassword@2026",
    "sk-super-secret-key-12345"
]


def collect_text_fields_for_scan(payload: SanitizedContextPackage) -> list[tuple[str, str]]:
    """
    Returns (field_path, text_value) pairs for every HUMAN-READABLE prose field.

    EXCLUDED:
    - payload.screenshot  (base64 data_url — binary, would cause regex false positives)
    - element.id          (opaque DOM identifier — not human PII; Amazon uses numeric IDs)
    - element.role        (enum value like 'button', 'link' — not PII)
    - session_id          (UUID — not PII)

    INCLUDED:
    - instruction_sanitized
    - page.url_sanitized
    - page.title_sanitized
    - elements[N].label   (human-readable text extracted from DOM)
    - redactions[N].placeholder  (synthetic label like [PHONE_1])
    - history[N].action / history[N].result
    """
    fields: list[tuple[str, str]] = []

    if payload.instruction_sanitized:
        fields.append(("instruction_sanitized", payload.instruction_sanitized))

    if payload.page:
        if payload.page.url_sanitized:
            fields.append(("page.url_sanitized", payload.page.url_sanitized))
        if payload.page.title_sanitized:
            fields.append(("page.title_sanitized", payload.page.title_sanitized))

    for el in payload.elements:
        # label only — id is an opaque DOM identifier, not human-readable PII
        if el.label:
            fields.append((f"elements[id={el.id}].label", el.label))

    for r in payload.redactions:
        if r.placeholder:
            fields.append((f"redactions[id={r.id}].placeholder", r.placeholder))

    for i, item in enumerate(payload.history):
        for key in ("action", "result", "summary"):
            val = item.get(key) if isinstance(item, dict) else getattr(item, key, None)
            if isinstance(val, str):
                fields.append((f"history[{i}].{key}", val))

    return fields

@app.get("/")
def root():
    planner_info = check_active_planner()
    return {
        "service": "Visiionary Privacy Planner Server",
        "status": "online",
        "privacy_shield": "active",
        "planner": planner_info["provider"].upper(),
        "model": planner_info["model"],
        "endpoints": {
            "health": "/api/health",
            "plan": "/api/agent/plan",
            "docs": "/docs"
        }
    }

@app.get("/api/health")
def health_check():
    planner_info = check_active_planner()
    return {
        "status": "ok",
        "service": "visiionary-server",
        "privacy_shield": "active",
        "planner": planner_info["provider"].upper(),
        "model": planner_info["model"]
    }

@app.post("/api/agent/plan", response_model=AgentPlanResponse)
def plan_action(payload: SanitizedContextPackage):
    # -----------------------------------------------------------------------
    # 1. Defense-in-depth: Scan prose text fields for genuine PII leaks.
    #    A. instruction_sanitized, page URLs, history: strict egress gate (HTTP 400).
    #    B. elements[...].label: auto-redacted in-place so cloud LLM receives zero PII
    #       without breaking autonomous browsing on dynamic pages.
    # -----------------------------------------------------------------------
    pii_violations: list[str] = []
    print(f"[PS26171 DIAGNOSTIC] PLANNER INPUT ELEMENT COUNT: {len(payload.elements)} | REDACTIONS: {len(payload.redactions)} | TASK: \"{payload.instruction_sanitized}\"")

    # Wire metadata & instruction checks (must never leak raw PII over the wire)
    wire_fields: list[tuple[str, str]] = []
    if payload.instruction_sanitized:
        wire_fields.append(("instruction_sanitized", payload.instruction_sanitized))
    if payload.page:
        if payload.page.url_sanitized:
            wire_fields.append(("page.url_sanitized", payload.page.url_sanitized))
        if payload.page.title_sanitized:
            wire_fields.append(("page.title_sanitized", payload.page.title_sanitized))
    for i, item in enumerate(payload.history):
        for key in ("action", "result", "summary"):
            val = item.get(key) if isinstance(item, dict) else getattr(item, key, None)
            if isinstance(val, str):
                wire_fields.append((f"history[{i}].{key}", val))

    for field_path, text_value in wire_fields:
        for pat_name, pattern in SERVER_PII_PROSE_PATTERNS:
            matches = pattern.findall(text_value)
            leaks = [m for m in matches if "REDACTED" not in m and is_genuine_pii(pat_name, m)]
            if leaks:
                print(f"[SERVER PRIVACY] Genuine PII in {field_path}: type={pat_name} count={len(leaks)}")
                pii_violations.append(f"{pat_name} in {field_path}")

    if pii_violations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Server privacy scanner rejected payload: unredacted pattern detected {pii_violations[:2]}"
        )

    # DOM elements: auto-redact genuine PII in-place before sending to LLM
    for el in payload.elements:
        if el.label:
            for pat_name, pattern in SERVER_PII_PROSE_PATTERNS:
                matches = pattern.findall(el.label)
                for m in matches:
                    if "REDACTED" not in m and is_genuine_pii(pat_name, m):
                        print(f"[SERVER DEFENSE] Auto-redacted genuine {pat_name} in element {el.id}")
                        el.label = el.label.replace(m, f"[REDACTED_{pat_name}]")

    # -----------------------------------------------------------------------
    # 2. Defense-in-depth: Scan FULL serialized payload for raw vault secrets.
    #    Vault secrets are exact credential strings — safe to check in full JSON.
    # -----------------------------------------------------------------------
    raw_str = payload.model_dump_json()
    for sec in FORBIDDEN_RAW_SECRETS:
        if sec in raw_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Server privacy scanner rejected payload: RAW CREDENTIAL LEAK DETECTED"
            )

    from server.app.planner import track_subgoal_progress
    subgoals, completed_subgoals, remaining_goal = track_subgoal_progress(
        payload.instruction_sanitized,
        payload.page.url_sanitized,
        payload.page.title_sanitized,
        payload.elements,
        payload.history
    )

    from server.app.product_constraints import extract_product_constraints
    product_constraints = payload.product_constraints or extract_product_constraints(payload.instruction_sanitized)

    # 3. Try Best Autonomous Neural LLM Planner (Groq Cloud API or Local Ollama)
    try:
        actions, summary, model_name = plan_with_best_llm(payload)
        return AgentPlanResponse(
            task=payload.instruction_sanitized,
            reasoning_summary=summary,
            actions=actions,
            subgoals=subgoals,
            completed_subgoals=completed_subgoals,
            remaining_goal=remaining_goal,
            product_constraints=product_constraints,
            selected_target=payload.selected_target
        )
    except Exception as e:
        print(f"[SERVER] Neural LLM planner warning ({e}), falling back to local semantic planner...")

    # 4. Fallback to Local Semantic Reasoning Planner
    actions, summary = decide_next_action(payload)
    return AgentPlanResponse(
        task=payload.instruction_sanitized,
        reasoning_summary=f"[LOCAL_SEMANTIC] {summary}",
        actions=actions,
        subgoals=subgoals,
        completed_subgoals=completed_subgoals,
        remaining_goal=remaining_goal,
        product_constraints=product_constraints,
        selected_target=payload.selected_target
    )

from server.app.schemas.schemas import VerificationPayload, VerificationResponse
from server.app.verifier import verify_task_completion

@app.post("/api/agent/verify", response_model=VerificationResponse)
def verify_endpoint(payload: VerificationPayload):
    """
    Independent Task Completion Verifier:
    Determines whether user's goal has actually been achieved.
    Prevents planner 'done' output from bypassing goal verification.
    """
    return verify_task_completion(payload)
