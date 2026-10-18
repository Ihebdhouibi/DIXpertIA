#!/usr/bin/env bash
# Step 2 (#172): updates, automatic security updates, swap, firewall, fail2ban.
#
#   sudo bash 02-baseline.sh
#
# Safe to run again. Nothing here can lock you out: the firewall allows SSH
# before it is switched on.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }
export DEBIAN_FRONTEND=noninteractive

# --- Packages ------------------------------------------------------------------
apt-get update -q
apt-get -q -y upgrade
apt-get -q -y install unattended-upgrades fail2ban ufw
echo "ok    packages up to date"

# --- Time: logs and invoices in Tunisian time -----------------------------------
timedatectl set-timezone Africa/Tunis
timedatectl set-ntp true
echo "ok    timezone Africa/Tunis, clock synchronised"

# --- Automatic security updates ----------------------------------------------------
# Security updates only (Ubuntu's default origins). No automatic reboot: a
# kernel update waits for a reboot we choose; verify.sh says when one is due.
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
systemctl enable --now unattended-upgrades >/dev/null
echo "ok    unattended security upgrades on"

# --- Swap: 2 GB ------------------------------------------------------------------
# There was none, so a memory spike (an image build next to the running apps,
# #184) would have the kernel kill processes instead of slowing down.
if swapon --show=NAME --noheadings | grep -q .; then
  echo "ok    swap already present"
else
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile >/dev/null
  swapon /swapfile
  grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo "ok    2 GB swap created"
fi
# Use swap as a last resort, not as working memory.
echo 'vm.swappiness=10' > /etc/sysctl.d/90-dixpertia-swap.conf
sysctl -q -p /etc/sysctl.d/90-dixpertia-swap.conf

# --- Firewall: SSH, HTTP, HTTPS, nothing else -------------------------------------
# PostgreSQL (5432) stays closed: it listens on localhost only (#158).
# NOTE Docker bypasses ufw: a port a container publishes is open whatever ufw
# says. With Dokploy (#183) only Traefik may publish ports (80, 443).
ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null
ufw limit 22/tcp comment 'SSH, rate limited' >/dev/null
ufw allow 80/tcp comment 'HTTP' >/dev/null
ufw allow 443/tcp comment 'HTTPS' >/dev/null
ufw --force enable >/dev/null
echo "ok    firewall on: 22 (rate limited), 80, 443"

# --- fail2ban: ban addresses that keep failing SSH ---------------------------------
cat > /etc/fail2ban/jail.d/dixpertia.local <<'EOF'
[sshd]
enabled  = true
backend  = systemd
maxretry = 5
findtime = 10m
bantime  = 1h
EOF
systemctl enable fail2ban >/dev/null
systemctl restart fail2ban
echo "ok    fail2ban watching SSH"

echo
echo "Done. Next: step 3, from an SSH session signed in as the admin user with your key."
