"""
OpenPII & AI4Privacy Dataset Adapter for Unified Schema.
Extracts multilingual text PII tokens and entities.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Iterator, Dict, Any, List
import pyarrow.parquet as pq

from dataset_adapters.base import (
    BaseDatasetAdapter,
    UnifiedSample,
    PIIAnnotation,
    PII_TAXONOMY
)

OPENPII_LABEL_MAP: Dict[str, str] = {
    "FIRSTNAME": "PERSON",
    "GIVENNAME": "PERSON",
    "SURNAME": "PERSON",
    "LASTNAME": "PERSON",
    "NAME": "PERSON",
    "EMAIL": "EMAIL",
    "PHONE": "PHONE",
    "PHONENUMBER": "PHONE",
    "TELEPHONENUM": "PHONE",
    "STREET": "ADDRESS",
    "CITY": "ADDRESS",
    "ZIPCODE": "ADDRESS",
    "BUILDINGNUM": "ADDRESS",
    "COUNTRY": "ADDRESS",
    "ADDRESS": "ADDRESS",
    "PASSWORD": "PASSWORD",
    "CREDITCARDNUMBER": "CREDIT_CARD",
    "CREDIT_CARD": "CREDIT_CARD",
    "IBAN": "BANK_ACCOUNT",
    "BANKACCOUNT": "BANK_ACCOUNT",
    "ACCOUNTNUMBER": "BANK_ACCOUNT",
    "BIC": "IFSC",
    "IFSC": "IFSC",
    "AADHAAR": "AADHAAR",
    "PAN": "PAN",
    "TAXNUM": "PAN",
    "IDCARDNUM": "AADHAAR",
    "SOCIALNUM": "OTHER_IDENTIFIER",
    "PASSPORT": "PASSPORT",
    "PASSPORTNUM": "PASSPORT",
    "DRIVERLICENSENUM": "DRIVERS_LICENSE",
    "DRIVING_LICENSE": "DRIVERS_LICENSE",
    "DATEOFBIRTH": "DATE_OF_BIRTH",
    "DOB": "DATE_OF_BIRTH",
    "DATE": "DATE_OF_BIRTH",
    "FINANCIAL": "FINANCIAL_VALUE",
    "AMOUNT": "FINANCIAL_VALUE",
    "USERNAME": "USERNAME",
    "PIN": "OTP",
    "OTP": "OTP"
}

class OpenPIIAdapter(BaseDatasetAdapter):
    def __init__(self, source_dir: Path = Path("data/raw/openpii_1.5m")):
        super().__init__("OpenPII", source_dir)

    def get_data_files(self) -> List[Path]:
        files = []
        # Check source dir and alt dirs
        check_dirs = [self.source_dir, Path("data/raw/ai4privacy_1.5m"), Path("data/raw/ai4privacy_1m"), Path("data/raw/ai4privacy")]
        for d in check_dirs:
            if d.exists():
                files.extend(list(d.glob("**/*.parquet")))
                files.extend(list(d.glob("**/*.jsonl")))
                if files:
                    break
        return sorted(files)

    def count_samples(self) -> int:
        total = 0
        for f in self.get_data_files():
            try:
                if f.suffix == ".parquet":
                    table = pq.read_table(f)
                    total += table.num_rows
                elif f.suffix == ".jsonl":
                    with open(f, "r", encoding="utf-8") as jf:
                        total += sum(1 for _ in jf)
            except Exception:
                pass
        return total

    def iter_samples(self, limit: Optional[int] = None) -> Iterator[UnifiedSample]:
        count = 0
        for f in self.get_data_files():
            try:
                if f.suffix == ".jsonl":
                    with open(f, "r", encoding="utf-8") as jf:
                        for idx, line in enumerate(jf):
                            try:
                                row = json.loads(line)
                            except Exception:
                                continue
                            sample_id = f"openpii_{f.stem}_{idx}"
                            text = str(row.get("source_text", row.get("text", "")))
                            pii_annotations: List[PIIAnnotation] = []
                            mask = row.get("privacy_mask", row.get("entities", []))
                            if isinstance(mask, list):
                                for ent in mask:
                                    if isinstance(ent, dict):
                                        raw_label = str(ent.get("label", ent.get("type", ""))).upper()
                                        unified_label = OPENPII_LABEL_MAP.get(raw_label, "OTHER_IDENTIFIER")
                                        pii_annotations.append(PIIAnnotation(
                                            bbox=[0.05, 0.05, 0.95, 0.15],
                                            type=unified_label,
                                            confidence=1.0,
                                            text=str(ent.get("value", "[REDACTED]"))
                                        ))
                            sample = UnifiedSample(
                                sample_id=sample_id,
                                source_dataset="OpenPII",
                                dom=text,
                                pii=pii_annotations
                            )
                            valid, _ = self.validate_sample(sample)
                            if valid:
                                yield sample
                                count += 1
                                if limit and count >= limit:
                                    return
                elif f.suffix == ".parquet":
                    table = pq.read_table(f)
                    df = table.to_pandas()
                    for idx, row in df.iterrows():
                        sample_id = f"openpii_{f.stem}_{idx}"
                        text = str(row.get("text", row.get("source_text", "")))
                        pii_annotations: List[PIIAnnotation] = []
                        entities = row.get("entities", row.get("spans", []))
                        if isinstance(entities, list):
                            for ent in entities:
                                if isinstance(ent, dict):
                                    raw_label = str(ent.get("label", ent.get("type", ""))).upper()
                                    unified_label = OPENPII_LABEL_MAP.get(raw_label, "OTHER_IDENTIFIER")
                                    pii_annotations.append(PIIAnnotation(
                                        bbox=[0.05, 0.05, 0.95, 0.15],
                                        type=unified_label,
                                        confidence=1.0,
                                        text="[REDACTED]"
                                    ))
                        sample = UnifiedSample(
                            sample_id=sample_id,
                            source_dataset="OpenPII",
                            dom=text,
                            pii=pii_annotations
                        )
                        valid, _ = self.validate_sample(sample)
                        if valid:
                            yield sample
                            count += 1
                            if limit and count >= limit:
                                return
            except Exception as e:
                print(f"[OpenPIIAdapter] Error reading {f.name}: {e}")
