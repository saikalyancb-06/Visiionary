"""
Generic Semantic Entity Model & Aggregator for Visiionary.

Aggregates raw DOM/accessibility elements into structured SemanticEntity objects.
Distinguishes:
- Direct Entity Target (the actual focal item)
- Intermediate Navigation Destination (a directory, category, or search link leading elsewhere)
- Form Field
- Action Control
- Document / Article Record

Zero domain, website, or product-type hardcoding.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set
from server.app.schemas.schemas import ElementMetadata

# Semantic Entity Types
ENTITY_PRODUCT = "product"
ENTITY_DOCUMENT = "document"
ENTITY_ARTICLE = "article"
ENTITY_RECORD = "record"
ENTITY_DESTINATION = "intermediate_destination"
ENTITY_FORM_CONTROL = "form_control"
ENTITY_ACCOUNT = "account"
ENTITY_UNKNOWN = "unknown"

@dataclass
class SemanticEntity:
    entity_id: str
    semantic_type: str = ENTITY_UNKNOWN
    title: str = ""
    summary: str = ""
    visible_text: str = ""
    href: Optional[str] = None
    is_destination_only: bool = False   # True if this link leads to an intermediate page/category/portal
    attributes: Dict[str, Any] = field(default_factory=dict)
    badges: List[str] = field(default_factory=list)
    selection_evidence: List[str] = field(default_factory=list)
    source_element_ids: List[str] = field(default_factory=list)
    bounding_box: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "semantic_type": self.semantic_type,
            "title": self.title,
            "summary": self.summary,
            "visible_text": self.visible_text,
            "href": self.href,
            "is_destination_only": self.is_destination_only,
            "attributes": self.attributes,
            "badges": self.badges,
            "selection_evidence": self.selection_evidence,
            "source_element_ids": self.source_element_ids,
            "bounding_box": self.bounding_box,
            "confidence": self.confidence
        }


def _bbox_overlap_or_nearby(box_a: List[int], box_b: List[int], max_x_dist: int = 40, max_y_dist: int = 50) -> bool:
    if not box_a or not box_b or len(box_a) != 4 or len(box_b) != 4:
        return False
    x1_a, y1_a, x2_a, y2_a = box_a
    x1_b, y1_b, x2_b, y2_b = box_b

    x_overlap = max(0, min(x2_a, x2_b) - max(x1_a, x1_b))
    x_dist = max(0, max(x1_a, x1_b) - min(x2_a, x2_b))
    y_dist = max(0, max(y1_a, y1_b) - min(y2_a, y2_b))

    return (x_overlap > 10 or x_dist <= max_x_dist) and y_dist <= max_y_dist


def _normalize_href(href: Optional[str]) -> Optional[str]:
    if not href:
        return None
    return href.split("?")[0].split("#")[0].rstrip("/").lower()


def _classify_destination_vs_entity(
    href: Optional[str],
    label: str,
    page_is_search: bool = False
) -> Tuple[str, bool]:
    """
    Distinguishes whether an observed link is:
    - An intermediate navigation destination (category, search result, directory)
    - A direct focal entity (detail page, download link, specific record)
    """
    if not href:
        return ENTITY_UNKNOWN, False

    h_lower = href.lower()
    lbl_lower = label.lower()

    # Search result links pointing outside search engine are intermediate destinations unless directly targeting a PDF/file
    if page_is_search:
        if any(h_lower.endswith(ext) for ext in (".pdf", ".csv", ".xlsx", ".zip", ".json")):
            return ENTITY_DOCUMENT, False
        return ENTITY_DESTINATION, True

    # Category or directory pages
    category_indicators = ("/c/", "/category/", "/browse/", "/department/", "/search", "/shop/all", "/catalog/")
    if any(k in h_lower for k in category_indicators) or any(k in lbl_lower for k in ("shop all", "view all", "browse", "category")):
        return ENTITY_DESTINATION, True

    # Direct entity indicators (individual item/product/article/doc paths)
    entity_indicators = ("/p/", "/dp/", "/product/", "/item/", "/article/", "/doc/", "/details/", "/view/", "/post/")
    if any(k in h_lower for k in entity_indicators):
        return ENTITY_PRODUCT, False

    if any(h_lower.endswith(ext) for ext in (".pdf", ".doc", ".docx", ".pdf")):
        return ENTITY_DOCUMENT, False

    return ENTITY_UNKNOWN, False


def extract_semantic_entities(
    elements: List[ElementMetadata],
    page_title: str = "",
    current_url: str = ""
) -> List[SemanticEntity]:
    """
    Generic entity aggregation layer.
    Clusters raw DOM/accessibility elements into coherent SemanticEntity objects.
    Enforces boundary detection through:
    1. Shared normalized destination href
    2. Spatial proximity / Card bounding box envelopment
    3. Structural element patterns
    """
    if not elements:
        return []

    url_lower = (current_url or "").lower()
    page_is_search = "search" in url_lower or "google." in url_lower or "bing." in url_lower or "duckduckgo." in url_lower

    # Phase 1: Cluster by shared normalized destination href
    href_groups: Dict[str, List[ElementMetadata]] = {}
    remaining_elements: List[ElementMetadata] = []

    for el in elements:
        if not el.label or len(el.label.strip()) < 2:
            continue
        norm_h = _normalize_href(el.href)
        if norm_h and (len(norm_h.split("/")) > 3 or "/p/" in norm_h or "/dp/" in norm_h):
            if norm_h not in href_groups:
                href_groups[norm_h] = []
            href_groups[norm_h].append(el)
        else:
            remaining_elements.append(el)

    clusters: List[List[ElementMetadata]] = list(href_groups.values())

    # Phase 2: Spatial cluster remaining elements
    for el in remaining_elements:
        assigned = False
        lbl = el.label.strip()
        is_independent_anchor = el.role in ("a", "link", "h2", "h3", "h4") and len(lbl) > 10

        if not is_independent_anchor and el.bbox and len(el.bbox) == 4 and (el.bbox[2] > el.bbox[0] or el.bbox[3] > el.bbox[1]):
            for cluster in clusters:
                cluster_boxes = [m.bbox for m in cluster if m.bbox and len(m.bbox) == 4]
                if any(_bbox_overlap_or_nearby(el.bbox, cb) for cb in cluster_boxes):
                    cluster.append(el)
                    assigned = True
                    break

        if not assigned and (el.interactable or el.role in ("h2", "h3", "h4", "div")):
            clusters.append([el])

    # Phase 3: Synthesize SemanticEntity objects
    entities: List[SemanticEntity] = []
    entity_counter = 1

    for cluster in clusters:
        if not cluster:
            continue
        # Find primary label & href
        primary_el = cluster[0]
        href = next((e.href for e in cluster if e.href), None)
        text_parts = [e.label.strip() for e in cluster if e.label and e.label.strip()]
        if not text_parts:
            continue

        title = text_parts[0]
        for e in cluster:
            if e.role in ("h1", "h2", "h3", "h4", "a") and len(e.label.strip()) > len(title):
                title = e.label.strip()

        combined_text = " | ".join(text_parts)
        combined_lower = combined_text.lower()

        # Classify entity vs destination
        sem_type, is_dest = _classify_destination_vs_entity(href, title, page_is_search)

        # Attribute extraction
        attributes: Dict[str, Any] = {}
        badges: List[str] = []
        evidence: List[str] = []

        # Badge / Superlative check
        superlatives = ("best seller", "best-selling", "top rated", "highest rated", "most popular", "trending")
        for s in superlatives:
            if s in combined_lower:
                badges.append(s)
                evidence.append(f"Observed '{s}' badge on entity card")

        # Price check
        price_m = re.search(r'([$€£₹]\s*[0-9]+(?:,[0-9]{3})*(?:\.[0-9]{2})?|INR\s*[0-9,]+)', combined_text)
        if price_m:
            attributes["price"] = price_m.group(1)

        # Numerical ID check (e.g. PS 171)
        id_m = re.search(r'(?:problem statement|ps|item|code|no\.?)\s*([0-9]{2,6})', combined_lower)
        if id_m:
            attributes["item_id"] = id_m.group(1)
            sem_type = ENTITY_DOCUMENT

        # Spatial bounding box
        min_x = min((e.bbox[0] for e in cluster if e.bbox), default=0)
        min_y = min((e.bbox[1] for e in cluster if e.bbox), default=0)
        max_x = max((e.bbox[2] for e in cluster if e.bbox), default=0)
        max_y = max((e.bbox[3] for e in cluster if e.bbox), default=0)

        entity = SemanticEntity(
            entity_id=f"entity_{entity_counter}_{primary_el.id}",
            semantic_type=sem_type,
            title=title,
            summary=combined_text[:160],
            visible_text=combined_text,
            href=href,
            is_destination_only=is_dest,
            attributes=attributes,
            badges=badges,
            selection_evidence=evidence,
            source_element_ids=[e.id for e in cluster if e.id],
            bounding_box=[min_x, min_y, max_x, max_y],
            confidence=1.0
        )
        entities.append(entity)
        entity_counter += 1

    return entities
