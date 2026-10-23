#!/usr/bin/env bash
# Run by CI in the postgres:17 image (#171), with this folder on /conf:
#   docker run --rm -v "$PWD/deploy/backup:/conf:ro" postgres:17 bash /conf/ci-check.sh
#
# backup.sh against a real PostgreSQL 17: a backup is encrypted, the server's
# side cannot read it, the private key can, and pg_restore accepts it; a failed
# night leaves no half-written file; retention keeps 7 daily and 4 weekly.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null
apt-get install -qq -y age >/dev/null

failures=0
check() { if [ "$2" = "$3" ]; then echo "ok    $1"; else echo "FAIL  $1: expected '$2', got '$3'"; failures=$((failures + 1)); fi; }

# A running cluster with a dixpertia database and a row to find again.
DATA=/tmp/pgdata
install -d -o postgres -m 0700 "$DATA"
su postgres -c "initdb -D $DATA --auth=trust" >/dev/null
su postgres -c "pg_ctl -D $DATA -w -l /tmp/pg.log start -o '-c port=5432 -c listen_addresses='" >/dev/null
su postgres -c "psql -q -c 'CREATE DATABASE dixpertia'"
su postgres -c "psql -q -d dixpertia -c \"CREATE TABLE invoices (id int); INSERT INTO invoices VALUES (42);\""

# The server's side, as install.sh lays it out.
groupadd --system dixbackup
install -d -m 0750 -o root -g dixbackup /var/backups/dixpertia
install -d /etc/dixpertia
age-keygen -o /tmp/private.key 2>/dev/null
age-keygen -y /tmp/private.key > /etc/dixpertia/backup-recipient.txt
install -m 0750 /conf/backup.sh /usr/local/sbin/dixpertia-backup

# --- A backup, readable only with the private key ---------------------------------
/usr/local/sbin/dixpertia-backup >/dev/null
dump="$(ls /var/backups/dixpertia/dixpertia-*.dump.age | head -1)"
check "a dump was written" "1" "$(ls /var/backups/dixpertia/dixpertia-*.dump.age | wc -l)"
check "the roles were written" "1" "$(ls /var/backups/dixpertia/dixpertia-*.roles.sql.age | wc -l)"
check "the dump is encrypted, not a plain pg_dump" "age-encryption.org/v1" "$(head -c 21 "$dump")"
check "readable by group dixbackup, not by others" "640 dixbackup" "$(stat -c '%a %G' "$dump")"
age --decrypt -i /tmp/private.key -o /tmp/restore.dump "$dump"
check "pg_restore accepts the decrypted dump" "0" "$(pg_restore --list /tmp/restore.dump >/dev/null 2>&1; echo $?)"
su postgres -c "psql -q -c 'CREATE DATABASE restored'"
pg_restore -U postgres -d restored --no-owner --no-acl /tmp/restore.dump
check "the restored data is the original" "42" "$(su postgres -c "psql -A -t -d restored -c 'SELECT id FROM invoices'")"
check "LAST_SUCCESS written" "1" "$(test -s /var/backups/dixpertia/LAST_SUCCESS && echo 1)"

# --- A failed night leaves no partial file ----------------------------------------------
su postgres -c "pg_ctl -D $DATA -w stop" >/dev/null
before="$(ls /var/backups/dixpertia | wc -l)"
if /usr/local/sbin/dixpertia-backup >/dev/null 2>&1; then failed=no; else failed=yes; fi
check "a backup with the database down fails" "yes" "$failed"
check "and leaves nothing behind" "$before" "$(ls /var/backups/dixpertia | wc -l)"
check "no .part file" "0" "$(ls /var/backups/dixpertia | grep -c '\.part$' || true)"
su postgres -c "pg_ctl -D $DATA -w -l /tmp/pg.log start -o '-c port=5432 -c listen_addresses='" >/dev/null

# --- Retention: the newest 7 daily and 4 weekly ------------------------------------------
for day in $(seq -w 1 12); do
    for ext in dump.age roles.sql.age; do
        : > "/var/backups/dixpertia/dixpertia-daily-202601${day}-0230.$ext"
        : > "/var/backups/dixpertia/dixpertia-weekly-202601${day}-0230.$ext"
    done
done
/usr/local/sbin/dixpertia-backup >/dev/null
check "7 daily dumps kept" "7" "$(ls /var/backups/dixpertia/dixpertia-daily-*.dump.age | wc -l)"
check "7 daily role files kept" "7" "$(ls /var/backups/dixpertia/dixpertia-daily-*.roles.sql.age | wc -l)"
check "4 weekly dumps kept" "4" "$(ls /var/backups/dixpertia/dixpertia-weekly-*.dump.age | wc -l)"
check "the oldest daily went first" "0" "$(ls /var/backups/dixpertia | grep -c 'daily-20260101' || true)"

exit "$failures"
