#!/usr/bin/env python3
"""dsm-validation :: validation engine (Python).

Chooses AND runs an honest map-accuracy assessment, parameterized by sample
size and spatial structure. Encodes the current debate rather than resolving it
(SKILL.md §2): random k-fold is optimistic under clustering; spatial CV can be
over-pessimistic (Wadoux et al. 2021); kNNDM matches CV geometry to the
prediction task (Linnenbrink et al. 2024); design-based validation with an
independent probability sample is cleanest when affordable.

Includes a clustering diagnostic so the recommendation is driven by the data,
not a guess. Read SKILL.md before adapting.

Deps: numpy, scikit-learn.
"""
from __future__ import annotations
import numpy as np
from sklearn.cluster import KMeans
from sklearn.neighbors import NearestNeighbors


# ---- Clustering diagnostic -----------------------------------------------
def clustering_index(coords):
    """Clark-Evans-style nearest-neighbour index R. R<1 clustered, ~1 random,
    >1 dispersed. Drives the validation recommendation."""
    coords = np.asarray(coords, float)
    N = len(coords)
    nn = NearestNeighbors(n_neighbors=2).fit(coords)
    d, _ = nn.kneighbors(coords)
    mean_nn = d[:, 1].mean()
    # area from bounding box; density-based expected NN distance
    area = np.ptp(coords[:, 0]) * np.ptp(coords[:, 1])
    expected = 0.5 / np.sqrt(N / area) if area > 0 else np.nan
    return mean_nn / expected if expected and np.isfinite(expected) else np.nan


def recommend_validation(n, coords, can_draw_independent_sample):
    """Concrete validation strategy from n + measured clustering."""
    R = clustering_index(coords)
    clustered = np.isfinite(R) and R < 0.8
    recs = [f"Clustering index R={R:.2f} "
            f"({'clustered' if clustered else 'roughly random/dispersed'})."]

    if clustered:
        if can_draw_independent_sample:
            recs.append(
                "Clustered data: prefer DESIGN-BASED validation with an "
                "independent probability sample as the headline accuracy "
                "(Wadoux et al. 2021). Report CV only as secondary.")
        else:
            recs.append(
                "Clustered data, no independent sample: use kNNDM CV to match "
                "fold geometry to the prediction task (Linnenbrink et al. 2024). "
                "Do NOT headline random k-fold - it is optimistic here.")
        recs.append(
            "Spatial/block CV is acceptable for sensitivity but can be "
            "over-pessimistic; report it as a bound, not the truth.")
    else:
        recs.append(
            "Roughly even sampling: random k-fold is defensible; still run "
            "block CV as a sensitivity check.")

    if n < 60:
        recs.append(
            f"n={n} is small: use NESTED CV (inner loop for tuning/feature "
            "selection, outer for accuracy) or the outer estimate is optimistic. "
            "Consider repeated CV to stabilize the estimate.")
    return recs


# ---- Fold builders --------------------------------------------------------
def random_kfold(n, k=5, seed=1):
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    return np.array_split(idx, k)


def spatial_block_folds(coords, k=5, seed=1):
    lab = KMeans(n_clusters=k, random_state=seed, n_init=10).fit_predict(
        (coords - coords.mean(0)) / coords.std(0))
    return [np.where(lab == f)[0] for f in np.unique(lab)]


