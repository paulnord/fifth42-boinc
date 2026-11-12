# Real BOINC lifecycle recipe

Run these inside `with_stack.sh STOCK bash` after initializing the project. See
`README.md` for the first control and service lifetime. Preserve the actual DB IDs
from `update_versions` and `status.sh`; the IDs below describe the recorded run,
not universal constants. All jobs are TEST_ONLY and deadline_bound is 600 seconds.

The helper automatically prefixes science arguments with the stock wrapper's
`--passthrough_child` switch. Raw `create_work` calls must include that prefix.

The recorded sequence used:

| Physical application label | Build identity | BOINC version | app_version ID |
|---|---|---:|---:|
| A | A | 1.00 | 1 |
| A2 | A | 1.01 | 2 |
| B | B | 1.02 | 3 |

A2 added wrapper forwarding of workunit command-line arguments and its
multi-process flag, without changing the embedded science A build. The reusable
`stage_application.py` includes those flags from the beginning. Each label's
physical filenames remain immutable; no existing download was overwritten.

Set up a convenient standard client-command helper in the running shell:

```bash
bc() {
  (cd "$STOCK/client" && "$STOCK/root/usr/bin/boinccmd" \
    --host 127.0.0.1:31420 --passwd "$(cat gui_rpc_auth.cfg)" "$@")
}
```

Do not write this expanded password into logs or Git.

## Checkpoint and application rollout

1. Stage A2 with `stage_application.py --label A2 --build A --version 1.01` and
   invoke stock `php bin/update_versions --noconfirm --verbose` in the project.
2. Submit the three-control manifest with trusted build A and app-version ID 2.
   Pass `--command-line '--packet-delay 2 --pause-after 2 --pause-seconds 60'` to
   `submit.py`. These switches delay **real** committed work; they do not fabricate
   results or checkpoints.
3. Request work with `bc --project http://127.0.0.1:8765/fifth42/ update`.
4. Wait until the active slot's `checkpoint.json` reports `completed_prefix: 2`
   and `receipts.json` contains the matching two durable receipts. Save both, the
   wrapper/client state fields, and the active science stdout. Do not save raw
   client XML publicly because it contains account credentials.
5. While the old job is active, stage B with a **new** physical label/version
   `--label B --build B --version 1.02`, and run normal `update_versions` again.
   Capture the server application version records and SHA256 hashes of the files
   actually downloaded into the client's project directory. Existing A2 work
   retains its A2 app-version binding.
6. `bc --quit` requests a real client shutdown. Check that the science and wrapper
   processes exit. Keep the same client directory intact.
7. Restart the stock client via `start_client.sh STOCK`. The science stdout must
   say `resumed_prefix: 2`. Allow completion/upload, request a scheduler update,
   and verify the server scientific audit and canonical-result ID.
8. Submit an ordinary B job; confirm downloaded B's actual `science_driver.py`
   hash differs from A/A2 and matches its release manifest. Verify the uploaded B
   result with the same GMP oracle and inspect its BOINC app-version ID.

The packet delay spans wrapper polling intervals. Stock wrapper checkpoint
recognition uses whole-second mtime and ignores the first observation; a job
that finishes in milliseconds would not demonstrate checkpoint recognition.

## Failed attempt and retry

1. Submit a three-control B job with
   `--command-line '--packet-delay 2 --pause-after 1 --pause-seconds 60'`.
2. After a real durable prefix of one, save the slot's checkpoint/receipts.
3. Use stock `bc --task http://127.0.0.1:8765/fifth42/ RESULT_NAME abort` to create
   an explicitly failed attempt, and request a scheduler update.
4. Let BOINC's transitioner create and assign its retry. Do not submit the logical
   workunit twice and do not edit result states in SQL.
5. Observe the new attempt starts with prefix zero and repeats the whole bounded
   workunit. BOINC does not migrate the failed attempt's checkpoint. The server
   must accept only one canonical result for the logical workunit.

The recorded job `retryB` had aborted attempt 7 and accepted canonical result 12.
It repeated all three packets/nine positions; the earlier three-position prefix
was wasted work, not scientific coverage. This is retry/reassignment behavior,
not a claim of exactly-once execution or live checkpoint migration.

## Uploaded scientific negatives

For three distinct logical jobs, pass respectively:

```text
--corrupt-output identity
--corrupt-output count
--corrupt-output truncated
```

The actual native computation runs first. The test-only driver corrupts the
uploaded result **afterward** and exits zero. Observe BOINC execution success but
scientific rejection (`validate_state=2`), with no canonical result. The recorded
negative result IDs were 8, 9, and 10. Bounded error limits prevent endless retries.
Do not conflate those scientific negatives with the earlier hook/cwd setup faults.

## Representative packet

Use `make_manifest.py --names ada-upper-w0-b0` to select the exact catalog row recorded in
`trusted/representative.json` / the final evidence manifest, then `submit.py` with
B's registered ID. The recorded accepted workunit `representativeB`, canonical
result 11, visited 49,491,764 coefficient positions through the full
server/download/wrapper/upload/independent-GMP-validation path.

## Final audit and stop

Run `status.sh`, retain canonical IDs, app-version IDs, timestamps, binary/input
hashes, validator audits and uploaded outputs, then `drain.sh`. After all relevant
uploads are reported and validated, exit `with_stack.sh` to stop the private
stack. Keep the project database, signing keys and client directories private;
retain sanitized evidence separately. Do not delete unresolved production work,
change reservations, or import these fixtures as coverage.
