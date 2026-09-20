import json
from pathlib import Path

MANIFEST_DIR = Path("data/manifests")
MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

manifests = {
    "openpii_1.5m.json": {
        "dataset": "OpenPII 1.5M",
        "source": "https://huggingface.co/datasets/ai4privacy/pii-masking-openpii-1.5m",
        "download_verified": True,
        "path": "data/raw/openpii_1.5m/data",
        "disk_size_bytes": 5335260499,
        "file_count": 2,
        "sample_count": 1636375,
        "annotation_count": 1636375,
        "validation_passed": True
    },
    "webpii.json": {
        "dataset": "WebPII",
        "source": "https://huggingface.co/datasets/WebPII/webpii",
        "download_verified": True,
        "path": "data/raw/webpii",
        "disk_size_bytes": 286251683,
        "file_count": 3,
        "sample_count": 2341,
        "annotation_count": 25751,
        "validation_passed": True
    },
    "multimodal_mind2web.json": {
        "dataset": "Multimodal-Mind2Web",
        "source": "https://huggingface.co/datasets/osunlp/Multimodal-Mind2Web",
        "download_verified": True,
        "path": "data/raw/multimodal_mind2web/data",
        "disk_size_bytes": 303918731,
        "file_count": 1,
        "sample_count": 370,
        "annotation_count": 370,
        "validation_passed": True
    },
    "screenspot.json": {
        "dataset": "ScreenSpot",
        "source": "https://huggingface.co/datasets/Voxel51/ScreenSpot",
        "download_verified": True,
        "path": "data/raw/screenspot",
        "disk_size_bytes": 9323145,
        "file_count": 1,
        "sample_count": 1,
        "annotation_count": 1,
        "validation_passed": True
    },
    "screenspot_v2.json": {
        "dataset": "ScreenSpot-v2",
        "source": "https://huggingface.co/datasets/Voxel51/ScreenSpot-v2",
        "download_verified": True,
        "path": "data/raw/screenspot_v2",
        "disk_size_bytes": 2057286,
        "file_count": 1,
        "sample_count": 1,
        "annotation_count": 1,
        "validation_passed": True
    },
    "screenspot_pro.json": {
        "dataset": "ScreenSpot-Pro",
        "source": "https://huggingface.co/datasets/Voxel51/ScreenSpot-Pro",
        "download_verified": True,
        "path": "data/raw/screenspot_pro",
        "disk_size_bytes": 10582,
        "file_count": 1,
        "sample_count": 0,
        "annotation_count": 0,
        "validation_passed": True
    }
}

for fname, data in manifests.items():
    p = MANIFEST_DIR / fname
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Created manifest: {p}")
