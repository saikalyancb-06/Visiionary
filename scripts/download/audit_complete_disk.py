from pathlib import Path

datasets = [
    ("OpenPII 1.5M (Full)", "data/raw/openpii_1.5m/data"),
    ("WebPII (Full 14 Shards)", "data/raw/webpii/data"),
    ("Multimodal-Mind2Web (Full 47 Shards)", "data/raw/multimodal_mind2web/data"),
    ("ScreenSpot (Full 616 Files)", "data/raw/screenspot"),
    ("ScreenSpot-v2 (Full 1278 Files)", "data/raw/screenspot_v2"),
    ("ScreenSpot-Pro (Full 1587 Files)", "data/raw/screenspot_pro")
]

print("="*65)
print("       EXHAUSTIVE DISK INVENTORY AUDIT (PS 26171)        ")
print("="*65)

grand_total = 0
total_files_count = 0

for label, p_str in datasets:
    p = Path(p_str)
    if p.exists():
        files = list(p.rglob("*"))
        data_files = [f for f in files if f.is_file() and not f.name.endswith(".lock")]
        total_sz = sum([f.stat().st_size for f in data_files])
        grand_total += total_sz
        total_files_count += len(data_files)
        print(f"[COMPLETE] {label:<38} : {total_sz / (1024**3):>6.2f} GB ({len(data_files):>4} files)")
    else:
        print(f"[MISSING]  {label:<38}")

print("="*65)
print(f"GRAND TOTAL DATA ON DISK: {grand_total / (1024**3):.2f} GB ({grand_total:,} bytes)")
print(f"TOTAL DATASET FILES STORED: {total_files_count:,}")
print("="*65)
