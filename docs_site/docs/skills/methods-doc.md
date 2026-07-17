---
name: dsm-methods-doc
description: >
  Auto-draft a defensible methods section from the pipeline's ACTUAL choices -
  covariates used, harmonization applied, sampling and validation design, model
  and transformation, uncertainty and AOA - with citations, ready for a paper
  or a policy justification. Trigger for "write the methods", "document how this
  map was made", "methods section", "reproducibility report".
version: 0.1.0
---

# dsm-methods-doc

Every map needs a defensible "how it was made" for publication or policy. Draft
it from the real pipeline choices, not a generic template.

## 1. When to trigger
After a pipeline is built/run, when a methods write-up or reproducibility record
is needed.

## 2. Core behavior
- Read the actual choices made in the session (covariates, harmonization spline
  and depths, sampling design and n, validation design and why, model class and
  hyperparameters, transformation fit inside folds, uncertainty method, AOA
  threshold) and narrate them in order.
- Cite the method source for each non-trivial choice from docs/references.md
  (e.g. mass-preserving spline, kNNDM, AOA, QRF).
- Report the validation design WITH the accuracy number and the empirical
  interval coverage - never a bare RMSE.
- Flag anything that was assumed or defaulted so a reviewer can see it.

## 3. Output conventions
Direct academic voice, past tense, no em-dashes, no filler. Name software and
versions. Structure: data and harmonization; covariates; sampling; model and
preprocessing; validation; uncertainty and applicability; software.

## 4. Reference implementation
Procedure skill; no code template. Assembles prose from the pipeline record.
