# Changelog

Curated updates to the DSM skills. `dsm-lit-watch` proposes; a human vets and
merges here.

## [0.1.0] - 2026-07-17
### Added
- Repo skeleton mirroring dgilford/ai-tools (skills/, scripts/, templates/, docs/).
- `dsm-model-fit` (flagship): RK + RF/QRF + stacking, leakage-safe preprocessing,
  spatial/kNNDM CV, AOA. Tested R + Python templates on synthetic data.
- `dsm-site-assessment`: location -> DSM approach decision matrix.
- Structured stubs: dsm-covariate-prep, dsm-sampling-design, dsm-uncertainty,
  dsm-validation, dsm-lit-watch.
- docs/references.md grounding the decision rules in the DSM literature.

## [0.2.0] - 2026-07-17
### Added
- Wider model zoo (RF, QRF, XGBoost, LightGBM, SVR, GP, GAM, Cubist) with
  judgment-based recommend_model(); Python full, R capability-gated. Tested.
- Sampling design engine (cLHS, spatial coverage, uncertainty in-fill,
  validation sample) parameterized by n/dimensionality. Tested.
- Validation engine (clustering diagnostic; random/spatial/kNNDM/nested/
  design-based) - demonstrates accuracy spread across designs. Tested.
- Legacy-data harmonization (mass-preserving depth spline to GSM depths, unit &
  lab-bias correction). Tested on synthetic profiles.
- Explainability (SHAP/permutation + partial dependence -> plain language). Tested.
- Transfer learning for data-sparse regions (instance weighting, fine-tuning,
  AOA gate; deep transfer documented GPU-optional). Tested (CPU toy).
- Covariate acquisition connectors (SoilGrids/DEM/Sentinel) - spec-correct,
  dry-run tested; needs live confirmation.
- New skills: dsm-harmonization, dsm-explainability, dsm-methods-doc.
- dsm-site-assessment rebuilt as literature-grounded ORCHESTRATOR.
- Uncertainty -> decision tiers for stakeholders.
- Packaging: GitHub Actions CI (runs templates), JOSS paper skeleton,
  CONTRIBUTING.md, mkdocs docs site.
### Note
- External-API connectors and GPU deep-transfer are the two components not
  fully executable in the build environment; both carry honesty labels.
