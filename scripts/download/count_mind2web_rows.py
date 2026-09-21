import pyarrow.parquet as pq
from pathlib import Path
import time

DATA_DIR = Path("data/raw/multimodal_mind2web/data")
shards = sorted(list(DATA_DIR.glob("*.parquet")))

print(f"Counting exact rows across all {len(shards)} Mind2Web shards...")
t0 = time.time()
total_rows = 0

for s in shards:
    meta = pq.read_metadata(s)
    total_rows += meta.num_rows

print("-" * 50)
print(f"TOTAL VERIFIED MIND2WEB ACTIONS: {total_rows:,} (verified across {len(shards)} shards in {time.time()-t0:.2f}s)")
print(f"TOTAL DISK FOOTPRINT: {sum([f.stat().st_size for f in shards]) / (1024**3):.2f} GB")
print("-" * 50)
