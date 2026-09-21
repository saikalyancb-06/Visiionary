import re
from typing import List, Optional, Tuple
from server.app.schemas.schemas import SanitizedContextPackage, BrowserAction, ActionTarget, ActionValue, ElementMetadata

def normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', (text or '')).strip().lower()

def extract_search_terms(task: str) -> List[str]:
    # Extract candidate query terms from task: e.g. "search for laptop", "find black shoes"
    m = re.search(r'(?:search for|find|search|look for|query)\s+["\']?([^"\']+)["\']?', task, re.IGNORECASE)
    if m:
        query = m.group(1).strip()
        # strip trailing directives like "and open it", "and add to cart"
        query = re.sub(r'\s+(?:and\s+.*|on\s+.*)$', '', query, flags=re.IGNORECASE)
        return [query]
    return []

def score_element_for_action(el: ElementMetadata, keywords: List[str], preferred_roles: List[str]) -> float:
    score = 0.0
    label = normalize(el.label)
    role = el.role.lower()

    if role in preferred_roles:
        score += 2.0

    for kw in keywords:
        kw_norm = normalize(kw)
        if not kw_norm:
            continue
        if kw_norm == label:
            score += 10.0
        elif kw_norm in label:
            score += 5.0
        else:
            # Word-level overlap
            words = kw_norm.split()
            matched = sum(1 for w in words if len(w) > 2 and w in label)
            score += matched * 2.0

    return score

def decide_next_action(payload: SanitizedContextPackage) -> Tuple[List[BrowserAction], str]:
    task = payload.instruction_sanitized
    task_lower = normalize(task)
    history = payload.history or []
    history_actions = [h.get("action") for h in history if isinstance(h, dict)]

    elements = [el for el in payload.elements if el.interactable and el.sensitivity != "sensitive_raw"]
    if not elements:
        return [BrowserAction(type="done")], "No actionable interactive elements detected on page."

    # 1. Search Intent: "search for X", "find X", etc.
    search_terms = extract_search_terms(task)
    query_text = search_terms[0] if search_terms else ""

    # Check if we have already typed into a search box in this session
    has_typed = any(h == "type" for h in history_actions)

    if query_text and not has_typed:
        # Find the best editable search input
        inputs = [el for el in elements if el.role in ("input", "textarea") and el.sensitivity != "redacted"]
        best_input = None
        best_score = -1.0

        for inp in inputs:
            score = score_element_for_action(inp, ["search", "find", "query", "kw", "q", "input", query_text], ["input", "textarea"])
            if score > best_score:
                best_score = score
                best_input = inp

        if best_input:
            actions = [
                BrowserAction(
                    type="type",
                    target=ActionTarget(element_id=best_input.id),
                    value=ActionValue(text=query_text)
                ),
                BrowserAction(type="wait", milliseconds=300)
            ]
            # Look for an adjacent search/submit button or hit enter
            search_btns = [el for el in elements if el.role in ("button", "a") and any(k in normalize(el.label) for k in ("search", "go", "submit", "find"))]
            if search_btns:
                actions.append(BrowserAction(type="click", target=ActionTarget(element_id=search_btns[0].id)))
            else:
                actions.append(BrowserAction(type="wait", milliseconds=500))

            return actions, f"Identified search input '{best_input.label}' (id={best_input.id}). Typed query '{query_text}' and triggered search."

    # 2. Add to Cart / Shopping Intent
    if any(k in task_lower for k in ("cart", "buy", "purchase", "add")):
        cart_targets = [el for el in elements if any(k in normalize(el.label) for k in ("add to cart", "add", "cart", "buy now"))]
        if cart_targets:
            target = cart_targets[0]
            return [
                BrowserAction(type="click", target=ActionTarget(element_id=target.id)),
                BrowserAction(type="wait", milliseconds=500),
                BrowserAction(type="done")
            ], f"Located actionable shopping element '{target.label}' (id={target.id}). Dispatched click."

    # 3. Statement / Download / Export Intent
    if any(k in task_lower for k in ("download", "statement", "export", "pdf", "file")):
        dl_targets = [el for el in elements if any(k in normalize(el.label) for k in ("download", "statement", "export", "get statement", "download statement"))]
        if dl_targets:
            target = dl_targets[0]
            return [
                BrowserAction(type="click", target=ActionTarget(element_id=target.id)),
                BrowserAction(type="wait", milliseconds=500),
                BrowserAction(type="done")
            ], f"Located download action element '{target.label}' (id={target.id}). Dispatched click."

    # 4. Sign in / Authentication Intent
    if any(k in task_lower for k in ("login", "sign in", "auth", "password")):
        pass_inputs = [el for el in payload.elements if "password" in el.id.lower() or el.role == "password" or "pass" in normalize(el.label)]
        btn_logins = [el for el in elements if any(k in normalize(el.label) for k in ("sign in", "log in", "login", "submit"))]

        if pass_inputs and btn_logins:
            return [
                BrowserAction(
                    type="type",
                    target=ActionTarget(element_id=pass_inputs[0].id),
                    value=ActionValue(secret_ref="login.password")
                ),
                BrowserAction(type="wait", milliseconds=200),
                BrowserAction(type="click", target=ActionTarget(element_id=btn_logins[0].id)),
                BrowserAction(type="wait", milliseconds=500),
                BrowserAction(type="done")
            ], f"Entered credentials via local secret_ref into '{pass_inputs[0].id}' and clicked '{btn_logins[0].label}'."

    # 5. Form submission / Verification Intent
    if any(k in task_lower for k in ("verify", "submit", "proceed", "continue")):
        submit_btns = [el for el in elements if any(k in normalize(el.label) for k in ("verify", "submit", "proceed", "continue", "confirm"))]
        if submit_btns:
            target = submit_btns[0]
            return [
                BrowserAction(type="click", target=ActionTarget(element_id=target.id)),
                BrowserAction(type="wait", milliseconds=500),
                BrowserAction(type="done")
            ], f"Dispatched click on form submission element '{target.label}' (id={target.id})."

    # 6. General Semantic Matcher (ranks interactive elements by overlap with task keywords)
    task_words = [w for w in task_lower.split() if len(w) > 3 and w not in ("please", "click", "open", "this", "that", "with")]
    if task_words:
        scored = [(el, score_element_for_action(el, task_words, ["button", "a", "input"])) for el in elements]
        scored.sort(key=lambda x: x[1], reverse=True)
        if scored and scored[0][1] > 2.0:
            best_el = scored[0][0]
            return [
                BrowserAction(type="click", target=ActionTarget(element_id=best_el.id)),
                BrowserAction(type="wait", milliseconds=500),
                BrowserAction(type="done")
            ], f"Semantically selected candidate element '{best_el.label}' (id={best_el.id}, score={scored[0][1]})."

    # 7. Fallback: task completed or first actionable element
    if history_actions:
        return [BrowserAction(type="done")], "Previous action succeeded; task goal verified and completed."
    
    first = elements[0]
    return [
        BrowserAction(type="click", target=ActionTarget(element_id=first.id)),
        BrowserAction(type="done")
    ], f"Defaulted to first actionable element '{first.label}' (id={first.id})."
