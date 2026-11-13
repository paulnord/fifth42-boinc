#!/bin/bash
# Rootless Debian container. "acquire" has host networking ONLY for package download.
# "build" has host networking ONLY for source/package download and compilation.
# "local" has ONLY private loopback; all services and the client use this mode.
set -euo pipefail
BASE=$(cd -- "$(dirname -- "$0")" && pwd)
MODE=${1:?Usage: container.sh acquire|build|local COMMAND [ARGS...]}; shift
net=(); rootmode=--ro-bind; uid=1330
case "$MODE" in
  acquire) net=(--share-net); rootmode=--bind; uid=0;;
  build) net=(--share-net);;
  local) ;;
  *) exit 2;;
esac
exec systemd-run --user --scope --unit="fifth42-boinc-pilot-${MODE}-$$" \
  -p CPUQuota=200% -p MemoryMax=4G -p MemorySwapMax=0 -p TasksMax=256 \
  nice -n 19 ionice -c 3 \
  bwrap --unshare-all "${net[@]}" --uid "$uid" --gid "$uid" \
  --hostname fifth42-boinc-pilot --new-session --die-with-parent \
  "$rootmode" "$BASE/rootfs" / \
  --ro-bind "$BASE/source" /source \
  --ro-bind "$BASE/recipe" /recipe \
  --bind "$BASE/work" /pilot \
  --bind "$BASE/evidence" /evidence \
  --proc /proc --dev /dev --tmpfs /tmp --tmpfs /run \
  --clearenv --setenv PATH /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  --setenv USER pnord --setenv LOGNAME pnord --setenv HOME /pilot/home \
  --setenv LANG C.UTF-8 --setenv TZ UTC \
  --chdir /pilot "$@"
