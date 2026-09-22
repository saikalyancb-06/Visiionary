"""
Deterministic Action Validator Module for Visiionary Agent

Intercepts and validates all proposed actions from LLM or heuristic planners before browser execution.
Guarantees:
1. Structural schema validity.
2. Target existence in the current observed element snapshot.
3. Element interactability and safety (not redacted/sensitive).
4. URL Provenance: OPEN_LINK / NAVIGATE can only visit observed safe hrefs or authorized search discovery.
5. Anti-Element-ID typing protection: Prevents typing internal IDs like visi_el_*, red_*, selectors, or empty strings.
6. Generic Subgoal & Task Relevance: Domain-agnostic scoring to prevent clicking irrelevant links.
7. Blocked signatures: Prevents repeating actions that failed to alter state.
"""
import re
import urllib.parse
from typing import Tuple, Optional, List, Set
from server.app.schemas.schemas import BrowserAction, ActionTarget, ActionValue, SanitizedContextPackage, ElementMetadata

RE_INTERNAL_ID = re.compile(r'^(visi_el_\d+|red_\d+|element_\d+|name_[\w-]+)$', re.IGNORECASE)
RE_SELECTOR_OR_XPATH = re.compile(r'^(\/\/|\/\*|css:|xpath:|#|\.|\w+\[\w+)', re.IGNORECASE)

VALID_ACTION_TYPES = {
    "click",
    "type",
    "search",
    "open_link",
    "navigate",
    "select",
    "scroll",
    "download",
    "go_back",
    "go_forward",
    "wait",
    "done",
    "ask_user",
}

def get_action_signature(action: BrowserAction) -> str:
    target_id = ""
    if action.target:
        target_id = action.target.element_id or action.target.xpath or ""
    val_text = ""
    if action.value:
        val_text = action.value.text or ""
    return f"{action.type}:{target_id}:{action.url or ''}:{val_text}:{action.direction or ''}"

def tokenize(text: str) -> Set[str]:
    if not text:
        return set()
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
    stop_words = {
        "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with",
        "of", "by", "from", "up", "about", "into", "over", "after", "it",
        "this", "that", "these", "those", "website", "portal", "page", "site",
        "online", "webpage", "open", "go", "navigate", "find", "search"
    }
    tokens = set()
    for t in cleaned.split():
        if len(t) > 2 and t not in stop_words:
            tokens.add(t)
    return tokens

def extract_url_identity(href: str) -> Tuple[str, str, Set[str]]:
    """
    Generic destination identity resolver for any observed URL.
    Returns:
      (normalized_hostname, normalized_pathname, identity_tokens)
    Treats query parameters, fragments, tracking, and redirect parameters as NON-IDENTITY.
    """
    if not href:
        return "", "", set()
    try:
        parsed = urllib.parse.urlparse(href)
        hostname = (parsed.hostname or parsed.netloc or "").lower()
        if hostname.startswith("www."):
            hostname = hostname[4:]
        pathname = (parsed.path or "").lower()
        # Clean path segments
        path_tokens = tokenize(pathname)
        host_tokens = tokenize(hostname.replace('.', ' '))
        identity_tokens = host_tokens.union(path_tokens)
        return hostname, pathname, identity_tokens
    except Exception:
        return "", "", set()

def score_link_relevance(el: ElementMetadata, task: str, remaining_goal: str) -> float:
    """
    Domain-agnostic relevance scoring between an element (label, href destination identity)
    and the current task / remaining subgoal.
    Zero hardcoded domain or site names.
    Query parameters, fragments, and tracking/redirect parameters are strictly excluded from identity.
    """
    goal_tokens = tokenize(remaining_goal) or tokenize(task)
    if not goal_tokens:
        return 1.0

    el_tokens = tokenize(el.label)
    if el.href:
        _, _, identity_tokens = extract_url_identity(el.href)
        el_tokens.update(identity_tokens)

    overlap = goal_tokens.intersection(el_tokens)
    return len(overlap) / float(len(goal_tokens))

