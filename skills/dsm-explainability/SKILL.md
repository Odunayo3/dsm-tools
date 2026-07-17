---
name: dsm-explainability
description: >
  Make a DSM model trustworthy to non-technical stakeholders: rank covariate
  importance (SHAP or permutation), report the direction of each driver
  (partial dependence), and translate it into a plain-language summary a
  policymaker can read. Trigger for "explain the map", "why does the model
  predict", "covariate importance", "SHAP", "feature importance", "make this
  understandable for decision-makers".
version: 0.1.0
---

# dsm-explainability

A policymaker will not act on a black box. Translate the model into ranked
drivers, directions, and plain language - without overclaiming causation.

## 1. When to trigger
Communicating why a map looks the way it does, or which covariates matter, to a
non-modeler audience.

## 2. Core judgment
- SHAP for tree models gives locally faithful, additive attributions; use it
  when available, permutation importance as fallback.
- Importance is about what the MODEL USES, not proven physical causation. Say so
  every time - it is the difference between honest and misleading communication.
- Report direction, not just magnitude: "SOC rises with rainfall, falls with
  slope" is what a stakeholder can reason about.
- Distinguish a covariate that is important because it is a good proxy from one
  that is causally meaningful; do not assert mechanism the data cannot support.

## 3. Failure modes
- Presenting importance as causation.
- Reading SHAP on a leaked model (importance of a leaked feature is spurious) -
  explainability comes AFTER the leakage-safe pipeline in dsm-model-fit.

## 4. Output conventions
One plain-language paragraph naming the top 2-3 drivers, their share, and their
direction, plus the explicit "describes model use, not causation" caveat.

## 5. Reference implementation
templates/explain.py - SHAP/permutation importance, partial-dependence
direction, plain-language summary. Tested on synthetic data.
