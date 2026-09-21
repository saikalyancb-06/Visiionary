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

# Comprehensive Defense-in-depth Server PII Scanner (Fail-Closed)
SERVER_PII_PATTERNS = [
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    re.compile(r"(?:\+91[\-\s]?)?[6789]\d{4}[\-\s]?\d{5}"),
    re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b"),
    re.compile(r"\b\d{4}[\-\s]?\d{4}[\-\s]?\d{4}\b"),
    re.compile(r"\b\d{9,18}\b"),
    re.compile(r"[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}")
]

# Sensitive raw secret keywords that MUST NEVER appear in raw value form
FORBIDDEN_RAW_SECRETS = [
    "SuperSecretBankPass2026!",
    "SecureEnterprisePassword#99",
    "SuperSecretPassword@2026",
    "sk-super-secret-key-12345"
]

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
    raw_str = payload.model_dump_json()

    # 1. Defense-in-depth: Reject any unredacted PII patterns
    for pattern in SERVER_PII_PATTERNS:
        matches = pattern.findall(raw_str)
        leaks = [m for m in matches if "REDACTED" not in m]
        if leaks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Server privacy scanner rejected payload: unredacted pattern detected {leaks[:2]}"
            )

    # 2. Defense-in-depth: Reject any leaked raw secret credentials
    for sec in FORBIDDEN_RAW_SECRETS:
        if sec in raw_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Server privacy scanner rejected payload: RAW CREDENTIAL LEAK DETECTED"
            )

    # 3. Try Local Ollama LLM first (Priority 1)
    ollama_info = check_ollama_status()
    if ollama_info["available"]:
        try:
            actions, summary, model_name = plan_with_local_llm(payload)
            return AgentPlanResponse(
                task=payload.instruction_sanitized,
                reasoning_summary=summary,
                actions=actions
            )
        except Exception as e:
            print(f"[SERVER] Local Ollama call warning ({e}), falling back to local semantic planner...")

    # 4. Fallback to Local Semantic Reasoning Planner
    actions, summary = decide_next_action(payload)
    return AgentPlanResponse(
        task=payload.instruction_sanitized,
        reasoning_summary=f"[LOCAL_SEMANTIC] {summary}",
        actions=actions
    )
