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

        # Create timestamped backup (release versions are kept in Data folder)
        $backupFile = Join-Path $dataDir "prodmilestone_${datetime}.json"
        $activeFile = Join-Path $scriptDir "prodmilestone.json"

        $statusResponse | ConvertTo-Json -Depth 20 | Out-File -FilePath $backupFile -Encoding utf8
        Copy-Item -Path $backupFile -Destination $activeFile -Force

        # Normalize schema and rows from possible response shapes
        # Try explicit result endpoint first, fall back to status response
        $resultUrl = "$baseUrl/api/2.0/sql/statements/$statementId/result"
        $resultResponse = try { Invoke-RestMethod -Uri $resultUrl -Headers $headers -Method Get -ErrorAction Stop } catch { $null }
        
        $response = if ($resultResponse) { $resultResponse } else { $statusResponse }
        
        $schema = if ($response.manifest.schema) { $response.manifest.schema } elseif ($response.result.schema) { $response.result.schema } else { $response.schema }
        $rows = if ($response.result.data_array) { $response.result.data_array } elseif ($response.data_array) { $response.data_array } elseif ($response.result.data) { $response.result.data } else { $response.data }
        
        $tableObjects = $null

        $cols = if ($schema -and $schema.columns) { $schema.columns | ForEach-Object { $_.name } } else { $null }
        
        if ($cols -and $rows) {
            $tableObjects = @()
            foreach ($r in $rows) {
                $h = [ordered]@{}
                for ($i = 0; $i -lt $cols.Count; $i++) { $h[$cols[$i]] = $r[$i] }
                $tableObjects += [PSCustomObject]$h
            }
        }

        # Produce JSON and CSV files with timestamped backups
        $csvActive = Join-Path $scriptDir "prodmilestone.csv"
        $csvBackup = Join-Path $dataDir "prodmilestone_${datetime}.csv"

        if ($tableObjects) {
            # Write a plain comma-separated CSV without quoting and with literal 'null' for nulls
            $csvContent = New-Object System.Text.StringBuilder
            [void]$csvContent.AppendLine(($cols -join ','))
            
            foreach ($r in $rows) {
                $fields = for ($i = 0; $i -lt $cols.Count; $i++) { if ($null -eq $r[$i]) { 'null' } else { $r[$i].ToString() } }
                [void]$csvContent.AppendLine(($fields -join ','))
            }
            
            $csvContent.ToString() | Out-File -FilePath $csvActive -Encoding UTF8
            $csvContent.ToString() | Out-File -FilePath $csvBackup -Encoding UTF8

            Write-Host "Successfully saved Product Milestone data to:`n  - $activeFile (active JSON)`n  - $csvActive (active CSV)`n  - $csvBackup (CSV backup)"
        } else {
            # Fallback: write the full JSON as a single CSV cell (header 'json' then compact JSON line)
            $jsonCompact = $statusResponse | ConvertTo-Json -Depth 20 -Compress
            $lines = @()
            $lines += 'json'
            $lines += $jsonCompact
            $lines | Out-File -FilePath $csvActive -Encoding UTF8
            $lines | Out-File -FilePath $csvBackup -Encoding UTF8

            Write-Host "No tabular result data found; wrote JSON-as-CSV fallback:`n  - $activeFile (active JSON)`n  - $csvActive (active CSV)`n  - $csvBackup (CSV backup)"
        }

        # --- GENERATE CHANGE LOGS ---
        try {
            # Compare against the latest committed release in git (source of truth)
            $previousJsonFile = $null
            $releaseDataJson = $null
            
            # Find git root directory
            $gitRoot = $scriptDir
            while ($gitRoot -and -not (Test-Path (Join-Path $gitRoot ".git"))) {
                $gitRoot = Split-Path -Parent $gitRoot
            }
            
            if ($gitRoot) {
                try {
                    # Try to retrieve the latest committed version from git
                    $committedJson = & git -C $gitRoot show HEAD:ProductMilestone/prodmilestone.json 2>$null
                    if ($committedJson) {
                        $releaseDataJson = $committedJson | ConvertFrom-Json -ErrorAction SilentlyContinue
                        if ($releaseDataJson.result -and $releaseDataJson.result.data_array) {
                            $previousJsonFile = @{ data = $releaseDataJson; source = "git" }
                            Write-Host "Comparing current data (row count: $($rows.Count)) with latest git release (row count: $($releaseDataJson.result.row_count))"
                            
                            # Try to get the baseline date from the last committed backup filename
                            $committedBackupFiles = & git -C $gitRoot ls-tree -r --name-only HEAD ProductMilestone/Data/ 2>$null | Where-Object { $_ -match 'prodmilestone_(\d{4}-\d{2}-\d{2})_' }
                            if ($committedBackupFiles) {
                                $lastCommittedFile = $committedBackupFiles | Sort-Object -Descending | Select-Object -First 1
                                if ($lastCommittedFile -match 'prodmilestone_(\d{4}-\d{2}-\d{2})_') {
                                    $baselineCommitDate = $matches[1]
                                    Write-Host "Baseline date from last committed file: $baselineCommitDate"
                                }
                            }
                        }
                    } else {
                        Write-Host "Note: No committed release in git. This is the first release."
                    }
                } catch {
                    Write-Host "Note: Could not retrieve git release. This may be the first release."
                }
            }
            
            $changes = @{
                timestamp = $timestamp
                revision = 1  # Will be updated if previous exists
                compared_against = "git"
                git_commit = ""
                git_commit_date = ""
                baseline_date = $baselineCommitDate  # Date from last committed backup file
                new_products = @()
                removed_products = @()
                value_changes = @()
            }

            # Get current git commit hash and date for tracking
            if ($gitRoot) {
                try {
                    $gitCommit = & git -C $gitRoot rev-parse --short HEAD 2>$null
                    if ($gitCommit) { 
                        $changes.git_commit = $gitCommit 
                        # Get commit date in YYYY-MM-DD format
                        $gitCommitDate = & git -C $gitRoot show -s --format=%ci HEAD 2>$null
                        if ($gitCommitDate) {
                            $commitDateTime = [DateTime]::Parse($gitCommitDate)
                            $changes.git_commit_date = $commitDateTime.ToString("yyyy-MM-dd")
                        }
                    }
                } catch { }
            }

            # Helper function to calculate WW (week number in YYYYWW format)
            function Get-WeekNumber {
                param([string]$dateStr)
                try {
                    $date = [DateTime]::Parse($dateStr)
                    $year = $date.Year
                    $weekNum = [System.Globalization.CultureInfo]::CurrentCulture.Calendar.GetWeekOfYear(
                        $date,
                        [System.Globalization.CalendarWeekRule]::FirstDay,
                        [DayOfWeek]::Sunday
                    )
                    return "$year" + $weekNum.ToString("00")
                } catch {
                    return ""
                }
            }

            if ($previousJsonFile) {
                try {
                    # Load previous release (can be from git or backup file)
                    $previousJson = $null
                    
                    if ($previousJsonFile -is [hashtable]) {
                        # Data from git
                        $previousJson = $previousJsonFile.data
                    } else {
                        # Data from file
                        $previousJson = Get-Content $previousJsonFile -Raw | ConvertFrom-Json
                    }
                    
                    if ($previousJson -and $previousJson.result -and $previousJson.result.data_array) {
                        $prevData = $previousJson.result.data_array
                        $prevSchema = $previousJson.manifest.schema.columns | ForEach-Object { $_.name }

                        if ($prevData -and $prevSchema) {
                            # Pre-calculate column indices for performance
                            $currProjIdx = $cols.IndexOf('AtlasProjectName')
                            $currMileIdx = $cols.IndexOf('Milestone')
                            $currDateIdx = $cols.IndexOf('MilestoneDate')
                            $prevProjIdx = $prevSchema.IndexOf('AtlasProjectName')
                            $prevMileIdx = $prevSchema.IndexOf('Milestone')
                            $prevDateIdx = $prevSchema.IndexOf('MilestoneDate')
                            
                            # Build index maps for current and previous data
                            $currentIndex = @{}
                            $previousIndex = @{}

                            foreach ($item in $rows) {
                                $key = "$($item[$currProjIdx])|$($item[$currMileIdx])|$($item[$currDateIdx])"
                                if (-not $currentIndex.ContainsKey($key)) { $currentIndex[$key] = @() }
                                $currentIndex[$key] += $item
                            }

                            if ($prevProjIdx -ge 0 -and $prevMileIdx -ge 0 -and $prevDateIdx -ge 0) {
                                foreach ($item in $prevData) {
                                    $key = "$($item[$prevProjIdx])|$($item[$prevMileIdx])|$($item[$prevDateIdx])"
                                    if (-not $previousIndex.ContainsKey($key)) { $previousIndex[$key] = @() }
                                    $previousIndex[$key] += $item
                                }
                            }

                            # Detect new/removed records
                            foreach ($key in $currentIndex.Keys) {
                                if (-not $previousIndex.ContainsKey($key)) {
                                    $parts = $key -split '\|'
                                    $changes.new_products += @{
                                        project = $parts[0]
                                        milestone = $parts[1]
                                        date = $parts[2]
                                        ww = Get-WeekNumber $parts[2]
                                    }
                                }
                            }

                            foreach ($key in $previousIndex.Keys) {
                                if (-not $currentIndex.ContainsKey($key)) {
                                    $parts = $key -split '\|'
                                    $changes.removed_products += @{
                                        project = $parts[0]
                                        milestone = $parts[1]
                                        date = $parts[2]
                                        ww = Get-WeekNumber $parts[2]
                                    }
                                }
                            }

                            # Detect value changes (for records that exist in both)
                            foreach ($key in $currentIndex.Keys) {
                                if ($previousIndex.ContainsKey($key)) {
                                    $currentItem = $currentIndex[$key][0]
                                    $previousItem = $previousIndex[$key][0]
                                    $fieldChanges = @()
                                    
                                    # Compare each column value
                                    for ($i = 0; $i -lt $cols.Count; $i++) {
                                        $prevIdx = $prevSchema.IndexOf($cols[$i])
                                        if ($prevIdx -ge 0) {
                                            $currentStr = if ($null -eq $currentItem[$i]) { '' } else { $currentItem[$i].ToString() }
                                            $previousStr = if ($null -eq $previousItem[$prevIdx]) { '' } else { $previousItem[$prevIdx].ToString() }
                                            
                                            if ($currentStr -ne $previousStr) {
                                                $fieldChanges += @{
                                                    column = $cols[$i]
                                                    old_value = $previousStr
                                                    new_value = $currentStr
                                                }
                                            }
                                        }
                                    }
                                    
                                    # Only add to changes if there are actual field changes
                                    if ($fieldChanges.Count -gt 0) {
                                        $parts = $key -split '\|'
                                        $changes.value_changes += @{
                                            project = $parts[0]
                                            milestone = $parts[1]
                                            date = $parts[2]
                                            ww = Get-WeekNumber $parts[2]
                                            changes = $fieldChanges
                                        }
                                    }
                                }
                            }
                        }
                    }
                } catch {
                    Write-Host "Warning: Could not parse previous JSON for changelog: $_"
                }
            } else {
                Write-Host "No previous release found - this appears to be the first release. Changelog will show all current items as new."
            }

            # Load previous changelog for comparison if available BEFORE saving new one
            $previousChangelog = $null
            $changelogActive = Join-Path $scriptDir "changelog.json"
            $isDuplicate = $false
            
            # Check if there's a previous version saved
            if (Test-Path $changelogActive) {
                try {
                    $previousChangelog = Get-Content $changelogActive -Raw | ConvertFrom-Json
                    Write-Host "Loaded previous changelog for comparison"
                    
                    # Increment revision number
                    if ($previousChangelog.revision) {
                        $changes.revision = $previousChangelog.revision + 1
                    }
                    
                    # Check if changes are identical to previous run (avoid duplicate entries)
                    if ($previousChangelog.new_products.Count -eq $changes.new_products.Count -and
                        $previousChangelog.removed_products.Count -eq $changes.removed_products.Count -and
                        $previousChangelog.value_changes.Count -eq $changes.value_changes.Count) {
                        
                        # Quick check: if all counts match and both are comparing against same git commit, likely duplicate
                        if ($previousChangelog.git_commit -eq $changes.git_commit) {
                            $isDuplicate = $true
                            Write-Host "Duplicate detection: Changes are identical to Rev $($previousChangelog.revision). Skipping changelog generation."
                        }
                    }
                } catch {
                    Write-Host "Warning: Could not load previous changelog: $_"
                }
            }

            # Check if there are any changes to record (and not a duplicate)
            $hasChanges = (($changes.new_products.Count -gt 0) -or 
                          ($changes.removed_products.Count -gt 0) -or 
                          ($changes.value_changes.Count -gt 0)) -and (-not $isDuplicate)
            
            if (-not $hasChanges) {
                Write-Host "No changes detected compared to git baseline. Skipping changelog generation."
                Write-Host "Current data matches the last committed release."
            } else {
                Write-Host "Changes detected: $($changes.new_products.Count) new, $($changes.removed_products.Count) removed, $($changes.value_changes.Count) modified"
                
                # Save current changelog as backup and active (JSON + CSV)
                $changelogBackup = Join-Path $dataDir "changelog_${datetime}.json"
                $changelogBackupCsv = Join-Path $dataDir "changelog_${datetime}.csv"
                $changelogActiveCsv = Join-Path $scriptDir "changelog.csv"
                
                $changes | ConvertTo-Json -Depth 10 | Out-File -FilePath $changelogBackup -Encoding UTF8
            Copy-Item -Path $changelogBackup -Destination $changelogActive -Force
            
            # Generate CSV format for current revision changes
            # Format: Rev 1 uses baseline date (from last committed backup file), Rev 2+ uses current date
            $baselineDate = $changes.baseline_date
            
            # Fallback to git_commit_date if baseline_date not available
            if (-not $baselineDate) {
                $baselineDate = $changes.git_commit_date
            }
            
            # If still missing (older changelogs), try to get it from git commit
            if (-not $baselineDate -and $changes.git_commit -and $gitRoot) {
                try {
                    $gitCommitDate = & git -C $gitRoot show -s --format=%ci $($changes.git_commit) 2>$null
                    if ($gitCommitDate) {
                        $commitDateTime = [DateTime]::Parse($gitCommitDate)
                        $baselineDate = $commitDateTime.ToString("yyyy-MM-dd")
                    }
                } catch { }
            }
            
            if (-not $baselineDate) {
                $baselineDate = "Unknown"
            }
            
            $currentDate = (Get-Date).ToString("yyyy-MM-dd")
            
            # Use baseline date for Rev 1, current date for Rev 2+
            if ($changes.revision -eq 1) {
                $revisionInfo = "Rev 1 ($baselineDate)"
            } else {
                $revisionInfo = "Rev $($changes.revision) ($currentDate)"
            }
            
            $csvBuilder = New-Object System.Text.StringBuilder
            
            foreach ($item in $changes.new_products) {
                [void]$csvBuilder.AppendLine("`"$revisionInfo`",NEW,`"$($item.project)`",`"$($item.milestone)`",`"$($item.date)`",`"$($item.ww)`",N/A,N/A,N/A")
            }
            
            foreach ($item in $changes.removed_products) {
                [void]$csvBuilder.AppendLine("`"$revisionInfo`",REMOVED,`"$($item.project)`",`"$($item.milestone)`",`"$($item.date)`",`"$($item.ww)`",N/A,N/A,N/A")
            }
            
            foreach ($item in $changes.value_changes) {
                if ($item.changes -and $item.changes.Count -gt 0) {
                    foreach ($ch in $item.changes) {
                        [void]$csvBuilder.AppendLine("`"$revisionInfo`",VALUE_CHANGE,`"$($item.project)`",`"$($item.milestone)`",`"$($item.date)`",`"$($item.ww)`",`"$($ch.column)`",`"$($ch.old_value)`",`"$($ch.new_value)`"")
                    }
                }
            }
            
            # Save backup with current revision only
            $backupCsvBuilder = New-Object System.Text.StringBuilder
            [void]$backupCsvBuilder.AppendLine("Revision,Indicator,AtlasProjectName,Milestone,Date,WW,ChangedColumn,OldValue,NewValue")
            [void]$backupCsvBuilder.Append($csvBuilder.ToString())
            $backupCsvBuilder.ToString() | Out-File -FilePath $changelogBackupCsv -Encoding UTF8
            
            # Append to active CSV (accumulate all revisions)
            if (Test-Path $changelogActiveCsv) {
                # File exists, append new revision data without extra newline
                $existingContent = Get-Content $changelogActiveCsv -Raw
                $newContent = $existingContent.TrimEnd() + "`n" + $csvBuilder.ToString().TrimEnd()
                $newContent | Out-File -FilePath $changelogActiveCsv -Encoding UTF8 -NoNewline
            } else {
                # First time, create with header
                $activeCsvBuilder = New-Object System.Text.StringBuilder
                [void]$activeCsvBuilder.AppendLine("Revision,Indicator,AtlasProjectName,Milestone,Date,WW,ChangedColumn,OldValue,NewValue")
                [void]$activeCsvBuilder.Append($csvBuilder.ToString())
                $activeCsvBuilder.ToString() | Out-File -FilePath $changelogActiveCsv -Encoding UTF8
            }
            
            Write-Host "Change logs saved to: $changelogBackup and $changelogActive (JSON + CSV)"
            }  # End of hasChanges check

            # Add changelog and comparison to the active JSON for embedding in HTML
            $jsonWithChangelog = Get-Content $activeFile -Raw | ConvertFrom-Json
            
            # Only add changelog if there were changes
            if ($hasChanges) {
                $jsonWithChangelog | Add-Member -MemberType NoteProperty -Name 'changelog' -Value $changes -Force
            }
            
            # Load ALL historical changelogs for full revision export
            $allHistoricalChangelogs = @()
            $historicalFiles = Get-ChildItem -Path $dataDir -Filter "changelog_*.json" | Sort-Object Name
            foreach ($histFile in $historicalFiles) {
                try {
                    $histData = Get-Content $histFile.FullName -Raw | ConvertFrom-Json
                    $allHistoricalChangelogs += $histData
                } catch {
                    Write-Host "Warning: Could not load $($histFile.Name): $_"
                }
            }
            
            if ($allHistoricalChangelogs.Count -gt 0) {
                $jsonWithChangelog | Add-Member -MemberType NoteProperty -Name 'all_changelogs' -Value $allHistoricalChangelogs -Force
            }
            
            # Add changelog history for comparison (only if there were changes)
            if ($previousChangelog -and $hasChanges) {
                $jsonWithChangelog | Add-Member -MemberType NoteProperty -Name 'previous_changelog' -Value $previousChangelog -Force
                
                # Build proper comparison metrics
                $currentNewList = @($changes.new_products) | Where-Object { $null -ne $_ }
                $currentRemovedList = @($changes.removed_products) | Where-Object { $null -ne $_ }
                $currentChangedList = @($changes.value_changes) | Where-Object { $null -ne $_ }
                
                $previousNewList = if ($previousChangelog.new_products) { @($previousChangelog.new_products) | Where-Object { $null -ne $_ } } else { @() }
                $previousRemovedList = if ($previousChangelog.removed_products) { @($previousChangelog.removed_products) | Where-Object { $null -ne $_ } } else { @() }
                $previousChangedList = if ($previousChangelog.value_changes) { @($previousChangelog.value_changes) | Where-Object { $null -ne $_ } } else { @() }
                
                # Calculate delta metrics
                $newProductsAddedCount = 0
                $newProductsResolvedCount = 0
                $stillPendingCount = 0
                
                # Count newly added (items in current but not in previous new_products list)
                foreach ($item in $currentNewList) {
                    $found = $previousNewList | Where-Object { $_.project -eq $item.project -and $_.milestone -eq $item.milestone }
                    if (-not $found) { $newProductsAddedCount++ }
                }
                
                # Count resolved (items that were in previous new_products but not in current new_products)
                foreach ($item in $previousNewList) {
                    $found = $currentNewList | Where-Object { $_.project -eq $item.project -and $_.milestone -eq $item.milestone }
                    if (-not $found) { 
                        $newProductsResolvedCount++ 
                    } else {
                        $stillPendingCount++
                    }
                }
                
                # Calculate change trends
                $changeInValueChanges = $currentChangedList.Count - $previousChangedList.Count
                
                $jsonWithChangelog | Add-Member -MemberType NoteProperty -Name 'changelog_comparison' -Value @{
                    current_run = @{
                        revision = $changes.revision
                        timestamp = $timestamp
                        git_commit = $changes.git_commit
                    }
                    previous_run = @{
                        revision = if ($previousChangelog.revision) { $previousChangelog.revision } else { 0 }
                        timestamp = $previousChangelog.timestamp
                        git_commit = if ($previousChangelog.git_commit) { $previousChangelog.git_commit } else { "N/A" }
                    }
                    summary = @{
                        new_products_current = $currentNewList.Count
                        new_products_previous = $previousNewList.Count
                        newly_added_since_last = $newProductsAddedCount
                        newly_resolved_since_last = $newProductsResolvedCount
                        still_pending = $stillPendingCount
                        removed_products_current = $currentRemovedList.Count
                        removed_products_previous = $previousRemovedList.Count
                        value_changes_current = $currentChangedList.Count
                        value_changes_previous = $previousChangedList.Count
                        value_changes_delta = $changeInValueChanges
                    }
                    interpretation = @{
                        status = if ($newProductsAddedCount -eq 0 -and $newProductsResolvedCount -gt 0) { "Improving" } elseif ($newProductsAddedCount -gt $newProductsResolvedCount) { "Worsening" } else { "Stable" }
                        message = if ($newProductsAddedCount -eq 0 -and $currentNewList.Count -eq 0) { "All issues resolved!" } elseif ($stillPendingCount -gt 0) { "$stillPendingCount issues still pending" } else { "No significant changes" }
                    }
                } -Force
            }
            
            $jsonWithChangelog | ConvertTo-Json -Depth 20 | Out-File -FilePath $activeFile -Encoding UTF8

        } catch {
            Write-Host "Failed to generate change logs: $_"
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
        
        # Changelog files are kept as history - no cleanup performed
        # Each run creates a new changelog that builds the historical record
        
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
