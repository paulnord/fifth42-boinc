#!/bin/bash
set -euo pipefail
set -x
# Export is essential: with_stack.sh starts a nested shell.
export HERE=/source/experiments/boinc-20261112
export STOCK=/pilot/stock
export RUNTIME=/pilot/science/runtime
date -u --iso-8601=seconds
python3 - <<'PY'
import json,subprocess
interfaces=json.loads(subprocess.check_output(['ip','-j','address','show']))
assert [x['ifname'] for x in interfaces]==['lo'],interfaces
assert not json.loads(subprocess.check_output(['ip','-j','route','show']))
PY
ip -details address show
ip route show
ss -lntup
test ! -e /dev/nvidia0
test -d "$STOCK/project"
test -d "$STOCK/project/apps/fifth42/1.00/x86_64-pc-linux-gnu"
bash "$HERE/stock/with_stack.sh" "$STOCK" bash /recipe/control.sh
# These execute while the private network and PID namespaces still exist.
sleep 2
ss -lntup > /evidence/listeners-after.txt
ss -tanp > /evidence/tcp-after.txt
ps -eo user,pid,ppid,stat,args > /evidence/processes-after.txt
python3 /recipe/check-stopped.py
tail -60 "$STOCK/mysql.log" > /evidence/database-shutdown.txt
cp "$STOCK/client-console.log" /evidence/client-console.txt
cp "$STOCK/validator.log" /evidence/validator.txt
cp "$STOCK/httpd-console.log" /evidence/httpd-console.txt
cp "$STOCK/binary-hashes.txt" /evidence/stock-binary-hashes.txt
cp "$STOCK/client-version.txt" /evidence/client-version.txt
cp "$STOCK/wrapper-version.txt" /evidence/wrapper-version.txt
date -u --iso-8601=seconds
