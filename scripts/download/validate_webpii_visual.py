"""
Sample validation for WebPII:
Extract image bytes from test-00000-of-00002.parquet, parse bounding boxes,
overlay bounding boxes on the image, and save visual verification images.
"""
import pyarrow.parquet as pq
import io
import json
from PIL import Image, ImageDraw
from pathlib import Path

OUT_VAL_DIR = Path("data/validation/webpii_visual_check")
OUT_VAL_DIR.mkdir(parents=True, exist_ok=True)

parquet_path = Path("data/raw/webpii/data/test-00000-of-00002.parquet")
table = pq.read_table(parquet_path)
df = table.slice(0, 5).to_pandas()

print(f"Generating visual validation overlays from {parquet_path}...")

for idx, row in df.iterrows():
    img_bytes = row["image"]["bytes"]
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    
    pii_elements = json.loads(row["pii_elements_json"])
    w, h = row["image_width"], row["image_height"]
    
    for el in pii_elements:
        # Bbox format in WebPII
        bbox = el.get("bbox_px") or el.get("bbox")
        if bbox:
            x1, y1, x2, y2 = bbox
            draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
            draw.text((x1, max(0, y1-12)), el.get("key", "PII"), fill="red")
            
    out_file = OUT_VAL_DIR / f"sample_overlay_{idx}_{row['company']}_{row['page_type']}.png"
    img.save(out_file)
    print(f"  [OK] Saved overlay: {out_file.name} (PII Count: {len(pii_elements)})")

print("WebPII visual check complete!")
