#!/usr/bin/env bash
# publish.sh — one-shot local setup + publish for TokenTrim.
#
# Run this from your OWN terminal (Docker and GitHub are not reachable from the
# restricted build sandbox). It performs three idempotent steps:
#
#   1. Normalize the git directory (.gitdb -> .git), a leftover from the sandbox.
#   2. Bring up the pgvector Postgres in Docker and verify it.
#   3. Create the GitHub repo (if needed) and push.
#
# Usage:
#   ./scripts/publish.sh                  # private repo named "tokentrim"
#   ./scripts/publish.sh --public         # public repo
#   ./scripts/publish.sh --name my-repo   # custom repo name
#   ./scripts/publish.sh --skip-db        # skip the Docker/DB step
#   ./scripts/publish.sh --skip-push      # skip the GitHub step
#
# Safe to re-run: each step detects whether it is already done and skips.
set -euo pipefail

usage() { sed -n '2,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//; /^set -euo/d'; }

# ---- args ----------------------------------------------------------------
REPO_NAME="tokentrim"
VISIBILITY="private"
DO_DB=1
DO_PUSH=1
while [ $# -gt 0 ]; do
  case "$1" in
    --public)    VISIBILITY="public" ;;
    --private)   VISIBILITY="private" ;;
    --name)      REPO_NAME="${2:?--name needs a value}"; shift ;;
    --name=*)    REPO_NAME="${1#*=}" ;;
    --skip-db)   DO_DB=0 ;;
    --skip-push) DO_PUSH=0 ;;
    -h|--help)   usage; exit 0 ;;
    *) echo "unknown arg: $1 (try --help)" >&2; exit 2 ;;
  esac
  shift
done

# ---- pretty output (plain when not a tty) --------------------------------
if [ -t 1 ]; then B=$'\033[1;36m'; Y=$'\033[1;33m'; R=$'\033[1;31m'; N=$'\033[0m'
else B=''; Y=''; R=''; N=''; fi
say()  { printf '\n%s==> %s%s\n' "$B" "$1" "$N"; }
warn() { printf '%s!! %s%s\n' "$Y" "$1" "$N" >&2; }
die()  { printf '%sxx %s%s\n' "$R" "$1" "$N" >&2; exit 1; }

cd "$(dirname "$0")/.."

# ---- 1. normalize git directory -----------------------------------------
say "Normalizing git directory"
if [ -d .git ]; then
  echo "   .git already present — nothing to do."
elif [ -d .gitdb ]; then
  mv .gitdb .git && echo "   moved .gitdb -> .git"
else
  die "no .git or .gitdb here — run this from the TokenTrim repo root."
fi
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not a valid git repo after normalization."
BRANCH="$(git branch --show-current)"

# ---- 2. database (Docker) ------------------------------------------------
db_bringup() {
  docker compose up -d --wait || return 1
  docker compose exec -T db psql -U tokentrim -d tokentrim -v ON_ERROR_STOP=1 \
    -c "\dx vector" -c "\dt tokentrim_cache" || return 1
}
if [ "$DO_DB" -eq 1 ]; then
  say "Bringing up pgvector Postgres (Docker)"
  if ! command -v docker >/dev/null 2>&1; then
    warn "docker not found — skipping DB. Install Docker, then: ./scripts/db_up.sh"
  elif ! docker info >/dev/null 2>&1; then
    warn "docker daemon not reachable — is Docker Desktop running? Retry later: ./scripts/db_up.sh"
  elif db_bringup; then
    echo "   DB ready: postgresql://tokentrim:tokentrim@localhost:5432/tokentrim (already in .env)"
  else
    warn "DB bring-up failed (see output above). Fix Docker, then: ./scripts/db_up.sh"
  fi
else
  echo "   (--skip-db) skipping database"
fi

# ---- 3. GitHub -----------------------------------------------------------
if [ "$DO_PUSH" -eq 1 ]; then
  say "Publishing to GitHub"
  command -v gh >/dev/null 2>&1 || die "gh (GitHub CLI) not found — install it, then re-run."

  if ! gh auth status >/dev/null 2>&1; then
    warn "GitHub CLI not authenticated — launching 'gh auth login'..."
    gh auth login
  fi
  gh auth status >/dev/null 2>&1 || die "still not authenticated; aborting push."

  [ -n "$(git status --porcelain)" ] && \
    warn "working tree has uncommitted changes — commit them first if you want them pushed."

  if git remote get-url origin >/dev/null 2>&1; then
    echo "   origin already set: $(git remote get-url origin)"
    git push -u origin "$BRANCH"
  elif gh repo create "$REPO_NAME" --source=. --"$VISIBILITY" --push; then
    :
  else
    warn "gh repo create failed. If the repo already exists on GitHub, run:"
    warn "  git remote add origin https://github.com/<you>/$REPO_NAME.git && git push -u origin $BRANCH"
    die "aborting."
  fi
  echo "   repo: $(gh repo view --json url --jq '.url' 2>/dev/null || echo '(run: gh repo view --web)')"
else
  echo "   (--skip-push) skipping GitHub"
fi

say "Done."
