#!/usr/bin/env bash
# =============================================================================
# scripts/cleanup_repo.sh
#
# One-shot repo cleanup before the first public push.
#
# What it does (in this order):
#   1. Untracks runtime artifacts that should never have been in git:
#        - data/governance.db (contains user PII / password hashes)
#        - data/schemes_faiss.index (regenerated from seed)
#        - data/schemes_metadata.pkl (regenerated from seed)
#        - .agents/ (Claude Code metadata)
#        - skills-lock.json (Claude Code skill lockfile)
#      The local files stay on disk; they just stop being tracked.
#   2. Removes the empty `backend/` and `temp/` placeholder dirs (if empty).
#   3. Wipes any stray __pycache__ dirs under src/.
#
# Usage:
#   bash scripts/cleanup_repo.sh             # dry-run (default, shows what would happen)
#   bash scripts/cleanup_repo.sh --apply     # actually apply changes
#
# After running with --apply, review `git status` and commit yourself:
#   git commit -m "chore: untrack runtime artifacts; remove empty dirs"
# =============================================================================

set -euo pipefail

DRY_RUN=true
if [[ "${1:-}" == "--apply" ]]; then
  DRY_RUN=false
fi

run() {
  if $DRY_RUN; then
    echo "[dry-run] $*"
  else
    echo "[apply]   $*"
    eval "$@"
  fi
}

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root"

echo "==> Repo: $repo_root"
if $DRY_RUN; then
  echo "==> Mode: DRY RUN (no changes will be made). Re-run with --apply to execute."
else
  echo "==> Mode: APPLY"
fi
echo

# ----- 1. Untrack runtime artifacts ------------------------------------------
echo "--- 1/3 Untracking runtime artifacts from git index ---"
# `--ignore-unmatch` so the script doesn't fail if a path was already untracked.
run "git rm --cached --ignore-unmatch data/governance.db || true"
run "git rm --cached --ignore-unmatch data/governance.db-wal || true"
run "git rm --cached --ignore-unmatch data/governance.db-shm || true"
run "git rm --cached --ignore-unmatch data/schemes_faiss.index || true"
run "git rm --cached --ignore-unmatch data/schemes_metadata.pkl || true"
run "git rm --cached --ignore-unmatch -r .agents || true"
run "git rm --cached --ignore-unmatch skills-lock.json || true"
echo

# ----- 2. Remove empty placeholder dirs --------------------------------------
echo "--- 2/3 Removing empty placeholder dirs ---"
for d in backend temp; do
  if [[ -d "$d" ]]; then
    if [[ -z "$(ls -A "$d" 2>/dev/null)" ]]; then
      run "rmdir \"$d\""
    else
      echo "[skip]    $d/ is not empty — refusing to delete"
    fi
  else
    echo "[skip]    $d/ does not exist"
  fi
done
echo

# ----- 3. Wipe __pycache__ under src/ ----------------------------------------
echo "--- 3/3 Removing __pycache__ dirs under src/ ---"
if [[ -d src ]]; then
  # `find ... -exec rm -rf {} +` works on Git Bash, macOS, and Linux.
  while IFS= read -r -d '' pyc; do
    run "rm -rf \"$pyc\""
  done < <(find src -type d -name __pycache__ -print0)
else
  echo "[skip]    src/ does not exist"
fi
echo

# ----- Summary ---------------------------------------------------------------
echo "==> Cleanup complete."
if $DRY_RUN; then
  cat <<EOF

Nothing was changed (dry run). To actually apply:

  bash scripts/cleanup_repo.sh --apply

EOF
else
  cat <<EOF

Next steps:
  git status               # review what changed
  git add -A
  git commit -m "chore: untrack runtime artifacts; remove empty dirs"

If you have not yet rotated secrets that may have been committed historically,
do so now (Groq, Sarvam, JWT). git history still contains old data/governance.db
contents — consider \`git filter-repo\` if PII removal is required.
EOF
fi
