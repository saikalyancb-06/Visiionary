"""
GroundCUA Dataset Adapter for Unified Schema.
Grounded computer-use actions, bounding boxes, and cross-application UI states.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Iterator, Dict, Any, List
import pyarrow.parquet as pq

from dataset_adapters.base import (
    BaseDatasetAdapter,
    UnifiedSample,
    UIElement,
    ActionAnnotation,
    UI_TAXONOMY
)

GROUNDCUA_UI_MAP: Dict[str, str] = {
    "button": "button",
    "menu": "menu",
    "menu_item": "menu",
    "text": "text",
    "icon": "icon",
    "input elements": "input",
    "input": "input",
    "tab": "tab",
    "navigation": "navigation",
    "visual elements": "image",
    "information display": "text",
    "tree_item": "list",
    "toolbar": "toolbar",
    "others": "other"
}

class GroundCUAAdapter(BaseDatasetAdapter):
    def __init__(self, source_dir: Path = Path("data/external/groundcua")):
        super().__init__("GroundCUA", source_dir)

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
                    sample_id = f"gc_{pfile.parent.name}_{pfile.stem}_{idx}"
                    w, h = 1920, 1080
                    instruction = str(row.get("instruction", row.get("query", "")))
                    
                    img_bytes = None
                    if isinstance(row.get("image"), dict) and "bytes" in row["image"]:
                        img_bytes = row["image"]["bytes"]

                    elements: List[UIElement] = []
                    raw_bboxes = row.get("bbox", [])
                    raw_cats = row.get("category", [])
                    raw_texts = row.get("text", [])

                    if hasattr(raw_bboxes, "__len__"):
                        for bi in range(len(raw_bboxes)):
                            b = raw_bboxes[bi]
                            if len(b) != 4:
                                continue
                            x1, y1, x2, y2 = [float(v) for v in b]
                            nx1 = max(0.0, min(1.0, x1 / w))
                            ny1 = max(0.0, min(1.0, y1 / h))
                            nx2 = max(0.0, min(1.0, x2 / w))
                            ny2 = max(0.0, min(1.0, y2 / h))

                            cat_str = str(raw_cats[bi]).lower().strip() if bi < len(raw_cats) else "button"
                            ui_type = GROUNDCUA_UI_MAP.get(cat_str, "other")
                            txt_str = str(raw_texts[bi]).strip() if bi < len(raw_texts) else None

                            elements.append(UIElement(
                                bbox=[min(nx1, nx2), min(ny1, ny2), max(nx1, nx2), max(ny1, ny2)],
                                type=ui_type,
                                text=txt_str if txt_str else None,
                                interactable=(ui_type in ["button", "menu", "input", "tab", "navigation"])
                            ))

                    target_box = elements[0].bbox if elements else [0.5, 0.5, 0.55, 0.55]
                    sample = UnifiedSample(
                        sample_id=sample_id,
                        source_dataset="GroundCUA",
                        image_bytes=img_bytes,
                        width=w,
                        height=h,
                        elements=elements,
                        task=instruction,
                        action=ActionAnnotation(
                            type="CLICK",
                            target_bbox=target_box
                        )
                    )
                    valid, _ = self.validate_sample(sample)
                    if valid:
                        yield sample
                        count += 1
                        if limit and count >= limit:
                            return
            except Exception as e:
                print(f"[GroundCUAAdapter] Error reading {pfile.name}: {e}")

