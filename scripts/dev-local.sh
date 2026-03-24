#!/usr/bin/env bash
# Start Postgres (Docker), migrate backend, run API + Vite locally.
# Usage: ./scripts/dev-local.sh
#        SKIP_POSTGRES=1 ./scripts/dev-local.sh   # if Postgres already running

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

need() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing: $1 — $2" >&2; exit 1; }
}

need python "Install Python 3.12+"
need npm "Install Node.js 22+"

if [[ "${SKIP_POSTGRES:-}" != "1" ]]; then
  need docker "Install Docker, or set SKIP_POSTGRES=1 if Postgres is already running"
  echo "==> Starting PostgreSQL (docker compose)..."
  docker compose up -d postgres
  echo "==> Waiting for Postgres..."
  for i in $(seq 1 45); do
    if docker compose exec -T postgres pg_isready -U archai -d archai >/dev/null 2>&1; then
      echo "    Postgres is up."
      break
    fi
    if [[ "$i" -eq 45 ]]; then
      echo "Postgres did not become ready. Try: docker compose logs postgres" >&2
      exit 1
    fi
    sleep 2
  done
else
  echo "==> SKIP_POSTGRES=1 — ensure backend/.env DATABASE_URL is correct."
fi

if [[ ! -f backend/.env ]]; then
  cp backend/.env.example backend/.env
  echo "==> Created backend/.env from .env.example"
fi
if [[ ! -f frontend/.env ]]; then
  cp frontend/.env.example frontend/.env
  echo "==> Created frontend/.env from .env.example"
fi

cd backend
if [[ ! -d .venv ]]; then
  echo "==> Creating Python venv..."
  python -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
echo "==> Installing backend dependencies..."
pip install -r requirements.txt
echo "==> Running migrations..."
alembic upgrade head
cd "$ROOT"

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "==> Starting API (http://127.0.0.1:8000) in background..."
(
  cd "$ROOT/backend"
  exec .venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
) &
BACKEND_PID=$!
sleep 2

cd "$ROOT/frontend"
if [[ ! -d node_modules ]]; then
  echo "==> npm install (frontend)..."
  npm install
fi

echo "==> Starting Vite (http://localhost:5173) — Ctrl+C stops frontend and script will stop the API."
echo "    API docs: http://127.0.0.1:8000/docs"
npm run dev
