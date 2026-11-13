import json,time
from pathlib import Path
Path('/evidence/boole-server-ready.json').write_text(json.dumps(dict(ready=True,transport='SSH Unix-socket forwarding',HTTP='container loopback only',database='not forwarded'))+'\n')
print('Cabbage private server ready for Boole',flush=True)
while not Path('/pilot/stop-remote-server').exists():time.sleep(.5)
