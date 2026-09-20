from huggingface_hub import HfApi
api = HfApi()

for r in ["Voxel51/ScreenSpot", "ai4privacy/pii-masking-200k", "ai4privacy/pii-masking-300k"]:
    info = api.dataset_info(r)
    print(f"=== {r} ===")
    for f in info.siblings[:6]:
        print("  ", f.rfilename)
