#!/usr/bin/env python3
"""dsm-model-fit :: model zoo (Python).

A judgment-first menu of soil-property learners behind ONE interface, so the
skill can recommend AND run whichever class fits the data/goal profile. This is
deliberately not "run 10 models, pick best RMSE" (that is automated overfitting).
The recommend_model() function encodes the decision logic from SKILL.md §3;
fit_predict() is the uniform runner.

Models: linear trend, RF, QRF (quantiles), XGBoost, LightGBM, SVR, Gaussian
process, GAM. Regression kriging wraps any trend (see model_fit_rk_qrf.py).

Every learner respects fold-internal preprocessing when driven by the CV engine
in cv_engine.py. Read SKILL.md before adapting.

Deps: scikit-learn (always), xgboost, lightgbm, pygam (optional; degrade
gracefully if absent).
"""
from __future__ import annotations
import numpy as np
import warnings

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.svm import SVR
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel

# optional deps -----------------------------------------------------------
try:
    from xgboost import XGBRegressor
    _HAS_XGB = True
except Exception:  # noqa
    _HAS_XGB = False
try:
    from lightgbm import LGBMRegressor
    _HAS_LGBM = True
except Exception:  # noqa
    _HAS_LGBM = False
try:
    from pygam import LinearGAM
    _HAS_GAM = True
except Exception:  # noqa
    _HAS_GAM = False


def capabilities():
    """What this install can actually run. The skill should check this before
    recommending a model it cannot execute here."""
    return dict(linear=True, rf=True, qrf=True, svr=True, gp=True,
                xgboost=_HAS_XGB, lightgbm=_HAS_LGBM, gam=_HAS_GAM)


# ---- Decision logic (SKILL.md §3, widened beyond RK/RF/QRF) ---------------
def recommend_model(n, n_covars, needs_intervals, skewed,
                    strong_spatial_resid, has_gpu=False):
    """Return an ordered list of (model, reason) recommendations. Judgment, not
    a leaderboard. The first entry is the suggested starting point."""
    recs = []

    if needs_intervals:
        recs.append(("qrf",
            "Per-pixel intervals requested; QRF gives a conditional "
            "distribution without a distributional assumption."))
        recs.append(("gp",
            "Gaussian process gives a principled posterior variance if n is "
            "small-to-moderate and the surface is smooth (heavier to fit)."))

    if n < 50:
        recs.append(("linear",
            f"n={n} is small; a linear/GLM trend plus kriging is more stable "
            "than a deep ensemble that will overfit."))
        recs.append(("gp",
            "Gaussian process is sample-efficient at small n."))
        recs.append(("svr",
            "SVR is competitive at small n but sensitive to kernel/C tuning "
            "(tune inside the fold)."))
    else:
        recs.append(("rf",
            "RF is a strong, hard-to-beat baseline at this sample size; start "
            "here and justify any move away from it."))
        if _HAS_XGB:
            recs.append(("xgboost",
                "Gradient boosting often edges RF and handles gappy covariates; "
                "watch early-stopping leakage (tune on an inner fold, not test)."))
        if _HAS_LGBM:
            recs.append(("lightgbm",
                "LightGBM is faster on large covariate stacks with similar "
                "accuracy to XGBoost."))

    if n_covars > 15:
        recs.append(("gam",
            "Many covariates but interpretability wanted: a GAM gives smooth, "
            "inspectable terms; pair with feature selection.") if _HAS_GAM else
            ("rf", "Many covariates: use RF with forward feature selection to "
                   "prune collinear DEM derivatives."))

    if strong_spatial_resid:
        recs.append(("+kriging",
            "Residuals remain autocorrelated: wrap the chosen trend in "
            "regression kriging (kriged residual correction)."))

    if skewed:
        recs.append(("~transform",
            "Target is right-skewed: fit a Yeo-Johnson/log transform INSIDE the "
            "training fold; back-transform quantiles (QRF) or smear-correct means."))

    if not has_gpu:
        recs.append(("!note",
            "Deep learning / transfer learning omitted: no GPU declared. They "
            "are optional-if-hardware, not a default recommendation."))

    # de-duplicate keeping order
    seen, ordered = set(), []
    for m, r in recs:
        if m not in seen:
            ordered.append((m, r)); seen.add(m)
    return ordered


