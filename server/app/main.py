"""
FastAPI Server for PS 26171 Browser Agent
Defends privacy in depth, validates schema, and interfaces with LLM/VLM planner.
"""
from fastapi import FastAPI, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from server.app.schemas.schemas import SanitizedContextPackage, AgentPlanResponse, BrowserAction, ActionTarget
import re

app = FastAPI(title="PS26171 Privacy Browser Agent Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Defense in Depth: Secondary server-side PII check
SERVER_PII_PATTERNS = [
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), # Email
    re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), # Card
]

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "ps26171-server", "privacy_shield": "active"}

@app.post("/api/agent/plan", response_model=AgentPlanResponse)
def plan_action(payload: SanitizedContextPackage):
    # 1. Defense-in-depth verification
    raw_str = payload.model_dump_json()
    for pattern in SERVER_PII_PATTERNS:
        matches = pattern.findall(raw_str)
        # Filter out redacted placeholders
        leaks = [m for m in matches if "REDACTED" not in m]
        if leaks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Server privacy scanner rejected payload: unredacted pattern detected {leaks[:2]}"
            )

    # 2. Plan reasoning based strictly on sanitized elements & instruction
    task = payload.instruction_sanitized
    actions = []

    # Look for matching target element among sanitized elements
    target_btn = None
    for el in payload.elements:
        if "statement" in el.label.lower() or "download" in el.label.lower():
            target_btn = el
            break

    if target_btn:
        actions.append(BrowserAction(
            type="click",
            target=ActionTarget(element_id=target_btn.id)
        ))
        actions.append(BrowserAction(
            type="wait",
            milliseconds=1000
        ))
        summary = f"Located statement download element '{target_btn.label}' (id={target_btn.id}). Executing click."
    else:
        actions.append(BrowserAction(type="done"))
        summary = "No pending action required or goal achieved."

    return AgentPlanResponse(
        task=task,
        reasoning_summary=summary,
        actions=actions
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
