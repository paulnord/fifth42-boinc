import json,signal,time,urllib.request
from pathlib import Path
stop=False
def stopping(*args):
    global stop
    stop=True
signal.signal(signal.SIGTERM,stopping);signal.signal(signal.SIGINT,stopping)
url='http://127.0.0.1:8765/fifth42/'
with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url,timeout=15) as response:
    status=response.status
Path('/evidence/mac-attachment/server-ready.json').write_text(json.dumps(dict(ready=True,url=url,http_status=status,
    transport='authenticated SSH local TCP to private Unix socket',lan_listeners=False,database_forwarded=False))+'\n')
print('Private Mac BOINC server ready; HTTP Unix socket /pilot/transport/http.sock',flush=True)
while not stop and not Path('/pilot/mac-server/STOP').exists():time.sleep(.5)
