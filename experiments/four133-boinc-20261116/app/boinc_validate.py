"""script_validator hook; trusted database/config select work and binary identity."""
import json
import os
from pathlib import Path
import subprocess
import sys

from protocol import atomic, load_manifest
from validate import InfrastructureUnavailable, validate


def main(argv):
    if len(argv) != 3 or not argv[1].isascii() or not argv[1].isdecimal():
        raise ValueError('Expected result ID and exactly one uploaded output')
    config = json.loads(Path(os.environ['FOUR133_VALIDATOR_CONFIG']).read_text())
    sql = ('SELECT w.name,r.app_version_id,a.name FROM result r JOIN workunit w '
           'ON w.id=r.workunitid JOIN app a ON a.id=w.appid '
           f'WHERE r.id={int(argv[1])};')
    try:
        rows = subprocess.check_output(config['mysql_command'] + ['--batch','--skip-column-names',
            config['database'],'-e',sql],text=True,timeout=15).splitlines()
    except (OSError,subprocess.SubprocessError) as exc:
        raise InfrastructureUnavailable('Result lookup unavailable') from exc
    if len(rows) != 1:
        raise InfrastructureUnavailable('Result lookup missing or ambiguous')
    name,version,app = rows[0].split('\t')
    work = config['workunits'][name]
    if app != 'four133' or int(version) not in work['allowed_app_version_ids']:
        raise InfrastructureUnavailable('Trusted assignment/app version differs')
    engine = config['application_versions'][version]['engine_sha256']
    # A corrupt/missing trusted assignment is an operator fault.
    load_manifest(work['manifest'])
    try:
        outcome = validate(work['manifest'],argv[2],config['gmp_reference'],engine,'BOINC')
    except (ValueError,AssertionError) as exc:
        print('Scientific validation rejected: '+str(exc),file=sys.stderr)
        return 1
    outcome.update(boinc_result_id=int(argv[1]),boinc_workunit=name,boinc_app_version_id=int(version))
    atomic(Path(config['audit_directory'])/(argv[1]+'.json'),outcome)
    print(json.dumps(outcome,sort_keys=True))
    return 0


def cli(argv):
    try:
        return main(argv)
    except Exception as exc:
        # Trusted configuration, database, oracle and unexpected failures are
        # retryable infrastructure faults. Never expose credentials in errors.
        print('Validation deferred: server-side '+type(exc).__name__,file=sys.stderr)
        return 3


if __name__ == '__main__':
    sys.exit(cli(sys.argv))
