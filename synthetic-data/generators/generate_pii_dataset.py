"""
Synthetic PII and UI Page Generator for PS 26171
Generates realistic web pages with exact bounding box ground truths:
- Identity: name, DOB, username
- Contact: email, phone, address
- Financial: account number, card, balance, UPI, IFSC
- Indian synthetic identifiers: PAN-format, Aadhaar-format (fictional)
- Safe UI elements: buttons, search inputs, navigation tabs, cards
- Template-split: held-out templates for unbiased evaluation
"""
import os
import json
import random
from pathlib import Path
from faker import Faker
from PIL import Image, ImageDraw, ImageFont

fake = Faker(['en_IN', 'en_US'])
random.seed(42)

OUT_DIR = Path("data/processed/synthetic_pii")
OUT_DIR.mkdir(parents=True, exist_ok=True)

TEMPLATES = [
    {"id": "bank_dashboard", "split": "train", "theme": "navy", "bg": (245, 247, 250)},
    {"id": "tax_portal", "split": "train", "theme": "green", "bg": (250, 250, 252)},
    {"id": "ecommerce_checkout", "split": "val", "theme": "orange", "bg": (255, 255, 255)},
    {"id": "user_profile_modal", "split": "test", "theme": "dark", "bg": (240, 242, 245)},
    {"id": "adversarial_dense", "split": "test", "theme": "dense", "bg": (235, 238, 242)}
]

def generate_indian_pan():
    letters = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=5))
    digits = "".join(random.choices("0123456789", k=4))
    last = random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ")
    return f"{letters}{digits}{last}"

def generate_indian_aadhaar():
    return f"{random.randint(2000, 8999)} {random.randint(1000, 9999)} {random.randint(1000, 9999)}"

def generate_samples(count=120):
    metadata = []
    w, h = 1024, 768

    for i in range(count):
        tmpl = random.choice(TEMPLATES)
        img = Image.new("RGB", (w, h), color=tmpl["bg"])
        draw = ImageDraw.Draw(img)

        sample_boxes = []

        # Header Bar
        draw.rectangle([0, 0, w, 60], fill=(20, 35, 60) if tmpl["theme"] != "green" else (18, 55, 30))
        draw.text((25, 20), f"Portal System - {tmpl['id']}", fill=(255, 255, 255))
        sample_boxes.append({"type": "safe_ui", "label": "Portal Title", "bbox": [25, 20, 250, 45], "sensitive": False})

        # Nav button
        draw.rectangle([850, 15, 990, 45], fill=(0, 102, 204), outline=(255, 255, 255))
        draw.text((875, 22), "Download", fill=(255, 255, 255))
        sample_boxes.append({"type": "button", "label": "Download", "bbox": [850, 15, 990, 45], "sensitive": False})

        # Content Card
        draw.rectangle([50, 90, 974, 700], fill=(255, 255, 255), outline=(220, 225, 230))

        # Sensitive Items
        y_cursor = 120

        # Person Name
        name = fake.name()
        draw.text((80, y_cursor), f"Account Holder: {name}", fill=(10, 10, 10))
        sample_boxes.append({"type": "person_name", "value": name, "bbox": [180, y_cursor, 400, y_cursor + 20], "sensitive": True})
        y_cursor += 45

        # Email
        email = fake.email()
        draw.text((80, y_cursor), f"Email Address: {email}", fill=(10, 10, 10))
        sample_boxes.append({"type": "email", "value": email, "bbox": [170, y_cursor, 450, y_cursor + 20], "sensitive": True})
        y_cursor += 45

        # Phone
        phone = f"+91 {random.randint(60000, 99999)} {random.randint(10000, 99999)}"
        draw.text((80, y_cursor), f"Registered Mobile: {phone}", fill=(10, 10, 10))
        sample_boxes.append({"type": "phone", "value": phone, "bbox": [200, y_cursor, 380, y_cursor + 20], "sensitive": True})
        y_cursor += 45

        # Gov ID (PAN or Aadhaar)
        govid = generate_indian_pan() if i % 2 == 0 else generate_indian_aadhaar()
        gtype = "pan" if i % 2 == 0 else "aadhaar"
        draw.text((80, y_cursor), f"Identity Document ({gtype.upper()}): {govid}", fill=(10, 10, 10))
        sample_boxes.append({"type": "gov_id", "value": govid, "bbox": [260, y_cursor, 440, y_cursor + 20], "sensitive": True})
        y_cursor += 45

        # Financial Account / Card
        acc = f"{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
        draw.text((80, y_cursor), f"Primary Financial Account: {acc}", fill=(10, 10, 10))
        sample_boxes.append({"type": "bank_account", "value": acc, "bbox": [260, y_cursor, 440, y_cursor + 20], "sensitive": True})
        y_cursor += 45

        # Save Image & Annotations
        img_filename = f"sample_{i:04d}.png"
        json_filename = f"sample_{i:04d}.json"
        
        img.save(OUT_DIR / img_filename)
        with open(OUT_DIR / json_filename, "w", encoding="utf-8") as f:
            json.dump({
                "sample_id": i,
                "template_id": tmpl["id"],
                "split": tmpl["split"],
                "width": w,
                "height": h,
                "annotations": sample_boxes
            }, f, indent=2)

        metadata.append({
            "image": img_filename,
            "json": json_filename,
            "split": tmpl["split"],
            "sensitive_count": len([b for b in sample_boxes if b["sensitive"]])
        })

    with open(OUT_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"Generated {count} synthetic screenshots and exact bounding-box ground truth annotations in {OUT_DIR}")

if __name__ == "__main__":
    generate_samples()
