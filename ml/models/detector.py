"""
Multi-Task Lightweight Neural Architectures for On-Device Browser Perception.
SIH PS 26171: On-device Visual Perception for Light-weight Browser Agents.

Architectures:
1. LightweightBrowserAgentDetector: Original baseline model (backward compatible).
2. UIDetectorModel: Stage A UI Perception (34 UI taxonomy classes + BBox regression).
3. PIIDetectorModel: Stage B On-Device PII Detector (26 PII classes + BBox regression).
4. ActionGrounderModel: Stage C Multimodal Action Grounder (Text instruction + Screen -> Action + Target BBox).
"""
import torch
import torch.nn as nn
from dataset_adapters.base import UI_TAXONOMY, PII_TAXONOMY, ACTION_TYPES

# -------------------------------------------------------------------
# 1. Baseline Model (Preserved for Backward Compatibility)
# -------------------------------------------------------------------
class LightweightBrowserAgentDetector(nn.Module):
    def __init__(self, num_classes=16):
        super().__init__()
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
        self.bbox_head = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 4),
            nn.Sigmoid()
        )
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


# -------------------------------------------------------------------
# 2. Stage A: UI Perception Model (34 UI Classes)
# -------------------------------------------------------------------
class UIDetectorModel(nn.Module):
    def __init__(self, num_classes=len(UI_TAXONOMY), p_drop=0.2):
        super().__init__()
        self.backbone = nn.Sequential(
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
        self.bbox_head = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.SiLU(),
            nn.Linear(128, 4),
            nn.Sigmoid()
        )
        self.cls_head = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.SiLU(),
            nn.Linear(128, num_classes)
        )

    def forward(self, x):
        feat = self.backbone(x).flatten(1)
        bboxes = self.bbox_head(feat)
        logits = self.cls_head(feat)
        return bboxes, logits


# -------------------------------------------------------------------
# 3. Stage B: Enhanced PII Detector (26 PII Classes with Indian Context)
# -------------------------------------------------------------------
class PIIDetectorModel(nn.Module):
    def __init__(self, num_classes=len(PII_TAXONOMY), p_drop=0.25):
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


# -------------------------------------------------------------------
# 4. Stage C: Multimodal Action Grounder
# -------------------------------------------------------------------
class ActionGrounderModel(nn.Module):
    def __init__(self, vocab_size=5000, num_actions=len(ACTION_TYPES), embed_dim=64):
        super().__init__()
        # Visual feature extractor
        self.vis_encoder = nn.Sequential(
            nn.Conv2d(3, 32, 3, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.Conv2d(32, 64, 3, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.Conv2d(64, 128, 3, stride=2, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1))
        )
        # Instruction text encoder
        self.token_embed = nn.Embedding(vocab_size, embed_dim)
        self.text_lstm = nn.LSTM(embed_dim, 64, batch_first=True, bidirectional=True)

        # Fusion & Multi-Task Action Heads (128 vis + 128 text = 256)
        self.action_head = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, num_actions)
        )
        self.target_bbox_head = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 4),
            nn.Sigmoid()
        )

    def forward(self, img, tokens):
        v_feat = self.vis_encoder(img).flatten(1)  # [B, 128]
        t_emb = self.token_embed(tokens)           # [B, L, 64]
        t_out, _ = self.text_lstm(t_emb)
        t_pooled = t_out.mean(dim=1)               # [B, 128]

        fused = torch.cat([v_feat, t_pooled], dim=1) # [B, 256]
        action_logits = self.action_head(fused)
        target_bboxes = self.target_bbox_head(fused)
        return target_bboxes, action_logits


def build_model(num_classes=16):
    return LightweightBrowserAgentDetector(num_classes=num_classes)
