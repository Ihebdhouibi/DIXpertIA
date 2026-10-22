#!/usr/bin/env bash
# Apply the DI Xpertia PostgreSQL configuration to a 17 cluster (#158).
#
# Production is the 17/main cluster on 5432. CLUSTER=staging applies the same
# configuration to the 17/staging cluster on 5433 (#184), plus staging.conf
# (its port and a smaller memory budget). staging.sh creates that cluster.
#
# Installs dixpertia.conf and pg_hba.conf, refuses to restart if PostgreSQL
# reports an error in either, restarts (listen_addresses needs a restart, not
# a reload), and creates the dixpertia database if it does not exist yet.
#
# Run as root on the server, from the repository checkout:
#     bash deploy/postgres/apply.sh
#     CLUSTER=staging bash deploy/postgres/apply.sh
# Safe to run again after any change to the two files.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "Run as root: sudo bash $0" >&2; exit 1; }

HERE="$(cd "$(dirname "$0")" && pwd)"
CLUSTER="${CLUSTER:-main}"
case "$CLUSTER" in
    main) PORT=5432 ;;
    staging) PORT=5433 ;;
    *) echo "CLUSTER must be main or staging, not '$CLUSTER'." >&2; exit 1 ;;
esac
ETC=/etc/postgresql/17/$CLUSTER
SERVICE=postgresql@17-$CLUSTER

[ -d "$ETC" ] || { echo "No 17/$CLUSTER cluster in $ETC. Run install.sh (or staging.sh) first." >&2; exit 1; }

# Keep the packaged pg_hba.conf once, to compare or to roll back.
[ -f "$ETC/pg_hba.conf.orig" ] || cp -p "$ETC/pg_hba.conf" "$ETC/pg_hba.conf.orig"

install -o postgres -g postgres -m 0640 "$HERE/dixpertia.conf" "$ETC/conf.d/dixpertia.conf"
install -o postgres -g postgres -m 0640 "$HERE/pg_hba.conf" "$ETC/pg_hba.conf"
if [ "$CLUSTER" = staging ]; then
    install -o postgres -g postgres -m 0640 "$HERE/staging.conf" "$ETC/conf.d/zz-staging.conf"
fi

# pg_file_settings and pg_hba_file_rules read the files as they are on disk
# now, before any restart: an error here would stop the server from starting.
# config-errors.sql leaves out settings that are merely waiting for that
# restart (max_connections, shared_buffers).
# The port the cluster runs on now: until this restart a new staging cluster
# may still be on the one pg_createcluster gave it.
RUNNING_PORT="$(pg_lsclusters -h | awk -v c="$CLUSTER" '$1 == 17 && $2 == c {print $3}')"
psql_super() { sudo -u postgres psql -p "${RUNNING_PORT:-$PORT}" -X -A -t -v ON_ERROR_STOP=1 "$@"; }
config_errors=$(psql_super < "$HERE/config-errors.sql")
hba_errors=$(psql_super -c "SELECT count(*) FROM pg_hba_file_rules WHERE error IS NOT NULL")
if [ "$config_errors" != "0" ] || [ "$hba_errors" != "0" ]; then
    echo "Configuration errors - not restarting:" >&2
    psql_super -c "SELECT f.sourcefile, f.sourceline, f.name, f.error FROM pg_file_settings f
        LEFT JOIN pg_settings s ON s.name = f.name
        WHERE f.error IS NOT NULL
          AND NOT (s.context = 'postmaster' AND f.error = 'setting could not be applied')" >&2
    psql_super -c "SELECT line_number, error FROM pg_hba_file_rules WHERE error IS NOT NULL" >&2
    exit 1
fi

# Start after Docker at boot (#183): docker_gwbridge, and its 172.18.0.1, only
# exist once Docker is up. Ordering only: PostgreSQL does not require Docker.
install -d /etc/systemd/system/$SERVICE.service.d
cat > /etc/systemd/system/$SERVICE.service.d/after-docker.conf <<'EOF'
[Unit]
After=docker.service
EOF
systemctl daemon-reload

systemctl restart "$SERVICE"
RUNNING_PORT=$PORT

psql_super <<'SQL'
SELECT 'CREATE DATABASE dixpertia' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'dixpertia')\gexec
SQL

echo "Applied to 17/$CLUSTER. Check with: CLUSTER=$CLUSTER bash deploy/postgres/verify.sh"
