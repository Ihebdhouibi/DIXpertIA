#!/usr/bin/env bash
# Step 3 (#172): SSH with keys only, and never as root.
#
# Run it signed in AS THE ADMIN USER, WITH YOUR KEY - not as root:
#   sudo bash 03-ssh-lockdown.sh
#
# That is the safeguard against locking everyone out: the script refuses to run
# unless the session it runs in proves that key login as the admin works. It
# also checks the new configuration with `sshd -t` before applying it, and
# keeps existing sessions open. Test a NEW login before closing this one.
set -euo pipefail

ADMIN_USER="${ADMIN_USER:-dixadmin}"
CONF=/etc/ssh/sshd_config.d/01-dixpertia.conf
SOURCE_CONF="$(dirname "$0")/sshd-dixpertia.conf"

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }
[ -f "$SOURCE_CONF" ] || { echo "sshd-dixpertia.conf must sit next to this script."; exit 1; }

# --- The safeguards -------------------------------------------------------------
if [ "${SUDO_USER:-}" != "$ADMIN_USER" ]; then
  echo "Refused: run this as $ADMIN_USER (signed in with your key) through sudo, not as root."
  echo "If you cannot sign in as $ADMIN_USER with your key yet, do NOT lock SSH down."
  exit 1
fi
HOME_DIR="$(getent passwd "$ADMIN_USER" | cut -d: -f6)"
if ! grep -qE '^(ssh-ed25519|ecdsa-sha2-nistp256|sk-ssh-ed25519@openssh.com) ' "$HOME_DIR/.ssh/authorized_keys" 2>/dev/null; then
  echo "Refused: $ADMIN_USER has no authorised key."; exit 1
fi
# A key login by the admin, recently: sshd logs the method. (Not $SSH_CONNECTION:
# sudo clears the environment, so the script never sees it.) Searched by the
# program that logs it, not by unit: once a login is accepted, pam_systemd
# moves that sshd process into the user's session, so `journalctl -u ssh`
# does not show the line. sshd-session is its name from OpenSSH 9.8.
if ! { journalctl -t sshd -t sshd-session --since "12 hours ago" --no-pager -q 2>/dev/null
       cat /var/log/auth.log 2>/dev/null; } \
     | grep -q "Accepted publickey for $ADMIN_USER "; then
  echo "Refused: no key login by $ADMIN_USER in the last 12 hours. Sign in with your key, then run this again."
  exit 1
fi
echo "ok    $ADMIN_USER signs in with a key; safe to lock SSH down"

# --- Apply ------------------------------------------------------------------------
# "01-": sshd keeps the FIRST value it reads, and Ubuntu cloud images ship
# 50-cloud-init.conf with PasswordAuthentication yes. Ours must come first.
sed "s/__ADMIN_USER__/$ADMIN_USER/" "$SOURCE_CONF" > "$CONF.new"
chmod 644 "$CONF.new"
mv "$CONF.new" "$CONF"
if ! sshd -t; then
  rm -f "$CONF"
  echo "Refused: sshd rejected the configuration; it was removed and nothing changed."
  exit 1
fi
systemctl reload ssh
echo "ok    SSH: keys only, no root, only $ADMIN_USER"

# Root's password is no longer needed for anything: lock it.
passwd -l root >/dev/null
echo "ok    root password locked (sudo from $ADMIN_USER still works)"

echo
echo "NOW, from your laptop, in a NEW terminal - keep this session open until it works:"
echo "  ssh -i <your private key> $ADMIN_USER@<server-ip>     # must work"
echo "  ssh root@<server-ip>                                  # must be refused"
echo "If the new login fails, fix it from THIS session:  sudo rm $CONF && sudo systemctl reload ssh"
