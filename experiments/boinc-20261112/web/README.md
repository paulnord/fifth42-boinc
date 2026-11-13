# FifthPower@home private homepage preview

An original PHP/CSS/SVG homepage for the existing private BOINC Mac project.
The working public name is **FifthPower@home**. The repository, BOINC master
URL, database project identity, applications and scientific state are preserved.

The page features the known example `13^5 + 16^5 - 17^5 = 12`, its expanded
arithmetic, a generated fifth-power surface illustration and an accurately
placed +12 marker in a magnified residual window. It explicitly describes
`|a^5+b^5-c^5| <= 100` as a proposed goal within defined bounds, retaining the
current lattice/sieve algorithm. It does not claim existing cap-42 coverage
has cap-100 scope. No cap-100 production packet generation or ledger migration
is performed by this presentation work.

The M4 timing panel uses the six independently accepted benchmark results.
`pilot.json` contains exact measured medians, not invented counters. The plot is
a continuous mathematical illustration, not a map of discovered integer hits
or completed coverage. All graphics, CSS and JavaScript are served locally;
no CDN, web fonts, analytics, image generation or external asset requests are
needed. A copy-URL control has a manual selection fallback.

## Install on the existing private pilot

Inside its existing namespace:

```bash
export HERE=/source/experiments/boinc-20261112
export STOCK=/pilot/mac-server RUNTIME=/pilot/science/runtime
source "$STOCK/env.sh"
php -l "$HERE/web/index.php"
python3 "$HERE/web/deploy.py" --stock "$STOCK"
```

The installer checks this private pilot's configured loopback URL and staged
M4 application marker. It backs up only the previous homepage/assets under
`work/mac-server/homepage-backups/<UTC timestamp>/`, then installs `index.php`
and `fifthpower-assets/`. It does not alter BOINC account/session endpoints,
`schedulers.txt`, configuration, applications, DB, validator or production state.
The homepage includes the original scheduler discovery file so adding or
refreshing the project still finds the same scheduler.

View through the existing SSH tunnel at **http://127.0.0.1:8765/fifth42/**.
Account and server-status links use the existing stock PHP endpoints. The
current server lifetime still ends at 19:32:52 Central on November 13.

## Verification

PHP syntax, JavaScript syntax, SVG XML, measured data and the exact equation
were checked. HTTP checks covered all local routes/assets, stock account
redirects, and unchanged scheduler discovery. Desktop and narrow-layout
screenshots were rendered with a fresh Firefox profile, software rendering,
the private server's network namespace and bounded user units; no host HTTP
listener or LAN port was added. Responsive visual fixes were checked in the
same browser. Screenshot evidence is local under `evidence/homepage/` and in
the final experiment archive. The page remains a private preview.
