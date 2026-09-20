"""
Download real full files for OpenPII 1.5M:
- data/validation.jsonl (1.07 GB / 1,065,720,636 bytes)
- data/train.jsonl (4.27 GB / 4,269,539,863 bytes)
"""
from pathlib import Path
from huggingface_hub import hf_hub_download
import time

TARGET_DIR = Path("data/raw/openpii_1.5m")
TARGET_DIR.mkdir(parents=True, exist_ok=True)

print("Starting direct download of OpenPII 1.5M validation.jsonl...")
t0 = time.time()
hf_hub_download(
    repo_id="ai4privacy/pii-masking-openpii-1.5m",
    repo_type="dataset",
    filename="data/validation.jsonl",
    local_dir=TARGET_DIR
)
print(f"validation.jsonl downloaded in {time.time() - t0:.2f}s")

print("Starting direct download of OpenPII 1.5M train.jsonl...")
t0 = time.time()
hf_hub_download(
    repo_id="ai4privacy/pii-masking-openpii-1.5m",
    repo_type="dataset",
    filename="data/train.jsonl",
    local_dir=TARGET_DIR
)
print(f"train.jsonl downloaded in {time.time() - t0:.2f}s")

print("OpenPII 1.5M complete!")
