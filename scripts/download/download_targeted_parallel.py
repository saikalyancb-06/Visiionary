"""
Parallel Downloader for ScreenSpot, ai4privacy-200k, ai4privacy-300k, and Mind2Web
Downloads primary files concurrently without waiting for single 3.5GB giant shards.
"""
from pathlib import Path
from huggingface_hub import hf_hub_download
import concurrent.futures
import subprocess

TARGETS = [
    # 1. ScreenSpot annotations and images
    {"repo": "Voxel51/ScreenSpot", "file": "README.md", "dir": "data/raw/screenspot"},
    {"repo": "Voxel51/ScreenSpot", "file": "screenspot_web.json", "dir": "data/raw/screenspot"},
    # 2. ai4privacy 200k
    {"repo": "ai4privacy/pii-masking-200k", "file": "README.md", "dir": "data/raw/ai4privacy_200k"},
    {"repo": "ai4privacy/pii-masking-200k", "file": "data/validation.jsonl", "dir": "data/raw/ai4privacy_200k"},
    # 3. ai4privacy 300k
    {"repo": "ai4privacy/pii-masking-300k", "file": "README.md", "dir": "data/raw/ai4privacy_300k"},
    # 4. Multimodal Mind2Web
    {"repo": "osunlp/Multimodal-Mind2Web", "file": "README.md", "dir": "data/raw/multimodal_mind2web"}
]

def dl(item):
    try:
        p = Path(item["dir"])
        p.mkdir(parents=True, exist_ok=True)
        hf_hub_download(repo_id=item["repo"], repo_type="dataset", filename=item["file"], local_dir=p)
        print(f"Downloaded: {item['repo']} -> {item['file']}")
    except Exception as e:
        print(f"Error {item['repo']} / {item['file']}: {e}")

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
    ex.map(dl, TARGETS)

# Clone Khang repo
k_dir = Path("data/raw/curated_agent_datasets")
if not k_dir.exists():
    subprocess.run(["git", "clone", "--depth", "1", "https://github.com/Khang-9966/Computer-Browser-Phone-Use-Agent-Datasets.git", str(k_dir)])
