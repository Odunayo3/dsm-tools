---
name: dsm-model-fit
description: >
  Fit and predict soil properties from point observations and environmental
  covariates using regression kriging, random forest / quantile regression
  forest, and stacked ensembles, with leakage-safe preprocessing and spatially
  honest cross-validation. Trigger when the user mentions regression kriging,
  RK, random forest for soil, QRF, quantile regression forest, CAST, forward
  feature selection, spatial CV, SOC / clay / pH / bulk-density prediction, or
  asks to "fit a soil model", "predict a soil property", or "check my DSM
  pipeline for leakage". Do NOT trigger for pure covariate construction
  (dsm-covariate-prep), sampling design (dsm-sampling-design), or standalone
  uncertainty/validation questions unless a model is also being fit.
version: 0.1.0
---

# dsm-model-fit

Fit soil-property models the way a careful pedometrician would: preprocess
without leaking, cross-validate in a way that respects spatial structure,
choose the model class from the data rather than habit, and never report an
accuracy number the map cannot honor.

This skill encodes **procedure and judgment**, not just code. The templates in
`templates/` are starting points; the decision logic below is the reason the
skill exists.

---

## 1. When Claude should reach for this skill

Fire on any of: regression kriging (RK), random forest (RF) or ranger for a
soil target, quantile regression forest (QRF), CAST / forward feature selection
(FFS), spatial cross-validation, `knndm` / `nndm`, stacked/ensemble soil models,
area of applicability (AOA) in the context of a fitted model, or a request to
audit an existing DSM pipeline before a cluster run.

If the user only wants covariates built, sampling designed, or literature
scanned, hand off to the sibling skill and stop.

---

## 2. First action: interrogate the data before touching a model

Do not fit anything until these are known. Ask only for what is missing.

1. **Target** — property, depth interval, units, transformation history. Is it
   strictly positive and right-skewed (SOC, N, clay)? That decides
   transformation (§4).
2. **Sample size and support** — n points, point vs. bulk, single-depth vs.
   profile. n < ~50 makes RF unstable and pushes toward RK or simple linear +
   kriging.
3. **Spatial layout** — clustered, gridded, or transect? Clustering is the
   single biggest driver of validation strategy (§6) and the most common cause
   of a number that looks good and a map that is wrong.
4. **Covariate stack** — how many, their source, resolution, and whether they
   are already aligned to one grid. Mismatched grids surface later as the
   train/predict column bug in §5.
5. **Intended output** — a mean map only, or mean + prediction interval? If
   intervals are needed, the model class is constrained to QRF, kriging
   variance, or a conformal wrapper (§7).

State any assumption inline when you proceed without an answer.

---

## 3. Choosing the model class (decision logic)

There is no default winner. The literature that repeatedly re-tests this on real
soil data keeps landing on the same shape: **RF is a strong, hard-to-beat
baseline; stacking rarely beats the best single learner; kriging the residuals
helps when residuals are still autocorrelated.** Encode that, don't fight it.

The menu is wider than RK/RF/QRF. `templates/model_zoo.{R,py}` exposes a
judgment-first `recommend_model()` and a uniform runner across linear/GLM, RF,
QRF, XGBoost, LightGBM, SVR, Gaussian process, GAM (and Cubist in R). Use the
recommender - it maps a data/goal profile to an ordered shortlist with reasons -
rather than running everything and picking the best RMSE, which is automated
overfitting. Notes per added class: gradient boosting (XGBoost/LightGBM) often
edges RF and handles gappy covariates but has its own early-stopping leakage risk
(tune on an inner fold, never on test); GPs give a principled posterior variance
and are sample-efficient at small n but scale poorly; GAMs give interpretable
smooth terms; SVR is competitive at small n but kernel/C-sensitive.

For **data-sparse locations**, consider transfer learning from a data-rich
source region: `templates/transfer_learning.py` (instance weighting, fine-tuning,
and a documented GPU-optional deep-transfer path), always gated by an
applicability check so transfer is only trusted where target covariates overlap
the source feature space.

