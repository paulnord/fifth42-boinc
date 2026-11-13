#!/bin/bash
set -euo pipefail
export HERE=/source/experiments/boinc-20261112
export STOCK=/pilot/stock-verify
export RUNTIME=/pilot/science/runtime
ip -details address show > /evidence/network.txt
ip route show >> /evidence/network.txt
bash "$HERE/stock/initialize.sh" "$STOCK"
bash "$HERE/stock/with_stack.sh" "$STOCK" python3 "$HERE/stock/lifecycle/run_suite.py"
sleep 2
ss -lntup > /evidence/listeners-after.txt
ps -eo pid,ppid,stat,args > /evidence/processes-after.txt
cp "$STOCK/validator.log" /evidence/validator.log
cp "$STOCK/mysql.log" /evidence/mysql.log
cp "$STOCK/transitioner.log" /evidence/transitioner.log
cp "$RUNTIME/results/benchmark-cpu.json" /evidence/full-native-baseline.json
