#!/bin/bash
set -euo pipefail
umask 077
export HERE=/source/experiments/boinc-20261112 STOCK=/pilot/mac-plan-regression RUNTIME=/pilot/science/runtime
source "$STOCK/env.sh"
bash "$HERE/stock/initialize.sh" "$STOCK"
python3 - <<'PY'
import shutil,xml.etree.ElementTree as E
from pathlib import Path
s=Path('/pilot/mac-plan-regression')
for v in ('1.30','1.40'):
    shutil.copytree(Path('/pilot/input-project/apps/fifth42')/v,s/'project/apps/fifth42'/v)
shutil.copy2('/pilot/input-project/plan_class_spec.xml',s/'project/plan_class_spec.xml')
p=s/'project/config.xml';t=E.parse(p);E.SubElement(t.getroot().find('config'),'debug_version_select').text='1';E.SubElement(t.getroot().find('config'),'debug_send').text='1';E.SubElement(t.getroot().find('config'),'debug_send_job').text='1';E.indent(t);t.write(p,encoding='unicode')
PY
bash "$HERE/stock/with_stack.sh" "$STOCK" bash -c '
cd "$STOCK/project"
php bin/update_versions --noconfirm --verbose
version=$("$STOCK/root/usr/bin/mariadb" --no-defaults --protocol=TCP -h127.0.0.1 -uroot --batch --skip-column-names fifth42 -e "SELECT id FROM app_version WHERE version_num=140")
python3 "$HERE/stock/submit.py" --stock "$STOCK" --runtime "$RUNTIME" --manifest /pilot/bundle/controls.json --name synthetic_old_alias_control --app-version-id "$version" --build A --backend gpu --engine /pilot/bundle/engine-identity
sleep 8
python3 /recipe/requests.py
'
