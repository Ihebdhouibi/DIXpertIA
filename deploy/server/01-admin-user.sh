#!/usr/bin/env bash
# Step 1 (#172): an admin user with sudo, who signs in with an SSH key.
#
# Run as root, with the PUBLIC key file you copied to the server:
#   bash 01-admin-user.sh /root/admin_key.pub
#
# Safe to run again: an existing user is kept, and a key already present is
# not added twice. The user gets no password for SSH (keys only, step 3), but
# sudo asks for one, so set it when prompted at the end.
set -euo pipefail

ADMIN_USER="${ADMIN_USER:-dixadmin}"
KEY_FILE="${1:-}"

[ "$(id -u)" -eq 0 ] || { echo "Run as root."; exit 1; }
[ -n "$KEY_FILE" ] && [ -f "$KEY_FILE" ] || { echo "Usage: bash $0 /path/to/admin_key.pub"; exit 1; }

# A public key, one line, of a type we accept. A private key pasted by mistake
# is refused rather than installed.
if grep -q "PRIVATE KEY" "$KEY_FILE"; then
  echo "That is a PRIVATE key. Copy the .pub file, never the private one."; exit 1
fi
KEY="$(grep -E '^(ssh-ed25519|ecdsa-sha2-nistp256|sk-ssh-ed25519@openssh.com) ' "$KEY_FILE" | head -1 || true)"
[ -n "$KEY" ] || { echo "No ed25519 or ecdsa public key found in $KEY_FILE."; exit 1; }

if id "$ADMIN_USER" >/dev/null 2>&1; then
  echo "ok    user $ADMIN_USER exists"
else
  adduser --disabled-password --gecos "" "$ADMIN_USER"
  echo "ok    user $ADMIN_USER created"
fi
usermod -aG sudo "$ADMIN_USER"

HOME_DIR="$(getent passwd "$ADMIN_USER" | cut -d: -f6)"
install -d -m 700 -o "$ADMIN_USER" -g "$ADMIN_USER" "$HOME_DIR/.ssh"
AUTH="$HOME_DIR/.ssh/authorized_keys"
touch "$AUTH"
if grep -qxF "$KEY" "$AUTH"; then
  echo "ok    key already authorised"
else
  echo "$KEY" >> "$AUTH"
  echo "ok    key authorised"
fi
chown "$ADMIN_USER:$ADMIN_USER" "$AUTH"
chmod 600 "$AUTH"

# Remove the copied key file: it is not secret, but it has no business lying around.
rm -f "$KEY_FILE"

if passwd -S "$ADMIN_USER" | awk '{exit !($2 == "P")}'; then
  echo "ok    $ADMIN_USER has a sudo password"
else
  echo
  echo "Set the password sudo will ask $ADMIN_USER for (a long one, kept in your password manager):"
  passwd "$ADMIN_USER"
fi

echo
echo "Next, from your laptop, in a NEW terminal - keep this root session open:"
echo "  ssh -i <your private key> $ADMIN_USER@<server-ip>"
echo "  sudo -v      # must accept the password you just set"