# ---- Uniform learner factory ---------------------------------------------
def make_model(kind, **kw):
    kind = kind.lower()
    if kind == "linear":
        return LinearRegression()
    if kind in ("rf", "qrf"):
        return RandomForestRegressor(n_estimators=kw.get("n_estimators", 500),
                                     min_samples_leaf=kw.get("min_samples_leaf", 5),
                                     oob_score=True, n_jobs=-1)
    if kind == "svr":
        return SVR(C=kw.get("C", 10.0), gamma=kw.get("gamma", "scale"))
    if kind == "gp":
        kernel = (ConstantKernel(1.0) * RBF(length_scale=1.0)
                  + WhiteKernel(noise_level=1.0))
        return GaussianProcessRegressor(kernel=kernel, normalize_y=True,
                                        alpha=kw.get("alpha", 1e-6))
    if kind == "xgboost":
        if not _HAS_XGB:
            raise RuntimeError("xgboost not installed")
        return XGBRegressor(n_estimators=kw.get("n_estimators", 600),
                            max_depth=kw.get("max_depth", 5),
                            learning_rate=kw.get("learning_rate", 0.05),
                            subsample=0.8, colsample_bytree=0.8, n_jobs=-1)
    if kind == "lightgbm":
        if not _HAS_LGBM:
            raise RuntimeError("lightgbm not installed")
        return LGBMRegressor(n_estimators=kw.get("n_estimators", 600),
                             learning_rate=kw.get("learning_rate", 0.05),
                             subsample=0.8, verbose=-1)
    if kind == "gam":
        if not _HAS_GAM:
            raise RuntimeError("pygam not installed")
        return LinearGAM()
    raise ValueError(f"unknown model kind: {kind}")


# ---- QRF quantiles from any sklearn forest (Meinshausen leaf harvest) -----
def qrf_quantiles(rf, Xtr, ytr, Xnew, qs=(0.05, 0.5, 0.95)):
    ytr = np.asarray(ytr)
    leaves_tr = rf.apply(Xtr)
    leaves_new = rf.apply(Xnew)
    out = np.empty((len(Xnew), len(qs)))
    for i in range(len(Xnew)):
        mask = (leaves_tr == leaves_new[i]).any(axis=1)
        pool = ytr[mask]
        out[i] = np.quantile(pool, qs) if pool.size else np.nan
    return out


def fit_predict(kind, Xtr, ytr, Xnew):
    """Uniform fit+predict. Returns dict with 'pred' and optional 'quantiles'."""
    m = make_model(kind)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m.fit(Xtr, ytr)
        pred = m.predict(Xnew)
    res = {"pred": np.asarray(pred), "model": m}
    if kind.lower() == "qrf":
        res["quantiles"] = qrf_quantiles(m, Xtr, ytr, Xnew)
    return res


# ---- Demo ----------------------------------------------------------------
if __name__ == "__main__":
    print("Capabilities:", capabilities())
    rng = np.random.default_rng(0)
    n = 200
    X = rng.random((n, 4))
    y = np.exp(1 + 2 * X[:, 0] + X[:, 1] + 0.3 * rng.standard_normal(n))
    Xtr, ytr, Xte, yte = X[:150], y[:150], X[150:], y[150:]

    print("\nRecommendation (n=150, 4 covars, intervals=True, skewed=True):")
    for mdl, why in recommend_model(150, 4, needs_intervals=True, skewed=True,
                                    strong_spatial_resid=False):
        print(f"  [{mdl}] {why}")

    print("\nRunning every available learner on synthetic data:")
    for k in ["linear", "rf", "qrf", "svr", "gp", "xgboost", "lightgbm", "gam"]:
        if not capabilities().get(k.replace("qrf", "qrf"), True):
            print(f"  {k:9s}  (unavailable)"); continue
        try:
            r = fit_predict(k, Xtr, ytr, Xte)
            rmse = float(np.sqrt(np.mean((yte - r["pred"]) ** 2)))
            extra = " +quantiles" if "quantiles" in r else ""
            print(f"  {k:9s}  RMSE={rmse:6.3f}{extra}")
        except Exception as e:  # noqa
            print(f"  {k:9s}  skipped ({e})")
