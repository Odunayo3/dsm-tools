#!/usr/bin/env python3
"""dsm-sampling-design :: sampling design engine (Python).

Turns data characteristics into a concrete sampling recommendation, not prose.
Covers conditioned Latin hypercube (cLHS) for feature-space coverage, spatial
coverage sampling for geographic spread, uncertainty-guided in-fill, and an
independent probability sample for design-based validation.

cLHS is implemented directly (simulated annealing after Minasny & McBratney
2006) so no clhs dependency is needed. Read SKILL.md before adapting.

Deps: numpy, scikit-learn.
"""
from __future__ import annotations
import numpy as np
from sklearn.cluster import KMeans


# ---- Design recommendation (SKILL.md decision logic) ---------------------
def recommend_design(n_budget, n_covars, extent_km2, target_resolution_m=None,
                     for_validation=False):
    """Concrete design advice from budget + covariate dimensionality + extent."""
    recs = []
    density = n_budget / extent_km2 if extent_km2 else float("nan")

    if for_validation:
        recs.append(
            "Validation sample must be INDEPENDENT and probability-based "
            "(simple or stratified random) to support design-based accuracy "
            "(Wadoux et al. 2021). Do not reuse calibration points.")
        recs.append(
            f"For ~{n_budget} validation points over {extent_km2:g} km^2, "
            "stratify by a few covariate/landscape classes to stabilize the "
            "estimate, then sample randomly within strata.")
        return recs

    # calibration design
    if n_budget < 50:
        recs.append(
            f"n={n_budget} is small. Prefer cLHS to guarantee covariate "
            "feature-space coverage; every point must earn its place. Expect "
            "wide area-of-applicability gaps and report them.")
    elif n_budget < 200:
        recs.append(
            f"n={n_budget} is moderate. cLHS on the covariate stack, with a "
            "spatial-spread constraint to avoid clustering that would later "
            "force pessimistic/leaky validation.")
    else:
        recs.append(
            f"n={n_budget} is comfortable. cLHS still preferred for feature "
            "coverage; a share (~10-20%) reserved for spatial coverage sampling "
            "improves interpolation in under-sampled regions.")

    if n_covars > 20:
        recs.append(
            f"{n_covars} covariates is high-dimensional for cLHS; reduce to the "
            "SCORPAN-meaningful set (or PCA) first, or cLHS will chase noise "
            "dimensions.")
    if not np.isnan(density):
        recs.append(f"Implied density ~{density:.2f} pts/km^2; document the "
                    "basis for n (variability, dimensionality, budget).")
    recs.append(
        "Reserve an independent probability sample for validation separately "
        "(call recommend_design(..., for_validation=True)).")
    return recs


# ---- Conditioned Latin Hypercube Sampling (Minasny & McBratney 2006) ------
def clhs(cov_grid, n, iters=5000, seed=1, temp=1.0, cooling=0.999):
    """Select n rows of cov_grid (candidate pixels x covariates) that jointly
    stratify every covariate's marginal (Latin hypercube) while matching the
    covariate correlation structure. Simulated annealing on the objective:
        O = w1 * sum |eta_j - 1|  +  w2 * sum |corr_sample - corr_pop|
    where eta_j counts samples per quantile stratum of covariate j.
    Returns selected row indices.
    """
    rng = np.random.default_rng(seed)
    X = np.asarray(cov_grid, float)
    N, K = X.shape
    n = min(n, N)

    # quantile edges per covariate -> n strata
    edges = np.quantile(X, np.linspace(0, 1, n + 1), axis=0)  # (n+1, K)
    corr_pop = np.corrcoef(X, rowvar=False)

    def strata_counts(rows):
        cnt = np.zeros((n, K))
        sub = X[rows]
        for j in range(K):
            b = np.clip(np.searchsorted(edges[1:-1, j], sub[:, j]), 0, n - 1)
            for bi in b:
                cnt[bi, j] += 1
        return cnt

    def objective(rows):
        cnt = strata_counts(rows)
        o1 = np.abs(cnt - 1.0).sum()               # LH stratification
        if len(rows) > 2:
            cs = np.corrcoef(X[rows], rowvar=False)
            o2 = np.nansum(np.abs(cs - corr_pop))  # correlation match
        else:
            o2 = 0.0
        return o1 + 0.5 * o2

    cur = rng.choice(N, n, replace=False)
    cur_set = set(cur.tolist())
    best = cur.copy()
    o_cur = o_best = objective(cur)
    T = temp
    for _ in range(iters):
        # swap one selected pixel for one unselected
        out_idx = rng.integers(n)
        cand = rng.integers(N)
        if cand in cur_set:
            continue
        trial = cur.copy(); trial[out_idx] = cand
        o_trial = objective(trial)
        if o_trial < o_cur or rng.random() < np.exp(-(o_trial - o_cur) / max(T, 1e-6)):
            cur_set.discard(cur[out_idx]); cur_set.add(cand)
            cur = trial; o_cur = o_trial
            if o_cur < o_best:
                best, o_best = cur.copy(), o_cur
        T *= cooling
    return np.sort(best)


