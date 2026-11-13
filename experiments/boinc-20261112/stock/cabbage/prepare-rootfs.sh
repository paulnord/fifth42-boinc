#!/bin/bash
set -euo pipefail
BASE=$(cd -- "$(dirname -- "$0")" && pwd)
cd "$BASE"
set -x
printf '%s  %s\n' a6dd1c05fbba4f9028078a11f143cbb625d2408921eb8207bfa1dd1ad301276f debian13-rootfs.tar.gz | sha256sum -c -
test ! -e rootfs/.pilot-extracted
tar --extract --gzip --file debian13-rootfs.tar.gz --directory rootfs --no-same-owner
touch rootfs/.pilot-extracted
# No package postinsts, user creation, daemon installation, or host package changes.
cp -L /etc/resolv.conf rootfs/etc/resolv.conf
printf '127.0.0.1 localhost fifth42-boinc-pilot\n::1 localhost\n' > rootfs/etc/hosts
printf 'pnord:x:1330:1330:Pilot:/pilot/home:/bin/bash\n' >> rootfs/etc/passwd
printf 'pnord:x:1330:\n' >> rootfs/etc/group
./container.sh acquire bash /recipe/acquire.sh
for deb in rootfs/var/cache/apt/archives/*.deb; do dpkg-deb --extract "$deb" rootfs; done
# ca-certificates normally generates this bundle in postinst; use the host's
# public trust store solely as a seed, copying it into the private Debian root.
mkdir -p rootfs/etc/ssl/certs
cp /etc/ssl/certs/ca-certificates.crt rootfs/etc/ssl/certs/ca-certificates.crt
python3 - <<'PY'
import hashlib,json,subprocess
from pathlib import Path
items=[]
for p in sorted(Path('rootfs/var/cache/apt/archives').glob('*.deb')):
    fields=subprocess.check_output(['dpkg-deb','-f',str(p),'Package','Version','Architecture'],text=True)
    items.append(dict(file=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),metadata=fields))
Path('evidence/base-packages.json').write_text(json.dumps(items,indent=2)+'\n')
PY
./container.sh build bash -c 'id; cat /etc/debian_version; python3 --version; gcc --version; g++ --version; git --version; curl --version; make --version'
