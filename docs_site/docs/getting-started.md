# Getting started

## As Claude Code skills
```bash
git clone https://github.com/Odunayo3/dsm-tools.git ~/dsm-tools
cd ~/dsm-tools && bash scripts/sync.sh push
```

## Testing templates without Claude Code
The templates are plain scripts. Run them directly:
```bash
python skills/dsm-model-fit/templates/model_fit_rk_qrf.py
Rscript skills/dsm-model-fit/templates/model_fit_rk_qrf.R
```
Swap in your data by replacing the synthetic block at the bottom of each file.

## Live data connectors
`skills/dsm-covariate-prep/templates/fetch_covariates.py` fetches open covariates.
Supply your own free API keys (OpenTopography) and Sentinel OAuth token. Run once
with `--live` on a machine that can reach the services to confirm.
