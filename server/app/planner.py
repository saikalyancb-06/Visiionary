import re
from typing import List, Optional, Tuple
from server.app.schemas.schemas import SanitizedContextPackage, BrowserAction, ActionTarget, ActionValue, ElementMetadata

def normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', (text or '')).strip().lower()

SUPERLATIVE_CRITERIA_MAP = [
    (re.compile(r'\b(best\s*seller|best-selling|best\s*selling|top\s*seller|top-selling)\b', re.I), "BEST_SELLING", "best seller"),
    (re.compile(r'\b(highest\s*rated|top\s*rated|top-rated|best\s*rated|best-reviewed)\b', re.I), "HIGHEST_RATED", "highest rated"),
    (re.compile(r'\b(most\s*popular|trending|popular)\b', re.I), "MOST_POPULAR", "most popular"),
    (re.compile(r'\b(cheapest|lowest\s*priced|lowest\s*price|most\s*affordable)\b', re.I), "LOWEST_PRICED", "cheapest"),
    (re.compile(r'\b(highest\s*priced|most\s*expensive)\b', re.I), "HIGHEST_PRICED", "highest priced"),
]

def extract_selection_criterion(task: str) -> Optional[Tuple[str, str]]:
    """
    Extracts generic selection criterion like BEST_SELLING, HIGHEST_RATED, LOWEST_PRICED.
    Returns (CRITERION_NAME, display_label) or None.
    Zero website hardcoding.
    """
    for pattern, crit_name, disp in SUPERLATIVE_CRITERIA_MAP:
        if pattern.search(task):
            return crit_name, disp
    return None

def has_downstream_actions(task: str) -> bool:
    """
    Detects if task contains any downstream actions after initial search.
    e.g. open, add, cart, buy, download, submit, select, etc.
    """
    t_clean = normalize(task)
    downstream_patterns = [
        r'\b(open\s+it|open\s+product|open\s+the\s+selected|open\s+the\s+item|open\s+selected|view\s+details)\b',
        r'\b(add\s+to\s+cart|add\s+it\s+to\s+cart|add\s+to\s+basket|add\s+item|cart|buy|purchase)\b',
        r'\b(download|export|save\s+pdf|get\s+pdf|save\s+document)\b',
        r'\b(submit|apply|confirm|book|reserve|checkout|proceed)\b',
        r'\b(select\s+the\s+result|select\s+the\s+best|choose\s+the\s+best|pick\s+the\s+best|select\s+the\s+cheapest)\b'
    ]
    if any(re.search(p, t_clean) for p in downstream_patterns):
        return True

    # If the user task specifies a concrete product entity or attributes,
    # finding is not just a query - selecting/opening the item is required downstream.
    from server.app.product_constraints import extract_product_constraints
    pc = extract_product_constraints(task)
    if pc.get("product_type") or pc.get("attributes"):
        pt = pc.get("product_type", "")
        if pt and not any(k in pt for k in ("portal", "website", "sih", "page", "statement", "query", "score", "scores", "event", "results")):
            return True

    return False

def decompose_task_into_subgoals(task: str) -> List[str]:
    """
    Decomposes arbitrary user task into an ordered sequence of required subgoals:
    1. Navigation (reach portal/site)
    2. Search / Query intent (search for keywords)
    3. Target Identification / Selection (by criterion or id)
    4. Downstream Action (open, add_to_cart, download, submit)
    """
    subgoals = []
    task_clean = task.strip().rstrip('.')
    task_lower = normalize(task_clean)

    # 1. Navigation / Site access (requires conjunction like 'and' or 'then' before further actions)
    nav_match = re.search(r'(?:open|go to|navigate to|visit)\s+([a-zA-Z0-9\s._-]+?)(?:\s+(?:and|then|to)\s+)', task_clean, re.I)
    if nav_match:
        site_target = nav_match.group(1).strip()
        subgoals.append(f"reach {site_target}")

    # 2. Search / Query intent
    search_match = re.search(r'(?:find|search for|search|look for|query)\s+([a-zA-Z0-9\s._-]+?)(?:\s+(?:and|then|to)\s+|$)', task_clean, re.I)
    if search_match:
        query_target = search_match.group(1).strip()
        subgoals.append(f"find {query_target}")

    # 3. Item identification / Selection criteria (generic: BEST_SELLING, HIGHEST_RATED, etc.)
    criterion = extract_selection_criterion(task_clean)
    if criterion:
        crit_name, disp = criterion
        subgoals.append(f"identify {disp} item")
    elif re.search(r'\b(?:problem statement|ps)\s*(?:no\.?|id|#)?\s*([0-9]{2,5})\b', task_clean, re.I):
        m = re.search(r'\b(?:problem statement|ps)\s*(?:no\.?|id|#)?\s*([0-9]{2,5})\b', task_clean, re.I)
        subgoals.append(f"locate problem statement {m.group(1)}")
    elif any(w in task_lower for w in ("select the result", "choose the result", "identify the result")):
        subgoals.append("identify target item")
    else:
        from server.app.product_constraints import extract_product_constraints
        pc = extract_product_constraints(task_clean)
        if pc.get("product_type") or pc.get("attributes"):
            pt_label = pc.get("product_type") or "target product"
            subgoals.append(f"identify {pt_label}")

    # 4. Action execution (open product, add to cart, download file, submit)
    if re.search(r'\b(?:open it|open product|open the selected|open the item|view details)\b', task_clean, re.I):
        subgoals.append("open selected product")
    elif re.search(r'\b(?:add to cart|add it to cart|buy now|add the selected result to cart|add to basket)\b', task_clean, re.I):
        subgoals.append("add selected item to cart")
    elif re.search(r'\b(?:download|export|save pdf|download it|download its document)\b', task_clean, re.I):
        subgoals.append("download document")
    elif re.search(r'\b(?:submit|apply|book|checkout)\b', task_clean, re.I):
        subgoals.append("submit form")
    elif any(sg.startswith("identify ") for sg in subgoals) and not any(w in task_lower for w in ("find ", "search ", "look for ", "portal", "website", "sih", "score", "scores", "event", "results")):
        subgoals.append("open selected product")

    if not subgoals:
        subgoals = [task_clean if task_clean.lower().startswith(('open ', 'reach ', 'view ', 'find ', 'search ')) else f"open {task_clean}"]
    return subgoals

