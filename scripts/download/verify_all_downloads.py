from pathlib import Path
import os

files = [
    ("WebPII Parquet Test Shard", "data/raw/webpii/data/test-00000-of-00002.parquet"),
    ("WebPII Visual Samples Zip", "data/raw/webpii/sample/webpii_visual_samples.zip"),
    ("WebPII Schema Sample", "data/raw/webpii/sample/schema_sample_100.parquet"),
    ("ai4privacy 1M Validation JSONL", "data/raw/ai4privacy/data/validation.jsonl"),
    ("ai4privacy 200k English JSONL", "data/raw/ai4privacy_200k/english_pii_43k.jsonl"),
    ("ai4privacy 300k English JSONL", "data/raw/ai4privacy_300k/data/train/1english_openpii_30k.jsonl"),
    ("ScreenSpot Image Sample", "data/raw/screenspot/data/mobile_043c3a5e-c12c-4991-bb7f-676c617b2f9b.png"),
    ("Curated Agent Datasets Repo", "data/raw/curated_agent_datasets/README.md")
]

print("=== REAL DATASET VERIFICATION SUMMARY ===")
total = 0
for name, p in files:
    f = Path(p)
    if f.exists():
        sz = f.stat().st_size
        total += sz
        print(f"[VERIFIED] {name:<32} : {sz / (1024*1024):>8.2f} MB ({p})")
    else:
        print(f"[MISSING]  {name:<32} : NOT FOUND")

print(f"\nTOTAL VERIFIED REAL DATA ON DISK: {total / (1024*1024):.2f} MB (~{total / (1024**3):.2f} GB)")
