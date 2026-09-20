from huggingface_hub import HfApi

api = HfApi()

info = api.dataset_info("WebPII/webpii", files_metadata=True)
print("=== WebPII Complete File Listing ===")
total = 0
for f in info.siblings:
    total += (f.size or 0)
    print(f"  {f.rfilename:<38} : {(f.size or 0) / (1024**2):>7.2f} MB")
print(f"Total size: {total / (1024**3):.2f} GB")
