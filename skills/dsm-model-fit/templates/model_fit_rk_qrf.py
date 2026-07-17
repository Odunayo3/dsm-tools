#!/usr/bin/env python3
"""dsm-model-fit :: regression kriging + quantile regression forest (Python parity).

Mirrors templates/model_fit_rk_qrf.R. Same discipline: every data-dependent
preprocessing step is fit INSIDE the training fold and applied frozen to the
held-out fold, preventing leakage failure modes F1-F3 in SKILL.md.

Dependencies: numpy, scikit-learn, pykrige. QRF quantiles are computed directly
from a RandomForestRegressor by harvesting per-leaf training responses
(Meinshausen 2006), so no quantile-forest dependency is required.

Read SKILL.md before adapting. The judgment in sections 3-8 matters more than
this code, which only partially enforces it.
"""
from __future__ import annotations
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.cluster import KMeans
from sklearn.preprocessing import PowerTransformer
from pykrige.ok import OrdinaryKriging


# ---- 1. Leakage-safe preprocessing, fit on TRAIN only --------------------
class TargetTransform:
    """Yeo-Johnson fit on training target only; apply/invert are frozen."""

    def __init__(self):
        self._pt = PowerTransformer(method="yeo-johnson", standardize=False)

    def fit(self, y_train):
        self._pt.fit(np.asarray(y_train).reshape(-1, 1))
        return self

    def apply(self, y):
        return self._pt.transform(np.asarray(y).reshape(-1, 1)).ravel()

    def invert(self, z):
        return self._pt.inverse_transform(np.asarray(z).reshape(-1, 1)).ravel()


def fit_factor_levels(df_cols: dict, factor_cols):
    """Store training levels; unseen predict levels -> NaN code, never a new
    column (F2). df_cols maps column name -> 1D array."""
    return {c: np.unique(df_cols[c]) for c in factor_cols}


def encode_factor(values, levels):
    """Integer-code against fixed training levels; unseen -> -1 (mask/lump)."""
    lut = {v: i for i, v in enumerate(levels)}
    return np.array([lut.get(v, -1) for v in values])


# ---- 2. AOA dissimilarity index (SKILL.md §7) ----------------------------
def aoa_di(train_X, new_X, quantile_thresh=0.95):
    mu = train_X.mean(0)
    sd = train_X.std(0)
    sd[sd == 0] = 1.0
    ztr = (train_X - mu) / sd
    znew = (new_X - mu) / sd

    def nn_dist(A, B, self_=False):
        out = np.empty(len(A))
        for i, r in enumerate(A):
            d = np.sqrt(((B - r) ** 2).sum(1))
            if self_:
                d = d[d > 0]
            out[i] = d.min()
        return out

    dbar = nn_dist(ztr, ztr, self_=True).mean()
    di_train = nn_dist(ztr, ztr, self_=True) / dbar
    di_new = nn_dist(znew, ztr) / dbar
    thresh = np.quantile(di_train, quantile_thresh)
    return di_new, thresh, di_new <= thresh


# ---- 3. Regression kriging: RF trend + kriged residuals ------------------
def fit_rk(Xtr, ytr, coords_tr, nugget_sill_skip=0.95):
    trend = RandomForestRegressor(n_estimators=500, oob_score=True, n_jobs=-1)
    trend.fit(Xtr, ytr)
    resid = ytr - trend.oob_prediction_  # OOB residuals, not in-sample

    krige_ok, OK = False, None
    try:
        OK = OrdinaryKriging(coords_tr[:, 0], coords_tr[:, 1], resid,
                             variogram_model="spherical", enable_plotting=False)
        psill = OK.variogram_model_parameters[0]
        nugget = OK.variogram_model_parameters[2]
        sill = psill + nugget
        ratio = nugget / sill if sill > 0 else 1.0
        krige_ok = ratio < nugget_sill_skip
        print(f"[RK] nugget/sill = {ratio:.2f} -> kriging "
              f"{'USED' if krige_ok else 'SKIPPED (pure nugget)'}")
    except Exception as e:  # noqa
        print(f"[RK] variogram fit failed ({e}); trend only")
    return dict(trend=trend, OK=OK, krige_ok=krige_ok)


