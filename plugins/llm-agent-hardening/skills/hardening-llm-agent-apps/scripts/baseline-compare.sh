#!/usr/bin/env bash
# Run the same probe against a baseline ref (throwaway git worktree) and against the current checkout.
# Usage: bash baseline-compare.sh <repo-dir> <baseline-ref> "<probe command run from the repo root>"
# The probe must be a file NOT committed at the baseline: it is copied into the worktree. node_modules is symlinked.
set -euo pipefail
REPO="$1"; REF="$2"; PROBE="$3"
cd "$REPO"
WT="$(mktemp -d "${TMPDIR:-/tmp}/baseline-XXXXXX")"
cleanup() { git worktree remove --force "$WT" >/dev/null 2>&1 || true; }
trap cleanup EXIT
git worktree add --detach "$WT" "$REF" >/dev/null
[ -d node_modules ] && ln -s "$PWD/node_modules" "$WT/node_modules"
for f in $PROBE; do [ -f "$f" ] && mkdir -p "$WT/$(dirname "$f")" && cp "$f" "$WT/$f"; done
echo "== BEFORE ($REF)"; (cd "$WT" && eval "$PROBE") || echo "(probe exited non-zero)"
echo "== AFTER ($(git rev-parse --short HEAD))"; eval "$PROBE" || echo "(probe exited non-zero)"
