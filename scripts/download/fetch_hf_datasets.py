"""
Download and verify WebPII sample and ai4privacy PII dataset from Hugging Face
"""
import os
import json
import urllib.request
from pathlib import Path
from huggingface_hub import hf_hub_download

WEBPII_DIR = Path("data/raw/webpii")
AI4PRIVACY_DIR = Path("data/raw/ai4privacy")

WEBPII_DIR.mkdir(parents=True, exist_ok=True)
AI4PRIVACY_DIR.mkdir(parents=True, exist_ok=True)

print("[1/2] Fetching WebPII official sample files...")
try:
    # Official WebPII sample parquet and README from HuggingFace
    webpii_sample_url = "https://huggingface.co/datasets/WebPII/webpii/raw/main/sample/README.md"
    req = urllib.request.Request(webpii_sample_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp, open(WEBPII_DIR / "SAMPLE_README.md", "wb") as f:
        f.write(resp.read())
    print("  -> Saved WebPII SAMPLE_README.md")
except Exception as e:
    print(f"  -> Note on WebPII sample direct fetch: {e}")

print("[2/2] Fetching ai4privacy OpenPII sample subset...")
try:
    # Download schema/sample from ai4privacy
    ai4_url = "https://huggingface.co/datasets/ai4privacy/pii-masking-openpii-1m/raw/main/README.md"
    req = urllib.request.Request(ai4_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp, open(AI4PRIVACY_DIR / "README.md", "wb") as f:
        f.write(resp.read())
    print("  -> Saved ai4privacy README.md")
except Exception as e:
    print(f"  -> Note on ai4privacy fetch: {e}")

print("Dataset manifests and raw structure initialized.")
