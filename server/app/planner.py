import re
from typing import List, Optional, Tuple
from server.app.schemas.schemas import SanitizedContextPackage, BrowserAction, ActionTarget, ActionValue, ElementMetadata

def normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', (text or '')).strip().lower()

def decompose_task_into_subgoals(task: str) -> List[str]:
    subgoals = []
    task_clean = task.strip().rstrip('.')
    
    # 1. Navigation / Site access
    nav_match = re.search(r'(?:open|go to|navigate to|visit)\s+([a-zA-Z0-9\s._-]+?)(?:\s+(?:and|then|to)\s+|$)', task_clean, re.I)
    if nav_match:
        site_target = nav_match.group(1).strip()
        subgoals.append(f"reach {site_target}")

    # 2. Search / Query intent
    search_match = re.search(r'(?:find|search for|search|look for|query)\s+([a-zA-Z0-9\s._-]+?)(?:\s+(?:and|then|to)\s+|$)', task_clean, re.I)
    if search_match:
        query_target = search_match.group(1).strip()
        subgoals.append(f"find {query_target}")

    # 3. Item identification (e.g. best seller, highest rated, specific id)
    if re.search(r'\bbest\s*seller\b', task_clean, re.I):
        subgoals.append("identify best seller")
    if re.search(r'\b(?:problem statement|ps)\s*([0-9]{2,5})\b', task_clean, re.I):
        m = re.search(r'\b(?:problem statement|ps)\s*([0-9]{2,5})\b', task_clean, re.I)
        subgoals.append(f"locate problem statement {m.group(1)}")

    # 4. Action execution (open product, download file, add to cart)
    if re.search(r'\b(?:open it|open product|open the selected|open the item|view details)\b', task_clean, re.I):
        subgoals.append("open the selected product")
    elif re.search(r'\b(?:download|export|save pdf|download it)\b', task_clean, re.I):
        subgoals.append("download problem statement")
    elif re.search(r'\b(?:add to cart|add it to cart|buy now)\b', task_clean, re.I):
        subgoals.append("add to cart")

    if not subgoals:
        subgoals = [f"execute {task_clean}"]
    return subgoals

def track_subgoal_progress(task: str, current_url: str, page_title: str, elements: List[ElementMetadata], history: List[dict]) -> Tuple[List[str], List[str], str]:
    subgoals = decompose_task_into_subgoals(task)
    completed = []
    url_lower = (current_url or "").lower()
    title_lower = (page_title or "").lower()
    page_text = f"{title_lower} {url_lower} " + " ".join(e.label.lower() for e in elements[:30])

    for sg in subgoals:
        sg_l = sg.lower()
        if sg_l.startswith("reach "):
            site = sg_l[6:].strip()
            # If current URL is no longer google search or blank, and contains site token or domain
            clean_site = re.sub(r'\b(the|portal|website|site)\b', '', site).strip()
            if clean_site and clean_site in url_lower and "google.com/search" not in url_lower and "bing.com/search" not in url_lower:
                completed.append(sg)
        elif sg_l.startswith("find "):
            query = sg_l[5:].strip()
            # Check if search action has been typed in history or query terms are on page
            has_typed = any(h.get("action") == "type" or h.get("action") == "search" for h in history if isinstance(h, dict))
            query_words = [w for w in clean_site_query(query).split() if len(w) > 2]
            if has_typed and any(w in page_text for w in query_words):
                completed.append(sg)
        elif sg_l == "identify best seller":
            has_bestseller = any("best seller" in e.label.lower() for e in elements)
            if has_bestseller:
                completed.append(sg)
        elif "problem statement" in sg_l and sg_l.startswith("locate "):
            num_m = re.search(r'([0-9]{2,5})', sg_l)
            if num_m and num_m.group(1) in page_text:
                completed.append(sg)
        elif sg_l == "open the selected product":
            # Completed only if current URL/title indicates an individual product page
            is_product_page = any(k in url_lower for k in ("/dp/", "/gp/product/", "/p/", "/item/", "/product/")) or any(k in title_lower for k in ("product details", "buy ", ": clothing"))
            if is_product_page and any(h.get("action") == "click" for h in history if isinstance(h, dict)):
                completed.append(sg)
        elif sg_l == "download problem statement":
            has_dl = any(h.get("action") == "download" or (h.get("action") == "click" and "download" in str(h)) for h in history if isinstance(h, dict))
            if has_dl:
                completed.append(sg)

    remaining = [sg for sg in subgoals if sg not in completed]
    remaining_str = remaining[0] if remaining else "All subgoals completed"
    return subgoals, completed, remaining_str

def clean_site_query(query: str) -> str:
    cleaned = re.sub(r'\b(the|best|seller|portal|website|page)\b', '', query, flags=re.I).strip()
    return cleaned

def extract_search_terms(task: str) -> List[str]:
    # Extract candidate query terms from task: e.g. "search for laptop", "find black shoes"
    m = re.search(r'(?:search for|find|search|look for|query)\s+["\']?([^"\']+)["\']?', task, re.IGNORECASE)
    if m:
        query = m.group(1).strip()
        # strip trailing directives like "and open it", "and add to cart", "inside that website"
        query = re.sub(r'\s+(?:inside|in|on)\s+(?:that|the|this)?\s*(?:website|portal|page|site|store|app).*$', '', query, flags=re.IGNORECASE)
        query = re.sub(r'\s+(?:and\s+.*|on\s+.*)$', '', query, flags=re.IGNORECASE)
        # strip leading superlatives if user said "find the best seller black shirt" -> "black shirt"
        query_cleaned = re.sub(r'\b(the\s+)?best\s*sell(?:er|ing)\s*', '', query, flags=re.IGNORECASE).strip()
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

