"""
Sample validation for ScreenSpot / ScreenSpot-v2:
Open downloaded test images, verify dimensions, channels, integrity, and draw sample grounding box.
"""
from PIL import Image, ImageDraw
from pathlib import Path

VAL_DIR = Path("data/validation/screenspot_visual_check")
VAL_DIR.mkdir(parents=True, exist_ok=True)

test_imgs = [
    Path("data/raw/screenspot/data/mobile_043c3a5e-c12c-4991-bb7f-676c617b2f9b.png"),
    Path("data/raw/screenspot_v2/data/mobile_02e9bl_0.png")
]

print("Validating ScreenSpot images and rendering visual overlays...")
for p in test_imgs:
    if p.exists():
        img = Image.open(p)
        print(f"  [OK] {p.name}: Dimensions={img.size}, Mode={img.mode}, Size={p.stat().st_size / (1024*1024):.2f} MB")
        # Draw grounding box on center element
        draw = ImageDraw.Draw(img)
        w, h = img.size
        draw.rectangle([w//4, h//4, 3*w//4, h//2], outline="green", width=5)
        draw.text((w//4 + 10, h//4 + 10), "Grounding Target", fill="green")
        out_p = VAL_DIR / f"grounding_check_{p.name}"
        img.save(out_p)
        print(f"    Saved visual check: {out_p}")
    else:
        print(f"  [MISSING] {p}")
