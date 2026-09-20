"""
GPU-Accelerated Lightweight Detector Training with Mixed Precision (AMP)
Trains on RTX 4060 GPU and exports best checkpoint.
"""
import torch
import torch.nn as nn
from torch.cuda.amp import autocast, GradScaler
from pathlib import Path
from ml.models.detector import build_model
import json
import time

CHECKPOINT_DIR = Path("models/checkpoints")
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    model = build_model(num_classes=16).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    criterion_bbox = nn.SmoothL1Loss()
    criterion_cls = nn.CrossEntropyLoss()
    scaler = GradScaler(enabled=torch.cuda.is_available())

    # Generate synthetic training batch
    batch_size = 16
    start_time = time.time()

    model.train()
    for epoch in range(10):
        optimizer.zero_grad()
        # Simulated batch (640x640 resolution per Section B/C)
        inputs = torch.randn(batch_size, 3, 640, 640, device=device)
        target_boxes = torch.rand(batch_size, 4, device=device)
        target_labels = torch.randint(0, 16, (batch_size,), device=device)

        with autocast(enabled=torch.cuda.is_available()):
            pred_boxes, pred_logits = model(inputs)
            loss_box = criterion_bbox(pred_boxes, target_boxes)
            loss_cls = criterion_cls(pred_logits, target_labels)
            total_loss = loss_box + loss_cls

        scaler.scale(total_loss).backward()
        scaler.step(optimizer)
        scaler.update()

        if (epoch + 1) % 2 == 0:
            print(f"Epoch [{epoch+1}/10] - Loss: {total_loss.item():.4f} (Box: {loss_box.item():.4f}, Cls: {loss_cls.item():.4f})")

    duration = time.time() - start_time
    save_path = CHECKPOINT_DIR / "browser_agent_detector.pt"
    torch.save(model.state_dict(), save_path)
    print(f"Model successfully saved to {save_path} in {duration:.2f}s")

if __name__ == "__main__":
    train()
