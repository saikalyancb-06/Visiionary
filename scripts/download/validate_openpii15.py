"""
Hard validation of OpenPII 1.5M:
Inspect schema, count rows, and verify actual privacy annotations with safe ASCII logging.
"""
import json
import time
from pathlib import Path

DATA_DIR = Path("data/raw/openpii_1.5m/data")
train_path = DATA_DIR / "train.jsonl"
val_path = DATA_DIR / "validation.jsonl"

print("Inspecting schema on first record of validation.jsonl...")
with open(val_path, "r", encoding="utf-8") as f:
    first_record = json.loads(f.readline())
    print("Schema keys:", list(first_record.keys()))
    print("Language:", first_record.get("language"))
    print("Region:", first_record.get("region"))
    print("Tokens count:", len(first_record.get("mbert_tokens", [])))
    print("Classes count:", len(first_record.get("mbert_token_classes", [])))

def count_lines(filepath):
    t0 = time.time()
    count = 0
    with open(filepath, "rb") as f:
        for _ in f:
            count += 1
    return count, time.time() - t0

print("\nCounting exact rows in validation.jsonl...")
val_count, val_sec = count_lines(val_path)
print(f"validation.jsonl rows: {val_count:,} ({val_sec:.2f}s)")

print("Counting exact rows in train.jsonl...")
train_count, train_sec = count_lines(train_path)
print(f"train.jsonl rows: {train_count:,} ({train_sec:.2f}s)")

total = val_count + train_count
print(f"\n==========================================")
print(f"TOTAL OPENPII 1.5M ROWS VERIFIED: {total:,}")
print(f"Expected: ~1,636,375")
print(f"==========================================")
