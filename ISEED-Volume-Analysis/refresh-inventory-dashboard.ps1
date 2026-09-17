param(
    [ValidateSet('Outlook', 'Graph')]
    [string]$Method = 'Outlook',

    [string]$OutlookFolderPath = '\\nazmi.abd.ghani@intel.com\DDG\iSEED',

    # Graph API only: Azure AD app registration (public client) used for device-code sign-in.
    [string]$GraphClientId,
    [string]$GraphTenantId = 'common',

    [string]$SnapshotDirectory = (Join-Path $PSScriptRoot 'Input\Snapshots'),
    [string]$DashboardPath = (Join-Path $PSScriptRoot 'inventory-dashboard.html'),
    [switch]$OpenDashboard = $true
)

$ErrorActionPreference = 'Stop'

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

    Write-Output $deviceResponse.message
    if ($OpenDashboard) {
        try { Start-Process $deviceResponse.verification_uri } catch {}
    }

    $interval = [int]($deviceResponse.interval ?? 5)
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
    throw 'Device code sign-in timed out before the user completed authentication.'
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

New-Item -ItemType Directory -Force -Path $SnapshotDirectory | Out-Null

if ($Method -eq 'Graph') {
    $accessToken = Get-GraphAccessToken -ClientId $GraphClientId -TenantId $GraphTenantId
    $folderId = Find-GraphFolderId -AccessToken $accessToken -FolderPath $OutlookFolderPath
    $savedFiles = Save-AttachmentsViaGraph -AccessToken $accessToken -FolderId $folderId -SnapshotDirectory $SnapshotDirectory
} else {
    $savedFiles = Save-AttachmentsViaOutlook -FolderPath $OutlookFolderPath -SnapshotDirectory $SnapshotDirectory
}

$records = @(
    foreach ($file in Get-ChildItem -LiteralPath $SnapshotDirectory -Filter '*.txt') {
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
    }
)

if (-not (Test-Path -LiteralPath $DashboardPath)) {
    throw "Dashboard not found: $DashboardPath"
}

$json = $records | ConvertTo-Json -Compress -Depth 4

$buildProductConfig = Join-Path $PSScriptRoot 'build-product-config.ps1'
$productConfigPath = Join-Path $PSScriptRoot 'Input\product-config.json'
if (Test-Path -LiteralPath $buildProductConfig) {
    & $buildProductConfig
}
$productConfigJson = '{}'
if (Test-Path -LiteralPath $productConfigPath) {
    $productConfigJson = (Get-Content -LiteralPath $productConfigPath -Raw | ConvertFrom-Json) | ConvertTo-Json -Compress -Depth 6
}

$html = [IO.File]::ReadAllText($DashboardPath)
$dataStart = $html.IndexOf('const DATA=')
$formatMarker = ';const fmt='
$formatStart = $html.IndexOf($formatMarker, $dataStart)
if ($dataStart -lt 0 -or $formatStart -lt 0) {
    throw "Dashboard data marker was not found in $DashboardPath"
}

$prefix = $html.Substring(0, $dataStart)
$suffix = $html.Substring($formatStart + 1)
$updated = $prefix + "const DATA=$json;const PRODUCT_CONFIG=$productConfigJson;" + $suffix

[IO.File]::WriteAllText(
    $DashboardPath,
    $updated,
    (New-Object Text.UTF8Encoding($false))
)

Write-Output "Method: $Method"
Write-Output "Mail folder: $OutlookFolderPath"
Write-Output "Attachments refreshed: $($savedFiles.Count)"
Write-Output "Inventory records embedded: $($records.Count)"
Write-Output "Dashboard updated: $DashboardPath"
Write-Output "Product config embedded: $productConfigPath"

if ($OpenDashboard) {
    Start-Process $DashboardPath
}
