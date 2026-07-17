---
name: dsm-validation
description: >
  Choose and run an honest map-accuracy assessment, parameterized by sample size
  and spatial clustering: random k-fold vs spatial/block CV vs kNNDM CV vs nested
  CV vs design-based validation with an independent probability sample. Includes
  a clustering diagnostic so the choice is data-driven. Trigger for "validate my
  map", "cross-validation strategy", "spatial CV", "kNNDM", "nested CV",
  "design-based validation", "is my accuracy honest".
version: 0.2.0
---

# dsm-validation

Estimate map accuracy honestly. Encodes the current debate rather than resolving
it. Runs through templates/validation_engine.py (clustering_index,
recommend_validation, random/spatial/kNNDM folds, design_based_accuracy).

## 1. When to trigger
Deciding how to estimate accuracy, or diagnosing a number that seems too good or
too harsh.

## 2. Core judgment - measure clustering first, then choose
- Compute the clustering index. It drives everything.
- Random k-fold is optimistic under clustering (near-duplicate neighbors span
  train and test).
- Spatial/block CV was the standard fix but can be OVER-pessimistic: validation
  folds may fall outside training feature space, scoring extrapolation not map
  error (Wadoux, Heuvelink, de Bruin, Brus 2021).
- kNNDM CV matches CV fold geometry to the train-to-prediction distance
  distribution; preferred CV-only option for clustered data (Linnenbrink et al.
  2024).
- Design-based validation with an independent probability sample is the cleanest
  accuracy estimate when a validation sample can be drawn; prefer it.
- Small n (<~60): use NESTED CV (inner loop for tuning/feature selection, outer
  for accuracy) or the estimate is optimistic. Repeated CV stabilizes it.
- Preprocessing, feature selection, and tuning go INSIDE the fold. Nested CV or
  the accuracy is inflated.

```
Clustered? -> independent probability sample drawable? YES: design-based.
                                                       NO : kNNDM CV.
Even/probability sample already? -> random k-fold defensible; block CV for
                                     sensitivity.
Small n? -> nest tuning/selection inside the outer loop.
Never headline plain random k-fold on clustered data.
```

## 3. Failure modes
- Headlining random k-fold on clustered data.
- Feature selection/tuning outside the CV loop.
- Comparing against a benchmark map at mismatched support/resolution.

## 4. Output conventions
Report the validation design and WHY, with the metric. An RMSE without its CV
design is not interpretable. The demo shows the same data/model scoring
RMSE 0.32 (random) vs 0.58 (block) vs 0.34 (kNNDM) - the spread is the point.

## 5. Reference implementation
templates/validation_engine.py (Python, tested). R parity via CAST::knndm and
blockCV TODO.
