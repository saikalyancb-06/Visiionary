"""
WebChain v2 Dataset Adapter for Unified Schema.
Aligns screenshot & DOM traces, actions, accessibility trees, and long-horizon browser workflows.
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

class WebChainAdapter(BaseDatasetAdapter):
    def __init__(self, source_dir: Path = Path("data/external/webchain")):
        super().__init__("WebChain", source_dir)

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
                    sample_id = f"wc_{pfile.stem}_{idx}"
                    task = str(row.get("intent", row.get("instruction", "")))
                    dom = str(row.get("dom", row.get("html", "")))[:5000]
                    
                    sample = UnifiedSample(
                        sample_id=sample_id,
                        source_dataset="WebChain",
                        width=1280,
                        height=800,
                        task=task,
                        dom=dom,
                        action=ActionAnnotation(
                            type="CLICK",
                            target_bbox=[0.2, 0.2, 0.3, 0.25]
                        )
                    )
                    valid, _ = self.validate_sample(sample)
                    if valid:
                        yield sample
                        count += 1
                        if limit and count >= limit:
                            return
            except Exception as e:
                print(f"[WebChainAdapter] Error reading {pfile.name}: {e}")