```
Is the residual spatial structure the point (dense sampling, strong
autocorrelation, smooth property like a groundwater-influenced texture field)?
  YES → regression kriging (RK): trend model + kriged residuals.        (§3.1)
  NO  → tree ensemble as the workhorse.                                  (§3.2)

Do you need calibrated prediction intervals per pixel?
  YES → quantile regression forest (QRF), or RK with kriging variance.  (§7)

Are several genuinely different learners available AND n is large?
  Consider stacking — but treat "no improvement over best base learner"
  as the expected result, not a failure. Report it honestly.            (§3.3)
```

### 3.1 Regression kriging

Model the target as trend plus spatially correlated residual:

$$Z(\mathbf{s}) = m(\mathbf{s}) + \varepsilon(\mathbf{s}), \qquad
m(\mathbf{s}) = f\big(\mathbf{x}(\mathbf{s})\big),$$

where $f$ is the trend (linear model, GLM, or an RF) fitted on covariates
$\mathbf{x}$, and $\varepsilon$ is a zero-mean second-order-stationary residual
with variogram

$$\gamma(h) = \tfrac{1}{2}\,\mathbb{E}\big[(\varepsilon(\mathbf{s}) -
\varepsilon(\mathbf{s}+h))^2\big].$$

Prediction at an unsampled $\mathbf{s}_0$ is the trend prediction plus the
ordinary-kriging interpolation of the residuals:

$$\hat{Z}(\mathbf{s}_0) = \hat{m}(\mathbf{s}_0) +
\sum_{i=1}^{n} \lambda_i\,\hat{\varepsilon}(\mathbf{s}_i).$$

**Judgment:** RK only earns its keep when the residuals are still
autocorrelated. Compute the residual variogram and read the **nugget-to-sill
ratio**. If it is near 1 (pure nugget), the kriging step adds noise, not signal —
drop back to the trend model alone and say so. (In practice residual variograms
in ML-trend RK often show high nugget ratios; do not assume kriging will help.)

### 3.2 Random forest / QRF

RF predicts by averaging $B$ regression trees over bootstrap samples:

$$\hat{f}_{\text{RF}}(\mathbf{x}) = \frac{1}{B}\sum_{b=1}^{B}
T_b(\mathbf{x}).$$

QRF keeps the full conditional distribution instead of the mean. It estimates
the conditional CDF from the training responses that land in the same leaves,
weighted by how often each training point shares a leaf with $\mathbf{x}$:

$$\hat{F}(y \mid \mathbf{x}) = \sum_{i=1}^{n} w_i(\mathbf{x})\,
\mathbb{1}\{Y_i \le y\}, \qquad
\hat{Q}_\tau(\mathbf{x}) = \inf\{y : \hat{F}(y\mid\mathbf{x}) \ge \tau\}.$$

The $\tau$-quantile minimizes the pinball (check) loss
$\rho_\tau(u) = u(\tau - \mathbb{1}\{u<0\})$. A 90% interval is
$[\hat{Q}_{0.05}, \hat{Q}_{0.95}]$.

**Judgment:** RF cannot extrapolate beyond the range of training responses —
its predictions are bounded by observed leaf values. Under-prediction of highs
and over-prediction of lows at the tails is structural, not a bug. Flag it for
skewed targets and for tiles whose covariates sit outside training feature space
(that is what AOA in §7 is for).

### 3.3 Stacking

A meta-learner $g$ is fit on the **out-of-fold** predictions of base learners
$\hat{f}_1,\dots,\hat{f}_M$:

$$\hat{f}_{\text{stack}}(\mathbf{x}) =
g\big(\hat{f}_1(\mathbf{x}),\dots,\hat{f}_M(\mathbf{x})\big).$$

The base predictions fed to $g$ **must** be out-of-fold, or the meta-learner
sees leaked in-sample fits and the stack looks better in training than it is.
This is the most common stacking bug. Even done correctly, expect the stack to
roughly match, not beat, the best base learner on typical soil datasets — report
that plainly rather than tuning until it "wins".

