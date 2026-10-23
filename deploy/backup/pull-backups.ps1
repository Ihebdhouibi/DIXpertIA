# Pull the DI Xpertia database backups from the server to this machine (#171).
#
# Run by a scheduled task (README.md, step 4). By hand:
#   powershell -ExecutionPolicy Bypass -File pull-backups.ps1
#
# Uses the dedicated backup key, which the server lets do one thing: download
# from /var/backups/dixpertia, read-only. The files are encrypted with your age
# key; nothing here can read them without it. Keeps 90 days locally.
param(
    [string]$Server = "102.204.207.34",
    [string]$Destination = "$HOME\DIXpertIA-backups",
    [string]$Key = "$HOME\.ssh\dixpertia_backup",
    [int]$KeepDays = 90
)
$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force $Destination | Out-Null
$log = Join-Path $Destination "pull.log"

function Write-Log([string]$message) {
    "$(Get-Date -Format s)  $message" | Add-Content -Path $log
}

try {
    # Only new files: scp would re-download everything, so ask for the list first.
    $listing = "ls -1" | sftp -q -b - -i $Key -o BatchMode=yes "dixbackup@${Server}" 2>&1
    if ($LASTEXITCODE -ne 0) { throw "listing failed: $listing" }
    $remote = $listing | Where-Object { $_ -match '^dixpertia-.*\.age$' }
    $new = $remote | Where-Object { -not (Test-Path (Join-Path $Destination $_)) }
    foreach ($file in $new) {
        scp -q -i $Key -o BatchMode=yes "dixbackup@${Server}:$file" (Join-Path $Destination $file)
        if ($LASTEXITCODE -ne 0) { throw "download of $file failed" }
    }
    scp -q -i $Key -o BatchMode=yes "dixbackup@${Server}:LAST_SUCCESS" (Join-Path $Destination "LAST_SUCCESS")

    Get-ChildItem $Destination -Filter "dixpertia-*.age" |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$KeepDays) } |
        Remove-Item
    Write-Log "ok: $($new.Count) new file(s); server's last backup $(Get-Content (Join-Path $Destination 'LAST_SUCCESS'))"
}
catch {
    Write-Log "FAILED: $_"
    throw
}
