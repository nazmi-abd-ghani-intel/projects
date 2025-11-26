param(
    [switch]$OpenTimeline,
    [switch]$Embedded
)

$baseUrl = "https://adb-3205722585840303.3.azuredatabricks.net"
$httpPath = "/api/2.0/sql/statements"
$apiEndpoint = "$baseUrl$httpPath"

$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Definition }
$sqlFile = Join-Path $scriptDir "Products_Milestone.sql"
$datetime = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"

if (-not (Test-Path $sqlFile)) {
    Write-Host "SQL file not found: $sqlFile"
    exit 1
}

# Read SQL and strip any triple-backtick fences if present
$rawSql = Get-Content $sqlFile -Raw
# split on CRLF or LF using single-quoted regex, ignore triple-backtick fence lines, then rejoin using the system newline
$sqlQuery = ($rawSql -split '\r?\n' | Where-Object { $_ -notmatch '^```' }) -join [System.Environment]::NewLine

$secretFile = Join-Path $scriptDir "databricks_secret.txt"
if (-not (Test-Path $secretFile)) {
    New-Item -ItemType File -Path $secretFile | Out-Null
    Write-Host "Secret file not found. Created an empty file at $secretFile."
    Write-Host "Please add your Databricks PAT to this file and rerun the script."
    exit 1
}

$pat = Get-Content $secretFile -Raw
if (-not $pat -or $pat.Trim().Length -eq 0) {
    Write-Host "Databricks PAT is empty. Please add it to $secretFile and rerun."
    exit 1
}

Write-Host "Executing SQL from: $sqlFile"

$headers = @{
    "Authorization" = "Bearer $pat"
    "Content-Type"  = "application/json"
}

$body = @{
    statement    = $sqlQuery
    warehouse_id = "80e5cb743670bfb7"
} | ConvertTo-Json

Write-Host "Sending request to Databricks API..."

