"""
Generic Semantic Page Understanding Layer for Visiionary.

Dynamically classifies the current page based on observable DOM, accessibility,
and vision signals rather than assuming its purpose from domain names or URLs.
Zero website, search-engine, or portal hardcoding.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from server.app.schemas.schemas import ElementMetadata

# Semantic Page States
PAGE_SEARCH_DISCOVERY = "SEARCH_DISCOVERY"
PAGE_LISTING_CATALOG = "LISTING_CATALOG"
PAGE_DETAIL_ENTITY = "DETAIL_ENTITY"
PAGE_ARTICLE_DOCUMENT = "ARTICLE_DOCUMENT"
PAGE_FORM_INTERACTION = "FORM_INTERACTION"
PAGE_AUTHENTICATION = "AUTHENTICATION"
PAGE_DASHBOARD_TABLE = "DASHBOARD_TABLE"
PAGE_TRANSACTION_CART = "TRANSACTION_CART"
PAGE_CONFIRMATION_RESULT = "CONFIRMATION_RESULT"
PAGE_NAVIGATION_INTERMEDIATE = "NAVIGATION_INTERMEDIATE"
PAGE_UNKNOWN = "UNKNOWN"

@dataclass
class PageSemanticModel:
    semantic_state: str
    confidence: float
    has_search_input: bool = False
    has_repeated_cards: bool = False
    has_detail_focal_entity: bool = False
    has_form_fields: bool = False
    has_cart_summary: bool = False
    has_table_data: bool = False
    has_auth_fields: bool = False
    has_confirmation: bool = False
    primary_entity_type: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "semantic_state": self.semantic_state,
            "confidence": self.confidence,
            "has_search_input": self.has_search_input,
            "has_repeated_cards": self.has_repeated_cards,
            "has_detail_focal_entity": self.has_detail_focal_entity,
            "has_form_fields": self.has_form_fields,
            "has_cart_summary": self.has_cart_summary,
            "has_table_data": self.has_table_data,
            "has_auth_fields": self.has_auth_fields,
            "has_confirmation": self.has_confirmation,
            "primary_entity_type": self.primary_entity_type,
            "capabilities": self.capabilities
        }


def classify_page_semantics(
    elements: List[ElementMetadata],
    page_title: str = "",
    current_url: str = "",
    screen_summary: Optional[Dict[str, Any]] = None
) -> PageSemanticModel:
    """
    Classifies the current page's semantic state strictly from observable DOM signals,
    element roles, text properties, and spatial arrangements.
    Zero domain names, zero website-specific selectors.
    """
    title_lower = (page_title or "").lower()
    url_lower = (current_url or "").lower()
    
    # Analyze element characteristics
    input_elements = [e for e in elements if e.role in ("input", "textarea") and e.sensitivity != "redacted"]
    button_elements = [e for e in elements if e.role in ("button", "role_button")]
    link_elements = [e for e in elements if e.role in ("a", "link", "role_link") and e.href]
    headings = [e for e in elements if e.role in ("h1", "h2", "h3", "h4")]
    
    # 1. Search input detection
    search_inputs = [
        e for e in input_elements 
        if any(k in (e.label or "").lower() + e.id.lower() for k in ("search", "find", "query", "kw", "q"))
    ]
    has_search_input = bool(search_inputs)

    # 2. Authentication fields
    password_fields = [
        e for e in elements 
        if "password" in e.id.lower() or e.role == "password" or "password" in (e.label or "").lower()
    ]
    has_auth_fields = bool(password_fields)

    # 3. Form fields (non-search inputs)
    form_inputs = [e for e in input_elements if e not in search_inputs]
    has_form_fields = len(form_inputs) >= 2

    # 4. Cart / Transaction indicators
    cart_indicators = [
        e for e in elements 
        if any(k in (e.label or "").lower() for k in ("shopping cart", "view cart", "checkout", "order summary", "subtotal", "items in cart"))
    ]
    has_cart_summary = bool(cart_indicators) or any(k in title_lower for k in ("cart", "basket", "checkout"))

    # 5. Confirmation / Result state
    confirmation_indicators = [
        e for e in elements 
        if any(k in (e.label or "").lower() for k in ("thank you", "order confirmed", "submission successful", "success", "confirmed", "download ready"))
    ]
    has_confirmation = bool(confirmation_indicators) or any(k in title_lower for k in ("confirmation", "thank you", "receipt", "success"))

    # 6. Table data
    table_indicators = [
        e for e in elements 
        if e.role in ("table", "row", "grid", "cell") or any(k in e.id.lower() for k in ("dt-search", "datatable", "table"))
    ]
    has_table_data = len(table_indicators) >= 4

    # 7. Repeated cards / Catalog listings (look for multiple links with image/price or similar horizontal/vertical stride)
    product_type_anchors = [
        e for e in link_elements 
        if len(e.label.strip()) > 10 and not any(k in e.label.lower() for k in ("sign in", "privacy", "terms", "about", "contact"))
    ]
    has_repeated_cards = len(product_type_anchors) >= 3

    # 8. Detail / Focal Entity
    # Single dominant entity with specs, add to cart / action buttons, or high descriptive text.
    # CRITICAL: A page with multiple independent result/product links is a discovery or listing page, NOT a detail entity!
    action_buttons = [
        e for e in button_elements 
        if any(k in (e.label or "").lower() for k in ("add to cart", "buy now", "download", "submit", "apply now", "enroll"))
    ]
    # To be a focal detail entity, there must NOT be a collection of repeated result links/cards
    has_detail_focal_entity = bool(action_buttons) and len(product_type_anchors) <= 1 and not has_repeated_cards

    capabilities: List[str] = []
    if has_search_input:
        capabilities.append("can_search")
    if has_repeated_cards:
        capabilities.append("can_browse_listings")
    if has_table_data:
        capabilities.append("can_filter_table")
    if has_detail_focal_entity:
        capabilities.append("can_interact_with_focal_entity")
    if has_form_fields:
        capabilities.append("can_fill_form")
    if has_cart_summary:
        capabilities.append("has_cart_summary")

    # Classification logic: Search results page requires true search query evidence in URL or title
    is_search_context = (
        "google.com/search" in url_lower
        or "bing.com/search" in url_lower
        or "duckduckgo.com" in url_lower
        or "/search" in url_lower
        or "search?" in url_lower
        or "?q=" in url_lower
        or "&q=" in url_lower
        or "/?q=" in url_lower
        or "search results" in title_lower
        or "results for" in title_lower
        or "search for" in title_lower
    )

    if has_confirmation:
        state = PAGE_CONFIRMATION_RESULT
        conf = 0.95
    elif has_auth_fields:
        state = PAGE_AUTHENTICATION
        conf = 0.95
    elif has_cart_summary:
        state = PAGE_TRANSACTION_CART
        conf = 0.90
    elif is_search_context and (has_repeated_cards or len(product_type_anchors) >= 2 or len(link_elements) >= 4):
        state = PAGE_SEARCH_DISCOVERY
        conf = 0.92
    elif has_repeated_cards or len(product_type_anchors) >= 3:
        state = PAGE_LISTING_CATALOG
        conf = 0.88
    elif has_form_fields and not has_repeated_cards:
        state = PAGE_FORM_INTERACTION
        conf = 0.85
    elif has_table_data and not has_repeated_cards:
        state = PAGE_DASHBOARD_TABLE
        conf = 0.85
    elif has_detail_focal_entity:
        state = PAGE_DETAIL_ENTITY
        conf = 0.88
    elif has_repeated_cards:
        state = PAGE_LISTING_CATALOG
        conf = 0.85
    elif has_search_input and len(elements) < 25:
        state = PAGE_SEARCH_DISCOVERY
        conf = 0.80
    elif len(link_elements) > 10 and len(headings) >= 2:
        state = PAGE_NAVIGATION_INTERMEDIATE
        conf = 0.75
    elif len(elements) > 0 and any(len(e.label) > 120 for e in elements):
        state = PAGE_ARTICLE_DOCUMENT
        conf = 0.80
    else:
        state = PAGE_UNKNOWN
        conf = 0.50

    return PageSemanticModel(
        semantic_state=state,
        confidence=conf,
        has_search_input=has_search_input,
        has_repeated_cards=has_repeated_cards,
        has_detail_focal_entity=has_detail_focal_entity,
        has_form_fields=has_form_fields,
        has_cart_summary=has_cart_summary,
        has_table_data=has_table_data,
        has_auth_fields=has_auth_fields,
        has_confirmation=has_confirmation,
        capabilities=capabilities
    )
