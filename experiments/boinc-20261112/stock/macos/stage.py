"""Stage a hash-checked CPU package as an immutable native Mac app version."""
import argparse,hashlib,json,re,shutil,xml.etree.ElementTree as E,zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--stock',required=True);p.add_argument('--bundle',required=True);p.add_argument('--version',default='1.30');p.add_argument('--label',default='MacCPU130');a=p.parse_args()
if not re.fullmatch(r'[A-Za-z0-9_-]+',a.label) or not re.fullmatch(r'[0-9]+\.[0-9]{2}',a.version):raise ValueError('Immutable label/version required')
stock=Path(a.stock).resolve();bundle=Path(a.bundle).resolve();metadata=json.loads((bundle/'BOINC_BUILD.json').read_text())
assert metadata['TEST_ONLY'] is True and metadata['new_scientific_coverage'] is False
assert metadata['boinc_platform']=='arm64-apple-darwin' and metadata['backend'] in ('cpu','gpu') and metadata['build']=='A'
for name,digest in metadata['files'].items():
    assert Path(name).name==name and hashlib.sha256((bundle/name).read_bytes()).hexdigest()==digest,name
with zipfile.ZipFile(bundle/'runtime.zip') as z:
    engine=metadata.get('engine_name','scaling_gpu' if metadata['backend']=='gpu' else 'scaling_cpu')
    assert hashlib.sha256(z.read('bin/'+engine)).hexdigest()==metadata['engine_sha256']
    assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist())
platform=metadata['boinc_platform']
if metadata['backend']=='gpu':
    assert metadata['plan_class']=='fifth42_apple_gpu_metal_m4'
    platform+='__'+metadata['plan_class']
    spec=stock/'project/plan_class_spec.xml'
    candidate=E.parse(Path(__file__).with_name('fifth42_apple_gpu_metal.xml')).getroot().find('plan_class')
    tree=E.parse(spec) if spec.exists() else E.ElementTree(E.Element('plan_classes'))
    existing=next((p for p in tree.getroot().findall('plan_class') if p.findtext('name')==metadata['plan_class']),None)
    if existing is not None:assert E.tostring(existing).strip()==E.tostring(candidate).strip(),'Immutable plan class differs'
    else:tree.getroot().append(candidate);E.indent(tree);tree.write(spec,encoding='unicode')
directory=stock/'project/apps/fifth42'/a.version/platform;directory.mkdir(parents=True,exist_ok=False)
version=E.Element('version');E.SubElement(version,'is_wrapper');E.SubElement(version,'api_version').text='8.3.0'
for logical in ('wrapper','runtime.zip','job.xml'):
    physical='fifth42_'+a.label+'_'+logical;shutil.copy2(bundle/logical,directory/physical)
    (directory/physical).chmod(0o755 if logical=='wrapper' else 0o644)
    f=E.SubElement(version,'file');E.SubElement(f,'physical_name').text=physical;E.SubElement(f,'logical_name').text=logical;E.SubElement(f,'copy_file')
    if logical=='wrapper':E.SubElement(f,'main_program')
E.ElementTree(version).write(directory/'version.xml',encoding='unicode')
(stock/('MAC_APPLICATION_'+a.label+'.json')).write_text(json.dumps(dict(metadata,version=a.version,label=a.label),indent=2)+'\n')
# The bundled runtime alone is ~98 MiB; preserve a margin for zip extraction,
# wrapper/checkpoints and bytecode in this new Mac-only test project.
template=stock/'project/templates/fifth42_in';text=template.read_text()
text,count=re.subn(r'<rsc_disk_bound>[^<]+</rsc_disk_bound>','<rsc_disk_bound>536870912</rsc_disk_bound>',text)
assert count==1;template.write_text(text)
print(json.dumps(dict(platform=metadata['boinc_platform'],version=a.version,engine_sha256=metadata['engine_sha256'],staged=str(directory))))
