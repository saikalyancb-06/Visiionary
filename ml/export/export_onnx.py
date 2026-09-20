"""
ONNX Export and Numerical Parity Verification (Phase 10)
Exports PyTorch detector to ONNX with FP32 and FP16 options.
Verifies PyTorch vs ONNX Runtime numerical outputs.
"""
import torch
import numpy as np
import onnx
import onnxruntime as ort
from pathlib import Path
from ml.models.detector import build_model
import json

ONNX_DIR = Path("models/onnx")
ONNX_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT = Path("models/checkpoints/browser_agent_detector.pt")

def export_and_verify():
    # 1. Load trained model
    model = build_model(num_classes=16)
    model.load_state_dict(torch.load(CHECKPOINT, map_location="cpu"))
    model.eval()

    # 2. Export to ONNX (Fixed 640x640 resolution)
    dummy_input = torch.randn(1, 3, 640, 640)
    onnx_path = ONNX_DIR / "browser_agent_detector.onnx"

    torch.onnx.export(
        model,
        dummy_input,
        str(onnx_path),
        input_names=["input_image"],
        output_names=["bboxes", "logits"],
        opset_version=17
    )
    print(f"Exported model to ONNX: {onnx_path}")

    # 3. Numerical Parity Test
    with torch.no_grad():
        pt_boxes, pt_logits = model(dummy_input)

    ort_session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    ort_inputs = {"input_image": dummy_input.numpy()}
    ort_boxes, ort_logits = ort_session.run(None, ort_inputs)

    box_diff = np.max(np.abs(pt_boxes.numpy() - ort_boxes))
    logits_diff = np.max(np.abs(pt_logits.numpy() - ort_logits))

    print(f"Parity Box Max Diff: {box_diff:.6e}")
    print(f"Parity Logits Max Diff: {logits_diff:.6e}")

    parity_passed = box_diff < 1e-4 and logits_diff < 1e-4
    assert parity_passed, "Numerical parity check failed!"
    print("SUCCESS: Numerical parity verified between PyTorch and ONNX Runtime!")

    # Record parity metrics
    parity_report = {
        "model": "browser_agent_detector.onnx",
        "box_max_diff": float(box_diff),
        "logits_max_diff": float(logits_diff),
        "parity_status": "PASS",
        "file_size_mb": onnx_path.stat().st_size / (1024 * 1024)
    }
    with open("benchmarks/accuracy/numerical_parity.json", "w", encoding="utf-8") as f:
        json.dump(parity_report, f, indent=2)

if __name__ == "__main__":
    export_and_verify()
