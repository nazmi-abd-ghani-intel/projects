# Build script for FFR Check GUI Application
# Creates an executable using PyInstaller

Write-Host "`n=== FFR Check GUI - Build Script ===" -ForegroundColor Green
Write-Host ""

# Check if PyInstaller is installed
Write-Host "Checking for PyInstaller..." -ForegroundColor Cyan
try {
    $pyinstallerVersion = & pyinstaller --version 2>&1
    Write-Host "  Found PyInstaller: $pyinstallerVersion" -ForegroundColor Green
} catch {
    Write-Host "  PyInstaller not found!" -ForegroundColor Red
    Write-Host "  Installing PyInstaller..." -ForegroundColor Yellow
    pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`nFailed to install PyInstaller. Please install manually:" -ForegroundColor Red
        Write-Host "  pip install pyinstaller" -ForegroundColor Yellow
        exit 1
    }
}

# Clean previous builds
Write-Host "`nCleaning previous builds..." -ForegroundColor Cyan
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
    Write-Host "  Removed build/ directory" -ForegroundColor Gray
}
if (Test-Path "dist") {
    Remove-Item -Recurse -Force "dist"
    Write-Host "  Removed dist/ directory" -ForegroundColor Gray
}

# Build the executable
Write-Host "`nBuilding executable..." -ForegroundColor Cyan
Write-Host "  Using: gui_app.spec" -ForegroundColor Gray
Write-Host ""

pyinstaller gui_app.spec --clean

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n=== BUILD SUCCESSFUL ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Executable created at:" -ForegroundColor Cyan
    Write-Host "  dist\FFRCheck\FFRCheck.exe" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To run the application:" -ForegroundColor Cyan
    Write-Host "  .\dist\FFRCheck\FFRCheck.exe" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To distribute:" -ForegroundColor Cyan
    Write-Host "  Zip the entire 'dist\FFRCheck' folder" -ForegroundColor Yellow
    Write-Host ""
    
    # Show file size
    $exePath = "dist\FFRCheck\FFRCheck.exe"
    if (Test-Path $exePath) {
        $fileSize = (Get-Item $exePath).Length / 1MB
        Write-Host "Executable size: $("{0:N2}" -f $fileSize) MB" -ForegroundColor Gray
    }
    
    # Ask to run
    Write-Host ""
    $response = Read-Host "Do you want to run the GUI now? (y/n)"
    if ($response -eq 'y' -or $response -eq 'Y') {
        Start-Process "dist\FFRCheck\FFRCheck.exe"
    }
    
} else {
    Write-Host "`n=== BUILD FAILED ===" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please check the error messages above." -ForegroundColor Yellow
    Write-Host "Common issues:" -ForegroundColor Cyan
    Write-Host "  - Missing dependencies: pip install -r requirements.txt" -ForegroundColor Gray
    Write-Host "  - Missing files: Ensure config.json and src/ exist" -ForegroundColor Gray
    Write-Host ""
    exit 1
}
