# IRIS poster copy: INOVATALK 2026

A1 portrait. Body text in English. IEEE in-text citations (`[1]`, `[2]`). One source per reference number.

> **Designer use:** Sections 1–6 contain paste-ready poster copy. Render the farmer journey as an arrow diagram, the evaluation text as three cards, and the Prototype section as screenshots with captions. Do not paste lines explicitly marked as designer instructions, the Designer handoff, or the full reference records as body paragraphs.

---

## Banner

INOVATALK 2026 · STEM · Lentera Harmoni: Green & Sustainable Innovation

## Title

IRIS - Intelligent Rice Integrated System

## Subtitle

Rain-aware AWD, canopy-anomaly triage, and a plot assistant - on one plot

## Authors

Joshua Christopher Gunawan, Archangela Sheilla Haryanto Sundjaya, and Dominic Xaviera  
Department of Informatics, Universitas Kristen Maranatha  
2572001@maranatha.ac.id · 2472014@maranatha.ac.id · 2472011@maranatha.ac.id

---

## 1. Problem

**The National Water Challenge**

Indonesia harvested 10.05 million hectares of paddy and produced 53.14 million tonnes of dry unhusked paddy in 2024 [1], making rice water management a national sustainability concern.

**The Evidence-Based Opportunity**

IRRI’s safe AWD protocol lets the field water table fall to −15 cm before refilling to about +5 cm and protects the flowering flood [3]; field evidence shows that AWD can reduce irrigation and CH₄ while maintaining yield, although N₂O may rise [4], [5], [6].

**Research Objective**

Farmers still read field tubes and inspect leaves as separate tasks; IRIS tests whether one WebApp can unite those observations, recommendations, and human review on the same plot.

## 2. Approach and methods

IRIS is designed to connect IoT-assisted water sensing, safe-AWD guidance, rice-leaf screening, and plot-specific explanations in one farmer-controlled workflow. The current prototype uses demo data; IRIS recommends, and the farmer or extension officer decides.

### A. Farmer journey

**Designer instruction - do not paste:** Render the following six steps as one arrow diagram.

**1. SENSE + OBSERVE** An IoT field sensor sends the water level to IRIS; the farmer confirms crop stage and adds a leaf photo when needed. → **2. ADD CONTEXT** IRIS retrieves the official BMKG 72-hour forecast and applies its ≥15 mm project rain-hold rule; BMKG alone enters the scheduler [12]. → **3. ANALYSE** Stage rules protect establishment and flowering and apply safe AWD during vegetative and grain-fill stages; MobileNetV3-Large screens five leaf classes [3], [9]. → **4. COMBINE + EXPLAIN** Rules combine water, weather, and leaf signals; the assistant explains the same plot record and uses the knowledge base as fallback. → **5. REVIEW** The farmer or extension officer checks the recommendation and uncertainty flags. → **6. ACT** The farmer decides and acts; IRIS never controls a pump or prescribes pesticide doses.

### B. Evaluation

**Designer instruction - do not paste:** Render the following evidence statements as three compact cards.

- **DEFINED WATER + CH₄ SCENARIO:** A 100-day, 1 ha, zero-rain simulation uses 0.8 cm day⁻¹ drawdown and stage-aware refill to +5 cm. CH₄ follows IPCC Tier 1 with a declared project SF_w interpolation and GWP100 = 27; the run excludes live rain-hold, N₂O, and field measurements [2], [6], [7].
- **PUBLIC-DATASET LEAF TEST:** The classifier uses Sethy and Paddy Doctor images [10], [11], [13]. The held-out split provides public-dataset evidence; its raw manifest is absent, and Indonesian field leaves remain untested.
- **SECONDARY RAIN REVIEW:** Logistic regression uses Open-Meteo rain for Salatiga (2018–2026; _n_ = 3,154) without a held-out test. It only flags disagreement or uncertainty for review; BMKG remains the scheduler input [12], [14].

**FIELD VALIDATION PENDING:** sensor calibration, water use, yield, emissions, usability, and Indonesian leaf performance.

## 3. Results

**Headline:** −37.5% irrigation water (8,000 → 5,000 m³ ha⁻¹ season⁻¹). Modelled CH₄ −10.8%, or 0.3784 t CO₂e ha⁻¹ season⁻¹. Project simulation, 100 days, 1 ha, 0 mm rain.

