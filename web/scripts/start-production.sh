#!/bin/sh

set -eu

eve_port="${EVE_NEXT_PRODUCTION_PORT:-4274}"
export EVE_NEXT_PRODUCTION_ORIGIN="${EVE_NEXT_PRODUCTION_ORIGIN:-http://127.0.0.1:${eve_port}}"

# A self-hosted Next/Eve deployment needs both processes in the same service:
# Next owns the public HTTP port and proxies /eve/* to this loopback runtime.
PORT="$eve_port" ./node_modules/.bin/eve start --host 127.0.0.1 --port "$eve_port" &
eve_pid=$!

cleanup() {
  kill "$eve_pid" 2>/dev/null || true
  wait "$eve_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

next_status=0
npm run start -- --hostname 0.0.0.0 --port "${PORT:-3000}" || next_status=$?
exit "$next_status"
