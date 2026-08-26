# IRIS poster copy: INOVATALK 2026

A1 portrait. Body text in English. IEEE in-text citations (`[1]`, `[2]`). One source per reference number. Do not use em dashes.

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

In 2024 Indonesia harvested 10.05 million hectares of paddy and produced 53.14 million tonnes of dry unhusked paddy (GKG) [1]. The usual way to grow that crop - keeping the field flooded - is also why irrigated rice is a major agricultural source of methane. IPCC AR6 assigns non-fossil CH₄ a GWP100 of 27 [2].

The agronomic reply is already on the shelf. IRRI’s safe alternate wetting and drying (AWD) protocol lets the water table fall to 15 cm below the soil surface, then refills the field to about 5 cm, and holds a flood from one week before to one week after flowering [3]. Under mild (safe) AWD a meta-analysis reports 23.4% less water use, with no significant yield loss in most circumstances [5]; adoption studies in Asia report irrigation-input cuts of up to 38% when the protocol is followed [4]. A greenhouse-gas meta-analysis finds CH₄ down 51.6% versus continuous flooding, with N₂O up 44.0% [6]. The science is not the missing piece.

What stalls in the field is the watch. Safe AWD still depends on reading a perforated field water tube [3], and leaf stress is often noticed only after damage is advanced. Both jobs sit on the same plot. That is the gap software can close.

## 2. Approach

IRIS is a web application for that plot. It does not invent a new cultivation method. It runs the existing safe-AWD protocol, reads the canopy for anomalies, and answers from the same records. A person remains in the loop: the system recommends, and the farmer or extension officer acts.

1. Irrigation follows growth stage: establishment, vegetative AWD, flowering flood, grain fill, and harvest. If the BMKG forecast is ≥15 mm of rain within 72 h [12], irrigation is deferred unless the water table is already near a dry hard floor (trigger minus 10 cm). Establishment and flowering stay flooded. A sensor ingest API is in place; field hardware has not been tested.

2. Five leaf classes (four diseases plus healthy) are recognised with MobileNetV3-Large [9] and then scored against the plot’s water and weather through explicit rules. That combination is the anomaly signal, not the photo class alone. Low-confidence photographs may be rejected. No end-to-end fusion model is used.

3. The assistant answers from plot data and a knowledge base. It replies in Indonesian when the user writes Indonesian. If the language-model endpoint is down, it retrieves from that knowledge base and appends the latest plot status. Pesticide doses are not recommended.

## 3. Methods

Water use and CH₄ come from a 100-day water-balance simulation (0 mm rain, 0.8 cm day⁻¹ drawdown, 1 ha). Drawdown is halved while the table is below 0 cm. That run uses stage triggers and refill to +5 cm only; it does not apply the live rain-hold rule. Sensor calibration and a mesocosm trial remain protocol only; no field data have been collected.

The image classifier was trained on public rice-leaf photographs: Mendeley samples of four diseases [10], [11] and Paddy Doctor field photographs for the overlapping classes, including healthy leaves [13]. Indonesian field leaves have not been measured.

A logistic regression on Open-Meteo historical daily rainfall for Salatiga (1 Jan. 2018–26 Aug. 2026; *n* = 3,154) [14] estimates whether day *i* plus the next two days sum to ≥15 mm. In-sample accuracy is 0.5891 versus a wet base rate of 0.5022; there is no held-out test. That score is never used to withhold irrigation. The scheduler still uses the BMKG 72 h total [12]. If the score disagrees with BMKG, or lies between 0.35 and 0.65, the interface flags the forecast for human review.

Emissions follow IPCC 2006 Tier 1 [7]: seasonal CH₄ = 1.30 · SF_w · *t* · *A* kg (SF_p = SF_o = 1). Continuous flooding uses SF_w = 1.00. The effective SF_w of 0.8922 interpolates 1.00 and the 2006 aggregated irrigated factor 0.78 by the flooded-day fraction (51/100). That interpolation is a project assumption, not an IPCC equation, and not the 2006 multiple-aeration factor 0.52. GWP100 = 27 [2]. N₂O is omitted, so the CO₂e figure is an upper bound on net climate benefit if N₂O rises under AWD [6]. The 2019 Refinement sets SF_w for multiple drainage at 0.55 [8]. During flowering, irrigation is triggered at or below +3 cm (refill to +5 cm). IRRI requires a flood in this window [3].

