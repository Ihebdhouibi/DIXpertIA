# PostgreSQL on the production server (#158)

The production server is an Oxahost VPS running Ubuntu 24.04, with 4 cores and 7.8 GB of RAM. The API and PostgreSQL run on the same machine. PostgreSQL listens on **localhost only**, so it is never reachable from the network, and the connection between the API and the database never leaves the machine. That is why it has no TLS. Server hardening (admin user, SSH keys, firewall) is #172, and backups are #171.

| File | What it is |
|---|---|
| `install.sh` | Installs PostgreSQL 17 from the official repository (apt.postgresql.org). CI tests against 17, while Ubuntu ships 16. |
| `dixpertia.conf` | Our server settings: localhost only, memory, timeouts, logging. Installed into `conf.d/`, so the packaged `postgresql.conf` is never edited. |
| `pg_hba.conf` | Who may connect: the `postgres` superuser from a shell on the server, and the two application roles to `dixpertia` from this machine with a password. Nothing else. |
| `apply.sh` | Installs both files, refuses to restart if PostgreSQL reports an error in them, restarts, and creates the `dixpertia` database. |
| `verify.sh` | Checks the running server against all of the above. |
| `ci-check.sh` | Run by CI: parses both files with a real PostgreSQL 17 on every pull request. |

## First installation

From PowerShell, in the repository, copy this folder to the server:

```powershell
scp -r deploy/postgres root@<server-ip>:/root/postgres-setup
ssh root@<server-ip>
```

Then, on the server:

```bash
bash /root/postgres-setup/install.sh    # PostgreSQL 17
bash /root/postgres-setup/apply.sh      # our configuration, and the dixpertia database
bash /root/postgres-setup/verify.sh     # every line should read "ok"
```

All three scripts can be run again safely. After changing `dixpertia.conf` or `pg_hba.conf`, copy the folder again, then run `apply.sh` and `verify.sh`.

The roles (`db/setup_roles.py`) and the schema (`alembic upgrade head`) come with the application's deployment. They need the application's code on the server. On the server, `setup_roles.py` connects as the `postgres` superuser through the local socket, with no password:
`--superuser-url "postgresql://postgres@/dixpertia?host=/var/run/postgresql"`, run as the `postgres` OS user.

## Decisions in `dixpertia.conf`

- **Timeouts:** 5 minutes per statement and 10 minutes idle in a transaction, for every role. This is a safety net that leaves room for a migration; a longer one can `SET statement_timeout` for itself. The application role keeps its tighter 30 s / 60 s from #70.
- **Memory:** `shared_buffers` 1 GB and `effective_cache_size` 4 GB, leaving room for the API on the same 7.8 GB.
- **Logging:** every connection and disconnection, every schema change (`log_statement = ddl`), queries slower than 500 ms, and lock waits. Messages are in English (`lc_messages = 'C'`), which is what the application recognises and translates (#135, #161).

## The staging cluster (#184)

Staging has its own PostgreSQL **cluster**, `17/staging` on port **5433**, next to production's `17/main` on 5432. It is not a second database in the same cluster, because roles belong to the whole cluster and the migrations name `dixpertia_app` and `dixpertia_owner`. In one cluster, staging would share production's roles and their passwords. Here it has its own roles, passwords and data.

```bash
sudo bash /opt/dixpertia/deploy/postgres/staging.sh             # create it, apply the configuration
sudo CLUSTER=staging bash /opt/dixpertia/deploy/postgres/verify.sh
```

`staging.conf` is read after `dixpertia.conf`. It changes only the port and the memory (256 MB of shared buffers instead of 1 GB); everything else is production's configuration, so staging tests the same rules. Both `apply.sh` and `verify.sh` take `CLUSTER=staging`.

## Logs

Ubuntu's packaging writes them to `/var/log/postgresql/postgresql-17-main.log` and rotates them weekly (`/etc/logrotate.d/postgresql-common`).

```bash
tail -f /var/log/postgresql/postgresql-17-main.log
grep 'duration:' /var/log/postgresql/postgresql-17-main.log    # slow queries
```

## Rolling back

```bash
cp -p /etc/postgresql/17/main/pg_hba.conf.orig /etc/postgresql/17/main/pg_hba.conf
rm /etc/postgresql/17/main/conf.d/dixpertia.conf
systemctl restart postgresql@17-main
```
