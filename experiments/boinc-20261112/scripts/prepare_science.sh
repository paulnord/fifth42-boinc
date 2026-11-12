#!/usr/bin/env bash
set -euo pipefail
# Usage: prepare_science.sh NEW_WORKSPACE
# Never uses production files or ledgers; official published TEST_ONLY inputs only.
base=$(realpath -m "${1:?Specify a new empty workspace}")
test ! -e "$base" || { echo 'Destination already exists' >&2; exit 2; }
mkdir -p "$base"
git clone --filter=blob:none --no-checkout https://github.com/paulnord/fifth42.git "$base/inputs"
git -C "$base/inputs" checkout --detach 4668a27951f2b9d7d533896d1aa32684808341d4
python3 "$base/inputs/colab/20261112/load_bundle.py" --destination "$base/runtime"
(cd "$base/runtime"; python3 build.py; python3 colab_bench.py --backend cpu --repeats 1 --max-seconds 180 --verify-gmp)
scriptdir=$(cd "$(dirname "$0")" && pwd)
mkdir "$base/application"
cp "$scriptdir/../app/"*.py "$base/application/"
cp "$base/runtime/engine_session.py" "$base/runtime/colab_bench.py" "$base/runtime/bin/scaling_cpu" "$base/application/"
sha256sum "$base/application/"* > "$base/application.SHA256SUMS"
FIFTH42_RUNTIME="$base/runtime" python3 -m unittest discover -s "$scriptdir/../tests" -v
printf 'TEST_ONLY application prepared in %s/application; no BOINC execution claimed by this script.\n' "$base"