## 4. Workflow

Two observations are taken on the same plot and meet in one loop. The water process records the water table, then runs the stage scheduler and the rain-hold rule. A shallow pond is left to recede; at or above +15 cm the advice is to lower the water toward +5 cm if a drain exists. Drain-to-dry is harvest only. The canopy process checks a photograph and classifies it on CPU. Both feed a rule matrix and the assistant. The emission sheet shows the 100-day water-balance, not the leaf class. Pumps are not actuated; the user decides (human in the loop). During establishment and flowering the rain-hold rule is disabled so the flood is kept.

## 5. Results

**Headline:** −37.5% irrigation water (8,000 → 5,000 m³ ha⁻¹). CH₄ −10.8%, or 0.378 t CO₂e ha⁻¹ season⁻¹. Water-balance simulation, 100 days, 1 ha, 0 mm rain.

| Metric | Continuous flooding | This run (sim.) |
| --- | --- | --- |
| Irrigation water (m³) | 8,000 | 5,000 |
| Flooded days | 100 | 51 |
| CH₄ (kg) | 130.00 | 115.99 |
| CO₂e avoided (t) | - | 0.378 |
| Model irrigation events | 100* | 23* |

*Daily water-balance top-ups at 0.8 cm day⁻¹, not 100 farmer irrigations. The 23 events are 14 establishment plus 9 flowering; vegetative and grain-fill AWD triggers never fired. The table reached −14.6 cm and did not reach −15 cm (Fig. 1).

On the public image mix, held-out test accuracy of the served model is 0.9784 (*n* = 1,621; macro-F1 0.9783). Indonesian field leaves have not been measured.

**Fig. 1.** Water-table trace, 100-day simulation (0 mm rain). Triangles mark irrigation events. Yellow band: flowering flood. The dashed −15 cm line is the safe-AWD trigger [3]; it was not reached in this run.

**Fig. 2.** Seasonal irrigation volume and CH₄. CH₄ difference = 14.01 kg ha⁻¹; CO₂e = 14.01 × 27 / 1000 = 0.378 t ha⁻¹ [2], [7].

Chart files: `assets/poster/chart_water_trace.png`, `assets/poster/chart_results.png`.

## 6. Prototype

The web application (Next.js and FastAPI) is organised around one demonstration plot, Sawah Demo - Salatiga. That plot is a 30-day synthetic walkthrough, not a field trial. Irrigation, canopy triage, and the assistant read the same plot record. The emission sheet shows the simulation figures in the table, not the 30-day window of the demonstration plot. Five leaf classes run on CPU. Outputs are stored when they are computed; the prototype does not log a human confirmation.

## 7. Implications

On one hectare the simulation saves 3,000 m³ of water per season (−37.5%) and cuts CH₄ by 10.8%. Relative to the mild-AWD water mean in [5], the water saving is large; relative to [6], the CH₄ saving is small, because this run did not reach −15 cm. What is available now is working software and a repeatable calculation; field measurements have not been made.

## 8. Conclusion

IRIS does not replace IRRI’s safe-AWD protocol [3]. It puts that protocol, canopy-anomaly triage, and a plot assistant on the same plot, with a person in the loop, and writes water and CH₄ under IPCC Tier 1 [7]. The numbers on this poster come from a water-balance simulation. Field sensors, chamber CH₄ measurements, and Indonesian leaf-image tests have not been carried out.

---

## References

[1] Badan Pusat Statistik, “Pada 2024, luas panen padi mencapai sekitar 10,05 juta hektare dengan produksi padi sebanyak 53,14 juta ton gabah kering giling (GKG),” Press release, Jakarta, Indonesia, Feb. 3, 2025. Accessed: Aug. 26, 2026. [Online]. Available: https://www.bps.go.id/id/pressrelease/2025/02/03/2414/

