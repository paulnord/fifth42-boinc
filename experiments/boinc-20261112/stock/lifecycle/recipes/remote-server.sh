#!/bin/bash
set -euo pipefail
export HERE=/source/experiments/boinc-20261112 STOCK=/pilot/boole-server RUNTIME=/pilot/science/runtime
bash "$HERE/stock/initialize.sh" "$STOCK"
cp "$HERE/stock/lifecycle/fifth42_cuda.xml" "$STOCK/project/plan_class_spec.xml"
bash "$HERE/stock/with_stack.sh" "$STOCK" bash /recipe/prepare-remote.sh
