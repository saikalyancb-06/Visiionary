# SYSTEM THREAT MODEL — SIH 2026 PS 26171 (STRIDE Framework)

## 1. Assets
- Raw screen pixels containing sensitive financial, identity, or credential data.
- User credentials, OTPs, Aadhaar numbers, PAN cards, banking balances.
- Browser action execution integrity.

## 2. Adversaries & Threat Vectors
1. **Network Observer / Man-in-the-Middle:** Mitigated by Local Zone processing; raw PII never reaches the network.
2. **Untrusted / Curious Cloud LLM Provider:** Mitigated by Solid Opaque local redaction, typed placeholders (`[[TYPE_N]]`), and Egress Gate choking.
3. **Malicious Web Page (Indirect Prompt Injection):** Mitigated by treating all page text and DOM attributes strictly as untrusted metadata. Server outputs are restricted to schema-validated allow-list actions (`click`, `type`, `scroll`, `wait`).
4. **Faulty / Compromised Server Output:** The browser extension validates every action locally, rejecting off-origin navigation or invalid selectors.
5. **High-Risk Actions (Payment, Deletion):** Require explicit user confirmation modal before execution.

## 3. Residual Leakage & Mitigations
- **Bounding-box length leakage:** Mitigated by quantizing/padding redaction bounding boxes.
- **Fail-Closed Guarantee:** If any detector errors or times out, the Egress Gate blocks all outgoing requests.
