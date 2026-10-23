#!/usr/bin/env bash
# Nightly backup of the production database (#171), run by the
# dixpertia-backup systemd timer. By hand:  sudo /usr/local/sbin/dixpertia-backup
#
# pg_dump of `dixpertia` (17/main), plus the cluster's roles, each piped
# straight into `age` with the RECIPIENT's public key: what lands on disk is
# encrypted, and this server cannot decrypt it. Only the private key, kept off
# the server, can. A dump is always consistent, unlike a disk snapshot taken
# mid-write.
#
# Kept here: the last 7 daily and the last 4 weekly (Sunday) backups. The copy
# that matters is the off-server one: the admin's machine pulls this folder
# (see README.md).
set -euo pipefail

DIR=/var/backups/dixpertia
RECIPIENT_FILE=/etc/dixpertia/backup-recipient.txt
DAILY_KEEP=7
WEEKLY_KEEP=4

[ "$(id -u)" -eq 0 ] || { echo "Run as root." >&2; exit 1; }
[ -s "$RECIPIENT_FILE" ] || { echo "No public key in $RECIPIENT_FILE: run install.sh with it." >&2; exit 1; }

stamp="$(date +%Y%m%d-%H%M)"
kind=daily
[ "$(date +%u)" = 7 ] && kind=weekly
umask 027

# Written under a temporary name and renamed only when complete: a failed
# night never leaves a truncated file that looks like a backup.
dump="$DIR/dixpertia-$kind-$stamp.dump.age"
roles="$DIR/dixpertia-$kind-$stamp.roles.sql.age"
trap 'rm -f "$dump.part" "$roles.part"' EXIT

runuser -u postgres -- pg_dump -p 5432 --format=custom --compress=6 dixpertia \
    | age --encrypt --recipients-file "$RECIPIENT_FILE" > "$dump.part"
# Roles and their password hashes: restoring onto a new server needs them.
runuser -u postgres -- pg_dumpall -p 5432 --globals-only \
    | age --encrypt --recipients-file "$RECIPIENT_FILE" > "$roles.part"
mv "$dump.part" "$dump"
mv "$roles.part" "$roles"
chgrp dixbackup "$dump" "$roles"
chmod 0640 "$dump" "$roles"

# Retention: the newest N of each kind, by name (the names sort by date).
for k in daily:$DAILY_KEEP weekly:$WEEKLY_KEEP; do
    name=${k%%:*} keep=${k##*:}
    for ext in dump.age roles.sql.age; do
        find "$DIR" -maxdepth 1 -name "dixpertia-$name-*.$ext" -printf '%f\n' | sort -r \
            | tail -n +"$((keep + 1))" | while read -r old; do rm -f "$DIR/$old"; done
    done
done

date -Iseconds > "$DIR/LAST_SUCCESS"
chgrp dixbackup "$DIR/LAST_SUCCESS"
echo "backup ok: $(basename "$dump") ($(du -h "$dump" | cut -f1))"
