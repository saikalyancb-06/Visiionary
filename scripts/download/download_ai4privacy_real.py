"""
Download real validation subset from ai4privacy/pii-masking-openpii-1m (877 MB)
"""
from pathlib import Path
from huggingface_hub import hf_hub_download

AI4_DIR = Path("data/raw/ai4privacy")
AI4_DIR.mkdir(parents=True, exist_ok=True)

print("Downloading ai4privacy data/validation.jsonl (877.65 MB)...")
hf_hub_download(
    repo_id="ai4privacy/pii-masking-openpii-1m",
    repo_type="dataset",
    filename="data/validation.jsonl",
    local_dir=AI4_DIR
)
print("ai4privacy validation.jsonl downloaded successfully!")
