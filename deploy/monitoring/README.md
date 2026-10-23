# Monitoring and alerts (#188)

Goal: we know that production is down, full or failing **before a user tells us**.

There are three layers, because no single one sees everything:

| Layer | Sees | Why it is needed |
|---|---|---|
| **1. An outside uptime service** | the site and the API do not answer from the Internet | a server that is down, or cut off, cannot send its own alert |
| **2. Dokploy's notifications** | a build or deploy failed, Dokploy restarted | Dokploy knows its own deploys best |
| **3. `dixpertia-check` on the server**, every 5 min | disk, memory, databases, backup, certificates, containers, bursts of 429/401/5xx | what the outside cannot see, and the early warnings |

Alerts go to **contact@dixpertia.tn**. Each problem is mailed **once** when it starts, again every **12 h** while it lasts, and once more when it is **resolved**. A quiet server sends nothing.

What to do when an alert arrives: **[RUNBOOK.md](RUNBOOK.md)**.

---

## 1. Outside uptime check (5 minutes, in a browser)

We use **UptimeRobot**'s free plan: 50 monitors, a check every 5 minutes, and e-mail alerts. It only ever sees the public addresses, never any data. Better Stack's free plan does the same, if you prefer it.

1. Create an account at https://uptimerobot.com with **contact@dixpertia.tn**, and use a strong password. Turn on its two-factor authentication.
2. **+ New monitor** for the API:
   - Type: **Keyword** if the plan offers it, otherwise **HTTP(s)**.
   - URL: `https://dixpertia.tn/api/health`.
   - For a Keyword monitor, keyword `"ok"`, alerting when the keyword is **missing**. This catches the API answering, but without its database (`"unavailable"`, 503).
   - Interval: **5 minutes**.
   - Alert contact: contact@dixpertia.tn.
3. **+ New monitor** for the site: type **HTTP(s)**, URL `https://dixpertia.tn`, every 5 minutes.
4. Add `https://dixpertia.com` once that domain points to the server.
5. Check that it works: in Dokploy, **Stop** the `web` app for 10 minutes at a quiet time. A "down" mail should arrive, then an "up" mail after you **Start** it again.

Do not monitor staging from outside: it is behind a password, and it is allowed to be down.

## 2. Dokploy notifications (in Dokploy)

1. Go to **Settings → Notifications → Add notification**, and pick **Email**.
2. Fill in the SMTP settings:
   - Server `mailpro2.tn.oxa.host`, port `465`.
   - User `contact@dixpertia.tn`, and that mailbox's password.
   - From address and to address: both `contact@dixpertia.tn`.
3. Tick **App Build Error** and **Dokploy Restart**, plus **App Deploy** if you also want a mail for every successful deploy.
4. Click **Test**, then **Create**.

The exact names can differ between Dokploy versions. Whatever they are called, the events that matter are the **failed build** and the **failed deploy**.

## 3. The server checks (about 5 minutes, over SSH)

Connect as `dixadmin`, then:

```bash
sudo git -C /opt/dixpertia pull --ff-only
sudo bash /opt/dixpertia/deploy/monitoring/install.sh
```

The first run creates **`/etc/dixpertia/monitoring.env`** and stops. That file is readable by root only (0600), because it holds the mailbox password.

1. Put the password in it:

   ```bash
   sudo nano /etc/dixpertia/monitoring.env
   ```

   Replace `__CONTACT_MAILBOX_PASSWORD__` with the password of contact@dixpertia.tn, keeping the quotes. Save with **Ctrl+O**, **Enter**, then quit with **Ctrl+X**.

2. Run the installer again:

   ```bash
   sudo bash /opt/dixpertia/deploy/monitoring/install.sh
   ```

It prints `ok` lines, then a first run of the checks.

- A line starting with `PROBLEM` is a real finding: see [RUNBOOK.md](RUNBOOK.md).
- Finally it sends a **test mail** titled `[DIXpertIA] ... TEST - install of #188, ignore`, which should arrive within a minute.

