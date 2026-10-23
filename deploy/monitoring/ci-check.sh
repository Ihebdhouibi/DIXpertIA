#!/usr/bin/env bash
# Run by CI in the ubuntu:24.04 image (#188), with this folder on /conf:
#   docker run --rm -v "$PWD/deploy/monitoring:/conf:ro" ubuntu:24.04 bash /conf/ci-check.sh
#
# check.sh against made-up problems: each one is mailed once, reminded after
# REMIND_HOURS, and reported resolved once gone; a quiet server sends nothing.
# Mails go to files (MAIL_MODE=file), docker is a stub that replays a log.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null
apt-get install -qq -y curl openssl >/dev/null

failures=0
check() { if [ "$2" = "$3" ]; then echo "ok    $1"; else echo "FAIL  $1: expected '$2', got '$3'"; failures=$((failures + 1)); fi; }
has() { if grep -q -- "$2" "$3"; then echo "ok    $1"; else echo "FAIL  $1: '$2' not in $3"; cat "$3"; failures=$((failures + 1)); fi; }

W=/tmp/mon
mkdir -p "$W/bin"
export MAIL_MODE=file MAIL_SPOOL="$W/mail" STATE_DIR="$W/state" CONFIG=/nonexistent
# Everything off; each test turns on what it needs. A space, not empty: empty
# means "use the default".
export DISK_PATHS=/ DISK_MAX_PERCENT=101 MEM_MIN_PERCENT=0 PG_PORTS=" " CERT_HOSTS=" " \
       HEALTH_URLS=" " CONTAINERS=" " API_CONTAINERS=" " BACKUP_DIR=/nonexistent
run() { env "$@" bash /conf/check.sh > "$W/out" 2>&1 || true; }
mails() { find "$MAIL_SPOOL" -name '*.eml' 2>/dev/null | wc -l; }
last_mail() { find "$MAIL_SPOOL" -name '*.eml' | sort | tail -1; }

# --- A quiet server ------------------------------------------------------------------
run
check "a quiet server sends nothing" "0" "$(mails)"
has "and says so" "all checks passed" "$W/out"

