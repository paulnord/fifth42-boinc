#!/usr/bin/env python3
"""BOINC script_validator init hook: `boinc_validate result_id files`.
Config at FIFTH42_VALIDATOR_CONFIG (server only); uploaded claims never select work.
"""
import json,os,subprocess,sys
from pathlib import Path
from science_driver import atomic
from validate_result import validate
from validation_errors import ScientificValidationError, ValidationInfrastructureError

def resolve(config,result_id):
    if not result_id.isascii() or not result_id.isdecimal():raise ValueError('Invalid result ID')
    sql=('SELECT w.name,r.app_version_id FROM result r JOIN workunit w '
         f'ON w.id=r.workunitid WHERE r.id={int(result_id)};')
    # mysql_command includes trusted binary, private defaults file or localhost
    # connection flags. Credentials must not be placed in tracked config.
    command=config['mysql_command']+['--batch','--skip-column-names',config['database'],'-e',sql]
    try:
        lines=subprocess.check_output(command,text=True,timeout=15).splitlines()
    except (OSError,subprocess.SubprocessError) as exc:
        raise ValidationInfrastructureError('BOINC result lookup unavailable') from exc
    if len(lines)!=1:raise ValueError('Result not found or ambiguous')
    name,version=lines[0].split('\t');version=int(version)
    work=config['workunits'][name];app=config['application_versions'][str(version)]
    # For version-transition tests each logical job has an explicit allowed
    # app-version set; never accept a worker-declared build as authority.
    if version not in work['allowed_app_version_ids']:raise ValueError('Unexpected BOINC app version')
    return name,version,work,app

def main(argv):
    if len(argv)!=3:raise ValueError('Exactly result_id and one uploaded output required')
    cfg=json.loads(Path(os.environ['FIFTH42_VALIDATOR_CONFIG']).read_text())
    name,version,work,app=resolve(cfg,argv[1])
    outcome=validate(work['manifest'],argv[2],cfg['gmp_reference'],app['engine_sha256'],app['build'],app.get('backend','emulated'))
    outcome.update(boinc_result_id=int(argv[1]),boinc_workunit=name,boinc_app_version_id=version,uploaded_output=str(Path(argv[2]).resolve()))
    atomic(Path(cfg['audit_directory'])/(argv[1]+'.json'),outcome)
    print(json.dumps(outcome,sort_keys=True))
def cli(argv):
    try:
        main(argv)
        return 0
    except ScientificValidationError as exc:
        print(f'Scientific validation rejected: {exc}',file=sys.stderr)
        return 1
    except ValidationInfrastructureError as exc:
        print(f'Validation deferred: {exc}',file=sys.stderr)
        return 3
    except Exception as exc:
        # Missing/corrupt trusted config, filesystem errors, and unexpected bugs
        # require operator attention. Do not charge them to a healthy worker or
        # print subprocess arguments that could contain database credentials.
        print(f'Validation deferred: server-side {type(exc).__name__}',file=sys.stderr)
        return 3

if __name__=='__main__':
    sys.exit(cli(sys.argv))