def predict_rk(model, Xnew, coords_new):
    trend_pred = model["trend"].predict(Xnew)
    if not model["krige_ok"]:
        return trend_pred
    kr, _ = model["OK"].execute("points", coords_new[:, 0], coords_new[:, 1])
    return trend_pred + np.asarray(kr)


# ---- 4. QRF from a plain RandomForest (Meinshausen leaf harvesting) ------
class QRF:
    def fit(self, Xtr, ytr):
        self.rf = RandomForestRegressor(n_estimators=500, min_samples_leaf=5,
                                        n_jobs=-1)
        self.rf.fit(Xtr, ytr)
        self.ytr = np.asarray(ytr)
        self.leaves_tr = self.rf.apply(Xtr)  # (n_train, n_trees)
        return self

    def predict_quantiles(self, Xnew, qs=(0.05, 0.5, 0.95)):
        leaves_new = self.rf.apply(Xnew)
        out = np.empty((len(Xnew), len(qs)))
        for i in range(len(Xnew)):
            # training responses sharing a leaf with x, pooled across trees
            mask = (self.leaves_tr == leaves_new[i]).any(axis=1)
            pool = self.ytr[mask]
            out[i] = np.quantile(pool, qs) if pool.size else np.nan
        return out


# ---- 5. Spatial fold assignment ------------------------------------------
def spatial_folds(coords, k=5, seed=1):
    cs = (coords - coords.mean(0)) / coords.std(0)
    return KMeans(n_clusters=k, random_state=seed, n_init=10).fit_predict(cs)


def rmse(o, p):
    return float(np.sqrt(np.mean((o - p) ** 2)))


def coverage(o, lo, hi):
    return float(np.mean((o >= lo) & (o <= hi)))


# ---- 6. Nested, fold-internal CV driver ----------------------------------
def run_cv(X, y, coords, k=5):
    folds = spatial_folds(coords, k=k)
    rows = []
    for f in np.unique(folds):
        tr, te = folds != f, folds == f
        # preprocessing fit on TRAIN fold only (F1)
        tf = TargetTransform().fit(y[tr])
        ytr_t = tf.apply(y[tr])

        rk = fit_rk(X[tr], ytr_t, coords[tr])
        p_rk = tf.invert(predict_rk(rk, X[te], coords[te]))

        qrf = QRF().fit(X[tr], ytr_t)
        q = qrf.predict_quantiles(X[te])
        lo, med, hi = tf.invert(q[:, 0]), tf.invert(q[:, 1]), tf.invert(q[:, 2])

        _, _, inside = aoa_di(X[tr], X[te])
        rows.append(dict(fold=int(f), rmse_rk=rmse(y[te], p_rk),
                         rmse_qrf=rmse(y[te], med),
                         cov90=coverage(y[te], lo, hi),
                         pct_inside_aoa=float(inside.mean())))
    return rows


# ---- 7. Demo on synthetic data -------------------------------------------
if __name__ == "__main__":
    rng = np.random.default_rng(42)
    n = 300
    x, yc = rng.random(n), rng.random(n)
    dem = 100 * x + 50 * yc + rng.normal(0, 5, n)
    slope = np.abs(rng.normal(5, 2, n))
    ndvi = 0.3 + 0.4 * yc + rng.normal(0, 0.05, n)
    soc = np.exp(1 + 0.01 * dem + 0.5 * ndvi + 0.3 * np.sin(6 * x)
                 + rng.normal(0, 0.2, n))

    X = np.column_stack([dem, slope, ndvi])
    coords = np.column_stack([x, yc])
    res = run_cv(X, soc, coords, k=5)

    print("\n--- Spatial CV results ---")
    print(f"{'fold':>4} {'rmse_rk':>8} {'rmse_qrf':>9} {'cov90':>6} {'in_aoa':>7}")
    for r in res:
        print(f"{r['fold']:>4} {r['rmse_rk']:>8.3f} {r['rmse_qrf']:>9.3f} "
              f"{r['cov90']:>6.3f} {r['pct_inside_aoa']:>7.3f}")
    mrk = np.mean([r["rmse_rk"] for r in res])
    mqrf = np.mean([r["rmse_qrf"] for r in res])
    mcov = np.mean([r["cov90"] for r in res])
    print(f"\nMean RMSE  RK={mrk:.3f}  QRF={mqrf:.3f} | "
          f"mean 90% coverage={mcov:.2f}")
