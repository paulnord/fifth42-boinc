#!/bin/bash
set -euo pipefail
set -x
: "${HERE:?HERE must be exported}" "${STOCK:?STOCK must be exported}" "${RUNTIME:?RUNTIME must be exported}"
source "$STOCK/env.sh"
cd "$STOCK/project"
php bin/update_versions --noconfirm --verbose
python3 "$HERE/scripts/make_manifest.py" --catalog "$RUNTIME/data/packets.jsonl" \
  --output "$STOCK/cabbage-control.json" \
  --names control-cap100-r12 control-cap42-r12 control-cap2951-r-2002
# Determine the actual registered version ID, rather than assuming it is 1.
version_id=$("$STOCK/root/usr/bin/mariadb" --no-defaults --protocol=TCP -h127.0.0.1 -uroot \
  --batch --skip-column-names fifth42 -e "SELECT av.id FROM app_version av JOIN app a ON a.id=av.appid WHERE a.name='fifth42' AND av.version_num=100")
test -n "$version_id"
python3 "$HERE/stock/submit.py" --stock "$STOCK" --runtime "$RUNTIME" \
  --manifest "$STOCK/cabbage-control.json" --name cabbage_pilot_control \
  --app-version-id "$version_id" --build A
bash "$HERE/stock/start_client.sh" "$STOCK"
ss -lntup > /evidence/listeners-during.txt
ip -details address show > /evidence/network-during.txt
ip route show >> /evidence/network-during.txt
ps -eo user,pid,ppid,ni,stat,args > /evidence/processes-during.txt
python3 /recipe/await-result.py
bash "$HERE/stock/status.sh" "$STOCK" > /evidence/stock-status.txt
bash "$HERE/stock/drain.sh" "$STOCK"
python3 /recipe/capture.py
python3 /recipe/quit-client.py
