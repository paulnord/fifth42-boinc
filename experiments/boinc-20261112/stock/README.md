# Stock BOINC installation used by the prototype

This is a **private, loopback-only, one-user Linux prototype**, not a public BOINC
service deployment. No source files in BOINC were patched. All scheduling,
assignment, application signatures, downloads, uploads, deadlines, retries and
canonical-result handling use upstream BOINC. The custom pieces are the bounded
Fifth42 science driver, work submission/trusted manifest registration, and exact
scientific validator.

## Versions actually executed

| Component | Identity |
|---|---|
| BOINC server | upstream tag `server_release/1.6/1.6.3` |
| Source | `351ad42a102c2bbe70e33f7aa44c23ac6ac3db9c` |
| Configure package version | `8.3.0` (different upstream numbering, not another source) |
| Supplied wrapper | startup `8.3.26019`, same source commit |
| Stock client/boinccmd | Debian `8.0.4+dfsg-1` |
| MariaDB | Debian `11.8.6-0+deb13u1` |
| Apache/PHP | `2.4.68` / `8.4.24` |

See `executed-stock-provenance.json` for executable SHA256 hashes. The Debian
package lock includes package versions, official repository filenames and SHA256.
The development host is Debian 13 x86_64. This first binary package is **not a
portable volunteer release**: it uses host Python 3.13, shared system libraries,
and the native engine's recent glibc/libstdc++ ABI. Later distribution needs a
compatible baseline or bundled dependency policy and its own validation.

## Build and initialize

Prerequisites on an isolated Debian 13 x86_64 host: `git`, `curl`, `dpkg-deb`,
`make`, GCC/G++ 14, `/usr/bin/python3` 3.13, and GMP development headers for the
separately built Fifth42 engine. Use the pinned handoff's loader and `build.py` to
create `RUNTIME` first. These scripts do **not** install system packages or alter
GPU drivers. They extract official packages into a new private directory.

```bash
export HERE=/absolute/path/to/fifth42/experiments/boinc-20261112
export STOCK=/absolute/path/to/new-boinc-test
export RUNTIME=/absolute/path/to/fifth42-boinc-runtime
bash "$HERE/stock/bootstrap.sh" "$STOCK"
bash "$HERE/stock/initialize.sh" "$STOCK"
python3 "$HERE/stock/stage_application.py" --stock "$STOCK" --runtime "$RUNTIME" \
  --label A --build A --version 1.00
```

`bootstrap.sh` codifies the exact build commands exercised during this work. Its
final combined form has syntax checks; the server was built by the equivalent
individual commands, not by a second full clean compilation. Fresh-project
setup and the reusable integration scripts passed a second real BOINC job against
that built stock runtime: `recipe_control`, canonical result 1, three packets/nine
positions, independently accepted at 2026-11-12 22:08:32 UTC. See
`fresh-recipe-smoke.json` and `fresh-recipe-status.txt`. Do not confuse this with a container-image reproducibility
claim.

The later Cabbage validation on 2026-11-13 ran the revised combined bootstrap
successfully from a new empty directory in Debian 13, including its multiarch
include paths and generated version-header step. The original corrected/resumed
control run is recorded separately in [the Cabbage pilot notes](CABBAGE_PILOT.md).

Upstream build details that mattered:

* Extracted Debian headers include a multiarch subtree; pass both
  `root/usr/include` and `root/usr/include/x86_64-linux-gnu` to the compiler.
* Generate upstream `svn_version.h` before building individual subdirectories.
* Rootless extracted Autoconf/Automake/Libtool need their data paths relocated.
  Only local bootstrap tool scripts are adjusted; BOINC remains unchanged.
* Complete package extraction **before** configure/build. Concurrent extraction
  initially caused a transient `as: Text file busy` feature probe failure.
* BOINC's Python `setup.py` uses removed `distutils`. It isn't needed to run the
  source-tree tools: build `api lib zip sched tools apps vda` directly and use the
  provided Python modules with `PYTHONPATH`.
* Use BOINC's supplied **`stage_file_native`**. The PHP `stage_file` in this
  upstream release failed here with undefined `parse_config()`.
