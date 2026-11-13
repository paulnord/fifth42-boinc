#!/bin/bash
set -euo pipefail
umask 077
export HERE=/source/experiments/boinc-20261112 STOCK=/pilot/mac-server RUNTIME=/pilot/science/runtime
if ! test -e "$STOCK/project" && ! test -e "$STOCK/db"; then
    bash "$HERE/stock/initialize.sh" "$STOCK"
fi
test -d "$STOCK/project" && test -d "$STOCK/db"
bash "$HERE/stock/with_stack.sh" "$STOCK" bash -c '
python3 "$HERE/stock/lifecycle/socket_relay.py" --listen-unix /pilot/transport/http.sock --target-port 8765 > /evidence/mac-attachment/http-relay.log 2>&1 &
relay=$!
trap '\''kill "$relay" 2>/dev/null || true; wait "$relay" 2>/dev/null || true'\'' EXIT
python3 /recipe/mac-server-wait.py
'
