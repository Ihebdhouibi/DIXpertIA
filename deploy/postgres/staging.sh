#!/usr/bin/env bash
# The staging PostgreSQL (#184): a second cluster, 17/staging on port 5433,
# next to production's 17/main on 5432.
#
#   sudo bash /opt/dixpertia/deploy/postgres/staging.sh
#
# A separate cluster, not a second database: roles belong to the cluster, and
# the migrations name dixpertia_app and dixpertia_owner. Here staging gets
# roles of its own, with their own passwords, and its own data: a staging
# password never opens production. Safe to run again.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }

if pg_lsclusters -h | awk '$1 == 17 && $2 == "staging" {found = 1} END {exit !found}'; then
    echo "ok    cluster 17/staging exists"
else
    pg_createcluster 17 staging --port 5433 --start >/dev/null
    echo "ok    cluster 17/staging created"
fi

# The same configuration as production, with staging.conf on top.
CLUSTER=staging bash "$HERE/apply.sh"

# The API's staging container reaches it through the Docker bridge, like
# production's (#183): 5433, from the bridge only.
if ip -4 -o addr show docker_gwbridge 2>/dev/null | grep -q ' 172.18.0.1/16 '; then
    ufw allow in on docker_gwbridge from 172.18.0.0/16 to 172.18.0.1 port 5433 proto tcp \
        comment 'PostgreSQL staging, for the staging API container only' >/dev/null
    echo "ok    ufw lets the Docker bridge, and only it, reach 5433"
else
    echo "note  no docker_gwbridge yet: run deploy/dokploy/install.sh, then this again"
fi

echo
echo "Next: the staging roles, printed once (store them, never paste them anywhere):"
echo "  sudo -u postgres python3 /opt/dixpertia/db/setup_roles.py \\"
echo "    --superuser-url \"postgresql:///dixpertia?host=/var/run/postgresql&port=5433\" | grep -o 'dixpertia_[a-z]*:[^@]*'"
