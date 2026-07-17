---
name: dsm-sampling-design
description: >
  Design where and how many soil samples to take, driven by budget, covariate
  dimensionality, extent, and clustering: conditioned Latin hypercube (cLHS) for
  feature-space coverage, spatial coverage sampling for geographic spread,
  uncertainty-guided in-fill, and INDEPENDENT probability samples for
  design-based validation. Trigger for "where should I sample", "how many
  samples", "cLHS", "sampling design", "validation sample design".
version: 0.2.0
---

# dsm-sampling-design

Turn budget and data structure into a concrete design, with a reason for each
choice. Runs through templates/sampling_design.py (recommend_design, clhs,
spatial_coverage, uncertainty_infill, validation_sample).

## 1. When to trigger
Choosing sampling locations or sample size, for calibration or validation.

## 2. Core judgment (parameterized by n, dimensionality, clustering)
- cLHS covers COVARIATE feature space; spatial coverage covers GEOGRAPHIC space.
  Feature-space coverage is what protects against the AOA gaps that hurt
  prediction (dsm-model-fit/uncertainty). Prefer cLHS when covariates are good;
  add spatial spread to avoid clustering that later corrupts validation.
- Small n (<50): cLHS is essential - every point must earn its place. Expect
  wide AOA gaps; report them. Consider transfer learning to compensate.
- High covariate count (>~20) for cLHS: reduce to the SCORPAN-meaningful set or
  PCA first, or cLHS chases noise dimensions.
- Validation sampling is a SEPARATE design decision. If accuracy must be
  defensible, draw an INDEPENDENT probability sample (design-based validation,
  Wadoux et al. 2021) rather than relying on CV of the calibration set alone.
- Larger, well-dispersed samples generally improve DSM performance (Lagacherie
  et al. 2020); document the basis for n.
- Uncertainty-guided in-fill: place additional samples where the current map's
  uncertainty or AOA is worst.

## 3. Failure modes
- Clustered calibration sampling that forces pessimistic/leaky validation.
- Using the calibration set as if it were a probability sample for accuracy.
- Running cLHS on a raw, high-dimensional, collinear covariate stack.

## 4. Output conventions
State the design type, the covariates/strata used, and n with its justification.

## 5. Reference implementation
templates/sampling_design.py (Python, tested). R parity via the clhs and spcosa
packages TODO.
