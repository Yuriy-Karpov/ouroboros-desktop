$ErrorActionPreference = "Stop"

$ModeFile = ".ouroboros-python-env"
$UvBin = if ($env:OUROBOROS_UV_BIN) { $env:OUROBOROS_UV_BIN } else { "uv" }
$PythonCmd = if ($env:PYTHON_CMD) { $env:PYTHON_CMD } else { "python" }

$Mode = $args[0]
if ([string]::IsNullOrWhiteSpace($Mode)) {
    throw "Usage: powershell -ExecutionPolicy Bypass -File scripts/setup_python_env.ps1 <uv|global>. Use scripts/install.ps1 for interactive installation."
}

$Mode = switch ($Mode.Trim().ToLowerInvariant()) {
    "uv" { "uv" }
    "venv" { "uv" }
    "uv-venv" { "uv" }
    "global" { "global" }
    "pip" { "global" }
    default { throw "Unknown mode: $Mode" }
}

Set-Content -Path $ModeFile -Value "$Mode`n" -Encoding utf8NoBOM
Write-Host "Saved mode to $ModeFile: $Mode"

if ($Mode -eq "uv") {
    & $UvBin venv --allow-existing --python $PythonCmd ".venv"
    $env:VIRTUAL_ENV = Join-Path (Get-Location) ".venv"
    $env:UV_PROJECT_ENVIRONMENT = $env:VIRTUAL_ENV
    $env:PATH = "$env:VIRTUAL_ENV\Scripts;$env:PATH"
    & $UvBin sync --active --extra browser
} else {
    & $PythonCmd -m pip install -r requirements.txt
}

Write-Host "Python environment is ready in mode: $Mode"
