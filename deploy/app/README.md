# The application images (#185)

Two images, built and checked in CI (the **images** job) and deployed by Dokploy (#183) on staging and production (#184). The same images run in both environments; only the environment variables differ.

| Image | Built from | Runs as | Listens on |
|---|---|---|---|
| **API** | `Dockerfile` | uid 10001, not root | 8000 |
| **Web** (the frontend) | `Dockerfile.web`: the Vite build, served by nginx-unprivileged | uid 101, not root | 8080 |

Both answer a health check: the API on `GET /api/health`, the web image on `/`.

## Routing (Traefik, set up in #184)

Each domain has two routes on the same host:
- `/api` goes to the API container;
- everything else goes to the web container.

The browser therefore calls the API on its own origin, with no CORS. HTTPS and HSTS are Traefik's job. The containers only see plain HTTP inside the Docker network, and **neither publishes a port**: Docker bypasses ufw (#172).

## API environment

| Variable | Value |
|---|---|
| `DATABASE_URL` | The **app** role (`dixpertia_app`), least privilege (#70). |
| `SCHEMA_DATABASE_URL` | The **owner** role, for migrations only. See below. |
| `SECRET_KEY` | At least 32 characters, **different per environment**, so a staging token never works in production. |
| `MIGRATE_ON_START` | `true`: run `alembic upgrade head` before starting. A failed migration stops the deploy. |
| `FORWARDED_ALLOW_IPS` | The Docker network's range, e.g. `10.0.1.0/24`, found in #183. Without it, every visitor counts as Traefik for the rate limits (#175). **Never `*`**: uvicorn would then believe whatever `X-Forwarded-For` a visitor sends, and the rate limits could be bypassed. |
| `WEB_CONCURRENCY` | Workers: 2 in production, 1 on staging. |
| `API_DOCS` | `true` on staging only. |
| `FRONTEND_URL` | The environment's origin. Also passed as a build argument to the web image, for its link-preview tags. |
| Others | The SMTP settings (#186), `CONTACT_*`, the rate limits: see `.env.example`. |

**The owner's password never reaches the running API.** The entrypoint first runs the migrations with it, then starts uvicorn with `SCHEMA_DATABASE_URL` removed from the environment. CI checks this by reading the running process's environment.

## Database: first time, then every deploy

**Once per environment**, on the server, as the PostgreSQL superuser (#158). This step creates the roles, builds the schema, and then grants table rights that only apply once the tables exist:

```bash
docker run --rm --network host --entrypoint python <api-image> db/setup_roles.py \
  --superuser-url "postgresql://postgres@/dixpertia?host=/var/run/postgresql"
# keep the two passwords it prints: they go into DATABASE_URL and SCHEMA_DATABASE_URL
```

Run it again after the first deploy has migrated, with the same two passwords (`--app-password`, `--owner-password`), as `db/README.md` describes. This version uses the socket; how containers reach PostgreSQL is decided in #183.

**Every deploy:** nothing to do by hand. `MIGRATE_ON_START=true` brings the schema up to date before the new API answers. A migration that adds a table carries its own grants and revokes, as `b3d7f1a9c2e5_auth_attempts` does.

## Building by hand

```bash
docker build -t dixpertia-api .
docker build -f Dockerfile.web --build-arg FRONTEND_URL=https://dixpertia.tn -t dixpertia-web .
```
