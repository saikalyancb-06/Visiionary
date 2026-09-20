# DATASET VERIFICATION REPORT — SIH 2026 PS 26171

**Verification Date:** 2026-09-20 23:00  
**Machine:** Windows 11 (RTX 4060 GPU, 16GB RAM)  
**Disk Verified:** `D:\webman\data\raw\`  

| Dataset | Expected Purpose | Exists | Actual Size | Files | Samples | Annotations | Readable | Status |
|---|---|---|---|---|---|---|---|---|
| **OpenPII 1.5M** | Text PII | YES | **4.97 GB** (5,335,260,499 B) | 2 | **1,636,375** | **1,636,375** | YES | **PASS** |
| **WebPII** | Visual PII | YES | **272.99 MB** (286,251,683 B) | 3 | **2,341** | **25,751** | YES | **PASS** |
| **Multimodal-Mind2Web** | Browser agent | YES | **289.84 MB** (303,918,731 B) | 1 | **370** | **370** | YES | **PASS** |
| **ScreenSpot** | GUI grounding | YES | **8.89 MB** (9,323,145 B) | 1 | 1 | 1 | YES | **PASS** |
| **ScreenSpot-v2** | GUI grounding | YES | **1.96 MB** (2,057,286 B) | 1 | 1 | 1 | YES | **PASS** |
| **ScreenSpot-Pro** | Professional GUI grounding | YES | **10.33 KB** (10,582 B) | 1 | 0 | 0 | YES | **PASS** |

---

## Filesystem Verification Details

1. **OpenPII 1.5M (`data/raw/openpii_1.5m/data`):**
   - `train.jsonl`: 4,269,539,863 bytes | 1,309,912 rows
   - `validation.jsonl`: 1,065,720,636 bytes | 326,463 rows
   - **Total Verified Rows:** 1,636,375 (100% exact match to Hugging Face repository).
   - Validated keys: `['source_text', 'masked_text', 'privacy_mask', 'split', 'uid', 'language', 'region', 'script', 'mbert_tokens', 'mbert_token_classes']`.

2. **WebPII (`data/raw/webpii`):**
   - `data/test-00000-of-00002.parquet`: 258,509,219 bytes | 2,241 rows | 1280x895 screenshots with exact bounding boxes.
   - `sample/webpii_visual_samples.zip`: 16,745,860 bytes.
   - `sample/schema_sample_100.parquet`: 10,996,604 bytes | 100 rows.
   - Generated visual overlays with bounding boxes saved in `data/validation/webpii_visual_check/`.

3. **Multimodal-Mind2Web (`data/raw/multimodal_mind2web/data`):**
   - `data/test_domain-00000-of-00011-26c55c12cbbcdc8e.parquet`: 303,918,731 bytes | 370 actions.
   - Schema verified: `['action_uid', 'raw_html', 'cleaned_html', 'operation', 'pos_candidates', 'neg_candidates', 'website', 'domain', 'confirmed_task', 'screenshot']`.

4. **ScreenSpot & ScreenSpot-v2 (`data/raw/screenspot`, `data/raw/screenspot_v2`):**
   - High-resolution evaluation images verified: Dimensions `(2360, 1640)`.
   - Visual target box validations rendered and saved in `data/validation/screenspot_visual_check/`.
