"""Stock script_validator hook with a trusted database/work assignment."""
import json
import os
import subprocess
import sys
from pathlib import Path
from protocol import atomic, require
from validate import InfrastructureUnavailable, validate


def main(argv):
    require(len(argv) == 3 and argv[1].isascii() and argv[1].isdecimal(), 'Result ID and one upload required')
    config = json.loads(Path(os.environ['FERMAT_NEAR_VALIDATOR_CONFIG']).read_text())
    query = ('SELECT w.name,r.app_version_id,a.name,r.hostid FROM result r JOIN workunit w '
             'ON w.id=r.workunitid JOIN app a ON a.id=w.appid WHERE r.id=' + str(int(argv[1])))
    lines = subprocess.check_output(config['mysql_command'] + ['--batch', '--skip-column-names',
        config['database'], '-e', query], text=True, timeout=15).splitlines()
    if len(lines) != 1:
        raise InfrastructureUnavailable('Database lookup missing')
    name, version, app, host = lines[0].split('\t')
    work = config['workunits'][name]
    require(app == 'fermat_near' and int(version) in work['allowed_app_version_ids']
            and int(host) == work['target_host'], 'Database assignment differs')
    build = config['application_versions'][version]
    try:
        outcome = validate(work['manifest'], argv[2], config['gmp_reference'],
                           build['build_identity'], build['backend'])
    except (ValueError, AssertionError) as exc:
        print('Scientific rejection: ' + str(exc), file=sys.stderr)
        return 1
    outcome.update(boinc_result_id=int(argv[1]), boinc_workunit=name, boinc_app_version_id=int(version))
    atomic(Path(config['audit_directory']) / (argv[1] + '.json'), outcome)
    print(json.dumps(outcome, sort_keys=True))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except Exception as exc:
        print('Validation deferred: server-side ' + type(exc).__name__, file=sys.stderr)
        sys.exit(3)
