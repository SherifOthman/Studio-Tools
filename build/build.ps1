# build/build.ps1  –  Build Studio Tools into a standalone .exe + installer.
# Run from the project root:  .\build\build.ps1

$ErrorActionPreference = "Stop"
$Root    = Split-Path $PSScriptRoot -Parent
$Py      = "C:\Users\eleml\AppData\Local\Programs\Python\Python311\python.exe"
$ISCC    = "C:\Users\eleml\AppData\Local\Programs\Inno Setup 6\iscc.exe"

Set-Location $Root

Write-Host "==> Installing / updating dependencies..." -ForegroundColor Cyan
& $Py -m pip install -q -r requirements.txt

Write-Host "==> Generating icon..." -ForegroundColor Cyan
& $Py build\gen_icon.py

Write-Host "==> PyInstaller – building EXE..." -ForegroundColor Cyan
& $Py -m PyInstaller `
    --noconfirm --onefile --windowed `
    --name "StudioTools" `
    --icon "app\assets\app.ico" `
    --add-data "app\assets\app.ico;app\assets" `
    main.py

if (-not (Test-Path "dist\StudioTools.exe")) {
    Write-Error "PyInstaller failed – no exe produced."
    exit 1
}
Write-Host ("EXE: " + [math]::Round((Get-Item "dist\StudioTools.exe").Length/1MB,1) + " MB") -ForegroundColor Green

Write-Host "==> Inno Setup – building installer..." -ForegroundColor Cyan
& $ISCC /Q "build\installer.iss"

if (Test-Path "dist\StudioTools-Setup.exe") {
    Write-Host ("Installer: " + [math]::Round((Get-Item "dist\StudioTools-Setup.exe").Length/1MB,1) + " MB") -ForegroundColor Green
} else {
    Write-Warning "Installer not produced (check build\installer.iss)"
}

Write-Host "==> Done." -ForegroundColor Green