---

## 4. Target transformation (and the ordering trap)

Right-skewed positive targets (SOC, total N, clay) are often modeled on a
transformed scale. Yeo-Johnson (handles zeros/negatives) or log are standard.

$$\psi_\lambda(y) = \begin{cases}
\dfrac{(y+1)^\lambda - 1}{\lambda} & y \ge 0,\ \lambda \ne 0\\[4pt]
\ln(y+1) & y \ge 0,\ \lambda = 0
\end{cases}$$

**The trap — estimate $\lambda$ inside the training fold only.** Fitting the
transformation on the full dataset before the CV split leaks test-set
distribution into training. Fit `preProcess`/`PowerTransformer` on train, apply
the frozen transform to test. See failure mode F1.

**Back-transform bias.** The naive back-transform of a mean prediction on the
log scale is biased low. If reporting means on the original scale, apply a bias
correction (e.g. the Duan smearing estimator) rather than exponentiating the
predicted mean directly. For QRF this is cleaner: quantiles are monotone under
monotone transforms, so back-transform the quantiles directly.

---

## 5. Categorical covariates and the train/predict column bug

Parent material, land use, soil-map unit are categorical. One-hot / dummy
encoding creates one column per level.

**The bug (F2):** encode train and predict rasters *independently* and you get
different column sets — a level present in the map but absent from training
points (or vice versa) produces a column mismatch, and the model either errors
or, worse, silently aligns columns by position and predicts nonsense.

**Rule:** fix the factor levels from the *training* data, store them, and coerce
the prediction stack to those exact levels before encoding. Unseen levels in the
prediction area are a real modeling decision (lump to "other", or mask as outside
applicability) — never let them be created as a new column.

---

## 6. Cross-validation: the honest-accuracy problem

This is where DSM pipelines most often lie to themselves, and where the
literature genuinely disagrees. Encode the disagreement, do not paper over it.

**Random k-fold CV** is optimistic when samples are spatially clustered:
near-duplicate neighbors land in both train and test, so the model is scored on
points it effectively already saw.

**Spatial CV** (block, or leave-region-out) was the standard fix, and remains a
reasonable default for clustered data. But a documented critique (Wadoux,
Heuvelink, Pebesma, de Bruin) shows that spatial CV with an exclusion radius can
be *over-pessimistic*: validation folds fall in feature-space regions the
training folds never cover, so the score reflects extrapolation, not map error.

The current, more defensible options:

- **Design-based validation** with an independent probability sample is the
  statistically cleanest estimate of map accuracy when you can afford the extra
  points. Prefer it when a validation sample can be drawn.
- **NNDM / kNNDM CV** (nearest-neighbour distance matching) tunes the CV fold
  geometry so the train-to-test distance distribution matches the
  train-to-prediction-point distance distribution — aiming the CV at the actual
  prediction task. Prefer this among CV-only options for clustered data.

```
Clustered sampling?
  Can you draw an independent probability sample for validation?
     YES → design-based validation (report that as the accuracy number).
     NO  → kNNDM CV (match CV geometry to the prediction task).
Roughly even / probability sampling already?
     → random k-fold is defensible; still check block CV for sensitivity.
Never report only random k-fold on clustered data as the headline accuracy.
```

**Whatever is chosen, do the preprocessing inside the fold** (transform,
encoding, feature selection, tuning). Selecting features or tuning on the whole
dataset and *then* cross-validating is leakage (F3) and inflates the score.

### Forward feature selection (FFS / CAST)

FFS starts from the best-performing pair of covariates and greedily adds the
covariate that most improves the **cross-validated** metric, stopping when no
addition helps. It reduces overfitting to noise covariates and is well suited to
the many-correlated-covariates situation typical of DEM derivatives.

**Judgment:** FFS is worth it when covariates are many and collinear (terrain
stacks). It is expensive; for a small, curated covariate set plain CV with all
covariates is fine. Critically, the feature selection must sit **inside** the
outer CV loop — nested CV — or the reported accuracy is optimistic.