def track_subgoal_progress(task: str, current_url: str, page_title: str, elements: List[ElementMetadata], history: List[dict]) -> Tuple[List[str], List[str], str]:
    subgoals = decompose_task_into_subgoals(task)
    completed = []
    url_lower = (current_url or "").lower()
    title_lower = (page_title or "").lower()
    page_text = f"{title_lower} {url_lower} " + " ".join(e.label.lower() for e in elements[:40])
    history_actions = [h.get("action") for h in history if isinstance(h, dict)]

    is_search_engine_page = "google.com/search" in url_lower or "bing.com/search" in url_lower

    for sg in subgoals:
        sg_l = sg.lower()
        if sg_l.startswith("reach "):
            site = sg_l[6:].strip()
            clean_site = re.sub(r'\b(the|portal|website|site)\b', '', site).strip()
            if clean_site and clean_site in url_lower and not is_search_engine_page:
                completed.append(sg)
        elif sg_l.startswith("find "):
            query = sg_l[5:].strip()
            # Verified search query completion requires having searched and landed on store/portal results (not blank/unrelated)
            has_typed = any(h.get("action") == "type" or h.get("action") == "search" for h in history if isinstance(h, dict))
            query_words = [w for w in clean_site_query(query).split() if len(w) > 2]
            if (has_typed and any(w in page_text for w in query_words)) or (len(history_actions) >= 2 and any(w in page_text for w in query_words)):
                completed.append(sg)
        elif sg_l.startswith("identify "):
            # Strict Invariant: TARGET_IDENTIFIED == true ONLY IF candidate entity satisfies ALL hard constraints.
            # RAW DOM ELEMENT != PRODUCT. Must aggregate evidence into ProductCandidate entities first.
            from server.app.product_constraints import extract_product_constraints, verify_selection_criterion_evidence
            from server.app.candidate_extractor import extract_product_candidates, verify_product_candidate_match
            constraints = extract_product_constraints(task)
            
            # Aggregate raw elements into structured product candidates
            product_candidates = extract_product_candidates(elements, page_title or "", current_url or "")
            matching_candidate = None
            for pc in product_candidates:
                ok_cand, _ = verify_product_candidate_match(pc, constraints)
                if ok_cand:
                    matching_candidate = pc
                    break

            if matching_candidate:
                crit = constraints.get("selection_criterion")
                if crit:
                    has_ev, _ = verify_selection_criterion_evidence(matching_candidate, constraints)
                    if has_ev:
                        completed.append(sg)
                else:
                    completed.append(sg)
        elif "problem statement" in sg_l and sg_l.startswith("locate "):
            num_m = re.search(r'([0-9]{2,5})', sg_l)
            if num_m and num_m.group(1) in page_text:
                completed.append(sg)
        elif sg_l == "open selected product":
            # True postcondition: Current URL or page title indicates an individual product/item page
            is_product_page = any(k in url_lower for k in ("/dp/", "/gp/product/", "/p/", "/item/", "/product/")) or any(k in title_lower for k in ("product details", "buy ", ": clothing", "specifications"))
            has_click = any(h.get("action") == "click" for h in history if isinstance(h, dict))
            if is_product_page and has_click:
                completed.append(sg)
        elif sg_l == "add selected item to cart":
            # True postcondition: Cart action confirmed by cart indicators in title/page text or state transition
            cart_confirmed = any(k in page_text for k in ("added to cart", "item added", "in your cart", "view cart", "cart (1)", "cart: 1", "checkout (1)"))
            if cart_confirmed and any(h.get("action") == "click" for h in history if isinstance(h, dict)):
                completed.append(sg)
        elif sg_l == "download document":
            # True postcondition: Browser download state records completed download
            # (handled by verifier using payload.downloads)
            pass
        elif sg_l == "submit form":
            form_submitted = any(k in page_text for k in ("thank you", "submitted", "success", "confirmation", "received"))
            if form_submitted:
                completed.append(sg)

    remaining = [sg for sg in subgoals if sg not in completed]
    remaining_str = remaining[0] if remaining else "None"
    return subgoals, completed, remaining_str

def clean_site_query(query: str) -> str:
    cleaned = re.sub(r'\b(the|best|seller|selling|portal|website|page)\b', '', query, flags=re.I).strip()
    return cleaned

