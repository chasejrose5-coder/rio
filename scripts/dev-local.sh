#!/usr/bin/env bash
# API on :8000 and the Next.js app on :3000. Local accounts. Not production.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

if [[ "${RIO_USE_HOSTED:-}" != "1" ]]; then
  export RIO_SUPABASE_URL=
  export RIO_SUPABASE_ANON_KEY=
  export RIO_SUPABASE_SERVICE_ROLE_KEY=
fi
export RIO_FRONTEND_ORIGIN="${RIO_FRONTEND_ORIGIN:-http://localhost:3000}"
# Strava returns to the Next.js callback. Override with a full RIO_STRAVA_REDIRECT_URI.
export RIO_CALLBACK_BASE_URL="${RIO_CALLBACK_BASE_URL:-$RIO_FRONTEND_ORIGIN}"
export NEXT_PUBLIC_RIO_API_URL="${NEXT_PUBLIC_RIO_API_URL:-http://localhost:8000}"

python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000 &
api_pid=$!
npm --prefix web run dev -- --hostname 127.0.0.1 --port 3000 &
web_pid=$!

cleanup() {
  kill "$api_pid" "$web_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
wait
