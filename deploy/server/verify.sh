#!/usr/bin/env bash
# Check the server against #172. Every line should read "ok".
#
#   sudo bash verify.sh
#
# Read-only. Ends with the server's SSH host key fingerprints, to record in
# the README so anyone connecting for the first time can check them.
set -uo pipefail

ADMIN_USER="${ADMIN_USER:-dixadmin}"
failures=0
ok()   { echo "ok    $1"; }
fail() { echo "FAIL  $1"; failures=$((failures + 1)); }
check() { if eval "$2" >/dev/null 2>&1; then ok "$1"; else fail "$1"; fi; }

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }

# --- Admin user and SSH --------------------------------------------------------
check "user $ADMIN_USER exists" "id $ADMIN_USER"
check "$ADMIN_USER is in sudo" "id -nG $ADMIN_USER | grep -qw sudo"
check "$ADMIN_USER has an authorised key" \
      "grep -qE '^(ssh-ed25519|ecdsa-sha2-nistp256|sk-ssh-ed25519@openssh.com) ' ~$ADMIN_USER/.ssh/authorized_keys"

SSHD="$(sshd -T 2>/dev/null)"
want() { echo "$SSHD" | grep -qix "$1"; }
for setting in "permitrootlogin no" "passwordauthentication no" "kbdinteractiveauthentication no" \
               "pubkeyauthentication yes" "authenticationmethods publickey" "allowusers $ADMIN_USER" \
               "maxauthtries 3" "x11forwarding no"; do
  if want "$setting"; then ok "sshd: $setting"; else fail "sshd: $setting (got: $(echo "$SSHD" | grep -i "^${setting%% *} " || echo unset))"; fi
done
check "root password locked" "passwd -S root | awk '{exit !(\$2 == \"L\")}'"

# --- Firewall --------------------------------------------------------------------
check "ufw is active" "ufw status | grep -q '^Status: active'"
OPEN="$(ufw status | awk '/ALLOW|LIMIT/ && !/\(v6\)/ {print $1}' | sort -u | tr '\n' ' ')"
if [ "$OPEN" = "22/tcp 443/tcp 80/tcp " ]; then ok "ufw opens only 22, 80, 443"; else fail "ufw opens: $OPEN"; fi
check "incoming denied by default" "ufw status verbose | grep -q 'deny (incoming)'"
# Docker bypasses ufw: what actually listens on a public address is what counts.
PUBLIC="$(ss -tlnH | awk '{print $4}' | grep -vE '^(127\.|\[::1\]|::1)' | sed -E 's/.*:([0-9]+)$/\1/' | sort -nu | tr '\n' ' ')"
case " $PUBLIC" in
  *" 5432 "*) fail "PostgreSQL listens on a public address" ;;
  *) ok "PostgreSQL not on a public address" ;;
esac
echo "      listening on public addresses: ${PUBLIC:-none} (expected: 22, and 80 443 once Traefik runs)"

# --- fail2ban, updates, swap, time -----------------------------------------------
check "fail2ban guards SSH" "fail2ban-client status sshd"
check "unattended upgrades enabled" "systemctl is-enabled unattended-upgrades && grep -q 'Unattended-Upgrade \"1\"' /etc/apt/apt.conf.d/20auto-upgrades"
check "swap present" "swapon --show=NAME --noheadings | grep -q ."
check "timezone Africa/Tunis" "timedatectl show -p Timezone --value | grep -qx Africa/Tunis"
check "clock synchronised" "timedatectl show -p NTPSynchronized --value | grep -qx yes"
if [ -f /var/run/reboot-required ]; then
  echo "note  a reboot is due to finish an update: sudo reboot (at a quiet time)"
fi

echo
echo "SSH host key fingerprints (record them in deploy/server/README.md):"
for key in /etc/ssh/ssh_host_*_key.pub; do ssh-keygen -lf "$key"; done

echo
if [ "$failures" -eq 0 ]; then echo "All checks passed."; else echo "$failures check(s) failed."; exit 1; fi
