#!/usr/bin/env bash
# Apply the DI Xpertia PostgreSQL configuration to the 17/main cluster (#158).
#
# Installs dixpertia.conf and pg_hba.conf, refuses to restart if PostgreSQL
# reports an error in either, restarts (listen_addresses needs a restart, not
# a reload), and creates the dixpertia database if it does not exist yet.
#
# Run as root on the server, from the repository checkout:
#     bash deploy/postgres/apply.sh
# Safe to run again after any change to the two files.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "Run as root: sudo bash $0" >&2; exit 1; }

HERE="$(cd "$(dirname "$0")" && pwd)"
ETC=/etc/postgresql/17/main
SERVICE=postgresql@17-main

[ -d "$ETC" ] || { echo "No 17/main cluster in $ETC. Run install.sh first." >&2; exit 1; }

# Keep the packaged pg_hba.conf once, to compare or to roll back.
[ -f "$ETC/pg_hba.conf.orig" ] || cp -p "$ETC/pg_hba.conf" "$ETC/pg_hba.conf.orig"

install -o postgres -g postgres -m 0640 "$HERE/dixpertia.conf" "$ETC/conf.d/dixpertia.conf"
install -o postgres -g postgres -m 0640 "$HERE/pg_hba.conf" "$ETC/pg_hba.conf"

# pg_file_settings and pg_hba_file_rules read the files as they are on disk
# now, before any restart: an error here would stop the server from starting.
psql_super() { sudo -u postgres psql -X -A -t -v ON_ERROR_STOP=1 "$@"; }
config_errors=$(psql_super -c "SELECT count(*) FROM pg_file_settings WHERE error IS NOT NULL")
hba_errors=$(psql_super -c "SELECT count(*) FROM pg_hba_file_rules WHERE error IS NOT NULL")
if [ "$config_errors" != "0" ] || [ "$hba_errors" != "0" ]; then
    echo "Configuration errors - not restarting:" >&2
    psql_super -c "SELECT sourcefile, sourceline, name, error FROM pg_file_settings WHERE error IS NOT NULL" >&2
    psql_super -c "SELECT line_number, error FROM pg_hba_file_rules WHERE error IS NOT NULL" >&2
    exit 1
fi

systemctl restart "$SERVICE"

psql_super <<'SQL'
SELECT 'CREATE DATABASE dixpertia' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'dixpertia')\gexec
SQL

echo "Applied. Check with: bash deploy/postgres/verify.sh"
