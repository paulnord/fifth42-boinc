#!/bin/bash
set -euo pipefail
set -x
apt-get -o APT::Sandbox::User=root update
apt-get -o APT::Sandbox::User=root --download-only --no-install-recommends -y \
  install build-essential git curl python3 libgmp-dev ca-certificates media-types \
  procps iproute2 time
