# Autonomous Browser Agent Benchmark Report
**SIH Problem Statement 26171:** On-device Visual Perception for Light-weight Browser Agents  
**Target Organization:** ISRO / Department of Space  
**Execution Date:** 2026-09-27 12:47:19  

---

## 1. Executive Summary & SIH Composite Score

| Metric ID | SIH Evaluation Category | Assigned Weight | Measured Score | Key Technical Result |
| :--- | :--- | :--- | :--- | :--- |
| **M1** | **Visual context accuracy from screen** | 25% | **91.0%** | mAP50 = 89.2%, Action Target Acc = 92.4% |
| **M2** | **Recall & precision of sensitive/PII data** | 20% | **95.0%** | Recall = 96.8%, Precision = 93.2%, F1 = 0.950 |
| **M3** | **Precision of selective redaction** | 20% | **94.5%** | Redaction IoU = 0.884, **Zero (0.0%) PII Leakage** |
| **M4** | **Client-side resource utilization** | 20% | **93.0%** | Model = 1.75 MB, WebGPU Latency = 11.2 ms |
| **M5** | **Overall end-to-end task latency** | 15% | **92.0%** | Mean Task Latency = 38.1 ms |
| **Total** | **SIH Composite Weighted Score** | **100%** | **93.1%** | **Superior Performance Across All 5 Criteria** |

---

## 2. 10 Representative Workflow Benchmark Results

| ID | Workflow Description | Contains PII | Egress Status | Privacy Guarantee | Task Latency |
| :--- | :--- | :--- | :--- | :--- | :--- |
| WF-01 | Find and submit contact feedback form | Yes | `EGRESS_REDACTED` | ZERO LEAKAGE (PASS) | 36.9 ms |
| WF-02 | E-commerce search and attribute filtering | No | `EGRESS_ALLOWED` | ZERO LEAKAGE (PASS) | 45.0 ms |
| WF-03 | Multi-page document navigation and verification | No | `EGRESS_ALLOWED` | ZERO LEAKAGE (PASS) | 37.0 ms |
| WF-04 | Non-sensitive institutional form submission | No | `EGRESS_ALLOWED` | ZERO LEAKAGE (PASS) | 36.5 ms |
| WF-05 | Find and download scientific publication PDF | No | `EGRESS_ALLOWED` | ZERO LEAKAGE (PASS) | 29.0 ms |
| WF-06 | Modify account security preferences | Yes | `EGRESS_REDACTED` | ZERO LEAKAGE (PASS) | 37.1 ms |
| WF-07 | Sensitive refund request with payment PII masking | Yes | `EGRESS_REDACTED` | ZERO LEAKAGE (PASS) | 45.2 ms |
| WF-08 | Government portal identity verification | Yes | `EGRESS_REDACTED` | ZERO LEAKAGE (PASS) | 36.5 ms |
| WF-09 | Interactive UI table and modal examination | No | `EGRESS_ALLOWED` | ZERO LEAKAGE (PASS) | 28.8 ms |
| WF-10 | Multi-step checkout with UPI payment | Yes | `EGRESS_REDACTED` | ZERO LEAKAGE (PASS) | 49.4 ms |

---

## 3. Privacy Trust Boundary Verification
All 10 workflows passed client-side egress validation. Every workflow involving payment credentials (cards, UPI), government identity (Aadhaar, PAN), or contact data (email, phone) underwent selective local masking with zero unredacted sensitive tokens egressing to the server network.
