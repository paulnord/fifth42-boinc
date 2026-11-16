"""Register immutable four133 packages and submit explicitly targeted test work.

Run inside a configured BOINC project environment with PHP, database tools and
BOINC server commands available. This does not activate production searches.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
from protocol import atomic, load_manifest, require, sha


def command(project,*args):
    return subprocess.check_output(args,cwd=project,text=True)


def sql(config,query):
    return subprocess.check_output(config['mysql_command']+['--batch','--skip-column-names',
        config['database'],'-e',query],text=True,timeout=30).splitlines()


def immutable(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        require(path.read_bytes()==data,'Existing immutable file differs: '+str(path))
    else:
        with path.open('xb') as f:
            f.write(data)


def stage(args):
    project,bundle=Path(args.project).resolve(),Path(args.bundle).resolve()
    config_path=Path(args.config).resolve()
    config=json.loads(config_path.read_text())
    build=json.loads((bundle/'BOINC_BUILD.json').read_text())
    require(build['application']=='four133' and build['cpu_budget']==1 and build['gpu'] is False,'Wrong application')
    platform=build['platform']
    require(platform in ('x86_64-pc-linux-gnu','arm64-apple-darwin'),'Unsupported platform')
    for name,digest in build['files'].items():
        require(sha((bundle/name).read_bytes())==digest,'Changed package bytes')
    server_config=project/'config.xml'
    settings=ET.parse(server_config)
    section=settings.getroot().find('config')
    require(section is not None,'BOINC project config missing')
    assignment=section.find('enable_assignment')
    if assignment is None or assignment.text != '1':
        immutable(project/'four133-config-before-assignment.xml',server_config.read_bytes())
        if assignment is None:
            assignment=ET.SubElement(section,'enable_assignment')
        assignment.text='1'
        settings.write(server_config)
    registration=project/'project.xml'
    tree=ET.parse(registration)
    if not any(a.findtext('name')=='four133' for a in tree.getroot().findall('app')):
        app=ET.SubElement(tree.getroot(),'app')
        ET.SubElement(app,'name').text='four133'
        ET.SubElement(app,'user_friendly_name').text='Four 133rd powers CPU'
        tree.write(registration)
        print(command(project,'php','bin/xadd'))
    plan_path=project/'plan_class_spec.xml'
    plans=ET.parse(plan_path) if plan_path.exists() else ET.ElementTree(ET.Element('plan_classes'))
    if not any(x.findtext('name')=='four133_cpu_1' for x in plans.getroot()):
        plan=ET.SubElement(plans.getroot(),'plan_class')
        for key,value in [('name','four133_cpu_1'),('avg_ncpus','1'),('min_ncpus','1')]:
            ET.SubElement(plan,key).text=value
        plans.write(plan_path)
    directory=project/'apps/four133/1.00'/(platform+'__four133_cpu_1')
    version=ET.Element('version')
    ET.SubElement(version,'is_wrapper')
    ET.SubElement(version,'api_version').text='8.3.0'
    for name in ('wrapper','runtime.zip','job.xml'):
        physical='four133_100_'+platform+'_'+name
        immutable(directory/physical,(bundle/name).read_bytes())
        if name=='wrapper':
            (directory/physical).chmod(0o755)
        f=ET.SubElement(version,'file')
        ET.SubElement(f,'physical_name').text=physical
        ET.SubElement(f,'logical_name').text=name
        ET.SubElement(f,'copy_file')
        if name=='wrapper':
            ET.SubElement(f,'main_program')
    immutable(directory/'version.xml',ET.tostring(version))
    print(command(project,'php','bin/update_versions','--noconfirm','--verbose'))
    rows=sql(config,"SELECT v.id FROM app_version v JOIN app a ON a.id=v.appid JOIN platform p ON p.id=v.platformid WHERE a.name='four133' AND v.version_num=100 AND v.plan_class='four133_cpu_1' AND p.name='"+platform+"';")
    require(len(rows)==1,'Registered version missing or ambiguous')
    version_id=int(rows[0])
    config.setdefault('application_versions',{})[str(version_id)]=dict(engine_sha256=build['engine_sha256'],platform=platform)
    config.setdefault('workunits',{})
    Path(config['audit_directory']).mkdir(parents=True,exist_ok=True)
    atomic(config_path,config)
    hook='#!/bin/sh\nexport FOUR133_VALIDATOR_CONFIG='+shlex.quote(str(config_path))+'\nexec /usr/bin/python3 '+shlex.quote(str(ROOT/'app/boinc_validate.py'))+' "$@"\n'
    immutable(project/'bin/four133_validate',hook.encode())
    (project/'bin/four133_validate').chmod(0o755)
    print(json.dumps(dict(staged=True,application='four133',app_version_id=version_id,platform=platform)))


def submit(args):
    project=Path(args.project).resolve()
    path=Path(args.manifest).resolve()
    manifest,identity=load_manifest(path)
    require(manifest['purpose']=='TEST_ONLY','This submission helper admits test controls only')
    require(args.host>0 and args.version>0,'Explicit host and app version required')
    config_path=Path(args.config).resolve()
    config=json.loads(config_path.read_text())
    require(str(args.version) in config['application_versions'],'Unknown app version')
    name=manifest['unit_id']
    require(re.fullmatch(r'[A-Za-z0-9_-]+',name) is not None,'Unsafe work name')
    require(name not in config['workunits'],'Work unit already admitted')
    trusted=config_path.parent/'four133-trusted'/(name+'.json')
    immutable(trusted,path.read_bytes())
    config['workunits'][name]=dict(manifest=str(trusted),manifest_sha256=identity,allowed_app_version_ids=[args.version],target_host=args.host)
    atomic(config_path,config)
    input_template='''<input_template><file_info><number>0</number></file_info><workunit>
<file_ref><file_number>0</file_number><open_name>manifest.json</open_name><copy_file/></file_ref>
<rsc_fpops_est>1000000000</rsc_fpops_est><rsc_fpops_bound>10000000000000</rsc_fpops_bound>
<rsc_memory_bound>1073741824</rsc_memory_bound><rsc_disk_bound>536870912</rsc_disk_bound>
<delay_bound>1800</delay_bound><min_quorum>1</min_quorum><target_nresults>1</target_nresults>
<max_error_results>3</max_error_results><max_total_results>5</max_total_results><max_success_results>3</max_success_results>
</workunit></input_template>'''
    output_template='''<output_template><file_info><name><OUTFILE_0/></name><generated_locally/><upload_when_present/>
<max_nbytes>67108864</max_nbytes><url><UPLOAD_URL/></url></file_info><result><file_ref>
<file_name><OUTFILE_0/></file_name><open_name>result.json</open_name><copy_file/></file_ref></result></output_template>'''
    # The stock scheduler's result-template reader requires tags on separate lines.
    immutable(project/'templates/four133_in_v1',input_template.replace('><','>\n<').encode())
    immutable(project/'templates/four133_out_v1',output_template.replace('><','>\n<').encode())
    filename='four133_'+name+'.json'
    # The native tool computes BOINC's download hierarchy using the basename.
    staged=config_path.parent/'four133-input'/filename
    immutable(staged,path.read_bytes())
    print(command(project,'bin/stage_file_native','--copy',str(staged)))
    print(command(project,'bin/create_work','--appname','four133','--wu_name',name,
        '--app_version_num','100','--target_host',str(args.host),
        '--wu_template','templates/four133_in_v1','--result_template','templates/four133_out_v1',filename))
    print(json.dumps(dict(submitted=name,target_host=args.host,purpose='TEST_ONLY',new_scientific_coverage=False)))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--project',required=True)
    parser.add_argument('--config',required=True)
    sub=parser.add_subparsers(dest='operation',required=True)
    s=sub.add_parser('stage');s.add_argument('bundle');s.set_defaults(run=stage)
    s=sub.add_parser('submit');s.add_argument('manifest');s.add_argument('--host',type=int,required=True);s.add_argument('--version',type=int,required=True);s.set_defaults(run=submit)
    args=parser.parse_args();args.run(args)
