"""
Download real parquet files and samples for WebPII and ScreenSpot directly from HuggingFace
"""
import os
from pathlib import Path
from huggingface_hub import hf_hub_download

WEBPII_DIR = Path("data/raw/webpii")
WEBPII_DIR.mkdir(parents=True, exist_ok=True)

print("Starting real download of WebPII official files from HuggingFace...")

# 1. Download official sample schema parquet
print("1/3 Downloading sample/schema_sample_100.parquet (10.49 MB)...")
hf_hub_download(
    repo_id="WebPII/webpii",
    repo_type="dataset",
    filename="sample/schema_sample_100.parquet",
    local_dir=WEBPII_DIR
)
print("  -> schema_sample_100.parquet downloaded.")

# 2. Download visual samples zip
print("2/3 Downloading sample/webpii_visual_samples.zip (15.97 MB)...")
hf_hub_download(
    repo_id="WebPII/webpii",
    repo_type="dataset",
    filename="sample/webpii_visual_samples.zip",
    local_dir=WEBPII_DIR
)
print("  -> webpii_visual_samples.zip downloaded.")

# 3. Download first test parquet shard
print("3/3 Downloading data/test-00000-of-00002.parquet (246.53 MB)...")
hf_hub_download(
    repo_id="WebPII/webpii",
    repo_type="dataset",
    filename="data/test-00000-of-00002.parquet",
    local_dir=WEBPII_DIR
)
print("  -> test-00000-of-00002.parquet downloaded.")

print("WebPII download completed successfully!")
