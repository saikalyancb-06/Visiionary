"""
Export the regularized best checkpoint to ONNX and verify numerical parity
"""
import torch
import torch.nn as nn
import numpy as np
import onnxruntime as ort
from pathlib import Path

CKPT = Path("models/checkpoints/regularized_best_pii_detector.pt")
ONNX_OUT = Path("models/onnx/regularized_visual_pii_detector.onnx")

class RegularizedVisualPIIDetector(nn.Module):
    def __init__(self, num_classes=20, p_drop=0.2):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.SiLU(),
            nn.Dropout2d(p_drop),
            nn.Conv2d(32, 64, 3, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.SiLU(),
            nn.Dropout2d(p_drop),
            nn.Conv2d(64, 128, 3, stride=2, padding=1),
            nn.BatchNorm2d(128),
            nn.SiLU(),
            nn.Dropout2d(p_drop),
            nn.Conv2d(128, 256, 3, stride=2, padding=1),
            nn.BatchNorm2d(256),
            nn.SiLU(),
            nn.AdaptiveAvgPool2d((1, 1))
        )
        self.box_reg = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.SiLU(),
            nn.Linear(128, 4),
            nn.Sigmoid()
        )
        self.cls_head = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.SiLU(),
            nn.Linear(128, num_classes)
        )

    def forward(self, x):
        feat = self.features(x).flatten(1)
        return self.box_reg(feat), self.cls_head(feat)

model = RegularizedVisualPIIDetector(num_classes=20)
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

print(f"Exported regularized model to {ONNX_OUT} ({ONNX_OUT.stat().st_size / (1024*1024):.2f} MB)")
print(f"Parity check: Box diff = {diff_b:.6e}, Logits diff = {diff_l:.6e}")
assert diff_b < 1e-4 and diff_l < 1e-4
print("PARITY PASS: Regularized model verified in ONNX Runtime!")
