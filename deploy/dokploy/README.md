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
  - E-mail (#186), through Oxahost's mail server, which hands mail to MailChannels. The domain's SPF, DKIM and DMARC records must be in place (they are for dixpertia.tn; see *E-mail DNS records* below), or Gmail refuses or bins the mail:
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

There is no admin yet to send an invitation, so create the first one directly in the API container:

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
5. **E-mail:** the SMTP lines of step 6, with `SMTP_FROM=DI Xpertia (staging) <contact@dixpertia.tn>`. Staging only e-mails the team, and its links lead to staging only, because of its `FRONTEND_URL`. If the mailbox password changes, follow *Rotating the mailbox password* below: it is used in `api`, `api-staging` and the alerts.
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

## Rotating the mailbox password (#186)

The app sends its e-mail as `contact@dixpertia.tn`, and that mailbox's password is used in several places. When it changes, update **every** place on the same day, or that place stops sending without anyone noticing.

**When:**
- on every departure of someone who knew the password or had access to Dokploy or the server;
- at once if it may have leaked (pasted in a chat, a ticket, a screenshot, a commit);
- otherwise once a year.

**Where the password is used:**

| Where | What uses it |
|---|---|
| Oxahost, the mailbox itself | the source of truth: change it here first |
| Dokploy, application `api`, Environment, `SMTP_PASSWORD` | production's e-mails |
| Dokploy, application `api-staging`, Environment, `SMTP_PASSWORD` | staging's e-mails |
| Dokploy, **Settings → Notifications**, the Email notification | failed build and deploy alerts |
| Server, `/etc/dixpertia/monitoring.env` | the server checks' alerts (`deploy/monitoring/`) |
| Your password manager | the only copy kept by a person |

UptimeRobot only sends alerts to `contact@dixpertia.tn`, so it keeps working. Its own sign-in password is separate: change it too when someone who knew it leaves.

**How (about 15 minutes, at a quiet time).** The app sends each e-mail once and does not retry. Between the change at Oxahost and the redeploys, an invitation or a reset link would be lost: keep that window short.

1. Generate a new password in the password manager (long, random, unique), and save it there as the new entry.
2. **Oxahost:** change the password of `contact@dixpertia.tn`. Check that webmail accepts the new one.
3. **Dokploy, `api`:** set `SMTP_PASSWORD` to the new password, save, then **Deploy**. Do the same for **`api-staging`**. Without the redeploy, the running container keeps the old password.
4. **Dokploy, Settings → Notifications:** edit the Email notification, set the new password, click **Test**.
5. **Server**, over SSH:
   ```bash
   sudo nano /etc/dixpertia/monitoring.env                  # replace the password, keep the quotes
   sudo bash /opt/dixpertia/deploy/monitoring/install.sh    # ends with a test mail
   ```
   The test mail, titled `[DIXpertIA] ... TEST - install of #188, ignore`, arrives within a minute.
6. **Verify the app**, on production and on staging:
   - As an admin, invite a test user at your own address. The activation e-mail arrives, in the inbox and not in spam. Then deactivate the test user.
   - The API's log has no `Email error` line: Dokploy, `api` (then `api-staging`), **Logs**.
7. If someone was invited during the window, use **Resend activation link** on the Users screen. Someone who asked for a password reset then just asks again.

Never write the password in a ticket, a commit, a chat or a screenshot. The password manager is the only place it is written down.

**Known weakness.** The app sends with the team's own `contact@` mailbox, because the plan has one mailbox. A dedicated `no-reply@dixpertia.tn` account, used by the app only, would let us change the app's password without touching anyone's mailbox, and would keep replies out of the app's way. Worth creating if the plan allows a second mailbox (#259).

## E-mail DNS records (#186)

Without these records in the `dixpertia.tn` zone, Gmail refuses our mail or puts it in spam, and anyone can send mail that claims to come from us. The zone is managed outside this repository; this is the reference of what it must contain.

| Record | Type | Value | Purpose |
|---|---|---|---|
| `dixpertia.tn` | MX | `mailpro2.tn.oxa.host` | where mail to `@dixpertia.tn` is delivered |
| `dixpertia.tn` | TXT | `v=spf1 a:mailpro2.tn.oxa.host include:relay.mailchannels.net ~all` | **SPF:** the servers allowed to send as us. Oxahost hands outbound mail to MailChannels, hence the `include` |
| `default._domainkey.dixpertia.tn` | TXT | the public key, provided by Oxahost | **DKIM:** the signature that proves a message is ours and unchanged |
| `_dmarc.dixpertia.tn` | TXT | `v=DMARC1; p=quarantine; rua=mailto:contact@dixpertia.tn` | **DMARC:** mail that claims to be from us but fails both SPF and DKIM goes to spam; receivers send a daily report to `contact@` |
| `_mailchannels.dixpertia.tn` | TXT | `v=mc1 auth=<Oxahost's MailChannels account id>` | **Domain Lockdown, not set yet:** only Oxahost's MailChannels account may send as us. Without it, any MailChannels customer passes our SPF |

**DMARC policy.**
- `p=none` from October 2026 to November 2026, while the reports were collected.
- `p=quarantine` once the reports for 10–20 November showed all of our mail passing (38 of 38 messages).
- Do not move to `p=reject` while DKIM fails on part of our mail (#261): a forwarded message, which fails SPF by design, would then be refused instead of filed as spam.

**Before any change to these records, read the DMARC reports.**
1. Download the report attachments that arrived at `contact@` (`.zip` or `.gz`, from Gmail and others) into `dmarc-reports/` at the root of the repository. It is git-ignored: the reports name the servers that sent our mail.
2. Run `python scripts/dmarc_report.py dmarc-reports`. It lists each sending server with its DMARC, DKIM and SPF results, and DKIM per day. Its exit status is 1 if any message sent as `dixpertia.tn` failed DMARC.
3. Every sender should be MailChannels (`23.83.208.0/20` so far) passing DMARC. An unknown server that fails is either someone impersonating us, which is what the policy is for, or a service of ours that is not set up yet. Find out which before tightening the policy.

**The Domain Lockdown record.** Ask Oxahost support for "the MailChannels account id (`auth=`) for the Domain Lockdown record". A wrong id makes MailChannels refuse **all** our mail, so send yourself an invitation right after adding it, and remove the record if it does not arrive.

**After any change**, invite a test user at your own address from production. The activation e-mail must arrive in the inbox, not in spam. To undo a DMARC change, set its previous `p=` value again.

## Decisions

- **PostgreSQL on the host, reached through `docker_gwbridge` (172.18.0.1).** Three layers keep it closed:
  - `pg_hba.conf` admits only the two application roles, only from that bridge;
  - ufw allows 5432 on that interface only;
  - PostgreSQL starts after Docker, so the bridge address exists when it binds.
- **The installer is pinned and checksummed.** `curl … | sh` of a moving `install.sh` would run whatever is on the server that day, as root. A new Dokploy version is a reviewed change to this folder.
- **Only Traefik publishes ports.** Docker bypasses ufw, so `verify.sh` checks what is really published rather than trusting the firewall.
