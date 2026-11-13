import hashlib,json,subprocess
from pathlib import Path
lock=[]
for deb in sorted(Path('/var/cache/apt/archives').glob('*.deb')):
    def field(k):return subprocess.check_output(['dpkg-deb','-f',str(deb),k],text=True).strip()
    name,version,arch=field('Package'),field('Version'),field('Architecture')
    metadata=subprocess.check_output(['apt-cache','-o','Dir::Cache::pkgcache=','-o','Dir::Cache::srcpkgcache=','show',f'{name}={version}'],text=True)
    fields={}
    for line in metadata.splitlines():
        if ': ' in line and not line.startswith(' '):
            k,v=line.split(': ',1);fields[k]=v
    digest=hashlib.sha256(deb.read_bytes()).hexdigest()
    assert fields['SHA256']==digest,(name,digest,fields.get('SHA256'))
    filename=fields['Filename']
    # Preserve pool identity, signed index origin available in the retained rootfs.
    lock.append(dict(Package=name,Version=version,Architecture=arch,Filename=filename,SHA256=digest,local_archive=str(deb)))
Path('/evidence/base-packages-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
print('Verified signed-index package digests:',len(lock))