def decide_next_action(payload: SanitizedContextPackage) -> Tuple[List[BrowserAction], str]:
    task = payload.instruction_sanitized
    task_lower = normalize(task)
    history = payload.history or []
    history_actions = [h.get("action") for h in history if isinstance(h, dict)]

    elements = [el for el in payload.elements if el.interactable and el.sensitivity != "sensitive_raw"]

    # 0. Universal Navigation Intent: "open X", "go to X", "navigate to X"
    nav_match = re.search(r'(?:open|go to|navigate to|visit)\s+([a-zA-Z0-9\s._-]+)', task_lower)
    clean_name = ""
    target_name = ""
    if nav_match:
        raw_query = nav_match.group(1).strip()
        # Clean query: strip words like "portal", "website", "the", "and search...", etc.
        clean_name = re.sub(r'^(the|a|an)\s+', '', raw_query, flags=re.IGNORECASE).strip()
        clean_name = re.sub(r'\s+(and|then|to|for)\s+.*$', '', clean_name, flags=re.IGNORECASE).strip()
        target_name = re.sub(r'\b(portal|website|page|site|webpage|online)\b', '', clean_name, flags=re.IGNORECASE).strip()

    has_navigated = any(h == "navigate" for h in history_actions)
    if nav_match and not has_navigated:
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

    # Autonomous Search Engine Result Selection: automatically enter top result link
    curr_url = (payload.page.url_sanitized or '').lower()
    if "google.com/search" in curr_url or "bing.com/search" in curr_url:
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
            # Check if there is a result matching the target destination
            target_match_links = []
            if clean_name:
                dest_term = clean_name.lower().split()[0]
                target_match_links = [el for el in result_links if dest_term in el.label.lower() or (el.href and dest_term in el.href.lower())]
            best_link = target_match_links[0] if target_match_links else result_links[0]

            # Requirement 5: Use observed href / OPEN_LINK if available
            if best_link.href and (best_link.href.startswith("http://") or best_link.href.startswith("https://")):
                return [
                    BrowserAction(type="open_link", target=ActionTarget(element_id=best_link.id), url=best_link.href),
                    BrowserAction(type="wait", milliseconds=500)
                ], f"Autonomously navigating via observed link '{best_link.label}' -> {best_link.href}."

            return [
                BrowserAction(type="click", target=ActionTarget(element_id=best_link.id)),
                BrowserAction(type="wait", milliseconds=500)
            ], f"Autonomously selected top organic search result: '{best_link.label}'."

    # 1. General Search Intent: "search for X", "find X", etc.
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

    # 3. Product / Item Selection Intent: e.g. "open it", "open the best seller", "open product"
    wants_to_open = any(w in task_lower for w in ["open it", "open product", "open the selected", "open", "view details"])
    if wants_to_open:
        # Check if we are already on the specific product details page
        is_product_page = any(k in curr_url for k in ("/dp/", "/gp/product/", "/p/", "/item/", "/product/")) or any(k in (payload.page.title_sanitized or '').lower() for k in ("product details", "buy ", ": clothing"))
        if not is_product_page:
            # 1. If best seller is specifically requested, prioritize best seller badge or card
            if "best seller" in task_lower:
                bestseller_els = [el for el in elements if "best seller" in el.label.lower()]
                if bestseller_els:
                    target_bs = bestseller_els[0]
                    return [
                        BrowserAction(type="click", target=ActionTarget(element_id=target_bs.id)),
                        BrowserAction(type="wait", milliseconds=500)
                    ], f"Located 'Best Seller' product card ('{target_bs.label}'). Dispatched click to open item."

            # 2. Look for product title links matching query words (e.g. black shirt)
            query_words = [w for w in search_terms[0].split() if len(w) > 2] if search_terms else []
            if query_words:
                product_links = [
                    el for el in elements 
                    if el.role in ("a", "link", "h2", "h3") 
                    and any(w in el.label.lower() for w in query_words)
                    and not any(x in el.label.lower() for x in ("filter", "sort", "next", "customer review"))
                ]
                if product_links:
                    chosen_prod = product_links[0]
                    return [
                        BrowserAction(type="click", target=ActionTarget(element_id=chosen_prod.id)),
                        BrowserAction(type="wait", milliseconds=500)
                    ], f"Selected top matching product link ('{chosen_prod.label[:40]}'). Dispatched click to open product."

    # 4. Add to Cart / Shopping Intent
    if any(k in task_lower for k in ("cart", "buy", "purchase", "add")):
        cart_targets = [el for el in elements if any(k in normalize(el.label) for k in ("add to cart", "add", "cart", "buy now"))]
        if cart_targets:
            target = cart_targets[0]
            return [
                BrowserAction(type="click", target=ActionTarget(element_id=target.id)),
                BrowserAction(type="wait", milliseconds=500)
            ], f"Located actionable shopping element '{target.label}' (id={target.id}). Dispatched click."

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

    # 9. Fallback: Wait or yield to independent goal verifier
    if history_actions:
        return [BrowserAction(type="wait", milliseconds=300)], "Action completed; yielding to independent goal verifier."
    
    first = elements[0]
    return [
        BrowserAction(type="click", target=ActionTarget(element_id=first.id)),
        BrowserAction(type="wait", milliseconds=300)
    ], f"Defaulted to first actionable element '{first.label}' (id={first.id})."
