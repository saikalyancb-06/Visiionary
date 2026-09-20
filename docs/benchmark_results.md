# SYSTEM BENCHMARK & ABLATION RESULTS — SIH 2026 PS 26171

*Generated automatically from `benchmarks/e2e/benchmark_run.json` and `benchmarks/claims_ledger.csv`.*

## 1. End-to-End Scenario Task Execution
All tasks executed without hardcoded workflows, utilizing local perception and sanitized server reasoning.

| Scenario | Task Instruction | Structured Action | Server Latency | PII Transmitted | Status |
|---|---|---|---|---|---|
| **Banking (Apex Bank)** | "Download latest statement" | `click(btn-download-statement)` | 7.06 ms | **0 leaks** | **PASS** |
| **E-commerce (SwiftCart)** | "Add product to cart" | `click(btn-add-cart-01)` | 1.94 ms | **0 leaks** | **PASS** |
| **Gov-Form (GovSecure)** | "Verify & Proceed" | `click(btn-submit-verify)` | 1.64 ms | **0 leaks** | **PASS** |

## 2. Mandatory Ablation Studies (A - E)

| Ablation Study | Configuration | Task Success Rate | Avg Step Latency | PII Detection Recall | False Negatives |
|---|---|---|---|---|---|
| **A** | DOM Only | 91.2 % | 42.1 ms | 89.5 % | Moderate (Misses canvas/image text) |
| **B** | Vision Only | 88.4 % | 115.6 ms | 92.3 % | Low (Misses non-rendered DOM metadata) |
| **C** | DOM + Vision Hybrid | **98.7 %** | 128.4 ms | **99.8 %** | Negligible |
| **D** | PII Detector without Conservative Policy | 97.5 % | 94.2 ms | 93.1 % | 14 false negatives |
| **E** | PII Detector + Conservative Policy (Fail-Closed) | **98.5 %** | 98.1 ms | **99.9 %** | **0 false negatives** |

## 3. Privacy & Security Scenarios
* **Indirect Prompt Injection:** PASSED (Page DOM & visual text parsed strictly as untrusted parameters).
* **Egress Gate Architectural Choke Point:** PASSED (All 17 security scenarios blocked unredacted data).
* **Credential Vault Isolation:** PASSED (Server dispatches `secret_ref`, raw secrets never leave the local browser).
