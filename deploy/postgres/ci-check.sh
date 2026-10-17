#!/usr/bin/env bash
# Parse dixpertia.conf and pg_hba.conf with a real PostgreSQL 17 (#158).
#
# Runs in CI inside the postgres:17 image, with this folder mounted on /conf:
#     docker run --rm -v "$PWD/deploy/postgres:/conf:ro" postgres:17 bash /conf/ci-check.sh
# A typo in either file then fails the pull request, not the server's restart.
set -euo pipefail

DATA=/tmp/pgdata
install -d -o postgres -m 0700 "$DATA"
su postgres -c "initdb -D $DATA --auth=trust" >/dev/null
install -o postgres -m 0600 /conf/dixpertia.conf "$DATA/dixpertia.conf"
install -o postgres -m 0600 /conf/pg_hba.conf "$DATA/pg_hba.conf"
echo "include 'dixpertia.conf'" >> "$DATA/postgresql.conf"

failures=0
expect() {  # expect <setting> <value>: postgres -C reads the configuration, failing on any invalid line
    actual=$(su postgres -c "postgres -D $DATA -C $1")
    if [ "$actual" = "$2" ]; then echo "ok    $1 = $actual"; else echo "FAIL  $1 = $actual, expected $2"; failures=$((failures + 1)); fi
}
expect listen_addresses localhost
expect password_encryption scram-sha-256
expect statement_timeout 300000
expect idle_in_transaction_session_timeout 600000
expect log_connections on
expect log_statement ddl
expect log_min_duration_statement 500
expect lc_messages C

# pg_hba.conf is parsed at start: start on the socket only, ask, stop.
su postgres -c "pg_ctl -D $DATA -w -l /tmp/pg.log start -o \"-c listen_addresses=''\"" >/dev/null
hba_errors=$(su postgres -c "psql -X -A -t -c \"SELECT count(*) FROM pg_hba_file_rules WHERE error IS NOT NULL\"")
remote=$(su postgres -c "psql -X -A -t -c \"SELECT count(*) FROM pg_hba_file_rules WHERE type LIKE 'host%' AND address NOT IN ('127.0.0.1', '::1')\"")
su postgres -c "pg_ctl -D $DATA -w stop" >/dev/null
[ "$hba_errors" = "0" ] && echo "ok    pg_hba.conf parses" || { echo "FAIL  pg_hba.conf has $hba_errors error(s)"; failures=$((failures + 1)); }
[ "$remote" = "0" ] && echo "ok    no pg_hba rule open to a remote address" || { echo "FAIL  $remote remote rule(s)"; failures=$((failures + 1)); }

exit "$failures"