def knndm_folds(coords, prediction_coords, k=5, seed=1, max_iter=40):
    """k-fold nearest-neighbour distance matching (simplified).
    Reassign spatial-block folds to make the train->test NN-distance
    distribution resemble the train->prediction-point NN-distance distribution.
    Full method: Linnenbrink et al. 2024 (CAST::knndm)."""
    coords = np.asarray(coords, float)
    pred = np.asarray(prediction_coords, float)
    # target distribution: sample-to-prediction NN distances
    nn_pred = NearestNeighbors(n_neighbors=1).fit(pred)
    d_target = np.sort(nn_pred.kneighbors(coords)[0].ravel())

    folds = spatial_block_folds(coords, k=k, seed=seed)
    rng = np.random.default_rng(seed)

    def w1(a, b):  # 1-Wasserstein between two sorted empirical CDFs
        a = np.sort(a); b = np.sort(b)
        q = np.linspace(0, 1, 100)
        return np.mean(np.abs(np.quantile(a, q) - np.quantile(b, q)))

    def cv_nn_dist(folds):
        ds = []
        for te in folds:
            tr = np.setdiff1d(np.arange(len(coords)), te)
            nn = NearestNeighbors(n_neighbors=1).fit(coords[tr])
            ds.append(nn.kneighbors(coords[te])[0].ravel())
        return np.concatenate(ds)

    best = folds; best_w = w1(cv_nn_dist(folds), d_target)
    for _ in range(max_iter):
        # random point reassignment to reduce distribution mismatch
        f_from, f_to = rng.integers(len(folds), size=2)
        if f_from == f_to or len(best[f_from]) < 2:
            continue
        trial = [f.copy() for f in best]
        mv = rng.choice(trial[f_from])
        trial[f_from] = trial[f_from][trial[f_from] != mv]
        trial[f_to] = np.append(trial[f_to], mv)
        w = w1(cv_nn_dist(trial), d_target)
        if w < best_w:
            best, best_w = trial, w
    return best, best_w


# ---- Runner + metrics -----------------------------------------------------
def rmse(o, p):
    return float(np.sqrt(np.mean((o - p) ** 2)))


def run_cv(fit_predict_fn, X, y, folds):
    """fit_predict_fn(Xtr,ytr,Xte)->pred. Preprocessing must live INSIDE it
    (fold-internal) to avoid leakage F3."""
    preds = np.full(len(y), np.nan)
    for te in folds:
        tr = np.setdiff1d(np.arange(len(y)), te)
        preds[te] = fit_predict_fn(X[tr], y[tr], X[te])
    mask = ~np.isnan(preds)
    return rmse(y[mask], preds[mask]), preds


def design_based_accuracy(y_true, y_pred, inclusion_prob=None):
    """Design-based RMSE estimate for an independent probability sample.
    With equal probabilities this is the ordinary RMSE; with unequal
    probabilities it is Horvitz-Thompson weighted."""
    e2 = (y_true - y_pred) ** 2
    if inclusion_prob is None:
        return float(np.sqrt(e2.mean()))
    w = 1.0 / np.asarray(inclusion_prob)
    return float(np.sqrt(np.sum(w * e2) / np.sum(w)))


# ---- Demo ----------------------------------------------------------------
if __name__ == "__main__":
    from sklearn.ensemble import RandomForestRegressor
    rng = np.random.default_rng(7)

    # clustered sample: three tight blobs
    centers = np.array([[0.2, 0.2], [0.8, 0.3], [0.5, 0.8]])
    coords = np.vstack([c + 0.05 * rng.standard_normal((80, 2)) for c in centers])
    n = len(coords)
    X = np.column_stack([coords, rng.random(n)])
    y = 3 * coords[:, 0] + 2 * coords[:, 1] + rng.normal(0, 0.3, n)
    pred_grid = rng.random((500, 2))  # dense prediction area

    print("=== Validation recommendation ===")
    for r in recommend_validation(n, coords, can_draw_independent_sample=False):
        print("  -", r)

    def fp(Xtr, ytr, Xte):
        m = RandomForestRegressor(n_estimators=300, n_jobs=-1).fit(Xtr, ytr)
        return m.predict(Xte)

    r_rand, _ = run_cv(fp, X, y, random_kfold(n, 5))
    r_block, _ = run_cv(fp, X, y, spatial_block_folds(coords, 5))
    kfolds, wmatch = knndm_folds(coords[:, :2], pred_grid, k=5)
    # map back into full X folds
    r_knndm, _ = run_cv(fp, X, y, kfolds)

    print("\n=== Accuracy under different CV designs (same data/model) ===")
    print(f"  random k-fold : RMSE={r_rand:.3f}  (optimistic when clustered)")
    print(f"  spatial block : RMSE={r_block:.3f}  (can be over-pessimistic)")
    print(f"  kNNDM         : RMSE={r_knndm:.3f}  (geometry matched to prediction)")
    print(f"  kNNDM distribution mismatch (1-Wasserstein): {wmatch:.4f}")
    print("\nThe spread across designs IS the point: report the design with the "
          "number, never a bare RMSE.")
