#!/usr/bin/env Rscript
# ---------------------------------------------------------------------------
# dsm-model-fit :: regression kriging + quantile regression forest
# Reference implementation (R, primary).
#
# Design principle: every data-dependent preprocessing step (transformation,
# factor-level encoding, feature choice) is fit INSIDE the training fold and
# applied frozen to the held-out fold. This is what prevents the leakage
# failure modes F1-F3 in SKILL.md. Read the skill before adapting this.
#
# Dependencies (CRAN or apt r-cran-*): ranger, gstat, sp.
# ranger supplies both RF and QRF (quantile regression) -> no quantregForest
# dependency. AOA dissimilarity index is implemented here directly so the
# template runs without CAST; swap in CAST::aoa / CAST::ffs for production.
# ---------------------------------------------------------------------------

suppressMessages({
  library(ranger)
  library(gstat)
  library(sp)
})

# ---- 1. Leakage-safe preprocessing, fit on TRAIN only --------------------

# Yeo-Johnson-style log1p transform for positive skewed targets. lambda is a
# stand-in; in production estimate lambda on the training fold (e.g.
# bestNormalize / car::powerTransform) and freeze it. The point of the
# function signature is that fit and apply are SEPARATE steps.
fit_target_transform <- function(y_train) {
  # returns a frozen transform object estimated on training data only
  stopifnot(all(is.finite(y_train)))
  list(shift = 0, apply = function(y) log1p(y), invert = function(z) expm1(z))
}

# Fix factor levels from training; coerce any data frame to those levels.
# Unseen levels in prediction data become NA (a deliberate modeling decision:
# lump or mask downstream) rather than silently creating a new column (F2).
fit_factor_levels <- function(df, factor_cols) {
  lvls <- lapply(factor_cols, function(cn) levels(as.factor(df[[cn]])))
  names(lvls) <- factor_cols
  lvls
}
apply_factor_levels <- function(df, lvls) {
  for (cn in names(lvls)) df[[cn]] <- factor(df[[cn]], levels = lvls[[cn]])
  df
}

# ---- 2. AOA dissimilarity index (lightweight; see SKILL.md §7) ------------
# DI(x) = d(x, nearest training point) / mean(train-to-train nearest distances)
# in standardized covariate space. Pixels with DI above the training-DI
# threshold are outside the area of applicability.
aoa_di <- function(train_X, new_X, quantile_thresh = 0.95) {
  mu <- colMeans(train_X); sdv <- apply(train_X, 2, sd); sdv[sdv == 0] <- 1
  z <- function(M) sweep(sweep(M, 2, mu, "-"), 2, sdv, "/")
  ztr <- z(train_X); znew <- z(new_X)
  nn_dist <- function(A, B, self = FALSE) {
    apply(A, 1, function(r) {
      d <- sqrt(colSums((t(B) - r)^2))
      if (self) d <- d[d > 0]
      min(d)
    })
  }
  dbar <- mean(nn_dist(ztr, ztr, self = TRUE))
  di_train <- nn_dist(ztr, ztr, self = TRUE) / dbar
  di_new   <- nn_dist(znew, ztr) / dbar
  thresh <- as.numeric(quantile(di_train, quantile_thresh))
  list(di = di_new, threshold = thresh, inside = di_new <= thresh)
}

# ---- 3. Regression kriging: RF/linear trend + kriged residuals -----------
# Returns trend predictions plus, IF residuals are autocorrelated, a kriged
# residual correction. If the residual variogram is ~pure nugget, the kriging
# step is skipped and reported (F5).
fit_rk <- function(train, coords_cols, target, covars,
                   nugget_sill_skip = 0.95) {
  form <- as.formula(paste(target, "~", paste(covars, collapse = " + ")))
  trend <- ranger(form, data = train, num.trees = 500)
  train$.resid <- train[[target]] - trend$predictions  # OOB trend residuals

  sp_df <- train
  coordinates(sp_df) <- coords_cols
  vg_emp <- tryCatch(variogram(.resid ~ 1, sp_df), error = function(e) NULL)

  krige_ok <- FALSE; vg_fit <- NULL
  if (!is.null(vg_emp)) {
    vg_fit <- tryCatch(
      fit.variogram(vg_emp, vgm("Sph"), fit.method = 7),
      error = function(e) NULL)
    if (!is.null(vg_fit) && nrow(vg_fit) >= 2) {
      nugget <- vg_fit$psill[1]; sill <- sum(vg_fit$psill)
      ratio <- if (sill > 0) nugget / sill else 1
      krige_ok <- ratio < nugget_sill_skip
      message(sprintf("[RK] nugget/sill = %.2f -> kriging %s",
                      ratio, ifelse(krige_ok, "USED", "SKIPPED (pure nugget)")))
    }
  }
  list(trend = trend, vg_fit = vg_fit, krige_ok = krige_ok,
       coords_cols = coords_cols, train_sp = sp_df, target = target)
}