| Metric                                  | Continuous flooding | This run (sim.) |
| --------------------------------------- | ------------------- | --------------- |
| Irrigation water (m³ ha⁻¹ season⁻¹)     | 8,000               | 5,000           |
| Flooded days                            | 100                 | 51              |
| Modelled CH₄ (kg ha⁻¹ season⁻¹)         | 130.00              | 115.99          |
| Modelled CO₂e avoided (t ha⁻¹ season⁻¹) | -                   | 0.3784          |
| Model irrigation events                 | 100\*               | 23\*            |

\*Daily water-balance top-ups at 0.8 cm day⁻¹, not 100 farmer visits. The 23 IRIS events are 14 establishment plus 9 flowering top-ups. The −15 cm trigger never fired during the vegetative or grain-fill stages. The minimum level was −14.6 cm immediately before the first flowering top-up; the minimum end-of-day level was −14.2 cm (Fig. 1).

For the committed public-dataset split, the served model reports held-out test accuracy of 0.9784 (_n_ = 1,621; macro-F1 0.9783). The raw split is absent from the repository, and Indonesian field leaves have not been evaluated.

**Fig. 1.** Water-table trace for the 100-day project simulation (0 mm rain), including pre-refill and end-of-day states. Triangles mark model top-ups, and the yellow band marks the flowering flood. The dashed −15 cm line is the safe-AWD trigger [3]; it did not trigger a vegetative or grain-fill refill.

**Fig. 2.** Seasonal irrigation volume and modelled CH₄. The unrounded CH₄ difference is 14.014 kg ha⁻¹; CO₂e = 14.014 × 27 / 1000 = 0.3784 t ha⁻¹ season⁻¹ [2], [7]. N₂O is omitted.

### Fig. 2 literature comparison strip - designer-ready copy

**Field literature - different studies and conditions; context, not validation of IRIS E3**

| Outcome vs continuous flooding | IRIS E3               | Field-literature context                           |
| ------------------------------ | --------------------- | -------------------------------------------------- |
| Irrigation water               | −37.5% `[simulated]`  | Mild AWD −23.4% [5]; Asian adoption up to −38% [4] |
| CH₄                            | −10.8% `[modelled]`   | Overall AWD −51.6% [6]                             |
| Climate scope                  | CH₄ only; N₂O omitted | Combined CH₄+N₂O GWP −46.9%, with N₂O +44.0% [6]   |

**Designer instruction:** place this as a compact, visually separate strip below Fig. 2. Keep the absolute IRIS bars (m³ ha⁻¹ season⁻¹ and kg CH₄ ha⁻¹ season⁻¹) unchanged. Present the literature values only as percentages versus continuous flooding; do not convert them to IRIS absolute units. Use distinct labels for `This prototype [simulated]` and `Field literature`, and retain the context-not-validation line.

Chart files: `assets/poster/chart_water_trace.{svg,png}` and `assets/poster/chart_results.{svg,png}`. Reproduce with `python experiments/run_all.py` and `python experiments/generate_poster_charts.py`; plotted values are preserved as CSV files beside the charts.

## 4. Prototype

**WORKING PROTOTYPE - DEMO DATA:** The WebApp links irrigation guidance, leaf screening, and plot-specific explanations on Sawah Demo - Salatiga. Its 30-day walkthrough is synthetic and separate from the 100-day evidence run. The prototype stores computed outputs but does not yet log the farmer’s subsequent confirmation.

**Designer instruction - do not paste:** Use three cropped WebApp screenshots with these captions:

1. **Today + Water:** One plot shows water level, crop stage, BMKG status, and the current recommendation.
2. **Leaf screening:** The same plot receives a five-class screening result or a retake/review request.
3. **Ask IRIS:** The assistant explains the stored plot context in Indonesian or English and labels offline fallback.

## 5. Implications

On one hectare the simulation saves 3,000 m³ of irrigation water per season (−37.5%) and reduces modelled CH₄ by 10.8%. The Fig. 2 literature strip places those project results beside field evidence without treating different studies, units, or conditions as one experiment. The comparison is contextual, not a validation. What is available now is working software and a repeatable calculation; field measurements have not been made.

## 6. Conclusion

IRIS does not replace IRRI’s safe-AWD protocol [3]. It puts that protocol, canopy-anomaly triage, and a plot assistant on the same plot, with a person in the loop. Its water and CH₄ figures are project simulations; the CH₄ scenario uses the IPCC Tier 1 equation plus a clearly stated project interpolation [7]. Field sensors, chamber CH₄ measurements, yield measurements, and Indonesian leaf-image tests have not been carried out.

