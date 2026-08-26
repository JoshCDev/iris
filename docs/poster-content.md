# IRIS poster copy: INOVATALK 2026

A1 portrait. Body text in English. IEEE in-text citations (`[1]`, `[2]`). One source per reference number.

---

## Banner

INOVATALK 2026 · STEM · Lentera Harmoni: Green & Sustainable Innovation

## Title

IRIS - Intelligent Rice Integrated System

## Subtitle

Rain-aware AWD, canopy-anomaly triage, and a grounded assistant - on one plot

## Authors

Joshua Christopher Gunawan, Archangela Sheilla Haryanto Sundjaya, and Dominic Xaviera  
Department of Informatics, Universitas Kristen Maranatha  
2572001@maranatha.ac.id · 2472014@maranatha.ac.id · 2472011@maranatha.ac.id

---

## 1. Problem

In 2024 Indonesia harvested 10.05 million hectares of paddy and produced 53.14 million tonnes of milled dry unhusked grain (GKG) [1]. The usual way to grow that crop - keeping the field flooded - is also why irrigated rice is a major agricultural source of methane. IPCC AR6 assigns non-fossil CH₄ a GWP100 of 27 [2].

The agronomic reply is already on the shelf. IRRI’s safe alternate wetting and drying (AWD) protocol lets the water table fall to 15 cm below the soil surface, then refills the field to about 5 cm, and holds a flood through flowering [3]. At that threshold a meta-analysis reports 23.4% less irrigation water with no meaningful yield loss [5]; adoption studies in Asia report cuts of up to 38% when the protocol is followed [4]. A greenhouse-gas meta-analysis finds CH₄ down 51.6% versus continuous flooding, with N₂O up 44.0% [6]. The science is not the missing piece.

What stalls in the field is the watch. Safe AWD still depends on reading a perforated field water tube [3], [4], and leaf stress is often noticed only after damage is advanced. Both jobs sit on the same plot. That is the gap software can close.

## 2. Approach

IRIS is a web application for that plot. It does not invent a new cultivation method. It runs the existing safe-AWD protocol, reads the canopy for anomalies, and answers the farmer from the same records.

1. Irrigation follows growth stage: establishment, vegetative AWD, flowering flood, grain fill, and harvest. If the forecast is ≥15 mm of rain within 72 h [12], irrigation is deferred unless the water table is already near the dry limit. A sensor ingest API is in place; field hardware has not been tested.

2. Four leaf-disease classes are recognised with MobileNetV3-Large [9] and then scored against the plot’s water and weather through explicit rules. That combination is the anomaly signal - not the photo class alone. The worked example is hypothetical. No end-to-end fusion model is used.

3. The assistant answers in Indonesian from plot data and cited sources. If the language-model endpoint is down, it searches the plot status text. Pesticide doses are not recommended.

## 3. Methods

Water use and CH₄ come from a 100-day water-balance simulation (0 mm rain, 0.8 cm day⁻¹ drawdown, 1 ha). Sensor calibration and a mesocosm trial remain protocol only; no field data have been collected.

The image classifier was trained on 5,932 public photographs of four rice-leaf diseases (bacterial blight, blast, brown spot, and tungro) [10], [11]. Performance on Indonesian leaves has not been measured, so test accuracy is not reported.

Emissions follow IPCC 2006 Tier 1 [7]: CH₄ = EF_c · t · A, with EF_c = EF_base · SF_w · SF_p · SF_o. We use EF_base = 1.30 kg ha⁻¹ day⁻¹ (Table 5.11) and SF_w = 1.00 (continuous flooding) or 0.78 (multiple aeration; Table 5.12). The effective SF_w of 0.8922 is a linear interpolation between 1.00 and 0.78 by the flooded-day fraction. That interpolation is a project assumption, not an IPCC equation. GWP100 = 27 [2]. N₂O is omitted, so the CO₂e figure is an upper bound. The 2019 Refinement sets SF_w for AWD at 0.55 [8]; the 2006 chain used here is the more conservative claim.

## 4. Workflow

Two observations are taken on the same plot and meet in one loop. The water process records the water table, then runs the stage scheduler and the rain-hold rule. The canopy process checks a photograph and classifies it on CPU. Both feed a rule matrix, the assistant, and an emission sheet. Pumps are not actuated; the user decides. During flowering the rain-hold rule is disabled so the flood is kept.

## 5. Results

**Headline:** −37.5% irrigation water (8,000 → 5,000 m³ ha⁻¹). CH₄ −10.8%, or 0.378 t CO₂e ha⁻¹ season⁻¹. Water-balance simulation, 100 days, 1 ha.

| Metric | Continuous flooding | IRIS (safe AWD) |
| --- | --- | --- |
| Irrigation water (m³) | 8,000 | 5,000 |
| Flooded days | 100 | 51 |
| CH₄ (kg) | 130.00 | 115.99 |
| CO₂e avoided (t) | - | 0.378 |
| Model irrigation events | 100 | 23 |

Both event counts are outputs of the daily water-balance model (0.8 cm day⁻¹ drawdown). They are not 100 farmer irrigations and not 23 dry-down cycles to −15 cm. The reported results are water volume and CH₄.

**Fig. 1.** Water-table trace, 100-day simulation (0 mm rain). Triangles mark irrigation events. Yellow band: flowering flood. The dashed −15 cm line is the safe-AWD trigger [3]; it is rarely reached in this run.

**Fig. 2.** Seasonal irrigation volume and CH₄. CH₄ difference = 14.01 kg ha⁻¹; CO₂e = 14.01 × 27 / 1000 = 0.378 t ha⁻¹ [2], [7].

Chart files: `assets/poster/chart_water_trace.png`, `assets/poster/chart_results.png`.

## 6. Prototype

The web application (Next.js and FastAPI) is organised around one demonstration plot. Irrigation, canopy triage, and the assistant read the same plot record. The emission sheet shows the simulation figures in the table, not the 30-day window of the demonstration plot. The four disease classes run on CPU. Indonesian leaf photographs have not been evaluated.

## 7. Implications

On one hectare the simulation saves 3,000 m³ of water per season (−37.5%) and cuts CH₄ by 10.8%. Those figures are smaller than full AWD ranges in the literature [4]–[6] because the water table rarely reached −15 cm in this run. What is available now is working software and a repeatable calculation; field measurements have not been made.

## 8. Conclusion

IRIS does not replace IRRI’s safe-AWD protocol [3]. It puts that protocol, canopy-anomaly triage, and a grounded assistant on the same plot, and writes water and CH₄ under IPCC Tier 1 [7]. The numbers on this poster come from a water-balance simulation. Field sensors, chamber CH₄ measurements, and Indonesian leaf-image tests have not been carried out.

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

---

Reproducibility: `experiments/outputs/backtest_summary.json`. Print format: A1, 594 × 841 mm.
