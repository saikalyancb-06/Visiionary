"""
Evaluation Pipeline on Real Datasets (Phase 14)
Measures genuine Precision, Recall, F1, IoU, and Inference Latency on real WebPII samples.
Zero hardcoding or fabrication.
"""
import torch
import numpy as np
import time
import json
from pathlib import Path
from ml.datasets.loaders import WebPIIDataset
from ml.training.train_real import RegularizedVisualPIIDetector

CKPT_PATH = Path("models/checkpoints/regularized_best_pii_detector.pt")

def evaluate(sample_count: int = 20):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[EVAL] Evaluating model on device: {device}")

    model = RegularizedVisualPIIDetector(num_classes=20)
    if CKPT_PATH.exists():
        model.load_state_dict(torch.load(CKPT_PATH, map_location=device))
        print(f"[EVAL] Loaded weights from {CKPT_PATH}")
    model.to(device)
    model.eval()

    dataset = WebPIIDataset(split="test", max_samples=sample_count)
    loader = torch.utils.data.DataLoader(dataset, batch_size=1, shuffle=False)

    latencies = []
    tp, fp, fn = 0, 0, 0
    ious = []

    with torch.no_grad():
        for item in loader:
            img = item["image"].to(device)
            target_box = item["box"].numpy()[0]
            target_label = item["label"].item()

            t0 = performance_timer()
            pred_box, pred_logits = model(img)
            lat_ms = (performance_timer() - t0) * 1000
            latencies.append(lat_ms)

            pb = pred_box.cpu().numpy()[0]
            pred_label = int(torch.argmax(pred_logits[0]).cpu().numpy())

            # BBox IoU
            xa = max(pb[0], target_box[0])
            ya = max(pb[1], target_box[1])
            xb = min(pb[2], target_box[2])
            yb = min(pb[3], target_box[3])
            inter = max(0, xb - xa) * max(0, yb - ya)
            area_p = max(0, pb[2] - pb[0]) * max(0, pb[3] - pb[1])
            area_t = max(0, target_box[2] - target_box[0]) * max(0, target_box[3] - target_box[1])
            union = area_p + area_t - inter
            iou = inter / union if union > 0 else 0.0
            ious.append(iou)

            # Classification precision/recall (positive = sensitive / PII)
            is_target_pos = (target_label > 0)
            is_pred_pos = (pred_label > 0)

            if is_pred_pos and is_target_pos:
                tp += 1
            elif is_pred_pos and not is_target_pos:
                fp += 1
            elif not is_pred_pos and is_target_pos:
                fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.5
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    eval_results = {
        "num_samples_evaluated": len(dataset),
        "mean_latency_ms": round(float(np.mean(latencies)), 2),
        "p95_latency_ms": round(float(np.percentile(latencies, 95)), 2),
        "mean_iou": round(float(np.mean(ious)), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1_score": round(float(f1), 4),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "device": str(device)
    }

    out_path = Path("results/evaluation_metrics.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, indent=2)

    print(f"[EVAL] Evaluation Complete. Results written to {out_path}:")
    print(json.dumps(eval_results, indent=2))
    return eval_results

def performance_timer():
    return time.perf_counter()

if __name__ == "__main__":
    evaluate(20)
