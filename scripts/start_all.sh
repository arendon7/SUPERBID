#!/usr/bin/env bash
set -euo pipefail
: "${SUPERBID_DB:=/data/superbid.db}"
: "${PORT:=8000}"
export SUPERBID_DB PORT
mkdir -p "$(dirname "$SUPERBID_DB")"
python - <<'PY2'
import os
from superbid_collector.bootstrap import bootstrap
db=os.environ.get("SUPERBID_DB","/data/superbid.db")
bootstrap(db)
print(f"SUPERBID DB ready: {db}")
PY2
exec supervisord -c /app/deploy/supervisord.conf
