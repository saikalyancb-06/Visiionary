import unittest
import sys
import os
sys.path.insert(0, os.path.abspath("."))

from server.app.schemas.schemas import SanitizedContextPackage, PageContext, ElementMetadata, PrivacyReport
from server.app.planner import decide_next_action
from server.app.page_model import classify_page_semantics, PAGE_SEARCH_DISCOVERY, PAGE_LISTING_CATALOG, PAGE_DETAIL_ENTITY

def make_payload(task: str, url: str, title: str, elements: list) -> SanitizedContextPackage:
    return SanitizedContextPackage(
        session_id="test_session",
        step=1,
        instruction_sanitized=task,
        page=PageContext(url_sanitized=url, title_sanitized=title, viewport={"w": 1280, "h": 720}),
        elements=elements,
        redactions=[],
        privacy_report=PrivacyReport(detected=0, sensitive=0, redacted=0, categories=[]),
        metrics={"duration_ms": 10},
        history=[],
        verification_state={},
        product_constraints=None,
        selected_target=None
    )

class TestSearchDiscoveryPlanner(unittest.TestCase):

    def test_scenario_a_populated_search_page_never_retypes(self):
        """Scenario A: Given an already-populated search-results page, the planner MUST NOT type the query again."""
        task = "Find a laptop under ₹80,000 with at least 16 GB RAM and 512 GB SSD."
        url = "https://html.duckduckgo.com/html/?q=laptop+under+80000+16GB+RAM+512GB+SSD"
        title = "laptop under 80000 16GB RAM 512GB SSD at DuckDuckGo"
        
        elements = [
            ElementMetadata(id="search_input", role="input", label="Search query input", interactable=True, bbox=[10, 10, 300, 30]),
            ElementMetadata(id="search_button", role="button", label="Submit search", interactable=True, bbox=[320, 10, 50, 30]),
            ElementMetadata(
                id="res_link_1",
                role="a",
                label="Best 16GB RAM Laptops Under 80000 in 2026 - Tech Reviews & Store Catalog",
                href="https://store.gadgethub.org/laptops/16gb-ram-80k",
                interactable=True,
                bbox=[50, 100, 600, 30]
            ),
            ElementMetadata(
                id="res_link_2",
                role="a",
                label="Top 10 High Performance 512GB SSD Laptops Under 80000",
                href="https://hardware-market.net/deals/laptops",
                interactable=True,
                bbox=[50, 150, 600, 30]
            ),
        ]
        
        payload = make_payload(task, url, title, elements)
        actions, summary = decide_next_action(payload)

        # Precondition check: must NOT be TYPE
        self.assertNotEqual(actions[0].type, "type", "Planner re-typed search query into search input on already-populated search page!")
        # Must transition via opening destination link
        self.assertIn(actions[0].type, ("open_link", "click"))
        chosen_url = actions[0].url or summary
        self.assertTrue(
            "store.gadgethub.org" in chosen_url or "hardware-market.net" in chosen_url,
            f"Expected organic search destination, got: {chosen_url}"
        )

    def test_scenario_b_category_listing_destination_selection(self):
        """Scenario B: Given a search page with multiple store/catalog links, selects top destination matching task terms."""
        task = "find best selling black shirt for men"
        url = "https://www.google.com/search?q=best+selling+black+shirt+for+men"
        title = "best selling black shirt for men - Google Search"

        elements = [
            ElementMetadata(id="q", role="input", label="Search", interactable=True, bbox=[0, 0, 100, 20]),
            ElementMetadata(id="unrelated", role="a", label="Unrelated Article on Weather", href="https://news.org/weather", interactable=True, bbox=[0, 30, 200, 20]),
            ElementMetadata(
                id="link_store",
                role="a",
                label="Men's Black Shirts Collection - Best Sellers & Trends",
                href="https://mensfashionhub.com/collections/black-shirts",
                interactable=True,
                bbox=[0, 60, 400, 20]
            )
        ]

        payload = make_payload(task, url, title, elements)
        actions, summary = decide_next_action(payload)

        self.assertNotEqual(actions[0].type, "type")
        self.assertEqual(actions[0].type, "open_link")
        self.assertEqual(actions[0].url, "https://mensfashionhub.com/collections/black-shirts")

    def test_scenario_c_direct_product_listing_page_extracts_candidates(self):
        """Scenario C: On an actual catalog/listing page, aggregates candidates and does not attempt search."""
        task = "Find a laptop under ₹80,000 with at least 16 GB RAM and 512 GB SSD."
        url = "https://electronics-mart.com/laptops"
        title = "Laptops Catalog - High Performance Machines"

        elements = [
            ElementMetadata(
                id="p1_title", role="a", label="UltraBook Pro 15 - 16GB RAM 512GB SSD Laptop",
                href="https://electronics-mart.com/p/ultrabook-pro-15", interactable=True, bbox=[50, 100, 300, 20]
            ),
            ElementMetadata(
                id="p1_price", role="span", label="₹74,999", interactable=False, bbox=[50, 125, 100, 20]
            ),
            ElementMetadata(
                id="p2_title", role="a", label="Gaming Elite 16 - 16GB RAM 1TB SSD Laptop",
                href="https://electronics-mart.com/p/gaming-elite-16", interactable=True, bbox=[50, 250, 300, 20]
            ),
            ElementMetadata(
                id="p2_price", role="span", label="₹79,990", interactable=False, bbox=[50, 275, 100, 20]
            ),
        ]

        payload = make_payload(task, url, title, elements)
        actions, summary = decide_next_action(payload)

        # On a store listing page, planner extracts candidate and opens target or accumulates
        self.assertIn(actions[0].type, ("open_link", "click", "scroll"))
        self.assertNotEqual(actions[0].type, "type")

    def test_scenario_d_product_detail_page_reaches_verification(self):
        """Scenario D: When on product detail page, recognizes detail entity and does not navigate away."""
        task = "Find a laptop under ₹80,000 with at least 16 GB RAM and 512 GB SSD. Open its product page and report specifications."
        url = "https://electronics-mart.com/p/ultrabook-pro-15"
        title = "UltraBook Pro 15 Laptop Specifications and Buy"

        elements = [
            ElementMetadata(id="h1_title", role="h1", label="UltraBook Pro 15 Laptop", interactable=False, bbox=[50, 50, 400, 30]),
            ElementMetadata(id="spec_ram", role="div", label="16 GB DDR5 RAM, 512 GB NVMe SSD", interactable=False, bbox=[50, 90, 400, 20]),
            ElementMetadata(id="btn_buy", role="button", label="Buy Now", interactable=True, bbox=[50, 130, 120, 40]),
        ]

        payload = make_payload(task, url, title, elements)
        semantics = classify_page_semantics(elements=elements, page_title=title, current_url=url)
        self.assertEqual(semantics.semantic_state, PAGE_DETAIL_ENTITY)

    def test_scenario_e_no_relevant_destinations_scrolls(self):
        """Scenario E: Search page with zero relevant destination matches scrolls rather than clicking first result."""
        task = "open customenterpriseportal and check orders"
        url = "https://www.google.com/search?q=customenterpriseportal"
        title = "customenterpriseportal - Google Search"

        elements = [
            ElementMetadata(id="res1", role="a", label="Unrelated Online Gaming Site", href="https://gamingportal.io", interactable=True, bbox=[10, 50, 200, 20]),
            ElementMetadata(id="res2", role="a", label="Random Cat Pictures Hub", href="https://cats.org", interactable=True, bbox=[10, 100, 200, 20]),
        ]

        payload = make_payload(task, url, title, elements)
        actions, summary = decide_next_action(payload)

        self.assertEqual(actions[0].type, "scroll")
        self.assertIn("NO_RELEVANT_CANDIDATE", summary)

if __name__ == "__main__":
    unittest.main()
