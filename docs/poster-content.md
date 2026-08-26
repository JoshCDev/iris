# IRIS poster copy: INOVATALK 2026

A1 portrait. Body text in English. IEEE in-text citations (`[1]`, `[2]`). One source per reference number.

---

## Banner

INOVATALK 2026 · STEM · Lentera Harmoni: Green & Sustainable Innovation

## Title

IRIS - Intelligent Rice Integrated System

## Subtitle

AIoT sensing on one plot, ending in a smart decision the farmer confirms

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

IRIS is AIoT for one plot: a pipe reading, a leaf photograph, and a BMKG forecast land in the same record. The agronomy is IRRI safe AWD [3], not a new cultivation method. **The novelty is the smart decision at the end of that loop**, not a new CNN and not a new IPCC factor.

**Defence (why this is not “just another IoT dashboard”).** Sensing without a closed decision is telemetry. IRIS turns three noisy signals into one recommendation with fail-closed rules: (i) the live water table is the safety constraint; (ii) rain may only *hold* irrigation above a hard floor, and a persistence LogReg flags BMKG disagreement for a person; (iii) low-confidence leaf photos are rejected; (iv) pumps are not actuated. A juror asking “what if the AI is wrong?” is answered by that loop: the system recommends, a human confirms.

1. Irrigation follows growth stage: establishment, vegetative AWD, flowering flood, grain fill, and harvest. The live water table is the safety constraint. If the forecast is ≥15 mm of rain within 72 h [12], irrigation may be deferred only while the table is still above a hard floor (trigger minus 10 cm). A persistence logistic regression, fit on Open-Meteo daily rain for Salatiga, is a *second opinion* only: it never skips irrigation by itself. When it disagrees with BMKG, or P(wet) is in 0.35–0.65, the UI asks for human review. A wrong forecast is corrected at the next reading. Prolonged rain does not trigger a drain: if the table is already at or above 0 cm, the action is WAIT with “Do not drain” (AWD dries by evapotranspiration, not by pumping out). `DRAIN` is harvest only. Field hardware has not been tested.

2. Five leaf classes (four diseases plus healthy) are recognised with MobileNetV3-Large [9] and then scored against the plot’s water and weather through explicit rules. That combination is the anomaly signal - not the photo class alone. The worked example is hypothetical. No end-to-end fusion model is used. Low-confidence photographs are rejected.

3. The assistant answers in Indonesian from plot data and cited sources. If the language-model endpoint is down, it searches the plot status text. Pesticide doses are not recommended. Pumps are not actuated; a person confirms every irrigation and leaf call (human in the loop).

## 3. Methods

Water use and CH₄ come from a 100-day water-balance simulation (0 mm rain, 0.8 cm day⁻¹ drawdown, 1 ha). Sensor calibration and a mesocosm trial remain protocol only; no field data have been collected.

The image classifier was trained on public rice-leaf photographs (four diseases plus healthy) [10], [11]. Held-out accuracy on that public mix is 97.8%; Indonesian field leaves have not been measured, so that figure is not a field claim.

Emissions follow IPCC 2006 Tier 1 [7]: CH₄ = EF_c · t · A, with EF_c = EF_base · SF_w · SF_p · SF_o. We use EF_base = 1.30 kg ha⁻¹ day⁻¹ (Table 5.11) and SF_w = 1.00 (continuous flooding) or 0.78 (multiple aeration; Table 5.12). The effective SF_w of 0.8922 is a linear interpolation between 1.00 and 0.78 by the flooded-day fraction. That interpolation is a project assumption, not an IPCC equation. GWP100 = 27 [2]. N₂O is omitted, so the CO₂e figure is an upper bound. The 2019 Refinement sets SF_w for AWD at 0.55 [8]; the 2006 chain used here is the more conservative claim.

## 4. Workflow

Two observations are taken on the same plot and meet in one loop. The water process records the water table, then runs the stage scheduler and the rain-hold rule. The canopy process checks a photograph and classifies it on CPU. Both feed a rule matrix, the assistant, and an emission sheet. IRIS recommends; it does not start a pump. During flowering the rain-hold rule is disabled so the flood is kept.

## 5. Results

Two impact columns, labelled so a juror can ask which is which.

**This prototype [simulated] - E3 water-balance, 100 days, 1 ha, 0 mm rain.** Not field measurements. Reproduce: `experiments/outputs/backtest_summary.json`.

| Metric | Continuous flooding | IRIS (this run) |
| --- | --- | --- |
| Irrigation water (m³) | 8,000 | 5,000 (−37.5%) |
| Flooded days | 100 | 51 |
| CH₄ (kg) | 130.00 | 115.99 (−10.8%) |
| CO₂e avoided (t) | - | 0.378 |
| Model irrigation events | 100* | 23* |

