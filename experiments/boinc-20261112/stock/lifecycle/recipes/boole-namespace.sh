#!/bin/bash
set -euo pipefail
BASE=/home/pnord/boinc-fifth42-client-test-20261113
exec bwrap --unshare-all --uid 1330 --gid 1330 --hostname boole-boinc-test \
  --tmpfs / --ro-bind /usr /usr --ro-bind /etc /etc --ro-bind /sys /sys --ro-bind "$BASE/work/hosts" /etc/hosts \
  --symlink usr/bin /bin --symlink usr/sbin /sbin --symlink usr/lib /lib --symlink usr/lib64 /lib64 \
  --bind "$BASE/work" /pilot --ro-bind "$BASE/recipe" /recipe --bind "$BASE/evidence" /evidence \
  --dir /home --dir /mnt --dir /media --proc /proc --dev /dev --tmpfs /tmp --tmpfs /run \
  --dev-bind /dev/nvidia0 /dev/nvidia0 --dev-bind /dev/nvidiactl /dev/nvidiactl \
  --dev-bind /dev/nvidia-uvm /dev/nvidia-uvm --dev-bind /dev/nvidia-uvm-tools /dev/nvidia-uvm-tools \
  --clearenv --setenv HOME /pilot/home --setenv USER pnord --setenv LANG C.UTF-8 \
  --setenv PATH /usr/bin:/bin --setenv LD_LIBRARY_PATH /pilot/runtime/usr/lib/x86_64-linux-gnu \
  --chdir /pilot "$@"
