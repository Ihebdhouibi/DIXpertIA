# Hardening the production server (#172)

The VPS (Oxahost, Ubuntu 24.04, 4 cores, 7.8 GB RAM) starts out reachable as **root with a password** on port 22, the first thing internet scanners try. These steps give it an admin user who signs in with an SSH key, then turn passwords and root login off, put a firewall in front, and keep it patched. **Do this before installing Dokploy (#183).**

| File | What it does |
|---|---|
| `01-admin-user.sh` | Creates the admin user `dixadmin`, with sudo and your SSH public key. |
| `02-baseline.sh` | Updates, automatic security updates, Tunisian time, 2 GB of swap, the firewall (22, 80, 443) and fail2ban on SSH. |
| `03-ssh-lockdown.sh` + `sshd-dixpertia.conf` | SSH with keys only, no root, only `dixadmin`. **Refuses to run** unless your session proves key login as `dixadmin` works. |
| `verify.sh` | Checks all of the above and prints the server's host key fingerprints. |

Every script is safe to run again. Nothing secret is in this folder: your **private key never leaves your laptop**, and no password goes in the repository, in a chat or in a ticket.

## 0. On your laptop: create your SSH key (once)

In PowerShell:

```powershell
ssh-keygen -t ed25519 -f $HOME\.ssh\dixpertia_vps -C "iheb@dixpertia-vps"
```

Give it a passphrase when asked. This creates two files:
- `dixpertia_vps` is the **private** key. It stays on your laptop: never copy it, never send it.
- `dixpertia_vps.pub` is the **public** key, the one the server gets.

## 1. Copy the scripts and your public key to the server

Still in PowerShell, from the repository folder. Root's password still works at this point:

```powershell
scp -r deploy/server root@<server-ip>:/root/server-setup
scp $HOME\.ssh\dixpertia_vps.pub root@<server-ip>:/root/admin_key.pub
```

When `scp` asks for the password, **nothing appears as you type**, not even dots. That is normal: type it and press Enter.

If `scp` still fails, use the Oxahost web console for the key:
1. Run `Get-Content $HOME\.ssh\dixpertia_vps.pub` in PowerShell, and copy the single line it prints. It starts with `ssh-ed25519`.
2. In the console, type `nano /root/admin_key.pub`, paste the line, then save with Ctrl+O, Enter and Ctrl+X.

## 2. As root: the admin user and the baseline

```bash
ssh root@<server-ip>
bash /root/server-setup/01-admin-user.sh /root/admin_key.pub   # asks you to set dixadmin's sudo password
bash /root/server-setup/02-baseline.sh
```

Keep a password manager entry for `dixadmin`'s sudo password. SSH no longer uses passwords, but `sudo` does.

## 3. As dixadmin, with your key: lock SSH down

**Keep the root session open.** In a **new** PowerShell window:

```powershell
ssh -i $HOME\.ssh\dixpertia_vps dixadmin@<server-ip>
```

Then, on the server, in that `dixadmin` session:

```bash
sudo cp -r /root/server-setup ~/server-setup && sudo chown -R dixadmin: ~/server-setup
sudo bash ~/server-setup/03-ssh-lockdown.sh
```

Then open **a third window** and check:

```powershell
ssh -i $HOME\.ssh\dixpertia_vps dixadmin@<server-ip>   # must work
ssh root@<server-ip>                                    # must be refused
```

Only once the first command works, close the old sessions.

If the new login fails, nothing is lost: in the session that is still open, run
`sudo rm /etc/ssh/sshd_config.d/01-dixpertia.conf && sudo systemctl reload ssh`.
That puts SSH back as it was.

To shorten the command on your laptop, add this to `$HOME\.ssh\config`:

```
Host dixpertia
    HostName <server-ip>
    User dixadmin
    IdentityFile ~/.ssh/dixpertia_vps
```

Then `ssh dixpertia` is enough.

## 4. Verify

```bash
sudo bash ~/server-setup/verify.sh     # every line should read "ok"
```

It ends with the server's **SSH host key fingerprints**. Copy them into the table below in a PR. They are public, not secret. The first time anyone connects, SSH asks "Are you sure you want to continue connecting?" and shows a fingerprint. It must match this table; if it does not, answer **no** and say so.

| Key | Fingerprint (SHA256) |
|---|---|
| ED25519 | `SHA256:uB5PWyEkXq2k4gm3+AgkiveJq+3tIJT6OjGeyk0fLY8` |
| ECDSA | `SHA256:sWVYxYe7XWSit/2QN8+dM/ZQT9bcP4ioa3G2fxNOzvA` |
| RSA (3072) | `SHA256:calKChrAovJVkCBV6cp0ax1CZ+zVhW+61kRVTmW++WA` |

## Decisions

- **One admin user, keys only.** `AllowUsers dixadmin`: no other account can sign in over SSH, even one created by a package later.
- **The config file is called `01-dixpertia.conf`.** sshd keeps the first value it reads, and Ubuntu cloud images ship `50-cloud-init.conf` with `PasswordAuthentication yes`. A higher number would be silently overridden.
- **Port 22 stays.** Moving SSH elsewhere only hides it from the laziest scanners. Keys-only, `ufw limit` and fail2ban do the real work.
- **Security updates install by themselves, but the server never reboots by itself.** `verify.sh` says when a reboot is due; reboot at a quiet time.
- **Docker bypasses ufw.** Once Dokploy runs (#183), a port a container publishes is open whatever ufw says. Only Traefik may publish ports (80, 443). `verify.sh` lists what really listens on public addresses, so this can be checked.
- **2 GB of swap, `swappiness` 10:** a cushion for image builds (#184), not working memory.

## Undoing

| To undo | Run |
|---|---|
| SSH lockdown | `sudo rm /etc/ssh/sshd_config.d/01-dixpertia.conf && sudo systemctl reload ssh` |
| Firewall | `sudo ufw disable` |
| fail2ban | `sudo rm /etc/fail2ban/jail.d/dixpertia.local && sudo systemctl restart fail2ban` |
| Root password lock | `sudo passwd -u root` |

Don't undo the lockdown unless you have to; the server is then exposed again.
