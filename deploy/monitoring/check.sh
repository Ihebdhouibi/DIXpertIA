#!/usr/bin/env bash
# Server-side checks (#188), run every 5 minutes by the dixpertia-check timer.
# By hand:  sudo /usr/local/sbin/dixpertia-check
#
# Looks at what an outside uptime monitor cannot see: disk and memory, the
# databases, the nightly backup, certificates about to expire, the containers,
# and bursts in the API's refusals and errors. Mails the admin when a problem
# starts, again every REMIND_HOURS while it lasts, and once when it is gone;
# a quiet run sends nothing.
#
# Settings: /etc/dixpertia/monitoring.env (see monitoring.env.example).
#
# No `set -e`: one failing check must not stop the others. No pipefail either,
# and never `cmd | grep -q` (#207): every output is captured, then tested.
set -u

CONFIG="${CONFIG:-/etc/dixpertia/monitoring.env}"
# shellcheck source=/dev/null
[ -r "$CONFIG" ] && . "$CONFIG"

STATE_DIR="${STATE_DIR:-/var/lib/dixpertia-monitor}"
DISK_PATHS="${DISK_PATHS:-/}"
DISK_MAX_PERCENT="${DISK_MAX_PERCENT:-80}"
MEM_MIN_PERCENT="${MEM_MIN_PERCENT:-10}"
PG_PORTS="${PG_PORTS:-5432 5433}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/dixpertia}"
BACKUP_MAX_AGE_HOURS="${BACKUP_MAX_AGE_HOURS:-26}"
CERT_HOSTS="${CERT_HOSTS:-dixpertia.tn www.dixpertia.tn staging.dixpertia.tn dokploy.dixpertia.tn}"
CERT_MIN_DAYS="${CERT_MIN_DAYS:-14}"
HEALTH_URLS="${HEALTH_URLS:-https://dixpertia.tn/api/health}"
CONTAINERS="${CONTAINERS:-dixpertia-api- dixpertia-web-}"
API_CONTAINERS="${API_CONTAINERS:-dixpertia-api-}"
LOG_WINDOW="${LOG_WINDOW:-5m}"
MAX_429="${MAX_429:-30}"
MAX_401="${MAX_401:-40}"
MAX_5XX="${MAX_5XX:-10}"
REMIND_HOURS="${REMIND_HOURS:-12}"
MAIL_MODE="${MAIL_MODE:-smtp}"
MAIL_FROM="${MAIL_FROM:-contact@dixpertia.tn}"
MAIL_TO="${MAIL_TO:-contact@dixpertia.tn}"
MAIL_SPOOL="${MAIL_SPOOL:-/tmp/dixpertia-mail}"
HOST_LABEL="${HOST_LABEL:-$(hostname)}"

install -d -m 0700 "$STATE_DIR"

# --- Collecting problems ------------------------------------------------------------
# Each problem has a stable key (one state file) and a line for the mail.
declare -A PROBLEMS=()
problem() { PROBLEMS["$1"]="$2"; }

check_disk() {
    local path used
    for path in $DISK_PATHS; do
        used="$(df --output=pcent "$path" 2>/dev/null | tail -1 | tr -dc '0-9')"
        if [ -z "$used" ]; then
            problem "disk-${path//\//_}" "Disk: cannot read the usage of $path."
        elif [ "$used" -ge "$DISK_MAX_PERCENT" ]; then
            problem "disk-${path//\//_}" "Disk: $path is ${used}% full (alert at ${DISK_MAX_PERCENT}%)."
        fi
    done
}

check_memory() {
    local total avail percent
    total="$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)"
    avail="$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)"
    [ -n "$total" ] && [ "$total" -gt 0 ] || return
    percent=$((avail * 100 / total))
    if [ "$percent" -lt "$MEM_MIN_PERCENT" ]; then
        problem memory "Memory: only ${percent}% available (alert under ${MEM_MIN_PERCENT}%)."
    fi
}

check_postgres() {
    local port
    [ -n "${PG_PORTS// /}" ] || return
    command -v pg_isready >/dev/null || { problem postgres "PostgreSQL: pg_isready is missing."; return; }
    for port in $PG_PORTS; do
        if ! pg_isready -q -h localhost -p "$port" -t 5; then
            problem "postgres-$port" "PostgreSQL: the cluster on port $port does not answer."
        fi
    done
}

