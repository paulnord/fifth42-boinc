# Cabbage private CPU pilot, 2026-11-13

The local Debian 13 CPU pilot passed: workunit `cabbage_pilot_control` (ID 1),
canonical result 1, application version 1.00/ID 1, three signed control packets,
nine positions, and fresh independent GMP validation. The client downloaded the
six staged application files with matching SHA256 hashes and uploaded its actual
1,793-byte result. All fixtures remain `TEST_ONLY`, with zero production coverage.
The client was drained and quit through BOINC RPC; MariaDB shut down normally;
no pilot processes or listeners remained. No other host was attached.

The initial source was `aad1bb3c87c26081f3243ad68a7ab1a42e23b9de`. BOINC remains
at upstream `351ad42a102c2bbe70e33f7aa44c23ac6ac3db9c` (server release 1.6.3,
wrapper 8.3.26019), and the Debian client is 8.0.4. The science source is pinned
to `4668a27951f2b9d7d533896d1aa32684808341d4`. Numerical and BOINC source were
not patched. Private data, keys and authenticators stay outside this repository.

## Host and isolation

Cabbage is Ubuntu 26.04.1 LTS, x86_64, with 32 logical CPUs and 125 GiB RAM.
Its root filesystem had about 94 GiB free; `/mnt/localstorage` had 6.9 TiB free.
Docker 29.8.2 was installed but inaccessible to this account. Passwordless sudo
was unavailable; plain `unshare -Urn` was denied. Installed Bubblewrap 0.11.1
successfully provided rootless user, mount, PID, IPC, UTS and network namespaces.
No Docker permissions, host packages or security policies were changed.

The supplied `cabbage/` recipe is specific to Cabbage's `pnord` UID/GID 1330.
Its namespaces mount only the private Debian root, prototype source, private
work/evidence directories, a new `/proc`, minimal `/dev`, and temporary directories.
There are no production/NFS mounts, GPU devices, host-network services or port
forwards. Acquisition/build modes share host networking for downloads; runtime
has only private loopback, with no external interface or routes. The server and
separate client process run in the same runtime namespace.

Each scope has a two-CPU quota, 4 GiB memory limit, zero swap allowance, 256-task
limit, nice 19 and idle I/O priority. The client requests one CPU with GPUs disabled.
The successful initial runtime took 51.3 seconds and peaked at 203.64 MiB of
aggregate cgroup memory; the initial build phases peaked at 1.52 GiB. These tiny
controls are integration evidence, not a throughput or production-sizing result.
The revised combined bootstrap then passed from another empty directory in
146.5 seconds, peaking at 2.04 GiB, without the earlier compiler-environment
workaround. Real TCP regression tests passed for TIME_WAIT reuse and refusal of
an active listener.
The revised initialize/start scripts also passed another real control job against
that fresh build and a new database in one private namespace, including immediate
startup after initialization. Its own WU 1/canonical result 1 was accepted by GMP,
and its client/server services stopped cleanly. This confirms the port-guard fix
in the actual lifecycle, as well as in the TCP regression tests.

## Recipe

Use a new destination. The retained initial pilot is at
`/mnt/localstorage/pnord-fifth42-boinc-pilot-20261113`; do not initialize over it.
These scripts preserve the executed host/container layout. The bootstrap changes
are validated separately from the original corrected/resumed run.

```bash
set -euo pipefail
export PILOT=/mnt/localstorage/pnord-fifth42-boinc-pilot-new
test "$(id -u)" -eq 1330
test "$(id -g)" -eq 1330
test ! -e "$PILOT"
mkdir -m 700 "$PILOT"
git clone https://github.com/paulnord/fifth42-boinc.git "$PILOT/source"
git -C "$PILOT/source" rev-parse HEAD
cp -a "$PILOT/source/experiments/boinc-20261112/stock/cabbage/." "$PILOT/"
cd "$PILOT"
mkdir -p rootfs work/home evidence
curl -fL --retry 2 https://raw.githubusercontent.com/debuerreotype/docker-debian-artifacts/373f61a386722a989c79f0c11f23fcf379b56e94/trixie/oci/blobs/rootfs.tar.gz -o debian13-rootfs.tar.gz
curl -fsSL https://raw.githubusercontent.com/debuerreotype/docker-debian-artifacts/373f61a386722a989c79f0c11f23fcf379b56e94/trixie/oci/blobs/image-manifest.json -o evidence/debian-oci-manifest.json
bash prepare-rootfs.sh > evidence/prepare-rootfs.log 2>&1
python3 run-step.py build build /usr/bin/time -v -o /evidence/build-time.txt bash /recipe/build.sh
python3 run-step.py base-provenance local python3 /recipe/base-provenance.py
python3 run-step.py initialize local bash /recipe/initialize-app.sh
python3 run-step.py pilot local /usr/bin/time -v -o /evidence/pilot-time.txt bash /recipe/pilot.sh
```

