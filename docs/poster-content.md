# IRIS poster copy: INOVATALK 2026

A1 portrait. Body text in English. IEEE in-text citations (`[1]`, `[2]`). One source per reference number.

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

In 2024 Indonesia harvested 10.05 million hectares of paddy and produced 53.14 million tonnes of dry unhusked paddy (GKG) [1]. Continuous flooding is the reference water regime in the IPCC Tier 1 method for CH₄ emissions from rice cultivation [7]. IPCC AR6 assigns non-fossil CH₄ a 100-year global warming potential (GWP100) of 27 [2].

IRRI’s safe alternate wetting and drying (AWD) protocol lets the water table fall to 15 cm below the soil surface, then refills the field to about 5 cm, and maintains flooding from one week before to one week after flowering [3]. A meta-analysis found that mild AWD used 23.4% less irrigation water than continuous flooding while maintaining yield [5]. An Asian adoption review reported irrigation-input reductions of up to 38% when AWD was implemented correctly [4]. A greenhouse-gas meta-analysis found overall CH₄ emissions 51.6% lower than continuous flooding and N₂O emissions 44.0% higher [6].

Safe AWD still requires repeated readings from a perforated field water tube [3]. Leaf inspection is a separate manual task on the same plot. IRIS tests whether software can organise those observations and recommendations in one workflow.

## 2. Approach

IRIS is a web application for that plot. It does not invent a new cultivation method. It runs the existing safe-AWD protocol, reads the canopy for anomalies, and answers from the same records. A person remains in the loop: the system recommends, and the farmer or extension officer acts.

1. Irrigation follows growth stage: establishment, vegetative AWD, flowering flood, grain fill, and harvest. IRIS sums the official BMKG three-day forecast [12] and applies a project rule: if the total is ≥15 mm, irrigation is deferred unless the water table is already near a dry hard floor (trigger minus 10 cm). The 15 mm threshold is not a BMKG recommendation. Establishment and flowering stay flooded. A sensor ingest API is in place; field hardware has not been tested.

2. A MobileNetV3-Large image classifier [9] assigns one of five leaf classes (four diseases plus healthy). Explicit rules then combine that result with the plot’s water and weather. That combination is the anomaly signal, not the photo class alone. Low-confidence photographs may be rejected. No end-to-end fusion model is used.

3. The assistant answers from plot data and a knowledge base. It replies in Indonesian when the user writes Indonesian. If the language-model endpoint is down, it retrieves from that knowledge base and appends the latest plot status. Pesticide doses are not recommended.

## 3. Methods

Water use and CH₄ come from a 100-day water-balance simulation (1 ha; 0 mm rain; 0.8 cm day⁻¹ drawdown, halved below 0 cm). Stage rules refill to +5 cm without live rain-hold. Calibration and mesocosm testing remain protocols; no field data were collected.

The five-class classifier used Sethy’s public four-disease dataset [10], [11] plus disease and healthy images from Paddy Doctor [13]. Indonesian field leaves were not tested. Uncommitted training images and split manifest prevent independent reconstruction of the split.

Logistic regression used Open-Meteo rain for Salatiga (2018–2026; _n_ = 3,154)[14]. It estimates whether day _i_ plus the next two days sum to ≥15 mm. In-sample accuracy was 0.5891 versus the 0.5022 wet base rate, without held-out testing. The score is never used to withhold irrigation. The scheduler still uses the BMKG 72 h total [12]. If the score disagrees with BMKG, or lies between 0.35 and 0.65, the interface flags the forecast for human review.

Emissions used IPCC 2006 Tier 1[7]: seasonal CH₄ = 1.30 · SF_w · t · A kg (SF_p = SF_o = 1). Effective SF_w = 0.8922 is a project interpolation between 1.00 and the aggregate irrigated factor 0.78 using 51% flooded days, not an IPCC method. GWP100 = 27 [2]. Omitting N₂O makes avoided CO₂e an upper bound [6]. During flowering, irrigation is triggered at or below +3 cm (refill to +5 cm). IRRI requires a flood in this window [3].

## 4. Workflow

Two observations are taken on the same plot and meet in one loop. The water process records the water table, then runs the stage scheduler and the rain-hold rule. A shallow pond is left to recede; at or above +15 cm the advice is to lower the water toward +5 cm if a drain exists. Drain-to-dry is harvest only. The canopy process checks a photograph and classifies it on CPU. Both feed a rule matrix and the assistant. The emission sheet shows the 100-day water-balance, not the leaf class. Pumps are not actuated; the user decides (human in the loop). During establishment and flowering the rain-hold rule is disabled so the flood is kept.

## 5. Results

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

## 6. Prototype

The web application (Next.js and FastAPI) is organised around one demonstration plot, Sawah Demo - Salatiga. That plot is a 30-day synthetic walkthrough, not a field trial. Irrigation, canopy triage, and the assistant read the same plot record. The emission sheet shows the simulation figures in the table, not the 30-day window of the demonstration plot. Five leaf classes run on CPU. Outputs are stored when they are computed; the prototype does not log a human confirmation.

## 7. Implications

On one hectare the simulation saves 3,000 m³ of irrigation water per season (−37.5%) and reduces modelled CH₄ by 10.8%. The Fig. 2 literature strip places those project results beside field evidence without treating different studies, units, or conditions as one experiment. The comparison is contextual, not a validation. What is available now is working software and a repeatable calculation; field measurements have not been made.

## 8. Conclusion

IRIS does not replace IRRI’s safe-AWD protocol [3]. It puts that protocol, canopy-anomaly triage, and a plot assistant on the same plot, with a person in the loop. Its water and CH₄ figures are project simulations; the CH₄ scenario uses the IPCC Tier 1 equation plus a clearly stated project interpolation [7]. Field sensors, chamber CH₄ measurements, yield measurements, and Indonesian leaf-image tests have not been carried out.

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
