# WallDrop Installer & Launcher
# Run this ONCE with: Right-click → Run with PowerShell
# Python must remain installed for the app and its scheduled task to run.

$ErrorActionPreference = "Stop"
$AppName = "WallDrop"
$AppDir  = "$env:LOCALAPPDATA\WallDrop"
$Script  = "$AppDir\walldrop.py"
$Icon    = "$AppDir\walldrop.ico"
$Shortcut = "$env:USERPROFILE\Desktop\WallDrop.lnk"

Write-Host ""
Write-Host "  ◈ WallDrop Installer" -ForegroundColor Magenta
Write-Host "  Anime Wallpaper Changer" -ForegroundColor DarkGray
Write-Host ""

# ── 1. Check Python ──────────────────────────────────────────────────────────
Write-Host "  [1/4] Checking Python..." -ForegroundColor Cyan
$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3") {
            $python = $cmd
            Write-Host "        Found: $ver" -ForegroundColor Green
            break
        }
    } catch {}
}

if (-not $python) {
    Write-Host ""
    Write-Host "  ✗ Python not found!" -ForegroundColor Red
    Write-Host "  Please install Python 3 from: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "  Make sure to check 'Add Python to PATH' during install." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "  Press Enter to open the Python download page"
    Start-Process "https://www.python.org/downloads/"
    exit 1
}

# ── 2. Copy app to AppData (no UAC needed) ──────────────────────────────────
Write-Host "  [2/4] Installing to $AppDir..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $AppDir | Out-Null

$sourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Copy-Item "$sourceDir\walldrop.py" $AppDir -Force

Write-Host "        Installed." -ForegroundColor Green

# ── 3. Create Desktop Shortcut ───────────────────────────────────────────────
Write-Host "  [3/4] Creating desktop shortcut..." -ForegroundColor Cyan

$pythonFull = (Get-Command $python).Source
$WshShell = New-Object -ComObject WScript.Shell
$lnk = $WshShell.CreateShortcut($Shortcut)
$lnk.TargetPath       = $pythonFull
$lnk.Arguments        = "`"$Script`""
$lnk.WorkingDirectory = $AppDir
$lnk.Description      = "WallDrop - Anime Wallpaper Changer"
$lnk.WindowStyle      = 1
$lnk.Save()

Write-Host "        Shortcut created on Desktop." -ForegroundColor Green

# ── 4. Launch ────────────────────────────────────────────────────────────────
Write-Host "  [4/4] Launching WallDrop..." -ForegroundColor Cyan
Start-Process $pythonFull -ArgumentList "`"$Script`"" -WorkingDirectory $AppDir

Write-Host ""
Write-Host "  ✓ Done! WallDrop is running." -ForegroundColor Green
Write-Host "  Use the Desktop shortcut next time." -ForegroundColor DarkGray
Write-Host ""
Start-Sleep -Seconds 2
