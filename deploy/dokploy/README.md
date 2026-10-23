# Deploying with Dokploy (#183)

[Dokploy](https://dokploy.com) runs the two application images (#185) on the VPS. It builds them from this repository, routes traffic with Traefik, gets HTTPS certificates from Let's Encrypt, and redeploys on a push. PostgreSQL stays the one already on the host (#158). The containers reach it through Docker's internal bridge, and it is never on a public address.

**Before you start:** the server must be hardened (`deploy/server`, #172). `install.sh` refuses to run while SSH still accepts passwords or root.

**Until dixpertia.tn exists**, the app lives at **`https://102-204-207-34.sslip.io`**. sslip.io is a public DNS service that resolves a hostname written that way to that IP, so Let's Encrypt can issue a real certificate with no domain of our own. The dashboard gets `dokploy.102-204-207-34.sslip.io`. When the domain is ready, add it in Dokploy next to these (#184).

| File | What it does |
|---|---|
| `install.sh` | Installs Dokploy at a **pinned, checksummed** release. Makes `/etc/dokploy` no longer world-writable. Lets the Docker bridge, and only it, reach PostgreSQL. |
| `verify.sh` | Checks what runs, what the internet can reach, and the API's path to PostgreSQL. |

All commands run in your **SSH session as `dixadmin`** (VS Code terminal), unless marked **[LAPTOP]**.

---

## 1. Update the repository and install

```bash
sudo git -C /opt/dixpertia pull --ff-only
sudo bash /opt/dixpertia/deploy/dokploy/install.sh
```

It takes a few minutes: Docker, the swarm, then Dokploy, its own database and Traefik. It ends by re-applying the PostgreSQL configuration, so that PostgreSQL now also listens on the Docker bridge.

**Do step 2 straight away.** Until you create the admin account, anyone who opens port 3000 of the server's address can create it instead.

## 2. Create the admin account, through an SSH tunnel

**[LAPTOP]** In a new PowerShell window:

```powershell
ssh -i $HOME\.ssh\dixpertia_vps -L 3000:localhost:3000 dixadmin@102.204.207.34
```

Leave that window open. In your browser, open **http://localhost:3000**. The tunnel carries it to the server, encrypted, so this is not the public port.

- Create the admin account: your e-mail address and a **long, unique password** from your password manager.
- Go to **Settings → Profile** and **enable two-factor authentication** right away. Dokploy controls Docker, which is root on this server.

## 3. Give the dashboard its HTTPS address, then close port 3000

In Dokploy, open **Settings → Server / Web Server** (the server's own domain):

- **Domain:** `dokploy.102-204-207-34.sslip.io`
- **Let's Encrypt e-mail:** yours
- **HTTPS:** on, with the Let's Encrypt certificate

Save, wait a minute, then open **https://dokploy.102-204-207-34.sslip.io** in a new tab. Close port 3000 **only once that page loads with a valid padlock**:

```bash
docker service update --publish-rm "published=3000,target=3000,mode=host" dokploy
```

Since port 3000 is no longer published, the SSH tunnel from step 2 stops working. If the HTTPS address ever fails, publish the port again with `--publish-add` in place of `--publish-rm` and use the tunnel.

## 4. Verify

```bash
sudo bash /opt/dixpertia/deploy/dokploy/verify.sh
```

Every line should read `ok`. The output ends with **dokploy-network's address range**; note it for step 6 (`FORWARDED_ALLOW_IPS`).

## 5. The database and its two roles

```bash
sudo apt-get install -y python3-psycopg2
sudo -u postgres python3 /opt/dixpertia/db/setup_roles.py \
  --superuser-url "postgresql:///dixpertia?host=/var/run/postgresql"
```

It prints **two passwords, once**: one for `dixpertia_app`, one for `dixpertia_owner`. Store them in your password manager now. They go into the API's settings in step 6, and nowhere else.

## 6. The two applications

In Dokploy: **Projects → Create project** `DIXpertIA`. Inside it, create two **Applications**.

First connect GitHub: **Settings → Git → GitHub** → install the Dokploy GitHub App **on the DIXpertIA repository only** (not "all repositories").

### `api`
- **Source:** GitHub, repository `Ihebdhouibi/DIXpertIA`, branch **`main`** for production (the `deployment` branch is staging's, see *Staging* below).
- **Build type:** Dockerfile, path `Dockerfile`.
- **Environment.** Replace `<...>`, and generate the secret with `openssl rand -base64 48`:

  ```
  DATABASE_URL=postgresql://dixpertia_app:<app password>@172.18.0.1:5432/dixpertia
  SCHEMA_DATABASE_URL=postgresql://dixpertia_owner:<owner password>@172.18.0.1:5432/dixpertia
  SECRET_KEY=<openssl rand -base64 48>
  MIGRATE_ON_START=true
  FORWARDED_ALLOW_IPS=<dokploy-network range from step 4, e.g. 10.0.1.0/24>
  WEB_CONCURRENCY=1
  API_DOCS=true
  FRONTEND_URL=https://102-204-207-34.sslip.io
  ```

  - **Never set `FORWARDED_ALLOW_IPS` to `*`.** A visitor could then fake their IP address and bypass the rate limits.
  - `API_DOCS=true` is for this test environment only.
  - E-mail (#186), through Oxahost's mail server, which hands mail to MailChannels. The domain's SPF, DKIM and DMARC records must be in place (they are for dixpertia.tn), or Gmail refuses or bins the mail:
    ```
    SMTP_HOST=mailpro2.tn.oxa.host
    SMTP_PORT=465
    SMTP_USER=contact@dixpertia.tn
    SMTP_PASSWORD=<contact mailbox password>
    SMTP_FROM=DI Xpertia <contact@dixpertia.tn>
    CONTACT_INBOX=contact@dixpertia.tn
    ```
- **Domain:** host `102-204-207-34.sslip.io`, path **`/api`**, container port **8000**, HTTPS on, certificate **Let's Encrypt**. Do **not** strip the path: the API's routes start with `/api`.

### `web`
- **Source:** the same repository and branch.
- **Build type:** Dockerfile, path `Dockerfile.web`.
- **Build arguments:** `FRONTEND_URL=https://102-204-207-34.sslip.io`
- **Domain:** host `102-204-207-34.sslip.io`, path **`/`**, container port **8080**, HTTPS on, **Let's Encrypt**.

**Deploy `api` first, then `web`.** The API's log should show `alembic upgrade head`, then uvicorn starting.

## 7. The table grants, once, after the first migration

Re-run the role setup with **the same two passwords**, so that the grants that need the tables apply (`db/README.md`, step 4). Start the line with **a space**: Ubuntu's shell then keeps it out of its history.

```bash
 sudo -u postgres python3 /opt/dixpertia/db/setup_roles.py \
  --superuser-url "postgresql:///dixpertia?host=/var/run/postgresql" \
  --app-password '<app password>' --owner-password '<owner password>'
```

## 8. The first administrator

E-mail is not set up yet (#186), so activation links cannot be sent. Create the first admin directly in the API container:

```bash
# Dokploy names containers <project>-<app without dashes>-<random>: production's
# API is dixpertia-api-..., staging's dixpertia-apistaging-... A bare "name=api"
# matches both, so name the one you mean.
sudo docker exec -it $(sudo docker ps -q -f name=dixpertia-api- | head -1) \
  python seed_users.py --email <your e-mail> --role admin
```

It prints a generated password **once**. Sign in at **https://102-204-207-34.sslip.io** and check that `/api/health` answers `{"status":"ok"}`.

## Staging (#184)

Staging is a second pair of applications, `api-staging` and `web-staging`, at **`https://staging.dixpertia.tn`**. It uses its own database cluster on port 5433, with its own roles, and **invented data only** (GDPR).

| | Production | Staging |
|---|---|---|
| Address | `dixpertia.tn`, `www.dixpertia.tn` | `staging.dixpertia.tn` |
| Branch | `main` (a release) | `deployment` |
| PostgreSQL | `17/main`, port 5432 | `17/staging`, port 5433 |
| API docs | off | on (`API_DOCS=true`) |
| E-mail | `contact@dixpertia.tn` | the same mailbox, sender name **DI Xpertia (staging)**, links to staging only. The plan has one mailbox. |

1. **DNS:** an `A` record `staging` pointing to `102.204.207.34`.
2. **Database:**
   ```bash
   sudo git -C /opt/dixpertia pull --ff-only
   sudo bash /opt/dixpertia/deploy/postgres/staging.sh
   sudo -u postgres python3 /opt/dixpertia/db/setup_roles.py \
     --superuser-url "postgresql:///dixpertia?host=/var/run/postgresql&port=5433" | grep -o 'dixpertia_[a-z]*:[^@]*'
   ```
   The last command prints the **staging** passwords, once. They are different from production's.
3. **`api-staging`:** set it up as `api` in step 6, with branch **`deployment`**, and this environment:
   ```
   DATABASE_URL=postgresql://dixpertia_app:<staging app password>@172.18.0.1:5433/dixpertia
   SCHEMA_DATABASE_URL=postgresql://dixpertia_owner:<staging owner password>@172.18.0.1:5433/dixpertia
   SECRET_KEY=<a new one: openssl rand -base64 48, never production's>
   MIGRATE_ON_START=true
   FORWARDED_ALLOW_IPS=10.0.1.0/24
   WEB_CONCURRENCY=1
   API_DOCS=true
   FRONTEND_URL=https://staging.dixpertia.tn
   ```
   **Domain:** `staging.dixpertia.tn`, path `/api`, port `8000`, HTTPS with Let's Encrypt. Under **Advanced → Resources**, limit memory to **512 MB**, so a staging fault cannot starve production.
4. **`web-staging`:** set it up as `web`, with branch **`deployment`** and build argument `FRONTEND_URL=https://staging.dixpertia.tn`.
   - **Domain:** `staging.dixpertia.tn`, path `/`, port `8080`, HTTPS with Let's Encrypt.
   - **Advanced → Security → Basic Auth:** a user name and password, so that only the team can open staging, and search engines can't index it.
   - Put basic auth on `web-staging` **only, never on `api-staging`**: the app sends its own `Authorization: Bearer` header to the API, which basic auth would replace. The API is protected anyway: it requires sign-in, and its public routes are rate-limited.
5. **E-mail:** the SMTP lines of step 6, with `SMTP_FROM=DI Xpertia (staging) <contact@dixpertia.tn>`. Staging only e-mails the team, and its links lead to staging only, because of its `FRONTEND_URL`. If the mailbox password changes, update it in **both** `api` and `api-staging`.
6. **Table grants and first admin:** steps 7 and 8, with `&port=5433` in the URL, the staging passwords, and `name=dixpertia-apistaging-` in the `docker ps` filter.

**The release flow:**
1. Merge features into `develop`.
2. Open a PR from `develop` into `deployment`. Merging it redeploys **staging**. Check it there.
3. Open a PR from `deployment` into `main`, tag the release, and **Deploy** production.

## Updating

- **Redeploy:** nothing deploys from `develop` directly; see *the release flow* under *Staging*. Turn **Auto deploy** on for the staging applications only, so that production changes only when you click **Deploy**. Migrations run by themselves.
- **Dokploy itself:** use its own update button (**Settings → Server**). Then re-run `install.sh`'s permission fix: `sudo chmod 0750 /etc/dokploy`.
- **Docker:** the installer holds the Docker packages (`apt-mark hold`), so unattended upgrades skip them. Once a month:
  ```bash
  sudo apt-mark unhold docker-ce docker-ce-cli docker-ce-rootless-extras
  sudo apt-get update && sudo apt-get install --only-upgrade docker-ce docker-ce-cli docker-ce-rootless-extras
  sudo apt-mark hold docker-ce docker-ce-cli docker-ce-rootless-extras
  ```

## Decisions

- **PostgreSQL on the host, reached through `docker_gwbridge` (172.18.0.1).** Three layers keep it closed:
  - `pg_hba.conf` admits only the two application roles, only from that bridge;
  - ufw allows 5432 on that interface only;
  - PostgreSQL starts after Docker, so the bridge address exists when it binds.
- **The installer is pinned and checksummed.** `curl … | sh` of a moving `install.sh` would run whatever is on the server that day, as root. A new Dokploy version is a reviewed change to this folder.
- **Only Traefik publishes ports.** Docker bypasses ufw, so `verify.sh` checks what is really published rather than trusting the firewall.
