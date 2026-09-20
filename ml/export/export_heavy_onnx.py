"""
Export heavy trained model checkpoint to ONNX and verify numerical parity
"""
import torch
import numpy as np
import onnxruntime as ort
from pathlib import Path
import sys

sys.path.append("D:/webman")
from ml.training.heavy_train_overnight import HeavyVisualPIIDetector

CKPT = Path("models/checkpoints/heavy_pii_detector_epoch_50.pt")
ONNX_OUT = Path("models/onnx/heavy_visual_pii_detector.onnx")

model = HeavyVisualPIIDetector(num_classes=20)
model.load_state_dict(torch.load(CKPT, map_location="cpu"))
model.eval()

dummy_in = torch.randn(1, 3, 320, 320)
torch.onnx.export(
    model,
    dummy_in,
    str(ONNX_OUT),
    input_names=["input_image"],
    output_names=["boxes", "logits"],
    opset_version=17
)

with torch.no_grad():
    pt_b, pt_l = model(dummy_in)

sess = ort.InferenceSession(str(ONNX_OUT), providers=["CPUExecutionProvider"])
ort_b, ort_l = sess.run(None, {"input_image": dummy_in.numpy()})

diff_b = float(np.max(np.abs(pt_b.numpy() - ort_b)))
diff_l = float(np.max(np.abs(pt_l.numpy() - ort_l)))

print(f"Exported heavy model to {ONNX_OUT} ({ONNX_OUT.stat().st_size / (1024*1024):.2f} MB)")
print(f"Parity check: Box diff = {diff_b:.6e}, Logits diff = {diff_l:.6e}")
assert diff_b < 1e-4 and diff_l < 1e-4
print("PARITY PASS: Heavy visual model verified in ONNX Runtime!")
