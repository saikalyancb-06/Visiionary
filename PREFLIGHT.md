# PREFLIGHT INSPECTION REPORT (GATE 2)

**Machine:** Windows 11 (build x86_64)  
**GPU:** NVIDIA GeForce RTX 4060 Laptop GPU (8188 MiB VRAM)  
**CUDA Version:** 13.1 (Driver: 592.82)  
**PyTorch:** 2.6.0+cu124 (CUDA Available: True)  
**Python Environment:** C:\Users\cbsai\AppData\Local\Programs\Python\Python313\python.exe  
**Disk Space Budget:** D: drive free: 232 GB -> DISK_BUDGET_GB = min(60, 50% of 232) = 60.0 GB  

## Toolchain Status
- Python 3.13.x / WSL2 Python 3.12: READY
- Node.js v22.20.0, npm 10.9.3: READY
- Git 2.51.0: READY
- Chrome: PRESENT
- Playwright: INSTALLED
- ONNX & ONNX Runtime: INSTALLED & VERIFIED
- FastAPI & Uvicorn: RUNNING

## OOM Mitigation Strategy (RTX 4060 8GB VRAM)
1. Default resolution: 640x640 (letterboxed)
2. Batch size: 8-16 with AMP (`torch.amp.autocast`)
3. Gradient accumulation: 2-4 steps if needed
4. Model architecture: Lightweight MobileNetV3/SSDLite style backbone + custom NER heads