try {
    $response = Invoke-RestMethod -Uri $apiEndpoint -Headers $headers -Method Post -Body $body
    $statementId = $response.statement_id

    if (-not $statementId) {
        Write-Host "No statement_id returned. Response:`n"
        $response | ConvertTo-Json -Depth 10
        exit 1
    }

    Write-Host "Statement ID: $statementId"
    $statusUrl = "$baseUrl/api/2.0/sql/statements/$statementId"

    $maxTries = 60
    $try = 0

    do {
        Start-Sleep -Seconds 2
        $statusResponse = Invoke-RestMethod -Uri $statusUrl -Headers $headers -Method Get
        $state = $statusResponse.status.state
        Write-Host "Current state: $state"
        $try++
    } while ($state -ne "SUCCEEDED" -and $state -ne "FAILED" -and $try -lt $maxTries)

    if ($state -eq "SUCCEEDED") {
        Write-Host "Query succeeded! Writing result to JSON files..."

        # Add metadata with timestamp in PST
        $pstZone = [System.TimeZoneInfo]::FindSystemTimeZoneById("Pacific Standard Time")
        $pstTime = [System.TimeZoneInfo]::ConvertTimeFromUtc([DateTime]::UtcNow, $pstZone)
        $timestamp = $pstTime.ToString("yyyy-MM-dd HH:mm:ss") + " (PST)"
        if ($statusResponse.PSObject.Properties.Name -contains 'metadata') {
            $statusResponse.metadata.last_updated = $timestamp
        } else {
            $statusResponse | Add-Member -MemberType NoteProperty -Name 'metadata' -Value @{ last_updated = $timestamp } -Force
        }

        $dataDir = Join-Path $scriptDir "Data"
        if (-not (Test-Path $dataDir)) {
            New-Item -ItemType Directory -Path $dataDir | Out-Null
            Write-Host "Created Data directory: $dataDir"
        }

        $backupFile = Join-Path $dataDir "prodmilestone_${datetime}.json"
        $activeFile = Join-Path $scriptDir "prodmilestone.json"

        $statusResponse | ConvertTo-Json -Depth 20 | Out-File -FilePath $backupFile -Encoding utf8
        Copy-Item -Path $backupFile -Destination $activeFile -Force

        # Try to fetch the statement result explicitly and build a proper table for CSV output
        $tableObjects = $null
        $resultUrl = "$baseUrl/api/2.0/sql/statements/$statementId/result"
        try {
            $resultResponse = Invoke-RestMethod -Uri $resultUrl -Headers $headers -Method Get -ErrorAction Stop
        } catch {
            $resultResponse = $null
        }

        # Normalize schema and rows from possible response shapes:
        # - JSON_ARRAY: schema is under manifest.schema and rows under result.data_array
        # - other shapes: schema under result.schema and rows under result.data
        $schema = $null
        $rows = $null

        if ($resultResponse) {
            if ($resultResponse.manifest -and $resultResponse.manifest.schema) {
                $schema = $resultResponse.manifest.schema
            } elseif ($resultResponse.schema) {
                $schema = $resultResponse.schema
            }
            if ($resultResponse.result -and $resultResponse.result.data_array) {
                $rows = $resultResponse.result.data_array
            } elseif ($resultResponse.data_array) {
                $rows = $resultResponse.data_array
            } elseif ($resultResponse.result -and $resultResponse.result.data) {
                $rows = $resultResponse.result.data
            } elseif ($resultResponse.data) {
                $rows = $resultResponse.data
            }
        }

        if (-not $schema -and $statusResponse) {
            if ($statusResponse.manifest -and $statusResponse.manifest.schema) {
                $schema = $statusResponse.manifest.schema
            } elseif ($statusResponse.result -and $statusResponse.result.schema) {
                $schema = $statusResponse.result.schema
            }
            if ($statusResponse.result -and $statusResponse.result.data_array) {
                $rows = $statusResponse.result.data_array
            } elseif ($statusResponse.result -and $statusResponse.result.data) {
                $rows = $statusResponse.result.data
            }
        }

        if ($schema -and $schema.columns -and $rows) {
            $cols = $schema.columns | ForEach-Object { $_.name }
            $list = @()
            foreach ($r in $rows) {
                $h = [ordered]@{}
                for ($i = 0; $i -lt $cols.Count; $i++) {
                    $h[$cols[$i]] = $r[$i]
                }
                $list += New-Object PSObject -Property $h
            }
            $tableObjects = $list
        }

        # Always produce CSV files. If we have tabular rows, write them with the original column order; otherwise write a single-column CSV containing the raw JSON.
        $csvBackup = Join-Path $dataDir "prodmilestone_${datetime}.csv"
        $csvActive = Join-Path $scriptDir "prodmilestone.csv"

        if ($tableObjects) {
            # Write a plain comma-separated CSV without quoting and with literal 'null' for nulls to match SQL output
            $lines = @()
            $header = $cols -join ','
            $lines += $header
            foreach ($r in $rows) {
                $fields = @()
                for ($i = 0; $i -lt $cols.Count; $i++) {
                    $val = $r[$i]
                    if ($null -eq $val) { $fields += 'null' } else { $fields += $val.ToString() }
                }
                $lines += ($fields -join ',')
            }
            $lines | Out-File -FilePath $csvBackup -Encoding UTF8
            Copy-Item -Path $csvBackup -Destination $csvActive -Force

            Write-Host "Successfully saved Product Milestone data to:`n  - $backupFile (backup JSON)`n  - $activeFile (active JSON)`n  - $csvBackup (backup CSV)`n  - $csvActive (active CSV)"
        } else {
            # Fallback: write the full JSON as a single CSV cell (header 'json' then compact JSON line)
            $jsonCompact = $statusResponse | ConvertTo-Json -Depth 20 -Compress
            $lines = @()
            $lines += 'json'
            $lines += $jsonCompact
            $lines | Out-File -FilePath $csvBackup -Encoding UTF8
            Copy-Item -Path $csvBackup -Destination $csvActive -Force

            Write-Host "No tabular result data found; wrote JSON-as-CSV fallback:`n  - $backupFile (backup JSON)`n  - $activeFile (active JSON)`n  - $csvBackup (backup CSV)`n  - $csvActive (active CSV)"
        }

            # Always generate an embedded HTML copy that inlines the active JSON so it can be opened directly (no server required)
            try {
                $embeddedHtmlPath = Join-Path $scriptDir "prodmilestone_timeline_embedded.html"
                $jsonContent = Get-Content $activeFile -Raw

                $templatePath = Join-Path $scriptDir "prodmilestone_timeline.html"
                if (-not (Test-Path $templatePath)) {
                    Write-Host "Template HTML not found: $templatePath. Skipping embedded HTML generation."
                } else {
                    $template = Get-Content $templatePath -Raw -Encoding UTF8
                    # Simple injection: replace a marker comment in template with the JSON variable
                    if ($template -match '<!-- INLINE_JSON_MARKER -->') {
                        $injected = $template -replace '<!-- INLINE_JSON_MARKER -->', "const INLINE_JSON = $jsonContent;"
                        # Use UTF8 without BOM to preserve emoji and special characters
                        [System.IO.File]::WriteAllText($embeddedHtmlPath, $injected, [System.Text.UTF8Encoding]::new($false))
                        Write-Host "Embedded timeline written to: $embeddedHtmlPath"
                    } else {
                        Write-Host "Template does not contain INLINE_JSON_MARKER. Skipping embedded generation."
                    }
                }
            } catch {
                Write-Host "Failed to write embedded HTML: $_"
            }

            # Optionally open timeline: prefer server-based (start-timeline.ps1) unless Embedded was requested
            if ($OpenTimeline) {
                try {
                    if ($Embedded -and (Test-Path (Join-Path $scriptDir 'prodmilestone_timeline_embedded.html'))) {
                        Start-Process (Join-Path $scriptDir 'prodmilestone_timeline_embedded.html')
                    } else {
                        $starter = Join-Path $scriptDir 'start-timeline.ps1'
                        if (Test-Path $starter) {
                            & $starter -Open
                        } else {
                            Write-Host "start-timeline.ps1 not found; please run a local server and open /prodmilestone_timeline.html manually."
                        }
                    }
                } catch {
                    Write-Host "Failed to open timeline: $_"
                }
            }
    } else {
        Write-Host "Query did not succeed. Final state: $state"
        $statusResponse | ConvertTo-Json -Depth 10
        exit 1
    }
} catch {
    Write-Host "API call failed: $_"
    if ($_.Exception) { Write-Host "Error details: $($_.Exception.Message)" }
    exit 1
}