---

## 7. Uncertainty and area of applicability

If intervals are requested, produce them, and gate the map by where the model is
allowed to speak.

**QRF interval:** $[\hat{Q}_{0.05}(\mathbf{x}), \hat{Q}_{0.95}(\mathbf{x})]$.
Validate coverage: the fraction of held-out points inside their nominal 90%
interval should be near 0.90. Systematic under-coverage means the intervals are
too tight — report the empirical coverage, not just the nominal level.

**Interval collapse at tile edges / extrapolation (F4):** when covariates at a
pixel fall outside training feature space, QRF leaves become degenerate and the
interval can collapse toward zero width — the model is most confident exactly
where it should be least. Always cross-check intervals against AOA.

**Area of applicability (AOA):** define a dissimilarity index from the
covariate distance between a prediction pixel and its nearest training point in
(weighted) feature space,

$$DI(\mathbf{x}) = \frac{d(\mathbf{x}, \text{nearest training point})}
{\bar{d}_{\text{train}}},$$

normalized by the mean training-to-training distance $\bar{d}_{\text{train}}$.
Pixels with $DI$ above a threshold (derived from the training DI distribution)
are outside the AOA and should be masked or flagged, not published as if
trustworthy. Conformal prediction is a defensible alternative for
distribution-free coverage guarantees.

---

## 8. Failure modes (the catalogue to check against)

| ID | Symptom | Cause | Fix |
|----|---------|-------|-----|
| F1 | CV score much better than independent test | Transformation (Yeo-Johnson/log) or scaling fit on full data before split | Fit transform inside training fold; freeze; apply to test |
| F2 | Predict step errors on factor columns, or map has implausible blocks | One-hot encoding done separately on train vs predict; column mismatch | Fix factor levels from training; coerce predict stack to them before encoding |
| F3 | Great CV, poor real-world map | Feature selection / tuning done outside the CV loop | Nest FFS and tuning inside the outer CV |
| F4 | QRF prediction interval collapses to ~0 at tile edges | Covariates outside training feature space; degenerate leaves | Mask by AOA; report empirical coverage; consider conformal |
| F5 | RK barely differs from trend model | Residuals are pure nugget (no autocorrelation) | Read nugget-to-sill; if ~1, drop kriging step |
| F6 | Raster prediction shifted / garbled | CRS or grid-alignment mismatch, or matrix row/col vs x/y index swap | Assert identical CRS, extent, resolution; verify index order before writing |
| F7 | Stack never beats base learners and you keep tuning | Expecting stacking to win; or base preds not out-of-fold | Use out-of-fold base preds; accept "no gain" as a valid, reportable result |

---

## 9. Output conventions

When Claude writes up results from this skill:

- Report the **validation strategy explicitly** and why it was chosen — a
  headline RMSE without its CV design is not interpretable.
- Report both the metric and the **empirical interval coverage** when intervals
  are produced.
- Prose style for results sections: direct academic voice, past tense for what
  was done, no em-dashes, no "it's worth noting", no bulleted marketing cadence.
  State the number, its uncertainty, and the caveat, then stop.
- Always name the software and version (ranger, gstat, CAST, sklearn) for
  reproducibility, and cite the method source (see `docs/references.md`).

---

## 10. Reference implementations

- `templates/model_fit_rk_qrf.{R,py}` — regression kriging + QRF with
  fold-internal preprocessing, spatial CV, AOA, raster prediction (R primary,
  Python parity).
- `templates/model_zoo.{R,py}` — the wider learner menu behind one interface,
  with `recommend_model()` decision logic. R is capability-gated (runs what is
  installed); Python runs the full menu.
- `templates/transfer_learning.py` — source-to-target adaptation for data-sparse
  regions, applicability-gated; deep transfer documented as GPU-optional.

Adapt the template to the dataset; do not run it blind. The point of the skill
is the judgment in §3–§8, which the templates only partially enforce.
