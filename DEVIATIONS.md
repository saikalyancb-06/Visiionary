# DEVIATIONS LOG — SIH 2026 PS 26171

Every architectural adjustment or dataset fallback is recorded here per Rule R8.

---

### DEV-001: Synthetic Indian PII Portal Generator Built Locally
* **Component:** Phase 4 / 5 Dataset Pipeline
* **Reason:** Public web datasets (e.g. WebUI, RICO) lack Indian-specific PII formats (Aadhaar with Verhoeff check digits, PAN pattern, IFSC codes, UPI handles, Hindi/Devanagari numerals).
* **Replacement:** Built `synthetic-data/generators/generate_pii_dataset.py` generating realistic portals with exact pixel bounding boxes via DOM coordinates.
* **Impact:** 100% ground-truth accuracy with zero real personal data leakage (Rule R3).

---

### DEV-002: Strata Insurance Corpus Fallback
* **Component:** Supplementary dataset
* **Reason:** Strata Insurance Corpus requires private/commercial access and was unverified publicly without login gates.
* **Replacement:** Replaced with synthetic complex financial and KYC statement templates in our synthetic generator.
* **Impact:** No external dependency, fully reproducible on any machine.
