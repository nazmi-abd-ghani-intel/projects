# ============================================================================
# ISEED Snapshot Feeder - SharePoint (OneDrive sync) -> git
# ============================================================================
# Copies new ISEED snapshot .txt files from the OneDrive-synced SharePoint
# folder into Input/Snapshots, commits ONLY those files and pushes to main.
# GitHub Actions (.github/workflows/iseed-refresh.yml) rebuilds the dashboard.
#
# Runs unattended from Windows Task Scheduler. Never touches the HTML.
# ============================================================================

param(
    # OneDrive-synced copy of
    # https://intel.sharepoint.com/sites/mpefusewg/Shared Documents/NVL Fuse Sync/Dynamic and Security Fuses/KeyIDs/Volume/KeysSnapshot
    [string]$SourcePath,
    [string]$RepoPath = (Split-Path $PSScriptRoot -Parent),
    [string]$Branch = 'main',
    [switch]$NoPush,
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
$script:LogFile = Join-Path $PSScriptRoot 'Logs\sync-snapshots.log'

function Write-Log {
    param([string]$Message, [ValidateSet('INFO', 'WARN', 'ERROR')][string]$Level = 'INFO')
    $line = "[{0}] [{1}] {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message
    Write-Host $line
    $dir = Split-Path $script:LogFile -Parent
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
    [IO.File]::AppendAllText($script:LogFile, $line + [Environment]::NewLine)
}

function Resolve-SourcePath {
    param([string]$Explicit)
    if ($Explicit) { return $Explicit }
    $relative = 'NVL Fuse Sync\Dynamic and Security Fuses\KeyIDs\Volume\KeysSnapshot'
    $roots = @($env:OneDriveCommercial)
    $acct = Get-ItemProperty 'HKCU:\Software\Microsoft\OneDrive\Accounts\Business1' -ErrorAction SilentlyContinue
    if ($acct -and $acct.UserFolder) { $roots += $acct.UserFolder }
    $roots += Get-ChildItem $env:USERPROFILE -Directory -Filter 'OneDrive - *' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
    foreach ($r in ($roots | Where-Object { $_ } | Select-Object -Unique)) {
        $candidate = Join-Path $r $relative
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    throw "KeysSnapshot folder not found under any OneDrive root. Sync the SharePoint folder or pass -SourcePath."
}

function Invoke-Git {
    param([string[]]$Arguments)
    $out = & git @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw "git $($Arguments -join ' ') failed ($LASTEXITCODE): $($out -join ' | ')" }
    return $out
}

try {
    Write-Log "=== ISEED snapshot sync start ==="

    $source = Resolve-SourcePath -Explicit $SourcePath
    $target = Join-Path $PSScriptRoot 'Input\Snapshots'
    if (-not (Test-Path -LiteralPath $target)) { throw "Target folder missing: $target" }
    Write-Log "Source: $source"
    Write-Log "Target: $target"

    # Only well-formed snapshot files: yyyyMMdd-HHmmss-<name>.txt, non-empty, not yet in git
    $pattern = '^\d{8}-\d{6}-.+\.txt$'
    $existing = @{}
    Get-ChildItem -LiteralPath $target -Filter '*.txt' | ForEach-Object { $existing[$_.Name.ToLowerInvariant()] = $true }

    $candidates = @(Get-ChildItem -LiteralPath $source -Filter '*.txt' -File)
    $new = @($candidates | Where-Object { $_.Name -match $pattern -and $_.Length -gt 0 -and -not $existing.ContainsKey($_.Name.ToLowerInvariant()) })
    $skippedBadName = @($candidates | Where-Object { $_.Name -notmatch $pattern }).Count
    if ($skippedBadName -gt 0) { Write-Log "$skippedBadName file(s) ignored: name does not match yyyyMMdd-HHmmss-*.txt" 'WARN' }

    Write-Log "Found $($candidates.Count) file(s) in source, $($new.Count) new"
    if ($new.Count -eq 0) {
        Write-Log "Nothing to do"
        Write-Log "=== done (no changes) ==="
        exit 0
    }

    Set-Location $RepoPath
    $dirty = Invoke-Git @('status', '--porcelain', '--', 'ISEED-Volume-Analysis/Input/Snapshots')
    if ($dirty) { throw "Input/Snapshots has uncommitted changes; refusing to run: $($dirty -join ' | ')" }

    Invoke-Git @('fetch', '--quiet', 'origin', $Branch) | Out-Null
    Invoke-Git @('checkout', '--quiet', $Branch) | Out-Null
    Invoke-Git @('pull', '--quiet', '--ff-only', 'origin', $Branch) | Out-Null

    $copied = @()
    foreach ($f in $new) {
        $dest = Join-Path $target $f.Name
        if ($WhatIf) { Write-Log "WHATIF copy $($f.Name) ($($f.Length) bytes)"; continue }
        # Force the OneDrive placeholder to hydrate, then copy bytes verbatim
        [IO.File]::WriteAllBytes($dest, [IO.File]::ReadAllBytes($f.FullName))
        $copied += $f.Name
        Write-Log "Copied $($f.Name) ($($f.Length) bytes)"
    }
    if ($WhatIf) { Write-Log "=== done (WhatIf) ==="; exit 0 }

    foreach ($name in $copied) {
        Invoke-Git @('add', '--', "ISEED-Volume-Analysis/Input/Snapshots/$name") | Out-Null
    }
    $staged = @(Invoke-Git @('diff', '--cached', '--name-only'))
    $unexpected = @($staged | Where-Object { $_ -notmatch '^ISEED-Volume-Analysis/Input/Snapshots/[^/]+\.txt$' })
    if ($unexpected.Count -gt 0) {
        Invoke-Git @('reset', '--quiet') | Out-Null
        throw "Unexpected staged paths, aborted: $($unexpected -join ', ')"
    }

    $msg = "data(iseed): add $($copied.Count) snapshot$(if ($copied.Count -ne 1) { 's' })"
    Invoke-Git @('commit', '--quiet', '-m', $msg, '-m', "Feeder: sync-snapshots.ps1 (SharePoint KeysSnapshot via OneDrive)`n`n$($copied -join "`n")") | Out-Null
    $sha = (Invoke-Git @('rev-parse', '--short', 'HEAD')) -join ''
    Write-Log "Committed $sha : $msg"

    if ($NoPush) {
        Write-Log "NoPush set; commit left local" 'WARN'
    } else {
        try {
            Invoke-Git @('push', '--quiet', 'origin', $Branch) | Out-Null
        } catch {
            Write-Log "Push rejected, rebasing once: $($_.Exception.Message)" 'WARN'
            Invoke-Git @('pull', '--quiet', '--rebase', 'origin', $Branch) | Out-Null
            Invoke-Git @('push', '--quiet', 'origin', $Branch) | Out-Null
        }
        Write-Log "Pushed to origin/$Branch - GitHub Actions 'ISEED Dashboard Refresh' will rebuild the dashboard"
    }

    Write-Log "=== done ($($copied.Count) new) ==="
    exit 0
} catch {
    Write-Log "FAILED: $($_.Exception.Message)" 'ERROR'
    exit 1
}
