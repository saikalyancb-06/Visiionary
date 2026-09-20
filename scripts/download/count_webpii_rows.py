import pyarrow.parquet as pq
from pathlib import Path
import time

DATA_DIR = Path("data/raw/webpii/data")
shards = sorted(list(DATA_DIR.glob("*.parquet")))

print(f"Counting total exact rows across all {len(shards)} WebPII shards...")
t0 = time.time()
total_rows = 0

for s in shards:
    meta = pq.read_metadata(s)
    rows = meta.num_rows
    total_rows += rows
    print(f"  {s.name:<32} : {rows:>6,} rows ({s.stat().st_size / (1024**2):>6.2f} MB)")

print("-" * 50)
print(f"TOTAL VERIFIED WEBPII ROWS: {total_rows:,} (verified in {time.time() - t0:.2f}s)")
