"""
Download and verify ScreenSpot and ScreenSpot-v2 evaluation samples and metadata
"""
from pathlib import Path
from huggingface_hub import hf_hub_download

# ScreenSpot
ss_dir = Path("data/raw/screenspot")
ss_dir.mkdir(parents=True, exist_ok=True)
print("Downloading ScreenSpot evaluation image...")
hf_hub_download(
    repo_id="Voxel51/ScreenSpot",
    repo_type="dataset",
    filename="data/mobile_04545977-3f36-4a33-a787-72ec8a9dd4f2.png",
    local_dir=ss_dir
)
print("  -> ScreenSpot sample downloaded.")

# ScreenSpot-v2
ss2_dir = Path("data/raw/screenspot_v2")
ss2_dir.mkdir(parents=True, exist_ok=True)
print("Downloading ScreenSpot-v2 evaluation image...")
hf_hub_download(
    repo_id="Voxel51/ScreenSpot-v2",
    repo_type="dataset",
    filename="data/mobile_02e9bl_0.png",
    local_dir=ss2_dir
)
print("  -> ScreenSpot-v2 sample downloaded.")

# ScreenSpot-Pro
sspro_dir = Path("data/raw/screenspot_pro")
sspro_dir.mkdir(parents=True, exist_ok=True)
print("Downloading ScreenSpot-Pro README...")
hf_hub_download(
    repo_id="Voxel51/ScreenSpot-Pro",
    repo_type="dataset",
    filename="README.md",
    local_dir=sspro_dir
)
print("  -> ScreenSpot-Pro README downloaded.")
