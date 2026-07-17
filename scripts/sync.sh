#!/usr/bin/env bash
# Sync DSM skills between this repo and the Claude Code global skills dir.
# skills/ is the source of truth.
#   bash scripts/sync.sh push   # deploy skills/ -> ~/.claude/skills/
#   bash scripts/sync.sh pull   # pull ~/.claude/skills/ -> skills/
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_SRC="$REPO_DIR/skills"
SKILLS_DST="$HOME/.claude/skills"
CMD="${1:-}"

case "$CMD" in
  push)
    mkdir -p "$SKILLS_DST"
    for d in "$SKILLS_SRC"/*/; do
      name="$(basename "$d")"
      rsync -a --delete "$d" "$SKILLS_DST/$name/"
      echo "pushed: $name"
    done
    echo "Done. Skills deployed to $SKILLS_DST"
    ;;
  pull)
    mkdir -p "$SKILLS_SRC"
    rsync -a "$SKILLS_DST"/ "$SKILLS_SRC"/
    echo "Pulled from $SKILLS_DST. Review 'git diff skills/' before committing."
    ;;
  *)
    echo "usage: bash scripts/sync.sh {push|pull}" >&2
    exit 1
    ;;
esac
