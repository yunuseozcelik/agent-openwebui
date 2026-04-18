#!/usr/bin/env bash
# Prod mode: build frontend once, then serve via uvicorn at :8000.

set -e
cd "$(dirname "$0")"

if [ ! -d "web/node_modules" ]; then
  echo "[web] installing deps..."
  (cd web && npm install)
fi

echo "[web] building..."
(cd web && npm run build)

echo "[api] starting on :8000"
exec uvicorn api.main:app --host 0.0.0.0 --port 8000
