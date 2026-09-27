# Visiionary Project Comprehensive System Audit
**Problem Statement ID:** 26171  
**Problem Statement Title:** On-device Visual Perception for Light-weight Browser Agents  
**Target Organization:** Indian Space Research Organisation (ISRO) / Department of Space  
**Audit Date:** 2026-09-27  

---

## 1. System Overview & Current Architecture

Visiionary Browser Agent is an on-device privacy-preserving vision agent operating as a Chromium Manifest V3 extension coupled with an asynchronous Python FastAPI backend planner. The system enforces strict on-device data sovereignty: screen capture, DOM extraction, visual perception, PII identification, and redaction occur locally inside the browser client before any network egress. Only anonymized, redaction-masked payloads reach the server-side LLM planner for multi-step reasoning.

```mermaid
flowchart TD
    Screen[Browser Tab Screen State] --> Capture[Capture Screenshot Offscreen / Tab]
    DOMTree[Accessibility / DOM Tree] --> Capture
    Capture --> LocalVision[Local Vision / PII Detector (ONNX Runtime Web)]
    LocalVision --> PrivacyGate[Local Privacy Egress Gate]
    DOMTree --> PrivacyGate
    PrivacyGate -->|Fail-Closed Check| SanitizedPayload[Sanitized Context Package]
    PrivacyGate -.->|Violation Detected| Block[Block Network Request]
    SanitizedPayload -->|HTTP POST| ServerPlanner[FastAPI Server Planner]
    ServerPlanner --> LLM[Local/Cloud Reasoning LLM]
    LLM --> StructuredAction[Structured BrowserAction]
    StructuredAction --> LocalValidator[Local Client Action Validator]
    LocalValidator --> Execution[Browser DOM Event Dispatcher]
    Execution --> Screen
```

---

## 2. Existing Models & Checkpoints

The repository maintains lightweight PyTorch checkpoints and corresponding ONNX exports designed for browser execution (WASM / WebGPU):

| Model Name | Checkpoint Path | ONNX Export Path | Size | Architecture / Classes |
| :--- | :--- | :--- | :--- | :--- |
| **Regularized PII Detector** | `models/checkpoints/regularized_best_pii_detector.pt` | `models/onnx/regularized_visual_pii_detector.onnx` | ~1.85 MB (.pt)<br>1.75 MB (.onnx) | MobileNetV3-style Conv2d + BatchNorm + SiLU + Dropout, 20 PII classes + Bbox Regression |
| **Browser Agent Detector** | `models/checkpoints/browser_agent_detector.pt` | `models/onnx/browser_agent_detector.onnx` | ~1.85 MB | Primary deployed on-device model |
| **Text PII Detector** | `models/checkpoints/text_pii_detector.pt` | N/A (PyTorch) | ~2.09 MB | BiLSTM + Linear for token/text classification |
| **Heavy PII Detector** | `models/checkpoints/heavy_pii_detector_epoch_*.pt` | `models/onnx/heavy_visual_pii_detector.onnx` | ~1.85 MB | Multi-epoch checkpoints (epochs 1 to 50) |
| **Extension Asset** | N/A | `browser-extension/public/models/detector.onnx` | 1.75 MB | Model packaged directly inside Chrome extension |

---

## 3. Existing Datasets Inventory (Preserved in `data/raw/`)

Total local raw dataset storage currently occupies **~37.4 GB** across 7,000+ files:

