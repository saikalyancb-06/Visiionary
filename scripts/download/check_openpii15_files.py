from huggingface_hub import HfApi
api = HfApi()

info = api.dataset_info("ai4privacy/pii-masking-openpii-1.5m", files_metadata=True)
print("=== ai4privacy/pii-masking-openpii-1.5m Files ===")
for f in info.siblings:
    sz = (f.size or 0) / (1024**3)
    print(f"  {f.rfilename:<35} : {sz:>5.2f} GB ({f.size} bytes)")
