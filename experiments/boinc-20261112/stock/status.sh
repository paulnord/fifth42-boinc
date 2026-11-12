#!/bin/bash
set -euo pipefail
cd "${1:?Usage: status.sh STOCK_DIR}";source ./env.sh
root/usr/bin/mariadb --no-defaults --protocol=TCP -h127.0.0.1 -uroot fifth42 --batch -e 'SELECT id,name,server_state,outcome,validate_state,app_version_id,hostid FROM result ORDER BY id; SELECT id,name,canonical_resultid,need_validate,error_mask FROM workunit ORDER BY id;'
if test -f client/gui_rpc_auth.cfg; then
 cd client
 ../root/usr/bin/boinccmd --host 127.0.0.1:31420 --passwd "$(cat gui_rpc_auth.cfg)" --get_tasks
fi
