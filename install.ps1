# Install LectureDub on Windows with an NVIDIA GPU.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python 3.11 or newer is required."
}

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python 3.11 or newer is required."
}

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Error "ffmpeg is required. Install it with: winget install Gyan.FFmpeg"
}

python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install ".[nvidia,desktop]"
.\.venv\Scripts\lecturedub doctor
Write-Host "Run: .\.venv\Scripts\lecturedub app"
