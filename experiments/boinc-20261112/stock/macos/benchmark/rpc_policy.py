"""Temporarily request 20-second RPCs in this private project; always restore."""
import json,signal,time,xml.etree.ElementTree as E
from pathlib import Path
config=Path('/pilot/mac-server/project/config.xml');e=Path('/evidence/mac-benchmark')
stop=False
def stopping(*args):
 global stop
 stop=True
signal.signal(signal.SIGTERM,stopping);signal.signal(signal.SIGINT,stopping)
t=E.parse(config);c=t.getroot().find('config');assert c is not None
assert c.find('next_rpc_delay') is None,'Do not override an existing RPC policy'
def write(tree):
 E.indent(tree);tmp=config.with_suffix('.benchmark-tmp');tree.write(tmp,encoding='unicode');tmp.replace(config)
E.SubElement(c,'next_rpc_delay').text='20';write(t)
(e/'RPC_POLICY.json').write_text(json.dumps(dict(temporary_next_rpc_delay_seconds=20,restored=False))+'\n')
try:
 deadline=time.monotonic()+1800
 while not stop and time.monotonic()<deadline:
  if json.loads((e/'STATUS.json').read_text())['state'] in ('complete','failed'):break
  time.sleep(2)
finally:
 t=E.parse(config);c=t.getroot().find('config');node=c.find('next_rpc_delay')
 assert node is not None and node.text=='20','RPC policy changed externally; inspect before removal'
 c.remove(node);write(t)
 (e/'RPC_POLICY.json').write_text(json.dumps(dict(temporary_next_rpc_delay_seconds=20,restored=True))+'\n')
