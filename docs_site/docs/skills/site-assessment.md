---
name: dsm-site-assessment
description: >
  The orchestrating advisor: given a location (and whatever data the user has),
  recommend an END-TO-END digital soil mapping approach - which covariates to
  fetch, how to sample, which model class, which validation design, and the
  honest uncertainty caveats - grounded in a LIVE search of published DSM
  literature for that region/biome/property. Trigger when the user gives a place,
  coordinates, or region and asks how to map soil there, "best approach for
  <location>", "design a DSM study", or "what covariates/model/validation for
  <area>". This skill reasons and delegates; it calls the sibling skills for
  execution.
version: 0.2.0
---

# dsm-site-assessment  (orchestrator)

Turn "map soil at this location" into a defensible, literature-grounded plan,
then hand each stage to the specialist skill. This is the skill that delivers
the core promise: location in, integrated expert advice out, so the researcher
or policymaker does not have to reason through feature engineering, model choice,
and validation design from scratch.

## 1. Gather the minimum context (ask only what is missing)

1. Target property, depth, units, intended use (a farm nutrient map and a
   national SOC-stock map need different designs).
2. Extent and grain - field, catchment, region, nation; output resolution.
3. Existing data - how many soil points, how clustered, how old, what depths.
4. DEM resolution and EO access; new-sampling budget.

State assumptions inline when proceeding without an answer. Never claim to know
the soil; recommend an approach.

## 2. Search the literature LIVE for this location (do not skip)

This is what makes the advice location-specific rather than generic. Before
recommending, search published DSM work for the region/biome/property:

- Query the web (or the user's reference manager) for recent DSM studies in the
  same biome or country and for the target property. Example queries:
  "digital soil mapping <region> <property>", "<biome> soil organic carbon
  covariates random forest", "DSM <country> sampling design".
- Extract from the best 3-8 hits: which covariates carried signal there, which
  model classes were used and which won, what sampling density and validation
  design were reported, and what the authors flagged as hard.
- Prefer recent, peer-reviewed sources and known groups. Cite them in the plan.
- If the biome's best practice is unclear or fast-moving, trigger dsm-lit-watch.

Ground the recommendation in what was found, not only the static matrix in §3.

## 3. Fallback decision matrix (terrain x data density x EO coverage)

When literature is thin, reason from structure (patterns after Adeniyi et al.
2024 lowland review and the SCORPAN framework):

- Low relief (plains, agricultural lowlands): relief covariates weaken;
  vegetation indices, parent material, land use, and EO dominate. RF strong
  baseline; ML + residual kriging recovers short-range structure. Do not
  over-rely on DEM derivatives.
- Complex relief: SCORPAN relief factors (slope, curvature, TWI, MRVBF, position
  indices) carry signal; build and FFS-prune a DEM-derivative stack. RF/QRF the
  workhorse.
- Dense, dispersed data: full ML + optional residual kriging; kNNDM or
  design-based validation.
- Sparse/clustered: lean on covariates over point density; expect wide AOA
  exclusions; consider TRANSFER LEARNING from a data-rich region
  (dsm-model-fit/transfer_learning). Clustered-aware validation only.
- Rich EO: seasonal NDVI, bare-soil composites add skill (esp. low relief).
- Poor EO: terrain + legacy maps + coarse climate; widen uncertainty caveats.

## 4. Emit an end-to-end plan and DELEGATE

Produce a short plan naming, for THIS location and its data:
- Covariates to fetch and prioritize -> dsm-covariate-prep (fetch_covariates.py)
- Sampling density and design, driven by n and dimensionality
  -> dsm-sampling-design (recommend_design / clhs)
- Legacy-data harmonization if depths/labs are mixed -> dsm-harmonization
- Model class from the data/goal profile -> dsm-model-fit (recommend_model)
- Validation design from n and clustering -> dsm-validation (recommend_validation)
- Uncertainty + decision tiers for stakeholders -> dsm-uncertainty
- Stakeholder explanation + methods write-up -> dsm-explainability, dsm-methods-doc

Each delegation should carry the concrete parameters gathered in §1-§2 (n,
clustering, covariate count, property, biome), not vague pointers.

## 5. Output conventions

Direct academic voice, no em-dashes. Frame recommendations as conditional on the
§1 data questions. Cite the literature found in §2. Separate what is
literature-grounded from what is heuristic fallback.
