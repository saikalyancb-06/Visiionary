"""
Data Quality and Validation Pipeline for SIH PS 26171.
Evaluates raw samples across all datasets, validates bounding box geometries,
normalizes coordinates, calculates MD5 duplicate hashes, maps taxonomies,
and exports comprehensive data quality reports.
"""
from __future__ import annotations

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import Counter

from dataset_adapters.base import (
    UnifiedSample,
    UIElement,
    PIIAnnotation,
    ActionAnnotation,
    UI_TAXONOMY,
    PII_TAXONOMY,
    ACTION_TYPES
)
from dataset_adapters.webpii import WebPIIAdapter
from dataset_adapters.openpii import OpenPIIAdapter
from dataset_adapters.mind2web import Mind2WebAdapter
from dataset_adapters.screenspot import ScreenSpotAdapter
from dataset_adapters.screenparse import ScreenParseAdapter
from dataset_adapters.groundcua import GroundCUAAdapter
from dataset_adapters.android_control import AndroidControlAdapter
from dataset_adapters.webchain import WebChainAdapter

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
REPORT_FILE = REPORTS_DIR / "data_quality_report.json"


class DataQualityPipeline:
    def __init__(self):
        self.seen_hashes = set()
        self.metrics = {
            "total_samples": 0,
            "valid_samples": 0,
            "invalid_samples": 0,
            "duplicates": 0,
            "corrupted_images": 0,
            "label_frequencies": Counter(),
            "pii_frequencies": Counter(),
            "ui_class_frequencies": Counter(),
            "action_frequencies": Counter(),
            "dataset_contribution": Counter()
        }

    def compute_sample_hash(self, sample: UnifiedSample) -> str:
        h = hashlib.md5()
        h.update(sample.source_dataset.encode("utf-8"))
        if sample.image_bytes:
            h.update(sample.image_bytes[:4096])
        elif sample.image:
            h.update(sample.image.encode("utf-8"))
        if sample.dom:
            h.update(sample.dom[:1024].encode("utf-8"))
        if sample.task:
            h.update(sample.task.encode("utf-8"))
        return h.hexdigest()

    def process_adapter(self, adapter, sample_limit: int = 500):
        print(f"Validating samples from [{adapter.name}] (limit={sample_limit})...")
        t0 = time.time()
        count = 0
        try:
            for sample in adapter.iter_samples(limit=sample_limit):
                self.metrics["total_samples"] += 1
                count += 1

                # 1. Deduplication check
                shash = self.compute_sample_hash(sample)
                if shash in self.seen_hashes:
                    self.metrics["duplicates"] += 1
                    continue
                self.seen_hashes.add(shash)

                # 2. Geometry and bounds validation
                is_valid, errors = adapter.validate_sample(sample)
                if not is_valid:
                    self.metrics["invalid_samples"] += 1
                    continue

                self.metrics["valid_samples"] += 1
                self.metrics["dataset_contribution"][sample.source_dataset] += 1

                # 3. Frequency distributions
                for el in sample.elements:
                    self.metrics["ui_class_frequencies"][el.type] += 1
                    self.metrics["label_frequencies"][el.type] += 1

                for p in sample.pii:
                    self.metrics["pii_frequencies"][p.type] += 1
                    self.metrics["label_frequencies"][p.type] += 1

                if sample.action:
                    self.metrics["action_frequencies"][sample.action.type] += 1

            print(f"  -> Validated {count} samples from {adapter.name} in {time.time()-t0:.2f}s")
        except Exception as e:
            print(f"  -> Error validating {adapter.name}: {e}")

    def run(self, per_dataset_limit: int = 500) -> Dict[str, Any]:
        print("=" * 70)
        print("  DATA QUALITY PIPELINE EXECUTION")
        print("=" * 70)

        adapters = [
            WebPIIAdapter(),
            OpenPIIAdapter(),
            Mind2WebAdapter(),
            ScreenSpotAdapter(),
            ScreenParseAdapter(),
            GroundCUAAdapter(),
            AndroidControlAdapter(),
            WebChainAdapter()
        ]

        for adapter in adapters:
            self.process_adapter(adapter, sample_limit=per_dataset_limit)

        # Convert Counters to serializable dicts
        report_data = {
            "validation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_samples": self.metrics["total_samples"],
            "valid_samples": self.metrics["valid_samples"],
            "invalid_samples": self.metrics["invalid_samples"],
            "duplicates": self.metrics["duplicates"],
            "corrupted_images": self.metrics["corrupted_images"],
            "ui_class_frequencies": dict(self.metrics["ui_class_frequencies"].most_common()),
            "pii_frequencies": dict(self.metrics["pii_frequencies"].most_common()),
            "action_frequencies": dict(self.metrics["action_frequencies"].most_common()),
            "dataset_contribution": dict(self.metrics["dataset_contribution"].most_common()),
            "quality_pass_rate_pct": round((self.metrics["valid_samples"] / max(1, self.metrics["total_samples"])) * 100, 2)
        }

        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        print(f"\n[DATA QUALITY REPORT GENERATED] -> {REPORT_FILE}")
        print(f"Valid Samples: {report_data['valid_samples']} / {report_data['total_samples']} ({report_data['quality_pass_rate_pct']}%)")
        return report_data

if __name__ == "__main__":
    DataQualityPipeline().run()
