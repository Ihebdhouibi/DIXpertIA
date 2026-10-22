# The API image (#185). The same image runs on staging and production; only
# the environment differs. Built and scanned in CI.
#
#   docker build -t dixpertia-api .
#   docker run --env-file .env -p 8000:8000 dixpertia-api
#
# Python 3.11, as in CI, on a pinned Debian release so a rebuild does not
# silently move the base.
FROM python:3.11.16-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Security fixes released since the base image was built (the CI scan fails on
# a critical one that has a fix). Nothing else is installed.
RUN apt-get update     && apt-get -y upgrade     && rm -rf /var/lib/apt/lists/*

# Dependencies first, for layer caching. psycopg2-binary ships its own libpq,
# so no compiler is installed.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Only what runs: the API, its migrations, the role setup and the first-admin
# script. Tests, the frontend and documents stay out (.dockerignore).
COPY main.py alembic.ini seed_users.py ./
COPY app ./app
COPY alembic ./alembic
COPY db ./db
COPY deploy/app/entrypoint.sh /usr/local/bin/entrypoint

# Never root: an application flaw then owns one unprivileged user in one
# container, not the container. A fixed uid, so file ownership is predictable.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app \
    && chmod 0755 /usr/local/bin/entrypoint
USER app

EXPOSE 8000

# Workers per container. Behind Traefik (#183), set FORWARDED_ALLOW_IPS to the
# Docker network's range so request.client is the visitor's address and the
# rate limits (#175) count visitors, not the proxy. The default trusts no one.
ENV WEB_CONCURRENCY=2 \
    FORWARDED_ALLOW_IPS=127.0.0.1

# Python, not curl: nothing extra installed just for the check.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status != 200)"]

ENTRYPOINT ["entrypoint"]
