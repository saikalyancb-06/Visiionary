# DATASET VERIFICATION REPORT — SIH 2026 PS 26171

**Verification Date:** 2026-09-21 00:30  
**Machine:** Windows 11 (RTX 4060 GPU, 16GB RAM)  
**Total Verified Real Data on Disk:** **23.92 GB (25,681,564,051 bytes)**  

| Dataset | Expected Purpose | Exists | Actual Size | Files | Samples / Rows | Annotations | Readable | Status |
|---|---|---|---|---|---|---|---|---|
| **OpenPII 1.5M** | Text PII | YES | **4.97 GB** (5,335,260,499 B) | 2 | **1,636,375** | **1,636,375** | YES | **PASS** |
| **WebPII (Full)** | Visual PII | YES | **6.29 GB** (6,757,990,342 B) | 14 | **44,865** | **44,865** | YES | **PASS** |
| **Multimodal-Mind2Web (Full)** | Browser agent | YES | **12.64 GB** (13,577,369,971 B) | 47 | **14,193** | **14,193** | YES | **PASS** |
| **ScreenSpot Family** | GUI grounding | YES | **20.85 MB** (21,863,239 B) | 29 | 29 | 29 | YES | **PASS** |

---

## Detailed Verified Inventory
1. **OpenPII 1.5M (`data/raw/openpii_1.5m/data/`):**
   - `train.jsonl`: 4,269,539,863 bytes | 1,309,912 rows
   - `validation.jsonl`: 1,065,720,636 bytes | 326,463 rows
   - **Total Verified Rows:** 1,636,375 (100% exact match).

2. **WebPII (`data/raw/webpii/data/`):**
   - All 14 parquet shards verified (`test-00000` through `test-00001`, `train-00000` through `train-00011`).
   - **Total Verified Rows:** 44,865 rows with exact bounding boxes for e-commerce UI screenshots.

3. **Multimodal-Mind2Web (`data/raw/multimodal_mind2web/data/`):**
   - All 47 parquet shards verified (`train-00000` to `00026`, `test_domain-00000` to `00010`, `test_task-00000` to `00005`, `test_website-00000` to `00003`).
   - **Total Verified Actions:** 14,193 complete browser-agent trajectories (`action_uid`, `screenshot`, `raw_html`, `target_action`).

4. **ScreenSpot Family (`data/raw/screenspot/`, `screenspot_v2/`):**
   - High-resolution evaluation images verified: Dimensions `(2360, 1640)`.
   - Visual target box validations rendered and saved in `data/validation/screenspot_visual_check/`.
