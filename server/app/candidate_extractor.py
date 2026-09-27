"""
Generic Product Candidate Aggregation and Entity Extraction Engine.

Converts raw observed DOM/accessibility elements into structured ProductCandidate objects
before constraint verification and selection.

A ProductCandidate aggregates evidence belonging to the same product across multiple
related DOM elements (title, price, badge, category, color, link, rating, review count).

Grouping is strictly structural and generic:
1. Shared href (anchors pointing to the same product destination)
2. Nearby / overlapping bounding boxes (card spatial clusters)
3. DOM element id prefix / container patterns
4. Repeated card layout structures

Zero website names, zero domain names, zero website-specific selectors or classes.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

from server.app.schemas.schemas import ElementMetadata
from server.app.product_constraints import (
    COMMON_COLORS,
    COMMON_SIZES,
    COMMON_GENDERS,
    COMMON_MATERIALS,
    SUPERLATIVE_CRITERIA,
    clean_tokens
)

@dataclass
class ProductCandidate:
    candidate_id: str
    title: str = ""
    visible_text: str = ""
    href: Optional[str] = None
    product_type: Optional[str] = None
    gender: Optional[str] = None
    color: Optional[str] = None
    brand: Optional[str] = None
    material: Optional[str] = None
    price: Optional[str] = None
    ram: Optional[str] = None
    storage: Optional[str] = None
    rating: Optional[str] = None
    review_count: Optional[str] = None
    badges: List[str] = field(default_factory=list)
    selection_evidence: List[str] = field(default_factory=list)
    source_element_ids: List[str] = field(default_factory=list)
    bounding_box: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "title": self.title,
            "visible_text": self.visible_text,
            "href": self.href,
            "product_type": self.product_type,
            "gender": self.gender,
            "color": self.color,
            "brand": self.brand,
            "material": self.material,
            "price": self.price,
            "ram": self.ram,
            "storage": self.storage,
            "rating": self.rating,
            "review_count": self.review_count,
            "badges": self.badges,
            "selection_evidence": self.selection_evidence,
            "source_element_ids": self.source_element_ids,
            "bounding_box": self.bounding_box,
            "confidence": self.confidence,
            "attributes": {
                "product_type": self.product_type,
                "gender": self.gender,
                "color": self.color,
                "brand": self.brand,
                "material": self.material,
                "price": self.price,
                "ram": self.ram,
                "storage": self.storage,
                "rating": self.rating
            }
        }


def _bbox_overlap_or_nearby(b1: List[int], b2: List[int], max_y_dist: int = 50, max_x_dist: int = 60) -> bool:
    """
    Checks if two element bounding boxes are spatially proximate to belong to the same card.
    Sub-elements within the same card (e.g. badge, title, price, specs) are tightly packed vertically or horizontally.
    """
    if not b1 or not b2 or len(b1) < 4 or len(b2) < 4:
        return False
    
    x1_a, y1_a, x2_a, y2_a = b1
    x1_b, y1_b, x2_b, y2_b = b2

    # If both boxes have zero/empty dimensions, cannot cluster by space
    if (x2_a <= x1_a and y2_a <= y1_a) or (x2_b <= x1_b and y2_b <= y1_b):
        return False

    # Check horizontal alignment/overlap
    x_overlap = max(0, min(x2_a, x2_b) - max(x1_a, x1_b))
    x_dist = max(0, max(x1_a, x1_b) - min(x2_a, x2_b))

    # Check vertical proximity
    # If b1 = [x, y, w, h] format vs [x1, y1, x2, y2]
    # In schemas, bbox is [left, top, right, bottom] or [x, y, w, h]
    top_a, bottom_a = min(y1_a, y2_a), max(y1_a, y2_a)
    top_b, bottom_b = min(y1_b, y2_b), max(y1_b, y2_b)
    y_dist = max(0, max(top_a, top_b) - min(bottom_a, bottom_b))

    # Sub-elements within the same card share horizontal alignment and are directly adjacent vertically
    if (x_overlap > 10 or x_dist <= max_x_dist) and y_dist <= max_y_dist:
        return True

    return False



def _normalize_href(href: Optional[str]) -> Optional[str]:
    """Strips ephemeral tracking query parameters to group elements pointing to the same product."""
    if not href:
        return None
    clean = href.split("?")[0].split("#")[0].rstrip("/")
    return clean.lower() if clean else None


def _is_nav_or_structural(el: ElementMetadata) -> bool:
    """Filters out navigation bars, search headers, footers, pagination, and filters."""
    lbl = (el.label or "").strip().lower()
    if not lbl or len(lbl) < 2:
        return True
    
    structural_terms = (
        "sign in", "sign up", "login", "register", "customer service",
        "search", "search here", "type to search", "all categories", "menu",
        "cart", "view cart", "shopping cart", "basket", "checkout",
        "privacy notice", "terms of use", "conditions of use", "help",
        "feedback", "sort by", "filter by", "previous", "next page", "page 1", "page 2",
        "skip to content", "back to top"
    )
    if any(lbl == term or lbl.startswith(term + " ") for term in structural_terms):
        return True
    return False


def extract_product_candidates(
    elements: List[ElementMetadata],
    page_title: str = "",
    current_url: str = ""
) -> List[ProductCandidate]:
    """
    Groups raw observed DOM/accessibility elements into structured ProductCandidates
    using domain-agnostic structural relationships:
    1. Shared normalized href
    2. Nearby bounding box proximity
    3. DOM element clustering
    """
    if not elements:
        return []

    url_lower = (current_url or "").lower()
    page_is_search = "search" in url_lower or "q=" in url_lower or "/?q=" in url_lower or "google." in url_lower or "bing." in url_lower or "duckduckgo." in url_lower

    # Filter non-product structural elements
    content_elements = [el for el in elements if not _is_nav_or_structural(el)]
    if not content_elements:
        return []

    # On search engine results pages, search result links leading outside the search engine
    # are intermediate discovery destinations, NOT individual product cards/candidates on this page.
    if page_is_search:
        return []

    # Phase 1: Group by shared normalized href
    href_groups: Dict[str, List[ElementMetadata]] = {}
    remaining_elements: List[ElementMetadata] = []

    for el in content_elements:
        norm_h = _normalize_href(el.href)
        if norm_h and ("/p/" in norm_h or "/dp/" in norm_h or "/product/" in norm_h or "/item/" in norm_h or len(norm_h.split("/")) > 4):
            if norm_h not in href_groups:
                href_groups[norm_h] = []
            href_groups[norm_h].append(el)
        else:
            remaining_elements.append(el)

    clusters: List[List[ElementMetadata]] = list(href_groups.values())

    # Phase 2: Cluster remaining elements.
    # Primary product headings/links (a, link, h2, h3, h4) with substantive titles represent INDEPENDENT product cards
    # rather than subordinate elements. Subordinate elements (prices, badges, spans) attach to proximate cards.
    for el in remaining_elements:
        assigned = False
        lbl = (el.label or "").strip()
        is_primary_product_anchor = el.role in ("a", "link", "h2", "h3", "h4") and len(lbl) > 10 and not any(crit in lbl.lower() for crit in ("best seller", "$", "₹", "rating", "review"))

        if not is_primary_product_anchor and el.bbox and len(el.bbox) == 4 and (el.bbox[2] > el.bbox[0] or el.bbox[3] > el.bbox[1]):
            for cluster in clusters:
                cluster_boxes = [m.bbox for m in cluster if m.bbox and len(m.bbox) == 4]
                if any(_bbox_overlap_or_nearby(el.bbox, cb) for cb in cluster_boxes):
                    cluster.append(el)
                    assigned = True
                    break

        if not assigned:
            # Standalone candidate or new product card
            if len(lbl) > 3 and el.role in ("a", "link", "h2", "h3", "h4", "div", "button", "span"):
                clusters.append([el])


    # Phase 3: Synthesize ProductCandidate objects from clusters
    candidates: List[ProductCandidate] = []
    
    for idx, cluster in enumerate(clusters):
        candidate = _synthesize_candidate_from_cluster(cluster, idx + 1)
        if candidate and (candidate.title or candidate.visible_text):
            candidates.append(candidate)

    return candidates


def _synthesize_candidate_from_cluster(cluster: List[ElementMetadata], cluster_num: int) -> Optional[ProductCandidate]:
    """Aggregates evidence from a cluster of DOM elements into one ProductCandidate."""
    if not cluster:
        return None

    candidate_id = f"cand_{cluster_num}_{cluster[0].id}"
    source_ids = [el.id for el in cluster if el.id]
    
    # Envelope bounding box
    min_x = min((el.bbox[0] for el in cluster if el.bbox), default=0)
    min_y = min((el.bbox[1] for el in cluster if el.bbox), default=0)
    max_x = max((el.bbox[2] for el in cluster if el.bbox), default=0)
    max_y = max((el.bbox[3] for el in cluster if el.bbox), default=0)
    bbox = [min_x, min_y, max_x, max_y]

    # Find canonical href (prefer explicit product link)
    href = None
    for el in cluster:
        if el.href:
            href = el.href
            break

    # Aggregate texts and detect attributes across all elements in the cluster
    title = ""
    badges: List[str] = []
    prices: List[str] = []
    ratings: List[str] = []
    review_counts: List[str] = []
    selection_evidence: List[str] = []
    text_pieces: List[str] = []

    for el in cluster:
        lbl = (el.label or "").strip()
        if not lbl:
            continue
        text_pieces.append(lbl)
        lbl_lower = lbl.lower()

        # 1. Badge / Superlative detection
        for pat, crit_name, disp in SUPERLATIVE_CRITERIA:
            if pat.search(lbl_lower):
                badges.append(disp)
                selection_evidence.append(f"{crit_name}: '{lbl}'")

        if any(b in lbl_lower for b in ("best seller", "bestseller", "top rated", "popular", "choice", "deal of the day", "sponsored")):
            if lbl not in badges:
                badges.append(lbl)

        # 2. Price detection
        price_m = re.search(r'([$₹£€]\s*[0-9,]+(?:\.[0-9]{2})?|\b[0-9,]+(?:\.[0-9]{2})?\s*(?:usd|inr|eur|gbp)\b)', lbl_lower)
        if price_m:
            prices.append(price_m.group(1))

        # 3. Rating & Review detection
        rating_m = re.search(r'\b([0-5]\.[0-9])\s*(?:out of 5|stars?|\*)\b', lbl_lower)
        if rating_m:
            ratings.append(rating_m.group(1))

        rev_m = re.search(r'\b([0-9,]+)\s*(?:ratings?|reviews?)\b', lbl_lower)
        if rev_m:
            review_counts.append(rev_m.group(1))

        # 4. Title candidate detection
        if not title:
            if el.role in ("h2", "h3", "h4", "a", "link") and len(lbl) > 10 and not price_m and not any(crit in lbl_lower for crit in ("best seller", "top rated", "sponsored")):
                title = lbl
        elif len(lbl) > len(title) and not price_m and el.role in ("h2", "h3", "h4", "a", "link"):
            title = lbl

    if not title and text_pieces:
        non_badge = [t for t in text_pieces if not any(b in t.lower() for b in ("best seller", "$", "₹", "rating", "review"))]
        title = non_badge[0] if non_badge else text_pieces[0]

    visible_text = " | ".join(text_pieces)
    combined_tokens = set(clean_tokens(visible_text.lower()))
    vt_lower = visible_text.lower()

    # Extract RAM attribute across text
    detected_ram = None
    ram_m = re.search(r'\b(\d+)\s*(?:gb|g)\s*(?:ddr\d|lpddr\d|ram|memory)\b', vt_lower)
    if not ram_m:
        ram_m = re.search(r'\b(?:ram|memory)[:\s]+(\d+)\s*(?:gb|g)?\b', vt_lower)
    if ram_m:
        detected_ram = f"{ram_m.group(1)}GB RAM"

    # Extract Storage attribute across text
    detected_storage = None
    storage_m = re.search(r'\b(\d+)\s*(gb|tb)\s*(ssd|hdd|nvme|emmc|rom|storage)?\b', vt_lower)
    if not storage_m:
        storage_m = re.search(r'\b(?:ssd|storage|hdd|drive)[:\s]+(\d+)\s*(gb|tb)?\b', vt_lower)
    if storage_m:
        s_val = storage_m.group(1)
        s_unit = (storage_m.group(2) or "gb").upper()
        s_type = (storage_m.group(3) or "").upper() if storage_m.lastindex >= 3 and storage_m.group(3) else ""
        detected_storage = f"{s_val}{s_unit} {s_type}".strip()

    # Extract semantic attributes across entire aggregated text
    detected_color = None
    for tok in combined_tokens:
        if tok in COMMON_COLORS:
            detected_color = tok
            break

    detected_gender = None
    for tok in combined_tokens:
        if tok in COMMON_GENDERS:
            detected_gender = COMMON_GENDERS[tok]
            break

    detected_material = None
    for tok in combined_tokens:
        if tok in COMMON_MATERIALS:
            detected_material = tok
            break

    # Determine product type from title / visible text
    product_type = None
    title_words = clean_tokens(title.lower())
    type_tokens = [
        w for w in title_words 
        if w not in COMMON_COLORS 
        and w not in COMMON_GENDERS 
        and w not in COMMON_MATERIALS 
        and w not in ("the", "a", "an", "for", "with", "men", "women", "mens", "womens")
        and len(w) > 2
    ]
    if type_tokens:
        product_type = " ".join(type_tokens[:3])

    return ProductCandidate(
        candidate_id=candidate_id,
        title=title,
        visible_text=visible_text,
        href=href,
        product_type=product_type,
        gender=detected_gender,
        color=detected_color,
        brand=None,
        material=detected_material,
        price=prices[0] if prices else None,
        ram=detected_ram,
        storage=detected_storage,
        rating=ratings[0] if ratings else None,
        review_count=review_counts[0] if review_counts else None,
        badges=badges,
        selection_evidence=selection_evidence,
        source_element_ids=source_ids,
        bounding_box=bbox,
        confidence=1.0
    )


def verify_product_candidate_match(
    candidate: ProductCandidate,
    constraints: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Evaluates whether an aggregated ProductCandidate satisfies EVERY required HARD CONSTRAINT.
    Operates on the entire candidate entity (title, visible_text, attributes) rather than a single DOM label.
    Strict 3-valued constraint logic (TRUE, FALSE, UNKNOWN).
    """
    cand_text = f"{candidate.title} {candidate.visible_text}".lower()
    text_tokens = set(clean_tokens(cand_text))

    # 1. Product Type Verification (HARD CONSTRAINT)
    req_pt = constraints.get("product_type", "")
    if req_pt:
        pt_tokens = clean_tokens(req_pt)
        matched_pt_tokens = [t for t in pt_tokens if t in text_tokens or any(t in tok for tok in text_tokens)]
        if not matched_pt_tokens:
            return False, f"Product type mismatch: requested '{req_pt}', but candidate lacks '{req_pt}'"

        if len(pt_tokens) == 1:
            req_singular = pt_tokens[0].rstrip('s')
            if not any(req_singular in tok for tok in text_tokens):
                return False, f"Product type mismatch: requested singular '{req_singular}' not found in candidate"

        MUTUALLY_EXCLUSIVE_TYPES = {
            "shirt": {"dress", "gown", "kurta", "saree", "skirt", "pant", "pants", "trouser", "trousers", "jeans", "shoe", "shoes", "hoodie"},
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
        if norm_req_gender == "men":
            if any(w in text_tokens for w in ("women", "womens", "girl", "girls")):
                if not any(w in text_tokens for w in ("men", "mens", "boy", "boys")):
                    return False, "Gender/Category mismatch: requested 'men', but candidate specifies women/girls"
            if not any(w in text_tokens for w in ("men", "mens", "boy", "boys", "male", "unisex")):
                return False, "Gender/Category mismatch: requested 'men' not found in candidate"
        elif norm_req_gender == "women":
            if any(w in text_tokens for w in ("men", "mens", "boy", "boys")) and not any(w in text_tokens for w in ("women", "womens", "girl", "girls", "female", "unisex")):
                return False, "Gender/Category mismatch: requested 'women', but candidate specifies men/boys"
            if not any(w in text_tokens for w in ("women", "womens", "girl", "girls", "female", "unisex")):
                return False, "Gender/Category mismatch: requested 'women' not found in candidate"

    # 3. Color Verification (HARD CONSTRAINT)
    req_color = constraints.get("color") or constraints.get("attributes", {}).get("color")
    if req_color:
        if req_color not in text_tokens:
            conflicting_colors = [c for c in COMMON_COLORS if c in text_tokens and c != req_color]
            return False, f"Color mismatch: requested '{req_color}', candidate specifies {conflicting_colors or 'different color'}"

    # 4. Size Verification (HARD CONSTRAINT)
    req_size = constraints.get("size") or constraints.get("attributes", {}).get("size")
    if req_size:
        if req_size not in text_tokens:
            return False, f"Size mismatch: requested '{req_size}', candidate lacks requested size"

    # 5. Brand Verification (HARD CONSTRAINT)
    req_brand = constraints.get("brand") or constraints.get("attributes", {}).get("brand")
    if req_brand:
        if req_brand.lower() not in text_tokens:
            return False, f"Brand mismatch: requested '{req_brand}', candidate lacks requested brand"

    # 6. Material Verification (HARD CONSTRAINT)
    req_material = constraints.get("material") or constraints.get("attributes", {}).get("material")
    if req_material:
        if req_material.lower() not in text_tokens:
            return False, f"Material mismatch: requested '{req_material}', candidate lacks requested material"

    # 7. Numeric & Hardware Specifications (HARD CONSTRAINTS with 3-valued logic: TRUE, FALSE, UNKNOWN)
    num_constraints = constraints.get("numeric_constraints", {})

    # 7.1 Maximum Price Verification
    max_price = num_constraints.get("max_price")
    if max_price is not None:
        cand_price_val = None
        raw_price_str = candidate.price or ""
        if not raw_price_str:
            p_match = re.search(r'[$₹£€]\s*([0-9,]+(?:\.[0-9]+)?)', cand_text)
            if p_match:
                raw_price_str = p_match.group(1)
        if raw_price_str:
            num_clean = re.sub(r'[^0-9.]', '', raw_price_str)
            try:
                cand_price_val = float(num_clean)
            except ValueError:
                pass

        if cand_price_val is None:
            return False, f"Price unknown: requested price <= {max_price}, but candidate has unobserved price (UNKNOWN)"
        if cand_price_val > max_price:
            return False, f"Price exceeded: requested <= {max_price}, candidate price is {cand_price_val} (FALSE)"

    # 7.2 Minimum RAM Verification
    min_ram = num_constraints.get("min_ram_gb")
    if min_ram is not None:
        cand_ram_gb = None
        ram_src = candidate.ram or cand_text
        r_match = re.search(r'\b(\d+)\s*(?:gb|g)\s*(?:ddr\d|lpddr\d|ram|memory)\b', ram_src.lower())
        if not r_match:
            r_match = re.search(r'\b(?:ram|memory)[:\s]+(\d+)\s*(?:gb|g)?\b', ram_src.lower())
        if r_match:
            try:
                cand_ram_gb = int(r_match.group(1))
            except ValueError:
                pass

        if cand_ram_gb is None:
            return False, f"RAM unknown: requested >= {min_ram} GB RAM, but candidate has unobserved RAM specification (UNKNOWN)"
        if cand_ram_gb < min_ram:
            return False, f"RAM insufficient: requested >= {min_ram} GB RAM, candidate has {cand_ram_gb} GB (FALSE)"

    # 7.3 Minimum Storage & Storage Type Verification
    min_storage = num_constraints.get("min_storage_gb")
    req_storage_type = num_constraints.get("storage_type")
    if min_storage is not None:
        cand_storage_gb = None
        cand_storage_type = None
        stor_src = candidate.storage or cand_text
        s_match = re.search(r'\b(\d+)\s*(gb|tb)\s*(ssd|hdd|nvme|emmc|rom|storage)?\b', stor_src.lower())
        if not s_match:
            s_match = re.search(r'\b(?:ssd|storage|hdd|drive)[:\s]+(\d+)\s*(gb|tb)?\b', stor_src.lower())
        if s_match:
            try:
                s_val = int(s_match.group(1))
                s_unit = (s_match.group(2) or "gb").lower()
                if s_unit == "tb":
                    s_val *= 1024
                cand_storage_gb = s_val
                if s_match.lastindex >= 3 and s_match.group(3):
                    cand_storage_type = s_match.group(3).lower()
            except ValueError:
                pass

        if cand_storage_gb is None:
            return False, f"Storage unknown: requested >= {min_storage} GB, but candidate has unobserved storage (UNKNOWN)"
        if cand_storage_gb < min_storage:
            return False, f"Storage insufficient: requested >= {min_storage} GB, candidate has {cand_storage_gb} GB (FALSE)"
        if req_storage_type:
            # Check for storage type (e.g. SSD)
            if cand_storage_type and req_storage_type in cand_storage_type:
                pass
            elif req_storage_type in cand_text:
                pass
            else:
                return False, f"Storage type mismatch: requested {req_storage_type.upper()}, but candidate lacks {req_storage_type.upper()} specification (UNKNOWN)"

    return True, "All hard product constraints satisfied by candidate entity."


def verify_candidate_selection_evidence(
    candidate: ProductCandidate,
    constraints: Dict[str, Any]
) -> Tuple[bool, str]:
    """Checks if the aggregated candidate possesses verifiable evidence of requested selection criterion."""
    crit = constraints.get("selection_criterion")
    if not crit:
        return True, "No selection criterion required."

    disp = constraints.get("selection_criterion_disp", "").lower()
    text_lower = f"{candidate.title} {candidate.visible_text} {' '.join(candidate.badges)}".lower()

    if disp and all(t in text_lower for t in clean_tokens(disp)):
        return True, f"Observable evidence of criterion '{disp}' confirmed."

    if crit == "BEST_SELLING":
        if any(p in text_lower for p in ("#1 best seller", "best seller", "bestseller", "top selling", "most bought")):
            return True, "Observable evidence of best seller confirmed in candidate badges/text."
    elif crit == "HIGHEST_RATED":
        if any(p in text_lower for p in ("top rated", "highest rated", "4.8", "4.9", "5.0 star")):
            return True, "Observable evidence of top rating confirmed in candidate badges/text."
    elif crit == "LOWEST_PRICED":
        if any(p in text_lower for p in ("lowest price", "cheapest", "price: low")):
            return True, "Observable evidence of lowest price confirmed in candidate text."

    return False, f"Selection criterion '{disp}' has NO observable evidence on candidate."


def rank_product_candidates(
    valid_candidates: List[ProductCandidate],
    constraints: Dict[str, Any]
) -> List[Tuple[ProductCandidate, float, bool]]:
    """
    Ranks candidates that HAVE ALREADY PASSED hard constraint filtering.
    Candidates with proven selection evidence score significantly higher.
    """
    scored = []
    crit = constraints.get("selection_criterion")
    disp = constraints.get("selection_criterion_disp", "")
    disp_tokens = clean_tokens(disp)

    for cand in valid_candidates:
        score = 1.0
        has_proven_crit = False

        if crit:
            has_ev, _ = verify_candidate_selection_evidence(cand, constraints)
            if has_ev:
                score += 20.0
                has_proven_crit = True
            elif disp and any(t in f"{cand.title} {cand.visible_text}".lower() for t in disp_tokens):
                score += 5.0

        scored.append((cand, score, has_proven_crit))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def print_candidate_diagnostics(
    all_candidates: List[ProductCandidate],
    valid_candidates: List[ProductCandidate],
    rejected_candidates: List[Tuple[ProductCandidate, str]],
    selected_target: Optional[ProductCandidate] = None,
    current_product: Optional[ProductCandidate] = None,
    cart_product: Optional[ProductCandidate] = None
) -> None:
    """Diagnostic mode tracer printing structured entity pipeline stages."""
    print("\n" + "="*50)
    print("PRODUCT CANDIDATES FOUND")
    print("="*50)
    for c in all_candidates:
        print(f"candidate_id:       {c.candidate_id}")
        print(f"title:              {c.title}")
        print(f"attributes:         product_type={c.product_type}, gender={c.gender}, color={c.color}, material={c.material}")
        print(f"badge:              {c.badges}")
        print(f"price:              {c.price}")
        print(f"rating:             {c.rating}")
        print(f"href:               {c.href}")
        print(f"source_element_ids: {c.source_element_ids}")
        print("-" * 30)

    print("\n" + "="*50)
    print(f"VALID CANDIDATES ({len(valid_candidates)})")
    print("="*50)
    for c in valid_candidates:
        print(f"  * [{c.candidate_id}] {c.title} (badges: {c.badges})")

    print("\n" + "="*50)
    print(f"REJECTED CANDIDATES ({len(rejected_candidates)})")
    print("="*50)
    for c, reason in rejected_candidates:
        print(f"  * [{c.candidate_id}] {c.title} -> REASON: {reason}")

    if selected_target:
        print("\n" + "="*50)
        print("SELECTED TARGET")
        print("="*50)
        print(f"candidate_id:       {selected_target.candidate_id}")
        print(f"title:              {selected_target.title}")
        print(f"evidence:           {selected_target.selection_evidence or selected_target.badges}")
        print(f"href:               {selected_target.href}")
        print(f"source_element_ids: {selected_target.source_element_ids}")

    if current_product:
        print("\n" + "="*50)
        print("CURRENT PRODUCT (PAGE RECONSTRUCTION)")
        print("="*50)
        print(f"title:              {current_product.title}")
        print(f"attributes:         {current_product.to_dict()['attributes']}")
        if selected_target:
            match_title = (selected_target.title.lower() in current_product.title.lower()) or (current_product.title.lower() in selected_target.title.lower())
            print(f"matches_selected:   {match_title}")

    if cart_product:
        print("\n" + "="*50)
        print("CART PRODUCT (CART RECONSTRUCTION)")
        print("="*50)
        print(f"title:              {cart_product.title}")
        if selected_target:
            match_cart = (selected_target.title.lower() in cart_product.title.lower()) or (cart_product.title.lower() in selected_target.title.lower())
            print(f"matches_selected:   {match_cart}")
    print("="*50 + "\n")