* The client ignores the container's localhost proxy exception in this setup.
  The client subprocess alone has proxy variables unset and contacts only
  `127.0.0.1`; source/package acquisition retains its normal proxy environment.
* This execution environment prohibits Unix-domain sockets. MariaDB works over
  loopback TCP with `--socket=`. BOINC SysV shared memory and loopback TCP were
  tested successfully. No security setting or kernel change was made.

## Start, release, submit, status, drain, cleanup

Keep all services and test commands in the same isolated host/session. The start
command opens a shell surrounded by stock services. Exit that shell to stop
services cleanly, retaining the database, checkpoints and evidence.

```bash
bash "$HERE/stock/with_stack.sh" "$STOCK" bash
# Now inside that shell; source environment if needed:
source "$STOCK/env.sh"
cd "$STOCK/project"
php bin/update_versions --noconfirm --verbose
# This stages and signs ordinary immutable BOINC application files.

python3 "$HERE/scripts/make_manifest.py" --catalog "$RUNTIME/data/packets.jsonl" \
  --output "$STOCK/control.json" \
  --names control-cap100-r12 control-cap42-r12 control-cap2951-r-2002

python3 "$HERE/stock/submit.py" --stock "$STOCK" --runtime "$RUNTIME" \
  --manifest "$STOCK/control.json" --name first_control \
  --app-version-id 1 --build A
bash "$HERE/stock/start_client.sh" "$STOCK"
bash "$HERE/stock/status.sh" "$STOCK"
bash "$HERE/stock/drain.sh" "$STOCK"
# Wait for accepted results, then exit to stop the test stack.
exit
```

Use the **actual** application-version ID printed by `update_versions`, not
necessarily `1` after prior releases. The submit helper pins BOINC's version
number and the server-side allowed app-version ID, copies the exact trusted
manifest, and registers its independent GMP validator mapping before submission.
Inputs and application files are immutable. To add B, use a new version and
physical label, for example `--label B --build B --version 1.02`, then run stock
`update_versions` again. Do not edit files already in `project/download`.

`status.sh` reads BOINC's result/workunit database records and `boinccmd --get_tasks`.
The normal BOINC web interface is at `http://127.0.0.1:8765/fifth42/` while running.
`drain.sh` uses BOINC's `nomorework` command and requests a scheduler update.
`with_stack.sh` stops its child services on exit; it does not erase data.
For local restart, rerun `with_stack.sh` with the same directory and restart the
client with the same client directory. Do not rerun `initialize.sh` over a project.

## Boundaries and operational cautions

The rootless demonstration database uses the isolated MariaDB instance's local
root account with no password, exactly as the executed prototype did. Ports
3306 and 8765 are restricted to loopback. This is suitable only in the isolated
single-user development container. It is **not** a shared-host/public service
security configuration. Before a maintained deployment use a least-privilege
project database account, secret management, authenticated administrative pages,
TLS and normal service ownership/backups. Do not expose these prototype ports.
The scripts refuse occupied ports before starting; they never reuse a running
production database. Signing keys, database files, account authenticators and
client XML remain outside Git.

The port check uses `SO_REUSEADDR` so that a clean database shutdown during
initialization does not produce a false occupied-port failure from TCP TIME_WAIT.
Live listeners still cause setup to fail. `HERE`, `STOCK` and `RUNTIME` must be
exported before entering the nested stack shell. See [the Cabbage pilot](CABBAGE_PILOT.md)
for the Debian 13 rootless-container recipe and the separately recorded host test.

The wrapper must resolve BOINC logical filenames. App modules are declared
`copy_file` into the slot; packet input/output/engine use `boinc_resolve(...)`.
The wrapper exposes checkpoint/progress only after real committed work. The
server validator runs from the usual daemon subdirectory (`project/tmp`), because
upstream `script_validator` invokes `../bin/<hook>`.

BOINC templates are line-oriented in places. An early one-line result template
failed with `insert_after: <result> not found`; the checked-in templates preserve
newlines. Early validator launch attempts used the wrong working directory and
were rejected. Those are setup failures, not successful scientific validation.
The first accepted real control was workunit `controlA2`, canonical result `4`,
three packets/nine positions, independently validated at 2026-11-12 21:59:28 UTC.
All such work is TEST_ONLY and earns **zero new scientific coverage**.
