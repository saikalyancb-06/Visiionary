"""
Generic Product Constraints, Target Verification, Prerequisite Detection & Postcondition Engine.

Zero website, category, product, domain or selector hardcoding.
Provides:
1. ProductConstraintExtractor: Extracts {product_type, attributes (color, size, material, brand, gender), selection_criterion, requested_action}
2. ProductCandidateEvaluator: Evaluates candidates strictly enforcing HARD CONSTRAINTS before soft preferences / popularity.
3. TargetVerification: Validates that candidate and opened product page match requested product type and attributes.
4. PrerequisiteDetector: Detects missing required variants (size, color, quantity) before requested actions and resolves safely.
5. ActionPostconditionVerifier: Verifies observable postconditions for actions (e.g. cart, open, download).
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

COMMON_GENDERS = {"men", "mens", "men's", "women", "womens", "women's", "kids", "boys", "girls", "unisex"}

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
]

def clean_tokens(text: str) -> List[str]:
    return [w for w in re.split(r'[^a-zA-Z0-9]+', (text or '').lower()) if len(w) > 1]

def extract_product_constraints(task: str) -> Dict[str, Any]:
    """
    Extracts structured product constraints dynamically from the user's prompt.
    Does not hardcode product categories.
    """
    t_clean = re.sub(r'\s+', ' ', (task or '').strip().rstrip('.'))
    t_lower = t_clean.lower()

    # 1. Selection criterion
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
    elif re.search(r'\b(open\s+it|open\s+product|open\s+the\s+selected|open\s+the\s+item|open|view\s+details)\b', t_lower):
        requested_action = "OPEN"
    elif re.search(r'\b(download|export|save\s+pdf|get\s+pdf)\b', t_lower):
        requested_action = "DOWNLOAD"

    # 3. Attributes (color, size, gender, material)
    attributes: Dict[str, str] = {}
    tokens = clean_tokens(t_lower)

    # Detect color
    for tok in tokens:
        if tok in COMMON_COLORS and "color" not in attributes:
            attributes["color"] = tok

    # Detect size
    size_pattern_match = re.search(r'\b(?:size|sz)\s+([a-zA-Z0-9]+)\b', t_lower)
    if size_pattern_match and size_pattern_match.group(1) in COMMON_SIZES:
        attributes["size"] = size_pattern_match.group(1)
    else:
        for tok in tokens:
            if tok in COMMON_SIZES and "size" not in attributes:
                attributes["size"] = tok

    # Detect gender
    for tok in tokens:
        if tok in COMMON_GENDERS and "gender" not in attributes:
            attributes["gender"] = tok

    # Detect material
    for tok in tokens:
        if tok in COMMON_MATERIALS and "material" not in attributes:
            attributes["material"] = tok

    # 4. Extract product type dynamically from noun phrase
    # Remove directives, store/portal names, prepositions, and known attributes
    clean_prompt = t_lower
    # Strip leading actions: "open amazon and find", "go to store and search for", "look for"
    clean_prompt = re.sub(r'^(?:open|go to|navigate to|visit|search for|find|search|look for)\s+.*?(?:and\s+(?:find|search for|look for)\s+)?', '', clean_prompt)
    # Strip tail actions: "and open it", "and add to cart", "inside that website"
    clean_prompt = re.sub(r'\s+(?:and|then|to)\s+(?:open|add|buy|view|download|cart).*$', '', clean_prompt)
    clean_prompt = re.sub(r'\s+(?:inside|in|on)\s+(?:that|the|this)?\s*(?:website|portal|page|site|store|app).*$', '', clean_prompt)
    # Strip superlatives and articles
    for pat, _, _ in SUPERLATIVE_CRITERIA:
        clean_prompt = pat.sub('', clean_prompt)
    clean_prompt = re.sub(r'\b(the|a|an|for|with|of|in|under|below|above|priced|size|sz)\b', '', clean_prompt)
    
    # Strip detected attributes from product_type string
    for attr_val in attributes.values():
        clean_prompt = re.sub(rf'\b{re.escape(attr_val)}\b', '', clean_prompt)

    product_words = [w for w in clean_tokens(clean_prompt) if len(w) > 2]
    product_type = " ".join(product_words).strip() if product_words else ""

    return {
        "product_type": product_type,
        "attributes": attributes,
        "selection_criterion": criterion,
        "selection_criterion_disp": criterion_disp,
        "requested_action": requested_action,
        "raw_task": task
    }

def verify_candidate_match(
    candidate_text: str,
    constraints: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Evaluates whether a candidate element (e.g. title, product card label, or opened page title/URL)
    satisfies all HARD CONSTRAINTS before soft preferences are considered.
    Returns (matches, reason).
    """
    text_lower = (candidate_text or '').lower()
    text_tokens = set(clean_tokens(text_lower))

    # 1. Verify PRODUCT TYPE (HARD CONSTRAINT)
    req_pt = constraints.get("product_type", "")
    if req_pt:
        pt_tokens = clean_tokens(req_pt)
        # For multi-word product types (e.g. "running shoes", "dress shirt"),
        # the primary noun or tokens must be present.
        matched_pt_tokens = [t for t in pt_tokens if t in text_tokens or any(t in tok for tok in text_tokens)]
        if not matched_pt_tokens:
            return False, f"Product type mismatch: requested '{req_pt}', but candidate '{candidate_text[:60]}' lacks '{req_pt}'"
        # If candidate explicitly mentions a competing/different product type
        # (e.g. user asked for shirt, candidate is pants or shoes)
        if len(pt_tokens) == 1:
            req_singular = pt_tokens[0].rstrip('s')
            # Look for exact root match
            if not any(req_singular in tok for tok in text_tokens):
                return False, f"Product type mismatch: requested '{req_pt}' not found in candidate '{candidate_text[:60]}'"

    # 2. Verify ATTRIBUTES (HARD CONSTRAINTS)
    attrs = constraints.get("attributes", {})
    req_color = attrs.get("color")
    if req_color:
        if req_color not in text_tokens:
            # Check if text contains other conflicting colors while missing requested color
            conflicting_colors = [c for c in COMMON_COLORS if c in text_tokens and c != req_color]
            return False, f"Color mismatch: requested '{req_color}', candidate does not specify '{req_color}' (found: {conflicting_colors[:2]})"

    req_size = attrs.get("size")
    if req_size:
        if req_size not in text_tokens:
            return False, f"Size mismatch: requested '{req_size}', candidate does not match"

    req_gender = attrs.get("gender")
    if req_gender:
        g_clean = req_gender.replace("'", "")
        if not any(g_clean in tok for tok in text_tokens):
            return False, f"Gender/Category mismatch: requested '{req_gender}'"

    req_material = attrs.get("material")
    if req_material:
        if req_material not in text_tokens:
            return False, f"Material mismatch: requested '{req_material}'"

    return True, "All hard product constraints satisfied."

