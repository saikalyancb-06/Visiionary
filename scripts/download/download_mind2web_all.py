"""
Download 100% of all Multimodal-Mind2Web parquet shards (12.64 GB)
"""
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download
import time

TARGET_DIR = Path("data/raw/multimodal_mind2web")
TARGET_DIR.mkdir(parents=True, exist_ok=True)

api = HfApi()
info = api.dataset_info("osunlp/Multimodal-Mind2Web", files_metadata=True)

print(f"Starting 100% download of Multimodal-Mind2Web ({len(info.siblings)} files)...")

for idx, f in enumerate(info.siblings):
    fname = f.rfilename
    if fname.endswith(".parquet") or fname.endswith(".json") or fname.endswith(".md"):
        local_f = TARGET_DIR / fname
        if local_f.exists() and (f.size is None or local_f.stat().st_size == f.size):
            print(f"[{idx+1}/{len(info.siblings)}] [SKIP] Exists: {fname}")
            continue
        print(f"[{idx+1}/{len(info.siblings)}] [DOWNLOAD] {fname} ({(f.size or 0)/(1024**2):.2f} MB)...")
        t0 = time.time()
        hf_hub_download(
            repo_id="osunlp/Multimodal-Mind2Web",
            repo_type="dataset",
            filename=fname,
            local_dir=TARGET_DIR
        )
        print(f"  -> Done in {time.time() - t0:.2f}s")

print("Multimodal-Mind2Web 100% complete!")