# --- One problem: mailed once, reminded, resolved --------------------------------------
run DISK_MAX_PERCENT=0
check "a new problem is mailed" "1" "$(mails)"
has "as NEW" "^NEW" "$(last_mail)"
has "with what is wrong" "Disk: / is" "$(last_mail)"
has "and a subject" "^Subject: \[DIXpertIA\] 1 problem(s)" "$(last_mail)"
run DISK_MAX_PERCENT=0
check "the same problem 5 minutes later is not mailed again" "1" "$(mails)"
touch -d '13 hours ago' "$STATE_DIR"/*
run DISK_MAX_PERCENT=0
check "after 12 hours, a reminder" "2" "$(mails)"
has "as STILL ONGOING" "^STILL ONGOING" "$(last_mail)"
run
check "once gone, one mail" "3" "$(mails)"
has "as RESOLVED" "^RESOLVED" "$(last_mail)"
check "and nothing is remembered" "0" "$(find "$STATE_DIR" -type f | wc -l)"
run
check "then quiet again" "3" "$(mails)"

# --- The backup ----------------------------------------------------------------------
mkdir -p "$W/backups"
date -Iseconds -d '30 hours ago' > "$W/backups/LAST_SUCCESS"
run BACKUP_DIR="$W/backups"
has "a 30-hour-old backup is a problem" "Backup: the last successful backup is 30 hours old" "$W/out"
date -Iseconds > "$W/backups/LAST_SUCCESS"
run BACKUP_DIR="$W/backups"
has "a fresh one is not" "all checks passed" "$W/out"
rm "$W/backups/LAST_SUCCESS"
run BACKUP_DIR="$W/backups"
has "no backup at all is" "no successful backup recorded" "$W/out"
run BACKUP_DIR=/nonexistent
has "and no backup installed yet is not watched" "all checks passed" "$W/out"

# --- Certificates ---------------------------------------------------------------------
openssl req -x509 -newkey rsa:2048 -nodes -subj /CN=localhost -days 5 \
    -keyout "$W/key.pem" -out "$W/cert.pem" 2>/dev/null
openssl s_server -quiet -accept 8443 -cert "$W/cert.pem" -key "$W/key.pem" -www >/dev/null 2>&1 &
server=$!
for _ in $(seq 20); do (exec 3<>/dev/tcp/127.0.0.1/8443) 2>/dev/null && break; sleep 0.5; done
run CERT_HOSTS=localhost:8443
has "a certificate with 5 days left is a problem" "Certificate: localhost:8443 expires in 4 days" "$W/out"
run CERT_HOSTS=localhost:8443 CERT_MIN_DAYS=3
has "not under the threshold" "all checks passed" "$W/out"
kill "$server"
run CERT_HOSTS=localhost:8443
has "an unreachable site is" "could not read the certificate of localhost:8443" "$W/out"

# --- Health ---------------------------------------------------------------------------
echo '{"status":"ok"}' > "$W/ok.json"
echo '{"status":"unavailable"}' > "$W/down.json"
run HEALTH_URLS="file://$W/ok.json"
has "a healthy API is fine" "all checks passed" "$W/out"
run HEALTH_URLS="file://$W/down.json"
has "an unavailable one is a problem" "Health: file://$W/down.json does not answer ok" "$W/out"

# --- Containers and the API's log -------------------------------------------------------
{
    for _ in $(seq 35); do echo 'INFO:     203.0.113.9:0 - "POST /api/login HTTP/1.1" 429 Too Many Requests'; done
    for _ in $(seq 41); do echo 'INFO:     198.51.100.7:0 - "POST /api/login HTTP/1.1" 401 Unauthorized'; done
    for _ in $(seq 3); do echo 'INFO:     192.0.2.1:0 - "POST /api/login HTTP/1.1" 401 Unauthorized'; done
    for _ in $(seq 2); do echo 'INFO:     192.0.2.1:0 - "GET /api/invoices HTTP/1.1" 500 Internal Server Error'; done
    echo 'INFO:     192.0.2.1:0 - "GET /api/health HTTP/1.1" 200 OK'
} > "$W/api.log"
cat > "$W/bin/docker" <<STUB
#!/usr/bin/env bash
case "\$1" in
    info) exit 0 ;;
    ps) case "\$*" in *dixpertia-api-*) echo abc123 ;; esac ;;
    logs) cat "$W/api.log" ;;
esac
STUB
chmod +x "$W/bin/docker"
run PATH="$W/bin:$PATH" CONTAINERS="dixpertia-api- dixpertia-web-" API_CONTAINERS="dixpertia-api-"
has "a missing container is a problem" "no running container named dixpertia-web-" "$W/out"
has "35 rate-limit refusals in 5 minutes are a problem" "Security: 35 requests refused for rate limits" "$W/out"
has "with the address behind them" "Top: 203.0.113.9 (35)" "$W/out"
has "44 refused sign-ins are a problem" "Security: 44 refused sign-ins" "$W/out"
has "with the top addresses, most first" "Top: 198.51.100.7 (41), 192.0.2.1 (3)" "$W/out"
check "2 server errors are under the threshold" "0" "$(grep -c 'Errors:' "$W/out" || true)"
check "the running container is not reported" "0" "$(grep -c 'named dixpertia-api-' "$W/out" || true)"

# --- Sending by SMTP: the password never on the command line -----------------------------
# A stand-in curl records its arguments (what `ps` shows every user) apart
# from its standard input (what nobody else sees).
mkdir -p "$W/smtp"
cat > "$W/smtp/curl" <<STUB
#!/usr/bin/env bash
printf '%s\n' "\$*" > "$W/curl.args"
cat > "$W/curl.stdin"
STUB
chmod +x "$W/smtp/curl"
rm -rf "$STATE_DIR"
run PATH="$W/smtp:$PATH" MAIL_MODE=smtp DISK_MAX_PERCENT=0 SMTP_URL=smtps://mail.example:465 \
    SMTP_USER=alerts@example.tn SMTP_PASSWORD='s3cr"et\pw' MAIL_FROM=alerts@example.tn MAIL_TO=admin@example.tn
has "the mail is sent" "alert mail sent" "$W/out"
check "the password is not in curl's arguments" "0" "$(grep -c 's3cr' "$W/curl.args" || true)"
has "it reaches curl on its standard input, quoted" 'user = "alerts@example.tn:s3cr\\"et\\\\pw"' "$W/curl.stdin"
has "to the right server and recipient" "--url smtps://mail.example:465 --mail-from alerts@example.tn --mail-rcpt admin@example.tn" "$W/curl.args"
has "over TLS only" "--ssl-reqd" "$W/curl.args"

echo
if [ "$failures" -gt 0 ]; then echo "$failures check(s) failed"; exit 1; fi
echo "all monitoring checks passed"
