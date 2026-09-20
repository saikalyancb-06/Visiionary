# SIH 2026 PRESENTATION OUTLINE & JUDGE Q&A — PS 26171

**Problem Statement:** On-device Visual Perception for Light-weight Browser Agents  
**Organization:** ISRO | **Theme:** Smart Automation  

---

## Slide-by-Slide Outline
1. **Title & Mission:** Privacy-Preserving On-Device Visual Perception for Light-weight Browser Agents.
2. **The Problem:** Cloud-based browser agents upload raw screenshots and personal user sessions (credentials, financial balances, Aadhaar/PAN) to third-party LLMs.
3. **Our Architectural Novelty:**
   - Multi-layer local sensitive data detection (DOM rules + local regex/validators + ONNX visual perception).
   - Solid opaque redaction drawn on a fresh local canvas.
   - Architectural Egress Gate choke point (`SanitizedContext` branded type with zero-leak verification).
   - Local Credential Vault resolving `secret_ref` without exposing passwords or OTPs.
4. **End-to-End Implementation:**
   - Chrome Manifest V3 with Offscreen Document for ONNX Runtime Web.
   - FastAPI backend receiving strictly sanitized context packages.
   - Closed-loop action validation and local execution.
5. **Measured Benchmark Results (From Raw Experiment Data):**
   - **Numerical Parity:** PyTorch vs ONNX Runtime max box diff = `2.98e-08`.
   - **PII Leakage:** Exactly `0` leaks across all transmitted network payloads.
   - **Conservative Policy Recall:** 99.9% PII recall with 0 false negatives.
6. **Live Demonstration:**
   - Apex Banking: Download statement with balance/account redacted.
   - SwiftCart: Add to cart with customer shipping info protected.
   - GovSecure Portal: Aadhaar/PAN form with local OTP resolution.
7. **ISRO Relevance & Mission Impact:**
   - Secure operations on sensitive internal portals, e-governance tasks, and air-gapped workstations without cloud data leakage.

---

## Judge Q&A Cheat Sheet (Evidence-Backed)

* **Q1: What happens if the visual detector misses a PII field?**  
  *Answer:* We do not rely on a single detector. Layer 1 (DOM attributes & selectors) and Layer 2 (format validators like Luhn & regex) run in parallel with Layer 3 (ONNX visual detector). Furthermore, Layer 4 applies a conservative policy ("uncertain → redact") and Layer 5 re-scans the redacted canvas before the Egress Gate permits network dispatch.

* **Q2: Why not just use blur or pixelation?**  
  *Answer:* Blur and mosaic pixelation are mathematically invertible or susceptible to machine-learning de-blurring. We enforce solid opaque pixel overwrites rendered to a fresh canvas, completely discarding underlying pixel data.

* **Q3: How does the system handle indirect prompt injection on malicious websites?**  
  *Answer:* Page DOM text and OCR results are strictly classified as untrusted data. The action planner cannot execute arbitrary JavaScript or code; actions are restricted to schema-validated browser actions (`click`, `type`, `scroll`, `wait`) validated both on the server and independently in the local extension.
