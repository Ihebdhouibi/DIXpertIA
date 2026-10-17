#!/usr/bin/env bash
# Install PostgreSQL 17 on Ubuntu 24.04 from the official PostgreSQL repository (#158).
#
# 17, not the 16 Ubuntu ships: CI tests against postgres:17, and production
# should run what the tests run. The repository is apt.postgresql.org, set up
# by the script the postgresql-common package provides for exactly this.
#
# Run as root on the server:  bash deploy/postgres/install.sh
# Safe to run again: it installs nothing that is already there.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "Run as root: sudo bash $0" >&2; exit 1; }

apt-get update
apt-get install -y postgresql-common ca-certificates
# Adds apt.postgresql.org and its signing key for this Ubuntu release.
/usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y
apt-get install -y postgresql-17

# The package creates and starts the 17/main cluster.
pg_lsclusters
echo "PostgreSQL 17 installed. Next: bash deploy/postgres/apply.sh"
