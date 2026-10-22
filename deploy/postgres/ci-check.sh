#!/usr/bin/env bash
# Rehearse apply.sh with a real PostgreSQL 17 (#158).
#
# Runs in CI inside the postgres:17 image, with this folder mounted on /conf:
#     docker run --rm -v "$PWD/deploy/postgres:/conf:ro" postgres:17 bash /conf/ci-check.sh
# Same order as on the server: a running cluster with its defaults, our files
# added, the pre-restart check of config-errors.sql, a restart, the values. A
# typo in either file - or a check that would stop apply.sh by mistake - then
# fails the pull request instead of the server.
set -euo pipefail

DATA=/tmp/pgdata
run() { su postgres -c "$1"; }
sql() { su postgres -c "psql -X -A -t -v ON_ERROR_STOP=1" ; }

install -d -o postgres -m 0700 "$DATA"
run "initdb -D $DATA --auth=trust" >/dev/null
# As on Ubuntu: the cluster runs with its defaults before we touch it.
run "pg_ctl -D $DATA -w -l /tmp/pg.log start -o \"-c listen_addresses=''\"" >/dev/null

install -o postgres -m 0600 /conf/dixpertia.conf "$DATA/dixpertia.conf"
install -o postgres -m 0600 /conf/pg_hba.conf "$DATA/pg_hba.conf"
echo "include 'dixpertia.conf'" >> "$DATA/postgresql.conf"

failures=0
check() {  # check <description> <expected> <actual>
    if [ "$2" = "$3" ]; then echo "ok    $1"; else echo "FAIL  $1: expected '$2', got '$3'"; failures=$((failures + 1)); fi
}

# What apply.sh asks before restarting, on the files as they are on disk.
check "apply.sh's pre-restart check finds no error" "0" "$(sql < /conf/config-errors.sql)"
check "pg_hba.conf parses" "0" "$(echo "SELECT count(*) FROM pg_hba_file_rules WHERE error IS NOT NULL" | sql)"
check "no pg_hba rule open beyond this host and the Docker bridge" "0" \
    "$(echo "SELECT count(*) FROM pg_hba_file_rules WHERE type LIKE 'host%' AND address NOT IN ('127.0.0.1', '::1', '172.18.0.0')" | sql)"

# The restart apply.sh does; listen_addresses stays empty here (socket only).
run "pg_ctl -D $DATA -w -l /tmp/pg.log restart -o \"-c listen_addresses=''\"" >/dev/null
for setting in "max_connections=50" "shared_buffers=1GB" "password_encryption=scram-sha-256" \
               "statement_timeout=5min" "idle_in_transaction_session_timeout=10min" \
               "log_connections=on" "log_disconnections=on" "log_statement=ddl" \
               "log_min_duration_statement=500ms" "lc_messages=C"; do
    check "$setting" "${setting#*=}" "$(echo "SHOW ${setting%%=*}" | sql)"
done
# The same query as before the restart: here listen_addresses is overridden
# on the command line, which pg_file_settings reports as not applied.
check "no error once restarted" "0" "$(sql < /conf/config-errors.sql)"
# On the server listen_addresses comes from dixpertia.conf; here it is
# overridden on the command line to keep the container off the network.
check "listen_addresses in dixpertia.conf" "localhost,172.18.0.1" "$(run "postgres -D $DATA -C listen_addresses" 2>/dev/null || true)"

run "pg_ctl -D $DATA -w stop" >/dev/null
exit "$failures"
