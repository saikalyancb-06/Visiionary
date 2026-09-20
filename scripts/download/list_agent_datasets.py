from huggingface_hub import HfApi
api = HfApi()

for r in ["osunlp/Multimodal-Mind2Web", "Voxel51/ScreenSpot", "Voxel51/ScreenSpot-v2", "Voxel51/ScreenSpot-Pro"]:
    info = api.dataset_info(r, files_metadata=True)
    print(f"=== {r} (Total Files: {len(info.siblings)}) ===")
    for f in info.siblings[:6]:
        sz_mb = (f.size or 0) / (1024**2)
        print(f"  {f.rfilename} ({sz_mb:.2f} MB)")
