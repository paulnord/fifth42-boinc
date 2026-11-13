#!/bin/bash
set -euo pipefail
export HERE=/source/experiments/boinc-20261112 STOCK=/pilot/stock-verify RUNTIME=/pilot/science/runtime
bash "$HERE/stock/with_stack.sh" "$STOCK" bash -c 'export PYTHONPATH="$HERE/stock/lifecycle"; python3 - <<'"'"'PY'"'"'
import run_suite as s
s.start_client()
s.infrastructure_tests(int(s.sql("SELECT id FROM app_version WHERE version_num=101")))
s.finish()
PY'
ss -lntup > /evidence/listeners-after.txt
cp "$STOCK/validator.log" /evidence/validator-final.log
cp "$STOCK/mysql.log" /evidence/mysql.log
cp "$RUNTIME/results/benchmark-cpu.json" /evidence/full-native-baseline.json
