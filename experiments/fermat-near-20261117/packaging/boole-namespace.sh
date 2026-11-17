#!/bin/bash
set -euo pipefail
base=${1:?new private client directory}; runtime=${2:?existing extracted BOINC runtime}; shift 2
exec bwrap --unshare-all --uid "$(id -u)" --gid "$(id -g)" --hostname boole-near-test \
  --tmpfs / --ro-bind /usr /usr --ro-bind /etc /etc --ro-bind /sys /sys \
  --ro-bind "$base/work/hosts" /etc/hosts \
  --symlink usr/bin /bin --symlink usr/sbin /sbin --symlink usr/lib /lib --symlink usr/lib64 /lib64 \
  --bind "$base/work" /pilot --ro-bind "$runtime" /pilot/runtime \
  --ro-bind "$base/recipe" /recipe --bind "$base/evidence" /evidence \
  --dir /home --dir /mnt --dir /media --proc /proc --dev /dev --tmpfs /tmp --tmpfs /run \
  --dev-bind /dev/nvidia0 /dev/nvidia0 --dev-bind /dev/nvidiactl /dev/nvidiactl \
  --dev-bind /dev/nvidia-uvm /dev/nvidia-uvm --dev-bind /dev/nvidia-uvm-tools /dev/nvidia-uvm-tools \
  --clearenv --setenv HOME /pilot/home --setenv USER pnord --setenv LANG C.UTF-8 \
  --setenv PATH /usr/bin:/bin --setenv LD_LIBRARY_PATH /pilot/runtime/usr/lib/x86_64-linux-gnu \
  --chdir /pilot "$@"
