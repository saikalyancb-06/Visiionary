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
    href: Optional[str] = None

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
    screen_summary: Optional[Dict[str, Any]] = None

class SanitizedContextPackage(BaseModel):
    session_id: str
    step: int
    instruction_sanitized: str
    page: PageContext
    screenshot: Optional[Dict[str, Any]] = None
    elements: List[ElementMetadata] = Field(default_factory=list)
    redactions: List[RedactionMetadata] = Field(default_factory=list)
    privacy_report: PrivacyReport
    metrics: Optional[Dict[str, Any]] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)
    verification_state: Optional[Dict[str, Any]] = None

class ActionTarget(BaseModel):
    element_id: Optional[str] = None
    xpath: Optional[str] = None

class ActionValue(BaseModel):
    text: Optional[str] = None
    secret_ref: Optional[str] = None

class BrowserAction(BaseModel):
    type: str  # click, type, scroll, select, navigate, wait, done, ask_user, download, go_back, go_forward, search
    target: Optional[ActionTarget] = None
    value: Optional[ActionValue] = None
    milliseconds: Optional[int] = None
    url: Optional[str] = None
    option: Optional[str] = None
    direction: Optional[str] = None
    amount: Optional[int] = None
    question: Optional[str] = None

class AgentPlanResponse(BaseModel):
    task: str
    reasoning_summary: str
    actions: List[BrowserAction]
    subgoals: List[str] = Field(default_factory=list)
    completed_subgoals: List[str] = Field(default_factory=list)
    remaining_goal: str = ""

class DownloadItem(BaseModel):
    id: Optional[int] = None
    filename: Optional[str] = None
    url: Optional[str] = None
    state: Optional[str] = None
    file_size: Optional[int] = None

class VerificationPayload(BaseModel):
    task: str
    current_url: str
    page_title: str
    screen_summary: Optional[Dict[str, Any]] = None
    action_history: List[Dict[str, Any]] = Field(default_factory=list)
    downloads: List[DownloadItem] = Field(default_factory=list)
    last_action: Optional[Dict[str, Any]] = None

class VerificationResponse(BaseModel):
    achieved: bool
    confidence: float
    reason: str
    next_hint: Optional[str] = None
    requires_recovery: bool = False
    goal_status: str = "GOAL_NOT_YET_ACHIEVED"  # ACTION_SUCCESS | GOAL_NOT_YET_ACHIEVED | GOAL_ACHIEVED | ACTION_FAILED | RECOVERY_REQUIRED
    subgoals: List[str] = Field(default_factory=list)
    completed_subgoals: List[str] = Field(default_factory=list)
    remaining_goal: str = ""
