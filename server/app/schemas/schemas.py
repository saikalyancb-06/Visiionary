from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class BoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int

class ElementMetadata(BaseModel):
    id: str
    role: str
    label: str
    bbox: List[int]
    interactable: bool = True
    sensitivity: str = "safe"
    source: str = "dom+vision"
    confidence: float = 1.0

class RedactionMetadata(BaseModel):
    id: str
    type: str
    placeholder: str
    bbox: List[int]

class PrivacyReport(BaseModel):
    detected: int
    sensitive: int
    redacted: int
    uncertain_redacted: int = 0
    verification: str = "PASS"
    gate: str = "PASS"

class PageContext(BaseModel):
    url_sanitized: str
    title_sanitized: str
    viewport: Dict[str, Any]

class SanitizedContextPackage(BaseModel):
    session_id: str
    step: int
    instruction_sanitized: str
    page: PageContext
    screenshot: Optional[Dict[str, Any]] = None
    elements: List[ElementMetadata] = Field(default_factory=list)
    redactions: List[RedactionMetadata] = Field(default_factory=list)
    privacy_report: PrivacyReport
    history: List[Dict[str, Any]] = Field(default_factory=list)

class ActionTarget(BaseModel):
    element_id: Optional[str] = None
    xpath: Optional[str] = None

class ActionValue(BaseModel):
    text: Optional[str] = None
    secret_ref: Optional[str] = None

class BrowserAction(BaseModel):
    type: str  # click, type, scroll, select, navigate, keypress, wait, done, ask_user
    target: Optional[ActionTarget] = None
    value: Optional[ActionValue] = None
    milliseconds: Optional[int] = None
    url: Optional[str] = None

class AgentPlanResponse(BaseModel):
    task: str
    reasoning_summary: str
    actions: List[BrowserAction]
