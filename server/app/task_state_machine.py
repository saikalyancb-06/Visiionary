"""
Dependency-Aware Task State Machine for Visiionary Autonomous Browser Agent.

Implements an explicit ordered dependency graph for arbitrary browser tasks:

  DISCOVER -> SEARCH -> EXTRACT_ENTITIES -> ACCUMULATE_CANDIDATES
  -> COMPARE -> SELECT_TARGET -> OPEN_TARGET
  -> VERIFY_TARGET_PAGE -> EXTRACT_INFORMATION -> GOAL_ACHIEVED

Every phase has explicit prerequisite predicates.
The planner may only dispatch actions whose phase prerequisites are satisfied.
Violations are blocked and emitted as PLANNER_BLOCKED diagnostics.

Zero website/domain/URL/product hardcoding.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Task Phase Constants
# ---------------------------------------------------------------------------
PHASE_DISCOVER           = "DISCOVER"
PHASE_SEARCH             = "SEARCH"
PHASE_EXTRACT_ENTITIES   = "EXTRACT_ENTITIES"
PHASE_ACCUMULATE         = "ACCUMULATE_CANDIDATES"
PHASE_COMPARE            = "COMPARE"
PHASE_SELECT_TARGET      = "SELECT_TARGET"
PHASE_OPEN_TARGET        = "OPEN_TARGET"
PHASE_VERIFY_TARGET_PAGE = "VERIFY_TARGET_PAGE"
PHASE_EXTRACT_INFORMATION= "EXTRACT_INFORMATION"
PHASE_GOAL_ACHIEVED      = "GOAL_ACHIEVED"

_PHASE_ORDER = [
    PHASE_DISCOVER, PHASE_SEARCH, PHASE_EXTRACT_ENTITIES, PHASE_ACCUMULATE,
    PHASE_COMPARE, PHASE_SELECT_TARGET, PHASE_OPEN_TARGET,
    PHASE_VERIFY_TARGET_PAGE, PHASE_EXTRACT_INFORMATION, PHASE_GOAL_ACHIEVED,
]

def _phase_rank(phase: str) -> int:
    try:
        return _PHASE_ORDER.index(phase)
    except ValueError:
        return -1

def phase_gte(a: str, b: str) -> bool:
    return _phase_rank(a) >= _phase_rank(b)


# ---------------------------------------------------------------------------
# TaskExecutionState
# ---------------------------------------------------------------------------
@dataclass
class TaskExecutionState:
    phase: str = PHASE_DISCOVER
    verified_candidates: List[Dict[str, Any]] = field(default_factory=list)
    selected_target: Optional[Dict[str, Any]] = None
    required_candidate_count: int = 1
    requires_comparison: bool = False
    requires_information_extraction: bool = False
    information_fields_requested: List[str] = field(default_factory=list)
    information_extracted: Optional[Dict[str, Any]] = None
    target_page_verified: bool = False
    blocked_transitions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "verified_candidates": self.verified_candidates,
            "selected_target": self.selected_target,
            "required_candidate_count": self.required_candidate_count,
            "requires_comparison": self.requires_comparison,
            "requires_information_extraction": self.requires_information_extraction,
            "information_fields_requested": self.information_fields_requested,
            "information_extracted": self.information_extracted,
            "target_page_verified": self.target_page_verified,
            "blocked_transitions": self.blocked_transitions,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TaskExecutionState":
        if not d:
            return cls()
        return cls(
            phase=d.get("phase", PHASE_DISCOVER),
            verified_candidates=d.get("verified_candidates", []),
            selected_target=d.get("selected_target"),
            required_candidate_count=d.get("required_candidate_count", 1),
            requires_comparison=d.get("requires_comparison", False),
            requires_information_extraction=d.get("requires_information_extraction", False),
            information_fields_requested=d.get("information_fields_requested", []),
            information_extracted=d.get("information_extracted"),
            target_page_verified=d.get("target_page_verified", False),
            blocked_transitions=d.get("blocked_transitions", []),
        )


# ---------------------------------------------------------------------------
# Task Requirement Extraction
# ---------------------------------------------------------------------------
_WORD_TO_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

_COUNT_PATTERNS = [
    re.compile(r'(?:at\s+least|compare|top|best)\s+(\d+)', re.I),
    re.compile(r'(?:at\s+least|compare|top|best)\s+(' + '|'.join(_WORD_TO_NUM.keys()) + r')\b', re.I),
    re.compile(r'(\d+)\s+(?:matching|different|products?|items?|results?|options?|candidates?)', re.I),
    re.compile(r'(' + '|'.join(_WORD_TO_NUM.keys()) + r')\s+(?:matching|different|products?|items?|results?|options?|candidates?)', re.I),
]

_COMPARE_PATTERN  = re.compile(r'\bcompar\w*\b', re.I)
_INFO_TRIGGER     = re.compile(r'\b(report|extract|tell\s+me|list|show\s+me|output|give\s+me|provide)\b', re.I)
_FIELD_SEPARATORS = re.compile(r'[,;]|\band\b', re.I)


def parse_task_requirements(task: str) -> Dict[str, Any]:
    t = (task or "").strip()

    required_count = 1
    for pat in _COUNT_PATTERNS:
        m = pat.search(t)
        if m:
            raw = m.group(1)
            if raw.isdigit():
                required_count = max(required_count, int(raw))
            else:
                required_count = max(required_count, _WORD_TO_NUM.get(raw.lower(), 1))
            break

    requires_comparison = bool(_COMPARE_PATTERN.search(t))
    if requires_comparison:
        required_count = max(required_count, 2)

    requires_info = bool(_INFO_TRIGGER.search(t))
    info_fields: List[str] = []
    if requires_info:
        m_info = _INFO_TRIGGER.search(t)
        if m_info:
            after = t[m_info.end():].strip()
            after = re.sub(r'^(the|a|an|its|their|this|that)\s+', '', after, flags=re.I)
            after = re.split(r'\.\s+[A-Z]|and\s+(?:then|also|additionally|finally)\b', after)[0]
            for rf in _FIELD_SEPARATORS.split(after):
                cleaned = rf.strip().rstrip('.')
                tokens = cleaned.split()
                if 1 <= len(tokens) <= 6:
                    info_fields.append(cleaned)

    return {
        "required_candidate_count": required_count,
        "requires_comparison": requires_comparison,
        "requires_information_extraction": requires_info,
        "information_fields_requested": info_fields,
    }


# ---------------------------------------------------------------------------
# State Reconstruction & Persistence
# ---------------------------------------------------------------------------
def reconstruct_state(
    payload_verification_state: Optional[Dict[str, Any]],
    payload_selected_target: Optional[Dict[str, Any]],
    payload_task_execution_state: Optional[Dict[str, Any]] = None,
) -> TaskExecutionState:
    raw: Optional[Dict[str, Any]] = payload_task_execution_state
    if not raw and payload_verification_state:
        raw = payload_verification_state.get("task_execution_state")

    if raw:
        state = TaskExecutionState.from_dict(raw)
        if payload_selected_target and not state.selected_target:
            state.selected_target = payload_selected_target
        return state

    state = TaskExecutionState()
    if payload_selected_target:
        state.selected_target = payload_selected_target
        state.phase = PHASE_SELECT_TARGET
    return state


def save_state(state: TaskExecutionState, payload: Any) -> None:
    if payload.verification_state is None:
        payload.verification_state = {}
    payload.verification_state["task_execution_state"] = state.to_dict()


# ---------------------------------------------------------------------------
# Prerequisite Predicates
# ---------------------------------------------------------------------------
def evaluate_phase_prerequisites(
    phase: str,
    state: TaskExecutionState,
) -> Tuple[bool, List[str]]:
    missing: List[str] = []

    if phase == PHASE_COMPARE:
        have, need = len(state.verified_candidates), state.required_candidate_count
        if have < need:
            missing.append(f"sufficient_verified_candidates: have {have}, need {need}")

    elif phase == PHASE_SELECT_TARGET:
        if len(state.verified_candidates) < 1:
            missing.append("at_least_one_candidate: verified_candidates is empty")
        if state.requires_comparison:
            have, need = len(state.verified_candidates), state.required_candidate_count
            if have < need:
                missing.append(f"comparison_complete: have only {have}/{need} verified candidates")

    elif phase == PHASE_OPEN_TARGET:
        if not state.selected_target:
            missing.append(
                "selected_target_exists: no target has been selected yet"
            )
        # Note: we do NOT require href here. The planner decides whether to use
        # open_link (for URL hrefs) or click (for in-page elements).
        # The state machine's role is only to ensure an entity was selected.

    elif phase == PHASE_VERIFY_TARGET_PAGE:
        if not phase_gte(state.phase, PHASE_OPEN_TARGET):
            missing.append("open_target_dispatched: OPEN_TARGET has not been dispatched yet")

    elif phase == PHASE_EXTRACT_INFORMATION:
        if not state.target_page_verified:
            missing.append("target_page_verified: target page identity has not been confirmed")

    elif phase == PHASE_GOAL_ACHIEVED:
        if state.requires_information_extraction and not state.information_extracted:
            missing.append("information_extracted: required information fields have not been extracted")
        if state.requires_comparison and not state.selected_target:
            missing.append("comparison_and_selection_done: not completed")

    return (len(missing) == 0), missing


# ---------------------------------------------------------------------------
# Legal Transition Computation
# ---------------------------------------------------------------------------
def get_legal_transitions(
    state: TaskExecutionState,
    task_requirements: Optional[Dict[str, Any]] = None,
) -> List[str]:
    legal: List[str] = [PHASE_DISCOVER, PHASE_SEARCH, PHASE_EXTRACT_ENTITIES, PHASE_ACCUMULATE]

    ok_compare, _ = evaluate_phase_prerequisites(PHASE_COMPARE, state)
    if ok_compare:
        legal.append(PHASE_COMPARE)

    ok_select, _ = evaluate_phase_prerequisites(PHASE_SELECT_TARGET, state)
    if ok_select:
        legal.append(PHASE_SELECT_TARGET)

    ok_open, _ = evaluate_phase_prerequisites(PHASE_OPEN_TARGET, state)
    if ok_open:
        legal.append(PHASE_OPEN_TARGET)

    ok_verify, _ = evaluate_phase_prerequisites(PHASE_VERIFY_TARGET_PAGE, state)
    if ok_verify:
        legal.append(PHASE_VERIFY_TARGET_PAGE)

    ok_extract, _ = evaluate_phase_prerequisites(PHASE_EXTRACT_INFORMATION, state)
    if ok_extract:
        legal.append(PHASE_EXTRACT_INFORMATION)

    ok_goal, _ = evaluate_phase_prerequisites(PHASE_GOAL_ACHIEVED, state)
    if ok_goal:
        legal.append(PHASE_GOAL_ACHIEVED)

    return legal


# ---------------------------------------------------------------------------
# PLANNER_BLOCKED Diagnostic
# ---------------------------------------------------------------------------
def get_blocked_diagnostic(requested_phase: str, state: TaskExecutionState) -> str:
    _, missing = evaluate_phase_prerequisites(requested_phase, state)
    legal = get_legal_transitions(state)
    lines = [
        "[PLANNER BLOCKED]",
        f"  Requested transition : {requested_phase}",
        f"  Current phase        : {state.phase}",
        "  Missing prerequisites:",
    ]
    for m in missing:
        lines.append(f"    - {m}")
    lines += [
        f"  Current legal transitions: {legal}",
        f"  verified_candidates  : {len(state.verified_candidates)}/{state.required_candidate_count}",
        f"  selected_target      : {'SET' if state.selected_target else 'NONE'}",
        f"  target_page_verified : {state.target_page_verified}",
        f"  requires_comparison  : {state.requires_comparison}",
    ]
    return "\n".join(lines)
