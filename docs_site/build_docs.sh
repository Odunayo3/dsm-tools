#!/usr/bin/env bash
# Mirror each skill's SKILL.md into the docs site as a page.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/docs_site/docs/skills"
mkdir -p "$DEST"
declare -A map=(
  [dsm-site-assessment]=site-assessment [dsm-covariate-prep]=covariate-prep
  [dsm-sampling-design]=sampling-design [dsm-harmonization]=harmonization
  [dsm-model-fit]=model-fit [dsm-validation]=validation
  [dsm-uncertainty]=uncertainty [dsm-explainability]=explainability
  [dsm-methods-doc]=methods-doc [dsm-lit-watch]=lit-watch)
for skill in "${!map[@]}"; do
  cp "$ROOT/skills/$skill/SKILL.md" "$DEST/${map[$skill]}.md"
done
cp "$ROOT/docs/references.md" "$ROOT/docs_site/docs/references.md"
echo "docs pages generated in $DEST"
