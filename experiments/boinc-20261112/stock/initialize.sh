#!/bin/bash
# Fresh, private, single-user test environment only; no public enrollment.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
STOCK=${1:?Usage: initialize.sh STOCK_DIR}
cd "$STOCK"; source ./env.sh
export USER=${USER:-agent} HOME="$BOINC_STOCK"
export PYTHONPATH="$BOINC_STOCK/root/usr/lib/python3/dist-packages${PYTHONPATH:+:$PYTHONPATH}"
test ! -e project
test ! -e db
umask 077
/usr/bin/python3 "$HERE/check_ports.py" 3306
root/usr/bin/mariadb-install-db --no-defaults --basedir="$BOINC_STOCK/root/usr" --datadir="$BOINC_STOCK/db" --auth-root-authentication-method=normal > db-init.log 2>&1
root/usr/sbin/mariadbd --no-defaults --basedir="$BOINC_STOCK/root/usr" --datadir="$BOINC_STOCK/db" --socket= --port=3306 --bind-address=127.0.0.1 --pid-file="$BOINC_STOCK/mysql.pid" --log-error="$BOINC_STOCK/mysql.log" &
pid=$!; trap 'kill "$pid" 2>/dev/null || true; wait "$pid" || true' EXIT
for i in $(seq 1 30); do
 if root/usr/bin/mariadb --no-defaults --protocol=TCP -h127.0.0.1 -uroot -e 'SELECT 1' >/dev/null 2>&1; then break; fi
 sleep 1
done
cd source
/usr/bin/python3 tools/make_project --no_query --srcdir="$BOINC_STOCK/source" --project_root="$BOINC_STOCK/project" --url_base=http://127.0.0.1:8765/ --project_host=localhost --db_host=127.0.0.1 --db_user=root fifth42 'Fifth42 TEST ONLY' > "$BOINC_STOCK/project-init.log" 2>&1
cd "$BOINC_STOCK"
cp "$HERE/fifth42_in" "$HERE/fifth42_out" project/templates/
/usr/bin/python3 "$HERE/configure_http.py" "$BOINC_STOCK"
# Include only our CPU app; stock platform records retained.
/usr/bin/python3 - <<'PY'
import xml.etree.ElementTree as E
p='project/project.xml';t=E.parse(p);a=E.SubElement(t.getroot(),'app');E.SubElement(a,'name').text='fifth42';E.SubElement(a,'user_friendly_name').text='Fifth42 TEST ONLY';t.write(p,encoding='unicode')
PY
cd project
php bin/xadd > ../xadd.log 2>&1
printf 'Private test project initialized; services stop on return.\n'
