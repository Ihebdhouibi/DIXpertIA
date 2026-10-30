#!/usr/bin/env bash
# Install the server checks and alerts (#188), and cap the size of the logs.
#
#   sudo bash /opt/dixpertia/deploy/monitoring/install.sh
#
# The first run writes /etc/dixpertia/monitoring.env from the example and
# stops: put the mailbox password in it (README.md, step 3), then run this
# again. Safe to run again at any time.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE=/etc/dixpertia/monitoring.env

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }

apt-get install -y -q curl openssl >/dev/null
echo "ok    curl and openssl installed"

# --- Settings ------------------------------------------------------------------------
install -d -m 0755 /etc/dixpertia
if [ ! -e "$ENV_FILE" ]; then
    install -m 0600 -o root -g root "$HERE/monitoring.env.example" "$ENV_FILE"
    echo "next  Put the contact@ mailbox password in $ENV_FILE:"
    echo "        sudo nano $ENV_FILE"
    echo "      then run this script again."
    exit 0
fi
chown root:root "$ENV_FILE"
chmod 0600 "$ENV_FILE"
settings="$(cat "$ENV_FILE")"
if grep -q '__CONTACT_MAILBOX_PASSWORD__' <<< "$settings"; then
    echo "next  $ENV_FILE still has the placeholder password: edit it, then run this again."
    exit 1
fi
echo "ok    $ENV_FILE is root's only (0600)"

# --- The checks ----------------------------------------------------------------------
install -m 0750 "$HERE/check.sh" /usr/local/sbin/dixpertia-check
install -m 0644 "$HERE/dixpertia-check.service" /etc/systemd/system/
install -m 0644 "$HERE/dixpertia-check.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now dixpertia-check.timer >/dev/null
echo "ok    checks every 5 minutes"

# --- Log sizes -----------------------------------------------------------------------
# journald: capped in size, and kept 90 days. Provisional until the retention
# decision (#187); the logs hold IP addresses, personal data under the GDPR.
install -d -m 0755 /etc/systemd/journald.conf.d
install -m 0644 "$HERE/journald-dixpertia.conf" /etc/systemd/journald.conf.d/50-dixpertia.conf
systemctl restart systemd-journald
echo "ok    journald capped at 1G and 90 days"

# Docker keeps every container's output, without limit, until the disk is
# full. Cap each container at 5 x 20 MB. Merged into daemon.json, keeping
# whatever Dokploy put there.
python3 - <<'PY'
import json, os
path = "/etc/docker/daemon.json"
conf = {}
if os.path.exists(path):
    with open(path) as f:
        text = f.read().strip()
        conf = json.loads(text) if text else {}
wanted = {"log-driver": "json-file", "log-opts": {"max-size": "20m", "max-file": "5"}}
if all(conf.get(k) == v for k, v in wanted.items()):
    print("ok    docker logs already capped at 5 x 20 MB")
else:
    conf.update(wanted)
    os.makedirs("/etc/docker", exist_ok=True)
    with open(path + ".new", "w") as f:
        json.dump(conf, f, indent=2)
        f.write("\n")
    os.replace(path + ".new", path)
    print("ok    docker logs capped at 5 x 20 MB, from the next reboot (README.md, step 5)")
PY

# --- A first run, and a test mail ------------------------------------------------------
echo
echo "First run:"
/usr/local/sbin/dixpertia-check || true
echo
echo "Test mail to the alert address:"
# Only the mail settings, and a disk "problem" at 0%: one mail, whatever the
# server's state. A state folder of its own, so the real alerts are untouched.
probe_dir="$(mktemp -d)"
grep -E '^(SMTP_|MAIL_)' "$ENV_FILE" > "$probe_dir/env"
CONFIG="$probe_dir/env" STATE_DIR="$probe_dir/state" DISK_PATHS=/ DISK_MAX_PERCENT=0 PG_PORTS=" " \
    CERT_HOSTS=" " HEALTH_URLS=" " CONTAINERS=" " API_CONTAINERS=" " BACKUP_DIR=/nonexistent \
    HOST_LABEL="TEST - install of #188, ignore" \
    /usr/local/sbin/dixpertia-check | tail -1
rm -rf "$probe_dir"
echo "      A mail titled '[DIXpertIA] ... TEST - install of #188' should arrive in a minute."
