# Third-party data and media notices

This file records provenance separately from the IRIS project license. Each
third-party item remains subject to its original terms.

## Training and evaluation datasets

### Rice Leaf Disease Image Samples

- Creator: P. K. Sethy
- Dataset DOI: <https://doi.org/10.17632/fwcj7stb8r.1>
- License shown by Mendeley Data: CC BY 4.0
- Use in IRIS: four disease classes used during model training and evaluation;
  raw images are not committed.

### Paddy Doctor

- Paper: <https://doi.org/10.1145/3570991.3570994>
- Public mirror used by the training script:
  <https://huggingface.co/datasets/Project-AgML/paddy_disease_classification>
- Use in IRIS: overlapping disease classes and `normal` mapped to `healthy`.
- License status: the public mirror's dataset card does not state a license as
  of 31 August 2026. Public access is not proof of permission to redistribute
  the images or derived model. Confirm the original dataset terms before
  relicensing or redistributing `model.onnx`.

## Committed evaluation photographs

### Rice blast demonstration photograph and derived copies

The current repository contains a rice-blast demonstration image and derived
copies used by tests and the local demo. Its original source is not recorded in
the repository. Replace it with a traceable project-owned or openly licensed
image before redistribution, and record author, source, license, and changes.

Paths: `apps/api/crop_packs/rice/rice-blast-demo.jpg`,
`apps/api/crop_packs/rice/rice-blast-demo.svg`,
`apps/api/crop_packs/rice/rice-blast-demo.webp`,
`apps/web/public/demo_samples/rice/rice-blast-demo.jpg`,
`apps/web/public/demo_samples/rice/rice-blast-demo.svg`,
`apps/web/public/demo_samples/rice/rice-blast-demo.webp`.

### Derived ONNX model weights

`apps/api/crop_packs/rice/model.onnx` (MobileNetV3-Large, ~16.8 MB) is derived
from the Sethy and Paddy Doctor training sets above. Because Paddy Doctor's
reuse terms are unresolved, the redistribution status of the derived weights is
unresolved. This asset must not be covered by a project-wide license and must
be withheld or replaced unless the owner records adequate permission.

### Bacterial leaf-blight spot-check image

Path: `experiments/data/field_spotcheck/bacterial_leaf_blight/bacterial_leaf_blight_1.jpg`.

- Work: `Xanthomonas-disease.jpg`
- Authors: An SQ, Potnis N, Dow M, Vorholter FJ, He YQ, Becker A, Teper D,
  Li Y, Wang N, Bleris L, and Tang JL
- Source: <https://commons.wikimedia.org/wiki/File:Xanthomonas-disease.jpg>
- License: CC BY 4.0
- Changes: the committed copy is resized. The source is a composite; rice
  bacterial-blight examples are panels vii-viii.

### Brown-spot spot-check image

Path: `experiments/data/field_spotcheck/brown_spot/brown_spot_1.jpg`.

- Work: `Cochliobolus miyabeanus.jpg`
- Photographer: Donald Groth, Louisiana State University AgCenter,
  Bugwood.org
- Source: <https://commons.wikimedia.org/wiki/File:Cochliobolus_miyabeanus.jpg>
- License: CC BY 3.0 US
- Changes: resized from the source image to 1280 x 669 pixels.

The spot-check photographs are external examples, not an independently
sampled Indonesian validation set.

## Other assets

`apps/web/public/mascot.png` is committed as a project asset, but the current
repository contains no authorship or license record for it. Confirm ownership
before granting a project-wide redistribution license.
