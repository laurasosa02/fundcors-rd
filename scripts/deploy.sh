#!/usr/bin/env bash
# One-command deploy for FUNDCORSRD to the Network Solutions hosting account.
#
# Does NOT assume the host supports git-based deployment (unconfirmed for
# Network Solutions, which uses its own control panel rather than cPanel) —
# uploads over FTP/SFTP instead, which works on any shared hosting account.
# See docs/deployment-guide.md for the one-time setup this script assumes
# is already done (Python App configured, env vars set on the host).
#
# Usage: ./scripts/deploy.sh
# Config: copy scripts/deploy.example.env to scripts/deploy.env first.

set -euo pipefail

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
: "${DEPLOY_FTP_PASS:?Set DEPLOY_FTP_PASS in scripts/deploy.env}"
: "${DEPLOY_FRONTEND_REMOTE_PATH:?Set DEPLOY_FRONTEND_REMOTE_PATH in scripts/deploy.env}"
: "${DEPLOY_BACKEND_REMOTE_PATH:?Set DEPLOY_BACKEND_REMOTE_PATH in scripts/deploy.env}"
DEPLOY_FTP_PROTOCOL="${DEPLOY_FTP_PROTOCOL:-sftp}"
DEPLOY_SSH_HOST="${DEPLOY_SSH_HOST:-}"

if ! command -v lftp >/dev/null 2>&1; then
  echo "lftp is required for this script (handles both FTP and SFTP mirroring)." >&2
  echo "Install it with: brew install lftp" >&2
  exit 1
fi

echo "==> Building frontend"
( cd "$ROOT_DIR/frontend" && npm run build )

echo "==> Uploading frontend/dist to $DEPLOY_FRONTEND_REMOTE_PATH"
lftp -u "$DEPLOY_FTP_USER,$DEPLOY_FTP_PASS" "$DEPLOY_FTP_PROTOCOL://$DEPLOY_FTP_HOST" \
  -e "mirror --reverse --delete --verbose \"$ROOT_DIR/frontend/dist\" \"$DEPLOY_FRONTEND_REMOTE_PATH\"; bye"

echo "==> Uploading backend/ to $DEPLOY_BACKEND_REMOTE_PATH (excluding local-only files)"
lftp -u "$DEPLOY_FTP_USER,$DEPLOY_FTP_PASS" "$DEPLOY_FTP_PROTOCOL://$DEPLOY_FTP_HOST" \
  -e "mirror --reverse --delete --verbose \
      --exclude-glob .venv/ \
      --exclude-glob venv/ \
      --exclude-glob __pycache__/ \
      --exclude-glob '*.pyc' \
      --exclude-glob data/ \
      --exclude-glob .env \
      --exclude-glob staticfiles/ \
      \"$ROOT_DIR/backend\" \"$DEPLOY_BACKEND_REMOTE_PATH\"; bye"

if [[ -n "$DEPLOY_SSH_HOST" ]]; then
  echo "==> SSH access configured — running install/migrate/collectstatic/restart remotely"
  # shellcheck disable=SC2087
  ssh "$DEPLOY_SSH_HOST" bash -s <<EOF
set -euo pipefail
cd "$DEPLOY_BACKEND_REMOTE_PATH"
source venv/bin/activate 2>/dev/null || source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
touch tmp/restart.txt 2>/dev/null || echo "Note: couldn't touch tmp/restart.txt — restart the app manually from the Network Solutions panel if this host doesn't use that Passenger convention."
EOF
  echo "==> Done. Backend installed, migrated, and restarted."
else
  cat <<'MSG'
==> No DEPLOY_SSH_HOST configured — files are uploaded, but these steps
    still need to be done manually via the Network Solutions panel
    (only required when requirements.txt or the data models changed,
    not for a routine content/frontend update):
      1. pip install -r requirements.txt
      2. python manage.py migrate
      3. python manage.py collectstatic --noinput
      4. Restart the Python app (see docs/deployment-guide.md)
MSG
fi

echo "==> Deploy finished."