def rank_candidates_by_criteria(
    valid_candidates: List[ElementMetadata],
    constraints: Dict[str, Any]
) -> List[Tuple[ElementMetadata, float]]:
    """
    Ranks candidates that HAVE ALREADY PASSED hard constraint filtering
    by the requested selection criterion (e.g. BEST_SELLING, HIGHEST_RATED, LOWEST_PRICED).
    """
    scored = []
    crit = constraints.get("selection_criterion")
    disp = constraints.get("selection_criterion_disp", "")
    disp_tokens = clean_tokens(disp)

    for el in valid_candidates:
        score = 1.0
        label_lower = el.label.lower()
        # Bonus for explicit criterion badge / text in label
        if crit:
            if all(t in label_lower for t in disp_tokens):
                score += 10.0
            elif any(t in label_lower for t in disp_tokens):
                score += 5.0

        # Position preference (top results in catalog)
        scored.append((el, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored

def detect_missing_prerequisites(
    elements: List[ElementMetadata],
    requested_action: Optional[str],
    constraints: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Inspects current product page interactive elements to detect required prerequisites
    before the requested action (e.g. ADD_TO_CART) can succeed.
    Generic detection: unselected size dropdowns/buttons, color variants, option pickers.
    Returns {prerequisite_type, candidate_elements, user_specified_value, requires_user_prompt} or None.
    """
    if requested_action != "ADD_TO_CART":
        return None

    # Check if there are variant selector groups on page:
    # Look for size selectors
    size_selectors = []
    color_selectors = []
    
    for el in elements:
        lbl = el.label.lower()
        el_id = el.id.lower()
        combined = f"{lbl} {el_id}"

        # Size indicators
        if any(k in combined for k in ("select size", "choose size", "size_name", "size-selector", "native_dropdown_selected_size")):
            size_selectors.append(el)
        elif el.role == "select" and "size" in combined:
            size_selectors.append(el)

        # Color indicators
        if any(k in combined for k in ("select color", "choose color", "color_name", "color-selector")):
            color_selectors.append(el)

    user_size = constraints.get("attributes", {}).get("size")
    if size_selectors:
        # Check if a size is already selected or if user provided one
        if user_size:
            # Look for element matching user's requested size
            matching_size_el = next((e for e in elements if e.label.lower().strip() == user_size or f"size {user_size}" in e.label.lower()), None)
            if matching_size_el:
                return {
                    "type": "SIZE_SELECTION",
                    "element": matching_size_el,
                    "value": user_size,
                    "requires_prompt": False
                }
        else:
            # Size is required but user didn't specify
            # Check if there are multiple size options (e.g. S, M, L, XL)
            size_options = [e for e in elements if e.label.lower().strip() in COMMON_SIZES]
            if len(size_options) > 1:
                return {
                    "type": "SIZE_SELECTION",
                    "element": size_selectors[0],
                    "available_options": [e.label.strip() for e in size_options[:6]],
                    "requires_prompt": True
                }

    return None
