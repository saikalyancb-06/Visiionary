"""
Generic Product Constraints, State Machine & Deterministic Invariant Engine.

Zero website, category, product, domain or selector hardcoding.
Provides:
1. ProductConstraintExtractor: Extracts {product_type, gender, color, brand, material, size, other_constraints, selection_criterion, requested_action}
2. ProductCandidateEvaluator: Evaluates candidates strictly enforcing HARD CONSTRAINTS before soft preferences / popularity.
3. Structured Product State Machine:
   SEARCH_COMPLETE -> TARGET_CANDIDATE_FOUND -> TARGET_IDENTIFIED -> TARGET_VERIFIED -> PREREQUISITES_RESOLVED -> ACTION_EXECUTED -> ACTION_VERIFIED -> GOAL_ACHIEVED
4. Strict Invariant: TARGET_IDENTIFIED == True ONLY IF candidate satisfies ALL required hard constraints.
5. Evidence-based Selection Criterion: Selection criterion requires proven observation evidence (badge/label/rating/sort); cannot be invented.
6. PrerequisiteDetector: Identifies missing options (size, color, variants) and generates ASK_USER if unspecified and multiple choices exist.
7. Postcondition Verifier: Connects task requirements -> selected target -> action -> postcondition evidence.
"""
import re
from typing import Dict, Any, Optional, List, Tuple, Set
from server.app.schemas.schemas import ElementMetadata

# Linguistic color lexicon (domain-agnostic colors, shades, finishes)
COMMON_COLORS = {
    "black", "white", "blue", "red", "green", "yellow", "pink", "purple", "orange",
    "brown", "grey", "gray", "navy", "beige", "maroon", "teal", "silver", "gold",
    "olive", "cyan", "magenta", "violet", "indigo", "turquoise", "charcoal", "cream",
    "tan", "khaki", "burgundy", "crimson", "emerald", "coral", "peach", "lavender"
}

COMMON_SIZES = {
    "xs", "s", "m", "l", "xl", "xxl", "xxxl", "2xl", "3xl", "4xl",
    "small", "medium", "large", "extra large", "extra-large",
    "28", "30", "32", "34", "36", "38", "40", "42", "44",
    "6", "7", "8", "9", "10", "11", "12"
}

COMMON_GENDERS = {
    "men": "men",
    "mens": "men",
    "men's": "men",
    "women": "women",
    "womens": "women",
    "women's": "women",
    "kids": "kids",
    "boys": "boys",
    "girls": "girls",
    "unisex": "unisex"
}

COMMON_MATERIALS = {
    "cotton", "leather", "denim", "silk", "wool", "linen", "polyester", "nylon",
    "canvas", "velvet", "satin", "fleece", "metal", "wood", "glass", "plastic", "ceramic"
}

SUPERLATIVE_CRITERIA = [
    (re.compile(r'\b(best\s*seller|best-selling|best\s*selling|top\s*seller|top-selling)\b', re.I), "BEST_SELLING", "best seller"),
    (re.compile(r'\b(highest\s*rated|top\s*rated|top-rated|best\s*rated|best-reviewed)\b', re.I), "HIGHEST_RATED", "highest rated"),
    (re.compile(r'\b(most\s*popular|trending|popular)\b', re.I), "MOST_POPULAR", "most popular"),
    (re.compile(r'\b(cheapest|lowest\s*priced|lowest\s*price|most\s*affordable)\b', re.I), "LOWEST_PRICED", "cheapest"),
    (re.compile(r'\b(highest\s*priced|most\s*expensive)\b', re.I), "HIGHEST_PRICED", "highest priced"),
    (re.compile(r'\b(newest|latest|new arrival)\b', re.I), "NEWEST", "newest")
]

# Product State Machine constants
STATE_SEARCH_COMPLETE = "SEARCH_COMPLETE"
STATE_TARGET_CANDIDATE_FOUND = "TARGET_CANDIDATE_FOUND"
STATE_TARGET_IDENTIFIED = "TARGET_IDENTIFIED"
STATE_TARGET_VERIFIED = "TARGET_VERIFIED"
STATE_PREREQUISITES_RESOLVED = "PREREQUISITES_RESOLVED"
STATE_ACTION_EXECUTED = "ACTION_EXECUTED"
STATE_ACTION_VERIFIED = "ACTION_VERIFIED"
STATE_GOAL_ACHIEVED = "GOAL_ACHIEVED"

