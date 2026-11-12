#!/usr/bin/env python3
"""Rootless Apache config, loopback only, stock BOINC CGI and web pages."""
from pathlib import Path
import os,pwd,sys
p=Path(sys.argv[1]).resolve();r=p/'root/usr';user=pwd.getpwuid(os.getuid()).pw_name
mods=['mpm_prefork','authz_core','authz_host','dir','mime','alias','env','cgi']
s=f'ServerRoot "{p}"\nListen 127.0.0.1:8765\nServerName localhost\nPidFile "{p}/httpd.pid"\nErrorLog "{p}/httpd-error.log"\nLogLevel info\n'
for m in mods:s+=f'LoadModule {m}_module "{r}/lib/apache2/modules/mod_{m}.so"\n'
s+=f'LoadModule php_module "{r}/lib/apache2/modules/libphp8.4.so"\nPHPIniDir "{p}"\nTypesConfig /etc/mime.types\nDirectoryIndex index.html index.php\nUser {user}\n'
s+=f'<Directory "{p}/project">\nRequire local\nOptions FollowSymLinks\nAllowOverride None\n</Directory>\n'
s+='AddType application/x-httpd-php .php\n'
s+=f'PassEnv LD_LIBRARY_PATH\nInclude "{p}/project/fifth42.httpd.conf"\n'
(p/'httpd.conf').write_text(s)
