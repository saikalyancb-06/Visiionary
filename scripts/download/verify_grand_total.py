from pathlib import Path

datasets = [
    ("OpenPII 1.5M (Full)", "data/raw/openpii_1.5m/data"),
    ("WebPII (Full 14 Shards)", "data/raw/webpii/data"),
    ("Multimodal-Mind2Web (Full 47 Shards)", "data/raw/multimodal_mind2web/data"),
    ("ScreenSpot Family", "data/raw/screenspot")
]

print("="*60)
print("     COMPREHENSIVE DATASET INVENTORY ON DISK     ")
print("="*60)

grand_total = 0

for label, p_str in datasets:
    p = Path(p_str)
    if p.exists():
        files = list(p.rglob("*"))
        data_files = [f for f in files if f.is_file() and not f.name.endswith(".lock")]
        total_sz = sum([f.stat().st_size for f in data_files])
        grand_total += total_sz
        print(f"[VERIFIED] {label:<36} : {total_sz / (1024**3):>6.2f} GB ({len(data_files)} files)")
    else:
        print(f"[MISSING]  {label:<36}")

print("="*60)
print(f"GRAND TOTAL ACTUAL DATA ON DISK: {grand_total / (1024**3):.2f} GB ({grand_total:,} bytes)")
print("="*60)
