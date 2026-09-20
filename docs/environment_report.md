# ENVIRONMENT INSPECTION REPORT — SIH 2026 PS 26171

**Date:** 2026-09-20  
**Host Machine:** Windows 11 (build x86_64)  
**WSL2:** Ubuntu 24.04 LTS (Kernel: 5.15.x/6.x, Python 3.12.3)  

## 1. Hardware & Compute Specifications

* **CPU:** 13th Gen Intel(R) Core(TM) i7-13620H (10 Cores, 16 Logical Processors)
* **System RAM:** 16.0 GB Physical RAM
* **GPU:** NVIDIA GeForce RTX 4060 Laptop GPU
  * **VRAM:** 8,188 MiB (8 GB) GDDR6
  * **Driver Version:** 592.82
  * **CUDA Version:** 13.1 (Hardware/Driver max support)
* **Storage / Disk Budget:**
  * **Active Workspace Drive (D:):** 232.53 GB free / 292.97 GB total
  * **Data Budget (`DATA_BUDGET_GB`):** 60% of 232.53 GB = **139.5 GB max data budget**
  * **Secondary Storage (E:):** 255.84 GB free
  * **OS Drive (C:):** 85.99 GB free

## 2. Software & Toolchains Detected

| Tool | Host (Windows) | WSL2 (Ubuntu) | Status / Notes |
|---|---|---|---|
| Python | 3.14.3 (MSYS2 UCRT64) | 3.12.3 | WSL2 recommended for PyTorch CUDA compatibility |
| Node.js | v22.20.0 | - | Host ready for extension build & tooling |
| npm | 10.9.3 | - | Host ready |
| Git | 2.51.0.windows.1 | - | Host ready |
| Browsers | Google Chrome, MS Edge | - | Chrome present for extension loading & Playwright |
| PyTorch (CUDA) | Pending installation in venv | Pending installation | CUDA 12.4/12.6 wheels targetable |
| ONNX Runtime | Pending installation | Pending installation | ONNX Runtime CPU/GPU & Web |

## 3. Training & Compute Strategy

* **Per-run Training Wall-clock Budget:** Default 2.0 hours.
* **Acceleration Environment:** WSL2 Ubuntu 24.04 with NVIDIA CUDA container/direct passthrough for PyTorch training (as specified in Section A4).
* **Browser Runtime:** Google Chrome MV3 (host side) with Offscreen Document for ONNX Runtime Web (WASM + WebGPU fallback).
* **Fallbacks Documented:**
  * *If PyTorch CUDA wheel for Python 3.14 on Windows is unstable:* Use WSL2 Python 3.12 with official CUDA 12.4 PyTorch wheels.
  * *If WebGPU is unavailable in offscreen document context:* Fall back seamlessly to multi-threaded/single-threaded WebAssembly (`wasm-unsafe-eval`).
