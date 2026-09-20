from huggingface_hub import HfApi
api = HfApi()

datasets = [
    "WebPII/webpii",
    "ai4privacy/pii-masking-openpii-1m",
    "osunlp/Multimodal-Mind2Web",
    "Voxel51/ScreenSpot"
]

for d in datasets:
    try:
        info = api.dataset_info(d, files_metadata=True)
        total_bytes = sum([f.size for f in info.siblings if f.size is not None])
        print(f"Dataset: {d} | Files: {len(info.siblings)} | Total Size: {total_bytes / (1024**3):.2f} GB | Gated/Private: {info.private}")
    except Exception as e:
        print(f"Error checking {d}: {e}")
