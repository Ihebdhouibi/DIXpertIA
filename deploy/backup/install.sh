#!/usr/bin/env bash
# Install the nightly backup (#171) and the read-only account the admin's
# machine pulls it with.
#
#   sudo bash /opt/dixpertia/deploy/backup/install.sh '<age public key>' '<backup SSH public key>'
#
# Both arguments are PUBLIC keys, made on the admin's machine (README.md, step
# 1). The private halves never come to this server. Safe to run again.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
AGE_RECIPIENT="${1:-}"
PULL_KEY="${2:-}"

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }
case "$AGE_RECIPIENT" in
    age1*) ;;
    *) echo "First argument: the age PUBLIC key, starting with age1 (never the AGE-SECRET-KEY)."; exit 1 ;;
esac
case "$PULL_KEY" in
    ssh-ed25519\ *) ;;
    *) echo "Second argument: the backup SSH PUBLIC key, starting with ssh-ed25519."; exit 1 ;;
esac

apt-get install -y -q age rsync >/dev/null
echo "ok    age installed"

# --- The read-only account ------------------------------------------------------
# No shell, no password, one key, and that key can only run sftp-server
# read-only, starting in the backup folder: it can download, nothing else.
if ! id dixbackup >/dev/null 2>&1; then
    adduser --system --group --home /var/lib/dixbackup --shell /usr/sbin/nologin dixbackup >/dev/null
fi
install -d -m 0750 -o dixbackup -g dixbackup /var/lib/dixbackup/.ssh
printf 'restrict,command="/usr/lib/openssh/sftp-server -R -d /var/backups/dixpertia" %s\n' "$PULL_KEY" \
    > /var/lib/dixbackup/.ssh/authorized_keys
chown dixbackup:dixbackup /var/lib/dixbackup/.ssh/authorized_keys
chmod 0600 /var/lib/dixbackup/.ssh/authorized_keys
echo "ok    dixbackup can only download the backups"

# SSH admits only the users listed in AllowUsers (#172): add dixbackup.
CONF=/etc/ssh/sshd_config.d/01-dixpertia.conf
if [ -f "$CONF" ] && ! grep -qE '^AllowUsers .*\bdixbackup\b' "$CONF"; then
    sed -i -E 's/^(AllowUsers .*)$/\1 dixbackup/' "$CONF"
    sshd -t || { echo "sshd rejected the change; check $CONF"; exit 1; }
    systemctl reload ssh
fi
echo "ok    SSH admits dixbackup"

# --- The backup itself --------------------------------------------------------------
install -d -m 0750 -o root -g dixbackup /var/backups/dixpertia
install -d -m 0755 /etc/dixpertia
echo "$AGE_RECIPIENT" > /etc/dixpertia/backup-recipient.txt
chmod 0644 /etc/dixpertia/backup-recipient.txt
install -m 0750 "$HERE/backup.sh" /usr/local/sbin/dixpertia-backup
install -m 0644 "$HERE/dixpertia-backup.service" /etc/systemd/system/
install -m 0644 "$HERE/dixpertia-backup.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now dixpertia-backup.timer >/dev/null
echo "ok    nightly backup at 02:30"

# A first backup now, so there is something to pull and to test.
/usr/local/sbin/dixpertia-backup