# ---- Spatial coverage sampling (k-means centroids -> nearest candidates) ---
def spatial_coverage(coords, n, seed=1):
    coords = np.asarray(coords, float)
    km = KMeans(n_clusters=min(n, len(coords)), random_state=seed,
                n_init=10).fit(coords)
    sel = []
    for c in km.cluster_centers_:
        d = ((coords - c) ** 2).sum(1)
        sel.append(int(np.argmin(d)))
    return np.array(sorted(set(sel)))


# ---- Uncertainty-guided in-fill ------------------------------------------
def uncertainty_infill(coords, uncertainty, n, existing=None, seed=1):
    """Pick n new points weighted toward high uncertainty, avoiding existing."""
    rng = np.random.default_rng(seed)
    u = np.asarray(uncertainty, float).copy()
    if existing is not None:
        u[np.asarray(existing)] = -np.inf
    valid = np.where(np.isfinite(u))[0]
    w = u[valid] - u[valid].min() + 1e-9
    p = w / w.sum()
    n = min(n, len(valid))
    return np.sort(rng.choice(valid, size=n, replace=False, p=p))


# ---- Independent probability sample for validation -----------------------
def validation_sample(coords, n, strata=None, seed=1):
    """Stratified (or simple) random sample, independent of any calibration set."""
    rng = np.random.default_rng(seed)
    N = len(coords)
    if strata is None:
        return np.sort(rng.choice(N, min(n, N), replace=False))
    strata = np.asarray(strata)
    out = []
    for s in np.unique(strata):
        idx = np.where(strata == s)[0]
        take = max(1, round(n * len(idx) / N))
        out += rng.choice(idx, min(take, len(idx)), replace=False).tolist()
    return np.sort(np.array(out))


# ---- Demo ----------------------------------------------------------------
if __name__ == "__main__":
    print("=== Design recommendation (n=45, 8 covars, 120 km^2) ===")
    for r in recommend_design(45, 8, 120):
        print("  -", r)
    print("\n=== Validation design (n=100, 500 km^2) ===")
    for r in recommend_design(100, 8, 500, for_validation=True):
        print("  -", r)

    rng = np.random.default_rng(3)
    N = 800
    grid = np.column_stack([rng.normal(size=N), rng.uniform(size=N),
                            rng.gamma(2, size=N)])
    coords = rng.random((N, 2))

    sel = clhs(grid, n=40, iters=3000)
    print(f"\ncLHS selected {len(sel)} points.")
    # coverage check: each covariate's selected values should span its range
    for j in range(grid.shape[1]):
        full = np.ptp(grid[:, j]); samp = np.ptp(grid[sel, j])
        print(f"  covar {j}: sample range covers {100*samp/full:4.0f}% of population range")

    sc = spatial_coverage(coords, 30)
    print(f"\nSpatial coverage selected {len(sc)} well-dispersed points.")

    unc = rng.random(N)
    inf = uncertainty_infill(coords, unc, 20, existing=sel)
    print(f"Uncertainty in-fill selected {len(inf)} high-uncertainty points "
          f"(mean unc {unc[inf].mean():.2f} vs overall {unc.mean():.2f}).")

    val = validation_sample(coords, 100,
                            strata=(coords[:, 0] > 0.5).astype(int))
    print(f"Validation sample: {len(val)} independent stratified points.")
