#!/bin/bash
set -euo pipefail
source "$STOCK/env.sh"
python3 "$HERE/stock/stage_application.py" --stock "$STOCK" --runtime "$RUNTIME" --label BooleCPU --build B --version 1.10
python3 "$HERE/stock/stage_application.py" --stock "$STOCK" --runtime "$RUNTIME" --label BooleGPU --build B --version 1.20 --backend gpu
(cd "$STOCK/project"; php bin/update_versions --noconfirm --verbose)
python3 "$HERE/scripts/make_manifest.py" --catalog "$RUNTIME/data/packets.jsonl" --output "$STOCK/controls.json" --names control-cap100-r12 control-cap42-r12 control-cap2951-r-2002
python3 - <<'PY'
import os,secrets,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
s=Path(os.environ['STOCK'])
url='http://127.0.0.1:8765/fifth42/'
r=subprocess.check_output(['curl','--noproxy','*','-fsS',url+'create_account.php?email_addr=boole-test%40example.invalid&passwd_hash='+secrets.token_hex(16)+'&user_name=BoolePrivateTest'])
key=ET.fromstring(r).findtext('authenticator');assert key
p=s/'remote-account.xml'
root=ET.Element('account');ET.SubElement(root,'master_url').text=url;ET.SubElement(root,'authenticator').text=key;ET.SubElement(root,'project_name').text='Fifth42 TEST ONLY'
ET.ElementTree(root).write(p,encoding='unicode');p.chmod(0o600)
PY
python3 "$HERE/stock/lifecycle/socket_relay.py" --listen-unix /pilot/server-http.sock --target-port 8765 > /evidence/server-relay.log 2>&1 &
relay=$!
trap 'kill "$relay" 2>/dev/null || true; wait "$relay" 2>/dev/null || true' EXIT
python3 /recipe/remote-server-wait.py
