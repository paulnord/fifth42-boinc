# Four 133rd powers through BOINC

This is a separate, single-CPU application for
`a^133+b^133+c^133+d^133=42`, including signed and repeated integer bases.
It packages the original modular engine from `paulnord/fifth42` commit
`853fd98fc91968987fcb3e9e4c43b4fe880c8246`, with byte identities in
[UPSTREAM.json](UPSTREAM.json). Numerical source, range guards, two sieve moduli
and finite-box proof are preserved. BOINC handles delivery and scheduling.
The host-specific eight-hour coordinator is not included in the client.

## Build and test

Native packages target Linux x86_64 and Apple Silicon macOS. A C++17 compiler
and GMP development files are needed to build the independent server checker.
The client engine itself has no GMP dependency. The package includes a pinned
stock BOINC 26019 wrapper and pinned relocatable CPython 3.13.18 runtime.

```sh
python3 packaging/build.py bundle
FOUR133_TEST_BUILD=bundle python3 -m unittest discover -s tests -v
python3 packaging/smoke.py bundle wrapper-slot
```

The build produces `bundle/four133-boinc.tar.gz`. Its client files are `wrapper`,
`runtime.zip` and `job.xml`; `BOINC_BUILD.json` binds hashes, source and platform.
Linux additionally ships the hash-pinned stock wrapper's `libzip.so.4` and its
copyright notice, using BOINC's normal slot library search path. The Linux
package targets current glibc systems (Ubuntu 24.04/Debian 13 class); it still
uses the operating system's C, zlib, bzip2 and OpenSSL 3 libraries.
Work templates reserve two GiB of disk for the runtime archive, unpacked files,
checkpoints and output. The Linux standalone Python distribution unpacks to
about 550 MiB; Mac is about 100 MiB. Actual byte counts are in build metadata.
The CI workflow builds on native Linux and arm64 Mac runners. Wrapper smoke is
explicitly a standalone wrapper test, separate from real BOINC client acceptance.

Every task uses one CPU and no GPU. Native chunks are bounded to sixteen gaps,
20,000 emitted candidates and four MiB of logs, with at most eight tasks and two
million pair entries per work unit. Each invocation budgets 300 CPU seconds
across the driver and its children; the native process receives the remaining
kernel CPU limit. BOINC suspension and duty-cycle waits do not consume that
budget, so user CPU-time limits do not cause a wall-clock timeout.
Linux retains the original one-GiB address-space guard. Darwin rejects that
limit; `packaging/macos_engine.cpp` caps live C++ heap allocations at one GiB
instead. The engine's power table and pair buffers are standard C++ vectors.
The adapter also converts Darwin's RSS bytes to KiB. Its hash and guard type
are recorded in build metadata; a separately compiled self-test verifies
allocation rejection and release accounting. Mathematical source remains
byte-identical, including its 20-million maximum absolute base. No new long
search is started by packaging.

## Work and validation

`app/make_work.py` generates bounded work for both original sieve moduli. For
example, the following creates a TEST_ONLY replay using the production-domain
guards; it does not admit a production search or claim new coverage:

```sh
python3 app/make_work.py --bound 5000000 --first-gap 1 --gap-count 1 \
  --unit-id four133-domain-check --output domain-check.json
```

`--search` changes the manifest purpose and requires the original shell's
`previous_bound=4000000`, all normalized ordinary-sum constraints, and both
moduli for each assigned region. Planning an entire larger box requires every
case from the upstream proof and a separately admitted authoritative campaign.
Individual receipts verify only their assigned gaps. They do not claim a new
full-box result or automatically credit coverage that might overlap an existing
search.

The default control manifest exercises both sign patterns and both reflections
using a small TEST_ONLY sieve modulus that produces modular collisions. Those
collisions are not exact solutions to 42.

The driver fsyncs a native log and receipt before advancing its checkpoint.
Restart rechecks the immutable work identity, binary identity and all committed
logs. An uncommitted chunk is recomputed. The wrapper receives the application's
checkpoint and fraction-done files through its standard interface.

The server validator independently re-enumerates every modular pair join,
including equal-residue multiplicities, canonicalization and per-gap counts.
It checks all final candidate powers using a separately compiled GMP program.
Forged zero-candidate output is rejected even if worker-reported pair counts
and log hashes are self-consistent. Infrastructure failures such as an unavailable
oracle remain retryable rather than marking scientifically valid work invalid.

## Distribution scope

Register this as BOINC application `four133`, distinct from `fifth42`. Stage
immutable native versions and use logical filenames `manifest.json` and
`result.json`. No project credentials, database, signing keys or authenticators
belong in the package or repository. Existing fifth-power apps and production
searches remain separate.

`packaging/server.py` stages and signs immutable versions with the stock server
tools and submits TEST_ONLY work to an explicit host. Run it inside the existing
project environment. Prepare a private server-only JSON config containing
`mysql_command` (an argument array, with credentials kept in a private defaults
file), `database`, `gmp_reference` (the server-native `gmp_exact` executable),
`audit_directory`, and empty `application_versions` / `workunits` dictionaries.
The source tree must remain available at its installed absolute path.

```sh
python3 packaging/server.py --project PROJECT --config PRIVATE_CONFIG stage BUNDLE
python3 packaging/server.py --project PROJECT --config PRIVATE_CONFIG \
  submit TEST_MANIFEST --host HOST_ID --version REGISTERED_APP_VERSION_ID
python3 packaging/server.py --project PROJECT --config PRIVATE_CONFIG validate
```

Staging adds the CPU plan and enables stock host assignments, retaining the prior
project config in `four133-config-before-assignment.xml`. The output template
uses the stock scheduler's required line layout. The hook resolves the work unit
and actual app version from the server database; worker declarations cannot
choose either. Successful audits are saved by BOINC result ID. Scientific
rejection returns 1; server/database/oracle failures return 3 for retry. Use an
external process/resource supervisor for validators and pilot clients.
The launcher uses a project log directory because stock `script_validator`
resolves its hook as `../bin/four133_validate`.

User CPU limits remain BOINC controls. The client explicitly requires an
allocation of exactly one CPU and no GPU. No automatic tuning, GPU backend or
thermal-performance claim is included in this first CPU package.