check_backup() {
    # Only once the backup is installed (#171), which makes this folder.
    [ -d "$BACKUP_DIR" ] || return
    local last age_h state
    if [ ! -s "$BACKUP_DIR/LAST_SUCCESS" ]; then
        problem backup "Backup: no successful backup recorded in $BACKUP_DIR/LAST_SUCCESS."
    else
        last="$(date -d "$(cat "$BACKUP_DIR/LAST_SUCCESS")" +%s 2>/dev/null || echo 0)"
        age_h=$(( ($(date +%s) - last) / 3600 ))
        if [ "$age_h" -ge "$BACKUP_MAX_AGE_HOURS" ]; then
            problem backup "Backup: the last successful backup is ${age_h} hours old (alert at ${BACKUP_MAX_AGE_HOURS})."
        fi
    fi
    if command -v systemctl >/dev/null; then
        state="$(systemctl is-failed dixpertia-backup.service 2>/dev/null)"
        if [ "$state" = failed ]; then
            problem backup-unit "Backup: the last run failed. See: journalctl -u dixpertia-backup -n 50"
        fi
    fi
}

check_certificates() {
    local host target end end_s days
    for host in $CERT_HOSTS; do
        target="$host"
        case "$target" in *:*) ;; *) target="$host:443" ;; esac
        end="$(timeout 15 openssl s_client -connect "$target" -servername "${host%%:*}" </dev/null 2>/dev/null \
               | openssl x509 -noout -enddate 2>/dev/null)"
        end="${end#notAfter=}"
        if [ -z "$end" ]; then
            problem "cert-$host" "Certificate: could not read the certificate of $host."
            continue
        fi
        end_s="$(date -d "$end" +%s 2>/dev/null || echo 0)"
        days=$(( (end_s - $(date +%s)) / 86400 ))
        if [ "$days" -lt "$CERT_MIN_DAYS" ]; then
            problem "cert-$host" "Certificate: $host expires in $days days ($end). Let's Encrypt renews at 30 days left, so renewal is failing."
        fi
    done
}

check_health() {
    local url answer
    for url in $HEALTH_URLS; do
        answer="$(curl -fsS --max-time 15 "$url" 2>&1)"
        case "$answer" in
            *'"ok"'*) ;;
            *) problem "health-$url" "Health: $url does not answer ok (${answer:0:120})." ;;
        esac
    done
}

# A running container whose name contains the prefix. Dokploy names them
# <project>-<app>-<random>, so "dixpertia-api-" never matches staging's
# "dixpertia-apistaging-".
container_for() { docker ps -q -f "name=$1" 2>/dev/null | head -1; }

check_containers() {
    local prefix id
    [ -n "${CONTAINERS// /}" ] || return
    command -v docker >/dev/null || { problem docker "Docker: the docker command is missing."; return; }
    if ! docker info >/dev/null 2>&1; then
        problem docker "Docker: the daemon does not answer."
        return
    fi
    for prefix in $CONTAINERS; do
        id="$(container_for "$prefix")"
        [ -n "$id" ] || problem "container-$prefix" "Containers: no running container named ${prefix}*."
    done
}

# Bursts in the API's access log: uvicorn writes
#   INFO:     203.0.113.9:0 - "POST /api/login HTTP/1.1" 401 Unauthorized
# Many 429s or 401s is someone trying passwords or tokens (#175); many 5xx is
# the application failing. The top addresses go in the mail, to block them.
check_api_logs() {
    command -v docker >/dev/null || return
    local prefix id logs n429 n401 n5xx
    for prefix in $API_CONTAINERS; do
        id="$(container_for "$prefix")"
        [ -n "$id" ] || continue
        logs="$(docker logs --since "$LOG_WINDOW" "$id" 2>&1)"
        n429="$(grep -cE '" 429 ' <<< "$logs")"
        n401="$(grep -cE '" 401 ' <<< "$logs")"
        n5xx="$(grep -cE '" 5[0-9]{2} ' <<< "$logs")"
        top() { grep -E "\" $1 " <<< "$logs" | grep -oE '[0-9a-f.:]+:[0-9]+ - "' \
                | sed -E 's/:[0-9]+ - "$//' | sort | uniq -c | sort -rn | head -3 \
                | awk '{printf "%s%s (%s)", (NR>1?", ":""), $2, $1}'; }
        if [ "$n429" -gt "$MAX_429" ]; then
            problem "api-429-$prefix" "Security: $n429 requests refused for rate limits (429) in $LOG_WINDOW on ${prefix}*. Top: $(top 429)."
        fi
        if [ "$n401" -gt "$MAX_401" ]; then
            problem "api-401-$prefix" "Security: $n401 refused sign-ins or tokens (401) in $LOG_WINDOW on ${prefix}*. Top: $(top 401)."
        fi
        if [ "$n5xx" -gt "$MAX_5XX" ]; then
            problem "api-5xx-$prefix" "Errors: $n5xx server errors (5xx) in $LOG_WINDOW on ${prefix}*. See: docker logs --since $LOG_WINDOW $id"
        fi
    done
}

