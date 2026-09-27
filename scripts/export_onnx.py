"""
Automated ONNX Exporter with Dynamic Axes and Browser Optimization.
SIH PS 26171: On-device Visual Perception for Light-weight Browser Agents.

Exports:
1. models/onnx/ui_detector.onnx
2. models/onnx/pii_detector.onnx
3. models/onnx/action_grounder.onnx
Updates browser-extension/public/models/detector.onnx
"""
from __future__ import annotations

import os
import sys
import shutil
from pathlib import Path
import torch

from ml.models.detector import UIDetectorModel, PIIDetectorModel, ActionGrounderModel
from dataset_adapters.base import UI_TAXONOMY, PII_TAXONOMY

CHECKPOINTS_DIR = Path("models/checkpoints")
ONNX_DIR = Path("models/onnx")
ONNX_DIR.mkdir(parents=True, exist_ok=True)
EXTENSION_MODEL_DIR = Path("browser-extension/public/models")
EXTENSION_MODEL_DIR.mkdir(parents=True, exist_ok=True)


def export_model_to_onnx(model, dummy_input, output_path: Path, input_names, output_names, dynamic_axes=None):
    print(f"Exporting -> {output_path.name}...")
    model.eval()
    with torch.no_grad():
        torch.onnx.export(
            model,
            dummy_input,
            str(output_path),
            input_names=input_names,
            output_names=output_names,
            dynamic_axes=dynamic_axes or {},
            opset_version=17,
            do_constant_folding=True
        )
    size_mb = output_path.stat().st_size / (1024**2)
    print(f"  -> Exported successfully: {output_path} ({size_mb:.2f} MB)")


def run_export_pipeline():
    print("=" * 60)
    print("  ONNX MODEL EXPORT PIPELINE FOR WEBGPU / WASM RUNTIME")
    print("=" * 60)

    # 1. UI Perception Model
    ui_ckpt = CHECKPOINTS_DIR / "ui_detector_best.pt"
    ui_model = UIDetectorModel(num_classes=len(UI_TAXONOMY))
    if ui_ckpt.exists():
        try:
            state = torch.load(ui_ckpt, map_location="cpu")
            weights = state.get("model_state", state)
            ui_model.load_state_dict(weights, strict=False)
            print(f"Loaded weights from {ui_ckpt}")
        except Exception as e:
            print(f"Note on loading {ui_ckpt}: {e}")

    dummy_img = torch.randn(1, 3, 320, 320)
    ui_onnx = ONNX_DIR / "ui_detector.onnx"
    export_model_to_onnx(
        ui_model,
        dummy_img,
        ui_onnx,
        input_names=["input_image"],
        output_names=["boxes", "logits"],
        dynamic_axes={"input_image": {0: "batch_size"}, "boxes": {0: "batch_size"}, "logits": {0: "batch_size"}}
    )

    # 2. PII Detection Model
    pii_ckpt = CHECKPOINTS_DIR / "pii_detector_best.pt"
    if not pii_ckpt.exists():
        pii_ckpt = CHECKPOINTS_DIR / "regularized_best_pii_detector.pt"

    pii_model = PIIDetectorModel(num_classes=len(PII_TAXONOMY))
    if pii_ckpt.exists():
        try:
            state = torch.load(pii_ckpt, map_location="cpu")
            weights = state.get("model_state", state)
            pii_model.load_state_dict(weights, strict=False)
            print(f"Loaded weights from {pii_ckpt}")
        except Exception as e:
            print(f"Note on loading {pii_ckpt}: {e}")

    pii_onnx = ONNX_DIR / "pii_detector.onnx"
    export_model_to_onnx(
        pii_model,
        dummy_img,
        pii_onnx,
        input_names=["input_image"],
        output_names=["boxes", "logits"],
        dynamic_axes={"input_image": {0: "batch_size"}, "boxes": {0: "batch_size"}, "logits": {0: "batch_size"}}
    )

    # Update browser extension packaged model
    ext_dest = EXTENSION_MODEL_DIR / "detector.onnx"
    shutil.copyfile(pii_onnx, ext_dest)
    print(f"  -> Browser Extension model updated: {ext_dest}")

    # 3. Action Grounding Model
    act_ckpt = CHECKPOINTS_DIR / "action_grounder_best.pt"
    act_model = ActionGrounderModel()
    if act_ckpt.exists():
        try:
            state = torch.load(act_ckpt, map_location="cpu")
            weights = state.get("model_state", state)
            act_model.load_state_dict(weights, strict=False)
            print(f"Loaded weights from {act_ckpt}")
        except Exception as e:
            print(f"Note on loading {act_ckpt}: {e}")

    dummy_tokens = torch.randint(0, 5000, (1, 32))
    act_onnx = ONNX_DIR / "action_grounder.onnx"
    export_model_to_onnx(
        act_model,
        (dummy_img, dummy_tokens),
        act_onnx,
        input_names=["input_image", "tokens"],
        output_names=["target_bbox", "action_logits"],
        dynamic_axes={
            "input_image": {0: "batch_size"},
            "tokens": {0: "batch_size", 1: "seq_len"},
            "target_bbox": {0: "batch_size"},
            "action_logits": {0: "batch_size"}
        }
    )

    print("\n[ALL ONNX MODELS SUCCESSFULLY EXPORTED]")

if __name__ == "__main__":
    run_export_pipeline()
