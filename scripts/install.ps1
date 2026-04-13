$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir
$UvInstallDocsUrl = "https://docs.astral.sh/uv/getting-started/installation/"

function Select-Mode {
    $Labels = @(
        "uv + .venv (recommended)",
        "global pip"
    )
    $Values = @("uv", "global")
    $Selected = 0

    while ($true) {
        Clear-Host
        Write-Host "Ouroboros installer"
        Write-Host "Select Python environment mode with Up/Down and press Enter:"
        for ($i = 0; $i -lt $Labels.Count; $i++) {
            if ($i -eq $Selected) {
                Write-Host ([string]::Concat(" ● ", $Labels[$i])) -ForegroundColor Green
            } else {
                Write-Host ([string]::Concat(" ○ ", $Labels[$i]))
            }
        }

        $Key = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        switch ($Key.VirtualKeyCode) {
            13 { return $Values[$Selected] }
            38 { $Selected = ($Selected + $Labels.Count - 1) % $Labels.Count }
            40 { $Selected = ($Selected + 1) % $Labels.Count }
        }
    }
}

$Mode = Select-Mode
if ($Mode -eq "uv") {
    $UvCommand = if ($env:OUROBOROS_UV_BIN) { $env:OUROBOROS_UV_BIN } else { "uv" }
    if (-not (Get-Command $UvCommand -ErrorAction SilentlyContinue)) {
        throw "uv is not installed on this system. Install uv first: $UvInstallDocsUrl"
    }
}
& powershell -ExecutionPolicy Bypass -File "scripts/setup_python_env.ps1" $Mode
