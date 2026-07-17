#!/usr/bin/env Rscript
# ---------------------------------------------------------------------------
# dsm-model-fit :: model zoo (R, primary)
#
# Judgment-first menu of learners behind one interface. recommend_model()
# encodes SKILL.md §3 decision logic; fit_predict() is the uniform runner.
# Capability-gated: only runs learners whose packages are installed, so the
# template degrades gracefully. Install the optional packages for the full menu:
#   install.packages(c("xgboost","mgcv","kernlab","Cubist"))
# (ranger, randomForest, e1071, gstat, sp cover the tested subset.)
# ---------------------------------------------------------------------------

.has <- function(pkg) requireNamespace(pkg, quietly = TRUE)

capabilities <- function() {
  c(linear = TRUE,
    rf   = .has("ranger") || .has("randomForest"),
    qrf  = .has("ranger"),
    svr  = .has("e1071") || .has("kernlab"),
    gp   = .has("kernlab"),
    xgboost = .has("xgboost"),
    gam  = .has("mgcv"),
    cubist = .has("Cubist"))
}

# ---- Decision logic (SKILL.md §3) ----------------------------------------
recommend_model <- function(n, n_covars, needs_intervals, skewed,
                            strong_spatial_resid, has_gpu = FALSE) {
  recs <- list()
  add <- function(m, r) recs[[length(recs) + 1]] <<- c(m, r)

  if (needs_intervals) {
    add("qrf", "Per-pixel intervals requested; QRF gives a conditional distribution with no distributional assumption.")
    add("gp",  "Gaussian process gives a principled posterior variance at small-to-moderate n on smooth surfaces.")
  }
  if (n < 50) {
    add("linear", sprintf("n=%d is small; linear/GLM trend + kriging is more stable than a deep ensemble.", n))
    add("gp",  "Gaussian process is sample-efficient at small n.")
    add("svr", "SVR is competitive at small n but sensitive to kernel/C (tune inside the fold).")
  } else {
    add("rf", "RF is a strong, hard-to-beat baseline at this n; justify any move away from it.")
    if (.has("xgboost")) add("xgboost", "Boosting often edges RF and handles gappy covariates; avoid early-stopping leakage.")
  }
  if (n_covars > 15) {
    if (.has("mgcv")) add("gam", "Many covariates, interpretability wanted: GAM gives smooth inspectable terms.")
    else add("rf", "Many covariates: RF with forward feature selection to prune collinear DEM derivatives.")
  }
  if (strong_spatial_resid) add("+kriging", "Residuals autocorrelated: wrap chosen trend in regression kriging.")
  if (skewed) add("~transform", "Right-skewed target: fit transform INSIDE training fold; back-transform quantiles / smear-correct means.")
  if (!has_gpu) add("!note", "Deep/transfer learning omitted: no GPU declared. Optional-if-hardware, not a default.")

  seen <- character(0); ordered <- list()
  for (rc in recs) if (!rc[1] %in% seen) { ordered[[length(ordered)+1]] <- rc; seen <- c(seen, rc[1]) }
  ordered
}

# ---- Uniform fit/predict --------------------------------------------------
fit_predict <- function(kind, train, target, covars, newdata) {
  form <- as.formula(paste(target, "~", paste(covars, collapse = " + ")))
  qs <- NULL
  pred <- switch(kind,
    linear = {
      m <- lm(form, train); predict(m, newdata)
    },
    rf = {
      if (.has("ranger")) predict(ranger::ranger(form, train, num.trees = 500), newdata)$predictions
      else predict(randomForest::randomForest(form, train), newdata)
    },
    qrf = {
      m <- ranger::ranger(form, train, num.trees = 500, quantreg = TRUE)
      q <- predict(m, newdata, type = "quantiles",
                   quantiles = c(0.05, 0.5, 0.95))$predictions
      qs <<- q; q[, 2]
    },
    svr = {
      m <- e1071::svm(form, train); predict(m, newdata)
    },
    gp = {
      m <- kernlab::gausspr(form, data = train); as.numeric(kernlab::predict(m, newdata))
    },
    xgboost = {
      X <- as.matrix(train[covars]); Xn <- as.matrix(newdata[covars])
      m <- xgboost::xgboost(data = X, label = train[[target]], nrounds = 400,
                            max_depth = 5, eta = 0.05, verbose = 0)
      predict(m, Xn)
    },
    gam = {
      sm <- paste(sprintf("s(%s)", covars), collapse = " + ")
      m <- mgcv::gam(as.formula(paste(target, "~", sm)), data = train)
      as.numeric(predict(m, newdata))
    },
    cubist = {
      m <- Cubist::cubist(x = train[covars], y = train[[target]])
      predict(m, newdata[covars])
    },
    stop(paste("unknown model kind:", kind))
  )
  list(pred = as.numeric(pred), quantiles = qs)
}

# ---- Demo -----------------------------------------------------------------
if (sys.nframe() == 0) {
  suppressMessages({ if (.has("ranger")) library(ranger)
                     if (.has("e1071")) library(e1071) })
  cat("Capabilities:\n"); print(capabilities())

  set.seed(0); n <- 200
  d <- data.frame(x1 = runif(n), x2 = runif(n), x3 = runif(n), x4 = runif(n))
  d$y <- exp(1 + 2 * d$x1 + d$x2 + 0.3 * rnorm(n))
  tr <- d[1:150, ]; te <- d[151:n, ]
  covars <- c("x1", "x2", "x3", "x4")

  cat("\nRecommendation (n=150, 4 covars, intervals=TRUE, skewed=TRUE):\n")
  for (rc in recommend_model(150, 4, TRUE, TRUE, FALSE))
    cat(sprintf("  [%s] %s\n", rc[1], rc[2]))

  cat("\nRunning available learners:\n")
  cap <- capabilities()
  for (k in c("linear","rf","qrf","svr","gp","xgboost","gam","cubist")) {
    ok <- switch(k, linear = TRUE, cap[[k]])
    if (isTRUE(ok)) {
      r <- tryCatch(fit_predict(k, tr, "y", covars, te), error = function(e) NULL)
      if (!is.null(r)) {
        rmse <- sqrt(mean((te$y - r$pred)^2))
        cat(sprintf("  %-8s RMSE=%.3f%s\n", k, rmse,
                    if (!is.null(r$quantiles)) " +quantiles" else ""))
      } else cat(sprintf("  %-8s skipped (error)\n", k))
    } else cat(sprintf("  %-8s (unavailable - install package)\n", k))
  }
}