check_disk
check_memory
check_postgres
check_backup
check_certificates
check_health
check_containers
check_api_logs

# --- Deciding what to mail ------------------------------------------------------------
now="$(date +%s)"
new=() ongoing=() resolved=()
for key in "${!PROBLEMS[@]}"; do
    file="$STATE_DIR/$(printf '%s' "$key" | tr -c 'A-Za-z0-9._-' '_')"
    if [ ! -e "$file" ]; then
        new+=("${PROBLEMS[$key]}")
        printf '%s\n' "${PROBLEMS[$key]}" > "$file"
    elif [ $(( now - $(stat -c %Y "$file") )) -ge $(( REMIND_HOURS * 3600 )) ]; then
        ongoing+=("${PROBLEMS[$key]}")
        printf '%s\n' "${PROBLEMS[$key]}" > "$file"
    fi
done
known=" "
for key in "${!PROBLEMS[@]}"; do known+="$(printf '%s' "$key" | tr -c 'A-Za-z0-9._-' '_') "; done
for file in "$STATE_DIR"/*; do
    [ -e "$file" ] || continue
    case "$known" in *" $(basename "$file") "*) continue ;; esac
    resolved+=("$(cat "$file")")
    rm -f "$file"
done

for line in "${PROBLEMS[@]}"; do echo "PROBLEM  $line"; done
[ "${#PROBLEMS[@]}" -eq 0 ] && echo "ok    all checks passed"

total=$(( ${#new[@]} + ${#ongoing[@]} + ${#resolved[@]} ))
[ "$total" -gt 0 ] || exit 0

if [ "${#new[@]}" -gt 0 ] || [ "${#ongoing[@]}" -gt 0 ]; then
    subject="[DIXpertIA] ${#PROBLEMS[@]} problem(s) on $HOST_LABEL"
else
    subject="[DIXpertIA] resolved on $HOST_LABEL"
fi
body="$(
    echo "Server: $HOST_LABEL, $(date -R)"
    echo
    if [ "${#new[@]}" -gt 0 ]; then echo "NEW"; printf -- '- %s\n' "${new[@]}"; echo; fi
    if [ "${#ongoing[@]}" -gt 0 ]; then echo "STILL ONGOING"; printf -- '- %s\n' "${ongoing[@]}"; echo; fi
    if [ "${#resolved[@]}" -gt 0 ]; then echo "RESOLVED"; printf -- '- %s\n' "${resolved[@]}"; echo; fi
    echo "What to do: deploy/monitoring/RUNBOOK.md in the repository."
)"

# --- Sending -------------------------------------------------------------------------
message="$(mktemp)"
trap 'rm -f "$message"' EXIT
{
    echo "From: DI Xpertia monitoring <$MAIL_FROM>"
    echo "To: $MAIL_TO"
    echo "Subject: $subject"
    echo "Date: $(date -R)"
    echo "Content-Type: text/plain; charset=utf-8"
    echo
    echo "$body"
} > "$message"

if [ "$MAIL_MODE" = file ]; then
    install -d -m 0700 "$MAIL_SPOOL"
    cp "$message" "$MAIL_SPOOL/$(date +%s%N).eml"
    exit 0
fi

: "${SMTP_URL:?SMTP_URL missing in $CONFIG}" "${SMTP_USER:?}" "${SMTP_PASSWORD:?}"
# The password goes through curl's config on stdin, never on the command line,
# where any user could read it in the process list.
escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }
if ! printf 'user = "%s:%s"\n' "$(escape "$SMTP_USER")" "$(escape "$SMTP_PASSWORD")" \
    | curl -sS --max-time 30 --ssl-reqd --config - --url "$SMTP_URL" \
        --mail-from "$MAIL_FROM" --mail-rcpt "$MAIL_TO" \
        --upload-file "$message"; then
    echo "could not send the alert mail" >&2
    # Forget the new problems, so the next run tries to send them again.
    for key in "${!PROBLEMS[@]}"; do
        file="$STATE_DIR/$(printf '%s' "$key" | tr -c 'A-Za-z0-9._-' '_')"
        for line in "${new[@]}"; do [ "$line" = "${PROBLEMS[$key]}" ] && rm -f "$file"; done
    done
    exit 1
fi
echo "alert mail sent: $subject"
