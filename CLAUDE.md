# CLAUDE.md — dsm-tools

Global Claude Code skills for agentic **digital soil mapping (DSM)** research and
development. This file gives Claude standing guidance across the toolkit; each
skill's `SKILL.md` holds the detailed procedure and judgment.

## What this repo is

A curated, versioned set of skills that encode DSM *procedure and judgment* —
the expensive-to-relearn decisions in model choice, leakage-safe preprocessing,
spatially honest validation, and uncertainty reporting. It is not a black-box
that produces maps; it makes Claude a more careful pedometrician.

## Skills

| Skill | Purpose |
|-------|---------|
| `dsm-site-assessment` | **Orchestrator**: literature-grounded DSM approach for any location; delegates to the rest |
| `dsm-covariate-prep`  | Fetch (SoilGrids/DEM/Sentinel) and align the SCORPAN covariate stack |
| `dsm-sampling-design` | cLHS, spatial coverage, in-fill, validation samples — driven by n & dimensionality |
| `dsm-harmonization`   | Legacy data: mass-preserving depth splines, unit & lab-bias correction |
| `dsm-model-fit`       | RK, RF/QRF, XGBoost, LightGBM, SVR, GP, GAM, stacking, transfer learning (flagship) |
| `dsm-validation`      | Clustering-driven: random / spatial / kNNDM / nested / design-based |
| `dsm-uncertainty`     | QRF intervals, conformal, AOA masking, decision-ready confidence tiers |
| `dsm-explainability`  | SHAP + partial dependence → plain-language driver summary |
| `dsm-methods-doc`     | Auto-draft a cited methods section from the pipeline's actual choices |
| `dsm-lit-watch`       | Scan recent literature; propose (never auto-apply) skill updates |

Delegation flow: `dsm-site-assessment` → covariate-prep → sampling-design →
harmonization → model-fit → validation → uncertainty → explainability →
methods-doc, with lit-watch keeping it current.

## Standing rules for Claude in this repo

1. **Never report an accuracy the map cannot honor.** Always state the validation
   design and why. An RMSE without its CV design is not interpretable.
2. **Preprocess inside the fold.** Transformation, encoding, feature selection,
   and tuning are fit on training data only. Leakage is the default failure;
   avoid it deliberately (see dsm-model-fit §4-§6).
3. **Respect spatial structure.** Clustered sampling changes the validation
   choice. Never headline plain random k-fold on clustered data.
4. **Gate predictions by applicability.** Pair every map with an uncertainty map
   and an AOA mask; report empirical coverage, not just nominal.
5. **No default model winner.** Choose the class from the data. Expect stacking
   to rarely beat the best base learner, and say so honestly.
6. **Cite the method.** When a judgment call is applied in a write-up, cite its
   source from `docs/references.md`.

## Writing style for results

Direct academic voice, past tense for methods, no em-dashes, no filler ("it's
worth noting", marketing cadence). State the number, its uncertainty, and the
caveat, then stop. Name software and versions for reproducibility.

## Languages

R is primary (ranger, gstat, CAST, terra); Python parity is provided
(scikit-learn, pykrige). Templates live in each skill's `templates/`.

## Maintenance

Curated and versioned, not "always current". `dsm-lit-watch` proposes updates; a
human vets and merges, and records them in `docs/changelog.md`. Do not
auto-ingest findings.
