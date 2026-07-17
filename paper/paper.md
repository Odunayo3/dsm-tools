---
title: 'dsm-tools: literature-grounded Claude skills for digital soil mapping'
tags:
  - digital soil mapping
  - pedometrics
  - machine learning
  - geostatistics
  - reproducibility
  - large language models
authors:
  - name: Odunayo David Adeniyi
    orcid: 0000-0002-1312-9255
    affiliation: Politecnico di Milano, and CMCC Foundation
affiliations:
  - name: Politecnico di Milano, and CMCC Foundation
    index: 1
date: 17 July 2026
bibliography: paper.bib
---

# Summary

`dsm-tools` is an open-source collection of Claude Code skills, decision engines,
and tested reference implementations for digital soil mapping (DSM). It encodes
the *procedure and judgment* of DSM - model choice, leakage-safe preprocessing,
spatially honest validation, uncertainty quantification, and communication - so
that a researcher or policymaker can obtain a defensible, location-specific
mapping approach without reasoning through feature engineering, model selection,
and validation design from first principles. Given a location, an orchestrating
skill searches published DSM literature for the relevant region, biome, and soil
property, then delegates each stage (covariate acquisition, sampling design, data
harmonization, model fitting, validation, uncertainty, and reporting) to a
specialist skill with concrete, data-driven parameters.

# Statement of need

DSM combines soil observations with environmental covariates and statistical or
machine-learning models to predict soil properties across space
[@McBratney2003]. Producing a trustworthy map requires a chain of decisions that
are easy to get subtly wrong: which covariates proxy the soil-forming factors of
a given landscape; how to sample given a limited budget; how to harmonize legacy
measurements taken over different depths and by different laboratories; which
model class fits the data and goal; and - most consequentially - how to estimate
map accuracy honestly when samples are spatially clustered. The last of these is
an active methodological debate: spatial cross-validation can be systematically
over-pessimistic [@Wadoux2021], while random cross-validation is optimistic under
clustering, and newer designs such as kNNDM cross-validation [@Linnenbrink2024]
and area-of-applicability masking [@Meyer2021] aim to align accuracy estimates
with the actual prediction task.

These decisions are typically re-derived per project and per person, and common
pitfalls - preprocessing leakage, headline accuracy from inappropriate
cross-validation, publishing predictions outside the model's applicability - recur
across the literature. `dsm-tools` packages the current best judgment on each
decision as reusable skills, with tested code and cited sources, lowering the
expertise barrier for researchers and making map provenance legible to
decision-makers.

# Functionality

The toolkit provides skills for site assessment (a literature-grounded
orchestrator), covariate acquisition and alignment, sampling design (conditioned
Latin hypercube, spatial coverage, uncertainty-guided in-fill, and independent
probability samples for design-based validation), legacy-data harmonization
(mass-preserving depth splines to GlobalSoilMap intervals [@Malone2009], unit and
laboratory-bias correction), model fitting (regression kriging, random forest and
quantile regression forest [@Meinshausen2006], gradient boosting, Gaussian
processes, generalized additive models, and transfer learning for data-sparse
regions), validation (a clustering diagnostic driving the choice among random,
spatial-block, kNNDM, nested, and design-based schemes), uncertainty (calibrated
intervals, applicability masking, and decision-ready confidence tiers), and
communication (SHAP-based plain-language explanation and automated methods
documentation). Reference implementations are provided in R (primary) and Python,
and are exercised in continuous integration.

# Acknowledgements

We thank the pedometrics community whose published methods are cited throughout
`docs/references.md`.

# References