## Designer handoff - instructions and retained technical notes, not poster body

1. Use the supplied IRIS poster as the base. Use S-SPARC as a lesson in scan-first narrative and visual hierarchy: highlighted claims, a context-to-objective progression, short text blocks, icon-supported flow, and generous figure space. Do not copy its content, section names, colour treatment, or illustrations.
2. Replace the current separate **Approach**, **Method**, and system-centred **Workflow** text boxes with one wide **Approach and methods** panel. Put the six IoT-assisted farmer-journey steps in the upper lane as arrows with simple icons; put the three evaluation cards and **FIELD VALIDATION PENDING** badge below them.
3. Keep **Problem** as exactly three highlighted mini-sections, each containing one main sentence. Preserve their narrative sequence: national relevance → evidence-based opportunity → research objective. Do not restore the former supporting sentences in the poster body.
4. Replace the current text-heavy **Prototype** box with two or three actual WebApp screenshots. Capture the seeded demo from Today/Water, Leaf (`/health`), and Ask IRIS (`/assistant`). Crop browser chrome, use consistent scale, keep the DEMO state visible, and add the three supplied captions. Do not fabricate screens; leave a slot pending if a required UI state is not yet presentable.
5. The current IRIS draft places prototype-description copy under **Workflow** and system-workflow copy under **Prototype**. Replace both blocks; do not merely swap their headings.
6. Keep both result charts and their values unchanged. Give the charts more space than prose, preserve accessible labels, and keep the literature comparison visually separate from the IRIS simulation.
7. Use visible evidence badges: **WORKING PROTOTYPE**, **DEFINED SIMULATION**, **PUBLIC-DATASET BENCHMARK**, **EXPLORATORY CH₄ MODEL**, and **FIELD VALIDATION PENDING**.
8. Prefer active constructions already supplied in this revision. Do not expand them into passive explanatory paragraphs.
9. Keep the GitHub QR code and print the URL below it. The QR destination is the source for full references and technical detail.

### Retained technical notes - use for accuracy checks, not body copy

- Irrigation follows establishment, vegetative AWD, flowering flood, grain fill, and harvest. The ≥15 mm rain-hold threshold is an IRIS project rule, not a BMKG recommendation. Rain hold never applies during establishment or flowering and never overrides the dry hard floor (trigger minus 10 cm).
- The scheduler leaves shallow ponding to recede naturally. At or above +15 cm it advises lowering water toward +5 cm if drainage exists; only harvest uses drain-to-dry advice.
- An IoT/sensor ingest API exists, but the team has not field-tested the node hardware, calibration, or mesocosm protocol.
- The leaf pathway runs five classes on CPU, rejects some low-confidence photographs, and combines outputs through explicit rules rather than an end-to-end fusion model. The photo class alone is not the combined anomaly signal.
- The assistant reads the same plot record, responds in the user’s language, and uses the knowledge base when the language-model endpoint fails. It never recommends pesticide doses.
- The rain logistic regression predicts whether three-day rainfall reaches 15 mm. It achieved 0.5891 in-sample accuracy versus a 0.5022 wet base rate, has no held-out test, and flags review when it disagrees with BMKG or scores 0.35–0.65. It never withholds irrigation.
- The CH₄ scenario uses `1.30 × SF_w × t × A`, assumes `SF_p = SF_o = 1`, and obtains effective `SF_w = 0.8922` by interpolating continuous flooding `1.00` and the 2006 aggregate irrigated factor `0.78` from 51 flooded days. IPCC does not prescribe that interpolation. The 2019 Refinement gives `SF_w = 0.55` for multiple drainage [8], but this project run does not substitute that factor. GWP100 is 27, and omitting N₂O makes avoided CO₂e an upper bound.
- The 30-day demo plot and the 100-day evidence run are separate. The emission sheet reports the evidence run, not the demo window or the leaf class. The prototype stores computed outputs but not the farmer’s later confirmation.

---

## References

[1] Badan Pusat Statistik, “Pada 2024, luas panen padi mencapai sekitar 10,05 juta hektare dengan produksi padi sebanyak 53,14 juta ton gabah kering giling (GKG),” Press release, Jakarta, Indonesia, Feb. 3, 2025. Accessed: Aug. 30, 2026. [Online]. Available: https://www.bps.go.id/id/pressrelease/2025/02/03/2414/

