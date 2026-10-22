#!/bin/sh
# Start the API container (#185): migrate, then serve.
#
# With MIGRATE_ON_START=true, the schema is brought up to date first, as the
# schema owner (SCHEMA_DATABASE_URL). A failed migration stops here: the
# container never becomes healthy and the platform keeps the previous one.
#
# The owner's credentials are then REMOVED from the environment before the
# API starts. The application runs as the least-privileged role (#70); it must
# not be able to read the owner's password from its own environment, even
# after a flaw (/proc/self/environ).
set -eu

if [ "${MIGRATE_ON_START:-false}" = "true" ]; then
  echo "entrypoint: alembic upgrade head"
  alembic upgrade head
fi

exec env -u SCHEMA_DATABASE_URL uvicorn main:app \
  --host 0.0.0.0 --port 8000 \
  --workers "${WEB_CONCURRENCY:-2}" \
  --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}" \
  --no-server-header
