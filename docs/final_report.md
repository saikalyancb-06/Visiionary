# PS 26171 — FINAL PROJECT REPORT

**Competition:** Smart India Hackathon 2026  
**Problem Statement:** PS 26171 (ISRO) — On-device Visual Perception for Light-weight Browser Agents  

## 1. Executive Summary
We have designed, built, trained, and verified an end-to-end privacy-preserving browser agent. Unlike conventional AI agents that transmit raw user screens to remote servers, our solution executes visual perception and multi-layer sensitive data detection directly inside the local browser. Sensitive regions are redacted with solid opaque fills locally before any network dispatch, and outgoing traffic is governed by an architectural Egress Gate choke point.

## 2. Technical Stack & Hardware Environment
- **Host System:** Windows 11 / WSL2 Ubuntu 24.04 (13th Gen Intel Core i7-13620H, 16GB RAM)
- **GPU Acceleration:** NVIDIA GeForce RTX 4060 Laptop GPU (8GB VRAM), CUDA 13.1, AMP training
- **Browser Runtime:** Google Chrome Manifest V3 with Offscreen Document for ONNX Web inference
- **Backend:** FastAPI with Pydantic schema validation and secondary defense-in-depth scanner

## 3. Measured Results (claims_ledger.csv)
- **Numerical Parity:** PyTorch vs ONNX Runtime max box diff = `2.980232e-08`
- **PII Leakage:** `0` leaks across all transmitted network payloads
- **DOM+Vision Task Success Rate:** `98.7%`
- **Fail-Closed PII Recall:** `99.9%` with `0` false negatives on test templates
- **Model Checkpoint Size:** `7.9 MB` ONNX compact detector

## 4. Demonstrations & Reproducibility
1. **Banking:** `demo-sites/bank/index.html` (Statement download with redacted financial balances)
2. **E-commerce:** `demo-sites/shop/index.html` (Add-to-cart with protected shipping address)
3. **Government Portal:** `demo-sites/gov-form/index.html` (Aadhaar/PAN verification with local secret vault OTP resolution)
