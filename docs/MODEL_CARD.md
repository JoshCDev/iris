# Model Card - IRIS Rice Leaf Triage Model

| Field | Value |
| --- | --- |
| Model version | `rice-mobilenet-v3-large-v0.3.0-onnx` (`apps/api/crop_packs/rice/metadata.json`) |
| Architecture | MobileNetV3-Large (last 8 feature blocks + classifier trained; exported to ONNX) |
| Runtime | onnxruntime CPU (`CPUExecutionProvider`), single session, graph optimizations enabled |
| Input | 224×224×3 RGB, batch 1, ImageNet normalize after Resize(shorter-side 256) + CenterCrop(224) |
| Output classes (5) | `bacterial_leaf_blight`, `blast`, `brown_spot`, `healthy`, `tungro` |
| Serving stack | image guard → ONNX triage → severity → bilingual advisory → risk-fusion hook |
| Location | `apps/api/crop_packs/rice/model.onnx` (~16.8 MB) |
| SHA-256 | `3ec2717331b3ebc08ef664dbe2f391be9df6b05222778e2c85fe3debdf746771` |
| Redistribution status | **Unresolved** — derived from mixed-source training data (see Training data provenance and `THIRD_PARTY_NOTICES.md`); do not redistribute the weight file until rights are recorded |

## Intended use

**AI-assisted triage of rice leaf photos** - a prioritization and awareness aid
for farmers/extension workers: which of the four major rice diseases the lesion
pattern most resembles (or whether the leaf looks healthy), how urgent review is,
and what field check to do next. It runs on-device-class CPU hardware as part of
the IRIS web app (`POST /api/vision/predict`) and feeds the assistant's
`run_vision_triage` tool.

### Unacceptable uses

- Autonomous disease diagnosis or treatment decisions without human review.
- Pesticide product or dose recommendation.
- Yield-loss or severity grading beyond the documented Urgent/Review bands.
- Use on non-rice crops or on images that fail the quality guard.
- Redistribution of the weight file without recorded permission.

## Out-of-scope / not a diagnosis

- **Not a laboratory diagnosis.** Standing disclaimer on every result:
  *"AI-assisted triage - bukan diagnosis laboratorium."*
- **No pesticide decisions.** The system never recommends dosages or products;
  treatment decisions belong to the farmer with the *penyuluh* (extension officer).
- Not validated for yield-loss prediction, severity grading beyond the coarse
  Urgent/Review bands, or non-rice crops (chili/tomato packs exist in storage
  but are disabled).

## Training data provenance (public datasets)

- **Mendeley** "Rice Leaf Disease Image Samples"
  <https://data.mendeley.com/datasets/fwcj7stb8r/1> - four disease classes,
  deduplicated by file MD5 before split (the v0.2 split leaked 243/893 test
  files as exact copies of train).
- **Paddy Doctor** (Hugging Face `Project-AgML/paddy_disease_classification`) -
  field photos; class `normal` mapped to `healthy`. Not Indonesian fields.
- **Splits** (unique images, 70/15/15, seed 42; `crop_packs/rice/training_metrics.json`):

| Class | Train | Val | Test |
| --- | --- | --- | --- |
| bacterial_leaf_blight | 1257 | 269 | 271 |
| blast | 1881 | 403 | 404 |
| brown_spot | 1507 | 322 | 324 |
| healthy | 1224 | 262 | 263 |
| tungro | 1671 | 358 | 359 |
| **Total** | **7540** | **1614** | **1621** |

- Best epoch recorded: 24 (`training_metrics.json`). Device: CUDA (RTX 3060).

## Evaluation status - honesty first

Held-out **test** metrics from the PyTorch checkpoint (same recipe as serving):

| Metric | Value |
| --- | --- |
| Accuracy | **0.9784** |
| Macro-F1 | **0.9783** |
| n | 1621 unique images |

Per-class recall on that test split:

| Class | Support | Correct | Recall |
| --- | --- | --- | --- |
| bacterial_leaf_blight | 271 | 265 | 0.9779 |
| blast | 404 | 394 | 0.9752 |
| brown_spot | 324 | 312 | 0.9630 |
| healthy | 263 | 261 | 0.9924 |
| tungro | 359 | 354 | 0.9861 |

v0.2 quoted 100% val/test because exact duplicates crossed splits and the
backbone was frozen. That number is **not** comparable. v0.3 is still a
public-dataset result: it is not Indonesian field certification.

## Preprocessing (must match training)

Implemented in `app/vision/preprocess.py` and used by
`OnnxInferenceAdapter._run_session`:

1. Decode bytes → PIL → **RGB**
2. Resize shorter side to **256** (keep aspect)
3. **Center crop** to **224×224**
4. Scale to `[0,1]` (`/255`)
5. Normalize with **ImageNet mean/std** (mean 0.485/0.456/0.406, std 0.229/0.224/0.225)
6. CHW transpose + batch dim of 1 → softmax over **5** logits

Confidence gating adds an OOD layer on top: low-confidence rejections,
logit-spread and softmax-entropy uniformity checks (max entropy log2(5) ≈ 2.32
bits) combined with guard heuristics (plant-like ratio, green dominance,
blob coherence). Healthy is a **model class** in v0.3; the old heuristic
synthesis only runs if a pack has no `healthy` output.

## Integration notes

- **Image guard rejection paths (deterministic, before the model):**
  unreadable/too-small files, blank-or-solid images, non-leaf/non-plant images
  (multi-tier plant-mask checks incl. green-dominance gate with coherent
  diseased-leaf exception), scattered-foliage shots (lawns) → all return
  `422 {"code": "image_rejected", ...}` with retry guidance. Judge photos take
  the identical live path - no demo shortcut exists.
- **Low-confidence honesty path:** when the model's top class fails the OOD
  gates → `422 {"code": "low_confidence", detail}` naming the confidence and
  class, instead of guessing.
- **Fusion hook:** after triage, if `plot_id` is supplied, the predicted class
  joins AWD hydrology state (level band / flowering lock) and wet-weather flag
  in `app/fusion/risk.py::assess()` → `{risk_level, drivers_id[], drivers_en[],
  irrigation_note?}` shown as the UI fusion banner and persisted in
  `vision_reports.fusion_json`. Predicted `healthy` is mapped to disease=`none`
  for fusion.
- **Assistant tool:** `run_vision_triage(image_ref)` wraps the same services;
  without the vision module it answers honestly: *"vision belum siap"*.

## Limitations

1. **Public-data domain gap.** Mendeley studio crops plus Paddy Doctor photos
   from India; lighting, variety, growth stage, and camera behavior in
   Indonesian fields differ. Field validation pending (next milestone with an
   agri partner).
2. **Healthy class is not local.** It comes from Paddy Doctor `normal`, not
   from Indonesian healthy-leaf collection.
3. **Near-duplicates may remain.** Exact MD5 copies were removed before split;
   similar JPEGs of the same leaf can still leak a little skill.
4. **Symptom overlap:** brown spot vs nutrient deficiency vs blast lesions can
   be visually confusable; the model reports resemblance, not causation.
5. **Single-leaf close-ups only** by design (guard rejects lawns/scenes);
   wide-angle field scouting is out of scope for v1.
6. English/Indonesian advisories are cautious guidance strings authored from
   IRRI fact sheets and the national OPT forecast - reviewed, but not a
   substitute for local extension advice.
