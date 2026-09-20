import pyarrow.parquet as pq
import pandas as pd
from pathlib import Path
import json

p_path = Path("data/raw/webpii/data/test-00000-of-00002.parquet")
if p_path.exists():
    print(f"Reading {p_path} ({p_path.stat().st_size / (1024*1024):.2f} MB)...")
    table = pq.read_table(p_path)
    print(f"Schema columns: {table.column_names}")
    print(f"Total rows in this shard: {table.num_rows:,}")
    df = table.slice(0, 5).to_pandas()
    print("\nSample row keys & types:")
    for col in df.columns:
        val = df[col].iloc[0]
        v_type = type(val).__name__
        val_str = str(val)[:50]
        print(f"  {col} ({v_type}): {val_str}")
