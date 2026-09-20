"""
Download remaining WebPII parquet shards to complete the dataset (6.31 GB total)
"""
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download
import time

TARGET_DIR = Path("data/raw/webpii")
TARGET_DIR.mkdir(parents=True, exist_ok=True)

api = HfApi()
info = api.dataset_info("WebPII/webpii", files_metadata=True)

for f in info.siblings:
    fname = f.rfilename
    if fname.endswith(".parquet") or fname.endswith(".zip") or fname.endswith(".json") or fname.endswith(".md"):
        local_f = TARGET_DIR / fname
        if local_f.exists() and local_f.stat().st_size == f.size:
            print(f"[SKIP] Already complete: {fname} ({f.size / (1024**2):.2f} MB)")
            continue
        print(f"[DOWNLOAD] {fname} ({f.size / (1024**2):.2f} MB)...")
        t0 = time.time()
        hf_hub_download(
            repo_id="WebPII/webpii",
            repo_type="dataset",
            filename=fname,
            local_dir=TARGET_DIR
        )
        print(f"  -> Done in {time.time() - t0:.2f}s")

print("All WebPII files downloaded successfully!")