[2] P. Forster *et al.*, “The Earth’s energy budget, climate feedbacks, and climate sensitivity,” in *Climate Change 2021: The Physical Science Basis. Contribution of Working Group I to the Sixth Assessment Report of the Intergovernmental Panel on Climate Change*, V. Masson-Delmotte *et al.*, Eds. Cambridge, U.K.: Cambridge Univ. Press, 2021, ch. 7, pp. 923–1054, doi: 10.1017/9781009157896.009.

[3] International Rice Research Institute, “Saving water with alternate wetting drying (AWD),” *Rice Knowledge Bank*. Accessed: Aug. 26, 2026. [Online]. Available: http://knowledgebank.irri.org/step-by-step-production/growth/water-management/alternate-wetting-drying-awd

[4] R. M. Lampayan, R. M. Rejesus, G. R. Singleton, and B. A. M. Bouman, “Adoption and economics of alternate wetting and drying water management for irrigated lowland rice,” *Field Crops Res.*, vol. 170, pp. 95–108, Jan. 2015, doi: 10.1016/j.fcr.2014.10.013.

[5] D. R. Carrijo, M. E. Lundy, and B. A. Linquist, “Rice yields and water use under alternate wetting and drying irrigation: A meta-analysis,” *Field Crops Res.*, vol. 203, pp. 173–180, Feb. 2017, doi: 10.1016/j.fcr.2016.12.002.

[6] C. Zhao, R. Qiu, T. Zhang, Y. Luo, and E. Agathokleous, “Effects of alternate wetting and drying irrigation on methane and nitrous oxide emissions from rice fields: A meta-analysis,” *Glob. Change Biol.*, vol. 30, no. 12, Art. no. e17581, Dec. 2024, doi: 10.1111/gcb.17581.

[7] IPCC, *2006 IPCC Guidelines for National Greenhouse Gas Inventories*, vol. 4, *Agriculture, Forestry and Other Land Use*. Hayama, Japan: IGES, 2006, ch. 5.

[8] IPCC, *2019 Refinement to the 2006 IPCC Guidelines for National Greenhouse Gas Inventories*, vol. 4. Hayama, Japan: IGES, 2019, ch. 5.

[9] A. Howard *et al.*, “Searching for MobileNetV3,” in *Proc. IEEE/CVF Int. Conf. Comput. Vis. (ICCV)*, Seoul, Korea (South), Oct. 27–Nov. 2, 2019, pp. 1314–1324, doi: 10.1109/ICCV.2019.00140.

[10] P. K. Sethy, N. K. Barpanda, A. K. Rath, and S. K. Behera, “Deep feature based rice leaf disease identification using support vector machine,” *Comput. Electron. Agric.*, vol. 175, Art. no. 105527, Aug. 2020, doi: 10.1016/j.compag.2020.105527.

[11] P. K. Sethy, Jul. 18, 2020, “Rice Leaf Disease Image Samples,” Mendeley Data, V1, doi: 10.17632/fwcj7stb8r.1.

[12] Badan Meteorologi, Klimatologi, dan Geofisika, “Data Prakiraan Cuaca Terbuka.” Accessed: Aug. 26, 2026. [Online]. Available: https://data.bmkg.go.id/prakiraan-cuaca/

[13] A. Petchiammal, S. Briskline Kiruba, D. Murugan, and A. Pandarasamy, “Paddy Doctor: A visual image dataset for automated paddy disease classification and benchmarking,” in *Proc. 6th Joint Int. Conf. Data Sci. Manage. Data (CODS-COMAD)*, Mumbai, India, Jan. 4–7, 2023, pp. 203–207, doi: 10.1145/3570991.3570994.

[14] P. Zippenfenig, “Open-Meteo.com Weather API,” Zenodo, 2023, doi: 10.5281/zenodo.7970649.

---

Reproducibility: `experiments/outputs/backtest_summary.json`. Print format: A1, 594 × 841 mm.
