#!/bin/bash
set -euo pipefail
export HERE=/source/experiments/boinc-20261112 STOCK=/pilot/boole-server RUNTIME=/pilot/science/runtime
bash "$HERE/stock/with_stack.sh" "$STOCK" bash -c '
python3 "$HERE/stock/lifecycle/socket_relay.py" --listen-unix /pilot/server-http.sock --target-port 8765 > /evidence/server-relay.log 2>&1 &
relay=$!
trap '\''kill "$relay" 2>/dev/null || true; wait "$relay" 2>/dev/null || true'\'' EXIT
python3 /recipe/remote-server-wait.py
'
