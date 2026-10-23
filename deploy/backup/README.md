# Database backups (#171)

The production database is backed up every night on the server, **encrypted with your public key**, and pulled to your own machine. If the VPS disk dies, the latest backup plus your private key rebuild everything.

| Where | What |
|---|---|
| **Server**, `/var/backups/dixpertia` | `pg_dump` of `dixpertia` plus the roles, at **02:30**. The **last 7 daily and 4 weekly** backups are kept. Encrypted with [age](https://age-encryption.org): the server holds only the public key, so it **cannot read its own backups**. |
| **Your machine**, `%USERPROFILE%\DIXpertIA-backups` | Pulled every day by a scheduled task, kept **90 days**. Still encrypted. |
| **Your password manager** | The age **private** key. Without it, no backup can be restored. Keep a second copy somewhere safe, offline. |

The backups contain payroll and personal data (GDPR). They are encrypted end to end, and the folder on your machine should be on a **BitLocker**-encrypted drive. If the machine is an employer's, use a personal one or an external drive.

Only production is backed up. Staging holds invented data.

---

## 1. On your machine: two keys (once) [PowerShell]

**The encryption key (age):**
```powershell
winget install --id FiloSottile.age -e
age-keygen -o $HOME\.dixpertia-backup-age.key
```
`age-keygen` prints `Public key: age1…`; copy that line for step 2. The file `.dixpertia-backup-age.key` holds the **private** key (`AGE-SECRET-KEY-…`):
- copy its content into your password manager now;
- never put it on the server, in the repository or in a chat.

**The download key (SSH)**, without a passphrase, so the scheduled task can use it unattended. The server only lets it download the backups:
```powershell
ssh-keygen -t ed25519 -N '""' -f $HOME\.ssh\dixpertia_backup -C "dixpertia-backup-pull"
Get-Content $HOME\.ssh\dixpertia_backup.pub
```

## 2. On the server: install [SSH as dixadmin]
```bash
sudo git -C /opt/dixpertia pull --ff-only
sudo bash /opt/dixpertia/deploy/backup/install.sh '<age1… public key>' '<ssh-ed25519 … backup public key>'
```
Both arguments are **public** keys. The script:
- installs age;
- creates the **read-only `dixbackup` account**, which may only download from the backup folder;
- adds it to SSH's allowed users;
- turns on the nightly timer;
- makes a first backup. It ends with `backup ok: dixpertia-daily-….dump.age`.

## 3. Pull once by hand [PowerShell]
```powershell
powershell -ExecutionPolicy Bypass -File D:\Projects\DIXpertIA\deploy\backup\pull-backups.ps1
Get-ChildItem $HOME\DIXpertIA-backups
```
The first time, SSH asks you to confirm the server's key. Check it is the ED25519 fingerprint in `deploy/server/README.md`, then type `yes`.

## 4. Pull every day [PowerShell, as yourself]
```powershell
$action  = New-ScheduledTaskAction -Execute "powershell.exe" -Argument '-NoProfile -ExecutionPolicy Bypass -File "D:\Projects\DIXpertIA\deploy\backup\pull-backups.ps1"'
$trigger = New-ScheduledTaskTrigger -Daily -At 9am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries
Register-ScheduledTask -TaskName "DIXpertIA backup pull" -Action $action -Trigger $trigger -Settings $settings
```
**StartWhenAvailable** means that if the machine is off at 9:00, the task runs as soon as it is back on. Each run writes one line to `%USERPROFILE%\DIXpertIA-backups\pull.log`.

## 5. Prove a backup restores (now, then once a month) [PowerShell + Docker Desktop]
A backup that has never been restored is a hope, not a backup. This restores the latest one into a **throwaway** PostgreSQL on your machine, never into production:
```powershell
$latest = Get-ChildItem $HOME\DIXpertIA-backups -Filter "dixpertia-*.dump.age" | Sort-Object Name | Select-Object -Last 1
age --decrypt -i $HOME\.dixpertia-backup-age.key -o "$env:TEMP\restore-test.dump" $latest.FullName
docker run -d --name dixpertia-restore-test -e POSTGRES_PASSWORD=restore-test -v "$env:TEMP\restore-test.dump:/restore.dump:ro" postgres:17
Start-Sleep 10
docker exec dixpertia-restore-test createdb -U postgres dixpertia
docker exec dixpertia-restore-test pg_restore -U postgres -d dixpertia --no-owner --no-acl /restore.dump
docker exec dixpertia-restore-test psql -U postgres -d dixpertia -c "SELECT count(*) AS users FROM users; SELECT count(*) AS invoices FROM invoices;"
docker rm -f dixpertia-restore-test; Remove-Item "$env:TEMP\restore-test.dump"
```
The counts must match what the app shows. The decrypted dump is plain personal data, so the last line deletes it.

## Restoring production (disaster only)
1. Decrypt the dump and the roles file as in step 5.
2. On the new server, apply the roles with `psql -f roles.sql`.
3. Restore with `pg_restore -d dixpertia` as the owner role.

Ask before doing this: it replaces the live data.

## Checks
```bash
systemctl list-timers dixpertia-backup.timer           # next run
journalctl -u dixpertia-backup --since "2 days ago"     # last runs
cat /var/backups/dixpertia/LAST_SUCCESS                  # must be from the last night
```
An alert when a backup fails, or when `LAST_SUCCESS` is older than a day, is part of monitoring (#188).
