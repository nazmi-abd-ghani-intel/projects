param(
    [ValidateSet('Outlook', 'Graph')]
    [string]$Method = 'Outlook',

    [string]$OutlookFolderPath = '\\nazmi.abd.ghani@intel.com\DDG\iSEED',

    # Graph API only: Azure AD app registration (public client) used for device-code sign-in.
    [string]$GraphClientId,
    [string]$GraphTenantId = 'common',

    [string]$SnapshotDirectory = (Join-Path $PSScriptRoot 'Input\Snapshots'),
    [string]$DashboardPath = (Join-Path $PSScriptRoot 'inventory-dashboard.html'),
    [switch]$OpenDashboard = $true,

    # --- Unattended/cron hardening ---
    # Forces $OpenDashboard=$false and suppresses any interactive prompts (e.g. Graph
    # device-code browser launch). Use this for scheduled task / cron invocations.
    [switch]$Unattended,

    # Safety floor: if the newly parsed snapshot records fall below this count, the
    # dashboard is NOT overwritten (protects against a mail outage or empty snapshot
    # folder silently wiping out a working dashboard).
    [int]$MinExpectedRecords = 1000,

    # Safety ratio: if the new record count is below this fraction of the previously
    # embedded record count, treat it as a suspicious partial pull and abort instead of
    # overwriting the dashboard.
    [double]$MinRecordRetentionRatio = 0.5,

    # Number of timestamped dashboard backups to retain in Backups\.
    [int]$BackupRetentionCount = 10,

    # Attachment-collection retry policy (covers transient Outlook COM / network errors).
    [int]$RetryCount = 3,
    [int]$RetryDelaySeconds = 15,

    # Hard wall-clock ceiling (seconds) for the Outlook COM attachment-collection step.
    # Outlook COM calls can hang indefinitely (bad folder path, dead profile, network
    # share unavailable) with no exception ever raised — this guarantees the run fails
    # fast instead of blocking a cron slot forever.
    [int]$OutlookTimeoutSeconds = 180,

    # How long snapshot .txt files are kept in $SnapshotDirectory before automatic
    # cleanup. Only ever deletes files strictly older than this, and only after a
    # successful refresh, so a slow mail trickle never loses same-day data.
    [int]$SnapshotRetentionDays = 60,

    [string]$LogPath = (Join-Path $PSScriptRoot 'Logs\refresh-inventory-dashboard.log'),
    [int]$LogMaxSizeMB = 5,
    [int]$LogRetentionCount = 5,

    [string]$HeartbeatPath = (Join-Path $PSScriptRoot 'Logs\last-run-status.json'),

    # Best-effort failure notification (Outlook method only). Left blank = disabled.
    [string]$AlertRecipient,

    # Prevents two overlapping runs (e.g. a slow run still going when the next cron
    # tick fires) from racing each other against the same dashboard/snapshot folder.
    [string]$LockPath = (Join-Path $PSScriptRoot 'Logs\refresh.lock'),
    [int]$LockStaleMinutes = 240
)

$ErrorActionPreference = 'Stop'

if ($Unattended) {
    # Never pop up a browser/dashboard window when run from a scheduled task.
    $OpenDashboard = $false
}

# ---------------------------------------------------------------------------
# Logging: writes to console AND a persistent, size-capped log file so a
# cron/scheduled-task run that nobody is watching still leaves an auditable
# trail without growing forever.
# ---------------------------------------------------------------------------
function Invoke-LogRotation {
    param([string]$LogPath, [int]$MaxSizeMB, [int]$RetentionCount)

    if (-not (Test-Path -LiteralPath $LogPath)) { return }
    $sizeMB = (Get-Item -LiteralPath $LogPath).Length / 1MB
    if ($sizeMB -lt $MaxSizeMB) { return }

    for ($i = $RetentionCount; $i -ge 1; $i--) {
        $src = if ($i -eq 1) { $LogPath } else { "$LogPath.$($i - 1)" }
        $dst = "$LogPath.$i"
        if (Test-Path -LiteralPath $src) {
            Move-Item -LiteralPath $src -Destination $dst -Force
        }
    }
}

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet('INFO', 'WARN', 'ERROR')]
        [string]$Level = 'INFO'
    )
    $line = "[{0}] [{1}] {2}" -f (Get-Date -Format 's'), $Level, $Message
    Write-Output $line
    try {
        $logDir = Split-Path -Parent $LogPath
        if ($logDir -and -not (Test-Path -LiteralPath $logDir)) {
            New-Item -ItemType Directory -Force -Path $logDir | Out-Null
        }
        Invoke-LogRotation -LogPath $LogPath -MaxSizeMB $LogMaxSizeMB -RetentionCount $LogRetentionCount
        Add-Content -LiteralPath $LogPath -Value $line -Encoding utf8
    } catch {
        # Logging failures must never abort the refresh itself.
        Write-Output "[$(Get-Date -Format 's')] [WARN] Could not write to log file $LogPath : $($_.Exception.Message)"
    }
}

