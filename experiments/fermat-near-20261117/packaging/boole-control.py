"""Private loopback RPC; never print the authenticator or account XML."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
client = Path('/pilot/client')
if sys.argv[1] == 'inspect':
    slots = []
    for p in (client / 'slots').glob('*'):
        record = dict(slot=p.name)
        for name in ('checkpoint.json', 'result.json'):
            if (p / name).exists():
                record[name] = json.loads((p / name).read_text())
        if (p / 'near.stdout').exists():
            record['stdout'] = (p / 'near.stdout').read_text()
        slots.append(record)
    downloads = [dict(file=p.name, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                 for p in (client / 'projects').glob('*/fermat_near_*') if p.is_file()]
    print(json.dumps(dict(slots=slots, downloads=downloads)))
else:
    key = (client / 'gui_rpc_auth.cfg').read_text().strip()
    result = subprocess.run(['/pilot/runtime/usr/bin/boinccmd', '--host', '127.0.0.1:31427',
        '--passwd', key, *sys.argv[1:]], text=True, capture_output=True)
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    sys.exit(result.returncode)
