"""Rice v0.3: deduped Mendeley + Paddy Doctor field photos, unfrozen last blocks.

Subcommands: prepare | train | export

Uses the mango-ml CUDA venv if invoked with that interpreter:
  C:\\xampp\\htdocs\\mango_detector\\mango-ml\\.venv\\Scripts\\python.exe experiments\\train_rice_v03.py prepare
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PHYTO = Path(r"C:\xampp\htdocs\phytosignal")
MENDELEY = PHYTO / "data" / "processed" / "rice"
DATA = ROOT / "experiments" / "data"
PADDY_RAW = DATA / "paddy_hf"
SPLITS = DATA / "rice_v03"
CKPT_DIR = ROOT / "experiments" / "outputs" / "rice_v03"
PACK = ROOT / "apps" / "api" / "crop_packs" / "rice"

CLASSES = [
    "bacterial_leaf_blight",
    "blast",
    "brown_spot",
    "healthy",
    "tungro",
]
PADDY_MAP = {
    "bacterial_leaf_blight": "bacterial_leaf_blight",
    "blast": "blast",
    "brown_spot": "brown_spot",
    "tungro": "tungro",
    "normal": "healthy",
}
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
HF_ID = "Project-AgML/paddy_disease_classification"


def _md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _md5_file(path: Path) -> str:
    return _md5_bytes(path.read_bytes())


def _iter_images(root: Path):
    if not root.is_dir():
        return
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in EXTS:
            yield path


def cmd_prepare(seed: int = 42) -> None:
    import os
    os.environ.setdefault("HF_HOME", str(DATA / "hf_cache"))
    PADDY_RAW.mkdir(parents=True, exist_ok=True)
    paddy_images = PADDY_RAW / "images"
    if not any(_iter_images(paddy_images)):
        print("downloading Paddy Doctor from Hugging Face ...", flush=True)
        from datasets import load_dataset

        ds = load_dataset(HF_ID, split="train")
        names = ds.features["label"].names
        kept = 0
        for i, row in enumerate(ds):
            src = names[int(row["label"])]
            dest_cls = PADDY_MAP.get(src)
            if dest_cls is None:
                continue
            folder = paddy_images / dest_cls
            folder.mkdir(parents=True, exist_ok=True)
            img = row["image"].convert("RGB")
            out = folder / f"paddy_{i:05d}.jpg"
            img.save(out, format="JPEG", quality=92)
            kept += 1
            if kept % 500 == 0:
                print(f"  saved {kept} mapped paddy images", flush=True)
        print(f"saved {kept} paddy images -> {paddy_images}", flush=True)
        del ds

    records: dict[str, dict[str, Path | str]] = {}
    for cls in ("bacterial_leaf_blight", "blast", "brown_spot", "tungro"):
        for split in ("train", "val", "test"):
            folder = MENDELEY / split / cls
            for path in _iter_images(folder):
                digest = _md5_file(path)
                if digest not in records:
                    records[digest] = {
                        "path": path, "class": cls, "source": "mendeley",
                    }
    for cls in CLASSES:
        for path in _iter_images(paddy_images / cls):
            digest = _md5_file(path)
            if digest not in records:
                records[digest] = {
                    "path": path, "class": cls, "source": "paddy",
                }

    by_class: dict[str, list[dict]] = defaultdict(list)
    for rec in records.values():
        by_class[str(rec["class"])].append(rec)

    rng = random.Random(seed)
    if SPLITS.exists():
        shutil.rmtree(SPLITS)
    manifest = []
    counts: dict[str, dict[str, int]] = {}
    for cls in CLASSES:
        items = by_class.get(cls, [])
        rng.shuffle(items)
        n = len(items)
        n_train = max(1, int(n * 0.70)) if n else 0
        n_val = max(1, int(n * 0.15)) if n >= 3 else 0
        splits = {
            "train": items[:n_train],
            "val": items[n_train:n_train + n_val],
            "test": items[n_train + n_val:],
        }
        counts[cls] = {k: len(v) for k, v in splits.items()}
        for split, rows in splits.items():
            dest_dir = SPLITS / split / cls
            dest_dir.mkdir(parents=True, exist_ok=True)
            for i, rec in enumerate(rows, start=1):
                src = Path(rec["path"])
                dest = dest_dir / f"{rec['source']}_{src.stem[:60]}_{i:05d}{src.suffix.lower()}"
                try:
                    dest.hardlink_to(src)
                except OSError:
                    shutil.copy2(src, dest)
                manifest.append({
                    "split": split, "class": cls, "source": rec["source"],
                    "path": str(dest.relative_to(SPLITS)),
                })
    SPLITS.mkdir(parents=True, exist_ok=True)
    (SPLITS / "counts.json").write_text(json.dumps(counts, indent=2), encoding="utf-8")
    (SPLITS / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    print(json.dumps(counts, indent=2))
    print(f"unique images {len(records)} -> {SPLITS}")


def _confusion_f1(preds: list[int], targets: list[int], n_cls: int):
    matrix = [[0] * n_cls for _ in range(n_cls)]
    for t, p in zip(targets, preds):
        matrix[t][p] += 1
    f1s = []
    for i in range(n_cls):
        tp = matrix[i][i]
        fp = sum(matrix[r][i] for r in range(n_cls) if r != i)
        fn = sum(matrix[i][c] for c in range(n_cls) if c != i)
        prec = tp / max(1, tp + fp)
        rec = tp / max(1, tp + fn)
        f1s.append(0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec))
    acc = sum(1 for t, p in zip(targets, preds) if t == p) / max(1, len(targets))
    return matrix, acc, sum(f1s) / n_cls


def cmd_train(epochs: int, batch_size: int, patience: int, seed: int) -> None:
    if not (SPLITS / "train").is_dir():
        raise SystemExit("run prepare first")
    import torch
    import torchvision.transforms as T
    from torch import nn
    from torch.utils.data import DataLoader, WeightedRandomSampler
    from torchvision import datasets, models

    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    train_tfms = T.Compose([
        T.RandomResizedCrop(224, scale=(0.6, 1.0)),
        T.RandomHorizontalFlip(),
        T.RandomVerticalFlip(p=0.15),
        T.RandomRotation(18),
        T.ColorJitter(0.25, 0.25, 0.2, 0.05),
        T.ToTensor(),
        T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        T.RandomErasing(p=0.25, scale=(0.02, 0.12)),
    ])
    eval_tfms = T.Compose([
        T.Resize(256),
        T.CenterCrop(224),
        T.ToTensor(),
        T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    train_ds = datasets.ImageFolder(SPLITS / "train", transform=train_tfms)
    val_ds = datasets.ImageFolder(SPLITS / "val", transform=eval_tfms)
    if list(train_ds.classes) != CLASSES:
        raise SystemExit(f"class order {train_ds.classes} != {CLASSES}")

    counts = Counter(train_ds.targets)
    weights = [1.0 / counts[y] for y in train_ds.targets]
    sampler = WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)
    train_loader = DataLoader(
        train_ds, batch_size=batch_size, sampler=sampler,
        num_workers=0, pin_memory=True,
    )
    val_loader = DataLoader(
        val_ds, batch_size=batch_size, shuffle=False,
        num_workers=0, pin_memory=True,
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device} n_train={len(train_ds)} n_val={len(val_ds)}", flush=True)

    model = models.mobilenet_v3_large(weights=models.MobileNet_V3_Large_Weights.DEFAULT)
    model.classifier[3] = nn.Linear(model.classifier[3].in_features, len(CLASSES))
    for param in model.parameters():
        param.requires_grad = False
    for param in model.features[-8:].parameters():
        param.requires_grad = True
    for param in model.classifier.parameters():
        param.requires_grad = True
    model.to(device)

    backbone_params = [p for p in model.features[-8:].parameters() if p.requires_grad]
    head_params = [p for p in model.classifier.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(
        [
            {"params": backbone_params, "lr": 3e-5},
            {"params": head_params, "lr": 3e-4},
        ],
        weight_decay=1e-4,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.08)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    mixup_alpha = 0.2

    CKPT_DIR.mkdir(parents=True, exist_ok=True)
    best_f1 = -1.0
    best_epoch = 0
    history = []

    def mixup(inputs, targets):
        if mixup_alpha <= 0:
            return inputs, targets, None
        lam = float(torch.distributions.Beta(mixup_alpha, mixup_alpha).sample())
        index = torch.randperm(inputs.size(0), device=inputs.device)
        mixed = lam * inputs + (1 - lam) * inputs[index]
        return mixed, targets, (targets[index], lam)

    for epoch in range(1, epochs + 1):
        model.train()
        running = 0.0
        n_seen = 0
        for inputs, targets in train_loader:
            inputs = inputs.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)
            inputs, targets_a, extra = mixup(inputs, targets)
            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast("cuda", enabled=device.type == "cuda"):
                logits = model(inputs)
                if extra is None:
                    loss = criterion(logits, targets_a)
                else:
                    targets_b, lam = extra
                    loss = lam * criterion(logits, targets_a) + (1 - lam) * criterion(logits, targets_b)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            running += float(loss.item()) * targets.size(0)
            n_seen += targets.size(0)
        scheduler.step()

        model.eval()
        preds_all: list[int] = []
        t_all: list[int] = []
        with torch.no_grad():
            for inputs, targets in val_loader:
                inputs = inputs.to(device, non_blocking=True)
                logits = model(inputs)
                preds_all.extend(logits.argmax(1).cpu().tolist())
                t_all.extend(targets.tolist())
        matrix, acc, macro_f1 = _confusion_f1(preds_all, t_all, len(CLASSES))
        train_loss = running / max(1, n_seen)
        row = {"epoch": epoch, "train_loss": round(train_loss, 4),
               "val_acc": round(acc, 4), "val_macro_f1": round(macro_f1, 4)}
        history.append(row)
        print(row, flush=True)
        if macro_f1 > best_f1:
            best_f1 = macro_f1
            best_epoch = epoch
            torch.save({
                "model": model.state_dict(),
                "classes": train_ds.classes,
                "architecture": "mobilenet_v3_large",
                "input_size": [224, 224],
                "normalization": "imagenet",
                "preprocess": "resize256_centercrop224",
                "epoch": epoch,
                "val_acc": acc,
                "val_macro_f1": macro_f1,
                "confusion": matrix,
            }, CKPT_DIR / "best.pt")
        elif epoch - best_epoch >= patience:
            print(f"early_stop epoch={epoch} best_epoch={best_epoch}", flush=True)
            break

    # Held-out test with best checkpoint
    blob = torch.load(CKPT_DIR / "best.pt", map_location="cpu", weights_only=False)
    model.load_state_dict(blob["model"])
    model.to(device).eval()
    test_ds = datasets.ImageFolder(SPLITS / "test", transform=eval_tfms)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=0)
    preds_all, t_all = [], []
    with torch.no_grad():
        for inputs, targets in test_loader:
            logits = model(inputs.to(device))
            preds_all.extend(logits.argmax(1).cpu().tolist())
            t_all.extend(targets.tolist())
    matrix, acc, macro_f1 = _confusion_f1(preds_all, t_all, len(CLASSES))
    per_class = {}
    for i, cls in enumerate(CLASSES):
        tp = matrix[i][i]
        support = sum(matrix[i])
        per_class[cls] = {
            "support": support,
            "correct": tp,
            "recall": round(tp / max(1, support), 4),
        }
    metrics = {
        "crop": "rice",
        "version": "rice-mobilenet-v3-large-v0.3.0-onnx",
        "architecture": "mobilenet_v3_large",
        "device": str(device),
        "classes": CLASSES,
        "class_to_idx": train_ds.class_to_idx,
        "split_counts": json.loads((SPLITS / "counts.json").read_text(encoding="utf-8")),
        "best_epoch": best_epoch,
        "best_val_accuracy": blob["val_acc"],
        "best_macro_f1": blob["val_macro_f1"],
        "test_accuracy": acc,
        "test_macro_f1": macro_f1,
        "test_confusion": matrix,
        "test_per_class": per_class,
        "history": history,
        "sources": ["mendeley-fwcj7stb8r-deduped", "paddy-doctor-huggingface"],
        "notes": [
            "Duplicates removed by MD5 before split.",
            "Paddy Doctor normal class mapped to healthy.",
            "Last 8 MobileNetV3 feature blocks unfrozen.",
            "Serving preprocess is Resize(256)+CenterCrop(224).",
        ],
    }
    CKPT_DIR.mkdir(parents=True, exist_ok=True)
    (CKPT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print("TEST", {"acc": round(acc, 4), "macro_f1": round(macro_f1, 4)})
    print(f"wrote {CKPT_DIR / 'metrics.json'}")


def cmd_export() -> None:
    import torch
    from torch import nn
    from torchvision import models

    ckpt = CKPT_DIR / "best.pt"
    blob = torch.load(ckpt, map_location="cpu", weights_only=False)
    classes = list(blob["classes"])
    model = models.mobilenet_v3_large(weights=None)
    model.classifier[3] = nn.Linear(model.classifier[3].in_features, len(classes))
    model.load_state_dict(blob["model"])
    model.eval()
    onnx_path = CKPT_DIR / "model.onnx"
    dummy = torch.randn(1, 3, 224, 224)
    # dynamo=False: Torch 2.12 default exporter prints a checkmark that
    # crashes cp1252 consoles, and the legacy graph is what onnxruntime-cpu
    # already serves for this pack.
    torch.onnx.export(
        model, dummy, str(onnx_path),
        input_names=["image"], output_names=["logits"],
        opset_version=17,
        dynamo=False,
    )
    shutil.copy2(onnx_path, PACK / "model.onnx")
    (PACK / "model_classes.json").write_text(
        json.dumps(classes, indent=2), encoding="utf-8")
    metrics_src = CKPT_DIR / "metrics.json"
    if metrics_src.exists():
        shutil.copy2(metrics_src, PACK / "training_metrics.json")
        metrics = json.loads(metrics_src.read_text(encoding="utf-8"))
    else:
        metrics = {}
    meta_path = PACK / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["model_version"] = metrics.get("version", "rice-mobilenet-v3-large-v0.3.0-onnx")
    meta["normalization"] = "imagenet"
    meta["input_size"] = [224, 224]
    meta["dataset_sources"] = [
        "https://data.mendeley.com/datasets/fwcj7stb8r/1",
        "https://huggingface.co/datasets/Project-AgML/paddy_disease_classification",
    ]
    test_acc = metrics.get("test_accuracy")
    test_f1 = metrics.get("test_macro_f1")
    if test_acc is not None:
        meta["validation_notes"] = (
            f"v0.3 deduped Mendeley + Paddy Doctor field photos. "
            f"Held-out test accuracy {test_acc:.4f}, macro F1 {test_f1:.4f}. "
            f"Not Indonesian field-certified."
        )
    meta["limitations"] = [
        "Healthy class comes from Paddy Doctor (India), not Indonesian fields",
        "Mendeley studio photos and Paddy Doctor field photos remain domain-shifted from many phone snapshots",
        "Symptoms may overlap with nutrient stress or pest damage",
        "Low-confidence results must be reviewed by an expert",
    ]
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"exported {onnx_path} -> {PACK / 'model.onnx'}")
    print(f"classes {classes}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_prep = sub.add_parser("prepare")
    p_prep.add_argument("--seed", type=int, default=42)
    p_tr = sub.add_parser("train")
    p_tr.add_argument("--epochs", type=int, default=25)
    p_tr.add_argument("--batch-size", type=int, default=32)
    p_tr.add_argument("--patience", type=int, default=8)
    p_tr.add_argument("--seed", type=int, default=42)
    sub.add_parser("export")
    args = parser.parse_args()
    if args.cmd == "prepare":
        cmd_prepare(seed=args.seed)
    elif args.cmd == "train":
        cmd_train(args.epochs, args.batch_size, args.patience, args.seed)
    else:
        cmd_export()


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "apps" / "api"))
    main()
