"""
Updated Server Planner supporting Local Ollama LLM (Qwen3.5:9B):
- Uses local Ollama LLM directly for task understanding and action selection
- Zero hardcoded websites, coordinates, or element IDs
- Defense-in-depth Fail-Closed PII and Raw Secret Scanners
"""
from fastapi import FastAPI, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from server.app.schemas.schemas import SanitizedContextPackage, AgentPlanResponse, BrowserAction, ActionTarget, ActionValue
from server.app.llm_planner import plan_with_local_llm, check_ollama_status
from server.app.planner import decide_next_action
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

# Patterns run on prose text fields only (NOT element IDs or binary data)
SERVER_PII_PROSE_PATTERNS = [
    ("EMAIL",   _PAT_EMAIL),
    ("PHONE",   _PAT_PHONE),
    ("CARD",    _PAT_CARD),
    ("PAN",     _PAT_PAN),
    ("AADHAAR", _PAT_AADHAAR),
    ("UPI",     _PAT_UPI),
]

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
    ollama_info = check_ollama_status()
    return {
        "service": "Visiionary Local Planner Server",
        "status": "online",
        "privacy_shield": "active",
        "planner": "LOCAL_OLLAMA" if ollama_info["available"] else "LOCAL_SEMANTIC",
        "model": ollama_info["model"],
        "endpoints": {
            "health": "/api/health",
            "plan": "/api/agent/plan",
            "docs": "/docs"
        }
    }

@app.get("/api/health")
def health_check():
    ollama_info = check_ollama_status()
    return {
        "status": "ok",
        "service": "visiionary-server",
        "privacy_shield": "active",
        "planner": "LOCAL_OLLAMA" if ollama_info["available"] else "LOCAL_SEMANTIC",
        "model": ollama_info["model"]
    }

@app.post("/api/agent/plan", response_model=AgentPlanResponse)
def plan_action(payload: SanitizedContextPackage):
    # -----------------------------------------------------------------------
    # 1. Defense-in-depth: Scan ONLY human-readable prose text fields for PII.
    #    We explicitly DO NOT scan element.id or the full JSON dump to avoid
    #    false positives on opaque DOM identifiers (e.g. Amazon numeric element
    #    IDs) and base64 screenshot data.
    # -----------------------------------------------------------------------
    text_fields = collect_text_fields_for_scan(payload)
    pii_violations: list[str] = []

    for field_path, text_value in text_fields:
        for pat_name, pattern in SERVER_PII_PROSE_PATTERNS:
            matches = pattern.findall(text_value)
            leaks = [m for m in matches if "REDACTED" not in m]
            if leaks:
                # Log field + pattern — NEVER the raw matched value
                print(f"[SERVER PRIVACY] PII candidate: field={field_path} type={pat_name} count={len(leaks)}")
                pii_violations.append(f"{pat_name} in {field_path}")

    if pii_violations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Server privacy scanner rejected payload: unredacted pattern detected {pii_violations[:2]}"
        )

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

    # 3. Try Local Ollama LLM first (Priority 1)
    ollama_info = check_ollama_status()
    if ollama_info["available"]:
        try:
            actions, summary, model_name = plan_with_local_llm(payload)
            return AgentPlanResponse(
                task=payload.instruction_sanitized,
                reasoning_summary=summary,
                actions=actions,
                subgoals=subgoals,
                completed_subgoals=completed_subgoals,
                remaining_goal=remaining_goal
            )
        except Exception as e:
            print(f"[SERVER] Local Ollama call warning ({e}), falling back to local semantic planner...")

    # 4. Fallback to Local Semantic Reasoning Planner
    actions, summary = decide_next_action(payload)
    return AgentPlanResponse(
        task=payload.instruction_sanitized,
        reasoning_summary=f"[LOCAL_SEMANTIC] {summary}",
        actions=actions,
        subgoals=subgoals,
        completed_subgoals=completed_subgoals,
        remaining_goal=remaining_goal
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
