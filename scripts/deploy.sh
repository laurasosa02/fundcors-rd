#!/usr/bin/env bash
# One-command deploy for the FUNDCORSRD frontend to the Network Solutions
# hosting account. Backend deploys are separate — see docs/deployment-guide.md
# section "3-bis" (the backend lives on PythonAnywhere, updated via git pull).
#
# Does NOT assume the host supports git-based deployment (unconfirmed for
# Network Solutions, which uses its own control panel rather than cPanel) —
# uploads over FTP/SFTP instead, which works on any shared hosting account.
#
# Usage: ./scripts/deploy.sh [--dry-run]
#   --dry-run  Connect and show exactly what would be uploaded/deleted,
#              without changing anything on the server. Run this first.
# Config: copy scripts/deploy.example.env to scripts/deploy.env first.

set -euo pipefail

DRY_RUN=""
case "${1:-}" in
  --dry-run) DRY_RUN="--dry-run" ;;
  "") ;;
  *) echo "Unknown argument: $1 (only --dry-run is supported)" >&2; exit 1 ;;
esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/scripts/deploy.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE — copy scripts/deploy.example.env to scripts/deploy.env and fill in real values first." >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$ENV_FILE"

: "${DEPLOY_FTP_HOST:?Set DEPLOY_FTP_HOST in scripts/deploy.env}"
: "${DEPLOY_FTP_USER:?Set DEPLOY_FTP_USER in scripts/deploy.env}"
: "${DEPLOY_FRONTEND_REMOTE_PATH:?Set DEPLOY_FRONTEND_REMOTE_PATH in scripts/deploy.env}"
DEPLOY_FTP_PROTOCOL="${DEPLOY_FTP_PROTOCOL:-sftp}"
DEPLOY_FTP_PORT="${DEPLOY_FTP_PORT:-}"

# Password is deliberately optional in deploy.env: leaving it out keeps the
# hosting password off disk entirely, and the script asks for it per run
# (same as FileZilla's "Ask for password" logon type).
if [[ -z "${DEPLOY_FTP_PASS:-}" ]]; then
  read -r -s -p "Password for $DEPLOY_FTP_USER@$DEPLOY_FTP_HOST: " DEPLOY_FTP_PASS
  echo
  [[ -n "$DEPLOY_FTP_PASS" ]] || { echo "No password entered." >&2; exit 1; }
fi

if ! command -v lftp >/dev/null 2>&1; then
  echo "lftp is required for this script (handles both FTP and SFTP mirroring)." >&2
  echo "Install it with: brew install lftp" >&2
  exit 1
fi

# Non-standard ports are the norm on shared hosting (this account uses 2222).
REMOTE_URL="$DEPLOY_FTP_PROTOCOL://$DEPLOY_FTP_HOST"
[[ -n "$DEPLOY_FTP_PORT" ]] && REMOTE_URL="$REMOTE_URL:$DEPLOY_FTP_PORT"

# Accept the host key on first connect instead of hanging on the prompt, and
# don't let one slow file abort the whole mirror.
LFTP_SETTINGS="set sftp:auto-confirm yes; set net:max-retries 3; set net:timeout 20;"

if [[ "$DEPLOY_FTP_PROTOCOL" == "sftp" ]]; then
  # This host (an "ipage FTP Server", the platform behind the Network Solutions
  # account) only offers ssh-rsa/ssh-dss host keys, which OpenSSH 8.8+ refuses
  # by default -- without these options the connection dies at
  # "no matching host key type found". Re-enabling ssh-rsa here affects only
  # this connection, not the machine's global ssh config.
  LFTP_SETTINGS="$LFTP_SETTINGS set sftp:connect-program \"ssh -a -x -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa\";"
fi

echo "==> Building frontend"
if command -v npm >/dev/null 2>&1; then
  ( cd "$ROOT_DIR/frontend" && npm run build )
elif [[ -f "$ROOT_DIR/frontend/dist/index.html" ]]; then
  # No Node on this machine. Reusing the committed build is fine, but shipping
  # a stale bundle silently is worse than failing, so check src/ against it.
  STALE="$(find "$ROOT_DIR/frontend/src" -type f -newer "$ROOT_DIR/frontend/dist/index.html" -print -quit)"
  if [[ -n "$STALE" ]]; then
    echo "npm not found, and frontend/dist is older than frontend/src (e.g. $STALE)." >&2
    echo "Install Node 20+ and re-run so dist/ gets rebuilt before uploading." >&2
    exit 1
  fi
  echo "    npm not found — reusing existing frontend/dist (already up to date with src/)."
else
  echo "npm not found and there is no frontend/dist to fall back on." >&2
  echo "Install Node 20+ (https://nodejs.org) and re-run." >&2
  exit 1
fi

# --delete makes the remote an exact copy of the local directory, so anything
# already living in that remote path and not in this repo gets removed.
if [[ -z "$DRY_RUN" ]]; then
  echo
  echo "About to mirror onto $DEPLOY_FTP_HOST:"
  echo "  frontend/dist -> $DEPLOY_FRONTEND_REMOTE_PATH"
  echo "Files already in that remote folder that aren't in this repo WILL BE DELETED."
  read -r -p "Type 'deploy' to continue: " CONFIRM
  [[ "$CONFIRM" == "deploy" ]] || { echo "Aborted."; exit 1; }
fi

# Commands (and the credentials) go to lftp over stdin rather than argv, so the
# hosting password never shows up in `ps` output while the upload runs.
run_lftp() {
  lftp <<LFTP_SCRIPT
$LFTP_SETTINGS
open -u "$DEPLOY_FTP_USER","$DEPLOY_FTP_PASS" "$REMOTE_URL"
$1
bye
LFTP_SCRIPT
}

echo "==> Uploading frontend/dist to $DEPLOY_FRONTEND_REMOTE_PATH"
run_lftp "mirror --reverse --delete --verbose $DRY_RUN --exclude-glob .htaccess --exclude-glob mantenimiento.html --exclude-glob fundcorsrd-backend/ --exclude-glob .membership --exclude-glob stats/ \"$ROOT_DIR/frontend/dist\" \"$DEPLOY_FRONTEND_REMOTE_PATH\""

if [[ -n "$DRY_RUN" ]]; then
  echo "==> Dry run: nothing was changed on the server. Re-run without --dry-run to deploy."
  exit 0
fi

echo "==> Deploy finished. (Backend updates are separate — see docs/deployment-guide.md, section 3-bis, PythonAnywhere.)"