function Write-Heartbeat {
    param(
        [string]$Status,
        [string]$Message,
        [Nullable[int]]$RecordCount = $null
    )
    try {
        $heartbeatDir = Split-Path -Parent $HeartbeatPath
        if ($heartbeatDir -and -not (Test-Path -LiteralPath $heartbeatDir)) {
            New-Item -ItemType Directory -Force -Path $heartbeatDir | Out-Null
        }
        [pscustomobject]@{
            status      = $Status
            message     = $Message
            recordCount = $RecordCount
            timestamp   = (Get-Date).ToString('s')
            method      = $Method
        } | ConvertTo-Json | Set-Content -LiteralPath $HeartbeatPath -Encoding utf8
    } catch {
        Write-Log "Could not write heartbeat file $HeartbeatPath : $($_.Exception.Message)" 'WARN'
    }
}

# ---------------------------------------------------------------------------
# Concurrency guard: refuses to start a second overlapping run (e.g. cron
# firing again while a slow prior run is still in progress). Stale locks
# (from a crashed prior run / dead PID) are auto-reclaimed.
# ---------------------------------------------------------------------------
function Enter-RunLock {
    param([string]$LockPath, [int]$StaleMinutes)

    $lockDir = Split-Path -Parent $LockPath
    if ($lockDir -and -not (Test-Path -LiteralPath $lockDir)) {
        New-Item -ItemType Directory -Force -Path $lockDir | Out-Null
    }

    if (Test-Path -LiteralPath $LockPath) {
        try {
            $existing = Get-Content -LiteralPath $LockPath -Raw | ConvertFrom-Json
            $existingProc = Get-Process -Id $existing.pid -ErrorAction SilentlyContinue
            $ageMinutes = ((Get-Date) - [datetime]$existing.startedAt).TotalMinutes
            if ($existingProc -and $ageMinutes -lt $StaleMinutes) {
                throw "Another refresh is already running (PID $($existing.pid), started $($existing.startedAt)). Aborting to avoid a concurrent write race. If this is stale, delete $LockPath."
            }
            Write-Log "Reclaiming stale lock from PID $($existing.pid) (age $([math]::Round($ageMinutes,1)) min, process running: $([bool]$existingProc))." 'WARN'
        } catch [System.Management.Automation.RuntimeException] {
            throw
        } catch {
            Write-Log "Existing lock file was unreadable/corrupt; reclaiming it: $($_.Exception.Message)" 'WARN'
        }
    }

    [pscustomobject]@{ pid = $PID; startedAt = (Get-Date).ToString('s') } |
        ConvertTo-Json | Set-Content -LiteralPath $LockPath -Encoding utf8
}

function Exit-RunLock {
    param([string]$LockPath)
    Remove-Item -LiteralPath $LockPath -Force -ErrorAction SilentlyContinue
}

function Invoke-WithRetry {
    param(
        [Parameter(Mandatory)][scriptblock]$ScriptBlock,
        [string]$ActionName = 'operation',
        [int]$Attempts = $RetryCount,
        [int]$DelaySeconds = $RetryDelaySeconds
    )
    $attempt = 0
    while ($true) {
        $attempt++
        try {
            return & $ScriptBlock
        } catch {
            if ($attempt -ge $Attempts) {
                Write-Log "$ActionName failed after $attempt attempt(s): $($_.Exception.Message)" 'ERROR'
                throw
            }
            Write-Log "$ActionName failed on attempt $attempt/$Attempts : $($_.Exception.Message). Retrying in $DelaySeconds s..." 'WARN'
            Start-Sleep -Seconds $DelaySeconds
        }
    }
}

