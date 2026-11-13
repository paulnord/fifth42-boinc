#!/bin/bash
# Run once, in its OWN private container invocation before recipe/pilot.sh.
# This avoids the stock port guard colliding with initialization TCP TIME_WAIT.
set -euo pipefail
set -x
export HERE=/source/experiments/boinc-20261112
export STOCK=/pilot/stock
export RUNTIME=/pilot/science/runtime
bash "$HERE/stock/initialize.sh" "$STOCK"
python3 "$HERE/stock/stage_application.py" --stock "$STOCK" --runtime "$RUNTIME" \
  --label CabbageA --build A --version 1.00
