#!/bin/bash
set -euo pipefail
cd "${1:?Usage: start_client.sh STOCK_DIR}";source ./env.sh
umask 077
if ! test -s account-key; then
 pass=$(python3 -c 'import secrets;print(secrets.token_hex(16))')
 curl --noproxy '*' -fsS "http://127.0.0.1:8765/fifth42/create_account.php?email_addr=boinc-test%40example.invalid&passwd_hash=$pass&user_name=Prototype" > account-response.xml
 python3 - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as E
x=E.parse('account-response.xml');a=x.findtext('authenticator')
if not a:raise ValueError('Local account setup failed; see private account-response.xml')
Path('account-key').write_text(a)
PY
fi
mkdir -p client
cat > client/cc_config.xml <<'XML'
<cc_config><options><ncpus>1</ncpus><no_gpus>1</no_gpus><skip_cpu_benchmarks>1</skip_cpu_benchmarks></options><log_flags><task>1</task><file_xfer>1</file_xfer><sched_ops>1</sched_ops></log_flags></cc_config>
XML
cat > client/global_prefs_override.xml <<'XML'
<global_preferences><run_on_batteries>1</run_on_batteries><run_if_user_active>1</run_if_user_active><cpu_usage_limit>100</cpu_usage_limit><suspend_cpu_usage>0</suspend_cpu_usage><max_ncpus_pct>100</max_ncpus_pct><work_buf_min_days>0</work_buf_min_days><work_buf_additional_days>0</work_buf_additional_days></global_preferences>
XML
# All networking for this test client is to the private loopback project.
# Acquiring sources/packages uses the original environment, not this override.
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy "$BOINC_STOCK/root/usr/bin/boinc" --dir "$BOINC_STOCK/client" --no_gpus --no_info_fetch --allow_multiple_clients --gui_rpc_port 31420 --attach_project http://127.0.0.1:8765/fifth42/ "$(cat account-key)" > client-console.log 2>&1 &
echo $! > client.pid
printf 'Client started with one CPU, GPU disabled. PID %s\n' "$(cat client.pid)"
