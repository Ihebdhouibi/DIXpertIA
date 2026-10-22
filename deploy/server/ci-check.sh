#!/usr/bin/env bash
# Run by CI in an ubuntu:24.04 container (#172): sshd-dixpertia.conf parses,
# and wins over the cloud image's 50-cloud-init.conf, which turns passwords on.
# A typo, or a file name sorting after 50-, would otherwise only show on the
# server - as a lockdown that silently did nothing.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null
apt-get install -qq -y openssh-server >/dev/null
mkdir -p /run/sshd
ssh-keygen -A >/dev/null
useradd -m dixadmin

# What an Oxahost / cloud Ubuntu image ships.
echo 'PasswordAuthentication yes' > /etc/ssh/sshd_config.d/50-cloud-init.conf
# What 03-ssh-lockdown.sh installs.
sed "s/__ADMIN_USER__/dixadmin/" /conf/sshd-dixpertia.conf > /etc/ssh/sshd_config.d/01-dixpertia.conf

sshd -t
echo "ok    sshd accepts the configuration"

EFFECTIVE="$(sshd -T)"
failures=0
for setting in "permitrootlogin no" "passwordauthentication no" "kbdinteractiveauthentication no" \
               "authenticationmethods publickey" "allowusers dixadmin" "maxauthtries 3" \
               "x11forwarding no" "allowtcpforwarding local"; do
  if grep -qix "$setting" <<< "$EFFECTIVE"; then
    echo "ok    $setting"
  else
    echo "FAIL  $setting (got: $(echo "$EFFECTIVE" | grep -i "^${setting%% *} " || echo unset))"
    failures=$((failures + 1))
  fi
done
[ "$failures" -eq 0 ]