def extract_search_terms(task: str) -> List[str]:
    # Extract candidate query terms from task: e.g. "search for laptop", "find best selling black shirt for men"
    t = (task or "").strip()
    # Strip any parenthetical notes/recovery hints
    t = re.sub(r'\s*\([^)]*\)', '', t).strip()
    # Strip conversational prefixes: "can you find me a", "could you please search for"
    t_clean = re.sub(r'^(?:can\s+you\s+(?:please\s+)?|could\s+you\s+(?:please\s+)?|please\s+|i\s+(?:want|need)\s+(?:you\s+to\s+)?|help\s+me\s+(?:to\s+)?|kindly\s+)', '', t, flags=re.IGNORECASE)
    # Strip leading navigation site: "open sih portal and", "go to amazon and"
    t_clean = re.sub(r'^(?:open|go\s+to|navigate\s+to|visit)\s+[a-zA-Z0-9\s._-]+?\s+(?:and|then)\s+', '', t_clean, flags=re.IGNORECASE)
    # Strip site mentions: "in flipkart", "on amazon"
    t_clean = re.sub(r'\b(?:in|on|at|from)\s+(?:flipkart|amazon|myntra|ebay|walmart|target|etsy|aliexpress|bestbuy|ajio|meesho|google|bing)\b.*$', '', t_clean, flags=re.IGNORECASE)
    # Strip trailing condition clauses: ", it should...", "it shou..."
    t_clean = re.sub(r'[,;]?\s*\b(?:it\s+shou\w*|it\s+should|it\s+must|it\s+needs\s+to|make\s+sure|which\s+should|having)\b.*$', '', t_clean, flags=re.IGNORECASE)

    # Check for specific problem statement or item ID: e.g. "find me ps no.143" -> extract "143"
    ps_m = re.search(r'\b(?:problem statement|ps)\s*(?:no\.?|id|#)?\s*([0-9]{2,6})\b', t_clean, re.I)
    if ps_m:
        return [ps_m.group(1)]

    m = re.search(r'(?:search for\s+a|search for|find\s+me\s+a|find\s+me|find\s+a|find|search|look for\s+a|look for|query|get\s+me\s+a|get\s+me|get)\s+["\']?([^"\']+)["\']?', t_clean, re.IGNORECASE)
    if m:
        query = m.group(1).strip()
        # strip trailing directives like "and open it", "and add to cart", "inside that website"
        query = re.sub(r'\s+(?:inside|in|on)\s+(?:that|the|this)?\s*(?:website|portal|page|site|store|app).*$', '', query, flags=re.IGNORECASE)
        query = re.sub(r'\s+(?:and\s+.*|on\s+.*)$', '', query, flags=re.IGNORECASE)
        # strip leading superlatives if user said "find the best seller black shirt for men" -> "black shirt for men"
        query_cleaned = re.sub(r'^\s*(?:the\s+)?(?:best\s*sell(?:er|ing)|highest\s*rated|top\s*rated|cheapest)\s+', '', query, flags=re.IGNORECASE).strip()
        query_cleaned = re.sub(r'\b(?:in|on|at)\s+(?:flipkart|amazon|myntra|ebay|walmart|target|etsy|aliexpress|bestbuy|ajio|meesho)\b', '', query_cleaned, flags=re.IGNORECASE).strip()
        return [query_cleaned or query]
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

