# ============================================================================
# ISEED Dashboard Refresh - Snapshot-Only Mode
# ============================================================================
# This script assumes snapshots are already downloaded to Input/Snapshots/
# It only handles: parsing -> validation -> dashboard injection -> backup
#
# Used by: Copilot Workflow (attachments pre-fetched via Graph)
# Does NOT: Authenticate, fetch emails, download attachments
# ============================================================================

param(
    [string]$ProjectPath = $PSScriptRoot,
    [string]$SnapshotDirectory = (Join-Path $ProjectPath 'Input\Snapshots'),
    [string]$DashboardPath = (Join-Path $ProjectPath 'inventory-dashboard.html'),
    [string]$BackupDirectory = (Join-Path $ProjectPath 'Backups'),
    
    # Safety thresholds (same as main refresh script)
    [int]$MinExpectedRecords = 1000,
    [double]$MinRecordRetentionRatio = 0.5,
    [int]$BackupRetentionCount = 10
)

$ErrorActionPreference = 'Stop'

# ============================================================================
# Logging
# ============================================================================
function Write-Log {
    param([string]$Message, [ValidateSet('INFO', 'WARN', 'ERROR')][string]$Level = 'INFO')
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "[$timestamp] [$Level] $Message"
    Write-Host $line
}

# ============================================================================
# Parse Snapshots
# ============================================================================
function Get-SnapshotRecords {
    param([string]$SnapshotDirectory)
    
    Write-Log "Parsing snapshots from: $SnapshotDirectory"
    
    if (-not (Test-Path -LiteralPath $SnapshotDirectory)) {
        throw "Snapshot directory not found: $SnapshotDirectory"
    }

    $records = @()
    $fileCount = 0

    foreach ($file in Get-ChildItem -LiteralPath $SnapshotDirectory -Filter '*.txt') {
        try {
            $fileCount++
            
            # Extract snapshot timestamp from filename (format: yyyyMMdd-HHmmss-*.txt)
            $kind = if ($file.Name -like '*central*') { 'central' } else { 'site' }
            $timestamp = [datetime]::ParseExact(
                $file.BaseName.Substring(0, 15),
                'yyyyMMdd-HHmmss',
                $null
            ).ToString('s')

            # Parse CSV rows
            foreach ($row in Import-Csv -LiteralPath $file.FullName) {
                $records += [pscustomobject]@{
                    file      = $file.Name
                    snapshot  = $timestamp
                    kind      = $kind
                    factory   = $row.'FACTORY ID'
                    keyType   = [int]$row.'KEYTYPE ID'
                    count     = [long]$row.COUNT
                    upper     = [long]$row.UPPER_LIMIT
                    critical  = [long]$row.CRITICAL_LOWER_LIMIT
                    warning   = [long]$row.WARNING_LOWER_LIMIT
                    lastEvent = if ($kind -eq 'central') { $row.LAST_LOADED } else { $row.LAST_DISTRIBUTED }
                }
            }
        } catch {
            Write-Log "Skipping unparsable file '$($file.Name)': $($_.Exception.Message)" 'WARN'
        }
    }

    Write-Log "Parsed $($records.Count) records from $fileCount snapshot files"
    return $records
}

# ============================================================================
# Extract Previous Record Count from Dashboard
# ============================================================================
function Get-PreviousRecordCount {
    param([string]$DashboardPath)
    
    if (-not (Test-Path -LiteralPath $DashboardPath)) {
        return 0
    }

    $html = [IO.File]::ReadAllText($DashboardPath)
    $dataStart = $html.IndexOf('const DATA=')
    if ($dataStart -lt 0) {
        return 0
    }

    # Find the next marker to extract the data block
    $nextMarker = $html.IndexOf('const PRODUCT_CONFIG=', $dataStart)
    if ($nextMarker -lt 0) {
        $nextMarker = $html.IndexOf('const KEYTYPE_NAME=', $dataStart)
    }
    if ($nextMarker -lt 0) {
        return 0
    }

    $dataBlock = $html.Substring($dataStart, $nextMarker - $dataStart)
    
    # Count JSON array elements
    try {
        $json = $dataBlock -replace '^const DATA=', '' -replace ';$', ''
        $data = $json | ConvertFrom-Json
        return @($data).Count
    } catch {
        return 0
    }
}

