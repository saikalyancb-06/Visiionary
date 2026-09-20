# DECISIONS LOG — SIH 2026 PS 26171

All non-obvious architecture, engineering, and model choices are recorded here with options considered, trade-offs, and rationale.

---

### DEC-001: Accelerated Training Environment on Windows (WSL2 Ubuntu vs Native Windows Python 3.14)
* **Date:** 2026-09-20
* **Context:** Host OS is Windows 11 with Python 3.14 (MSYS2 UCRT64). Official pre-built PyTorch CUDA wheels for Windows with CUDA 12.x/13.x are generally targeted up to Python 3.12. Host machine has WSL2 Ubuntu 24.04 with Python 3.12 and direct NVIDIA RTX 4060 GPU passthrough.
* **Options Considered:**
  1. Attempt to build PyTorch from source for Python 3.14 on Windows.
  2. Use WSL2 Ubuntu 24.04 (Python 3.12.3 + PyTorch CUDA 12.4/12.6) for GPU training and dataset preparation, with exported ONNX models served to the Windows Chrome browser runtime.
* **Decision:** Option 2 (WSL2 for GPU model training, Windows host for Chrome MV3 extension runtime & FastAPI).
* **Rationale:** Maximizes stability, guarantees official PyTorch CUDA acceleration and mixed precision (AMP) without source compilation instability.

---

### DEC-002: Browser MV3 Inference Context (Offscreen Document vs Service Worker)
* **Date:** 2026-09-20
* **Context:** Chrome Manifest V3 service workers are ephemeral and cannot access DOM `canvas` or WebGPU consistently across all background states.
* **Options Considered:**
  1. Service Worker inference (ephemeral lifecycle issues, no WebGPU).
  2. Offscreen Document (`chrome.offscreen`) dedicated to hosting ONNX Runtime Web sessions.
* **Decision:** Option 2 (Offscreen Document).
* **Rationale:** Offscreen documents provide persistent WebAssembly / WebGPU access, full Canvas 2D / WebGL support for image preprocessing and redaction verification, and avoid worker termination mid-inference.

---

### DEC-003: Licensing Choice for Object Detection Architectures
* **Date:** 2026-09-20
* **Context:** Section A5 requires conscious licensing decisions (Ultralytics YOLO is AGPL-3.0).
* **Options Considered:**
  1. Ultralytics YOLOv8/v11 (AGPL-3.0 - viral copyleft restrictions).
  2. Apache 2.0 / MIT architectures: MobileNetV3-SSDLite, YOLOX (Apache 2.0), RT-DETR (Apache 2.0 / Paddle), torchvision lightweight detectors.
* **Decision:** Provide support for Apache 2.0 / MIT lightweight detectors (MobileNetV3 SSDLite / YOLOX-nano) for permissible distribution, alongside benchmarks of compact models to guarantee no licensing ambiguity for ISRO deliverables.
