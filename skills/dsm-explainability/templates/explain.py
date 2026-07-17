#!/usr/bin/env python3
"""dsm-explainability :: model interpretation for non-technical stakeholders.

A policymaker will not trust a black-box map. This module turns a fitted model
into (1) ranked covariate importance, (2) partial-dependence direction, and
(3) a plain-language summary a non-modeler can read.

SHAP is used when available (exact for tree models); a permutation-importance
fallback keeps the module running without it. Read SKILL.md before adapting.

Deps: numpy, scikit-learn; shap optional.
"""
from __future__ import annotations
import numpy as np
from sklearn.inspection import permutation_importance, partial_dependence

try:
    import shap
    _HAS_SHAP = True
except Exception:  # noqa
    _HAS_SHAP = False


def covariate_importance(model, X, y, feature_names, use_shap=True):
    """Ranked importance. SHAP mean-|value| for tree models if available,
    else permutation importance. Returns list of (name, score) descending."""
    if use_shap and _HAS_SHAP:
        try:
            expl = shap.TreeExplainer(model)
            sv = expl.shap_values(X)
            score = np.abs(sv).mean(axis=0)
            imp = sorted(zip(feature_names, score), key=lambda t: -t[1])
            return imp, "SHAP (mean |value|)"
        except Exception:  # noqa
            pass
    r = permutation_importance(model, X, y, n_repeats=10, random_state=1)
    imp = sorted(zip(feature_names, r.importances_mean), key=lambda t: -t[1])
    return imp, "permutation importance"


def dependence_direction(model, X, feature_names, top_k=3):
    """Sign of the trend of each top covariate's partial dependence: does the
    soil property rise or fall as this covariate rises?"""
    out = {}
    for i in range(min(top_k, len(feature_names))):
        pd_ = partial_dependence(model, X, [i], kind="average")
        vals = pd_["average"][0]
        slope = np.polyfit(range(len(vals)), vals, 1)[0]
        out[feature_names[i]] = ("increase" if slope > 0 else "decrease")
    return out


def plain_language_summary(importance, method, directions, target="the soil property",
                           region="this area"):
    """Assemble a stakeholder-readable paragraph. Direct voice, no jargon."""
    total = sum(max(s, 0) for _, s in importance) or 1.0
    top = importance[:3]
    lead = top[0][0]
    shares = ", ".join(f"{n} ({100*max(s,0)/total:.0f}%)" for n, s in top)
    dir_txt = "; ".join(
        f"{target} tends to {d} where {n} is higher"
        for n, d in directions.items())
    return (
        f"For {region}, the map of {target} relies most on {shares} "
        f"(ranked by {method}). {lead.capitalize()} is the dominant driver. "
        f"In terms of direction, {dir_txt}. Covariates outside this top set "
        f"contribute little and could be dropped without much loss. This "
        f"explanation describes what the model uses, not proven physical "
        f"causation.")


# ---- Demo ----------------------------------------------------------------
if __name__ == "__main__":
    from sklearn.ensemble import RandomForestRegressor
    rng = np.random.default_rng(4)
    n = 400
    rain = rng.uniform(400, 1200, n)
    slope = rng.uniform(0, 30, n)
    ndvi = rng.uniform(0.1, 0.8, n)
    noise_cov = rng.random(n)
    names = ["rainfall", "slope", "ndvi", "noise_layer"]
    X = np.column_stack([rain, slope, ndvi, noise_cov])
    # SOC rises with rainfall & ndvi, falls with slope; noise_layer irrelevant
    soc = (0.02 * rain + 15 * ndvi - 0.3 * slope + rng.normal(0, 2, n))

    model = RandomForestRegressor(n_estimators=400, n_jobs=-1).fit(X, soc)

    imp, method = covariate_importance(model, X, soc, names)
    print(f"=== Covariate importance ({method}) ===")
    for nme, s in imp:
        print(f"  {nme:12s} {s:8.3f}")

    dirs = dependence_direction(model, X, names, top_k=3)
    print("\n=== Direction of dependence (top 3) ===")
    for nme, d in dirs.items():
        print(f"  SOC {d} as {nme} rises")

    print("\n=== Plain-language summary for stakeholders ===")
    print(plain_language_summary(imp, method, dirs, target="soil organic carbon",
                                 region="the study catchment"))
