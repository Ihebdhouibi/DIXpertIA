#!/usr/bin/env bash
# Check the Dokploy installation against #183. Every line should read "ok".
#
#   sudo bash /opt/dixpertia/deploy/dokploy/verify.sh
#
# Read-only, apart from one throwaway container that checks the API's path to
# PostgreSQL.
# No pipefail: each check asks `... | grep -q`, and under pipefail grep's early
# exit on a match makes the producer fail (SIGPIPE), so a pass would read as a FAIL.
set -u

failures=0
ok()   { echo "ok    $1"; }
fail() { echo "FAIL  $1"; failures=$((failures + 1)); }
note() { echo "note  $1"; }
check() { if eval "$2" >/dev/null 2>&1; then ok "$1"; else fail "$1"; fi; }

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }

# --- Dokploy is running ---------------------------------------------------------
check "Docker swarm active" "docker info --format '{{.Swarm.LocalNodeState}}' | grep -qx active"
for service in dokploy dokploy-postgres; do
  check "service $service running" \
        "docker service ls --filter name=^$service\$ --format '{{.Replicas}}' | grep -qx '1/1'"
done
check "Traefik running" "docker ps --filter name=^dokploy-traefik\$ --filter status=running -q | grep -q ."
check "/etc/dokploy not world-writable" "[ \"\$(stat -c %a /etc/dokploy)\" = 750 ]"

# --- What the internet can reach ---------------------------------------------------
# Docker bypasses ufw, so the published ports are the ones that count.
published="$(docker ps --format '{{.Ports}}' | tr ',' '\n' | grep -oE '0\.0\.0\.0:[0-9]+' | cut -d: -f2 | sort -nu | tr '\n' ' ')"
if [ "$published" = "80 443 " ]; then
  ok "only Traefik publishes ports: 80, 443"
else
  case " $published" in
    *" 3000 "*) note "the dashboard is still published on port 3000 - close it once its HTTPS domain works (README step 3)" ;;
    *) fail "published ports: $published (expected 80 443)" ;;
  esac
fi
check "ufw does not open the swarm ports" "! ufw status | grep -qE '^(2377|7946|4789)'"

# --- The API's path to PostgreSQL --------------------------------------------------
check "docker_gwbridge is 172.18.0.1/16" "ip -4 -o addr show docker_gwbridge | grep -q ' 172.18.0.1/16 '"
check "PostgreSQL listens on the bridge" "ss -tlnH 'sport = :5432' | grep -q '172.18.0.1:5432'"
check "ufw lets the bridge reach 5432" "ufw status | grep -q '172.18.0.1 5432/tcp on docker_gwbridge'"
check "PostgreSQL starts after Docker" "systemctl show postgresql@17-main -p After | grep -q docker.service"
check "a container on dokploy-network reaches PostgreSQL" \
      "docker run --rm --network dokploy-network postgres:17 pg_isready -q -h 172.18.0.1 -p 5432"

echo
echo "dokploy-network's range, for the API's FORWARDED_ALLOW_IPS:"
docker network inspect dokploy-network --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'

echo
if [ "$failures" -eq 0 ]; then echo "All checks passed."; else echo "$failures check(s) failed."; exit 1; fi
