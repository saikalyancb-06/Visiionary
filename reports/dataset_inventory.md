# Dataset Inventory & Characterization Report
**SIH Problem Statement 26171:** On-device Visual Perception for Light-weight Browser Agents  
**Target Organization:** ISRO / Department of Space  
**Generated:** 2026-09-27  

---

## 1. Unified Dataset Summary

The training and perception corpus integrates **37.4+ GB** of existing curated datasets with external target datasets covering UI detection, dense screen parsing, multilingual PII extraction, and grounded browser actions.

| Dataset Name | Source Location | Total Size (GB) | Sample Count | Modality & Annotations | Training Role | Validation / Benchmark Role |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **WebPII** | `data/raw/webpii` | 6.31 GB | 4,200+ samples | Web screenshots, bounding boxes, 20+ PII categories | Stage B (PII Detection) | Visual PII Recall & Redaction IoU |
| **OpenPII 1.5M** | `data/raw/openpii_1.5m` | 4.97 GB | 1,500,000 tokens | Multilingual text PII entity spans, Indian & global context | Stage B (Text PII Detection) | Text PII Precision & Recall |
| **Multimodal Mind2Web** | `data/raw/multimodal_mind2web` | 12.64 GB | 10,000+ trajectories | Full web DOM, accessibility trees, viewport screenshots, actions | Stage C (Action Grounding) | Multi-step Task Completion |
| **ScreenSpot Suite** | `data/raw/screenspot*` | 5.01 GB | 6,968 screens | Web, mobile, and desktop screens with UI bounding boxes | Stage A (UI Perception) | mAP50, Click Target Precision |
| **AI4Privacy Suite** | `data/raw/ai4privacy*` | 8.45 GB | 3,000,000+ spans | Synthetic and real multilingual PII annotations | Stage B (PII Regularization) | Generalization & Zero-Shot PII |
| **ScreenParse** | `data/external/screenparse` | 1.6+ GB (shards) | 2,500+ dense screens | Screen-level parsing, 55 UI classes, bounding boxes, reading order | Stage A (Dense UI Perception) | Screen Parsing Accuracy, Dense mAP |
| **GroundCUA** | `data/external/groundcua` | 1.2+ GB (shards) | 4,000+ interactions | Real desktop & web software platforms, computer-use actions | Stage A & C (UI & Action Grounding) | Cross-Application Grounding |
| **AndroidControl** | `data/external/android_control` | 1.5+ GB (shards) | 5,000+ gestures | Mobile screen states, touch coordinates, action labels | Stage C (Action Grounding) | Gesture Precision & Trajectory Flow |
| **Android in the Wild** | `data/external/android_in_the_wild` | 0.8+ GB (shards) | 3,500+ trajectories | Dual-point touches, scrolls, high-level user tasks | Stage C (Action Grounding) | Long-Horizon Task Grounding |
| **WebChain v2** | `data/external/webchain` | 1.8+ GB (shards) | 2,000+ workflows | DOM alignments, bounding boxes, grounded browser operations | Stage C (Browser Workflows) | Complex Multi-Page Web Navigation |

---

## 2. Taxonomy Coverage Matrix

### A. UI Element Taxonomy (34 Categories)
`button`, `link`, `text`, `heading`, `input`, `password_input`, `search`, `checkbox`, `radio`, `select`, `dropdown`, `menu`, `tab`, `navigation`, `sidebar`, `toolbar`, `table`, `list`, `image`, `icon`, `avatar`, `notification`, `dialog`, `modal`, `scroll`, `slider`, `calendar`, `date_picker`, `pagination`, `code`, `chart`, `video`, `window`, `other`.

### B. PII Taxonomy (26 Categories including Indian Context)
- **Direct Identifiers:** `PERSON`, `EMAIL`, `PHONE`, `ADDRESS`, `USERNAME`, `OTHER_IDENTIFIER`
- **Authentication & Secrets:** `PASSWORD`, `OTP`, `API_KEY`, `ACCESS_TOKEN`, `JWT`, `SECRET`, `PRIVATE_MESSAGE`
- **Financial & Payment:** `CREDIT_CARD`, `DEBIT_CARD`, `BANK_ACCOUNT`, `IFSC`, `UPI_ID`, `FINANCIAL_VALUE`
- **Government & Identity (Indian & Global):** `AADHAAR`, `PAN`, `PASSPORT`, `DRIVERS_LICENSE`, `DATE_OF_BIRTH`
- **Biometric & Physical:** `FACE`, `QR_CODE`

---

## 3. Storage Allocation & Preservation Guarantee
- **Existing `data/raw/` Corpus:** 37.38 GB (Strictly preserved, read-only).
- **External Ingested `data/external/` Corpus:** Complete valid shards matching storage budget (~6–10 GB total).
- **Host Drive Capacity:** D: drive has 172.39 GB free, leaving >135 GB headroom for model weights, ONNX exports, training logs, and evaluations.
