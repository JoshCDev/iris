"""One-off audit of the IRIS rice ONNX vs a PhyToSignal-style training set.

Does not modify models. Writes a vision-audit JSON report to --out.
The dataset root is passed explicitly; there is no developer-path default.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "apps" / "api" / "crop_packs" / "rice" / "model.onnx"
CLASSES = json.loads(
    (ROOT / "apps" / "api" / "crop_packs" / "rice" / "model_classes.json")
    .read_text(encoding="utf-8")
)
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MEAN = np.asarray([0.485, 0.456, 0.406], dtype="float32")
STD = np.asarray([0.229, 0.224, 0.225], dtype="float32")


def list_images(data_root: Path, split: str, cls: str) -> list[Path]:
    folder = data_root / split / cls
    if not folder.is_dir():
        return []
    return sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in EXTS
    )


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def pixel_md5(path: Path, size: int = 64) -> str:
    img = Image.open(path).convert("RGB").resize((size, size))
    return hashlib.md5(np.asarray(img).tobytes()).hexdigest()


def stretch_224(path: Path) -> np.ndarray:
    img = Image.open(path).convert("RGB").resize((224, 224))
    arr = np.asarray(img).astype("float32") / 255.0
    arr = (arr - MEAN) / STD
    return np.transpose(arr, (2, 0, 1))[None, :, :, :]


def eval_crop_224(path: Path) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    w, h = img.size
    scale = 256 / min(w, h)
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    img = img.resize((nw, nh))
    left = max(0, (nw - 224) // 2)
    top = max(0, (nh - 224) // 2)
    img = img.crop((left, top, left + 224, top + 224))
    if img.size != (224, 224):
        img = img.resize((224, 224))
    arr = np.asarray(img).astype("float32") / 255.0
    arr = (arr - MEAN) / STD
    return np.transpose(arr, (2, 0, 1))[None, :, :, :]


def softmax(logits: np.ndarray) -> np.ndarray:
    x = logits - logits.max()
    e = np.exp(x)
    return e / e.sum()


def main(data_root: Path, out: Path) -> None:
    report: dict = {"dataset_root": str(data_root),
                    "dataset_exists": data_root.is_dir()}
    if not data_root.is_dir():
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print("missing dataset", data_root)
        return

    splits = ["train", "val", "test"]
    counts: dict[str, dict[str, int]] = {}
    sizes: list[tuple[int, int]] = []
    hash_to_locs: dict[str, list[str]] = defaultdict(list)
    pix_to_locs: dict[str, list[str]] = defaultdict(list)

    for split in splits:
        for cls in CLASSES:
            files = list_images(data_root, split, cls)
            counts.setdefault(cls, {})[split] = len(files)
            for path in files:
                loc = f"{split}/{cls}/{path.name}"
                hash_to_locs[md5_file(path)].append(loc)
                pix_to_locs[pixel_md5(path)].append(loc)
                if len(sizes) < 400:
                    with Image.open(path) as im:
                        sizes.append(im.size)

    exact_cross = []
    for digest, locs in hash_to_locs.items():
        parts = {loc.split("/", 1)[0] for loc in locs}
        if len(parts) > 1:
            exact_cross.append({"md5": digest, "n": len(locs), "locs": locs[:8]})
    pix_cross = []
    for digest, locs in pix_to_locs.items():
        parts = {loc.split("/", 1)[0] for loc in locs}
        if len(parts) > 1:
            pix_cross.append({"n": len(locs), "locs": locs[:8]})

    uniq_sizes = sorted(set(sizes))
    report["counts"] = counts
    report["n_unique_file_md5"] = len(hash_to_locs)
    report["n_files"] = sum(len(v) for v in hash_to_locs.values())
    report["exact_md5_leaking_across_splits"] = len(exact_cross)
    report["exact_md5_leak_examples"] = exact_cross[:12]
    report["resized64_pixel_leaking_across_splits"] = len(pix_cross)
    report["resized64_leak_examples"] = pix_cross[:12]
    report["sampled_unique_resolutions"] = [
        {"w": w, "h": h} for w, h in uniq_sizes[:30]
    ]
    report["sampled_square_share"] = (
        round(sum(1 for w, h in sizes if w == h) / max(1, len(sizes)), 4)
    )

    import onnxruntime as ort

    sess = ort.InferenceSession(
        str(MODEL), providers=["CPUExecutionProvider"]
    )
    inp = sess.get_inputs()[0].name

    def eval_preprocess(fn, max_per_class: int = 80) -> dict:
        confusion = np.zeros((4, 4), dtype=int)
        n = 0
        disagree_stretch = 0
        t0 = time.time()
        for true_i, cls in enumerate(CLASSES):
            files = list_images(data_root, "test", cls)[:max_per_class]
            for path in files:
                logits = sess.run(None, {inp: fn(path)})[0][0]
                pred = int(np.argmax(logits))
                confusion[true_i, pred] += 1
                n += 1
        acc = float(np.trace(confusion) / max(1, n))
        return {
            "n": n,
            "accuracy": round(acc, 4),
            "seconds": round(time.time() - t0, 2),
            "confusion": confusion.tolist(),
        }

    report["test_subset_stretch_224"] = eval_preprocess(stretch_224)
    report["test_subset_resize256_centercrop224"] = eval_preprocess(eval_crop_224)

    # Same images, count prediction flips between the two serving recipes.
    flips = 0
    n_pair = 0
    for true_i, cls in enumerate(CLASSES):
        for path in list_images(data_root, "test", cls)[:40]:
            a = int(np.argmax(sess.run(None, {inp: stretch_224(path)})[0][0]))
            b = int(np.argmax(sess.run(None, {inp: eval_crop_224(path)})[0][0]))
            n_pair += 1
            if a != b:
                flips += 1
    report["stretch_vs_centercrop_label_flips"] = {
        "n": n_pair,
        "flips": flips,
        "flip_rate": round(flips / max(1, n_pair), 4),
    }

    # IRIS demo photos (real jpg/webp, not svg placeholders).
    pack = ROOT / "apps" / "api" / "crop_packs" / "rice"
    demo = {}
    for name in ["rice-blast-demo.jpg", "rice-blast-demo.webp"]:
        p = pack / name
        if not p.is_file():
            continue
        logits = sess.run(None, {inp: stretch_224(p)})[0][0]
        probs = softmax(logits)
        demo[name] = {
            "pred": CLASSES[int(np.argmax(probs))],
            "confidence": round(float(probs.max()), 4),
            "probs": {CLASSES[i]: round(float(probs[i]), 4) for i in range(4)},
            "size": list(Image.open(p).size),
        }
    report["iris_demo_photos_stretch"] = demo

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in report if k not in (
        "exact_md5_leak_examples", "resized64_leak_examples",
        "sampled_unique_resolutions")}, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Audit IRIS rice ONNX against a processed dataset root")
    ap.add_argument("--dataset-root", type=Path, required=True,
                    help="processed rice dir with train/val/test subfolders")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "experiments" / "outputs" / "vision_audit.json")
    args = ap.parse_args()
    main(args.dataset_root, args.out)
