#!/usr/bin/env bash
# Dev mode: backend (reload) + frontend (vite) side by side.
# Both logs prefix their lines with [api] / [web].

set -e
cd "$(dirname "$0")"

if [ ! -d "web/node_modules" ]; then
  echo "[web] installing deps..."
  (cd web && npm install)
fi

cleanup() {
  echo
  echo "shutting down..."
  kill 0
}
trap cleanup EXIT INT TERM

# Backend — FastAPI with reload
(uvicorn api.main:app --reload --port 8000 2>&1 | sed -u 's/^/[api] /') &

# Frontend — Vite dev server with /api proxy
(cd web && npm run dev 2>&1 | sed -u 's/^/[web] /') &

wait
