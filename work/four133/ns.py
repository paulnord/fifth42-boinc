import subprocess,sys
p=subprocess.check_output(['pgrep','-f','^python3 /recipe/mac-server-wait.py$'],text=True).strip()
command=['nsenter','--target',p,'--user','--mount','--net','--pid','--preserve-credentials','bash','-c','export STOCK=/pilot/mac-server; source "$STOCK/env.sh"; cd "$STOCK/project"; exec "$@"','four133']+sys.argv[1:]
sys.exit(subprocess.call(command))
