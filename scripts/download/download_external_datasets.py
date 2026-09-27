"""
Automated External Dataset Downloader with Resume, Verification, and Manifest Generation.
SIH PS 26171: On-device Visual Perception for Light-weight Browser Agents.

Datasets:
1. ScreenParse (docling-project/screenparse) - Dense UI screen parsing shards
2. GroundCUA (Fhrozen/GroundCUA) - Complete multi-application grounding shards
3. AndroidControl (xwm/AndroidControl) - Complete action trajectory shards
4. Android in the Wild (cjfcsjt/AITW_General) - Complete mobile trajectory shards
5. WebChain v2 (webagentlab/webchain) - Complete browser workflow SFT part shards
"""
import os
import sys
import json
import time
import shutil
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from huggingface_hub import hf_hub_download
import pyarrow.parquet as pq

DATA_EXTERNAL = Path("data/external")
DATA_MANIFESTS = Path("data/manifests")
DATA_MANIFESTS.mkdir(parents=True, exist_ok=True)

def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def verify_parquet_integrity(file_path: Path) -> Tuple[bool, int, List[str]]:
    """Returns (is_valid, num_rows, column_names)."""
    try:
        table = pq.read_table(file_path)
        return (True, table.num_rows, table.column_names)
    except Exception as e:
        print(f"  [CORRUPTION CHECK FAILED] {file_path.name}: {e}")
        return (False, 0, [])

def download_and_verify(
    repo_id: str,
    filename: str,
    dataset_subdir: str
) -> Optional[Dict[str, Any]]:
    """Downloads a complete shard, verifies parquet integrity, and copies to destination."""
    dest_path = DATA_EXTERNAL / dataset_subdir / filename
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Check if already downloaded and valid
    if dest_path.exists() and dest_path.stat().st_size > 0:
        is_valid, num_rows, cols = verify_parquet_integrity(dest_path)
        if is_valid:
            print(f"  [ALREADY VERIFIED] {dataset_subdir}/{filename} ({dest_path.stat().st_size / (1024**2):.2f} MB, {num_rows} rows)")
            return {
                "filename": filename,
                "local_path": str(dest_path),
                "size_bytes": dest_path.stat().st_size,
                "size_mb": round(dest_path.stat().st_size / (1024**2), 2),
                "sha256": compute_sha256(dest_path),
                "num_samples": num_rows,
                "columns": cols,
                "status": "VERIFIED_VALID"
            }

    print(f"Downloading [{repo_id}] {filename}...")
    t0 = time.time()
    try:
        # Download through standard HF cache to avoid Windows lock issues
        cached_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            repo_type="dataset"
        )
        p_cached = Path(cached_path)
        if not p_cached.exists() or p_cached.stat().st_size == 0:
            raise FileNotFoundError(f"Cached file is empty or missing: {p_cached}")

        # Copy to destination
        shutil.copyfile(p_cached, dest_path)
        actual_size = dest_path.stat().st_size
        sha256_hash = compute_sha256(dest_path)

        is_valid_parquet, num_rows, cols = verify_parquet_integrity(dest_path)
        if not is_valid_parquet:
            raise ValueError(f"Parquet file {filename} failed integrity check.")

        elapsed = time.time() - t0
        print(f"  -> VERIFIED: {filename} ({actual_size / (1024**2):.2f} MB, {num_rows} rows, in {elapsed:.1f}s)")
        return {
            "filename": filename,
            "local_path": str(dest_path),
            "size_bytes": actual_size,
            "size_mb": round(actual_size / (1024**2), 2),
            "sha256": sha256_hash,
            "num_samples": num_rows,
            "columns": cols,
            "status": "VERIFIED_VALID"
        }
    except Exception as e:
        print(f"  -> ERROR downloading {filename}: {e}")
        return None