# ============================================================================
# Backup Dashboard
# ============================================================================
function Backup-Dashboard {
    param([string]$DashboardPath, [string]$BackupDirectory, [int]$RetentionCount)
    
    if (-not (Test-Path -LiteralPath $DashboardPath)) {
        return
    }

    New-Item -ItemType Directory -Force -Path $BackupDirectory | Out-Null
    
    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $backupFile = Join-Path $BackupDirectory "$timestamp-inventory-dashboard.html"
    Copy-Item -LiteralPath $DashboardPath -Destination $backupFile
    Write-Log "Backed up dashboard to: $backupFile"

    # Clean old backups
    $existing = @(Get-ChildItem -LiteralPath $BackupDirectory -Filter '*.html' | Sort-Object LastWriteTime -Descending)
    if ($existing.Count -gt $RetentionCount) {
        $toDelete = $existing | Select-Object -Skip $RetentionCount
        foreach ($file in $toDelete) {
            Remove-Item -LiteralPath $file.FullName
            Write-Log "Deleted old backup: $($file.Name)"
        }
    }
}

# ============================================================================
# Inject Data into Dashboard
# ============================================================================
function Update-Dashboard {
    param([string]$DashboardPath, [array]$Records)
    
    Write-Log "Updating dashboard HTML..."

    if (-not (Test-Path -LiteralPath $DashboardPath)) {
        throw "Dashboard file not found: $DashboardPath"
    }

    $html = [IO.File]::ReadAllText($DashboardPath)
    $dataStart = $html.IndexOf('const DATA=')
    if ($dataStart -lt 0) {
        throw "Data marker 'const DATA=' not found in dashboard"
    }

    # Find the next marker (PRODUCT_CONFIG, KEYTYPE_NAME, or fmt)
    $endMarkers = @(
        $html.IndexOf('const PRODUCT_CONFIG=', $dataStart),
        $html.IndexOf('const KEYTYPE_NAME=', $dataStart),
        $html.IndexOf('const fmt=', $dataStart)
    ) | Where-Object { $_ -gt 0 }

    if ($endMarkers.Count -eq 0) {
        throw "No end marker found after DATA in dashboard"
    }

    $dataEnd = $endMarkers | Sort-Object | Select-Object -First 1
    
    # Build new data block
    $json = $Records | ConvertTo-Json -Compress -Depth 4
    $newDataBlock = "const DATA=$json;"
    
    # Replace
    $before = $html.Substring(0, $dataStart)
    $after = $html.Substring($dataEnd)
    $newHtml = $before + $newDataBlock + "`r`n" + $after

    # Validate JSON can round-trip
    $null = $json | ConvertFrom-Json

    # Write back
    [IO.File]::WriteAllText($DashboardPath, $newHtml, [System.Text.Encoding]::UTF8)
    Write-Log "Dashboard injected with $($Records.Count) records"
}

# ============================================================================
# Main
# ============================================================================
try {
    Write-Log "=== ISEED Dashboard Refresh (Snapshot-Only Mode) ==="
    Write-Log "Snapshot Directory: $SnapshotDirectory"
    Write-Log "Dashboard Path: $DashboardPath"

    # Parse existing snapshots
    $records = Get-SnapshotRecords -SnapshotDirectory $SnapshotDirectory
    
    # Validate counts
    if ($records.Count -lt $MinExpectedRecords) {
        throw "Only $($records.Count) records parsed, below floor of $MinExpectedRecords. Dashboard left untouched."
    }

    $prevCount = Get-PreviousRecordCount -DashboardPath $DashboardPath
    if ($prevCount -gt 0 -and $records.Count -lt ($prevCount * $MinRecordRetentionRatio)) {
        throw "New count ($($records.Count)) is below $($MinRecordRetentionRatio * 100)% of previous ($prevCount). Suspicious data pull. Dashboard left untouched."
    }

    Write-Log "Safety checks passed (previous: $prevCount, new: $($records.Count))"

    # Backup current dashboard
    Backup-Dashboard -DashboardPath $DashboardPath -BackupDirectory $BackupDirectory -RetentionCount $BackupRetentionCount

    # Update dashboard
    Update-Dashboard -DashboardPath $DashboardPath -Records $records

    Write-Log "=== SUCCESS ==="
    Write-Output "Refreshed with $($records.Count) records"

} catch {
    Write-Log "ERROR: $($_.Exception.Message)" 'ERROR'
    Write-Log "Stack: $($_.ScriptStackTrace)" 'ERROR'
    exit 1
}
