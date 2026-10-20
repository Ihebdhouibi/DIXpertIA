#!/usr/bin/env bash
# Install Dokploy (#183) at a pinned, checksummed release, then close what its
# installer leaves open.
#
#   sudo bash /opt/dixpertia/deploy/dokploy/install.sh
#
# Refuses to run on a server that is not hardened yet (#172): Dokploy controls
# Docker, which is root on this machine.
set -euo pipefail

DOKPLOY_VERSION=v0.30.8
# sha256 of that release's install.sh, as read and reviewed for #183. A
# different file is refused: never pipe an unread script into a root shell.
INSTALLER_SHA256=534679c2f2730d369302df4e938d4dfaec177731b6d91cb87d8ecc7ca7cbc9bd
HERE="$(cd "$(dirname "$0")" && pwd)"

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }

# --- The server is hardened first (#172) ------------------------------------------
ufw status | grep -q '^Status: active' || { echo "Refused: the firewall is off. Run deploy/server first."; exit 1; }
sshd -T | grep -qix 'passwordauthentication no' \
  || { echo "Refused: SSH still accepts passwords. Run deploy/server/03-ssh-lockdown.sh first."; exit 1; }
sshd -T | grep -qix 'permitrootlogin no' \
  || { echo "Refused: SSH still accepts root. Run deploy/server/03-ssh-lockdown.sh first."; exit 1; }
echo "ok    server hardened"

# --- The installer, pinned and verified ---------------------------------------------
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
curl -fsSL -o "$work/install.sh" \
  "https://github.com/Dokploy/dokploy/releases/download/$DOKPLOY_VERSION/install.sh"
echo "$INSTALLER_SHA256  $work/install.sh" | sha256sum -c --quiet - \
  || { echo "Refused: the installer does not match the reviewed one."; exit 1; }
echo "ok    installer $DOKPLOY_VERSION verified"

# Swarm needs an address to advertise; this VPS has only its public one, which
# the installer cannot find by itself. The swarm ports it opens (2377, 7946,
# 4789) are host sockets, so ufw keeps them closed to the internet.
ADVERTISE_ADDR="$(ip -4 route get 1.1.1.1 | awk '{for (i = 1; i < NF; i++) if ($i == "src") print $(i + 1)}')"
export ADVERTISE_ADDR DOKPLOY_VERSION
sh "$work/install.sh"

# --- Close what the installer leaves open ---------------------------------------------
# It makes /etc/dokploy world-writable; Traefik's routes and certificates live
# there. Dokploy runs as root, so it needs nothing more than root's access.
chown root:root /etc/dokploy
chmod 0750 /etc/dokploy
echo "ok    /etc/dokploy no longer world-writable"

# --- PostgreSQL for the API's container ------------------------------------------------
gateway="$(ip -4 -o addr show docker_gwbridge | awk '{print $4}')"
if [ "$gateway" != "172.18.0.1/16" ]; then
  echo "STOP: docker_gwbridge is '$gateway', not 172.18.0.1/16. listen_addresses in"
  echo "      deploy/postgres/dixpertia.conf and the bridge rule in pg_hba.conf must"
  echo "      name that address before the API can reach PostgreSQL. Say so in #183."
  exit 1
fi
ufw allow in on docker_gwbridge from 172.18.0.0/16 to 172.18.0.1 port 5432 proto tcp \
  comment 'PostgreSQL, for the API container only' >/dev/null
echo "ok    ufw lets the Docker bridge, and only it, reach PostgreSQL"
# Now that the bridge exists, PostgreSQL can bind 172.18.0.1 (and starts after
# Docker from the next boot on).
bash "$HERE/../postgres/apply.sh"

echo
echo "Dokploy is installed. Its dashboard is still on port 3000 of the public"
echo "address: whoever opens it first creates the admin account. Do step 2 of"
echo "deploy/dokploy/README.md NOW, through the SSH tunnel."
