"""
Re-export the retrained 20-class detector to ONNX and verify numerical parity
"""
import torch
import numpy as np
import onnxruntime as ort
from pathlib import Path
from ml.models.detector import build_model
import json

CHECKPOINT = Path("models/checkpoints/browser_agent_detector.pt")
ONNX_PATH = Path("models/onnx/browser_agent_detector.onnx")

def export_and_verify():
    model = build_model(num_classes=20)
    model.load_state_dict(torch.load(CHECKPOINT, map_location="cpu"))
    model.eval()

    dummy_input = torch.randn(1, 3, 640, 640)
    torch.onnx.export(
        model,
        dummy_input,
        str(ONNX_PATH),
        input_names=["input_image"],
        output_names=["bboxes", "logits"],
        opset_version=17
    )

    with torch.no_grad():
        pt_boxes, pt_logits = model(dummy_input)

    ort_session = ort.InferenceSession(str(ONNX_PATH), providers=["CPUExecutionProvider"])
    ort_boxes, ort_logits = ort_session.run(None, {"input_image": dummy_input.numpy()})

    box_diff = float(np.max(np.abs(pt_boxes.numpy() - ort_boxes)))
    logits_diff = float(np.max(np.abs(pt_logits.numpy() - ort_logits)))

    print(f"Retrained ONNX exported to {ONNX_PATH}")
    print(f"Parity Box Max Diff: {box_diff:.6e}, Logits Diff: {logits_diff:.6e}")
    assert box_diff < 1e-4 and logits_diff < 1e-4, "Parity check failed"
    print("SUCCESS: Full numerical parity verified!")

if __name__ == "__main__":
    export_and_verify()
