import pyarrow.parquet as pq
from pathlib import Path

p = Path("data/raw/multimodal_mind2web/data/test_domain-00000-of-00011-26c55c12cbbcdc8e.parquet")
if p.exists():
    print(f"Reading Mind2Web shard: {p} ({p.stat().st_size / (1024*1024):.2f} MB)...")
    table = pq.read_table(p)
    print(f"Schema columns: {table.column_names}")
    print(f"Total rows: {table.num_rows}")
    df = table.slice(0, 3).to_pandas()
    for col in df.columns:
        print(f"  Col: {col:<20} | Type: {type(df[col].iloc[0]).__name__}")