| Dataset Directory | Size (GB) | File Count | Modality / Contents | Status / Action |
| :--- | :--- | :--- | :--- | :--- |
| `data/raw/multimodal_mind2web` | 12.64 GB | 100 files | Multi-step browser interaction traces & DOM-action groundings | **Preserve & Read-Only** |
| `data/raw/webpii` | 6.31 GB | 43 files | Web screenshots, bounding boxes, PII labels | **Preserve & Read-Only** |
| `data/raw/openpii_1.5m` | 4.97 GB | 6 files | Text PII spans, multilingual tokens | **Preserve & Read-Only** |
| `data/raw/ai4privacy_1.5m` | 3.98 GB | 6 files | Text tokens & PII classification | **Preserve & Read-Only** |
| `data/raw/ai4privacy_1m` | 3.44 GB | 6 files | Text tokens & PII classification | **Preserve & Read-Only** |
| `data/raw/screenspot_pro` | 3.15 GB | 3,176 files | High-res UI screens, bounding boxes, instructions | **Preserve & Read-Only** |
| `data/raw/screenspot_v2` | 1.30 GB | 2,558 files | Mobile, web, desktop screens & bounding boxes | **Preserve & Read-Only** |
| `data/raw/screenspot` | 0.56 GB | 1,234 files | Original ScreenSpot UI benchmark screens | **Preserve & Read-Only** |
| `data/raw/ai4privacy` & variants | 1.03 GB | 19 files | Multi-split PII datasets | **Preserve & Read-Only** |

*Note: In accordance with project requirements, no files in `data/raw/` will be deleted, altered, or duplicated.*

---

## 4. Existing Training Pipeline

1. **Scripts Available:**
   - `ml/training/train_real.py`: Loads real WebPII parquet shards, extracts image bytes, trains bounding box + classification heads.
   - `ml/training/regularized_train.py`: Employs Spatial Dropout2d (0.2), Linear Dropout (0.3), AdamW with weight decay $10^{-4}$, AMP (autocast + GradScaler), and early stopping on held-out validation loss.
   - `ml/training/heavy_train_overnight.py`: 50-epoch checkpointing runner.
   - `ml/export/export_regularized_onnx.py`: Exports PyTorch model to ONNX with dynamic batching, opset 17.
2. **Execution Environment:**
   - Python: 3.13.1 64-bit
   - PyTorch: 2.x with CUDA 12.8 support
   - GPU: NVIDIA GeForce RTX 4060 Laptop GPU (8.0 GB VRAM)
   - CPU: 10 physical cores / 16 logical cores
   - Host Memory: 15.65 GB RAM (5.5 GB available)
   - Disk D: 172.39 GB free space

---

## 5. Existing Inference Pipeline

1. **Client-Side ONNX Runtime Web:**
   - Located at `browser-extension/src/inference/runner.js`.
   - Uses `window.ort` (loaded from `public/ort/` in the extension package).
   - Attempts WebGPU backend (`executionProviders: ['webgpu', 'wasm']`), gracefully falling back to WASM if WebGPU is unavailable or disabled.
   - Input format: Planar float32 RGB tensor `[1, 3, 320, 320]`, normalized to $[0, 1]$.
   - Output format: Bounding box sigmoid coordinates $[x_1, y_1, x_2, y_2]$ and class logit distribution.
2. **Latency:**
   - WebGPU Inference: ~8–16 ms per frame.
   - WASM Inference: ~40–70 ms per frame.

---

## 6. Existing Autonomous Actions & State Machine

1. **Server-Side State Machine (`server/app/task_state_machine.py`):**
   - Implements 10 phases: `DISCOVER` $\rightarrow$ `SEARCH` $\rightarrow$ `EXTRACT_ENTITIES` $\rightarrow$ `ACCUMULATE_CANDIDATES` $\rightarrow$ `COMPARE` $\rightarrow$ `SELECT_TARGET` $\rightarrow$ `OPEN_TARGET` $\rightarrow$ `VERIFY_TARGET_PAGE` $\rightarrow$ `EXTRACT_INFORMATION` $\rightarrow$ `GOAL_ACHIEVED`.
   - Blocks illegal transitions with `PLANNER_BLOCKED` diagnostics.
2. **Planner (`server/app/planner.py` & `llm_planner.py`):**
   - Supports Ollama local LLMs (e.g., Qwen2.5/3.5) and heuristic fallback.
   - Parses natural-language user queries into generic candidate constraints (sorting by price, ratings, best seller, keyword match) with zero website hardcoding.
3. **Client-Side Execution (`browser-extension/src/agent/executor.js` & `content/content.js`):**
   - Dispatches real trusted DOM events (`pointerdown`, `mousedown`, `click`, `input`, `keydown`, `keyup`).
   - Simulates smooth human-like scrolling and typing.

---

## 7. Existing Privacy Mechanism

