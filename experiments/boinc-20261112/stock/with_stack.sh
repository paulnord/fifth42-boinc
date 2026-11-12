#!/bin/bash
# Runs the real stock services around a bounded command or interactive shell.
set -euo pipefail
STOCK=${1:?Usage: with_stack.sh STOCK_DIR COMMAND [ARGS...]};shift
test "$#" -gt 0
cd "$STOCK";source ./env.sh
export USER=${USER:-agent} HOME="$BOINC_STOCK"
export PYTHONPATH="$BOINC_STOCK/root/usr/lib/python3/dist-packages${PYTHONPATH:+:$PYTHONPATH}"
/usr/bin/python3 - <<'PY'
import socket
for port in (3306,8765,31420):
 s=socket.socket();s.bind(('127.0.0.1',port));s.close()
PY
# Refuse active services above, then discard only stale local PID tracking files.
# Cleanup must never signal a stale PID inherited from an earlier invocation.
rm -f client.pid validator.pid
pids=()
cleanup(){
 for file in client.pid validator.pid; do
  if test -s "$BOINC_STOCK/$file"; then kill "$(cat "$BOINC_STOCK/$file")" 2>/dev/null || true; fi
 done
 for p in "${pids[@]}"; do kill "$p" 2>/dev/null || true; done
 wait || true
}
trap cleanup EXIT INT TERM
root/usr/sbin/mariadbd --no-defaults --basedir="$BOINC_STOCK/root/usr" --datadir="$BOINC_STOCK/db" --socket= --port=3306 --bind-address=127.0.0.1 --pid-file="$BOINC_STOCK/mysql.pid" --log-error="$BOINC_STOCK/mysql.log" & pids+=($!)
for i in $(seq 1 30); do
 if root/usr/bin/mariadb --no-defaults --protocol=TCP -h127.0.0.1 -uroot -e 'SELECT 1' >/dev/null 2>&1; then break; fi
 sleep 1
done
rm -f httpd.pid
setsid root/usr/sbin/apache2 -DFOREGROUND -f "$BOINC_STOCK/httpd.conf" > httpd-console.log 2>&1 & pids+=($!)
# Upstream's daemon runner normally uses project/tmp; ../bin in script_validator
# is intentional. Use that same cwd with explicit foreground processes here.
mkdir -p project/tmp
cd project/tmp
../bin/feeder -d 3 > ../../feeder.log 2>&1 & pids+=($!)
../bin/transitioner -d 3 > ../../transitioner.log 2>&1 & pids+=($!)
../bin/script_validator --app fifth42 --init_script 'fifth42_validate result_id files' -d 3 > ../../validator.log 2>&1 & pids+=($!)
cd "$BOINC_STOCK"
sleep 3
"$@"
