# Model Card - IRIS Rice Leaf Triage Model

| Field | Value |
| --- | --- |
| Model version | `rice-mobilenet-v3-large-v0.2.0-onnx` (`apps/api/crop_packs/rice/metadata.json`) |
| Architecture | MobileNetV3-Large (classifier head exported to ONNX) |
| Runtime | onnxruntime CPU (`CPUExecutionProvider`), single session, graph optimizations enabled |
| Input | 224×224×3 RGB, batch 1 |
| Output classes (4) | `bacterial_leaf_blight`, `blast`, `brown_spot`, `tungro` |
| Serving stack | image guard → ONNX triage → severity → bilingual advisory → risk-fusion hook |
| Location | `apps/api/crop_packs/rice/model.onnx` |

## Intended use

**AI-assisted triage of rice leaf photos** - a prioritization and awareness aid
for farmers/extension workers: which of the four major rice diseases the lesion
pattern most resembles, how urgent review is, and what field check to do next.
It runs on-device-class CPU hardware as part of the IRIS web app
(`POST /api/vision/predict`) and feeds the assistant's `run_vision_triage` tool.

## Out-of-scope / not a diagnosis

- **Not a laboratory diagnosis.** Standing disclaimer on every result:
  *"AI-assisted triage - bukan diagnosis laboratorium."*
- **No pesticide decisions.** The system never recommends dosages or products;
  treatment decisions belong to the farmer with the *penyuluh* (extension officer).
- Not validated for yield-loss prediction, severity grading beyond the coarse
  Urgent/Review bands, or non-rice crops (chili/tomato packs exist in storage
  but are disabled).

## Training data provenance (public datasets)

- **Source:** "Rice Leaf Disease Image Samples" - Mendeley Data,
  <https://data.mendeley.com/datasets/fwcj7stb8r/1> (public dataset; no field
  data from our own trials).
- **Splits** (from `crop_packs/rice/training_metrics.json`, identical copy at
  `C:\xampp\htdocs\phytosignal\models\rice\metrics.json`):

| Class | Train | Val | Test |
| --- | --- | --- | --- |
| bacterial_leaf_blight | 1108 | 237 | 239 |
| blast | 1007 | 216 | 217 |
| brown_spot | 1120 | 240 | 240 |
| tungro | 915 | 196 | 197 |
| **Total** | **4150** | **889** | **893** |

- Best epoch recorded: 5 (`training_metrics.json`).

## Evaluation status - honesty first

- **Test-split metrics:** **held-out evaluation in progress.** The metrics
  files record split counts for the test set but no completed test-split
  accuracy/F1 yet. We will publish per-class + macro-F1 on the held-out test
  split when the evaluation run finishes - and nothing better than that number.
- **We deliberately do NOT quote 100%.** `best_val_accuracy = 1.00`,
  `best_macro_f1 = 1.00` on this public dataset is a classic leakage/
  near-duplicate red flag (near-identical images across splits), not evidence
  of field performance. We disclose it rather than print it.
- For context only, the shipped v0.2.0 checkpoint's earlier training note in
  `metadata.json` records validation accuracy 0.9055 / macro-F1 0.9036 on the
  same data regime - also validation-only, not a field claim.

## Preprocessing (must match training parity)

Implemented verbatim in `app/vision/inference.py::OnnxInferenceAdapter._run_session`:

1. Decode bytes → PIL → **RGB**
2. Plain resize to **224×224** (no center-crop)
3. Scale to `[0,1]` (`/255`)
4. Normalize with **ImageNet mean/std** (mean 0.485/0.456/0.406, std 0.229/0.224/0.225)
5. CHW transpose + batch dim of 1 → softmax over 4 logits

Confidence gating adds an OOD layer on top: low-confidence rejections,
logit-spread and softmax-entropy uniformity checks (max entropy 2.0 bits for
4 classes) combined with guard heuristics (plant-like ratio, green dominance,
blob coherence). Healthy-leaf synthesis exists for clean leaves because the
dataset contains no healthy class.

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
  `vision_reports.fusion_json`.
- **Assistant tool:** `run_vision_triage(image_ref)` wraps the same services;
  without the vision module it answers honestly: *"vision belum siap"*.

## Limitations

1. **Public-data domain gap.** Trained only on the Mendeley sample set; lighting,
   variety, growth stage, and camera behavior in Indonesian fields differ.
   Field validation pending (next milestone with an agri partner).
2. **Leakage caveat on perfect val scores** - see Evaluation status above.
3. **No healthy class in the source dataset**; "healthy" outputs are heuristic
   syntheses, clearly gated.
4. **Symptom overlap:** brown spot vs nutrient deficiency vs blast lesions can
   be visually confusable; the model reports resemblance, not causation.
5. **Single-leaf close-ups only** by design (guard rejects lawns/scenes);
   wide-angle field scouting is out of scope for v1.
6. English/Indonesian advisories are cautious guidance strings authored from
   IRRI fact sheets and the national OPT forecast - reviewed, but not a
   substitute for local extension advice.