function Find-OutlookFolder {
    param([object]$Namespace, [string]$FolderPath)

    foreach ($store in $Namespace.Stores) {
        $stack = New-Object System.Collections.Stack
        $stack.Push($store.GetRootFolder())

        while ($stack.Count -gt 0) {
            $folder = $stack.Pop()
            if ($folder.FolderPath -ieq $FolderPath) {
                return $folder
            }

            foreach ($child in $folder.Folders) {
                $stack.Push($child)
            }
        }
    }

    throw "Outlook folder not found: $FolderPath"
}

function Get-SafeFileName {
    param([string]$Name)
    return $Name -replace '[<>:"/\\|?*]', '_'
}

function Save-AttachmentsViaOutlook {
    param([string]$FolderPath, [string]$SnapshotDirectory)

    # Requires the desktop Outlook client to be installed and signed in on this machine.
    $outlook = New-Object -ComObject Outlook.Application
    $namespace = $outlook.GetNameSpace('MAPI')
    $folder = Find-OutlookFolder -Namespace $namespace -FolderPath $FolderPath

    $savedFiles = @()
    foreach ($item in $folder.Items) {
        if ($item.Class -ne 43 -or $item.Attachments.Count -eq 0) {
            continue
        }

        for ($index = 1; $index -le $item.Attachments.Count; $index++) {
            $attachment = $item.Attachments.Item($index)
            $safeName = Get-SafeFileName $attachment.FileName
            $received = ([datetime]$item.ReceivedTime).ToString('yyyyMMdd-HHmmss')
            $path = Join-Path $SnapshotDirectory "$received-$safeName"
            $attachment.SaveAsFile($path)
            $savedFiles += $path
        }
    }
    return $savedFiles
}

