"""Queue bounded native Windows BOINC controls in the private pilot server."""
import argparse
import json
from pathlib import Path
import re
import sys

from server import ROOT, immutable, sql, submit
sys.path.insert(0, str(ROOT / 'app'))
from make_work import make
from protocol import canonical, require


def objects(config, query):
    return [json.loads(line) for line in sql(config, query)]


def versions(config):
    rows = objects(config, "SELECT JSON_OBJECT('id',v.id,'version',v.version_num,"
        "'plan',v.plan_class) FROM app_version v JOIN app a ON a.id=v.appid "
        "JOIN platform p ON p.id=v.platformid WHERE a.name='fermat_near' "
        "AND p.name='windows_x86_64' AND v.version_num IN (140,150) AND v.deprecated=0")
    found = {}
    for row in rows:
        backend = {140: 'cpu', 150: 'gpu'}[row['version']]
        expected = 'fermat_near_cpu_1' if backend == 'cpu' else 'fermat_near_gpu_windows_1'
        require(row['plan'] == expected and backend not in found, 'Ambiguous Windows version')
        registered = config['application_versions'].get(str(row['id']))
        require(registered and registered['backend'] == backend and
                registered['version_num'] == row['version'], 'Untrusted Windows version')
        found[backend] = row
    require(set(found) == {'cpu', 'gpu'}, 'Stage both Windows packages first')
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--config', required=True)
    sub = parser.add_subparsers(dest='operation', required=True)
    sub.add_parser('doctor')
    sub.add_parser('hosts')
    status = sub.add_parser('status')
    status.add_argument('--host', type=int, required=True)
    queue = sub.add_parser('queue')
    queue.add_argument('--host', type=int, required=True)
    queue.add_argument('--backend', choices=['cpu', 'gpu'], required=True)
    queue.add_argument('--restart', action='store_true')
    queue.add_argument('--run-label', default='20261117')
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    registered = versions(config)
    if args.operation == 'doctor':
        print(json.dumps(dict(ready=True, Windows_versions=registered,
            project_url='http://127.0.0.1:8765/fifth42/', purpose='TEST_ONLY'), indent=2))
        return
    if args.operation == 'hosts':
        rows = objects(config, "SELECT JSON_OBJECT('host',id,'OS',os_name,"
            "'OS_version',os_version,'CPU',p_model,'last_rpc_UTC',FROM_UNIXTIME(rpc_time)) "
            "FROM host WHERE os_name LIKE '%Windows%' ORDER BY id DESC")
        print(json.dumps(rows, indent=2))
        return
    require(args.host > 0, 'Positive actual BOINC host ID required')
    if args.operation == 'status':
        rows = objects(config, "SELECT JSON_OBJECT('result',r.id,'workunit',w.name,"
            "'host',r.hostid,'app_version',r.app_version_id,'server_state',r.server_state,"
            "'outcome',r.outcome,'validate_state',r.validate_state,'exit_status',r.exit_status,"
            "'canonical_result',w.canonical_resultid) FROM result r JOIN workunit w "
            "ON w.id=r.workunitid JOIN app a ON a.id=w.appid WHERE a.name='fermat_near' "
            "AND r.hostid=" + str(args.host) + " ORDER BY r.id")
        for row in rows:
            row['accepted'] = (row['server_state'] == 5 and row['outcome'] == 1 and
                row['validate_state'] == 1 and row['exit_status'] == 0 and
                row['canonical_result'] == row['result'])
            audit = Path(config['audit_directory']) / (str(row['result']) + '.json')
            if audit.exists():
                data = json.loads(audit.read_text())
                row['GMP_verified_candidates'] = data['GMP_verified_candidates']
                row['resumed_tasks'] = data['resumed_tasks']
        print(json.dumps(rows, indent=2))
        return
    host = sql(config, 'SELECT os_name FROM host WHERE id=' + str(args.host))
    require(len(host) == 1 and 'windows' in host[0].lower(), 'Actual Windows BOINC host required')
    require(re.fullmatch(r'[A-Za-z0-9_-]{1,24}', args.run_label), 'Unsafe run label')
    version = registered[args.backend]['id']
    controls = [('restart', [21,32], 2,40,120)] if args.restart else [
        ('ranges', list(range(4,33)), 2,200,0), ('wide-match',[30],966,966,0)]
    for label, exponents, first, last, pause in controls:
        name = f'near-win-h{args.host}-{args.backend}-{label}-{args.run_label}'
        work = make(name, exponents, first,last, rows=256, pause=pause)
        path = Path(args.config).resolve().parent / 'near-windows-controls' / (name + '.json')
        immutable(path, canonical(work) + b'\n')
        config = json.loads(Path(args.config).read_text())
        if name in config['workunits']:
            admitted = config['workunits'][name]
            require(admitted['target_host'] == args.host and
                    admitted['allowed_app_version_ids'] == [version], 'Different admission exists')
            require(len(sql(config,"SELECT id FROM workunit WHERE name='" + name + "'")) == 1,
                    'Admission incomplete; inspect server before retrying')
            print(json.dumps(dict(already_queued=name)))
        else:
            submit(argparse.Namespace(project=args.project, config=args.config,
                manifest=str(path), host=args.host, version=version))


if __name__ == '__main__':
    main()
