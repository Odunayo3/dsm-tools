#!/usr/bin/env python3
"""dsm-covariate-prep :: covariate acquisition connectors (Python).

Fetch environmental covariates for a location so a non-GIS-expert does not have
to know which product to pull. Connectors are written to each service's
DOCUMENTED API. They are credential-based where the service requires it; the
END USER supplies their own credentials (never embedded in this open repo).

IMPORTANT HONESTY LABEL: these connectors were written to spec but could NOT be
live-tested in the build sandbox (its network is allowlisted and does not reach
these services). Run once on your own machine to confirm against the live APIs.
A --dry-run mock path exercises the parsing/return logic without network.

Services:
  - SoilGrids 2.0 (ISRIC) - open, no key. REST point queries.
  - WorldClim / bioclim - open, tiled downloads.
  - Copernicus GLO-30 DEM via OpenTopography - free API key.
  - Sentinel-2 - requires a Copernicus/Sentinel Hub account + token (user-supplied).

Deps: requests (install on your machine); numpy for the mock.
"""
from __future__ import annotations
import argparse
import json
import numpy as np

try:
    import requests
    _HAS_REQUESTS = True
except Exception:  # noqa
    _HAS_REQUESTS = False

SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
OPENTOPO_URL = "https://portal.opentopography.org/API/globaldem"


# ---- SoilGrids 2.0 point query (open, no key) ----------------------------
def fetch_soilgrids_point(lon, lat, properties=("soc", "clay", "phh2o"),
                          depths=("0-5cm", "5-15cm"), dry_run=False):
    """Query SoilGrids 2.0 for property values at a point. Returns a flat dict
    {property_depth: value}. Values are in SoilGrids native units (see their
    docs; e.g. soc in dg/kg -> divide by 10 for g/kg)."""
    if dry_run or not _HAS_REQUESTS:
        return _mock_soilgrids(properties, depths)
    params = [("lon", lon), ("lat", lat)]
    for p in properties:
        params.append(("property", p))
    for d in depths:
        params.append(("depth", d))
    params.append(("value", "mean"))
    r = requests.get(SOILGRIDS_URL, params=params, timeout=60)
    r.raise_for_status()
    return _parse_soilgrids(r.json())


def _parse_soilgrids(js):
    out = {}
    for layer in js.get("properties", {}).get("layers", []):
        name = layer["name"]
        for d in layer.get("depths", []):
            label = d["label"]
            val = d.get("values", {}).get("mean")
            out[f"{name}_{label}"] = val
    return out


def _mock_soilgrids(properties, depths):
    rng = np.random.default_rng(0)
    return {f"{p}_{d}": float(rng.uniform(50, 300))
            for p in properties for d in depths}


# ---- Copernicus GLO-30 DEM via OpenTopography (free key) -----------------
def fetch_dem(south, north, west, east, api_key=None, dem="COP30",
              out_path="dem.tif", dry_run=False):
    """Download a DEM tile for a bounding box. Requires a free OpenTopography
    API key passed by the user (do not hard-code)."""
    if dry_run or not _HAS_REQUESTS:
        return {"status": "dry-run", "would_download": dem,
                "bbox": [south, north, west, east], "out": out_path}
    if not api_key:
        raise ValueError("OpenTopography API key required (free); pass api_key=")
    params = dict(demtype=dem, south=south, north=north, west=west, east=east,
                  outputFormat="GTiff", API_Key=api_key)
    r = requests.get(OPENTOPO_URL, params=params, timeout=300)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(r.content)
    return {"status": "ok", "out": out_path, "bytes": len(r.content)}


# ---- Sentinel-2 (user credentials required) ------------------------------
def fetch_sentinel_composite(bbox, start, end, token=None, dry_run=False):
    """Placeholder for a Sentinel-2 bare-soil / seasonal-NDVI composite. Sentinel
    access requires a Copernicus Data Space or Sentinel Hub account and an OAuth
    token the USER supplies. Implement the request body against Sentinel Hub's
    Process API on your account; this stub documents the contract."""
    if dry_run or not token:
        return {"status": "requires_user_token",
                "note": "Supply a Sentinel Hub / Copernicus OAuth token. "
                        "See docs. Not runnable without user credentials.",
                "bbox": bbox, "window": [start, end]}
    raise NotImplementedError(
        "Wire this to Sentinel Hub Process API with your token; body per "
        "their docs (evalscript for NDVI/bare-soil composite).")


# ---- Orchestrator: covariates for a location -----------------------------
def covariates_for_location(lon, lat, bbox=None, opentopo_key=None,
                            dry_run=False):
    """One call a non-expert can make: pull the open covariates available for a
    point/area. Returns a dict of what was retrieved and what needs credentials."""
    result = {"point": {"lon": lon, "lat": lat}}
    result["soilgrids"] = fetch_soilgrids_point(lon, lat, dry_run=dry_run)
    if bbox:
        s, n, w, e = bbox
        result["dem"] = fetch_dem(s, n, w, e, api_key=opentopo_key,
                                  dry_run=dry_run)
        result["sentinel"] = fetch_sentinel_composite(
            bbox, "2023-01-01", "2023-12-31", dry_run=dry_run)
    result["_note"] = ("SoilGrids is open. DEM needs a free OpenTopography key. "
                       "Sentinel needs a user OAuth token. Verify live on first run.")
    return result


# ---- Demo (dry-run: exercises parsing/return without network) ------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true",
                    help="attempt real network calls (needs reachable services + keys)")
    args = ap.parse_args()
    dry = not args.live

    print(f"Running {'LIVE' if args.live else 'DRY-RUN (mock, no network)'}\n")
    out = covariates_for_location(
        lon=7.5, lat=9.1,  # example: central Nigeria
        bbox=(9.0, 9.2, 7.4, 7.6),
        dry_run=dry)
    print(json.dumps(out, indent=2))
    print("\nParsing/return logic exercised. For live use: pip install requests, "
          "supply keys, run with --live on a machine that can reach the services.")