# ---------------------------------------------------------------------------
# Hard-timeout wrapper for Outlook COM collection. Outlook COM calls (e.g.
# against an unreachable/misconfigured folder path) can block indefinitely
# with no exception ever thrown — observed firsthand taking 4+ minutes with
# no sign of returning. Running the call in an isolated background job lets
# us kill it on a wall-clock deadline instead of hanging the whole cron slot.
# ---------------------------------------------------------------------------
function Invoke-OutlookCollectionWithTimeout {
    param([string]$FolderPath, [string]$SnapshotDirectory, [int]$TimeoutSeconds)

    $initScript = [scriptblock]::Create(@"
function Find-OutlookFolder {
$((Get-Item function:Find-OutlookFolder).Definition)
}
function Get-SafeFileName {
$((Get-Item function:Get-SafeFileName).Definition)
}
function Save-AttachmentsViaOutlook {
$((Get-Item function:Save-AttachmentsViaOutlook).Definition)
}
"@)

    $job = Start-Job -InitializationScript $initScript -ScriptBlock {
        param($FolderPath, $SnapshotDirectory)
        Save-AttachmentsViaOutlook -FolderPath $FolderPath -SnapshotDirectory $SnapshotDirectory
    } -ArgumentList $FolderPath, $SnapshotDirectory

    try {
        $completed = Wait-Job -Job $job -Timeout $TimeoutSeconds
        if (-not $completed) {
            Stop-Job -Job $job -ErrorAction SilentlyContinue
            throw "Outlook attachment collection exceeded the $TimeoutSeconds s hard timeout and was aborted (likely a hung/unreachable Outlook COM call)."
        }
        if ($job.State -eq 'Failed') {
            $reason = $job.ChildJobs[0].JobStateInfo.Reason
            throw "Outlook attachment collection failed: $($reason.Message)"
        }
        return @(Receive-Job -Job $job)
    } finally {
        Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
    }
}

function Get-GraphAccessToken {
    param([string]$ClientId, [string]$TenantId)

    if ([string]::IsNullOrWhiteSpace($ClientId)) {
        throw "GraphClientId is required when -Method Graph is used. Register a public-client Azure AD app (Mail.Read delegated permission) and pass its Application (client) ID."
    }

    # Device code flow: no client secret needed, works from any machine with just a browser
    # available somewhere (no Outlook installation required on this machine).
    $deviceCodeUri = "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/devicecode"
    $tokenUri = "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token"
    $scope = 'https://graph.microsoft.com/Mail.Read offline_access'

    $deviceResponse = Invoke-RestMethod -Method Post -Uri $deviceCodeUri -Body @{
        client_id = $ClientId
        scope     = $scope
    }

    Write-Log $deviceResponse.message
    if ($OpenDashboard -and -not $Unattended) {
        try { Start-Process $deviceResponse.verification_uri } catch {}
    }

    $interval = if ($deviceResponse.interval) { [int]$deviceResponse.interval } else { 5 }
    $expiresAt = (Get-Date).AddSeconds([int]$deviceResponse.expires_in)
    while ((Get-Date) -lt $expiresAt) {
        Start-Sleep -Seconds $interval
        try {
            $token = Invoke-RestMethod -Method Post -Uri $tokenUri -Body @{
                grant_type  = 'urn:ietf:params:oauth:grant-type:device_code'
                client_id   = $ClientId
                device_code = $deviceResponse.device_code
            }
            return $token.access_token
        } catch {
            $errBody = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue
            if ($errBody.error -eq 'authorization_pending') { continue }
            throw
        }
    }
    throw 'Device code sign-in timed out before the user completed authentication. Device-code Graph auth is not suitable for unattended/cron runs without a pre-cached refresh token.'
}

function Find-GraphFolderId {
    param([string]$AccessToken, [string]$FolderPath)

    # FolderPath uses the same '\Store\Parent\Child' convention as Outlook COM; we walk it
    # segment by segment through Graph's mailFolders (and childFolders) endpoints.
    $segments = $FolderPath.Trim('\') -split '\\' | Where-Object { $_ }
    $headers = @{ Authorization = "Bearer $AccessToken" }

    # First segment is typically the mailbox/store display name — Graph's /me/mailFolders is
    # already scoped to the signed-in mailbox, so skip a leading segment that matches the
    # display name convention (e.g. the account's own name) and start from top-level folders.
    $current = Invoke-RestMethod -Headers $headers -Uri 'https://graph.microsoft.com/v1.0/me/mailFolders?$top=250'
    $remaining = $segments
    $folderId = $null

    foreach ($seg in $remaining) {
        $match = $current.value | Where-Object { $_.displayName -ieq $seg }
        if (-not $match -and $folderId -eq $null) {
            # Might be the mailbox/store name itself (not a real folder) — skip it once.
            continue
        }
        if (-not $match) {
            throw "Graph folder segment '$seg' not found under the current folder."
        }
        $folderId = $match.id
        $current = Invoke-RestMethod -Headers $headers -Uri "https://graph.microsoft.com/v1.0/me/mailFolders/$folderId/childFolders?`$top=250"
    }

    if (-not $folderId) {
        throw "Graph folder not found: $FolderPath"
    }
    return $folderId
}

function Save-AttachmentsViaGraph {
    param([string]$AccessToken, [string]$FolderId, [string]$SnapshotDirectory)

    $headers = @{ Authorization = "Bearer $AccessToken" }
    $savedFiles = @()
    $uri = "https://graph.microsoft.com/v1.0/me/mailFolders/$FolderId/messages?`$filter=hasAttachments eq true&`$select=id,receivedDateTime,hasAttachments&`$top=100"

    while ($uri) {
        $page = Invoke-RestMethod -Headers $headers -Uri $uri
        foreach ($msg in $page.value) {
            $attachments = Invoke-RestMethod -Headers $headers -Uri "https://graph.microsoft.com/v1.0/me/messages/$($msg.id)/attachments"
            $received = ([datetime]$msg.receivedDateTime).ToString('yyyyMMdd-HHmmss')
            foreach ($att in $attachments.value) {
                if ($att.'@odata.type' -ne '#microsoft.graph.fileAttachment') { continue }
                $safeName = Get-SafeFileName $att.name
                $path = Join-Path $SnapshotDirectory "$received-$safeName"
                [IO.File]::WriteAllBytes($path, [Convert]::FromBase64String($att.contentBytes))
                $savedFiles += $path
            }
        }
        $uri = $page.'@odata.nextLink'
    }
    return $savedFiles
}

# ---------------------------------------------------------------------------
# Backup / rollback helpers for the dashboard file. The live dashboard is only
# ever touched via an atomic temp-file swap after full validation, and a
# timestamped backup is kept so a bad refresh can be rolled back by hand even
# if validation itself had a blind spot.
# ---------------------------------------------------------------------------
function Backup-Dashboard {
    param([string]$DashboardPath, [int]$RetentionCount)

    if (-not (Test-Path -LiteralPath $DashboardPath)) { return }

    $backupDir = Join-Path (Split-Path -Parent $DashboardPath) 'Backups'
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $name = Split-Path -Leaf $DashboardPath
    $backupPath = Join-Path $backupDir "$stamp-$name"
    Copy-Item -LiteralPath $DashboardPath -Destination $backupPath -Force

    $old = Get-ChildItem -LiteralPath $backupDir -Filter "*-$name" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -Skip $RetentionCount
    $old | Remove-Item -Force -ErrorAction SilentlyContinue

    return $backupPath
}

function Test-DashboardContent {
    param([string]$Html, [int]$ExpectedRecordCount)

    $dataStart = $Html.IndexOf('const DATA=')
    $configStart = $Html.IndexOf('const PRODUCT_CONFIG=', [Math]::Max($dataStart, 0))
    if ($dataStart -lt 0 -or $configStart -lt 0) {
        throw 'Validation failed: DATA/PRODUCT_CONFIG markers missing from candidate dashboard.'
    }

    # These helper constants/functions live between PRODUCT_CONFIG and fmt() and are
    # derived from PRODUCT_CONFIG at load time. If they go missing the dashboard UI
    # silently fails to render even though DATA looks fine (root cause of a prior outage).
    $requiredMarkers = 'const PRODUCT_KEYTYPES=', 'const PRODUCT_DIE_KEYTYPES=', 'const KEYTYPE_NAME=', 'const KEYTYPE_MILESTONE=', 'const ALL_MILESTONES=', 'const fmt='
    foreach ($marker in $requiredMarkers) {
        if ($Html.IndexOf($marker, $configStart) -lt 0) {
            throw "Validation failed: required dashboard marker '$marker' missing from candidate dashboard (refresh script may be replacing too much/too little content)."
        }
    }

    $m = [regex]::Match($Html, 'const DATA=(\[.*?\]);const PRODUCT_CONFIG=(\{.*?\});const PRODUCT_KEYTYPES=', 'Singleline')
    if (-not $m.Success) {
        throw 'Validation failed: could not extract DATA/PRODUCT_CONFIG as well-formed JSON from candidate dashboard.'
    }

    $parsedData = $m.Groups[1].Value | ConvertFrom-Json
    $parsedConfig = $m.Groups[2].Value | ConvertFrom-Json
    if ($null -eq $parsedData) { throw 'Validation failed: DATA JSON parsed to null.' }
    if ($parsedData.Count -ne $ExpectedRecordCount) {
        throw "Validation failed: embedded record count ($($parsedData.Count)) does not match generated record count ($ExpectedRecordCount)."
    }
    if ($null -eq $parsedConfig -or -not ($parsedConfig.PSObject.Properties.Name.Count -gt 0)) {
        throw 'Validation failed: PRODUCT_CONFIG parsed to an empty/invalid object.'
    }
}

function Get-PreviousRecordCount {
    param([string]$DashboardPath)

    if (-not (Test-Path -LiteralPath $DashboardPath)) { return 0 }
    try {
        $html = [IO.File]::ReadAllText($DashboardPath)
        $m = [regex]::Match($html, 'const DATA=(\[.*?\]);const PRODUCT_CONFIG=', 'Singleline')
        if (-not $m.Success) { return 0 }
        $data = $m.Groups[1].Value | ConvertFrom-Json
        return $data.Count
    } catch {
        return 0
    }
}

function Remove-OldSnapshots {
    param([string]$SnapshotDirectory, [int]$RetentionDays)

    if ($RetentionDays -le 0) { return 0 }
    $cutoff = (Get-Date).AddDays(-$RetentionDays)
    $old = Get-ChildItem -LiteralPath $SnapshotDirectory -Filter '*.txt' |
        Where-Object { $_.LastWriteTime -lt $cutoff }
    $old | Remove-Item -Force -ErrorAction SilentlyContinue
    return $old.Count
}

function Send-FailureAlert {
    param([string]$Recipient, [string]$ErrorMessage)

    if ([string]::IsNullOrWhiteSpace($Recipient) -or $Method -ne 'Outlook') { return }
    try {
        $outlook = New-Object -ComObject Outlook.Application
        $mail = $outlook.CreateItem(0)
        $mail.To = $Recipient
        $mail.Subject = 'ISEED dashboard refresh FAILED'
        $mail.Body = "The scheduled ISEED inventory dashboard refresh failed on $env:COMPUTERNAME at $(Get-Date -Format 's').`r`n`r`nError: $ErrorMessage`r`n`r`nThe dashboard was left at its last known-good state. See $LogPath for details."
        $mail.Send()
        Write-Log "Failure alert emailed to $Recipient" 'INFO'
    } catch {
        # Alerting must never mask the original failure.
        Write-Log "Could not send failure alert email: $($_.Exception.Message)" 'WARN'
    }
}

$lockAcquired = $false
try {
    Enter-RunLock -LockPath $LockPath -StaleMinutes $LockStaleMinutes
    $lockAcquired = $true

    New-Item -ItemType Directory -Force -Path $SnapshotDirectory | Out-Null

    if ($Method -eq 'Graph') {
        $accessToken = Invoke-WithRetry -ActionName 'Graph device-code sign-in' -ScriptBlock { Get-GraphAccessToken -ClientId $GraphClientId -TenantId $GraphTenantId }
        $folderId = Invoke-WithRetry -ActionName 'Graph folder lookup' -ScriptBlock { Find-GraphFolderId -AccessToken $accessToken -FolderPath $OutlookFolderPath }
        $savedFiles = Invoke-WithRetry -ActionName 'Graph attachment collection' -ScriptBlock { Save-AttachmentsViaGraph -AccessToken $accessToken -FolderId $folderId -SnapshotDirectory $SnapshotDirectory }
    } else {
        $savedFiles = Invoke-WithRetry -ActionName 'Outlook attachment collection' -ScriptBlock {
            Invoke-OutlookCollectionWithTimeout -FolderPath $OutlookFolderPath -SnapshotDirectory $SnapshotDirectory -TimeoutSeconds $OutlookTimeoutSeconds
        }
    }

    $records = @(
        foreach ($file in Get-ChildItem -LiteralPath $SnapshotDirectory -Filter '*.txt') {
            try {
                $kind = if ($file.Name -like '*central*') { 'central' } else { 'site' }
                $snapshot = [datetime]::ParseExact(
                    $file.BaseName.Substring(0, 15),
                    'yyyyMMdd-HHmmss',
                    $null
                ).ToString('s')

                foreach ($row in Import-Csv -LiteralPath $file.FullName) {
                    [long]$count = $row.COUNT
                    [long]$upper = $row.UPPER_LIMIT
                    [long]$critical = $row.CRITICAL_LOWER_LIMIT
                    [long]$warning = $row.WARNING_LOWER_LIMIT

                    [pscustomobject]@{
                        file      = $file.Name
                        snapshot  = $snapshot
                        kind      = $kind
                        factory   = $row.'FACTORY ID'
                        keyType   = [int]$row.'KEYTYPE ID'
                        count     = $count
                        upper     = $upper
                        critical  = $critical
                        warning   = $warning
                        lastEvent = if ($kind -eq 'central') {
                            $row.LAST_LOADED
                        } else {
                            $row.LAST_DISTRIBUTED
                        }
                    }
                }
            } catch {
                # Isolate a single malformed snapshot file (bad filename/date, missing
                # columns, corrupt CSV) so one bad attachment can't abort the whole run
                # and discard every other valid snapshot collected.
                Write-Log "Skipping unparsable snapshot file '$($file.Name)': $($_.Exception.Message)" 'WARN'
            }
        }
    )

    if (-not (Test-Path -LiteralPath $DashboardPath)) {
        throw "Dashboard not found: $DashboardPath"
    }

    # --- Safety floor / regression checks before touching anything ---
    if ($records.Count -lt $MinExpectedRecords) {
        throw "Refusing to update dashboard: only $($records.Count) record(s) parsed from $SnapshotDirectory, below the configured floor of $MinExpectedRecords. This usually means the snapshot folder is empty/stale or attachment collection silently failed. Dashboard left untouched."
    }
    $previousRecordCount = Get-PreviousRecordCount -DashboardPath $DashboardPath
    if ($previousRecordCount -gt 0 -and $records.Count -lt ($previousRecordCount * $MinRecordRetentionRatio)) {
        throw "Refusing to update dashboard: new record count ($($records.Count)) is less than $($MinRecordRetentionRatio * 100)% of the previously embedded count ($previousRecordCount). This looks like a partial/broken data pull. Dashboard left untouched."
    }

    $json = $records | ConvertTo-Json -Compress -Depth 4
    # Round-trip validation: catch malformed JSON before it ever reaches the dashboard.
    $null = $json | ConvertFrom-Json

    $buildProductConfig = Join-Path $PSScriptRoot 'build-product-config.ps1'
    $productConfigPath = Join-Path $PSScriptRoot 'Input\product-config.json'
    if (Test-Path -LiteralPath $buildProductConfig) {
        & $buildProductConfig
    }
    $productConfigJson = '{}'
    if (Test-Path -LiteralPath $productConfigPath) {
        $productConfigJson = (Get-Content -LiteralPath $productConfigPath -Raw | ConvertFrom-Json) | ConvertTo-Json -Compress -Depth 6
    }
    $null = $productConfigJson | ConvertFrom-Json

    $html = [IO.File]::ReadAllText($DashboardPath)
    $dataStart = $html.IndexOf('const DATA=')
    $configStart = $html.IndexOf('const PRODUCT_CONFIG=', $dataStart)
    if ($dataStart -lt 0) {
        throw "Dashboard data marker was not found in $DashboardPath"
    }
    if ($configStart -lt 0) {
        throw "Dashboard product config marker was not found in $DashboardPath"
    }

    $configEndMarkers = @(
        $html.IndexOf('const PRODUCT_KEYTYPES=', $configStart),
        $html.IndexOf('const KEYTYPE_NAME=', $configStart),
        $html.IndexOf('const fmt=', $configStart)
    ) | Where-Object { $_ -ge 0 }
    $configEnd = ($configEndMarkers | Measure-Object -Minimum).Minimum
    if ($null -eq $configEnd) {
        throw "Dashboard format marker was not found in $DashboardPath"
    }

    $prefix = $html.Substring(0, $dataStart)
    $suffix = $html.Substring($configEnd)
    $updated = $prefix + "const DATA=$json;const PRODUCT_CONFIG=$productConfigJson;" + $suffix

    # Validate the *candidate* content fully before it ever touches the live file.
    Test-DashboardContent -Html $updated -ExpectedRecordCount $records.Count

    # Atomic swap: write to a temp file on the same volume, then replace the live
    # file in one filesystem operation, so a crash mid-write never leaves a
    # half-written/corrupt dashboard.
    $tempPath = "$DashboardPath.tmp"
    [IO.File]::WriteAllText(
        $tempPath,
        $updated,
        (New-Object Text.UTF8Encoding($false))
    )

    # Re-read the temp file from disk and re-validate, guarding against any
    # encoding/IO corruption introduced by the write itself.
    $writtenHtml = [IO.File]::ReadAllText($tempPath)
    Test-DashboardContent -Html $writtenHtml -ExpectedRecordCount $records.Count

    $backupPath = Backup-Dashboard -DashboardPath $DashboardPath -RetentionCount $BackupRetentionCount
    Move-Item -LiteralPath $tempPath -Destination $DashboardPath -Force

    $removedSnapshots = Remove-OldSnapshots -SnapshotDirectory $SnapshotDirectory -RetentionDays $SnapshotRetentionDays

    Write-Log "Method: $Method"
    Write-Log "Mail folder: $OutlookFolderPath"
    Write-Log "Attachments refreshed: $($savedFiles.Count)"
    Write-Log "Inventory records embedded: $($records.Count) (previous: $previousRecordCount)"
    Write-Log "Dashboard updated: $DashboardPath"
    Write-Log "Dashboard backup: $backupPath"
    Write-Log "Product config embedded: $productConfigPath"
    if ($removedSnapshots -gt 0) {
        Write-Log "Pruned $removedSnapshots snapshot file(s) older than $SnapshotRetentionDays day(s)."
    }
    Write-Log 'Refresh completed successfully.'
    Write-Heartbeat -Status 'success' -Message 'Refresh completed successfully.' -RecordCount $records.Count

    if ($OpenDashboard) {
        Start-Process $DashboardPath
    }

    exit 0
} catch {
    Write-Log "Refresh FAILED: $($_.Exception.Message)" 'ERROR'
    Write-Log "Dashboard was left untouched at its last known-good state: $DashboardPath" 'ERROR'
    Write-Heartbeat -Status 'failed' -Message $_.Exception.Message
    Send-FailureAlert -Recipient $AlertRecipient -ErrorMessage $_.Exception.Message
    exit 1
} finally {
    if ($lockAcquired) {
        Exit-RunLock -LockPath $LockPath
    }
}


