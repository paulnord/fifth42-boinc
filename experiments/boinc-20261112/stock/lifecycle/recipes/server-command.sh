#!/bin/bash
set -euo pipefail
export HERE=/source/experiments/boinc-20261112 STOCK=/pilot/boole-server RUNTIME=/pilot/science/runtime
source "$STOCK/env.sh"
export HOME="$STOCK"
exec "$@"
