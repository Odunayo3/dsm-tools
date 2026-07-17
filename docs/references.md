# Methodological references

The decision rules in these skills are grounded in the DSM methods literature.
Cite the source when a skill's judgment call is applied in a write-up.

## Framework
- McBratney, Mendonça Santos & Minasny (2003). *On digital soil mapping.*
  Geoderma. — SCORPAN factors; the founding framework.
- Arrouays et al. (2014). *GlobalSoilMap: toward a fine-resolution global grid
  of soil properties.* Advances in Agronomy. — output specs, depth intervals,
  uncertainty reporting conventions.

## Models
- Meinshausen (2006). *Quantile regression forests.* JMLR. — the QRF
  conditional-distribution estimator and prediction intervals (SKILL §3.2, §7).
- Hengl et al. (2018). *Random forest as a generic framework for predictive
  modeling of spatial and spatio-temporal variables.* PeerJ. — RF + distance
  covariates as an RK-like alternative.
- Adeniyi, Brenning, Bernini, Brenna & Maerker (2023). *Digital mapping of soil
  properties using ensemble machine learning approaches in an agricultural
  lowland area of Lombardy, Italy.* Land 12(2):494. — stacking rarely beats the
  best base learner; RF dominant (SKILL §3.3).
- Adeniyi, Brenning & Maerker. *Spatial prediction of SOC combining machine
  learning with residual kriging (Lombardy).* — ML-trend regression kriging in
  a lowland setting (SKILL §3.1).
- Adeniyi, Bature & Maerker (2024). *A systematic review on digital soil mapping
  approaches in lowland areas.* Land 13(3):379. — covariate dominance patterns
  (vegetation, relief) in low-relief terrain (dsm-site-assessment).

## Validation (the debate to encode, not resolve)
- Meyer & Pebesma (2021). *Predicting into unknown space? Estimating the area of
  applicability of spatial prediction models.* Methods Ecol. Evol. — AOA / DI
  (SKILL §7).
- Wadoux, Heuvelink, de Bruin & Brus (2021). *Spatial cross-validation is not
  the right way to evaluate map accuracy.* Ecological Modelling 456:109692. —
  spatial CV can be over-pessimistic; design-based validation preferred
  (SKILL §6).
- de Bruin, Brus, Heuvelink, van Ebbenhorst Tengbergen & Wadoux (2022).
  *Dealing with clustered samples for assessing map accuracy by
  cross-validation.* Ecological Informatics 69:101665.
- Milà, Mateu, Pebesma & Meyer (2022). *Nearest neighbour distance matching
  Leave-One-Out CV for map validation.* Methods Ecol. Evol. (NNDM).
- Linnenbrink, Milà, Ludwig & Meyer (2024). *kNNDM CV: k-fold nearest-neighbour
  distance matching cross-validation for map accuracy estimation.* GMD
  17:5897-5912. — preferred CV-only option for clustered data (SKILL §6).

## Software
- ranger (Wright & Ziegler) — RF/QRF. gstat (Pebesma) — variogram/kriging.
  CAST (Meyer) — FFS, AOA, knndm. terra (Hijmans) — raster. sklearn, pykrige
  (Python parity).

## Reviews for currency (2025-2026)
- *Advancing soil mapping using geostatistics and integrated ML and RS: a
  synoptic review* (2000-2024), Discover Soil (2025).
- *Digital soil mapping in the era of big data and artificial intelligence*
  (2026) — ML dominant, deep learning as emerging frontier.
- Special Issue *DSM for Agri-Environmental Management and Sustainability*,
  Land (2026) — priorities: cost-effective sampling, robust uncertainty,
  map-accuracy-to-decision linkage.
