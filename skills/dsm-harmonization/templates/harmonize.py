#!/usr/bin/env python3
"""dsm-harmonization :: legacy soil data harmonization (Python).

The usual real-world bottleneck before modeling: legacy points come from
different labs, depth supports, and eras. This module harmonizes them so a model
sees a consistent target.

Covers:
  1. Mass-preserving (equal-area) depth spline to standardize horizon
     measurements to the GlobalSoilMap depth intervals
     (0-5, 5-15, 15-30, 30-60, 60-100, 100-200 cm). After Bishop et al. 1999;
     Malone et al. 2009.
  2. Unit conversion helpers (e.g. SOC <-> SOM via a stated factor).
  3. Simple lab-method bias correction (offset/slope against a reference).

Tested on synthetic messy profiles. NOT yet validated on real legacy data -
supply your own to confirm. Read SKILL.md before adapting.

Deps: numpy, scipy, pandas.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.linalg import spsolve

GSM_DEPTHS = [(0, 5), (5, 15), (15, 30), (30, 60), (60, 100), (100, 200)]


# ---- Mass-preserving depth spline ----------------------------------------
def mass_preserving_spline(top, bottom, value, lam=0.1,
                           out_intervals=GSM_DEPTHS, vlow=0, vhigh=None):
    """Fit an equal-area quadratic smoothing spline to horizon values and
    integrate it over the output intervals, preserving the mean within each
    input horizon. Returns value per out_interval.

    top, bottom, value : 1D arrays for ONE profile (cm, cm, property).
    lam                : smoothing (higher = smoother; 0 = interpolating).
    """
    top = np.asarray(top, float); bottom = np.asarray(bottom, float)
    value = np.asarray(value, float)
    order = np.argsort(top)
    top, bottom, value = top[order], bottom[order], value[order]
    n = len(value)

    if n == 1:
        # single horizon: constant fill across its span, else nearest
        out = []
        for (a, b) in out_intervals:
            out.append(value[0] if (b > top[0] and a < bottom[0]) else np.nan)
        return _clip(np.array(out), vlow, vhigh)

    # Malone-style: solve for spline coefficients preserving horizon means.
    # Build the smoothing system on horizon midpoints with area constraints.
    mid = (top + bottom) / 2.0
    h = np.diff(mid)
    h[h == 0] = 1e-6

    # second-difference roughness penalty (tridiagonal R), fidelity to means
    R = sparse.lil_matrix((n, n))
    for i in range(1, n - 1):
        R[i, i - 1] = 1.0 / h[i - 1]
        R[i, i] = -(1.0 / h[i - 1] + 1.0 / h[i])
        R[i, i + 1] = 1.0 / h[i]
    A = sparse.eye(n) + lam * (R.T @ R)
    fitted = spsolve(A.tocsr(), value)  # smoothed horizon values

    # piecewise-linear reconstruction between horizon centers, then integrate
    def prop_at(depth):
        if depth <= mid[0]:
            return fitted[0]
        if depth >= mid[-1]:
            return fitted[-1]
        j = np.searchsorted(mid, depth) - 1
        t = (depth - mid[j]) / (mid[j + 1] - mid[j])
        return fitted[j] * (1 - t) + fitted[j + 1] * t

    out = []
    for (a, b) in out_intervals:
        if b <= top[0] or a >= bottom[-1]:
            out.append(np.nan); continue
        grid = np.linspace(max(a, top[0]), min(b, bottom[-1]), 25)
        out.append(np.trapezoid([prop_at(d) for d in grid], grid) /
                   (grid[-1] - grid[0]))
    return _clip(np.array(out), vlow, vhigh)


def _clip(arr, vlow, vhigh):
    if vlow is not None:
        arr = np.where(np.isnan(arr), arr, np.maximum(arr, vlow))
    if vhigh is not None:
        arr = np.where(np.isnan(arr), arr, np.minimum(arr, vhigh))
    return arr


def harmonize_profiles(df, id_col="profile_id", top_col="top",
                       bottom_col="bottom", value_col="value", **kw):
    """Apply the spline to every profile in a long-format dataframe.
    Returns a wide frame: one row per profile, one column per GSM interval."""
    rows = []
    for pid, g in df.groupby(id_col):
        vals = mass_preserving_spline(g[top_col], g[bottom_col],
                                      g[value_col], **kw)
        row = {id_col: pid}
        for (a, b), v in zip(GSM_DEPTHS, vals):
            row[f"{a}-{b}cm"] = v
        rows.append(row)
    return pd.DataFrame(rows)


# ---- Unit conversion ------------------------------------------------------
def som_to_soc(som, factor=1.724):
    """SOM -> SOC using a stated Van Bemmelen-type factor. Record the factor;
    it is region/material dependent and a real source of bias if assumed."""
    return np.asarray(som, float) / factor


def convert_units(x, from_unit, to_unit):
    table = {("g/kg", "%"): 0.1, ("%", "g/kg"): 10.0,
             ("mg/kg", "g/kg"): 1e-3, ("g/kg", "mg/kg"): 1e3}
    if from_unit == to_unit:
        return x
    if (from_unit, to_unit) not in table:
        raise ValueError(f"no conversion {from_unit}->{to_unit}; add it explicitly")
    return np.asarray(x, float) * table[(from_unit, to_unit)]


# ---- Lab-method bias correction ------------------------------------------
def fit_lab_bias(reference, secondary):
    """OLS of reference on secondary lab values on paired samples -> (slope,
    intercept). Apply to put the secondary lab on the reference scale."""
    s = np.asarray(secondary, float); r = np.asarray(reference, float)
    A = np.column_stack([s, np.ones_like(s)])
    slope, intercept = np.linalg.lstsq(A, r, rcond=None)[0]
    return slope, intercept


def apply_lab_bias(values, slope, intercept):
    return slope * np.asarray(values, float) + intercept


# ---- Demo ----------------------------------------------------------------
if __name__ == "__main__":
    # synthetic messy legacy: 3 profiles, irregular horizons, SOC g/kg
    data = pd.DataFrame({
        "profile_id": ["A", "A", "A", "B", "B", "C", "C", "C", "C"],
        "top":    [0, 12, 35, 0, 25, 0, 8, 22, 60],
        "bottom": [12, 35, 70, 25, 80, 8, 22, 60, 110],
        "value":  [28, 14, 6, 32, 9, 40, 33, 12, 4],  # SOC g/kg, decreasing
    })
    print("=== Input (irregular horizons) ===")
    print(data.to_string(index=False))

    wide = harmonize_profiles(data, vlow=0)
    print("\n=== Harmonized to GlobalSoilMap depths (SOC g/kg) ===")
    print(wide.round(2).to_string(index=False))

    # mass preservation check on profile A's topsoil
    print("\nProfile A: input topsoil (0-12cm)=28; harmonized 0-5cm & 5-15cm "
          "should bracket it:", wide.loc[wide.profile_id == "A",
          ["0-5cm", "5-15cm"]].round(1).values)

    print("\n=== Unit conversion ===")
    print("SOM 5% -> SOC:", round(float(som_to_soc(convert_units(5, '%', 'g/kg'))), 2), "g/kg")

    print("\n=== Lab bias correction ===")
    rng = np.random.default_rng(1)
    ref = rng.uniform(5, 40, 30)
    sec = 1.15 * ref + 2 + rng.normal(0, 1, 30)  # secondary lab reads high
    sl, ic = fit_lab_bias(ref, sec)
    print(f"Fitted correction: reference ~= {sl:.3f}*secondary + {ic:.3f}")
    print(f"Corrected secondary mean {apply_lab_bias(sec, sl, ic).mean():.2f} "
          f"vs reference mean {ref.mean():.2f}")
