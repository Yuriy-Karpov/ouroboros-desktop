# Build script for Ouroboros on Windows
# Run from repo root: powershell -ExecutionPolicy Bypass -File build_windows.ps1

$ErrorActionPreference = "Stop"

$Version = (Get-Content VERSION).Trim()
$ArchiveName = "Ouroboros-${Version}-windows-x64.zip"
$ModeFile = ".ouroboros-python-env"
$PythonEnvMode = if (Test-Path $ModeFile) {
    (Get-Content $ModeFile -Raw).Trim()
} else {
    "global"
}
$UvBin = if ($env:OUROBOROS_UV_BIN) { $env:OUROBOROS_UV_BIN } else { "uv" }
$BuildVenv = if ($env:BUILD_VENV) { $env:BUILD_VENV } else { ".build-venv" }
$BuildPython = "python"

Write-Host "=== Building Ouroboros for Windows (v${Version}) ==="

if (-not (Test-Path "python-standalone\python.exe")) {
    Write-Host "ERROR: python-standalone\ not found."
    Write-Host "Run first: powershell -ExecutionPolicy Bypass -File scripts/download_python_standalone.ps1"
    exit 1
}

Write-Host "--- Installing launcher dependencies ---"
if ($PythonEnvMode -eq "uv") {
    & $UvBin venv --allow-existing --python python $BuildVenv
    & $UvBin pip install --python "$BuildVenv\Scripts\python.exe" -r requirements-launcher.txt
    $BuildPython = "$BuildVenv\Scripts\python.exe"
} else {
    python -m pip install -q -r requirements-launcher.txt
}

Write-Host "--- Syncing agent dependencies ---"
if ($PythonEnvMode -eq "uv") {
    & $UvBin venv --allow-existing --python "python-standalone\python.exe" ".venv"
    $env:VIRTUAL_ENV = (Join-Path (Get-Location) ".venv")
    $env:UV_PROJECT_ENVIRONMENT = $env:VIRTUAL_ENV
    $env:PATH = "$env:VIRTUAL_ENV\Scripts;$env:PATH"
    & $UvBin sync --active --extra browser
} else {
    & "python-standalone\python.exe" -m pip install -q -r requirements.txt
}

if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

$env:PYINSTALLER_CONFIG_DIR = Join-Path (Get-Location) ".pyinstaller-cache"
New-Item -ItemType Directory -Force -Path $env:PYINSTALLER_CONFIG_DIR | Out-Null

Write-Host "--- Running PyInstaller ---"
& $BuildPython -m PyInstaller Ouroboros.spec --clean --noconfirm

Write-Host ""
Write-Host "=== Creating archive ==="
Compress-Archive -Path "dist\Ouroboros" -DestinationPath "dist\$ArchiveName" -Force

Write-Host ""
Write-Host "=== Done ==="
Write-Host "Archive: dist\$ArchiveName"
Write-Host ""
Write-Host "To run: extract and execute Ouroboros\Ouroboros.exe"
