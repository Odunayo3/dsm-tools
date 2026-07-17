---
name: dsm-harmonization
description: >
  Harmonize messy legacy soil data before modeling: standardize horizon
  measurements to GlobalSoilMap depth intervals with a mass-preserving depth
  spline, convert units (SOM<->SOC, g/kg<->%), and correct lab-method bias
  against a reference. Trigger for "legacy soil data", "different depths",
  "harmonize horizons", "equal-area spline", "depth standardization", "combine
  soil datasets", "lab bias". Hand modeling to dsm-model-fit.
version: 0.1.0
---

# dsm-harmonization

The usual real bottleneck before DSM: points from different labs, depth
supports, and eras. Make them consistent so the model sees one clean target.

## 1. When to trigger
Combining or cleaning soil measurements with mixed depths, units, or lab methods.

## 2. Core judgment
- Depth support matters. Measurements over 0-25 cm and 0-30 cm are not
  interchangeable. Standardize to GlobalSoilMap intervals (0-5, 5-15, 15-30,
  30-60, 60-100, 100-200 cm) with a MASS-PRESERVING (equal-area) spline so the
  mean within each original horizon is preserved (Bishop et al. 1999; Malone et
  al. 2009). Do not linearly resample - it does not conserve mass.
- Never extrapolate the spline below the deepest horizon; return NA and let the
  model/AOA handle missingness, rather than inventing deep values.
- Unit and definition bias is real. SOM->SOC uses a factor (commonly 1.724) that
  is material-dependent; RECORD the factor used. Convert units explicitly, never
  by assumption.
- Lab-method bias: if two labs measured overlapping samples, fit a correction
  (slope+offset) on the paired data and put the secondary lab on the reference
  scale before pooling. Document it; do not silently merge.

## 3. Failure modes
- Treating differing depth supports as equal -> biased target.
- Linear depth resampling that fails to conserve mass.
- Silent unit/definition mismatch (SOM vs SOC; g/kg vs %).
- Pooling labs without bias correction.

## 4. Output conventions
Keep a harmonization log: input support, spline smoothing, unit factors, and lab
corrections applied per dataset, for reproducibility.

## 5. Reference implementation
templates/harmonize.py - mass-preserving spline to GSM depths, unit conversion,
lab-bias correction. Tested on synthetic messy profiles; validate on your real
legacy data. R parity (templates/harmonize.R) TODO via the aqp/mpspline2 pattern.
