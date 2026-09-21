from server.app.schemas.schemas import SanitizedContextPackage, PageContext, ElementMetadata, PrivacyReport
from server.app.llm_planner import plan_with_local_llm, check_ollama_status

status = check_ollama_status()
print("Ollama Status:", status)

payload = SanitizedContextPackage(
    session_id="test_llm_01",
    step=1,
    instruction_sanitized="Search for python books",
    page=PageContext(
        url_sanitized="https://books.toscrape.com",
        title_sanitized="All products | Books to Scrape - Sandbox",
        viewport={"w": 1280, "h": 720, "dpr": 1.0}
    ),
    elements=[
        ElementMetadata(id="search_box", role="input", label="Search books...", bbox=[100, 50, 300, 80]),
        ElementMetadata(id="search_btn", role="button", label="Search", bbox=[310, 50, 400, 80]),
        ElementMetadata(id="book_1", role="a", label="A Light in the Attic", bbox=[100, 150, 250, 300])
    ],
    privacy_report=PrivacyReport(detected=0, sensitive=0, redacted=0)
)

actions, summary, model = plan_with_local_llm(payload)
print("Model Used:", model)
print("Reasoning Summary:", summary)
print("Actions Generated:", [a.model_dump() for a in actions])
