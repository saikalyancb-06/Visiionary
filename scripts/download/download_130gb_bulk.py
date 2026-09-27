"""
Multi-threaded High-Speed Streaming Bulk Downloader.
Downloads files with live progress, flush to disk, and Drive D: safety limit.
"""
import os
import sys
import time
import shutil
from pathlib import Path
import requests

TARGET_DIR = Path("data/external")
MIN_FREE_SPACE_GB = 30.0

def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def get_d_free_gb() -> float:
    total, used, free = shutil.disk_usage("D:\\")
    return free / (1024 ** 3)

def download_file(url: str, dest_path: Path) -> bool:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(dest_path.suffix + ".part")

    if dest_path.exists() and dest_path.stat().st_size > 1024:
        log(f"[ALREADY EXISTS] {dest_path.name} ({dest_path.stat().st_size / (1024**2):.1f} MB)")
        return True

    free_gb = get_d_free_gb()
    if free_gb < MIN_FREE_SPACE_GB:
        log(f"[SAFETY LIMIT] Drive D: free space is {free_gb:.2f} GB (Floor: {MIN_FREE_SPACE_GB} GB). Stopping.")
        return False

    headers = {"User-Agent": "Mozilla/5.0"}
    existing_bytes = temp_path.stat().st_size if temp_path.exists() else 0
    if existing_bytes > 0:
        headers["Range"] = f"bytes={existing_bytes}-"

    log(f"Downloading: {dest_path.name} (resuming from {existing_bytes/(1024**2):.1f} MB)...")
    t0 = time.time()
    try:
        with requests.get(url, headers=headers, stream=True, timeout=45) as r:
            if r.status_code not in (200, 206):
                log(f"  [HTTP ERROR {r.status_code}] {dest_path.name}")
                return False

            total_size = int(r.headers.get("content-length", 0)) + existing_bytes
            mode = "ab" if existing_bytes > 0 and r.status_code == 206 else "wb"
            if mode == "wb":
                existing_bytes = 0

            downloaded = existing_bytes
            last_report = time.time()
            with open(temp_path, mode) as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024 * 2): # 2MB chunks
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        downloaded += len(chunk)
                        now = time.time()
                        if now - last_report > 15: # report every 15s
                            elapsed = now - t0
                            speed = (downloaded - existing_bytes) / (1024**2) / max(0.1, elapsed)
                            pct = (downloaded / total_size * 100) if total_size > 0 else 0
                            log(f"  ... {dest_path.name}: {downloaded/(1024**2):.1f}/{total_size/(1024**2):.1f} MB ({pct:.1f}%) @ {speed:.2f} MB/s | D: Free: {get_d_free_gb():.1f} GB")
                            last_report = now
                            if get_d_free_gb() < MIN_FREE_SPACE_GB:
                                log("[SAFETY HALT] Free space boundary hit during download.")
                                return False

        temp_path.rename(dest_path)
        elapsed = time.time() - t0
        mb = dest_path.stat().st_size / (1024 ** 2)
        log(f"  -> [SUCCESS] {dest_path.name} ({mb:.1f} MB in {elapsed:.1f}s) | D: Free: {get_d_free_gb():.1f} GB")
        return True
    except Exception as e:
        log(f"  -> [RETRYABLE ERROR] {dest_path.name}: {e}")
        return False

def main():
    log("=" * 70)
    log("  AUTONOMOUS BULK DATASET STREAMER")
    log(f"  Initial D: Free Space: {get_d_free_gb():.2f} GB | Safety Floor: {MIN_FREE_SPACE_GB} GB")
    log("=" * 70)

    queue = []

    # 1. ScreenParse v2 Shards (~70 GB)
    for i in range(1, 125):
        shard = f"{i:06d}.parquet"
        u = f"https://huggingface.co/datasets/docling-project/screenparse/resolve/main/train/{shard}"
        p = TARGET_DIR / "screenparse" / "train" / shard
        queue.append((u, p))

    # 2. AndroidControl Shards (~6 GB)
    for i in range(3, 18):
        shard = f"train-{i:05d}-of-00018.parquet"
        u = f"https://huggingface.co/datasets/xwm/AndroidControl/resolve/main/data/{shard}"
        p = TARGET_DIR / "android_control" / "data" / shard
        queue.append((u, p))

    # 3. Android in the Wild (AITW) (~2.5 GB)
    for i in range(5, 32):
        shard = f"test-{i:05d}-of-00032.parquet"
        u = f"https://huggingface.co/datasets/cjfcsjt/AITW_General/resolve/main/standard/{shard}"
        p = TARGET_DIR / "android_in_the_wild" / "standard" / shard
        queue.append((u, p))

    # 4. WebChain v2 Shards (~25 GB)
    for part_idx in range(1, 25):
        part_name = f"part_{part_idx:02d}"
        shard = "webchain_seed_demo_sft-00001.parquet"
        u = f"https://huggingface.co/datasets/webagentlab/webchain/resolve/main/data/seed_sft/parts/{part_name}/sft/{shard}"
        p = TARGET_DIR / "webchain" / part_name / shard
        queue.append((u, p))

    for u, p in queue:
        if get_d_free_gb() < MIN_FREE_SPACE_GB:
            log(f"[FINISHED] Safety limit of {MIN_FREE_SPACE_GB} GB reached. Download phase complete.")
            break
        download_file(u, p)
        time.sleep(0.1)

if __name__ == "__main__":
    main()
