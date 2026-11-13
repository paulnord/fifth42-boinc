"""Synthetic scheduling only, with a new DB/account; never a physical GPU result."""
import hashlib,json,re,secrets,shutil,socket,subprocess,time,urllib.parse,urllib.request,xml.etree.ElementTree as E
assert socket.gethostname()=="fifth42-mac-plan-regression","Fresh isolated regression namespace required"
from pathlib import Path
out=Path('/evidence')
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
base='http://127.0.0.1:8765/'
email='synthetic-plan-test@example.invalid'
params=urllib.parse.urlencode(dict(email_addr=email,passwd_hash=hashlib.md5((secrets.token_hex(32)+email).encode()).hexdigest(),user_name='Synthetic plan regression'))
account=E.fromstring(opener.open(base+'fifth42/create_account.php?'+params,timeout=30).read())
auth=account.findtext('authenticator')
assert auth is not None,E.tostring(account)

def request(label,cpu,gpu,hostid=0,seq=0):
    root=E.Element('scheduler_request')
    def put(parent,key,value):E.SubElement(parent,key).text=str(value)
    for k,v in dict(authenticator=auth,hostid=hostid,rpc_seqno=seq,platform_name='arm64-apple-darwin',core_client_major_version=8,core_client_minor_version=2,core_client_release=11,client_cap_plan_class=1,work_req_seconds=cpu,cpu_req_secs=cpu,cpu_req_instances=int(cpu>0),estimated_delay=0,resource_share_fraction=1,rrs_fraction=1,prrs_fraction=1,allow_multiple_clients=1).items():put(root,k,v)
    info=E.SubElement(root,'host_info')
    for k,v in dict(p_ncpus=10,p_vendor='Apple',p_model='Apple M4',p_fpops=8e9,p_iops=8e9,m_nbytes=16*1024**3,m_cache=16*1024**2,m_swap=16*1024**3,d_total=500*1024**3,d_free=250*1024**3,os_name='Darwin',os_version='25.6.0',virtualbox_version='',host_cpid='synthetic-m4-plan-regression').items():put(info,k,v)
    stats=E.SubElement(root,'time_stats')
    for k in ('on_frac','active_frac','connected_frac','gpu_active_frac'):put(stats,k,1)
    disk=E.SubElement(root,'disk_usage');put(disk,'d_boinc_used_total',0);put(disk,'d_boinc_used_project',0)
    cp=E.SubElement(E.SubElement(root,'coprocs'),'coproc_apple_gpu')
    for k,v in dict(count=1,model='Apple M4',available_ram=12*1024**3,have_metal=1,have_opencl=1,ncores=10,metal_support=4,peak_flops=80e9,req_secs=gpu,req_instances=int(gpu>0),estimated_delay=0).items():put(cp,k,v)
    cl=E.SubElement(cp,'coproc_opencl');put(cl,'global_mem_size',12*1024**3);put(cl,'opencl_device_version','OpenCL 1.2');put(cl,'device_num',0)
    E.indent(root);payload=E.tostring(root)
    safe=E.fromstring(payload);safe.find('authenticator').text='REDACTED';(out/(label+'-request.xml')).write_bytes(E.tostring(safe))
    response=opener.open(urllib.request.Request(base+'fifth42_cgi/cgi',data=payload,headers={'Content-Type':'text/xml'}),timeout=30).read()
    safe_response=re.sub(rb'([?&]auth=)[^<\s]+',rb'\1REDACTED',response.replace(auth.encode(),b'REDACTED'))
    (out/(label+'-raw-reply.txt')).write_bytes(safe_response)
    # BOINC's permissive XML protocol emits bare '&' in RSS URLs.
    reply=E.fromstring(re.sub(rb'&(?!#?[A-Za-z0-9]+;)',b'&amp;',safe_response))
    # Authenticator is never persisted in the evidence snapshot.
    for node in reply.iter('authenticator'):node.text='REDACTED'
    (out/(label+'-reply.xml')).write_bytes(E.tostring(reply))
    print(label,E.tostring(reply).decode()[-2600:],flush=True)
    return reply

old=request('old-cpu-resource',60,60)
old_av=next((av for av in old.findall('app_version') if av.findtext('version_num')=='140'),None)
assert old_av is not None,'Old alias was not reproduced'
assert old_av.find('coproc') is None,'Old alias unexpectedly assigned a GPU'
assert old.find('result') is not None,'Old control not assigned'
project=Path('/pilot/mac-plan-regression/project')
shutil.copytree('/pilot/input-project/apps/fifth42/1.41',project/'apps/fifth42/1.41')
subprocess.run(['php','bin/update_versions','--noconfirm','--verbose'],cwd=project,check=True)
version=subprocess.check_output(['/pilot/mac-plan-regression/root/usr/bin/mariadb','--no-defaults','--protocol=TCP','-h127.0.0.1','-uroot','--batch','--skip-column-names','fifth42','-e','SELECT id FROM app_version WHERE version_num=141'],text=True).strip()
subprocess.run(['python3','/source/experiments/boinc-20261112/stock/submit.py','--stock','/pilot/mac-plan-regression','--runtime','/pilot/science/runtime','--manifest','/pilot/bundle/controls.json','--name','synthetic_canonical_control','--app-version-id',version,'--build','A','--backend','gpu','--engine','/pilot/bundle/engine-identity'],check=True)
time.sleep(8)
for retry in range(5):
    fixed=request('canonical-gpu-resource-'+str(retry),0,60,int(old.findtext('hostid')),retry+1)
    av=next((av for av in fixed.findall('app_version') if av.findtext('version_num')=='141'),None)
    if av is not None:break
    time.sleep(8)
assert av is not None,'Canonical Apple GPU version not assigned after feeder refresh'
assert av.findtext('coproc/type')=='apple_gpu' and float(av.findtext('coproc/count'))==1,E.tostring(av)
assert fixed.find('result') is not None,'Corrected control not assigned'
report=dict(TEST_ONLY=True,synthetic_scheduler_request=True,physical_M4_execution=False,science_execution=False,server_source='351ad42a102c2bbe70e33f7aa44c23ac6ac3db9c',old_alias_assigned_as_CPU=True,canonical_type='apple_gpu',canonical_count=1,corrected_version_num=141)
(out/'SCHEDULER_REGRESSION.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