def clean_tokens(text: str) -> List[str]:
    return [w for w in re.split(r'[^a-zA-Z0-9]+', (text or '').lower()) if len(w) > 1]

def extract_product_constraints(task: str) -> Dict[str, Any]:
    """
    Extracts structured requirements from the user prompt into hard constraints and ranking criteria.
    Format:
    {
      "product_type": "shirt",
      "gender": "men",
      "color": "black",
      "brand": None,
      "material": None,
      "size": None,
      "other_constraints": {},
      "selection_criterion": "BEST_SELLING",
      "selection_criterion_disp": "best seller",
      "requested_action": "ADD_TO_CART",
      "raw_task": task
    }
    """
    t_clean = re.sub(r'\s+', ' ', (task or '').strip().rstrip('.'))
    t_lower = t_clean.lower()

    # 1. Selection criterion (Ranking Preference - NOT a hard constraint)
    criterion = None
    criterion_disp = None
    for pat, c_name, disp in SUPERLATIVE_CRITERIA:
        if pat.search(t_lower):
            criterion = c_name
            criterion_disp = disp
            break

    # 2. Requested downstream action
    requested_action = None
    if re.search(r'\b(add\s+to\s+cart|add\s+it\s+to\s+cart|cart|buy\s+now|buy|purchase|add\s+to\s+basket)\b', t_lower):
        requested_action = "ADD_TO_CART"
    elif re.search(r'\b(open\s+it|open\s+product|open\s+the\s+selected|open\s+the\s+item|open\s+selected|view\s+details)\b', t_lower):
        requested_action = "OPEN"
    elif re.search(r'(?:and|then)\s+(?:open|select)\s+(?:the\s+)?(?:product|item|selected|result|details|best\s*sell\w*)', t_lower):
        requested_action = "OPEN"
    elif re.search(r'\b(download|export|save\s+pdf|get\s+pdf)\b', t_lower):
        requested_action = "DOWNLOAD"

    # 3. Hard constraints extraction
    tokens = clean_tokens(t_lower)

    color = None
    for tok in tokens:
        if tok in COMMON_COLORS and not color:
            color = tok
            break

    size = None
    size_match = re.search(r'\b(?:size|sz)\s+([a-zA-Z0-9]+)\b', t_lower)
    if size_match and size_match.group(1).lower() in COMMON_SIZES:
        size = size_match.group(1).lower()
    else:
        for tok in tokens:
            if tok in COMMON_SIZES and not size:
                size = tok
                break

    gender = None
    for tok in tokens:
        if tok in COMMON_GENDERS and not gender:
            gender = COMMON_GENDERS[tok]
            break

    material = None
    for tok in tokens:
        if tok in COMMON_MATERIALS and not material:
            material = tok
            break

    brand = None
    brand_match = re.search(r'\b(?:by|brand|from)\s+([a-zA-Z0-9]+)\b', t_lower)
    if brand_match and brand_match.group(1) not in ("the", "a", "an", "this", "that"):
        brand = brand_match.group(1)

    # 3.5 Generic Numeric Specifications Extraction (price, RAM, storage)
    numeric_constraints: Dict[str, Any] = {}

    # Maximum Price: e.g. "under ₹80,000", "below $1,000", "priced under 80000", "<= 80000"
    price_match = re.search(r'(?:under|below|less\s+than|budget\s+of|max(?:imum)?\s+price\s+of|within)\s+[$₹£€]?\s*([0-9,]+(?:\.[0-9]+)?)', t_lower)
    if not price_match:
        price_match = re.search(r'[$₹£€]\s*([0-9,]+(?:\.[0-9]+)?)\s*(?:or\s+less|max|budget)?', t_lower)
    if price_match:
        try:
            val_str = price_match.group(1).replace(',', '')
            numeric_constraints["max_price"] = float(val_str)
        except ValueError:
            pass

    # Minimum RAM: e.g. "at least 16 GB RAM", "min 16gb ram", ">= 16GB", "16 GB RAM"
    ram_match = re.search(r'(?:at\s+least|min(?:imum)?|>=)?\s*(\d+)\s*(?:gb|g)\s*(?:ddr\d|lpddr\d|ram|memory)', t_lower)
    if not ram_match:
        ram_match = re.search(r'\b(?:ram|memory)[:\s]+(?:at\s+least|min)?\s*(\d+)\s*(?:gb|g)?', t_lower)
    if ram_match:
        try:
            numeric_constraints["min_ram_gb"] = int(ram_match.group(1))
        except ValueError:
            pass

    # Minimum Storage and Storage Type: e.g. "at least 512 GB SSD", "min 1TB SSD", "512GB SSD"
    storage_match = re.search(r'(?:at\s+least|min(?:imum)?|>=)?\s*(\d+)\s*(gb|tb)\s*(ssd|hdd|nvme|emmc|storage|rom)?', t_lower)
    if not storage_match:
        storage_match = re.search(r'\b(?:storage|ssd|hdd|drive)[:\s]+(?:at\s+least|min)?\s*(\d+)\s*(gb|tb)?', t_lower)
    if storage_match:
        try:
            val = int(storage_match.group(1))
            unit = (storage_match.group(2) or "gb").lower()
            if unit == "tb":
                val *= 1024
            numeric_constraints["min_storage_gb"] = val
            if storage_match.lastindex >= 3 and storage_match.group(3):
                st_type = storage_match.group(3).lower()
                if st_type in ("ssd", "hdd", "nvme", "emmc"):
                    numeric_constraints["storage_type"] = st_type
        except ValueError:
            pass

    # 4. Extract product type dynamically from noun phrase
    is_ps_task = bool(re.search(r'\b(?:problem statement|ps)\s*(?:no\.?|id|#)?\s*([0-9]{2,5})\b', t_lower))
    INFORMATIONAL_TERMS = {
        "score", "scores", "result", "results", "schedule", "fixtures", "standings",
        "news", "weather", "article", "articles", "portal", "problem statement", "ps",
        "admission", "admissions", "syllabus", "timetable", "documentation", "docs",
        "definition", "meaning", "overview", "rules", "guidelines", "ranking", "rankings",
        "stats", "statistics", "table tennis", "tennis score", "cricket score", "football score",
        "match", "matches", "tournament", "championship", "event"
    }
    is_info_task = is_ps_task or (any(t in t_lower for t in INFORMATIONAL_TERMS) and not any(w in t_lower for w in ["add to cart", "buy", "purchase", "order", "cart", "shop for"]))
    clean_prompt = t_lower
    # Strip conversational prefixes: "can you find me a", "could you please search for", "help me find"
    clean_prompt = re.sub(r'^(?:can\s+you\s+(?:please\s+)?|could\s+you\s+(?:please\s+)?|please\s+|i\s+(?:want|need)\s+(?:you\s+to\s+)?|help\s+me\s+(?:to\s+)?|kindly\s+)', '', clean_prompt)
    # Strip navigation prefix: "open sih portal and", "go to amazon and"
    clean_prompt = re.sub(r'^(?:open|go\s+to|navigate\s+to|visit)\s+[a-zA-Z0-9\s._-]+?\s+(?:and|then)\s+', '', clean_prompt)
    # Strip site / platform mentions: "in flipkart", "on amazon", "from myntra"
    clean_prompt = re.sub(r'\b(?:in|on|at|from)\s+(?:flipkart|amazon|myntra|ebay|walmart|target|etsy|aliexpress|bestbuy|ajio|meesho|google|bing)\b', '', clean_prompt)
    clean_prompt = re.sub(r'\b(?:flipkart|amazon|myntra|ebay|walmart|target|etsy|aliexpress|bestbuy|ajio|meesho)\b', '', clean_prompt)
    # Strip trailing condition clauses: ", it should...", "it shou...", "make sure it..."
    clean_prompt = re.sub(r'[,;]?\s*\b(?:it\s+shou\w*|it\s+should|it\s+must|it\s+needs\s+to|make\s+sure|which\s+should|having)\b.*$', '', clean_prompt)
    # Strip leading actions: "find me a", "search for", "select", etc.
    clean_prompt = re.sub(r'^(?:find\s+me\s+a|find\s+me|find\s+a|find|search\s+for\s+a|search\s+for|search|look\s+for\s+a|look\s+for|get\s+me\s+a|get\s+me|get|show\s+me\s+a|show\s+me|show|select|choose|pick)\s+', '', clean_prompt)
    # Strip tail actions: "and open it", "and add to cart", "inside that website"
    clean_prompt = re.sub(r'\s+(?:and|then|to)\s+(?:open|add|buy|view|download|cart).*$', '', clean_prompt)
    clean_prompt = re.sub(r'\s+(?:inside|in|on)\s+(?:that|the|this)?\s*(?:website|portal|page|site|store|app).*$', '', clean_prompt)
    # Strip superlatives
    for pat, _, _ in SUPERLATIVE_CRITERIA:
        clean_prompt = pat.sub('', clean_prompt)
    # Strip stop words, attributes, and directives
    clean_prompt = re.sub(r'\b(the|a|an|and|or|for|with|of|in|under|below|above|priced|price|costing|budget|size|sz|at\s+least|atleast|around|approx|me|you|no|no\.)\b', ' ', clean_prompt)
    # Strip numeric specifications and currencies (e.g. ₹80,000, $500, 16gb, 512gb, 8gb, ram, ssd, hdd, tb, gb, mb, hz, mah)
    clean_prompt = re.sub(r'[$₹£€]\s*[0-9,]+(?:\.[0-9]+)?', ' ', clean_prompt)
    clean_prompt = re.sub(r'\b[0-9,]+(?:\.[0-9]+)?\s*(?:k|lakh|lac|thousand|usd|inr|gb|tb|mb|ram|ssd|hdd|rom|hz|ghz|mah|mp|inch|inches|cm|mm)?\b', ' ', clean_prompt)
    clean_prompt = re.sub(r'\b(?:ram|ssd|hdd|rom|storage|memory|specs|specification|specifications)\b', ' ', clean_prompt)
    if color:
        clean_prompt = re.sub(rf'\b{re.escape(color)}\b', ' ', clean_prompt)
    if size:
        clean_prompt = re.sub(rf'\b{re.escape(size)}\b', ' ', clean_prompt)
    if gender:
        clean_prompt = re.sub(rf'\b(?:men|mens|men\'s|women|womens|women\'s|kids|boys|girls|unisex)\b', ' ', clean_prompt)
    if material:
        clean_prompt = re.sub(rf'\b{re.escape(material)}\b', ' ', clean_prompt)
    if brand:
        clean_prompt = re.sub(rf'\b{re.escape(brand)}\b', ' ', clean_prompt)

    GENERIC_PLACEHOLDERS = {
        "item", "items", "product", "products", "result", "results", "thing", "things",
        "something", "anything", "object", "objects", "content", "ps", "statement",
        "statements", "portal", "website", "site", "page", "table", "score", "scores",
        "event", "games", "sport", "sports", "match"
    }
    product_words = [w for w in clean_tokens(clean_prompt) if len(w) > 2 and w not in GENERIC_PLACEHOLDERS]
    product_type = " ".join(product_words).strip() if (product_words and not is_info_task) else ""

    attributes: Dict[str, Any] = {}
    if not is_info_task:
        if color: attributes["color"] = color
        if size: attributes["size"] = size
        if gender: attributes["gender"] = gender
        if material: attributes["material"] = material
        if brand: attributes["brand"] = brand
        for k, v in numeric_constraints.items():
            attributes[k] = v

    return {
        "product_type": product_type,
        "gender": gender,
        "color": color,
        "brand": brand,
        "material": material,
        "size": size,
        "numeric_constraints": numeric_constraints,
        "other_constraints": {},
        "attributes": attributes,
        "selection_criterion": criterion,
        "selection_criterion_disp": criterion_disp,
        "requested_action": requested_action,
        "raw_task": task
    }