[2] P. Forster _et al._, “The Earth’s energy budget, climate feedbacks, and climate sensitivity,” in _Climate Change 2021: The Physical Science Basis_, Cambridge Univ. Press, 2021, ch. 7, pp. 923-1054 and Supplementary Material, Table 7.SM.7, doi: 10.1017/9781009157896.009. Accessed: Aug. 30, 2026. [Online]. Available: https://www.ipcc.ch/report/ar6/wg1/chapter/chapter-7/

[3] International Rice Research Institute, “Saving water with alternate wetting drying (AWD),” _Rice Knowledge Bank_. Accessed: Aug. 30, 2026. [Online]. Available: https://www.knowledgebank.irri.org/training/fact-sheets/water-management/saving-water-alternate-wetting-drying-awd

[4] R. M. Lampayan, R. M. Rejesus, G. R. Singleton, and B. A. M. Bouman, “Adoption and economics of alternate wetting and drying water management for irrigated lowland rice,” _Field Crops Res._, vol. 170, pp. 95–108, Jan. 2015, doi: 10.1016/j.fcr.2014.10.013.

[5] D. R. Carrijo, M. E. Lundy, and B. A. Linquist, “Rice yields and water use under alternate wetting and drying irrigation: A meta-analysis,” _Field Crops Res._, vol. 203, pp. 173–180, Feb. 2017, doi: 10.1016/j.fcr.2016.12.002.

[6] C. Zhao, R. Qiu, T. Zhang, Y. Luo, and E. Agathokleous, “Effects of alternate wetting and drying irrigation on methane and nitrous oxide emissions from rice fields: A meta-analysis,” _Glob. Change Biol._, vol. 30, no. 12, Art. no. e17581, Dec. 2024, doi: 10.1111/gcb.17581.

[7] IPCC, _2006 IPCC Guidelines for National Greenhouse Gas Inventories_, vol. 4, _Agriculture, Forestry and Other Land Use_. Hayama, Japan: IGES, 2006, ch. 5, eqs. 5.1-5.2 and Tables 5.11-5.12. Accessed: Aug. 30, 2026. [Online]. Available: https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/4_Volume4/V4_05_Ch5_Cropland.pdf

[8] IPCC, _2019 Refinement to the 2006 IPCC Guidelines for National Greenhouse Gas Inventories_, vol. 4. Hayama, Japan: IGES, 2019, ch. 5, Table 5.12. Accessed: Aug. 30, 2026. [Online]. Available: https://www.ipcc-nggip.iges.or.jp/public/2019rf/pdf/4_Volume4/19R_V4_Ch05_Cropland.pdf

[9] A. Howard _et al._, “Searching for MobileNetV3,” in _Proc. IEEE/CVF Int. Conf. Comput. Vis. (ICCV)_, Seoul, Korea (South), Oct. 27–Nov. 2, 2019, pp. 1314–1324, doi: 10.1109/ICCV.2019.00140.

[10] P. K. Sethy, N. K. Barpanda, A. K. Rath, and S. K. Behera, “Deep feature based rice leaf disease identification using support vector machine,” _Comput. Electron. Agric._, vol. 175, Art. no. 105527, Aug. 2020, doi: 10.1016/j.compag.2020.105527.

[11] P. K. Sethy, Jul. 18, 2020, “Rice Leaf Disease Image Samples,” Mendeley Data, V1, doi: 10.17632/fwcj7stb8r.1.

[12] Badan Meteorologi, Klimatologi, dan Geofisika, “Data Prakiraan Cuaca Terbuka.” Accessed: Aug. 30, 2026. [Online]. Available: https://data.bmkg.go.id/prakiraan-cuaca/

[13] A. Petchiammal, S. Briskline Kiruba, D. Murugan, and A. Pandarasamy, “Paddy Doctor: A visual image dataset for automated paddy disease classification and benchmarking,” in _Proc. 6th Joint Int. Conf. Data Sci. Manage. Data (CODS-COMAD)_, Mumbai, India, Jan. 4–7, 2023, pp. 203–207, doi: 10.1145/3570991.3570994.

[14] Open-Meteo, “Historical Weather API.” Accessed: Aug. 30, 2026. [Online]. Available: https://open-meteo.com/en/docs/historical-weather-api (software citation doi: 10.5281/zenodo.7970649).

---

Reproducibility: `experiments/outputs/backtest_summary.json`, `experiments/generate_poster_charts.py`, and `assets/poster/*.csv`. Print format: A1, 594 × 841 mm.
