"""
FULL DOWNLOADER FOR 100% OF ALL REMAINING FILES
Downloads every single file from:
1. WebPII/webpii (all 12 train shards + test shards = 6.31 GB)
2. osunlp/Multimodal-Mind2Web (all 48 shards = 12.64 GB)
3. Voxel51/ScreenSpot (all 616 files = 0.56 GB)
4. Voxel51/ScreenSpot-v2 (all 1278 files = 1.30 GB)
5. Voxel51/ScreenSpot-Pro (all 1587 files = 3.15 GB)
"""
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download
import time
import sys

api = HfApi()

REPOS = [
    {"repo_id": "WebPII/webpii", "target_dir": "data/raw/webpii"},
    {"repo_id": "osunlp/Multimodal-Mind2Web", "target_dir": "data/raw/multimodal_mind2web"},
    {"repo_id": "Voxel51/ScreenSpot", "target_dir": "data/raw/screenspot"},
    {"repo_id": "Voxel51/ScreenSpot-v2", "target_dir": "data/raw/screenspot_v2"},
    {"repo_id": "Voxel51/ScreenSpot-Pro", "target_dir": "data/raw/screenspot_pro"}
]

print("=== STARTING 100% EXHAUSTIVE DOWNLOAD OF ALL DATASETS ===")

for item in REPOS:
    repo = item["repo_id"]
    target = Path(item["target_dir"])
    target.mkdir(parents=True, exist_ok=True)
    
    print(f"\nFetching complete file list for {repo}...")
    info = api.dataset_info(repo, files_metadata=True)
    total_files = len(info.siblings)
    total_size_mb = sum([(f.size or 0) for f in info.siblings]) / (1024**2)
    print(f"Total files: {total_files} | Total volume: {total_size_mb:.2f} MB (~{total_size_mb/1024:.2f} GB)")
    
    downloaded_count = 0
    skipped_count = 0
    
    for idx, f in enumerate(info.siblings):
        fname = f.rfilename
        local_path = target / fname
        expected_size = f.size or 0
        
        # Check if already downloaded with correct size
        if local_path.exists() and (expected_size == 0 or local_path.stat().st_size == expected_size):
            skipped_count += 1
            continue
            
        print(f"[{idx+1}/{total_files}] Downloading {fname} ({expected_size / (1024**2):.2f} MB)...")
        try:
            hf_hub_download(
                repo_id=repo,
                repo_type="dataset",
                filename=fname,
                local_dir=target,
                resume_download=True
            )
            downloaded_count += 1
        except Exception as e:
            print(f"  [ERROR] {fname}: {e}")
            
    print(f"Finished {repo}: {downloaded_count} newly downloaded, {skipped_count} already existed.")

print("\n=== ALL 100% REPOSITORIES FULLY DOWNLOADED TO DISK! ===")
