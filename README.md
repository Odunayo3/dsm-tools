# dsm-tools

Open-source Claude Code skills, decision engines, and tested templates for
agentic research and development in **digital soil mapping (DSM)** — for
researchers building maps and for policymakers using them. Give it a location and
your data; it returns a defensible, literature-grounded mapping approach so you
don't have to reason through feature engineering, model choice, and validation
design from scratch.

Modeled on the structure of [`dgilford/ai-tools`](https://github.com/dgilford/ai-tools),
adapted to DSM domain content.

## What it does

`dsm-site-assessment` is the **orchestrator**: given a location, it searches
published DSM literature for that region/biome/property, then delegates each
stage to a specialist skill with concrete, data-driven parameters.

| Skill | Purpose | Code |
|-------|---------|------|
| **dsm-site-assessment** | Literature-grounded advisor: covariates, sampling, model, validation, caveats for *any location* | orchestrator |
| **dsm-covariate-prep** | Fetch (SoilGrids/DEM/Sentinel) and align the SCORPAN stack | `fetch_covariates.py` |
| **dsm-sampling-design** | cLHS, spatial coverage, in-fill, validation samples — driven by n & dimensionality | `sampling_design.py` |
| **dsm-harmonization** | Legacy data: mass-preserving depth splines to GlobalSoilMap depths, unit & lab-bias correction | `harmonize.py` |
| **dsm-model-fit** *(flagship)* | RK, RF/QRF, XGBoost, LightGBM, SVR, GP, GAM, stacking, transfer learning — leakage-safe | `model_fit_rk_qrf.*`, `model_zoo.*`, `transfer_learning.py` |
| **dsm-validation** | Clustering-driven choice: random / spatial / kNNDM / nested / design-based | `validation_engine.py` |
| **dsm-uncertainty** | QRF intervals, conformal, AOA masking, decision-ready confidence tiers | (in model-fit templates) |
| **dsm-explainability** | SHAP + partial dependence → plain-language driver summary for stakeholders | `explain.py` |
| **dsm-methods-doc** | Auto-draft a cited methods section from the pipeline's actual choices | procedure |
| **dsm-lit-watch** | Scan recent literature; propose (never auto-apply) skill updates | procedure |

## Two tiers

- **Tier 1 — skills (free, no infrastructure):** all judgment/decision logic and
  the tested R/Python templates. Works the moment you clone into Claude Code.
- **Tier 2 — live tools (credential-based):** covariate acquisition connectors
  and GPU-optional deep transfer. You supply your own free API keys / tokens.

## Why judgment, not just code

- **No default model winner** — `recommend_model()` maps a data/goal profile to a
  reasoned shortlist rather than running everything and picking the best RMSE
  (that's automated overfitting). RF is a strong baseline; stacking rarely beats
  it; kriging residuals only helps when they're autocorrelated.
- **Leakage-safe by construction** — transformation, encoding, feature selection,
  and tuning are fit inside the training fold. Templates enforce it; a 7-row
  failure-mode catalogue in `dsm-model-fit` names the traps.
- **Spatially honest validation** — a clustering diagnostic drives the choice and
  encodes the Wadoux vs Meyer/Pebesma debate. The engine demonstrates the same
  data/model scoring RMSE **0.32 (random) vs 0.58 (block) vs 0.34 (kNNDM)** — the
  spread is the point.
- **Applicability-gated, decision-ready** — every prediction is paired with
  uncertainty, an AOA mask, and stakeholder confidence tiers; empirical coverage
  is reported, not just nominal.

Grounding for the rules is in [`docs/references.md`](docs/references.md).

## Installation

```bash
git clone https://github.com/Odunayo3/dsm-tools.git ~/dsm-tools
cd ~/dsm-tools
bash scripts/sync.sh push      # deploy skills/ -> ~/.claude/skills/
```

## Testing without Claude Code

The templates are plain scripts and run standalone on built-in synthetic data:

```bash
python skills/dsm-model-fit/templates/model_fit_rk_qrf.py
python skills/dsm-model-fit/templates/model_zoo.py
python skills/dsm-sampling-design/templates/sampling_design.py
python skills/dsm-validation/templates/validation_engine.py
python skills/dsm-harmonization/templates/harmonize.py
python skills/dsm-explainability/templates/explain.py
Rscript skills/dsm-model-fit/templates/model_fit_rk_qrf.R
```

CI (`.github/workflows/ci.yml`) runs these on every push, so broken code can't
merge. Swap in your data by replacing the synthetic block at the bottom of each
file.

### Dependencies

- **R (primary):** `ranger`, `gstat`, `sp`, `randomForest`, `e1071` cover the
  tested subset; `xgboost`, `mgcv`, `kernlab`, `Cubist`, `clhs`, `CAST` unlock the
  full menu.
- **Python:** `numpy`, `scipy`, `scikit-learn`, `pandas`, `pykrige`; optional
  `xgboost`, `lightgbm`, `shap`, `pygam`; `requests` for connectors.

## Honesty labels

Two components could not be fully executed in the build environment and carry
explicit notes: (1) the external-API covariate connectors are written to spec and
dry-run tested but need a live confirmation run on your machine; (2) deep/transfer
learning at realistic scale needs a GPU and is documented as optional.
Everything else is tested on synthetic data in CI.

## Shipping / citation

- **License:** MIT (see [LICENSE](LICENSE)).
- **Docs site:** `mkdocs.yml` + `docs_site/` → GitHub Pages (`bash
  docs_site/build_docs.sh` mirrors the skills into browsable pages).
- **Citability:** `paper/paper.md` is a JOSS submission skeleton; tag a release
  and mint a Zenodo DOI.
- **Contributing:** see [CONTRIBUTING.md](CONTRIBUTING.md) — changes to judgment
  require a citation; `dsm-lit-watch` proposals are human-vetted.

## Status

v0.2 — 10 skills, 7 tested code engines, docs + packaging. Curated and versioned,
not "always current"; see `dsm-lit-watch` and `docs/changelog.md`.
