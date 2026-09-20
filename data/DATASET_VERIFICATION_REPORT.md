# MASTER DATASET VERIFICATION & INVENTORY AUDIT — SIH 2026 PS 26171

**Verification Timestamp:** 2026-09-21 01:48  
**Operating System:** Windows 11 (win32)  
**Host Machine:** 13th Gen Intel Core i7-13620H, 16GB RAM, NVIDIA GeForce RTX 4060 Laptop GPU  
**Total Verified Real Data on Disk:** **28.91 GB (31,041,840,503 bytes)**  
**Total Dataset Files Stored:** **7,031 files**  

---

## Exhaustive Dataset Inventory Table

| Dataset | Expected Purpose | Exists | Actual Size | Files on Disk | Samples / Rows | Ground-Truth Format | Status |
|---|---|---|---|---|---|---|---|
| **OpenPII 1.5M (Full)** | Text PII / NER | YES | **4.97 GB** (5,335,260,499 B) | 2 | **1,636,375** | JSONL (`source_text`, `mbert_tokens`, `mbert_token_classes`) | **PASS** |
| **WebPII (Full 14 Shards)** | Visual PII Detection | YES | **6.29 GB** (6,757,990,342 B) | 14 | **44,865** | Parquet (1280x895 PNG bytes, PII bounding boxes) | **PASS** |
| **Multimodal-Mind2Web (Full)** | Browser Agent Grounding | YES | **12.64 GB** (13,577,369,971 B) | 47 | **14,193** | Parquet (`screenshot`, `raw_html`, `target_action_reprs`) | **PASS** |
| **ScreenSpot (Full)** | GUI Grounding | YES | **0.56 GB** (598,392,104 B) | 1,234 | 600+ | PNG screenshots + JSON metadata | **PASS** |
| **ScreenSpot-v2 (Full)** | Multi-platform GUI Grounding | YES | **1.30 GB** (1,399,842,156 B) | 2,558 | 1,200+ | PNG screenshots + target coordinates | **PASS** |
| **ScreenSpot-Pro (Full)** | High-Res Professional UI | YES | **3.15 GB** (3,372,985,431 B) | 3,176 | 1,500+ | High-Res PNG (2360x1640) + `samples.json` | **PASS** |

---

## Verification & Integrity Checks Completed
1. **OpenPII 1.5M:** Exactly 1,636,375 rows verified across `train.jsonl` and `validation.jsonl`.
2. **WebPII:** All 12 training shards + 2 test shards verified; 44,865 shopping & payment UI screenshots with pixel bounding boxes.
3. **Multimodal-Mind2Web:** 47 complete parquet shards verified containing 14,193 end-to-end task trajectories.
4. **ScreenSpot Suite (v1, v2, Pro):** Every single PNG image and JSON annotation file downloaded and verified on disk.
5. **No Redundant Duplicates:** All assets organized cleanly under `data/raw/`.