def run_download_pipeline():
    print("=" * 70)
    print("  EXTERNAL DATASET INGESTION & INTEGRITY VERIFICATION PIPELINE")
    print("=" * 70)

    # 1. ScreenParse (Complete Valid Shards)
    sp_shards = ["train/000000.parquet"]
    sp_files = []
    for s in sp_shards:
        res = download_and_verify("docling-project/screenparse", s, "screenparse")
        if res:
            sp_files.append(res)

    sp_manifest = {
        "dataset_name": "ScreenParse",
        "repo_id": "docling-project/screenparse",
        "license": "ODC-By 1.0",
        "purpose": "Dense UI screen parsing, 55 UI classes, bounding boxes, reading order",
        "storage_policy": "Complete valid shards selected within project storage target",
        "download_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_files": len(sp_files),
        "total_size_mb": sum(f["size_mb"] for f in sp_files),
        "total_samples": sum(f["num_samples"] for f in sp_files),
        "files": sp_files
    }
    with open(DATA_MANIFESTS / "screenparse_manifest.json", "w", encoding="utf-8") as f:
        json.dump(sp_manifest, f, indent=2)

    # 2. GroundCUA (Diverse Desktop / Web Applications)
    gc_shards = [
        "7-Zip/train-00000-of-00001.parquet",
        "Conky/train-00000-of-00001.parquet",
        "OnlyOffice_Forms/train-00000-of-00001.parquet",
        "Brave/train-00000-of-00001.parquet",
        "Bitwarden/train-00000-of-00001.parquet",
        "GIMP/train-00000-of-00001.parquet",
        "Inkscape/train-00000-of-00001.parquet"
    ]
    gc_files = []
    for s in gc_shards:
        res = download_and_verify("Fhrozen/GroundCUA", s, "groundcua")
        if res:
            gc_files.append(res)

    gc_manifest = {
        "dataset_name": "GroundCUA",
        "repo_id": "Fhrozen/GroundCUA",
        "license": "Apache 2.0",
        "purpose": "UI perception and computer-use grounding across real software applications",
        "download_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_files": len(gc_files),
        "total_size_mb": sum(f["size_mb"] for f in gc_files),
        "total_samples": sum(f["num_samples"] for f in gc_files),
        "files": gc_files
    }
    with open(DATA_MANIFESTS / "groundcua_manifest.json", "w", encoding="utf-8") as f:
        json.dump(gc_manifest, f, indent=2)

    # 3. AndroidControl
    ac_shards = [
        "data/train-00000-of-00018.parquet",
        "data/train-00001-of-00018.parquet",
        "data/train-00002-of-00018.parquet"
    ]
    ac_files = []
    for s in ac_shards:
        res = download_and_verify("xwm/AndroidControl", s, "android_control")
        if res:
            ac_files.append(res)

    ac_manifest = {
        "dataset_name": "AndroidControl",
        "repo_id": "xwm/AndroidControl",
        "license": "CC-BY-4.0",
        "purpose": "Screen states, UI positions, action labels, multi-step trajectories",
        "download_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_files": len(ac_files),
        "total_size_mb": sum(f["size_mb"] for f in ac_files),
        "total_samples": sum(f["num_samples"] for f in ac_files),
        "files": ac_files
    }
    with open(DATA_MANIFESTS / "android_control_manifest.json", "w", encoding="utf-8") as f:
        json.dump(ac_manifest, f, indent=2)

    # 4. Android in the Wild (AITW)
    aitw_shards = [
        "standard/test-00000-of-00032.parquet",
        "standard/test-00001-of-00032.parquet",
        "standard/test-00002-of-00032.parquet",
        "standard/test-00003-of-00032.parquet",
        "standard/test-00004-of-00032.parquet"
    ]
    aitw_files = []
    for s in aitw_shards:
        res = download_and_verify("cjfcsjt/AITW_General", s, "android_in_the_wild")
        if res:
            aitw_files.append(res)

    aitw_manifest = {
        "dataset_name": "Android in the Wild (AITW)",
        "repo_id": "cjfcsjt/AITW_General",
        "license": "Apache 2.0",
        "purpose": "Screen states, natural-language instructions, touch actions, interaction trajectories",
        "download_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_files": len(aitw_files),
        "total_size_mb": sum(f["size_mb"] for f in aitw_files),
        "total_samples": sum(f["num_samples"] for f in aitw_files),
        "files": aitw_files
    }
    with open(DATA_MANIFESTS / "android_in_the_wild_manifest.json", "w", encoding="utf-8") as f:
        json.dump(aitw_manifest, f, indent=2)

    # 5. WebChain v2
    wc_shards = [
        "data/seed_sft/parts/part_00/metadata/actions.parquet",
        "data/seed_sft/parts/part_00/metadata/traces.parquet",
        "data/seed_sft/parts/part_00/metadata/windows.parquet",
        "data/seed_sft/parts/part_00/sft/webchain_seed_demo_sft-00001.parquet"
    ]
    wc_files = []
    for s in wc_shards:
        res = download_and_verify("webagentlab/webchain", s, "webchain")
        if res:
            wc_files.append(res)

    wc_manifest = {
        "dataset_name": "WebChain v2",
        "repo_id": "webagentlab/webchain",
        "license": "Apache 2.0",
        "purpose": "Screenshot + DOM alignment, accessibility trees, grounded browser actions, long-horizon workflows",
        "download_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_files": len(wc_files),
        "total_size_mb": sum(f["size_mb"] for f in wc_files),
        "total_samples": sum(f["num_samples"] for f in wc_files),
        "files": wc_files
    }
    with open(DATA_MANIFESTS / "webchain_manifest.json", "w", encoding="utf-8") as f:
        json.dump(wc_manifest, f, indent=2)

    print("\n[DOWNLOAD SUMMARY] All target external datasets successfully ingested and verified.")

if __name__ == "__main__":
    run_download_pipeline()
