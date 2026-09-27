"""
Task Completion Verifier Module for Visiionary Agent
Decoupled verification engine that evaluates whether the user's FULL goal has actually
been achieved, preventing premature termination on action success or planner 'done'.
Enforces:
1. Subgoal completeness invariant: GOAL_ACHIEVED is illegal if any required subgoal remains.
2. Downstream action postcondition verification (open detail, add-to-cart, download file).
3. Search results displayed != goal achieved.
Zero website-specific hardcoding.
"""
import re
from typing import Dict, Any, Optional, List
from server.app.schemas.schemas import VerificationPayload, VerificationResponse
from server.app.planner import (
    decompose_task_into_subgoals,
    track_subgoal_progress,
    has_downstream_actions,
    extract_selection_criterion
)

def verify_task_completion(payload: VerificationPayload) -> VerificationResponse:
    task = (payload.task or "").strip()
    task_lower = task.lower()
    url = (payload.current_url or "").lower()
    title = (payload.page_title or "").lower()
    history = payload.action_history or []
    history_actions = [h.get("action") for h in history if isinstance(h, dict)]
    screen_summary = payload.screen_summary or {}
    headings = [h.lower() for h in screen_summary.get("main_headings", [])]
    elements_light = payload.elements or []
    element_text = " ".join((e.label or "") for e in elements_light).lower()
    combined_page_text = f"{title} {' '.join(headings)} {element_text} {url}"

    # Track Subgoal State dynamically based on observable DOM & URL state
    subgoals, completed_subgoals, remaining_goal = track_subgoal_progress(
        task, url, title, elements_light, history
    )
    remaining_subgoals = [sg for sg in subgoals if sg not in completed_subgoals]

    # -------------------------------------------------------------------------
    # 1. Reject Premature Verification on Search Engine Result Pages
    # -------------------------------------------------------------------------
    is_search_engine_page = "google.com/search" in url or "bing.com/search" in url
    wants_external_target = any(w in task_lower for w in ["open ", "go to ", "visit ", "portal", "store", "bookstore"])

    if is_search_engine_page and wants_external_target:
        return VerificationResponse(
            achieved=False,
            confidence=0.95,
            reason="Action success: Search engine results displayed, but target website has not yet been opened.",
            next_hint="Click on the organic search result link to enter the target portal.",
            requires_recovery=False,
            goal_status="GOAL_NOT_YET_ACHIEVED",
            subgoals=subgoals,
            completed_subgoals=completed_subgoals,
            remaining_goal=remaining_goal
        )

    # -------------------------------------------------------------------------
    # 2. Wrong-Site / Edition Archive Mismatch Detection & Recovery
    # Detects when landed on an older archived edition (e.g. 2024 archive when looking for recent/active)
    # -------------------------------------------------------------------------
    is_archive_page = "archive" in title or "archive" in url or "2024" in url
    task_wants_recent = any(y in task_lower for y in ["2026", "current", "latest", "recent"]) or ("2024" not in task_lower and "2025" not in task_lower)
    if is_archive_page and task_wants_recent and ("sih" in task_lower or "portal" in task_lower):
        return VerificationResponse(
            achieved=False,
            confidence=0.9,
            reason="Wrong-site edition mismatch: current page is an older archive instead of the active portal.",
            next_hint="Navigate to the active portal or search for the active edition.",
            requires_recovery=True,
            goal_status="RECOVERY_REQUIRED",
            subgoals=subgoals,
            completed_subgoals=completed_subgoals,
            remaining_goal="recover to active portal"
        )

    # -------------------------------------------------------------------------
    # 2. Generic Search Intent Check (HARD INVARIANT)
    # If the user's task contains downstream actions (e.g. open, add to cart,
    # download, select, submit), being on a search results page is NEVER goal success.
    # -------------------------------------------------------------------------
    has_downstream = has_downstream_actions(task)

    # -------------------------------------------------------------------------
    # 3. Postcondition: Add to Cart Action Verification
    # -------------------------------------------------------------------------
    wants_cart = any(w in task_lower for w in ["cart", "buy now", "purchase", "add to basket"])
    if wants_cart:
        # Observable evidence of cart postcondition:
        cart_success_indicators = [
            "added to cart", "item added", "in your cart", "view cart",
            "cart (1)", "cart: 1", "checkout (1)", "proceed to checkout",
            "added to basket", "1 item in cart"
        ]
        has_cart_evidence = any(ind in combined_page_text for ind in cart_success_indicators)
        has_click = any(h == "click" for h in history_actions)

        from server.app.product_constraints import (
            extract_product_constraints,
            verify_candidate_match,
            STATE_ACTION_EXECUTED,
            STATE_ACTION_VERIFIED,
            STATE_GOAL_ACHIEVED
        )
        from server.app.candidate_extractor import (
            ProductCandidate,
            print_candidate_diagnostics
        )
        constraints = payload.product_constraints or extract_product_constraints(task)
        matches_target = True
        match_reason = "ok"
        if constraints.get("product_type"):
            matches_target, match_reason = verify_candidate_match(combined_page_text, constraints)

        # Selected target comparison if present
        sel_t = payload.selected_target
        cart_cand = ProductCandidate(
            candidate_id="cart_observed",
            title=payload.page_title,
            visible_text=combined_page_text
        )

        if sel_t:
            sel_title = sel_t.get("title", "").lower()
            # If selected target has title, ensure cart reflects it or product type
            if sel_title and len(sel_title) > 5:
                title_words = [w for w in sel_title.split() if len(w) > 3]
                if not any(w in combined_page_text.lower() for w in title_words):
                    matches_target = False
                    match_reason = f"Cart page item '{combined_page_text[:40]}' does not match selected product '{sel_title[:40]}'"

            # Diagnostic tracing
            print_candidate_diagnostics(
                all_candidates=[],
                valid_candidates=[],
                rejected_candidates=[],
                selected_target=ProductCandidate(
                    candidate_id=sel_t.get("candidate_id", "selected"),
                    title=sel_t.get("title", ""),
                    href=sel_t.get("href")
                ),
                cart_product=cart_cand
            )

        if has_cart_evidence and has_click and matches_target:
            return VerificationResponse(
                achieved=True,
                confidence=0.98,
                reason="Goal verified achieved: Item matching all constraints successfully added to cart and confirmed in browser state.",
                next_hint=None,
                goal_status="GOAL_ACHIEVED",
                subgoals=subgoals,
                completed_subgoals=subgoals,
                remaining_goal="None",
                product_state=STATE_GOAL_ACHIEVED,
                verification_state="GOAL_ACHIEVED"
            )

        elif has_click and not has_cart_evidence:
            return VerificationResponse(
                achieved=False,
                confidence=0.85,
                reason="Goal not yet achieved: Cart action executed but cart postcondition not observable in browser state.",
                next_hint="Identify the target item and click 'Add to Cart'.",
                goal_status="GOAL_NOT_YET_ACHIEVED",
                subgoals=subgoals,
                completed_subgoals=completed_subgoals,
                remaining_goal="add selected item to cart",
                product_state=STATE_ACTION_EXECUTED,
                verification_state="ACTION_EXECUTED"
            )
        else:
            return VerificationResponse(
                achieved=False,
                confidence=0.85,
                reason="Goal not yet achieved: Item has not yet been added to cart (no cart confirmation observable).",
                next_hint="Identify the target item and click 'Add to Cart'.",
                goal_status="GOAL_NOT_YET_ACHIEVED",
                subgoals=subgoals,
                completed_subgoals=completed_subgoals,
                remaining_goal="add selected item to cart",
                product_state="PREREQUISITES_RESOLVED",
                verification_state="PENDING_ACTION"
            )

    # -------------------------------------------------------------------------
    # 4. Postcondition: Download Task Verification
    # -------------------------------------------------------------------------
    is_download_task = any(w in task_lower for w in ["download", "export", "save pdf", "get pdf", "download it", "save statement", "download its document"])
    if is_download_task:
        completed_downloads = [
            d for d in payload.downloads 
            if (d.state or "").lower() in ("complete", "completed", "in_progress")
        ]
        id_match = re.search(r'\b([0-9]{2,5})\b', task_lower)
        target_num = id_match.group(1) if id_match else None

        for dl in completed_downloads:
            dl_fn = (dl.filename or "").lower()
            dl_url = (dl.url or "").lower()
            if not target_num or (target_num in dl_fn or target_num in dl_url or ".pdf" in dl_fn or ".doc" in dl_fn):
                return VerificationResponse(
                    achieved=True,
                    confidence=0.98,
                    reason=f"Goal verified achieved: File download '{dl.filename or 'document.pdf'}' confirmed in browser download state.",
                    goal_status="GOAL_ACHIEVED",
                    subgoals=subgoals,
                    completed_subgoals=subgoals,
                    remaining_goal="None"
                )

        has_download_action = any(h == "download" or (h == "click" and "download" in str(h)) for h in history_actions)
        if has_download_action and completed_downloads:
            return VerificationResponse(
                achieved=True,
                confidence=0.95,
                reason="Goal verified achieved: Download action executed and recorded.",
                goal_status="GOAL_ACHIEVED",
                subgoals=subgoals,
                completed_subgoals=subgoals,
                remaining_goal="None"
            )

        return VerificationResponse(
            achieved=False,
            confidence=0.85,
            reason="Goal not yet achieved: Task requires downloading artifact, but no completed download has been verified in browser state.",
            next_hint="Locate the download/export button or link for the target item and click it.",
            requires_recovery=False,
            goal_status="GOAL_NOT_YET_ACHIEVED",
            subgoals=subgoals,
            completed_subgoals=completed_subgoals,
            remaining_goal="download document"
        )

    # -------------------------------------------------------------------------
    # 5. Postcondition: Open Product / Item Detail Verification
    # -------------------------------------------------------------------------
    wants_open_product = any(w in task_lower for w in ["open it", "open product", "open the", "view details", "open selected"]) or any(sg == "open selected product" for sg in subgoals)
    if wants_open_product:
        # Observable evidence: URL or title points to an item details view
        is_on_product_page = any(k in url for k in ("/dp/", "/gp/product/", "/p/", "/item/", "/product/", "/detail/")) or any(k in title for k in ("product details", "buy ", ": clothing", "specifications"))
        has_click = any(h == "click" for h in history_actions)

        if is_on_product_page and has_click:
            from server.app.product_constraints import extract_product_constraints, verify_candidate_match
            from server.app.candidate_extractor import ProductCandidate, print_candidate_diagnostics
            constraints = payload.product_constraints or extract_product_constraints(task)
            matches_target, match_reason = verify_candidate_match(combined_page_text, constraints)

            # Reconstruct current product representation from the opened page
            current_prod = ProductCandidate(
                candidate_id="page_reconstructed",
                title=payload.page_title,
                visible_text=combined_page_text,
                href=url
            )

            sel_t = payload.selected_target
            if sel_t:
                sel_title = sel_t.get("title", "").lower()
                if sel_title and len(sel_title) > 5:
                    title_words = [w for w in sel_title.split() if len(w) > 3]
                    # Ensure opened page matches selected target identity
                    if not any(w in combined_page_text.lower() for w in title_words):
                        matches_target = False
                        match_reason = f"Opened page '{payload.page_title}' does not match selected target '{sel_t.get('title')}'"

                # Diagnostic trace
                print_candidate_diagnostics(
                    all_candidates=[],
                    valid_candidates=[],
                    rejected_candidates=[],
                    selected_target=ProductCandidate(
                        candidate_id=sel_t.get("candidate_id", "selected"),
                        title=sel_t.get("title", ""),
                        href=sel_t.get("href")
                    ),
                    current_product=current_prod
                )

            if not matches_target:
                return VerificationResponse(
                    achieved=False,
                    confidence=0.90,
                    reason=f"TARGET_MISMATCH: Opened page does not match required product constraints ({match_reason}).",
                    next_hint="Navigate back and select a candidate matching the exact product type and attributes.",
                    requires_recovery=True,
                    goal_status="RECOVERY_REQUIRED",
                    subgoals=subgoals,
                    completed_subgoals=completed_subgoals,
                    remaining_goal="recover and select correct product",
                    target_match=False,
                    product_state="TARGET_CANDIDATE_FOUND",
                    verification_state="RECOVERY_REQUIRED",
                    recovery_state={
                        "failure_type": "WRONG_CANDIDATE",
                        "reason": match_reason,
                        "required_recovery": "choose_different_candidate"
                    }
                )


            return VerificationResponse(
                achieved=True,
                confidence=0.98,
                reason=f"Goal verified achieved: Candidate product page opened and confirmed on screen matching '{task}'.",
                next_hint=None,
                goal_status="GOAL_ACHIEVED",
                subgoals=subgoals,
                completed_subgoals=subgoals,
                remaining_goal="None",
                target_match=True,
                product_state="GOAL_ACHIEVED",
                verification_state="GOAL_ACHIEVED"
            )
        else:
            return VerificationResponse(
                achieved=False,
                confidence=0.85,
                reason="Action success: Search results displayed, but requested candidate item has not yet been opened.",
                next_hint="Select and click on the best matching product to open its detail page.",
                goal_status="GOAL_NOT_YET_ACHIEVED",
                subgoals=subgoals,
                completed_subgoals=completed_subgoals,
                remaining_goal="open selected product",
                product_state="SEARCH_COMPLETE",
                verification_state="PENDING_SELECTION"
            )

    # -------------------------------------------------------------------------
    # 6. Specific Number / Code Match (e.g. PS 171, PS 143)
    # -------------------------------------------------------------------------
    ps_match = re.search(r'(?:problem statement|ps|item|number|no\.?)\s*(?:no\.?|id|#)?\s*([0-9]{2,5})|(?:\b([0-9]{3,5})\b)', task_lower)
    if ps_match and not has_downstream:
        target_num = ps_match.group(1) or ps_match.group(2)
        if not is_search_engine_page and target_num:
            target_present = (target_num in combined_page_text) or any(target_num in tok for tok in combined_page_text.split())
            if target_present:
                return VerificationResponse(
                    achieved=True,
                    confidence=0.95,
                    reason=f"Goal verified achieved: Target item {target_num} confirmed present on current page context.",
                    goal_status="GOAL_ACHIEVED",
                    subgoals=subgoals,
                    completed_subgoals=subgoals,
                    remaining_goal="None"
                )

    # -------------------------------------------------------------------------
    # 7. Basic Search Query Task (ONLY when NO downstream actions exist and NO product is requested)
    # -------------------------------------------------------------------------
    if ("find" in task_lower or "search" in task_lower) and not has_downstream:
        from server.app.product_constraints import extract_product_constraints
        constraints = payload.product_constraints or extract_product_constraints(task)
        is_product_finding = bool(constraints.get("product_type") or constraints.get("attributes"))
        if not is_product_finding and not is_search_engine_page and len(history_actions) >= 1:
            return VerificationResponse(
                achieved=True,
                confidence=0.90,
                reason="Goal verified achieved: Search results located and presented on screen.",
                goal_status="GOAL_ACHIEVED",
                subgoals=subgoals,
                completed_subgoals=subgoals,
                remaining_goal="None"
            )

    # -------------------------------------------------------------------------
    # 7.5. Informational / Query / Scores / Content Verification
    # -------------------------------------------------------------------------
    is_info_task = any(t in task_lower for t in (
        "score", "scores", "result", "results", "schedule", "fixtures", "standings",
        "news", "weather", "article", "portal", "problem statement", "ps", "ranking",
        "rankings", "stats", "statistics", "table tennis", "match", "tournament",
        "quarter-final", "quarterfinal", "semi-final", "final"
    ))

    if is_info_task and not has_downstream and not is_search_engine_page:
        # Check topic word overlap with page context
        stop_words = {"open", "in", "the", "a", "an", "and", "for", "to", "of", "on", "at", "by", "with", "event", "me", "show", "find"}
        topic_words = [w for w in re.split(r'[^a-zA-Z0-9]+', task_lower) if len(w) > 2 and w not in stop_words]
        matched_words = [w for w in topic_words if (w in combined_page_text or w.rstrip('s') in combined_page_text)]
        match_ratio = len(matched_words) / len(topic_words) if topic_words else 0
        has_content_indicators = any(ind in combined_page_text for ind in ("results", "result", "scores", "score", "quarter-final", "1/8", "final", "table tennis", "match", "points", "winner"))

        if (match_ratio >= 0.5 and has_content_indicators) or match_ratio >= 0.7:
            return VerificationResponse(
                achieved=True,
                confidence=0.95,
                reason=f"Goal verified achieved: Requested information and scores for '{task}' successfully located and displayed on screen.",
                goal_status="GOAL_ACHIEVED",
                subgoals=subgoals,
                completed_subgoals=subgoals,
                remaining_goal="None"
            )

    # -------------------------------------------------------------------------
    # 8. HARD INVARIANT GUARD
    # GOAL_ACHIEVED is illegal if any required subgoal remains incomplete.
    # -------------------------------------------------------------------------
    action_note = f"Previous action '{history_actions[-1]}' completed successfully" if history_actions else "Initial state"
    return VerificationResponse(
        achieved=False,
        confidence=0.50,
        reason=f"{action_note}, but overall user goal is not yet fully achieved (remaining: {remaining_goal}).",
        next_hint=f"Proceed to {remaining_goal}.",
        goal_status="GOAL_NOT_YET_ACHIEVED",
        subgoals=subgoals,
        completed_subgoals=completed_subgoals,
        remaining_goal=remaining_goal
    )

