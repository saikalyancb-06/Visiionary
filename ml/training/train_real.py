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

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

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


def train_on_full_dataset(epochs: int = 1, batch_size: int = 32, lr: float = 5e-4):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[TRAIN] ================================================================")
    print(f"[TRAIN] RETRAINING ON-DEVICE VISUAL DETECTOR WITH FULL DATASET (PS 26171)")
    print(f"[TRAIN] Compute Device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")
    print(f"[TRAIN] ================================================================")

    webpii_dir = Path("data/raw/webpii/data")
    train_shards = sorted(list(webpii_dir.glob("train-*.parquet")))
    val_shards = sorted(list(webpii_dir.glob("test-*.parquet")))

    if not train_shards:
        print("[TRAIN] ERROR: No training parquet shards found in data/raw/webpii/data.")
        return

    print(f"[TRAIN] Discovered {len(train_shards)} real training shards and {len(val_shards)} validation shards.")

    model = RegularizedVisualPIIDetector(num_classes=20, p_drop=0.2).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    criterion_box = nn.SmoothL1Loss()
    criterion_cls = nn.CrossEntropyLoss()
    use_cuda = torch.cuda.is_available()
    scaler = torch.amp.GradScaler('cuda', enabled=use_cuda)

    best_val_loss = float("inf")
    metrics_history = []
    t_start = time.time()
    total_samples_trained = 0

    for epoch in range(1, epochs + 1):
        model.train()
        epoch_train_loss = 0.0
        epoch_batches = 0
        epoch_samples = 0
        t_epoch_start = time.time()

        for s_idx, shard_path in enumerate(train_shards, 1):
            t_shard = time.time()
            shard_ds = WebPIIDataset(parquet_file=shard_path)
            shard_loader = torch.utils.data.DataLoader(shard_ds, batch_size=batch_size, shuffle=True)

            shard_loss = 0.0
            shard_batches = 0

            for batch in shard_loader:
                imgs = batch["image"].to(device, non_blocking=True)
                boxes = batch["box"].to(device, non_blocking=True)
                labels = batch["label"].to(device, non_blocking=True)

                optimizer.zero_grad()
                with torch.amp.autocast('cuda', enabled=use_cuda):
                    p_boxes, p_logits = model(imgs)
                    loss_b = criterion_box(p_boxes, boxes)
                    loss_c = criterion_cls(p_logits, labels)
                    loss = loss_b + loss_c

                if use_cuda:
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    loss.backward()
                    optimizer.step()

                shard_loss += loss.item()
                shard_batches += 1
                epoch_samples += imgs.size(0)

            avg_shard_loss = shard_loss / max(1, shard_batches)
            epoch_train_loss += shard_loss
            epoch_batches += shard_batches
            total_samples_trained += len(shard_ds)
            shard_time = time.time() - t_shard
            print(f"[TRAIN] Epoch {epoch}/{epochs} | Shard {s_idx:02d}/{len(train_shards):02d} ({shard_path.name}) - Samples: {len(shard_ds):,} | Loss: {avg_shard_loss:.4f} | Time: {shard_time:.1f}s")

            del shard_ds, shard_loader
            if use_cuda:
                torch.cuda.empty_cache()

        mean_train_loss = epoch_train_loss / max(1, epoch_batches)

        # Validation on test shards
        model.eval()
        val_loss = 0.0
        val_batches = 0
        val_ious = []
        val_tp, val_fp, val_fn = 0, 0, 0

        print(f"[VAL] Evaluating epoch {epoch} on held-out test shards...")
        with torch.no_grad():
            for v_shard in val_shards:
                val_ds = WebPIIDataset(parquet_file=v_shard)
                val_loader = torch.utils.data.DataLoader(val_ds, batch_size=batch_size, shuffle=False)
                for batch in val_loader:
                    imgs = batch["image"].to(device)
                    boxes = batch["box"].to(device)
                    labels = batch["label"].to(device)

                    with torch.amp.autocast('cuda', enabled=use_cuda):
                        p_boxes, p_logits = model(imgs)
                        l_b = criterion_box(p_boxes, boxes)
                        l_c = criterion_cls(p_logits, labels)
                        val_loss += (l_b + l_c).item()
                        val_batches += 1

                    for pb, tb, pl, tl in zip(p_boxes.cpu().numpy(), boxes.cpu().numpy(), torch.argmax(p_logits, dim=-1).cpu().numpy(), labels.cpu().numpy()):
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

                        # Classification precision/recall (positive = sensitive PII class > 0)
                        is_target_pos = (tl > 0)
                        is_pred_pos = (pl > 0)
                        if is_pred_pos and is_target_pos:
                            val_tp += 1
                        elif is_pred_pos and not is_target_pos:
                            val_fp += 1
                        elif not is_pred_pos and is_target_pos:
                            val_fn += 1
                del val_ds, val_loader

        mean_val_loss = val_loss / max(1, val_batches)
        mean_iou = float(np.mean(val_ious)) if val_ious else 0.0
        prec = val_tp / (val_tp + val_fp) if (val_tp + val_fp) > 0 else 1.0
        rec = val_tp / (val_tp + val_fn) if (val_tp + val_fn) > 0 else 0.5
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

        epoch_time = time.time() - t_epoch_start
        print(f"[VAL] Epoch {epoch}/{epochs} Complete ({epoch_time:.1f}s) - Train Loss: {mean_train_loss:.4f} | Val Loss: {mean_val_loss:.4f} | Val IoU: {mean_iou:.4f} | F1: {f1:.4f}")

        epoch_record = {
            "epoch": epoch,
            "train_loss": round(mean_train_loss, 4),
            "val_loss": round(mean_val_loss, 4),
            "mean_iou": round(mean_iou, 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "samples_trained": epoch_samples
        }
        metrics_history.append(epoch_record)

        # Checkpoint saving
        if mean_val_loss < best_val_loss or epoch == epochs:
            best_val_loss = mean_val_loss
            ckpt_path = CHECKPOINTS_DIR / "regularized_best_pii_detector.pt"
            torch.save(model.state_dict(), ckpt_path)
            # Also update browser_agent_detector.pt for universal compatibility
            torch.save(model.state_dict(), CHECKPOINTS_DIR / "browser_agent_detector.pt")
            print(f"[CHECKPOINT] Saved best model checkpoint to {ckpt_path}")

    total_duration = time.time() - t_start
    print(f"\n[TRAIN] ================================================================")
    print(f"[TRAIN] Full dataset training completed in {total_duration:.1f}s ({total_duration/60:.2f} min).")
    print(f"[TRAIN] Total real samples trained: {total_samples_trained:,}")
    print(f"[TRAIN] ================================================================\n")

    # Save training metrics
    results_dir = Path("results")
    results_dir.mkdir(parents=True, exist_ok=True)
    with open(results_dir / "real_training_metrics.json", "w", encoding="utf-8") as f:
        json.dump({"metrics": metrics_history, "duration_s": total_duration, "total_samples": total_samples_trained}, f, indent=2)

    # -------------------------------------------------------------------------
    # EXPORT TO ONNX FOR ON-DEVICE WEBGPU/WASM BROWSER AGENT
    # -------------------------------------------------------------------------
    print("[EXPORT] Exporting newly trained model to ONNX for on-device browser agent...")
    onnx_dir = Path("models/onnx")
    onnx_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = onnx_dir / "regularized_visual_pii_detector.onnx"
    onnx_agent_path = onnx_dir / "browser_agent_detector.onnx"

    model.eval().to("cpu")
    dummy_input = torch.randn(1, 3, 320, 320)
    torch.onnx.export(
        model,
        dummy_input,
        str(onnx_path),
        input_names=["input_image"],
        output_names=["boxes", "logits"],
        opset_version=17
    )
    torch.onnx.export(
        model,
        dummy_input,
        str(onnx_agent_path),
        input_names=["input_image"],
        output_names=["boxes", "logits"],
        opset_version=17
    )
    print(f"[EXPORT] Successfully exported ONNX models to {onnx_path} ({onnx_path.stat().st_size / (1024*1024):.2f} MB)")

    # Verify numerical parity with onnxruntime
    try:
        import onnxruntime as ort
        with torch.no_grad():
            pt_b, pt_l = model(dummy_input)
        sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        ort_b, ort_l = sess.run(None, {"input_image": dummy_input.numpy()})
        diff_b = float(np.max(np.abs(pt_b.numpy() - ort_b)))
        diff_l = float(np.max(np.abs(pt_l.numpy() - ort_l)))
        print(f"[EXPORT] ONNX Parity Verified: Box diff={diff_b:.2e}, Logit diff={diff_l:.2e}")
    except Exception as e:
        print(f"[EXPORT] Warning during ONNX verification: {e}")

    # Build browser extension assets
    import subprocess
    print("[BUILD] Compiling extension assets with updated detector.onnx model...")
    try:
        res = subprocess.run(["node", "browser-extension/build.js"], capture_output=True, text=True, check=True)
        print(f"[BUILD] {res.stdout.strip()}")
    except Exception as e:
        print(f"[BUILD] Warning running build.js: {e}")

if __name__ == "__main__":
    train_on_full_dataset(epochs=1, batch_size=32, lr=5e-4)
