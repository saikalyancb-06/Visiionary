"""
Multimodal-Mind2Web Dataset Adapter for Unified Schema.
Extracts browser interaction workflows, DOM nodes, target bounding boxes, and actions.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Optional, Iterator, Dict, Any, List
import pyarrow.parquet as pq

from dataset_adapters.base import (
    BaseDatasetAdapter,
    UnifiedSample,
    ActionAnnotation,
    UIElement
)

MIND2WEB_ACTION_MAP: Dict[str, str] = {
    "click": "CLICK",
    "type": "TYPE",
    "select": "SELECT",
    "hover": "HOVER",
    "press_enter": "PRESS",
    "scroll": "SCROLL"
}

class Mind2WebAdapter(BaseDatasetAdapter):
    def __init__(self, source_dir: Path = Path("data/raw/multimodal_mind2web")):
        super().__init__("Mind2Web", source_dir)
        self.data_dir = self.source_dir / "data" if (self.source_dir / "data").exists() else self.source_dir

    def get_parquet_files(self) -> List[Path]:
        if not self.data_dir.exists():
            return []
        return sorted(list(self.data_dir.glob("*.parquet")))

    def count_samples(self) -> int:
        total = 0
        for pfile in self.get_parquet_files():
            try:
                table = pq.read_table(pfile, columns=["action_reprs"])
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
                    sample_id = f"m2w_{pfile.stem}_{idx}"
                    task = str(row.get("confirmed_task", row.get("intent", "")))
                    
                    # Extract raw action
                    raw_act_type = str(row.get("action_type", "click")).lower()
                    act_type = MIND2WEB_ACTION_MAP.get(raw_act_type, "CLICK")
                    
                    # Extract target element bbox if present
                    act_bbox = [0.1, 0.1, 0.2, 0.2]  # Default fallback normalized bbox
                    raw_box = row.get("target_bbox")
                    if isinstance(raw_box, (list, tuple)) and len(raw_box) == 4:
                        act_bbox = [float(c) for c in raw_box]

                    action = ActionAnnotation(
                        type=act_type,
                        target_bbox=act_bbox,
                        value=str(row.get("action_value", "")) if row.get("action_value") else None
                    )

                    sample = UnifiedSample(
                        sample_id=sample_id,
                        source_dataset="Multimodal-Mind2Web",
                        task=task,
                        action=action,
                        dom=str(row.get("cleaned_html", row.get("dom", "")))[:5000]
                    )
                    valid, _ = self.validate_sample(sample)
                    if valid:
                        yield sample
                        count += 1
                        if limit and count >= limit:
                            return
            except Exception as e:
                print(f"[Mind2WebAdapter] Error reading {pfile.name}: {e}")
