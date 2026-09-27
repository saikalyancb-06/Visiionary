"""
ScreenSpot Suite Adapter (ScreenSpot, ScreenSpot-v2, ScreenSpot-Pro) for Unified Schema.
Extracts high-resolution UI screen states, bounding boxes, and grounding instructions.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Iterator, Dict, Any, List
from PIL import Image

from dataset_adapters.base import (
    BaseDatasetAdapter,
    UnifiedSample,
    UIElement,
    ActionAnnotation,
    UI_TAXONOMY
)

SCREENSPOT_UI_MAP: Dict[str, str] = {
    "button": "button",
    "link": "link",
    "text": "text",
    "input": "input",
    "search": "search",
    "icon": "icon",
    "image": "image",
    "checkbox": "checkbox",
    "radio": "radio",
    "select": "select",
    "tab": "tab",
    "table": "table",
    "menu": "menu"
}

class ScreenSpotAdapter(BaseDatasetAdapter):
    def __init__(self, source_dir: Path = Path("data/raw/screenspot")):
        super().__init__("ScreenSpot", source_dir)
        # Check subdirectories or variants (screenspot_pro, screenspot_v2)
        self.dirs = [
            source_dir,
            Path("data/raw/screenspot_pro"),
            Path("data/raw/screenspot_v2")
        ]

    def count_samples(self) -> int:
        total = 0
        for d in self.dirs:
            if d.exists():
                json_files = list(d.glob("**/*.json"))
                for jf in json_files:
                    try:
                        with open(jf, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                total += len(data)
                            elif isinstance(data, dict):
                                total += len(data.get("samples", [1]))
                    except Exception:
                        pass
        return total

    def iter_samples(self, limit: Optional[int] = None) -> Iterator[UnifiedSample]:
        count = 0
        for d in self.dirs:
            if not d.exists():
                continue
            for jf in d.glob("**/*.json"):
                if "metadata" in jf.name:
                    continue
                try:
                    with open(jf, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    sample_list = data.get("samples", data) if isinstance(data, dict) else data
                    if not isinstance(sample_list, list):
                        continue

                    for idx, entry in enumerate(sample_list):
                        if not isinstance(entry, dict):
                            continue
                        
                        img_path = entry.get("filepath") or entry.get("img_filename") or entry.get("image") or entry.get("file_name")
                        full_img_path = None
                        if img_path:
                            cand1 = d / img_path
                            cand2 = jf.parent / img_path
                            if cand1.exists():
                                full_img_path = str(cand1)
                            elif cand2.exists():
                                full_img_path = str(cand2)
                                    
                        task = entry.get("instruction", entry.get("task", entry.get("prompt", "")))
                        
                        det = entry.get("action_detection") or entry.get("detection") or {}
                        raw_bbox = det.get("bounding_box") or entry.get("bbox") or entry.get("box", [0, 0, 100, 100])
                        
                        meta = entry.get("metadata", {})
                        w = int(meta.get("width", 1920)) if isinstance(meta, dict) else 1920
                        h = int(meta.get("height", 1080)) if isinstance(meta, dict) else 1080

                        elements = []
                        if isinstance(raw_bbox, (list, tuple)) and len(raw_bbox) == 4:
                            x1, y1, x2, y2 = [float(v) for v in raw_bbox]
                            if max(x1, y1, x2, y2) > 1.0:
                                nx1 = max(0.0, min(1.0, x1 / w))
                                ny1 = max(0.0, min(1.0, y1 / h))
                                nx2 = max(0.0, min(1.0, (x1 + x2) / w))
                                ny2 = max(0.0, min(1.0, (y1 + y2) / h))
                            else:
                                nx1, ny1 = x1, y1
                                nx2, ny2 = min(1.0, x1 + x2), min(1.0, y1 + y2)
                                
                            raw_type = str(det.get("label") or entry.get("ui_type") or entry.get("data_type") or "button").lower()
                            ui_type = SCREENSPOT_UI_MAP.get(raw_type, "button")
                            
                            elements.append(UIElement(
                                bbox=[min(nx1, nx2), min(ny1, ny2), max(nx1, nx2), max(ny1, ny2)],
                                type=ui_type,
                                text=entry.get("text"),
                                interactable=True
                            ))

                        sample = UnifiedSample(
                            sample_id=f"screenspot_{jf.stem}_{idx}",
                            source_dataset="ScreenSpot",
                            image=full_img_path,
                            width=w,
                            height=h,
                            elements=elements,
                            task=task,
                            action=ActionAnnotation(
                                type="CLICK",
                                target_bbox=elements[0].bbox if elements else [0.5, 0.5, 0.55, 0.55]
                            )
                        )
                        valid, _ = self.validate_sample(sample)
                        if valid:
                            yield sample
                            count += 1
                            if limit and count >= limit:
                                return
                except Exception as e:
                    pass
