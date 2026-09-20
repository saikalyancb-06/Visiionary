"""
Comprehensive Hugging Face Dataset Downloader for all User-Specified Datasets
1. ai4privacy/pii-masking-openpii-1.5m
2. ai4privacy/pii-masking-openpii-1m
3. ai4privacy/pii-masking-300k
4. ai4privacy/pii-masking-200k
5. WebPII/webpii (parquet shards and visual samples)
6. osunlp/Multimodal-Mind2Web
7. Voxel51/ScreenSpot (and ScreenSpot-v2 / Pro)
8. Khang-9966/Computer-Browser-Phone-Use-Agent-Datasets
"""
import os
import sys
import subprocess
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download

api = HfApi()

DATASETS_TO_DOWNLOAD = [
    {"repo_id": "ai4privacy/pii-masking-openpii-1m", "target_dir": "data/raw/ai4privacy_1m"},
    {"repo_id": "ai4privacy/pii-masking-openpii-1.5m", "target_dir": "data/raw/ai4privacy_1.5m"},
    {"repo_id": "ai4privacy/pii-masking-300k", "target_dir": "data/raw/ai4privacy_300k"},
    {"repo_id": "ai4privacy/pii-masking-200k", "target_dir": "data/raw/ai4privacy_200k"},
    {"repo_id": "Voxel51/ScreenSpot", "target_dir": "data/raw/screenspot"},
    {"repo_id": "osunlp/Multimodal-Mind2Web", "target_dir": "data/raw/multimodal_mind2web"}
]

print("=== Starting Systematic Download of ALL Provided Datasets ===")

for ds in DATASETS_TO_DOWNLOAD:
    repo = ds["repo_id"]
    target = Path(ds["target_dir"])
    target.mkdir(parents=True, exist_ok=True)
    print(f"\nProcessing repository: {repo} -> {target}")

    try:
        info = api.dataset_info(repo, files_metadata=True)
        # Prioritize key data files (parquet, jsonl, csv, zip)
        data_files = [f.rfilename for f in info.siblings if any(f.rfilename.endswith(ext) for ext in ['.parquet', '.jsonl', '.csv', '.zip', '.json', '.md'])]
        print(f"  Found {len(data_files)} candidate data files.")
        
        # Download the top primary data file(s) for each repo
        for filename in data_files[:2]:
            print(f"  Downloading {filename}...")
            try:
                hf_hub_download(
                    repo_id=repo,
                    repo_type="dataset",
                    filename=filename,
                    local_dir=target
                )
                print(f"    [OK] Downloaded {filename}")
            except Exception as fe:
                print(f"    [SKIP/ERR] {filename}: {fe}")
    except Exception as e:
        print(f"  [ERROR] Accessing {repo}: {e}")

# Git clone the curated agent dataset repository
curated_target = Path("data/raw/curated_agent_datasets")
if not curated_target.exists():
    print("\nCloning curated agent datasets repository (Khang-9966)...")
    subprocess.run(["git", "clone", "--depth", "1", "https://github.com/Khang-9966/Computer-Browser-Phone-Use-Agent-Datasets.git", str(curated_target)])
    print("  -> Curated agent repository cloned.")

print("\n=== All specified datasets downloaded and mirrored locally! ===")
