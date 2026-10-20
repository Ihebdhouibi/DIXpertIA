#!/usr/bin/env bash
# Check that the running PostgreSQL is configured as #158 decided.
#
# Run as root on the server:  bash deploy/postgres/verify.sh
# Prints one line per check and exits non-zero if any fails.
set -uo pipefail

[ "$(id -u)" -eq 0 ] || { echo "Run as root: sudo bash $0" >&2; exit 1; }

failures=0
check() {  # check <description> <expected> <actual>
    if [ "$2" = "$3" ]; then
        echo "ok    $1"
    else
        echo "FAIL  $1: expected '$2', got '$3'"
        failures=$((failures + 1))
    fi
}
show() { sudo -u postgres psql -X -A -t -c "SHOW $1" 2>/dev/null; }

check "server version 17" "17" "$(show server_version | cut -d. -f1)"

# Listening on the loopback addresses and the Docker bridge (#183), never on
# a public one.
public=$(ss -tlnH 'sport = :5432' | awk '{print $4}' \
    | grep -v -E '^(127\.0\.0\.1|\[::1\]|172\.18\.0\.1):5432$' | tr '\n' ' ')
check "listening on localhost and the Docker bridge only" "" "$public"

for setting in "listen_addresses=localhost,172.18.0.1" "password_encryption=scram-sha-256" \
               "statement_timeout=5min" "idle_in_transaction_session_timeout=10min" \
               "log_connections=on" "log_disconnections=on" "log_statement=ddl" \
               "log_min_duration_statement=500ms" "lc_messages=C"; do
    check "$setting" "${setting#*=}" "$(show "${setting%%=*}")"
done

check "no error in the configuration files" "0" \
    "$(sudo -u postgres psql -X -A -t -c "SELECT count(*) FROM pg_file_settings WHERE error IS NOT NULL")"
check "no error in pg_hba.conf" "0" \
    "$(sudo -u postgres psql -X -A -t -c "SELECT count(*) FROM pg_hba_file_rules WHERE error IS NOT NULL")"
check "no pg_hba rule open beyond this host and the Docker bridge" "0" \
    "$(sudo -u postgres psql -X -A -t -c "SELECT count(*) FROM pg_hba_file_rules
        WHERE type LIKE 'host%' AND address NOT IN ('127.0.0.1', '::1', '172.18.0.0')")"
check "the dixpertia database exists" "1" \
    "$(sudo -u postgres psql -X -A -t -c "SELECT count(*) FROM pg_database WHERE datname = 'dixpertia'")"

if [ "$failures" -eq 0 ]; then
    echo "All checks passed."
else
    echo "$failures check(s) failed."
    exit 1
fi
