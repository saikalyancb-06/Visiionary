"""
Updated Server Planner to support diverse actions across all synthetic demo portals
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

SERVER_PII_PATTERNS = [
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
]

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "ps26171-server", "privacy_shield": "active"}

@app.post("/api/agent/plan", response_model=AgentPlanResponse)
def plan_action(payload: SanitizedContextPackage):
    raw_str = payload.model_dump_json()
    for pattern in SERVER_PII_PATTERNS:
        matches = pattern.findall(raw_str)
        leaks = [m for m in matches if "REDACTED" not in m]
        if leaks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Server privacy scanner rejected payload: unredacted pattern detected {leaks[:2]}"
            )

    task_lower = payload.instruction_sanitized.lower()
    actions = []
    summary = ""

    # Match target interactable element
    target_el = None
    for el in payload.elements:
        if el.interactable and (el.label.lower() in task_lower or any(w in el.label.lower() for w in ["download", "cart", "verify", "statement"])):
            target_el = el
            break

    if target_el:
        actions.append(BrowserAction(
            type="click",
            target=ActionTarget(element_id=target_el.id)
        ))
        actions.append(BrowserAction(
            type="wait",
            milliseconds=1000
        ))
        summary = f"Located interactable target element '{target_el.label}' (id={target_el.id}). Dispatched validated click."
    else:
        # Default to first element if provided
        if payload.elements:
            first = payload.elements[0]
            actions.append(BrowserAction(
                type="click",
                target=ActionTarget(element_id=first.id)
            ))
            summary = f"Selected candidate element '{first.label}' (id={first.id})."
        else:
            actions.append(BrowserAction(type="done"))
            summary = "Task complete."

    return AgentPlanResponse(
        task=payload.instruction_sanitized,
        reasoning_summary=summary,
        actions=actions
    )
