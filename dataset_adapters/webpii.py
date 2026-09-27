"""
WebPII Dataset Adapter for Unified Schema.
Extracts web screenshots, dimensions, and PII bounding box annotations.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Optional, Iterator, Dict, Any, List
import pyarrow.parquet as pq
from PIL import Image

from dataset_adapters.base import (
    BaseDatasetAdapter,
    UnifiedSample,
    PIIAnnotation,
    UIElement,
    PII_TAXONOMY
)

# Map WebPII raw category names to Unified PII Taxonomy
WEBPII_LABEL_MAP: Dict[str, str] = {
    "person": "PERSON",
    "name": "PERSON",
    "email": "EMAIL",
    "phone": "PHONE",
    "telephone": "PHONE",
    "mobile": "PHONE",
    "address": "ADDRESS",
    "location": "ADDRESS",
    "street": "ADDRESS",
    "city": "ADDRESS",
    "zipcode": "ADDRESS",
    "pincode": "ADDRESS",
    "password": "PASSWORD",
    "passcode": "PASSWORD",
    "pin": "PASSWORD",
    "otp": "OTP",
    "credit_card": "CREDIT_CARD",
    "card_number": "CREDIT_CARD",
    "debit_card": "DEBIT_CARD",
    "bank_account": "BANK_ACCOUNT",
    "account_number": "BANK_ACCOUNT",
    "ifsc": "IFSC",
    "upi": "UPI_ID",
    "upi_id": "UPI_ID",
    "aadhaar": "AADHAAR",
    "pan": "PAN",
    "passport": "PASSPORT",
    "driving_license": "DRIVERS_LICENSE",
    "dob": "DATE_OF_BIRTH",
    "birth_date": "DATE_OF_BIRTH",
    "financial": "FINANCIAL_VALUE",
    "salary": "FINANCIAL_VALUE",
    "balance": "FINANCIAL_VALUE",
    "api_key": "API_KEY",
    "secret": "SECRET",
    "face": "FACE",
    "qr": "QR_CODE",
    "username": "USERNAME"
}

class WebPIIAdapter(BaseDatasetAdapter):
    def __init__(self, source_dir: Path = Path("data/raw/webpii")):
        super().__init__("WebPII", source_dir)
        self.data_dir = self.source_dir / "data" if (self.source_dir / "data").exists() else self.source_dir

    def get_parquet_files(self) -> List[Path]:
        if not self.data_dir.exists():
            return []
        return sorted(list(self.data_dir.glob("*.parquet")))

    def count_samples(self) -> int:
        total = 0
        for pfile in self.get_parquet_files():
            try:
                table = pq.read_table(pfile, columns=["source_id"])
                total += table.num_rows
            except Exception:
                pass
        return total

    def iter_samples(self, limit: Optional[int] = None) -> Iterator[UnifiedSample]:
        count = 0
        for pfile in self.get_parquet_files():
            try:
                table = pq.read_table(pfile)
                df = table.to_pandas()
                for idx, row in df.iterrows():
                    sample_id = f"webpii_{row.get('source_id', f'{pfile.stem}_{idx}')}"
                    w = int(row.get("image_width", 1280)) or 1280
                    h = int(row.get("image_height", 720)) or 720
                    img_bytes = None
                    if isinstance(row.get("image"), dict) and "bytes" in row["image"]:
                        img_bytes = row["image"]["bytes"]

                    pii_annotations: List[PIIAnnotation] = []
                    raw_pii_json = row.get("pii_elements_json", "[]")
                    try:
                        elements = json.loads(raw_pii_json) if isinstance(raw_pii_json, str) else raw_pii_json
                        for el in elements:
                            if not isinstance(el, dict):
                                continue
                            raw_k = str(el.get("key", el.get("type", el.get("category", "")))).upper().strip()
                            val = str(el.get("value", ""))

                            # Detailed key classification
                            if "PASSWORD" in raw_k:
                                pii_type = "PASSWORD"
                            elif "CARD" in raw_k or "SECURITY_CODE" in raw_k:
                                pii_type = "CREDIT_CARD"
                            elif "EMAIL" in raw_k:
                                pii_type = "EMAIL"
                            elif "PHONE" in raw_k:
                                pii_type = "PHONE"
                            elif any(k in raw_k for k in ["CITY", "STREET", "POSTCODE", "STATE", "COUNTRY", "LOCATION", "ADDRESS"]):
                                pii_type = "ADDRESS"
                            elif any(k in raw_k for k in ["NAME", "FIRSTNAME", "LASTNAME", "FULLNAME"]):
                                pii_type = "PERSON"
                            elif "USERNAME" in raw_k:
                                pii_type = "USERNAME"
                            elif "PROMO" in raw_k or "SECRET" in raw_k:
                                pii_type = "SECRET"
                            elif "MESSAGE" in raw_k:
                                pii_type = "PRIVATE_MESSAGE"
                            else:
                                pii_type = WEBPII_LABEL_MAP.get(raw_k.lower(), "OTHER_IDENTIFIER")
                            
                            # Extract bbox: check bbox_x, bbox_y, bbox_width, bbox_height first
                            if "bbox_x" in el and "bbox_y" in el and "bbox_width" in el and "bbox_height" in el:
                                bx = float(el["bbox_x"])
                                by = float(el["bbox_y"])
                                bw = float(el["bbox_width"])
                                bh = float(el["bbox_height"])
                                nx1 = max(0.0, min(1.0, bx / w))
                                ny1 = max(0.0, min(1.0, by / h))
                                nx2 = max(0.0, min(1.0, (bx + bw) / w))
                                ny2 = max(0.0, min(1.0, (by + bh) / h))
                            else:
                                raw_bbox = el.get("bbox", el.get("box", [0, 0, w, h]))
                                if len(raw_bbox) == 4:
                                    x1, y1, x2, y2 = [float(v) for v in raw_bbox]
                                    if max(x1, x2, y1, y2) > 1.0:
                                        nx1 = max(0.0, min(1.0, x1 / w))
                                        ny1 = max(0.0, min(1.0, y1 / h))
                                        nx2 = max(0.0, min(1.0, x2 / w))
                                        ny2 = max(0.0, min(1.0, y2 / h))
                                    else:
                                        nx1, ny1, nx2, ny2 = x1, y1, x2, y2
                                else:
                                    continue
                            
                            pii_annotations.append(PIIAnnotation(
                                bbox=[min(nx1, nx2), min(ny1, ny2), max(nx1, nx2), max(ny1, ny2)],
                                type=pii_type,
                                confidence=float(el.get("confidence", 1.0)),
                                text="[REDACTED]"
                            ))
                    except Exception:
                        pass

                    sample = UnifiedSample(
                        sample_id=sample_id,
                        source_dataset="WebPII",
                        image_bytes=img_bytes,
                        width=w,
                        height=h,
                        pii=pii_annotations
                    )
                    valid, _ = self.validate_sample(sample)
                    if valid:
                        yield sample
                        count += 1
                        if limit and count >= limit:
                            return
            except Exception as e:
                print(f"[WebPIIAdapter] Error reading {pfile.name}: {e}")
