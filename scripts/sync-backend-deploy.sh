#!/usr/bin/env bash
# Regenerates the `backend-deploy` branch from the current backend/ subtree
# of `main`, and pushes it to origin.
#
# Why this exists: the PythonAnywhere clone (~/fundcorsrd-backend) tracks a
# dedicated `backend-deploy` branch whose root IS backend/'s content (no
# backend/ prefix) — PythonAnywhere's working directory / WSGI setup needs
# manage.py etc. directly at the clone's root, and the repo as a whole also
# contains frontend/. `git subtree split` would be the standard tool to
# maintain a branch like this, but it isn't available in this environment's
# git install (Apple Git doesn't bundle the subtree contrib command), so
# this reproduces the same result with `git archive` + a throwaway worktree
# instead.
#
# Run this any time backend/ changes on main and gets pushed, BEFORE
# telling PythonAnywhere to `git pull` — otherwise backend-deploy (and so
# the PythonAnywhere clone) still has the old content. See
# docs/deployment-guide.md section 3-bis.
#
# Usage: ./scripts/sync-backend-deploy.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Working tree has uncommitted changes — commit or stash them first." >&2
  exit 1
fi

echo "==> Fetching main and backend-deploy from origin"
git fetch origin main backend-deploy

TMP_PARENT="$(mktemp -d)"
WT_DIR="$TMP_PARENT/backend-deploy-wt"
BRANCH="backend-deploy-sync-$$"

cleanup() {
  # cd out of $WT_DIR first - the trap can fire while it's still the shell's
  # cwd (e.g. after the early "already up to date" exit below), and removing
  # a worktree out from under the shell's own cwd left both the worktree
  # removal and the branch delete silently failing (masked by `|| true`),
  # leaking a stray local branch on every run.
  cd "$ROOT_DIR"
  git worktree remove "$WT_DIR" --force >/dev/null 2>&1 || true
  git branch -D "$BRANCH" >/dev/null 2>&1 || true
  rm -rf "$TMP_PARENT" 2>/dev/null || true
}
trap cleanup EXIT

git worktree add "$WT_DIR" -b "$BRANCH" origin/backend-deploy >/dev/null

find "$WT_DIR" -mindepth 1 -maxdepth 1 -not -name ".git" -exec rm -rf {} +
git archive origin/main -- backend | (cd "$WT_DIR" && tar -x --strip-components=1)

cd "$WT_DIR"
git add -A

if git diff --cached --quiet; then
  echo "==> backend-deploy is already up to date with main's backend/ — nothing to push."
  exit 0
fi

MAIN_SHA="$(git -C "$ROOT_DIR" rev-parse --short origin/main)"
git commit -q -m "Sincroniza con backend/ de main @ $MAIN_SHA"
git push origin "HEAD:backend-deploy"

echo "==> Listo. En PythonAnywhere: cd ~/fundcorsrd-backend && git pull"