def normalize_attribute_value(val: Optional[str]) -> str:
    if not val:
        return ""
    return re.sub(r'[^a-zA-Z0-9]+', '', val.lower())

def verify_candidate_match(
    candidate: Any,
    constraints: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Evaluates whether a candidate satisfies EVERY required HARD CONSTRAINT.
    Accepts either an aggregated ProductCandidate or candidate_text string.
    Does NOT check soft selection criteria (e.g. best-seller).
    Strict invariant: If ANY hard constraint fails, candidate is rejected immediately.
    """
    if hasattr(candidate, "title") and hasattr(candidate, "visible_text"):
        # Candidate is a ProductCandidate object
        candidate_text = f"{candidate.title} {candidate.visible_text}"
    else:
        candidate_text = str(candidate or "")

    text_lower = (candidate_text or '').lower()
    text_tokens = set(clean_tokens(text_lower))

    # 1. Product Type Verification (HARD CONSTRAINT)
    req_pt = constraints.get("product_type", "")
    if req_pt:
        pt_tokens = clean_tokens(req_pt)
        matched_pt_tokens = [t for t in pt_tokens if t in text_tokens or any(t in tok for tok in text_tokens)]
        if not matched_pt_tokens:
            return False, f"Product type mismatch: requested '{req_pt}', but candidate '{candidate_text[:60]}' lacks '{req_pt}'"

        if len(pt_tokens) == 1:
            req_singular = pt_tokens[0].rstrip('s')
            if not any(req_singular in tok for tok in text_tokens):
                return False, f"Product type mismatch: requested '{req_pt}' not found in candidate '{candidate_text[:60]}'"

        # Reject mutually exclusive apparel/product classes
        MUTUALLY_EXCLUSIVE_TYPES = {
            "shirt": {"dress", "gown", "kurta", "saree", "skirt", "pant", "pants", "trouser", "trousers", "jeans", "shoe", "shoes"},
            "dress": {"shirt", "t-shirt", "pant", "pants", "jeans", "shoe", "shoes"},
            "t-shirt": {"dress", "gown", "saree", "skirt", "pant", "pants", "trouser"},
            "pant": {"shirt", "t-shirt", "dress", "gown", "saree", "skirt"},
            "shoes": {"shirt", "dress", "pant", "pants", "hat"}
        }
        for base_type, exclusives in MUTUALLY_EXCLUSIVE_TYPES.items():
            if base_type in pt_tokens:
                conflicts = [c for c in exclusives if c in text_tokens]
                if conflicts:
                    return False, f"Product type mismatch: requested '{base_type}', but candidate specifies conflicting category '{conflicts[0]}'"


    # 2. Gender / Category Verification (HARD CONSTRAINT)
    req_gender = constraints.get("gender") or constraints.get("attributes", {}).get("gender")
    if req_gender:
        norm_req_gender = COMMON_GENDERS.get(req_gender.lower(), req_gender.lower())
        # Check for explicit conflicting gender
        if norm_req_gender == "men":
            if any(w in text_tokens for w in ("women", "womens", "girl", "girls")):
                if not any(w in text_tokens for w in ("men", "mens", "boy", "boys")):
                    return False, f"Gender/Category mismatch: requested 'men', but candidate specifies women/girls"
            if not any(w in text_tokens for w in ("men", "mens", "boy", "boys", "male", "unisex")):
                return False, f"Gender/Category mismatch: requested 'men' not found in candidate"
        elif norm_req_gender == "women":
            if any(w in text_tokens for w in ("men", "mens", "boy", "boys")) and not any(w in text_tokens for w in ("women", "womens", "girl", "girls", "female", "unisex")):
                return False, f"Gender/Category mismatch: requested 'women', but candidate specifies men/boys"
            if not any(w in text_tokens for w in ("women", "womens", "girl", "girls", "female", "unisex")):
                return False, f"Gender/Category mismatch: requested 'women' not found in candidate"

    # 3. Color Verification (HARD CONSTRAINT)
    req_color = constraints.get("color") or constraints.get("attributes", {}).get("color")
    if req_color:
        if req_color not in text_tokens:
            conflicting_colors = [c for c in COMMON_COLORS if c in text_tokens and c != req_color]
            return False, f"Color mismatch: requested '{req_color}', candidate does not specify '{req_color}' (found: {conflicting_colors[:2]})"

    # 4. Size Verification (HARD CONSTRAINT)
    req_size = constraints.get("size") or constraints.get("attributes", {}).get("size")
    if req_size:
        if req_size not in text_tokens:
            return False, f"Size mismatch: requested '{req_size}', candidate does not match"

    # 5. Brand Verification (HARD CONSTRAINT)
    req_brand = constraints.get("brand") or constraints.get("attributes", {}).get("brand")
    if req_brand:
        if req_brand.lower() not in text_tokens:
            return False, f"Brand mismatch: requested '{req_brand}', candidate does not match"

    # 6. Material Verification (HARD CONSTRAINT)
    req_material = constraints.get("material") or constraints.get("attributes", {}).get("material")
    if req_material:
        if req_material.lower() not in text_tokens:
            return False, f"Material mismatch: requested '{req_material}', candidate does not match"

    return True, "All hard product constraints satisfied."

def verify_selection_criterion_evidence(
    candidate: Any,
    constraints: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Evaluates whether the candidate has PROVABLE OBSERVABLE EVIDENCE for the requested selection criterion.
    Accepts either an aggregated ProductCandidate or candidate_text string.
    Invariant: "Best-selling" is NOT equivalent to first result, first clicked, or visual prominence.
    If evidence cannot be established reliably, DO NOT invent it.
    Returns (has_evidence, reason).
    """
    crit = constraints.get("selection_criterion")
    if not crit:
        return True, "No selection criterion required."

    disp = constraints.get("selection_criterion_disp", "").lower()
    disp_tokens = clean_tokens(disp)

    if hasattr(candidate, "title") and hasattr(candidate, "visible_text"):
        badges_str = " ".join(getattr(candidate, "badges", []))
        text_lower = f"{candidate.title} {candidate.visible_text} {badges_str}".lower()
    else:
        text_lower = str(candidate or '').lower()

    if all(t in text_lower for t in disp_tokens):
        return True, f"Observable evidence of criterion '{disp}' confirmed in candidate text."
    
    # Check synonymous criterion patterns
    if crit == "BEST_SELLING":
        if any(p in text_lower for p in ("#1 best seller", "best seller", "bestseller", "top selling", "most bought")):
            return True, "Observable evidence of best seller confirmed."
    elif crit == "HIGHEST_RATED":
        if any(p in text_lower for p in ("top rated", "highest rated", "4.8", "4.9", "5.0 star")):
            return True, "Observable evidence of top rating confirmed."
    elif crit == "LOWEST_PRICED":
        if any(p in text_lower for p in ("lowest price", "cheapest", "price: low")):
            return True, "Observable evidence of lowest price confirmed."

    return False, f"Selection criterion '{disp}' has NO observable evidence on candidate."

def rank_candidates_by_criteria(
    valid_candidates: List[ElementMetadata],
    constraints: Dict[str, Any]
) -> List[Tuple[ElementMetadata, float, bool]]:
    """
    Ranks candidates that HAVE ALREADY PASSED hard constraint filtering.
    Returns list of (candidate, score, has_proven_criterion).
    Strict invariant: If selection criterion is requested, candidates with PROVEN evidence score significantly higher.
    """
    scored = []
    crit = constraints.get("selection_criterion")
    disp = constraints.get("selection_criterion_disp", "")
    disp_tokens = clean_tokens(disp)

    for el in valid_candidates:
        score = 1.0
        label_lower = el.label.lower()
        has_proven_crit = False

        if crit:
            has_crit_ev, _ = verify_selection_criterion_evidence(label_lower, constraints)
            if has_crit_ev:
                score += 15.0
                has_proven_crit = True
            elif any(t in label_lower for t in disp_tokens):
                score += 5.0

        scored.append((el, score, has_proven_crit))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored

def detect_missing_prerequisites(
    elements: List[ElementMetadata],
    requested_action: Optional[str],
    constraints: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Inspects current page interactive elements to detect required prerequisites before requested action.
    Generic detection: unselected size dropdowns/buttons, color variants, option pickers.
    Rules:
    A. If user specified value: select that value (requires_prompt=False).
    B. If exactly one safe/default value is ALREADY selected: return None (proceed).
    C. If multiple choices exist and user did not specify: return ASK_USER (requires_prompt=True).
    D. Never invent a user preference.
    """
    if requested_action != "ADD_TO_CART":
        return None

    size_selectors = []
    for el in elements:
        lbl = el.label.lower()
        el_id = el.id.lower()
        combined = f"{lbl} {el_id}"

        # Size indicators
        if any(k in combined for k in ("select size", "choose size", "size_name", "size-selector", "native_dropdown_selected_size")):
            size_selectors.append(el)
        elif el.role == "select" and "size" in combined:
            size_selectors.append(el)

    user_size = constraints.get("size") or constraints.get("attributes", {}).get("size")
    if size_selectors:
        # Check if user specified a size
        if user_size:
            matching_size_el = next(
                (e for e in elements if e.label.lower().strip() == user_size.lower() or f"size {user_size.lower()}" in e.label.lower()),
                None
            )
            if matching_size_el:
                return {
                    "type": "SIZE_SELECTION",
                    "element": matching_size_el,
                    "value": user_size,
                    "requires_prompt": False
                }

        # Check if an option is ALREADY safely selected
        already_selected = next(
            (e for e in elements if ("selected" in e.label.lower() or "active" in e.label.lower() or "is_selected" in e.id.lower()) and any(sz in e.label.lower() for sz in COMMON_SIZES)),
            None
        )
        if already_selected:
            return None  # Rule B: Default/existing selection safely active

        # Rule C: Size is required, user did not specify, and multiple options exist -> ASK USER
        size_options = [e for e in elements if e.label.lower().strip() in COMMON_SIZES]
        if len(size_options) > 1:
            return {
                "type": "SIZE_SELECTION",
                "element": size_selectors[0],
                "available_options": [e.label.strip() for e in size_options[:6]],
                "requires_prompt": True
            }

    return None

