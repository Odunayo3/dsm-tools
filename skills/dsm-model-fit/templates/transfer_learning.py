#!/usr/bin/env python3
"""dsm-model-fit :: transfer learning for data-sparse regions (Python).

For the researcher with few local samples: borrow strength from a data-rich
source region (e.g. a continental dataset) and adapt to a data-sparse target.
This is one of the more promising directions for making DSM feasible where
sampling budgets are small.

Three strategies, lightest first:
  1. Instance weighting  - weight source samples by similarity to the target
     covariate distribution, train one model on the pooled, weighted data.
  2. Feature-based fine-tuning - fit a model on source, then refit/adjust on
     the small target set (warm start).
  3. Deep transfer (documented, OPTIONAL, needs GPU) - pretrain a network on
     source, fine-tune final layers on target. Not run here.

Applicability gating (AOA) is essential: transfer is only trustworthy where the
target covariates overlap the source feature space.

CPU-runnable toy below. Deep transfer is documented, not executed. Read
SKILL.md before adapting. Deps: numpy, scikit-learn (torch/tensorflow optional
for strategy 3).
"""
from __future__ import annotations
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.neighbors import NearestNeighbors


# ---- Strategy 1: instance weighting by target similarity -----------------
def similarity_weights(X_source, X_target, bandwidth=None):
    """Weight each source sample by proximity to the target distribution
    (kernel density of target in source-standardized space)."""
    mu, sd = X_source.mean(0), X_source.std(0)
    sd[sd == 0] = 1
    zs = (X_source - mu) / sd
    zt = (X_target - mu) / sd
    nn = NearestNeighbors(n_neighbors=min(5, len(zt))).fit(zt)
    d, _ = nn.kneighbors(zs)
    dmean = d.mean(1)
    h = bandwidth or np.median(dmean)
    w = np.exp(-(dmean ** 2) / (2 * h ** 2))
    return w / w.mean()


def transfer_instance_weighting(X_source, y_source, X_target, y_target, X_new):
    w = similarity_weights(X_source, X_target)
    X = np.vstack([X_source, X_target])
    y = np.concatenate([y_source, y_target])
    sample_w = np.concatenate([w, np.full(len(y_target), w.max() + 1.0)])
    m = RandomForestRegressor(n_estimators=400, n_jobs=-1)
    m.fit(X, y, sample_weight=sample_w)
    return m.predict(X_new)


# ---- Strategy 2: fit on source, fine-tune on target (warm start) ---------
def transfer_finetune(X_source, y_source, X_target, y_target, X_new):
    """Boosting warm-started on source, additional stages fit on target -
    a simple, faithful feature-based fine-tune that runs on CPU."""
    base = GradientBoostingRegressor(n_estimators=300, learning_rate=0.05,
                                     max_depth=3, warm_start=True)
    base.fit(X_source, y_source)
    # add target-fit stages on top of the source-trained ensemble
    base.set_params(n_estimators=400)
    Xc = np.vstack([X_target, X_target])  # emphasize target in added stages
    yc = np.concatenate([y_target, y_target])
    base.fit(Xc, yc)
    return base.predict(X_new)


# ---- Applicability gate (transfer is only valid inside source feature space)
def transfer_aoa(X_source, X_new, quantile_thresh=0.95):
    mu, sd = X_source.mean(0), X_source.std(0)
    sd[sd == 0] = 1
    zs = (X_source - mu) / sd
    zn = (X_new - mu) / sd
    nn = NearestNeighbors(n_neighbors=2).fit(zs)
    dtr = nn.kneighbors(zs)[0][:, 1]
    dbar = dtr.mean()
    dnew = NearestNeighbors(n_neighbors=1).fit(zs).kneighbors(zn)[0].ravel()
    thresh = np.quantile(dtr / dbar, quantile_thresh)
    di = dnew / dbar
    return di <= thresh, di, thresh


# ---- Strategy 3 (documented, NOT executed) -------------------------------
DEEP_TRANSFER_NOTE = """
Deep transfer (optional; needs GPU for realistic sizes):
  1. Pretrain a network (MLP on covariate vectors, or CNN on covariate patches
     to exploit spatial context) on the data-rich SOURCE region.
  2. Freeze early layers; fine-tune the final layer(s) on the small TARGET set.
  3. Gate predictions by transfer_aoa(); report where the target leaves the
     source feature space.
Frameworks: PyTorch or TensorFlow. Provide --device cuda. On CPU this is only
feasible for toy sizes, so it is intentionally not run in this template.
"""


# ---- Demo (CPU) ----------------------------------------------------------
if __name__ == "__main__":
    rng = np.random.default_rng(11)

    def make_region(n, shift, seed_noise):
        x1 = rng.uniform(0, 1, n) + shift
        x2 = rng.uniform(0, 1, n)
        y = 10 * x1 + 5 * x2 + rng.normal(0, seed_noise, n)
        return np.column_stack([x1, x2]), y

    # data-rich source, data-sparse target (slightly shifted covariates)
    Xs, ys = make_region(600, shift=0.0, seed_noise=1.0)
    Xt, yt = make_region(25, shift=0.15, seed_noise=1.0)   # only 25 target pts
    Xnew, ynew = make_region(200, shift=0.15, seed_noise=1.0)

    def rmse(a, b):
        return float(np.sqrt(np.mean((a - b) ** 2)))

    # baselines
    m_target_only = RandomForestRegressor(n_estimators=400, n_jobs=-1).fit(Xt, yt)
    r_target_only = rmse(ynew, m_target_only.predict(Xnew))
    m_source_only = RandomForestRegressor(n_estimators=400, n_jobs=-1).fit(Xs, ys)
    r_source_only = rmse(ynew, m_source_only.predict(Xnew))

    r_iw = rmse(ynew, transfer_instance_weighting(Xs, ys, Xt, yt, Xnew))
    r_ft = rmse(ynew, transfer_finetune(Xs, ys, Xt, yt, Xnew))

    inside, di, thr = transfer_aoa(Xs, Xnew)

    print("=== Transfer learning on data-sparse target (n_target=25) ===")
    print(f"  target-only RF        RMSE={r_target_only:6.3f}  (too few points)")
    print(f"  source-only RF        RMSE={r_source_only:6.3f}  (covariate shift)")
    print(f"  instance weighting    RMSE={r_iw:6.3f}")
    print(f"  source+target finetune RMSE={r_ft:6.3f}")
    print(f"\n  {100*inside.mean():.0f}% of prediction points inside source AOA "
          f"(DI threshold {thr:.2f}) - transfer trustworthy there.")
    print(DEEP_TRANSFER_NOTE)
