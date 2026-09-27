"""
AndroidControl & Android in the Wild Adapters for Unified Schema.
Extracts mobile UI actions, gestures, and multi-step screen trajectories.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Iterator, Dict, Any, List
import pyarrow.parquet as pq

from dataset_adapters.base import (
    BaseDatasetAdapter,
    UnifiedSample,
    ActionAnnotation,
    UIElement
)

class AndroidControlAdapter(BaseDatasetAdapter):
    def __init__(self, source_dir: Path = Path("data/external/android_control")):
        super().__init__("AndroidControl", source_dir)

    def get_parquet_files(self) -> List[Path]:
        if not self.source_dir.exists():
            return []
        return sorted(list(self.source_dir.glob("**/*.parquet")))

    def count_samples(self) -> int:
        total = 0
        for pfile in self.get_parquet_files():
            try:
                table = pq.read_table(pfile)
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
                    sample_id = f"ac_{pfile.stem}_{idx}"
                    instruction = str(row.get("instruction", row.get("goal", "")))
                    
                    action_type = "CLICK"
                    raw_action = str(row.get("action_type", "")).upper()
                    if "SCROLL" in raw_action:
                        action_type = "SCROLL"
                    elif "TYPE" in raw_action:
                        action_type = "TYPE"

                    # Target coordinates [x, y] or [x1, y1, x2, y2]
                    target_bbox = [0.5, 0.5, 0.55, 0.55]
                    if "point" in row and isinstance(row["point"], (list, tuple)) and len(row["point"]) >= 2:
                        px, py = float(row["point"][0]), float(row["point"][1])
                        # If pixel vs normalized
                        px = px / 1080.0 if px > 1.0 else px
                        py = py / 2400.0 if py > 1.0 else py
                        target_bbox = [max(0.0, px - 0.02), max(0.0, py - 0.02), min(1.0, px + 0.02), min(1.0, py + 0.02)]

                    sample = UnifiedSample(
                        sample_id=sample_id,
                        source_dataset="AndroidControl",
                        width=1080,
                        height=2400,
                        task=instruction,
                        action=ActionAnnotation(
                            type=action_type,
                            target_bbox=target_bbox,
                            value=str(row.get("text", "")) if action_type == "TYPE" else None
                        )
                    )
                    valid, _ = self.validate_sample(sample)
                    if valid:
                        yield sample
                        count += 1
                        if limit and count >= limit:
                            return
            except Exception as e:
                print(f"[AndroidControlAdapter] Error reading {pfile.name}: {e}")

class AndroidInTheWildAdapter(BaseDatasetAdapter):
    def __init__(self, source_dir: Path = Path("data/external/android_in_the_wild")):
        super().__init__("AndroidInTheWild", source_dir)

    def get_parquet_files(self) -> List[Path]:
        if not self.source_dir.exists():
            return []
        return sorted(list(self.source_dir.glob("**/*.parquet")))

    def count_samples(self) -> int:
        total = 0
        for pfile in self.get_parquet_files():
            try:
                table = pq.read_table(pfile)
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
                    sample_id = f"aitw_{pfile.stem}_{idx}"
                    instruction = str(row.get("goal_info", row.get("instruction", "")))
                    
                    sample = UnifiedSample(
                        sample_id=sample_id,
                        source_dataset="AndroidInTheWild",
                        width=1080,
                        height=2400,
                        task=instruction,
                        action=ActionAnnotation(
                            type="CLICK",
                            target_bbox=[0.5, 0.5, 0.55, 0.55]
                        )
                    )
                    valid, _ = self.validate_sample(sample)
                    if valid:
                        yield sample
                        count += 1
                        if limit and count >= limit:
                            return
            except Exception as e:
                print(f"[AndroidInTheWildAdapter] Error reading {pfile.name}: {e}")