1. **Client-Side Egress Gate (`browser-extension/src/egress/gate.js`):**
   - Single point of egress: all outbound network calls to `/api/agent/plan` pass through `sendSanitizedContextToGate`.
   - Performs schema verification.
   - Runs post-redaction deep privacy scans (`verifyPostRedactionPrivacy`).
   - Checks for raw vault credential leaks (`containsVaultSecret`).
   - Emits `EGRESS_ALLOWED` or `EGRESS_BLOCKED` without logging sensitive values.
2. **Server-Side Defense-in-Depth (`server/app/main.py`):**
   - Second-line scanner on received text fields with Verhoeff (Aadhaar) and Luhn (Cards) checksum validation to avoid false positives on catalog/SKU numbers.

---

## 8. Current Bottlenecks & Gaps Identified

1. **Single-Element Visual Detection:**
   - Current `LightweightBrowserAgentDetector` predicts a single bounding box and class per forward pass. A production UI agent requires dense multi-element detection (anchors, inputs, buttons, tables, menus, icons, cards).
2. **Separated Perception Pipelines:**
   - UI structure detection, PII detection, and Action grounding are currently separated rather than coordinated through a unified dataset adapter and perception fusion framework.
3. **Absence of Unified Schema:**
   - Datasets in `data/raw/` use distinct formats (parquet with embedded bytes, json bboxes in xywh vs xyxy, text span offsets).
4. **Missing External Target Datasets:**
   - ScreenParse, GroundCUA, AndroidControl, Android in the Wild, and WebChain v2 must be downloaded as clean, complete shards into `data/external/` with rigorous manifests.
5. **Overnight Pipeline Runner:**
   - Requires a unified, automated, resumable multi-stage master script (`scripts/run_overnight_pipeline.py`) supporting graceful recovery, checkpointed stage markers (`runs/state/`), and comprehensive SIH metric reporting.

---

## 9. File Modification Plan

### A. Files to Create / Add
- `reports/project_audit.md` (this audit report)
- `data/external/{screenparse,groundcua,android_control,android_in_the_wild,webchain}`
- `data/manifests/{screenparse,groundcua,android_control,android_in_the_wild,webchain}_manifest.json`
- `reports/dataset_inventory.md`
- `dataset_adapters/base.py`
- `dataset_adapters/{webpii,openpii,mind2web,screenspot,screenparse,groundcua,android_control,android_in_the_wild,webchain}.py`
- `reports/data_quality_report.json`
- `privacy/pii_fusion.py`
- `privacy/confidence_engine.py`
- `privacy/redaction_engine.py`
- `privacy/egress_gate.py`
- `ml/training/{train_ui_stage_a,train_pii_stage_b,train_action_stage_c}.py`
- `scripts/export_onnx.py`
- `scripts/validate_onnx.py`
- `scripts/run_overnight_pipeline.py`
- `tests/test_privacy_attacks.py`
- `tests/test_action_validation.py`
- `benchmarks/run_sih_benchmarks.py`
- `models/model_registry.json`
- `reports/overnight_training_report.md`
- `reports/overnight_training_report.json`

### B. Files to Modify (Carefully preserving working functionality)
- `ml/models/detector.py`: Extend architecture to support dense multi-head detection and action grounding heads while keeping ONNX-Web compatibility.
- `server/app/planner.py` & `main.py`: Integrate unified egress validation schemas and client action verification rules.
- `browser-extension/src/inference/runner.js`: Support dense multi-element output parsing alongside existing single-box legacy fallback.

### C. Files to Keep Untouched
- `data/raw/**/*`: All 37.4 GB of existing downloaded datasets remain intact and immutable.
- `models/checkpoints/regularized_best_pii_detector.pt`: Retained as baseline checkpoint.
- `models/onnx/regularized_visual_pii_detector.onnx`: Retained as working fallback.
- `server/app/task_state_machine.py`: Verified dependency order and state transitions.
- `server/app/candidate_extractor.py`, `product_constraints.py`, `verifier.py`: Keep core e-commerce, search, and generic evaluation logic.
- `browser-extension/src/background/background.js`, `src/vault/vault.js`: Retain credential vault and session persistence.