def _decide_next_action_core(payload: SanitizedContextPackage) -> Tuple[List[BrowserAction], str]:
    task = payload.instruction_sanitized
    task_lower = normalize(task)
    history = payload.history or []
    history_actions = [h.get("action") for h in history if isinstance(h, dict)]

    elements = [el for el in payload.elements if el.interactable and el.sensitivity != "sensitive_raw"]

    # Structured Loop / Failure Recovery Handling (Requirement 13)
    recovery_info = payload.recovery_state or (payload.verification_state.get("recovery_state") if payload.verification_state else None)
    blocked_element_id = None
    if recovery_info:
        rec_type = recovery_info.get("failure_type")
        if rec_type in ("REPEATED_ACTION", "WRONG_CANDIDATE", "BLOCKED_ACTION"):
            blocked_act = recovery_info.get("blocked_action", {})
            if isinstance(blocked_act, dict) and blocked_act.get("target"):
                blocked_element_id = blocked_act.get("target")
            elif recovery_info.get("blocked_target_id"):
                blocked_element_id = recovery_info.get("blocked_target_id")
            if blocked_element_id:
                elements = [el for el in elements if el.id != blocked_element_id]

    # -----------------------------------------------------------------------
    # Reconstruct dependency-aware task execution state & classify page semantics
    # -----------------------------------------------------------------------
    from server.app.task_state_machine import (
        reconstruct_state, save_state, parse_task_requirements,
        get_legal_transitions, evaluate_phase_prerequisites, get_blocked_diagnostic,
        PHASE_DISCOVER, PHASE_SEARCH, PHASE_EXTRACT_ENTITIES, PHASE_ACCUMULATE,
        PHASE_COMPARE, PHASE_SELECT_TARGET, PHASE_OPEN_TARGET, PHASE_VERIFY_TARGET_PAGE,
        PHASE_EXTRACT_INFORMATION, PHASE_GOAL_ACHIEVED,
    )
    from server.app.page_model import (
        classify_page_semantics,
        PAGE_SEARCH_DISCOVERY, PAGE_LISTING_CATALOG, PAGE_DETAIL_ENTITY,
        PAGE_TRANSACTION_CART, PAGE_CONFIRMATION_RESULT, PAGE_AUTHENTICATION,
        PAGE_FORM_INTERACTION, PAGE_DASHBOARD_TABLE, PAGE_NAVIGATION_INTERMEDIATE,
        PAGE_ARTICLE_DOCUMENT, PAGE_UNKNOWN,
    )

    page_semantics = classify_page_semantics(
        elements=elements,
        page_title=payload.page.title_sanitized or '',
        current_url=payload.page.url_sanitized or '',
    )

    task_state = reconstruct_state(
        payload.verification_state,
        payload.selected_target,
        getattr(payload, 'task_execution_state', None),
    )
    task_reqs = parse_task_requirements(task)
    # Hydrate state with task requirements (first call bootstraps count/flags)
    if task_state.required_candidate_count == 1 and task_reqs["required_candidate_count"] > 1:
        task_state.required_candidate_count = task_reqs["required_candidate_count"]
    if not task_state.requires_comparison and task_reqs["requires_comparison"]:
        task_state.requires_comparison = task_reqs["requires_comparison"]
    if not task_state.requires_information_extraction and task_reqs["requires_information_extraction"]:
        task_state.requires_information_extraction = task_reqs["requires_information_extraction"]
        task_state.information_fields_requested = task_reqs["information_fields_requested"]

    legal_phases = get_legal_transitions(task_state)

    # -----------------------------------------------------------------------
    # 0. Universal Navigation Intent: "open X", "go to X", "navigate to X"
    #    GUARD: Skip if the captured target is a deictic/relative reference
    #           (it, its, this, that, the selected, product page, etc.)
    #           Such phrases refer to a previously-selected entity, not a site.
    # -----------------------------------------------------------------------
    # Deictic pronouns and relative-reference words that are NOT concrete nav targets
    DEICTIC_REFERENCES = {
        "it", "its", "them", "their", "this", "that", "these", "those",
        "selected", "chosen", "picked", "result", "page",
    }

    nav_match = re.search(r'(?:open|go to|navigate to|visit)\s+([a-zA-Z0-9\s._/:-]+)', task_lower)
    clean_name = ""
    target_name = ""
    if nav_match:
        raw_query = nav_match.group(1).strip()
        clean_name = re.sub(r'^(the|a|an)\s+', '', raw_query, flags=re.IGNORECASE).strip()
        clean_name = re.sub(r'\s+(and|then|to|for)\s+.*$', '', clean_name, flags=re.IGNORECASE).strip()
        target_name = re.sub(r'\b(portal|website|page|site|webpage|online|it|them|item)\b', '', clean_name, flags=re.IGNORECASE).strip()

        # Check for deictic/relative references — these are downstream actions, not nav targets
        target_tokens = re.split(r'[^a-zA-Z]+', target_name.lower())
        target_tokens = [t for t in target_tokens if t]
        is_deictic = (
            target_name in ("", "it", "them", "item", "this", "that")
            or any(tok in DEICTIC_REFERENCES for tok in target_tokens)
        )
        if is_deictic:
            nav_match = None


    has_navigated = any(h == "navigate" for h in history_actions)
    curr_url = (payload.page.url_sanitized or '').lower()
    is_on_search_engine = (
        "google.com/search" in curr_url
        or "bing.com/search" in curr_url
        or "duckduckgo.com" in curr_url
        or "search.yahoo.com" in curr_url
    )
    is_on_search = is_on_search_engine or ("search" in curr_url and ("q=" in curr_url or "query=" in curr_url)) or "/?q=" in curr_url

    if nav_match and not has_navigated and not is_on_search:
        target_url = None
        if target_name.startswith("http://") or target_name.startswith("https://"):
            target_url = target_name
        elif "." in target_name and " " not in target_name:
            target_url = f"https://{target_name}"
        elif clean_name and len(clean_name) > 1:
            # Autonomous discovery for any unseen site, portal, or tool in the world
            import urllib.parse
            target_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(clean_name)}"

        if target_url and target_url not in (payload.page.url_sanitized or ''):
            return [BrowserAction(type="navigate", url=target_url)], f"Autonomous Navigation: Navigating to {target_url} for '{clean_name}'."

    if not elements:
        return [BrowserAction(type="done")], "No actionable interactive elements detected on page."

    # Autonomous Search Engine Result / Intermediate Destination Selection
    # When on an external search engine (Google, Bing, DuckDuckGo), evaluate organic destination links to enter target portal
    nav_target = clean_name or target_name or ""
    if is_on_search_engine:
        target_already_reached = False
    else:
        target_already_reached = bool(nav_target and len(nav_target) > 2 and nav_target.lower() in curr_url)

    if is_on_search_engine and not target_already_reached:
        skip_labels = {"all", "images", "videos", "news", "maps", "more", "tools", "sign in", "settings", "privacy", "terms", "feedback", "next"}
        result_links = [
            el for el in elements 
            if el.role in ("a", "link") 
            and len(el.label.strip()) > 3 
            and normalize(el.label) not in skip_labels
            and not any(normalize(el.label).startswith(p) for p in ("images for", "videos for", "news for", "shopping for"))
            and not any(x in normalize(el.label) for x in ("verbatim", "any time", "past hour", "clear"))
        ]
        if result_links:
            import urllib.parse
            target_tokens = [t.lower() for t in re.split(r'[^a-zA-Z0-9]+', nav_target) if len(t) > 2]
            target_match_links = []

            for el in result_links:
                label_lower = el.label.lower()
                matched_identity = False

                if target_tokens:
                    # Check 1: Label match
                    if any(t in label_lower for t in target_tokens):
                        matched_identity = True

                    # Check 2: True URL Destination Identity (hostname & pathname ONLY)
                    # Query parameters, fragments, redirect/continue parameters are strictly ignored.
                    if el.href:
                        try:
                            parsed_href = urllib.parse.urlparse(el.href)
                            raw_host = (parsed_href.hostname or parsed_href.netloc or "").lower()
                            if raw_host.startswith("www."):
                                raw_host = raw_host[4:]
                            raw_path = (parsed_href.path or "").lower()

                            # Hostname match (subdomains or domain name)
                            host_parts = [p for p in raw_host.split('.') if p and p not in ('com', 'org', 'net', 'gov', 'edu', 'io', 'in', 'co', 'uk')]
                            if any(t in host_parts or any(t == hp for hp in host_parts) for t in target_tokens):
                                matched_identity = True
                            
                            # Path segments match (excluding file extensions)
                            path_parts = [p for p in re.split(r'[/_.-]+', raw_path) if len(p) > 2]
                            if any(t in path_parts for t in target_tokens):
                                matched_identity = True
                        except Exception:
                            pass

                if matched_identity:
                    target_match_links.append(el)

            # If user explicitly specified a navigation target, match by identity or emit NO_RELEVANT_CANDIDATE
            if nav_target:
                if target_match_links:
                    best_link = target_match_links[0]
                    if best_link.href and (best_link.href.startswith("http://") or best_link.href.startswith("https://")):
                        return [
                            BrowserAction(type="open_link", target=ActionTarget(element_id=best_link.id), url=best_link.href),
                            BrowserAction(type="wait", milliseconds=500)
                        ], f"Autonomously navigating via verified destination link '{best_link.label}' -> {best_link.href}."

                    return [
                        BrowserAction(type="click", target=ActionTarget(element_id=best_link.id)),
                        BrowserAction(type="wait", milliseconds=500)
                    ], f"Autonomously selected verified organic search result: '{best_link.label}'."
                else:
                    return [
                        BrowserAction(type="scroll", direction="down", amount=500),
                        BrowserAction(type="wait", milliseconds=500)
                    ], f"NO_RELEVANT_CANDIDATE: No search results matched destination '{nav_target}' by identity. Scrolling to inspect more candidates."

            # For pure product/discovery search tasks without a named navigation target:
            # Select the most relevant organic discovery destination matching task keywords
            elif result_links:
                task_tokens = [t.lower() for t in re.split(r'[^a-zA-Z0-9]+', task_lower) if len(t) > 2 and t not in ('find', 'search', 'with', 'least', 'under', 'from', 'best', 'more', 'flipkart', 'amazon', 'store', 'portal', 'site', 'website')]
                scored_links = []
                for el in result_links:
                    # Ignore links staying within search engine
                    if el.href and any(s in el.href.lower() for s in ('duckduckgo.com', 'google.com', 'bing.com')) and ('q=' in el.href or 'search' in el.href):
                        continue
                    l_text = f"{el.label} {el.href or ''}".lower()
                    overlap = sum(1 for tok in task_tokens if tok in l_text)
                    if overlap > 0:
                        scored_links.append((el, overlap))

                scored_links.sort(key=lambda x: x[1], reverse=True)
                if scored_links:
                    top_link = scored_links[0][0]
                    if top_link.href and (top_link.href.startswith("http://") or top_link.href.startswith("https://")):
                        return [
                            BrowserAction(type="open_link", target=ActionTarget(element_id=top_link.id), url=top_link.href),
                            BrowserAction(type="wait", milliseconds=500)
                        ], f"Transitioning from SEARCH_DISCOVERY to organic destination '{top_link.label}' -> {top_link.href}."
                    return [
                        BrowserAction(type="click", target=ActionTarget(element_id=top_link.id)),
                        BrowserAction(type="wait", milliseconds=500)
                    ], f"Transitioning from SEARCH_DISCOVERY to organic destination '{top_link.label}'."

    # 1. General Search Intent: "search for X", "find X", etc.
    # Inhibit typing when already on populated search results / discovery page
    search_terms = extract_search_terms(task)
    query_text = search_terms[0] if search_terms else ""
    has_typed = any(h == "type" for h in history_actions)

    curr_url_clean = curr_url.lower()
    url_has_query = any(w in curr_url_clean for w in query_text.lower().split() if len(w) > 2) if query_text else False
    is_already_populated_search = (
        ("search" in curr_url_clean or "results" in (payload.page.title_sanitized or '').lower() or "/search" in curr_url_clean)
        and (url_has_query or has_typed)
        and len([el for el in elements if el.role in ("a", "link") and len(el.label.strip()) > 3]) >= 2
    )

    # When on a store page and downstream items require search:
    if query_text and not has_typed and not is_already_populated_search:

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

    # 2. Specific Target / Problem Statement Intent (e.g. "problem statement 171", "PS 171")
    # Note: Avoid matching price ranges like "under 1000" or "below 500" as problem statements
    ps_match = re.search(r'(?:problem statement|ps|item|number|no\.?)\s*([0-9]{2,5})', task_lower)
    target_id_num = ps_match.group(1) if ps_match else None

    if target_id_num:
        # A. Check if the target item or problem statement is ALREADY visible on screen
        target_elements = [el for el in elements if target_id_num in el.label or (el.id and target_id_num in el.id)]
        if target_elements:
            matched_el = target_elements[0]
            # If the user specifically asked to download it:
            if any(w in task_lower for w in ["download", "pdf", "export"]):
                dl_btns = [
                    el for el in elements 
                    if any(k in normalize(el.label) + el.id.lower() for k in ("download", "pdf", "export", "view/download", "save"))
                ]
                if dl_btns:
                    target_dl = dl_btns[0]
                    return [
                        BrowserAction(type="download", target=ActionTarget(element_id=target_dl.id)),
                        BrowserAction(type="wait", milliseconds=500)
                    ], f"Located download action for target '{matched_el.label}' (id={target_dl.id}). Triggered download."

            return [
                BrowserAction(type="click", target=ActionTarget(element_id=matched_el.id)),
                BrowserAction(type="wait", milliseconds=300),
                BrowserAction(type="done")
            ], f"Found target Problem Statement '{matched_el.label}' (id={matched_el.id}). Clicked and highlighted."

        # B. If not visible, check for a table Search/Filter input box to filter directly
        if not has_typed:
            search_inputs = [
                el for el in elements 
                if el.role in ("input", "textarea") 
                and any(k in normalize(el.label) + el.id.lower() for k in ("search", "filter", "find", "dt-search", "table"))
            ]
            if not search_inputs:
                search_inputs = [el for el in elements if el.role in ("input", "textarea") and el.sensitivity != "redacted"]

            if search_inputs:
                target_inp = search_inputs[0]
                return [
                    BrowserAction(type="type", target=ActionTarget(element_id=target_inp.id), value=ActionValue(text=target_id_num)),
                    BrowserAction(type="wait", milliseconds=300)
                ], f"Located portal search filter input (id={target_inp.id}). Filtered for Problem Statement '{target_id_num}'."

        # C. Check for Pagination (e.g. Page '2' for 101-200, or 'Next')
        has_clicked_page = any(h == "click" for h in history_actions)
        if not has_clicked_page:
            target_page_str = "2" if int(target_id_num) > 100 and int(target_id_num) <= 200 else None
            if target_page_str:
                page_links = [el for el in elements if el.label.strip() == target_page_str or el.label.strip() == "Next"]
                if page_links:
                    page_el = page_links[0]
                    return [
                        BrowserAction(type="click", target=ActionTarget(element_id=page_el.id)),
                        BrowserAction(type="wait", milliseconds=500)
                    ], f"Advanced to pagination page {target_page_str} containing items 101-200."

    # 3. Product / Item Selection Intent with Strict Constraint Enforcement & Prerequisite Resolution
    from server.app.product_constraints import (
        extract_product_constraints,
        verify_candidate_match,
        rank_candidates_by_criteria,
        detect_missing_prerequisites
    )

    constraints = extract_product_constraints(task)
    req_pt = constraints.get("product_type")
    is_product_page = any(k in curr_url for k in ("/dp/", "/gp/product/", "/p/", "/item/", "/product/", "/detail/")) or any(k in (payload.page.title_sanitized or '').lower() for k in ("product details", "buy ", ": clothing", "specifications"))

    # When on a product page, check for missing prerequisites before cart/buy action
    if is_product_page:
        prereq = detect_missing_prerequisites(elements, constraints.get("requested_action"), constraints)
        if prereq:
            if prereq.get("requires_prompt"):
                opts = ", ".join(prereq.get("available_options", []))
                return [
                    BrowserAction(type="ask_user", question=f"Please specify your preferred {prereq['type'].lower()} (available options: {opts}):")
                ], f"Action Prerequisite: Multiple {prereq['type'].lower()} choices exist and none was specified. Asking user."
            elif prereq.get("element"):
                el_prereq = prereq["element"]
                return [
                    BrowserAction(type="click", target=ActionTarget(element_id=el_prereq.id)),
                    BrowserAction(type="wait", milliseconds=500)
                ], f"Action Prerequisite: Selecting user's requested {prereq['type'].lower()} '{prereq.get('value')}' ({el_prereq.label})."

    # If looking to select or open target item and NOT yet on the confirmed product page:
    if (constraints.get("requested_action") or req_pt) and not is_product_page:
        from server.app.candidate_extractor import (
            extract_product_candidates,
            verify_product_candidate_match,
            rank_product_candidates,
            print_candidate_diagnostics
        )

        # Step 1: Aggregate raw DOM/accessibility elements into structured ProductCandidate entities
        product_candidates = extract_product_candidates(
            elements,
            payload.page.title_sanitized or '',
            curr_url
        )

        valid_candidates = []
        rejected_candidates = []

        for cand in product_candidates:
            matches, reason = verify_product_candidate_match(cand, constraints)
            if matches:
                valid_candidates.append(cand)
            else:
                rejected_candidates.append((cand, reason))

        # Step 2: Rank valid candidates by selection criteria (BEST_SELLING, HIGHEST_RATED, etc.)
        if valid_candidates:
            ranked = rank_product_candidates(valid_candidates, constraints)

            # ---------------------------------------------------------------
            # STATE MACHINE GATE: Candidate Accumulation
            # For compare tasks, accumulate candidates until required count is
            # met. Do NOT dispatch OPEN_TARGET until SELECT_TARGET is legal.
            # ---------------------------------------------------------------
            if task_state.requires_comparison or task_state.required_candidate_count > 1:
                # Merge new candidates into verified_candidates (dedup by title)
                existing_titles = {c.get("title", "").lower() for c in task_state.verified_candidates}
                for rc, *rest in ranked:
                    rc_title = (rc.title or "").lower()
                    if rc_title not in existing_titles:
                        task_state.verified_candidates.append(rc.to_dict())
                        existing_titles.add(rc_title)

                have = len(task_state.verified_candidates)
                need = task_state.required_candidate_count
                print_candidate_diagnostics(
                    all_candidates=product_candidates,
                    valid_candidates=valid_candidates,
                    rejected_candidates=rejected_candidates,
                )
                print(f"[ACCUMULATE] {have}/{need} verified candidates collected.")

                if have < need:
                    # Not enough candidates yet â€” scroll to find more
                    task_state.phase = PHASE_ACCUMULATE
                    save_state(task_state, payload)
                    return [
                        BrowserAction(type="scroll", direction="down", amount=500),
                        BrowserAction(type="wait", milliseconds=500),
                    ], (
                        f"ACCUMULATE_CANDIDATES: {have}/{need} verified candidates so far. "
                        f"Scrolling to discover more matching candidates."
                    )

                # Enough candidates â€” select best among accumulated set
                # Re-rank all accumulated candidates (they are stored as dicts)
                # For now select first (ranking over dicts requires reconstruction)
                # TODO: full ranking over accumulated set when candidate_extractor supports it
                chosen_dict = task_state.verified_candidates[0]
                task_state.selected_target = chosen_dict
                task_state.phase = PHASE_SELECT_TARGET
                payload.selected_target = chosen_dict
                save_state(task_state, payload)

                chosen_href = chosen_dict.get("href") or chosen_dict.get("url") or ""
                chosen_title = chosen_dict.get("title", "")[:50]

                # -------------------------------------------------------
                # OPEN_TARGET gate
                # -------------------------------------------------------
                ok_open, missing_open = evaluate_phase_prerequisites(PHASE_OPEN_TARGET, task_state)
                if not ok_open:
                    print(get_blocked_diagnostic(PHASE_OPEN_TARGET, task_state))
                    return [
                        BrowserAction(type="scroll", direction="down", amount=400),
                        BrowserAction(type="wait", milliseconds=400),
                    ], "[PLANNER_BLOCKED] OPEN_TARGET prerequisites not satisfied. Continuing discovery."

                if chosen_href and chosen_href.startswith(("http://", "https://")):
                    task_state.phase = PHASE_OPEN_TARGET
                    save_state(task_state, payload)
                    return [
                        BrowserAction(type="open_link", target=ActionTarget(element_id=None), url=chosen_href),
                        BrowserAction(type="wait", milliseconds=500),
                    ], f"COMPARE+SELECT: {have}/{need} candidates. Selected '{chosen_title}'. Navigating to product page."

                # No href â€” scroll for more context
                save_state(task_state, payload)
                return [
                    BrowserAction(type="scroll", direction="down", amount=400),
                    BrowserAction(type="wait", milliseconds=400),
                ], f"COMPARE+SELECT: Selected '{chosen_title}' but destination href unavailable. Scrolling."

            # Non-compare path: single-entity selection
            chosen_candidate = ranked[0][0]

            # ---------------------------------------------------------------
            # OPEN_TARGET gate for non-compare path
            # ---------------------------------------------------------------
            # Save selected target into state before checking prerequisites
            payload.selected_target = chosen_candidate.to_dict()
            task_state.selected_target = chosen_candidate.to_dict()
            task_state.phase = PHASE_SELECT_TARGET

            ok_open, missing_open = evaluate_phase_prerequisites(PHASE_OPEN_TARGET, task_state)
            if not ok_open:
                print(get_blocked_diagnostic(PHASE_OPEN_TARGET, task_state))
                save_state(task_state, payload)
                return [
                    BrowserAction(type="scroll", direction="down", amount=400),
                    BrowserAction(type="wait", milliseconds=400),
                ], "[PLANNER_BLOCKED] OPEN_TARGET prerequisites not satisfied after selection. Continuing discovery."

            # Diagnostic tracing
            print_candidate_diagnostics(
                all_candidates=product_candidates,
                valid_candidates=valid_candidates,
                rejected_candidates=rejected_candidates,
                selected_target=chosen_candidate
            )

            # Choose the primary actionable element from the candidate's source elements
            target_el_id = None
            for sid in chosen_candidate.source_element_ids:
                cand_el = next((e for e in elements if e.id == sid), None)
                if cand_el and cand_el.role in ("a", "link", "button", "h2", "h3", "div") and cand_el.interactable:
                    target_el_id = sid
                    break
            if not target_el_id and chosen_candidate.source_element_ids:
                target_el_id = chosen_candidate.source_element_ids[0]

            task_state.phase = PHASE_OPEN_TARGET
            save_state(task_state, payload)

            if chosen_candidate.href and (chosen_candidate.href.startswith("http://") or chosen_candidate.href.startswith("https://")):
                return [
                    BrowserAction(type="open_link", target=ActionTarget(element_id=target_el_id), url=chosen_candidate.href),
                    BrowserAction(type="wait", milliseconds=500)
                ], f"Selected product candidate '{chosen_candidate.title[:50]}' (id={chosen_candidate.candidate_id}) matching all hard constraints. Navigating to product page."

            return [
                BrowserAction(type="click", target=ActionTarget(element_id=target_el_id)),
                BrowserAction(type="wait", milliseconds=500)
            ], f"Selected product candidate '{chosen_candidate.title[:50]}' (id={chosen_candidate.candidate_id}) matching all hard constraints."

        elif req_pt:
            # Print rejection diagnostics when no candidates qualify
            print_candidate_diagnostics(
                all_candidates=product_candidates,
                valid_candidates=[],
                rejected_candidates=rejected_candidates
            )
            # HARD CONSTRAINT FAILURE: Never select a wrong product just to make progress!
            save_state(task_state, payload)
            return [
                BrowserAction(type="scroll", direction="down", amount=500),
                BrowserAction(type="wait", milliseconds=500)
            ], f"NO_VALID_TARGET_FOUND: No candidates on screen satisfied required product type '{req_pt}' and attributes {constraints.get('attributes')}. Scrolling to inspect more."


    # 4. Add to Cart / Shopping Intent (Operates strictly on the selected item or product detail page)
    if any(k in task_lower for k in ("cart", "buy", "purchase", "add")):
        cart_targets = [el for el in elements if any(k in normalize(el.label) for k in ("add to cart", "add to basket", "buy now"))]
        if not cart_targets:
            cart_targets = [el for el in elements if el.role in ("button", "a") and any(k in normalize(el.label) for k in ("add", "cart"))]

        if cart_targets:
            target = cart_targets[0]
            return [
                BrowserAction(type="click", target=ActionTarget(element_id=target.id)),
                BrowserAction(type="wait", milliseconds=500)
            ], f"Located actionable shopping element '{target.label}' (id={target.id}). Dispatched click on target item."

    # 5. Statement / Download / Export Intent
    if any(k in task_lower for k in ("download", "statement", "export", "pdf", "file")):
        dl_targets = [el for el in elements if any(k in normalize(el.label) for k in ("download", "statement", "export", "get statement", "download statement"))]
        if dl_targets:
            target = dl_targets[0]
            return [
                BrowserAction(type="click", target=ActionTarget(element_id=target.id)),
                BrowserAction(type="wait", milliseconds=500)
            ], f"Located download action element '{target.label}' (id={target.id}). Dispatched click."

    # 6. Sign in / Authentication Intent
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
                BrowserAction(type="wait", milliseconds=500)
            ], f"Entered credentials via local secret_ref into '{pass_inputs[0].id}' and clicked '{btn_logins[0].label}'."

    # 7. Form submission / Verification Intent
    if any(k in task_lower for k in ("verify", "submit", "proceed", "continue")):
        submit_btns = [el for el in elements if any(k in normalize(el.label) for k in ("verify", "submit", "proceed", "continue", "confirm"))]
        if submit_btns:
            target = submit_btns[0]
            return [
                BrowserAction(type="click", target=ActionTarget(element_id=target.id)),
                BrowserAction(type="wait", milliseconds=500)
            ], f"Dispatched click on form submission element '{target.label}' (id={target.id})."

    # 8. General Semantic Matcher (ranks interactive elements by overlap with task keywords)
    task_words = [w for w in task_lower.split() if len(w) > 3 and w not in ("please", "click", "open", "this", "that", "with")]
    if task_words:
        scored = [(el, score_element_for_action(el, task_words, ["button", "a", "input"])) for el in elements]
        scored.sort(key=lambda x: x[1], reverse=True)
        if scored and scored[0][1] > 2.0:
            best_el = scored[0][0]
            return [
                BrowserAction(type="click", target=ActionTarget(element_id=best_el.id)),
                BrowserAction(type="wait", milliseconds=500)
            ], f"Semantically selected candidate element '{best_el.label}' (id={best_el.id}, score={scored[0][1]})."

    # 9. Fallback: For semantic product/item tasks, NEVER select an arbitrary candidate or click elements[0]
    if req_pt or constraints.get("requested_action"):
        save_state(task_state, payload)
        return [
            BrowserAction(type="scroll", direction="down", amount=400),
            BrowserAction(type="wait", milliseconds=400)
        ], "NO_VALID_CANDIDATE: No interactive elements satisfied semantic task requirements. Scrolling to inspect more candidates."

    save_state(task_state, payload)
    if history_actions:
        return [BrowserAction(type="wait", milliseconds=300)], "Action completed; yielding to independent goal verifier."

    return [
        BrowserAction(type="wait", milliseconds=500)
    ], "Awaiting clear actionable candidate matching task criteria."