**Literature aggregate [field meta-analyses], not this plot.** Mild/safe AWD (water table not below −15 cm) cuts irrigation water 23.4% with no meaningful yield loss [5]. Adoption studies in Asia report water cuts of up to 38% when the protocol is followed [4]. Zhao et al. (2024) report CH₄ −51.6% vs continuous flooding overall, −49.4% under mild AWD, and −40.6% when drying events are ≤ 3 [6]. IPCC 2019 Table 5.12 SF_w = 0.55 for multiple drainage is a ~45% CH₄ cut vs SF_w = 1.00 [8]. Those larger CH₄ cuts need deeper or more frequent drying than this simulation, which rarely reaches −15 cm (Fig. 1). N₂O rises 44.0% under AWD [6]; our CO₂e omits N₂O and is therefore an upper bound on benefit.

*Irrigation events are daily water-balance outputs (0.8 cm day⁻¹), not 100 farmer irrigations and not 23 dry-down cycles to −15 cm.

**Headline for the poster (this prototype only, [simulated]):** −37.5% water, CH₄ −10.8%, 0.378 t CO₂e ha⁻¹. Stand next to the literature column; do not mix the labels.

| Label | What it is | Water vs CF | CH₄ vs CF |
| --- | --- | --- | --- |
| This prototype `[simulated]` | E3 water-balance, 100 days, 1 ha, 0 mm rain | −37.5% (8,000 → 5,000 m³) | −10.8% (130.00 → 115.99 kg); 0.378 t CO₂e |
| Literature aggregate `[field meta-analyses]` | Multi-site trials, not this plot | Mild/safe AWD −23.4% [5]; adoption up to −38% [4] | Mild AWD −49.4%; overall −51.6%; ≤3 drying events −40.6% [6]. IPCC 2019 SF_w 0.55 is a ~45% model cut [8], not a field mean. |

**Fig. 1.** Water-table trace, 100-day simulation (0 mm rain). Triangles mark irrigation events. Yellow band: flowering flood. The dashed −15 cm line is the safe-AWD trigger [3]; it is rarely reached in this run.

**Fig. 2.** Seasonal irrigation volume and CH₄. CH₄ difference = 14.01 kg ha⁻¹; CO₂e = 14.01 × 27 / 1000 = 0.378 t ha⁻¹ [2], [7].

Chart files: `assets/poster/chart_water_trace.png`, `assets/poster/chart_results.png`.

## 6. Prototype

Working software (Next.js and FastAPI), one demonstration plot labelled Salatiga. That plot is a prototype walkthrough, not a field trial. Irrigation, canopy triage, and the assistant read the same plot record. The emission sheet shows the simulation figures in the table, not the 30-day demo window. Five leaf classes run on CPU.

**Human in the loop.** Irrigation and leaf outputs are recommendations. A farmer or extension officer confirms; IRIS does not actuate a pump and does not issue a laboratory diagnosis. Low-confidence leaf photos are rejected rather than guessed.

**Rain forecast.** Indonesian rainfall forecasts are uncertain. IRIS treats the BMKG 72 h total [12] as a supporting factor only. A logistic regression trained on Open-Meteo daily precipitation for Salatiga (n = 3,154 days; train accuracy 0.59 vs a ~0.50 base rate) is a persistence/climatology second opinion. It never overrides the pipe or forces HOLD_FOR_RAIN. Disagreement or an uncertain probability (0.35–0.65) raises a human-review flag. The measured water table is the safety constraint: a dry hard floor still irrigates despite rain. If rain ponds the field at or above 0 cm, the recommendation is WAIT / “Do not drain”. If the forecast misses, the next reading re-decides.

## 7. Implications

Show both numbers and keep the labels. This **simulation** saves 3,000 m³ ha⁻¹ (−37.5%) and 10.8% CH₄ because the table rarely hits −15 cm. The literature aggregate in section 5 is the ceiling under deeper or more frequent drying, not a measurement from Salatiga. Field sensors, chamber CH₄, and Indonesian leaf tests have not been carried out.

## 8. Conclusion

IRIS does not replace IRRI’s safe-AWD protocol [3]. It is AIoT that ends in a smart decision on one plot: water table, rain (BMKG + LogReg HITL), leaf triage, and a person who confirms. The headline numbers on this poster come from a water-balance simulation. Field sensors, chamber CH₄ measurements, and Indonesian leaf-image tests have not been carried out.

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
