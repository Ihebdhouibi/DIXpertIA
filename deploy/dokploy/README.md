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
- **Source:** GitHub, repository `Ihebdhouibi/DIXpertIA`, branch **`deployment`**.
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
  - Leave SMTP unset until #186: e-mails are then logged, not sent.
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
sudo docker exec -it $(sudo docker ps -q -f name=api | head -1) \
  python seed_users.py --email <your e-mail> --role admin
```

It prints a generated password **once**. Sign in at **https://102-204-207-34.sslip.io** and check that `/api/health` answers `{"status":"ok"}`.

## Updating

- **Redeploy:** the server deploys the **`deployment`** branch, never `develop` directly. To ship, open a PR from `develop` into `deployment` (CI runs on it) and merge it. Dokploy then redeploys if **Auto deploy** is on for both applications; otherwise use the **Deploy** button. Migrations run by themselves.
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
