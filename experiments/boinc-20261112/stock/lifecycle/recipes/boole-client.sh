#!/bin/bash
set -euo pipefail
umask 077
mkdir -p /pilot/home /pilot/client
python3 /recipe/socket_relay.py --listen-port 8765 --target-unix /pilot/project.sock > /evidence/relay.log 2>&1 &
relay=$!
cleanup(){ kill "$relay" 2>/dev/null || true; wait "$relay" 2>/dev/null || true; }
trap cleanup EXIT
cat > /pilot/client/cc_config.xml <<'XML'
<cc_config><options><ncpus>1</ncpus><skip_cpu_benchmarks>1</skip_cpu_benchmarks></options><log_flags><task>1</task><file_xfer>1</file_xfer><sched_ops>1</sched_ops><coproc_debug>1</coproc_debug></log_flags></cc_config>
XML
cat > /pilot/client/global_prefs_override.xml <<'XML'
<global_preferences><run_on_batteries>1</run_on_batteries><run_if_user_active>1</run_if_user_active><run_gpu_if_user_active>1</run_gpu_if_user_active><cpu_usage_limit>100</cpu_usage_limit><suspend_cpu_usage>0</suspend_cpu_usage><max_ncpus_pct>100</max_ncpus_pct><work_buf_min_days>0</work_buf_min_days><work_buf_additional_days>0</work_buf_additional_days></global_preferences>
XML
/pilot/runtime/usr/bin/boinc --dir /pilot/client --no_info_fetch --allow_multiple_clients --gui_rpc_port 31422 > /evidence/client-console.log 2>&1 &
client=$!
wait "$client"
