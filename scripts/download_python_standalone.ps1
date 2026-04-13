# Downloads python-build-standalone for Windows (x86_64)
# Run from repo root: powershell -ExecutionPolicy Bypass -File scripts/download_python_standalone.ps1

$ErrorActionPreference = "Stop"

$Release = "20260211"
$PyVersion = "3.10.19"
$Dest = "python-standalone"
$Platform = "x86_64-pc-windows-msvc"
$ModeFile = ".ouroboros-python-env"
$PythonEnvMode = if (Test-Path $ModeFile) {
    (Get-Content $ModeFile -Raw).Trim()
} else {
    "global"
}
$UvBin = if ($env:OUROBOROS_UV_BIN) { $env:OUROBOROS_UV_BIN } else { "uv" }

$Filename = "cpython-${PyVersion}+${Release}-${Platform}-install_only_stripped.tar.gz"
$Url = "https://github.com/astral-sh/python-build-standalone/releases/download/${Release}/${Filename}"

Write-Host "=== Downloading Python ${PyVersion} for ${Platform} ==="
Write-Host "URL: ${Url}"

if (Test-Path $Dest) { Remove-Item -Recurse -Force $Dest }
if (Test-Path "_python_tmp") { Remove-Item -Recurse -Force "_python_tmp" }
New-Item -ItemType Directory -Path "_python_tmp" | Out-Null

$ArchivePath = "_python_tmp\python.tar.gz"
Write-Host "Downloading..."
Invoke-WebRequest -Uri $Url -OutFile $ArchivePath -UseBasicParsing

Write-Host "Extracting..."
tar -xzf $ArchivePath -C "_python_tmp"

Move-Item "_python_tmp\python" $Dest
Remove-Item -Recurse -Force "_python_tmp"

Write-Host ""
Write-Host "=== Syncing agent dependencies ==="
if ($PythonEnvMode -eq "uv") {
    & $UvBin venv --allow-existing --python "${Dest}\python.exe" ".venv"
    $env:VIRTUAL_ENV = (Join-Path (Get-Location) ".venv")
    $env:UV_PROJECT_ENVIRONMENT = $env:VIRTUAL_ENV
    $env:PATH = "$env:VIRTUAL_ENV\Scripts;$env:PATH"
    & $UvBin sync --active --extra browser
} else {
    & "${Dest}\python.exe" -m pip install --quiet -r requirements.txt
}

Write-Host ""
Write-Host "=== Installing optional: local model support ==="
try {
    if ($PythonEnvMode -eq "uv") {
        & $UvBin pip install --python ".venv\Scripts\python.exe" "llama-cpp-python[server]" 2>&1
    } else {
        & "${Dest}\python.exe" -m pip install --quiet "llama-cpp-python[server]" 2>&1
    }
    Write-Host "llama-cpp-python installed successfully"
} catch {
    Write-Warning "llama-cpp-python install failed - local model support will not be available"
}

Write-Host ""
Write-Host "=== Done ==="
Write-Host "Python: ${Dest}\python.exe"
& "${Dest}\python.exe" --version
