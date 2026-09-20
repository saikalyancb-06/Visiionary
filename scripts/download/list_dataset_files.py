from huggingface_hub import HfApi
api = HfApi()

info_webpii = api.dataset_info("WebPII/webpii", files_metadata=True)
print("=== WebPII files ===")
for f in info_webpii.siblings:
    size_mb = (f.size or 0) / (1024**2)
    print(f"  {f.rfilename} ({size_mb:.2f} MB)")

info_ai4 = api.dataset_info("ai4privacy/pii-masking-openpii-1m", files_metadata=True)
print("=== ai4privacy files ===")
for f in info_ai4.siblings:
    size_mb = (f.size or 0) / (1024**2)
    print(f"  {f.rfilename} ({size_mb:.2f} MB)")
