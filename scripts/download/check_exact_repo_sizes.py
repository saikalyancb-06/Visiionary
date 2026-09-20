from huggingface_hub import HfApi

api = HfApi()

targets = [
    "ai4privacy/pii-masking-openpii-1.5m",
    "WebPII/webpii",
    "osunlp/Multimodal-Mind2Web",
    "Voxel51/ScreenSpot",
    "Voxel51/ScreenSpot-v2",
    "Voxel51/ScreenSpot-Pro"
]

print("=== REPOSITORY SIZES & FILE DETAILS ===")
grand_total = 0
for t in targets:
    try:
        info = api.dataset_info(t, files_metadata=True)
        total_b = sum([f.size for f in info.siblings if f.size is not None])
        grand_total += total_b
        print(f"Repo: {t:<36} | Files: {len(info.siblings):>4} | Total Size: {total_b / (1024**3):>6.2f} GB")
    except Exception as e:
        print(f"Repo: {t:<36} | ERROR: {e}")

print(f"\nGRAND TOTAL DATA SIZE ACROSS ALL 6 REPOSITORIES: {grand_total / (1024**3):.2f} GB")
