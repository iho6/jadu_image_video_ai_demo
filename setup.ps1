#requires -Version 5.1
<#
.SYNOPSIS
  Windows parity for repo-root setup.sh: venv, deps, LFS, models, custom nodes, start ComfyUI.

Environment (optional):
  HF_TOKEN            — Hugging Face token for utils/download_models.py
  GITHUB_PAT          — For git LFS over HTTPS if your remote needs auth
  COMFY_PORT          — Listen port (default 8188)
  COMFY_CACHE_ENABLE  — Set to 1/true/yes to enable cache; otherwise --cache-none is passed
#>

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $RepoRoot

function Write-SetupLog([string]$Message) {
    Write-Host ("[setup] {0}" -f $Message)
}

function Test-ComfyCacheOn {
    $v = $env:COMFY_CACHE_ENABLE
    if ([string]::IsNullOrWhiteSpace($v)) { return $false }
    switch -Regex ($v.Trim().ToLowerInvariant()) {
        '^(1|true|yes|y|on)$' { return $true }
        default { return $false }
    }
}

function Invoke-CustomNodeInstaller {
    $installer = Join-Path $RepoRoot "utils\install_custom_nodes.sh"
    $target = Join-Path $RepoRoot "comfyui\custom_nodes"

    if (-not (Test-Path -LiteralPath $installer)) {
        Write-Warning "Custom-node installer not found at $installer; skipping."
        return
    }

    $bash = Get-Command bash -ErrorAction SilentlyContinue
    if (-not $bash) {
        Write-Warning "bash not found; skipping custom-node installer."
        return
    }

    & $bash.Path $installer $target
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Custom-node installer failed."
    }
}

$gitLfs = Get-Command git-lfs -ErrorAction SilentlyContinue
if (-not $gitLfs) {
    Write-Warning "git-lfs not found; install Git LFS if you need LFS assets."
} else {
    Push-Location $RepoRoot
    try {
        git lfs install --local 2>$null
        Write-SetupLog "git lfs pull..."
        git lfs pull
        if ($LASTEXITCODE -ne 0) {
            Write-Error "git lfs pull failed (check HTTPS credentials / GITHUB_PAT)."
        }
    } finally {
        Pop-Location
    }
}

$venvPath = Join-Path $RepoRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$requirements = Join-Path $RepoRoot "requirements.txt"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "python not found on PATH. Install Python 3 and retry."
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-SetupLog "Creating venv at $venvPath"
    & python -m venv $venvPath
}

Write-SetupLog "Upgrading pip tooling..."
& $venvPython -m pip install --upgrade pip "setuptools<82" wheel
Write-SetupLog "Installing PyTorch (cu121)..."
& $venvPython -m pip install torch torchvision torchaudio `
    --index-url https://download.pytorch.org/whl/cu121
Write-SetupLog "Installing requirements.txt..."
& $venvPython -m pip install -r $requirements

Write-SetupLog "Running custom-node installer (placeholder-safe)..."
Invoke-CustomNodeInstaller

Write-SetupLog "Downloading models (utils/download_models.py --img-edit --edit-angle)..."
& $venvPython (Join-Path $RepoRoot "utils\download_models.py") --img-edit --edit-angle

$port = 8188
if (-not [string]::IsNullOrWhiteSpace($env:COMFY_PORT)) {
    $parsedPort = 0
    if ([int]::TryParse($env:COMFY_PORT.Trim(), [ref]$parsedPort)) {
        $port = $parsedPort
    } else {
        Write-Warning "Invalid COMFY_PORT; using 8188"
    }
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$pyArgs = @(
    "main.py",
    "--disable-metadata",
    "--listen", "127.0.0.1",
    "--port", "$port"
)
if (-not (Test-ComfyCacheOn)) {
    $pyArgs += "--cache-none"
}

Write-SetupLog "Starting ComfyUI on 127.0.0.1:$port (background)..."
Start-Process -FilePath $venvPython -ArgumentList $pyArgs -WorkingDirectory $RepoRoot -WindowStyle Hidden

Write-SetupLog "Waiting for port $port..."
$deadline = (Get-Date).AddSeconds(120)
$ready = $false
while ((Get-Date) -lt $deadline) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $c.Connect("127.0.0.1", $port)
        $c.Close()
        $ready = $true
        break
    } catch {
        Start-Sleep -Milliseconds 250
    }
}

if (-not $ready) {
    Write-Error "Timeout waiting for Comfy on 127.0.0.1:$port"
}

Write-SetupLog "Comfy ready."
Write-Host ""
Write-Host "Inference CLIs can use:"
Write-Host ('  $env:COMFY_PORT = "{0}"' -f $port)
Write-Host ('  $env:COMFY_URL = "http://127.0.0.1:{0}"' -f $port)
Write-Host ""
