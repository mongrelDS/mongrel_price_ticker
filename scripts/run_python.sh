#!/usr/bin/env bash
set -euo pipefail
REPO="/home/mongreldatalab/mongrel_price_ticker"
export PYTHONPATH="$REPO:$REPO/src:${PYTHONPATH:-}"
if [ -f "$REPO/.env" ]; then
  set -a
  . "$REPO/.env"
  set +a
fi
cd "$REPO"
exec /usr/bin/python3 "$@"
