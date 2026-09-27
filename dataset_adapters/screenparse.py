"""
ScreenParse Dataset Adapter for Unified Schema.
Dense UI element parsing, reading order, 55 UI classes mapped to 34 UI Taxonomy.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Iterator, Dict, Any, List
import pyarrow.parquet as pq

from dataset_adapters.base import (
    BaseDatasetAdapter,
    UnifiedSample,
    UIElement,
    UI_TAXONOMY
)

SCREENPARSE_UI_MAP: Dict[str, str] = {
    "button": "button",
    "utility button": "button",
    "link": "link",
    "text": "text",
    "heading": "heading",
    "title": "heading",
    "input": "input",
    "text input": "input",
    "password": "password_input",
    "search": "search",
    "search bar": "search",
    "search field": "search",
    "checkbox": "checkbox",
    "radio": "radio",
    "radiobox": "radio",
    "select": "select",
    "combobox": "dropdown",
    "dropdown": "dropdown",
    "menu": "menu",
    "menu_item": "menu",
    "popup menu": "menu",
    "tab": "tab",
    "navigation": "navigation",
    "navbar": "navigation",
    "navigation bar": "navigation",
    "bottom navigation": "navigation",
    "breadcrumb": "navigation",
    "sidebar": "sidebar",
    "side bar": "sidebar",
    "toolbar": "toolbar",
    "table": "table",
    "list": "list",
    "list item": "list",
    "image": "image",
    "icon": "icon",
    "app icon": "icon",
    "file icon": "icon",
    "avatar": "avatar",
    "logo": "logo",
    "notification": "notification",
    "alert": "notification",
    "badge": "badge",
    "tooltip": "tooltip",
    "modal": "modal",
    "dialog": "dialog",
    "popup": "dialog",
    "scroll": "scroll",
    "slider": "slider",
    "calendar": "calendar",
    "date-time picker": "date_picker",
    "datepicker": "date_picker",
    "pagination": "pagination",
    "page control": "pagination",
    "progress bar": "progress_bar",
    "switch": "switch",
    "code": "code",
    "chart": "chart",
    "video": "video",
    "carousel": "carousel",
    "window": "window"
}

class ScreenParseAdapter(BaseDatasetAdapter):
    def __init__(self, source_dir: Path = Path("data/external/screenparse")):
        super().__init__("ScreenParse", source_dir)

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
                    sample_id = f"sp_{pfile.stem}_{idx}"
                    w = int(row.get("width", 1920)) or 1920
                    h = int(row.get("height", 1080)) or 1080
                    
                    elements: List[UIElement] = []
                    
                    # Direct parquet schema: bboxes, labels, texts, interactable
                    if "bboxes" in row and "labels" in row:
                        raw_bboxes = row.get("bboxes", [])
                        raw_labels = row.get("labels", [])
                        raw_texts = row.get("texts", [])
                        raw_interact = row.get("interactable", [])
                        
                        n_boxes = len(raw_bboxes)
                        for bi in range(n_boxes):
                            bbox = raw_bboxes[bi]
                            if len(bbox) != 4:
                                continue
                            raw_cls = str(raw_labels[bi] if bi < len(raw_labels) else "button").lower()
                            ui_type = SCREENPARSE_UI_MAP.get(raw_cls, "other")
                            
                            bx, by, bw, bh = [float(v) for v in bbox]
                            # Coordinates in ScreenParse are [x, y, w, h] in absolute pixel coordinates
                            x1 = bx
                            y1 = by
                            x2 = bx + bw
                            y2 = by + bh
                            
                            nx1 = max(0.0, min(1.0, x1 / w))
                            ny1 = max(0.0, min(1.0, y1 / h))
                            nx2 = max(0.0, min(1.0, x2 / w))
                            ny2 = max(0.0, min(1.0, y2 / h))
                            
                            txt = str(raw_texts[bi]) if (raw_texts is not None and bi < len(raw_texts)) else None
                            inter = bool(raw_interact[bi]) if (raw_interact is not None and bi < len(raw_interact)) else True
                            
                            elements.append(UIElement(
                                bbox=[min(nx1, nx2), min(ny1, ny2), max(nx1, nx2), max(ny1, ny2)],
                                type=ui_type,
                                text=txt if txt else None,
                                interactable=inter
                            ))
                    else:
                        # Fallback for dict/list elements schema
                        raw_annotations = row.get("elements", row.get("annotations", []))
                        if isinstance(raw_annotations, str):
                            try:
                                raw_annotations = json.loads(raw_annotations)
                            except Exception:
                                raw_annotations = []
                        if isinstance(raw_annotations, list):
                            for el in raw_annotations:
                                if not isinstance(el, dict):
                                    continue
                                raw_cls = str(el.get("category", el.get("class", "button"))).lower()
                                ui_type = SCREENPARSE_UI_MAP.get(raw_cls, "other")
                                bbox = el.get("bbox", [0, 0, w, h])
                                if len(bbox) == 4:
                                    x1, y1, x2, y2 = [float(v) for v in bbox]
                                    if max(x1, y1, x2, y2) > 1.0:
                                        nx1 = max(0.0, min(1.0, x1 / w))
                                        ny1 = max(0.0, min(1.0, y1 / h))
                                        nx2 = max(0.0, min(1.0, x2 / w))
                                        ny2 = max(0.0, min(1.0, y2 / h))
                                    else:
                                        nx1, ny1, nx2, ny2 = x1, y1, x2, y2
                                    elements.append(UIElement(
                                        bbox=[min(nx1, nx2), min(ny1, ny2), max(nx1, nx2), max(ny1, ny2)],
                                        type=ui_type,
                                        text=el.get("text"),
                                        interactable=el.get("interactable", True)
                                    ))

                    img_bytes = None
                    if isinstance(row.get("image"), dict) and "bytes" in row["image"]:
                        img_bytes = row["image"]["bytes"]

                    sample = UnifiedSample(
                        sample_id=sample_id,
                        source_dataset="ScreenParse",
                        image_bytes=img_bytes,
                        width=w,
                        height=h,
                        elements=elements
                    )
                    valid, _ = self.validate_sample(sample)
                    if valid:
                        yield sample
                        count += 1
                        if limit and count >= limit:
                            return
            except Exception as e:
                print(f"[ScreenParseAdapter] Error reading {pfile.name}: {e}")
