# What to do when (#188)

**What this page covers:** short procedures for each alert. Every command runs on the server, connected over SSH as `dixadmin`: `ssh dixadmin@102.204.207.34`.

**Before anything:**
- Note the time you started. Every incident gets a short note: what happened, when, what you did. NIS2 expects that trace.
- **Personal data:** if personal data may have leaked or been lost (a stolen account, a database exposed, a backup gone), the CNIL must be told **within 72 hours**. In Tunisia, the INPDP must be told as well. Tell Iheb at once.

---

## The site is down

UptimeRobot says "down", or the `Health` or `Containers` checks alert.

1. **Is it only you?** Open https://dixpertia.tn on your phone's mobile data. If it opens there, the problem is on your network, not on the server.
2. **Is the server alive?** Run `ssh dixadmin@102.204.207.34`.
   - If SSH does not answer either, the VPS itself is down. Open the **Oxahost** client area, check the server's status, and use **Reboot** there. If it does not come back, open an Oxahost ticket.
3. **Are the apps running?** In Dokploy, open `api` and `web`.
   - An app that is not **Running**: open **Deployments**, read the last log, then click **Deploy** again.
   - A first look from the server:

   ```bash
   sudo docker ps --format '{{.Names}}  {{.Status}}' | grep dixpertia
   sudo docker logs --tail 100 $(sudo docker ps -q -f name=dixpertia-api- | head -1)
   ```

4. **The API is up, but health answers `unavailable`.** The database does not answer: see *The database is down* below.
5. **It broke right after a deploy.** Go back to the previous version. In Dokploy, open `api` (or `web`), then **Deployments**. On the last version that worked, click **Rollback**, if this Dokploy version offers it. Otherwise:
   1. Revert the faulty merge on `main`: `git revert -m 1 <merge commit>`, through a PR.
   2. Click **Deploy** again.

## The disk is full

The `Disk` check alerts at 80%.

```bash
df -h /                                              # how full
sudo du -xh --max-depth=1 / 2>/dev/null | sort -h | tail   # which folder
sudo docker system df                                # what Docker holds
```

**Usual causes, from the most likely:**

1. **Old Docker images** from earlier deploys. Running containers are not touched:

   ```bash
   sudo docker image prune -a --filter "until=168h"
   ```

   Dokploy also has **Settings → Server → Docker cleanup**.
2. **Logs**:
   - `sudo journalctl --disk-usage`. To shrink: `sudo journalctl --vacuum-size=500M`.
   - The Docker logs are capped only after the reboot and the redeploy of README.md, step 5. If they have not happened yet, do them now.
3. **Backups**: `sudo du -sh /var/backups/dixpertia`. Retention keeps 7 daily and 4 weekly. Never delete them by hand without checking that the off-server copy (#171) has them.
4. **PostgreSQL**: `sudo du -sh /var/lib/postgresql/17/*`.

**Never delete** anything in `/var/lib/postgresql` or `/var/lib/docker/volumes` by hand.

**If it keeps filling:** the VPS needs a bigger disk. Upgrade it in the Oxahost client area.

## The database is down

`PostgreSQL: the cluster on port 5432 does not answer`, or health answers `unavailable`.

```bash
sudo systemctl status postgresql@17-main --no-pager      # production (staging: 17-staging)
sudo journalctl -u postgresql@17-main -n 50 --no-pager
sudo tail -50 /var/log/postgresql/postgresql-17-main.log
```

**Common causes:**
- **Disk full:** PostgreSQL stops writing. See *The disk is full* above, then run `sudo systemctl start postgresql@17-main`.
- **Started before Docker** after a reboot, so the `172.18.0.1` address did not exist yet. This was fixed in #172, but if it shows up again: `sudo systemctl restart postgresql@17-main`.
- **Out of memory:** look for `Killed process` in the output of `sudo journalctl -k | grep -i oom`.

When it is back, check that https://dixpertia.tn/api/health answers `{"status":"ok"}`.

**Data looks wrong or is lost:** stop and do not "fix" anything in the database. Restore from the backup, following deploy/backup/README.md: restore to a **copy** first, then compare.

## A certificate is about to expire

`Certificate: dixpertia.tn expires in N days`. Let's Encrypt renews certificates at 30 days left, so this alert means renewal has been failing for two weeks.

1. In Dokploy, open the app, then **Domains**. Check that the domain is still there, with **HTTPS** on and **Let's Encrypt** selected.
2. Read Traefik's log for the reason:

   ```bash
   sudo docker logs --tail 200 dokploy-traefik 2>&1 | grep -iE "acme|certificate|error" | tail -20
   ```

   **Usual causes:**
   - The DNS record no longer points to `102.204.207.34`. Check with `nslookup dixpertia.tn`.
   - Port 80 is blocked. It must stay open in ufw for the Let's Encrypt challenge.
   - Let's Encrypt's rate limit after many retries: wait one hour.
3. Remove the domain and add it again in Dokploy, which requests a new certificate.

## The backup failed

`Backup: the last successful backup is N hours old`, or `the last run failed`.

```bash
sudo journalctl -u dixpertia-backup -n 50 --no-pager
sudo /usr/local/sbin/dixpertia-backup        # try again now
```

**Usual causes:**
- The disk is full.
- PostgreSQL is down.
- `/etc/dixpertia/backup-recipient.txt` is missing.

Once it works again, tell the backup holder (#171) to check that her machine pulled the new file.

## Bursts of 429 or 401: someone is trying passwords

`Security: N refused sign-ins (401) ... Top: 203.0.113.9 (41)`

1. **Is it us?** Someone on the team mistyping a password, or a test script. The address of our office or of a team member's connection is not an attack. Ask in the team chat.
2. **Otherwise it is an attack, and the account lock (#220) is already slowing it down.** If it goes on, block the address at the firewall:

   ```bash
   sudo ufw insert 1 deny from 203.0.113.9 comment "#188 brute force $(date +%F)"
   sudo ufw status numbered        # to remove it later: sudo ufw delete <number>
   ```

   Traefik runs in Docker, which can bypass ufw for published ports. If the address still gets through, block it in Traefik instead: in Dokploy, **Settings → Traefik**, with an IP deny middleware. Then remove the block after a few days.
3. **One account targeted many times** (in the audit trail, many failures for one e-mail): tell its owner. Make sure they have two-factor authentication on (#44).
4. **An account was actually taken over:**
   1. In **Users**, deactivate it. That closes all its sessions.
   2. Reset its password and its two-factor authentication.
   3. Read its actions in the audit trail.
   4. Then the 72-hour rule at the top of this page applies.

## Bursts of 5xx: the application is failing

```bash
sudo docker logs --since 15m $(sudo docker ps -q -f name=dixpertia-api- | head -1) 2>&1 | grep -B2 -A20 Traceback | tail -60
```

- It started after a deploy: roll back, as in *The site is down*, step 5.
- It points to the database: see *The database is down*.
- Otherwise: open an issue with the traceback. Remove any personal data from it first.

## Memory is low

```bash
free -h
sudo docker stats --no-stream
```

A container that keeps growing is a leak: restart it in Dokploy, then open an issue. If memory is always short, upgrade the VPS in Oxahost.

## After an incident

**Close the incident:**
- Write a short note: what happened, when, how long it lasted, the cause, and what was done. Put it in the issue tracker, label `security` if it was one.
- **Delete** the alert mails that contain IP addresses once the note is written (GDPR).

**If an alert was only noise:** raise its threshold in `/etc/dixpertia/monitoring.env`. Say so in the note.
