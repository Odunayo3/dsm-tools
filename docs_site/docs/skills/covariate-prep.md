---
name: dsm-covariate-prep
description: >
  Acquire and align the SCORPAN covariate stack for DSM: fetch open covariates
  for a location (SoilGrids, DEM via OpenTopography, Sentinel with user
  credentials), derive DEM terrain attributes, compute EO indices, and align
  everything to one grid, CRS, extent, and resolution. Trigger for "prepare
  covariates", "fetch covariates for <location>", "DEM derivatives", "align my
  rasters", "SCORPAN layers", "build covariate stack". Hand modeling to
  dsm-model-fit.
version: 0.2.0
---

# dsm-covariate-prep

Get the covariates and make them model-ready - the most intimidating step for a
non-GIS user, so this skill removes it.

## 1. When to trigger
Covariate acquisition, construction, and alignment. If a model is being fit, go
to dsm-model-fit.

## 2. Covariate acquisition (removes the "which product?" barrier)
templates/fetch_covariates.py fetches open covariates for a point/area:
SoilGrids (open), Copernicus DEM via OpenTopography (free key), Sentinel-2
(user OAuth token). The END USER supplies their own credentials; none are
embedded. The connectors are written to spec and MUST be confirmed on first live
run (the build sandbox could not reach these services).

## 3. Core judgment
- SCORPAN mapping: each covariate should proxy a soil-forming factor, not be
  added for its own sake. Prune redundant DEM derivatives (highly collinear) -
  leave final selection to FFS in dsm-model-fit.
- Grid discipline: ALL layers must share CRS, extent, resolution, and origin. A
  single misaligned layer is the root of the shifted-map failure (F6) in
  dsm-model-fit. Assert alignment before stacking.
- Terrain scale: DEM derivatives are scale-dependent; compute at the resolution
  matching the process, and record the window size.
- EO compositing: cloud-mask and reduce time series to stable features (seasonal
  NDVI, bare-soil composite); document the date window. Keep covariates
  independent of the target-measurement campaign to avoid leakage.

## 4. Failure modes
- Misaligned CRS/extent -> shifted predictions (F6).
- EO index derived from the sampling campaign date leaking target information.
- Fetch connectors assumed working without a live confirmation run.

## 5. Output conventions
Keep a covariate manifest: each layer's source, date, resolution, and processing.

## 6. Reference implementation
templates/fetch_covariates.py (acquisition, spec-correct, needs live test).
Terrain-derivative + alignment template (terra / rasterio) TODO.
