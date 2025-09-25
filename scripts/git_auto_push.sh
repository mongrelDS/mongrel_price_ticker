#!/bin/bash
set -euo pipefail

# Simple, safe auto-commit/push for the repo
REPO_DIR="/home/mongreldatalab/mongrel_price_ticker"
LOG_DIR="$REPO_DIR/logs/cron_jobs"
BRANCH="main"

mkdir -p "$LOG_DIR"

cd "$REPO_DIR"

# Ensure we are on the right branch and up to date
git fetch --prune

# If there are remote updates, rebase to avoid merge commits
if ! git diff --quiet "origin/$BRANCH".."$BRANCH"; then
  git pull --rebase origin "$BRANCH"
fi

# Stage only if there are changes
if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
  git add -A
  COMMIT_MSG="chore(auto): periodic auto-commit from cron $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  # Commit only if there is something to commit
  if ! git diff --cached --quiet; then
    git commit -m "$COMMIT_MSG"
    git push origin "$BRANCH"
    echo "$(date -u) - Auto-commit pushed" >> "$LOG_DIR/git_auto_push.log"
  else
    echo "$(date -u) - No staged changes after add" >> "$LOG_DIR/git_auto_push.log"
  fi
else
  echo "$(date -u) - No changes to commit" >> "$LOG_DIR/git_auto_push.log"
fi