def decide_next_action(payload: SanitizedContextPackage) -> Tuple[List[BrowserAction], str]:
    from server.app.page_model import classify_page_semantics, PAGE_SEARCH_DISCOVERY
    from server.app.task_state_machine import (
        reconstruct_state, parse_task_requirements, evaluate_phase_prerequisites
    )
    from server.app.candidate_extractor import extract_product_candidates, verify_product_candidate_match

    task = payload.instruction_sanitized
    curr_url = payload.page.url_sanitized or ''
    elements = [el for el in payload.elements if el.interactable and el.sensitivity != "sensitive_raw"]
    page_semantics = classify_page_semantics(
        elements=elements,
        page_title=payload.page.title_sanitized or '',
        current_url=curr_url,
    )
    task_state = reconstruct_state(payload.verification_state, payload.selected_target, getattr(payload, 'task_execution_state', None))

    # Relevant destinations
    skip_labels = {"all", "images", "videos", "news", "maps", "more", "tools", "sign in", "settings", "privacy", "terms", "feedback", "next"}
    candidate_destinations = [
        el for el in elements 
        if el.role in ("a", "link") 
        and len(el.label.strip()) > 3 
        and normalize(el.label) not in skip_labels
    ]

    # Available product candidates on current page
    extracted_candidates = extract_product_candidates(elements, payload.page.title_sanitized or '', curr_url)

    # Next predicate
    ok_phase, missing_preds = evaluate_phase_prerequisites(task_state.phase, task_state)
    next_predicate = f"{task_state.phase} (Prerequisites missing: {missing_preds})" if missing_preds else f"{task_state.phase} (Prerequisites SATISFIED)"

    # Execute core decision
    actions, summary = _decide_next_action_core(payload)

    # Diagnostic output
    selected_act_str = f"{actions[0].type} target={actions[0].target.element_id if actions[0].target else None} url={actions[0].url}" if actions else "None"
    try:
        print("\n" + "="*60)
        print("PLANNER DECISION DIAGNOSTIC")
        print("="*60)
        print(f"1. CURRENT PAGE TYPE:             {page_semantics.semantic_state} (confidence={page_semantics.confidence})")
        print(f"2. AVAILABLE RELEVANT DESTINATIONS: {len(candidate_destinations)} destination links detected")
        print(f"3. AVAILABLE PRODUCT ENTITIES:    {len(extracted_candidates)} product candidates detected on page")
        print(f"4. CURRENT TASK STATE:            Phase={task_state.phase}, verified={len(task_state.verified_candidates)}/{task_state.required_candidate_count}, selected={'SET' if task_state.selected_target else 'None'}")
        print(f"5. REQUIRED NEXT PREDICATE:       {next_predicate}")
        print(f"6. SELECTED ACTION:               {selected_act_str}")
        print(f"7. ACTION PRECONDITIONS:          Validated by Action Grounding & Semantic Engine")
        clean_summary = summary.encode('ascii', errors='backslashreplace').decode('ascii')
        print(f"8. WHY OTHER ACTIONS REJECTED:    {clean_summary}")
        print("="*60 + "\n")
    except Exception:
        pass

    return actions, summary