If the test mail does not come:
- check the password in the file;
- check the spam folder;
- run `sudo /usr/local/sbin/dixpertia-check` and read its last line.

When the contact@ password changes (the rotation in #186), update it in this file too, as well as in Dokploy and in UptimeRobot's account.

## 4. Check it runs

```bash
systemctl list-timers dixpertia-check.timer      # the next run, within 5 minutes
sudo /usr/local/sbin/dixpertia-check             # "ok    all checks passed", or the problems
journalctl -u dixpertia-check -n 20 --no-pager   # what the last runs said
```

## 5. One reboot, for the log limits

Until now, Docker kept every container's output **without limit**, so the disk would have filled up in the end. The installer caps it at **5 files of 20 MB per container**. The cap applies only once Docker has restarted and the apps have been recreated.

At a quiet time, run:

```bash
sudo reboot
```

The site is down for about 1 to 2 minutes. After the reboot, check that all four apps are **Running** in Dokploy, and that https://dixpertia.tn opens. A reboot rather than `systemctl restart docker` keeps the start order of PostgreSQL after Docker (#172), which a Docker restart alone could break.

## What is checked, and when it alerts

All the thresholds are in `/etc/dixpertia/monitoring.env`. After changing one, nothing needs restarting: the next run reads the file.

| Check | Alerts when | Setting |
|---|---|---|
| Disk | `/` is at least 80% full | `DISK_MAX_PERCENT` |
| Memory | under 10% available | `MEM_MIN_PERCENT` |
| PostgreSQL | production (5432) or staging (5433) does not answer | `PG_PORTS` |
| Backup (#171) | last success more than 26 h ago, or the last run failed. Not watched until the backup is installed. | `BACKUP_MAX_AGE_HOURS` |
| Certificates | under 14 days left. Let's Encrypt renews at 30, so this means renewal is failing. | `CERT_HOSTS`, `CERT_MIN_DAYS` |
| Health, from the server | `https://dixpertia.tn/api/health` is not `ok` | `HEALTH_URLS` |
| Containers | no running `dixpertia-api-*` or `dixpertia-web-*` | `CONTAINERS` |
| Rate limits (#175) | over 30 answers of 429 in 5 minutes, from production's API | `MAX_429` |
| Refused sign-ins | over 40 answers of 401 in 5 minutes | `MAX_401` |
| Server errors | over 10 answers of 5xx in 5 minutes | `MAX_5XX` |

For 429 and 401 bursts, the mail names the **three busiest IP addresses**, so that they can be blocked (RUNBOOK.md).

## Personal data and logs (GDPR)

- The API's access log, and so the alert mails about bursts, contain **IP addresses**, which are personal data. The mails stay in the company mailbox. Delete them once the incident is closed.
- **Docker logs** are capped at 5 x 20 MB per container. On a quiet site, that is a few weeks of history; on a busy one, less.
- **journald** (the system logs, SSH logins included) is capped at **1 GB and 90 days**. Both values are **provisional** until the retention decision (#187) sets them.
- **No secrets in the logs** remains the rule in the code: no passwords, no tokens, no codes.
- The checks keep **no history of their own**: `/var/lib/dixpertia-monitor` holds only the problems still open.

## Security notes

- `dixpertia-check` runs as root, because it needs Docker and the backup folder. It is installed root-owned, mode 0750.
- The **SMTP password is passed to curl on standard input**, never on the command line, where any user could read it in the process list. CI checks this.
- Mail is sent over **TLS only** (`--ssl-reqd`, port 465).
- **Least privilege, not reached yet.** The checks use the contact@ mailbox itself, because the plan has only one. A separate `alerts@` mailbox, with its own password, would be better. It is worth creating if the plan ever allows a second mailbox.
- CI tests every check against made-up problems, as well as the once, reminder and resolved logic: `ci-check.sh`, in the **server hardening config** job.
