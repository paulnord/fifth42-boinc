"""Stage immutable CPU/CUDA versions and submit private host-targeted controls."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from protocol import atomic, load_manifest, require, sha


def sql(config, query):
    return subprocess.check_output(config['mysql_command'] + ['--batch', '--skip-column-names',
        config['database'], '-e', query], text=True, timeout=30).splitlines()


def command(project, *args):
    return subprocess.check_output(args, cwd=project, text=True)


def immutable(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        require(path.read_bytes() == data, 'Existing immutable file differs: ' + str(path))
    else:
        with path.open('xb') as stream:
            stream.write(data)


def stage(args):
    project, bundle = Path(args.project).resolve(), Path(args.bundle).resolve()
    config_path = Path(args.config).resolve()
    config = json.loads(config_path.read_text())
    build = json.loads((bundle / 'BOINC_BUILD.json').read_text())
    require(build['application'] == 'fermat_near' and build['boinc_ncpus'] == 1, 'Wrong application')
    require((build['platform'], build['backend']) in {('x86_64-pc-linux-gnu','cpu'),
        ('x86_64-pc-linux-gnu','gpu'), ('arm64-apple-darwin','cpu'), ('arm64-apple-darwin','metal'),
        ('windows_x86_64','cpu'), ('windows_x86_64','gpu')},
        'Unsupported platform/backend')
    for name, digest in build['files'].items():
        require(sha((bundle / name).read_bytes()) == digest, 'Changed package bytes')
    tree = ET.parse(project / 'config.xml')
    section = tree.getroot().find('config')
    require(section is not None and section.findtext('enable_assignment') == '1', 'Host assignment must be enabled')
    registration = ET.parse(project / 'project.xml')
    if not any(a.findtext('name') == 'fermat_near' for a in registration.getroot().findall('app')):
        app = ET.SubElement(registration.getroot(), 'app')
        ET.SubElement(app, 'name').text = 'fermat_near'
        ET.SubElement(app, 'user_friendly_name').text = 'Fermat near misses, powers 4-32'
        registration.write(project / 'project.xml')
        print(command(project, 'php', 'bin/xadd'))
    plan_path = project / 'plan_class_spec.xml'
    plans = ET.parse(plan_path)
    if not any(x.findtext('name') == build['plan_class'] for x in plans.getroot()):
        plan = ET.SubElement(plans.getroot(), 'plan_class')
        pairs = [('name', build['plan_class']), ('avg_ncpus', '1'), ('min_ncpus', '1')]
        if build['backend'] == 'gpu':
            # This first immutable CUDA package is tested on Boole's SM86 GPU.
            pairs += [('gpu_type', 'nvidia'), ('cuda', ''), ('min_cuda_version', '13000'),
                ('min_driver_version', '58000'), ('min_nvidia_compcap', '806'),
                ('max_nvidia_compcap', '806'), ('ngpus', '1'), ('min_gpu_ram_mb', '128'),
                ('gpu_ram_used_mb', '128'), ('cpu_frac', '1')]
            if build['platform']=='windows_x86_64':
                pairs=[(k,v) for k,v in pairs if k!='max_nvidia_compcap']
                pairs=[(k,'12080' if k=='min_cuda_version' else '57261' if k=='min_driver_version'
                        else '705' if k=='min_nvidia_compcap' else '512' if k in ('gpu_ram_used_mb','min_gpu_ram_mb') else v) for k,v in pairs]
        if build['backend'] == 'metal':
            pairs += [('gpu_type', 'apple_gpu'), ('cpu_model_regex', '^Apple M4( Pro| Max)?$'),
                ('min_core_client_version', '80211'), ('ngpus', '1'), ('gpu_ram_used_mb', '512'),
                ('cpu_frac', '1')]
        for key, value in pairs:
            ET.SubElement(plan, key).text = value
        plans.write(plan_path)
    release = build['version']
    require(release in ('1.00','1.01','1.02','1.10','1.11','1.12','1.20','1.21','1.30','1.31','1.40','1.50'), 'Unsupported version')
    number = int(release.replace('.', ''))
    directory = project / 'apps/fermat_near' / release / (build['platform'] + '__' + build['plan_class'])
    version = ET.Element('version')
    ET.SubElement(version, 'is_wrapper')
    ET.SubElement(version, 'api_version').text = '8.3.0'
    for name in build['client_files']:
        physical = 'fermat_near_' + str(number) + '_' + build['backend'] + '_' + name
        immutable(directory / physical, (bundle / name).read_bytes())
        if name in ('wrapper','wrapper.exe'):
            (directory / physical).chmod(0o755)
        node = ET.SubElement(version, 'file')
        ET.SubElement(node, 'physical_name').text = physical
        ET.SubElement(node, 'logical_name').text = name
        ET.SubElement(node, 'copy_file')
        if name in ('wrapper','wrapper.exe'):
            ET.SubElement(node, 'main_program')
    immutable(directory / 'version.xml', ET.tostring(version))
    print(command(project, 'php', 'bin/update_versions', '--noconfirm', '--verbose'))
    versions = sql(config, "SELECT v.id FROM app_version v JOIN app a ON a.id=v.appid JOIN platform p ON p.id=v.platformid WHERE a.name='fermat_near' AND v.version_num=" + str(number) + " AND v.plan_class='" + build['plan_class'] + "' AND p.name='" + build['platform'] + "'")
    require(len(versions) == 1, 'Registered version ambiguous')
    version_id = int(versions[0])
    config['application_versions'][str(version_id)] = dict(backend=build['backend'],
        build_identity=build['build_identity'], version_num=number)
    atomic(config_path, config)
    hook = '#!/bin/sh\nexport FERMAT_NEAR_VALIDATOR_CONFIG=' + shlex.quote(str(config_path)) + '\nexec /usr/bin/python3 ' + shlex.quote(str(ROOT / 'app/boinc_validate.py')) + ' "$@"\n'
    immutable(project / 'bin/fermat_near_validate', hook.encode())
    (project / 'bin/fermat_near_validate').chmod(0o755)
    print(json.dumps(dict(staged=True, app_version_id=version_id, backend=build['backend'])))


def submit(args):
    project, config_path = Path(args.project).resolve(), Path(args.config).resolve()
    manifest_path = Path(args.manifest).resolve()
    manifest, identity = load_manifest(manifest_path)
    config = json.loads(config_path.read_text())
    require(args.host > 0 and str(args.version) in config['application_versions'], 'Explicit registered host/version required')
    name = manifest['unit_id']
    require(name not in config['workunits'], 'Work already admitted')
    trusted = config_path.parent / 'near-trusted' / (name + '.json')
    immutable(trusted, manifest_path.read_bytes())
    config['workunits'][name] = dict(manifest=str(trusted), manifest_sha256=identity,
        allowed_app_version_ids=[args.version], target_host=args.host)
    atomic(config_path, config)
    incoming = '''<input_template><file_info><number>0</number></file_info><workunit>
<file_ref><file_number>0</file_number><open_name>manifest.json</open_name><copy_file/></file_ref>
<rsc_fpops_est>1000000000</rsc_fpops_est><rsc_fpops_bound>10000000000000</rsc_fpops_bound>
<rsc_memory_bound>1073741824</rsc_memory_bound><rsc_disk_bound>2147483648</rsc_disk_bound>
<delay_bound>1800</delay_bound><min_quorum>1</min_quorum><target_nresults>1</target_nresults>
<max_error_results>3</max_error_results><max_total_results>5</max_total_results><max_success_results>3</max_success_results>
</workunit></input_template>'''
    outgoing = '''<output_template><file_info><name><OUTFILE_0/></name><generated_locally/><upload_when_present/>
<max_nbytes>8388608</max_nbytes><url><UPLOAD_URL/></url></file_info><result><file_ref>
<file_name><OUTFILE_0/></file_name><open_name>result.json</open_name><copy_file/></file_ref></result></output_template>'''
    immutable(project / 'templates/near_in_v1', incoming.replace('><', '>\n<').encode())
    immutable(project / 'templates/near_out_v1', outgoing.replace('><', '>\n<').encode())
    staged = config_path.parent / 'near-input' / ('near_' + name + '.json')
    immutable(staged, manifest_path.read_bytes())
    print(command(project, 'bin/stage_file_native', '--copy', str(staged)))
    print(command(project, 'bin/create_work', '--appname', 'fermat_near', '--wu_name', name,
        '--app_version_num', str(config['application_versions'][str(args.version)]['version_num']),
        '--target_host', str(args.host), '--wu_template', 'templates/near_in_v1',
        '--result_template', 'templates/near_out_v1', staged.name))
    print(json.dumps(dict(submitted=name, target_host=args.host, app_version_id=args.version)))


def validator(args):
    project = Path(args.project).resolve()
    directory = project / 'log_fermat_near'
    directory.mkdir(exist_ok=True)
    os.chdir(directory)
    os.execv(str(project / 'bin/script_validator'), ['script_validator', '--app', 'fermat_near',
        '--init_script', 'fermat_near_validate result_id files', '--no_credit', '--sleep_interval', '2', '-d', '3'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required=True)
    parser.add_argument('--config', required=True)
    sub = parser.add_subparsers(dest='operation', required=True)
    s = sub.add_parser('stage'); s.add_argument('bundle'); s.set_defaults(run=stage)
    s = sub.add_parser('submit'); s.add_argument('manifest'); s.add_argument('--host', type=int, required=True); s.add_argument('--version', type=int, required=True); s.set_defaults(run=submit)
    s = sub.add_parser('validate'); s.set_defaults(run=validator)
    args = parser.parse_args(); args.run(args)