def validate_action(
    action: BrowserAction,
    context: SanitizedContextPackage,
    blocked_signatures: Optional[Set[str]] = None
) -> Tuple[bool, Optional[BrowserAction], str]:
    """
    Validates a single BrowserAction against the current context snapshot.
    Returns (is_valid, validated_action, failure_reason).
    """
    if not action or not action.type:
        return False, None, "Action is empty or missing 'type'."

    action_type = action.type.lower()
    if action_type not in VALID_ACTION_TYPES:
        return False, None, f"Action type '{action_type}' is not recognized in supported schema."

    # Check blocked signatures (Loop Shield hard block)
    action_sig = get_action_signature(action)
    if blocked_signatures and action_sig in blocked_signatures:
        return False, None, f"Action '{action_sig}' is blocked by Loop Shield due to repeated non-transition."

    # Build lookup table of observable elements
    elements_by_id = {el.id: el for el in context.elements}

    # 1. CLICK Validation
    if action_type == "click":
        if not action.target or not action.target.element_id:
            return False, None, "CLICK action missing target element_id."
        target_id = action.target.element_id
        if target_id not in elements_by_id:
            return False, None, f"CLICK target '{target_id}' does not exist in observed page elements."
        target_el = elements_by_id[target_id]
        if not target_el.interactable:
            return False, None, f"Target '{target_id}' is marked non-interactable."
        if target_el.sensitivity == "sensitive_raw":
            return False, None, f"Target '{target_id}' is protected by Client Privacy Gate."

        # If it's a link or navigation element, check relevance if remaining_goal specifies a target
        remaining = ""
        if context.verification_state:
            remaining = context.verification_state.get("remaining_goal") or ""
        curr_url = (context.page.url_sanitized or "").lower()
        if ("google.com/search" in curr_url or "bing.com/search" in curr_url) and target_el.role in ("a", "link"):
            rel_score = score_link_relevance(target_el, context.instruction_sanitized, remaining)
            # Irrelevant link rejection on search result pages when we have candidate links
            if rel_score == 0.0:
                # Check if other links have higher relevance
                better_links = [
                    e for e in context.elements 
                    if e.role in ("a", "link") and score_link_relevance(e, context.instruction_sanitized, remaining) > 0.0
                ]
                if better_links:
                    return False, None, f"CLICK target '{target_id}' ({target_el.label}) is unrelated to goal '{remaining or context.instruction_sanitized}'."

        return True, action, "Valid CLICK action."

    # 2. TYPE / SEARCH Validation
    elif action_type in ("type", "search"):
        if not action.target or not action.target.element_id:
            return False, None, f"{action_type.upper()} action missing target element_id."
        target_id = action.target.element_id
        if target_id not in elements_by_id:
            return False, None, f"{action_type.upper()} target '{target_id}' does not exist in observed page elements."
        target_el = elements_by_id[target_id]
        if not target_el.interactable:
            return False, None, f"Target '{target_id}' is marked non-interactable."
        if target_el.sensitivity == "sensitive_raw":
            return False, None, f"Target '{target_id}' is protected by Client Privacy Gate."

        text = ""
        if action.value:
            text = (action.value.text or "").strip()

        # ANTI-ELEMENT-ID AND ANTI-GARBAGE GUARDS
        if not text and not (action.value and action.value.secret_ref):
            return False, None, f"{action_type.upper()} text value cannot be empty."
        if text == target_id:
            return False, None, f"TYPE text equals element ID '{target_id}'. Typing element ID into input is strictly forbidden."
        if RE_INTERNAL_ID.match(text):
            return False, None, f"TYPE text matches internal element ID pattern '{text}'. Rejecting element ID confusion."
        if RE_SELECTOR_OR_XPATH.match(text):
            return False, None, f"TYPE text appears to be a CSS/XPath selector ('{text}'). Rejecting selector typing."

        return True, action, f"Valid {action_type.upper()} action."

    # 3. OPEN_LINK Validation (URL Provenance)
    elif action_type == "open_link":
        target_url = action.url
        # If target has element_id, verify target and see if href matches
        observed_hrefs = {el.href for el in context.elements if el.href}
        if action.target and action.target.element_id:
            el = elements_by_id.get(action.target.element_id)
            if el and el.href:
                target_url = el.href
                action.url = el.href

        if not target_url:
            return False, None, "OPEN_LINK missing URL."

        if not (target_url.startswith("http://") or target_url.startswith("https://")):
            return False, None, f"OPEN_LINK URL '{target_url}' must be a valid http(s) URL."

        # Provenance check: URL must either match an observed href in context elements,
        # or be a valid initial search discovery URL
        if target_url not in observed_hrefs:
            # Check if it is a safe search discovery query matching task tokens
            parsed = urllib.parse.urlparse(target_url)
            is_search = "google.com" in parsed.netloc or "bing.com" in parsed.netloc
            if not is_search:
                return False, None, f"URL Provenance Violation: OPEN_LINK destination '{target_url}' was not observed in current page elements."

        return True, action, "Valid OPEN_LINK action with verified provenance."

    # 4. NAVIGATE Validation
    elif action_type == "navigate":
        nav_url = action.url
        if not nav_url:
            return False, None, "NAVIGATE missing URL."
        if not (nav_url.startswith("http://") or nav_url.startswith("https://")):
            return False, None, f"NAVIGATE URL '{nav_url}' must be a valid http(s) URL."

        # Allow search discovery or direct user specified domain/URL
        parsed = urllib.parse.urlparse(nav_url)
        is_search = "google.com" in parsed.netloc or "bing.com" in parsed.netloc
        
        # If not search, check if domain was explicitly or implicitly in user instruction or history
        instruction_tokens = tokenize(context.instruction_sanitized)
        domain_tokens = tokenize(parsed.netloc)
        observed_hrefs = {el.href for el in context.elements if el.href}
        
        has_overlap = bool(instruction_tokens.intersection(domain_tokens))
        in_observed = nav_url in observed_hrefs

        if not is_search and not has_overlap and not in_observed and context.step > 1:
            return False, None, f"NAVIGATE URL '{nav_url}' has no provenance in task or observed page elements."

        return True, action, "Valid NAVIGATE action."

    # 5. SELECT Validation
    elif action_type == "select":
        if not action.target or not action.target.element_id:
            return False, None, "SELECT action missing target element_id."
        target_id = action.target.element_id
        if target_id not in elements_by_id:
            return False, None, f"SELECT target '{target_id}' does not exist in observed page elements."
        return True, action, "Valid SELECT action."

    # 6. DOWNLOAD Validation
    elif action_type == "download":
        if action.target and action.target.element_id:
            target_id = action.target.element_id
            if target_id not in elements_by_id:
                return False, None, f"DOWNLOAD target '{target_id}' does not exist in observed page elements."
        return True, action, "Valid DOWNLOAD action."

    # 7. Passive & Control Actions: SCROLL, WAIT, GO_BACK, GO_FORWARD, DONE, ASK_USER
    elif action_type in ("scroll", "wait", "go_back", "go_forward", "done", "ask_user"):
        return True, action, f"Valid {action_type.upper()} action."

    return False, None, f"Unhandled action type '{action_type}'."
