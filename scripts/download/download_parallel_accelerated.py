"""
High-Speed Parallel Multi-Worker Streaming Bulk Downloader.
Downloads multiple large shards concurrently (4 workers) to maximize bandwidth.
"""
import os
import sys
import time
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

TARGET_DIR = Path("data/external")
MIN_FREE_SPACE_GB = 30.0
MAX_WORKERS = 4

def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def get_d_free_gb() -> float:
    total, used, free = shutil.disk_usage("D:\\")
    return free / (1024 ** 3)

def download_file(item: tuple) -> bool:
    url, dest_path = item
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(dest_path.suffix + ".part")

    if dest_path.exists() and dest_path.stat().st_size > 1024:
        log(f"[EXISTS] {dest_path.name} ({dest_path.stat().st_size / (1024**2):.1f} MB)")
        return True

    if get_d_free_gb() < MIN_FREE_SPACE_GB:
        log(f"[SAFETY LIMIT] D: free space ({get_d_free_gb():.2f} GB) reached floor ({MIN_FREE_SPACE_GB} GB). Skipping {dest_path.name}.")
        return False

    headers = {"User-Agent": "Mozilla/5.0"}
    existing_bytes = temp_path.stat().st_size if temp_path.exists() else 0
    if existing_bytes > 0:
        headers["Range"] = f"bytes={existing_bytes}-"

    log(f"[START] {dest_path.name} (resuming from {existing_bytes/(1024**2):.1f} MB)...")
    t0 = time.time()
    try:
        with requests.get(url, headers=headers, stream=True, timeout=60) as r:
            if r.status_code not in (200, 206):
                log(f"[HTTP {r.status_code}] {dest_path.name}")
                return False

            mode = "ab" if existing_bytes > 0 and r.status_code == 206 else "wb"
            with open(temp_path, mode) as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024 * 2): # 2MB
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        if get_d_free_gb() < MIN_FREE_SPACE_GB:
                            log(f"[SAFETY HALT] Disk limit reached during {dest_path.name}.")
                            return False

        temp_path.rename(dest_path)
        elapsed = time.time() - t0
        mb = dest_path.stat().st_size / (1024 ** 2)
        log(f"[DONE] {dest_path.name} ({mb:.1f} MB in {elapsed:.1f}s @ {mb/max(0.1, elapsed):.2f} MB/s) | D: Free: {get_d_free_gb():.1f} GB")
        return True
    except Exception as e:
        log(f"[RETRY ERROR] {dest_path.name}: {e}")
        return False

def main():
    log("=" * 70)
    log(f"  PARALLEL MULTI-THREADED DATASET ACCELERATOR (CONCURRENCY: {MAX_WORKERS})")
    log(f"  Current D: Free Space: {get_d_free_gb():.2f} GB | Safety Floor: {MIN_FREE_SPACE_GB} GB")
    log("=" * 70)

    # Shards to bring new data from 96.36 GB to ~125 GB (need ~28 GB = ~50 shards)
    queue = []
    for i in range(125, 175):
        shard = f"{i:06d}.parquet"
        u = f"https://huggingface.co/datasets/docling-project/screenparse/resolve/main/train/{shard}"
        p = TARGET_DIR / "screenparse" / "train" / shard
        queue.append((u, p))

    completed = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(download_file, item): item for item in queue}
        for future in as_completed(futures):
            item = futures[future]
            try:
                res = future.result()
                if res:
                    completed += 1
            except Exception as e:
                log(f"Task failed: {e}")

            if get_d_free_gb() < MIN_FREE_SPACE_GB:
                log(f"[STORAGE BOUNDARY] Drive D: reached {MIN_FREE_SPACE_GB} GB limit. Stopping parallel queue.")
                executor.shutdown(wait=False, cancel_futures=True)
                break

    log("=" * 70)
    log(f"  PARALLEL DOWNLOAD COMPLETE: {completed} additional shards ingested.")
    log(f"  Final D: Free Space: {get_d_free_gb():.2f} GB")
    log("=" * 70)

if __name__ == "__main__":
    main()
