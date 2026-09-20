"""
UI & PII Multi-Task Lightweight Detector Architecture
Apache 2.0 / Permissive Backbone (MobileNetV3-Small / SSDLite style)
Detects both Safe UI elements (buttons, inputs) and Sensitive PII regions.
Exports directly to ONNX for in-browser execution.
"""
import torch
import torch.nn as nn

class LightweightBrowserAgentDetector(nn.Module):
    def __init__(self, num_classes=16):
        super().__init__()
        # Lightweight Feature Extractor (MobileNetV3 style inverted bottlenecks)
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(16),
            nn.Hardswish(),
            nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.Hardswish(),
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.Hardswish(),
            nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(128),
            nn.Hardswish()
        )
        self.global_pool = nn.AdaptiveAvgPool2d((1, 1))
        # Bounding box regression head [x1, y1, x2, y2]
        self.bbox_head = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 4),
            nn.Sigmoid()
        )
        # Class classification head (UI roles & PII types)
        self.cls_head = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        feat = self.features(x)
        pooled = self.global_pool(feat).flatten(1)
        bboxes = self.bbox_head(pooled)
        logits = self.cls_head(pooled)
        return bboxes, logits

def build_model(num_classes=16):
    return LightweightBrowserAgentDetector(num_classes=num_classes)