predict_rk <- function(model, newdata, coords_cols) {
  trend_pred <- predict(model$trend, newdata)$predictions
  if (!model$krige_ok) return(trend_pred)
  nd <- newdata; coordinates(nd) <- coords_cols
  kr <- krige(.resid ~ 1, model$train_sp, nd, model = model$vg_fit,
              debug.level = 0)
  trend_pred + kr$var1.pred
}

# ---- 4. QRF with prediction intervals ------------------------------------
fit_qrf <- function(train, target, covars) {
  form <- as.formula(paste(target, "~", paste(covars, collapse = " + ")))
  ranger(form, data = train, num.trees = 500, quantreg = TRUE)
}
predict_qrf_interval <- function(model, newdata, lower = 0.05, upper = 0.95) {
  q <- predict(model, newdata, type = "quantiles",
               quantiles = c(lower, 0.5, upper))$predictions
  data.frame(lo = q[, 1], med = q[, 2], hi = q[, 3])
}

# ---- 5. Spatial / kNNDM-style fold assignment ----------------------------
# Minimal spatial blocking: k clusters in coordinate space -> leave-block-out.
# For production, replace with CAST::knndm to match CV geometry to the
# prediction grid (SKILL.md §6).
spatial_folds <- function(coords, k = 5, seed = 1) {
  set.seed(seed)
  km <- kmeans(scale(coords), centers = k)
  km$cluster
}

# metrics
rmse <- function(o, p) sqrt(mean((o - p)^2))
coverage <- function(o, lo, hi) mean(o >= lo & o <= hi)

# ---- 6. Nested, fold-internal CV driver ----------------------------------
run_cv <- function(df, coords_cols, target, covars, factor_cols = character(0),
                   k = 5) {
  folds <- spatial_folds(df[, coords_cols], k = k)
  out <- data.frame()
  for (f in sort(unique(folds))) {
    tr <- df[folds != f, ]; te <- df[folds == f, ]

    # preprocessing fit on TRAIN fold only (F1, F2)
    tf <- fit_target_transform(tr[[target]])
    lvls <- if (length(factor_cols)) fit_factor_levels(tr, factor_cols) else NULL
    tr2 <- tr; te2 <- te
    tr2[[target]] <- tf$apply(tr[[target]])
    if (!is.null(lvls)) { tr2 <- apply_factor_levels(tr2, lvls)
                          te2 <- apply_factor_levels(te2, lvls) }

    m_rk  <- fit_rk(tr2, coords_cols, target, covars)
    m_qrf <- fit_qrf(tr2, target, covars)

    p_rk  <- tf$invert(predict_rk(m_rk, te2, coords_cols))
    qi    <- predict_qrf_interval(m_qrf, te2)
    p_qrf <- tf$invert(qi$med)
    lo    <- tf$invert(qi$lo); hi <- tf$invert(qi$hi)

    ao <- aoa_di(as.matrix(tr[covars]), as.matrix(te[covars]))

    out <- rbind(out, data.frame(
      fold = f,
      rmse_rk  = rmse(te[[target]], p_rk),
      rmse_qrf = rmse(te[[target]], p_qrf),
      cov90    = coverage(te[[target]], lo, hi),
      pct_inside_aoa = mean(ao$inside)))
  }
  out
}

# ---- 7. Demo on synthetic data (runs standalone) -------------------------
if (sys.nframe() == 0) {
  set.seed(42)
  n <- 300
  x <- runif(n); y <- runif(n)
  dem   <- 100 * x + 50 * y + rnorm(n, 0, 5)
  slope <- abs(rnorm(n, 5, 2))
  ndvi  <- 0.3 + 0.4 * y + rnorm(n, 0, 0.05)
  # skewed positive target (SOC-like) with spatial trend + autocorrelated noise
  soc <- exp(1 + 0.01 * dem + 0.5 * ndvi + 0.3 * sin(6 * x) + rnorm(n, 0, 0.2))
  d <- data.frame(x, y, dem, slope, ndvi, soc)
  res <- run_cv(d, c("x", "y"), "soc", c("dem", "slope", "ndvi"), k = 5)
  cat("\n--- Spatial CV results ---\n"); print(round(res, 3))
  cat(sprintf("\nMean RMSE  RK=%.3f  QRF=%.3f | mean 90%% coverage=%.2f\n",
              mean(res$rmse_rk), mean(res$rmse_qrf), mean(res$cov90)))
}
