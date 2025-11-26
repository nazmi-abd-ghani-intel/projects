param(
    [int]$Port = 8000,
    [switch]$Open
)

$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Definition }
Push-Location $scriptDir
try {
    $started = $false

    if (Get-Command python -ErrorAction SilentlyContinue) {
        $py = (Get-Command python).Source
        Write-Host "Starting Python HTTP server on port $Port using: $py"
        Start-Process -FilePath $py -ArgumentList '-m', 'http.server', "$Port" -WindowStyle Hidden
        $started = $true
    } elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        $py = (Get-Command python3).Source
        Write-Host "Starting Python3 HTTP server on port $Port using: $py"
        Start-Process -FilePath $py -ArgumentList '-m', 'http.server', "$Port" -WindowStyle Hidden
        $started = $true
    } elseif (Get-Command npx -ErrorAction SilentlyContinue) {
        Write-Host "Starting http-server via npx on port $Port"
        Start-Process -FilePath (Get-Command npx).Source -ArgumentList 'http-server', '-p', "$Port" -WindowStyle Hidden
        $started = $true
    }

    if (-not $started) {
        Write-Host "No supported server runtime found. Install Python 3 or Node (npx)."
        Write-Host 'Or run manually:'
        Write-Host "  python -m http.server $Port"
        exit 1
    }

    $url = "http://localhost:$Port/prodmilestone_timeline.html"
    Write-Host "Server started (background). Open the timeline at: $url"
    if ($Open) { Start-Process $url }
} finally {
    Pop-Location
}
