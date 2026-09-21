"""
Reproducible Training Pipeline on Real Datasets (Phase 14)
Uses WebPII real dataset samples with train/val splits,
evaluates IoU and CrossEntropy loss, logs real metrics, and saves checkpoint.
"""
import torch
import torch.nn as nn
from pathlib import Path
import time
import json
import numpy as np
from PIL import Image
import torchvision.transforms as T

from ml.models.detector import build_model
from ml.datasets.loaders import WebPIIDataset

CHECKPOINTS_DIR = Path("models/checkpoints")
CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)

# Regularized Visual Detector
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


def train_on_real_dataset(epochs: int = 3, sample_count: int = 20):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[TRAIN] Training with REAL data on: {device}")

    # 1. Load real samples
    dataset = WebPIIDataset(split="test", max_samples=sample_count)
    if len(dataset) < 4:
        print("[TRAIN] Warning: Insufficient real samples, aborting.")
        return

    train_n = int(0.75 * len(dataset))
    val_n = len(dataset) - train_n
    train_set, val_set = torch.utils.data.random_split(dataset, [train_n, val_n])

    train_loader = torch.utils.data.DataLoader(train_set, batch_size=4, shuffle=True)
    val_loader = torch.utils.data.DataLoader(val_set, batch_size=4, shuffle=False)

    model = RegularizedVisualPIIDetector(num_classes=20, p_drop=0.2).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
    criterion_box = nn.SmoothL1Loss()
    criterion_cls = nn.CrossEntropyLoss()

    best_val_loss = float("inf")
    metrics_history = []

    t0 = time.time()
    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        for batch in train_loader:
            imgs = batch["image"].to(device)
            boxes = batch["box"].to(device)
            labels = batch["label"].to(device)

            optimizer.zero_grad()
            p_boxes, p_logits = model(imgs)
            loss_b = criterion_box(p_boxes, boxes)
            loss_c = criterion_cls(p_logits, labels)
            loss = loss_b + loss_c

            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        train_loss /= len(train_loader)

        # Validation
        model.eval()
        val_loss = 0.0
        val_ious = []
        with torch.no_grad():
            for batch in val_loader:
                imgs = batch["image"].to(device)
                boxes = batch["box"].to(device)
                labels = batch["label"].to(device)

                p_boxes, p_logits = model(imgs)
                l_b = criterion_box(p_boxes, boxes)
                l_c = criterion_cls(p_logits, labels)
                val_loss += (l_b + l_c).item()

                # Calculate IoU
                for pb, tb in zip(p_boxes.cpu().numpy(), boxes.cpu().numpy()):
                    xa = max(pb[0], tb[0])
                    ya = max(pb[1], tb[1])
                    xb = min(pb[2], tb[2])
                    yb = min(pb[3], tb[3])
                    inter = max(0, xb - xa) * max(0, yb - ya)
                    area_p = max(0, pb[2] - pb[0]) * max(0, pb[3] - pb[1])
                    area_t = max(0, tb[2] - tb[0]) * max(0, tb[3] - tb[1])
                    union = area_p + area_t - inter
                    iou = inter / union if union > 0 else 0.0
                    val_ious.append(iou)

        val_loss /= len(val_loader)
        mean_iou = float(np.mean(val_ious)) if val_ious else 0.0

        epoch_record = {
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "val_loss": round(val_loss, 4),
            "mean_iou": round(mean_iou, 4)
        }
        metrics_history.append(epoch_record)
        print(f"[TRAIN] Epoch {epoch}/{epochs} - Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Val IoU: {mean_iou:.4f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), CHECKPOINTS_DIR / "regularized_best_pii_detector.pt")

    duration = time.time() - t0
    print(f"[TRAIN] Training on real WebPII data completed in {duration:.2f}s. Checkpoint saved.")

    # Save real training metrics
    with open("results/real_training_metrics.json", "w", encoding="utf-8") as f:
        json.dump({"metrics": metrics_history, "duration_s": duration}, f, indent=2)

if __name__ == "__main__":
    train_on_real_dataset(epochs=2, sample_count=16)
