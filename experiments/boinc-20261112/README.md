# Fifth42 stock BOINC prototype (TEST_ONLY)

This is isolated integration work, **not production deployment**. Replayed fixtures
contribute **zero new scientific coverage**. Existing workers, grants, deadlines,
reservations and NFS data are untouched.

## What is implemented

- `app/science_driver.py`: bounded CPU replay through the published persistent
  framed engine; exact verifier; atomic/fsynced receipts followed by checkpoint;
  durable prefix recovery; deterministic TEST_ONLY interruption/failure hooks.
- `app/validate_result.py`: server-side validation against a **trusted server
  manifest**, engine/build allowlist, strict counts and exact candidate
  reconstruction, and a newly executed independent GMP oracle. An existing file
  or exit status zero is not scientific acceptance.
- `scripts/make_manifest.py`: immutable known input catalog identity, explicit
  packet selection and TEST_ONLY scope.
- `scripts/package_application.py`: A/B build identities with unchanged numerical
  implementation, producing distinct driver hashes. These packages are staged through BOINC's normal version staging/signing/distribution in the executed integration.
- `scripts/prepare_science.sh`: reproducible input download, hash-checked unpack,
  Linux C++17 native build, direct baseline and tests.

## Direct science reproduction

Requires Linux x86_64, Python 3, git, g++, pthread and GMP development libraries.
From this directory:

```sh
bash scripts/prepare_science.sh /absolute/path/to/new-empty-workspace
FIFTH42_RUNTIME=/absolute/path/to/new-empty-workspace/runtime \
  python3 -m unittest discover -s tests -v
python3 scripts/package_application.py \
  --runtime /absolute/path/to/new-empty-workspace/runtime \
  --destination /absolute/path/to/application-A --build A
```

These commands do **not** claim BOINC end-to-end success. The real BOINC scheduler/transfer/version results are recorded in `REPORT.md`,
with reproducible operations in `stock/README.md`.
The initial implementation is CPU-only: no GPU is available in this development
workspace, and no production GPU was commandeered. Public volunteer enrollment
is out of scope.

## Evidence classification

`evidence/native-baseline.json` records the full 42-packet CPU comparison and
fresh independent GMP verification. `direct-tests.txt` and
`independent-review-tests.txt` cover direct application behavior and rejection
cases. These direct tests alone are not BOINC lifecycle evidence. The separate real
client/wrapper recovery and A/B rollout passed and are recorded under
`evidence/boinc/` and `REPORT.md`.

See `docs/ACCEPTANCE_REVIEW.md` and `docs/MIGRATION_REVIEW.md`. Migration remains
conditional on genuine integration results; never import TEST_ONLY fixture counts
as accepted search coverage. BOINC's at-least-once attempts must be distinguished
from one canonical accepted logical result. Executable provenance is verified
from actual client/server records, not trusted from worker self-reported hashes.

## Portability limits of the first CPU package

The first private test host supplies `/usr/bin/python3`; this prototype does not
claim a self-contained Python distribution for arbitrary volunteer computers.
The locally built native CPU executable dynamically links libstdc++, libgcc,
libc and libm, requiring observed symbols up to GLIBC 2.38 and GLIBCXX 3.4.32.
A broader deployment needs a deliberate older build baseline or packaged runtime,
plus plan-class compatibility checks and license review. Do not advertise this
specific binary as universal Linux, macOS or Windows support. Independent GMP
validation runs on the server; GMP is not a new client-side dependency here.
