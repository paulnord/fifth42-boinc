#!/bin/bash
set -euo pipefail
set -x
export HERE=/source/experiments/boinc-20261112
export STOCK=/pilot/stock
export RUNTIME=/pilot/science/runtime
date -u --iso-8601=seconds
cat /etc/os-release
id
gcc --version
g++ --version
python3 --version
mkdir /pilot/science
git clone --filter=blob:none --no-checkout https://github.com/paulnord/fifth42.git /pilot/science/inputs
git -C /pilot/science/inputs checkout --detach 4668a27951f2b9d7d533896d1aa32684808341d4
python3 /pilot/science/inputs/colab/20261112/load_bundle.py --destination "$RUNTIME"
(cd "$RUNTIME"; python3 build.py)
bash "$HERE/stock/bootstrap.sh" "$STOCK"
date -u --iso-8601=seconds
