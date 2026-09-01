"""Held-out test-split evaluation for the IRIS rice vision model.

Runs the production ONNX model (apps/api/crop_packs/rice/model.onnx) over the
prepared rice_v03 test split using the EXACT preprocessing of
app/vision/preprocess.py (Resize shorter-side 256 + CenterCrop 224).

Writes a vision-test-metrics JSON to --out and prints a summary.

Example:
  python apps/api/scripts/eval_vision_test.py \\
      --test-root experiments/data/rice_v03/test \\
      --model apps/api/crop_packs/rice/model.onnx \\
      --classes apps/api/crop_packs/rice/model_classes.json \\
      --out experiments/outputs/vision_test_metrics.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))
from app.vision.preprocess import pil_to_nchw

REPO_ROOT = Path(__file__).resolve().parents[3]


def preprocess(path: Path):
    return pil_to_nchw(Image.open(path).convert("RGB"))


def main(test_root: Path, model: Path, classes_path: Path, out: Path) -> None:
    if not test_root.is_dir():
        raise SystemExit(
            f"test root not found: {test_root}\n"
            "Pass --test-root pointing at the prepared held-out test split.")
    if not model.is_file():
        raise SystemExit(f"model not found: {model}")
    if not classes_path.is_file():
        raise SystemExit(f"classes file not found: {classes_path}")

    classes = json.loads(classes_path.read_text(encoding="utf-8"))
    idx_to_class = dict(enumerate(classes))
    sess_opts = ort.SessionOptions()
    sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session = ort.InferenceSession(str(model), sess_options=sess_opts,
                                   providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name

    confusion = np.zeros((len(classes), len(classes)), dtype=int)
    confidences: list[float] = []
    per_class_total = Counter()
    per_class_correct = Counter()
    n = 0
    t0 = time.time()
    latencies: list[float] = []

    for true_idx, cls in enumerate(classes):
        folder = test_root / cls
        files = sorted(p for p in folder.iterdir()
                       if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
        per_class_total[cls] = len(files)
        for f in files:
            arr = preprocess(f)
            t1 = time.time()
            logits = session.run(None, {input_name: arr})[0][0]
            latencies.append(time.time() - t1)
            pred_idx = int(np.argmax(logits))
            probs = np.exp(logits - logits.max())
            probs = probs / probs.sum()
            confidences.append(float(probs[pred_idx]))
            confusion[true_idx][pred_idx] += 1
            per_class_correct[cls] += int(pred_idx == true_idx)
            n += 1
            if n % 100 == 0:
                print(f"  {n} images...", flush=True)

    per_class = {}
    f1s = []
    for i, cls in enumerate(classes):
        tp = confusion[i][i]
        fp = confusion[:, i].sum() - tp
        fn = confusion[i, :].sum() - tp
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        f1s.append(f1)
        per_class[cls] = {
            "support": int(per_class_total[cls]),
            "correct": int(per_class_correct[cls]),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    accuracy = float(confusion.trace()) / n
    macro_f1 = float(sum(f1s)) / len(f1s)
    avg_conf = float(sum(confidences) / len(confidences))
    avg_lat = float(sum(latencies) / len(latencies)) * 1000

    result = {
        "evaluated_at": time.strftime("%Y-%m-%d"),
        "dataset": "rice_v03 held-out test split (MD5-deduped Mendeley + "
                   "Paddy Doctor; experiments/data/rice_v03/test; no test "
                   "augmentation)",
        "model": "MobileNetV3-Large ONNX v0.3 (crop_packs/rice/model.onnx)",
        "n_images": n,
        "overall_accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "mean_confidence_when_correct": round(avg_conf, 4),
        "avg_latency_ms_cpu": round(avg_lat, 1),
        "per_class": per_class,
        "confusion_matrix_rows_true_cols_pred": {
            cls: [int(v) for v in confusion[i]] for i, cls in enumerate(classes)
        },
        "provenance_caveat": "Test images originate from the same public dataset "
                            "used for training (pipeline-separated split). "
                            "Independent field validation with Indonesian leaves "
                            "is the next milestone.",
    }
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("confusion_matrix_rows_true_cols_pred",)},
                     indent=2))
    print("confusion (rows=true, cols=pred):")
    print("            " + "  ".join(f"{c[:9]:>9}" for c in classes))
    for i, cls in enumerate(classes):
        print(f"{cls[:11]:>11}  " + "  ".join(f"{int(v):>9}" for v in confusion[i]))
    print(f"total: {n} images in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Evaluate the IRIS rice ONNX model on a held-out test split")
    ap.add_argument("--test-root", type=Path, required=True,
                    help="held-out test split dir (class subfolders)")
    ap.add_argument("--model", type=Path,
                    default=REPO_ROOT / "apps" / "api" / "crop_packs" / "rice" / "model.onnx")
    ap.add_argument("--classes", type=Path,
                    default=REPO_ROOT / "apps" / "api" / "crop_packs" / "rice" / "model_classes.json")
    ap.add_argument("--out", type=Path,
                    default=REPO_ROOT / "experiments" / "outputs" / "vision_test_metrics.json")
    args = ap.parse_args()
    main(args.test_root, args.model, args.classes, args.out)
