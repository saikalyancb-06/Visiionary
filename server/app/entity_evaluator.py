"""
Explicit 3-Valued Logic Evaluator & Candidate Selection Engine.

Evaluates candidates strictly using:
- SATISFIED
- NOT_SATISFIED
- UNKNOWN

Never collapses UNKNOWN into FALSE or TRUE.
Enforces:
1. Hard constraint verification (rejects immediately if NOT_SATISFIED; flags UNKNOWN for exploration)
2. Empirical selection criteria verification (requires proven badges/evidence)
3. Target Identity preservation across page transitions
"""

from typing import Dict, Any, Tuple, List, Optional
from server.app.task_model import GeneralTaskModel
from server.app.entity_model import SemanticEntity, ENTITY_DESTINATION

# 3-Valued Truth States
STATE_SATISFIED = "SATISFIED"
STATE_NOT_SATISFIED = "NOT_SATISFIED"
STATE_UNKNOWN = "UNKNOWN"

def evaluate_candidate_constraints(
    entity: SemanticEntity,
    task_model: GeneralTaskModel
) -> Tuple[str, Dict[str, str], str]:
    """
    Evaluates an entity against the task model's hard constraints.
    Returns:
      (OVERALL_STATE, per_attribute_evaluations, reason_description)
    """
    attr_results: Dict[str, str] = {}
    entity_text = f"{entity.title} {entity.visible_text}".lower()
    
    # Check each hard constraint
    for key, req_val in task_model.hard_constraints.items():
        if not req_val:
            continue
        req_str = str(req_val).lower().strip()
        
        # Check if attribute is known from entity attributes dict
        obs_val = entity.attributes.get(key)
        if obs_val:
            obs_str = str(obs_val).lower().strip()
            if req_str == obs_str or req_str in obs_str:
                attr_results[key] = STATE_SATISFIED
            else:
                attr_results[key] = STATE_NOT_SATISFIED
        elif req_str in entity_text:
            attr_results[key] = STATE_SATISFIED
        else:
            # Crucial: If not visible in summary card, it is UNKNOWN, NOT necessarily FALSE!
            attr_results[key] = STATE_UNKNOWN

    # Evaluate overall hard constraint status
    if any(res == STATE_NOT_SATISFIED for res in attr_results.values()):
        return STATE_NOT_SATISFIED, attr_results, "Candidate directly violates hard constraints."
    
    if any(res == STATE_UNKNOWN for res in attr_results.values()):
        missing_keys = [k for k, v in attr_results.items() if v == STATE_UNKNOWN]
        return STATE_UNKNOWN, attr_results, f"Missing observable attributes on current card: {missing_keys}"

    return STATE_SATISFIED, attr_results, "All hard constraints verified SATISFIED."


def evaluate_selection_criterion(
    entity: SemanticEntity,
    task_model: GeneralTaskModel
) -> Tuple[bool, str]:
    """
    Verifies if candidate possesses verified empirical evidence for requested comparative/superlative.
    Zero speculation or arbitrary default selection.
    """
    crit = task_model.selection_criterion
    if not crit:
        return True, "No comparative/superlative selection criterion required."

    # Empirical check
    crit_lower = (task_model.selection_criterion_label or "").lower()
    if any(crit_lower in b.lower() for b in entity.badges):
        return True, f"Verified observable badge: '{crit_lower}'"
    if entity.selection_evidence:
        return True, "; ".join(entity.selection_evidence)

    return False, f"Selection criterion '{crit_lower}' has NO observable evidence on candidate card."


def verify_target_identity_match(
    selected_target: Dict[str, Any],
    current_entity: SemanticEntity
) -> Tuple[bool, str]:
    """
    Preserves Target Identity across navigation.
    Reconstructs entity from new page and compares against previously selected target.
    Prevents acting on wrong pages.
    """
    if not selected_target:
        return True, "No target previously selected."

    sel_title = (selected_target.get("title") or "").lower()
    curr_title = (current_entity.title or "").lower()
    curr_text = (current_entity.visible_text or "").lower()

    if not sel_title:
        return True, "Selected target had no title constraint."

    # Check title/token overlap
    sel_tokens = [w for w in sel_title.split() if len(w) > 2]
    matched = sum(1 for w in sel_tokens if w in curr_title or w in curr_text)
    
    if len(sel_tokens) > 0 and (matched / len(sel_tokens)) >= 0.5:
        return True, "Target identity verified on current page."

    return False, f"TARGET_MISMATCH: Current page focal entity '{curr_title[:40]}' does not match selected target '{sel_title[:40]}'."
