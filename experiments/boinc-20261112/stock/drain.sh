#!/bin/bash
set -euo pipefail
cd "${1:?Usage: drain.sh STOCK_DIR}";source ./env.sh
cd client
../root/usr/bin/boinccmd --host 127.0.0.1:31420 --passwd "$(cat gui_rpc_auth.cfg)" --project http://127.0.0.1:8765/fifth42/ nomorework
../root/usr/bin/boinccmd --host 127.0.0.1:31420 --passwd "$(cat gui_rpc_auth.cfg)" --project http://127.0.0.1:8765/fifth42/ update