The pinned Debian 13.7 OCI layer digest is
`a6dd1c05fbba4f9028078a11f143cbb625d2408921eb8207bfa1dd1ad301276f`.
`prepare-rootfs.sh` verifies it before extraction. APT verifies its signed indexes;
packages are downloaded and extracted without running maintainer scripts or
installing anything on the host. The host public CA bundle seeds the private
root's HTTPS trust store. Package hashes, resource samples, command logs, server
records, downloaded hashes, uploaded output, validator audit and shutdown checks
are retained in `evidence/`. Database state, a consistent SQL backup, test account
keys and signing keys remain private under `work/stock/`.

For manual operations, enter `./container.sh local bash`, export `HERE`, `STOCK`
and `RUNTIME` as in the stock README (container paths `/source/...`, `/pilot/stock`,
`/pilot/science/runtime`), then start `with_stack.sh` and use its nested shell.
Every status/drain/RPC command must run in that same container invocation.
Each new invocation has a different private loopback. No restart persistence is
installed. The README's lifecycle commands apply; the helper `quit-client.py`
provides a graceful RPC quit before exiting the service shell.

## Setup failures and fixes

* The artifact repository now stores its root layer at `trixie/oci/blobs/rootfs.tar.gz`;
  the initial old `trixie/rootfs.tar.xz` URL returned 404.
* The clean BOINC build initially missed `curl/curl.h`: the extracted Debian
  multiarch include directory was absent from compiler flags. Bootstrap now
  supplies both include directories.
* Subdirectory-only builds missed `svn_version.h`. Bootstrap now runs the
  upstream top-level generation target before compiling subdirectories.
* Immediate startup after the temporary initialization database exited failed
  the bare-bind preflight because of TCP TIME_WAIT. The common preflight now uses
  `SO_REUSEADDR`; real TCP tests confirm that live listeners still fail. The
  container recipe also keeps initialization in a separate private invocation.
* `HERE`, `STOCK` and `RUNTIME` must be exported for nested shells; the stock
  README now does so explicitly.

The original failed logs and successful corrected run are retained locally. This
does not reclassify the earlier Debian prototype's evidence as Cabbage testing.
Recovery, retries, upgrades, large fixtures, GPU execution, host-loss and
production migration were not rerun as part of this initial control test.

## Separate follow-ups

For secure LAN clients, use a stable HTTPS project URL and regenerate/verify all
scheduler/download/upload URLs; replace loopback-only HTTP policy with narrowly
authorized client access; restrict enrollment and administration; protect signing
material; use a least-privilege database account and managed secrets; keep the DB
and client RPC private; and establish ownership, backups and restore checks.
The demo passwordless database must not be exposed. The prototype's validator
infrastructure-error handling and packaging compatibility also need hardening.

GPU work needs a separately authorized available GPU, a compatible CUDA build,
BOINC NVIDIA plan-class and CPU/GPU resource requests, actual allocated-device
mapping through `$GPU_DEVICE_NUM`/visibility, and CPU/GPU/GMP comparisons plus a
real GPU workunit and suspend/abort checks. See upstream [plan classes](https://github.com/BOINC/boinc/wiki/Specifying-plan-classes-in-XML)
and [wrapper support](https://github.com/BOINC/boinc/wiki/WrapperApp). No GPU
application or Ada/Boole client was deployed by this pilot.
