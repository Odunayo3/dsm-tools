---
name: dsm-uncertainty
description: >
  Quantify, validate, and TRANSLATE prediction uncertainty for decisions: QRF
  intervals, kriging variance, conformal prediction, empirical coverage checking,
  area-of-applicability masking, and turning a variance map into decision-ready
  confidence tiers a policymaker can act on. Trigger for "prediction interval",
  "uncertainty map", "coverage", "conformal", "area of applicability", "AOA",
  "how confident", "can I trust this map for decisions".
version: 0.2.0
---

# dsm-uncertainty

Produce uncertainty, prove it is calibrated, gate the map by applicability, and
translate it into something a decision-maker can use.

## 1. When to trigger
Producing/validating per-pixel uncertainty, or deciding where and how confidently
the map may inform a decision.

## 2. Core judgment
- Nominal is not empirical. A 90% interval must be checked against held-out
  coverage; report the empirical fraction (dsm-model-fit §7).
- Interval collapse under extrapolation: QRF intervals can narrow exactly where
  covariates leave training feature space. Always cross-check against AOA.
- Method choice: QRF quantiles (distribution from leaves), kriging variance (RK),
  or conformal prediction (distribution-free coverage guarantee). Conformal is
  the safer default when calibrated coverage matters more than shape.
- AOA / DI (Meyer & Pebesma 2021): mask or flag pixels beyond the training-DI
  threshold rather than publishing confident nonsense.

## 3. Uncertainty -> decision tiers (for stakeholders)
A variance map means nothing to a policymaker. Translate to action tiers:
- HIGH confidence: inside AOA AND relative interval width below a chosen
  threshold -> suitable for land-use/policy decisions.
- MODERATE: inside AOA but wide interval -> use with caution; corroborate.
- LOW / OUT: outside AOA or interval collapsed -> field-verify before acting; do
  not base decisions on this pixel.
Choose the width thresholds with the stakeholder and the decision's risk
tolerance; state them explicitly.

## 4. Failure modes
- Reporting nominal coverage without empirical validation.
- Publishing predictions outside the AOA without a caveat.
- Handing a raw variance map to a non-technical decision-maker untranslated.

## 5. Output conventions
Pair every prediction map with an uncertainty map, an AOA mask, and a
decision-tier map. Report empirical coverage alongside the nominal level.

## 6. Reference implementation
Interval mechanics and AOA in dsm-model-fit/templates. Conformal wrapper and
decision-tier rasterizer TODO (templates/uncertainty_tiers.py).
