#!/bin/bash
# Linux x86_64 Debian13 host; no root, no production services.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
DEST=${1:?Usage: bootstrap.sh NEW_ISOLATED_DIRECTORY}
if test -e "$DEST"; then echo 'Destination must not exist' >&2; exit 2; fi
for tool in curl git dpkg-deb make g++ gcc /usr/bin/python3; do command -v "$tool" >/dev/null; done
mkdir -p "$DEST"; DEST=$(cd "$DEST" && pwd)
python3 "$HERE/fetch_packages.py" "$DEST"
cd "$DEST"
git clone --no-checkout https://github.com/BOINC/boinc.git source
git -C source checkout --detach 351ad42a102c2bbe70e33f7aa44c23ac6ac3db9c
test "$(git -C source rev-parse HEAD)" = 351ad42a102c2bbe70e33f7aa44c23ac6ac3db9c
# Relocate installed autotools' data paths; BOINC source remains unmodified.
sed "s|/usr/share/autoconf|$DEST/root/usr/share/autoconf|g" root/usr/share/autoconf/autom4te.cfg > autom4te.cfg
sed "s|/usr/share/autoconf|$DEST/root/usr/share/autoconf|g" root/usr/bin/autoconf > autoconf-local
sed "s|/usr/share/libtool|$DEST/root/usr/share/libtool|g;s|/usr/share/aclocal|$DEST/root/usr/share/aclocal|g" root/usr/bin/libtoolize > libtoolize-local
chmod +x autoconf-local libtoolize-local
cat > env.sh <<'ENV'
export BOINC_STOCK=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export PATH="$BOINC_STOCK/localbin:$BOINC_STOCK/root/usr/bin:$BOINC_STOCK/root/usr/sbin:$PATH"
export LD_LIBRARY_PATH="$BOINC_STOCK/root/usr/lib/x86_64-linux-gnu:$BOINC_STOCK/root/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PKG_CONFIG_PATH="$BOINC_STOCK/root/usr/lib/x86_64-linux-gnu/pkgconfig:$BOINC_STOCK/root/usr/share/pkgconfig"
export ACLOCAL_PATH="$BOINC_STOCK/root/usr/share/aclocal"
export AUTOM4TE_PERLLIBDIR="$BOINC_STOCK/root/usr/share/autoconf"
export AC_MACRODIR="$BOINC_STOCK/root/usr/share/autoconf"
export AUTOM4TE="$BOINC_STOCK/root/usr/bin/autom4te"
export M4="$BOINC_STOCK/root/usr/bin/m4"
export AUTOMAKE_LIBDIR="$BOINC_STOCK/root/usr/share/automake-1.17"
export PERL5LIB="$BOINC_STOCK/root/usr/share/automake-1.17:$BOINC_STOCK/root/usr/share/autoconf"
export AUTOMAKE="$BOINC_STOCK/root/usr/bin/automake-1.17"
export ACLOCAL="$BOINC_STOCK/root/usr/bin/aclocal-1.17 --system-acdir=$BOINC_STOCK/root/usr/share/aclocal --automake-acdir=$BOINC_STOCK/root/usr/share/aclocal-1.17"
export AUTOM4TE_CFG="$BOINC_STOCK/autom4te.cfg"
export LIBTOOLIZE="$BOINC_STOCK/libtoolize-local"
export AUTOCONF="$BOINC_STOCK/autoconf-local"
export AUTOHEADER="$BOINC_STOCK/root/usr/bin/autoheader"
export PYTHONPATH="$BOINC_STOCK/root/usr/lib/python3/dist-packages${PYTHONPATH:+:$PYTHONPATH}"
export USER=${USER:-agent}
ENV
cat > mysql-config-local <<'MYSQL'
#!/bin/bash
r=$(dirname "$0")/root/usr
case "$1" in
 --libs) echo "-L$r/lib/x86_64-linux-gnu -lmariadb";;
 --cflags) echo "-I$r/include/mariadb";;
 *) "$r/bin/mariadb_config" "$@";;
esac
MYSQL
chmod +x mysql-config-local
source ./env.sh
cd source
./_autosetup > ../bootstrap.log 2>&1
./configure --disable-client --disable-manager --disable-boinczip --enable-server --enable-apps --prefix="$DEST/install" MYSQL_CONFIG="$DEST/mysql-config-local" CC=/usr/bin/gcc CXX=/usr/bin/g++ CPPFLAGS="-I$DEST/root/usr/include -I$DEST/root/usr/include/x86_64-linux-gnu" LDFLAGS="-L$DEST/root/usr/lib/x86_64-linux-gnu" > ../configure.log 2>&1
# Subdirectory builds do not run the top-level BUILT_SOURCES target.
make svn_version.h > ../make-version-header.log 2>&1
# Python packaging via old distutils isn't needed: make_project uses source modules.
for dir in api lib zip sched tools apps vda; do make -C "$dir" -j4 > "../make-$dir.log" 2>&1; done
make -C samples/wrapper -j2 CXX=/usr/bin/g++ CPPFLAGS="-I$DEST/root/usr/include -I$DEST/root/usr/include/x86_64-linux-gnu" LDFLAGS="-L$DEST/root/usr/lib/x86_64-linux-gnu" > ../make-wrapper.log 2>&1
cd ..
mkdir localbin
cat > localbin/php <<'PHP'
#!/bin/bash
r=$(cd "$(dirname "$0")/.." && pwd)
exec "$r/root/usr/bin/php8.4" -c "$r/php.ini" "$@"
PHP
chmod +x localbin/php
printf 'extension_dir="%s/root/usr/lib/php/20240924"\nextension=mysqlnd\nextension=mysqli\nextension=ctype\nextension=xml\nextension=simplexml\nextension=dom\n' "$DEST" > php.ini
root/usr/bin/boinc --version > client-version.txt
source/samples/wrapper/wrapper__x86_64-pc-linux-gnu --version > wrapper-version.txt 2>&1
sha256sum source/samples/wrapper/wrapper__x86_64-pc-linux-gnu root/usr/bin/boinc source/sched/{cgi,feeder,script_validator} > binary-hashes.txt
printf 'Stock build ready: %s\n' "$DEST"
