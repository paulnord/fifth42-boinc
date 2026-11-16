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
The CI workflow builds on native Linux and arm64 Mac runners. Wrapper smoke is
explicitly a standalone wrapper test, separate from real BOINC client acceptance.

Every task uses one CPU and no GPU. Native chunks are bounded to sixteen gaps,
20,000 emitted candidates and four MiB of logs, with at most eight tasks and two
million pair entries per work unit. Application runtime is capped at 300 seconds.
The original native engine retains its one-GiB address-space guard and its
20-million maximum absolute base. No new long search is started by packaging.

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

User CPU limits remain BOINC controls. The client explicitly requires an
allocation of exactly one CPU and no GPU. No automatic tuning, GPU backend or
thermal-performance claim is included in this first CPU package.
