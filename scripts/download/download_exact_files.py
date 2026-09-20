from pathlib import Path
from huggingface_hub import hf_hub_download

print("Downloading verified exact data files from HuggingFace...")

# 1. ai4privacy 200k exact data file
print("Downloading ai4privacy-200k: english_pii_43k.jsonl...")
hf_hub_download(
    repo_id="ai4privacy/pii-masking-200k",
    repo_type="dataset",
    filename="english_pii_43k.jsonl",
    local_dir="data/raw/ai4privacy_200k"
)
print("  -> english_pii_43k.jsonl downloaded.")

# 2. ai4privacy 300k exact data file
print("Downloading ai4privacy-300k: data/train/1english_openpii_30k.jsonl...")
hf_hub_download(
    repo_id="ai4privacy/pii-masking-300k",
    repo_type="dataset",
    filename="data/train/1english_openpii_30k.jsonl",
    local_dir="data/raw/ai4privacy_300k"
)
print("  -> 1english_openpii_30k.jsonl downloaded.")

# 3. ScreenSpot sample images
print("Downloading ScreenSpot real test samples...")
hf_hub_download(
    repo_id="Voxel51/ScreenSpot",
    repo_type="dataset",
    filename="data/mobile_043c3a5e-c12c-4991-bb7f-676c617b2f9b.png",
    local_dir="data/raw/screenspot"
)
print("  -> ScreenSpot sample downloaded.")

print("All exact data files downloaded successfully!")
